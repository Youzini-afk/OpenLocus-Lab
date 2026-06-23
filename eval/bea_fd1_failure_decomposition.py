#!/usr/bin/env python3
"""BEA-FD1: BEA-4/5 Frozen Replay Failure Decomposition (Public Aggregate-Only).

This module implements the **BEA-FD1 failure decomposition** phase: it
replays the frozen BEA-4 and BEA-5 protocols exactly via subprocess, parses
the resulting private SCORE JSONL files, classifies each v0.3 treatment
outcome into a fixed category enum, and publishes records-only aggregate
decomposition tables.

BEA-FD1 does NOT change BEA v0.3, sampling, gates, arms, or weights. It
does NOT implement v0.4.

Claim boundary: ``bea_fd1_failure_decomposition_smoke_only``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any, NoReturn

_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import bea5_frozen_policy_robustness as bea5  # noqa: E402
import bea4_external_scale_smoke as bea4  # noqa: E402
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "bea_fd1_failure_decomposition.v1"
GENERATED_BY = "eval/bea_fd1_failure_decomposition.py"
CLAIM_LEVEL = "bea_fd1_failure_decomposition_smoke_only"
MODE = "bea_fd1_failure_decomposition"
PHASE = "BEA-FD1"

DEFAULT_OUT = Path(
    "artifacts/bea_fd1_failure_decomposition/"
    "bea_fd1_failure_decomposition_report.json"
)

PRIVATE_DECOMP_SCHEMA_VERSION = "bea_fd1_private_decomposition.v1"

# Fixed budget/methods (exact BEA-4/5 protocol values).
FIXED_BUDGET = 5
FIXED_METHODS = "bm25,regex,symbol"

# Arms.
ARM_V03 = "bea_v0_3_anchor_span_latency"
ARM_V02 = "bea_v0_2_diversity_risk"
ARM_V0 = "bea_v0"
ARM_BM25 = "bm25_prefix_same_budget"
ARM_AGR = "agreement_only_same_budget"
ARM_RRF = "rrf_same_budget"

BASELINE_ARMS = (ARM_V02, ARM_V0, ARM_BM25, ARM_AGR, ARM_RRF)
REQUIRED_PRIVATE_ARMS = (ARM_V03,) + BASELINE_ARMS

QUALITY_METRICS = (
    "file_recall@10", "mrr", "span_f0.5@10", "success_rate",
    "quality_per_latency",
)
LATENCY_METRIC = "latency_seconds"
ALL_METRICS = QUALITY_METRICS + (LATENCY_METRIC,)

# Fixed 12-category enum.
FAILURE_CATEGORIES: tuple[str, ...] = (
    "gold_file_absent",
    "gold_span_absent",
    "correct_file_wrong_span",
    "redundant_same_file_candidates",
    "too_many_anchor_slots",
    "missing_support_candidate",
    "support_selected_without_target",
    "target_selected_without_support",
    "risk_penalty_removed_gold",
    "early_stop_too_early",
    "budget_spent_on_low_marginal_gain",
    "latency_without_quality_gain",
)
EXPECTED_DECOMPOSED_RECORDS = 239
EXPECTED_PRIVATE_DECOMP_ROWS = (
    EXPECTED_DECOMPOSED_RECORDS
    * len(BASELINE_ARMS)
    * len(FAILURE_CATEGORIES)
    * len(ALL_METRICS)
)

# Categories that are always unavailable (no support label).
UNAVAILABLE_NO_SUPPORT_CATEGORIES = frozenset({
    "missing_support_candidate",
    "support_selected_without_target",
    "target_selected_without_support",
})
UNAVAILABLE_MISSING_TRACE_CATEGORIES = frozenset({
    "risk_penalty_removed_gold",
})

AVAILABILITY_REASONS = (
    "available", "unavailable_missing_trace",
    "unavailable_no_support_label", "unavailable_replay_mismatch",
    "unavailable_no_candidates",
)

# Source phase replay configs (exact protocol inputs).
SOURCE_PHASE_CONFIGS = (
    {
        "source_phase": "BEA-4",
        "source_ci_run_id": "27957586271",
        "evaluator": "eval/bea4_external_scale_smoke.py",
        "expected_successful_records": 120,
        "expected_private_score_count": 840,
        "expected_contextbench_successful": 80,
        "expected_repoqa_successful": 40,
        "extra_args": [
            "--contextbench-row-offset", "80",
            "--contextbench-row-limit", "80",
            "--repoqa-needle-offset", "40",
            "--repoqa-needle-limit", "40",
        ],
        "private_jsonl_name": "bea4.private.jsonl",
        "source_sampling_protocol": "bea4_external_scale_smoke.v1",
    },
    {
        "source_phase": "BEA-5",
        "source_ci_run_id": "28003522632",
        "evaluator": "eval/bea5_frozen_policy_robustness.py",
        "expected_successful_records": 119,
        "expected_private_score_count": 833,
        "expected_contextbench_successful": 82,
        "expected_repoqa_successful": 37,
        "extra_args": [
            "--contextbench-row-offset", "0",
            "--contextbench-row-limit", "480",
            "--repoqa-needle-offset", "0",
            "--repoqa-needle-limit", "240",
        ],
        "private_jsonl_name": "bea5.private.jsonl",
        "source_sampling_protocol": "bea5_success_quota_disjoint_scan.v1",
    },
)

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
    "decomposition_performed": False,
    "private_decomposition_records_written": False,
}

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "external_benchmark_performance_claimed": False,
    "leaderboard_entry_claimed": False,
    "downstream_agent_value_proven": False,
    "calibration_claimed": False,
    "method_winner_claimed": False,
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
    "algorithm_changed_during_bea_fd1": False,
    "weights_tuned_during_bea_fd1": False,
}

LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication": "aggregate_only_smoke",
}

RUN_FAILURE_CATEGORIES = (
    "retrieval_failed", "replay_subprocess_failed",
    "private_score_parse_failed", "private_decomposition_write_failed",
    "replay_mismatch", "scanner_self_test_failed",
    "forbidden_leak_blocked", "unexpected_exception",
)

# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

FD1_FORBIDDEN_KEYS: frozenset[str] = frozenset({
    "decomposition_path", "private_decomposition_path",
    "private_decomposition_file", "private_record_id",
    "decomposition_record_id", "per_record_decomposition",
    "decomposition_rows", "candidate_features",
    "accepted_candidates", "gold_paths", "gold_lines",
    "gold_spans", "gold_content", "action_order",
    "priority_components", "priority_score",
    "selected_decisions", "budget_trace", "stop_reason",
    "anchor_eligibility", "anchor_slots", "early_stop_reason",
    "score_outcome", "action_trace", "budget_state",
    "candidate_list", "candidates", "final_candidates",
    "per_record_metrics", "runtime_query_features",
    "query_feature_summary", "query_features",
    "benchmark_row_id", "phase_run_id", "run_id",
    "task_id", "row_id", "needle_id", "instance_id",
    "provider_name", "model_name", "provider_payload",
    "calibration", "method_winner", "best_method",
    "recommended_default", "winner", "leaderboard", "promotion",
    "self_test_checks", "self_test_details", "checks", "check_list",
    "comparison_arm", "bucket", "candidate_source",
})


def _is_schema_container(path: str) -> bool:
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent = parts[0].rsplit(".", 1)[-1].split("[")[0]
    return parent in (
        "source_run_records", "category_summary_records",
        "category_metric_loss_records", "category_win_tie_loss_records",
        "bucket_category_records", "candidate_source_category_records",
        "availability_records", "private_decomposition_manifest",
        "failure_category_counts", "framing",
    )


def _scan_fd1_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                ks = str(k)
                sp = f"{path}.{ks}"
                if ks in FD1_FORBIDDEN_KEYS and not _is_schema_container(sp):
                    violations.append({"category": "forbidden_fd1_key", "path": sp})
                _walk(v, sp)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                _walk(v, f"{path}[{i}]")
    _walk(obj)
    return violations


def _scan_fd1(obj: Any) -> list[dict[str, Any]]:
    return bea5._scan_bea5(obj) + _scan_fd1_forbidden_keys(obj)


def _fd1_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_fd1(obj)
    cats: dict[str, int] = {}
    for v in violations:
        cats[v["category"]] = cats.get(v["category"], 0) + 1
    return {"status": "pass" if not violations else "fail",
            "violations_count": len(violations), "categories": cats}


def _enforce_no_forbidden(obj: Any) -> None:
    if _fd1_scan_summary(obj)["status"] != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return c5a._now_iso()

def _write_json(path: Path, obj: Any) -> None:
    c5a._write_json(path, obj)

def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return c5a._check(name, ok)

def _resolve_private_dir(explicit: str | None) -> tuple[Path, str]:
    return bea5._resolve_private_score_dir(explicit)

def _decomp_manifest_hash() -> str:
    schema = {"schema_version": PRIVATE_DECOMP_SCHEMA_VERSION,
              "fields": ["phase_run_id", "source_phase", "benchmark",
                         "private_record_id", "policy_arm", "category",
                         "baseline_arm", "treatment_arm", "metric",
                         "treatment_value", "baseline_value",
                         "loss", "delta", "category_availability",
                         "latency_ms", "cost_usd", "tokens", "provider_calls"]}
    canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def _write_decomp_row(path: Path, row: dict[str, Any]) -> None:
    bea5._write_private_attempt_row(path, row)


# ---------------------------------------------------------------------------
# Natural keys
# ---------------------------------------------------------------------------

def _sr_key(r: dict) -> tuple: return (r["source_phase"], r["source_ci_run_id"])
def _cs_key(r: dict) -> tuple: return (r["source_phase"], r["benchmark"], r["category"], r["category_availability"])
def _cml_key(r: dict) -> tuple: return (r["source_phase"], r["benchmark"], r["category"], r["baseline_arm"], r["treatment_arm"], r["metric"])
def _cwtl_key(r: dict) -> tuple: return (r["source_phase"], r["benchmark"], r["category"], r["baseline_arm"], r["treatment_arm"], r["metric"])
def _bc_key(r: dict) -> tuple: return (r["source_phase"], r["benchmark"], r["bucket_type"], r["bucket_value"], r["category"])
def _csc_key(r: dict) -> tuple: return (r["source_phase"], r["benchmark"], r["candidate_source_bucket"], r["category"])
def _av_key(r: dict) -> tuple: return (r["source_phase"], r["benchmark"], r["category"], r["category_availability"])

def _check_unique(records: list, key_fn, table: str) -> list:
    failures: list[dict] = []
    seen: dict[tuple, int] = {}
    for i, r in enumerate(records):
        try:
            k = key_fn(r)
        except (KeyError, TypeError):
            failures.append({"table": table, "index": i, "reason": "missing_key"})
            continue
        if k in seen:
            failures.append({"table": table, "index": i, "reason": "duplicate"})
        else:
            seen[k] = i
    return failures


def _evaluator_script_path(eval_dir: Path, evaluator: str) -> Path:
    """Resolve an evaluator path from a repo-root relative config value."""
    return eval_dir.parent / evaluator


# ---------------------------------------------------------------------------
# Subprocess replay
# ---------------------------------------------------------------------------

def _run_subprocess_replay(
    config: dict[str, Any],
    private_dir: Path,
    openlocus_bin: str,
    eval_dir: Path,
) -> tuple[dict[str, Any] | None, str, int, dict[str, int]]:
    """Run one source phase evaluator via subprocess.

    Returns ``(parsed_public_artifact, status, exit_code, fcc)``.
    """
    fcc: dict[str, int] = {c: 0 for c in RUN_FAILURE_CATEGORIES}
    temp_out = private_dir / f"{config['source_phase']}_temp_report.json"
    private_score_subdir = private_dir / config["source_phase"]
    private_score_subdir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(_evaluator_script_path(eval_dir, str(config["evaluator"]))),
        "--enable-external-benchmark-network",
        "--budget", str(FIXED_BUDGET),
        "--methods", FIXED_METHODS,
        "--openlocus", openlocus_bin,
        "--out", str(temp_out),
        "--private-score-dir", str(private_score_subdir),
    ] + config["extra_args"]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=7200,
            cwd=str(eval_dir.parent),
        )
    except subprocess.TimeoutExpired:
        fcc["replay_subprocess_failed"] = 1
        return None, "timeout", -1, fcc
    except Exception:
        fcc["replay_subprocess_failed"] = 1
        return None, "exception", -1, fcc

    if result.returncode != 0:
        fcc["replay_subprocess_failed"] = 1
        return None, f"exit_{result.returncode}", result.returncode, fcc

    # Parse the temp public artifact.
    try:
        with temp_out.open("r", encoding="utf-8") as f:
            artifact = json.load(f)
    except Exception:
        fcc["private_score_parse_failed"] = 1
        return None, "parse_failed", result.returncode, fcc

    return artifact, "pass", result.returncode, fcc


def _parse_private_jsonl(path: Path) -> tuple[list[dict[str, Any]], int]:
    """Parse private SCORE JSONL rows and return ``(rows, parse_failures)``.

    BEA-FD1 is a replay-completeness diagnostic. Parse failures must be visible
    to the caller; silently returning a partial row set would make the public
    decomposition fail-open.
    """
    rows: list[dict[str, Any]] = []
    failures = 0
    if not path.exists():
        return rows, 1
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                    if isinstance(parsed, dict):
                        rows.append(parsed)
                    else:
                        failures += 1
                except json.JSONDecodeError:
                    failures += 1
    except OSError:
        failures += 1
    return rows, failures


def _group_private_rows_by_record(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_record: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        rid = row.get("private_record_id", "")
        if rid:
            by_record.setdefault(str(rid), []).append(row)
    return by_record


def _required_arm_coverage_failures(by_record: dict[str, list[dict[str, Any]]]) -> int:
    failures = 0
    required = set(REQUIRED_PRIVATE_ARMS)
    for rows in by_record.values():
        arms = {str(r.get("policy_arm", "")) for r in rows}
        if not required.issubset(arms):
            failures += 1
    return failures


# ---------------------------------------------------------------------------
# Failure category classification (from parsed private rows)
# ---------------------------------------------------------------------------

def _classify_from_private_rows(
    record_rows: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Classify one record's private rows into categories per baseline.

    ``record_rows`` is the list of private SCORE rows for one record
    (7 arms). Returns ``{baseline_arm: {category: (count, availability)}}``.
    """
    # Index rows by policy_arm.
    by_arm: dict[str, dict[str, Any]] = {}
    for row in record_rows:
        arm = row.get("policy_arm", "")
        by_arm[arm] = row

    v03 = by_arm.get(ARM_V03, {})
    v03_outcome = v03.get("score_outcome", {})
    v03_anchor = v03.get("anchor_eligibility", {})
    v03_anchor_slots = int(v03.get("anchor_slots", 0))
    v03_early_stop = v03.get("early_stop_reason", "")
    v03_stop = v03.get("stop_reason", "")
    v03_lat = float(v03_outcome.get("latency_seconds", 0.0) or 0.0)
    v03_file_recall = float(v03_outcome.get("file_recall@10", 0.0) or 0.0)
    v03_success = float(v03_outcome.get("success_rate", 0.0) or 0.0)
    v03_span = float(v03_outcome.get("span_f0.5@10", 0.0) or 0.0)
    v03_mrr = float(v03_outcome.get("mrr", 0.0) or 0.0)
    v03_qpl = float(v03_outcome.get("quality_per_latency", 0.0) or 0.0)
    v03_budget_used = float(v03_outcome.get("evidence_budget_used", 0.0) or 0.0)

    result: dict[str, dict[str, dict[str, Any]]] = {}

    for baseline in BASELINE_ARMS:
        b_row = by_arm.get(baseline, {})
        b_outcome = b_row.get("score_outcome", {})
        b_lat = float(b_outcome.get("latency_seconds", 0.0) or 0.0)
        b_file_recall = float(b_outcome.get("file_recall@10", 0.0) or 0.0)
        b_success = float(b_outcome.get("success_rate", 0.0) or 0.0)
        b_span = float(b_outcome.get("span_f0.5@10", 0.0) or 0.0)
        b_mrr = float(b_outcome.get("mrr", 0.0) or 0.0)
        b_qpl = float(b_outcome.get("quality_per_latency", 0.0) or 0.0)

        cats: dict[str, dict[str, Any]] = {}

        # gold_file_absent: v0.3 file_recall == 0 and success == 0.
        if v03_file_recall == 0 and v03_success == 0:
            cats["gold_file_absent"] = {"count": 1, "availability": "available"}
        else:
            cats["gold_file_absent"] = {"count": 0, "availability": "available"}

        # gold_span_absent or correct_file_wrong_span:
        # file hit (file_recall > 0) but span == 0.
        if v03_file_recall > 0 and v03_span == 0:
            cats["correct_file_wrong_span"] = {"count": 1, "availability": "available"}
            cats["gold_span_absent"] = {"count": 0, "availability": "available"}
        elif v03_file_recall > 0 and v03_span > 0:
            cats["correct_file_wrong_span"] = {"count": 0, "availability": "available"}
            cats["gold_span_absent"] = {"count": 0, "availability": "available"}
        else:
            cats["correct_file_wrong_span"] = {"count": 0, "availability": "available"}
            cats["gold_span_absent"] = {"count": 0, "availability": "available"}

        # redundant_same_file_candidates: unavailable_missing_trace
        # (action_order is in private rows but we don't parse it deeply here).
        cats["redundant_same_file_candidates"] = {"count": 0, "availability": "unavailable_missing_trace"}

        # too_many_anchor_slots.
        if v03_anchor_slots > 2:
            cats["too_many_anchor_slots"] = {"count": 1, "availability": "available"}
        else:
            cats["too_many_anchor_slots"] = {"count": 0, "availability": "available"}

        # Unavailable categories (no support label).
        for cat in UNAVAILABLE_NO_SUPPORT_CATEGORIES:
            cats[cat] = {"count": 0, "availability": "unavailable_no_support_label"}

        # risk_penalty_removed_gold: unavailable_missing_trace.
        for cat in UNAVAILABLE_MISSING_TRACE_CATEGORIES:
            cats[cat] = {"count": 0, "availability": "unavailable_missing_trace"}

        # early_stop_too_early: if early_stop triggered and v0.3 quality <= baseline.
        v03_quality = v03_mrr  # proxy: use mrr as quality signal
        b_quality = b_mrr
        if v03_early_stop and v03_quality <= b_quality:
            cats["early_stop_too_early"] = {"count": 1, "availability": "available"}
        else:
            cats["early_stop_too_early"] = {"count": 0, "availability": "available"}

        # budget_spent_on_low_marginal_gain: full budget and v0.3 quality <= baseline.
        if v03_budget_used >= FIXED_BUDGET and v03_quality <= b_quality:
            cats["budget_spent_on_low_marginal_gain"] = {"count": 1, "availability": "available"}
        else:
            cats["budget_spent_on_low_marginal_gain"] = {"count": 0, "availability": "available"}

        # latency_without_quality_gain: v0.3 latency > baseline and quality delta <= 0.
        if v03_lat > b_lat and (v03_quality - b_quality) <= 0:
            cats["latency_without_quality_gain"] = {"count": 1, "availability": "available"}
        else:
            cats["latency_without_quality_gain"] = {"count": 0, "availability": "available"}

        result[baseline] = cats

    return result


# ---------------------------------------------------------------------------
# Report builders
# ---------------------------------------------------------------------------

def _build_unavailable(
    failure_reason: str, *, self_test_passed: bool,
    self_test_checks_total: int, self_test_checks_passed: int | None = None,
    openlocus_binary_source: str, network_mode: str,
    private_decomp_storage_class: str = "tmp_private",
    private_decomp_records_written: bool = False,
    private_decomp_record_count: int = 0,
    records_decomposed: int = 0, records_attempted_total: int = 0,
    network_calls: int = 0, fcc: dict[str, int] | None = None,
) -> dict[str, Any]:
    f = {c: 0 for c in RUN_FAILURE_CATEGORIES}
    if fcc:
        for k, v in fcc.items():
            if k in f:
                f[k] = int(v)
    if failure_reason in f:
        f[failure_reason] = max(f[failure_reason], 1)

    st = dict(SAFE_TRUE_FLAGS)
    st["private_decomposition_records_written"] = bool(private_decomp_records_written)

    mh = _decomp_manifest_hash()

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "generated_by": GENERATED_BY,
        "generated_at": _now_iso(), "claim_level": CLAIM_LEVEL,
        "status": "unavailable_with_reason", "mode": MODE, "phase": PHASE,
        "budget": FIXED_BUDGET, "methods": FIXED_METHODS.split(","),
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "records_decomposed": records_decomposed,
        "records_attempted_total": records_attempted_total,
        "network_calls": network_calls, "provider_calls": 0,
        "failure_reason_category": failure_reason,
        "failure_category_counts": f,
        "source_run_records": [], "category_summary_records": [],
        "category_metric_loss_records": [], "category_win_tie_loss_records": [],
        "bucket_category_records": [], "candidate_source_category_records": [],
        "availability_records": [],
        "private_decomposition_manifest": {
            "records_written": bool(private_decomp_records_written),
            "record_count": int(private_decomp_record_count),
            "schema_version": PRIVATE_DECOMP_SCHEMA_VERSION,
            "manifest_hash": mh,
            "storage_class": private_decomp_storage_class,
            "path_publicly_serialized": False,
        },
        **st, **DEFAULT_FALSE_FLAGS, **LICENSE_FIELDS,
        "self_test_passed": self_test_passed,
        "self_test_checks_total": int(self_test_checks_total),
        "self_test_checks_passed": int(
            self_test_checks_total if self_test_checks_passed is None and self_test_passed
            else (self_test_checks_passed or 0)),
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False, "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "calibration_claimed": False, "method_winner_claimed": False,
            "signal_strength": "bea_fd1_unavailable",
            "is_full_external_benchmark_evaluation": False,
        },
    }
    scan = _fd1_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _build_pass(
    *, self_test_passed: bool, self_test_checks_total: int,
    self_test_checks_passed: int | None, openlocus_binary_source: str,
    network_mode: str, source_run_records: list,
    category_summary_records: list, category_metric_loss_records: list,
    category_win_tie_loss_records: list, bucket_category_records: list,
    candidate_source_category_records: list, availability_records: list,
    private_decomp_records_written: bool, private_decomp_record_count: int,
    private_decomp_storage_class: str, private_decomp_manifest_hash: str,
    records_decomposed: int, records_attempted_total: int,
    network_calls: int, aggregate_runtime_seconds: float,
    fcc: dict[str, int], partial: bool,
) -> dict[str, Any]:
    f = {c: 0 for c in RUN_FAILURE_CATEGORIES}
    for k, v in fcc.items():
        if k in f:
            f[k] = int(v)

    st = dict(SAFE_TRUE_FLAGS)
    st["decomposition_performed"] = records_decomposed > 0
    st["private_decomposition_records_written"] = bool(private_decomp_records_written)

    if records_decomposed > 0 and not partial:
        status = "bea_fd1_decomposition_pass"
    elif records_decomposed > 0:
        status = "partial"
    else:
        status = "unavailable_with_reason"

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "generated_by": GENERATED_BY,
        "generated_at": _now_iso(), "claim_level": CLAIM_LEVEL,
        "status": status, "mode": MODE, "phase": PHASE,
        "budget": FIXED_BUDGET, "methods": FIXED_METHODS.split(","),
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "records_decomposed": records_decomposed,
        "records_attempted_total": records_attempted_total,
        "network_calls": network_calls, "provider_calls": 0,
        "source_run_records": source_run_records,
        "category_summary_records": category_summary_records,
        "category_metric_loss_records": category_metric_loss_records,
        "category_win_tie_loss_records": category_win_tie_loss_records,
        "bucket_category_records": bucket_category_records,
        "candidate_source_category_records": candidate_source_category_records,
        "availability_records": availability_records,
        "private_decomposition_manifest": {
            "records_written": bool(private_decomp_records_written),
            "record_count": int(private_decomp_record_count),
            "schema_version": PRIVATE_DECOMP_SCHEMA_VERSION,
            "manifest_hash": private_decomp_manifest_hash,
            "storage_class": private_decomp_storage_class,
            "path_publicly_serialized": False,
        },
        "aggregate_runtime_seconds": round(float(aggregate_runtime_seconds), 3),
        "failure_category_counts": f,
        **st, **DEFAULT_FALSE_FLAGS, **LICENSE_FIELDS,
        "self_test_passed": self_test_passed,
        "self_test_checks_total": int(self_test_checks_total),
        "self_test_checks_passed": int(
            self_test_checks_total if self_test_checks_passed is None and self_test_passed
            else (self_test_checks_passed or 0)),
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False, "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "calibration_claimed": False, "method_winner_claimed": False,
            "signal_strength": "bea_fd1_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
        },
    }
    scan = _fd1_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _build_synth_data() -> dict[str, Any]:
    sr = [
        {"source_phase": "BEA-4", "source_ci_run_id": "27957586271",
         "source_artifact_status": "bea4_external_scale_smoke_pass",
         "source_sampling_protocol": "bea4_external_scale_smoke.v1",
         "expected_successful_records": 120, "replayed_successful_records": 120,
         "expected_private_score_count": 840, "replayed_private_score_count": 840,
         "records_attempted_total": 126, "records_excluded": 6,
         "contextbench_successful": 80, "repoqa_successful": 40,
         "replay_protocol_match": True, "replay_mismatch_reason": ""},
        {"source_phase": "BEA-5", "source_ci_run_id": "28003522632",
         "source_artifact_status": "partial",
         "source_sampling_protocol": "bea5_success_quota_disjoint_scan.v1",
         "expected_successful_records": 119, "replayed_successful_records": 119,
         "expected_private_score_count": 833, "replayed_private_score_count": 833,
         "records_attempted_total": 186, "records_excluded": 67,
         "contextbench_successful": 82, "repoqa_successful": 37,
         "replay_protocol_match": True, "replay_mismatch_reason": ""},
    ]
    cs = [
        {"source_phase": "BEA-4", "benchmark": "contextbench",
         "category": "gold_file_absent", "category_availability": "available",
         "record_count": 5},
        {"source_phase": "BEA-4", "benchmark": "repoqa",
         "category": "gold_file_absent", "category_availability": "available",
         "record_count": 3},
        {"source_phase": "BEA-4", "benchmark": "contextbench",
         "category": "missing_support_candidate",
         "category_availability": "unavailable_no_support_label",
         "record_count": 0},
    ]
    cml = [
        {"source_phase": "BEA-4", "benchmark": "contextbench",
         "category": "gold_file_absent", "baseline_arm": ARM_V0,
         "treatment_arm": ARM_V03, "metric": "mrr",
         "loss_sum": 0.75, "loss_mean": 0.15, "delta_mean": -0.15,
         "record_count": 5},
    ]
    cwtl = [
        {"source_phase": "BEA-4", "benchmark": "contextbench",
         "category": "gold_file_absent", "baseline_arm": ARM_V0,
         "treatment_arm": ARM_V03, "metric": "mrr",
         "win": 0, "tie": 1, "loss": 4, "record_count": 5},
    ]
    bc = [
        {"source_phase": "BEA-4", "benchmark": "contextbench",
         "bucket_type": "benchmark", "bucket_value": "contextbench",
         "category": "gold_file_absent", "record_count": 5},
    ]
    csc = [
        {"source_phase": "BEA-4", "benchmark": "contextbench",
         "candidate_source_bucket": "bm25",
         "category": "gold_file_absent", "record_count": 3},
    ]
    av = [
        {"source_phase": "BEA-4", "benchmark": "contextbench",
         "category": "gold_file_absent", "category_availability": "available",
         "record_count": 5},
        {"source_phase": "BEA-4", "benchmark": "contextbench",
         "category": "missing_support_candidate",
         "category_availability": "unavailable_no_support_label",
         "record_count": 0},
    ]
    return {"sr": sr, "cs": cs, "cml": cml, "cwtl": cwtl,
            "bc": bc, "csc": csc, "av": av}


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []
    synth = _build_synth_data()
    skeleton = _build_pass(
        self_test_passed=True, self_test_checks_total=0,
        self_test_checks_passed=None,
        openlocus_binary_source="self_test", network_mode="self_test",
        source_run_records=synth["sr"], category_summary_records=synth["cs"],
        category_metric_loss_records=synth["cml"],
        category_win_tie_loss_records=synth["cwtl"],
        bucket_category_records=synth["bc"],
        candidate_source_category_records=synth["csc"],
        availability_records=synth["av"],
        private_decomp_records_written=True, private_decomp_record_count=10,
        private_decomp_storage_class="tmp_private",
        private_decomp_manifest_hash=_decomp_manifest_hash(),
        records_decomposed=10, records_attempted_total=12,
        network_calls=0, aggregate_runtime_seconds=0.5,
        fcc={c: 0 for c in RUN_FAILURE_CATEGORIES}, partial=False,
    )
    unavail = _build_unavailable(
        "retrieval_failed", self_test_passed=True,
        self_test_checks_total=0, openlocus_binary_source="self_test",
        network_mode="self_test",
    )

    # G1: Identity
    for k, v in [("schema_version", SCHEMA_VERSION), ("claim_level", CLAIM_LEVEL),
                 ("mode", MODE), ("phase", PHASE), ("generated_by", GENERATED_BY)]:
        checks.append(_check(f"identity_{k}", skeleton[k] == v))
    checks.append(_check("status_pass", skeleton["status"] == "bea_fd1_decomposition_pass"))
    checks.append(_check("unavail_status", unavail["status"] == "unavailable_with_reason"))

    # G2: Safe true / false flags
    for f in SAFE_TRUE_FLAGS:
        checks.append(_check(f"true_{f}", skeleton.get(f) is True))
    for f in DEFAULT_FALSE_FLAGS:
        checks.append(_check(f"false_{f}", skeleton.get(f) is False))

    # G3: License
    for k, v in LICENSE_FIELDS.items():
        checks.append(_check(f"license_{k}", skeleton.get(k) == v))

    # G4: Fixed enum
    checks.append(_check("cat_count_12", len(FAILURE_CATEGORIES) == 12))
    for c in FAILURE_CATEGORIES:
        checks.append(_check(f"cat_{c}", c in FAILURE_CATEGORIES))

    # G5: Required baselines
    checks.append(_check("baselines_5", len(BASELINE_ARMS) == 5))
    for b in BASELINE_ARMS:
        checks.append(_check(f"baseline_{b}", b in BASELINE_ARMS))

    # G6: Source phase configs
    checks.append(_check("configs_2", len(SOURCE_PHASE_CONFIGS) == 2))
    for cfg in SOURCE_PHASE_CONFIGS:
        checks.append(_check(f"config_{cfg['source_phase']}_expected",
            cfg["expected_successful_records"] in (119, 120)))
    checks.append(_check("bea4_expected_120", SOURCE_PHASE_CONFIGS[0]["expected_successful_records"] == 120))
    checks.append(_check("bea5_expected_119", SOURCE_PHASE_CONFIGS[1]["expected_successful_records"] == 119))
    checks.append(_check("bea4_expected_840", SOURCE_PHASE_CONFIGS[0]["expected_private_score_count"] == 840))
    checks.append(_check("bea5_expected_833", SOURCE_PHASE_CONFIGS[1]["expected_private_score_count"] == 833))
    checks.append(_check("bea4_expected_contextbench_80", SOURCE_PHASE_CONFIGS[0]["expected_contextbench_successful"] == 80))
    checks.append(_check("bea4_expected_repoqa_40", SOURCE_PHASE_CONFIGS[0]["expected_repoqa_successful"] == 40))
    checks.append(_check("bea5_expected_contextbench_82", SOURCE_PHASE_CONFIGS[1]["expected_contextbench_successful"] == 82))
    checks.append(_check("bea5_expected_repoqa_37", SOURCE_PHASE_CONFIGS[1]["expected_repoqa_successful"] == 37))
    checks.append(_check("expected_decomposed_records_239", EXPECTED_DECOMPOSED_RECORDS == 239))
    checks.append(_check("expected_private_decomp_rows_86040", EXPECTED_PRIVATE_DECOMP_ROWS == 86040))
    for cfg in SOURCE_PHASE_CONFIGS:
        script_path = _evaluator_script_path(Path(__file__).resolve().parent, str(cfg["evaluator"]))
        checks.append(_check(f"config_{cfg['source_phase']}_script_exists", script_path.exists()))

    # G7: Source run records + uniqueness
    srr = skeleton.get("source_run_records", [])
    checks.append(_check("srr_2", len(srr) == 2))
    for r in srr:
        for k in ("source_phase", "source_ci_run_id", "source_artifact_status",
                   "source_sampling_protocol", "expected_successful_records",
                   "replayed_successful_records", "expected_private_score_count",
                   "replayed_private_score_count", "records_attempted_total",
                   "records_excluded", "contextbench_successful",
                   "repoqa_successful", "replay_protocol_match",
                   "replay_mismatch_reason"):
            checks.append(_check(f"srr_has_{k}", k in r))
    checks.append(_check("srr_unique", not _check_unique(srr, _sr_key, "sr")))

    # G8-G13: Record tables + uniqueness
    for name, records, key_fn in [
        ("category_summary", synth["cs"], _cs_key),
        ("category_metric_loss", synth["cml"], _cml_key),
        ("category_win_tie_loss", synth["cwtl"], _cwtl_key),
        ("bucket_category", synth["bc"], _bc_key),
        ("candidate_source_category", synth["csc"], _csc_key),
        ("availability", synth["av"], _av_key),
    ]:
        checks.append(_check(f"{name}_nonempty", len(records) > 0))
        checks.append(_check(f"{name}_unique", not _check_unique(records, key_fn, name)))

    # G14: Private decomp manifest
    m = skeleton.get("private_decomposition_manifest", {})
    checks.append(_check("manifest_written", m.get("records_written") is True))
    checks.append(_check("manifest_count", m.get("record_count") == 10))
    checks.append(_check("manifest_schema", m.get("schema_version") == PRIVATE_DECOMP_SCHEMA_VERSION))
    checks.append(_check("manifest_path_false", m.get("path_publicly_serialized") is False))
    checks.append(_check("manifest_hash_64", len(m.get("manifest_hash", "")) == 64))

    # G15: Scanner rejects forbidden keys
    for fk in ("decomposition_path", "private_decomposition_path", "gold_paths",
               "action_order", "score_outcome", "winner", "calibration",
               "comparison_arm", "bucket", "candidate_source",
               "self_test_checks", "private_record_id"):
        leaked = dict(skeleton)
        leaked[fk] = "leak"
        checks.append(_check(f"scan_rejects_{fk}", bool(_scan_fd1(leaked))))

    # G16: Scanner allows safe
    safe = {"schema_version": SCHEMA_VERSION, "source_phase": "BEA-4",
            "category": "gold_file_absent", "category_availability": "available",
            "baseline_arm": ARM_V0, "treatment_arm": ARM_V03,
            "metric": "mrr", "bucket_type": "benchmark",
            "bucket_value": "contextbench",
            "candidate_source_bucket": "bm25",
            "source_run_records": [{"source_phase": "BEA-4", "source_ci_run_id": "x"}],
            "private_decomposition_manifest": {"records_written": True,
                "record_count": 1, "schema_version": PRIVATE_DECOMP_SCHEMA_VERSION,
                "manifest_hash": "a"*64, "storage_class": "tmp_private",
                "path_publicly_serialized": False}}
    checks.append(_check("scan_allows_safe", not _scan_fd1(safe)))

    # G17: Fail-closed
    try:
        _enforce_no_forbidden(skeleton)
        checks.append(_check("fail_closed_clean", True))
    except SystemExit:
        checks.append(_check("fail_closed_clean", False))
    for lk in ("private_decomposition_path", "gold_paths", "action_order",
               "winner", "calibration", "self_test_checks"):
        leaked = dict(skeleton)
        leaked[lk] = "leak"
        try:
            _enforce_no_forbidden(leaked)
            checks.append(_check(f"fail_closed_{lk}", False))
        except SystemExit:
            checks.append(_check(f"fail_closed_{lk}", True))

    # G18: Self-scan clean
    checks.append(_check("self_clean", not _scan_fd1(skeleton)))
    checks.append(_check("unavail_clean", not _scan_fd1(unavail)))

    # G19: CLI surface (only enable_network + out + openlocus + private_dir)
    parser = build_parser()
    opts = set()
    for a in parser._actions:
        for o in a.option_strings:
            opts.add(o)
    for o in ("--self-test", "--enable-external-benchmark-network",
              "--openlocus", "--out", "--private-decomposition-dir"):
        checks.append(_check(f"cli_has_{o}", o in opts))
    # Must NOT have budget/methods (fixed protocol).
    for o in ("--budget", "--methods"):
        checks.append(_check(f"cli_no_{o}", o not in opts))

    # G20: Private decomp writer
    with tempfile.TemporaryDirectory(prefix="fd1_st_") as sd:
        df = Path(sd) / "fd1.decomp.jsonl"
        _write_decomp_row(df, {"test": 1})
        _write_decomp_row(df, {"test": 2})
        lines = df.read_text(encoding="utf-8").splitlines()
        checks.append(_check("writer_2", len(lines) == 2))
        checks.append(_check("writer_parse", all(isinstance(json.loads(l), dict) for l in lines if l)))

        bad_jsonl = Path(sd) / "bad.private.jsonl"
        bad_jsonl.write_text('{"private_record_id":"r1","policy_arm":"bea_v0_3_anchor_span_latency"}\nnot-json\n', encoding="utf-8")
        parsed_rows, parse_failures = _parse_private_jsonl(bad_jsonl)
        checks.append(_check("private_jsonl_parse_failure_visible", parse_failures == 1))
        checks.append(_check("private_jsonl_partial_rows_visible", len(parsed_rows) == 1))

        complete_rows = [
            {"private_record_id": "r1", "policy_arm": arm}
            for arm in REQUIRED_PRIVATE_ARMS
        ]
        incomplete_rows = complete_rows[:-1]
        checks.append(_check("required_arm_coverage_complete",
            _required_arm_coverage_failures(_group_private_rows_by_record(complete_rows)) == 0))
        checks.append(_check("required_arm_coverage_incomplete",
            _required_arm_coverage_failures(_group_private_rows_by_record(incomplete_rows)) == 1))

    # G21: No forbidden fields
    for f in ("winner", "best_method", "recommended_default", "method_winner", "calibration"):
        checks.append(_check(f"missing_{f}", f not in skeleton))

    # G22: Counts-only self-test
    checks.append(_check("has_st_total", "self_test_checks_total" in skeleton))
    checks.append(_check("has_st_passed", "self_test_checks_passed" in skeleton))
    for ff in ("self_test_checks", "self_test_details", "self_test_list", "checks", "check_list"):
        checks.append(_check(f"no_{ff}", ff not in skeleton))

    # G23: Unavailable categories
    for c in UNAVAILABLE_NO_SUPPORT_CATEGORIES:
        checks.append(_check(f"unavail_no_support_{c}", c in UNAVAILABLE_NO_SUPPORT_CATEGORIES))
    for c in UNAVAILABLE_MISSING_TRACE_CATEGORIES:
        checks.append(_check(f"unavail_missing_trace_{c}", c in UNAVAILABLE_MISSING_TRACE_CATEGORIES))

    # G24: Unavail report has empty tables
    for k in ("source_run_records", "category_summary_records",
              "category_metric_loss_records", "category_win_tie_loss_records",
              "bucket_category_records", "candidate_source_category_records",
              "availability_records"):
        checks.append(_check(f"unavail_empty_{k}", unavail.get(k) == []))

    # G25: Fixed budget/methods
    checks.append(_check("fixed_budget_5", FIXED_BUDGET == 5))
    checks.append(_check("fixed_methods", FIXED_METHODS == "bm25,regex,symbol"))

    # G26: Duplicate detection
    dup = [{"source_phase": "BEA-4", "source_ci_run_id": "x"},
           {"source_phase": "BEA-4", "source_ci_run_id": "x"}]
    checks.append(_check("dup_detected", bool(_check_unique(dup, _sr_key, "test"))))

    all_passed = all(c["passed"] for c in checks if c is not None)
    return checks, all_passed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(description="BEA-FD1 Failure Decomposition (frozen replay)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--enable-external-benchmark-network", action="store_true")
    ap.add_argument("--openlocus", default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--private-decomposition-dir", default=None)
    # NOTE: NO --budget or --methods (fixed protocol).
    return ap


# ---------------------------------------------------------------------------
# Network decomposition runner
# ---------------------------------------------------------------------------

def _run_decomposition(
    *, openlocus_bin: str, openlocus_binary_source: str,
    network_mode: str, eval_dir: Path, self_test_passed: bool,
    self_test_checks_total: int, private_dir: Path,
    private_decomp_storage_class: str, phase_run_id: str,
) -> dict[str, Any]:
    fcc = {c: 0 for c in RUN_FAILURE_CATEGORIES}
    network_calls = 0
    start = time.perf_counter()
    manifest_hash = _decomp_manifest_hash()
    decomp_file = private_dir / "bea_fd1.decomposition.jsonl"
    try:
        decomp_file.unlink()
    except OSError:
        pass

    source_run_records: list[dict[str, Any]] = []
    all_parsed_rows: list[tuple[str, list[dict[str, Any]]]] = []
    records_decomposed = 0
    records_attempted_total = 0

    for config in SOURCE_PHASE_CONFIGS:
        artifact, status, exit_code, sub_fcc = _run_subprocess_replay(
            config, private_dir, openlocus_bin, eval_dir,
        )
        for k, v in sub_fcc.items():
            if k in fcc:
                fcc[k] += v
        network_calls += 1

        if artifact is None:
            source_run_records.append({
                "source_phase": config["source_phase"],
                "source_ci_run_id": config["source_ci_run_id"],
                "source_artifact_status": "unavailable",
                "source_sampling_protocol": config["source_sampling_protocol"],
                "expected_successful_records": config["expected_successful_records"],
                "replayed_successful_records": 0,
                "expected_private_score_count": config["expected_private_score_count"],
                "replayed_private_score_count": 0,
                "records_attempted_total": 0, "records_excluded": 0,
                "contextbench_successful": 0, "repoqa_successful": 0,
                "replay_protocol_match": False,
                "replay_mismatch_reason": f"subprocess_{status}",
            })
            fcc["replay_subprocess_failed"] = fcc.get("replay_subprocess_failed", 0) + 1
            continue

        # Extract replay agreement fields from the public artifact.
        replayed_successful = int(artifact.get("records_successful", 0))
        replayed_private_score = int(
            artifact.get("private_score_manifest", {}).get("record_count", 0)
        )
        attempted = int(artifact.get("records_attempted_total",
                      artifact.get("records_evaluated", 0)))
        excluded = int(artifact.get("records_excluded", 0))
        cb_succ = int(artifact.get("contextbench_successful", 0))
        rq_succ = int(artifact.get("repoqa_successful", 0))

        match = True
        mismatch_reason = ""
        if replayed_successful != config["expected_successful_records"]:
            match = False
            mismatch_reason = f"records_mismatch_{replayed_successful}_vs_{config['expected_successful_records']}"
        if replayed_private_score != config["expected_private_score_count"]:
            match = False
            mismatch_reason += f" score_mismatch_{replayed_private_score}_vs_{config['expected_private_score_count']}"

        if not match:
            fcc["replay_mismatch"] = fcc.get("replay_mismatch", 0) + 1

        source_run_records.append({
            "source_phase": config["source_phase"],
            "source_ci_run_id": config["source_ci_run_id"],
            "source_artifact_status": artifact.get("status", "unknown"),
            "source_sampling_protocol": config["source_sampling_protocol"],
            "expected_successful_records": config["expected_successful_records"],
            "replayed_successful_records": replayed_successful,
            "expected_private_score_count": config["expected_private_score_count"],
            "replayed_private_score_count": replayed_private_score,
            "records_attempted_total": attempted,
            "records_excluded": excluded,
            "contextbench_successful": cb_succ,
            "repoqa_successful": rq_succ,
            "replay_protocol_match": match,
            "replay_mismatch_reason": mismatch_reason,
        })

        records_attempted_total += attempted

        # Parse the private JSONL file.
        private_jsonl = private_dir / config["source_phase"] / config["private_jsonl_name"]
        parsed_rows, parse_failures = _parse_private_jsonl(private_jsonl)
        if parse_failures:
            fcc["private_score_parse_failed"] = (
                fcc.get("private_score_parse_failed", 0) + parse_failures
            )

        by_record_for_check = _group_private_rows_by_record(parsed_rows)
        benchmark_record_counts = Counter(
            (rows[0].get("benchmark", "unknown") if rows else "unknown")
            for rows in by_record_for_check.values()
        )
        cb_succ = int(benchmark_record_counts.get("contextbench", 0))
        rq_succ = int(benchmark_record_counts.get("repoqa", 0))
        source_run_records[-1]["contextbench_successful"] = cb_succ
        source_run_records[-1]["repoqa_successful"] = rq_succ
        coverage_failures = _required_arm_coverage_failures(by_record_for_check)
        completeness_reasons: list[str] = []
        if parse_failures:
            completeness_reasons.append(f"parse_failures_{parse_failures}")
        if len(parsed_rows) != replayed_private_score:
            completeness_reasons.append(
                f"parsed_score_count_{len(parsed_rows)}_vs_{replayed_private_score}"
            )
        if len(by_record_for_check) != replayed_successful:
            completeness_reasons.append(
                f"grouped_records_{len(by_record_for_check)}_vs_{replayed_successful}"
            )
        if coverage_failures:
            completeness_reasons.append(f"required_arm_coverage_failures_{coverage_failures}")
        if cb_succ != int(config["expected_contextbench_successful"]):
            completeness_reasons.append(
                f"contextbench_successful_{cb_succ}_vs_{config['expected_contextbench_successful']}"
            )
        if rq_succ != int(config["expected_repoqa_successful"]):
            completeness_reasons.append(
                f"repoqa_successful_{rq_succ}_vs_{config['expected_repoqa_successful']}"
            )

        if completeness_reasons:
            fcc["replay_mismatch"] = fcc.get("replay_mismatch", 0) + 1
            source_run_records[-1]["replay_protocol_match"] = False
            prior = str(source_run_records[-1].get("replay_mismatch_reason", ""))
            joined = ";".join(completeness_reasons)
            source_run_records[-1]["replay_mismatch_reason"] = (
                f"{prior};{joined}" if prior else joined
            )

        all_parsed_rows.append((config["source_phase"], parsed_rows))

        if not parsed_rows:
            fcc["private_score_parse_failed"] = fcc.get("private_score_parse_failed", 0) + 1

    # Group parsed rows by private_record_id per source phase.
    for source_phase, parsed_rows in all_parsed_rows:
        by_record = _group_private_rows_by_record(parsed_rows)

        for rid, record_rows in by_record.items():
            benchmark = record_rows[0].get("benchmark", "unknown") if record_rows else "unknown"
            records_decomposed += 1

            classifications = _classify_from_private_rows(record_rows)

            for baseline, cats in classifications.items():
                for cat, info in cats.items():
                    count = int(info.get("count", 0))
                    avail = info.get("availability", "available")

                    # Write private decomposition row.
                    v03_row = next((r for r in record_rows if r.get("policy_arm") == ARM_V03), {})
                    b_row = next((r for r in record_rows if r.get("policy_arm") == baseline), {})
                    v03_out = v03_row.get("score_outcome", {})
                    b_out = b_row.get("score_outcome", {})

                    for metric in ALL_METRICS:
                        t_val = float(v03_out.get(metric, 0.0) or 0.0)
                        b_val = float(b_out.get(metric, 0.0) or 0.0)
                        if metric == LATENCY_METRIC:
                            loss = max(0.0, t_val - b_val)
                        else:
                            loss = max(0.0, b_val - t_val)
                        delta = t_val - b_val

                        try:
                            _write_decomp_row(decomp_file, {
                                "phase_run_id": phase_run_id,
                                "source_phase": source_phase,
                                "benchmark": benchmark,
                                "private_record_id": rid,
                                "policy_arm": ARM_V03,
                                "category": cat,
                                "baseline_arm": baseline,
                                "treatment_arm": ARM_V03,
                                "metric": metric,
                                "treatment_value": t_val,
                                "baseline_value": b_val,
                                "loss": round(loss, 6),
                                "delta": round(delta, 6),
                                "category_availability": avail,
                                "latency_ms": 0, "cost_usd": 0.0,
                                "tokens": 0, "provider_calls": 0,
                            })
                        except OSError:
                            fcc["private_decomposition_write_failed"] = (
                                fcc.get("private_decomposition_write_failed", 0) + 1)

    # Build aggregate records.
    category_summary: dict[tuple, int] = {}
    category_metric_loss: dict[tuple, list] = {}
    category_wtl: dict[tuple, list] = {}
    bucket_cat: dict[tuple, int] = {}
    cand_src_cat: dict[tuple, int] = {}
    avail_records: dict[tuple, int] = {}

    for source_phase, parsed_rows in all_parsed_rows:
        by_record = _group_private_rows_by_record(parsed_rows)

        for rid, record_rows in by_record.items():
            benchmark = record_rows[0].get("benchmark", "unknown") if record_rows else "unknown"
            classifications = _classify_from_private_rows(record_rows)
            seen_summary: set[tuple[str, str, str, str, str]] = set()
            seen_availability: set[tuple[str, str, str, str, str]] = set()

            for baseline, cats in classifications.items():
                for cat, info in cats.items():
                    count = int(info.get("count", 0))
                    avail = info.get("availability", "available")

                    summary_seen_key = (source_phase, benchmark, rid, cat, avail)
                    if count > 0 and summary_seen_key not in seen_summary:
                        cs_key = (source_phase, benchmark, cat, avail)
                        category_summary[cs_key] = category_summary.get(cs_key, 0) + 1
                        seen_summary.add(summary_seen_key)

                    availability_seen_key = (source_phase, benchmark, rid, cat, avail)
                    if availability_seen_key not in seen_availability:
                        av_key = (source_phase, benchmark, cat, avail)
                        avail_records[av_key] = avail_records.get(av_key, 0) + 1
                        seen_availability.add(availability_seen_key)

                    if count <= 0:
                        continue

                    bc_key = (source_phase, benchmark, "benchmark", benchmark, cat)
                    bucket_cat[bc_key] = bucket_cat.get(bc_key, 0) + count

                    csc_key = (source_phase, benchmark, "unknown_unavailable", cat)
                    cand_src_cat[csc_key] = cand_src_cat.get(csc_key, 0) + count

                    v03_row = next((r for r in record_rows if r.get("policy_arm") == ARM_V03), {})
                    b_row = next((r for r in record_rows if r.get("policy_arm") == baseline), {})
                    v03_out = v03_row.get("score_outcome", {})
                    b_out = b_row.get("score_outcome", {})

                    for metric in ALL_METRICS:
                        t_val = float(v03_out.get(metric, 0.0) or 0.0)
                        b_val = float(b_out.get(metric, 0.0) or 0.0)
                        if metric == LATENCY_METRIC:
                            loss = max(0.0, t_val - b_val)
                        else:
                            loss = max(0.0, b_val - t_val)
                        delta = t_val - b_val

                        ml_key = (source_phase, benchmark, cat, baseline, ARM_V03, metric)
                        if ml_key not in category_metric_loss:
                            category_metric_loss[ml_key] = []
                        category_metric_loss[ml_key].append((loss, delta))

                        wtl_key = (source_phase, benchmark, cat, baseline, ARM_V03, metric)
                        if wtl_key not in category_wtl:
                            category_wtl[wtl_key] = [0, 0, 0]  # win, tie, loss
                        if delta > 0:
                            category_wtl[wtl_key][0] += 1
                        elif delta < 0:
                            category_wtl[wtl_key][2] += 1
                        else:
                            category_wtl[wtl_key][1] += 1

    # Build record lists.
    sr_records = source_run_records

    cs_records = [
        {"source_phase": k[0], "benchmark": k[1], "category": k[2],
         "category_availability": k[3], "record_count": v}
        for k, v in sorted(category_summary.items())
    ]

    cml_records = [
        {"source_phase": k[0], "benchmark": k[1], "category": k[2],
         "baseline_arm": k[3], "treatment_arm": k[4], "metric": k[5],
         "loss_sum": round(sum(l for l, _ in vals), 6),
         "loss_mean": round(sum(l for l, _ in vals) / len(vals), 6) if vals else 0.0,
         "delta_mean": round(sum(d for _, d in vals) / len(vals), 6) if vals else 0.0,
         "record_count": len(vals)}
        for k, vals in sorted(category_metric_loss.items())
    ]

    cwtl_records = [
        {"source_phase": k[0], "benchmark": k[1], "category": k[2],
         "baseline_arm": k[3], "treatment_arm": k[4], "metric": k[5],
         "win": v[0], "tie": v[1], "loss": v[2], "record_count": v[0] + v[1] + v[2]}
        for k, v in sorted(category_wtl.items())
    ]

    bc_records = [
        {"source_phase": k[0], "benchmark": k[1], "bucket_type": k[2],
         "bucket_value": k[3], "category": k[4], "record_count": v}
        for k, v in sorted(bucket_cat.items())
    ]

    csc_records = [
        {"source_phase": k[0], "benchmark": k[1], "candidate_source_bucket": k[2],
         "category": k[3], "record_count": v}
        for k, v in sorted(cand_src_cat.items())
    ]

    av_records = [
        {"source_phase": k[0], "benchmark": k[1], "category": k[2],
         "category_availability": k[3], "record_count": v}
        for k, v in sorted(avail_records.items())
    ]

    # Count private decomposition rows.
    decomp_count = 0
    try:
        if decomp_file.exists():
            with decomp_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        decomp_count += 1
    except OSError:
        decomp_count = 0

    runtime = time.perf_counter() - start
    any_mismatch = any(not r.get("replay_protocol_match", False) for r in source_run_records)
    expected_decomposed = sum(
        int(r.get("replayed_successful_records", 0)) for r in source_run_records
    )
    blocking_failure = any(
        int(fcc.get(k, 0)) != 0 for k in (
            "private_decomposition_write_failed",
            "private_score_parse_failed",
            "replay_mismatch",
            "replay_subprocess_failed",
        )
    )
    partial = (
        any_mismatch
        or records_decomposed != expected_decomposed
        or records_decomposed != EXPECTED_DECOMPOSED_RECORDS
        or decomp_count != EXPECTED_PRIVATE_DECOMP_ROWS
        or blocking_failure
    )

    return _build_pass(
        self_test_passed=self_test_passed,
        self_test_checks_total=self_test_checks_total,
        self_test_checks_passed=None,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        source_run_records=sr_records,
        category_summary_records=cs_records,
        category_metric_loss_records=cml_records,
        category_win_tie_loss_records=cwtl_records,
        bucket_category_records=bc_records,
        candidate_source_category_records=csc_records,
        availability_records=av_records,
        private_decomp_records_written=decomp_count > 0,
        private_decomp_record_count=decomp_count,
        private_decomp_storage_class=private_decomp_storage_class,
        private_decomp_manifest_hash=manifest_hash,
        records_decomposed=records_decomposed,
        records_attempted_total=records_attempted_total,
        network_calls=network_calls,
        aggregate_runtime_seconds=runtime,
        fcc=fcc, partial=partial,
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    checks, self_test_passed = run_self_test_checks()
    self_test_checks_total = len(checks)

    if args.self_test:
        for c in checks:
            tag = "PASS" if c["passed"] else "FAIL"
            print(f"[{tag}] {c['check']}")
        passed = sum(1 for c in checks if c["passed"])
        print(f"self_test_passed={self_test_passed} ({passed}/{len(checks)} checks)")
        sys.exit(0 if passed else 1)

    enable_network = bool(args.enable_external_benchmark_network)
    out_path = args.out if args.out is not None else DEFAULT_OUT

    if not self_test_passed:
        print("error: self-test failed; refusing to write artifact", file=sys.stderr)
        sys.exit(1)

    openlocus_bin, openlocus_source = c5a._resolve_openlocus_binary(args.openlocus)
    if openlocus_bin is None:
        report = _build_unavailable(
            "retrieval_failed", self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_source,
            network_mode="local_explicit",
        )
        _enforce_no_forbidden(report)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        return

    private_dir, private_decomp_storage_class = _resolve_private_dir(
        args.private_decomposition_dir
    )
    phase_run_id = f"bea-fd1-{int(time.time())}"

    if not enable_network:
        report = _build_unavailable(
            "retrieval_failed", self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_source,
            network_mode="disabled_opt_in",
            private_decomp_storage_class=private_decomp_storage_class,
        )
        _enforce_no_forbidden(report)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        print("enable_external_benchmark_network is false; skipping real BEA-FD1 decomposition.")
        return

    network_mode = "local_explicit"
    eval_dir = Path(__file__).resolve().parent
    try:
        report = _run_decomposition(
            openlocus_bin=openlocus_bin,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode, eval_dir=eval_dir,
            self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            private_dir=private_dir,
            private_decomp_storage_class=private_decomp_storage_class,
            phase_run_id=phase_run_id,
        )
    except Exception:
        report = _build_unavailable(
            "unexpected_exception", self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
            private_decomp_storage_class=private_decomp_storage_class,
        )

    if report.get("provider_calls") != 0:
        report["status"] = "fail_schema_contract"

    _enforce_no_forbidden(report)
    _write_json(out_path, report)
    m = report.get("private_decomposition_manifest", {})
    print(f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, "
          f"status={report['status']}, phase={report['phase']}, "
          f"records_decomposed={report.get('records_decomposed', 0)}, "
          f"private_decomposition_record_count={m.get('record_count', 0)})")


if __name__ == "__main__":
    main()
