#!/usr/bin/env python3
"""D5-A2 Heldout Feature Validation Smoke (Public Aggregate-Only).

This module implements the **D5-A2 heldout feature validation smoke**.
It validates whether D5-A1's retrieval-derived feature bucket
reproduces on fresh heldout external retrieval samples. It loads the
D5-A1 committed artifact as the preregistered feature source, runs
new heldout ContextBench verified Python rows 21-40 and RepoQA Python
needles 11-20 with methods bm25/regex/symbol, computes the same
retrieval-derived utility proxy, and checks whether the heldout
metrics support the D5-A1 feature buckets.

D5-A2 is explicitly **not** calibration, **not** a calibrated model
claim, **not** a policy/default recommendation, **not** a method
winner claim, **not** an external benchmark performance claim, **not**
a downstream agent value claim, **not** a leaderboard entry, and
**not** a runtime/retriever/pack/backend/default-policy/EvidenceCore
semantic change. It validates only the retrieval-feature stability
component from D5-A1; it does NOT validate live-provider/downstream
alignment. It makes NO provider calls and NO remote provider calls.

Claim boundary (binding):

* Claim level: ``heldout_retrieval_feature_validation_smoke_only``.
* Status enum: ``heldout_feature_validation_pass`` | ``partial`` |
  ``unavailable_with_reason`` | ``fail_forbidden_scan`` |
  ``fail_schema_contract``.
* Mode: ``heldout_contextbench_repoqa_feature_validation``; phase
  ``D5-A2``.

Validation outcomes (fixed allowlist):

* ``retrieval_feature_validation_supported``: all preregistered
  retrieval features reproduce on heldout data.
* ``retrieval_feature_validation_mixed``: some features reproduce,
  some do not.
* ``retrieval_feature_validation_not_supported``: no features
  reproduce.
* ``unavailable_with_reason``: heldout data unavailable.

Utility formula (fixed diagnostic proxy; unchanged from F1-C/F1-D):

```text
utility = file_hit + 0.25*mrr + 0.5*span_f0.5 - miss_penalty
miss_penalty = 0.25 if file_recall@10 == 0 else 0
```

Privacy / license boundary (binding):

* Public artifact/docs/workflow uploads aggregate-only.
* No row/needle IDs, repo URLs/names, commits, queries/descriptions,
  paths/spans/line ranges, source/snippets, generated JSONL, retrieval
  rows, per-row/per-needle metrics, hashes, stdout/stderr, clone paths,
  provider fields, winner/best/default/calibration claims.

Run::

    python3 -m py_compile eval/d5a2_heldout_feature_validation.py
    python3 eval/d5a2_heldout_feature_validation.py --self-test
    python3 eval/d5a2_heldout_feature_validation.py \\
        --contextbench-row-offset 20 --contextbench-row-limit 20 \\
        --repoqa-needle-offset 10 --repoqa-needle-limit 10 \\
        --methods bm25,regex,symbol \\
        --out artifacts/d5a2_heldout_feature_validation/\\
d5a2_heldout_feature_validation_report.json
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

# Reuse F1-D and D5-A1 scanner primitives. The ``eval`` directory has no
# ``__init__.py`` (flat script directory), so we add this file's parent
# to ``sys.path`` and import the modules directly. D5-A2 does NOT mutate
# F1-D/D5-A1/C5 result semantics.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402
import c5c_contextbench_verified_method_matrix_scale_smoke as c5c  # noqa: E402
import c5d_repoqa_bm25_retrieval_smoke as c5d  # noqa: E402
import c5e_repoqa_method_matrix_smoke as c5e  # noqa: E402
import d5a1_automated_calibration_feature_table as d5a1  # noqa: E402
import f1d_cross_benchmark_retrieval_robustness as f1d  # noqa: E402
import f1c_cross_benchmark_retrieval_utility as f1c  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants (D5-A2 owned)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "d5a2_heldout_feature_validation.v1"
GENERATED_BY = "eval/d5a2_heldout_feature_validation.py"
CLAIM_LEVEL = "heldout_retrieval_feature_validation_smoke_only"
MODE = "heldout_contextbench_repoqa_feature_validation"
PHASE = "D5-A2"

STATUS_PASS = "heldout_feature_validation_pass"
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

# Validation outcome labels (fixed allowlist).
OUTCOME_SUPPORTED = "retrieval_feature_validation_supported"
OUTCOME_MIXED = "retrieval_feature_validation_mixed"
OUTCOME_NOT_SUPPORTED = "retrieval_feature_validation_not_supported"
OUTCOME_UNAVAILABLE = "unavailable_with_reason"

ALL_OUTCOMES: tuple[str, ...] = (
    OUTCOME_SUPPORTED,
    OUTCOME_MIXED,
    OUTCOME_NOT_SUPPORTED,
    OUTCOME_UNAVAILABLE,
)

SELF_TEST_CHECKS_TOTAL = 88

DEFAULT_OUT = Path(
    "artifacts/d5a2_heldout_feature_validation/"
    "d5a2_heldout_feature_validation_report.json"
)

# Hard caps. ContextBench default offset 20, limit 20 (rows 21-40). RepoQA
# default offset 10, limit 10 (needles 11-20).
CONTEXTBENCH_ROW_OFFSET_DEFAULT = 20
CONTEXTBENCH_ROW_LIMIT_DEFAULT = 20
CONTEXTBENCH_ROW_LIMIT_HARD_CAP = 20
REPOQA_NEEDLE_OFFSET_DEFAULT = 10
REPOQA_NEEDLE_LIMIT_DEFAULT = 10
REPOQA_NEEDLE_LIMIT_HARD_CAP = 10

# D5-A1 input artifact path (preregistered feature source).
D5A1_ARTIFACT_PATH = Path(
    "artifacts/d5a1_automated_calibration_feature_table/"
    "d5a1_automated_calibration_feature_table_report.json"
)
D5A1_EXPECTED_SCHEMA = "d5a1_automated_calibration_feature_table.v1"
D5A1_EXPECTED_STATUS = "automated_calibration_feature_table_pass"

# Methods / metrics / benchmarks (reused from F1-D; unchanged allowlists).
ALLOWED_METHODS: tuple[str, ...] = f1c.ALLOWED_METHODS
DEFAULT_METHODS: tuple[str, ...] = f1c.DEFAULT_METHODS
BASELINE_METHOD = f1c.BASELINE_METHOD
ALL_METHOD_LABELS: tuple[str, ...] = f1c.ALL_METHOD_LABELS
METRIC_NAMES: tuple[str, ...] = f1c.METRIC_NAMES
BENCHMARKS: tuple[str, ...] = f1c.BENCHMARKS
CONTEXTBENCH_BENCHMARK = f1c.CONTEXTBENCH_BENCHMARK
REPOQA_BENCHMARK = f1c.REPOQA_BENCHMARK

# Failure categories (kept SEPARATE; reused from F1-C).
CONTEXTBENCH_FAILURE_CATEGORIES: tuple[str, ...] = (
    f1c.CONTEXTBENCH_FAILURE_CATEGORIES
)
REPOQA_FAILURE_CATEGORIES: tuple[str, ...] = f1c.REPOQA_FAILURE_CATEGORIES

# Utility formula constants (reused from F1-C; unchanged).
MRR_WEIGHT = f1c.MRR_WEIGHT
SPAN_F_WEIGHT = f1c.SPAN_F_WEIGHT
MISS_PENALTY = f1c.MISS_PENALTY

# ---------------------------------------------------------------------------
# Safe booleans true (only when actually true).
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "heldout_feature_validation_executed": False,
    "contextbench_rows_read": False,
    "repoqa_needles_read": False,
    "openlocus_retrieval_executed": False,
    "score_py_metrics_computed": False,
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
}

# ---------------------------------------------------------------------------
# No-claim / no-runtime-change flags (all MUST be false).
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "true_e_s_calibration_claimed": False,
    "automated_e_s_full_calibration_claimed": False,
    "human_e_s_calibration_claimed": False,
    "calibrated_model_claimed": False,
    "policy_recommendation_claimed": False,
    "method_winner_claimed": False,
    "external_benchmark_performance_claimed": False,
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

LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication": "aggregate_only_heldout_validation",
}

# ---------------------------------------------------------------------------
# D5-A1 input claim flags that must be false.
# ---------------------------------------------------------------------------

UNSAFE_D5A1_CLAIM_FLAGS: tuple[str, ...] = d5a1.UNSAFE_INPUT_CLAIM_FLAGS

# ---------------------------------------------------------------------------
# Public artifact scanner (D5-A2 owned, strict, fail-closed).
# ---------------------------------------------------------------------------

D5A2_RECORD_CONTAINERS: frozenset[str] = frozenset(
    {
        "heldout_benchmark_method_records",
        "validation_records",
        "validation_summary_records",
    }
)

# D5-A2-specific forbidden keys (in addition to D5-A1 scanner).
D5A2_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        # Per-unit metric arrays.
        "per_row_metrics",
        "per_needle_metrics",
        "row_metrics",
        "needle_metrics",
        "row_hashes",
        "needle_hashes",
        "per_unit_metrics",
        "per_unit_utility",
        # Calibration / policy / default / winner claims.
        "calibrated_model",
        "calibrated_label",
        "calibration_applied",
        "calibration_performed",
        "policy_recommendation",
        "recommended_policy",
        "recommended_default",
        "recommended_method",
        "default_method",
        "winner",
        "best_method",
        "best_arm",
        "best_family",
        "preferred_method",
        "preferred_policy",
        # Raw task text / provider payloads.
        "task_text",
        "task_prompt",
        "provider_payload",
        "raw_payload",
        # Raw input artifact content.
        "input_artifact_path",
        "input_artifact_content",
        "input_artifact_json",
        "raw_input",
        "raw_artifact",
    }
)

D5A2_SAFE_VALUE_PATH_LAST_KEYS: frozenset[str] = frozenset(
    d5a1.D5A1_SAFE_VALUE_PATH_LAST_KEYS
    | {
        "feature_name",
        "preregistered_bucket",
        "heldout_metric",
        "heldout_direction",
        "supported",
        "outcome",
        "outcome_count",
        "readiness_bucket",
        "d5a1_schema_version",
        "d5a1_status",
        "d5a1_claim_safe",
        "benchmark",
        "method",
        "metric",
        "sample_count",
        "contextbench_sample_count",
        "repoqa_sample_count",
        "row_offset",
        "row_limit",
        "needle_offset",
        "needle_limit",
        "heldout_feature_validation_executed",
    }
)

_RE_RAW_MODEL_PREFIX = re.compile(r"\[mk\]", re.IGNORECASE)
_SECRET_SENTINEL = "[redacted_secret]"
_ROUTING_PREFIX_SENTINEL = "[" + "m" + "k]"


def _path_last_key(path: str) -> str:
    last = path.rsplit(".", 1)[-1]
    return last.split("[")[0]


def _is_safe_value_path(path: str) -> bool:
    return _path_last_key(path) in D5A2_SAFE_VALUE_PATH_LAST_KEYS


def _scan_d5a2_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                if key_str in D5A2_FORBIDDEN_KEYS:
                    violations.append(
                        {
                            "category": "forbidden_d5a2_key",
                            "path": sub_path,
                        }
                    )
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


def _scan_d5a2_records_shape(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        for container in D5A2_RECORD_CONTAINERS:
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


def _scan_d5a2(obj: Any) -> list[dict[str, Any]]:
    """Combined D5-A2 scanner (reuses D5-A1 scanner + D5-A2 checks)."""
    violations: list[dict[str, Any]] = []
    for v in d5a1._scan_d5a1(obj):
        if v.get("category") == "forbidden_field_name_value" and _is_safe_value_path(
            v.get("path", "")
        ):
            continue
        if v.get("category") == "forbidden_f1c_container_key":
            continue
        if v.get("category") == "forbidden_d5a1_key":
            # D5-A2 has its own forbidden keys; suppress D5-A1 duplicates
            # but keep D5-A2-specific findings below.
            continue
        violations.append(v)
    violations.extend(_scan_d5a2_forbidden_keys(obj))
    violations.extend(_scan_d5a2_records_shape(obj))
    return violations


def _d5a2_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_d5a2(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_d5a2_no_forbidden(obj: Any) -> None:
    scan = _d5a2_forbidden_scan_summary(obj)
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
# Method parser / validators (reused from F1-C).
# ---------------------------------------------------------------------------

parse_methods = f1c.parse_methods
MethodConfigError = f1c.MethodConfigError


def _validate_row_offset(offset: int) -> int:
    if not isinstance(offset, int):
        raise SystemExit("invalid arguments")
    if offset < 0:
        raise SystemExit("invalid arguments")
    return offset


def _validate_row_limit(limit: int) -> int:
    if not isinstance(limit, int):
        raise SystemExit("invalid arguments")
    if limit < 1:
        raise SystemExit("invalid arguments")
    if limit > CONTEXTBENCH_ROW_LIMIT_HARD_CAP:
        return CONTEXTBENCH_ROW_LIMIT_HARD_CAP
    return limit


def _validate_needle_offset(offset: int) -> int:
    if not isinstance(offset, int):
        raise SystemExit("invalid arguments")
    if offset < 0:
        raise SystemExit("invalid arguments")
    return offset


def _validate_needle_limit(limit: int) -> int:
    if not isinstance(limit, int):
        raise SystemExit("invalid arguments")
    if limit < 1:
        raise SystemExit("invalid arguments")
    if limit > REPOQA_NEEDLE_LIMIT_HARD_CAP:
        return REPOQA_NEEDLE_LIMIT_HARD_CAP
    return limit


# ---------------------------------------------------------------------------
# Utility computation (reused from F1-C; formula unchanged).
# ---------------------------------------------------------------------------

_compute_utility = f1c._compute_utility
_extract_method_metrics = f1c._extract_method_metrics
_filter_metrics = f1c._filter_metrics


def _aggregate_per_unit_means(
    per_unit_metrics: list[dict[str, float]],
) -> dict[str, float]:
    """Aggregate per-unit metrics into per-method means (utility of means)."""
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
    result["success_rate"] = _round_metric(
        sum(1.0 for r in per_unit_metrics if r.get("success_rate", 0.0) > 0)
        / n
    )
    result["retrieval_utility"] = _compute_utility(result)
    return result


# ---------------------------------------------------------------------------
# D5-A1 input loading and validation.
# ---------------------------------------------------------------------------


class InputContractError(ValueError):
    """Raised when the D5-A1 input artifact violates the D5-A2 contract."""


def _load_d5a1_artifact() -> dict[str, Any]:
    """Load and validate the D5-A1 committed artifact."""
    repo_root = Path(__file__).resolve().parent.parent
    path = repo_root / D5A1_ARTIFACT_PATH
    if not path.is_file():
        raise InputContractError(
            f"D5-A1 input artifact not found: {path}"
        )
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise InputContractError(
            f"D5-A1 input artifact not valid JSON: {path} ({exc})"
        )
    actual_schema = artifact.get("schema_version", "")
    if actual_schema != D5A1_EXPECTED_SCHEMA:
        raise InputContractError(
            f"D5-A1 schema mismatch: expected={D5A1_EXPECTED_SCHEMA} "
            f"actual={actual_schema}"
        )
    actual_status = artifact.get("status", "")
    if actual_status != D5A1_EXPECTED_STATUS:
        raise InputContractError(
            f"D5-A1 status mismatch: expected={D5A1_EXPECTED_STATUS} "
            f"actual={actual_status}"
        )
    # Validate claim flags.
    for flag in UNSAFE_D5A1_CLAIM_FLAGS:
        if flag in artifact and artifact[flag] is not False:
            raise InputContractError(
                f"D5-A1 unsafe claim flag: {flag}={artifact[flag]!r}"
            )
    fs = artifact.get("forbidden_scan", {})
    if isinstance(fs, dict) and fs.get("status") != "pass":
        raise InputContractError(
            f"D5-A1 forbidden_scan not pass: {fs.get('status')!r}"
        )
    return artifact


def _build_d5a1_input_record(
    artifact: dict[str, Any],
) -> dict[str, Any]:
    """Build the d5a1_input_record (aggregate only)."""
    return {
        "d5a1_schema_version": artifact.get("schema_version", ""),
        "d5a1_status": artifact.get("status", ""),
        "readiness_bucket": artifact.get("readiness_bucket", ""),
        "cross_signal_alignment": artifact.get("cross_signal_alignment", ""),
        "d5a1_claim_safe": True,
        "feature_count": len(artifact.get("calibration_feature_records", []) or []),
        "signal_count": len(artifact.get("signal_records", []) or []),
    }


# ---------------------------------------------------------------------------
# Heldout ContextBench matrix runner (rows offset..offset+limit).
# ---------------------------------------------------------------------------


def _run_heldout_contextbench(
    *,
    row_offset: int,
    row_limit: int,
    methods: list[str],
    openlocus_bin: str,
    eval_dir: Path,
) -> dict[str, Any]:
    """Run heldout ContextBench rows [offset, offset+limit).

    Fetches (offset + limit) rows from HF, then evaluates only the
    heldout slice [offset, offset+limit) for each method. Per-unit
    metrics are captured in memory only (never to disk).

    Returns a dict with status, rows_fetched, per_method aggregate
    metrics, failure_category_counts, network_calls, and
    failure_reason_category.
    """
    fcc = {c: 0 for c in CONTEXTBENCH_FAILURE_CATEGORIES}
    network_calls = 0

    # Fetch enough rows to cover offset+limit.
    fetch_limit = row_offset + row_limit
    rows, fetch_status, nc, fcc_update = c5a._fetch_contextbench_rows(
        fetch_limit, c5a.DEFAULT_LANGUAGE_FILTER
    )
    network_calls += nc
    for k, v in c5c._public_failure_counts(fcc_update).items():
        if k in fcc:
            fcc[k] += v

    if fetch_status == "unavailable" or not rows:
        return {
            "status": "unavailable",
            "rows_fetched": 0,
            "method_results": [],
            "failure_category_counts": fcc,
            "network_calls": network_calls,
            "failure_reason_category": (
                "network_fetch_failed" if not rows else "no_python_rows"
            ),
        }

    # Slice the heldout portion.
    heldout_rows = rows[row_offset : row_offset + row_limit]
    if not heldout_rows:
        return {
            "status": "unavailable",
            "rows_fetched": len(rows),
            "method_results": [],
            "failure_category_counts": fcc,
            "network_calls": network_calls,
            "failure_reason_category": "heldout_offset_exceeds_available",
        }

    rows_fetched = len(heldout_rows)

    method_results: list[dict[str, Any]] = []
    for method in methods:
        method_fcc = {c: 0 for c in CONTEXTBENCH_FAILURE_CATEGORIES}
        rows_evaluated = 0
        rows_successful = 0
        rows_failed = 0
        per_unit: list[dict[str, float]] = []

        with tempfile.TemporaryDirectory(
            prefix=f"d5a2_cb_{method}_"
        ) as work_root_str:
            work_root = Path(work_root_str)
            tasks_jsonl = work_root / "tasks.jsonl"
            labels_jsonl = work_root / "labels.jsonl"
            run_jsonl = work_root / "run.jsonl"

            for idx, row in enumerate(heldout_rows):
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
                    prefix=f"d5a2_cb_repo_{method}_{idx}_"
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
                    task_id = f"heldout_row_{idx}"
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
                        c5a._write_transient_jsonl(tasks_jsonl, [task_record])
                        c5a._write_transient_jsonl(labels_jsonl, [label_record])
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

                    per_unit.append(_extract_method_metrics(metrics))
                    rows_successful += 1

                try:
                    run_jsonl.unlink()
                except OSError:
                    pass

        for k, v in method_fcc.items():
            if k in fcc:
                fcc[k] += v

        agg_metrics = _aggregate_per_unit_means(per_unit)
        method_status = (
            c5c.STATUS_PASS if rows_successful > 0 else c5c.STATUS_UNAVAILABLE
        )
        if rows_successful > 0 and rows_failed > 0:
            method_status = c5c.STATUS_PARTIAL

        method_results.append(
            {
                "benchmark": CONTEXTBENCH_BENCHMARK,
                "method": method,
                "status": method_status,
                "sample_count": rows_successful,
                "metrics": agg_metrics,
            }
        )

    any_success = any(r.get("sample_count", 0) > 0 for r in method_results)
    if not any_success:
        return {
            "status": "unavailable",
            "rows_fetched": rows_fetched,
            "method_results": method_results,
            "failure_category_counts": fcc,
            "network_calls": network_calls,
            "failure_reason_category": "retrieval_failed",
        }

    all_succeed = all(r.get("sample_count", 0) > 0 for r in method_results)
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
# Heldout RepoQA matrix runner (needles offset..offset+limit).
# ---------------------------------------------------------------------------


def _run_heldout_repoqa(
    *,
    needle_offset: int,
    needle_limit: int,
    methods: list[str],
    openlocus_bin: str,
    eval_dir: Path,
) -> dict[str, Any]:
    """Run heldout RepoQA needles [offset, offset+limit).

    Parses (offset + limit) needles from the RepoQA asset, then
    evaluates only the heldout slice [offset, offset+limit) for each
    method. Per-unit metrics are captured in memory only.
    """
    fcc = {c: 0 for c in REPOQA_FAILURE_CATEGORIES}
    network_calls = 0

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

    fetch_limit = needle_offset + needle_limit
    needles, needle_status, needle_fcc = c5d._parse_repoqa_needles(
        parsed, c5d.DEFAULT_LANGUAGE_FILTER, fetch_limit
    )
    del parsed
    for k, v in needle_fcc.items():
        if k in fcc:
            fcc[k] += v
    if needle_status != "pass" or not needles:
        return {
            "status": "unavailable",
            "needles_seen": 0,
            "method_results": [],
            "failure_category_counts": fcc,
            "network_calls": network_calls,
            "failure_reason_category": (
                "no_python_needles"
                if needle_status == "unavailable_no_python_needles"
                else "needle_parse_failed"
            ),
        }

    heldout_needles = needles[needle_offset : needle_offset + needle_limit]
    if not heldout_needles:
        return {
            "status": "unavailable",
            "needles_seen": len(needles),
            "method_results": [],
            "failure_category_counts": fcc,
            "network_calls": network_calls,
            "failure_reason_category": "heldout_offset_exceeds_available",
        }

    needles_seen = len(heldout_needles)

    method_results: list[dict[str, Any]] = []
    for method in methods:
        method_fcc = {c: 0 for c in REPOQA_FAILURE_CATEGORIES}
        needles_evaluated = 0
        needles_successful = 0
        needles_failed = 0
        per_unit: list[dict[str, float]] = []

        with tempfile.TemporaryDirectory(
            prefix=f"d5a2_rq_{method}_"
        ) as work_root_str:
            work_root = Path(work_root_str)
            tasks_jsonl = work_root / "tasks.jsonl"
            labels_jsonl = work_root / "labels.jsonl"
            run_jsonl = work_root / "run.jsonl"

            for idx, needle in enumerate(heldout_needles):
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
                    prefix=f"d5a2_rq_repo_{method}_{idx}_"
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
                    task_id = f"heldout_needle_{idx}"
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
                        c5d._write_transient_jsonl(tasks_jsonl, [task_record])
                        c5d._write_transient_jsonl(labels_jsonl, [label_record])
                    except OSError:
                        method_fcc["task_jsonl_write_failed"] += 1
                        needles_failed += 1
                        continue

                    metrics, _, score_fcc = c5d._run_retrieval_and_score(
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
                        needles_failed += 1
                        continue

                    per_unit.append(_extract_method_metrics(metrics))
                    needles_successful += 1

                try:
                    run_jsonl.unlink()
                except OSError:
                    pass

        for k, v in method_fcc.items():
            if k in fcc:
                fcc[k] += v

        agg_metrics = _aggregate_per_unit_means(per_unit)
        method_status = (
            c5e.STATUS_PASS if needles_successful > 0 else c5e.STATUS_UNAVAILABLE
        )
        if needles_successful > 0 and needles_failed > 0:
            method_status = c5e.STATUS_PARTIAL

        method_results.append(
            {
                "benchmark": REPOQA_BENCHMARK,
                "method": method,
                "status": method_status,
                "sample_count": needles_successful,
                "metrics": agg_metrics,
            }
        )

    any_success = any(r.get("sample_count", 0) > 0 for r in method_results)
    if not any_success:
        return {
            "status": "unavailable",
            "needles_seen": needles_seen,
            "method_results": method_results,
            "failure_category_counts": fcc,
            "network_calls": network_calls,
            "failure_reason_category": "retrieval_failed",
        }

    all_succeed = all(r.get("sample_count", 0) > 0 for r in method_results)
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
# Feature validation computation.
# ---------------------------------------------------------------------------


def _extract_d5a1_feature_buckets(
    d5a1_artifact: dict[str, Any],
) -> dict[str, str]:
    """Extract preregistered feature buckets from D5-A1.

    Returns a dict mapping feature_name -> preregistered_bucket.
    """
    buckets: dict[str, str] = {}
    for rec in d5a1_artifact.get("calibration_feature_records", []) or []:
        if not isinstance(rec, dict):
            continue
        name = rec.get("feature_name", "")
        bucket = rec.get("feature_bucket", "")
        if isinstance(name, str) and isinstance(bucket, str):
            buckets[name] = bucket
    return buckets


def _heldout_metrics_by_method(
    heldout_results: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, float]]]:
    """Build {benchmark -> {method -> metrics}} from heldout results."""
    out: dict[str, dict[str, dict[str, float]]] = {}
    for rec in heldout_results:
        benchmark = rec.get("benchmark", "")
        method = rec.get("method", "")
        metrics = rec.get("metrics", {}) or {}
        if benchmark not in out:
            out[benchmark] = {}
        out[benchmark][method] = {
            k: float(v) if isinstance(v, (int, float)) else 0.0
            for k, v in metrics.items()
        }
        out[benchmark][method]["sample_count"] = float(
            rec.get("sample_count", 0) or 0
        )
    return out


def _weighted_heldout_metric(
    heldout_by_benchmark: dict[str, dict[str, dict[str, float]]],
    method: str,
    metric: str,
) -> tuple[float, int]:
    """Return sample-count weighted heldout metric for a method."""
    total = 0.0
    weight_total = 0
    for benchmark_methods in heldout_by_benchmark.values():
        rec = benchmark_methods.get(method, {})
        if not rec:
            continue
        weight = int(rec.get("sample_count", 0.0))
        if weight <= 0:
            weight = 1
        total += float(rec.get(metric, 0.0)) * weight
        weight_total += weight
    if weight_total <= 0:
        return 0.0, 0
    return total / weight_total, weight_total


def _weighted_heldout_delta(
    heldout_by_benchmark: dict[str, dict[str, dict[str, float]]],
    treatment_method: str,
    baseline_method: str,
    metric: str,
) -> tuple[float, int]:
    """Return sample-count weighted treatment-minus-baseline metric delta."""
    total = 0.0
    weight_total = 0
    for benchmark_methods in heldout_by_benchmark.values():
        treatment = benchmark_methods.get(treatment_method, {})
        baseline = benchmark_methods.get(baseline_method, {})
        if not treatment or not baseline:
            continue
        weight = int(
            min(
                treatment.get("sample_count", 0.0),
                baseline.get("sample_count", 0.0),
            )
        )
        if weight <= 0:
            weight = 1
        total += (
            float(treatment.get(metric, 0.0))
            - float(baseline.get(metric, 0.0))
        ) * weight
        weight_total += weight
    if weight_total <= 0:
        return 0.0, 0
    return total / weight_total, weight_total


def _compute_validation_records(
    d5a1_buckets: dict[str, str],
    heldout_by_benchmark: dict[str, dict[str, dict[str, float]]],
) -> list[dict[str, Any]]:
    """Compute validation_records (one per feature check).

    Each record: {feature_name, preregistered_bucket, heldout_metric,
    heldout_direction, supported}.
    """
    records: list[dict[str, Any]] = []

    cb = heldout_by_benchmark.get(CONTEXTBENCH_BENCHMARK, {})
    bm25_cb = cb.get("bm25", {})
    rq = heldout_by_benchmark.get(REPOQA_BENCHMARK, {})
    bm25_rq = rq.get("bm25", {})

    # Feature 1: bm25_vs_empty_retrieval_utility_magnitude
    # Preregistered: weak_positive or strong_positive.
    # Heldout check: bm25 retrieval_utility > 0 (empty is 0).
    prereg = d5a1_buckets.get(
        "bm25_vs_empty_retrieval_utility_magnitude", ""
    )
    heldout_metric, bm25_util_weight = _weighted_heldout_metric(
        heldout_by_benchmark, "bm25", "retrieval_utility"
    )
    heldout_direction = (
        "positive" if heldout_metric > 0
        else ("zero" if heldout_metric == 0 else "negative")
    )
    expected_positive = prereg in (
        "weak_positive", "strong_positive"
    )
    supported = (
        (expected_positive and heldout_direction == "positive")
        or (not expected_positive and heldout_direction != "positive")
    ) if bm25_util_weight > 0 else False
    records.append(
        {
            "feature_name": "bm25_vs_empty_retrieval_utility_magnitude",
            "preregistered_bucket": prereg,
            "heldout_metric": _round_metric(heldout_metric),
            "heldout_direction": heldout_direction,
            "supported": bool(supported),
        }
    )

    # Feature 2: bm25_vs_empty_sign_stability
    # Preregistered: stable_positive.
    # Heldout check: bm25 file_recall@10 > 0 on both benchmarks.
    prereg2 = d5a1_buckets.get("bm25_vs_empty_sign_stability", "")
    cb_recall = bm25_cb.get("file_recall@10", 0.0)
    rq_recall = bm25_rq.get("file_recall@10", 0.0)
    heldout_metric2 = (
        (cb_recall + rq_recall) / 2.0
        if (bm25_cb or bm25_rq)
        else 0.0
    )
    heldout_direction2 = (
        "positive" if heldout_metric2 > 0
        else ("zero" if heldout_metric2 == 0 else "negative")
    )
    supported2 = (
        prereg2 == "stable_positive" and heldout_direction2 == "positive"
        and cb_recall > 0 and rq_recall > 0
    ) if (bm25_cb and bm25_rq) else False
    records.append(
        {
            "feature_name": "bm25_vs_empty_sign_stability",
            "preregistered_bucket": prereg2,
            "heldout_metric": _round_metric(heldout_metric2),
            "heldout_direction": heldout_direction2,
            "supported": bool(supported2),
        }
    )

    # Feature 3: regex_vs_bm25_sign_stability
    # Preregistered: stable_negative.
    # Heldout check: regex retrieval_utility < bm25 retrieval_utility.
    prereg3 = d5a1_buckets.get("regex_vs_bm25_sign_stability", "")
    heldout_metric3, regex_delta_weight = _weighted_heldout_delta(
        heldout_by_benchmark, "regex", "bm25", "retrieval_utility"
    )
    heldout_direction3 = (
        "negative" if heldout_metric3 < 0
        else ("zero" if heldout_metric3 == 0 else "positive")
    )
    supported3 = (
        prereg3 == "stable_negative" and heldout_direction3 == "negative"
    ) if regex_delta_weight > 0 else False
    records.append(
        {
            "feature_name": "regex_vs_bm25_sign_stability",
            "preregistered_bucket": prereg3,
            "heldout_metric": _round_metric(heldout_metric3),
            "heldout_direction": heldout_direction3,
            "supported": bool(supported3),
        }
    )

    # Feature 4: symbol_vs_bm25_sign_stability
    prereg4 = d5a1_buckets.get("symbol_vs_bm25_sign_stability", "")
    heldout_metric4, symbol_delta_weight = _weighted_heldout_delta(
        heldout_by_benchmark, "symbol", "bm25", "retrieval_utility"
    )
    heldout_direction4 = (
        "negative" if heldout_metric4 < 0
        else ("zero" if heldout_metric4 == 0 else "positive")
    )
    supported4 = (
        prereg4 == "stable_negative" and heldout_direction4 == "negative"
    ) if symbol_delta_weight > 0 else False
    records.append(
        {
            "feature_name": "symbol_vs_bm25_sign_stability",
            "preregistered_bucket": prereg4,
            "heldout_metric": _round_metric(heldout_metric4),
            "heldout_direction": heldout_direction4,
            "supported": bool(supported4),
        }
    )

    return records


def _compute_validation_outcome(
    validation_records: list[dict[str, Any]],
    heldout_available: bool,
) -> str:
    """Compute the overall validation outcome."""
    if not heldout_available:
        return OUTCOME_UNAVAILABLE
    if not validation_records:
        return OUTCOME_UNAVAILABLE
    supported_count = sum(1 for r in validation_records if r.get("supported"))
    total = len(validation_records)
    if supported_count == total:
        return OUTCOME_SUPPORTED
    if supported_count == 0:
        return OUTCOME_NOT_SUPPORTED
    return OUTCOME_MIXED


def _compute_validation_summary(
    validation_records: list[dict[str, Any]],
    outcome: str,
) -> list[dict[str, Any]]:
    """Build validation_summary_records (one per outcome, with count)."""
    supported_count = sum(1 for r in validation_records if r.get("supported"))
    not_supported_count = sum(
        1 for r in validation_records if not r.get("supported")
    )
    return [
        {
            "outcome": OUTCOME_SUPPORTED,
            "outcome_count": int(supported_count),
        },
        {
            "outcome": OUTCOME_MIXED,
            "outcome_count": 1 if outcome == OUTCOME_MIXED else 0,
        },
        {
            "outcome": OUTCOME_NOT_SUPPORTED,
            "outcome_count": int(not_supported_count),
        },
        {
            "outcome": OUTCOME_UNAVAILABLE,
            "outcome_count": 1 if outcome == OUTCOME_UNAVAILABLE else 0,
        },
    ]


# ---------------------------------------------------------------------------
# Public report builders.
# ---------------------------------------------------------------------------


def _build_input_summary(
    *,
    contextbench_row_offset: int,
    contextbench_row_limit: int,
    repoqa_needle_offset: int,
    repoqa_needle_limit: int,
    methods: list[str],
    contextbench_rows_fetched: int,
    repoqa_needles_seen: int,
) -> dict[str, Any]:
    return {
        "contextbench_row_offset": int(contextbench_row_offset),
        "contextbench_row_limit": int(contextbench_row_limit),
        "repoqa_needle_offset": int(repoqa_needle_offset),
        "repoqa_needle_limit": int(repoqa_needle_limit),
        "methods": list(methods),
        "benchmarks": list(BENCHMARKS),
        "contextbench_rows_fetched": int(contextbench_rows_fetched),
        "repoqa_needles_seen": int(repoqa_needles_seen),
        "method_labels": list(ALL_METHOD_LABELS),
        "metric_labels": list(METRIC_NAMES),
        "outcome_labels": list(ALL_OUTCOMES),
    }


def _build_unavailable_report(
    failure_reason_category: str,
    *,
    self_test_passed: bool,
    contextbench_row_offset: int,
    contextbench_row_limit: int,
    repoqa_needle_offset: int,
    repoqa_needle_limit: int,
    methods: list[str],
    openlocus_binary_source: str,
    network_mode: str,
    d5a1_input_record: dict[str, Any] | None = None,
    contextbench_rows_fetched: int = 0,
    repoqa_needles_seen: int = 0,
    network_calls: int = 0,
    contextbench_failure_category_counts: dict[str, int] | None = None,
    repoqa_failure_category_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
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
    safe_true["heldout_feature_validation_executed"] = False

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
        "contextbench_row_offset_requested": int(contextbench_row_offset),
        "contextbench_row_limit_requested": int(contextbench_row_limit),
        "repoqa_needle_offset_requested": int(repoqa_needle_offset),
        "repoqa_needle_limit_requested": int(repoqa_needle_limit),
        "contextbench_rows_fetched": contextbench_rows_fetched,
        "repoqa_needles_seen": repoqa_needles_seen,
        "validation_outcome": OUTCOME_UNAVAILABLE,
        "d5a1_input_record": d5a1_input_record or {},
        "heldout_benchmark_method_records": [],
        "validation_records": [],
        "validation_summary_records": _compute_validation_summary(
            [], OUTCOME_UNAVAILABLE
        ),
        "input_summary": _build_input_summary(
            contextbench_row_offset=contextbench_row_offset,
            contextbench_row_limit=contextbench_row_limit,
            repoqa_needle_offset=repoqa_needle_offset,
            repoqa_needle_limit=repoqa_needle_limit,
            methods=methods,
            contextbench_rows_fetched=contextbench_rows_fetched,
            repoqa_needles_seen=repoqa_needles_seen,
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
            "is_calibration": False,
            "is_policy_recommendation": False,
            "is_live_provider_validation": False,
            "signal_strength": (
                "heldout_feature_validation_smoke_unavailable"
            ),
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _d5a2_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_FORBIDDEN_SCAN
    return report


def _build_pass_report(
    *,
    self_test_passed: bool,
    contextbench_row_offset: int,
    contextbench_row_limit: int,
    repoqa_needle_offset: int,
    repoqa_needle_limit: int,
    methods: list[str],
    contextbench_result: dict[str, Any],
    repoqa_result: dict[str, Any],
    openlocus_binary_source: str,
    network_mode: str,
    network_calls: int,
    d5a1_input_record: dict[str, Any],
    d5a1_buckets: dict[str, str],
) -> dict[str, Any]:
    cb_fcc = c5c._public_failure_counts(
        contextbench_result.get("failure_category_counts", {})
    )
    rq_fcc = {c: 0 for c in REPOQA_FAILURE_CATEGORIES}
    for k, v in repoqa_result.get("failure_category_counts", {}).items():
        if k in rq_fcc:
            rq_fcc[k] = int(v)

    contextbench_rows_fetched = int(contextbench_result.get("rows_fetched", 0))
    repoqa_needles_seen = int(repoqa_result.get("needles_seen", 0))

    cb_method_results = contextbench_result.get("method_results", [])
    rq_method_results = repoqa_result.get("method_results", [])

    heldout_benchmark_method_records: list[dict[str, Any]] = []
    for rec in cb_method_results:
        heldout_benchmark_method_records.append(
            {
                "benchmark": CONTEXTBENCH_BENCHMARK,
                "method": rec["method"],
                "sample_count": int(rec.get("sample_count", 0)),
                "metrics": _filter_metrics(rec.get("metrics", {})),
            }
        )
    for rec in rq_method_results:
        heldout_benchmark_method_records.append(
            {
                "benchmark": REPOQA_BENCHMARK,
                "method": rec["method"],
                "sample_count": int(rec.get("sample_count", 0)),
                "metrics": _filter_metrics(rec.get("metrics", {})),
            }
        )

    heldout_by_benchmark = _heldout_metrics_by_method(
        heldout_benchmark_method_records
    )
    validation_records = _compute_validation_records(
        d5a1_buckets, heldout_by_benchmark
    )
    heldout_available = (
        contextbench_rows_fetched > 0 or repoqa_needles_seen > 0
    )
    outcome = _compute_validation_outcome(
        validation_records, heldout_available
    )
    validation_summary = _compute_validation_summary(
        validation_records, outcome
    )

    # Status: pass if outcome is supported; partial if mixed or
    # not_supported but data was available; unavailable if no data.
    if not heldout_available:
        return _build_unavailable_report(
            "retrieval_failed",
            self_test_passed=self_test_passed,
            contextbench_row_offset=contextbench_row_offset,
            contextbench_row_limit=contextbench_row_limit,
            repoqa_needle_offset=repoqa_needle_offset,
            repoqa_needle_limit=repoqa_needle_limit,
            methods=methods,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            d5a1_input_record=d5a1_input_record,
            contextbench_rows_fetched=contextbench_rows_fetched,
            repoqa_needles_seen=repoqa_needles_seen,
            network_calls=network_calls,
            contextbench_failure_category_counts=cb_fcc,
            repoqa_failure_category_counts=rq_fcc,
        )

    if outcome == OUTCOME_SUPPORTED:
        status = STATUS_PASS
    else:
        status = STATUS_PARTIAL

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["contextbench_rows_read"] = contextbench_rows_fetched > 0
    safe_true["repoqa_needles_read"] = repoqa_needles_seen > 0
    safe_true["openlocus_retrieval_executed"] = True
    safe_true["score_py_metrics_computed"] = True
    safe_true["heldout_feature_validation_executed"] = True

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
        "contextbench_row_offset_requested": int(contextbench_row_offset),
        "contextbench_row_limit_requested": int(contextbench_row_limit),
        "repoqa_needle_offset_requested": int(repoqa_needle_offset),
        "repoqa_needle_limit_requested": int(repoqa_needle_limit),
        "contextbench_rows_fetched": contextbench_rows_fetched,
        "repoqa_needles_seen": repoqa_needles_seen,
        "validation_outcome": outcome,
        "d5a1_input_record": d5a1_input_record,
        "heldout_benchmark_method_records": heldout_benchmark_method_records,
        "validation_records": validation_records,
        "validation_summary_records": validation_summary,
        "input_summary": _build_input_summary(
            contextbench_row_offset=contextbench_row_offset,
            contextbench_row_limit=contextbench_row_limit,
            repoqa_needle_offset=repoqa_needle_offset,
            repoqa_needle_limit=repoqa_needle_limit,
            methods=methods,
            contextbench_rows_fetched=contextbench_rows_fetched,
            repoqa_needles_seen=repoqa_needles_seen,
        ),
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
            "is_calibration": False,
            "is_policy_recommendation": False,
            "is_live_provider_validation": False,
            "signal_strength": (
                "heldout_feature_validation_smoke_aggregate_only"
            ),
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _d5a2_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_FORBIDDEN_SCAN
    return report


# ---------------------------------------------------------------------------
# Heldout smoke runner.
# ---------------------------------------------------------------------------


def _run_heldout_smoke(
    *,
    contextbench_row_offset: int,
    contextbench_row_limit: int,
    repoqa_needle_offset: int,
    repoqa_needle_limit: int,
    methods: list[str],
    openlocus_bin: str,
    openlocus_binary_source: str,
    network_mode: str,
    eval_dir: Path,
    self_test_passed: bool,
    d5a1_input_record: dict[str, Any],
    d5a1_buckets: dict[str, str],
) -> dict[str, Any]:
    cb_result = _run_heldout_contextbench(
        row_offset=contextbench_row_offset,
        row_limit=contextbench_row_limit,
        methods=methods,
        openlocus_bin=openlocus_bin,
        eval_dir=eval_dir,
    )
    rq_result = _run_heldout_repoqa(
        needle_offset=repoqa_needle_offset,
        needle_limit=repoqa_needle_limit,
        methods=methods,
        openlocus_bin=openlocus_bin,
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
            contextbench_row_offset=contextbench_row_offset,
            contextbench_row_limit=contextbench_row_limit,
            repoqa_needle_offset=repoqa_needle_offset,
            repoqa_needle_limit=repoqa_needle_limit,
            methods=methods,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            d5a1_input_record=d5a1_input_record,
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
        contextbench_row_offset=contextbench_row_offset,
        contextbench_row_limit=contextbench_row_limit,
        repoqa_needle_offset=repoqa_needle_offset,
        repoqa_needle_limit=repoqa_needle_limit,
        methods=methods,
        contextbench_result=cb_result,
        repoqa_result=rq_result,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        network_calls=network_calls,
        d5a1_input_record=d5a1_input_record,
        d5a1_buckets=d5a1_buckets,
    )


# ---------------------------------------------------------------------------
# Self-test (no network; synthetic data).
# ---------------------------------------------------------------------------


def _build_synthetic_d5a1_artifact() -> dict[str, Any]:
    return {
        "schema_version": D5A1_EXPECTED_SCHEMA,
        "status": D5A1_EXPECTED_STATUS,
        "readiness_bucket": "ready_for_manual_review",
        "cross_signal_alignment": (
            "retrieval_robust_positive_plus_live_positive"
        ),
        "calibration_feature_records": [
            {
                "feature_name": "bm25_vs_empty_retrieval_utility_magnitude",
                "feature_bucket": "weak_positive",
            },
            {
                "feature_name": "bm25_vs_empty_sign_stability",
                "feature_bucket": "stable_positive",
            },
            {
                "feature_name": "regex_vs_bm25_sign_stability",
                "feature_bucket": "stable_negative",
            },
            {
                "feature_name": "symbol_vs_bm25_sign_stability",
                "feature_bucket": "stable_negative",
            },
        ],
        "signal_records": [
            {"signal_name": "bm25_vs_empty_retrieval_utility"},
            {"signal_name": "regex_vs_bm25_retrieval_utility"},
        ],
        "forbidden_scan": {"status": "pass"},
        "true_e_s_calibration_claimed": False,
        "method_winner_claimed": False,
        "external_benchmark_performance_claimed": False,
        "downstream_agent_value_proven": False,
        "promotion_ready": False,
        "default_should_change": False,
        "calibrated_model_claimed": False,
        "policy_recommendation_claimed": False,
    }


def _build_synthetic_heldout_metrics_supported() -> list[dict[str, Any]]:
    return [
        {
            "benchmark": CONTEXTBENCH_BENCHMARK,
            "method": "bm25",
            "sample_count": 20,
            "metrics": {
                "file_recall@10": 0.4,
                "mrr": 0.2,
                "span_f0.5@10": 0.02,
                "success_rate": 1.0,
                "retrieval_utility": _compute_utility(
                    {
                        "file_recall@10": 0.4,
                        "mrr": 0.2,
                        "span_f0.5@10": 0.02,
                        "success_rate": 1.0,
                    }
                ),
            },
        },
        {
            "benchmark": CONTEXTBENCH_BENCHMARK,
            "method": "regex",
            "sample_count": 20,
            "metrics": {
                "file_recall@10": 0.0,
                "mrr": 0.0,
                "span_f0.5@10": 0.0,
                "success_rate": 1.0,
                "retrieval_utility": -0.25,
            },
        },
        {
            "benchmark": CONTEXTBENCH_BENCHMARK,
            "method": "symbol",
            "sample_count": 20,
            "metrics": {
                "file_recall@10": 0.0,
                "mrr": 0.0,
                "span_f0.5@10": 0.0,
                "success_rate": 1.0,
                "retrieval_utility": -0.25,
            },
        },
        {
            "benchmark": REPOQA_BENCHMARK,
            "method": "bm25",
            "sample_count": 10,
            "metrics": {
                "file_recall@10": 0.5,
                "mrr": 0.3,
                "span_f0.5@10": 0.02,
                "success_rate": 1.0,
                "retrieval_utility": _compute_utility(
                    {
                        "file_recall@10": 0.5,
                        "mrr": 0.3,
                        "span_f0.5@10": 0.02,
                        "success_rate": 1.0,
                    }
                ),
            },
        },
        {
            "benchmark": REPOQA_BENCHMARK,
            "method": "regex",
            "sample_count": 10,
            "metrics": {
                "file_recall@10": 0.0,
                "mrr": 0.0,
                "span_f0.5@10": 0.0,
                "success_rate": 1.0,
                "retrieval_utility": -0.25,
            },
        },
        {
            "benchmark": REPOQA_BENCHMARK,
            "method": "symbol",
            "sample_count": 10,
            "metrics": {
                "file_recall@10": 0.0,
                "mrr": 0.0,
                "span_f0.5@10": 0.0,
                "success_rate": 1.0,
                "retrieval_utility": -0.25,
            },
        },
    ]


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []

    # --- Group 1: Artifact identity. ---
    d5a1_art = _build_synthetic_d5a1_artifact()
    d5a1_rec = _build_d5a1_input_record(d5a1_art)
    d5a1_buckets = _extract_d5a1_feature_buckets(d5a1_art)
    heldout_supported = _build_synthetic_heldout_metrics_supported()
    heldout_by_bench = _heldout_metrics_by_method(heldout_supported)
    val_records = _compute_validation_records(d5a1_buckets, heldout_by_bench)
    outcome = _compute_validation_outcome(val_records, True)
    summary = _compute_validation_summary(val_records, outcome)
    pass_report = _build_pass_report(
        self_test_passed=True,
        contextbench_row_offset=20,
        contextbench_row_limit=20,
        repoqa_needle_offset=10,
        repoqa_needle_limit=10,
        methods=["bm25", "regex", "symbol"],
        contextbench_result={
            "status": "pass",
            "rows_fetched": 20,
            "method_results": heldout_supported[:3],
            "failure_category_counts": {c: 0 for c in CONTEXTBENCH_FAILURE_CATEGORIES},
        },
        repoqa_result={
            "status": "pass",
            "needles_seen": 10,
            "method_results": heldout_supported[3:],
            "failure_category_counts": {c: 0 for c in REPOQA_FAILURE_CATEGORIES},
        },
        openlocus_binary_source="default",
        network_mode="local_explicit",
        network_calls=2,
        d5a1_input_record=d5a1_rec,
        d5a1_buckets=d5a1_buckets,
    )
    checks.append(
        _check("schema_version_correct", pass_report["schema_version"] == SCHEMA_VERSION)
    )
    checks.append(
        _check("claim_level_correct", pass_report["claim_level"] == CLAIM_LEVEL)
    )
    checks.append(_check("mode_correct", pass_report["mode"] == MODE))
    checks.append(_check("phase_correct", pass_report["phase"] == PHASE))
    checks.append(
        _check("generated_by_correct", pass_report["generated_by"] == GENERATED_BY)
    )
    checks.append(
        _check("status_pass_when_supported", pass_report["status"] == STATUS_PASS)
    )

    # --- Group 2: Safe true flags. ---
    for flag in SAFE_TRUE_FLAGS:
        checks.append(_check(f"safe_true_{flag}_present", flag in pass_report))
    checks.append(_check("diagnostic_only_true", pass_report.get("diagnostic_only") is True))
    checks.append(
        _check(
            "aggregate_only_true",
            pass_report.get("aggregate_only_public_artifact") is True,
        )
    )
    checks.append(
        _check(
            "heldout_validation_executed_true_on_pass",
            pass_report.get("heldout_feature_validation_executed") is True,
        )
    )
    unavail = _build_unavailable_report(
        "network_fetch_failed",
        self_test_passed=True,
        contextbench_row_offset=20,
        contextbench_row_limit=20,
        repoqa_needle_offset=10,
        repoqa_needle_limit=10,
        methods=["bm25", "regex", "symbol"],
        openlocus_binary_source="missing",
        network_mode="local_explicit",
    )
    checks.append(
        _check(
            "heldout_validation_executed_false_on_unavailable",
            unavail.get("heldout_feature_validation_executed") is False,
        )
    )

    # --- Group 3: No-claim flags false. ---
    for flag in DEFAULT_FALSE_FLAGS:
        checks.append(_check(f"default_false_{flag}", pass_report.get(flag) is False))

    # --- Group 4: Records-shaped containers. ---
    for container in D5A2_RECORD_CONTAINERS:
        checks.append(
            _check(f"{container}_is_list", isinstance(pass_report[container], list))
        )

    # --- Group 5: Outcomes allowlist. ---
    checks.append(
        _check(
            "outcomes_fixed_allowlist",
            ALL_OUTCOMES
            == (
                "retrieval_feature_validation_supported",
                "retrieval_feature_validation_mixed",
                "retrieval_feature_validation_not_supported",
                "unavailable_with_reason",
            ),
        )
    )

    # --- Group 6: Validation records fields. ---
    checks.append(
        _check(
            "validation_records_fields_exact",
            all(
                set(r.keys())
                == {
                    "feature_name",
                    "preregistered_bucket",
                    "heldout_metric",
                    "heldout_direction",
                    "supported",
                }
                for r in val_records
            ),
        )
    )
    checks.append(_check("validation_records_count_4", len(val_records) == 4))

    # --- Group 7: Supported outcome. ---
    checks.append(
        _check(
            "supported_outcome_when_all_supported",
            outcome == OUTCOME_SUPPORTED,
        )
    )
    checks.append(
        _check(
            "supported_count_4",
            summary[0]["outcome_count"] == 4,
        )
    )
    checks.append(
        _check(
            "not_supported_count_0",
            summary[2]["outcome_count"] == 0,
        )
    )

    # --- Group 8: Not-supported outcome (bm25 zero recall). ---
    heldout_not_supported = [
        {
            "benchmark": CONTEXTBENCH_BENCHMARK,
            "method": "bm25",
            "sample_count": 20,
            "metrics": {
                "file_recall@10": 0.0,
                "mrr": 0.0,
                "span_f0.5@10": 0.0,
                "success_rate": 1.0,
                "retrieval_utility": -0.25,
            },
        },
        {
            "benchmark": CONTEXTBENCH_BENCHMARK,
            "method": "regex",
            "sample_count": 20,
            "metrics": {
                "file_recall@10": 0.0,
                "mrr": 0.0,
                "span_f0.5@10": 0.0,
                "success_rate": 1.0,
                "retrieval_utility": -0.25,
            },
        },
        {
            "benchmark": CONTEXTBENCH_BENCHMARK,
            "method": "symbol",
            "sample_count": 20,
            "metrics": {
                "file_recall@10": 0.0,
                "mrr": 0.0,
                "span_f0.5@10": 0.0,
                "success_rate": 1.0,
                "retrieval_utility": -0.25,
            },
        },
        {
            "benchmark": REPOQA_BENCHMARK,
            "method": "bm25",
            "sample_count": 10,
            "metrics": {
                "file_recall@10": 0.0,
                "mrr": 0.0,
                "span_f0.5@10": 0.0,
                "success_rate": 1.0,
                "retrieval_utility": -0.25,
            },
        },
        {
            "benchmark": REPOQA_BENCHMARK,
            "method": "regex",
            "sample_count": 10,
            "metrics": {
                "file_recall@10": 0.0,
                "mrr": 0.0,
                "span_f0.5@10": 0.0,
                "success_rate": 1.0,
                "retrieval_utility": -0.25,
            },
        },
        {
            "benchmark": REPOQA_BENCHMARK,
            "method": "symbol",
            "sample_count": 10,
            "metrics": {
                "file_recall@10": 0.0,
                "mrr": 0.0,
                "span_f0.5@10": 0.0,
                "success_rate": 1.0,
                "retrieval_utility": -0.25,
            },
        },
    ]
    heldout_ns_by_bench = _heldout_metrics_by_method(heldout_not_supported)
    val_ns = _compute_validation_records(d5a1_buckets, heldout_ns_by_bench)
    outcome_ns = _compute_validation_outcome(val_ns, True)
    checks.append(
        _check(
            "not_supported_outcome_when_bm25_zero",
            outcome_ns == OUTCOME_NOT_SUPPORTED,
        )
    )

    # --- Group 9: Mixed outcome (bm25 positive on one, zero on other). ---
    heldout_mixed = list(heldout_not_supported)
    heldout_mixed[3] = {  # RepoQA bm25 positive
        "benchmark": REPOQA_BENCHMARK,
        "method": "bm25",
        "sample_count": 10,
        "metrics": {
            "file_recall@10": 0.5,
            "mrr": 0.3,
            "span_f0.5@10": 0.02,
            "success_rate": 1.0,
            "retrieval_utility": _compute_utility(
                {"file_recall@10": 0.5, "mrr": 0.3, "span_f0.5@10": 0.02, "success_rate": 1.0}
            ),
        },
    }
    heldout_mix_by_bench = _heldout_metrics_by_method(heldout_mixed)
    val_mix = _compute_validation_records(d5a1_buckets, heldout_mix_by_bench)
    outcome_mix = _compute_validation_outcome(val_mix, True)
    checks.append(
        _check(
            "mixed_outcome_when_partial_support",
            outcome_mix == OUTCOME_MIXED,
        )
    )

    # --- Group 10: Unavailable outcome. ---
    outcome_unavail = _compute_validation_outcome([], False)
    checks.append(
        _check(
            "unavailable_outcome_when_no_data",
            outcome_unavail == OUTCOME_UNAVAILABLE,
        )
    )

    # --- Group 11: D5-A1 input validation. ---
    checks.append(
        _check(
            "d5a1_input_record_has_readiness_bucket",
            d5a1_rec["readiness_bucket"] == "ready_for_manual_review",
        )
    )
    checks.append(
        _check(
            "d5a1_buckets_extracted_4",
            len(d5a1_buckets) == 4,
        )
    )

    # --- Group 12: Offset/limit validation. ---
    checks.append(_check("row_offset_rejects_negative", _validate_row_offset(-1) == 0 if False else True))
    try:
        _validate_row_offset(-1)
        checks.append(_check("row_offset_rejects_negative", False))
    except SystemExit:
        checks.append(_check("row_offset_rejects_negative", True))
    checks.append(_check("row_limit_caps_at_20", _validate_row_limit(100) == 20))
    try:
        _validate_row_limit(0)
        checks.append(_check("row_limit_rejects_zero", False))
    except SystemExit:
        checks.append(_check("row_limit_rejects_zero", True))
    checks.append(_check("needle_limit_caps_at_10", _validate_needle_limit(100) == 10))

    # --- Group 13: Scanner rejections. ---
    checks.append(_check("scanner_rejects_repo_url", bool(_scan_d5a2({"leaked": "https://github.com/x/y"}))))
    checks.append(_check("scanner_rejects_commit_sha", bool(_scan_d5a2({"leaked": "a" * 40}))))
    checks.append(_check("scanner_rejects_task_id_key", bool(_scan_d5a2({"task_id": "abc"}))))
    checks.append(_check("scanner_rejects_query_key", bool(_scan_d5a2({"query": "abc"}))))
    checks.append(_check("scanner_rejects_winner_key", bool(_scan_d5a2({"winner": "bm25"}))))
    checks.append(_check("scanner_rejects_calibrated_model_key", bool(_scan_d5a2({"calibrated_model": "abc"}))))
    checks.append(_check("scanner_rejects_policy_recommendation_key", bool(_scan_d5a2({"policy_recommendation": "abc"}))))
    checks.append(_check("scanner_rejects_per_row_metrics_key", bool(_scan_d5a2({"per_row_metrics": []}))))
    checks.append(_check("scanner_rejects_provider_payload_key", bool(_scan_d5a2({"provider_payload": "abc"}))))
    checks.append(_check("scanner_rejects_task_text_key", bool(_scan_d5a2({"task_text": "abc"}))))
    checks.append(_check("scanner_rejects_tmp_path", bool(_scan_d5a2({"leaked": "/tmp/d5a2_smoke_0"}))))
    checks.append(_check("scanner_rejects_raw_routing_prefix", bool(_scan_d5a2({"leaked": _ROUTING_PREFIX_SENTINEL + "Kimi"}))))
    for container in D5A2_RECORD_CONTAINERS:
        checks.append(
            _check(f"scanner_rejects_{container}_dict", bool(_scan_d5a2({container: {"x": {}}})))
        )

    # --- Group 14: Scanner allows. ---
    checks.append(_check("scanner_allows_method_name", not _scan_d5a2({"method": "bm25"})))
    checks.append(_check("scanner_allows_benchmark_name", not _scan_d5a2({"benchmark": "contextbench"})))
    checks.append(_check("scanner_allows_outcome_label", not _scan_d5a2({"outcome": OUTCOME_SUPPORTED})))
    checks.append(_check("scanner_allows_feature_name", not _scan_d5a2({"feature_name": "bm25_vs_empty_sign_stability"})))
    checks.append(
        _check(
            "scanner_allows_validation_records_list",
            not _scan_d5a2(
                {
                    "validation_records": [
                        {
                            "feature_name": "bm25_vs_empty_sign_stability",
                            "preregistered_bucket": "stable_positive",
                            "heldout_metric": 0.4,
                            "heldout_direction": "positive",
                            "supported": True,
                        }
                    ]
                }
            ),
        )
    )

    # --- Group 15: Fail-closed. ---
    try:
        _enforce_d5a2_no_forbidden(pass_report)
        clean_passes = True
    except SystemExit:
        clean_passes = False
    checks.append(_check("fail_closed_clean_report_does_not_raise", clean_passes))
    leaked = dict(pass_report)
    leaked["leaked_path"] = "src/openlocus/lib.rs"
    try:
        _enforce_d5a2_no_forbidden(leaked)
        leak_raises = False
    except SystemExit:
        leak_raises = True
    checks.append(_check("fail_closed_raises_on_leak", leak_raises))
    leaked2 = dict(pass_report)
    leaked2["calibrated_model"] = "abc"
    try:
        _enforce_d5a2_no_forbidden(leaked2)
        calib_raises = False
    except SystemExit:
        calib_raises = True
    checks.append(_check("fail_closed_raises_on_calibrated_model", calib_raises))
    leaked3 = dict(pass_report)
    leaked3["policy_recommendation"] = "abc"
    try:
        _enforce_d5a2_no_forbidden(leaked3)
        policy_raises = False
    except SystemExit:
        policy_raises = True
    checks.append(_check("fail_closed_raises_on_policy_recommendation", policy_raises))

    # --- Group 16: Full pass report self-scan. ---
    checks.append(
        _check("pass_report_forbidden_scan_clean", pass_report["forbidden_scan"]["status"] == "pass")
    )
    checks.append(_check("pass_report_self_scan_clean", not _scan_d5a2(pass_report)))

    # --- Group 17: CLI. ---
    cli_opts = _cli_argument_option_strings()
    checks.append(_check("cli_has_self_test_argument", "--self-test" in cli_opts))
    checks.append(_check("cli_has_out_argument", "--out" in cli_opts))
    checks.append(_check("cli_has_row_offset_argument", "--contextbench-row-offset" in cli_opts))
    checks.append(_check("cli_has_row_limit_argument", "--contextbench-row-limit" in cli_opts))
    checks.append(_check("cli_has_needle_offset_argument", "--repoqa-needle-offset" in cli_opts))
    checks.append(_check("cli_has_needle_limit_argument", "--repoqa-needle-limit" in cli_opts))
    checks.append(_check("cli_has_methods_argument", "--methods" in cli_opts))
    checks.append(_check("cli_has_openlocus_argument", "--openlocus" in cli_opts))

    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(
        description=(
            "D5-A2 heldout feature validation smoke "
            "(public aggregate-only artifact; runs fresh heldout "
            "ContextBench rows 21-40 + RepoQA needles 11-20; "
            "validates D5-A1 retrieval-feature buckets reproduce on "
            "heldout data; methods bm25,regex,symbol only; no provider "
            "calls; no raw rows/IDs/repo URLs/commits/queries/paths/"
            "spans/snippets/JSONL/evidence/per-unit metrics/hashes/"
            "stdout/stderr/clone paths/provider fields/winner/default/"
            "calibration claims committed)."
        )
    )
    ap.add_argument("--self-test", action="store_true", help="run self-test and exit")
    ap.add_argument(
        "--contextbench-row-offset", type=int, default=CONTEXTBENCH_ROW_OFFSET_DEFAULT,
        help=f"ContextBench row offset (default {CONTEXTBENCH_ROW_OFFSET_DEFAULT})",
    )
    ap.add_argument(
        "--contextbench-row-limit", type=int, default=CONTEXTBENCH_ROW_LIMIT_DEFAULT,
        help=f"ContextBench row limit (default {CONTEXTBENCH_ROW_LIMIT_DEFAULT}, hard cap {CONTEXTBENCH_ROW_LIMIT_HARD_CAP})",
    )
    ap.add_argument(
        "--repoqa-needle-offset", type=int, default=REPOQA_NEEDLE_OFFSET_DEFAULT,
        help=f"RepoQA needle offset (default {REPOQA_NEEDLE_OFFSET_DEFAULT})",
    )
    ap.add_argument(
        "--repoqa-needle-limit", type=int, default=REPOQA_NEEDLE_LIMIT_DEFAULT,
        help=f"RepoQA needle limit (default {REPOQA_NEEDLE_LIMIT_DEFAULT}, hard cap {REPOQA_NEEDLE_LIMIT_HARD_CAP})",
    )
    ap.add_argument(
        "--methods", default=None,
        help=f"comma-separated methods (default {','.join(DEFAULT_METHODS)}; allowed {','.join(ALLOWED_METHODS)})",
    )
    ap.add_argument(
        "--openlocus", default=None,
        help="OpenLocus binary path (default: target/release/openlocus then target/debug/openlocus)",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output artifact JSON path")
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
        print(f"self_test_passed={passed} ({passed_count}/{len(checks)} checks)")
        sys.exit(0 if passed else 1)

    try:
        methods = parse_methods(args.methods)
    except MethodConfigError:
        report = _build_unavailable_report(
            "scanner_self_test_failed",
            self_test_passed=False,
            contextbench_row_offset=args.contextbench_row_offset,
            contextbench_row_limit=args.contextbench_row_limit,
            repoqa_needle_offset=args.repoqa_needle_offset,
            repoqa_needle_limit=args.repoqa_needle_limit,
            methods=[],
            openlocus_binary_source="missing",
            network_mode="local_explicit",
        )
        _write_json(args.out, report)
        sys.exit(1)

    contextbench_row_offset = _validate_row_offset(args.contextbench_row_offset)
    contextbench_row_limit = _validate_row_limit(args.contextbench_row_limit)
    repoqa_needle_offset = _validate_needle_offset(args.repoqa_needle_offset)
    repoqa_needle_limit = _validate_needle_limit(args.repoqa_needle_limit)
    out_path = args.out if args.out is not None else DEFAULT_OUT

    checks, self_test_passed = run_self_test_checks()
    if not self_test_passed:
        print("error: self-test failed; refusing to write artifact", file=sys.stderr)
        for c in checks:
            if not c["passed"]:
                print(f"  FAIL: {c['check']}", file=sys.stderr)
        sys.exit(1)

    # Load D5-A1 input artifact (fail-closed on missing/unsafe).
    try:
        d5a1_artifact = _load_d5a1_artifact()
    except InputContractError as exc:
        report = _build_unavailable_report(
            f"d5a1_input_contract: {exc}",
            self_test_passed=self_test_passed,
            contextbench_row_offset=contextbench_row_offset,
            contextbench_row_limit=contextbench_row_limit,
            repoqa_needle_offset=repoqa_needle_offset,
            repoqa_needle_limit=repoqa_needle_limit,
            methods=methods,
            openlocus_binary_source="missing",
            network_mode="local_explicit",
        )
        _enforce_d5a2_no_forbidden(report)
        _write_json(out_path, report)
        print(
            f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, "
            f"status={report['status']}, failure_reason={report['failure_reason_category']})"
        )
        sys.exit(1)

    d5a1_input_record = _build_d5a1_input_record(d5a1_artifact)
    d5a1_buckets = _extract_d5a1_feature_buckets(d5a1_artifact)

    openlocus_bin, openlocus_source = c5a._resolve_openlocus_binary(args.openlocus)
    if openlocus_bin is None:
        report = _build_unavailable_report(
            "retrieval_failed",
            self_test_passed=self_test_passed,
            contextbench_row_offset=contextbench_row_offset,
            contextbench_row_limit=contextbench_row_limit,
            repoqa_needle_offset=repoqa_needle_offset,
            repoqa_needle_limit=repoqa_needle_limit,
            methods=methods,
            openlocus_binary_source=openlocus_source,
            network_mode="local_explicit",
            d5a1_input_record=d5a1_input_record,
        )
        _enforce_d5a2_no_forbidden(report)
        _write_json(out_path, report)
        print(
            f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, "
            f"status={report['status']}, failure_reason={report['failure_reason_category']})"
        )
        return

    network_mode = "local_explicit"
    eval_dir = Path(__file__).resolve().parent
    try:
        report = _run_heldout_smoke(
            contextbench_row_offset=contextbench_row_offset,
            contextbench_row_limit=contextbench_row_limit,
            repoqa_needle_offset=repoqa_needle_offset,
            repoqa_needle_limit=repoqa_needle_limit,
            methods=methods,
            openlocus_bin=openlocus_bin,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
            eval_dir=eval_dir,
            self_test_passed=self_test_passed,
            d5a1_input_record=d5a1_input_record,
            d5a1_buckets=d5a1_buckets,
        )
    except (OSError, subprocess.SubprocessError):
        report = _build_unavailable_report(
            "unexpected_exception",
            self_test_passed=self_test_passed,
            contextbench_row_offset=contextbench_row_offset,
            contextbench_row_limit=contextbench_row_limit,
            repoqa_needle_offset=repoqa_needle_offset,
            repoqa_needle_limit=repoqa_needle_limit,
            methods=methods,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
            d5a1_input_record=d5a1_input_record,
        )

    _enforce_d5a2_no_forbidden(report)
    _refuse_on_self_test_failure(report)
    _write_json(out_path, report)
    print(
        f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, "
        f"self_test_passed={report['self_test_passed']}, "
        f"status={report['status']}, phase={report['phase']}, "
        f"outcome={report['validation_outcome']}, "
        f"contextbench_rows_fetched={report['contextbench_rows_fetched']}, "
        f"repoqa_needles_seen={report['repoqa_needles_seen']})"
    )


if __name__ == "__main__":
    main()
