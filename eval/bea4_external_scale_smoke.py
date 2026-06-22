#!/usr/bin/env python3
"""BEA-4 External Scale Smoke (Public Aggregate-Only, Records-Shaped).

This module implements the **BEA-4 external scale smoke** for the frozen
BEA v0.3 policy. It measures scale behavior of v0.3 + same-budget controls
over a larger fresh external slice (ContextBench verified Python rows
offset 80, RepoQA Python needles offset 40) and publishes records-only
aggregate output with worst-slice visibility.

BEA-4 is explicitly **not** a benchmark result, **not** a leaderboard entry,
**not** a performance claim, **not** a method-winner claim, **not** a
calibration claim, **not** a promotion, **not** a default/policy change,
**not** a runtime/retriever/pack/backend/EvidenceCore semantic change, and
**not** an algorithm change. The v0.3 algorithm and weights are frozen
exactly as in BEA-3; this phase is scale measurement, not a new algorithm.

Claim boundary (binding):

* Claim level: ``bea_v03_external_scale_smoke_only``.
* Status: ``bea4_external_scale_smoke_pass`` | ``partial`` |
  ``unavailable_with_reason`` | ``fail_forbidden_scan`` |
  ``fail_schema_contract``.
* Mode: ``bea_v03_external_scale_smoke``; phase ``BEA-4``.

Privacy / license boundary (binding):

* Raw ContextBench rows / RepoQA needles, queries/problem statements,
  repo URLs/names, base commits / commit SHAs, gold paths/spans/contents,
  generated task/label/run JSONL, evidence rows, cloned repos, candidate
  lists, action traces, budget-state sequences, accepted/final candidate
  selections, score outcomes, worst-slice record IDs, slice labels, and
  stdout/stderr are kept **transient only** under ``/tmp`` or CI ephemeral
  workspace. They are NEVER committed or uploaded.
* Private per-record SCORE JSONL is written ONLY under ``/tmp`` (or an
  explicitly ignored private path). The private SCORE path is NEVER
  serialized in the public artifact, docs, or CI artifacts.
* The public artifact records ONLY aggregate SCORE manifest fields:
  ``records_written``, ``record_count``, ``schema_version``,
  ``manifest_hash``, ``storage_class``, ``path_publicly_serialized=false``.

Network / CI policy (binding):

* Default no-network self-test passes without HuggingFace/GitHub.
* Real scale smoke requires public network access. CI must be a separate
  explicit ``workflow_dispatch`` job with
  ``enable_external_benchmark_network=true``. It must NOT run on PR/push
  by default, must use no provider secrets/vars, no provider model env,
  and must upload only the aggregate report. The private SCORE JSONL is
  NEVER uploaded.

Run::

    python3 -m py_compile eval/bea4_external_scale_smoke.py
    python3 eval/bea4_external_scale_smoke.py --self-test
    python3 eval/bea4_external_scale_smoke.py \\
        --enable-external-benchmark-network \\
        --contextbench-row-offset 80 --contextbench-row-limit 3 \\
        --repoqa-needle-offset 40 --repoqa-needle-limit 2 \\
        --budget 5 --methods bm25,regex,symbol --enable-rrf-baseline \\
        --out artifacts/bea4_external_scale_smoke/\\
bea4_external_scale_smoke_report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, NoReturn

# Reuse BEA-3 helpers (frozen v0.3 policy + v0.2/v0 controls + scanners).
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import bea3_anchor_span_latency as bea3  # noqa: E402
import bea2_policy_v02 as bea2  # noqa: E402
import bea1_mechanism_ablation as bea1  # noqa: E402
import bea0_budgeted_evidence_acquisition as bea0  # noqa: E402
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402
import c5d_repoqa_bm25_retrieval_smoke as c5d  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants (BEA-4 owned)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "bea4_external_scale_smoke.v1"
GENERATED_BY = "eval/bea4_external_scale_smoke.py"
CLAIM_LEVEL = "bea_v03_external_scale_smoke_only"
SELF_TEST_CHECKS_EXPECTED = 237
MODE = "bea_v03_external_scale_smoke"
PHASE = "BEA-4"

DEFAULT_OUT = Path(
    "artifacts/bea4_external_scale_smoke/"
    "bea4_external_scale_smoke_report.json"
)

PRIVATE_SCORE_SCHEMA_VERSION = "bea4_private_score.v1"

# Scale defaults for manual CI. Local smoke may use smaller bounds.
CONTEXTBENCH_ROW_OFFSET_DEFAULT = 80
CONTEXTBENCH_ROW_LIMIT_DEFAULT = 80
CONTEXTBENCH_ROW_LIMIT_HARD_CAP = 80
REPOQA_NEEDLE_OFFSET_DEFAULT = 40
REPOQA_NEEDLE_LIMIT_DEFAULT = 40
REPOQA_NEEDLE_LIMIT_HARD_CAP = 40

BUDGET_DEFAULT = 5
BUDGET_HARD_CAP = 20

ALLOWED_METHODS: tuple[str, ...] = ("bm25", "regex", "symbol")
DEFAULT_METHODS = "bm25,regex,symbol"

# Required arms (frozen; NO ablations in BEA-4).
ARM_BEA_V0_3 = "bea_v0_3_anchor_span_latency"
ARM_BEA_V0_2 = "bea_v0_2_diversity_risk"
ARM_BEA_V0 = "bea_v0"
ARM_BM25_PREFIX = "bm25_prefix_same_budget"
ARM_AGREEMENT_ONLY = "agreement_only_same_budget"
ARM_SEEDED_RANDOM = "seeded_random_same_budget"
ARM_RRF_SAME_BUDGET = "rrf_same_budget"

TREATMENT_ARM = ARM_BEA_V0_3
BASELINE_ARM = ARM_BEA_V0  # fixed baseline for delta_records

# Contrast names for v0.3 vs each control (used in worst-slice aggregation).
CONTRAST_V03_VS_BM25 = "v03_vs_bm25"
CONTRAST_V03_VS_AGREEMENT = "v03_vs_agreement"
CONTRAST_V03_VS_RRF = "v03_vs_rrf"
CONTRAST_V03_VS_V02 = "v03_vs_v02"
CONTRAST_V03_VS_V0 = "v03_vs_v0"
CONTRAST_V03_VS_SEEDED_RANDOM = "v03_vs_seeded_random"

SEEDED_RANDOM_SEED = 20240621

# Worst-slice: maximum number of worst slices emitted per benchmark
# (sorted ascending by mean span_f0.5@10, then by mean mrr).
WORST_SLICE_MAX_PER_BENCHMARK = 5

# Metric allowlist (same as BEA-3).
ARM_METRIC_ALLOWLIST: tuple[str, ...] = (
    "file_recall@10",
    "mrr",
    "span_f0.5@10",
    "success_rate",
    "candidate_count_read",
    "evidence_budget_used",
    "action_steps",
    "latency_seconds",
    "quality_per_candidate",
    "quality_per_latency",
)

PRIMARY_METRICS: tuple[str, ...] = (
    "file_recall@10",
    "mrr",
    "span_f0.5@10",
    "success_rate",
)

# Worst-slice fixed public aggregate bucket labels.
WORST_SLICE_BUCKETS: tuple[str, ...] = (
    "benchmark",
    "query_length_bucket",
    "candidate_pool_size_bucket",
    "budget_exhaustion_bucket",
    "file_kind_mix_bucket",
    "method_agreement_bucket",
    "rank_gap_bucket",
)

# Safe true flags (only true when actually true).
SAFE_TRUE_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
    "external_benchmark_rows_read": False,
    "openlocus_retrieval_executed": False,
    "score_py_metrics_computed": False,
    "bea_v03_policy_executed": False,
    "bea_v02_policy_executed": False,
    "bea_v0_acquisition_performed": False,
    "scale_slice_read": False,
    "worst_slice_aggregated": False,
    "private_score_records_written": False,
}

# No-claim / no-runtime-change flags (all false).
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
    # BEA-4 binding: the v0.3 algorithm/weights MUST NOT change during BEA-4.
    "algorithm_changed_during_bea4": False,
    "weights_tuned_during_bea4": False,
}

LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication": "aggregate_only_smoke",
}

FAILURE_CATEGORIES: tuple[str, ...] = (
    "contextbench_fetch_failed",
    "contextbench_no_python_rows",
    "contextbench_gold_parse_failed",
    "repoqa_asset_download_failed",
    "repoqa_asset_decompress_failed",
    "repoqa_asset_parse_failed",
    "repoqa_no_python_needles",
    "repoqa_needle_parse_failed",
    "heldout_offset_exceeds_available",
    "repo_clone_failed",
    "repo_checkout_failed",
    "retrieval_failed",
    "score_failed",
    "private_score_write_failed",
    "record_excluded_from_paired_denominator",
    "row_limit_capped",
    "needle_limit_capped",
    "scanner_self_test_failed",
    "forbidden_leak_blocked",
    "unexpected_exception",
)

# ---------------------------------------------------------------------------
# Scanner (BEA-4 owned, strict, fail-closed). Extends BEA-3.
# ---------------------------------------------------------------------------

BEA4_FORBIDDEN_EXTRA_KEYS: frozenset[str] = frozenset(
    {
        # Private SCORE/private state fields.
        "action_order", "priority_components", "priority_score",
        "selected_decisions", "budget_trace", "stop_reason",
        "candidate_features", "anchor_eligibility",
        "anchor_slots", "early_stop_reason",
        "private_score_path", "score_path", "private_score_file",
        "private_record_id", "private_record_hash",
        "action_trace", "action_steps_trace",
        "budget_state", "budget_states",
        "accepted_candidates", "final_candidates",
        "candidate_list", "candidates", "score_outcome",
        "per_record_metrics", "runtime_query_features",
        "query_feature_summary", "query_features",
        "benchmark_row_id", "benchmark_record_id", "benchmark_label",
        "phase_run_id", "run_id", "task_id", "row_id", "needle_id",
        "instance_id", "provider_name", "model_name", "model_family",
        "provider_payload", "private_bucket", "route_bucket", "task_bucket",
        # Recommendation / policy / calibration / method-winner fields.
        "calibration", "method_winner", "best_method",
        "recommended_default", "recommended_method", "preferred_method",
        "default_method", "policy_decision", "decision", "ranking",
        "rank", "winner", "leaderboard", "promotion",
        # Worst-slice private identifiers.
        "worst_slice_record_id", "slice_label", "slice_id",
        "worst_slice_label", "slice_record_ids", "slice_member_ids",
    }
)


def _is_bea4_schema_key_container(path: str) -> bool:
    """Allow fixed bucket labels as child keys of schema containers."""
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in (
        "failure_category_counts", "benchmark_arm_metric_records",
        "delta_records", "win_tie_loss_records",
        "worst_slice_records", "mechanism_summary_records",
        "private_score_manifest", "framing", "arm_metric_records",
    )


def _scan_bea4_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                is_container = _is_bea4_schema_key_container(sub_path)
                if (key_str in BEA4_FORBIDDEN_EXTRA_KEYS
                        and not is_container):
                    violations.append({
                        "category": "forbidden_bea4_extra_key",
                        "path": sub_path,
                    })
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


def _scan_bea4(obj: Any) -> list[dict[str, Any]]:
    """Combined BEA-4 scanner: BEA-3 primitives + BEA-4 forbidden keys."""
    violations = bea3._scan_bea3(obj)
    violations.extend(_scan_bea4_forbidden_keys(obj))
    return violations


def _bea4_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_bea4(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_bea4_no_forbidden(obj: Any) -> None:
    scan = _bea4_forbidden_scan_summary(obj)
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


def _validate_row_offset(offset: int) -> int:
    if not isinstance(offset, int) or offset < 0:
        raise SystemExit("invalid arguments")
    return offset


def _validate_needle_offset(offset: int) -> int:
    if not isinstance(offset, int) or offset < 0:
        raise SystemExit("invalid arguments")
    return offset


def _validate_row_limit(limit: int) -> int:
    if not isinstance(limit, int) or limit < 1:
        raise SystemExit("invalid arguments")
    if limit > CONTEXTBENCH_ROW_LIMIT_HARD_CAP:
        return CONTEXTBENCH_ROW_LIMIT_HARD_CAP
    return limit


def _validate_needle_limit(limit: int) -> int:
    if not isinstance(limit, int) or limit < 1:
        raise SystemExit("invalid arguments")
    if limit > REPOQA_NEEDLE_LIMIT_HARD_CAP:
        return REPOQA_NEEDLE_LIMIT_HARD_CAP
    return limit


def _validate_budget(budget: int) -> int:
    if not isinstance(budget, int) or budget < 1:
        raise SystemExit("invalid arguments")
    if budget > BUDGET_HARD_CAP:
        return BUDGET_HARD_CAP
    return budget


def _validate_methods(methods: str) -> tuple[str, ...]:
    return bea0._validate_methods(methods)


# ---------------------------------------------------------------------------
# Private SCORE writer
# ---------------------------------------------------------------------------


def _resolve_private_score_dir(explicit: str | None) -> tuple[Path, str]:
    return bea0._resolve_private_score_dir(explicit)


def _private_score_manifest_hash() -> str:
    manifest_schema = {
        "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
        "fields": [
            "phase_run_id", "benchmark", "private_record_id",
            "policy_arm", "runtime_query_feature_summary",
            "candidate_features", "anchor_eligibility",
            "priority_components", "selected_decisions",
            "action_order", "budget_trace", "anchor_slots",
            "early_stop_reason", "score_outcome",
            "worst_slice_bucket_tuple",
            "latency_ms", "cost_usd", "tokens", "provider_calls",
            "failure_reason",
        ],
    }
    canonical = json.dumps(manifest_schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_private_score_row(score_path: Path, row: dict[str, Any]) -> None:
    bea0._write_private_score_row(score_path, row)


# ---------------------------------------------------------------------------
# Worst-slice bucket helpers (runtime-clean, deterministic)
# ---------------------------------------------------------------------------


def _query_length_bucket(query: str) -> str:
    """Bucket queries by word count. Runtime-clean (uses only query length)."""
    if not isinstance(query, str) or not query:
        return "empty"
    wc = len(query.split())
    if wc < 10:
        return "short"
    if wc <= 30:
        return "medium"
    return "long"


def _candidate_pool_size_bucket(deduped_count: int) -> str:
    """Bucket candidate pool sizes. Runtime-clean."""
    if not isinstance(deduped_count, int) or deduped_count <= 0:
        return "empty"
    if deduped_count < 5:
        return "small"
    if deduped_count <= 20:
        return "medium"
    return "large"


def _budget_exhaustion_bucket(budget_used: int, budget: int) -> str:
    """Bucket budget exhaustion. Runtime-clean."""
    if not isinstance(budget_used, int) or budget_used <= 0:
        return "empty"
    if budget <= 0:
        return "empty"
    if budget_used >= budget:
        return "full"
    return "partial"


def _file_kind_mix_bucket(accepted_evidence: list[dict[str, Any]]) -> str:
    """Bucket file-kind mix from accepted evidence paths. Runtime-clean."""
    if not accepted_evidence:
        return "empty"
    py_count = 0
    non_py_count = 0
    for entry in accepted_evidence:
        path = entry.get("path", "") if isinstance(entry, dict) else ""
        if not isinstance(path, str) or not path:
            continue
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if ext == "py":
            py_count += 1
        else:
            non_py_count += 1
    total = py_count + non_py_count
    if total == 0:
        return "empty"
    if py_count == total:
        return "pure_python"
    if non_py_count == total:
        return "non_python"
    return "mixed"


def _method_agreement_bucket(per_record_agreement: list[int]) -> str:
    """Bucket method agreement across accepted candidates. Runtime-clean."""
    if not per_record_agreement:
        return "empty"
    avg = sum(per_record_agreement) / len(per_record_agreement)
    if avg >= 2.5:
        return "high"
    if avg >= 1.5:
        return "medium"
    return "low"


def _rank_gap_bucket(per_record_ranks: list[int]) -> str:
    """Bucket rank gaps (max rank - min rank) for accepted candidates."""
    if not per_record_ranks:
        return "empty"
    rmin = min(per_record_ranks)
    rmax = max(per_record_ranks)
    gap = rmax - rmin
    if gap <= 3:
        return "narrow"
    if gap <= 10:
        return "medium"
    return "wide"


def _compute_record_bucket_tuple(
    *,
    benchmark: str,
    query: str,
    deduped_count: int,
    budget_used: int,
    budget: int,
    accepted_evidence: list[dict[str, Any]],
    per_record_agreement: list[int],
    per_record_ranks: list[int],
) -> dict[str, str]:
    """Compute the 7-bucket tuple for one record. Runtime-clean only."""
    return {
        "benchmark": benchmark,
        "query_length_bucket": _query_length_bucket(query),
        "candidate_pool_size_bucket": _candidate_pool_size_bucket(
            deduped_count
        ),
        "budget_exhaustion_bucket": _budget_exhaustion_bucket(
            budget_used, budget
        ),
        "file_kind_mix_bucket": _file_kind_mix_bucket(accepted_evidence),
        "method_agreement_bucket": _method_agreement_bucket(
            per_record_agreement
        ),
        "rank_gap_bucket": _rank_gap_bucket(per_record_ranks),
    }


# ---------------------------------------------------------------------------
# Public record builders (records-only; no dynamic arm dicts)
# ---------------------------------------------------------------------------


def _arm_means(per_record_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute mean across per-record metrics for one arm."""
    if not per_record_metrics:
        return {k: 0.0 for k in ARM_METRIC_ALLOWLIST}
    means: dict[str, Any] = {}
    for key in ARM_METRIC_ALLOWLIST:
        vals = [
            float(r[key]) for r in per_record_metrics
            if key in r and isinstance(r[key], (int, float))
        ]
        if vals:
            means[key] = round(sum(vals) / len(vals), 6)
        else:
            means[key] = 0.0
    return means


def _benchmark_arm_metric_records(
    per_benchmark_arm_aggs: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Build benchmark × arm × metric records."""
    records: list[dict[str, Any]] = []
    for benchmark in sorted(per_benchmark_arm_aggs.keys()):
        arm_aggs = per_benchmark_arm_aggs[benchmark]
        for arm_id in sorted(arm_aggs.keys()):
            agg = arm_aggs[arm_id]
            rc = int(agg.get("__record_count__", 0))
            for metric in ARM_METRIC_ALLOWLIST:
                value = agg.get(metric, 0.0)
                records.append({
                    "benchmark": benchmark,
                    "arm": arm_id,
                    "metric": metric,
                    "value": float(value) if isinstance(value, (int, float)) else 0.0,
                    "record_count": rc,
                })
    records.sort(key=lambda r: (r["benchmark"], r["arm"], r["metric"]))
    return records


def _delta_records(
    arm_aggs: dict[str, dict[str, Any]],
    baseline_arm: str,
    treatment_arms: list[str],
) -> list[dict[str, Any]]:
    """Build delta records (treatment - baseline) per metric."""
    records: list[dict[str, Any]] = []
    if baseline_arm not in arm_aggs:
        return records
    for treatment in treatment_arms:
        if treatment not in arm_aggs:
            continue
        for metric in ARM_METRIC_ALLOWLIST:
            b = float(arm_aggs[baseline_arm].get(metric, 0.0))
            t = float(arm_aggs[treatment].get(metric, 0.0))
            records.append({
                "baseline_arm": baseline_arm,
                "treatment_arm": treatment,
                "metric": metric,
                "delta": round(t - b, 6),
            })
    records.sort(key=lambda r: (r["baseline_arm"], r["treatment_arm"], r["metric"]))
    return records


def _win_tie_loss_records(
    per_record_arm_metrics: list[dict[str, dict[str, Any]]],
    baseline_arm: str,
    treatment_arm: str,
) -> list[dict[str, Any]]:
    """Build win/tie/loss records on primary metrics, paired denominator."""
    records: list[dict[str, Any]] = []
    paired: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for rec in per_record_arm_metrics:
        if baseline_arm in rec and treatment_arm in rec:
            paired.append((rec[baseline_arm], rec[treatment_arm]))
    record_count = len(paired)
    if record_count == 0:
        return records
    for metric in PRIMARY_METRICS:
        win = tie = loss = 0
        for b, t in paired:
            bv = b.get(metric, 0.0)
            tv = t.get(metric, 0.0)
            if not isinstance(bv, (int, float)) or not isinstance(tv, (int, float)):
                continue
            if tv > bv:
                win += 1
            elif tv < bv:
                loss += 1
            else:
                tie += 1
        records.append({
            "baseline_arm": baseline_arm,
            "treatment_arm": treatment_arm,
            "metric": metric,
            "win": win,
            "tie": tie,
            "loss": loss,
            "record_count": record_count,
        })
    records.sort(key=lambda r: r["metric"])
    return records


def _worst_slice_records(
    per_record_buckets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build worst-slice records from per-record bucket tuples.

    Each per_record_buckets entry has:
      ``bucket_tuple``: dict with the 7 fixed bucket labels
      ``arm``: treatment arm id
      ``metrics``: dict of arm metrics for this record

    Groups by (benchmark, arm, query_length_bucket,
    candidate_pool_size_bucket, budget_exhaustion_bucket,
    file_kind_mix_bucket, method_agreement_bucket, rank_gap_bucket).
    Each group is one slice. Computes mean metrics per slice.
    Emits the worst N slices per benchmark (sorted ascending by
    span_f0.5@10, then mrr). All bucket labels are fixed public aggregate
    labels; NO row IDs, repos, paths, commits, queries, labels, candidate
    lists, or gold/source snippets.
    """
    if not per_record_buckets:
        return []
    # Group by (benchmark, arm, all 7 bucket labels).
    groups: dict[tuple, list[dict[str, Any]]] = {}
    for rec in per_record_buckets:
        bt = rec["bucket_tuple"]
        key = (
            bt["benchmark"],
            rec["arm"],
            bt["query_length_bucket"],
            bt["candidate_pool_size_bucket"],
            bt["budget_exhaustion_bucket"],
            bt["file_kind_mix_bucket"],
            bt["method_agreement_bucket"],
            bt["rank_gap_bucket"],
        )
        groups.setdefault(key, []).append(rec)

    slice_records: list[dict[str, Any]] = []
    for key, recs in groups.items():
        benchmark, arm = key[0], key[1]
        n = len(recs)
        means: dict[str, float] = {}
        for metric in ARM_METRIC_ALLOWLIST:
            vals = [
                float(r["metrics"].get(metric, 0.0))
                for r in recs
                if isinstance(r["metrics"].get(metric, 0.0), (int, float))
            ]
            if vals:
                means[metric] = round(sum(vals) / len(vals), 6)
            else:
                means[metric] = 0.0
        slice_records.append({
            "benchmark": benchmark,
            "arm": arm,
            "query_length_bucket": key[2],
            "candidate_pool_size_bucket": key[3],
            "budget_exhaustion_bucket": key[4],
            "file_kind_mix_bucket": key[5],
            "method_agreement_bucket": key[6],
            "rank_gap_bucket": key[7],
            "record_count": n,
            "file_recall@10": means.get("file_recall@10", 0.0),
            "mrr": means.get("mrr", 0.0),
            "span_f0.5@10": means.get("span_f0.5@10", 0.0),
            "success_rate": means.get("success_rate", 0.0),
            "evidence_budget_used": means.get("evidence_budget_used", 0.0),
            "latency_seconds": means.get("latency_seconds", 0.0),
            "quality_per_candidate": means.get("quality_per_candidate", 0.0),
            "quality_per_latency": means.get("quality_per_latency", 0.0),
        })

    # Worst slices: ascending by span_f0.5@10, then by mrr, then by
    # file_recall@10. Take top N per (benchmark, arm).
    slice_records.sort(
        key=lambda r: (
            r["benchmark"], r["arm"],
            r["span_f0.5@10"], r["mrr"], r["file_recall@10"],
        )
    )
    worst: list[dict[str, Any]] = []
    seen_per_benchmark_arm: dict[tuple, int] = {}
    for rec in slice_records:
        bk = (rec["benchmark"], rec["arm"])
        if seen_per_benchmark_arm.get(bk, 0) >= WORST_SLICE_MAX_PER_BENCHMARK:
            continue
        worst.append(rec)
        seen_per_benchmark_arm[bk] = seen_per_benchmark_arm.get(bk, 0) + 1
    worst.sort(key=lambda r: (r["benchmark"], r["arm"], r["span_f0.5@10"]))
    return worst


def _mechanism_summary_records(
    per_record_mechanism_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Reuse BEA-3 mechanism summary records builder."""
    return bea3._mechanism_summary_records(per_record_mechanism_summaries)


# ---------------------------------------------------------------------------
# Per-record evaluation (subset of BEA-3 arms; no ablations)
# ---------------------------------------------------------------------------


def _evaluate_record(
    *,
    openlocus_bin: str,
    benchmark: str,
    private_record_id: str,
    task_id: str,
    query: str,
    gold_paths: list[str],
    gold_lines: list[list[int]],
    repo_root: Path,
    methods: tuple[str, ...],
    budget: int,
    enable_rrf_baseline: bool,
    score_path: Path,
    phase_run_id: str,
    fcc: dict[str, int],
) -> tuple[dict[str, Any] | None, dict[str, int], dict[str, Any],
           list[dict[str, Any]]]:
    """Evaluate one record across the BEA-4 fixed arms (no ablations).

    Writes one private SCORE row PER policy arm. Returns:
      ``per_arm_metrics``: dict[arm_id -> metrics]
      ``fcc``: failure category counts (updated in place)
      ``rec_mechanism_summary``: dict for mechanism_summary_records
      ``per_arm_buckets``: list of {arm, bucket_tuple, metrics} for
                            worst_slice_records
    """
    rec_start = time.perf_counter()
    failure_reason: str | None = None

    method_candidates: dict[str, list[dict[str, Any]]] = {}
    method_latencies_ms: dict[str, int] = {}
    method_errors: dict[str, str] = {}
    all_candidates: list[dict[str, Any]] = []
    for method in methods:
        cands, lat_ms, err = bea0._collect_method_candidates(
            openlocus_bin, method, query, repo_root
        )
        method_candidates[method] = cands
        method_latencies_ms[method] = lat_ms
        if not cands:
            method_errors[method] = err[:200] if err else "empty"
        else:
            all_candidates.extend(cands)

    rrf_candidates: list[dict[str, Any]] = []
    rrf_latency_ms = 0
    rrf_error: str | None = None
    if enable_rrf_baseline:
        channels = ",".join(methods)
        rrf_candidates, rrf_latency_ms, rrf_err = bea0._collect_rrf_candidates(
            openlocus_bin, query, repo_root, channels=channels
        )
        if not rrf_candidates:
            rrf_error = (rrf_err or "empty")[:200]

    if not all_candidates:
        failure_reason = "no_candidates_from_any_method"
        fcc["retrieval_failed"] = fcc.get("retrieval_failed", 0) + 1

    gold_record = {
        "task_id": task_id,
        "gold_paths": gold_paths,
        "gold_lines": gold_lines,
    }

    deduped_count = len(bea1._dedup_candidates(all_candidates)) if all_candidates else 0

    shared_retrieval_latency = sum(method_latencies_ms.values()) / 1000.0

    # --- v0.3 anchor/span/latency (treatment) ---
    policy_start = time.perf_counter()
    if all_candidates and failure_reason is None:
        v03_accepted, v03_action_order, v03_budget_trace, v03_stop_reason, v03_mech_summary = (
            bea3._bea_v0_3_policy(all_candidates, query, budget,
                                   use_anchor=True, use_early_stop=True)
        )
    else:
        v03_accepted, v03_action_order, v03_budget_trace, v03_stop_reason, v03_mech_summary = (
            [], [], [], "no_candidates_or_zero_budget",
            {"anchor_used": True, "early_stop_used": True,
             "anchor_count_reserved": 0, "anchor_count_filled": 0,
             "early_stop_reason": "", "mean_span_extent": 0.0,
             "span_proxy_bucket_counts": {}}
        )
    v03_policy_time = time.perf_counter() - policy_start
    v03_metrics = bea3._arm_metrics_for_record(
        ARM_BEA_V0_3, v03_accepted, gold_record, task_id,
        len(all_candidates), len(v03_accepted), len(v03_action_order),
        shared_retrieval_latency + v03_policy_time,
    )

    # --- v0.2 ---
    if all_candidates and failure_reason is None:
        v02_accepted, v02_action_order, v02_budget_trace, v02_stop_reason = (
            bea2._bea_v0_2_diversity_risk_policy(all_candidates, query, budget)
        )
    else:
        v02_accepted, v02_action_order, v02_budget_trace, v02_stop_reason = (
            [], [], [], "no_candidates_or_zero_budget"
        )
    v02_metrics = bea3._arm_metrics_for_record(
        ARM_BEA_V0_2, v02_accepted, gold_record, task_id,
        len(all_candidates), len(v02_accepted), len(v02_action_order),
        shared_retrieval_latency,
    )

    # --- v0 (BEA-0) ---
    if all_candidates and failure_reason is None:
        v0_accepted, v0_action_trace, v0_budget_states = (
            bea0._bea_v0_budgeted_policy(all_candidates, budget)
        )
    else:
        v0_accepted, v0_action_trace, v0_budget_states = [], [], []
    v0_metrics = bea3._arm_metrics_for_record(
        ARM_BEA_V0, v0_accepted, gold_record, task_id,
        len(all_candidates), len(v0_accepted), len(v0_action_trace),
        shared_retrieval_latency,
    )

    # --- Same-budget K (based on v0.3 accepted count) ---
    same_budget_k = bea2._same_budget_k(len(v03_accepted), deduped_count)

    # --- Controls ---
    sb_bm25_ev = bea2._bm25_prefix_same_budget_arm(method_candidates, same_budget_k)
    sb_bm25_metrics = bea3._arm_metrics_for_record(
        ARM_BM25_PREFIX, sb_bm25_ev, gold_record, task_id,
        len(method_candidates.get("bm25", [])),
        len(sb_bm25_ev), len(sb_bm25_ev), 0.0,
    )
    ao_ev = bea2._agreement_only_same_budget_arm(all_candidates, same_budget_k)
    ao_metrics = bea3._arm_metrics_for_record(
        ARM_AGREEMENT_ONLY, ao_ev, gold_record, task_id,
        len(all_candidates), len(ao_ev), len(ao_ev), 0.0,
    )
    sr_ev = bea2._seeded_random_same_budget_arm(all_candidates, same_budget_k)
    sr_metrics = bea3._arm_metrics_for_record(
        ARM_SEEDED_RANDOM, sr_ev, gold_record, task_id,
        len(all_candidates), len(sr_ev), len(sr_ev), 0.0,
    )
    rrf_metrics: dict[str, Any] | None = None
    rrf_ev: list[dict[str, Any]] = []
    if enable_rrf_baseline:
        rrf_ev = bea2._rrf_same_budget_arm(rrf_candidates, same_budget_k)
        rrf_metrics = bea3._arm_metrics_for_record(
            ARM_RRF_SAME_BUDGET, rrf_ev, gold_record, task_id,
            len(rrf_candidates), len(rrf_ev), len(rrf_ev),
            rrf_latency_ms / 1000.0,
        )

    per_arm_metrics: dict[str, dict[str, Any]] = {
        ARM_BEA_V0_3: v03_metrics,
        ARM_BEA_V0_2: v02_metrics,
        ARM_BEA_V0: v0_metrics,
        ARM_BM25_PREFIX: sb_bm25_metrics,
        ARM_AGREEMENT_ONLY: ao_metrics,
        ARM_SEEDED_RANDOM: sr_metrics,
    }
    if rrf_metrics is not None:
        per_arm_metrics[ARM_RRF_SAME_BUDGET] = rrf_metrics

    rec_latency_ms = int((time.perf_counter() - rec_start) * 1000)

    # --- Mechanism summary for this record (v0.3 only) ---
    rec_mechanism_summary = {
        "anchor_used": v03_mech_summary.get("anchor_used", False),
        "early_stop_used": bool(v03_mech_summary.get("early_stop_reason", "")),
        "budget_used": len(v03_accepted),
        "latency_ms": rec_latency_ms,
        "mean_span_extent": v03_mech_summary.get("mean_span_extent", 0.0),
        "span_proxy_bucket_counts": v03_mech_summary.get(
            "span_proxy_bucket_counts", {}
        ),
    }

    # --- Runtime query feature summary (private; never serialized publicly).
    runtime_query_feature_summary = {
        "benchmark": benchmark,
        "method_count": len(methods),
        "methods": list(methods),
        "candidate_count_total": len(all_candidates),
        "candidate_count_per_method": {
            m: len(method_candidates.get(m, [])) for m in methods
        },
        "rrf_baseline_enabled": bool(enable_rrf_baseline),
        "rrf_candidate_count": len(rrf_candidates) if enable_rrf_baseline else 0,
        "budget": int(budget),
        "same_budget_k": int(same_budget_k),
        "deduped_candidate_count": int(deduped_count),
        "v03_accepted_count": int(len(v03_accepted)),
        "v02_accepted_count": int(len(v02_accepted)),
        "v0_accepted_count": int(len(v0_accepted)),
        "shared_retrieval_latency_seconds": round(shared_retrieval_latency, 6),
        "query_length_chars": len(query) if isinstance(query, str) else 0,
        "query_word_count": (
            len(query.split()) if isinstance(query, str) and query else 0
        ),
    }

    # --- Compute per-arm bucket tuples for worst_slice_records ---
    per_arm_buckets: list[dict[str, Any]] = []

    def _agreement_and_ranks(accepted: list[dict[str, Any]],
                             all_cands: list[dict[str, Any]]) -> tuple[list[int], list[int]]:
        """Extract per-accepted-candidate agreement counts and ranks.
        Runtime-clean (uses only candidate metadata)."""
        # Build a lookup of (path, start, end) -> (rank, methods) per method.
        per_method_index: dict[str, dict[tuple, int]] = {}
        per_method_methods: dict[str, dict[tuple, set[str]]] = {}
        for c in all_cands:
            method = c.get("method", "")
            key = (c.get("path", ""), c.get("start_line", 0), c.get("end_line", 0))
            if method not in per_method_index:
                per_method_index[method] = {}
                per_method_methods[method] = {}
            if key not in per_method_index[method]:
                per_method_index[method][key] = c.get("rank", 0)
                per_method_methods[method][key] = {method}
            else:
                per_method_methods[method][key].add(method)
        agreements: list[int] = []
        ranks: list[int] = []
        for ev in accepted:
            key = (ev.get("path", ""), ev.get("start_line", 0), ev.get("end_line", 0))
            methods_set: set[str] = set()
            rank_min = 0
            for method in per_method_methods:
                if key in per_method_methods[method]:
                    methods_set |= per_method_methods[method][key]
                    r = per_method_index[method][key]
                    if rank_min == 0 or r < rank_min:
                        rank_min = r
            agreements.append(max(1, len(methods_set)))
            ranks.append(rank_min if rank_min > 0 else 1)
        return agreements, ranks

    v03_agr, v03_ranks = _agreement_and_ranks(v03_accepted, all_candidates)
    v02_agr, v02_ranks = _agreement_and_ranks(v02_accepted, all_candidates)
    v0_agr, v0_ranks = _agreement_and_ranks(v0_accepted, all_candidates)
    bm25_agr, bm25_ranks = _agreement_and_ranks(sb_bm25_ev, all_candidates)
    ao_agr, ao_ranks = _agreement_and_ranks(ao_ev, all_candidates)
    sr_agr, sr_ranks = _agreement_and_ranks(sr_ev, all_candidates)
    rrf_agr, rrf_ranks = ([], [])
    if enable_rrf_baseline:
        rrf_agr, rrf_ranks = _agreement_and_ranks(rrf_ev, all_candidates)

    arm_bucket_data = [
        (ARM_BEA_V0_3, v03_accepted, v03_metrics, v03_agr, v03_ranks),
        (ARM_BEA_V0_2, v02_accepted, v02_metrics, v02_agr, v02_ranks),
        (ARM_BEA_V0, v0_accepted, v0_metrics, v0_agr, v0_ranks),
        (ARM_BM25_PREFIX, sb_bm25_ev, sb_bm25_metrics, bm25_agr, bm25_ranks),
        (ARM_AGREEMENT_ONLY, ao_ev, ao_metrics, ao_agr, ao_ranks),
        (ARM_SEEDED_RANDOM, sr_ev, sr_metrics, sr_agr, sr_ranks),
    ]
    if enable_rrf_baseline and rrf_metrics is not None:
        arm_bucket_data.append(
            (ARM_RRF_SAME_BUDGET, rrf_ev, rrf_metrics, rrf_agr, rrf_ranks)
        )

    for arm_id, accepted, metrics, agr, ranks in arm_bucket_data:
        bt = _compute_record_bucket_tuple(
            benchmark=benchmark, query=query,
            deduped_count=deduped_count,
            budget_used=len(accepted), budget=budget,
            accepted_evidence=accepted,
            per_record_agreement=agr,
            per_record_ranks=ranks,
        )
        per_arm_buckets.append({
            "arm": arm_id,
            "bucket_tuple": bt,
            "metrics": metrics,
        })

    # --- Write one private SCORE row PER policy arm ---
    arms_to_write = [
        (ARM_BEA_V0_3, v03_action_order, v03_budget_trace,
         v03_stop_reason, v03_metrics, v03_mech_summary, v03_accepted),
        (ARM_BEA_V0_2, v02_action_order, v02_budget_trace,
         v02_stop_reason, v02_metrics, {}, v02_accepted),
        (ARM_BEA_V0, v0_action_trace, v0_budget_states,
         "v0_policy", v0_metrics, {}, v0_accepted),
        (ARM_BM25_PREFIX, [], [],
         "same_budget_bm25_prefix", sb_bm25_metrics, {}, sb_bm25_ev),
        (ARM_AGREEMENT_ONLY, [], [],
         "same_budget_agreement", ao_metrics, {}, ao_ev),
        (ARM_SEEDED_RANDOM, [], [],
         "same_budget_seeded_random", sr_metrics, {}, sr_ev),
    ]
    if rrf_metrics is not None:
        arms_to_write.append((
            ARM_RRF_SAME_BUDGET, [], [],
            "same_budget_rrf", rrf_metrics, {}, rrf_ev,
        ))

    # Find this arm's bucket tuple for the private SCORE row.
    arm_to_bucket = {ab["arm"]: ab["bucket_tuple"] for ab in per_arm_buckets}

    for arm_id, action_order, budget_trace, stop_reason, score_outcome, mech_summary, accepted in arms_to_write:
        # Compute per-arm bucket tuple (private; never serialized publicly).
        bt = arm_to_bucket.get(arm_id, {})
        private_score_row = {
            "phase_run_id": phase_run_id,
            "benchmark": benchmark,
            "private_record_id": private_record_id,
            "policy_arm": arm_id,
            "runtime_query_feature_summary": runtime_query_feature_summary,
            "candidate_features": [],
            "anchor_eligibility": (
                {k: v for k, v in mech_summary.items()
                 if k in ("anchor_used", "anchor_count_reserved",
                          "anchor_count_filled", "early_stop_reason")}
                if mech_summary else {}
            ),
            "priority_components": (
                [{"step": a.get("step", i), "priority_score": a.get("priority_score", 0.0),
                  "priority_components": a.get("priority_components", {})}
                 for i, a in enumerate(action_order) if a.get("action") == "accept_candidate"]
                if action_order else []
            ),
            "selected_decisions": [
                {"step": a.get("step", i), "action": a.get("action", ""),
                 "priority_score": a.get("priority_score", 0.0)}
                for i, a in enumerate(action_order)
            ] if action_order else [],
            "action_order": action_order,
            "budget_trace": budget_trace,
            "anchor_slots": mech_summary.get("anchor_count_filled", 0) if mech_summary else 0,
            "early_stop_reason": mech_summary.get("early_stop_reason", "") if mech_summary else "",
            "stop_reason": stop_reason,
            "score_outcome": score_outcome,
            "worst_slice_bucket_tuple": bt,
            "latency_ms": rec_latency_ms,
            "cost_usd": 0.0,
            "tokens": 0,
            "provider_calls": 0,
            "failure_reason": failure_reason,
        }
        try:
            _write_private_score_row(score_path, private_score_row)
        except OSError:
            fcc["private_score_write_failed"] = (
                fcc.get("private_score_write_failed", 0) + 1
            )
            return None, fcc, rec_mechanism_summary, per_arm_buckets

    return per_arm_metrics, fcc, rec_mechanism_summary, per_arm_buckets


# ---------------------------------------------------------------------------
# Heldout fetchers (reuse BEA-3)
# ---------------------------------------------------------------------------


def _fetch_heldout_contextbench_rows(
    row_offset: int, row_limit: int,
) -> tuple[list[dict[str, Any]], str, int, dict[str, int]]:
    return bea3._fetch_heldout_contextbench_rows(row_offset, row_limit)


def _fetch_heldout_repoqa_needles(
    needle_offset: int, needle_limit: int,
) -> tuple[list[dict[str, Any]], str, int, dict[str, int]]:
    return bea3._fetch_heldout_repoqa_needles(needle_offset, needle_limit)


# ---------------------------------------------------------------------------
# Public report builders
# ---------------------------------------------------------------------------


def _build_unavailable_report(
    failure_reason_category: str,
    *,
    self_test_passed: bool,
    self_test_checks_total: int = SELF_TEST_CHECKS_EXPECTED,
    self_test_checks_passed: int | None = None,
    contextbench_row_offset_requested: int,
    contextbench_row_limit_requested: int,
    repoqa_needle_offset_requested: int,
    repoqa_needle_limit_requested: int,
    budget: int,
    methods: tuple[str, ...],
    openlocus_binary_source: str,
    network_mode: str,
    private_score_records_written: bool = False,
    private_score_record_count: int = 0,
    private_score_storage_class: str = "tmp_private",
    private_score_manifest_hash: str | None = None,
    records_evaluated: int = 0,
    records_successful: int = 0,
    records_failed: int = 0,
    network_calls: int = 0,
    failure_category_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    if failure_category_counts:
        for k, v in failure_category_counts.items():
            if k in fcc:
                fcc[k] = int(v)
    if failure_reason_category in fcc:
        fcc[failure_reason_category] = max(fcc[failure_reason_category], 1)

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["external_benchmark_rows_read"] = records_evaluated > 0
    safe_true["bea_v03_policy_executed"] = False
    safe_true["bea_v02_policy_executed"] = False
    safe_true["bea_v0_acquisition_performed"] = False
    safe_true["scale_slice_read"] = False
    safe_true["worst_slice_aggregated"] = False
    safe_true["private_score_records_written"] = bool(private_score_records_written)

    manifest_hash = (
        private_score_manifest_hash
        if private_score_manifest_hash is not None
        else _private_score_manifest_hash()
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": "unavailable_with_reason",
        "mode": MODE,
        "phase": PHASE,
        "methods": list(methods),
        "budget": int(budget),
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "contextbench_row_offset_requested": contextbench_row_offset_requested,
        "contextbench_row_limit_requested": contextbench_row_limit_requested,
        "repoqa_needle_offset_requested": repoqa_needle_offset_requested,
        "repoqa_needle_limit_requested": repoqa_needle_limit_requested,
        "records_evaluated": records_evaluated,
        "records_successful": records_successful,
        "records_failed": records_failed,
        "network_calls": network_calls,
        "provider_calls": 0,
        "failure_reason_category": failure_reason_category,
        "failure_category_counts": fcc,
        "benchmark_arm_metric_records": [],
        "delta_records": [],
        "win_tie_loss_records": [],
        "worst_slice_records": [],
        "mechanism_summary_records": [],
        "private_score_manifest": {
            "records_written": bool(private_score_records_written),
            "record_count": int(private_score_record_count),
            "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
            "manifest_hash": manifest_hash,
            "storage_class": private_score_storage_class,
            "path_publicly_serialized": False,
        },
        **safe_true,
        **DEFAULT_FALSE_FLAGS,
        **LICENSE_FIELDS,
        "self_test_passed": self_test_passed,
        "self_test_checks_total": int(self_test_checks_total),
        "self_test_checks_passed": int(
            self_test_checks_total if self_test_checks_passed is None and self_test_passed
            else (self_test_checks_passed or 0)
        ),
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "calibration_claimed": False,
            "method_winner_claimed": False,
            "signal_strength": "bea_v03_external_scale_smoke_unavailable",
            "is_full_external_benchmark_evaluation": False,
        },
    }
    scan = _bea4_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _build_pass_report(
    *,
    self_test_passed: bool,
    self_test_checks_total: int = SELF_TEST_CHECKS_EXPECTED,
    self_test_checks_passed: int | None = None,
    contextbench_row_offset_requested: int,
    contextbench_row_limit_requested: int,
    repoqa_needle_offset_requested: int,
    repoqa_needle_limit_requested: int,
    budget: int,
    methods: tuple[str, ...],
    openlocus_binary_source: str,
    network_mode: str,
    records_evaluated: int,
    records_successful: int,
    records_failed: int,
    network_calls: int,
    arm_aggs: dict[str, dict[str, Any]],
    per_record_arm_metrics: list[dict[str, dict[str, Any]]],
    per_benchmark_arm_aggs: dict[str, dict[str, dict[str, Any]]],
    per_record_mechanism_summaries: list[dict[str, Any]],
    per_record_buckets: list[dict[str, Any]],
    private_score_records_written: bool,
    private_score_record_count: int,
    private_score_storage_class: str,
    private_score_manifest_hash: str,
    aggregate_runtime_seconds: float,
    failure_category_counts: dict[str, int],
    enable_rrf_baseline: bool,
    paired_exclusion_count: int,
    partial: bool,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    for k, v in failure_category_counts.items():
        if k in fcc:
            fcc[k] = int(v)

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["external_benchmark_rows_read"] = records_evaluated > 0
    safe_true["openlocus_retrieval_executed"] = records_successful > 0
    safe_true["score_py_metrics_computed"] = bool(arm_aggs)
    safe_true["bea_v03_policy_executed"] = records_successful > 0
    safe_true["bea_v02_policy_executed"] = records_successful > 0
    safe_true["bea_v0_acquisition_performed"] = records_successful > 0
    safe_true["scale_slice_read"] = records_evaluated > 0
    safe_true["worst_slice_aggregated"] = bool(per_record_buckets)
    safe_true["private_score_records_written"] = bool(private_score_records_written)

    benchmark_arm_metric_records = _benchmark_arm_metric_records(per_benchmark_arm_aggs)

    # Delta records: v0.3 vs each required control (bm25, agreement, rrf,
    # v0.2, v0, random). v0 is the fixed baseline arm for delta_records.
    required_controls = [
        ARM_BM25_PREFIX,
        ARM_AGREEMENT_ONLY,
        ARM_BEA_V0_2,
        ARM_BEA_V0,
        ARM_SEEDED_RANDOM,
    ]
    if enable_rrf_baseline:
        required_controls.append(ARM_RRF_SAME_BUDGET)
    delta_records = _delta_records(arm_aggs, BASELINE_ARM, [TREATMENT_ARM])
    for control in required_controls:
        delta_records.extend(
            _delta_records(arm_aggs, control, [TREATMENT_ARM])
        )
    delta_records.sort(key=lambda r: (r["baseline_arm"], r["treatment_arm"], r["metric"]))

    # Win/tie/loss records: v0.3 vs each required control on primary metrics.
    win_tie_loss_records: list[dict[str, Any]] = []
    for baseline in required_controls:
        win_tie_loss_records.extend(_win_tie_loss_records(
            per_record_arm_metrics, baseline, TREATMENT_ARM
        ))
    win_tie_loss_records.sort(key=lambda r: (r["baseline_arm"], r["metric"]))

    # Worst-slice records: from per-record bucket tuples (one per
    # record × arm). Public bucket labels only.
    worst_slice_records = _worst_slice_records(per_record_buckets)

    mechanism_summary_records = _mechanism_summary_records(per_record_mechanism_summaries)

    if records_successful > 0 and records_failed == 0 and not partial:
        status = "bea4_external_scale_smoke_pass"
    elif records_successful > 0:
        status = "partial"
    else:
        status = "unavailable_with_reason"

    fixed_arms = [
        ARM_BEA_V0_3,
        ARM_BEA_V0_2,
        ARM_BEA_V0,
        ARM_BM25_PREFIX,
        ARM_AGREEMENT_ONLY,
        ARM_SEEDED_RANDOM,
    ]
    if enable_rrf_baseline:
        fixed_arms.append(ARM_RRF_SAME_BUDGET)

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "methods": list(methods),
        "budget": int(budget),
        "enable_rrf_baseline": bool(enable_rrf_baseline),
        "fixed_arms": fixed_arms,
        "baseline_arm": BASELINE_ARM,
        "treatment_arm": TREATMENT_ARM,
        "seeded_random_seed": SEEDED_RANDOM_SEED,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "contextbench_row_offset_requested": contextbench_row_offset_requested,
        "contextbench_row_limit_requested": contextbench_row_limit_requested,
        "repoqa_needle_offset_requested": repoqa_needle_offset_requested,
        "repoqa_needle_limit_requested": repoqa_needle_limit_requested,
        "records_evaluated": records_evaluated,
        "records_successful": records_successful,
        "records_failed": records_failed,
        "paired_exclusion_count": int(paired_exclusion_count),
        "network_calls": network_calls,
        "provider_calls": 0,
        "benchmark_arm_metric_records": benchmark_arm_metric_records,
        "delta_records": delta_records,
        "win_tie_loss_records": win_tie_loss_records,
        "worst_slice_records": worst_slice_records,
        "mechanism_summary_records": mechanism_summary_records,
        "private_score_manifest": {
            "records_written": bool(private_score_records_written),
            "record_count": int(private_score_record_count),
            "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
            "manifest_hash": private_score_manifest_hash,
            "storage_class": private_score_storage_class,
            "path_publicly_serialized": False,
        },
        "aggregate_runtime_seconds": round(float(aggregate_runtime_seconds), 3),
        "failure_category_counts": fcc,
        **safe_true,
        **DEFAULT_FALSE_FLAGS,
        **LICENSE_FIELDS,
        "self_test_passed": self_test_passed,
        "self_test_checks_total": int(self_test_checks_total),
        "self_test_checks_passed": int(
            self_test_checks_total if self_test_checks_passed is None and self_test_passed
            else (self_test_checks_passed or 0)
        ),
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_proven": False,
            "calibration_claimed": False,
            "method_winner_claimed": False,
            "signal_strength": "bea_v03_external_scale_smoke_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
        },
    }
    scan = _bea4_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _build_synthetic_candidates() -> list[dict[str, Any]]:
    return bea0._build_synthetic_candidates()


def _build_synthetic_gold() -> dict[str, Any]:
    return bea0._build_synthetic_gold()


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []

    candidates = _build_synthetic_candidates()
    gold = _build_synthetic_gold()
    query = "merge adjacent strings into a single string"

    # Run v0.3 (frozen; same as BEA-3).
    v03_acc, v03_ao, v03_bt, v03_sr, v03_ms = bea3._bea_v0_3_policy(
        candidates, query, 5, use_anchor=True, use_early_stop=True
    )
    # Run v0.2.
    v02_acc, v02_ao, v02_bt, v02_sr = bea2._bea_v0_2_diversity_risk_policy(
        candidates, query, 5
    )
    # Run v0.
    v0_acc, v0_at, v0_bs = bea0._bea_v0_budgeted_policy(candidates, 5)

    deduped_count = len(bea1._dedup_candidates(candidates))
    same_budget_k = bea2._same_budget_k(len(v03_acc), deduped_count)
    sb_bm25_ev = bea2._bm25_prefix_same_budget_arm(
        {"bm25": [c for c in candidates if c["method"] == "bm25"]}, same_budget_k)
    ao_ev = bea2._agreement_only_same_budget_arm(candidates, same_budget_k)
    sr_ev = bea2._seeded_random_same_budget_arm(candidates, same_budget_k)

    v03_m = bea3._arm_metrics_for_record(
        ARM_BEA_V0_3, v03_acc, gold, "bea4-st", len(candidates),
        len(v03_acc), len(v03_ao), 0.05)
    v02_m = bea3._arm_metrics_for_record(
        ARM_BEA_V0_2, v02_acc, gold, "bea4-st", len(candidates),
        len(v02_acc), len(v02_ao), 0.04)
    v0_m = bea3._arm_metrics_for_record(
        ARM_BEA_V0, v0_acc, gold, "bea4-st", len(candidates),
        len(v0_acc), len(v0_at), 0.03)
    sb_m = bea3._arm_metrics_for_record(
        ARM_BM25_PREFIX, sb_bm25_ev, gold, "bea4-st",
        len(candidates), len(sb_bm25_ev), len(sb_bm25_ev), 0.0)
    ao_m = bea3._arm_metrics_for_record(
        ARM_AGREEMENT_ONLY, ao_ev, gold, "bea4-st",
        len(candidates), len(ao_ev), len(ao_ev), 0.0)
    sr_m = bea3._arm_metrics_for_record(
        ARM_SEEDED_RANDOM, sr_ev, gold, "bea4-st",
        len(candidates), len(sr_ev), len(sr_ev), 0.0)

    rrf_m = dict(v03_m)
    arm_aggs = {
        ARM_BEA_V0_3: _arm_means([v03_m]),
        ARM_BEA_V0_2: _arm_means([v02_m]),
        ARM_BEA_V0: _arm_means([v0_m]),
        ARM_BM25_PREFIX: _arm_means([sb_m]),
        ARM_AGREEMENT_ONLY: _arm_means([ao_m]),
        ARM_SEEDED_RANDOM: _arm_means([sr_m]),
        ARM_RRF_SAME_BUDGET: _arm_means([rrf_m]),
    }
    per_record_arm_metrics = [{
        ARM_BEA_V0_3: v03_m, ARM_BEA_V0_2: v02_m, ARM_BEA_V0: v0_m,
        ARM_BM25_PREFIX: sb_m, ARM_AGREEMENT_ONLY: ao_m,
        ARM_SEEDED_RANDOM: sr_m, ARM_RRF_SAME_BUDGET: rrf_m,
    }]
    per_benchmark_arm_aggs = {
        "contextbench": {
            arm_id: {**_arm_means([m]), "__record_count__": 1}
            for arm_id, m in [
                (ARM_BEA_V0_3, v03_m), (ARM_BEA_V0_2, v02_m),
                (ARM_BEA_V0, v0_m), (ARM_BM25_PREFIX, sb_m),
                (ARM_AGREEMENT_ONLY, ao_m), (ARM_SEEDED_RANDOM, sr_m),
                (ARM_RRF_SAME_BUDGET, rrf_m),
            ]
        },
    }

    # Build synthetic per-record buckets for worst_slice_records testing.
    per_record_buckets: list[dict[str, Any]] = []
    for arm_id, metrics in [
        (ARM_BEA_V0_3, v03_m), (ARM_BEA_V0_2, v02_m),
        (ARM_BEA_V0, v0_m), (ARM_BM25_PREFIX, sb_m),
        (ARM_AGREEMENT_ONLY, ao_m), (ARM_SEEDED_RANDOM, sr_m),
        (ARM_RRF_SAME_BUDGET, rrf_m),
    ]:
        bt = _compute_record_bucket_tuple(
            benchmark="contextbench", query=query,
            deduped_count=deduped_count,
            budget_used=len(v03_acc), budget=5,
            accepted_evidence=v03_acc if arm_id == ARM_BEA_V0_3 else [],
            per_record_agreement=[2, 1, 3][:len(v03_acc)],
            per_record_ranks=[1, 5, 2][:len(v03_acc)],
        )
        per_record_buckets.append({
            "arm": arm_id, "bucket_tuple": bt, "metrics": metrics,
        })

    per_record_mechanism_summaries = [{
        "anchor_used": True, "early_stop_used": False,
        "budget_used": len(v03_acc), "latency_ms": 50,
        "mean_span_extent": v03_ms.get("mean_span_extent", 0.0),
        "span_proxy_bucket_counts": v03_ms.get("span_proxy_bucket_counts", {}),
    }]

    skeleton = _build_pass_report(
        self_test_passed=True,
        contextbench_row_offset_requested=80,
        contextbench_row_limit_requested=3,
        repoqa_needle_offset_requested=40,
        repoqa_needle_limit_requested=2,
        budget=5, methods=("bm25", "regex", "symbol"),
        openlocus_binary_source="self_test",
        network_mode="self_test",
        records_evaluated=1, records_successful=1, records_failed=0,
        network_calls=0, arm_aggs=arm_aggs,
        per_record_arm_metrics=per_record_arm_metrics,
        per_benchmark_arm_aggs=per_benchmark_arm_aggs,
        per_record_mechanism_summaries=per_record_mechanism_summaries,
        per_record_buckets=per_record_buckets,
        private_score_records_written=True,
        private_score_record_count=7,
        private_score_storage_class="tmp_private",
        private_score_manifest_hash=_private_score_manifest_hash(),
        aggregate_runtime_seconds=0.5,
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES},
        enable_rrf_baseline=True,
        paired_exclusion_count=0, partial=False,
    )
    unavail = _build_unavailable_report(
        "retrieval_failed", self_test_passed=True,
        contextbench_row_offset_requested=80,
        contextbench_row_limit_requested=3,
        repoqa_needle_offset_requested=40,
        repoqa_needle_limit_requested=2,
        budget=5, methods=("bm25", "regex", "symbol"),
        openlocus_binary_source="self_test",
        network_mode="self_test",
    )

    # Group 1: Identity.
    checks.append(_check("schema_version", skeleton["schema_version"] == SCHEMA_VERSION))
    checks.append(_check("claim_level", skeleton["claim_level"] == CLAIM_LEVEL))
    checks.append(_check("mode", skeleton["mode"] == MODE))
    checks.append(_check("phase", skeleton["phase"] == PHASE))
    checks.append(_check("generated_by", skeleton["generated_by"] == GENERATED_BY))
    checks.append(_check("status_pass", skeleton["status"] == "bea4_external_scale_smoke_pass"))
    checks.append(_check("unavail_status", unavail["status"] == "unavailable_with_reason"))

    # Group 2: Safe true flags.
    for flag in ("aggregate_only_public_artifact", "diagnostic_only",
                 "scale_slice_read", "worst_slice_aggregated"):
        checks.append(_check(f"safe_true_{flag}", skeleton.get(flag) is True))

    # Group 3: No-claim false flags (includes algorithm_changed_during_bea4).
    for flag in ("external_benchmark_performance_claimed",
                 "leaderboard_entry_claimed", "downstream_agent_value_proven",
                 "calibration_claimed", "method_winner_claimed",
                 "promotion_ready", "default_should_change",
                 "runtime_behavior_changed", "retriever_changed",
                 "pack_builder_changed", "backend_changed",
                 "default_policy_changed", "evidencecore_semantics_changed",
                 "provider_calls_made", "remote_provider_calls_made",
                 "algorithm_changed_during_bea4", "weights_tuned_during_bea4"):
        checks.append(_check(f"false_{flag}", skeleton.get(flag) is False))

    # Group 4: License fields.
    for field, expected in LICENSE_FIELDS.items():
        checks.append(_check(f"license_{field}", skeleton.get(field) == expected))

    # Group 5: Scale defaults and hard caps.
    checks.append(_check("cb_offset_default", CONTEXTBENCH_ROW_OFFSET_DEFAULT == 80))
    checks.append(_check("cb_limit_default", CONTEXTBENCH_ROW_LIMIT_DEFAULT == 80))
    checks.append(_check("cb_limit_hard_cap", CONTEXTBENCH_ROW_LIMIT_HARD_CAP == 80))
    checks.append(_check("rq_offset_default", REPOQA_NEEDLE_OFFSET_DEFAULT == 40))
    checks.append(_check("rq_limit_default", REPOQA_NEEDLE_LIMIT_DEFAULT == 40))
    checks.append(_check("rq_limit_hard_cap", REPOQA_NEEDLE_LIMIT_HARD_CAP == 40))
    checks.append(_check("budget_default", BUDGET_DEFAULT == 5))
    checks.append(_check("budget_hard_cap", BUDGET_HARD_CAP == 20))

    # Group 6: Validation caps.
    checks.append(_check("validate_row_limit_caps", _validate_row_limit(200) == 80))
    checks.append(_check("validate_needle_limit_caps", _validate_needle_limit(200) == 40))
    checks.append(_check("validate_budget_caps", _validate_budget(100) == 20))
    try:
        _validate_row_limit(0)
        checks.append(_check("validate_row_limit_rejects_zero", False))
    except SystemExit:
        checks.append(_check("validate_row_limit_rejects_zero", True))
    try:
        _validate_methods("regex,symbol")
        checks.append(_check("methods_requires_bm25", False))
    except SystemExit:
        checks.append(_check("methods_requires_bm25", True))

    # Group 7: BEA v0.3 policy is frozen (same algorithm as BEA-3).
    checks.append(_check("v03_accepts_nonempty", len(v03_acc) > 0))
    checks.append(_check("v03_action_order_nonempty", len(v03_ao) > 0))
    checks.append(_check("v03_first_action_accept",
        v03_ao[0].get("action") == "accept_candidate" if v03_ao else False))
    checks.append(_check("v03_budget_trace_nonempty", len(v03_bt) > 0))
    checks.append(_check("v03_anchor_mechanism",
        v03_ms.get("anchor_used") is True))

    # Group 8: Required arms present (no ablations).
    fixed_arms = skeleton.get("fixed_arms", [])
    for expected in (ARM_BEA_V0_3, ARM_BEA_V0_2, ARM_BEA_V0,
                     ARM_BM25_PREFIX, ARM_AGREEMENT_ONLY, ARM_RRF_SAME_BUDGET,
                     ARM_SEEDED_RANDOM):
        checks.append(_check(f"fixed_arms_has_{expected}", expected in fixed_arms))
    # Ablations MUST NOT appear in BEA-4 fixed arms.
    for ablation in ("bea_v0_3_no_anchor", "bea_v0_3_no_early_stop"):
        checks.append(_check(f"fixed_arms_excludes_{ablation}", ablation not in fixed_arms))

    # Group 9: Benchmark arm metric records.
    bamr = skeleton.get("benchmark_arm_metric_records", [])
    checks.append(_check("bamr_nonempty", len(bamr) > 0))
    expected_bamr_count = len(per_benchmark_arm_aggs) * 7 * len(ARM_METRIC_ALLOWLIST)
    checks.append(_check("bamr_count", len(bamr) == expected_bamr_count))
    for rec in bamr[:3]:
        for key in ("benchmark", "arm", "metric", "value", "record_count"):
            checks.append(_check(f"bamr_has_{key}", key in rec))

    # Group 10: Delta records (v0.3 vs each required control).
    dr = skeleton.get("delta_records", [])
    required_controls = [ARM_BM25_PREFIX, ARM_AGREEMENT_ONLY, ARM_RRF_SAME_BUDGET,
                          ARM_BEA_V0_2, ARM_BEA_V0, ARM_SEEDED_RANDOM]
    for control in required_controls:
        found = any(r["baseline_arm"] == control and r["treatment_arm"] == ARM_BEA_V0_3
                    for r in dr)
        checks.append(_check(f"delta_v03_vs_{control}", found))

    # Group 11: Win/tie/loss records.
    wtl = skeleton.get("win_tie_loss_records", [])
    checks.append(_check("wtl_nonempty", len(wtl) > 0))
    for control in required_controls:
        found = any(r["baseline_arm"] == control and r["treatment_arm"] == ARM_BEA_V0_3
                    for r in wtl)
        checks.append(_check(f"wtl_v03_vs_{control}", found))

    # Group 12: Worst-slice records.
    wsr = skeleton.get("worst_slice_records", [])
    checks.append(_check("wsr_nonempty", len(wsr) > 0))
    for rec in wsr[:3]:
        for bucket in WORST_SLICE_BUCKETS:
            checks.append(_check(f"wsr_has_{bucket}", bucket in rec))
        for metric in PRIMARY_METRICS:
            checks.append(_check(f"wsr_has_{metric}", metric in rec))
        checks.append(_check("wsr_has_record_count", "record_count" in rec))
    # Worst slice max per benchmark arm.
    from collections import Counter
    bk_counts = Counter((r["benchmark"], r["arm"]) for r in wsr)
    for (benchmark, arm), count in bk_counts.items():
        checks.append(_check(f"wsr_max_per_{benchmark}_{arm}",
            count <= WORST_SLICE_MAX_PER_BENCHMARK))

    # Group 13: Mechanism summary records.
    msr = skeleton.get("mechanism_summary_records", [])
    checks.append(_check("msr_nonempty", len(msr) > 0))
    for field in ("anchor_used_rate", "early_stop_rate", "mean_budget_used",
                  "mean_latency_seconds", "mean_span_extent"):
        found = any(r.get("mechanism_field") == field for r in msr)
        checks.append(_check(f"msr_has_{field}", found))

    # Group 14: Private SCORE manifest.
    manifest = skeleton.get("private_score_manifest", {})
    checks.append(_check("manifest_records_written", manifest.get("records_written") is True))
    checks.append(_check("manifest_record_count", manifest.get("record_count") == 7))
    checks.append(_check("manifest_schema", manifest.get("schema_version") == PRIVATE_SCORE_SCHEMA_VERSION))
    checks.append(_check("manifest_storage_class", manifest.get("storage_class") == "tmp_private"))
    checks.append(_check("manifest_path_not_serialized",
        manifest.get("path_publicly_serialized") is False))
    # Manifest hash is 64-char hex.
    mh = manifest.get("manifest_hash", "")
    checks.append(_check("manifest_hash_len", len(mh) == 64))

    # Group 15: Bucket helpers.
    checks.append(_check("qlb_short", _query_length_bucket("a b c") == "short"))
    checks.append(_check("qlb_medium", _query_length_bucket(" ".join(["w"] * 20)) == "medium"))
    checks.append(_check("qlb_long", _query_length_bucket(" ".join(["w"] * 50)) == "long"))
    checks.append(_check("qlb_empty", _query_length_bucket("") == "empty"))
    checks.append(_check("cpsb_small", _candidate_pool_size_bucket(2) == "small"))
    checks.append(_check("cpsb_medium", _candidate_pool_size_bucket(15) == "medium"))
    checks.append(_check("cpsb_large", _candidate_pool_size_bucket(50) == "large"))
    checks.append(_check("cpsb_empty", _candidate_pool_size_bucket(0) == "empty"))
    checks.append(_check("beb_full", _budget_exhaustion_bucket(5, 5) == "full"))
    checks.append(_check("beb_partial", _budget_exhaustion_bucket(3, 5) == "partial"))
    checks.append(_check("beb_empty", _budget_exhaustion_bucket(0, 5) == "empty"))
    checks.append(_check("fkm_pure_python",
        _file_kind_mix_bucket([{"path": "a.py"}, {"path": "b.py"}]) == "pure_python"))
    checks.append(_check("fkm_mixed",
        _file_kind_mix_bucket([{"path": "a.py"}, {"path": "b.md"}]) == "mixed"))
    checks.append(_check("fkm_non_python",
        _file_kind_mix_bucket([{"path": "a.md"}, {"path": "b.md"}]) == "non_python"))
    checks.append(_check("fkm_empty", _file_kind_mix_bucket([]) == "empty"))
    checks.append(_check("mab_high", _method_agreement_bucket([3, 3, 2]) == "high"))
    checks.append(_check("mab_medium", _method_agreement_bucket([2, 1, 2]) == "medium"))
    checks.append(_check("mab_low", _method_agreement_bucket([1, 1, 1]) == "low"))
    checks.append(_check("rgb_narrow", _rank_gap_bucket([1, 2, 3]) == "narrow"))
    checks.append(_check("rgb_medium", _rank_gap_bucket([1, 5, 8]) == "medium"))
    checks.append(_check("rgb_wide", _rank_gap_bucket([1, 15, 30]) == "wide"))
    checks.append(_check("rgb_empty", _rank_gap_bucket([]) == "empty"))

    # Group 16: Worst-slice bucket tuple is complete (7 buckets).
    bt = _compute_record_bucket_tuple(
        benchmark="contextbench", query="test query",
        deduped_count=10, budget_used=3, budget=5,
        accepted_evidence=[{"path": "a.py"}],
        per_record_agreement=[2], per_record_ranks=[1],
    )
    checks.append(_check("bucket_tuple_7_keys", len(bt) == 7))
    for bucket in WORST_SLICE_BUCKETS:
        checks.append(_check(f"bucket_tuple_has_{bucket}", bucket in bt))

    # Group 17: Scanner rejects BEA-4-specific forbidden keys.
    for forbidden_key in ("private_score_path", "action_order",
                          "priority_components", "selected_decisions",
                          "budget_trace", "stop_reason",
                          "candidate_features", "anchor_eligibility",
                          "anchor_slots", "early_stop_reason",
                          "score_outcome", "winner", "calibration",
                          "method_winner", "best_method",
                          "recommended_default",
                          "worst_slice_record_id", "slice_label",
                          "slice_id", "worst_slice_label",
                          "slice_record_ids", "slice_member_ids"):
        leaked = dict(skeleton)
        leaked[forbidden_key] = "leak"
        checks.append(_check(f"scanner_rejects_{forbidden_key}",
            bool(_scan_bea4(leaked))))

    # Group 18: Scanner allows safe values.
    safe_sample = {
        "schema_version": SCHEMA_VERSION,
        "benchmark": "contextbench",
        "arm": ARM_BEA_V0_3,
        "metric": "mrr",
        "value": 0.5,
        "record_count": 5,
        "benchmark_arm_metric_records": [
            {"benchmark": "contextbench", "arm": ARM_BEA_V0_3,
             "metric": "mrr", "value": 0.5, "record_count": 5},
        ],
        "worst_slice_records": [
            {"benchmark": "contextbench", "arm": ARM_BEA_V0_3,
             "query_length_bucket": "short",
             "candidate_pool_size_bucket": "small",
             "budget_exhaustion_bucket": "full",
             "file_kind_mix_bucket": "pure_python",
             "method_agreement_bucket": "high",
             "rank_gap_bucket": "narrow",
             "record_count": 3, "mrr": 0.5},
        ],
        "private_score_manifest": {
            "records_written": True, "record_count": 6,
            "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
            "manifest_hash": "a" * 64,
            "storage_class": "tmp_private",
            "path_publicly_serialized": False,
        },
    }
    checks.append(_check("scanner_allows_safe", not _scan_bea4(safe_sample)))

    # Group 19: Fail-closed.
    try:
        _enforce_bea4_no_forbidden(skeleton)
        checks.append(_check("fail_closed_clean", True))
    except SystemExit:
        checks.append(_check("fail_closed_clean", False))
    for lk, lv in [
        ("private_score_path", "/tmp/x"),
        ("action_order", [{}]),
        ("candidate_features", [{}]),
        ("winner", "v03"),
        ("calibration", "x"),
        ("method_winner", "v03"),
        ("worst_slice_record_id", "ws-1"),
        ("slice_label", "my-slice"),
    ]:
        leaked = dict(skeleton)
        leaked[lk] = lv
        try:
            _enforce_bea4_no_forbidden(leaked)
            checks.append(_check(f"fail_closed_{lk}", False))
        except SystemExit:
            checks.append(_check(f"fail_closed_{lk}", True))

    # Group 20: Public artifact self-scan clean.
    checks.append(_check("self_scan_clean", not _scan_bea4(skeleton)))
    checks.append(_check("unavail_scan_clean", not _scan_bea4(unavail)))

    # Group 21: CLI surface.
    parser = build_parser()
    option_strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            option_strings.add(opt)
    for opt in ("--self-test", "--contextbench-row-offset", "--contextbench-row-limit",
                "--repoqa-needle-offset", "--repoqa-needle-limit", "--budget",
                "--methods", "--openlocus", "--out", "--private-score-dir",
                "--enable-rrf-baseline", "--enable-external-benchmark-network"):
        checks.append(_check(f"cli_has_{opt}", opt in option_strings))

    # Group 22: Private SCORE writer.
    with tempfile.TemporaryDirectory(prefix="bea4_st_") as sd:
        sf = Path(sd) / "bea4.private.jsonl"
        _write_private_score_row(sf, {"test": 1})
        _write_private_score_row(sf, {"test": 2})
        lines = sf.read_text(encoding="utf-8").splitlines()
        checks.append(_check("score_writer_2_rows", len(lines) == 2))
        checks.append(_check("score_rows_parse",
            all(isinstance(json.loads(l), dict) for l in lines if l)))

    # Group 23: No winner/calibration/method_winner anywhere.
    for field in ("winner", "best_method", "recommended_default",
                  "method_winner", "calibration"):
        checks.append(_check(f"missing_{field}", field not in skeleton))

    # Group 24: Aggregate runtime present.
    checks.append(_check("has_runtime", "aggregate_runtime_seconds" in skeleton))
    checks.append(_check("unavail_no_runtime", "aggregate_runtime_seconds" not in unavail))

    # Group 25: Paired denominator win/tie/loss.
    rec_a = {ARM_BEA_V0: v0_m, ARM_BEA_V0_3: v03_m}
    rec_b = {ARM_BEA_V0: v0_m}  # missing v0.3
    wtl_partial = _win_tie_loss_records([rec_a, rec_b], ARM_BEA_V0, ARM_BEA_V0_3)
    if wtl_partial:
        checks.append(_check("wtl_paired_excludes_missing", wtl_partial[0]["record_count"] == 1))
    else:
        checks.append(_check("wtl_paired_excludes_missing", False))

    # Group 26: Worst-slice max cap.
    big_buckets: list[dict[str, Any]] = []
    for i in range(20):
        bt_i = _compute_record_bucket_tuple(
            benchmark="contextbench", query=f"q{i}",
            deduped_count=10 + i, budget_used=3, budget=5,
            accepted_evidence=[{"path": f"a{i}.py"}],
            per_record_agreement=[2], per_record_ranks=[1],
        )
        big_buckets.append({
            "arm": ARM_BEA_V0_3, "bucket_tuple": bt_i,
            "metrics": v03_m,
        })
    big_wsr = _worst_slice_records(big_buckets)
    bk_wsr = Counter((r["benchmark"], r["arm"]) for r in big_wsr)
    for (benchmark, arm), count in bk_wsr.items():
        checks.append(_check(f"wsr_capped_{benchmark}_{arm}",
            count <= WORST_SLICE_MAX_PER_BENCHMARK))

    # Group 27: algorithm_changed_during_bea4 is present and false.
    checks.append(_check("has_algorithm_changed_flag", "algorithm_changed_during_bea4" in skeleton))
    checks.append(_check("algorithm_changed_false", skeleton.get("algorithm_changed_during_bea4") is False))
    checks.append(_check("weights_tuned_false", skeleton.get("weights_tuned_during_bea4") is False))

    # Group 28: No ablation arms in fixed_arms list.
    for ablation in ("bea_v0_3_no_anchor", "bea_v0_3_no_early_stop"):
        checks.append(_check(f"no_{ablation}_in_fixed_arms", ablation not in fixed_arms))

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
    ap = SafeArgumentParser(
        description="BEA-4 External Scale Smoke (frozen BEA v0.3)"
    )
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--contextbench-row-offset", type=int,
                    default=CONTEXTBENCH_ROW_OFFSET_DEFAULT)
    ap.add_argument("--contextbench-row-limit", type=int,
                    default=CONTEXTBENCH_ROW_LIMIT_DEFAULT)
    ap.add_argument("--repoqa-needle-offset", type=int,
                    default=REPOQA_NEEDLE_OFFSET_DEFAULT)
    ap.add_argument("--repoqa-needle-limit", type=int,
                    default=REPOQA_NEEDLE_LIMIT_DEFAULT)
    ap.add_argument("--budget", type=int, default=BUDGET_DEFAULT)
    ap.add_argument("--methods", default=DEFAULT_METHODS)
    ap.add_argument("--enable-rrf-baseline", action="store_true", default=True)
    ap.add_argument("--enable-external-benchmark-network", action="store_true")
    ap.add_argument("--openlocus", default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--private-score-dir", default=None)
    return ap


# ---------------------------------------------------------------------------
# Network smoke runner
# ---------------------------------------------------------------------------


def _run_network_smoke(
    *,
    contextbench_row_offset: int,
    contextbench_row_limit: int,
    repoqa_needle_offset: int,
    repoqa_needle_limit: int,
    budget: int,
    methods: tuple[str, ...],
    enable_rrf_baseline: bool,
    openlocus_bin: str,
    openlocus_binary_source: str,
    network_mode: str,
    eval_dir: Path,
    self_test_passed: bool,
    private_score_dir: Path,
    private_score_storage_class: str,
    phase_run_id: str,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    network_calls = 0
    smoke_start = time.perf_counter()
    manifest_hash = _private_score_manifest_hash()
    score_file = private_score_dir / "bea4.private.jsonl"
    try:
        score_file.unlink()
    except OSError:
        pass

    per_record_arm_metrics: list[dict[str, dict[str, Any]]] = []
    per_benchmark_arm_aggs: dict[str, dict[str, dict[str, Any]]] = {}
    per_record_mechanism_summaries: list[dict[str, Any]] = []
    per_record_buckets: list[dict[str, Any]] = []
    records_evaluated = 0
    records_successful = 0
    records_failed = 0
    paired_exclusion_count = 0

    # ContextBench heldout scale slice.
    cb_rows, cb_status, cb_nc, cb_fcc = _fetch_heldout_contextbench_rows(
        contextbench_row_offset, contextbench_row_limit
    )
    network_calls += cb_nc
    for k, v in cb_fcc.items():
        if k in fcc:
            fcc[k] += v
    if cb_status == "pass" and cb_rows:
        for idx, row in enumerate(cb_rows):
            records_evaluated += 1
            gold_paths, gold_lines, gc_status = c5a._parse_gold_context(
                row.get("gold_context")
            )
            if gc_status != "pass":
                fcc["contextbench_gold_parse_failed"] += 1
                records_failed += 1
                continue
            query = c5a._sanitize_query(
                row.get("problem_statement", ""), "first_paragraph"
            )
            if not query:
                fcc["contextbench_no_python_rows"] += 1
                records_failed += 1
                continue
            repo_url = row.get("repo_url", "")
            base_commit = row.get("base_commit", "")
            if not isinstance(repo_url, str) or not isinstance(
                base_commit, str
            ) or not repo_url or not base_commit:
                fcc["contextbench_no_python_rows"] += 1
                records_failed += 1
                continue
            with tempfile.TemporaryDirectory(prefix=f"bea4_cb_{idx}_") as rds:
                rwd = Path(rds)
                clone_ok, _, clone_fcc = c5d._clone_and_checkout(
                    repo_url, base_commit, rwd
                )
                for k, v in clone_fcc.items():
                    if k in fcc:
                        fcc[k] += v
                if not clone_ok:
                    records_failed += 1
                    continue
                repo_root = rwd / "repo"
                per_arm, fcc, mech_summary, rec_buckets = _evaluate_record(
                    openlocus_bin=openlocus_bin,
                    benchmark="contextbench",
                    private_record_id=f"contextbench-{idx}",
                    task_id=f"cb_row_{idx}", query=query,
                    gold_paths=gold_paths, gold_lines=gold_lines,
                    repo_root=repo_root, methods=methods, budget=budget,
                    enable_rrf_baseline=enable_rrf_baseline,
                    score_path=score_file, phase_run_id=phase_run_id, fcc=fcc,
                )
                if per_arm is None:
                    records_failed += 1
                    continue
                per_record_arm_metrics.append(per_arm)
                per_record_mechanism_summaries.append(mech_summary)
                per_record_buckets.extend(rec_buckets)
                cb_aggs = per_benchmark_arm_aggs.setdefault("contextbench", {})
                for arm_id, metrics in per_arm.items():
                    if arm_id not in cb_aggs:
                        cb_aggs[arm_id] = {"__record_count__": 0}
                    cb_aggs[arm_id]["__record_count__"] += 1
                    for m in ARM_METRIC_ALLOWLIST:
                        if m in metrics:
                            cb_aggs[arm_id].setdefault(m, [])
                            cb_aggs[arm_id][m].append(metrics[m])
                records_successful += 1

    # RepoQA heldout scale slice.
    rq_needles, rq_status, rq_nc, rq_fcc = _fetch_heldout_repoqa_needles(
        repoqa_needle_offset, repoqa_needle_limit
    )
    network_calls += rq_nc
    for k, v in rq_fcc.items():
        if k in fcc:
            fcc[k] += v
    if rq_status == "pass" and rq_needles:
        for idx, needle in enumerate(rq_needles):
            records_evaluated += 1
            query = c5d._sanitize_needle_description(
                needle.get("needle_description", "")
            )
            if not query:
                fcc["repoqa_needle_parse_failed"] += 1
                records_failed += 1
                continue
            repo_url = needle.get("repo_url", "")
            commit_sha = needle.get("commit_sha", "")
            needle_path = needle.get("needle_path", "")
            start_line = needle.get("needle_start_line", 0)
            end_line = needle.get("needle_end_line", 0)
            if (not isinstance(repo_url, str) or not repo_url
                or not isinstance(commit_sha, str) or not commit_sha
                or not isinstance(needle_path, str) or not needle_path):
                fcc["repoqa_needle_parse_failed"] += 1
                records_failed += 1
                continue
            with tempfile.TemporaryDirectory(prefix=f"bea4_rq_{idx}_") as rds:
                rwd = Path(rds)
                clone_ok, _, clone_fcc = c5d._clone_and_checkout(
                    repo_url, commit_sha, rwd
                )
                for k, v in clone_fcc.items():
                    if k in fcc:
                        fcc[k] += v
                if not clone_ok:
                    records_failed += 1
                    continue
                repo_root = rwd / "repo"
                per_arm, fcc, mech_summary, rec_buckets = _evaluate_record(
                    openlocus_bin=openlocus_bin,
                    benchmark="repoqa",
                    private_record_id=f"repoqa-{idx}",
                    task_id=f"rq_needle_{idx}", query=query,
                    gold_paths=[needle_path],
                    gold_lines=[[start_line, end_line]],
                    repo_root=repo_root, methods=methods, budget=budget,
                    enable_rrf_baseline=enable_rrf_baseline,
                    score_path=score_file, phase_run_id=phase_run_id, fcc=fcc,
                )
                if per_arm is None:
                    records_failed += 1
                    continue
                per_record_arm_metrics.append(per_arm)
                per_record_mechanism_summaries.append(mech_summary)
                per_record_buckets.extend(rec_buckets)
                rq_aggs = per_benchmark_arm_aggs.setdefault("repoqa", {})
                for arm_id, metrics in per_arm.items():
                    if arm_id not in rq_aggs:
                        rq_aggs[arm_id] = {"__record_count__": 0}
                    rq_aggs[arm_id]["__record_count__"] += 1
                    for m in ARM_METRIC_ALLOWLIST:
                        if m in metrics:
                            rq_aggs[arm_id].setdefault(m, [])
                            rq_aggs[arm_id][m].append(metrics[m])
                records_successful += 1

    if not per_record_arm_metrics:
        return _build_unavailable_report(
            "retrieval_failed", self_test_passed=self_test_passed,
            contextbench_row_offset_requested=contextbench_row_offset,
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_offset_requested=repoqa_needle_offset,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            budget=budget, methods=methods,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            private_score_storage_class=private_score_storage_class,
            private_score_manifest_hash=manifest_hash,
            records_evaluated=records_evaluated,
            records_successful=records_successful,
            records_failed=records_failed,
            network_calls=network_calls, failure_category_counts=fcc,
        )

    # Compute per-benchmark × arm means.
    for benchmark, arm_aggs in per_benchmark_arm_aggs.items():
        for arm_id, agg in arm_aggs.items():
            rc = agg.pop("__record_count__", 0)
            means: dict[str, Any] = {}
            for m in ARM_METRIC_ALLOWLIST:
                vals = agg.get(m, [])
                if vals:
                    means[m] = round(sum(float(v) for v in vals) / len(vals), 6)
                else:
                    means[m] = 0.0
            agg.clear()
            agg.update(means)
            agg["__record_count__"] = rc

    # Overall arm aggregates (across all benchmarks).
    arm_aggs: dict[str, dict[str, Any]] = {}
    fixed_arm_ids = [
        ARM_BEA_V0_3, ARM_BEA_V0_2, ARM_BEA_V0,
        ARM_BM25_PREFIX, ARM_AGREEMENT_ONLY, ARM_SEEDED_RANDOM,
    ]
    if enable_rrf_baseline:
        fixed_arm_ids.append(ARM_RRF_SAME_BUDGET)
    for arm_id in fixed_arm_ids:
        per_arm_list = [
            rec[arm_id] for rec in per_record_arm_metrics
            if arm_id in rec
        ]
        if per_arm_list:
            arm_aggs[arm_id] = _arm_means(per_arm_list)

    # Count private SCORE rows.
    private_score_count = 0
    try:
        if score_file.exists():
            with score_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        private_score_count += 1
    except OSError:
        private_score_count = 0

    private_score_written = private_score_count > 0
    num_arms = len(fixed_arm_ids)
    expected_count = records_successful * num_arms
    if records_successful > 0 and private_score_count != expected_count:
        fcc["private_score_write_failed"] = (
            fcc.get("private_score_write_failed", 0) + 1
        )
        return _build_unavailable_report(
            "private_score_write_failed", self_test_passed=self_test_passed,
            contextbench_row_offset_requested=contextbench_row_offset,
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_offset_requested=repoqa_needle_offset,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            budget=budget, methods=methods,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            private_score_records_written=private_score_written,
            private_score_record_count=private_score_count,
            private_score_storage_class=private_score_storage_class,
            private_score_manifest_hash=manifest_hash,
            records_evaluated=records_evaluated,
            records_successful=records_successful,
            records_failed=records_failed,
            network_calls=network_calls, failure_category_counts=fcc,
        )

    aggregate_runtime_seconds = time.perf_counter() - smoke_start
    partial = records_failed > 0 or records_successful < (
        contextbench_row_limit + repoqa_needle_limit
    )

    return _build_pass_report(
        self_test_passed=self_test_passed,
        contextbench_row_offset_requested=contextbench_row_offset,
        contextbench_row_limit_requested=contextbench_row_limit,
        repoqa_needle_offset_requested=repoqa_needle_offset,
        repoqa_needle_limit_requested=repoqa_needle_limit,
        budget=budget, methods=methods,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        records_evaluated=records_evaluated,
        records_successful=records_successful,
        records_failed=records_failed, network_calls=network_calls,
        arm_aggs=arm_aggs,
        per_record_arm_metrics=per_record_arm_metrics,
        per_benchmark_arm_aggs=per_benchmark_arm_aggs,
        per_record_mechanism_summaries=per_record_mechanism_summaries,
        per_record_buckets=per_record_buckets,
        private_score_records_written=private_score_written,
        private_score_record_count=private_score_count,
        private_score_storage_class=private_score_storage_class,
        private_score_manifest_hash=manifest_hash,
        aggregate_runtime_seconds=aggregate_runtime_seconds,
        failure_category_counts=fcc,
        enable_rrf_baseline=enable_rrf_baseline,
        paired_exclusion_count=paired_exclusion_count,
        partial=partial,
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
        print(f"self_test_passed={passed} ({passed_count}/{len(checks)} checks)")
        sys.exit(0 if passed else 1)

    contextbench_row_offset = _validate_row_offset(args.contextbench_row_offset)
    contextbench_row_limit = _validate_row_limit(args.contextbench_row_limit)
    repoqa_needle_offset = _validate_needle_offset(args.repoqa_needle_offset)
    repoqa_needle_limit = _validate_needle_limit(args.repoqa_needle_limit)
    budget = _validate_budget(args.budget)
    methods = _validate_methods(args.methods)
    enable_rrf_baseline = bool(args.enable_rrf_baseline)
    enable_network = bool(args.enable_external_benchmark_network)
    out_path = args.out if args.out is not None else DEFAULT_OUT

    checks, self_test_passed = run_self_test_checks()
    if not self_test_passed:
        print("error: self-test failed; refusing to write artifact", file=sys.stderr)
        sys.exit(1)

    openlocus_bin, openlocus_source = c5a._resolve_openlocus_binary(args.openlocus)
    if openlocus_bin is None:
        report = _build_unavailable_report(
            "retrieval_failed", self_test_passed=self_test_passed,
            contextbench_row_offset_requested=contextbench_row_offset,
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_offset_requested=repoqa_needle_offset,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            budget=budget, methods=methods,
            openlocus_binary_source=openlocus_source,
            network_mode="local_explicit",
        )
        _enforce_bea4_no_forbidden(report)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        return

    private_score_dir, private_score_storage_class = (
        _resolve_private_score_dir(args.private_score_dir)
    )
    phase_run_id = f"bea4-{int(time.time())}"

    if not enable_network:
        report = _build_unavailable_report(
            "contextbench_fetch_failed", self_test_passed=self_test_passed,
            contextbench_row_offset_requested=contextbench_row_offset,
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_offset_requested=repoqa_needle_offset,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            budget=budget, methods=methods,
            openlocus_binary_source=openlocus_source,
            network_mode="disabled_opt_in",
        )
        _enforce_bea4_no_forbidden(report)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        print("enable_external_benchmark_network is false; skipping real BEA-4 smoke.")
        return

    network_mode = "local_explicit"
    eval_dir = Path(__file__).resolve().parent
    try:
        report = _run_network_smoke(
            contextbench_row_offset=contextbench_row_offset,
            contextbench_row_limit=contextbench_row_limit,
            repoqa_needle_offset=repoqa_needle_offset,
            repoqa_needle_limit=repoqa_needle_limit,
            budget=budget, methods=methods,
            enable_rrf_baseline=enable_rrf_baseline,
            openlocus_bin=openlocus_bin,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode, eval_dir=eval_dir,
            self_test_passed=self_test_passed,
            private_score_dir=private_score_dir,
            private_score_storage_class=private_score_storage_class,
            phase_run_id=phase_run_id,
        )
    except Exception:
        report = _build_unavailable_report(
            "unexpected_exception", self_test_passed=self_test_passed,
            contextbench_row_offset_requested=contextbench_row_offset,
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_offset_requested=repoqa_needle_offset,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            budget=budget, methods=methods,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
            private_score_storage_class=private_score_storage_class,
        )

    if report.get("provider_calls") != 0:
        report["status"] = "fail_schema_contract"

    _enforce_bea4_no_forbidden(report)
    _write_json(out_path, report)
    manifest = report.get("private_score_manifest", {})
    print(f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, "
          f"status={report['status']}, phase={report['phase']}, "
          f"records_successful={report.get('records_successful', 0)}, "
          f"private_score_record_count={manifest.get('record_count', 0)})")


if __name__ == "__main__":
    main()
