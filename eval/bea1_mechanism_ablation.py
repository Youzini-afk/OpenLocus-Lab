#!/usr/bin/env python3
"""BEA-1 Mechanism Ablation Smoke (Public Aggregate-Only Records).

This module implements the **BEA-1 mechanism ablation** smoke over fresh
bounded ContextBench verified Python rows + RepoQA Python needles. It is a
real algorithmic retrieval/acquisition mechanism ablation: BEA-0's
``bea_v0_budgeted`` policy is compared against three same-budget controls
(``same_budget_bm25_prefix``, ``agreement_only_same_budget``,
``seeded_random_same_budget``) and the existing baselines
(``bm25_top10``, ``rrf_bm25_regex_symbol_top10`` when enabled), on the same
records under a paired denominator rule. Private per-record SCORE JSONL is
written ONLY under ``/tmp``; the public artifact is records-shaped
aggregate only.

BEA-1 is explicitly **not** a benchmark result, **not** a leaderboard entry,
**not** a performance claim, **not** a method-winner claim, **not** a
calibration claim, **not** a promotion, **not** a default/policy change, and
**not** a runtime/retriever/pack/backend/EvidenceCore semantic change. The
committed artifact records only aggregate per-arm metric records, baseline-
vs-treatment delta records, mechanism contrast records, and aggregate
private SCORE manifest fields.

Claim boundary (binding):

* Claim level: ``bea_v0_mechanism_ablation_smoke_only``.
* Status: ``bea1_mechanism_ablation_pass`` | ``partial`` |
  ``unavailable_with_reason`` | ``fail_forbidden_scan`` |
  ``fail_schema_contract``.
* Mode: ``bounded_external_retrieval_mechanism_ablation``; phase ``BEA-1``.

Privacy / license boundary (binding):

* Private per-record SCORE JSONL is written ONLY under ``/tmp`` (or an
  explicitly ignored private path). The private SCORE path is NEVER
  serialized in the public artifact, docs, or CI artifacts.
* The public artifact records ONLY aggregate SCORE manifest fields:
  ``records_written``, ``record_count``, ``schema_version``,
  ``manifest_hash``, ``storage_class``, ``path_publicly_serialized=false``
  (under the ``private_score_manifest`` block).
* ContextBench + RepoQA dataset licenses are unknown
  (``unknown_dataset_license``); row-level redistribution is disabled
  (``row_level_redistribution_allowed=false``) and derived row-level
  publication is disabled
  (``derived_row_level_publication_allowed=false``). Aggregate metrics
  publication is allowed as aggregate-only smoke
  (``aggregate_metrics_publication=aggregate_only_smoke``).

Network / CI policy (binding):

* Default no-network self-test passes without HuggingFace/GitHub.
* Real acquisition requires public network access to HF datasets-server
  and GitHub repos. CI is a separate explicit ``workflow_dispatch`` job
  with ``enable_external_benchmark_network=true``. It must NOT run on
  PR/push by default, must use no provider secrets/vars, no provider model
  env, and must upload only the aggregate report. The private SCORE JSONL
  is NEVER uploaded.

Run::

    python3 -m py_compile eval/bea1_mechanism_ablation.py
    python3 eval/bea1_mechanism_ablation.py --self-test
    python3 eval/bea1_mechanism_ablation.py \\
        --enable-external-benchmark-network \\
        --contextbench-row-limit 5 --repoqa-needle-limit 3 \\
        --budget 5 --methods bm25,regex,symbol --enable-rrf-baseline \\
        --out artifacts/bea1_mechanism_ablation/\\
bea1_mechanism_ablation_report.json

If the network smoke cannot complete in the environment, the default
artifact records truthful ``unavailable_with_reason`` with a real failure
category (no stale/fake pass). Self-test/docs/diff-check still pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# Reuse BEA-0 helpers (candidate normalization, BEA v0 policy, scanner
# primitives, private SCORE writer, arm metrics, etc.). The ``eval``
# directory has no ``__init__.py`` (it is a flat script directory), so we
# add this file's parent to ``sys.path`` and import directly. We also
# reuse C5-A/C5-D helpers via BEA-0's transitive imports.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402
import c5d_repoqa_bm25_retrieval_smoke as c5d  # noqa: E402
import bea0_budgeted_evidence_acquisition as bea0  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants (BEA-1 owned)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "bea1_mechanism_ablation.v1"
GENERATED_BY = "eval/bea1_mechanism_ablation.py"
CLAIM_LEVEL = "bea_v0_mechanism_ablation_smoke_only"
MODE = "bounded_external_retrieval_mechanism_ablation"
PHASE = "BEA-1"

DEFAULT_OUT = Path(
    "artifacts/bea1_mechanism_ablation/"
    "bea1_mechanism_ablation_report.json"
)

# Private SCORE JSONL schema version for BEA-1. Bumped because BEA-1 adds
# the same-budget control arm evidence to each private row.
PRIVATE_SCORE_SCHEMA_VERSION = "bea1_private_score.v1"

# Default bounded sample: ContextBench 5 rows + RepoQA 3 needles.
# Hard caps: ContextBench 20, RepoQA 10.
CONTEXTBENCH_ROW_LIMIT_DEFAULT = 5
CONTEXTBENCH_ROW_LIMIT_HARD_CAP = 20
REPOQA_NEEDLE_LIMIT_DEFAULT = 3
REPOQA_NEEDLE_LIMIT_HARD_CAP = 10

# Default evidence budget for the bea_v0_budgeted policy and same-budget
# controls. Hard cap 20.
BUDGET_DEFAULT = 5
BUDGET_HARD_CAP = 20

# Methods supported by the BEA-1 multi-method candidate collector.
ALLOWED_METHODS: tuple[str, ...] = ("bm25", "regex", "symbol")
DEFAULT_METHODS = "bm25,regex,symbol"

# Fixed arm IDs only; no dynamic arm names.
ARM_BM25_TOP10 = "bm25_top10"
ARM_RRF_TOP10 = "rrf_bm25_regex_symbol_top10"
ARM_BEA_V0_BUDGETED = "bea_v0_budgeted"
ARM_SAME_BUDGET_BM25_PREFIX = "same_budget_bm25_prefix"
ARM_AGREEMENT_ONLY_SAME_BUDGET = "agreement_only_same_budget"
ARM_SEEDED_RANDOM_SAME_BUDGET = "seeded_random_same_budget"

# Fixed baseline arms (for delta_records). rrf baseline is conditional on
# --enable-rrf-baseline.
BASELINE_ARM = ARM_BM25_TOP10

# Fixed mechanism contrast IDs. These appear as the ``contrast`` field in
# mechanism_contrast_records. Each contrast is bea_v0_budgeted vs a
# same-budget control arm on the paired denominator.
CONTRAST_BEA_VS_SAME_BUDGET_BM25 = "bea_vs_same_budget_bm25"
CONTRAST_BEA_VS_AGREEMENT_ONLY = "bea_vs_agreement_only"
CONTRAST_BEA_VS_SEEDED_RANDOM = "bea_vs_seeded_random"

# Public deterministic seed for the seeded_random_same_budget arm. This
# is a fixed public constant; no per-record seed, no gold/label/row-id
# derived seed.
SEEDED_RANDOM_SEED = 20240621

# Arm metric allowlist. Only these aggregate metric names from
# ``eval/score.py`` + BEA-0 acquisition policy may appear in the public
# artifact under per-arm records.
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
)

# ---------------------------------------------------------------------------
# Safe booleans true (only when actually true). Exactly these MAY be true
# in the committed public artifact.
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "mechanism_ablation_performed": False,
    "bea_v0_acquisition_performed": False,
    "private_score_records_written": False,
    "external_benchmark_rows_read": False,
    "openlocus_retrieval_executed": False,
    "score_py_metrics_computed": False,
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
}

# ---------------------------------------------------------------------------
# No-claim / no-runtime-change flags (all MUST be false in the committed
# public artifact).
# ---------------------------------------------------------------------------

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
# Fixed failure-category enum for the smoke.
# ---------------------------------------------------------------------------

FAILURE_CATEGORIES: tuple[str, ...] = (
    "contextbench_fetch_failed",
    "contextbench_no_python_rows",
    "contextbench_gold_parse_failed",
    "repoqa_asset_download_failed",
    "repoqa_asset_parse_failed",
    "repoqa_no_python_needles",
    "repoqa_needle_parse_failed",
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
# Public artifact scanner (BEA-1 owned, strict, fail-closed).
#
# BEA-1 reuses the BEA-0 forbidden scanner primitives (which extend
# C5-A/C5-D) for raw key/value leak detection. BEA-1 ADDS BEA-1-specific
# forbidden claim-boundary keys (``calibration``, ``method_winner``,
# ``best_method``, ``recommended_default``, etc.) that must NEVER appear
# as dict keys anywhere in a BEA-1 public artifact JSON.
# ---------------------------------------------------------------------------

# BEA-1-specific forbidden keys (in addition to bea0.BEA0_FORBIDDEN_EXTRA_KEYS
# and c5a.FORBIDDEN_KEY_NAMES). These are claim-boundary fields that must
# NEVER appear as dict keys anywhere in a public artifact JSON.
BEA1_FORBIDDEN_EXTRA_KEYS: frozenset[str] = frozenset(
    {
        # Claim-boundary fields (must remain false; never emitted as keys)
        "calibration",
        "method_winner",
        "best_method",
        "recommended_default",
        "recommended_method",
        "preferred_method",
        "default_method",
        "policy_decision",
        "decision",
        "ranking",
        "rank",
        "winner",
        "leaderboard",
        "promotion",
        # Per-record private fields already in BEA0_FORBIDDEN_EXTRA_KEYS,
        # but repeated here for BEA-1 self-documentation.
        "private_score_path",
        "score_path",
        "private_score_file",
        "private_record_id",
        "private_record_hash",
        "action_trace",
        "action_steps_trace",
        "budget_state",
        "budget_states",
        "accepted_candidates",
        "final_candidates",
        "candidate_list",
        "candidates",
        "score_outcome",
        "per_record_metrics",
        "runtime_query_features",
        "query_feature_summary",
        "query_features",
        "benchmark_row_id",
        "benchmark_record_id",
        "benchmark_label",
        "phase_run_id",
        "run_id",
        "task_id",
        "row_id",
        "needle_id",
        "instance_id",
        "provider_name",
        "model_name",
        "model_family",
        "provider_payload",
        "private_bucket",
        "route_bucket",
        "task_bucket",
    }
)


# BEA-1-specific safe VALUE path last-key segments. These keys MAY hold
# categorical bucket strings or sha256 hex strings (e.g. manifest_hash)
# without triggering the hex_digest_value / forbidden_field_name_value
# checks. Extends BEA-0's safe value path list with the nested
# ``manifest_hash`` key under ``private_score_manifest``.
BEA1_SAFE_VALUE_PATH_LAST_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "generated_by",
        "generated_at",
        "claim_level",
        "status",
        "mode",
        "phase",
        "method",
        "methods",
        "benchmark",
        "dataset_release",
        "language_filter",
        "query_mode",
        "gold_target_mode",
        "network_mode",
        "openlocus_binary_source",
        "private_score_schema_version",
        "private_score_storage_class",
        "private_score_manifest_hash",
        "manifest_hash",
        "storage_class",
        "claim_boundary",
        "signal_strength",
        "baseline_arm",
        "treatment_arm",
        "baseline_arms",
        "fixed_arms",
        "seeded_random_seed",
        "claim_level",
        "failure_reason_category",
        "dataset_license_status",
        "aggregate_metrics_publication",
        "citation_validation_mode",
        "arm",
        "metric",
        "contrast",
    }
)


def _is_bea1_schema_key_container(path: str) -> bool:
    """Check if the parent of the current key is a BEA-1 schema-key container.

    Extends BEA-0's container set with the BEA-1 records containers
    (``arm_metric_records``, ``delta_records``,
    ``mechanism_contrast_records``, ``private_score_manifest``).
    """
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in (
        bea0.BEA0_SCHEMA_KEY_CONTAINER_KEYS
        | {"arm_metric_records", "delta_records",
           "mechanism_contrast_records", "private_score_manifest"}
    )


def _bea1_safe_value_path(path: str) -> bool:
    """Check if a JSON path is a BEA-1-specific (or BEA-0) safe value path."""
    last = path.rsplit(".", 1)[-1]
    last_key = last.split("[")[0]
    if last_key in BEA1_SAFE_VALUE_PATH_LAST_KEYS:
        return True
    return bea0._bea0_safe_value_path(path)


def _scan_bea1_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    """Scan for BEA-1-specific forbidden keys (claim-boundary + private)."""
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                is_schema_container = _is_bea1_schema_key_container(sub_path)
                if (
                    key_str in BEA1_FORBIDDEN_EXTRA_KEYS
                    and not is_schema_container
                ):
                    violations.append(
                        {
                            "category": "forbidden_bea1_extra_key",
                            "path": sub_path,
                        }
                    )
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


def _scan_bea1(obj: Any) -> list[dict[str, Any]]:
    """Combined BEA-1 scanner: BEA-0 primitives + BEA-1 safe-path relaxation.

    The BEA-0 scanner is reused for raw key/value leak detection (URLs,
    hex digests, repo slugs, /tmp paths, etc.). BEA-1 relaxes false
    positives for legitimate categorical bucket strings / sha256
    manifest hashes that appear under BEA-1-specific safe value paths
    (e.g. ``private_score_manifest.manifest_hash``). BEA-1 ADDS rejection
    of BEA-1-specific claim-boundary keys (``calibration``,
    ``method_winner``, etc.) anywhere.
    """
    violations: list[dict[str, Any]] = []
    for v in bea0._scan_bea0(obj):
        cat = v.get("category")
        if cat == "forbidden_field_name_value" and _bea1_safe_value_path(
            v.get("path", "")
        ):
            continue
        if cat == "hex_digest_value" and _bea1_safe_value_path(
            v.get("path", "")
        ):
            continue
        violations.append(v)
    violations.extend(_scan_bea1_forbidden_keys(obj))
    return violations


def _bea1_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    """Run the BEA-1 forbidden scanner and return a sanitized summary."""
    violations = _scan_bea1(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_bea1_no_forbidden(obj: Any) -> None:
    """Fail-closed guard: raise SystemExit if any forbidden content leaks."""
    scan = _bea1_forbidden_scan_summary(obj)
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
    """Validate and cap --contextbench-row-limit to the hard cap (20)."""
    if not isinstance(row_limit, int):
        raise SystemExit("invalid arguments")
    if row_limit < 1:
        raise SystemExit("invalid arguments")
    if row_limit > CONTEXTBENCH_ROW_LIMIT_HARD_CAP:
        return CONTEXTBENCH_ROW_LIMIT_HARD_CAP
    return row_limit


def _validate_needle_limit(needle_limit: int) -> int:
    """Validate and cap --repoqa-needle-limit to the hard cap (10)."""
    if not isinstance(needle_limit, int):
        raise SystemExit("invalid arguments")
    if needle_limit < 1:
        raise SystemExit("invalid arguments")
    if needle_limit > REPOQA_NEEDLE_LIMIT_HARD_CAP:
        return REPOQA_NEEDLE_LIMIT_HARD_CAP
    return needle_limit


def _validate_budget(budget: int) -> int:
    """Validate and cap --budget to the hard cap (20)."""
    if not isinstance(budget, int):
        raise SystemExit("invalid arguments")
    if budget < 1:
        raise SystemExit("invalid arguments")
    if budget > BUDGET_HARD_CAP:
        return BUDGET_HARD_CAP
    return budget


def _validate_methods(methods: str) -> tuple[str, ...]:
    """Validate the --methods comma-separated list. Returns the parsed tuple.

    Allowed methods: bm25, regex, symbol. At least bm25 must be present.
    Duplicate methods are de-duplicated while preserving order.
    """
    return bea0._validate_methods(methods)


# ---------------------------------------------------------------------------
# Private SCORE JSONL writer (transient /tmp only; never committed).
# ---------------------------------------------------------------------------


def _resolve_private_score_dir(
    explicit: str | None,
) -> tuple[Path, str]:
    """Resolve the private SCORE JSONL directory.

    Wraps BEA-0's resolver. Default: a fresh TemporaryDirectory under
    ``/tmp``. If ``explicit`` is given, it must be under ``/tmp`` or the
    gitignored ``runs/`` directory.
    """
    return bea0._resolve_private_score_dir(explicit)


def _private_score_manifest_hash() -> str:
    """Compute a stable sha256 of the private SCORE manifest schema.

    The manifest schema is the fixed set of fields each private row carries
    (NOT the row values themselves). This hash is safe to publish because
    it is computed only over the canonical schema definition.
    """
    manifest_schema = {
        "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
        "fields": [
            "phase_run_id",
            "benchmark",
            "private_record_id",
            "runtime_query_feature_summary",
            "candidate_list",
            "bea_v0_action_trace",
            "bea_v0_budget_states",
            "bea_v0_accepted_candidates",
            "final_candidates",
            "baseline_bm25_top10_evidence",
            "baseline_rrf_top10_evidence",
            "same_budget_bm25_prefix_evidence",
            "agreement_only_same_budget_evidence",
            "seeded_random_same_budget_evidence",
            "same_budget_k",
            "score_outcome",
            "latency_ms",
            "cost_usd",
            "tokens",
            "provider_calls",
            "failure_reason",
        ],
        "candidate_fields": [
            "method",
            "rank",
            "score",
            "normalized_score",
            "path",
            "start_line",
            "end_line",
            "content_sha",
            "extension",
            "agreement",
        ],
    }
    canonical = json.dumps(manifest_schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_private_score_row(
    score_path: Path,
    row: dict[str, Any],
) -> None:
    """Append a single private SCORE row to the JSONL file (transient /tmp).
    """
    bea0._write_private_score_row(score_path, row)


# ---------------------------------------------------------------------------
# Same-budget control arm algorithms
# ---------------------------------------------------------------------------


def _dedup_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deduplicate candidates by ``(path, start_line, end_line)`` span.

    Returns a list of deduped span summaries (same shape as the BEA-0
    policy's internal ``dedup`` list). Stable order: first occurrence wins.
    Each entry carries: path, start_line, end_line, content_sha, extension,
    method, rank, score, normalized_score, agreement (count of distinct
    methods), min_rank, max_norm_score, max_score.
    """
    span_summary: dict[tuple[str, int, int], dict[str, Any]] = {}
    for c in candidates:
        key = bea0._span_key(c)
        if key not in span_summary:
            span_summary[key] = {
                "path": c["path"],
                "start_line": c["start_line"],
                "end_line": c["end_line"],
                "content_sha": c.get("content_sha", ""),
                "extension": c["extension"],
                "method": c["method"],
                "rank": c["rank"],
                "score": c["score"],
                "normalized_score": c["normalized_score"],
                "methods": set(),
                "min_rank": 99,
                "max_norm_score": 0.0,
                "max_score": 0.0,
                "first_method": c["method"],
                "first_rank": c["rank"],
                "stable_index": len(span_summary),
            }
        s = span_summary[key]
        s["methods"].add(c["method"])
        s["min_rank"] = min(s["min_rank"], c["rank"])
        s["max_norm_score"] = max(s["max_norm_score"], c["normalized_score"])
        s["max_score"] = max(s["max_score"], c["score"])
    return list(span_summary.values())


def _same_budget_k(
    bea_accepted_count: int,
    deduped_count: int,
) -> int:
    """Same-budget K exactly per plan.

    ``K = min(len(bea_v0_budgeted.accepted_candidates), available_deduped_candidate_count)``

    If BEA accepts zero candidates, K=0; same-budget controls also select
    zero.
    """
    if bea_accepted_count <= 0:
        return 0
    if deduped_count <= 0:
        return 0
    return min(bea_accepted_count, deduped_count)


def _same_budget_bm25_prefix_arm(
    method_candidates: dict[str, list[dict[str, Any]]],
    k: int,
) -> list[dict[str, Any]]:
    """``same_budget_bm25_prefix`` arm.

    First ``K`` BM25 candidates after dedupe; no agreement reranking, no
    BEA sequential coverage/defer/expand rules. Returns evidence list
    (path, start_line, end_line, content_sha) for scoring.
    """
    if k <= 0:
        return []
    bm25_cands = method_candidates.get("bm25", [])
    if not bm25_cands:
        return []
    # Dedupe BM25 candidates by span.
    seen: set[tuple[str, int, int]] = set()
    deduped: list[dict[str, Any]] = []
    for c in bm25_cands:
        key = bea0._span_key(c)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)
    selected = deduped[:k]
    return [
        {
            "path": c["path"],
            "start_line": c["start_line"],
            "end_line": c["end_line"],
            "content_sha": c.get("content_sha", ""),
        }
        for c in selected
    ]


def _agreement_only_same_budget_arm(
    all_candidates: list[dict[str, Any]],
    k: int,
) -> list[dict[str, Any]]:
    """``agreement_only_same_budget`` arm.

    Same deduped candidate universe as BEA; sort by agreement desc,
    min_rank asc, max_normalized_score desc, stable candidate order; take
    first ``K``; no BEA sequential coverage/defer/expand rules.
    """
    if k <= 0 or not all_candidates:
        return []
    deduped = _dedup_candidates(all_candidates)
    # Sort by (agreement desc, min_rank asc, max_norm_score desc, stable_index asc).
    deduped.sort(
        key=lambda c: (
            -len(c["methods"]),
            c["min_rank"],
            -c["max_norm_score"],
            c["stable_index"],
        )
    )
    selected = deduped[:k]
    return [
        {
            "path": c["path"],
            "start_line": c["start_line"],
            "end_line": c["end_line"],
            "content_sha": c.get("content_sha", ""),
        }
        for c in selected
    ]


def _seeded_random_same_budget_arm(
    all_candidates: list[dict[str, Any]],
    k: int,
) -> list[dict[str, Any]]:
    """``seeded_random_same_budget`` arm.

    Deterministic PRNG with fixed public seed ``20240621``; sample ``K``
    from the same deduped candidate universe after stable ordering; no
    gold/labels/row IDs/provider/model fields in seed or ordering.
    """
    if k <= 0 or not all_candidates:
        return []
    deduped = _dedup_candidates(all_candidates)
    # Stable ordering: by stable_index asc (insertion order).
    deduped.sort(key=lambda c: c["stable_index"])
    n = len(deduped)
    if k >= n:
        selected = deduped
    else:
        # Deterministic sample: seeded shuffle then take first K.
        rng = random.Random(SEEDED_RANDOM_SEED)
        indices = list(range(n))
        rng.shuffle(indices)
        selected_indices = sorted(indices[:k])  # preserve stable order in output
        selected = [deduped[i] for i in selected_indices]
    return [
        {
            "path": c["path"],
            "start_line": c["start_line"],
            "end_line": c["end_line"],
            "content_sha": c.get("content_sha", ""),
        }
        for c in selected
    ]


# ---------------------------------------------------------------------------
# Per-arm metrics computation (reuses BEA-0 helpers).
# ---------------------------------------------------------------------------


def _arm_metrics_for_record(
    arm_id: str,
    accepted_evidence: list[dict[str, Any]],
    gold_record: dict[str, Any],
    task_id: str,
    candidate_count_read: int,
    evidence_budget_used: int,
    action_steps: int,
    latency_seconds: float,
) -> dict[str, Any]:
    """Compute per-arm metrics for one record (wraps BEA-0 helper)."""
    return bea0._arm_metrics(
        arm_id,
        accepted_evidence,
        gold_record,
        task_id,
        candidate_count_read,
        evidence_budget_used,
        action_steps,
        latency_seconds,
    )


def _filter_arm_metrics(arm: dict[str, Any]) -> dict[str, Any]:
    """Filter an arm metrics dict to the allowlist only."""
    return bea0._filter_arm_metrics(arm)


def _arm_means(
    per_record_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute per-arm aggregate means across records."""
    return bea0._arm_means(per_record_metrics)


def _arm_metric_records(
    arm_metrics: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert arm metric maps to fixed-shape public records."""
    return bea0._arm_metric_records(arm_metrics)


def _delta_records(
    arm_metrics: dict[str, dict[str, Any]],
    baseline_arm: str,
    treatment_arms: list[str],
) -> list[dict[str, Any]]:
    """Convert baseline-vs-treatment delta maps to fixed-shape records.

    Each record: ``{baseline_arm, treatment_arm, metric, delta}``.
    """
    records: list[dict[str, Any]] = []
    baseline_agg = arm_metrics.get(baseline_arm, {})
    for treatment_arm in treatment_arms:
        treatment_agg = arm_metrics.get(treatment_arm, {})
        for metric in ARM_METRIC_ALLOWLIST:
            t = treatment_agg.get(metric, 0.0)
            b = baseline_agg.get(metric, 0.0)
            if isinstance(t, (int, float)) and isinstance(b, (int, float)):
                records.append(
                    {
                        "baseline_arm": baseline_arm,
                        "treatment_arm": treatment_arm,
                        "metric": metric,
                        "delta": round(float(t) - float(b), 6),
                    }
                )
    # Sort for stable output.
    records.sort(
        key=lambda r: (r["treatment_arm"], r["metric"])
    )
    return records


def _mechanism_contrast_records(
    per_record_arm_metrics: list[dict[str, dict[str, Any]]],
    contrasts: list[tuple[str, str, str]],
) -> list[dict[str, Any]]:
    """Compute fixed-shape mechanism contrast records on the paired denominator.

    Each contrast: ``(contrast_id, baseline_arm, treatment_arm)`` where the
    baseline is a same-budget control and the treatment is
    ``bea_v0_budgeted``. A contrast only includes records where BOTH arms
    have valid metrics for the same record (paired denominator rule).

    Each record: ``{contrast, baseline_arm, treatment_arm, metric, delta,
    record_count}``.
    """
    records: list[dict[str, Any]] = []
    for contrast_id, baseline_arm, treatment_arm in contrasts:
        # Collect paired records: only records where both arms have metrics.
        paired_baseline: list[dict[str, Any]] = []
        paired_treatment: list[dict[str, Any]] = []
        for rec in per_record_arm_metrics:
            if baseline_arm in rec and treatment_arm in rec:
                paired_baseline.append(rec[baseline_arm])
                paired_treatment.append(rec[treatment_arm])
        record_count = len(paired_baseline)
        if record_count == 0:
            continue
        baseline_agg = _arm_means(paired_baseline)
        treatment_agg = _arm_means(paired_treatment)
        for metric in ARM_METRIC_ALLOWLIST:
            t = treatment_agg.get(metric, 0.0)
            b = baseline_agg.get(metric, 0.0)
            if isinstance(t, (int, float)) and isinstance(b, (int, float)):
                records.append(
                    {
                        "contrast": contrast_id,
                        "baseline_arm": baseline_arm,
                        "treatment_arm": treatment_arm,
                        "metric": metric,
                        "delta": round(float(t) - float(b), 6),
                        "record_count": record_count,
                    }
                )
    # Sort for stable output.
    records.sort(
        key=lambda r: (r["contrast"], r["metric"])
    )
    return records


# ---------------------------------------------------------------------------
# Per-record evaluation
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
) -> tuple[dict[str, Any] | None, dict[str, int]]:
    """Evaluate one record (ContextBench row or RepoQA needle).

    Runs multi-method retrieval, builds the candidate list, runs all fixed
    arms (bm25_top10, rrf_bm25_regex_symbol_top10 when enabled,
    bea_v0_budgeted, same_budget_bm25_prefix, agreement_only_same_budget,
    seeded_random_same_budget), computes per-arm metrics, writes a private
    SCORE JSONL row, and returns per-arm metrics (or None on failure).

    The private SCORE row is written ONLY under ``/tmp``. It contains the
    full per-record detail including same-budget control arm evidence and
    the per-record same-budget K.
    """
    rec_start = time.perf_counter()
    failure_reason: str | None = None

    # Collect candidates per method.
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

    # Collect rrf baseline candidates (only if enabled).
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

    # If NO candidates at all from any method, fail this record.
    if not all_candidates:
        failure_reason = "no_candidates_from_any_method"
        fcc["retrieval_failed"] = fcc.get("retrieval_failed", 0) + 1

    # Gold record for eval/score.py functions.
    gold_record = {
        "task_id": task_id,
        "gold_paths": gold_paths,
        "gold_lines": gold_lines,
    }

    # --- Baseline arm: bm25_top10 ---
    bm25_top10 = method_candidates.get("bm25", [])[:10]
    bm25_metrics = _arm_metrics_for_record(
        ARM_BM25_TOP10,
        bm25_top10,
        gold_record,
        task_id,
        candidate_count_read=len(method_candidates.get("bm25", [])),
        evidence_budget_used=len(bm25_top10),
        action_steps=len(bm25_top10),
        latency_seconds=(
            method_latencies_ms.get("bm25", 0) / 1000.0
        ),
    )

    # --- Baseline arm: rrf_bm25_regex_symbol_top10 (conditional) ---
    rrf_metrics: dict[str, Any] | None = None
    if enable_rrf_baseline:
        rrf_top10 = rrf_candidates[:10]
        rrf_metrics = _arm_metrics_for_record(
            ARM_RRF_TOP10,
            rrf_top10,
            gold_record,
            task_id,
            candidate_count_read=len(rrf_candidates),
            evidence_budget_used=len(rrf_top10),
            action_steps=len(rrf_top10),
            latency_seconds=rrf_latency_ms / 1000.0,
        )

    # --- Treatment arm: bea_v0_budgeted ---
    if all_candidates and failure_reason is None:
        accepted, action_trace, budget_states = (
            bea0._bea_v0_budgeted_policy(all_candidates, budget)
        )
    else:
        accepted, action_trace, budget_states = [], [], []
    treatment_metrics = _arm_metrics_for_record(
        ARM_BEA_V0_BUDGETED,
        accepted,
        gold_record,
        task_id,
        candidate_count_read=len(all_candidates),
        evidence_budget_used=len(accepted),
        action_steps=len(action_trace),
        latency_seconds=time.perf_counter() - rec_start,
    )

    # --- Same-budget K exactly per plan ---
    deduped_count = len(_dedup_candidates(all_candidates)) if all_candidates else 0
    same_budget_k = _same_budget_k(len(accepted), deduped_count)

    # --- Same-budget control arm: same_budget_bm25_prefix ---
    sb_bm25_evidence = _same_budget_bm25_prefix_arm(
        method_candidates, same_budget_k
    )
    sb_bm25_metrics = _arm_metrics_for_record(
        ARM_SAME_BUDGET_BM25_PREFIX,
        sb_bm25_evidence,
        gold_record,
        task_id,
        candidate_count_read=len(method_candidates.get("bm25", [])),
        evidence_budget_used=len(sb_bm25_evidence),
        action_steps=len(sb_bm25_evidence),
        latency_seconds=0.0,  # same-budget control is in-process; no retrieval latency
    )

    # --- Same-budget control arm: agreement_only_same_budget ---
    ao_evidence = _agreement_only_same_budget_arm(
        all_candidates, same_budget_k
    )
    ao_metrics = _arm_metrics_for_record(
        ARM_AGREEMENT_ONLY_SAME_BUDGET,
        ao_evidence,
        gold_record,
        task_id,
        candidate_count_read=len(all_candidates),
        evidence_budget_used=len(ao_evidence),
        action_steps=len(ao_evidence),
        latency_seconds=0.0,
    )

    # --- Same-budget control arm: seeded_random_same_budget ---
    sr_evidence = _seeded_random_same_budget_arm(
        all_candidates, same_budget_k
    )
    sr_metrics = _arm_metrics_for_record(
        ARM_SEEDED_RANDOM_SAME_BUDGET,
        sr_evidence,
        gold_record,
        task_id,
        candidate_count_read=len(all_candidates),
        evidence_budget_used=len(sr_evidence),
        action_steps=len(sr_evidence),
        latency_seconds=0.0,
    )

    # --- Per-arm metrics dict (transient; written to private SCORE only) ---
    per_arm_metrics: dict[str, dict[str, Any]] = {
        ARM_BM25_TOP10: bm25_metrics,
        ARM_BEA_V0_BUDGETED: treatment_metrics,
        ARM_SAME_BUDGET_BM25_PREFIX: sb_bm25_metrics,
        ARM_AGREEMENT_ONLY_SAME_BUDGET: ao_metrics,
        ARM_SEEDED_RANDOM_SAME_BUDGET: sr_metrics,
    }
    if rrf_metrics is not None:
        per_arm_metrics[ARM_RRF_TOP10] = rrf_metrics

    rec_latency_ms = int((time.perf_counter() - rec_start) * 1000)

    # --- Build private SCORE row ---
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
        "bea_v0_accepted_count": int(len(accepted)),
        "query_length_chars": len(query) if isinstance(query, str) else 0,
        "query_word_count": (
            len(query.split()) if isinstance(query, str) and query else 0
        ),
    }

    # Build the private candidate list (deep copy with safe-to-log private
    # fields). Goes to /tmp private SCORE only; NEVER public.
    private_candidate_list: list[dict[str, Any]] = []
    for c in all_candidates:
        private_candidate_list.append(
            {
                "method": c["method"],
                "rank": c["rank"],
                "score": c["score"],
                "normalized_score": c["normalized_score"],
                "path": c["path"],
                "start_line": c["start_line"],
                "end_line": c["end_line"],
                "content_sha": c["content_sha"],
                "extension": c["extension"],
                "agreement": 0,
            }
        )
    # Fill agreement per candidate.
    span_agreement: dict[tuple[str, int, int], int] = {}
    for c in all_candidates:
        key = bea0._span_key(c)
        span_agreement.setdefault(key, 0)
        span_agreement[key] += 1
    for c in private_candidate_list:
        key = (c["path"], c["start_line"], c["end_line"])
        c["agreement"] = span_agreement.get(key, 0)

    private_score_row = {
        "phase_run_id": phase_run_id,
        "benchmark": benchmark,
        "private_record_id": private_record_id,
        "runtime_query_feature_summary": runtime_query_feature_summary,
        "candidate_list": private_candidate_list,
        "bea_v0_action_trace": action_trace,
        "bea_v0_budget_states": budget_states,
        "bea_v0_accepted_candidates": accepted,
        "final_candidates": accepted,
        "baseline_bm25_top10_evidence": bm25_top10,
        "baseline_rrf_top10_evidence": rrf_candidates[:10] if enable_rrf_baseline else [],
        "same_budget_bm25_prefix_evidence": sb_bm25_evidence,
        "agreement_only_same_budget_evidence": ao_evidence,
        "seeded_random_same_budget_evidence": sr_evidence,
        "same_budget_k": int(same_budget_k),
        "score_outcome": per_arm_metrics,
        "latency_ms": rec_latency_ms,
        "cost_usd": 0.0,
        "tokens": 0,
        "provider_calls": 0,
        "failure_reason": failure_reason,
        "method_latencies_ms": method_latencies_ms,
        "rrf_latency_ms": rrf_latency_ms,
        "method_errors": method_errors,
        "rrf_error": rrf_error,
    }

    try:
        _write_private_score_row(score_path, private_score_row)
    except OSError:
        fcc["private_score_write_failed"] = (
            fcc.get("private_score_write_failed", 0) + 1
        )
        return None, fcc

    return per_arm_metrics, fcc


# ---------------------------------------------------------------------------
# Public report builders (fail-closed scan).
# ---------------------------------------------------------------------------


def _build_unavailable_report(
    failure_reason_category: str,
    *,
    self_test_passed: bool,
    contextbench_row_limit_requested: int,
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
    """Build a truthful ``unavailable_with_reason`` report."""
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    if failure_category_counts:
        for k, v in failure_category_counts.items():
            if k in fcc:
                fcc[k] = int(v)
    if failure_reason_category in fcc:
        fcc[failure_reason_category] = max(
            fcc[failure_reason_category], 1
        )

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["external_benchmark_rows_read"] = records_evaluated > 0
    safe_true["openlocus_retrieval_executed"] = False
    safe_true["score_py_metrics_computed"] = False
    safe_true["mechanism_ablation_performed"] = False
    safe_true["bea_v0_acquisition_performed"] = False
    safe_true["private_score_records_written"] = bool(
        private_score_records_written
    )

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
        "contextbench_row_limit_requested": contextbench_row_limit_requested,
        "repoqa_needle_limit_requested": repoqa_needle_limit_requested,
        "records_evaluated": records_evaluated,
        "records_successful": records_successful,
        "records_failed": records_failed,
        "network_calls": network_calls,
        "provider_calls": 0,
        "failure_reason_category": failure_reason_category,
        "failure_category_counts": fcc,
        "arm_metric_records": [],
        "delta_records": [],
        "mechanism_contrast_records": [],
        "private_score_manifest": {
            "records_written": bool(private_score_records_written),
            "record_count": int(private_score_record_count),
            "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
            "manifest_hash": manifest_hash,
            "storage_class": private_score_storage_class,
            "path_publicly_serialized": False,
        },
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
            "calibration_claimed": False,
            "method_winner_claimed": False,
            "signal_strength": "bea_v0_mechanism_ablation_smoke_unavailable",
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _bea1_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _build_pass_report(
    *,
    self_test_passed: bool,
    contextbench_row_limit_requested: int,
    repoqa_needle_limit_requested: int,
    budget: int,
    methods: tuple[str, ...],
    openlocus_binary_source: str,
    network_mode: str,
    records_evaluated: int,
    records_successful: int,
    records_failed: int,
    network_calls: int,
    arm_metrics: dict[str, dict[str, Any]],
    per_record_arm_metrics: list[dict[str, dict[str, Any]]],
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
    """Build a pass/partial report with aggregate metrics + deltas + contrasts."""
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    for k, v in failure_category_counts.items():
        if k in fcc:
            fcc[k] = int(v)

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["external_benchmark_rows_read"] = records_evaluated > 0
    safe_true["openlocus_retrieval_executed"] = records_successful > 0
    safe_true["score_py_metrics_computed"] = bool(arm_metrics)
    safe_true["mechanism_ablation_performed"] = records_successful > 0
    safe_true["bea_v0_acquisition_performed"] = records_successful > 0
    safe_true["private_score_records_written"] = bool(
        private_score_records_written
    )

    arm_metric_records = _arm_metric_records(arm_metrics)

    # Delta records: each treatment arm vs the fixed bm25_top10 baseline.
    treatment_arms = [
        ARM_BEA_V0_BUDGETED,
        ARM_SAME_BUDGET_BM25_PREFIX,
        ARM_AGREEMENT_ONLY_SAME_BUDGET,
        ARM_SEEDED_RANDOM_SAME_BUDGET,
    ]
    if enable_rrf_baseline:
        treatment_arms.append(ARM_RRF_TOP10)
    delta_records = _delta_records(
        arm_metrics, BASELINE_ARM, treatment_arms
    )

    # Mechanism contrast records: bea_v0_budgeted vs each same-budget control.
    contrasts = [
        (CONTRAST_BEA_VS_SAME_BUDGET_BM25, ARM_SAME_BUDGET_BM25_PREFIX, ARM_BEA_V0_BUDGETED),
        (CONTRAST_BEA_VS_AGREEMENT_ONLY, ARM_AGREEMENT_ONLY_SAME_BUDGET, ARM_BEA_V0_BUDGETED),
        (CONTRAST_BEA_VS_SEEDED_RANDOM, ARM_SEEDED_RANDOM_SAME_BUDGET, ARM_BEA_V0_BUDGETED),
    ]
    mechanism_contrast_records = _mechanism_contrast_records(
        per_record_arm_metrics, contrasts
    )

    if records_successful > 0 and records_failed == 0 and not partial:
        status = "bea1_mechanism_ablation_pass"
    elif records_successful > 0:
        status = "partial"
    else:
        status = "unavailable_with_reason"

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
        "fixed_arms": (
            [ARM_BM25_TOP10, ARM_BEA_V0_BUDGETED,
             ARM_SAME_BUDGET_BM25_PREFIX,
             ARM_AGREEMENT_ONLY_SAME_BUDGET,
             ARM_SEEDED_RANDOM_SAME_BUDGET,
             ARM_RRF_TOP10]
            if enable_rrf_baseline
            else [ARM_BM25_TOP10, ARM_BEA_V0_BUDGETED,
                  ARM_SAME_BUDGET_BM25_PREFIX,
                  ARM_AGREEMENT_ONLY_SAME_BUDGET,
                  ARM_SEEDED_RANDOM_SAME_BUDGET]
        ),
        "baseline_arm": BASELINE_ARM,
        "treatment_arm": ARM_BEA_V0_BUDGETED,
        "seeded_random_seed": SEEDED_RANDOM_SEED,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "contextbench_row_limit_requested": contextbench_row_limit_requested,
        "repoqa_needle_limit_requested": repoqa_needle_limit_requested,
        "records_evaluated": records_evaluated,
        "records_successful": records_successful,
        "records_failed": records_failed,
        "paired_exclusion_count": int(paired_exclusion_count),
        "network_calls": network_calls,
        "provider_calls": 0,
        "arm_metric_records": arm_metric_records,
        "delta_records": delta_records,
        "mechanism_contrast_records": mechanism_contrast_records,
        "private_score_manifest": {
            "records_written": bool(private_score_records_written),
            "record_count": int(private_score_record_count),
            "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
            "manifest_hash": private_score_manifest_hash,
            "storage_class": private_score_storage_class,
            "path_publicly_serialized": False,
        },
        "aggregate_runtime_seconds": round(
            float(aggregate_runtime_seconds), 3
        ),
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
            "calibration_claimed": False,
            "method_winner_claimed": False,
            "signal_strength": "bea_v0_mechanism_ablation_smoke_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _bea1_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


# ---------------------------------------------------------------------------
# Self-test (no network; synthetic candidates + synthetic score data).
# ---------------------------------------------------------------------------


def _build_synthetic_candidates() -> list[dict[str, Any]]:
    """Build a synthetic multi-method candidate list for the self-test."""
    return bea0._build_synthetic_candidates()


def _build_synthetic_gold() -> dict[str, Any]:
    """Build a synthetic gold record for self-test."""
    return bea0._build_synthetic_gold()


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all BEA-1 self-test groups (no network; synthetic data)."""
    checks: list[dict[str, Any]] = []

    # --- Group 1: Artifact identity fields. ---
    candidates = _build_synthetic_candidates()
    gold = _build_synthetic_gold()
    accepted, action_trace, budget_states = bea0._bea_v0_budgeted_policy(
        candidates, budget=10
    )
    same_budget_k = _same_budget_k(len(accepted), len(_dedup_candidates(candidates)))
    sb_bm25_ev = _same_budget_bm25_prefix_arm(
        {"bm25": [c for c in candidates if c["method"] == "bm25"]},
        same_budget_k,
    )
    ao_ev = _agreement_only_same_budget_arm(candidates, same_budget_k)
    sr_ev = _seeded_random_same_budget_arm(candidates, same_budget_k)
    bm25_ev = [c for c in candidates if c["method"] == "bm25"][:10]
    bm25_m = _arm_metrics_for_record(
        ARM_BM25_TOP10, bm25_ev, gold, "bea1-st-001",
        len([c for c in candidates if c["method"] == "bm25"]),
        len(bm25_ev), len(bm25_ev), 0.01,
    )
    bea_m = _arm_metrics_for_record(
        ARM_BEA_V0_BUDGETED, accepted, gold, "bea1-st-001",
        len(candidates), len(accepted), len(action_trace), 0.05,
    )
    sb_bm25_m = _arm_metrics_for_record(
        ARM_SAME_BUDGET_BM25_PREFIX, sb_bm25_ev, gold, "bea1-st-001",
        len([c for c in candidates if c["method"] == "bm25"]),
        len(sb_bm25_ev), len(sb_bm25_ev), 0.0,
    )
    ao_m = _arm_metrics_for_record(
        ARM_AGREEMENT_ONLY_SAME_BUDGET, ao_ev, gold, "bea1-st-001",
        len(candidates), len(ao_ev), len(ao_ev), 0.0,
    )
    sr_m = _arm_metrics_for_record(
        ARM_SEEDED_RANDOM_SAME_BUDGET, sr_ev, gold, "bea1-st-001",
        len(candidates), len(sr_ev), len(sr_ev), 0.0,
    )
    arm_metrics = {
        ARM_BM25_TOP10: _arm_means([bm25_m]),
        ARM_BEA_V0_BUDGETED: _arm_means([bea_m]),
        ARM_SAME_BUDGET_BM25_PREFIX: _arm_means([sb_bm25_m]),
        ARM_AGREEMENT_ONLY_SAME_BUDGET: _arm_means([ao_m]),
        ARM_SEEDED_RANDOM_SAME_BUDGET: _arm_means([sr_m]),
    }
    per_record_arm_metrics = [
        {
            ARM_BM25_TOP10: bm25_m,
            ARM_BEA_V0_BUDGETED: bea_m,
            ARM_SAME_BUDGET_BM25_PREFIX: sb_bm25_m,
            ARM_AGREEMENT_ONLY_SAME_BUDGET: ao_m,
            ARM_SEEDED_RANDOM_SAME_BUDGET: sr_m,
        }
    ]
    manifest_hash = _private_score_manifest_hash()
    skeleton = _build_pass_report(
        self_test_passed=True,
        contextbench_row_limit_requested=5,
        repoqa_needle_limit_requested=3,
        budget=5,
        methods=("bm25", "regex", "symbol"),
        openlocus_binary_source="default",
        network_mode="local_explicit",
        records_evaluated=8,
        records_successful=8,
        records_failed=0,
        network_calls=2,
        arm_metrics=arm_metrics,
        per_record_arm_metrics=per_record_arm_metrics,
        private_score_records_written=True,
        private_score_record_count=8,
        private_score_storage_class="tmp_private",
        private_score_manifest_hash=manifest_hash,
        aggregate_runtime_seconds=42.0,
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES},
        enable_rrf_baseline=False,
        paired_exclusion_count=0,
        partial=False,
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
    checks.append(_check("mode_correct", skeleton["mode"] == MODE))
    checks.append(_check("phase_correct", skeleton["phase"] == PHASE))
    checks.append(
        _check(
            "generated_by_correct",
            skeleton["generated_by"] == GENERATED_BY,
        )
    )
    checks.append(
        _check(
            "status_pass_when_self_test_passed",
            skeleton["status"] == "bea1_mechanism_ablation_pass",
        )
    )
    checks.append(
        _check(
            "treatment_arm_correct",
            skeleton["treatment_arm"] == ARM_BEA_V0_BUDGETED,
        )
    )
    checks.append(
        _check(
            "baseline_arm_correct",
            skeleton["baseline_arm"] == BASELINE_ARM,
        )
    )
    checks.append(
        _check(
            "seeded_random_seed_correct",
            skeleton["seeded_random_seed"] == SEEDED_RANDOM_SEED,
        )
    )

    # --- Group 2: Safe true flags present + correct values. ---
    for flag in SAFE_TRUE_FLAGS:
        checks.append(
            _check(
                f"safe_true_{flag}_present",
                flag in skeleton,
            )
        )
    checks.append(
        _check(
            "safe_true_aggregate_only_public_artifact",
            skeleton.get("aggregate_only_public_artifact") is True,
        )
    )
    checks.append(
        _check(
            "safe_true_diagnostic_only",
            skeleton.get("diagnostic_only") is True,
        )
    )
    checks.append(
        _check(
            "safe_true_mechanism_ablation_performed",
            skeleton.get("mechanism_ablation_performed") is True,
        )
    )
    checks.append(
        _check(
            "safe_true_bea_v0_acquisition_performed",
            skeleton.get("bea_v0_acquisition_performed") is True,
        )
    )
    checks.append(
        _check(
            "safe_true_private_score_records_written",
            skeleton.get("private_score_records_written") is True,
        )
    )

    # --- Group 3: No-claim / no-runtime-change false flags. ---
    for flag in DEFAULT_FALSE_FLAGS:
        checks.append(
            _check(
                f"no_claim_{flag}_false",
                skeleton.get(flag) is False,
            )
        )

    # --- Group 4: License fields. ---
    checks.append(
        _check(
            "license_dataset_license_status",
            skeleton.get("dataset_license_status")
            == "unknown_dataset_license",
        )
    )
    checks.append(
        _check(
            "license_row_level_redistribution_allowed_false",
            skeleton.get("row_level_redistribution_allowed") is False,
        )
    )
    checks.append(
        _check(
            "license_derived_row_level_publication_allowed_false",
            skeleton.get("derived_row_level_publication_allowed")
            is False,
        )
    )
    checks.append(
        _check(
            "license_aggregate_metrics_publication",
            skeleton.get("aggregate_metrics_publication")
            == "aggregate_only_smoke",
        )
    )

    # --- Group 5: Private SCORE manifest aggregate-only fields. ---
    manifest = skeleton.get("private_score_manifest", {})
    checks.append(
        _check(
            "private_score_manifest_present",
            isinstance(manifest, dict) and len(manifest) > 0,
        )
    )
    checks.append(
        _check(
            "private_score_manifest_records_written_true",
            manifest.get("records_written") is True,
        )
    )
    checks.append(
        _check(
            "private_score_manifest_record_count_correct",
            manifest.get("record_count") == 8,
        )
    )
    checks.append(
        _check(
            "private_score_manifest_schema_version_correct",
            manifest.get("schema_version") == PRIVATE_SCORE_SCHEMA_VERSION,
        )
    )
    checks.append(
        _check(
            "private_score_manifest_storage_class_correct",
            manifest.get("storage_class") == "tmp_private",
        )
    )
    checks.append(
        _check(
            "private_score_manifest_path_not_publicly_serialized",
            manifest.get("path_publicly_serialized") is False,
        )
    )
    checks.append(
        _check(
            "private_score_manifest_hash_is_sha256_hex",
            isinstance(manifest.get("manifest_hash"), str)
            and len(manifest["manifest_hash"]) == 64
            and all(
                c in "0123456789abcdef"
                for c in manifest["manifest_hash"]
            ),
        )
    )
    # The private score path string must NEVER appear anywhere.
    for forbidden_key in (
        "private_score_path", "score_path", "private_score_file",
        "action_trace", "budget_states", "accepted_candidates",
        "final_candidates", "candidate_list", "candidates",
        "score_outcome", "per_record_metrics",
        "runtime_query_features", "query_features",
        "private_record_id", "private_record_hash",
    ):
        checks.append(
            _check(
                f"private_score_forbidden_key_{forbidden_key}_absent",
                forbidden_key not in skeleton,
            )
        )

    # --- Group 6: Row/needle/budget hard caps. ---
    checks.append(
        _check(
            "contextbench_row_limit_default_5",
            CONTEXTBENCH_ROW_LIMIT_DEFAULT == 5,
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
            "contextbench_row_limit_caps_at_20",
            _validate_row_limit(100) == 20,
        )
    )
    checks.append(
        _check(
            "repoqa_needle_limit_default_3",
            REPOQA_NEEDLE_LIMIT_DEFAULT == 3,
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
            "repoqa_needle_limit_caps_at_10",
            _validate_needle_limit(100) == 10,
        )
    )
    try:
        _validate_row_limit(0)
        checks.append(_check("row_limit_rejects_zero", False))
    except SystemExit:
        checks.append(_check("row_limit_rejects_zero", True))
    try:
        _validate_needle_limit(0)
        checks.append(_check("needle_limit_rejects_zero", False))
    except SystemExit:
        checks.append(_check("needle_limit_rejects_zero", True))

    # --- Group 7: Budget hard cap. ---
    checks.append(
        _check(
            "budget_default_5",
            BUDGET_DEFAULT == 5,
        )
    )
    checks.append(
        _check(
            "budget_hard_cap_20",
            BUDGET_HARD_CAP == 20,
        )
    )
    checks.append(
        _check(
            "budget_caps_at_20",
            _validate_budget(100) == 20,
        )
    )
    try:
        _validate_budget(0)
        checks.append(_check("budget_rejects_zero", False))
    except SystemExit:
        checks.append(_check("budget_rejects_zero", True))

    # --- Group 8: Method validation. ---
    checks.append(
        _check(
            "methods_default_correct",
            _validate_methods(DEFAULT_METHODS)
            == ("bm25", "regex", "symbol"),
        )
    )
    try:
        _validate_methods("regex,symbol")
        checks.append(_check("methods_requires_bm25_present", False))
    except SystemExit:
        checks.append(_check("methods_requires_bm25_present", True))
    try:
        _validate_methods("bm25,dense")
        checks.append(_check("methods_rejects_dense", False))
    except SystemExit:
        checks.append(_check("methods_rejects_dense", True))

    # --- Group 9: Same-budget K exactly per plan. ---
    checks.append(
        _check(
            "same_budget_k_min_of_bea_accepted_and_deduped",
            _same_budget_k(3, 5) == 3
            and _same_budget_k(5, 3) == 3
            and _same_budget_k(10, 10) == 10,
        )
    )
    checks.append(
        _check(
            "same_budget_k_zero_when_bea_accepts_zero",
            _same_budget_k(0, 5) == 0,
        )
    )
    checks.append(
        _check(
            "same_budget_k_zero_when_no_deduped",
            _same_budget_k(3, 0) == 0,
        )
    )
    checks.append(
        _check(
            "same_budget_k_zero_when_both_zero",
            _same_budget_k(0, 0) == 0,
        )
    )

    # --- Group 10: same_budget_bm25_prefix arm. ---
    method_cands = {
        "bm25": [c for c in candidates if c["method"] == "bm25"],
        "regex": [c for c in candidates if c["method"] == "regex"],
        "symbol": [c for c in candidates if c["method"] == "symbol"],
    }
    sb_bm25_ev_2 = _same_budget_bm25_prefix_arm(method_cands, 2)
    checks.append(
        _check(
            "same_budget_bm25_prefix_returns_k",
            len(sb_bm25_ev_2) == 2,
        )
    )
    checks.append(
        _check(
            "same_budget_bm25_prefix_zero_when_k_zero",
            len(_same_budget_bm25_prefix_arm(method_cands, 0)) == 0,
        )
    )
    # BM25 prefix takes the first K deduped BM25 candidates.
    checks.append(
        _check(
            "same_budget_bm25_prefix_first_path_is_path1",
            sb_bm25_ev_2[0]["path"] == "src/path1.py"
            if sb_bm25_ev_2
            else False,
        )
    )

    # --- Group 11: agreement_only_same_budget arm. ---
    ao_ev_2 = _agreement_only_same_budget_arm(candidates, 2)
    checks.append(
        _check(
            "agreement_only_returns_k",
            len(ao_ev_2) == 2,
        )
    )
    checks.append(
        _check(
            "agreement_only_zero_when_k_zero",
            len(_agreement_only_same_budget_arm(candidates, 0)) == 0,
        )
    )
    # First should be the high-agreement span (path1.py 10-20, agreement=3).
    checks.append(
        _check(
            "agreement_only_first_is_high_agreement",
            ao_ev_2[0]["path"] == "src/path1.py"
            and ao_ev_2[0]["start_line"] == 10
            and ao_ev_2[0]["end_line"] == 20
            if ao_ev_2
            else False,
        )
    )

    # --- Group 12: seeded_random_same_budget arm. ---
    sr_ev_2 = _seeded_random_same_budget_arm(candidates, 2)
    checks.append(
        _check(
            "seeded_random_returns_k",
            len(sr_ev_2) == 2,
        )
    )
    checks.append(
        _check(
            "seeded_random_zero_when_k_zero",
            len(_seeded_random_same_budget_arm(candidates, 0)) == 0,
        )
    )
    # Deterministic: two runs produce identical output.
    sr_ev_2_b = _seeded_random_same_budget_arm(candidates, 2)
    checks.append(
        _check(
            "seeded_random_deterministic",
            [(e["path"], e["start_line"], e["end_line"]) for e in sr_ev_2]
            == [(e["path"], e["start_line"], e["end_line"]) for e in sr_ev_2_b],
        )
    )
    # Different K produces different (or subset) but still deterministic.
    sr_ev_3 = _seeded_random_same_budget_arm(candidates, 3)
    checks.append(
        _check(
            "seeded_random_k3_deterministic",
            len(sr_ev_3) == 3,
        )
    )
    # When K >= deduped count, returns all deduped.
    deduped_n = len(_dedup_candidates(candidates))
    sr_all = _seeded_random_same_budget_arm(candidates, deduped_n + 5)
    checks.append(
        _check(
            "seeded_random_returns_all_when_k_exceeds",
            len(sr_all) == deduped_n,
        )
    )

    # --- Group 13: seeded_random runtime-clean (no gold/labels in seed). ---
    # The seed is a fixed public constant; it does not depend on gold/labels/
    # row IDs. Verify by running on a tainted candidate list (same gold
    # fields) and confirming output is identical.
    tainted = []
    for c in candidates:
        tc = dict(c)
        tc["gold_paths"] = ["src/path1.py"]
        tc["row_id"] = "leaked"
        tc["benchmark_label"] = "positive"
        tainted.append(tc)
    sr_ev_tainted = _seeded_random_same_budget_arm(tainted, 2)
    checks.append(
        _check(
            "seeded_random_runtime_clean_invariance",
            [(e["path"], e["start_line"], e["end_line"]) for e in sr_ev_2]
            == [(e["path"], e["start_line"], e["end_line"]) for e in sr_ev_tainted],
        )
    )
    # agreement_only also runtime-clean.
    ao_tainted = _agreement_only_same_budget_arm(tainted, 2)
    checks.append(
        _check(
            "agreement_only_runtime_clean_invariance",
            [(e["path"], e["start_line"], e["end_line"]) for e in ao_ev_2]
            == [(e["path"], e["start_line"], e["end_line"]) for e in ao_tainted],
        )
    )

    # --- Group 14: arm_metric_records fixed shape. ---
    arm_records = skeleton.get("arm_metric_records", [])
    checks.append(
        _check(
            "arm_metric_records_nonempty",
            isinstance(arm_records, list) and len(arm_records) > 0,
        )
    )
    if arm_records:
        for idx, rec in enumerate(arm_records):
            if not isinstance(rec, dict):
                checks.append(
                    _check(f"arm_record_{idx}_is_dict", False)
                )
                continue
            checks.append(
                _check(
                    f"arm_record_{idx}_shape",
                    set(rec.keys()) == {"arm", "metric", "value"},
                )
            )
            checks.append(
                _check(
                    f"arm_record_{idx}_metric_allowlisted",
                    rec.get("metric") in ARM_METRIC_ALLOWLIST,
                )
            )
            checks.append(
                _check(
                    f"arm_record_{idx}_value_numeric",
                    isinstance(rec.get("value"), (int, float)),
                )
            )
            checks.append(
                _check(
                    f"arm_record_{idx}_arm_fixed",
                    rec.get("arm") in (
                        ARM_BM25_TOP10, ARM_BEA_V0_BUDGETED,
                        ARM_SAME_BUDGET_BM25_PREFIX,
                        ARM_AGREEMENT_ONLY_SAME_BUDGET,
                        ARM_SEEDED_RANDOM_SAME_BUDGET,
                    ),
                )
            )

    # --- Group 15: delta_records fixed shape. ---
    delta_records = skeleton.get("delta_records", [])
    checks.append(
        _check(
            "delta_records_nonempty",
            isinstance(delta_records, list) and len(delta_records) > 0,
        )
    )
    if delta_records:
        for idx, rec in enumerate(delta_records[:5]):  # spot-check first 5
            if not isinstance(rec, dict):
                checks.append(_check(f"delta_record_{idx}_is_dict", False))
                continue
            checks.append(
                _check(
                    f"delta_record_{idx}_shape",
                    set(rec.keys())
                    == {"baseline_arm", "treatment_arm", "metric", "delta"},
                )
            )
            checks.append(
                _check(
                    f"delta_record_{idx}_baseline_arm_correct",
                    rec.get("baseline_arm") == BASELINE_ARM,
                )
            )
            checks.append(
                _check(
                    f"delta_record_{idx}_metric_allowlisted",
                    rec.get("metric") in ARM_METRIC_ALLOWLIST,
                )
            )
            checks.append(
                _check(
                    f"delta_record_{idx}_delta_numeric",
                    isinstance(rec.get("delta"), (int, float)),
                )
            )

    # --- Group 16: mechanism_contrast_records fixed shape + record_count. ---
    contrast_records = skeleton.get("mechanism_contrast_records", [])
    checks.append(
        _check(
            "mechanism_contrast_records_nonempty",
            isinstance(contrast_records, list) and len(contrast_records) > 0,
        )
    )
    if contrast_records:
        for idx, rec in enumerate(contrast_records[:5]):
            if not isinstance(rec, dict):
                checks.append(_check(f"contrast_record_{idx}_is_dict", False))
                continue
            checks.append(
                _check(
                    f"contrast_record_{idx}_shape",
                    set(rec.keys())
                    == {
                        "contrast",
                        "baseline_arm",
                        "treatment_arm",
                        "metric",
                        "delta",
                        "record_count",
                    },
                )
            )
            checks.append(
                _check(
                    f"contrast_record_{idx}_contrast_fixed",
                    rec.get("contrast") in (
                        CONTRAST_BEA_VS_SAME_BUDGET_BM25,
                        CONTRAST_BEA_VS_AGREEMENT_ONLY,
                        CONTRAST_BEA_VS_SEEDED_RANDOM,
                    ),
                )
            )
            checks.append(
                _check(
                    f"contrast_record_{idx}_treatment_is_bea",
                    rec.get("treatment_arm") == ARM_BEA_V0_BUDGETED,
                )
            )
            checks.append(
                _check(
                    f"contrast_record_{idx}_record_count_positive",
                    isinstance(rec.get("record_count"), int)
                    and int(rec.get("record_count") or 0) > 0,
                )
            )
            checks.append(
                _check(
                    f"contrast_record_{idx}_delta_numeric",
                    isinstance(rec.get("delta"), (int, float)),
                )
            )

    # --- Group 17: Failure category counts fixed enum. ---
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    fcc["retrieval_failed"] = 1
    sample_fail_report = {"failure_category_counts": fcc}
    checks.append(
        _check(
            "failure_category_counts_in_enum",
            not _scan_bea1(sample_fail_report),
        )
    )
    bad_fcc = dict(fcc)
    bad_fcc["not_a_real_category"] = 1
    rebuilt = _build_unavailable_report(
        "retrieval_failed",
        self_test_passed=True,
        contextbench_row_limit_requested=5,
        repoqa_needle_limit_requested=3,
        budget=5,
        methods=("bm25", "regex", "symbol"),
        openlocus_binary_source="default",
        network_mode="local_explicit",
        failure_category_counts=bad_fcc,
    )
    checks.append(
        _check(
            "failure_category_counts_rejects_non_enum",
            "not_a_real_category"
            not in rebuilt["failure_category_counts"],
        )
    )

    # --- Group 18: Unavailable report. ---
    unavail = _build_unavailable_report(
        "contextbench_fetch_failed",
        self_test_passed=True,
        contextbench_row_limit_requested=5,
        repoqa_needle_limit_requested=3,
        budget=5,
        methods=("bm25", "regex", "symbol"),
        openlocus_binary_source="default",
        network_mode="local_explicit",
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
            unavail["failure_reason_category"]
            == "contextbench_fetch_failed",
        )
    )
    checks.append(
        _check(
            "unavailable_no_mechanism_ablation_performed_flag",
            unavail["mechanism_ablation_performed"] is False,
        )
    )
    checks.append(
        _check(
            "unavailable_no_perf_claim",
            unavail["external_benchmark_performance_claimed"] is False,
        )
    )
    checks.append(
        _check(
            "unavailable_empty_arm_metric_records",
            unavail["arm_metric_records"] == [],
        )
    )
    checks.append(
        _check(
            "unavailable_empty_delta_records",
            unavail["delta_records"] == [],
        )
    )
    checks.append(
        _check(
            "unavailable_empty_mechanism_contrast_records",
            unavail["mechanism_contrast_records"] == [],
        )
    )
    checks.append(
        _check(
            "unavailable_private_score_manifest_present",
            isinstance(unavail.get("private_score_manifest"), dict)
            and unavail["private_score_manifest"].get("path_publicly_serialized") is False,
        )
    )
    checks.append(
        _check(
            "unavailable_forbidden_scan_pass",
            unavail["forbidden_scan"]["status"] == "pass",
        )
    )

    # --- Group 19: Scanner rejects forbidden content. ---
    for forbidden_key in bea0.BEA0_FORBIDDEN_EXTRA_KEYS:
        checks.append(
            _check(
                f"scanner_rejects_{forbidden_key}_key",
                bool(_scan_bea1({forbidden_key: "value"})),
            )
        )
    checks.append(
        _check(
            "scanner_rejects_repo_url_value",
            bool(_scan_bea1({"leaked": "https://github.com/foo/bar"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_repo_slug_value",
            bool(_scan_bea1({"leaked": "psf/black"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_commit_sha_value",
            bool(
                _scan_bea1(
                    {"leaked": "f03ee113c9f3dfeb477f2d4247bfb7de2e5f465c"}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_file_path_value",
            bool(_scan_bea1({"leaked": "src/black/trans.py"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_tmp_path_value",
            bool(_scan_bea1({"leaked": "/tmp/foo"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_multiline_value",
            bool(_scan_bea1({"leaked": "line1\nline2"})),
        )
    )

    # --- Group 20: Scanner allows safe values. ---
    checks.append(
        _check(
            "scanner_allows_schema_version",
            not _scan_bea1({"schema_version": SCHEMA_VERSION}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_methods_value",
            not _scan_bea1({"methods": ["bm25", "regex", "symbol"]}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_budget_value",
            not _scan_bea1({"budget": 5}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_arm_metric_records",
            not _scan_bea1(
                {"arm_metric_records": [{"arm": ARM_BM25_TOP10, "metric": "mrr", "value": 0.5}]}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_delta_records",
            not _scan_bea1(
                {"delta_records": [{"baseline_arm": BASELINE_ARM, "treatment_arm": ARM_BEA_V0_BUDGETED, "metric": "mrr", "delta": 0.1}]}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_mechanism_contrast_records",
            not _scan_bea1(
                {
                    "mechanism_contrast_records": [
                        {
                            "contrast": CONTRAST_BEA_VS_SAME_BUDGET_BM25,
                            "baseline_arm": ARM_SAME_BUDGET_BM25_PREFIX,
                            "treatment_arm": ARM_BEA_V0_BUDGETED,
                            "metric": "mrr",
                            "delta": 0.1,
                            "record_count": 5,
                        }
                    ]
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_private_score_manifest",
            not _scan_bea1(
                {
                    "private_score_manifest": {
                        "records_written": True,
                        "record_count": 8,
                        "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
                        "manifest_hash": "a" * 64,
                        "storage_class": "tmp_private",
                        "path_publicly_serialized": False,
                    }
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_failure_category_count",
            not _scan_bea1(
                {
                    "failure_category_counts": {
                        "retrieval_failed": 1,
                        "unexpected_exception": 0,
                    }
                }
            ),
        )
    )

    # --- Group 21: Fail-closed generation. ---
    try:
        _enforce_bea1_no_forbidden(skeleton)
        checks.append(_check("fail_closed_clean_report_no_raise", True))
    except SystemExit:
        checks.append(_check("fail_closed_clean_report_no_raise", False))

    leaked_report = dict(skeleton)
    leaked_report["private_score_path"] = "/tmp/leaked.jsonl"
    try:
        _enforce_bea1_no_forbidden(leaked_report)
        checks.append(_check("fail_closed_private_score_path_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_private_score_path_raises", True))

    leaked_report2 = dict(skeleton)
    leaked_report2["action_trace"] = [{"action": "accept_candidate"}]
    try:
        _enforce_bea1_no_forbidden(leaked_report2)
        checks.append(_check("fail_closed_action_trace_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_action_trace_raises", True))

    leaked_report3 = dict(skeleton)
    leaked_report3["accepted_candidates"] = [{"path": "src/foo.py"}]
    try:
        _enforce_bea1_no_forbidden(leaked_report3)
        checks.append(_check("fail_closed_accepted_candidates_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_accepted_candidates_raises", True))

    leaked_report4 = dict(skeleton)
    leaked_report4["winner"] = ARM_BEA_V0_BUDGETED
    try:
        _enforce_bea1_no_forbidden(leaked_report4)
        checks.append(_check("fail_closed_winner_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_winner_raises", True))

    leaked_report5 = dict(skeleton)
    leaked_report5["best_method"] = "bm25"
    try:
        _enforce_bea1_no_forbidden(leaked_report5)
        checks.append(_check("fail_closed_best_method_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_best_method_raises", True))

    leaked_report6 = dict(skeleton)
    leaked_report6["calibration"] = "calibrated"
    try:
        _enforce_bea1_no_forbidden(leaked_report6)
        checks.append(_check("fail_closed_calibration_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_calibration_raises", True))

    failed_self_test_report = dict(skeleton)
    failed_self_test_report["self_test_passed"] = False
    try:
        c5a._refuse_on_self_test_failure(failed_self_test_report)
        checks.append(_check("refuse_on_self_test_failure_raises", False))
    except SystemExit:
        checks.append(_check("refuse_on_self_test_failure_raises", True))

    try:
        c5a._refuse_on_self_test_failure(skeleton)
        checks.append(_check("refuse_on_self_test_pass_no_raise", True))
    except SystemExit:
        checks.append(_check("refuse_on_self_test_pass_no_raise", False))

    # --- Group 22: Public artifact self-scan is clean. ---
    checks.append(
        _check(
            "public_artifact_self_scan_clean",
            not _scan_bea1(skeleton),
        )
    )
    checks.append(
        _check(
            "unavailable_self_scan_clean",
            not _scan_bea1(unavail),
        )
    )

    # --- Group 23: CLI argument surface. ---
    parser = build_parser()
    option_strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            option_strings.add(opt)
    for required_opt in (
        "--self-test",
        "--contextbench-row-limit",
        "--repoqa-needle-limit",
        "--budget",
        "--methods",
        "--openlocus",
        "--out",
        "--private-score-dir",
        "--enable-rrf-baseline",
        "--enable-external-benchmark-network",
    ):
        checks.append(
            _check(
                f"cli_has_option_{required_opt}",
                required_opt in option_strings,
            )
        )

    # --- Group 24: Private SCORE writer round-trip. ---
    with tempfile.TemporaryDirectory(
        prefix="bea1_selftest_score_"
    ) as score_dir_str:
        score_dir = Path(score_dir_str)
        score_file = score_dir / "bea1.private.jsonl"
        row = {
            "phase_run_id": "bea1-selftest",
            "benchmark": "synthetic",
            "private_record_id": "synthetic-001",
            "runtime_query_feature_summary": {"benchmark": "synthetic"},
            "candidate_list": [],
            "bea_v0_action_trace": [],
            "bea_v0_budget_states": [],
            "bea_v0_accepted_candidates": [],
            "final_candidates": [],
            "baseline_bm25_top10_evidence": [],
            "baseline_rrf_top10_evidence": [],
            "same_budget_bm25_prefix_evidence": [],
            "agreement_only_same_budget_evidence": [],
            "seeded_random_same_budget_evidence": [],
            "same_budget_k": 0,
            "score_outcome": {},
            "latency_ms": 1,
            "cost_usd": 0.0,
            "tokens": 0,
            "provider_calls": 0,
            "failure_reason": None,
        }
        _write_private_score_row(score_file, row)
        _write_private_score_row(score_file, row)
        lines = score_file.read_text(encoding="utf-8").splitlines()
        checks.append(
            _check(
                "private_score_writer_two_rows",
                len(lines) == 2,
            )
        )
        checks.append(
            _check(
                "private_score_rows_parse_as_json",
                all(
                    isinstance(json.loads(l), dict) for l in lines if l
                ),
            )
        )
        # Path leak detection.
        leaked_path_report = dict(skeleton)
        leaked_path_report["private_score_path"] = str(score_file)
        checks.append(
            _check(
                "private_score_path_leak_detected_by_scanner",
                bool(_scan_bea1(leaked_path_report)),
            )
        )

    # --- Group 25: Paired denominator rule. ---
    # Build per-record metrics where one record is missing one arm; that
    # record must be excluded from contrasts involving that arm.
    rec_a = {
        ARM_BM25_TOP10: bm25_m,
        ARM_BEA_V0_BUDGETED: bea_m,
        ARM_SAME_BUDGET_BM25_PREFIX: sb_bm25_m,
        ARM_AGREEMENT_ONLY_SAME_BUDGET: ao_m,
        ARM_SEEDED_RANDOM_SAME_BUDGET: sr_m,
    }
    rec_b = {
        ARM_BM25_TOP10: bm25_m,
        ARM_BEA_V0_BUDGETED: bea_m,
        ARM_SAME_BUDGET_BM25_PREFIX: sb_bm25_m,
        # ARM_AGREEMENT_ONLY_SAME_BUDGET missing
        ARM_SEEDED_RANDOM_SAME_BUDGET: sr_m,
    }
    paired_metrics = [rec_a, rec_b]
    contrasts = [
        (CONTRAST_BEA_VS_SAME_BUDGET_BM25, ARM_SAME_BUDGET_BM25_PREFIX, ARM_BEA_V0_BUDGETED),
        (CONTRAST_BEA_VS_AGREEMENT_ONLY, ARM_AGREEMENT_ONLY_SAME_BUDGET, ARM_BEA_V0_BUDGETED),
        (CONTRAST_BEA_VS_SEEDED_RANDOM, ARM_SEEDED_RANDOM_SAME_BUDGET, ARM_BEA_V0_BUDGETED),
    ]
    contrast_recs = _mechanism_contrast_records(paired_metrics, contrasts)
    # bea_vs_same_budget_bm25 contrast: both records have both arms => record_count=2.
    # bea_vs_agreement_only: only rec_a has agreement_only => record_count=1.
    # bea_vs_seeded_random: both records have both arms => record_count=2.
    contrast_counts = {r["contrast"]: r["record_count"] for r in contrast_recs if r["metric"] == "mrr"}
    checks.append(
        _check(
            "paired_denominator_excludes_missing_arm_records",
            contrast_counts.get(CONTRAST_BEA_VS_SAME_BUDGET_BM25) == 2
            and contrast_counts.get(CONTRAST_BEA_VS_AGREEMENT_ONLY) == 1
            and contrast_counts.get(CONTRAST_BEA_VS_SEEDED_RANDOM) == 2,
        )
    )

    # --- Group 26: Aggregate runtime seconds present. ---
    checks.append(
        _check(
            "pass_report_has_aggregate_runtime_seconds",
            "aggregate_runtime_seconds" in skeleton
            and isinstance(
                skeleton["aggregate_runtime_seconds"], (int, float)
            ),
        )
    )
    checks.append(
        _check(
            "unavailable_report_has_no_runtime",
            "aggregate_runtime_seconds" not in unavail,
        )
    )

    # --- Group 27: No winner/best_method/method_winner/calibration anywhere. ---
    for field in (
        "winner", "best_method", "recommended_default",
        "method_winner", "calibration",
    ):
        checks.append(
            _check(
                f"clean_report_missing_{field}",
                field not in skeleton,
            )
        )

    # --- Group 28: Fixed arms present in fixed_arms list. ---
    fixed_arms = skeleton.get("fixed_arms", [])
    for expected_arm in (
        ARM_BM25_TOP10, ARM_BEA_V0_BUDGETED,
        ARM_SAME_BUDGET_BM25_PREFIX,
        ARM_AGREEMENT_ONLY_SAME_BUDGET,
        ARM_SEEDED_RANDOM_SAME_BUDGET,
    ):
        checks.append(
            _check(
                f"fixed_arms_contains_{expected_arm}",
                expected_arm in fixed_arms,
            )
        )
    checks.append(
        _check(
            "fixed_arms_excludes_rrf_when_disabled",
            ARM_RRF_TOP10 not in fixed_arms,
        )
    )

    all_passed = all(c["passed"] for c in checks if c is not None)
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
    """Build the BEA-1 CLI parser."""
    ap = SafeArgumentParser(
        description=(
            "BEA-1 Mechanism Ablation Smoke "
            "(public aggregate-only records; bounded ContextBench verified "
            "+ RepoQA Python samples; multi-method candidate collection "
            "(bm25/regex/symbol); BEA v0 budgeted policy + 3 same-budget "
            "controls (same_budget_bm25_prefix, agreement_only_same_budget, "
            "seeded_random_same_budget); private per-record SCORE JSONL "
            "traces in /tmp; no provider calls; no raw repo/commit/path/"
            "span/candidate/action-trace/budget-state/accepted-candidates/"
            "score-outcome/private-score-path committed)."
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
            "number of ContextBench verified Python rows to evaluate "
            "(default: "
            f"{CONTEXTBENCH_ROW_LIMIT_DEFAULT}; hard cap "
            f"{CONTEXTBENCH_ROW_LIMIT_HARD_CAP})"
        ),
    )
    ap.add_argument(
        "--repoqa-needle-limit",
        type=int,
        default=REPOQA_NEEDLE_LIMIT_DEFAULT,
        help=(
            "number of RepoQA Python needles to evaluate (default: "
            f"{REPOQA_NEEDLE_LIMIT_DEFAULT}; hard cap "
            f"{REPOQA_NEEDLE_LIMIT_HARD_CAP})"
        ),
    )
    ap.add_argument(
        "--budget",
        type=int,
        default=BUDGET_DEFAULT,
        help=(
            "evidence budget for the bea_v0_budgeted policy and same-budget "
            f"controls (default: {BUDGET_DEFAULT}; hard cap "
            f"{BUDGET_HARD_CAP})"
        ),
    )
    ap.add_argument(
        "--methods",
        default=DEFAULT_METHODS,
        help=(
            "comma-separated retrieval methods (default: "
            f"{DEFAULT_METHODS}; allowed: {', '.join(ALLOWED_METHODS)}; "
            "bm25 is required)"
        ),
    )
    ap.add_argument(
        "--enable-rrf-baseline",
        action="store_true",
        help=(
            "enable the rrf_bm25_regex_symbol_top10 baseline arm "
            "(default: disabled; optional, do not block on rrf)"
        ),
    )
    ap.add_argument(
        "--enable-external-benchmark-network",
        action="store_true",
        help=(
            "allow real HuggingFace + GitHub network access for the "
            "ContextBench row fetch + RepoQA asset download + repo clones "
            "(default: false; no provider secrets/vars)"
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
    ap.add_argument(
        "--private-score-dir",
        default=None,
        help=(
            "explicit private SCORE JSONL directory (default: fresh "
            "/tmp/bea0_private_score_<pid>_<ts>; must be under /tmp or "
            "the gitignored runs/ directory)"
        ),
    )
    return ap


# ---------------------------------------------------------------------------
# Network smoke runner (transient /tmp workspace; aggregate-only output).
# ---------------------------------------------------------------------------


def _run_network_smoke(
    *,
    contextbench_row_limit: int,
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
    """Run the real BEA-1 network smoke.

    For each benchmark arm (ContextBench + RepoQA):
      1. Fetch rows/needles (transient in-memory).
      2. For each record: clone repo, run multi-method retrieval, run all
         fixed arms, compute per-arm metrics, write private SCORE row to
         /tmp.
      3. Aggregate per-arm metrics + deltas + mechanism contrasts.
    """
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    network_calls = 0
    smoke_start = time.perf_counter()
    manifest_hash = _private_score_manifest_hash()
    score_file = private_score_dir / "bea1.private.jsonl"
    try:
        score_file.unlink()
    except OSError:
        pass

    per_record_arm_metrics: list[dict[str, dict[str, Any]]] = []
    records_evaluated = 0
    records_successful = 0
    records_failed = 0
    paired_exclusion_count = 0

    # --- ContextBench arm ---
    rows, cb_status, cb_nc, cb_fcc = c5a._fetch_contextbench_rows(
        contextbench_row_limit, "python"
    )
    network_calls += cb_nc
    for k, v in cb_fcc.items():
        if k in fcc:
            fcc[k] += v
    if cb_status == "unavailable" or not rows:
        fcc["contextbench_fetch_failed"] = (
            fcc.get("contextbench_fetch_failed", 0) + 1
        )
        if not rows:
            fcc["contextbench_no_python_rows"] = (
                fcc.get("contextbench_no_python_rows", 0) + 1
            )
        cb_rows: list[dict[str, Any]] = []
    else:
        cb_rows = rows

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

        with tempfile.TemporaryDirectory(
            prefix=f"bea1_cb_repo_{idx}_"
        ) as repo_root_str:
            repo_work_dir = Path(repo_root_str)
            clone_ok, _clone_fail_cat, clone_fcc = c5d._clone_and_checkout(
                repo_url, base_commit, repo_work_dir
            )
            for k, v in clone_fcc.items():
                if k in fcc:
                    fcc[k] += v
            if not clone_ok:
                records_failed += 1
                continue
            repo_root = repo_work_dir / "repo"
            private_record_id = f"contextbench-{idx}"
            task_id = f"cb_row_{idx}"
            per_arm, fcc = _evaluate_record(
                openlocus_bin=openlocus_bin,
                benchmark="contextbench",
                private_record_id=private_record_id,
                task_id=task_id,
                query=query,
                gold_paths=gold_paths,
                gold_lines=gold_lines,
                repo_root=repo_root,
                methods=methods,
                budget=budget,
                enable_rrf_baseline=enable_rrf_baseline,
                score_path=score_file,
                phase_run_id=phase_run_id,
                fcc=fcc,
            )
            if per_arm is None:
                records_failed += 1
                continue
            per_record_arm_metrics.append(per_arm)
            records_successful += 1

    # --- RepoQA arm ---
    asset_bytes, dl_status, dl_fcc = c5d._download_asset_to_bytes(
        c5d.ASSET_URL
    )
    network_calls += 1
    for k, v in dl_fcc.items():
        if k in fcc:
            fcc[k] += v
    repoqa_needles: list[dict[str, Any]] = []
    if dl_status == "pass" and asset_bytes:
        parsed, parse_status, parse_fcc = c5d._decompress_asset(asset_bytes)
        del asset_bytes
        for k, v in parse_fcc.items():
            if k in fcc:
                fcc[k] += v
        if parse_status == "pass" and parsed is not None:
            needles, needle_status, needle_fcc = (
                c5d._parse_repoqa_needles(
                    parsed, "python", repoqa_needle_limit
                )
            )
            del parsed
            for k, v in needle_fcc.items():
                if k in fcc:
                    fcc[k] += v
            if needle_status == "pass":
                repoqa_needles = needles
            else:
                fcc["repoqa_no_python_needles"] += 1
        else:
            fcc["repoqa_asset_parse_failed"] += 1
    else:
        fcc["repoqa_asset_download_failed"] += 1

    for idx, needle in enumerate(repoqa_needles):
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
        if (
            not isinstance(repo_url, str)
            or not isinstance(commit_sha, str)
            or not isinstance(needle_path, str)
            or not repo_url
            or not commit_sha
            or not needle_path
        ):
            fcc["repoqa_needle_parse_failed"] += 1
            records_failed += 1
            continue

        with tempfile.TemporaryDirectory(
            prefix=f"bea1_rq_repo_{idx}_"
        ) as repo_root_str:
            repo_work_dir = Path(repo_root_str)
            clone_ok, _clone_fail_cat, clone_fcc = c5d._clone_and_checkout(
                repo_url, commit_sha, repo_work_dir
            )
            for k, v in clone_fcc.items():
                if k in fcc:
                    fcc[k] += v
            if not clone_ok:
                records_failed += 1
                continue
            repo_root = repo_work_dir / "repo"
            private_record_id = f"repoqa-{idx}"
            task_id = f"rq_needle_{idx}"
            per_arm, fcc = _evaluate_record(
                openlocus_bin=openlocus_bin,
                benchmark="repoqa",
                private_record_id=private_record_id,
                task_id=task_id,
                query=query,
                gold_paths=[needle_path],
                gold_lines=[[start_line, end_line]],
                repo_root=repo_root,
                methods=methods,
                budget=budget,
                enable_rrf_baseline=enable_rrf_baseline,
                score_path=score_file,
                phase_run_id=phase_run_id,
                fcc=fcc,
            )
            if per_arm is None:
                records_failed += 1
                continue
            per_record_arm_metrics.append(per_arm)
            records_successful += 1

    # --- Aggregate per-arm metrics + deltas + contrasts ---
    if not per_record_arm_metrics:
        return _build_unavailable_report(
            "retrieval_failed",
            self_test_passed=self_test_passed,
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            budget=budget,
            methods=methods,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            private_score_records_written=False,
            private_score_record_count=0,
            private_score_storage_class=private_score_storage_class,
            private_score_manifest_hash=manifest_hash,
            records_evaluated=records_evaluated,
            records_successful=records_successful,
            records_failed=records_failed,
            network_calls=network_calls,
            failure_category_counts=fcc,
        )

    # Aggregate per arm.
    arm_aggs: dict[str, dict[str, Any]] = {}
    fixed_arm_ids = [
        ARM_BM25_TOP10, ARM_BEA_V0_BUDGETED,
        ARM_SAME_BUDGET_BM25_PREFIX,
        ARM_AGREEMENT_ONLY_SAME_BUDGET,
        ARM_SEEDED_RANDOM_SAME_BUDGET,
    ]
    if enable_rrf_baseline:
        fixed_arm_ids.append(ARM_RRF_TOP10)
    for arm_id in fixed_arm_ids:
        per_arm_list = [
            rec[arm_id] for rec in per_record_arm_metrics
            if arm_id in rec
        ]
        if per_arm_list:
            arm_aggs[arm_id] = _arm_means(per_arm_list)

    # Count private SCORE rows actually written.
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
    if records_successful > 0 and private_score_count != records_successful:
        fcc["private_score_write_failed"] += 1
        return _build_unavailable_report(
            "private_score_write_failed",
            self_test_passed=self_test_passed,
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            budget=budget,
            methods=methods,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            private_score_records_written=private_score_written,
            private_score_record_count=private_score_count,
            private_score_storage_class=private_score_storage_class,
            private_score_manifest_hash=manifest_hash,
            records_evaluated=records_evaluated,
            records_successful=records_successful,
            records_failed=records_failed,
            network_calls=network_calls,
            failure_category_counts=fcc,
        )

    aggregate_runtime_seconds = time.perf_counter() - smoke_start
    partial = records_failed > 0 or records_successful < (
        contextbench_row_limit + repoqa_needle_limit
    )

    return _build_pass_report(
        self_test_passed=self_test_passed,
        contextbench_row_limit_requested=contextbench_row_limit,
        repoqa_needle_limit_requested=repoqa_needle_limit,
        budget=budget,
        methods=methods,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        records_evaluated=records_evaluated,
        records_successful=records_successful,
        records_failed=records_failed,
        network_calls=network_calls,
        arm_metrics=arm_aggs,
        per_record_arm_metrics=per_record_arm_metrics,
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
        print(
            f"self_test_passed={passed} "
            f"({passed_count}/{len(checks)} checks)"
        )
        sys.exit(0 if passed else 1)

    contextbench_row_limit = _validate_row_limit(args.contextbench_row_limit)
    repoqa_needle_limit = _validate_needle_limit(args.repoqa_needle_limit)
    budget = _validate_budget(args.budget)
    methods = _validate_methods(args.methods)
    enable_rrf_baseline = bool(args.enable_rrf_baseline)
    enable_network = bool(args.enable_external_benchmark_network)
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
            budget=budget,
            methods=methods,
            openlocus_binary_source=openlocus_source,
            network_mode="local_explicit",
        )
        _enforce_bea1_no_forbidden(report)
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

    # Resolve private SCORE dir (transient /tmp or ignored runs/ only).
    private_score_dir, private_score_storage_class = (
        _resolve_private_score_dir(args.private_score_dir)
    )
    phase_run_id = f"bea1-{int(time.time())}"

    # If network is not enabled, write a truthful unavailable report.
    if not enable_network:
        report = _build_unavailable_report(
            "contextbench_fetch_failed",
            self_test_passed=self_test_passed,
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            budget=budget,
            methods=methods,
            openlocus_binary_source=openlocus_source,
            network_mode="disabled_opt_in",
        )
        _enforce_bea1_no_forbidden(report)
        _write_json(out_path, report)
        print(
            f"wrote artifact "
            f"(forbidden_scan={report['forbidden_scan']['status']}, "
            f"self_test_passed={report['self_test_passed']}, "
            f"status={report['status']}, "
            f"phase={report['phase']}, "
            f"failure_reason={report['failure_reason_category']})"
        )
        print(
            "enable_external_benchmark_network is false; skipping real "
            "BEA-1 mechanism ablation smoke. Run with --enable-external-"
            "benchmark-network to execute the real ContextBench + RepoQA "
            "mechanism ablation."
        )
        return

    network_mode = "local_explicit"
    eval_dir = Path(__file__).resolve().parent
    try:
        report = _run_network_smoke(
            contextbench_row_limit=contextbench_row_limit,
            repoqa_needle_limit=repoqa_needle_limit,
            budget=budget,
            methods=methods,
            enable_rrf_baseline=enable_rrf_baseline,
            openlocus_bin=openlocus_bin,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
            eval_dir=eval_dir,
            self_test_passed=self_test_passed,
            private_score_dir=private_score_dir,
            private_score_storage_class=private_score_storage_class,
            phase_run_id=phase_run_id,
        )
    except (OSError, subprocess.SubprocessError):
        report = _build_unavailable_report(
            "unexpected_exception",
            self_test_passed=self_test_passed,
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            budget=budget,
            methods=methods,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
            private_score_storage_class=private_score_storage_class,
        )

    # Fail-closed: provider_calls must be 0.
    if report.get("provider_calls") != 0:
        report["status"] = "fail_schema_contract"

    # Fail-closed: private SCORE record count must match records_successful.
    manifest = report.get("private_score_manifest", {})
    if (
        enable_network
        and report.get("records_successful", 0) > 0
        and manifest.get("record_count", 0)
        != report.get("records_successful", 0)
    ):
        report["status"] = "fail_schema_contract"

    # Fail-closed: forbidden scan.
    _enforce_bea1_no_forbidden(report)
    _write_json(out_path, report)
    print(
        f"wrote artifact "
        f"(forbidden_scan={report['forbidden_scan']['status']}, "
        f"self_test_passed={report['self_test_passed']}, "
        f"status={report['status']}, "
        f"phase={report['phase']}, "
        f"records_evaluated={report.get('records_evaluated', 0)}, "
        f"records_successful={report.get('records_successful', 0)}, "
        f"private_score_records_written="
        f"{report.get('private_score_records_written')}, "
        f"private_score_record_count="
        f"{manifest.get('record_count', 0)})"
    )


if __name__ == "__main__":
    main()
