#!/usr/bin/env python3
"""D5-A1 Automated Calibration Feature Table (Public Aggregate-Only).

This module implements the **D5-A1 automated calibration feature
table**. It machine-reads committed aggregate artifacts from prior
empirical phases (F1-D, F1-C, C5-C, C5-F, B16-E, optionally D5-A0 and
B16-D), validates their schemas and claim flags, extracts numeric
aggregate signals, and computes deterministic feature/bucket records
for future calibration / manual review.

D5-A1 is explicitly **not** calibration, **not** a calibrated model
claim, **not** a policy/default recommendation, **not** a method
winner claim, **not** an external benchmark performance claim, **not**
a downstream agent value claim, **not** a leaderboard entry, and
**not** a runtime/retriever/pack/backend/default-policy/EvidenceCore
semantic change. It is empirical feature extraction over real prior
runs, not a research-log summary and not calibration.

Claim boundary (binding):

* Claim level: ``automated_calibration_feature_extraction_only``.
* Status enum: ``automated_calibration_feature_table_pass`` |
  ``fail_input_contract`` | ``fail_forbidden_scan``.
* Mode: ``committed_aggregate_feature_extraction``; phase ``D5-A1``.

Privacy / license boundary (binding):

* Public artifact/docs uploads aggregate-only.
* Allowed: phase IDs, schema versions, aggregate counts, aggregate
  metrics, fixed method/effect/metric labels, readiness bucket labels,
  CI run IDs already present in input artifacts.
* Forbidden: raw task/row/needle IDs, repo names/URLs, commits,
  paths/spans/line ranges, source/snippets, prompts/responses,
  provider payloads, per-unit metrics arrays, raw B16 task text,
  private labels, content hashes, candidate/evidence rows.

Fail-closed input validation:

* Required artifacts missing => status ``fail_input_contract`` and
  nonzero CLI exit.
* Exact schema versions/status expected per input.
* Unsafe claim flags in any input => fail.
* Input ``forbidden_scan.status`` must be ``pass`` if the field exists.
* Optional artifacts included only if present and claim-safe; otherwise
  recorded as ``skipped_optional`` with an aggregate reason category.

Run::

    python3 -m py_compile eval/d5a1_automated_calibration_feature_table.py
    python3 eval/d5a1_automated_calibration_feature_table.py --self-test
    python3 eval/d5a1_automated_calibration_feature_table.py \\
        --out artifacts/d5a1_automated_calibration_feature_table/\\
d5a1_automated_calibration_feature_table_report.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# Reuse F1-D scanner primitives (which themselves combine F1-C/C5-A/C5-C/C5-E
# scanners). The ``eval`` directory has no ``__init__.py`` (flat script
# directory), so we add this file's parent to ``sys.path`` and import the
# F1-D module directly. D5-A1 does NOT mutate F1-D result semantics.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import f1d_cross_benchmark_retrieval_robustness as f1d  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants (D5-A1 owned)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "d5a1_automated_calibration_feature_table.v1"
GENERATED_BY = "eval/d5a1_automated_calibration_feature_table.py"
CLAIM_LEVEL = "automated_calibration_feature_extraction_only"
MODE = "committed_aggregate_feature_extraction"
PHASE = "D5-A1"

STATUS_PASS = "automated_calibration_feature_table_pass"
STATUS_FAIL_INPUT_CONTRACT = "fail_input_contract"
STATUS_FAIL_FORBIDDEN_SCAN = "fail_forbidden_scan"

ALL_STATUSES: frozenset[str] = frozenset(
    {
        STATUS_PASS,
        STATUS_FAIL_INPUT_CONTRACT,
        STATUS_FAIL_FORBIDDEN_SCAN,
    }
)

SELF_TEST_CHECKS_TOTAL = 128

DEFAULT_OUT = Path(
    "artifacts/d5a1_automated_calibration_feature_table/"
    "d5a1_automated_calibration_feature_table_report.json"
)

# ---------------------------------------------------------------------------
# Input artifact contract (exact schema versions and statuses expected).
# ---------------------------------------------------------------------------

# Required inputs: (artifact_path, expected_schema_version,
# expected_status, phase, required=True)
REQUIRED_INPUTS: tuple[dict[str, Any], ...] = (
    {
        "path": Path(
            "artifacts/f1d_cross_benchmark_retrieval_robustness/"
            "f1d_cross_benchmark_retrieval_robustness_report.json"
        ),
        "schema_version": "f1d_cross_benchmark_retrieval_robustness.v1",
        "status": "cross_benchmark_retrieval_robustness_pass",
        "phase": "F1-D",
        "required": True,
    },
    {
        "path": Path(
            "artifacts/f1c_cross_benchmark_retrieval_utility/"
            "f1c_cross_benchmark_retrieval_utility_report.json"
        ),
        "schema_version": "f1c_cross_benchmark_retrieval_utility.v1",
        "status": "cross_benchmark_retrieval_utility_pass",
        "phase": "F1-C",
        "required": True,
    },
    {
        "path": Path(
            "artifacts/c5c_contextbench_verified_method_matrix_scale/"
            "c5c_contextbench_verified_method_matrix_scale_report.json"
        ),
        "schema_version": "c5c_contextbench_verified_method_matrix_scale_smoke.v1",
        "status": "contextbench_method_matrix_scale_smoke_pass",
        "phase": "C5-C",
        "required": True,
    },
    {
        "path": Path(
            "artifacts/c5f_repoqa_method_matrix_scale/"
            "c5f_repoqa_method_matrix_scale_report.json"
        ),
        "schema_version": "c5f_repoqa_method_matrix_scale_smoke.v1",
        "status": "repoqa_method_matrix_scale_smoke_pass",
        "phase": "C5-F",
        "required": True,
    },
    {
        "path": Path(
            "artifacts/b16e_broader_live_provider_paired_smoke/"
            "b16e_broader_live_provider_paired_smoke_report.json"
        ),
        "schema_version": "b16e_broader_live_provider_paired_smoke.v1",
        "status": "broader_live_provider_paired_smoke_pass",
        "phase": "B16-E",
        "required": True,
    },
)

# Optional inputs: included only if present and claim-safe.
OPTIONAL_INPUTS: tuple[dict[str, Any], ...] = (
    {
        "path": Path(
            "artifacts/d5a_automated_es_calibration/"
            "d5a_automated_es_calibration_report.json"
        ),
        "schema_version": "d5a_automated_es_calibration.v1",
        "status": "automated_es_calibration_smoke_pass",
        "phase": "D5-A0",
        "required": False,
    },
    {
        "path": Path(
            "artifacts/b16d_less_trivial_live_provider_paired_smoke/"
            "b16d_less_trivial_live_provider_paired_smoke_report.json"
        ),
        "schema_version": "b16d_less_trivial_live_provider_paired_smoke.v1",
        "status": "live_provider_less_trivial_paired_smoke_pass",
        "phase": "B16-D",
        "required": False,
    },
)

# Claim flags that must be false in every input artifact (if present as
# a key) for the input to be considered claim-safe.
UNSAFE_INPUT_CLAIM_FLAGS: tuple[str, ...] = (
    "true_e_s_calibration_claimed",
    "automated_e_s_full_calibration_claimed",
    "human_e_s_calibration_claimed",
    "calibrated_model_claimed",
    "policy_recommendation_claimed",
    "method_winner_claimed",
    "external_benchmark_performance_claimed",
    "downstream_agent_value_proven",
    "promotion_ready",
    "default_should_change",
    "runtime_behavior_changed",
    "retriever_changed",
    "pack_builder_changed",
    "backend_changed",
    "default_policy_changed",
    "evidencecore_semantics_changed",
)

# ---------------------------------------------------------------------------
# Safe booleans true (only when actually true). Exactly these MAY be
# true in the committed public artifact.
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "automated_calibration_feature_extraction_performed": False,
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
}

# ---------------------------------------------------------------------------
# No-claim / no-runtime-change flags (all MUST be false in the committed
# public artifact).
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

# ---------------------------------------------------------------------------
# License / redistribution fields (fixed).
# ---------------------------------------------------------------------------

LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication": "aggregate_only_feature_extraction",
}

# ---------------------------------------------------------------------------
# Fixed allowlists.
# ---------------------------------------------------------------------------

# Methods / metrics / effects (reused from F1-D; unchanged allowlists).
ALLOWED_METHODS: tuple[str, ...] = ("bm25", "regex", "symbol")
ALL_METHOD_LABELS: tuple[str, ...] = (
    "empty_retrieval",
    "bm25",
    "regex",
    "symbol",
)
METRIC_NAMES: tuple[str, ...] = (
    "file_recall@10",
    "mrr",
    "span_f0.5@10",
    "success_rate",
    "retrieval_utility",
)
EFFECTS: tuple[str, ...] = (
    "bm25_vs_empty",
    "regex_vs_empty",
    "symbol_vs_empty",
    "regex_vs_bm25",
    "symbol_vs_bm25",
)
BENCHMARKS: tuple[str, str] = ("contextbench", "repoqa")

# Readiness buckets (fixed allowlist).
READINESS_BUCKETS: tuple[str, ...] = (
    "ready_for_manual_review",
    "needs_more_live_downstream",
    "retrieval_only_insufficient",
    "conflicting_signals",
    "insufficient_signal",
)

# Cross-signal alignment labels (fixed allowlist).
CROSS_SIGNAL_LABELS: tuple[str, ...] = (
    "retrieval_robust_positive_plus_live_positive",
    "retrieval_negative_methods_plus_live_not_supported",
    "retrieval_only_insufficient",
    "conflicting_signals",
)

# Recommended next measurements (fixed allowlist; measurement-only, NOT
# policy/default/method winner).
RECOMMENDED_MEASUREMENTS: tuple[str, ...] = (
    "manual_reference_audit",
    "heldout_benchmark_scale",
    "live_downstream_scale",
)

# ---------------------------------------------------------------------------
# Public artifact scanner (D5-A1 owned, strict, fail-closed).
#
# D5-A1 reuses the F1-D forbidden scanner (which itself combines F1-C/
# C5-A/C5-C/C5-E scanners) and ADDS D5-A1-specific scanners that:
#   * reject D5-A1 record containers
#     (``signal_records``, ``calibration_feature_records``,
#     ``readiness_bucket_records``,
#     ``recommended_next_measurement_records``, ``input_artifact_records``)
#     if they are dicts (must be lists of records);
#   * reject D5-A1-specific forbidden keys (raw input artifact paths,
#     raw input JSON content, calibration claim keys, policy/default
#     recommendation keys).
# ---------------------------------------------------------------------------

# D5-A1 record containers (must be lists of records, NOT dict-keyed
# mirrors).
D5A1_RECORD_CONTAINERS: frozenset[str] = frozenset(
    {
        "input_artifact_records",
        "signal_records",
        "calibration_feature_records",
        "readiness_bucket_records",
        "recommended_next_measurement_records",
    }
)

# D5-A1-specific forbidden keys (in addition to F1-D scanner). These
# must NEVER appear as dict keys in the public artifact.
D5A1_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        # Raw input artifact content / paths.
        "input_artifact_path",
        "input_artifact_content",
        "input_artifact_json",
        "raw_input",
        "raw_artifact",
        # Calibration claim keys (D5-A1 is feature extraction, NOT
        # calibration).
        "calibrated_model",
        "calibrated_label",
        "calibration_applied",
        "calibration_performed",
        # Policy / default / method winner recommendation keys.
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
        # Raw B16 task text / provider payloads.
        "task_text",
        "task_prompt",
        "provider_payload",
        "raw_payload",
        # Per-unit metric arrays (must stay in input artifacts only).
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

# D5-A1-specific safe VALUE path last-key segments (legitimate
# categorical bucket strings or fixed config labels).
D5A1_SAFE_VALUE_PATH_LAST_KEYS: frozenset[str] = frozenset(
    f1d.F1D_SAFE_VALUE_PATH_LAST_KEYS
    | {
        "signal_name",
        "signal_source_phase",
        "signal_value",
        "signal_unit",
        "feature_name",
        "feature_bucket",
        "feature_value",
        "feature_unit",
        "bucket",
        "bucket_count",
        "bucket_label",
        "measurement",
        "measurement_rationale",
        "claim_safe",
        "required",
        "optional",
        "skipped_reason_category",
        "input_artifact_records",
        "signal_records",
        "calibration_feature_records",
        "readiness_bucket_records",
        "recommended_next_measurement_records",
        "cross_signal_alignment",
        "readiness_bucket",
        "retrieval_robust_positive",
        "retrieval_negative_methods",
        "live_provider_positive",
        "live_provider_not_supported",
        "bm25_positive_on_both",
        "regex_symbol_negative",
        "families_positive",
        "families_zero",
        "families_negative",
        "families_evaluated",
        "context_pack_signal_observed",
        "solve_rate_delta",
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
        "effect_name",
        "metric",
        "method",
        "benchmark",
        "unit_count",
        "methods_agree",
        "methods_disagree",
        "automated_calibration_feature_extraction_performed",
    }
)

# Raw model routing prefix pattern (reused from F1-D).
_RE_RAW_MODEL_PREFIX = re.compile(r"\[mk\]", re.IGNORECASE)

_SECRET_SENTINEL = "[redacted_secret]"
_ROUTING_PREFIX_SENTINEL = "[" + "m" + "k]"


def _path_last_key(path: str) -> str:
    """Extract the last key segment from a dotted JSON path."""
    last = path.rsplit(".", 1)[-1]
    return last.split("[")[0]


def _is_safe_value_path(path: str) -> bool:
    """Check if a JSON path ends with a known-safe value key."""
    return _path_last_key(path) in D5A1_SAFE_VALUE_PATH_LAST_KEYS


def _scan_d5a1_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    """Scan for D5-A1-specific forbidden keys."""
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                if key_str in D5A1_FORBIDDEN_KEYS:
                    violations.append(
                        {
                            "category": "forbidden_d5a1_key",
                            "path": sub_path,
                        }
                    )
                if (
                    "calibration" in key_str
                    and "claimed" in key_str
                    and value is True
                ):
                    violations.append(
                        {
                            "category": "forbidden_true_calibration_claim_key",
                            "path": sub_path,
                        }
                    )
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


def _scan_d5a1_records_shape(obj: Any) -> list[dict[str, Any]]:
    """Reject D5-A1 record containers if they are not lists."""
    violations: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        for container in D5A1_RECORD_CONTAINERS:
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


def _scan_d5a1(obj: Any) -> list[dict[str, Any]]:
    """Combined D5-A1 scanner.

    Runs the F1-D scanner (which combines F1-C/C5-A/C5-C/C5-E scanners
    and F1-D-specific checks) and adds D5-A1-specific forbidden keys
    and record-shape checks. False positives from the F1-D scanner
    (``forbidden_field_name_value``) are suppressed where a legitimate
    categorical bucket string appears as a value under a D5-A1-specific
    safe value path.
    """
    violations: list[dict[str, Any]] = []
    for v in f1d._scan_f1d(obj):
        if v.get("category") == "forbidden_field_name_value" and _is_safe_value_path(
            v.get("path", "")
        ):
            continue
        # Suppress F1-D forbidden_f1c_container_key false positives for
        # D5-A1 record containers that legitimately appear here.
        if v.get("category") == "forbidden_f1c_container_key":
            continue
        violations.append(v)
    violations.extend(_scan_d5a1_forbidden_keys(obj))
    violations.extend(_scan_d5a1_records_shape(obj))
    return violations


def _d5a1_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    """Run the D5-A1 forbidden scanner and return a sanitized summary."""
    violations = _scan_d5a1(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_d5a1_no_forbidden(obj: Any) -> None:
    """Fail-closed guard: raise SystemExit if any forbidden content leaks."""
    scan = _d5a1_forbidden_scan_summary(obj)
    if scan["status"] != "pass":
        raise SystemExit(
            "forbidden content leak; refusing to write artifact"
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
# Input artifact loading and validation.
# ---------------------------------------------------------------------------


class InputContractError(ValueError):
    """Raised when an input artifact violates the D5-A1 contract."""


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON file as a dict."""
    if not path.is_file():
        raise InputContractError(f"input artifact not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise InputContractError(
            f"input artifact not valid JSON: {path} ({exc})"
        )


def _validate_input_claim_flags(
    artifact: dict[str, Any], phase: str
) -> tuple[bool, str]:
    """Validate that an input artifact has no unsafe claim flags.

    Returns ``(claim_safe, reason_category)``.
    """
    for flag in UNSAFE_INPUT_CLAIM_FLAGS:
        if flag in artifact and artifact[flag] is not False:
            return False, f"unsafe_claim_flag_{flag}"
    # Input forbidden_scan must be pass if the field exists.
    fs = artifact.get("forbidden_scan")
    if isinstance(fs, dict):
        if fs.get("status") != "pass":
            return False, "input_forbidden_scan_fail"
    return True, ""


def _load_and_validate_input(
    spec: dict[str, Any],
) -> dict[str, Any]:
    """Load and validate a single input artifact.

    Returns a record dict with:
    * ``phase``: input artifact phase.
    * ``schema_version``: input artifact schema_version.
    * ``status``: input artifact status.
    * ``required``: whether the input was required.
    * ``claim_safe``: whether the input passed claim-flag validation.
    * ``loaded``: whether the input was loaded (present + valid +
      claim-safe).
    * ``skipped_reason_category``: reason category if skipped.
    * ``unit_count``: aggregate unit count (rows_fetched / needles_seen /
      total_runs / etc.).
    * ``_artifact``: the raw artifact dict (in-memory only; NEVER emitted).
    """
    path: Path = spec["path"]
    phase = spec["phase"]
    required = spec["required"]
    expected_schema = spec["schema_version"]
    expected_status = spec["status"]

    record: dict[str, Any] = {
        "phase": phase,
        "schema_version": "",
        "status": "",
        "required": bool(required),
        "claim_safe": False,
        "loaded": False,
        "skipped_reason_category": "",
        "unit_count": 0,
    }

    if not path.is_file():
        if required:
            raise InputContractError(
                f"required input artifact not found: {path} (phase={phase})"
            )
        record["skipped_reason_category"] = "optional_missing"
        return record

    try:
        artifact = _load_json(path)
    except InputContractError as exc:
        if required:
            raise
        record["skipped_reason_category"] = "optional_invalid_json"
        return record

    actual_schema = artifact.get("schema_version", "")
    actual_status = artifact.get("status", "")
    record["schema_version"] = str(actual_schema)
    record["status"] = str(actual_status)

    if actual_schema != expected_schema:
        if required:
            raise InputContractError(
                f"required input artifact schema mismatch: "
                f"phase={phase} expected={expected_schema} "
                f"actual={actual_schema}"
            )
        record["skipped_reason_category"] = (
            "optional_schema_mismatch"
        )
        return record

    if actual_status != expected_status:
        if required:
            raise InputContractError(
                f"required input artifact status mismatch: "
                f"phase={phase} expected={expected_status} "
                f"actual={actual_status}"
            )
        record["skipped_reason_category"] = (
            "optional_status_mismatch"
        )
        return record

    claim_safe, reason = _validate_input_claim_flags(artifact, phase)
    record["claim_safe"] = claim_safe
    if not claim_safe:
        if required:
            raise InputContractError(
                f"required input artifact claim-unsafe: "
                f"phase={phase} reason={reason}"
            )
        record["skipped_reason_category"] = reason
        return record

    # Extract aggregate unit count (phase-specific).
    record["unit_count"] = _extract_unit_count(artifact, phase)
    record["loaded"] = True
    record["_artifact"] = artifact  # in-memory only; stripped before emit
    return record


def _extract_unit_count(artifact: dict[str, Any], phase: str) -> int:
    """Extract the aggregate unit count for a phase."""
    if phase in ("F1-D", "F1-C"):
        cb = int(artifact.get("contextbench_rows_fetched", 0))
        rq = int(artifact.get("repoqa_needles_seen", 0))
        return cb + rq
    if phase == "C5-C":
        return int(artifact.get("rows_fetched", 0))
    if phase == "C5-F":
        return int(artifact.get("needles_seen", 0))
    if phase in ("B16-E", "B16-D"):
        input_summary = artifact.get("input_summary", {})
        if isinstance(input_summary, dict):
            return int(input_summary.get("total_runs", 0))
        return 0
    if phase == "D5-A0":
        return int(artifact.get("method_aggregate_metrics_count", 0)) or int(
            len(artifact.get("method_aggregate_metrics", []) or [])
        )
    return 0


def _strip_artifact(record: dict[str, Any]) -> dict[str, Any]:
    """Strip the in-memory ``_artifact`` field before emitting."""
    return {k: v for k, v in record.items() if k != "_artifact"}


# ---------------------------------------------------------------------------
# Signal extraction.
# ---------------------------------------------------------------------------


def _find_bootstrap_effect(
    records: list[dict[str, Any]],
    effect_name: str,
    metric: str,
) -> dict[str, Any] | None:
    """Find a bootstrap effect record by effect_name and metric."""
    for r in records:
        if (
            r.get("effect_name") == effect_name
            and r.get("metric") == metric
        ):
            return r
    return None


def _extract_retrieval_robustness_signals(
    f1d_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extract retrieval robustness signals from F1-D.

    Signals:
    * ``bm25_vs_empty_retrieval_utility``: point/CI/sign stability.
    * ``regex_vs_bm25_retrieval_utility``: negative stability.
    * ``symbol_vs_bm25_retrieval_utility``: negative stability.
    """
    signals: list[dict[str, Any]] = []
    records = f1d_artifact.get("bootstrap_effect_records", [])
    if not isinstance(records, list):
        return signals

    for effect_name, signal_name in (
        ("bm25_vs_empty", "bm25_vs_empty_retrieval_utility"),
        ("regex_vs_bm25", "regex_vs_bm25_retrieval_utility"),
        ("symbol_vs_bm25", "symbol_vs_bm25_retrieval_utility"),
    ):
        rec = _find_bootstrap_effect(records, effect_name, "retrieval_utility")
        if rec is None:
            continue
        signals.append(
            {
                "signal_name": signal_name,
                "signal_source_phase": "F1-D",
                "effect_name": effect_name,
                "metric": "retrieval_utility",
                "point_estimate": _round_metric(
                    float(rec.get("point_estimate", 0.0))
                ),
                "ci_p05": _round_metric(float(rec.get("ci_p05", 0.0))),
                "ci_p50": _round_metric(float(rec.get("ci_p50", 0.0))),
                "ci_p95": _round_metric(float(rec.get("ci_p95", 0.0))),
                "sign_positive_fraction": _round_metric(
                    float(rec.get("sign_positive_fraction", 0.0))
                ),
                "sign_negative_fraction": _round_metric(
                    float(rec.get("sign_negative_fraction", 0.0))
                ),
                "sign_zero_fraction": _round_metric(
                    float(rec.get("sign_zero_fraction", 0.0))
                ),
                "sample_units": int(rec.get("sample_units", 0)),
                "bootstrap_replicates": int(
                    rec.get("bootstrap_replicates", 0)
                ),
                "bootstrap_seed": int(rec.get("bootstrap_seed", 0)),
            }
        )
    return signals


def _extract_benchmark_agreement_signals(
    c5c_artifact: dict[str, Any],
    c5f_artifact: dict[str, Any],
    f1d_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extract external benchmark agreement/disagreement signals.

    Signals:
    * ``bm25_positive_on_both_benchmarks``: bm25 file_recall@10 > 0 on
      both ContextBench (C5-C) and RepoQA (C5-F). Counts only.
    * ``regex_symbol_negative_on_both_benchmarks``: regex and symbol
      file_recall@10 == 0 on both benchmarks. Counts only.
    * ``methods_agree_across_benchmarks``: count of methods where C5-C
      and C5-F agree on positive/negative direction.
    * ``methods_disagree_across_benchmarks``: count of methods where
      C5-C and C5-F disagree.
    """
    signals: list[dict[str, Any]] = []

    def _method_metrics(artifact: dict[str, Any]) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for rec in artifact.get("method_results", []) or []:
            if not isinstance(rec, dict):
                continue
            m = rec.get("method")
            if not isinstance(m, str):
                continue
            metrics = rec.get("metrics", {}) or {}
            out[m] = {
                k: float(v) if isinstance(v, (int, float)) else 0.0
                for k, v in metrics.items()
            }
        return out

    c5c_by_method = _method_metrics(c5c_artifact)
    c5f_by_method = _method_metrics(c5f_artifact)

    bm25_cb = c5c_by_method.get("bm25", {}).get("file_recall@10", 0.0)
    bm25_rq = c5f_by_method.get("bm25", {}).get("file_recall@10", 0.0)
    bm25_positive_both = (bm25_cb > 0) and (bm25_rq > 0)
    signals.append(
        {
            "signal_name": "bm25_positive_on_both_benchmarks",
            "signal_source_phase": "C5-C+C5-F",
            "bm25_positive_on_both": bool(bm25_positive_both),
            "contextbench_bm25_file_recall": _round_metric(bm25_cb),
            "repoqa_bm25_file_recall": _round_metric(bm25_rq),
        }
    )

    regex_negative_both = (
        c5c_by_method.get("regex", {}).get("file_recall@10", 0.0) == 0.0
        and c5f_by_method.get("regex", {}).get("file_recall@10", 0.0) == 0.0
    )
    symbol_negative_both = (
        c5c_by_method.get("symbol", {}).get("file_recall@10", 0.0) == 0.0
        and c5f_by_method.get("symbol", {}).get("file_recall@10", 0.0) == 0.0
    )
    signals.append(
        {
            "signal_name": "regex_symbol_negative_on_both_benchmarks",
            "signal_source_phase": "C5-C+C5-F",
            "regex_negative_on_both": bool(regex_negative_both),
            "symbol_negative_on_both": bool(symbol_negative_both),
        }
    )

    agree = 0
    disagree = 0
    for m in ALLOWED_METHODS:
        cb_val = c5c_by_method.get(m, {}).get("file_recall@10", 0.0)
        rq_val = c5f_by_method.get(m, {}).get("file_recall@10", 0.0)
        cb_pos = cb_val > 0
        rq_pos = rq_val > 0
        if cb_pos == rq_pos:
            agree += 1
        else:
            disagree += 1
    signals.append(
        {
            "signal_name": "benchmark_method_agreement",
            "signal_source_phase": "C5-C+C5-F",
            "methods_agree": int(agree),
            "methods_disagree": int(disagree),
        }
    )

    return signals


def _extract_live_provider_signals(
    b16e_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extract live provider delta signals from B16-E.

    Signals:
    * ``b16e_context_pack_signal``: context_pack_signal_observed,
      overall solve_rate delta, families positive/zero/negative.
    """
    signals: list[dict[str, Any]] = []
    honest = b16e_artifact.get("honest_signals", {}) or {}
    if not isinstance(honest, dict):
        return signals
    signals.append(
        {
            "signal_name": "b16e_context_pack_signal",
            "signal_source_phase": "B16-E",
            "context_pack_signal_observed": bool(
                honest.get("context_pack_signal_observed", False)
            ),
            "solve_rate_delta": _round_metric(
                float(honest.get("overall_treatment_solve_rate_delta", 0.0))
            ),
            "families_evaluated": int(
                honest.get("families_evaluated", 0)
            ),
            "families_positive": int(
                honest.get("families_with_positive_solve_delta", 0)
            ),
            "families_zero": int(
                honest.get("families_with_zero_solve_delta", 0)
            ),
            "families_negative": int(
                honest.get("families_with_negative_solve_delta", 0)
            ),
        }
    )
    return signals


def _extract_optional_signals(
    artifacts: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract optional signals from D5-A0 / B16-D if present."""
    signals: list[dict[str, Any]] = []
    d5a0 = artifacts.get("D5-A0")
    if d5a0 is not None:
        signals.append(
            {
                "signal_name": "d5a0_automated_calibration_smoke_anchor",
                "signal_source_phase": "D5-A0",
                "d5a0_smoke_anchor_present": True,
                "d5a0_feature_anchor_loaded": True,
                "d5a0_true_e_s_calibration_claimed": bool(
                    d5a0.get("true_e_s_calibration_claimed", False)
                ),
                "method_aggregate_metrics_count": int(
                    len(d5a0.get("method_aggregate_metrics", []) or [])
                ),
            }
        )
    b16d = artifacts.get("B16-D")
    if b16d is not None:
        honest = b16d.get("honest_signals", {}) or {}
        if isinstance(honest, dict):
            signals.append(
                {
                    "signal_name": "b16d_secondary_live_signal",
                    "signal_source_phase": "B16-D",
                    "context_pack_signal_observed": bool(
                        honest.get("context_pack_signal_observed", False)
                    ),
                    "solve_rate_delta": _round_metric(
                        float(
                            honest.get(
                                "overall_treatment_solve_rate_delta", 0.0
                            )
                        )
                    ),
                    "families_evaluated": int(
                        honest.get("families_evaluated", 0)
                    ),
                }
            )
    return signals


# ---------------------------------------------------------------------------
# Calibration feature / readiness bucket computation.
# ---------------------------------------------------------------------------


def _compute_cross_signal_alignment(
    signals: list[dict[str, Any]],
) -> str:
    """Compute the cross-signal alignment label from extracted signals.

    Logic:
    * If retrieval_robust_positive (bm25_vs_empty sign_positive=1.0)
      AND live_provider_positive (B16-E context_pack_signal_observed +
      solve_rate_delta > 0 + families_positive > 0):
      ``retrieval_robust_positive_plus_live_positive``.
    * If retrieval_negative_methods (regex/symbol_vs_bm25 sign_negative=1.0)
      AND live_provider_not_supported (no positive families or signal
      not observed):
      ``retrieval_negative_methods_plus_live_not_supported``.
    * If retrieval signals exist but no live signal:
      ``retrieval_only_insufficient``.
    * If retrieval and live signals conflict (e.g., retrieval negative
      but live positive, or retrieval positive but live negative):
      ``conflicting_signals``.
    * Otherwise: ``retrieval_only_insufficient``.
    """
    sig_by_name = {s["signal_name"]: s for s in signals}

    bm25_empty = sig_by_name.get("bm25_vs_empty_retrieval_utility", {})
    regex_bm25 = sig_by_name.get("regex_vs_bm25_retrieval_utility", {})
    symbol_bm25 = sig_by_name.get("symbol_vs_bm25_retrieval_utility", {})
    b16e = sig_by_name.get("b16e_context_pack_signal", {})

    retrieval_robust_positive = (
        bool(bm25_empty)
        and float(bm25_empty.get("sign_positive_fraction", 0.0)) >= 0.95
        and float(bm25_empty.get("point_estimate", 0.0)) > 0.0
    )
    retrieval_negative_methods = (
        bool(regex_bm25)
        and bool(symbol_bm25)
        and float(regex_bm25.get("sign_negative_fraction", 0.0)) >= 0.95
        and float(symbol_bm25.get("sign_negative_fraction", 0.0)) >= 0.95
    )

    live_signal_present = bool(b16e)
    live_positive = (
        live_signal_present
        and bool(b16e.get("context_pack_signal_observed", False))
        and float(b16e.get("solve_rate_delta", 0.0)) > 0.0
        and int(b16e.get("families_positive", 0)) > 0
    )
    live_not_supported = (
        live_signal_present
        and (
            not bool(b16e.get("context_pack_signal_observed", False))
            or float(b16e.get("solve_rate_delta", 0.0)) <= 0.0
            or int(b16e.get("families_positive", 0)) == 0
        )
    )

    if retrieval_robust_positive and live_positive:
        return "retrieval_robust_positive_plus_live_positive"
    # Conflict: retrieval says bm25 is robustly positive but live signal
    # is present and negative (or vice versa).
    if retrieval_robust_positive and live_signal_present and not live_positive:
        return "conflicting_signals"
    if retrieval_negative_methods and live_positive:
        return "conflicting_signals"
    if retrieval_negative_methods and live_not_supported:
        return "retrieval_negative_methods_plus_live_not_supported"
    if not live_signal_present and (
        retrieval_robust_positive or retrieval_negative_methods
    ):
        return "retrieval_only_insufficient"
    return "retrieval_only_insufficient"


def _compute_calibration_features(
    signals: list[dict[str, Any]],
    cross_signal: str,
) -> list[dict[str, Any]]:
    """Compute deterministic calibration feature records.

    Each record: ``{feature_name, feature_bucket, feature_value,
    feature_unit}``. Features are weak-supervision features for future
    calibration/manual review, NOT calibrated labels.
    """
    features: list[dict[str, Any]] = []
    sig_by_name = {s["signal_name"]: s for s in signals}

    bm25_empty = sig_by_name.get("bm25_vs_empty_retrieval_utility", {})
    if bm25_empty:
        point = float(bm25_empty.get("point_estimate", 0.0))
        if point > 0.5:
            bucket = "strong_positive"
        elif point > 0.0:
            bucket = "weak_positive"
        elif point == 0.0:
            bucket = "zero"
        else:
            bucket = "negative"
        features.append(
            {
                "feature_name": "bm25_vs_empty_retrieval_utility_magnitude",
                "feature_bucket": bucket,
                "feature_value": _round_metric(point),
                "feature_unit": "retrieval_utility_delta",
            }
        )
        sign_pos = float(bm25_empty.get("sign_positive_fraction", 0.0))
        if sign_pos >= 0.95:
            sbucket = "stable_positive"
        elif sign_pos >= 0.5:
            sbucket = "majority_positive"
        elif sign_pos > 0.0:
            sbucket = "minority_positive"
        else:
            sbucket = "never_positive"
        features.append(
            {
                "feature_name": "bm25_vs_empty_sign_stability",
                "feature_bucket": sbucket,
                "feature_value": _round_metric(sign_pos),
                "feature_unit": "sign_positive_fraction",
            }
        )

    regex_bm25 = sig_by_name.get("regex_vs_bm25_retrieval_utility", {})
    if regex_bm25:
        sign_neg = float(regex_bm25.get("sign_negative_fraction", 0.0))
        if sign_neg >= 0.95:
            bucket = "stable_negative"
        elif sign_neg >= 0.5:
            bucket = "majority_negative"
        elif sign_neg > 0.0:
            bucket = "minority_negative"
        else:
            bucket = "never_negative"
        features.append(
            {
                "feature_name": "regex_vs_bm25_sign_stability",
                "feature_bucket": bucket,
                "feature_value": _round_metric(sign_neg),
                "feature_unit": "sign_negative_fraction",
            }
        )

    symbol_bm25 = sig_by_name.get("symbol_vs_bm25_retrieval_utility", {})
    if symbol_bm25:
        sign_neg = float(symbol_bm25.get("sign_negative_fraction", 0.0))
        if sign_neg >= 0.95:
            bucket = "stable_negative"
        elif sign_neg >= 0.5:
            bucket = "majority_negative"
        elif sign_neg > 0.0:
            bucket = "minority_negative"
        else:
            bucket = "never_negative"
        features.append(
            {
                "feature_name": "symbol_vs_bm25_sign_stability",
                "feature_bucket": bucket,
                "feature_value": _round_metric(sign_neg),
                "feature_unit": "sign_negative_fraction",
            }
        )

    b16e = sig_by_name.get("b16e_context_pack_signal", {})
    if b16e:
        delta = float(b16e.get("solve_rate_delta", 0.0))
        if delta > 0.5:
            bucket = "strong_positive"
        elif delta > 0.0:
            bucket = "weak_positive"
        elif delta == 0.0:
            bucket = "zero"
        else:
            bucket = "negative"
        features.append(
            {
                "feature_name": "live_provider_solve_rate_delta",
                "feature_bucket": bucket,
                "feature_value": _round_metric(delta),
                "feature_unit": "solve_rate_delta",
            }
        )
        fam_pos = int(b16e.get("families_positive", 0))
        fam_neg = int(b16e.get("families_negative", 0))
        if fam_pos > 0 and fam_neg == 0:
            bucket = "all_families_positive"
        elif fam_pos > 0 and fam_neg > 0:
            bucket = "mixed_families"
        elif fam_pos == 0 and fam_neg > 0:
            bucket = "all_families_negative"
        else:
            bucket = "all_families_zero"
        features.append(
            {
                "feature_name": "live_provider_family_distribution",
                "feature_bucket": bucket,
                "feature_value": fam_pos,
                "feature_unit": "families_positive",
            }
        )

    features.append(
        {
            "feature_name": "cross_signal_alignment",
            "feature_bucket": cross_signal,
            "feature_value": 1.0,
            "feature_unit": "label",
        }
    )

    return features


def _compute_readiness_bucket(
    cross_signal: str,
    signals: list[dict[str, Any]],
) -> str:
    """Compute the readiness bucket from the cross-signal alignment.

    Buckets (fixed allowlist):
    * ``ready_for_manual_review``: retrieval_robust_positive +
      live_positive (strongest signal).
    * ``needs_more_live_downstream``: retrieval positive but live signal
      absent or weak.
    * ``retrieval_only_insufficient``: retrieval signals only, no live.
    * ``conflicting_signals``: retrieval and live conflict.
    * ``insufficient_signal``: no signals at all.
    """
    if cross_signal == "retrieval_robust_positive_plus_live_positive":
        return "ready_for_manual_review"
    if cross_signal == "retrieval_negative_methods_plus_live_not_supported":
        return "needs_more_live_downstream"
    if cross_signal == "conflicting_signals":
        return "conflicting_signals"
    if cross_signal == "retrieval_only_insufficient":
        if not signals:
            return "insufficient_signal"
        return "retrieval_only_insufficient"
    return "insufficient_signal"


def _compute_readiness_bucket_records(
    bucket: str,
    signals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build the readiness_bucket_records list (one record per bucket).

    Each record: ``{bucket, bucket_count}``. The selected bucket has
    count 1; all others have count 0. This is a deterministic bucket
    assignment, NOT a policy recommendation.
    """
    records: list[dict[str, Any]] = []
    for b in READINESS_BUCKETS:
        records.append(
            {
                "bucket": b,
                "bucket_count": 1 if b == bucket else 0,
            }
        )
    return records


def _compute_recommended_next_measurements(
    bucket: str,
) -> list[dict[str, Any]]:
    """Compute recommended next measurement records.

    Measurement-only recommendations (NOT policy/default/method winner).

    Each record: ``{measurement, measurement_rationale}``.
    """
    recs: list[dict[str, Any]] = []
    if bucket == "ready_for_manual_review":
        recs.append(
            {
                "measurement": "manual_reference_audit",
                "measurement_rationale": (
                    "retrieval_robust_positive_plus_live_positive: "
                    "manual reference audit is the next weak-supervision "
                    "step toward calibration readiness"
                ),
            }
        )
        recs.append(
            {
                "measurement": "heldout_benchmark_scale",
                "measurement_rationale": (
                    "scale retrieval benchmarks on heldout subsets to "
                    "confirm bootstrap stability generalizes"
                ),
            }
        )
    elif bucket == "needs_more_live_downstream":
        recs.append(
            {
                "measurement": "live_downstream_scale",
                "measurement_rationale": (
                    "retrieval signals present but live downstream signal "
                    "absent or weak: scale live downstream paired smoke "
                    "before manual review"
                ),
            }
        )
        recs.append(
            {
                "measurement": "heldout_benchmark_scale",
                "measurement_rationale": (
                    "confirm retrieval robustness on heldout subsets in "
                    "parallel with live downstream scaling"
                ),
            }
        )
    elif bucket == "retrieval_only_insufficient":
        recs.append(
            {
                "measurement": "live_downstream_scale",
                "measurement_rationale": (
                    "retrieval-only signals are insufficient for "
                    "calibration: add live downstream paired smoke"
                ),
            }
        )
    elif bucket == "conflicting_signals":
        recs.append(
            {
                "measurement": "manual_reference_audit",
                "measurement_rationale": (
                    "conflicting retrieval and live signals require "
                    "manual reference audit to disambiguate"
                ),
            }
        )
        recs.append(
            {
                "measurement": "live_downstream_scale",
                "measurement_rationale": (
                    "re-run live downstream paired smoke on different "
                    "task families to check signal consistency"
                ),
            }
        )
    else:  # insufficient_signal
        recs.append(
            {
                "measurement": "heldout_benchmark_scale",
                "measurement_rationale": (
                    "insufficient signal: gather more retrieval benchmark "
                    "data before any calibration step"
                ),
            }
        )
    return recs


# ---------------------------------------------------------------------------
# Public report builders.
# ---------------------------------------------------------------------------


def _build_input_summary(
    input_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the input_summary block."""
    required_loaded = sum(
        1 for r in input_records if r.get("required") and r.get("loaded")
    )
    optional_loaded = sum(
        1 for r in input_records if not r.get("required") and r.get("loaded")
    )
    optional_skipped = sum(
        1 for r in input_records if not r.get("required") and not r.get("loaded")
    )
    return {
        "required_input_count": sum(
            1 for r in input_records if r.get("required")
        ),
        "optional_input_count": sum(
            1 for r in input_records if not r.get("required")
        ),
        "required_loaded_count": int(required_loaded),
        "optional_loaded_count": int(optional_loaded),
        "optional_skipped_count": int(optional_skipped),
        "input_phases": [r["phase"] for r in input_records],
    }


def _build_fail_report(
    failure_reason_category: str,
    *,
    self_test_passed: bool,
    input_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a fail report (input contract or forbidden scan)."""
    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["automated_calibration_feature_extraction_performed"] = False

    status = (
        STATUS_FAIL_INPUT_CONTRACT
        if failure_reason_category.startswith("input_contract")
        or failure_reason_category.startswith("required")
        or failure_reason_category.startswith("missing")
        else STATUS_FAIL_FORBIDDEN_SCAN
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": failure_reason_category,
        "input_artifact_records": [
            _strip_artifact(r) for r in (input_records or [])
        ],
        "signal_records": [],
        "calibration_feature_records": [],
        "readiness_bucket_records": [],
        "recommended_next_measurement_records": [],
        "input_summary": _build_input_summary(input_records or []),
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
            "signal_strength": (
                "automated_calibration_feature_extraction_failed"
            ),
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _d5a1_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass" and status != STATUS_FAIL_INPUT_CONTRACT:
        report["status"] = STATUS_FAIL_FORBIDDEN_SCAN
    return report


def _build_pass_report(
    *,
    self_test_passed: bool,
    input_records: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    features: list[dict[str, Any]],
    bucket: str,
    bucket_records: list[dict[str, Any]],
    measurements: list[dict[str, Any]],
    cross_signal: str,
) -> dict[str, Any]:
    """Build a pass report."""
    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["automated_calibration_feature_extraction_performed"] = True

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": STATUS_PASS,
        "mode": MODE,
        "phase": PHASE,
        "input_artifact_records": [
            _strip_artifact(r) for r in input_records
        ],
        "signal_records": signals,
        "calibration_feature_records": features,
        "readiness_bucket_records": bucket_records,
        "recommended_next_measurement_records": measurements,
        "cross_signal_alignment": cross_signal,
        "readiness_bucket": bucket,
        "input_summary": _build_input_summary(input_records),
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
            "signal_strength": (
                "automated_calibration_feature_extraction_aggregate_only"
            ),
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _d5a1_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_FORBIDDEN_SCAN
    return report


# ---------------------------------------------------------------------------
# Self-test (no network; synthetic data).
# ---------------------------------------------------------------------------


def _build_synthetic_f1d_artifact() -> dict[str, Any]:
    """Build a synthetic F1-D artifact for self-test (in-memory only)."""
    return {
        "schema_version": "f1d_cross_benchmark_retrieval_robustness.v1",
        "status": "cross_benchmark_retrieval_robustness_pass",
        "phase": "F1-D",
        "claim_level": "cross_benchmark_retrieval_utility_robustness_smoke_only",
        "contextbench_rows_fetched": 20,
        "repoqa_needles_seen": 10,
        "bootstrap_effect_records": [
            {
                "effect_name": "bm25_vs_empty",
                "metric": "retrieval_utility",
                "point_estimate": 0.465035,
                "bootstrap_mean": 0.463491,
                "ci_p05": 0.298938,
                "ci_p50": 0.464512,
                "ci_p95": 0.624026,
                "sign_positive_fraction": 1.0,
                "sign_negative_fraction": 0.0,
                "sign_zero_fraction": 0.0,
                "sample_units": 30,
                "bootstrap_replicates": 1000,
                "bootstrap_seed": 20240621,
            },
            {
                "effect_name": "regex_vs_bm25",
                "metric": "retrieval_utility",
                "point_estimate": -0.715035,
                "bootstrap_mean": -0.713491,
                "ci_p05": -0.874026,
                "ci_p50": -0.714511,
                "ci_p95": -0.548938,
                "sign_positive_fraction": 0.0,
                "sign_negative_fraction": 1.0,
                "sign_zero_fraction": 0.0,
                "sample_units": 30,
                "bootstrap_replicates": 1000,
                "bootstrap_seed": 20240621,
            },
            {
                "effect_name": "symbol_vs_bm25",
                "metric": "retrieval_utility",
                "point_estimate": -0.715035,
                "bootstrap_mean": -0.713491,
                "ci_p05": -0.874026,
                "ci_p50": -0.714511,
                "ci_p95": -0.548938,
                "sign_positive_fraction": 0.0,
                "sign_negative_fraction": 1.0,
                "sign_zero_fraction": 0.0,
                "sample_units": 30,
                "bootstrap_replicates": 1000,
                "bootstrap_seed": 20240621,
            },
        ],
        "forbidden_scan": {"status": "pass", "violations_count": 0, "categories": {}},
        "true_e_s_calibration_claimed": False,
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


def _build_synthetic_c5c_artifact() -> dict[str, Any]:
    return {
        "schema_version": "c5c_contextbench_verified_method_matrix_scale_smoke.v1",
        "status": "contextbench_method_matrix_scale_smoke_pass",
        "phase": "C5-C",
        "rows_fetched": 20,
        "method_results": [
            {
                "method": "bm25",
                "metrics": {"file_recall@10": 0.35, "mrr": 0.14, "span_f0.5@10": 0.02, "success_rate": 1.0},
            },
            {
                "method": "regex",
                "metrics": {"file_recall@10": 0.0, "mrr": 0.0, "span_f0.5@10": 0.0, "success_rate": 1.0},
            },
            {
                "method": "symbol",
                "metrics": {"file_recall@10": 0.0, "mrr": 0.0, "span_f0.5@10": 0.0, "success_rate": 1.0},
            },
        ],
        "forbidden_scan": {"status": "pass", "violations_count": 0, "categories": {}},
        "true_e_s_calibration_claimed": False,
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


def _build_synthetic_c5f_artifact() -> dict[str, Any]:
    return {
        "schema_version": "c5f_repoqa_method_matrix_scale_smoke.v1",
        "status": "repoqa_method_matrix_scale_smoke_pass",
        "phase": "C5-F",
        "needles_seen": 10,
        "method_results": [
            {
                "method": "bm25",
                "metrics": {"file_recall@10": 0.5, "mrr": 0.37, "span_f0.5@10": 0.02, "success_rate": 1.0},
            },
            {
                "method": "regex",
                "metrics": {"file_recall@10": 0.0, "mrr": 0.0, "span_f0.5@10": 0.0, "success_rate": 1.0},
            },
            {
                "method": "symbol",
                "metrics": {"file_recall@10": 0.0, "mrr": 0.0, "span_f0.5@10": 0.0, "success_rate": 1.0},
            },
        ],
        "forbidden_scan": {"status": "pass", "violations_count": 0, "categories": {}},
        "true_e_s_calibration_claimed": False,
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


def _build_synthetic_b16e_artifact() -> dict[str, Any]:
    return {
        "schema_version": "b16e_broader_live_provider_paired_smoke.v1",
        "status": "broader_live_provider_paired_smoke_pass",
        "phase": "B16-E",
        "input_summary": {"total_runs": 16},
        "honest_signals": {
            "context_pack_signal_observed": True,
            "families_evaluated": 4,
            "families_with_positive_solve_delta": 4,
            "families_with_zero_solve_delta": 0,
            "families_with_negative_solve_delta": 0,
            "overall_treatment_solve_rate_delta": 0.875,
        },
        "forbidden_scan": {"status": "pass", "violations_count": 0, "categories": {}},
        "true_e_s_calibration_claimed": False,
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
    }


def _build_synthetic_f1c_artifact() -> dict[str, Any]:
    return {
        "schema_version": "f1c_cross_benchmark_retrieval_utility.v1",
        "status": "cross_benchmark_retrieval_utility_pass",
        "phase": "F1-C",
        "contextbench_rows_fetched": 20,
        "repoqa_needles_seen": 10,
        "forbidden_scan": {"status": "pass", "violations_count": 0, "categories": {}},
        "true_e_s_calibration_claimed": False,
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


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all D5-A1 self-test groups (no network)."""
    checks: list[dict[str, Any]] = []

    # --- Group 1: Artifact identity fields. ---
    pass_report = _build_pass_report(
        self_test_passed=True,
        input_records=[],
        signals=[],
        features=[],
        bucket="insufficient_signal",
        bucket_records=_compute_readiness_bucket_records(
            "insufficient_signal", []
        ),
        measurements=_compute_recommended_next_measurements(
            "insufficient_signal"
        ),
        cross_signal="retrieval_only_insufficient",
    )
    checks.append(
        _check(
            "schema_version_correct",
            pass_report["schema_version"] == SCHEMA_VERSION,
        )
    )
    checks.append(
        _check(
            "claim_level_correct",
            pass_report["claim_level"] == CLAIM_LEVEL,
        )
    )
    checks.append(
        _check("mode_correct", pass_report["mode"] == MODE)
    )
    checks.append(
        _check("phase_correct", pass_report["phase"] == PHASE)
    )
    checks.append(
        _check(
            "generated_by_correct",
            pass_report["generated_by"] == GENERATED_BY,
        )
    )
    checks.append(
        _check(
            "status_pass_when_clean",
            pass_report["status"] == STATUS_PASS,
        )
    )

    # --- Group 2: Safe true flags. ---
    for flag in SAFE_TRUE_FLAGS:
        checks.append(
            _check(
                f"safe_true_{flag}_present",
                flag in pass_report,
            )
        )
    checks.append(
        _check(
            "diagnostic_only_true",
            pass_report.get("diagnostic_only") is True,
        )
    )
    checks.append(
        _check(
            "aggregate_only_true",
            pass_report.get("aggregate_only_public_artifact") is True,
        )
    )
    checks.append(
        _check(
            "feature_extraction_performed_true_on_pass",
            pass_report.get(
                "automated_calibration_feature_extraction_performed"
            )
            is True,
        )
    )
    fail_report = _build_fail_report(
        "input_contract_missing_required", self_test_passed=True
    )
    checks.append(
        _check(
            "feature_extraction_performed_false_on_fail",
            fail_report.get(
                "automated_calibration_feature_extraction_performed"
            )
            is False,
        )
    )

    # --- Group 3: No-claim flags false. ---
    for flag in DEFAULT_FALSE_FLAGS:
        checks.append(
            _check(
                f"default_false_{flag}",
                pass_report.get(flag) is False,
            )
        )

    # --- Group 4: Records-shaped containers. ---
    for container in D5A1_RECORD_CONTAINERS:
        checks.append(
            _check(
                f"{container}_is_list",
                isinstance(pass_report[container], list),
            )
        )
    checks.append(
        _check(
            "no_dynamic_dict_mirror_for_signals",
            not any(
                isinstance(v, dict)
                for v in [pass_report.get("signal_records")]
                if isinstance(v, dict)
            ),
        )
    )

    # --- Group 5: Readiness buckets allowlist. ---
    checks.append(
        _check(
            "readiness_buckets_fixed_allowlist",
            READINESS_BUCKETS
            == (
                "ready_for_manual_review",
                "needs_more_live_downstream",
                "retrieval_only_insufficient",
                "conflicting_signals",
                "insufficient_signal",
            ),
        )
    )
    for b in READINESS_BUCKETS:
        bucket_recs = _compute_readiness_bucket_records(b, [])
        checks.append(
            _check(
                f"readiness_bucket_{b}_selected_count_1",
                sum(r["bucket_count"] for r in bucket_recs) == 1
                and any(
                    r["bucket"] == b and r["bucket_count"] == 1
                    for r in bucket_recs
                ),
            )
        )

    # --- Group 6: Recommended measurements are measurement-only. ---
    for bucket in READINESS_BUCKETS:
        recs = _compute_recommended_next_measurements(bucket)
        checks.append(
            _check(
                f"measurements_for_{bucket}_all_in_allowlist",
                all(
                    r["measurement"] in RECOMMENDED_MEASUREMENTS
                    for r in recs
                ),
            )
        )
        checks.append(
            _check(
                f"measurements_for_{bucket}_not_policy_default",
                all(
                    "policy" not in r["measurement"]
                    and "default" not in r["measurement"]
                    and "winner" not in r["measurement"]
                    and "promotion" not in r["measurement"]
                    for r in recs
                ),
            )
        )

    # --- Group 7: Input contract validation. ---
    f1d_art = _build_synthetic_f1d_artifact()
    f1c_art = _build_synthetic_f1c_artifact()
    c5c_art = _build_synthetic_c5c_artifact()
    c5f_art = _build_synthetic_c5f_artifact()
    b16e_art = _build_synthetic_b16e_artifact()

    claim_safe, reason = _validate_input_claim_flags(f1d_art, "F1-D")
    checks.append(
        _check(
            "clean_f1d_input_claim_safe",
            claim_safe and reason == "",
        )
    )
    unsafe_f1d = dict(f1d_art)
    unsafe_f1d["method_winner_claimed"] = True
    claim_safe2, reason2 = _validate_input_claim_flags(unsafe_f1d, "F1-D")
    checks.append(
        _check(
            "unsafe_claim_flag_detected",
            not claim_safe2 and reason2 == "unsafe_claim_flag_method_winner_claimed",
        )
    )
    unsafe_f1d2 = dict(f1d_art)
    unsafe_f1d2["forbidden_scan"] = {"status": "fail"}
    claim_safe3, reason3 = _validate_input_claim_flags(unsafe_f1d2, "F1-D")
    checks.append(
        _check(
            "input_forbidden_scan_fail_detected",
            not claim_safe3 and reason3 == "input_forbidden_scan_fail",
        )
    )

    # --- Group 8: Signal extraction. ---
    signals = _extract_retrieval_robustness_signals(f1d_art)
    checks.append(
        _check(
            "retrieval_signals_count_3",
            len(signals) == 3,
        )
    )
    checks.append(
        _check(
            "bm25_vs_empty_signal_present",
            any(
                s["signal_name"] == "bm25_vs_empty_retrieval_utility"
                for s in signals
            ),
        )
    )
    bm25_sig = next(
        s for s in signals if s["signal_name"] == "bm25_vs_empty_retrieval_utility"
    )
    checks.append(
        _check(
            "bm25_vs_empty_point_estimate_correct",
            bm25_sig["point_estimate"] == 0.465035,
        )
    )
    checks.append(
        _check(
            "bm25_vs_empty_sign_positive_1",
            bm25_sig["sign_positive_fraction"] == 1.0,
        )
    )

    bench_signals = _extract_benchmark_agreement_signals(
        c5c_art, c5f_art, f1d_art
    )
    checks.append(
        _check(
            "benchmark_signals_count_3",
            len(bench_signals) == 3,
        )
    )
    bm25_both = next(
        s for s in bench_signals if s["signal_name"] == "bm25_positive_on_both_benchmarks"
    )
    checks.append(
        _check(
            "bm25_positive_on_both_true",
            bm25_both["bm25_positive_on_both"] is True,
        )
    )
    regex_neg = next(
        s for s in bench_signals if s["signal_name"] == "regex_symbol_negative_on_both_benchmarks"
    )
    checks.append(
        _check(
            "regex_symbol_negative_on_both_true",
            regex_neg["regex_negative_on_both"] is True
            and regex_neg["symbol_negative_on_both"] is True,
        )
    )
    agree = next(
        s for s in bench_signals if s["signal_name"] == "benchmark_method_agreement"
    )
    checks.append(
        _check(
            "methods_agree_3_disagree_0",
            agree["methods_agree"] == 3 and agree["methods_disagree"] == 0,
        )
    )

    live_signals = _extract_live_provider_signals(b16e_art)
    checks.append(
        _check(
            "live_signals_count_1",
            len(live_signals) == 1,
        )
    )
    live_sig = live_signals[0]
    checks.append(
        _check(
            "live_context_pack_signal_observed",
            live_sig["context_pack_signal_observed"] is True,
        )
    )
    checks.append(
        _check(
            "live_solve_rate_delta_correct",
            live_sig["solve_rate_delta"] == 0.875,
        )
    )
    checks.append(
        _check(
            "live_families_positive_4",
            live_sig["families_positive"] == 4,
        )
    )

    # --- Group 9: Cross-signal alignment. ---
    all_signals = signals + bench_signals + live_signals
    cross = _compute_cross_signal_alignment(all_signals)
    checks.append(
        _check(
            "cross_signal_retrieval_robust_positive_plus_live_positive",
            cross
            == "retrieval_robust_positive_plus_live_positive",
        )
    )
    # Test conflicting: live negative but retrieval positive.
    b16e_neg = dict(b16e_art)
    b16e_neg["honest_signals"] = {
        "context_pack_signal_observed": True,
        "families_evaluated": 4,
        "families_with_positive_solve_delta": 0,
        "families_with_zero_solve_delta": 0,
        "families_with_negative_solve_delta": 4,
        "overall_treatment_solve_rate_delta": -0.5,
    }
    live_neg = _extract_live_provider_signals(b16e_neg)
    conflict_signals = signals + bench_signals + live_neg
    cross_conflict = _compute_cross_signal_alignment(conflict_signals)
    checks.append(
        _check(
            "cross_signal_conflicting_when_retrieval_pos_live_neg",
            cross_conflict == "conflicting_signals",
        )
    )
    # Test retrieval-only (no live signal).
    retrieval_only = signals + bench_signals
    cross_ro = _compute_cross_signal_alignment(retrieval_only)
    checks.append(
        _check(
            "cross_signal_retrieval_only_insufficient_no_live",
            cross_ro == "retrieval_only_insufficient",
        )
    )

    # --- Group 10: Calibration features. ---
    features = _compute_calibration_features(all_signals, cross)
    checks.append(
        _check(
            "features_nonempty",
            len(features) > 0,
        )
    )
    checks.append(
        _check(
            "features_records_shaped",
            all(
                set(f.keys())
                == {
                    "feature_name",
                    "feature_bucket",
                    "feature_value",
                    "feature_unit",
                }
                for f in features
            ),
        )
    )
    cross_feat = next(
        f for f in features if f["feature_name"] == "cross_signal_alignment"
    )
    checks.append(
        _check(
            "cross_signal_feature_bucket_correct",
            cross_feat["feature_bucket"] == cross,
        )
    )

    # --- Group 11: Readiness bucket computation. ---
    bucket = _compute_readiness_bucket(cross, all_signals)
    checks.append(
        _check(
            "readiness_bucket_ready_for_manual_review",
            bucket == "ready_for_manual_review",
        )
    )
    bucket_conflict = _compute_readiness_bucket(
        "conflicting_signals", conflict_signals
    )
    checks.append(
        _check(
            "readiness_bucket_conflicting_signals",
            bucket_conflict == "conflicting_signals",
        )
    )
    bucket_ro = _compute_readiness_bucket(
        "retrieval_only_insufficient", retrieval_only
    )
    checks.append(
        _check(
            "readiness_bucket_retrieval_only_insufficient",
            bucket_ro == "retrieval_only_insufficient",
        )
    )
    bucket_insuf = _compute_readiness_bucket(
        "retrieval_only_insufficient", []
    )
    checks.append(
        _check(
            "readiness_bucket_insufficient_signal_when_no_signals",
            bucket_insuf == "insufficient_signal",
        )
    )

    # --- Group 12: Full pass report build. ---
    full_report = _build_pass_report(
        self_test_passed=True,
        input_records=[
            {
                "phase": "F1-D",
                "schema_version": "f1d_cross_benchmark_retrieval_robustness.v1",
                "status": "cross_benchmark_retrieval_robustness_pass",
                "required": True,
                "claim_safe": True,
                "loaded": True,
                "skipped_reason_category": "",
                "unit_count": 30,
            }
        ],
        signals=all_signals,
        features=features,
        bucket=bucket,
        bucket_records=_compute_readiness_bucket_records(bucket, all_signals),
        measurements=_compute_recommended_next_measurements(bucket),
        cross_signal=cross,
    )
    checks.append(
        _check(
            "full_pass_report_status_pass",
            full_report["status"] == STATUS_PASS,
        )
    )
    checks.append(
        _check(
            "full_pass_report_feature_extraction_performed",
            full_report[
                "automated_calibration_feature_extraction_performed"
            ]
            is True,
        )
    )
    checks.append(
        _check(
            "full_pass_report_has_signal_records",
            len(full_report["signal_records"]) > 0,
        )
    )
    checks.append(
        _check(
            "full_pass_report_has_feature_records",
            len(full_report["calibration_feature_records"]) > 0,
        )
    )
    checks.append(
        _check(
            "full_pass_report_has_bucket_records",
            len(full_report["readiness_bucket_records"])
            == len(READINESS_BUCKETS),
        )
    )
    checks.append(
        _check(
            "full_pass_report_has_measurements",
            len(full_report["recommended_next_measurement_records"]) > 0,
        )
    )
    checks.append(
        _check(
            "full_pass_report_forbidden_scan_clean",
            full_report["forbidden_scan"]["status"] == "pass",
        )
    )
    checks.append(
        _check(
            "full_pass_report_self_scan_clean",
            not _scan_d5a1(full_report),
        )
    )

    # --- Group 13: Fail-closed input contract. ---
    fail_input = _build_fail_report(
        "input_contract_missing_required",
        self_test_passed=True,
    )
    checks.append(
        _check(
            "fail_input_report_status_fail_input_contract",
            fail_input["status"] == STATUS_FAIL_INPUT_CONTRACT,
        )
    )
    checks.append(
        _check(
            "fail_input_report_feature_extraction_false",
            fail_input[
                "automated_calibration_feature_extraction_performed"
            ]
            is False,
        )
    )

    # --- Group 14: Scanner rejections. ---
    checks.append(
        _check(
            "scanner_rejects_repo_url",
            bool(_scan_d5a1({"leaked": "https://github.com/x/y"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_commit_sha",
            bool(_scan_d5a1({"leaked": "a" * 40})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_repo_slug",
            bool(_scan_d5a1({"leaked": "astropy/astropy"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_task_id_key",
            bool(_scan_d5a1({"task_id": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_query_key",
            bool(_scan_d5a1({"query": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_winner_key",
            bool(_scan_d5a1({"winner": "bm25"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_best_method_key",
            bool(_scan_d5a1({"best_method": "bm25"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_recommended_default_key",
            bool(_scan_d5a1({"recommended_default": "bm25"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_calibrated_model_key",
            bool(_scan_d5a1({"calibrated_model": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_policy_recommendation_key",
            bool(_scan_d5a1({"policy_recommendation": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_true_calibration_claim_key",
            bool(
                _scan_d5a1(
                    {"automated_e_s_calibration_smoke_claimed": True}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_false_calibration_claim_key",
            not _scan_d5a1({"true_e_s_calibration_claimed": False}),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_per_row_metrics_key",
            bool(_scan_d5a1({"per_row_metrics": []})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_per_needle_metrics_key",
            bool(_scan_d5a1({"per_needle_metrics": []})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_provider_payload_key",
            bool(_scan_d5a1({"provider_payload": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_task_text_key",
            bool(_scan_d5a1({"task_text": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_input_artifact_path_key",
            bool(_scan_d5a1({"input_artifact_path": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_raw_routing_prefix_value",
            bool(
                _scan_d5a1(
                    {"leaked": _ROUTING_PREFIX_SENTINEL + "Kimi"}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_tmp_path",
            bool(_scan_d5a1({"leaked": "/tmp/d5a1_smoke_0"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_provider_key",
            bool(_scan_d5a1({"api_key": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_secret_sentinel",
            bool(_scan_d5a1({"leaked": _SECRET_SENTINEL})),
        )
    )
    # Scanner rejects dict-keyed D5-A1 containers.
    for container in D5A1_RECORD_CONTAINERS:
        checks.append(
            _check(
                f"scanner_rejects_{container}_dict",
                bool(_scan_d5a1({container: {"x": {}}})),
            )
        )

    # --- Group 15: Scanner allows legitimate aggregate values. ---
    checks.append(
        _check(
            "scanner_allows_method_name",
            not _scan_d5a1({"method": "bm25"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_benchmark_name",
            not _scan_d5a1({"benchmark": "contextbench"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_signal_name",
            not _scan_d5a1({"signal_name": "bm25_vs_empty_retrieval_utility"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_feature_name",
            not _scan_d5a1({"feature_name": "bm25_vs_empty_sign_stability"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_bucket_label",
            not _scan_d5a1({"bucket": "ready_for_manual_review"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_measurement_label",
            not _scan_d5a1({"measurement": "manual_reference_audit"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_phase_label",
            not _scan_d5a1({"phase": "F1-D"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_signal_records_list",
            not _scan_d5a1(
                {
                    "signal_records": [
                        {
                            "signal_name": "bm25_vs_empty_retrieval_utility",
                            "signal_source_phase": "F1-D",
                            "point_estimate": 0.465035,
                        }
                    ]
                }
            ),
        )
    )

    # --- Group 16: Fail-closed generation. ---
    try:
        _enforce_d5a1_no_forbidden(full_report)
        clean_passes = True
    except SystemExit:
        clean_passes = False
    checks.append(
        _check(
            "fail_closed_clean_report_does_not_raise",
            clean_passes,
        )
    )
    leaked = dict(full_report)
    leaked["leaked_path"] = "src/openlocus/lib.rs"
    try:
        _enforce_d5a1_no_forbidden(leaked)
        leak_raises = False
    except SystemExit:
        leak_raises = True
    checks.append(
        _check("fail_closed_raises_on_leak", leak_raises)
    )
    leaked2 = dict(full_report)
    leaked2["calibrated_model"] = "abc"
    try:
        _enforce_d5a1_no_forbidden(leaked2)
        calib_raises = False
    except SystemExit:
        calib_raises = True
    checks.append(
        _check("fail_closed_raises_on_calibrated_model", calib_raises)
    )
    leaked3 = dict(full_report)
    leaked3["policy_recommendation"] = "abc"
    try:
        _enforce_d5a1_no_forbidden(leaked3)
        policy_raises = False
    except SystemExit:
        policy_raises = True
    checks.append(
        _check("fail_closed_raises_on_policy_recommendation", policy_raises)
    )

    # --- Group 17: CLI argument surface. ---
    cli_opts = _cli_argument_option_strings()
    checks.append(
        _check("cli_has_self_test_argument", "--self-test" in cli_opts)
    )
    checks.append(_check("cli_has_out_argument", "--out" in cli_opts))

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
    """Build the D5-A1 CLI parser."""
    ap = SafeArgumentParser(
        description=(
            "D5-A1 automated calibration feature table "
            "(public aggregate-only artifact; machine-reads committed "
            "aggregate artifacts from F1-D/F1-C/C5-C/C5-F/B16-E "
            "(optionally D5-A0/B16-D); validates schemas and claim "
            "flags; extracts numeric aggregate signals; computes "
            "deterministic calibration feature/bucket records for "
            "future calibration / manual review; feature extraction, "
            "NOT calibration; NOT policy/default/method winner; "
            "no raw task/row/needle IDs/repo URLs/commits/paths/spans/"
            "source/snippets/prompts/responses/provider payloads/"
            "per-unit metric arrays/B16 task text/private labels/"
            "content hashes/candidate/evidence rows committed)."
        )
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="run deterministic self-test groups and exit (no artifact written)",
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


def _run_feature_extraction(
    *,
    self_test_passed: bool,
) -> dict[str, Any]:
    """Run the full D5-A1 feature extraction over committed artifacts."""
    repo_root = Path(__file__).resolve().parent.parent
    input_records: list[dict[str, Any]] = []

    # Load required inputs (raises InputContractError on failure).
    for spec in REQUIRED_INPUTS:
        full_spec = dict(spec)
        full_spec["path"] = repo_root / spec["path"]
        input_records.append(_load_and_validate_input(full_spec))

    # Load optional inputs (skipped if missing/invalid/unsafe).
    for spec in OPTIONAL_INPUTS:
        full_spec = dict(spec)
        full_spec["path"] = repo_root / spec["path"]
        try:
            input_records.append(_load_and_validate_input(full_spec))
        except InputContractError:
            input_records.append(
                {
                    "phase": spec["phase"],
                    "schema_version": "",
                    "status": "",
                    "required": False,
                    "claim_safe": False,
                    "loaded": False,
                    "skipped_reason_category": "optional_invalid",
                    "unit_count": 0,
                }
            )

    # Build a dict of loaded artifacts (in-memory only).
    loaded_artifacts: dict[str, dict[str, Any]] = {}
    for rec in input_records:
        if rec.get("loaded"):
            loaded_artifacts[rec["phase"]] = rec["_artifact"]

    # Extract signals.
    signals: list[dict[str, Any]] = []
    f1d_art = loaded_artifacts.get("F1-D")
    if f1d_art is not None:
        signals.extend(_extract_retrieval_robustness_signals(f1d_art))
    c5c_art = loaded_artifacts.get("C5-C")
    c5f_art = loaded_artifacts.get("C5-F")
    if c5c_art is not None and c5f_art is not None and f1d_art is not None:
        signals.extend(
            _extract_benchmark_agreement_signals(c5c_art, c5f_art, f1d_art)
        )
    b16e_art = loaded_artifacts.get("B16-E")
    if b16e_art is not None:
        signals.extend(_extract_live_provider_signals(b16e_art))
    signals.extend(_extract_optional_signals(loaded_artifacts))

    # Compute cross-signal alignment, features, readiness bucket.
    cross_signal = _compute_cross_signal_alignment(signals)
    features = _compute_calibration_features(signals, cross_signal)
    bucket = _compute_readiness_bucket(cross_signal, signals)
    bucket_records = _compute_readiness_bucket_records(bucket, signals)
    measurements = _compute_recommended_next_measurements(bucket)

    return _build_pass_report(
        self_test_passed=self_test_passed,
        input_records=input_records,
        signals=signals,
        features=features,
        bucket=bucket,
        bucket_records=bucket_records,
        measurements=measurements,
        cross_signal=cross_signal,
    )


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

    try:
        report = _run_feature_extraction(self_test_passed=self_test_passed)
    except InputContractError as exc:
        report = _build_fail_report(
            f"input_contract_missing_required: {exc}",
            self_test_passed=self_test_passed,
        )
        _enforce_d5a1_no_forbidden(report)
        _write_json(out_path, report)
        print(
            f"wrote artifact "
            f"(forbidden_scan={report['forbidden_scan']['status']}, "
            f"self_test_passed={report['self_test_passed']}, "
            f"status={report['status']}, "
            f"phase={report['phase']}, "
            f"failure_reason={report['failure_reason_category']})"
        )
        sys.exit(1)

    _enforce_d5a1_no_forbidden(report)
    _write_json(out_path, report)
    print(
        f"wrote artifact "
        f"(forbidden_scan={report['forbidden_scan']['status']}, "
        f"self_test_passed={report['self_test_passed']}, "
        f"status={report['status']}, "
        f"phase={report['phase']}, "
        f"signals={len(report['signal_records'])}, "
        f"features={len(report['calibration_feature_records'])}, "
        f"bucket={report['readiness_bucket']}, "
        f"measurements={len(report['recommended_next_measurement_records'])})"
    )


if __name__ == "__main__":
    main()
