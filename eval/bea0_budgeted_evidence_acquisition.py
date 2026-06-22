#!/usr/bin/env python3
"""BEA-0 Budgeted Evidence Acquisition v0 (Public Aggregate-Only).

This module implements the **BEA-0 budgeted evidence acquisition** experiment
over fresh bounded ContextBench verified Python rows and RepoQA Python needles.
It is the first real algorithmic retrieval/acquisition experiment in the
OpenLocus research track that pairs a deterministic budgeted acquisition
policy with private per-record SCORE JSONL traces and publishes only
aggregate baseline-vs-treatment deltas.

BEA-0 is explicitly **not** a benchmark result, **not** a leaderboard entry,
**not** a performance claim, **not** a method-winner claim, **not** a
promotion, **not** a default/policy change, **not** a calibration claim, and
**not** a runtime/retriever/pack/backend/EvidenceCore semantic change. The
committed artifact records only aggregate retrieval/acquisition metrics
(``file_recall@10``, ``mrr``, ``span_f0.5@10``, ``success_rate``,
``candidate_count_read``, ``evidence_budget_used``, ``action_steps``,
``latency_seconds``, ``quality_per_candidate``) computed by ``eval/score.py``
plus deterministic budgeted acquisition policy accounting, over bounded real
ContextBench verified + RepoQA Python samples, with baseline-vs-treatment
deltas vs ``bm25_top10`` (and ``rrf_bm25_regex_symbol_top10`` when rrf is
enabled).

Claim boundary (binding):

* Claim level: ``bea_v0_budgeted_acquisition_smoke_only``.
* Status: ``bea_v0_smoke_pass`` | ``partial`` | ``unavailable_with_reason`` |
  ``fail_forbidden_scan`` | ``fail_schema_contract``.
* Mode: ``bea_v0_budgeted_acquisition``; phase ``BEA-0``.
* This is **eval/diagnostic only**. It is NOT a benchmark result, NOT a
  leaderboard entry, NOT a performance claim, NOT a method-winner claim, NOT
  a calibration claim, NOT a promotion, NOT a default change, NOT a
  runtime/retriever/pack/backend change, NOT an EvidenceCore semantic change,
  and NOT a downstream agent value claim.

Privacy / license boundary (binding):

* Raw ContextBench rows / RepoQA needles, queries/problem statements,
  repo URLs/names, base commits / commit SHAs, gold paths/spans/contents,
  generated task/label/run JSONL, evidence rows, cloned repos, candidate
  lists, action traces, budget-state sequences, accepted/final candidate
  selections, score outcomes, and stdout/stderr are kept **transient only**
  under ``/tmp`` or CI ephemeral workspace. They are NEVER committed or
  uploaded.
* Private per-record SCORE JSONL is written ONLY under ``/tmp`` (or an
  explicitly ignored private path). The private SCORE path is NEVER
  serialized in the public artifact, docs, or CI artifacts.
* The public artifact records ONLY aggregate SCORE manifest fields:
  ``private_score_records_written=true`` (only if rows actually written),
  ``private_score_record_count``, ``private_score_schema_version``,
  ``private_score_manifest_hash`` (sha256 of the in-memory manifest
  schema, never of the row contents), ``private_score_storage_class``,
  ``private_score_path_publicly_serialized=false``.
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
  and GitHub repos (asset download + repo clones). CI must be a separate
  explicit ``workflow_dispatch`` job with
  ``enable_external_benchmark_network=true``. It must NOT run on PR/push
  by default, must use no provider secrets/vars, no provider model env,
  and must upload only the aggregate report. The private SCORE JSONL is
  NEVER uploaded.

BEA v0 policy (runtime-clean, deterministic):

The treatment policy ``bea_v0_budgeted`` consumes only runtime-clean
candidate features available before scoring:

* method source (``bm25`` / ``regex`` / ``symbol``);
* candidate rank within method;
* score or normalized score if available;
* rank agreement across methods (how many methods returned the same
  path/span);
* duplicate path/span overlap (within and across methods);
* candidate count;
* accepted file/path coverage so far;
* budget remaining;
* cheap path kind/file extension metadata.

It MUST NOT use gold files/lines, labels, row IDs, benchmark-specific answer
hints, previous outcome on the same record, provider/model names, or private
route buckets.

Initial actions: ``accept_candidate``, ``skip_low_support``,
``rerank_by_agreement``, ``stop_budget_exhausted``. Optional if easy:
``expand_same_file`` (retain an additional same-file candidate under budget).

Run::

    python3 -m py_compile eval/bea0_budgeted_evidence_acquisition.py
    python3 eval/bea0_budgeted_evidence_acquisition.py --self-test
    python3 eval/bea0_budgeted_evidence_acquisition.py \\
        --contextbench-row-limit 10 --repoqa-needle-limit 5 \\
        --budget 10 --methods bm25,regex,symbol \\
        --out artifacts/bea0_budgeted_evidence_acquisition/\\
bea0_budgeted_evidence_acquisition_report.json

If the network smoke cannot complete in the environment, the default
artifact records truthful ``unavailable_with_reason`` with a real failure
category (no stale/fake pass). Self-test/docs/diff-check still pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# Reuse C5-A + C5-D helpers (query sanitizer, clone, scanner primitives,
# JSON helpers, score metric allowlist, license fields, etc.). The ``eval``
# directory has no ``__init__.py`` (it is a flat script directory), so we
# add this file's parent to ``sys.path`` and import directly.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402
import c5d_repoqa_bm25_retrieval_smoke as c5d  # noqa: E402
import run_retrieval  # noqa: E402
import score as score_mod  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants (BEA-0 owned)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "bea0_budgeted_evidence_acquisition.v1"
GENERATED_BY = "eval/bea0_budgeted_evidence_acquisition.py"
CLAIM_LEVEL = "bea_v0_budgeted_acquisition_smoke_only"
MODE = "bea_v0_budgeted_acquisition"
PHASE = "BEA-0"

DEFAULT_OUT = Path(
    "artifacts/bea0_budgeted_evidence_acquisition/"
    "bea0_budgeted_evidence_acquisition_report.json"
)

# Private SCORE JSONL schema version. Bumped only on breaking change to the
# private row schema. Public artifact records only this version string.
PRIVATE_SCORE_SCHEMA_VERSION = "bea0_private_score.v1"

# Hard caps on row/needle limits. Default ContextBench 10 / RepoQA 5.
CONTEXTBENCH_ROW_LIMIT_DEFAULT = 10
CONTEXTBENCH_ROW_LIMIT_HARD_CAP = 20
REPOQA_NEEDLE_LIMIT_DEFAULT = 5
REPOQA_NEEDLE_LIMIT_HARD_CAP = 10

# Default evidence budget for the bea_v0_budgeted policy.
BUDGET_DEFAULT = 10
BUDGET_HARD_CAP = 20

# Methods supported by the BEA-0 multi-method candidate collector.
ALLOWED_METHODS: tuple[str, ...] = ("bm25", "regex", "symbol")
DEFAULT_METHODS = "bm25,regex,symbol"

# Baseline arms.
BASELINE_BM25_TOP10 = "bm25_top10"
BASELINE_RRF_TOP10 = "rrf_bm25_regex_symbol_top10"
TREATMENT = "bea_v0_budgeted"

# Arm metric allowlist. Only these aggregate metric names from
# ``eval/score.py`` + BEA-0 acquisition policy may appear in the public
# artifact under per-arm ``aggregate_metrics``. No dynamic row IDs or paths.
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

# Bounded timeouts for external operations (seconds).
HF_TIMEOUT_SECONDS = 15
CLONE_TIMEOUT_SECONDS = 300
CHECKOUT_TIMEOUT_SECONDS = 90
RETRIEVAL_TIMEOUT_SECONDS = 90

# OpenLocus binary candidates (release then debug fallback).
DEFAULT_OPENLOCUS_CANDIDATES: tuple[str, ...] = (
    "target/release/openlocus",
    "target/debug/openlocus",
)

# ---------------------------------------------------------------------------
# Safe booleans true (only when actually true). Exactly these MAY be true
# in the committed public artifact.
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "bea_v0_acquisition_performed": False,
    "multi_method_candidates_collected": False,
    "budgeted_policy_executed": False,
    "private_score_records_written": False,
    "external_benchmark_rows_read": False,
    "repositories_materialized_transiently": False,
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
    "row_limit_capped",
    "needle_limit_capped",
    "scanner_self_test_failed",
    "forbidden_leak_blocked",
    "unexpected_exception",
)

# ---------------------------------------------------------------------------
# Public artifact scanner (BEA-0 owned, strict, fail-closed).
#
# BEA-0 reuses the C5-D forbidden scanner primitives (which extend C5-A)
# for raw key/value leak detection, and ADDS BEA-0-specific forbidden keys
# (private score path, action trace, candidate list, budget states, accepted
# candidates, final candidates, score outcome, etc.).
# ---------------------------------------------------------------------------

# BEA-0-specific forbidden keys (in addition to c5d.C5D_FORBIDDEN_EXTRA_KEYS
# and c5a.FORBIDDEN_KEY_NAMES). These are private per-record fields that
# must NEVER appear as dict keys anywhere in a public artifact JSON.
BEA0_FORBIDDEN_EXTRA_KEYS: frozenset[str] = frozenset(
    {
        # private SCORE path / storage (the path string is NEVER serialized)
        "private_score_path",
        "score_path",
        "private_score_file",
        # per-record private fields
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
        # benchmark / row identifiers
        "benchmark_row_id",
        "benchmark_record_id",
        "benchmark_label",
        "phase_run_id",
        "run_id",
        "task_id",
        "row_id",
        "needle_id",
        "instance_id",
        # model / provider / private buckets
        "provider_name",
        "model_name",
        "model_family",
        "provider_payload",
        "private_bucket",
        "route_bucket",
        "task_bucket",
    }
)

# BEA-0 schema-key container keys (children are fixed labels, not row
# values). Extends C5-D's set.
BEA0_SCHEMA_KEY_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "failure_category_counts",
        "aggregate_metrics",
        "arm_metrics",
        "deltas",
    }
)

# BEA-0-specific safe VALUE path last-key segments. These keys MAY hold
# categorical bucket strings or sha256 hex strings without triggering the
# hex_digest_value / forbidden_field_name_value checks.
BEA0_SAFE_VALUE_PATH_LAST_KEYS: frozenset[str] = frozenset(
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
        "claim_boundary",
        "signal_strength",
        "baseline_arm",
        "treatment_arm",
        "failure_reason_category",
        "dataset_license_status",
        "aggregate_metrics_publication",
        "citation_validation_mode",
        "storage_class",
    }
)


def _is_bea0_schema_key_container(path: str) -> bool:
    """Check if the parent of the current key is a BEA-0 schema-key container."""
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in BEA0_SCHEMA_KEY_CONTAINER_KEYS


def _bea0_safe_value_path(path: str) -> bool:
    """Check if a JSON path is a BEA-0-specific (or C5-D) safe value path."""
    last = path.rsplit(".", 1)[-1]
    last_key = last.split("[")[0]
    if last_key in BEA0_SAFE_VALUE_PATH_LAST_KEYS:
        return True
    return c5d._c5d_safe_value_path(path)


def _scan_bea0_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    """Scan for BEA-0-specific forbidden keys (private score / action trace / etc.)."""
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                is_schema_container = _is_bea0_schema_key_container(sub_path)
                if (
                    key_str in BEA0_FORBIDDEN_EXTRA_KEYS
                    and not is_schema_container
                ):
                    violations.append(
                        {
                            "category": "forbidden_bea0_extra_key",
                            "path": sub_path,
                        }
                    )
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


def _scan_bea0(obj: Any) -> list[dict[str, Any]]:
    """Combined BEA-0 scanner: C5-D primitives + BEA-0-specific checks.

    The C5-A/C5-D scanner is reused for raw key/value leak detection (URLs,
    hex digests, repo slugs, /tmp paths, etc.). BEA-0 ADDS rejection of
    private per-record SCORE fields anywhere (private_score_path,
    action_trace, budget_states, accepted_candidates, final_candidates,
    candidate_list, score_outcome, etc.) and relaxes false positives for
    legitimate categorical bucket strings / manifest hashes that appear
    under BEA-0-specific safe value paths.
    """
    violations: list[dict[str, Any]] = []
    for v in c5d._scan_c5d(obj):
        cat = v.get("category")
        if cat == "forbidden_field_name_value" and _bea0_safe_value_path(
            v.get("path", "")
        ):
            continue
        if cat == "hex_digest_value" and _bea0_safe_value_path(
            v.get("path", "")
        ):
            continue
        violations.append(v)
    violations.extend(_scan_bea0_forbidden_keys(obj))
    return violations


def _bea0_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    """Run the BEA-0 forbidden scanner and return a sanitized summary."""
    violations = _scan_bea0(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_bea0_no_forbidden(obj: Any) -> None:
    """Fail-closed guard: raise SystemExit if any forbidden content leaks."""
    scan = _bea0_forbidden_scan_summary(obj)
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

    Allowed methods: bm25, regex, symbol. At least bm25 must be present
    (the BEA-0 treatment requires a method source feature). Duplicate
    methods are de-duplicated while preserving order.
    """
    if not isinstance(methods, str) or not methods.strip():
        raise SystemExit("invalid arguments")
    parts: list[str] = []
    seen: set[str] = set()
    for raw in methods.split(","):
        m = raw.strip().lower()
        if not m:
            continue
        if m not in ALLOWED_METHODS:
            raise SystemExit("invalid arguments")
        if m in seen:
            continue
        seen.add(m)
        parts.append(m)
    if not parts:
        raise SystemExit("invalid arguments")
    if "bm25" not in parts:
        # BEA-0 treatment requires a bm25 method source for its primary
        # rank feature. Reject method lists without bm25.
        raise SystemExit("invalid arguments")
    return tuple(parts)


# ---------------------------------------------------------------------------
# Private SCORE JSONL writer (transient /tmp only; never committed).
# ---------------------------------------------------------------------------


def _resolve_private_score_dir(
    explicit: str | None,
) -> tuple[Path, str]:
    """Resolve the private SCORE JSONL directory.

    Default: a fresh TemporaryDirectory under ``/tmp``. If ``explicit`` is
    given, it must be an absolute path under ``/tmp`` (or an existing
    ignored private path). The returned directory is created if missing.

    Returns ``(absolute_path, storage_class)``. The storage_class is a
    categorical bucket string only ("tmp_private" or "ignored_private").
    The path itself is NEVER serialized in the public artifact.
    """
    if explicit:
        p = Path(explicit).expanduser().resolve()
        # Safety: the explicit path MUST be under /tmp (CI ephemeral) or
        # already in .gitignore (e.g. runs/). We refuse anywhere else to
        # avoid accidental commit.
        try:
            p.relative_to("/tmp")
            storage_class = "tmp_private"
        except ValueError:
            # Allow runs/ (gitignored) as an explicit private path.
            repo_root = Path(__file__).resolve().parent.parent
            try:
                p.relative_to(repo_root / "runs")
                storage_class = "ignored_private"
            except ValueError:
                raise SystemExit("invalid arguments")
        p.mkdir(parents=True, exist_ok=True)
        return p, storage_class
    # Default: fresh /tmp/bea0_private_score_<pid>_<ts> directory.
    ts = int(time.time())
    pid = os.getpid()
    p = Path("/tmp") / f"bea0_private_score_{pid}_{ts}"
    p.mkdir(parents=True, exist_ok=True)
    return p, "tmp_private"


def _private_score_manifest_hash() -> str:
    """Compute a stable sha256 of the private SCORE manifest schema.

    The manifest schema is the fixed set of fields each private row carries
    (NOT the row values themselves). This hash is safe to publish because
    it is computed only over the canonical schema definition (a fixed
    in-process dict), never over private row contents.
    """
    manifest_schema = {
        "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
        "fields": [
            "phase_run_id",
            "benchmark",
            "private_record_id",
            "runtime_query_feature_summary",
            "candidate_list",
            "action_trace",
            "budget_states",
            "accepted_candidates",
            "final_candidates",
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

    The file is created if missing. Rows are appended one per line.
    """
    score_path.parent.mkdir(parents=True, exist_ok=True)
    with score_path.open("a", encoding="utf-8") as dst:
        dst.write(json.dumps(row, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Candidate normalization + BEA v0 budgeted policy
# ---------------------------------------------------------------------------


_FILE_EXT_RE = re.compile(r"\.([A-Za-z0-9]+)$")


def _path_extension(path: str) -> str:
    """Return the lowercased file extension without the leading dot.

    Returns ``""`` if no extension. Cheap path-kind metadata only.
    """
    if not isinstance(path, str) or not path:
        return ""
    m = _FILE_EXT_RE.search(path)
    if not m:
        return ""
    return m.group(1).lower()


def _normalize_candidate(
    method: str,
    rank: int,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """Normalize a raw OpenLocus evidence dict into a BEA-0 candidate.

    Fields:
    * ``method``: bm25 | regex | symbol (rrf is handled separately for the
      rrf baseline, not as a candidate source for the treatment).
    * ``rank``: 1-based rank within the method's evidence list.
    * ``score``: numeric score from the evidence (or 0.0).
    * ``normalized_score``: score normalized to [0, 1] within the method's
      evidence list (max score -> 1.0; absent / zero -> 0.0). Computed by
      the caller after collecting the full method list.
    * ``path``, ``start_line``, ``end_line``, ``content_sha``: from evidence.
    * ``extension``: lowercased file extension (cheap path-kind metadata).
    """
    return {
        "method": method,
        "rank": int(rank),
        "score": float(evidence.get("score", 0.0) or 0.0),
        "normalized_score": 0.0,  # filled in by caller
        "path": str(evidence.get("path", "") or ""),
        "start_line": int(evidence.get("start_line", 0) or 0),
        "end_line": int(evidence.get("end_line", 0) or 0),
        "content_sha": str(evidence.get("content_sha", "") or ""),
        "extension": _path_extension(str(evidence.get("path", "") or "")),
    }


def _collect_method_candidates(
    openlocus_bin: str,
    method: str,
    query: str,
    cwd: Path,
    channels: str = "",
) -> tuple[list[dict[str, Any]], int, str]:
    """Run OpenLocus retrieval for one method, return normalized candidates.

    Returns ``(candidates, latency_ms, stderr_truncated)``. On subprocess
    failure or timeout, returns ``([], 0, "retrieval_failed")``. Never raises.
    """
    t0 = time.perf_counter()
    try:
        result = run_retrieval.run_query(
            openlocus_bin, method, query, str(cwd), channels
        )
    except Exception:
        return [], 0, "retrieval_failed"
    latency_ms = int((time.perf_counter() - t0) * 1000)
    raw_evidence = result.get("evidence", []) or []
    if not isinstance(raw_evidence, list):
        return [], latency_ms, "retrieval_failed"
    candidates: list[dict[str, Any]] = []
    for idx, ev in enumerate(raw_evidence):
        if not isinstance(ev, dict):
            continue
        candidates.append(_normalize_candidate(method, idx + 1, ev))
    # Compute normalized_score within this method's list.
    if candidates:
        max_score = max(abs(c["score"]) for c in candidates) or 0.0
        if max_score > 0:
            for c in candidates:
                c["normalized_score"] = round(c["score"] / max_score, 6)
    return candidates, latency_ms, result.get("stderr", "")


def _collect_rrf_candidates(
    openlocus_bin: str,
    query: str,
    cwd: Path,
    channels: str = "regex,bm25,symbol",
) -> tuple[list[dict[str, Any]], int, str]:
    """Run OpenLocus ``retrieve`` (rrf) and return normalized candidates.

    Returns ``(candidates, latency_ms, stderr_truncated)``. RRF evidence is
    used ONLY for the ``rrf_bm25_regex_symbol_top10`` baseline, never as a
    candidate source for the BEA-0 treatment (which uses only per-method
    bm25/regex/symbol candidates).
    """
    t0 = time.perf_counter()
    try:
        result = run_retrieval.run_query(
            openlocus_bin, "rrf", query, str(cwd), channels
        )
    except Exception:
        return [], 0, "retrieval_failed"
    latency_ms = int((time.perf_counter() - t0) * 1000)
    raw_evidence = result.get("evidence", []) or []
    if not isinstance(raw_evidence, list):
        return [], latency_ms, "retrieval_failed"
    candidates: list[dict[str, Any]] = []
    for idx, ev in enumerate(raw_evidence):
        if not isinstance(ev, dict):
            continue
        candidates.append(_normalize_candidate("rrf", idx + 1, ev))
    if candidates:
        max_score = max(abs(c["score"]) for c in candidates) or 0.0
        if max_score > 0:
            for c in candidates:
                c["normalized_score"] = round(c["score"] / max_score, 6)
    return candidates, latency_ms, result.get("stderr", "")


def _span_key(c: dict[str, Any]) -> tuple[str, int, int]:
    """Stable (path, start_line, end_line) span key for deduplication."""
    return (
        c.get("path", ""),
        int(c.get("start_line", 0) or 0),
        int(c.get("end_line", 0) or 0),
    )


def _bea_v0_budgeted_policy(
    candidates: list[dict[str, Any]],
    budget: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Deterministic BEA v0 budgeted acquisition policy.

    Consumes ONLY runtime-clean candidate features (method source, rank,
    score / normalized score, rank agreement across methods, duplicate
    path/span overlap, candidate count, accepted coverage, budget remaining,
    cheap path extension). NEVER reads gold paths/lines/labels, row IDs,
    benchmark labels, previous outcomes, provider/model names, or private
    route buckets.

    Algorithm:

    1. Compute per-span agreement: how many distinct methods returned the
       same ``(path, start_line, end_line)`` span. Build a per-span summary
       with max normalized_score, min rank, agreement count, method set.
    2. Sort the deduplicated span list by:
       (a) agreement count DESC (multi-method agreement first);
       (b) min rank across methods ASC (lower rank = earlier in any method);
       (c) max normalized_score DESC (higher score wins ties).
    3. Iterate the sorted list with a budget of ``budget`` accepted
       candidates. For each candidate:
       * If budget exhausted: emit ``stop_budget_exhausted`` and break.
       * If span has agreement==1 AND min_rank>5 AND max_norm_score<0.01:
         emit ``skip_low_support`` (skip without accepting).
       * If span has agreement>=2 AND path already in accepted_paths:
         emit ``rerank_by_agreement`` and defer (push to a deferred pool).
       * Else: emit ``accept_candidate`` and append to accepted; mark path.
    4. After the main pass, if budget remains, process deferred
       ``rerank_by_agreement`` candidates as ``expand_same_file`` actions
       (retain an additional same-file candidate under budget). This is the
       optional ``expand_same_file`` action.

    Returns ``(accepted_candidates, action_trace, budget_states)``. Each
    action trace entry contains ONLY runtime-clean features (no path/span
    values; no gold labels).
    """
    if not candidates or budget <= 0:
        return [], [], [
            {"step": 0, "budget_remaining": 0, "accepted_so_far": 0}
        ]

    # Step 1: per-span agreement + summary.
    span_summary: dict[tuple[str, int, int], dict[str, Any]] = {}
    for c in candidates:
        key = _span_key(c)
        if key not in span_summary:
            span_summary[key] = {
                "path": c["path"],
                "start_line": c["start_line"],
                "end_line": c["end_line"],
                "extension": c["extension"],
                "methods": set(),
                "min_rank": 99,
                "max_norm_score": 0.0,
                "max_score": 0.0,
                "first_method": c["method"],
                "first_rank": c["rank"],
            }
        s = span_summary[key]
        s["methods"].add(c["method"])
        s["min_rank"] = min(s["min_rank"], c["rank"])
        s["max_norm_score"] = max(s["max_norm_score"], c["normalized_score"])
        s["max_score"] = max(s["max_score"], c["score"])

    # Step 2: sort deduplicated spans.
    dedup: list[dict[str, Any]] = []
    for key, s in span_summary.items():
        dedup.append(
            {
                "path": s["path"],
                "start_line": s["start_line"],
                "end_line": s["end_line"],
                "content_sha": "",  # filled from first matching candidate
                "extension": s["extension"],
                "methods": s["methods"],
                "agreement": len(s["methods"]),
                "min_rank": s["min_rank"],
                "max_norm_score": s["max_norm_score"],
                "max_score": s["max_score"],
                "first_method": s["first_method"],
                "first_rank": s["first_rank"],
            }
        )
    dedup.sort(
        key=lambda c: (
            -c["agreement"],
            c["min_rank"],
            -c["max_norm_score"],
        )
    )

    # Fill content_sha from the first matching candidate (for accepted list).
    for entry in dedup:
        key = (entry["path"], entry["start_line"], entry["end_line"])
        for c in candidates:
            if _span_key(c) == key:
                entry["content_sha"] = c.get("content_sha", "")
                entry["method"] = c.get("method", entry["first_method"])
                entry["rank"] = c.get("rank", entry["first_rank"])
                entry["score"] = c.get("score", entry["max_score"])
                break

    accepted: list[dict[str, Any]] = []
    accepted_paths: set[str] = set()
    action_trace: list[dict[str, Any]] = []
    budget_states: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    candidate_count = len(dedup)

    # Step 3: main pass.
    for idx, entry in enumerate(dedup):
        budget_remaining = budget - len(accepted)
        budget_states.append(
            {
                "step": idx,
                "budget_remaining": budget_remaining,
                "accepted_so_far": len(accepted),
                "candidate_count": candidate_count,
            }
        )
        if len(accepted) >= budget:
            action_trace.append(
                {
                    "step": idx,
                    "action": "stop_budget_exhausted",
                    "candidate_method": entry["method"],
                    "candidate_rank": entry["rank"],
                    "agreement": entry["agreement"],
                    "max_norm_score": entry["max_norm_score"],
                }
            )
            break
        agreement = entry["agreement"]
        min_rank = entry["min_rank"]
        max_norm = entry["max_norm_score"]
        path = entry["path"]
        # Low-support rule.
        if (
            agreement == 1
            and min_rank > 5
            and max_norm < 0.01
        ):
            action_trace.append(
                {
                    "step": idx,
                    "action": "skip_low_support",
                    "candidate_method": entry["method"],
                    "candidate_rank": entry["rank"],
                    "agreement": agreement,
                    "max_norm_score": max_norm,
                }
            )
            continue
        # Rerank-by-agreement rule: agreement>=2 and same file already accepted.
        if agreement >= 2 and path in accepted_paths:
            action_trace.append(
                {
                    "step": idx,
                    "action": "rerank_by_agreement",
                    "candidate_method": entry["method"],
                    "candidate_rank": entry["rank"],
                    "agreement": agreement,
                    "max_norm_score": max_norm,
                }
            )
            deferred.append(entry)
            continue
        # Accept.
        accepted.append(
            {
                "path": entry["path"],
                "start_line": entry["start_line"],
                "end_line": entry["end_line"],
                "content_sha": entry["content_sha"],
                "method": entry["method"],
                "rank": entry["rank"],
                "score": entry["score"],
            }
        )
        accepted_paths.add(path)
        action_trace.append(
            {
                "step": idx,
                "action": "accept_candidate",
                "candidate_method": entry["method"],
                "candidate_rank": entry["rank"],
                "agreement": agreement,
                "max_norm_score": max_norm,
            }
        )

    # Step 4: optional expand_same_file pass over deferred rerank pool.
    if deferred and len(accepted) < budget:
        for entry in deferred:
            if len(accepted) >= budget:
                break
            accepted.append(
                {
                    "path": entry["path"],
                    "start_line": entry["start_line"],
                    "end_line": entry["end_line"],
                    "content_sha": entry["content_sha"],
                    "method": entry["method"],
                    "rank": entry["rank"],
                    "score": entry["score"],
                }
            )
            action_trace.append(
                {
                    "step": len(action_trace),
                    "action": "expand_same_file",
                    "candidate_method": entry["method"],
                    "candidate_rank": entry["rank"],
                    "agreement": entry["agreement"],
                    "max_norm_score": entry["max_norm_score"],
                }
            )

    return accepted, action_trace, budget_states


# ---------------------------------------------------------------------------
# Per-arm metrics computation (in-memory; reuses eval/score.py functions).
# ---------------------------------------------------------------------------


def _build_prediction_record(
    task_id: str,
    evidence_list: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a synthetic prediction record for ``eval/score.py`` functions.

    ``eval/score.py`` expects a prediction dict with ``task_id`` and
    ``evidence`` (a list of evidence dicts with path/start_line/end_line/
    content_sha). We build this in memory; it is NEVER written to the public
    artifact.
    """
    return {
        "task_id": task_id,
        "evidence": evidence_list,
        "returncode": 0,
        "latency_ms": 0,
    }


def _arm_metrics(
    arm_id: str,
    accepted_evidence: list[dict[str, Any]],
    gold_record: dict[str, Any],
    task_id: str,
    candidate_count_read: int,
    evidence_budget_used: int,
    action_steps: int,
    latency_seconds: float,
) -> dict[str, Any]:
    """Compute per-arm aggregate metrics for one record.

    Uses ``eval/score.py`` functions on a synthetic prediction record. Returns
    a dict with allowlisted metric names only.
    """
    pred = _build_prediction_record(task_id, accepted_evidence)
    gold = {task_id: gold_record}
    try:
        fr10 = score_mod.file_recall_at_k([pred], gold, 10)
    except Exception:
        fr10 = 0.0
    try:
        mrr_v = score_mod.mrr([pred], gold)
    except Exception:
        mrr_v = 0.0
    try:
        span_f = score_mod.span_f_beta_at_k([pred], gold, 10, 0.5)
    except Exception:
        span_f = 0.0
    # Success_rate: 1.0 if at least one accepted candidate matched a gold
    # file, else 0.0 (per-record binary; aggregate mean = success_rate).
    gold_paths = set(gold_record.get("gold_paths", []))
    pred_paths = set(e.get("path", "") for e in accepted_evidence[:10])
    success = 1.0 if (gold_paths & pred_paths) else 0.0
    # quality_per_candidate: span_f0.5 / candidate_count_read (or 0).
    quality_per_candidate = (
        round(span_f / candidate_count_read, 6)
        if candidate_count_read > 0
        else 0.0
    )
    return {
        "arm": arm_id,
        "file_recall@10": round(float(fr10), 6),
        "mrr": round(float(mrr_v), 6),
        "span_f0.5@10": round(float(span_f), 6),
        "success_rate": round(float(success), 6),
        "candidate_count_read": int(candidate_count_read),
        "evidence_budget_used": int(evidence_budget_used),
        "action_steps": int(action_steps),
        "latency_seconds": round(float(latency_seconds), 6),
        "quality_per_candidate": round(float(quality_per_candidate), 6),
    }


def _filter_arm_metrics(arm: dict[str, Any]) -> dict[str, Any]:
    """Filter an arm metrics dict to the allowlist only."""
    out: dict[str, Any] = {}
    for key in ARM_METRIC_ALLOWLIST:
        if key in arm:
            val = arm[key]
            if isinstance(val, bool):
                out[key] = bool(val)
            elif isinstance(val, (int, float)):
                if isinstance(val, float):
                    out[key] = round(val, 6)
                else:
                    out[key] = int(val)
    return out


def _arm_means(
    per_record_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute per-arm aggregate means across records.

    Returns an ``aggregate_metrics``-shaped dict with allowlisted keys only.
    """
    if not per_record_metrics:
        return {k: 0.0 for k in ARM_METRIC_ALLOWLIST}
    agg: dict[str, Any] = {}
    for key in ARM_METRIC_ALLOWLIST:
        values: list[Any] = []
        for rec in per_record_metrics:
            if key in rec:
                values.append(rec[key])
        if not values:
            agg[key] = 0.0
            continue
        if all(isinstance(v, bool) for v in values):
            agg[key] = any(values)
        elif all(isinstance(v, (int, float)) for v in values):
            nums = [float(v) for v in values]
            mean = sum(nums) / len(nums)
            agg[key] = round(mean, 6)
    return _filter_arm_metrics(agg)


def _arm_deltas(
    treatment_agg: dict[str, Any],
    baseline_agg: dict[str, Any],
) -> dict[str, float]:
    """Compute per-metric deltas (treatment - baseline)."""
    deltas: dict[str, float] = {}
    for key in ARM_METRIC_ALLOWLIST:
        t = treatment_agg.get(key, 0.0)
        b = baseline_agg.get(key, 0.0)
        if isinstance(t, (int, float)) and isinstance(b, (int, float)):
            deltas[key] = round(float(t) - float(b), 6)
        else:
            deltas[key] = 0.0
    return deltas


def _arm_metric_records(
    arm_metrics: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Convert arm metric maps to fixed-shape public records."""
    records: list[dict[str, Any]] = []
    for arm_id in sorted(arm_metrics):
        filtered = _filter_arm_metrics(arm_metrics[arm_id])
        for metric in ARM_METRIC_ALLOWLIST:
            if metric in filtered:
                records.append(
                    {
                        "arm": arm_id,
                        "metric": metric,
                        "value": filtered[metric],
                    }
                )
    return records


def _delta_records(
    deltas: dict[str, dict[str, float]]
) -> list[dict[str, Any]]:
    """Convert baseline-vs-treatment delta maps to fixed-shape records."""
    records: list[dict[str, Any]] = []
    for arm_id in sorted(deltas):
        for metric in ARM_METRIC_ALLOWLIST:
            if metric in deltas[arm_id]:
                records.append(
                    {
                        "baseline_arm": BASELINE_BM25_TOP10,
                        "treatment_arm": arm_id,
                        "metric": metric,
                        "delta": round(float(deltas[arm_id][metric]), 6),
                    }
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

    Runs multi-method retrieval, builds the BEA-0 candidate list, runs
    baselines + treatment, computes per-arm metrics, writes a private SCORE
    JSONL row, and returns per-arm metrics (or None on failure).

    The private SCORE row is written ONLY under ``/tmp`` (or an explicitly
    ignored private path). It contains the full per-record detail: phase/run
    id, benchmark, private record id, runtime query features, candidate list,
    action trace, budget states, accepted/final candidates, score outcome,
    latency/cost/tokens/provider_calls=0, failure reason.
    """
    rec_start = time.perf_counter()
    failure_reason: str | None = None

    # Collect candidates per method.
    method_candidates: dict[str, list[dict[str, Any]]] = {}
    method_latencies_ms: dict[str, int] = {}
    method_errors: dict[str, str] = {}
    all_candidates: list[dict[str, Any]] = []
    for method in methods:
        cands, lat_ms, err = _collect_method_candidates(
            openlocus_bin, method, query, repo_root
        )
        method_candidates[method] = cands
        method_latencies_ms[method] = lat_ms
        if not cands:
            method_errors[method] = err[:200] if err else "empty"
        else:
            all_candidates.extend(cands)

    # Collect rrf baseline candidates (only if enabled and bm25 method is
    # in the methods list — rrf baseline is fusion over the same channels).
    rrf_candidates: list[dict[str, Any]] = []
    rrf_latency_ms = 0
    rrf_error: str | None = None
    if enable_rrf_baseline:
        channels = ",".join(methods)
        rrf_candidates, rrf_latency_ms, rrf_err = _collect_rrf_candidates(
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
    bm25_metrics = _arm_metrics(
        BASELINE_BM25_TOP10,
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

    # --- Baseline arm: rrf_bm25_regex_symbol_top10 ---
    rrf_metrics: dict[str, Any] | None = None
    if enable_rrf_baseline:
        rrf_top10 = rrf_candidates[:10]
        rrf_metrics = _arm_metrics(
            BASELINE_RRF_TOP10,
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
        accepted, action_trace, budget_states = _bea_v0_budgeted_policy(
            all_candidates, budget
        )
    else:
        accepted, action_trace, budget_states = [], [], []
    treatment_metrics = _arm_metrics(
        TREATMENT,
        accepted,
        gold_record,
        task_id,
        candidate_count_read=len(all_candidates),
        evidence_budget_used=len(accepted),
        action_steps=len(action_trace),
        latency_seconds=time.perf_counter() - rec_start,
    )

    # --- Per-arm metrics dict (transient; written to private SCORE only) ---
    per_arm_metrics = {
        BASELINE_BM25_TOP10: bm25_metrics,
        TREATMENT: treatment_metrics,
    }
    if rrf_metrics is not None:
        per_arm_metrics[BASELINE_RRF_TOP10] = rrf_metrics

    rec_latency_ms = int((time.perf_counter() - rec_start) * 1000)

    # --- Build private SCORE row ---
    # Runtime query feature summary: cheap, runtime-clean features only.
    # NEVER includes the raw query text, gold paths/lines, or row IDs beyond
    # the local private record id (which is itself never serialized in the
    # public artifact).
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
        "query_length_chars": len(query) if isinstance(query, str) else 0,
        "query_word_count": (
            len(query.split()) if isinstance(query, str) and query else 0
        ),
    }

    # Build the private candidate list (deep copy with only the safe-to-log
    # private fields). This goes to /tmp private SCORE only; NEVER public.
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
                "agreement": 0,  # filled by policy; 0 here for raw list
            }
        )

    # Fill agreement per candidate from the policy span summary (re-compute).
    span_agreement: dict[tuple[str, int, int], int] = {}
    for c in all_candidates:
        key = _span_key(c)
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
        "action_trace": action_trace,
        "budget_states": budget_states,
        "accepted_candidates": accepted,
        "final_candidates": accepted,  # treatment final == accepted
        "baseline_bm25_top10_evidence": bm25_top10,
        "baseline_rrf_top10_evidence": rrf_candidates[:10] if enable_rrf_baseline else [],
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

    # Write private SCORE row (transient /tmp only).
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
    safe_true["repositories_materialized_transiently"] = False
    safe_true["openlocus_retrieval_executed"] = False
    safe_true["score_py_metrics_computed"] = False
    safe_true["bea_v0_acquisition_performed"] = False
    safe_true["multi_method_candidates_collected"] = False
    safe_true["budgeted_policy_executed"] = False
    safe_true["private_score_records_written"] = bool(
        private_score_records_written
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
        # Private SCORE manifest (aggregate-only; no path serialized).
        "private_score_records_written": bool(
            private_score_records_written
        ),
        "private_score_record_count": int(private_score_record_count),
        "private_score_schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
        "private_score_manifest_hash": (
            private_score_manifest_hash
            if private_score_manifest_hash is not None
            else _private_score_manifest_hash()
        ),
        "private_score_storage_class": private_score_storage_class,
        "private_score_path_publicly_serialized": False,
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
            "signal_strength": "bea_v0_budgeted_acquisition_smoke_unavailable",
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _bea0_forbidden_scan_summary(report)
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
    deltas: dict[str, dict[str, float]],
    private_score_records_written: bool,
    private_score_record_count: int,
    private_score_storage_class: str,
    private_score_manifest_hash: str,
    aggregate_runtime_seconds: float,
    failure_category_counts: dict[str, int],
    enable_rrf_baseline: bool,
    partial: bool,
) -> dict[str, Any]:
    """Build a pass/partial report with aggregate metrics + deltas."""
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    for k, v in failure_category_counts.items():
        if k in fcc:
            fcc[k] = int(v)

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["external_benchmark_rows_read"] = records_evaluated > 0
    safe_true["repositories_materialized_transiently"] = records_successful > 0
    safe_true["openlocus_retrieval_executed"] = records_successful > 0
    safe_true["score_py_metrics_computed"] = bool(arm_metrics)
    safe_true["bea_v0_acquisition_performed"] = records_successful > 0
    safe_true["multi_method_candidates_collected"] = records_successful > 0
    safe_true["budgeted_policy_executed"] = records_successful > 0
    safe_true["private_score_records_written"] = bool(
        private_score_records_written
    )

    arm_metric_records = _arm_metric_records(arm_metrics)
    delta_records = _delta_records(deltas)

    if records_successful > 0 and records_failed == 0 and not partial:
        status = "bea_v0_smoke_pass"
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
        "baseline_arms": (
            [BASELINE_BM25_TOP10, BASELINE_RRF_TOP10]
            if enable_rrf_baseline
            else [BASELINE_BM25_TOP10]
        ),
        "treatment_arm": TREATMENT,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "contextbench_row_limit_requested": contextbench_row_limit_requested,
        "repoqa_needle_limit_requested": repoqa_needle_limit_requested,
        "records_evaluated": records_evaluated,
        "records_successful": records_successful,
        "records_failed": records_failed,
        "network_calls": network_calls,
        "provider_calls": 0,
        "arm_metric_records": arm_metric_records,
        "delta_records": delta_records,
        # Private SCORE manifest (aggregate-only; no path serialized).
        "private_score_records_written": bool(
            private_score_records_written
        ),
        "private_score_record_count": int(private_score_record_count),
        "private_score_schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
        "private_score_manifest_hash": private_score_manifest_hash,
        "private_score_storage_class": private_score_storage_class,
        "private_score_path_publicly_serialized": False,
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
            "signal_strength": "bea_v0_budgeted_acquisition_smoke_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _bea0_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


# ---------------------------------------------------------------------------
# Self-test (no network; synthetic candidates + synthetic score data).
# ---------------------------------------------------------------------------


def _build_synthetic_candidates() -> list[dict[str, Any]]:
    """Build a synthetic multi-method candidate list for the self-test.

    The values are deliberately synthetic placeholder strings. They are
    NEVER written to any public artifact; only the policy mechanics,
    metrics, and aggregation logic are validated.
    """
    # 3 methods x 4 candidates each, with intentional overlap on path1.py
    # span (10,20) across all 3 methods (agreement=3), and on path2.py
    # span (5,8) across bm25+symbol (agreement=2).
    return [
        # bm25 method
        {
            "method": "bm25",
            "rank": 1,
            "score": 10.0,
            "normalized_score": 1.0,
            "path": "src/path1.py",
            "start_line": 10,
            "end_line": 20,
            "content_sha": "a" * 64,
            "extension": "py",
        },
        {
            "method": "bm25",
            "rank": 2,
            "score": 5.0,
            "normalized_score": 0.5,
            "path": "src/path2.py",
            "start_line": 5,
            "end_line": 8,
            "content_sha": "b" * 64,
            "extension": "py",
        },
        {
            "method": "bm25",
            "rank": 3,
            "score": 1.0,
            "normalized_score": 0.1,
            "path": "src/path3.py",
            "start_line": 1,
            "end_line": 5,
            "content_sha": "c" * 64,
            "extension": "py",
        },
        {
            "method": "bm25",
            "rank": 8,
            "score": 0.001,
            "normalized_score": 0.0001,
            "path": "src/path4.py",
            "start_line": 100,
            "end_line": 110,
            "content_sha": "d" * 64,
            "extension": "py",
        },
        # regex method
        {
            "method": "regex",
            "rank": 1,
            "score": 1.0,
            "normalized_score": 1.0,
            "path": "src/path1.py",
            "start_line": 10,
            "end_line": 20,
            "content_sha": "a" * 64,
            "extension": "py",
        },
        {
            "method": "regex",
            "rank": 2,
            "score": 1.0,
            "normalized_score": 1.0,
            "path": "src/path5.py",
            "start_line": 1,
            "end_line": 1,
            "content_sha": "e" * 64,
            "extension": "py",
        },
        # symbol method
        {
            "method": "symbol",
            "rank": 1,
            "score": 1.0,
            "normalized_score": 1.0,
            "path": "src/path1.py",
            "start_line": 10,
            "end_line": 20,
            "content_sha": "a" * 64,
            "extension": "py",
        },
        {
            "method": "symbol",
            "rank": 2,
            "score": 1.0,
            "normalized_score": 1.0,
            "path": "src/path2.py",
            "start_line": 5,
            "end_line": 8,
            "content_sha": "b" * 64,
            "extension": "py",
        },
        {
            "method": "symbol",
            "rank": 7,
            "score": 0.001,
            "normalized_score": 0.001,
            "path": "src/path6.py",
            "start_line": 50,
            "end_line": 60,
            "content_sha": "f" * 64,
            "extension": "py",
        },
    ]


def _build_synthetic_gold() -> dict[str, Any]:
    """Build a synthetic gold record for self-test."""
    return {
        "task_id": "bea0-selftest-001",
        "gold_paths": ["src/path1.py"],
        "gold_lines": [[10, 20]],
    }


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all BEA-0 self-test groups (no network; synthetic data)."""
    checks: list[dict[str, Any]] = []

    # --- Group 1: Artifact identity fields. ---
    arm_agg_bm25 = {
        "arm": BASELINE_BM25_TOP10,
        "file_recall@10": 1.0,
        "mrr": 1.0,
        "span_f0.5@10": 0.5,
        "success_rate": 1.0,
        "candidate_count_read": 4,
        "evidence_budget_used": 4,
        "action_steps": 4,
        "latency_seconds": 0.01,
        "quality_per_candidate": 0.125,
    }
    arm_agg_treatment = dict(arm_agg_bm25)
    arm_agg_treatment["arm"] = TREATMENT
    arm_agg_treatment["evidence_budget_used"] = 2
    arm_agg_treatment["action_steps"] = 5
    arm_agg_treatment["quality_per_candidate"] = 0.25
    arm_agg_rrf = dict(arm_agg_bm25)
    arm_agg_rrf["arm"] = BASELINE_RRF_TOP10
    arm_metrics = {
        BASELINE_BM25_TOP10: arm_agg_bm25,
        TREATMENT: arm_agg_treatment,
        BASELINE_RRF_TOP10: arm_agg_rrf,
    }
    deltas = {
        TREATMENT: _arm_deltas(arm_agg_treatment, arm_agg_bm25),
        BASELINE_RRF_TOP10: _arm_deltas(arm_agg_rrf, arm_agg_bm25),
    }
    manifest_hash = _private_score_manifest_hash()
    skeleton = _build_pass_report(
        self_test_passed=True,
        contextbench_row_limit_requested=10,
        repoqa_needle_limit_requested=5,
        budget=10,
        methods=("bm25", "regex", "symbol"),
        openlocus_binary_source="default",
        network_mode="local_explicit",
        records_evaluated=15,
        records_successful=15,
        records_failed=0,
        network_calls=2,
        arm_metrics=arm_metrics,
        deltas=deltas,
        private_score_records_written=True,
        private_score_record_count=15,
        private_score_storage_class="tmp_private",
        private_score_manifest_hash=manifest_hash,
        aggregate_runtime_seconds=42.0,
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES},
        enable_rrf_baseline=True,
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
            skeleton["status"] == "bea_v0_smoke_pass",
        )
    )
    checks.append(
        _check(
            "treatment_arm_correct",
            skeleton["treatment_arm"] == TREATMENT,
        )
    )
    checks.append(
        _check(
            "baseline_arms_includes_bm25",
            BASELINE_BM25_TOP10 in skeleton["baseline_arms"],
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
            "safe_true_bea_v0_acquisition_performed",
            skeleton.get("bea_v0_acquisition_performed") is True,
        )
    )
    checks.append(
        _check(
            "safe_true_multi_method_candidates_collected",
            skeleton.get("multi_method_candidates_collected") is True,
        )
    )
    checks.append(
        _check(
            "safe_true_budgeted_policy_executed",
            skeleton.get("budgeted_policy_executed") is True,
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
    checks.append(
        _check(
            "private_score_records_written_true",
            skeleton.get("private_score_records_written") is True,
        )
    )
    checks.append(
        _check(
            "private_score_record_count_correct",
            skeleton.get("private_score_record_count") == 15,
        )
    )
    checks.append(
        _check(
            "private_score_schema_version_correct",
            skeleton.get("private_score_schema_version")
            == PRIVATE_SCORE_SCHEMA_VERSION,
        )
    )
    checks.append(
        _check(
            "private_score_storage_class_correct",
            skeleton.get("private_score_storage_class") == "tmp_private",
        )
    )
    checks.append(
        _check(
            "private_score_path_not_publicly_serialized",
            skeleton.get("private_score_path_publicly_serialized")
            is False,
        )
    )
    checks.append(
        _check(
            "private_score_manifest_hash_is_sha256_hex",
            isinstance(skeleton.get("private_score_manifest_hash"), str)
            and len(skeleton["private_score_manifest_hash"]) == 64
            and all(
                c in "0123456789abcdef"
                for c in skeleton["private_score_manifest_hash"]
            ),
        )
    )
    # The private score path string must NEVER appear as a key or value
    # anywhere in the public artifact.
    private_score_forbidden_keys = (
        "private_score_path",
        "score_path",
        "private_score_file",
        "action_trace",
        "budget_states",
        "accepted_candidates",
        "final_candidates",
        "candidate_list",
        "candidates",
        "score_outcome",
        "per_record_metrics",
        "runtime_query_features",
        "query_features",
        "private_record_id",
        "private_record_hash",
    )
    for forbidden_key in private_score_forbidden_keys:
        checks.append(
            _check(
                f"private_score_forbidden_key_{forbidden_key}_absent",
                forbidden_key not in skeleton,
            )
        )

    # --- Group 6: Row/needle limit hard caps. ---
    checks.append(
        _check(
            "contextbench_row_limit_default_10",
            CONTEXTBENCH_ROW_LIMIT_DEFAULT == 10,
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
            "repoqa_needle_limit_default_5",
            REPOQA_NEEDLE_LIMIT_DEFAULT == 5,
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
            "budget_default_10",
            BUDGET_DEFAULT == 10,
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
    checks.append(
        _check(
            "methods_dedup_preserves_order",
            _validate_methods("bm25,bm25,regex")
            == ("bm25", "regex"),
        )
    )
    try:
        _validate_methods("regex,symbol")
        checks.append(
            _check("methods_requires_bm25_present", False)
        )
    except SystemExit:
        checks.append(
            _check("methods_requires_bm25_present", True)
        )
    try:
        _validate_methods("bm25,dense")
        checks.append(
            _check("methods_rejects_dense", False)
        )
    except SystemExit:
        checks.append(_check("methods_rejects_dense", True))
    try:
        _validate_methods("")
        checks.append(_check("methods_rejects_empty", False))
    except SystemExit:
        checks.append(_check("methods_rejects_empty", True))

    # --- Group 9: Path extension helper. ---
    checks.append(
        _check(
            "path_extension_py",
            _path_extension("src/foo.py") == "py",
        )
    )
    checks.append(
        _check(
            "path_extension_rs",
            _path_extension("src/bar.rs") == "rs",
        )
    )
    checks.append(
        _check(
            "path_extension_none",
            _path_extension("README") == "",
        )
    )
    checks.append(
        _check(
            "path_extension_lowercase",
            _path_extension("src/foo.PY") == "py",
        )
    )

    # --- Group 10: BEA v0 budgeted policy mechanics. ---
    candidates = _build_synthetic_candidates()
    accepted, action_trace, budget_states = _bea_v0_budgeted_policy(
        candidates, budget=10
    )
    checks.append(
        _check(
            "policy_accepts_nonempty",
            len(accepted) > 0,
        )
    )
    # First accepted should be the agreement=3 span (path1.py 10-20).
    checks.append(
        _check(
            "policy_first_accept_is_high_agreement",
            accepted[0]["path"] == "src/path1.py"
            and accepted[0]["start_line"] == 10
            and accepted[0]["end_line"] == 20
            if accepted
            else False,
        )
    )
    # Action trace should contain at least one accept_candidate.
    actions_present = {a["action"] for a in action_trace}
    checks.append(
        _check(
            "policy_has_accept_candidate_action",
            "accept_candidate" in actions_present,
        )
    )
    # The low-support candidate (bm25 rank 8, norm 0.0001, agreement=1)
    # should be skipped via skip_low_support.
    checks.append(
        _check(
            "policy_skips_low_support",
            "skip_low_support" in actions_present,
        )
    )
    # Budget states should track budget_remaining.
    checks.append(
        _check(
            "policy_budget_states_nonempty",
            len(budget_states) > 0,
        )
    )
    checks.append(
        _check(
            "policy_budget_remaining_decreasing",
            all(
                budget_states[i]["budget_remaining"]
                >= budget_states[i + 1]["budget_remaining"]
                for i in range(len(budget_states) - 1)
            )
            if len(budget_states) > 1
            else True,
        )
    )

    # --- Group 11: Policy respects budget cap. ---
    accepted_b3, _, _ = _bea_v0_budgeted_policy(candidates, budget=3)
    checks.append(
        _check(
            "policy_respects_budget_3",
            len(accepted_b3) <= 3,
        )
    )
    accepted_b1, _, _ = _bea_v0_budgeted_policy(candidates, budget=1)
    checks.append(
        _check(
            "policy_respects_budget_1",
            len(accepted_b1) <= 1,
        )
    )
    accepted_b0, action_trace_b0, budget_states_b0 = (
        _bea_v0_budgeted_policy(candidates, budget=0)
    )
    checks.append(
        _check(
            "policy_budget_0_accepts_nothing",
            len(accepted_b0) == 0,
        )
    )
    # Empty candidates.
    accepted_empty, _, budget_states_empty = _bea_v0_budgeted_policy(
        [], budget=10
    )
    checks.append(
        _check(
            "policy_empty_candidates_accepts_nothing",
            len(accepted_empty) == 0,
        )
    )

    # --- Group 12: Policy runtime-clean invariance. ---
    # Build a copy of candidates with synthetic gold/label/row-id fields
    # added (mimicking what a NON-runtime-clean policy might leak). The
    # policy must produce IDENTICAL accepted/action_trace/budget_states
    # because it ignores those fields.
    tainted_candidates = []
    for c in candidates:
        tc = dict(c)
        tc["gold_paths"] = ["src/path1.py"]  # would-be leak
        tc["gold_lines"] = [[10, 20]]
        tc["row_id"] = "synthetic-row-001"
        tc["benchmark_label"] = "positive"
        tc["previous_outcome"] = "accept"
        tc["model_family"] = "kimi"
        tc["task_bucket"] = "positive"
        tainted_candidates.append(tc)
    accepted_t, action_trace_t, budget_states_t = (
        _bea_v0_budgeted_policy(tainted_candidates, budget=10)
    )
    # Compare accepted lists by (path, start_line, end_line, method, rank).
    def _acc_key(a: dict[str, Any]) -> tuple:
        return (
            a["path"],
            a["start_line"],
            a["end_line"],
            a["method"],
            a["rank"],
        )
    acc_keys = [_acc_key(a) for a in accepted]
    acc_t_keys = [_acc_key(a) for a in accepted_t]
    checks.append(
        _check(
            "policy_runtime_clean_invariance_accepted",
            acc_keys == acc_t_keys,
        )
    )
    # Action traces must be identical (no field leaks into trace).
    def _strip_trace(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Strip to runtime-clean fields only.
        out = []
        for a in trace:
            out.append(
                {
                    k: v
                    for k, v in a.items()
                    if k in ("step", "action", "candidate_method",
                             "candidate_rank", "agreement",
                             "max_norm_score")
                }
            )
        return out
    checks.append(
        _check(
            "policy_runtime_clean_invariance_trace",
            _strip_trace(action_trace) == _strip_trace(action_trace_t),
        )
    )

    # --- Group 13: Per-arm metrics + deltas. ---
    gold = _build_synthetic_gold()
    bm25_evidence = [
        {
            "path": "src/path1.py",
            "start_line": 10,
            "end_line": 20,
            "content_sha": "a" * 64,
        },
        {
            "path": "src/path2.py",
            "start_line": 5,
            "end_line": 8,
            "content_sha": "b" * 64,
        },
    ]
    bm25_m = _arm_metrics(
        BASELINE_BM25_TOP10,
        bm25_evidence,
        gold,
        "bea0-selftest-001",
        candidate_count_read=4,
        evidence_budget_used=2,
        action_steps=2,
        latency_seconds=0.01,
    )
    checks.append(
        _check(
            "arm_metrics_bm25_file_recall_1",
            bm25_m["file_recall@10"] == 1.0,
        )
    )
    checks.append(
        _check(
            "arm_metrics_bm25_mrr_1",
            bm25_m["mrr"] == 1.0,
        )
    )
    checks.append(
        _check(
            "arm_metrics_bm25_success_rate_1",
            bm25_m["success_rate"] == 1.0,
        )
    )
    checks.append(
        _check(
            "arm_metrics_candidate_count_read",
            bm25_m["candidate_count_read"] == 4,
        )
    )
    checks.append(
        _check(
            "arm_metrics_quality_per_candidate_positive",
            bm25_m["quality_per_candidate"] > 0,
        )
    )
    # Empty evidence.
    empty_m = _arm_metrics(
        TREATMENT,
        [],
        gold,
        "bea0-selftest-empty",
        candidate_count_read=0,
        evidence_budget_used=0,
        action_steps=0,
        latency_seconds=0.0,
    )
    checks.append(
        _check(
            "arm_metrics_empty_file_recall_0",
            empty_m["file_recall@10"] == 0.0,
        )
    )
    checks.append(
        _check(
            "arm_metrics_empty_success_rate_0",
            empty_m["success_rate"] == 0.0,
        )
    )
    checks.append(
        _check(
            "arm_metrics_empty_quality_per_candidate_0",
            empty_m["quality_per_candidate"] == 0.0,
        )
    )
    # Deltas: treatment - baseline.
    d = _arm_deltas(bm25_m, empty_m)
    checks.append(
        _check(
            "arm_deltas_file_recall_positive",
            d["file_recall@10"] > 0,
        )
    )

    # --- Group 14: Aggregate means. ---
    agg = _arm_means([bm25_m, bm25_m])
    checks.append(
        _check(
            "arm_means_file_recall_1",
            agg["file_recall@10"] == 1.0,
        )
    )
    checks.append(
        _check(
            "arm_means_candidate_count_read_4",
            agg["candidate_count_read"] == 4,
        )
    )
    checks.append(
        _check(
            "arm_means_empty_zero",
            _arm_means([]) == {k: 0.0 for k in ARM_METRIC_ALLOWLIST},
        )
    )

    # --- Group 15: Arm metric allowlist filtering. ---
    raw = dict(bm25_m)
    raw["path"] = "src/leaked.py"  # forbidden key
    raw["row_id"] = "leaked-row-id"
    raw["content_sha"] = "a" * 64
    filtered = _filter_arm_metrics(raw)
    checks.append(
        _check(
            "arm_filter_excludes_path",
            "path" not in filtered,
        )
    )
    checks.append(
        _check(
            "arm_filter_excludes_row_id",
            "row_id" not in filtered,
        )
    )
    checks.append(
        _check(
            "arm_filter_excludes_content_sha",
            "content_sha" not in filtered,
        )
    )
    checks.append(
        _check(
            "arm_filter_includes_mrr",
            "mrr" in filtered,
        )
    )
    checks.append(
        _check(
            "arm_filter_excludes_arm",
            "arm" not in filtered,
        )
    )

    # --- Group 16: Failure category counts fixed enum. ---
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    fcc["retrieval_failed"] = 1
    sample_fail_report = {"failure_category_counts": fcc}
    checks.append(
        _check(
            "failure_category_counts_in_enum",
            not _scan_bea0(sample_fail_report),
        )
    )
    bad_fcc = dict(fcc)
    bad_fcc["not_a_real_category"] = 1
    rebuilt = _build_unavailable_report(
        "retrieval_failed",
        self_test_passed=True,
        contextbench_row_limit_requested=10,
        repoqa_needle_limit_requested=5,
        budget=10,
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

    # --- Group 17: Unavailable report. ---
    unavail = _build_unavailable_report(
        "contextbench_fetch_failed",
        self_test_passed=True,
        contextbench_row_limit_requested=10,
        repoqa_needle_limit_requested=5,
        budget=10,
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
            "unavailable_no_bea_v0_performed_flag",
            unavail["bea_v0_acquisition_performed"] is False,
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
            "unavailable_private_score_records_written_false_default",
            unavail["private_score_records_written"] is False,
        )
    )
    checks.append(
        _check(
            "unavailable_private_score_path_not_serialized",
            unavail["private_score_path_publicly_serialized"] is False
            and "private_score_path" not in unavail
            and "score_path" not in unavail,
        )
    )
    checks.append(
        _check(
            "unavailable_forbidden_scan_pass",
            unavail["forbidden_scan"]["status"] == "pass",
        )
    )

    # --- Group 18: Scanner rejects forbidden content. ---
    # BEA-0-specific forbidden keys.
    for forbidden_key in BEA0_FORBIDDEN_EXTRA_KEYS:
        checks.append(
            _check(
                f"scanner_rejects_{forbidden_key}_key",
                bool(_scan_bea0({forbidden_key: "value"})),
            )
        )
    # Value patterns (reuse c5d scanner primitives).
    checks.append(
        _check(
            "scanner_rejects_repo_url_value",
            bool(_scan_bea0({"leaked": "https://github.com/foo/bar"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_repo_slug_value",
            bool(_scan_bea0({"leaked": "psf/black"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_commit_sha_value",
            bool(
                _scan_bea0(
                    {"leaked": "f03ee113c9f3dfeb477f2d4247bfb7de2e5f465c"}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_file_path_value",
            bool(_scan_bea0({"leaked": "src/black/trans.py"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_tmp_path_value",
            bool(_scan_bea0({"leaked": "/tmp/foo"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_multiline_value",
            bool(_scan_bea0({"leaked": "line1\nline2"})),
        )
    )

    # --- Group 19: Scanner allows safe values. ---
    checks.append(
        _check(
            "scanner_allows_schema_version",
            not _scan_bea0({"schema_version": SCHEMA_VERSION}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_methods_value",
            not _scan_bea0({"methods": ["bm25", "regex", "symbol"]}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_budget_value",
            not _scan_bea0({"budget": 10}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_arm_metric_records",
            not _scan_bea0(
                {
                    "arm_metric_records": [
                        {
                            "arm": BASELINE_BM25_TOP10,
                            "metric": "mrr",
                            "value": 0.5,
                        }
                    ]
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_delta_records",
            not _scan_bea0(
                {
                    "delta_records": [
                        {
                            "baseline_arm": BASELINE_BM25_TOP10,
                            "treatment_arm": TREATMENT,
                            "metric": "mrr",
                            "delta": 0.1,
                        }
                    ]
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_private_score_manifest_hash",
            not _scan_bea0(
                {
                    "private_score_manifest_hash": "a" * 64,
                    "private_score_storage_class": "tmp_private",
                    "private_score_schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_failure_category_count",
            not _scan_bea0(
                {
                    "failure_category_counts": {
                        "retrieval_failed": 1,
                        "unexpected_exception": 0,
                    }
                }
            ),
        )
    )

    # --- Group 20: Fail-closed generation. ---
    try:
        _enforce_bea0_no_forbidden(skeleton)
        checks.append(_check("fail_closed_clean_report_no_raise", True))
    except SystemExit:
        checks.append(_check("fail_closed_clean_report_no_raise", False))

    leaked_report = dict(skeleton)
    leaked_report["private_score_path"] = "/tmp/leaked.jsonl"
    try:
        _enforce_bea0_no_forbidden(leaked_report)
        checks.append(_check("fail_closed_private_score_path_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_private_score_path_raises", True))

    leaked_report2 = dict(skeleton)
    leaked_report2["action_trace"] = [{"action": "accept_candidate"}]
    try:
        _enforce_bea0_no_forbidden(leaked_report2)
        checks.append(_check("fail_closed_action_trace_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_action_trace_raises", True))

    leaked_report3 = dict(skeleton)
    leaked_report3["accepted_candidates"] = [{"path": "src/foo.py"}]
    try:
        _enforce_bea0_no_forbidden(leaked_report3)
        checks.append(_check("fail_closed_accepted_candidates_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_accepted_candidates_raises", True))

    leaked_report4 = dict(skeleton)
    leaked_report4["winner"] = "bea_v0_budgeted"
    try:
        _enforce_bea0_no_forbidden(leaked_report4)
        checks.append(_check("fail_closed_winner_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_winner_raises", True))

    leaked_report5 = dict(skeleton)
    leaked_report5["best_method"] = "bm25"
    try:
        _enforce_bea0_no_forbidden(leaked_report5)
        checks.append(_check("fail_closed_best_method_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_best_method_raises", True))

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

    # --- Group 21: Public artifact self-scan is clean. ---
    checks.append(
        _check(
            "public_artifact_self_scan_clean",
            not _scan_bea0(skeleton),
        )
    )
    checks.append(
        _check(
            "unavailable_self_scan_clean",
            not _scan_bea0(unavail),
        )
    )

    # --- Group 22: CLI argument surface. ---
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
    ):
        checks.append(
            _check(
                f"cli_has_option_{required_opt}",
                required_opt in option_strings,
            )
        )

    # --- Group 23: Private SCORE writer round-trip (transient /tmp). ---
    with tempfile.TemporaryDirectory(
        prefix="bea0_selftest_score_"
    ) as score_dir_str:
        score_dir = Path(score_dir_str)
        score_file = score_dir / "bea0.private.jsonl"
        row = {
            "phase_run_id": "bea0-selftest",
            "benchmark": "synthetic",
            "private_record_id": "synthetic-001",
            "runtime_query_feature_summary": {"benchmark": "synthetic"},
            "candidate_list": [],
            "action_trace": [],
            "budget_states": [],
            "accepted_candidates": [],
            "final_candidates": [],
            "score_outcome": {},
            "latency_ms": 1,
            "cost_usd": 0.0,
            "tokens": 0,
            "provider_calls": 0,
            "failure_reason": None,
        }
        _write_private_score_row(score_file, row)
        _write_private_score_row(score_file, row)
        # Read back.
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
        # The private score file path is NEVER serialized in the public
        # artifact. Verify by scanning a fake report that tries to leak it.
        leaked_path_report = dict(skeleton)
        leaked_path_report["private_score_path"] = str(score_file)
        checks.append(
            _check(
                "private_score_path_leak_detected_by_scanner",
                bool(_scan_bea0(leaked_path_report)),
            )
        )

    # --- Group 24: Arm metric allowlist subset. ---
    for k in ARM_METRIC_ALLOWLIST:
        checks.append(
            _check(
                f"arm_metric_allowlist_in_filtered_{k}",
                k in _filter_arm_metrics(dict(bm25_m)),
            )
        )

    # --- Group 25: Aggregate runtime seconds present. ---
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

    # --- Group 26: No winner/best_method/method_winner anywhere. ---
    for field in (
        "winner",
        "best_method",
        "recommended_default",
        "method_winner",
        "calibration",
    ):
        checks.append(
            _check(
                f"clean_report_missing_{field}",
                field not in skeleton,
            )
        )
    checks.append(
        _check(
            "clean_report_missing_legacy_arm_metrics",
            "arm_metrics" not in skeleton,
        )
    )
    checks.append(
        _check(
            "clean_report_missing_legacy_deltas",
            "deltas" not in skeleton,
        )
    )

    # Filter out None entries (from the conditional methods_requires_bm25
    # placeholder check above).
    checks = [c for c in checks if c is not None]
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
    """Build the BEA-0 CLI parser."""
    ap = SafeArgumentParser(
        description=(
            "BEA-0 Budgeted Evidence Acquisition v0 "
            "(public aggregate-only artifact; bounded ContextBench verified "
            "+ RepoQA Python samples; multi-method candidate collection "
            "(bm25/regex/symbol); deterministic budgeted acquisition policy "
            "with private per-record SCORE JSONL traces in /tmp; no "
            "provider calls; no raw repo/commit/path/span/candidate/action-"
            "trace/budget-state/accepted-candidates/score-outcome/private-"
            "score-path committed)."
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
            "evidence budget for the bea_v0_budgeted policy (default: "
            f"{BUDGET_DEFAULT}; hard cap {BUDGET_HARD_CAP})"
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
    """Run the real BEA-0 network smoke.

    For each benchmark arm (ContextBench + RepoQA):
      1. Fetch rows/needles (transient in-memory).
      2. For each record: clone repo, run multi-method retrieval, run
         baselines + treatment, compute per-arm metrics, write private SCORE
         row to /tmp.
      3. Aggregate per-arm metrics + deltas.
    """
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    network_calls = 0
    smoke_start = time.perf_counter()
    manifest_hash = _private_score_manifest_hash()
    score_file = private_score_dir / "bea0.private.jsonl"
    # Reset (in case the explicit dir already had a stale file).
    try:
        score_file.unlink()
    except OSError:
        pass

    per_record_arm_metrics: list[dict[str, Any]] = []
    records_evaluated = 0
    records_successful = 0
    records_failed = 0

    # --- ContextBench arm ---
    rows, cb_status, cb_nc, cb_fcc = c5a._fetch_contextbench_rows(
        contextbench_row_limit, "python"
    )
    network_calls += cb_nc
    for k, v in cb_fcc.items():
        if k in fcc:
            fcc[k] += v
    if cb_status == "unavailable" or not rows:
        # ContextBench unavailable; record failure but continue to RepoQA.
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

    cb_records_run = 0
    for idx, row in enumerate(cb_rows):
        records_evaluated += 1
        cb_records_run += 1
        # Parse gold_context (transient).
        gold_paths, gold_lines, gc_status = c5a._parse_gold_context(
            row.get("gold_context")
        )
        if gc_status != "pass":
            fcc["contextbench_gold_parse_failed"] += 1
            records_failed += 1
            continue
        # Sanitize query (transient).
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

        # Clone repo (transient /tmp).
        with tempfile.TemporaryDirectory(
            prefix=f"bea0_cb_repo_{idx}_"
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
            prefix=f"bea0_rq_repo_{idx}_"
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

    # --- Aggregate per-arm metrics + deltas ---
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
    arm_ids = [BASELINE_BM25_TOP10, TREATMENT]
    if enable_rrf_baseline:
        arm_ids.append(BASELINE_RRF_TOP10)
    for arm_id in arm_ids:
        per_arm_list = [
            rec[arm_id] for rec in per_record_arm_metrics if arm_id in rec
        ]
        arm_aggs[arm_id] = _arm_means(per_arm_list)

    # Deltas: treatment - bm25, treatment - rrf (if present), rrf - bm25 (if present).
    deltas: dict[str, dict[str, float]] = {}
    if TREATMENT in arm_aggs and BASELINE_BM25_TOP10 in arm_aggs:
        deltas[TREATMENT] = _arm_deltas(
            arm_aggs[TREATMENT], arm_aggs[BASELINE_BM25_TOP10]
        )
    if enable_rrf_baseline and BASELINE_RRF_TOP10 in arm_aggs:
        deltas[BASELINE_RRF_TOP10] = _arm_deltas(
            arm_aggs[BASELINE_RRF_TOP10], arm_aggs[BASELINE_BM25_TOP10]
        )

    # Count private SCORE rows actually written.
    private_score_count = 0
    try:
        if score_file.exists():
            private_score_count = sum(
                1 for _ in score_file.open("r", encoding="utf-8")
                if _.strip()
            )
    except OSError:
        private_score_count = 0

    private_score_written = private_score_count > 0
    if records_successful > 0 and private_score_count != records_successful:
        # Fail-closed: private SCORE record count must match evaluated
        # successful record count.
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
        deltas=deltas,
        private_score_records_written=private_score_written,
        private_score_record_count=private_score_count,
        private_score_storage_class=private_score_storage_class,
        private_score_manifest_hash=manifest_hash,
        aggregate_runtime_seconds=aggregate_runtime_seconds,
        failure_category_counts=fcc,
        enable_rrf_baseline=enable_rrf_baseline,
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
        _enforce_bea0_no_forbidden(report)
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
    phase_run_id = f"bea0-{int(time.time())}"

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
        _enforce_bea0_no_forbidden(report)
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
            "BEA-0 acquisition smoke. Run with --enable-external-benchmark-"
            "network to execute the real ContextBench + RepoQA acquisition."
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

    # Fail-closed: private SCORE record count must match records_successful
    # when network was enabled and at least one record succeeded.
    if (
        enable_network
        and report.get("records_successful", 0) > 0
        and report.get("private_score_record_count", 0)
        != report.get("records_successful", 0)
    ):
        report["status"] = "fail_schema_contract"

    # Fail-closed: forbidden scan.
    _enforce_bea0_no_forbidden(report)
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
        f"{report.get('private_score_record_count', 0)})"
    )


if __name__ == "__main__":
    main()
