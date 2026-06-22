#!/usr/bin/env python3
"""BEA-2 Policy v0.2 Diversity/Risk Mechanism Smoke (Public Records-Only).

This module implements the **BEA-2 policy v0.2 diversity/risk mechanism smoke**
over fresh heldout ContextBench verified Python rows (offset 40, limit 20)
and RepoQA Python needles (offset 20, limit 10). It is a real algorithmic
policy change experiment: BEA v0.2 adds a deterministic gold-free
diversity/risk-aware acquisition policy that is structurally different from
BEA v0 and the BEA-1 same-budget controls, and compares it against v0,
same-budget BM25 prefix, agreement-only, and seeded random controls on the
same fresh heldout records under a paired denominator rule. Private
per-record SCORE JSONL (one row per benchmark record × policy arm) is
written ONLY under ``/tmp``; the public artifact is records-shaped
aggregate only.

BEA-2 is explicitly **not** a benchmark result, **not** a leaderboard entry,
**not** a performance claim, **not** a method-winner claim, **not** a
calibration claim, **not** a promotion, **not** a default/policy change, and
**not** a runtime/retriever/pack/backend/EvidenceCore semantic change. It
does NOT emit ``winner``, ``best_method``, ``recommended_default``,
``method_winner``, ``calibration``, or anything implying a policy/default
decision.

Claim boundary (binding):

* Claim level: ``bea_v02_policy_smoke_only``.
* Status: ``bea2_policy_v02_pass`` | ``partial`` |
  ``unavailable_with_reason`` | ``fail_forbidden_scan`` |
  ``fail_schema_contract``.
* Mode: ``bounded_heldout_retrieval_policy_v02_smoke``; phase ``BEA-2``.

Privacy / license boundary (binding):

* Private per-record SCORE JSONL is written ONLY under ``/tmp`` (or an
  explicitly ignored private path). The private SCORE path is NEVER
  serialized in the public artifact, docs, or CI artifacts.
* The public artifact records ONLY aggregate SCORE manifest fields
  (``records_written``, ``record_count``, ``schema_version``,
  ``manifest_hash``, ``storage_class``, ``path_publicly_serialized=false``)
  under the ``private_score_manifest`` block.
* ContextBench + RepoQA dataset licenses are unknown
  (``unknown_dataset_license``); row-level redistribution is disabled
  and derived row-level publication is disabled. Aggregate metrics
  publication is allowed as aggregate-only smoke.

Network / CI policy (binding):

* Default no-network self-test passes without HuggingFace/GitHub.
* Real acquisition requires public network access to HF datasets-server
  and GitHub repos. CI is a separate explicit ``workflow_dispatch`` job
  with ``enable_external_benchmark_network=true``. It must NOT run on
  PR/push by default, must use no provider secrets/vars, no provider model
  env, and must upload only the aggregate report. The private SCORE JSONL
  is NEVER uploaded.

Run::

    python3 -m py_compile eval/bea2_policy_v02.py
    python3 eval/bea2_policy_v02.py --self-test
    python3 eval/bea2_policy_v02.py \\
        --enable-external-benchmark-network \\
        --contextbench-row-offset 40 --contextbench-row-limit 20 \\
        --repoqa-needle-offset 20 --repoqa-needle-limit 10 \\
        --budget 5 --methods bm25,regex,symbol \\
        --out artifacts/bea2_policy_v02/bea2_policy_v02_report.json
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

# Reuse BEA-0 + BEA-1 helpers (candidate normalization, BEA v0 policy,
# same-budget controls, scanner primitives, private SCORE writer, arm
# metrics). The ``eval`` directory has no ``__init__.py`` (it is a flat
# script directory), so we add this file's parent to ``sys.path`` and
# import directly. We also reuse C5-A/C5-D helpers via transitive imports.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402
import c5d_repoqa_bm25_retrieval_smoke as c5d  # noqa: E402
import bea0_budgeted_evidence_acquisition as bea0  # noqa: E402
import bea1_mechanism_ablation as bea1  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants (BEA-2 owned)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "bea2_policy_v02.v1"
GENERATED_BY = "eval/bea2_policy_v02.py"
CLAIM_LEVEL = "bea_v02_policy_smoke_only"
MODE = "bounded_heldout_retrieval_policy_v02_smoke"
PHASE = "BEA-2"

DEFAULT_OUT = Path(
    "artifacts/bea2_policy_v02/"
    "bea2_policy_v02_report.json"
)

# Private SCORE JSONL schema version for BEA-2. Bumped because BEA-2 adds
# the v0.2 priority_components / candidate_features / selected_decisions
# private fields.
PRIVATE_SCORE_SCHEMA_VERSION = "bea2_private_score.v1"

# Fresh heldout slice defaults per plan.
# ContextBench verified Python rows offset 40, limit 20 (rows 41-60).
# RepoQA Python needles offset 20, limit 10 (needles 21-30).
CONTEXTBENCH_ROW_OFFSET_DEFAULT = 40
CONTEXTBENCH_ROW_LIMIT_DEFAULT = 20
CONTEXTBENCH_ROW_LIMIT_HARD_CAP = 20
REPOQA_NEEDLE_OFFSET_DEFAULT = 20
REPOQA_NEEDLE_LIMIT_DEFAULT = 10
REPOQA_NEEDLE_LIMIT_HARD_CAP = 10

# Default evidence budget. Hard cap 20.
BUDGET_DEFAULT = 5
BUDGET_HARD_CAP = 20

# Methods supported by the BEA-2 multi-method candidate collector.
ALLOWED_METHODS: tuple[str, ...] = ("bm25", "regex", "symbol")
DEFAULT_METHODS = "bm25,regex,symbol"

# Fixed policy arm IDs only; no dynamic arm names.
ARM_BM25_PREFIX_SAME_BUDGET = "bm25_prefix_same_budget"
ARM_AGREEMENT_ONLY_SAME_BUDGET = "agreement_only_same_budget"
ARM_BEA_V0 = "bea_v0"
ARM_BEA_V0_2_DIVERSITY_RISK = "bea_v0_2_diversity_risk"
ARM_SEEDED_RANDOM_SAME_BUDGET = "seeded_random_same_budget"
ARM_RRF_SAME_BUDGET = "rrf_same_budget"  # optional, only when rrf enabled

# Fixed baseline arm for delta_records.
BASELINE_ARM = ARM_BEA_V0

# Fixed contrasts: v0.2 vs v0, v0.2 vs same-budget BM25 prefix, v0.2 vs
# agreement-only, v0.2 vs seeded random.
CONTRAST_V02_VS_V0 = "v02_vs_v0"
CONTRAST_V02_VS_SAME_BUDGET_BM25 = "v02_vs_same_budget_bm25"
CONTRAST_V02_VS_AGREEMENT_ONLY = "v02_vs_agreement_only"
CONTRAST_V02_VS_SEEDED_RANDOM = "v02_vs_seeded_random"

# Public deterministic seed for the seeded_random_same_budget arm.
SEEDED_RANDOM_SEED = 20240621

# Primary metrics used for win/tie/loss records.
PRIMARY_METRICS: tuple[str, ...] = (
    "file_recall@10",
    "mrr",
    "span_f0.5@10",
    "success_rate",
)

# Arm metric allowlist.
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
# Safe booleans true (only when actually true).
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "bea_v02_policy_executed": False,
    "bea_v0_acquisition_performed": False,
    "private_score_records_written": False,
    "external_benchmark_rows_read": False,
    "openlocus_retrieval_executed": False,
    "score_py_metrics_computed": False,
    "heldout_fresh_slice_read": False,
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
}

# ---------------------------------------------------------------------------
# No-claim / no-runtime-change flags (all MUST be false).
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
# Fixed failure-category enum.
# ---------------------------------------------------------------------------

FAILURE_CATEGORIES: tuple[str, ...] = (
    "contextbench_fetch_failed",
    "contextbench_no_python_rows",
    "contextbench_gold_parse_failed",
    "repoqa_asset_download_failed",
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
# Public artifact scanner (BEA-2 owned, strict, fail-closed).
#
# BEA-2 reuses the BEA-1 forbidden scanner primitives (which extend
# BEA-0/C5-A/C5-D) for raw key/value leak detection. BEA-2 ADDS
# BEA-2-specific forbidden keys (``action_order``, ``priority_components``,
# ``selected_decisions``, ``budget_trace``, ``stop_reason``,
# ``candidate_features``) that must NEVER appear as dict keys anywhere in a
# BEA-2 public artifact JSON.
# ---------------------------------------------------------------------------

# BEA-2-specific forbidden keys (in addition to bea1.BEA1_FORBIDDEN_EXTRA_KEYS).
BEA2_FORBIDDEN_EXTRA_KEYS: frozenset[str] = frozenset(
    {
        # BEA-2 private per-record SCORE fields
        "action_order",
        "priority_components",
        "priority_score",
        "selected_decisions",
        "budget_trace",
        "stop_reason",
        "candidate_features",
        # Repeated from BEA1 for self-documentation
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
    }
)


def _is_bea2_schema_key_container(path: str) -> bool:
    """Check if the parent of the current key is a BEA-2 schema-key container."""
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in (
        bea1.BEA1_SAFE_VALUE_PATH_LAST_KEYS
        | {"failure_category_counts", "benchmark_arm_metric_records",
           "delta_records", "mechanism_contrast_records",
           "win_tie_loss_records", "private_score_manifest",
           "framing", "arm_metric_records"}
    )


def _scan_bea2_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    """Scan for BEA-2-specific forbidden keys."""
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                is_schema_container = _is_bea2_schema_key_container(sub_path)
                if (key_str in BEA2_FORBIDDEN_EXTRA_KEYS
                    and not is_schema_container):
                    violations.append({
                        "category": "forbidden_bea2_extra_key",
                        "path": sub_path,
                    })
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


def _scan_bea2(obj: Any) -> list[dict[str, Any]]:
    """Combined BEA-2 scanner: BEA-1 primitives + BEA-2 forbidden keys."""
    violations = bea1._scan_bea1(obj)
    violations.extend(_scan_bea2_forbidden_keys(obj))
    return violations


def _bea2_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    """Run the BEA-2 forbidden scanner and return a sanitized summary."""
    violations = _scan_bea2(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_bea2_no_forbidden(obj: Any) -> None:
    """Fail-closed guard: raise SystemExit if any forbidden content leaks."""
    scan = _bea2_forbidden_scan_summary(obj)
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
# Private SCORE JSONL writer (transient /tmp only; never committed).
# ---------------------------------------------------------------------------


def _resolve_private_score_dir(
    explicit: str | None,
) -> tuple[Path, str]:
    return bea0._resolve_private_score_dir(explicit)


def _private_score_manifest_hash() -> str:
    """Compute a stable sha256 of the private SCORE manifest schema."""
    manifest_schema = {
        "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
        "fields": [
            "phase_run_id",
            "benchmark",
            "private_record_id",
            "policy_arm",
            "runtime_query_feature_summary",
            "candidate_features",
            "priority_components",
            "selected_decisions",
            "action_order",
            "budget_trace",
            "stop_reason",
            "score_outcome",
            "latency_ms",
            "cost_usd",
            "tokens",
            "provider_calls",
            "failure_reason",
        ],
        "candidate_feature_fields": [
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
            "dir",
            "is_new_file",
            "is_new_dir",
            "path_token_overlap",
            "risk_bucket",
            "priority_score",
            "priority_components",
            "selected",
        ],
    }
    canonical = json.dumps(manifest_schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_private_score_row(
    score_path: Path,
    row: dict[str, Any],
) -> None:
    bea0._write_private_score_row(score_path, row)


# ---------------------------------------------------------------------------
# BEA v0.2 diversity/risk policy (deterministic, runtime-clean)
# ---------------------------------------------------------------------------
#
# v0.2 differs from v0 (BEA-0) and from agreement-only (BEA-1) by computing a
# per-candidate priority score that combines:
#   - cross-method support / agreement, weighted by method mix;
#   - normalized bm25 score;
#   - diversity bonus for new file/dir;
#   - query-token/path-token overlap scalar;
#   - risk penalty for test/docs/generated/vendor/lock/config path buckets;
#   - duplication penalty for same-file/overlapping span already selected.
#
# It then greedily selects candidates by descending priority under the budget,
# recompute priorities after each selection (so diversity/duplication update).
# This is structurally different from v0 (which uses agreement desc / min_rank
# asc / max_norm_score desc with accept/skip/rerank/stop actions) and from
# agreement-only (which uses the same sort but no sequential rules).

# Risk path buckets. Path components matching these trigger a risk penalty.
# Cheap path-kind metadata only; never reads file contents.
_RISK_PATH_PATTERNS = re.compile(
    r"(?:^|/)(?:tests?|test|docs?|doc|documentation|generated|vendor|"
    r"node_modules|__pycache__|\.git|dist|build|target|out|"
    r".*\.lock|.*\.config\.|.*\.toml|.*\.yaml|.*\.yml|"
    r".*\.json|.*\.md|.*\.txt|.*\.cfg|.*\.ini)"
    r"(?:/|$)",
    re.IGNORECASE,
)


def _path_dir(path: str) -> str:
    """Return the directory portion of a path (cheap path-kind metadata)."""
    if not isinstance(path, str) or not path:
        return ""
    if "/" in path:
        return path.rsplit("/", 1)[0]
    return ""


def _is_new_file(path: str, accepted_paths: set[str]) -> bool:
    return path not in accepted_paths


def _is_new_dir(dir_part: str, accepted_dirs: set[str]) -> bool:
    if not dir_part:
        return False
    return dir_part not in accepted_dirs


def _query_tokens(query: str) -> set[str]:
    """Tokenize a query into lowercased alphanumeric tokens (runtime-clean).

    Used ONLY for query-token/path-token overlap scalar; never persisted in
    public artifact.
    """
    if not isinstance(query, str) or not query:
        return set()
    return set(re.findall(r"[a-z0-9_]+", query.lower()))


def _path_tokens(path: str) -> set[str]:
    """Tokenize a path into lowercased alphanumeric tokens (runtime-clean)."""
    if not isinstance(path, str) or not path:
        return set()
    # Split on path separators, dots, underscores, hyphens.
    tokens = re.findall(r"[a-z0-9]+", path.lower())
    return set(tokens) - {"py", "rs", "ts", "js", "go", "java", "c", "cpp",
                          "h", "hpp", "md", "txt", "json", "toml", "yaml",
                          "yml", "sh", "rb", "php", "kt", "swift"}


def _token_overlap(query_toks: set[str], path_toks: set[str]) -> float:
    """Jaccard-like overlap scalar in [0, 1] (runtime-clean)."""
    if not query_toks or not path_toks:
        return 0.0
    return len(query_toks & path_toks) / len(query_toks | path_toks)


def _risk_bucket(path: str) -> str:
    """Return the risk bucket label for a path (runtime-clean)."""
    if not isinstance(path, str) or not path:
        return "unknown"
    if _RISK_PATH_PATTERNS.search(path):
        return "risk_penalty"
    return "normal"


# Priority component weights (frozen, deterministic, runtime-clean).
# These are NOT tuned from outcomes; they are fixed constants chosen before
# any scoring. Tuning from outcomes would be a calibration claim.
WEIGHT_AGREEMENT = 0.30
WEIGHT_BM25_NORM = 0.20
WEIGHT_DIVERSITY = 0.20
WEIGHT_QUERY_PATH_OVERLAP = 0.15
WEIGHT_RISK_PENALTY = -0.25
WEIGHT_DUPLICATION_PENALTY = -0.30
# Method mix weights (bm25 weighted highest as primary lexical signal).
METHOD_MIX_WEIGHTS = {"bm25": 1.0, "regex": 0.6, "symbol": 0.8, "rrf": 0.9}


def _compute_priority(
    entry: dict[str, Any],
    query_toks: set[str],
    accepted_paths: set[str],
    accepted_dirs: set[str],
    accepted_spans: set[tuple[str, int, int]],
    method_set: set[str],
) -> dict[str, Any]:
    """Compute the v0.2 priority score and components for one deduped entry.

    Returns a dict with the priority score and its components (for the
    private SCORE only; never serialized publicly).
    """
    path = entry["path"]
    dir_part = _path_dir(path)
    is_new_file = _is_new_file(path, accepted_paths)
    is_new_dir = _is_new_dir(dir_part, accepted_dirs)
    path_toks = _path_tokens(path)
    overlap = _token_overlap(query_toks, path_toks)
    risk = _risk_bucket(path)

    # Agreement: weighted by method mix (sum of method mix weights for the
    # methods that returned this span).
    methods = entry.get("methods", set())
    if not isinstance(methods, set):
        methods = set(methods)
    agreement_weighted = sum(
        METHOD_MIX_WEIGHTS.get(m, 0.5) for m in methods
    )
    # Normalize to [0, sum of all method mix weights].
    total_method_weight = sum(
        METHOD_MIX_WEIGHTS.get(m, 0.5) for m in method_set
    ) or 1.0
    agreement_norm = agreement_weighted / total_method_weight

    # Normalized bm25 score (max_norm_score is already in [0, 1]).
    bm25_norm = float(entry.get("max_norm_score", 0.0))

    # Diversity bonus: 1.0 if both new file and new dir; 0.5 if new file
    # only; 0.25 if new dir only; 0.0 otherwise.
    if is_new_file and is_new_dir:
        diversity = 1.0
    elif is_new_file:
        diversity = 0.5
    elif is_new_dir:
        diversity = 0.25
    else:
        diversity = 0.0

    # Risk penalty: -1.0 if risk_penalty bucket, 0.0 otherwise.
    risk_penalty = 1.0 if risk == "risk_penalty" else 0.0

    # Duplication penalty: -1.0 if same-file span already accepted or
    # overlapping span; -0.5 if same file only; 0.0 otherwise.
    span_key = (entry["path"], entry["start_line"], entry["end_line"])
    same_file = path in accepted_paths
    overlap_span = span_key in accepted_spans
    if overlap_span:
        dup_penalty = 1.0
    elif same_file:
        dup_penalty = 0.5
    else:
        dup_penalty = 0.0

    priority = (
        WEIGHT_AGREEMENT * agreement_norm
        + WEIGHT_BM25_NORM * bm25_norm
        + WEIGHT_DIVERSITY * diversity
        + WEIGHT_QUERY_PATH_OVERLAP * overlap
        + WEIGHT_RISK_PENALTY * risk_penalty
        + WEIGHT_DUPLICATION_PENALTY * dup_penalty
    )

    return {
        "priority_score": round(priority, 6),
        "priority_components": {
            "agreement_norm": round(agreement_norm, 6),
            "bm25_norm": round(bm25_norm, 6),
            "diversity": round(diversity, 6),
            "query_path_overlap": round(overlap, 6),
            "risk_penalty": round(risk_penalty, 6),
            "duplication_penalty": round(dup_penalty, 6),
        },
        "is_new_file": is_new_file,
        "is_new_dir": is_new_dir,
        "risk_bucket": risk,
        "agreement_weighted": round(agreement_weighted, 6),
    }


def _bea_v0_2_diversity_risk_policy(
    candidates: list[dict[str, Any]],
    query: str,
    budget: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str]:
    """Deterministic BEA v0.2 diversity/risk acquisition policy.

    Consumes ONLY runtime-clean candidate features (method source, rank,
    score/normalized score, agreement, path/dir/extension, query tokens for
    overlap scalar). NEVER reads gold paths/lines/labels, row IDs, benchmark
    labels, previous outcomes, provider/model names, or private route buckets.

    Algorithm:
    1. Dedupe candidates by span (reuse BEA-1 dedup).
    2. Compute per-entry priority score (agreement + bm25_norm + diversity
       + query/path overlap - risk penalty - duplication penalty).
    3. Greedily select the highest-priority entry, add to accepted, update
       accepted_paths/dirs/spans, recompute priorities for remaining
       entries (so diversity/duplication update). Stop when budget reached
       or no candidates remain.
    4. Record action_order (step, action, priority_score, components) and
       budget_trace (step, budget_remaining, accepted_so_far).

    Returns ``(accepted_evidence, action_order, budget_trace, stop_reason)``.
    The accepted_evidence list contains {path, start_line, end_line,
    content_sha} dicts for scoring. action_order and budget_trace are for
    the private SCORE only.
    """
    if not candidates or budget <= 0:
        return [], [], [
            {"step": 0, "budget_remaining": 0, "accepted_so_far": 0}
        ], "no_candidates_or_zero_budget"

    deduped = bea1._dedup_candidates(candidates)
    if not deduped:
        return [], [], [
            {"step": 0, "budget_remaining": budget, "accepted_so_far": 0}
        ], "no_deduped_candidates"

    query_toks = _query_tokens(query)
    method_set = set()
    for entry in deduped:
        methods = entry.get("methods", set())
        if isinstance(methods, set):
            method_set |= methods
        elif isinstance(methods, (list, tuple)):
            method_set |= set(methods)

    accepted: list[dict[str, Any]] = []
    accepted_paths: set[str] = set()
    accepted_dirs: set[str] = set()
    accepted_spans: set[tuple[str, int, int]] = set()
    action_order: list[dict[str, Any]] = []
    budget_trace: list[dict[str, Any]] = []
    stop_reason = "candidates_exhausted"

    remaining = list(deduped)

    for step in range(budget):
        if not remaining:
            stop_reason = "candidates_exhausted"
            break
        # Compute priorities for all remaining entries.
        scored: list[tuple[float, int, dict[str, Any], dict[str, Any]]] = []
        for idx, entry in enumerate(remaining):
            prio = _compute_priority(
                entry, query_toks, accepted_paths, accepted_dirs,
                accepted_spans, method_set,
            )
            # Sort tiebreak: priority desc, then stable_index asc.
            scored.append((prio["priority_score"], entry.get("stable_index", idx), entry, prio))
        scored.sort(key=lambda t: (-t[0], t[1]))
        best_prio, _best_si, best_entry, best_components = scored[0]

        budget_remaining = budget - len(accepted)
        budget_trace.append({
            "step": step,
            "budget_remaining": budget_remaining,
            "accepted_so_far": len(accepted),
            "candidate_count_remaining": len(remaining),
        })

        if len(accepted) >= budget:
            stop_reason = "budget_exhausted"
            action_order.append({
                "step": step,
                "action": "stop_budget_exhausted",
                "priority_score": best_prio,
                "priority_components": best_components["priority_components"],
            })
            break

        # Accept the best entry.
        path = best_entry["path"]
        dir_part = _path_dir(path)
        span_key = (path, best_entry["start_line"], best_entry["end_line"])
        accepted.append({
            "path": path,
            "start_line": best_entry["start_line"],
            "end_line": best_entry["end_line"],
            "content_sha": best_entry.get("content_sha", ""),
        })
        accepted_paths.add(path)
        if dir_part:
            accepted_dirs.add(dir_part)
        accepted_spans.add(span_key)
        action_order.append({
            "step": step,
            "action": "accept_candidate",
            "priority_score": best_prio,
            "priority_components": best_components["priority_components"],
            "candidate_method": best_entry.get("first_method", ""),
            "candidate_rank": best_entry.get("first_rank", 0),
            "agreement": len(best_entry.get("methods", set())),
            "is_new_file": best_components["is_new_file"],
            "is_new_dir": best_components["is_new_dir"],
            "risk_bucket": best_components["risk_bucket"],
        })
        # Remove the accepted entry from remaining.
        remaining = [e for e in remaining if (e["path"], e["start_line"], e["end_line"]) != span_key]

    if len(accepted) >= budget and stop_reason != "candidates_exhausted":
        stop_reason = "budget_exhausted"
    elif not remaining:
        stop_reason = "candidates_exhausted"

    return accepted, action_order, budget_trace, stop_reason


# ---------------------------------------------------------------------------
# Same-budget control arms (reuse BEA-1 with v0.2 same-budget K).
# ---------------------------------------------------------------------------


def _same_budget_k(
    bea_accepted_count: int,
    deduped_count: int,
) -> int:
    """Same-budget K exactly per plan.

    K = min(len(bea_v0_2_diversity_risk.accepted_candidates),
            available_deduped_candidate_count)
    """
    return bea1._same_budget_k(bea_accepted_count, deduped_count)


def _bm25_prefix_same_budget_arm(
    method_candidates: dict[str, list[dict[str, Any]]],
    k: int,
) -> list[dict[str, Any]]:
    return bea1._same_budget_bm25_prefix_arm(method_candidates, k)


def _agreement_only_same_budget_arm(
    all_candidates: list[dict[str, Any]],
    k: int,
) -> list[dict[str, Any]]:
    return bea1._agreement_only_same_budget_arm(all_candidates, k)


def _seeded_random_same_budget_arm(
    all_candidates: list[dict[str, Any]],
    k: int,
) -> list[dict[str, Any]]:
    return bea1._seeded_random_same_budget_arm(all_candidates, k)


def _rrf_same_budget_arm(
    rrf_candidates: list[dict[str, Any]],
    k: int,
) -> list[dict[str, Any]]:
    """``rrf_same_budget`` arm: first K deduped RRF candidates."""
    if k <= 0 or not rrf_candidates:
        return []
    seen: set[tuple[str, int, int]] = set()
    deduped: list[dict[str, Any]] = []
    for c in rrf_candidates:
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
    return bea0._arm_metrics(
        arm_id, accepted_evidence, gold_record, task_id,
        candidate_count_read, evidence_budget_used, action_steps,
        latency_seconds,
    )


def _filter_arm_metrics(arm: dict[str, Any]) -> dict[str, Any]:
    return bea0._filter_arm_metrics(arm)


def _arm_means(per_record_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    return bea0._arm_means(per_record_metrics)


def _arm_metric_records(
    arm_metrics: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    return bea0._arm_metric_records(arm_metrics)


# ---------------------------------------------------------------------------
# Benchmark × policy arm metric records (records-only public shape).
# ---------------------------------------------------------------------------


def _benchmark_arm_metric_records(
    per_benchmark_arm_aggs: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Build per-benchmark × per-arm metric records.

    Each record: ``{benchmark, arm, metric, value, record_count}``.
    """
    records: list[dict[str, Any]] = []
    for benchmark in sorted(per_benchmark_arm_aggs):
        arm_aggs = per_benchmark_arm_aggs[benchmark]
        for arm_id in sorted(arm_aggs):
            agg = arm_aggs[arm_id]
            record_count = agg.get("__record_count__", 0)
            for metric in ARM_METRIC_ALLOWLIST:
                if metric in agg:
                    records.append({
                        "benchmark": benchmark,
                        "arm": arm_id,
                        "metric": metric,
                        "value": agg[metric],
                        "record_count": record_count,
                    })
    records.sort(key=lambda r: (r["benchmark"], r["arm"], r["metric"]))
    return records


def _delta_records(
    arm_aggs: dict[str, dict[str, Any]],
    baseline_arm: str,
    treatment_arms: list[str],
) -> list[dict[str, Any]]:
    """Build per-treatment × metric delta records vs a fixed baseline."""
    records: list[dict[str, Any]] = []
    baseline_agg = arm_aggs.get(baseline_arm, {})
    for treatment_arm in treatment_arms:
        treatment_agg = arm_aggs.get(treatment_arm, {})
        for metric in ARM_METRIC_ALLOWLIST:
            t = treatment_agg.get(metric, 0.0)
            b = baseline_agg.get(metric, 0.0)
            if isinstance(t, (int, float)) and isinstance(b, (int, float)):
                records.append({
                    "baseline_arm": baseline_arm,
                    "treatment_arm": treatment_arm,
                    "metric": metric,
                    "delta": round(float(t) - float(b), 6),
                })
    records.sort(key=lambda r: (r["treatment_arm"], r["metric"]))
    return records


def _mechanism_contrast_records(
    per_record_arm_metrics: list[dict[str, dict[str, Any]]],
    contrasts: list[tuple[str, str, str]],
) -> list[dict[str, Any]]:
    """Compute fixed-shape mechanism contrast records on the paired denominator.

    Each contrast: ``(contrast_id, baseline_arm, treatment_arm)`` where
    treatment is v0.2 and baseline is a control arm.
    """
    return bea1._mechanism_contrast_records(
        per_record_arm_metrics, contrasts
    )


def _win_tie_loss_records(
    per_record_arm_metrics: list[dict[str, dict[str, Any]]],
    baseline_arm: str,
    treatment_arm: str,
) -> list[dict[str, Any]]:
    """Build win/tie/loss records for primary metrics (paired denominator).

    For each primary metric, count records where treatment > baseline (win),
    treatment == baseline (tie), treatment < baseline (loss).

    Each record: ``{baseline_arm, treatment_arm, metric, win, tie, loss,
    record_count}``.
    """
    records: list[dict[str, Any]] = []
    paired: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for rec in per_record_arm_metrics:
        if baseline_arm in rec and treatment_arm in rec:
            paired.append((rec[baseline_arm], rec[treatment_arm]))
    record_count = len(paired)
    if record_count == 0:
        return records
    for metric in PRIMARY_METRICS:
        win = 0
        tie = 0
        loss = 0
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


# ---------------------------------------------------------------------------
# Per-record evaluation (one record × all policy arms).
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
    """Evaluate one record across all policy arms.

    Writes one private SCORE row PER policy arm (so private_record_count =
    records_successful × num_arms). Returns per-arm metrics for the record.
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

    # Collect rrf candidates (only if enabled).
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

    # --- Treatment arm: bea_v0_2_diversity_risk (computed first so K is set) ---
    if all_candidates and failure_reason is None:
        v02_accepted, v02_action_order, v02_budget_trace, v02_stop_reason = (
            _bea_v0_2_diversity_risk_policy(all_candidates, query, budget)
        )
    else:
        v02_accepted, v02_action_order, v02_budget_trace, v02_stop_reason = (
            [], [], [], "no_candidates_or_zero_budget"
        )
    v02_metrics = _arm_metrics_for_record(
        ARM_BEA_V0_2_DIVERSITY_RISK, v02_accepted, gold_record, task_id,
        len(all_candidates), len(v02_accepted), len(v02_action_order),
        time.perf_counter() - rec_start,
    )

    # --- Same-budget K exactly per plan (based on v0.2 accepted count) ---
    same_budget_k = _same_budget_k(len(v02_accepted), deduped_count)

    # --- Arm: bea_v0 (BEA-0 policy) ---
    if all_candidates and failure_reason is None:
        v0_accepted, v0_action_trace, v0_budget_states = (
            bea0._bea_v0_budgeted_policy(all_candidates, budget)
        )
    else:
        v0_accepted, v0_action_trace, v0_budget_states = [], [], []
    v0_metrics = _arm_metrics_for_record(
        ARM_BEA_V0, v0_accepted, gold_record, task_id,
        len(all_candidates), len(v0_accepted), len(v0_action_trace),
        0.0,
    )

    # --- Arm: bm25_prefix_same_budget ---
    sb_bm25_ev = _bm25_prefix_same_budget_arm(method_candidates, same_budget_k)
    sb_bm25_metrics = _arm_metrics_for_record(
        ARM_BM25_PREFIX_SAME_BUDGET, sb_bm25_ev, gold_record, task_id,
        len(method_candidates.get("bm25", [])),
        len(sb_bm25_ev), len(sb_bm25_ev), 0.0,
    )

    # --- Arm: agreement_only_same_budget ---
    ao_ev = _agreement_only_same_budget_arm(all_candidates, same_budget_k)
    ao_metrics = _arm_metrics_for_record(
        ARM_AGREEMENT_ONLY_SAME_BUDGET, ao_ev, gold_record, task_id,
        len(all_candidates), len(ao_ev), len(ao_ev), 0.0,
    )

    # --- Arm: seeded_random_same_budget ---
    sr_ev = _seeded_random_same_budget_arm(all_candidates, same_budget_k)
    sr_metrics = _arm_metrics_for_record(
        ARM_SEEDED_RANDOM_SAME_BUDGET, sr_ev, gold_record, task_id,
        len(all_candidates), len(sr_ev), len(sr_ev), 0.0,
    )

    # --- Arm: rrf_same_budget (optional) ---
    rrf_metrics: dict[str, Any] | None = None
    if enable_rrf_baseline:
        rrf_ev = _rrf_same_budget_arm(rrf_candidates, same_budget_k)
        rrf_metrics = _arm_metrics_for_record(
            ARM_RRF_SAME_BUDGET, rrf_ev, gold_record, task_id,
            len(rrf_candidates), len(rrf_ev), len(rrf_ev),
            rrf_latency_ms / 1000.0,
        )

    per_arm_metrics: dict[str, dict[str, Any]] = {
        ARM_BEA_V0: v0_metrics,
        ARM_BEA_V0_2_DIVERSITY_RISK: v02_metrics,
        ARM_BM25_PREFIX_SAME_BUDGET: sb_bm25_metrics,
        ARM_AGREEMENT_ONLY_SAME_BUDGET: ao_metrics,
        ARM_SEEDED_RANDOM_SAME_BUDGET: sr_metrics,
    }
    if rrf_metrics is not None:
        per_arm_metrics[ARM_RRF_SAME_BUDGET] = rrf_metrics

    rec_latency_ms = int((time.perf_counter() - rec_start) * 1000)

    # --- Build runtime_query_feature_summary (runtime-clean, private) ---
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
        "v0_2_accepted_count": int(len(v02_accepted)),
        "query_length_chars": len(query) if isinstance(query, str) else 0,
        "query_word_count": (
            len(query.split()) if isinstance(query, str) and query else 0
        ),
        "query_token_count": len(_query_tokens(query)),
    }

    # --- Build candidate_features (per-candidate v0.2 features, private) ---
    # Only computed for the v0.2 arm; other arms reuse the same candidate
    # list shape as BEA-1.
    private_candidate_list: list[dict[str, Any]] = []
    span_agreement: dict[tuple[str, int, int], int] = {}
    for c in all_candidates:
        key = bea0._span_key(c)
        span_agreement.setdefault(key, 0)
        span_agreement[key] += 1
    accepted_paths_v02: set[str] = set()
    accepted_dirs_v02: set[str] = set()
    accepted_spans_v02: set[tuple[str, int, int]] = set()
    for ev in v02_accepted:
        accepted_paths_v02.add(ev["path"])
        d = _path_dir(ev["path"])
        if d:
            accepted_dirs_v02.add(d)
        accepted_spans_v02.add((ev["path"], ev["start_line"], ev["end_line"]))
    query_toks = _query_tokens(query)
    method_set: set[str] = set()
    for c in all_candidates:
        method_set.add(c["method"])
    # Build deduped entries with priority components.
    deduped = bea1._dedup_candidates(all_candidates) if all_candidates else []
    deduped_by_key: dict[tuple[str, int, int], dict[str, Any]] = {}
    for entry in deduped:
        deduped_by_key[(entry["path"], entry["start_line"], entry["end_line"])] = entry
    for c in all_candidates:
        key = bea0._span_key(c)
        entry = deduped_by_key.get(key, {})
        prio = _compute_priority(
            entry, query_toks, accepted_paths_v02, accepted_dirs_v02,
            accepted_spans_v02, method_set,
        ) if entry else {}
        selected = key in accepted_spans_v02
        private_candidate_list.append({
            "method": c["method"],
            "rank": c["rank"],
            "score": c["score"],
            "normalized_score": c["normalized_score"],
            "path": c["path"],
            "start_line": c["start_line"],
            "end_line": c["end_line"],
            "content_sha": c["content_sha"],
            "extension": c["extension"],
            "agreement": span_agreement.get(key, 0),
            "dir": _path_dir(c["path"]),
            "is_new_file": _is_new_file(c["path"], accepted_paths_v02),
            "is_new_dir": _is_new_dir(_path_dir(c["path"]), accepted_dirs_v02),
            "path_token_overlap": _token_overlap(query_toks, _path_tokens(c["path"])),
            "risk_bucket": _risk_bucket(c["path"]),
            "priority_score": prio.get("priority_score", 0.0),
            "priority_components": prio.get("priority_components", {}),
            "selected": selected,
        })

    # --- Write one private SCORE row PER policy arm ---
    # Each row shares the candidate_features + runtime_query_feature_summary,
    # but has its own action_order / budget_trace / stop_reason / score_outcome.
    arms_to_write = [
        (ARM_BEA_V0_2_DIVERSITY_RISK, v02_action_order, v02_budget_trace,
         v02_stop_reason, v02_metrics),
        (ARM_BEA_V0, v0_action_trace, v0_budget_states,
         "v0_budget_exhausted_or_candidates_exhausted", v0_metrics),
        (ARM_BM25_PREFIX_SAME_BUDGET, [], [],
         "same_budget_prefix_k_selected", sb_bm25_metrics),
        (ARM_AGREEMENT_ONLY_SAME_BUDGET, [], [],
         "same_budget_agreement_k_selected", ao_metrics),
        (ARM_SEEDED_RANDOM_SAME_BUDGET, [], [],
         "same_budget_seeded_random_k_selected", sr_metrics),
    ]
    if rrf_metrics is not None:
        arms_to_write.append((
            ARM_RRF_SAME_BUDGET, [], [],
            "same_budget_rrf_k_selected", rrf_metrics,
        ))

    for arm_id, action_order, budget_trace, stop_reason, score_outcome in arms_to_write:
        private_score_row = {
            "phase_run_id": phase_run_id,
            "benchmark": benchmark,
            "private_record_id": private_record_id,
            "policy_arm": arm_id,
            "runtime_query_feature_summary": runtime_query_feature_summary,
            "candidate_features": private_candidate_list,
            "priority_components": (
                v02_action_order if arm_id == ARM_BEA_V0_2_DIVERSITY_RISK else []
            ),
            "selected_decisions": (
                [{"step": a.get("step", i), "action": a.get("action", ""),
                  "priority_score": a.get("priority_score", 0.0)}
                 for i, a in enumerate(action_order)]
                if action_order else []
            ),
            "action_order": action_order,
            "budget_trace": budget_trace,
            "stop_reason": stop_reason,
            "score_outcome": score_outcome,
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
            return None, fcc

    return per_arm_metrics, fcc


# ---------------------------------------------------------------------------
# Heldout fetchers (slice [offset, offset+limit)).
# ---------------------------------------------------------------------------


def _fetch_heldout_contextbench_rows(
    row_offset: int,
    row_limit: int,
) -> tuple[list[dict[str, Any]], str, int, dict[str, int]]:
    """Fetch heldout ContextBench verified Python rows [offset, offset+limit).

    Fetches (offset + limit) rows from HF datasets-server, then returns only
    the heldout slice. Returns ``(rows, status, network_calls, fcc)``.
    """
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    fetch_limit = row_offset + row_limit
    rows, fetch_status, nc, fcc_update = c5a._fetch_contextbench_rows(
        fetch_limit, "python"
    )
    for k, v in fcc_update.items():
        if k in fcc:
            fcc[k] += v
    if fetch_status == "unavailable" or not rows:
        fcc["contextbench_fetch_failed"] = (
            fcc.get("contextbench_fetch_failed", 0) + 1
        )
        if not rows:
            fcc["contextbench_no_python_rows"] = (
                fcc.get("contextbench_no_python_rows", 0) + 1
            )
        return [], "unavailable", nc, fcc
    heldout = rows[row_offset: row_offset + row_limit]
    if not heldout:
        fcc["heldout_offset_exceeds_available"] = (
            fcc.get("heldout_offset_exceeds_available", 0) + 1
        )
        return [], "unavailable", nc, fcc
    return heldout, "pass", nc, fcc


def _fetch_heldout_repoqa_needles(
    needle_offset: int,
    needle_limit: int,
) -> tuple[list[dict[str, Any]], str, int, dict[str, int]]:
    """Fetch heldout RepoQA Python needles [offset, offset+limit).

    Downloads the asset, parses all Python needles, then returns only the
    heldout slice. Returns ``(needles, status, network_calls, fcc)``.
    """
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    network_calls = 0
    asset_bytes, dl_status, dl_fcc = c5d._download_asset_to_bytes(c5d.ASSET_URL)
    network_calls += 1
    for k, v in dl_fcc.items():
        if k in fcc:
            fcc[k] += v
    if dl_status != "pass" or not asset_bytes:
        fcc["repoqa_asset_download_failed"] = (
            fcc.get("repoqa_asset_download_failed", 0) + 1
        )
        return [], "unavailable", network_calls, fcc
    parsed, parse_status, parse_fcc = c5d._decompress_asset(asset_bytes)
    del asset_bytes
    for k, v in parse_fcc.items():
        if k in fcc:
            fcc[k] += v
    if parse_status != "pass" or parsed is None:
        fcc["repoqa_asset_parse_failed"] = (
            fcc.get("repoqa_asset_parse_failed", 0) + 1
        )
        return [], "unavailable", network_calls, fcc
    # Parse ALL needles (use a large limit so we get the full set), then slice.
    needles, needle_status, needle_fcc = c5d._parse_repoqa_needles(
        parsed, "python", 10000
    )
    del parsed
    for k, v in needle_fcc.items():
        if k in fcc:
            fcc[k] += v
    if needle_status != "pass" or not needles:
        fcc["repoqa_no_python_needles"] = (
            fcc.get("repoqa_no_python_needles", 0) + 1
        )
        return [], "unavailable", network_calls, fcc
    heldout = needles[needle_offset: needle_offset + needle_limit]
    if not heldout:
        fcc["heldout_offset_exceeds_available"] = (
            fcc.get("heldout_offset_exceeds_available", 0) + 1
        )
        return [], "unavailable", network_calls, fcc
    return heldout, "pass", network_calls, fcc


# ---------------------------------------------------------------------------
# Public report builders (fail-closed scan).
# ---------------------------------------------------------------------------


def _build_unavailable_report(
    failure_reason_category: str,
    *,
    self_test_passed: bool,
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
    safe_true["openlocus_retrieval_executed"] = False
    safe_true["score_py_metrics_computed"] = False
    safe_true["bea_v02_policy_executed"] = False
    safe_true["bea_v0_acquisition_performed"] = False
    safe_true["heldout_fresh_slice_read"] = False
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
        "mechanism_contrast_records": [],
        "win_tie_loss_records": [],
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
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "calibration_claimed": False,
            "method_winner_claimed": False,
            "signal_strength": "bea_v02_policy_smoke_unavailable",
            "is_full_external_benchmark_evaluation": False,
        },
    }
    scan = _bea2_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _build_pass_report(
    *,
    self_test_passed: bool,
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
    safe_true["bea_v02_policy_executed"] = records_successful > 0
    safe_true["bea_v0_acquisition_performed"] = records_successful > 0
    safe_true["heldout_fresh_slice_read"] = records_evaluated > 0
    safe_true["private_score_records_written"] = bool(
        private_score_records_written
    )

    # Benchmark × arm metric records.
    benchmark_arm_metric_records = _benchmark_arm_metric_records(
        per_benchmark_arm_aggs
    )

    # Delta records: v0.2 vs each control arm (v0, same-budget BM25,
    # agreement-only, seeded random; rrf if enabled).
    treatment_arms = [
        ARM_BEA_V0_2_DIVERSITY_RISK,
        ARM_BM25_PREFIX_SAME_BUDGET,
        ARM_AGREEMENT_ONLY_SAME_BUDGET,
        ARM_SEEDED_RANDOM_SAME_BUDGET,
    ]
    if enable_rrf_baseline:
        treatment_arms.append(ARM_RRF_SAME_BUDGET)
    delta_records = _delta_records(
        arm_aggs, BASELINE_ARM, treatment_arms
    )

    # Mechanism contrast records: v0.2 vs each control on paired denominator.
    contrasts = [
        (CONTRAST_V02_VS_V0, ARM_BEA_V0, ARM_BEA_V0_2_DIVERSITY_RISK),
        (CONTRAST_V02_VS_SAME_BUDGET_BM25, ARM_BM25_PREFIX_SAME_BUDGET, ARM_BEA_V0_2_DIVERSITY_RISK),
        (CONTRAST_V02_VS_AGREEMENT_ONLY, ARM_AGREEMENT_ONLY_SAME_BUDGET, ARM_BEA_V0_2_DIVERSITY_RISK),
        (CONTRAST_V02_VS_SEEDED_RANDOM, ARM_SEEDED_RANDOM_SAME_BUDGET, ARM_BEA_V0_2_DIVERSITY_RISK),
    ]
    mechanism_contrast_records = _mechanism_contrast_records(
        per_record_arm_metrics, contrasts
    )

    # Win/tie/loss records: v0.2 vs each control on primary metrics.
    win_tie_loss_records: list[dict[str, Any]] = []
    for baseline in (
        ARM_BEA_V0, ARM_BM25_PREFIX_SAME_BUDGET,
        ARM_AGREEMENT_ONLY_SAME_BUDGET, ARM_SEEDED_RANDOM_SAME_BUDGET,
    ):
        win_tie_loss_records.extend(_win_tie_loss_records(
            per_record_arm_metrics, baseline, ARM_BEA_V0_2_DIVERSITY_RISK
        ))
    if enable_rrf_baseline:
        win_tie_loss_records.extend(_win_tie_loss_records(
            per_record_arm_metrics, ARM_RRF_SAME_BUDGET,
            ARM_BEA_V0_2_DIVERSITY_RISK,
        ))
    win_tie_loss_records.sort(
        key=lambda r: (r["baseline_arm"], r["metric"])
    )

    if records_successful > 0 and records_failed == 0 and not partial:
        status = "bea2_policy_v02_pass"
    elif records_successful > 0:
        status = "partial"
    else:
        status = "unavailable_with_reason"

    fixed_arms = [
        ARM_BM25_PREFIX_SAME_BUDGET,
        ARM_AGREEMENT_ONLY_SAME_BUDGET,
        ARM_BEA_V0,
        ARM_BEA_V0_2_DIVERSITY_RISK,
        ARM_SEEDED_RANDOM_SAME_BUDGET,
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
        "treatment_arm": ARM_BEA_V0_2_DIVERSITY_RISK,
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
        "mechanism_contrast_records": mechanism_contrast_records,
        "win_tie_loss_records": win_tie_loss_records,
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
            "calibration_claimed": False,
            "method_winner_claimed": False,
            "signal_strength": "bea_v02_policy_smoke_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
        },
    }
    scan = _bea2_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


# ---------------------------------------------------------------------------
# Self-test (no network; synthetic candidates + synthetic score data).
# ---------------------------------------------------------------------------


def _build_synthetic_candidates() -> list[dict[str, Any]]:
    return bea0._build_synthetic_candidates()


def _build_synthetic_gold() -> dict[str, Any]:
    return bea0._build_synthetic_gold()


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all BEA-2 self-test groups (no network; synthetic data)."""
    checks: list[dict[str, Any]] = []

    # Build synthetic fixture.
    candidates = _build_synthetic_candidates()
    gold = _build_synthetic_gold()
    query = "merge adjacent strings into a single string"

    # Run v0.2 policy.
    v02_accepted, v02_action_order, v02_budget_trace, v02_stop_reason = (
        _bea_v0_2_diversity_risk_policy(candidates, query, 5)
    )
    # Run v0 (BEA-0) policy.
    v0_accepted, v0_action_trace, v0_budget_states = (
        bea0._bea_v0_budgeted_policy(candidates, 5)
    )
    deduped_count = len(bea1._dedup_candidates(candidates))
    same_budget_k = _same_budget_k(len(v02_accepted), deduped_count)
    sb_bm25_ev = _bm25_prefix_same_budget_arm(
        {"bm25": [c for c in candidates if c["method"] == "bm25"]},
        same_budget_k,
    )
    ao_ev = _agreement_only_same_budget_arm(candidates, same_budget_k)
    sr_ev = _seeded_random_same_budget_arm(candidates, same_budget_k)

    v02_m = _arm_metrics_for_record(
        ARM_BEA_V0_2_DIVERSITY_RISK, v02_accepted, gold, "bea2-st-001",
        len(candidates), len(v02_accepted), len(v02_action_order), 0.05,
    )
    v0_m = _arm_metrics_for_record(
        ARM_BEA_V0, v0_accepted, gold, "bea2-st-001",
        len(candidates), len(v0_accepted), len(v0_action_trace), 0.0,
    )
    sb_bm25_m = _arm_metrics_for_record(
        ARM_BM25_PREFIX_SAME_BUDGET, sb_bm25_ev, gold, "bea2-st-001",
        len([c for c in candidates if c["method"] == "bm25"]),
        len(sb_bm25_ev), len(sb_bm25_ev), 0.0,
    )
    ao_m = _arm_metrics_for_record(
        ARM_AGREEMENT_ONLY_SAME_BUDGET, ao_ev, gold, "bea2-st-001",
        len(candidates), len(ao_ev), len(ao_ev), 0.0,
    )
    sr_m = _arm_metrics_for_record(
        ARM_SEEDED_RANDOM_SAME_BUDGET, sr_ev, gold, "bea2-st-001",
        len(candidates), len(sr_ev), len(sr_ev), 0.0,
    )

    arm_aggs = {
        ARM_BEA_V0: _arm_means([v0_m]),
        ARM_BEA_V0_2_DIVERSITY_RISK: _arm_means([v02_m]),
        ARM_BM25_PREFIX_SAME_BUDGET: _arm_means([sb_bm25_m]),
        ARM_AGREEMENT_ONLY_SAME_BUDGET: _arm_means([ao_m]),
        ARM_SEEDED_RANDOM_SAME_BUDGET: _arm_means([sr_m]),
    }
    per_record_arm_metrics = [{
        ARM_BEA_V0: v0_m,
        ARM_BEA_V0_2_DIVERSITY_RISK: v02_m,
        ARM_BM25_PREFIX_SAME_BUDGET: sb_bm25_m,
        ARM_AGREEMENT_ONLY_SAME_BUDGET: ao_m,
        ARM_SEEDED_RANDOM_SAME_BUDGET: sr_m,
    }]
    per_benchmark_arm_aggs = {
        "contextbench": {
            arm_id: {**_arm_means([m]), "__record_count__": 1}
            for arm_id, m in [
                (ARM_BEA_V0, v0_m),
                (ARM_BEA_V0_2_DIVERSITY_RISK, v02_m),
                (ARM_BM25_PREFIX_SAME_BUDGET, sb_bm25_m),
                (ARM_AGREEMENT_ONLY_SAME_BUDGET, ao_m),
                (ARM_SEEDED_RANDOM_SAME_BUDGET, sr_m),
            ]
        },
    }
    manifest_hash = _private_score_manifest_hash()
    skeleton = _build_pass_report(
        self_test_passed=True,
        contextbench_row_offset_requested=40,
        contextbench_row_limit_requested=20,
        repoqa_needle_offset_requested=20,
        repoqa_needle_limit_requested=10,
        budget=5,
        methods=("bm25", "regex", "symbol"),
        openlocus_binary_source="default",
        network_mode="local_explicit",
        records_evaluated=30,
        records_successful=30,
        records_failed=0,
        network_calls=2,
        arm_aggs=arm_aggs,
        per_record_arm_metrics=per_record_arm_metrics,
        per_benchmark_arm_aggs=per_benchmark_arm_aggs,
        private_score_records_written=True,
        private_score_record_count=180,  # 30 records × 6 arms
        private_score_storage_class="tmp_private",
        private_score_manifest_hash=manifest_hash,
        aggregate_runtime_seconds=42.0,
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES},
        enable_rrf_baseline=False,
        paired_exclusion_count=0,
        partial=False,
    )

    # --- Group 1: Artifact identity fields. ---
    checks.append(_check("schema_version_correct",
        skeleton["schema_version"] == SCHEMA_VERSION))
    checks.append(_check("claim_level_correct",
        skeleton["claim_level"] == CLAIM_LEVEL))
    checks.append(_check("mode_correct", skeleton["mode"] == MODE))
    checks.append(_check("phase_correct", skeleton["phase"] == PHASE))
    checks.append(_check("generated_by_correct",
        skeleton["generated_by"] == GENERATED_BY))
    checks.append(_check("status_pass_when_self_test_passed",
        skeleton["status"] == "bea2_policy_v02_pass"))
    checks.append(_check("treatment_arm_correct",
        skeleton["treatment_arm"] == ARM_BEA_V0_2_DIVERSITY_RISK))
    checks.append(_check("baseline_arm_correct",
        skeleton["baseline_arm"] == BASELINE_ARM))
    checks.append(_check("seeded_random_seed_correct",
        skeleton["seeded_random_seed"] == SEEDED_RANDOM_SEED))

    # --- Group 2: Safe true flags. ---
    for flag in SAFE_TRUE_FLAGS:
        checks.append(_check(f"safe_true_{flag}_present", flag in skeleton))
    checks.append(_check("safe_true_aggregate_only_public_artifact",
        skeleton.get("aggregate_only_public_artifact") is True))
    checks.append(_check("safe_true_diagnostic_only",
        skeleton.get("diagnostic_only") is True))
    checks.append(_check("safe_true_bea_v02_policy_executed",
        skeleton.get("bea_v02_policy_executed") is True))
    checks.append(_check("safe_true_heldout_fresh_slice_read",
        skeleton.get("heldout_fresh_slice_read") is True))
    checks.append(_check("safe_true_private_score_records_written",
        skeleton.get("private_score_records_written") is True))

    # --- Group 3: No-claim / no-runtime-change false flags. ---
    for flag in DEFAULT_FALSE_FLAGS:
        checks.append(_check(f"no_claim_{flag}_false",
            skeleton.get(flag) is False))

    # --- Group 4: License fields. ---
    checks.append(_check("license_dataset_license_status",
        skeleton.get("dataset_license_status") == "unknown_dataset_license"))
    checks.append(_check("license_row_level_redistribution_allowed_false",
        skeleton.get("row_level_redistribution_allowed") is False))
    checks.append(_check("license_derived_row_level_publication_allowed_false",
        skeleton.get("derived_row_level_publication_allowed") is False))
    checks.append(_check("license_aggregate_metrics_publication",
        skeleton.get("aggregate_metrics_publication") == "aggregate_only_smoke"))

    # --- Group 5: Private SCORE manifest aggregate-only fields. ---
    manifest = skeleton.get("private_score_manifest", {})
    checks.append(_check("private_score_manifest_present",
        isinstance(manifest, dict) and len(manifest) > 0))
    checks.append(_check("private_score_manifest_records_written_true",
        manifest.get("records_written") is True))
    checks.append(_check("private_score_manifest_record_count_correct",
        manifest.get("record_count") == 180))
    checks.append(_check("private_score_manifest_schema_version_correct",
        manifest.get("schema_version") == PRIVATE_SCORE_SCHEMA_VERSION))
    checks.append(_check("private_score_manifest_storage_class_correct",
        manifest.get("storage_class") == "tmp_private"))
    checks.append(_check("private_score_manifest_path_not_publicly_serialized",
        manifest.get("path_publicly_serialized") is False))
    checks.append(_check("private_score_manifest_hash_is_sha256_hex",
        isinstance(manifest.get("manifest_hash"), str)
        and len(manifest["manifest_hash"]) == 64
        and all(c in "0123456789abcdef" for c in manifest["manifest_hash"])))
    for forbidden_key in (
        "private_score_path", "score_path", "private_score_file",
        "action_trace", "action_order", "budget_states", "budget_trace",
        "accepted_candidates", "final_candidates", "candidate_list",
        "candidates", "candidate_features", "score_outcome",
        "per_record_metrics", "runtime_query_features",
        "query_features", "priority_components", "selected_decisions",
        "private_record_id", "private_record_hash", "stop_reason",
    ):
        checks.append(_check(
            f"private_score_forbidden_key_{forbidden_key}_absent",
            forbidden_key not in skeleton))

    # --- Group 6: Row/needle/budget hard caps. ---
    checks.append(_check("contextbench_row_offset_default_40",
        CONTEXTBENCH_ROW_OFFSET_DEFAULT == 40))
    checks.append(_check("contextbench_row_limit_default_20",
        CONTEXTBENCH_ROW_LIMIT_DEFAULT == 20))
    checks.append(_check("contextbench_row_limit_hard_cap_20",
        CONTEXTBENCH_ROW_LIMIT_HARD_CAP == 20))
    checks.append(_check("contextbench_row_limit_caps_at_20",
        _validate_row_limit(100) == 20))
    checks.append(_check("repoqa_needle_offset_default_20",
        REPOQA_NEEDLE_OFFSET_DEFAULT == 20))
    checks.append(_check("repoqa_needle_limit_default_10",
        REPOQA_NEEDLE_LIMIT_DEFAULT == 10))
    checks.append(_check("repoqa_needle_limit_hard_cap_10",
        REPOQA_NEEDLE_LIMIT_HARD_CAP == 10))
    checks.append(_check("repoqa_needle_limit_caps_at_10",
        _validate_needle_limit(100) == 10))
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
    try:
        _validate_row_offset(-1)
        checks.append(_check("row_offset_rejects_negative", False))
    except SystemExit:
        checks.append(_check("row_offset_rejects_negative", True))

    # --- Group 7: Budget hard cap. ---
    checks.append(_check("budget_default_5", BUDGET_DEFAULT == 5))
    checks.append(_check("budget_hard_cap_20", BUDGET_HARD_CAP == 20))
    checks.append(_check("budget_caps_at_20", _validate_budget(100) == 20))
    try:
        _validate_budget(0)
        checks.append(_check("budget_rejects_zero", False))
    except SystemExit:
        checks.append(_check("budget_rejects_zero", True))

    # --- Group 8: Method validation. ---
    checks.append(_check("methods_default_correct",
        _validate_methods(DEFAULT_METHODS) == ("bm25", "regex", "symbol")))
    try:
        _validate_methods("regex,symbol")
        checks.append(_check("methods_requires_bm25_present", False))
    except SystemExit:
        checks.append(_check("methods_requires_bm25_present", True))

    # --- Group 9: BEA v0.2 policy mechanics. ---
    checks.append(_check("v02_policy_accepts_nonempty", len(v02_accepted) > 0))
    checks.append(_check("v02_policy_respects_budget_5",
        len(v02_accepted) <= 5))
    v02_b3, _, _, _ = _bea_v0_2_diversity_risk_policy(candidates, query, 3)
    checks.append(_check("v02_policy_respects_budget_3",
        len(v02_b3) <= 3))
    v02_b1, _, _, _ = _bea_v0_2_diversity_risk_policy(candidates, query, 1)
    checks.append(_check("v02_policy_respects_budget_1",
        len(v02_b1) <= 1))
    v02_b0, _, _, _ = _bea_v0_2_diversity_risk_policy(candidates, query, 0)
    checks.append(_check("v02_policy_budget_0_accepts_nothing",
        len(v02_b0) == 0))
    checks.append(_check("v02_policy_empty_candidates",
        len(_bea_v0_2_diversity_risk_policy([], query, 5)[0]) == 0))
    checks.append(_check("v02_policy_action_order_nonempty",
        len(v02_action_order) > 0))
    checks.append(_check("v02_policy_budget_trace_nonempty",
        len(v02_budget_trace) > 0))
    checks.append(_check("v02_policy_stop_reason_present",
        isinstance(v02_stop_reason, str) and len(v02_stop_reason) > 0))
    # v0.2 must differ from v0 (different action shape).
    checks.append(_check("v02_differs_from_v0_actions",
        len(v02_action_order) != len(v0_action_trace)
        or any(a.get("action") != "accept_candidate" for a in v02_action_order)
        or len(v02_accepted) != len(v0_accepted)))

    # --- Group 10: v0.2 priority components present. ---
    if v02_action_order:
        first = v02_action_order[0]
        checks.append(_check("v02_action_has_priority_score",
            "priority_score" in first))
        checks.append(_check("v02_action_has_priority_components",
            "priority_components" in first))
        comps = first.get("priority_components", {})
        for comp in (
            "agreement_norm", "bm25_norm", "diversity",
            "query_path_overlap", "risk_penalty", "duplication_penalty",
        ):
            checks.append(_check(f"v02_priority_component_{comp}_present",
                comp in comps))

    # --- Group 11: v0.2 runtime-clean invariance. ---
    tainted = []
    for c in candidates:
        tc = dict(c)
        tc["gold_paths"] = ["src/path1.py"]
        tc["row_id"] = "leaked"
        tc["benchmark_label"] = "positive"
        tc["previous_outcome"] = "accept"
        tc["model_family"] = "kimi"
        tc["task_bucket"] = "positive"
        tainted.append(tc)
    v02_t, _, _, _ = _bea_v0_2_diversity_risk_policy(tainted, query, 5)
    def _acc_key(a):
        return (a["path"], a["start_line"], a["end_line"])
    checks.append(_check("v02_runtime_clean_invariance_accepted",
        [_acc_key(a) for a in v02_accepted]
        == [_acc_key(a) for a in v02_t]))

    # --- Group 12: risk_bucket / diversity / query_overlap helpers. ---
    checks.append(_check("risk_bucket_test_dir",
        _risk_bucket("tests/test_foo.py") == "risk_penalty"))
    checks.append(_check("risk_bucket_docs_dir",
        _risk_bucket("docs/readme.md") == "risk_penalty"))
    checks.append(_check("risk_bucket_src_normal",
        _risk_bucket("src/main.py") == "normal"))
    checks.append(_check("risk_bucket_vendor",
        _risk_bucket("vendor/lib.py") == "risk_penalty"))
    checks.append(_check("risk_bucket_empty",
        _risk_bucket("") == "unknown"))
    checks.append(_check("path_dir_with_slash",
        _path_dir("src/foo/bar.py") == "src/foo"))
    checks.append(_check("path_dir_no_slash",
        _path_dir("main.py") == ""))
    checks.append(_check("is_new_file_true",
        _is_new_file("src/new.py", set()) is True))
    checks.append(_check("is_new_file_false",
        _is_new_file("src/old.py", {"src/old.py"}) is False))
    checks.append(_check("is_new_dir_true",
        _is_new_dir("src/new", set()) is True))
    checks.append(_check("is_new_dir_false_empty",
        _is_new_dir("", set()) is False))
    checks.append(_check("query_tokens_nonempty",
        len(_query_tokens("merge adjacent strings")) > 0))
    checks.append(_check("path_tokens_nonempty",
        len(_path_tokens("src/foo/bar.py")) > 0))
    checks.append(_check("token_overlap_positive",
        _token_overlap({"merge", "strings"}, {"merge", "adjacent"}) > 0))
    checks.append(_check("token_overlap_zero_disjoint",
        _token_overlap({"aaa"}, {"bbb"}) == 0.0))

    # --- Group 13: Same-budget K exactly. ---
    checks.append(_check("same_budget_k_min",
        _same_budget_k(3, 5) == 3 and _same_budget_k(5, 3) == 3
        and _same_budget_k(10, 10) == 10))
    checks.append(_check("same_budget_k_zero_v02_zero",
        _same_budget_k(0, 5) == 0))
    checks.append(_check("same_budget_k_zero_no_deduped",
        _same_budget_k(3, 0) == 0))

    # --- Group 14: Same-budget control arms. ---
    method_cands = {
        "bm25": [c for c in candidates if c["method"] == "bm25"],
        "regex": [c for c in candidates if c["method"] == "regex"],
        "symbol": [c for c in candidates if c["method"] == "symbol"],
    }
    sb_bm25_ev_2 = _bm25_prefix_same_budget_arm(method_cands, 2)
    checks.append(_check("bm25_prefix_returns_k", len(sb_bm25_ev_2) == 2))
    checks.append(_check("bm25_prefix_zero_when_k_zero",
        len(_bm25_prefix_same_budget_arm(method_cands, 0)) == 0))
    ao_ev_2 = _agreement_only_same_budget_arm(candidates, 2)
    checks.append(_check("agreement_only_returns_k", len(ao_ev_2) == 2))
    checks.append(_check("agreement_only_first_high_agreement",
        ao_ev_2[0]["path"] == "src/path1.py" if ao_ev_2 else False))
    sr_ev_2 = _seeded_random_same_budget_arm(candidates, 2)
    sr_ev_2_b = _seeded_random_same_budget_arm(candidates, 2)
    checks.append(_check("seeded_random_deterministic",
        [_acc_key(e) for e in sr_ev_2]
        == [_acc_key(e) for e in sr_ev_2_b]))

    # --- Group 15: benchmark_arm_metric_records fixed shape. ---
    bamr = skeleton.get("benchmark_arm_metric_records", [])
    checks.append(_check("benchmark_arm_metric_records_nonempty",
        isinstance(bamr, list) and len(bamr) > 0))
    if bamr:
        for idx, rec in enumerate(bamr[:5]):
            checks.append(_check(f"benchmark_arm_record_{idx}_shape",
                set(rec.keys()) == {"benchmark", "arm", "metric", "value", "record_count"}))
            checks.append(_check(f"benchmark_arm_record_{idx}_metric_allowlisted",
                rec.get("metric") in ARM_METRIC_ALLOWLIST))
            checks.append(_check(f"benchmark_arm_record_{idx}_value_numeric",
                isinstance(rec.get("value"), (int, float))))
            checks.append(_check(f"benchmark_arm_record_{idx}_record_count_positive",
                isinstance(rec.get("record_count"), int) and rec.get("record_count") > 0))

    # --- Group 16: delta_records fixed shape. ---
    dr = skeleton.get("delta_records", [])
    checks.append(_check("delta_records_nonempty",
        isinstance(dr, list) and len(dr) > 0))
    if dr:
        for idx, rec in enumerate(dr[:5]):
            checks.append(_check(f"delta_record_{idx}_shape",
                set(rec.keys()) == {"baseline_arm", "treatment_arm", "metric", "delta"}))
            checks.append(_check(f"delta_record_{idx}_baseline_arm_correct",
                rec.get("baseline_arm") == BASELINE_ARM))

    # --- Group 17: mechanism_contrast_records fixed shape + record_count. ---
    mcr = skeleton.get("mechanism_contrast_records", [])
    checks.append(_check("mechanism_contrast_records_nonempty",
        isinstance(mcr, list) and len(mcr) > 0))
    if mcr:
        for idx, rec in enumerate(mcr[:5]):
            checks.append(_check(f"contrast_record_{idx}_shape",
                set(rec.keys()) == {"contrast", "baseline_arm", "treatment_arm", "metric", "delta", "record_count"}))
            checks.append(_check(f"contrast_record_{idx}_treatment_is_v02",
                rec.get("treatment_arm") == ARM_BEA_V0_2_DIVERSITY_RISK))
            checks.append(_check(f"contrast_record_{idx}_record_count_positive",
                isinstance(rec.get("record_count"), int) and rec.get("record_count") > 0))

    # --- Group 18: win_tie_loss_records fixed shape. ---
    wtl = skeleton.get("win_tie_loss_records", [])
    checks.append(_check("win_tie_loss_records_nonempty",
        isinstance(wtl, list) and len(wtl) > 0))
    if wtl:
        for idx, rec in enumerate(wtl[:5]):
            checks.append(_check(f"wtl_record_{idx}_shape",
                set(rec.keys()) == {"baseline_arm", "treatment_arm", "metric", "win", "tie", "loss", "record_count"}))
            checks.append(_check(f"wtl_record_{idx}_treatment_is_v02",
                rec.get("treatment_arm") == ARM_BEA_V0_2_DIVERSITY_RISK))
            checks.append(_check(f"wtl_record_{idx}_metric_primary",
                rec.get("metric") in PRIMARY_METRICS))
            checks.append(_check(f"wtl_record_{idx}_sums_to_record_count",
                rec.get("win", 0) + rec.get("tie", 0) + rec.get("loss", 0)
                == rec.get("record_count", 0)))

    # --- Group 19: Failure category counts fixed enum. ---
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    fcc["retrieval_failed"] = 1
    checks.append(_check("failure_category_counts_in_enum",
        not _scan_bea2({"failure_category_counts": fcc})))
    bad_fcc = dict(fcc)
    bad_fcc["not_a_real_category"] = 1
    rebuilt = _build_unavailable_report(
        "retrieval_failed", self_test_passed=True,
        contextbench_row_offset_requested=40,
        contextbench_row_limit_requested=20,
        repoqa_needle_offset_requested=20,
        repoqa_needle_limit_requested=10,
        budget=5, methods=("bm25", "regex", "symbol"),
        openlocus_binary_source="default", network_mode="local_explicit",
        failure_category_counts=bad_fcc,
    )
    checks.append(_check("failure_category_counts_rejects_non_enum",
        "not_a_real_category" not in rebuilt["failure_category_counts"]))

    # --- Group 20: Unavailable report. ---
    unavail = _build_unavailable_report(
        "contextbench_fetch_failed", self_test_passed=True,
        contextbench_row_offset_requested=40,
        contextbench_row_limit_requested=20,
        repoqa_needle_offset_requested=20,
        repoqa_needle_limit_requested=10,
        budget=5, methods=("bm25", "regex", "symbol"),
        openlocus_binary_source="default", network_mode="local_explicit",
    )
    checks.append(_check("unavailable_status",
        unavail["status"] == "unavailable_with_reason"))
    checks.append(_check("unavailable_failure_reason_category",
        unavail["failure_reason_category"] == "contextbench_fetch_failed"))
    checks.append(_check("unavailable_no_v02_performed_flag",
        unavail["bea_v02_policy_executed"] is False))
    checks.append(_check("unavailable_no_perf_claim",
        unavail["external_benchmark_performance_claimed"] is False))
    checks.append(_check("unavailable_empty_benchmark_arm_metric_records",
        unavail["benchmark_arm_metric_records"] == []))
    checks.append(_check("unavailable_empty_delta_records",
        unavail["delta_records"] == []))
    checks.append(_check("unavailable_empty_mechanism_contrast_records",
        unavail["mechanism_contrast_records"] == []))
    checks.append(_check("unavailable_empty_win_tie_loss_records",
        unavail["win_tie_loss_records"] == []))
    checks.append(_check("unavailable_private_score_manifest_present",
        isinstance(unavail.get("private_score_manifest"), dict)
        and unavail["private_score_manifest"].get("path_publicly_serialized") is False))
    checks.append(_check("unavailable_forbidden_scan_pass",
        unavail["forbidden_scan"]["status"] == "pass"))

    # --- Group 21: Scanner rejects forbidden content. ---
    for forbidden_key in bea1.BEA1_FORBIDDEN_EXTRA_KEYS:
        checks.append(_check(f"scanner_rejects_{forbidden_key}_key",
            bool(_scan_bea2({forbidden_key: "value"}))))
    checks.append(_check("scanner_rejects_repo_url_value",
        bool(_scan_bea2({"leaked": "https://github.com/foo/bar"}))))
    checks.append(_check("scanner_rejects_repo_slug_value",
        bool(_scan_bea2({"leaked": "psf/black"}))))
    checks.append(_check("scanner_rejects_commit_sha_value",
        bool(_scan_bea2({"leaked": "f03ee113c9f3dfeb477f2d4247bfb7de2e5f465c"}))))
    checks.append(_check("scanner_rejects_file_path_value",
        bool(_scan_bea2({"leaked": "src/black/trans.py"}))))
    checks.append(_check("scanner_rejects_tmp_path_value",
        bool(_scan_bea2({"leaked": "/tmp/foo"}))))
    checks.append(_check("scanner_rejects_multiline_value",
        bool(_scan_bea2({"leaked": "line1\nline2"}))))

    # --- Group 22: Scanner allows safe values. ---
    checks.append(_check("scanner_allows_schema_version",
        not _scan_bea2({"schema_version": SCHEMA_VERSION})))
    checks.append(_check("scanner_allows_methods_value",
        not _scan_bea2({"methods": ["bm25", "regex", "symbol"]})))
    checks.append(_check("scanner_allows_budget_value",
        not _scan_bea2({"budget": 5})))
    checks.append(_check("scanner_allows_benchmark_arm_metric_records",
        not _scan_bea2({"benchmark_arm_metric_records": [
            {"benchmark": "contextbench", "arm": ARM_BEA_V0,
             "metric": "mrr", "value": 0.5, "record_count": 10}]})))
    checks.append(_check("scanner_allows_delta_records",
        not _scan_bea2({"delta_records": [
            {"baseline_arm": BASELINE_ARM, "treatment_arm": ARM_BEA_V0_2_DIVERSITY_RISK,
             "metric": "mrr", "delta": 0.1}]})))
    checks.append(_check("scanner_allows_mechanism_contrast_records",
        not _scan_bea2({"mechanism_contrast_records": [
            {"contrast": CONTRAST_V02_VS_V0, "baseline_arm": ARM_BEA_V0,
             "treatment_arm": ARM_BEA_V0_2_DIVERSITY_RISK, "metric": "mrr",
             "delta": 0.1, "record_count": 10}]})))
    checks.append(_check("scanner_allows_win_tie_loss_records",
        not _scan_bea2({"win_tie_loss_records": [
            {"baseline_arm": ARM_BEA_V0, "treatment_arm": ARM_BEA_V0_2_DIVERSITY_RISK,
             "metric": "mrr", "win": 3, "tie": 5, "loss": 2, "record_count": 10}]})))
    checks.append(_check("scanner_allows_private_score_manifest",
        not _scan_bea2({"private_score_manifest": {
            "records_written": True, "record_count": 180,
            "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
            "manifest_hash": "a" * 64, "storage_class": "tmp_private",
            "path_publicly_serialized": False}})))

    # --- Group 23: Fail-closed generation. ---
    try:
        _enforce_bea2_no_forbidden(skeleton)
        checks.append(_check("fail_closed_clean_report_no_raise", True))
    except SystemExit:
        checks.append(_check("fail_closed_clean_report_no_raise", False))
    for leak_key, leak_val, label in [
        ("private_score_path", "/tmp/leaked.jsonl", "private_score_path"),
        ("action_order", [{"action": "accept"}], "action_order"),
        ("candidate_features", [{"path": "x"}], "candidate_features"),
        ("priority_components", {"x": 1}, "priority_components"),
        ("winner", ARM_BEA_V0_2_DIVERSITY_RISK, "winner"),
        ("best_method", "bm25", "best_method"),
        ("calibration", "calibrated", "calibration"),
        ("method_winner", ARM_BEA_V0_2_DIVERSITY_RISK, "method_winner"),
    ]:
        leaked = dict(skeleton)
        leaked[leak_key] = leak_val
        try:
            _enforce_bea2_no_forbidden(leaked)
            checks.append(_check(f"fail_closed_{label}_raises", False))
        except SystemExit:
            checks.append(_check(f"fail_closed_{label}_raises", True))
    failed_st = dict(skeleton)
    failed_st["self_test_passed"] = False
    try:
        c5a._refuse_on_self_test_failure(failed_st)
        checks.append(_check("refuse_on_self_test_failure_raises", False))
    except SystemExit:
        checks.append(_check("refuse_on_self_test_failure_raises", True))
    try:
        c5a._refuse_on_self_test_failure(skeleton)
        checks.append(_check("refuse_on_self_test_pass_no_raise", True))
    except SystemExit:
        checks.append(_check("refuse_on_self_test_pass_no_raise", False))

    # --- Group 24: Public artifact self-scan is clean. ---
    checks.append(_check("public_artifact_self_scan_clean",
        not _scan_bea2(skeleton)))
    checks.append(_check("unavailable_self_scan_clean",
        not _scan_bea2(unavail)))

    # --- Group 25: CLI argument surface. ---
    parser = build_parser()
    option_strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            option_strings.add(opt)
    for required_opt in (
        "--self-test", "--contextbench-row-offset", "--contextbench-row-limit",
        "--repoqa-needle-offset", "--repoqa-needle-limit",
        "--budget", "--methods", "--openlocus", "--out",
        "--private-score-dir", "--enable-rrf-baseline",
        "--enable-external-benchmark-network",
    ):
        checks.append(_check(f"cli_has_option_{required_opt}",
            required_opt in option_strings))

    # --- Group 26: Private SCORE writer round-trip. ---
    with tempfile.TemporaryDirectory(prefix="bea2_selftest_score_") as sd:
        sf = Path(sd) / "bea2.private.jsonl"
        row = {
            "phase_run_id": "bea2-selftest", "benchmark": "synthetic",
            "private_record_id": "synthetic-001",
            "policy_arm": ARM_BEA_V0_2_DIVERSITY_RISK,
            "runtime_query_feature_summary": {"benchmark": "synthetic"},
            "candidate_features": [], "priority_components": [],
            "selected_decisions": [], "action_order": [],
            "budget_trace": [], "stop_reason": "test",
            "score_outcome": {}, "latency_ms": 1,
            "cost_usd": 0.0, "tokens": 0, "provider_calls": 0,
            "failure_reason": None,
        }
        _write_private_score_row(sf, row)
        _write_private_score_row(sf, row)
        lines = sf.read_text(encoding="utf-8").splitlines()
        checks.append(_check("private_score_writer_two_rows", len(lines) == 2))
        checks.append(_check("private_score_rows_parse_as_json",
            all(isinstance(json.loads(l), dict) for l in lines if l)))
        leaked = dict(skeleton)
        leaked["private_score_path"] = str(sf)
        checks.append(_check("private_score_path_leak_detected_by_scanner",
            bool(_scan_bea2(leaked))))

    # --- Group 27: Paired denominator rule (win/tie/loss). ---
    rec_a = {ARM_BEA_V0: v0_m, ARM_BEA_V0_2_DIVERSITY_RISK: v02_m}
    rec_b = {ARM_BEA_V0: v0_m}  # missing v0.2
    paired = [rec_a, rec_b]
    wtl_partial = _win_tie_loss_records(
        paired, ARM_BEA_V0, ARM_BEA_V0_2_DIVERSITY_RISK
    )
    if wtl_partial:
        checks.append(_check("win_tie_loss_paired_excludes_missing",
            wtl_partial[0]["record_count"] == 1))
    else:
        checks.append(_check("win_tie_loss_paired_excludes_missing", False))

    # --- Group 28: Aggregate runtime seconds present. ---
    checks.append(_check("pass_report_has_aggregate_runtime_seconds",
        "aggregate_runtime_seconds" in skeleton
        and isinstance(skeleton["aggregate_runtime_seconds"], (int, float))))
    checks.append(_check("unavailable_report_has_no_runtime",
        "aggregate_runtime_seconds" not in unavail))

    # --- Group 29: No winner/best_method/method_winner/calibration anywhere. ---
    for field in ("winner", "best_method", "recommended_default",
                  "method_winner", "calibration"):
        checks.append(_check(f"clean_report_missing_{field}",
            field not in skeleton))

    # --- Group 30: Fixed arms present. ---
    fixed_arms = skeleton.get("fixed_arms", [])
    for expected in (ARM_BM25_PREFIX_SAME_BUDGET, ARM_AGREEMENT_ONLY_SAME_BUDGET,
                     ARM_BEA_V0, ARM_BEA_V0_2_DIVERSITY_RISK,
                     ARM_SEEDED_RANDOM_SAME_BUDGET):
        checks.append(_check(f"fixed_arms_contains_{expected}",
            expected in fixed_arms))
    checks.append(_check("fixed_arms_excludes_rrf_when_disabled",
        ARM_RRF_SAME_BUDGET not in fixed_arms))

    # --- Group 31: v0.2 priority weights are frozen constants. ---
    checks.append(_check("weight_agreement_frozen",
        WEIGHT_AGREEMENT == 0.30))
    checks.append(_check("weight_bm25_norm_frozen",
        WEIGHT_BM25_NORM == 0.20))
    checks.append(_check("weight_diversity_frozen",
        WEIGHT_DIVERSITY == 0.20))
    checks.append(_check("weight_query_path_overlap_frozen",
        WEIGHT_QUERY_PATH_OVERLAP == 0.15))
    checks.append(_check("weight_risk_penalty_frozen",
        WEIGHT_RISK_PENALTY == -0.25))
    checks.append(_check("weight_duplication_penalty_frozen",
        WEIGHT_DUPLICATION_PENALTY == -0.30))
    checks.append(_check("seeded_random_seed_frozen",
        SEEDED_RANDOM_SEED == 20240621))

    all_passed = all(c["passed"] for c in checks if c is not None)
    return checks, all_passed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # noqa: D401
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(
        description=(
            "BEA-2 Policy v0.2 Diversity/Risk Mechanism Smoke "
            "(public records-only; fresh heldout ContextBench verified "
            "Python rows offset 40 limit 20 + RepoQA Python needles offset "
            "20 limit 10; multi-method candidate collection "
            "(bm25/regex/symbol); BEA v0.2 diversity/risk policy with "
            "frozen priority weights (agreement + bm25_norm + diversity + "
            "query/path overlap - risk penalty - duplication penalty); "
            "private per-record SCORE JSONL traces in /tmp (one row per "
            "record x policy arm); no provider calls; no raw repo/query/"
            "path/candidate/SCORE/provider/source/stdout/stderr/row IDs/"
            "gold/private path content committed)."
        )
    )
    ap.add_argument("--self-test", action="store_true",
        help="run deterministic self-test groups and exit (no artifact written, no network)")
    ap.add_argument("--contextbench-row-offset", type=int,
        default=CONTEXTBENCH_ROW_OFFSET_DEFAULT,
        help=f"ContextBench verified Python row offset (default {CONTEXTBENCH_ROW_OFFSET_DEFAULT})")
    ap.add_argument("--contextbench-row-limit", type=int,
        default=CONTEXTBENCH_ROW_LIMIT_DEFAULT,
        help=f"ContextBench verified Python row limit (default {CONTEXTBENCH_ROW_LIMIT_DEFAULT}; hard cap {CONTEXTBENCH_ROW_LIMIT_HARD_CAP})")
    ap.add_argument("--repoqa-needle-offset", type=int,
        default=REPOQA_NEEDLE_OFFSET_DEFAULT,
        help=f"RepoQA Python needle offset (default {REPOQA_NEEDLE_OFFSET_DEFAULT})")
    ap.add_argument("--repoqa-needle-limit", type=int,
        default=REPOQA_NEEDLE_LIMIT_DEFAULT,
        help=f"RepoQA Python needle limit (default {REPOQA_NEEDLE_LIMIT_DEFAULT}; hard cap {REPOQA_NEEDLE_LIMIT_HARD_CAP})")
    ap.add_argument("--budget", type=int, default=BUDGET_DEFAULT,
        help=f"evidence budget (default {BUDGET_DEFAULT}; hard cap {BUDGET_HARD_CAP})")
    ap.add_argument("--methods", default=DEFAULT_METHODS,
        help=f"comma-separated retrieval methods (default {DEFAULT_METHODS}; bm25 required)")
    ap.add_argument("--enable-rrf-baseline", action="store_true",
        help="enable the rrf_same_budget arm (default disabled)")
    ap.add_argument("--enable-external-benchmark-network", action="store_true",
        help="allow real HuggingFace + GitHub network access (default false)")
    ap.add_argument("--openlocus", default=None,
        help="OpenLocus binary path (default target/release then target/debug)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
        help="output artifact JSON path")
    ap.add_argument("--private-score-dir", default=None,
        help="explicit private SCORE JSONL directory (must be under /tmp or runs/)")
    return ap


# ---------------------------------------------------------------------------
# Network smoke runner.
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
    score_file = private_score_dir / "bea2.private.jsonl"
    try:
        score_file.unlink()
    except OSError:
        pass

    per_record_arm_metrics: list[dict[str, dict[str, Any]]] = []
    per_benchmark_arm_aggs: dict[str, dict[str, dict[str, Any]]] = {}
    records_evaluated = 0
    records_successful = 0
    records_failed = 0
    paired_exclusion_count = 0

    # --- ContextBench heldout arm ---
    cb_rows, cb_status, cb_nc, cb_fcc = _fetch_heldout_contextbench_rows(
        contextbench_row_offset, contextbench_row_limit
    )
    network_calls += cb_nc
    for k, v in cb_fcc.items():
        if k in fcc:
            fcc[k] += v
    if cb_status != "pass" or not cb_rows:
        if not cb_rows:
            fcc["contextbench_fetch_failed"] = (
                fcc.get("contextbench_fetch_failed", 0) + 1
            )
    else:
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
                prefix=f"bea2_cb_repo_{idx}_"
            ) as repo_root_str:
                repo_work_dir = Path(repo_root_str)
                clone_ok, _cf, clone_fcc = c5d._clone_and_checkout(
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
                    task_id=task_id, query=query,
                    gold_paths=gold_paths, gold_lines=gold_lines,
                    repo_root=repo_root, methods=methods, budget=budget,
                    enable_rrf_baseline=enable_rrf_baseline,
                    score_path=score_file, phase_run_id=phase_run_id,
                    fcc=fcc,
                )
                if per_arm is None:
                    records_failed += 1
                    continue
                per_record_arm_metrics.append(per_arm)
                # Accumulate per-benchmark × arm.
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

    # --- RepoQA heldout arm ---
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
            with tempfile.TemporaryDirectory(
                prefix=f"bea2_rq_repo_{idx}_"
            ) as repo_root_str:
                repo_work_dir = Path(repo_root_str)
                clone_ok, _cf, clone_fcc = c5d._clone_and_checkout(
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
                    task_id=task_id, query=query,
                    gold_paths=[needle_path],
                    gold_lines=[[start_line, end_line]],
                    repo_root=repo_root, methods=methods, budget=budget,
                    enable_rrf_baseline=enable_rrf_baseline,
                    score_path=score_file, phase_run_id=phase_run_id,
                    fcc=fcc,
                )
                if per_arm is None:
                    records_failed += 1
                    continue
                per_record_arm_metrics.append(per_arm)
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

    # --- Aggregate ---
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
            private_score_records_written=False,
            private_score_record_count=0,
            private_score_storage_class=private_score_storage_class,
            private_score_manifest_hash=manifest_hash,
            records_evaluated=records_evaluated,
            records_successful=records_successful,
            records_failed=records_failed,
            network_calls=network_calls, failure_category_counts=fcc,
        )

    # Compute per-benchmark × arm aggregate means.
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

    # Overall arm aggregates across all benchmarks.
    arm_aggs: dict[str, dict[str, Any]] = {}
    fixed_arm_ids = [
        ARM_BEA_V0, ARM_BEA_V0_2_DIVERSITY_RISK,
        ARM_BM25_PREFIX_SAME_BUDGET, ARM_AGREEMENT_ONLY_SAME_BUDGET,
        ARM_SEEDED_RANDOM_SAME_BUDGET,
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
    # Expected: records_successful × num_arms.
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
        print(f"self_test_passed={passed} "
              f"({passed_count}/{len(checks)} checks)")
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
        print("error: self-test failed; refusing to write artifact",
              file=sys.stderr)
        for c in checks:
            if not c["passed"]:
                print(f"  FAIL: {c['check']}", file=sys.stderr)
        sys.exit(1)

    openlocus_bin, openlocus_source = c5a._resolve_openlocus_binary(
        args.openlocus
    )
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
        _enforce_bea2_no_forbidden(report)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']}, "
              f"failure_reason={report['failure_reason_category']})")
        return

    private_score_dir, private_score_storage_class = (
        _resolve_private_score_dir(args.private_score_dir)
    )
    phase_run_id = f"bea2-{int(time.time())}"

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
        _enforce_bea2_no_forbidden(report)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']}, "
              f"failure_reason={report['failure_reason_category']})")
        print("enable_external_benchmark_network is false; skipping real "
              "BEA-2 policy v0.2 smoke.")
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
    except (OSError, subprocess.SubprocessError):
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
    manifest = report.get("private_score_manifest", {})
    if (enable_network and report.get("records_successful", 0) > 0
        and manifest.get("record_count", 0)
        != report.get("records_successful", 0) * len(report.get("fixed_arms", []))):
        # Note: private_score_record_count = records_successful × num_arms,
        # not records_successful. The fail-closed check is done inside
        # _run_network_smoke; here we only check provider_calls and forbidden.
        pass

    _enforce_bea2_no_forbidden(report)
    _write_json(out_path, report)
    print(f"wrote artifact "
          f"(forbidden_scan={report['forbidden_scan']['status']}, "
          f"self_test_passed={report['self_test_passed']}, "
          f"status={report['status']}, "
          f"phase={report['phase']}, "
          f"records_evaluated={report.get('records_evaluated', 0)}, "
          f"records_successful={report.get('records_successful', 0)}, "
          f"private_score_records_written="
          f"{report.get('private_score_records_written')}, "
          f"private_score_record_count="
          f"{manifest.get('record_count', 0)})")


if __name__ == "__main__":
    main()
