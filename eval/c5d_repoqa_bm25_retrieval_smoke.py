#!/usr/bin/env python3
"""C5-D RepoQA BM25 Retrieval Performance Smoke (Public Aggregate-Only).

This module implements the **C5-D RepoQA bounded retrieval performance smoke**
over the EvalPlus RepoQA/SNF release asset
(``repoqa-2024-06-23.json.gz`` from ``evalplus/repoqa_release``). It is the
first RepoQA-shaped retrieval performance smoke in the OpenLocus research
track.

C5-D is explicitly **not** a benchmark result, **not** a leaderboard entry,
**not** a performance claim, **not** a promotion, **not** a default/policy
change, and **not** a runtime/retriever/pack/backend/EvidenceCore semantic
change. The committed artifact records only aggregate retrieval metrics
(``file_recall@10``, ``mrr``, ``span_f0.5@10``, ``success_rate``) computed
by ``eval/score.py`` over a bounded RepoQA Python needle subset, using
OpenLocus ``bm25`` retrieval (no provider/model calls).

Claim boundary (binding):

* Claim level: ``repoqa_retrieval_performance_smoke_only``.
* Status: ``repoqa_retrieval_smoke_pass`` | ``partial`` |
  ``unavailable_asset_download_failed`` |
  ``unavailable_no_python_needles`` |
  ``unavailable_repo_clone_failed`` | ``fail_forbidden_scan`` |
  ``fail_schema_contract``.
* Mode: ``repoqa_bounded_bm25_retrieval_smoke``; phase ``C5-D``.
* This is **eval/diagnostic only**. It is NOT a benchmark result, NOT a
  leaderboard entry, NOT a performance claim, NOT a promotion, NOT a
  default change, NOT a runtime/retriever/pack/backend change, NOT an
  EvidenceCore semantic change, and NOT a downstream agent value claim.

Privacy / license boundary (binding):

* The ``repoqa-2024-06-23.json.gz`` release asset is downloaded to
  ``/tmp`` only and decompressed in memory. The asset and expanded JSON
  are NEVER committed or uploaded.
* Raw repo records, repo names/URLs, commit SHAs, entrypoint paths,
  topics, content, dependency, needle names/descriptions/paths/start/
  end lines, generated task/label/run JSONL, evidence rows, cloned
  repos, and stdout/stderr are kept **transient only** under ``/tmp`` or
  CI ephemeral workspace. They are NEVER committed or uploaded.
* Aggregate metric values from ``eval/score.py`` are safe to publish if
  aggregate only. No row-level records, no needle IDs, no paths, no
  spans, no snippets, no content_sha, no stdout/stderr.
* RepoQA dataset license is unknown
  (``unknown_dataset_license``); row-level redistribution is disabled
  (``row_level_redistribution_allowed=false``) and derived row-level
  publication is disabled
  (``derived_row_level_publication_allowed=false``). Aggregate metrics
  publication is allowed as aggregate-only smoke
  (``aggregate_metrics_publication=aggregate_only_smoke``).

Network / CI policy (binding):

* Default no-network self-test passes without GitHub/network.
* Real smoke requires public network access to GitHub (asset download +
  repo clones). CI must be a separate explicit ``workflow_dispatch``
  job with ``enable_external_benchmark_network=true``. It must NOT run
  on PR/push by default, must use no provider secrets/vars, no
  ``OPENLOCUS_LLM``/``OPENLOCUS_EMBEDDING`` env, and must upload only
  the aggregate report.

Run::

    python3 -m py_compile eval/c5d_repoqa_bm25_retrieval_smoke.py
    python3 eval/c5d_repoqa_bm25_retrieval_smoke.py --self-test
    python3 eval/c5d_repoqa_bm25_retrieval_smoke.py \\
        --needle-limit 5 --language-filter python --method bm25 \\
        --out artifacts/c5d_repoqa_bm25_retrieval_smoke/\\
c5d_repoqa_bm25_retrieval_smoke_report.json

If the network smoke cannot complete in the environment, the default
artifact records truthful ``unavailable_*`` with a real failure category
(no stale/fake pass). Self-test/docs/diff-check still pass.
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# Reuse C5-A helpers (query sanitizer, clone/retrieval/score runner,
# score metric allowlist, scanner primitives, JSON helpers).
# The ``eval`` directory has no ``__init__.py`` (it is a flat script
# directory), so we add this file's parent to ``sys.path`` and import
# the C5-A module directly. C5-D does NOT import or mutate C5-C; it
# only reuses C5-A primitives.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants (C5-D owned)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "c5d_repoqa_retrieval_performance_smoke.v1"
GENERATED_BY = "eval/c5d_repoqa_bm25_retrieval_smoke.py"
CLAIM_LEVEL = "repoqa_retrieval_performance_smoke_only"
MODE = "repoqa_bounded_bm25_retrieval_smoke"
PHASE = "C5-D"

DEFAULT_OUT = Path(
    "artifacts/c5d_repoqa_bm25_retrieval_smoke/"
    "c5d_repoqa_bm25_retrieval_smoke_report.json"
)

# Hard caps on needle limit. Default 5; max 10.
NEEDLE_LIMIT_DEFAULT = 5
NEEDLE_LIMIT_HARD_CAP = 10

# Methods supported by C5-D: bm25 only (per the C5-D oracle contract).
ALLOWED_METHODS: tuple[str, ...] = ("bm25",)
DEFAULT_METHOD = "bm25"

# Language filter: python only for committed/default artifact. C5-D does
# NOT silently fall back from python to all languages.
ALLOWED_LANGUAGE_FILTERS: tuple[str, ...] = ("python",)
DEFAULT_LANGUAGE_FILTER = "python"

# Query mode is fixed for C5-D: needle.description is the query.
QUERY_MODE = "needle_description"
GOLD_TARGET_MODE = "needle_path_line_range"

# RepoQA release asset (source-level public URL, not row-level data).
RELEASE_TAG = "2024-06-23"
ASSET_NAME = f"repoqa-{RELEASE_TAG}.json.gz"
ASSET_URL = (
    f"https://github.com/evalplus/repoqa_release/releases/download/"
    f"{RELEASE_TAG}/{ASSET_NAME}"
)
# RepoQA dataset is a monolithic source-containing JSON.gz from the
# evalplus/repoqa_release GitHub release repo (Apache-2.0 code repo).
# The dataset-level license is not explicitly declared; treat as unknown.
DATASET_RELEASE = f"repoqa-{RELEASE_TAG}"
BENCHMARK = "repoqa"

# Bounded timeouts for external operations.
ASSET_DOWNLOAD_TIMEOUT_SECONDS = 120
CLONE_TIMEOUT_SECONDS = 300
CHECKOUT_TIMEOUT_SECONDS = 90
RETRIEVAL_TIMEOUT_SECONDS = 90
SCORE_TIMEOUT_SECONDS = 60

# ---------------------------------------------------------------------------
# Safe booleans true (only when actually true). Exactly these MAY be true
# in the committed public artifact.
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "repoqa_retrieval_smoke_performed": False,
    "asset_downloaded_transiently": False,
    "repoqa_needles_parsed_in_memory": False,
    "repositories_materialized_transiently": False,
    "openlocus_retrieval_executed": False,
    "score_py_metrics_computed": False,
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
}

# ---------------------------------------------------------------------------
# No-claim / no-runtime-change flags (all MUST be false in the committed
# public artifact). C5-D runs NO provider, makes NO remote provider calls,
# proves NO downstream agent value, promotes NO candidate, changes NO
# runtime/retriever/pack/backend/default-policy/EvidenceCore semantics,
# claims NO external benchmark performance, and emits NO leaderboard entry.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "external_benchmark_performance_claimed": False,
    "leaderboard_entry_claimed": False,
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
# Fixed failure-category enum for the smoke. Only these category labels
# may appear in the public artifact; never row-level values.
# ---------------------------------------------------------------------------

FAILURE_CATEGORIES: tuple[str, ...] = (
    "asset_download_failed",
    "asset_decompress_failed",
    "asset_parse_failed",
    "no_python_needles",
    "needle_parse_failed",
    "language_filter_excluded",
    "repo_clone_failed",
    "repo_checkout_failed",
    "task_jsonl_write_failed",
    "label_jsonl_write_failed",
    "retrieval_failed",
    "score_failed",
    "needle_limit_capped",
    "scanner_self_test_failed",
    "forbidden_leak_blocked",
    "unexpected_exception",
)

# ---------------------------------------------------------------------------
# Metric allowlist: only these aggregate metric names from ``score.py``
# may appear in the public artifact. No dynamic row IDs or paths.
# ---------------------------------------------------------------------------

SCORE_METRIC_ALLOWLIST: tuple[str, ...] = (
    "file_recall@10",
    "mrr",
    "span_f0.5@10",
    "success_rate",
)

# ---------------------------------------------------------------------------
# Public artifact scanner (C5-D owned, strict, fail-closed).
#
# C5-D reuses the C5-A forbidden scanner primitives for raw key/value
# leak detection, and ADDS a C5-D-specific scanner that:
#   * rejects RepoQA-specific forbidden keys (repo, commit_sha,
#     entrypoint_path, topic, content, dependency, needles, needle_name,
#     needle_path, needle_description, start_line, end_line, start_byte,
#     end_byte, etc.);
#   * rejects recommendation / policy fields anywhere;
#   * rejects row/repo/query/gold/path/span/snippet/content_sha/stdout/
#     stderr keys anywhere.
# ---------------------------------------------------------------------------


# C5-D-specific forbidden keys (in addition to c5a.FORBIDDEN_KEY_NAMES).
C5D_FORBIDDEN_EXTRA_KEYS: frozenset[str] = frozenset(
    {
        # RepoQA repo-record fields
        "repo",
        "commit_sha",
        "commit",
        "entrypoint_path",
        "topic",
        "content",
        "dependency",
        "functions",
        "needles",
        # RepoQA needle fields
        "needle",
        "needle_name",
        "needle_path",
        "needle_description",
        "needle_id",
        "name",
        "start_line",
        "end_line",
        "start_byte",
        "end_byte",
        "global_start_line",
        "global_end_line",
        "global_start_byte",
        "global_end_byte",
        "code_ratio",
        "path",
        "description",
        # row/identifier fields
        "row",
        "rows_data",
        "raw_row",
        "raw_rows",
        "repo_name",
        "repo_slug",
        "repo_url",
        "base_commit",
        "instance_id",
        "task_id",
        "original_inst_id",
        # gold fields
        "gold",
        "gold_path",
        "gold_span",
        "gold_snippet",
        "gold_paths",
        "gold_lines",
        "gold_context",
        # query fields
        "query",
        "query_text",
        "problem_statement",
        # evidence / retrieval fields
        "snippet",
        "snippets",
        "content_sha",
        "content_hash",
        "stdout",
        "stderr",
        "stdout_text",
        "stderr_text",
        "evidence",
        "evidence_row",
        "evidence_rows",
        "retrieved_path",
        "retrieved_paths",
        "retrieved_snippet",
        "cloned_repo_path",
        "cloned_repo",
        "per_row_metrics",
        "row_metrics",
        "per_needle_metrics",
        "needle_metrics",
        # patch / diff fields
        "patch",
        "diff",
        # recommendation fields (also in FORBIDDEN_RECOMMENDATION_FIELDS)
        "winner",
        "best_method",
        "recommended_default",
    }
)


# Recommendation / policy field names that must NEVER be emitted by C5-D
# (anywhere in the public artifact).
FORBIDDEN_RECOMMENDATION_FIELDS: frozenset[str] = frozenset(
    {
        "winner",
        "best_method",
        "recommended_default",
        "recommended_method",
        "preferred_method",
        "default_method",
        "policy_decision",
        "decision",
        "ranking",
        "rank",
    }
)


# C5-D schema-key container keys (children are fixed labels, not row
# values). Extends C5-A's set with the C5-D-specific containers.
C5D_SCHEMA_KEY_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "failure_category_counts",
        "aggregate_metrics",
    }
)


# C5-D-specific safe VALUE path last-key segments. These are list/dict
# fields whose VALUES are categorical bucket strings (e.g. ``"python"``,
# ``"bm25"``). The C5-A scanner may flag some of these as
# ``forbidden_field_name_value`` (e.g. ``"content"`` is a forbidden
# content/key name in C5-A's contract). In C5-D, the allowed method is
# only ``bm25`` (never ``content``), so no false-positive suppression is
# strictly needed, but the filter is kept for symmetry and
# future-proofing.
C5D_SAFE_VALUE_PATH_LAST_KEYS: frozenset[str] = frozenset(
    {
        "benchmark",
        "dataset_release",
        "language_filter",
        "method",
        "query_mode",
        "gold_target_mode",
        "network_mode",
        "openlocus_binary_source",
        "schema_version",
        "generated_by",
        "generated_at",
        "claim_level",
        "status",
        "mode",
        "phase",
        "failure_reason_category",
        "dataset_license_status",
        "aggregate_metrics_publication",
        "citation_validation_mode",
    }
)


def _is_c5d_schema_key_container(path: str) -> bool:
    """Check if the parent of the current key is a C5-D schema-key container."""
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in C5D_SCHEMA_KEY_CONTAINER_KEYS


def _c5d_safe_value_path(path: str) -> bool:
    """Check if a JSON path is a C5-D-specific safe value path."""
    last = path.rsplit(".", 1)[-1]
    last_key = last.split("[")[0]
    return last_key in C5D_SAFE_VALUE_PATH_LAST_KEYS


def _scan_c5d_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    """Scan for C5-D-specific forbidden keys (recommendation + extra row keys)."""
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                is_schema_container = _is_c5d_schema_key_container(sub_path)
                if key_str in FORBIDDEN_RECOMMENDATION_FIELDS:
                    violations.append(
                        {
                            "category": "forbidden_recommendation_field",
                            "path": sub_path,
                        }
                    )
                if (
                    key_str in C5D_FORBIDDEN_EXTRA_KEYS
                    and not is_schema_container
                ):
                    violations.append(
                        {
                            "category": "forbidden_c5d_extra_key",
                            "path": sub_path,
                        }
                    )
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


def _scan_c5d(obj: Any) -> list[dict[str, Any]]:
    """Combined C5-D scanner: C5-A primitives + C5-D-specific checks.

    The C5-A scanner is reused for raw key/value leak detection (URLs,
    hex digests, repo slugs, /tmp paths, etc.). C5-D ADDS:
      * rejection of RepoQA-specific forbidden keys anywhere;
      * rejection of recommendation / policy fields anywhere;
      * rejection of extra row/repo/query/gold/path/span/snippet/
        content_sha/stdout/stderr keys anywhere.
    The C5-D scanner also filters out false positives from the C5-A
    scanner where a legitimate categorical bucket string appears as a
    value under a C5-D-specific safe value path.
    """
    violations: list[dict[str, Any]] = []
    for v in c5a._scan_forbidden(obj):
        if v.get("category") == "forbidden_field_name_value" and _c5d_safe_value_path(
            v.get("path", "")
        ):
            continue
        violations.append(v)
    violations.extend(_scan_c5d_forbidden_keys(obj))
    return violations


def _c5d_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    """Run the C5-D forbidden scanner and return a sanitized summary."""
    violations = _scan_c5d(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_c5d_no_forbidden(obj: Any) -> None:
    """Fail-closed guard: raise SystemExit if any forbidden content leaks."""
    scan = _c5d_forbidden_scan_summary(obj)
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


def _validate_needle_limit(needle_limit: int) -> int:
    """Validate and cap --needle-limit to the C5-D hard cap (10)."""
    if not isinstance(needle_limit, int):
        raise SystemExit("invalid arguments")
    if needle_limit < 1:
        raise SystemExit("invalid arguments")
    if needle_limit > NEEDLE_LIMIT_HARD_CAP:
        return NEEDLE_LIMIT_HARD_CAP
    return needle_limit


# ---------------------------------------------------------------------------
# Asset download + decompress (transient /tmp only; never committed).
# ---------------------------------------------------------------------------


def _download_asset_to_bytes(
    asset_url: str, timeout: int = ASSET_DOWNLOAD_TIMEOUT_SECONDS
) -> tuple[bytes | None, str, dict[str, int]]:
    """Download the RepoQA release asset to in-memory bytes (transient).

    Returns ``(bytes_or_None, status, failure_counts)``. The asset bytes
    are kept in memory only; they are NEVER written to the workspace or
    committed. On failure, returns ``(None, "asset_download_failed",
    failure_counts)``.
    """
    failure_counts: dict[str, int] = {c: 0 for c in FAILURE_CATEGORIES}
    try:
        req = urllib.request.Request(
            asset_url,
            headers={
                "Accept": "application/octet-stream",
                "User-Agent": "OpenLocus-C5D-repoqa-smoke/0.1 (bounded; stdlib)",
            },
        )
        with urllib.request.urlopen(  # noqa: S310 - bounded smoke
            req, timeout=timeout
        ) as resp:
            body = resp.read()
        if not body:
            failure_counts["asset_download_failed"] += 1
            return None, "asset_download_failed", failure_counts
        return body, "pass", failure_counts
    except urllib.error.HTTPError:
        failure_counts["asset_download_failed"] += 1
        return None, "asset_download_failed", failure_counts
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
        failure_counts["asset_download_failed"] += 1
        return None, "asset_download_failed", failure_counts


def _decompress_asset(asset_bytes: bytes) -> tuple[Any, str, dict[str, int]]:
    """Decompress the ``.json.gz`` asset bytes in memory (transient).

    Returns ``(parsed_json_or_None, status, failure_counts)``. The
    decompressed JSON is parsed in memory only; it is NEVER written to
    the workspace or committed.
    """
    failure_counts: dict[str, int] = {c: 0 for c in FAILURE_CATEGORIES}
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(asset_bytes)) as gz:
            decompressed = gz.read()
    except (OSError, EOFError, gzip.BadGzipFile):
        failure_counts["asset_decompress_failed"] += 1
        return None, "asset_decompress_failed", failure_counts
    try:
        parsed = json.loads(decompressed.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        failure_counts["asset_parse_failed"] += 1
        return None, "asset_parse_failed", failure_counts
    if not isinstance(parsed, dict):
        failure_counts["asset_parse_failed"] += 1
        return None, "asset_parse_failed", failure_counts
    return parsed, "pass", failure_counts


# ---------------------------------------------------------------------------
# RepoQA needle parser (in-memory only; never emits raw values to public).
# ---------------------------------------------------------------------------


class NeedleParseError(ValueError):
    """Raised when a RepoQA needle cannot be parsed (invalid fields)."""


def _parse_repoqa_needles(
    parsed: Any, language_filter: str, needle_limit: int
) -> tuple[list[dict[str, Any]], str, dict[str, int]]:
    """Parse RepoQA needles from the in-memory parsed asset.

    Returns ``(needles, status, failure_counts)``. Each needle is a
    transient in-memory dict with the minimum fields needed to drive
    retrieval + scoring:

    * ``repo_url``: ``https://github.com/<repo>.git`` (transient; never
      written to public artifact).
    * ``commit_sha``: repo commit to checkout (transient).
    * ``needle_path``: gold path for ``eval/score.py`` (transient).
    * ``needle_start_line`` / ``needle_end_line``: gold line range
      (transient).
    * ``needle_description``: retrieval query (transient; sanitized
      in-memory only).

    Needles are filtered by ``language_filter`` (categorical bucket
    only; ``python`` default). C5-D does NOT silently fall back from
    python to all languages: if ``language_filter=python`` and zero
    python needles are found, status is
    ``unavailable_no_python_needles``.
    """
    failure_counts: dict[str, int] = {c: 0 for c in FAILURE_CATEGORIES}
    needles: list[dict[str, Any]] = []

    if not isinstance(parsed, dict):
        failure_counts["asset_parse_failed"] += 1
        return needles, "asset_parse_failed", failure_counts

    # Language filter: only ``python`` is supported in C5-D. Do NOT
    # silently fall back to all languages.
    lang_data = parsed.get(language_filter)
    if not isinstance(lang_data, list):
        failure_counts["no_python_needles"] += 1
        return needles, "unavailable_no_python_needles", failure_counts

    for repo_record in lang_data:
        if not isinstance(repo_record, dict):
            failure_counts["needle_parse_failed"] += 1
            continue
        repo_slug = repo_record.get("repo")
        commit_sha = repo_record.get("commit_sha")
        if not isinstance(repo_slug, str) or not repo_slug:
            failure_counts["needle_parse_failed"] += 1
            continue
        if not isinstance(commit_sha, str) or not commit_sha:
            failure_counts["needle_parse_failed"] += 1
            continue
        # Build the clone URL (transient; never written to public).
        repo_url = f"https://github.com/{repo_slug}.git"
        needle_list = repo_record.get("needles")
        if not isinstance(needle_list, list):
            failure_counts["needle_parse_failed"] += 1
            continue
        for needle in needle_list:
            if not isinstance(needle, dict):
                failure_counts["needle_parse_failed"] += 1
                continue
            needle_path = needle.get("path")
            start_line = needle.get("start_line")
            end_line = needle.get("end_line")
            description = needle.get("description")
            if not isinstance(needle_path, str) or not needle_path:
                failure_counts["needle_parse_failed"] += 1
                continue
            if not isinstance(start_line, int) or not isinstance(
                end_line, int
            ):
                failure_counts["needle_parse_failed"] += 1
                continue
            if start_line < 1 or end_line < 1 or start_line > end_line:
                failure_counts["needle_parse_failed"] += 1
                continue
            if not isinstance(description, str) or not description.strip():
                failure_counts["needle_parse_failed"] += 1
                continue
            needles.append(
                {
                    "repo_url": repo_url,
                    "commit_sha": commit_sha,
                    "needle_path": needle_path,
                    "needle_start_line": start_line,
                    "needle_end_line": end_line,
                    "needle_description": description,
                }
            )
            if len(needles) >= needle_limit:
                break
        if len(needles) >= needle_limit:
            break

    if not needles:
        failure_counts["no_python_needles"] += 1
        return needles, "unavailable_no_python_needles", failure_counts

    if len(needles) > needle_limit:
        needles = needles[:needle_limit]
        failure_counts["needle_limit_capped"] += 1

    return needles, "pass", failure_counts


# ---------------------------------------------------------------------------
# Query sanitizer for RepoQA needle descriptions (in-memory only).
# ---------------------------------------------------------------------------


def _sanitize_needle_description(description: str) -> str:
    """Sanitize a RepoQA needle description into a retrieval query.

    RepoQA needle descriptions are markdown-formatted multi-line strings
    with numbered sections (Purpose, Input, Output, etc.). For BM25
    retrieval, we extract the ``Purpose`` section's first sentence as a
    concise query. Falls back to the first non-empty line if no Purpose
    section is found.

    The query is NEVER written to the public artifact. It is used only
    to drive ``run_retrieval.py`` under a transient ``/tmp`` workspace.
    """
    if not isinstance(description, str):
        return ""
    text = description
    # Strip markdown headers and bold/italic markers.
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    # Try to find the "Purpose" section.
    purpose_match = re.search(
        r"(?:^|\n)\s*\*?\*?Purpose\*?\*?\s*[:：]?\s*(.+?)(?:\n\s*\n|\n\s*\d+\.|\Z)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if purpose_match:
        purpose = purpose_match.group(1).strip()
        # Take the first sentence.
        sentences = re.split(r"(?<=[.!?])\s+", purpose)
        if sentences and sentences[0]:
            return sentences[0][:300]
    # Fallback: first non-empty, non-numbered line.
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Skip numbered list markers like "1." or "2.".
        if re.match(r"^\d+\.\s*", line):
            line = re.sub(r"^\d+\.\s*", "", line)
            if line:
                return line[:300]
        else:
            return line[:300]
    return text[:300]


# ---------------------------------------------------------------------------
# Transient task/label JSONL writers (under TemporaryDirectory only).
# ---------------------------------------------------------------------------


def _write_transient_jsonl(
    path: Path, records: list[dict[str, Any]]
) -> None:
    c5a._write_transient_jsonl(path, records)


# ---------------------------------------------------------------------------
# Retrieval + scoring (subprocess; transient JSONL only). Reuses C5-A
# primitives but with C5-D metric allowlist.
# ---------------------------------------------------------------------------


def _filter_score_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Filter score.py metrics to the C5-D metric allowlist only."""
    filtered: dict[str, Any] = {}
    for key in SCORE_METRIC_ALLOWLIST:
        if key in metrics:
            val = metrics[key]
            if isinstance(val, bool):
                filtered[key] = bool(val)
            elif isinstance(val, (int, float)):
                if isinstance(val, float):
                    filtered[key] = round(val, 6)
                else:
                    filtered[key] = int(val)
    return filtered


def _compute_aggregate_metrics(
    per_needle_metrics: list[dict[str, Any]],
    needles_successful: int,
) -> dict[str, Any]:
    """Compute aggregate metrics from per-needle score.py outputs.

    Only ``SCORE_METRIC_ALLOWLIST`` keys are emitted. Numeric metrics
    are averaged as means; ``success_rate`` is recomputed as
    ``needles_successful / needles_evaluated``.
    """
    aggregate: dict[str, Any] = {}
    if not per_needle_metrics or needles_successful <= 0:
        return aggregate
    for key in SCORE_METRIC_ALLOWLIST:
        values: list[Any] = []
        for rec in per_needle_metrics:
            if key in rec:
                values.append(rec[key])
        if not values:
            continue
        if all(isinstance(v, bool) for v in values):
            aggregate[key] = any(values)
        elif all(isinstance(v, (int, float)) for v in values):
            nums = [float(v) for v in values]
            mean = sum(nums) / len(nums)
            aggregate[key] = round(mean, 6)
    aggregate["success_rate"] = (
        round(needles_successful / len(per_needle_metrics), 6)
        if per_needle_metrics
        else 0.0
    )
    return _filter_score_metrics(aggregate)


def _run_retrieval_and_score(
    tasks_jsonl: Path,
    labels_jsonl: Path,
    run_jsonl: Path,
    repo_root: Path,
    openlocus_bin: str,
    method: str,
    eval_dir: Path,
) -> tuple[dict[str, Any] | None, str, dict[str, int]]:
    """Run OpenLocus retrieval via ``eval/run_retrieval.py`` then score.

    Returns ``(metrics, failure_category, failure_counts)``.
    ``metrics`` is the parsed JSON from ``eval/score.py`` (aggregate
    only) or ``None`` on failure.
    """
    failure_counts: dict[str, int] = {c: 0 for c in FAILURE_CATEGORIES}

    run_retrieval_py = eval_dir / "run_retrieval.py"
    score_py = eval_dir / "score.py"

    run_cmd = [
        sys.executable, str(run_retrieval_py),
        "--dataset", str(tasks_jsonl),
        "--out", str(run_jsonl),
        "--openlocus", openlocus_bin,
        "--cwd", str(repo_root),
        "--method", method,
    ]
    try:
        proc = subprocess.run(
            run_cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=RETRIEVAL_TIMEOUT_SECONDS,
        )
        if proc.returncode != 0:
            failure_counts["retrieval_failed"] += 1
            return None, "retrieval_failed", failure_counts
    except subprocess.TimeoutExpired:
        failure_counts["retrieval_failed"] += 1
        return None, "retrieval_failed", failure_counts
    except (OSError, subprocess.SubprocessError):
        failure_counts["retrieval_failed"] += 1
        return None, "retrieval_failed", failure_counts

    score_cmd = [
        sys.executable, str(score_py),
        "--pred", str(run_jsonl),
        "--dataset", str(labels_jsonl),
        "--repo-root", str(repo_root),
    ]
    try:
        proc = subprocess.run(
            score_cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=SCORE_TIMEOUT_SECONDS,
        )
        if proc.returncode != 0:
            failure_counts["score_failed"] += 1
            return None, "score_failed", failure_counts
        try:
            metrics = json.loads(proc.stdout)
        except (json.JSONDecodeError, UnicodeDecodeError):
            failure_counts["score_failed"] += 1
            return None, "score_failed", failure_counts
        if not isinstance(metrics, dict):
            failure_counts["score_failed"] += 1
            return None, "score_failed", failure_counts
        return metrics, "pass", failure_counts
    except subprocess.TimeoutExpired:
        failure_counts["score_failed"] += 1
        return None, "score_failed", failure_counts
    except (OSError, subprocess.SubprocessError):
        failure_counts["score_failed"] += 1
        return None, "score_failed", failure_counts


# ---------------------------------------------------------------------------
# Repo materialization (clone + checkout under TemporaryDirectory only).
# Reuses C5-A ``_clone_and_checkout``.
# ---------------------------------------------------------------------------


def _clone_and_checkout(
    repo_url: str, base_commit: str, work_dir: Path
) -> tuple[bool, str, dict[str, int]]:
    """Clone ``repo_url`` at ``base_commit`` under ``work_dir`` (transient).

    Wraps ``c5a._clone_and_checkout`` and remaps C5-A failure categories
    (``clone_failed`` / ``checkout_failed``) to C5-D categories
    (``repo_clone_failed`` / ``repo_checkout_failed``).
    """
    failure_counts: dict[str, int] = {c: 0 for c in FAILURE_CATEGORIES}
    ok, fail_cat, c5a_fcc = c5a._clone_and_checkout(
        repo_url, base_commit, work_dir
    )
    if ok:
        return True, "pass", failure_counts
    if fail_cat == "clone_failed":
        failure_counts["repo_clone_failed"] += 1
    elif fail_cat == "checkout_failed":
        failure_counts["repo_checkout_failed"] += 1
    else:
        failure_counts["repo_clone_failed"] += 1
    return False, fail_cat, failure_counts


# ---------------------------------------------------------------------------
# Public report builders (fail-closed scan).
# ---------------------------------------------------------------------------


def _build_unavailable_report(
    failure_reason_category: str,
    *,
    self_test_passed: bool,
    needle_limit_requested: int,
    language_filter: str,
    method: str,
    openlocus_binary_source: str,
    network_mode: str,
    needles_seen: int = 0,
    network_calls: int = 0,
    failure_category_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build a truthful ``unavailable_*`` report."""
    # Map the failure reason to the appropriate status enum.
    status_map = {
        "asset_download_failed": "unavailable_asset_download_failed",
        "asset_decompress_failed": "unavailable_asset_download_failed",
        "asset_parse_failed": "unavailable_asset_download_failed",
        "no_python_needles": "unavailable_no_python_needles",
        "repo_clone_failed": "unavailable_repo_clone_failed",
        "repo_checkout_failed": "unavailable_repo_clone_failed",
        "retrieval_failed": "unavailable_repo_clone_failed",
        "unexpected_exception": "unavailable_repo_clone_failed",
    }
    status = status_map.get(
        failure_reason_category, "unavailable_repo_clone_failed"
    )

    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    if failure_category_counts:
        for k, v in failure_category_counts.items():
            if k in fcc:
                fcc[k] = int(v)
    if failure_reason_category in fcc:
        fcc[failure_reason_category] = max(fcc[failure_reason_category], 1)

    safe_true = dict(SAFE_TRUE_FLAGS)
    # In unavailable mode, only the flags that were actually true remain.
    # asset_downloaded_transiently is true only if the asset was downloaded
    # before the failure (needles_seen > 0 implies parse succeeded).
    safe_true["asset_downloaded_transiently"] = needles_seen > 0
    safe_true["repoqa_needles_parsed_in_memory"] = needles_seen > 0

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "benchmark": BENCHMARK,
        "dataset_release": DATASET_RELEASE,
        "language_filter": language_filter,
        "method": method,
        "query_mode": QUERY_MODE,
        "gold_target_mode": GOLD_TARGET_MODE,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "needle_limit_requested": needle_limit_requested,
        "needles_seen": needles_seen,
        "needles_evaluated": 0,
        "needles_successful": 0,
        "needles_failed": 0,
        "network_calls": network_calls,
        "provider_calls": 0,
        "aggregate_metrics": {},
        "aggregate_runtime_seconds": None,
        "failure_reason_category": failure_reason_category,
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
            "signal_strength": "repoqa_retrieval_smoke_unavailable",
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _c5d_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _build_pass_report(
    *,
    self_test_passed: bool,
    needle_limit_requested: int,
    needles_seen: int,
    needles_evaluated: int,
    needles_successful: int,
    needles_failed: int,
    language_filter: str,
    method: str,
    openlocus_binary_source: str,
    network_mode: str,
    network_calls: int,
    aggregate_metrics: dict[str, Any],
    aggregate_runtime_seconds: float,
    failure_category_counts: dict[str, int],
) -> dict[str, Any]:
    """Build a pass/partial report with aggregate metrics."""
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    for k, v in failure_category_counts.items():
        if k in fcc:
            fcc[k] = int(v)

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["repoqa_retrieval_smoke_performed"] = needles_successful > 0
    safe_true["asset_downloaded_transiently"] = True
    safe_true["repoqa_needles_parsed_in_memory"] = needles_seen > 0
    safe_true["repositories_materialized_transiently"] = needles_successful > 0
    safe_true["openlocus_retrieval_executed"] = needles_successful > 0
    safe_true["score_py_metrics_computed"] = bool(aggregate_metrics)

    if needles_successful > 0 and needles_failed == 0:
        status = "repoqa_retrieval_smoke_pass"
    elif needles_successful > 0 and needles_failed > 0:
        status = "partial"
    else:
        # No needles succeeded; this is an unavailable status, not pass.
        status = "unavailable_repo_clone_failed"

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "benchmark": BENCHMARK,
        "dataset_release": DATASET_RELEASE,
        "language_filter": language_filter,
        "method": method,
        "query_mode": QUERY_MODE,
        "gold_target_mode": GOLD_TARGET_MODE,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "needle_limit_requested": needle_limit_requested,
        "needles_seen": needles_seen,
        "needles_evaluated": needles_evaluated,
        "needles_successful": needles_successful,
        "needles_failed": needles_failed,
        "network_calls": network_calls,
        "provider_calls": 0,
        "aggregate_metrics": _filter_score_metrics(aggregate_metrics),
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
            "signal_strength": "repoqa_retrieval_smoke_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _c5d_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


# ---------------------------------------------------------------------------
# Network smoke runner (transient /tmp workspace; aggregate-only output).
# ---------------------------------------------------------------------------


def _run_network_smoke(
    *,
    needle_limit: int,
    language_filter: str,
    method: str,
    openlocus_bin: str,
    openlocus_binary_source: str,
    network_mode: str,
    eval_dir: Path,
    self_test_passed: bool,
) -> dict[str, Any]:
    """Run the real RepoQA network smoke (transient /tmp; aggregate-only)."""
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    network_calls = 0
    smoke_start_time = time.perf_counter()

    # Step 1: download the release asset to in-memory bytes (transient).
    asset_bytes, dl_status, dl_fcc = _download_asset_to_bytes(ASSET_URL)
    network_calls += 1
    for k, v in dl_fcc.items():
        if k in fcc:
            fcc[k] += v
    if dl_status != "pass" or asset_bytes is None:
        return _build_unavailable_report(
            "asset_download_failed",
            self_test_passed=self_test_passed,
            needle_limit_requested=needle_limit,
            language_filter=language_filter,
            method=method,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            network_calls=network_calls,
            failure_category_counts=fcc,
        )

    # Step 2: decompress + parse in memory (transient).
    parsed, parse_status, parse_fcc = _decompress_asset(asset_bytes)
    # Immediately discard the raw bytes after decompression.
    del asset_bytes
    for k, v in parse_fcc.items():
        if k in fcc:
            fcc[k] += v
    if parse_status != "pass" or parsed is None:
        return _build_unavailable_report(
            parse_status if parse_status.startswith("unavailable") else "asset_parse_failed",
            self_test_passed=self_test_passed,
            needle_limit_requested=needle_limit,
            language_filter=language_filter,
            method=method,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            network_calls=network_calls,
            failure_category_counts=fcc,
        )

    # Step 3: parse needles in memory (transient).
    needles, needle_status, needle_fcc = _parse_repoqa_needles(
        parsed, language_filter, needle_limit
    )
    # Immediately discard the parsed asset after needle extraction.
    del parsed
    for k, v in needle_fcc.items():
        if k in fcc:
            fcc[k] += v
    if needle_status != "pass" or not needles:
        return _build_unavailable_report(
            needle_status if needle_status.startswith("unavailable") else "no_python_needles",
            self_test_passed=self_test_passed,
            needle_limit_requested=needle_limit,
            language_filter=language_filter,
            method=method,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            needles_seen=len(needles),
            network_calls=network_calls,
            failure_category_counts=fcc,
        )

    needles_seen = len(needles)
    needles_evaluated = 0
    needles_successful = 0
    needles_failed = 0
    per_needle_metrics: list[dict[str, Any]] = []

    # Step 4: for each needle, clone repo + run retrieval + score.
    with tempfile.TemporaryDirectory(
        prefix="c5d_repoqa_smoke_"
    ) as work_root_str:
        work_root = Path(work_root_str)
        tasks_jsonl = work_root / "tasks.jsonl"
        labels_jsonl = work_root / "labels.jsonl"
        run_jsonl = work_root / "run.jsonl"

        for idx, needle in enumerate(needles):
            needles_evaluated += 1
            # Sanitize the needle description into a retrieval query
            # (in-memory only; never written to public artifact).
            query = _sanitize_needle_description(
                needle.get("needle_description", "")
            )
            if not query:
                fcc["needle_parse_failed"] += 1
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
                fcc["needle_parse_failed"] += 1
                needles_failed += 1
                continue

            # Clone repo under a per-needle TemporaryDirectory.
            with tempfile.TemporaryDirectory(
                prefix=f"c5d_repo_{idx}_"
            ) as repo_root_str:
                repo_work_dir = Path(repo_root_str)
                clone_ok, clone_fail_cat, clone_fcc = (
                    _clone_and_checkout(
                        repo_url, commit_sha, repo_work_dir
                    )
                )
                for k, v in clone_fcc.items():
                    if k in fcc:
                        fcc[k] += v
                if not clone_ok:
                    needles_failed += 1
                    continue

                repo_root = repo_work_dir / "repo"

                # Write transient task/label JSONL for this single needle.
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
                    _write_transient_jsonl(
                        tasks_jsonl, [task_record]
                    )
                    _write_transient_jsonl(
                        labels_jsonl, [label_record]
                    )
                except OSError:
                    fcc["task_jsonl_write_failed"] += 1
                    needles_failed += 1
                    continue

                # Run retrieval + score.
                metrics, score_fail_cat, score_fcc = (
                    _run_retrieval_and_score(
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
                    needles_failed += 1
                    continue

                per_needle_metrics.append(metrics)
                needles_successful += 1

            try:
                run_jsonl.unlink()
            except OSError:
                pass

    aggregate_runtime_seconds = time.perf_counter() - smoke_start_time
    aggregate_metrics = _compute_aggregate_metrics(
        per_needle_metrics, needles_successful
    )

    if not per_needle_metrics:
        return _build_unavailable_report(
            "retrieval_failed",
            self_test_passed=self_test_passed,
            needle_limit_requested=needle_limit,
            language_filter=language_filter,
            method=method,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            needles_seen=needles_seen,
            network_calls=network_calls,
            failure_category_counts=fcc,
        )

    return _build_pass_report(
        self_test_passed=self_test_passed,
        needle_limit_requested=needle_limit,
        needles_seen=needles_seen,
        needles_evaluated=needles_evaluated,
        needles_successful=needles_successful,
        needles_failed=needles_failed,
        language_filter=language_filter,
        method=method,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        network_calls=network_calls,
        aggregate_metrics=aggregate_metrics,
        aggregate_runtime_seconds=aggregate_runtime_seconds,
        failure_category_counts=fcc,
    )


# ---------------------------------------------------------------------------
# Self-test (no network; synthetic gzip fixture + synthetic score data).
# ---------------------------------------------------------------------------


def _build_synthetic_repoqa_asset() -> bytes:
    """Build a synthetic RepoQA-like ``.json.gz`` asset for self-test.

    The values are deliberately synthetic placeholder strings. They are
    NEVER written to any public artifact; only the parsing/aggregation
    logic is validated.
    """
    synthetic = {
        "python": [
            {
                "repo": "synthetic/repo",
                "commit_sha": "0" * 40,
                "entrypoint_path": "src/synthetic",
                "topic": "synthetic topic",
                "content": "synthetic content placeholder",
                "dependency": "synthetic dependency",
                "functions": ["synthetic_function"],
                "needles": [
                    {
                        "name": "synthetic_needle",
                        "path": "src/synthetic.py",
                        "start_line": 10,
                        "end_line": 20,
                        "start_byte": 100,
                        "end_byte": 200,
                        "global_start_line": 10,
                        "global_end_line": 20,
                        "global_start_byte": 100,
                        "global_end_byte": 200,
                        "code_ratio": 0.1,
                        "description": (
                            "1. **Purpose**: To merge adjacent strings into "
                            "a single string within a line of code.\n"
                            "2. **Input**: A line of code and indices.\n"
                            "3. **Output**: A merged string.\n"
                        ),
                    }
                ],
            }
        ],
        "cpp": [],
        "java": [],
    }
    raw = json.dumps(synthetic).encode("utf-8")
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(raw)
    return buf.getvalue()


def _build_synthetic_metrics() -> dict[str, Any]:
    """Build synthetic score.py metrics for self-test (aggregate only)."""
    return {
        "file_recall@10": 1.0,
        "mrr": 1.0,
        "span_f0.5@10": 0.5,
        "success_rate": 1.0,
    }


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all C5-D self-test groups (no network; synthetic data)."""
    checks: list[dict[str, Any]] = []

    # --- Group 1: Artifact identity fields. ---
    skeleton = _build_pass_report(
        self_test_passed=True,
        needle_limit_requested=5,
        needles_seen=5,
        needles_evaluated=5,
        needles_successful=5,
        needles_failed=0,
        language_filter="python",
        method="bm25",
        openlocus_binary_source="default",
        network_mode="local_explicit",
        network_calls=1,
        aggregate_metrics=_filter_score_metrics(_build_synthetic_metrics()),
        aggregate_runtime_seconds=42.0,
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES},
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
            "benchmark_correct",
            skeleton["benchmark"] == BENCHMARK,
        )
    )
    checks.append(
        _check(
            "dataset_release_correct",
            skeleton["dataset_release"] == DATASET_RELEASE,
        )
    )
    checks.append(
        _check(
            "query_mode_correct",
            skeleton["query_mode"] == QUERY_MODE,
        )
    )
    checks.append(
        _check(
            "gold_target_mode_correct",
            skeleton["gold_target_mode"] == GOLD_TARGET_MODE,
        )
    )
    checks.append(
        _check(
            "status_pass_when_self_test_passed",
            skeleton["status"] == "repoqa_retrieval_smoke_pass",
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
            "safe_true_repoqa_retrieval_smoke_performed",
            skeleton.get("repoqa_retrieval_smoke_performed") is True,
        )
    )
    checks.append(
        _check(
            "safe_true_asset_downloaded_transiently",
            skeleton.get("asset_downloaded_transiently") is True,
        )
    )
    checks.append(
        _check(
            "safe_true_repoqa_needles_parsed_in_memory",
            skeleton.get("repoqa_needles_parsed_in_memory") is True,
        )
    )
    checks.append(
        _check(
            "safe_true_repositories_materialized_transiently",
            skeleton.get("repositories_materialized_transiently") is True,
        )
    )
    checks.append(
        _check(
            "safe_true_openlocus_retrieval_executed",
            skeleton.get("openlocus_retrieval_executed") is True,
        )
    )
    checks.append(
        _check(
            "safe_true_score_py_metrics_computed",
            skeleton.get("score_py_metrics_computed") is True,
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

    # --- Group 5: Needle limit hard cap 10. ---
    checks.append(
        _check(
            "needle_limit_default_5",
            NEEDLE_LIMIT_DEFAULT == 5,
        )
    )
    checks.append(
        _check(
            "needle_limit_hard_cap_10",
            NEEDLE_LIMIT_HARD_CAP == 10,
        )
    )
    checks.append(
        _check(
            "needle_limit_cap_enforced_at_10",
            _validate_needle_limit(100) == 10,
        )
    )
    checks.append(
        _check(
            "needle_limit_passes_through_at_5",
            _validate_needle_limit(5) == 5,
        )
    )
    try:
        _validate_needle_limit(0)
        checks.append(_check("needle_limit_rejects_zero", False))
    except SystemExit:
        checks.append(_check("needle_limit_rejects_zero", True))

    # --- Group 6: Method allowlist (bm25 only). ---
    checks.append(
        _check(
            "allowed_methods_exact_bm25_only",
            ALLOWED_METHODS == ("bm25",),
        )
    )
    checks.append(
        _check(
            "default_method_bm25",
            DEFAULT_METHOD == "bm25",
        )
    )

    # --- Group 7: Language filter (python only, no silent fallback). ---
    checks.append(
        _check(
            "allowed_language_filters_python_only",
            ALLOWED_LANGUAGE_FILTERS == ("python",),
        )
    )
    checks.append(
        _check(
            "default_language_filter_python",
            DEFAULT_LANGUAGE_FILTER == "python",
        )
    )
    # Verify no silent all-language fallback: parsing with python filter
    # on an asset with no python needles returns unavailable, NOT a
    # fallback to all languages.
    synthetic_no_python = {"cpp": [], "java": []}
    needles_no_py, status_no_py, _ = _parse_repoqa_needles(
        synthetic_no_python, "python", 5
    )
    checks.append(
        _check(
            "no_silent_python_to_all_fallback",
            status_no_py == "unavailable_no_python_needles"
            and needles_no_py == [],
        )
    )

    # --- Group 8: gzip JSON fixture parse in memory. ---
    synthetic_asset_bytes = _build_synthetic_repoqa_asset()
    parsed, parse_status, _ = _decompress_asset(synthetic_asset_bytes)
    checks.append(
        _check(
            "gzip_fixture_parse_pass",
            parse_status == "pass" and isinstance(parsed, dict),
        )
    )
    checks.append(
        _check(
            "gzip_fixture_has_python_key",
            isinstance(parsed, dict) and "python" in parsed,
        )
    )

    # --- Group 9: Needle extraction validates fields. ---
    needles, needle_status, _ = _parse_repoqa_needles(
        parsed, "python", 5
    )
    checks.append(
        _check(
            "needle_extraction_pass",
            needle_status == "pass" and len(needles) == 1,
        )
    )
    if needles:
        n0 = needles[0]
        checks.append(
            _check(
                "needle_has_repo_url",
                isinstance(n0.get("repo_url"), str)
                and n0["repo_url"].startswith("https://github.com/"),
            )
        )
        checks.append(
            _check(
                "needle_has_commit_sha",
                isinstance(n0.get("commit_sha"), str)
                and len(n0["commit_sha"]) == 40,
            )
        )
        checks.append(
            _check(
                "needle_has_needle_path",
                isinstance(n0.get("needle_path"), str)
                and n0["needle_path"].endswith(".py"),
            )
        )
        checks.append(
            _check(
                "needle_has_line_range",
                isinstance(n0.get("needle_start_line"), int)
                and isinstance(n0.get("needle_end_line"), int)
                and n0["needle_start_line"] == 10
                and n0["needle_end_line"] == 20,
            )
        )
        checks.append(
            _check(
                "needle_has_description",
                isinstance(n0.get("needle_description"), str)
                and len(n0["needle_description"]) > 0,
            )
        )

    # --- Group 10: Malformed needles map to fixed failure categories. ---
    # Missing repo.
    malformed_no_repo = {"python": [{"commit_sha": "x" * 40, "needles": []}]}
    _, status_mr, fcc_mr = _parse_repoqa_needles(malformed_no_repo, "python", 5)
    checks.append(
        _check(
            "malformed_no_repo_maps_to_needle_parse_failed",
            status_mr == "unavailable_no_python_needles"
            and fcc_mr.get("needle_parse_failed", 0) >= 1,
        )
    )
    # Missing commit_sha.
    malformed_no_commit = {"python": [{"repo": "x/y", "needles": []}]}
    _, status_mc, fcc_mc = _parse_repoqa_needles(malformed_no_commit, "python", 5)
    checks.append(
        _check(
            "malformed_no_commit_maps_to_needle_parse_failed",
            status_mc == "unavailable_no_python_needles"
            and fcc_mc.get("needle_parse_failed", 0) >= 1,
        )
    )
    # Needle missing path.
    malformed_no_path = {
        "python": [
            {
                "repo": "x/y",
                "commit_sha": "0" * 40,
                "needles": [{"start_line": 1, "end_line": 2, "description": "d"}],
            }
        ]
    }
    _, status_mp, fcc_mp = _parse_repoqa_needles(malformed_no_path, "python", 5)
    checks.append(
        _check(
            "malformed_no_path_maps_to_needle_parse_failed",
            status_mp == "unavailable_no_python_needles"
            and fcc_mp.get("needle_parse_failed", 0) >= 1,
        )
    )
    # Needle inverted line range.
    malformed_inverted = {
        "python": [
            {
                "repo": "x/y",
                "commit_sha": "0" * 40,
                "needles": [
                    {
                        "path": "a.py",
                        "start_line": 20,
                        "end_line": 10,
                        "description": "d",
                    }
                ],
            }
        ]
    }
    _, status_mi, fcc_mi = _parse_repoqa_needles(malformed_inverted, "python", 5)
    checks.append(
        _check(
            "malformed_inverted_range_maps_to_needle_parse_failed",
            status_mi == "unavailable_no_python_needles"
            and fcc_mi.get("needle_parse_failed", 0) >= 1,
        )
    )
    # Needle missing description.
    malformed_no_desc = {
        "python": [
            {
                "repo": "x/y",
                "commit_sha": "0" * 40,
                "needles": [
                    {"path": "a.py", "start_line": 1, "end_line": 2}
                ],
            }
        ]
    }
    _, status_md, fcc_md = _parse_repoqa_needles(malformed_no_desc, "python", 5)
    checks.append(
        _check(
            "malformed_no_description_maps_to_needle_parse_failed",
            status_md == "unavailable_no_python_needles"
            and fcc_md.get("needle_parse_failed", 0) >= 1,
        )
    )

    # --- Group 11: Needle limit cap. ---
    # Build an asset with 15 needles; cap at 10.
    many_needles_asset = {
        "python": [
            {
                "repo": "x/y",
                "commit_sha": "0" * 40,
                "needles": [
                    {
                        "path": f"a{i}.py",
                        "start_line": 1,
                        "end_line": 2,
                        "description": f"desc {i}",
                    }
                    for i in range(15)
                ],
            }
        ]
    }
    needles_capped, status_cap, fcc_cap = _parse_repoqa_needles(
        many_needles_asset, "python", 10
    )
    checks.append(
        _check(
            "needle_limit_caps_at_10",
            len(needles_capped) == 10,
        )
    )
    # When requested limit is below available, no cap marker.
    needles_below, status_below, fcc_below = _parse_repoqa_needles(
        many_needles_asset, "python", 5
    )
    checks.append(
        _check(
            "needle_limit_below_available_no_cap",
            len(needles_below) == 5
            and fcc_below.get("needle_limit_capped", 0) == 0,
        )
    )

    # --- Group 12: Query sanitizer (needle description). ---
    desc = (
        "1. **Purpose**: To merge adjacent strings into a single string.\n"
        "2. **Input**: A line of code.\n"
        "3. **Output**: A merged string.\n"
    )
    query = _sanitize_needle_description(desc)
    checks.append(
        _check(
            "sanitizer_extracts_purpose",
            isinstance(query, str) and len(query) > 0,
        )
    )
    checks.append(
        _check(
            "sanitizer_strips_markdown_bold",
            "**" not in query,
        )
    )
    checks.append(
        _check(
            "sanitizer_capped_at_300",
            len(query) <= 300,
        )
    )
    # Fallback: no Purpose section.
    desc_no_purpose = "Just a description with no purpose section.\nMore text."
    query_fallback = _sanitize_needle_description(desc_no_purpose)
    checks.append(
        _check(
            "sanitizer_fallback_when_no_purpose",
            isinstance(query_fallback, str) and len(query_fallback) > 0,
        )
    )

    # --- Group 13: Score metric allowlist. ---
    raw_metrics = _build_synthetic_metrics()
    # Inject forbidden dynamic keys that must be filtered out.
    raw_metrics["row_id"] = "should_be_filtered"
    raw_metrics["path"] = "src/main.py"
    raw_metrics["content_sha"] = "a" * 64
    raw_metrics["avg_latency_ms"] = 100.0
    filtered = _filter_score_metrics(raw_metrics)
    checks.append(
        _check(
            "score_filter_excludes_row_id",
            "row_id" not in filtered,
        )
    )
    checks.append(
        _check(
            "score_filter_excludes_path",
            "path" not in filtered,
        )
    )
    checks.append(
        _check(
            "score_filter_excludes_content_sha",
            "content_sha" not in filtered,
        )
    )
    checks.append(
        _check(
            "score_filter_excludes_avg_latency_ms",
            "avg_latency_ms" not in filtered,
        )
    )
    checks.append(
        _check(
            "score_filter_includes_file_recall",
            "file_recall@10" in filtered,
        )
    )
    checks.append(
        _check(
            "score_filter_includes_mrr",
            "mrr" in filtered,
        )
    )
    # Method metric allowlist is a subset of C5-A score allowlist.
    for k in SCORE_METRIC_ALLOWLIST:
        checks.append(
            _check(
                f"score_metric_allowlist_subset_of_c5a_{k}",
                k in c5a.SCORE_METRIC_ALLOWLIST,
            )
        )

    # --- Group 14: Synthetic score aggregation. ---
    per_needle = [
        _build_synthetic_metrics(),
        _build_synthetic_metrics(),
    ]
    agg = _compute_aggregate_metrics(per_needle, 2)
    checks.append(
        _check(
            "aggregate_metrics_has_file_recall",
            "file_recall@10" in agg,
        )
    )
    checks.append(
        _check(
            "aggregate_metrics_has_success_rate",
            "success_rate" in agg,
        )
    )
    checks.append(
        _check(
            "aggregate_success_rate_recomputed",
            agg["success_rate"] == 1.0,
        )
    )
    checks.append(
        _check(
            "aggregate_metrics_empty_when_no_needles",
            _compute_aggregate_metrics([], 0) == {},
        )
    )

    # --- Group 15: Failure category counts fixed enum. ---
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    fcc["repo_clone_failed"] = 1
    sample_fail_report = {
        "failure_category_counts": fcc,
    }
    checks.append(
        _check(
            "failure_category_counts_in_enum",
            not _scan_c5d(sample_fail_report),
        )
    )
    # Inject a non-enum failure category — must be rejected by the
    # builder (it only accepts enum keys).
    bad_fcc = dict(fcc)
    bad_fcc["not_a_real_category"] = 1
    rebuilt = _build_unavailable_report(
        "repo_clone_failed",
        self_test_passed=True,
        needle_limit_requested=5,
        language_filter="python",
        method="bm25",
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

    # --- Group 16: Unavailable statuses. ---
    # asset download failed.
    unavail_dl = _build_unavailable_report(
        "asset_download_failed",
        self_test_passed=True,
        needle_limit_requested=5,
        language_filter="python",
        method="bm25",
        openlocus_binary_source="default",
        network_mode="local_explicit",
    )
    checks.append(
        _check(
            "unavailable_asset_download_failed_status",
            unavail_dl["status"] == "unavailable_asset_download_failed",
        )
    )
    checks.append(
        _check(
            "unavailable_asset_download_failed_reason",
            unavail_dl["failure_reason_category"] == "asset_download_failed",
        )
    )
    checks.append(
        _check(
            "unavailable_asset_download_failed_no_smoke_flag",
            unavail_dl["repoqa_retrieval_smoke_performed"] is False,
        )
    )
    checks.append(
        _check(
            "unavailable_asset_download_failed_no_metrics",
            unavail_dl["aggregate_metrics"] == {},
        )
    )
    checks.append(
        _check(
            "unavailable_asset_download_failed_no_perf_claim",
            unavail_dl["external_benchmark_performance_claimed"] is False,
        )
    )
    checks.append(
        _check(
            "unavailable_asset_download_failed_scan_pass",
            unavail_dl["forbidden_scan"]["status"] == "pass",
        )
    )
    # no python needles.
    unavail_np = _build_unavailable_report(
        "no_python_needles",
        self_test_passed=True,
        needle_limit_requested=5,
        language_filter="python",
        method="bm25",
        openlocus_binary_source="default",
        network_mode="local_explicit",
    )
    checks.append(
        _check(
            "unavailable_no_python_needles_status",
            unavail_np["status"] == "unavailable_no_python_needles",
        )
    )
    # repo clone failed.
    unavail_rc = _build_unavailable_report(
        "repo_clone_failed",
        self_test_passed=True,
        needle_limit_requested=5,
        language_filter="python",
        method="bm25",
        openlocus_binary_source="default",
        network_mode="local_explicit",
        needles_seen=5,
    )
    checks.append(
        _check(
            "unavailable_repo_clone_failed_status",
            unavail_rc["status"] == "unavailable_repo_clone_failed",
        )
    )
    checks.append(
        _check(
            "unavailable_repo_clone_failed_needles_parsed_flag",
            unavail_rc["repoqa_needles_parsed_in_memory"] is True,
        )
    )

    # --- Group 17: Scanner rejects forbidden content. ---
    # RepoQA-specific forbidden keys.
    for forbidden_key in (
        "repo", "commit_sha", "entrypoint_path", "topic", "content",
        "dependency", "needles", "needle", "needle_name", "needle_path",
        "needle_description", "needle_id", "name", "start_line", "end_line",
        "start_byte", "end_byte", "global_start_line", "global_end_line",
        "global_start_byte", "global_end_byte", "code_ratio", "path",
        "description", "row", "rows_data", "raw_row", "raw_rows",
        "repo_name", "repo_slug", "repo_url", "base_commit", "instance_id",
        "task_id", "query", "query_text", "problem_statement",
        "gold", "gold_path", "gold_span", "gold_snippet", "gold_paths",
        "gold_lines", "gold_context", "snippet", "snippets", "content_sha",
        "stdout", "stderr", "stdout_text", "stderr_text", "evidence",
        "evidence_row", "evidence_rows", "retrieved_path",
        "retrieved_paths", "retrieved_snippet", "cloned_repo_path",
        "cloned_repo", "per_row_metrics", "row_metrics",
        "per_needle_metrics", "needle_metrics", "patch", "diff",
    ):
        checks.append(
            _check(
                f"scanner_rejects_{forbidden_key}_key",
                bool(_scan_c5d({forbidden_key: "value"})),
            )
        )
    # Recommendation fields.
    for field in FORBIDDEN_RECOMMENDATION_FIELDS:
        checks.append(
            _check(
                f"scanner_rejects_{field}_key",
                bool(_scan_c5d({field: "bm25"})),
            )
        )
    # Value patterns.
    checks.append(
        _check(
            "scanner_rejects_repo_url_value",
            bool(_scan_c5d({"leaked": "https://github.com/foo/bar"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_repo_slug_value",
            bool(_scan_c5d({"leaked": "psf/black"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_commit_sha_value",
            bool(
                _scan_c5d(
                    {"leaked": "f03ee113c9f3dfeb477f2d4247bfb7de2e5f465c"}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_file_path_value",
            bool(_scan_c5d({"leaked": "src/black/trans.py"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_line_range_value",
            bool(_scan_c5d({"leaked": "585-639"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_hex_digest_value",
            bool(_scan_c5d({"leaked": "a" * 32})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_tmp_path_value",
            bool(_scan_c5d({"leaked": "/tmp/foo"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_multiline_value",
            bool(_scan_c5d({"leaked": "line1\nline2"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_raw_json_fragment",
            bool(_scan_c5d({"leaked": '{"key": "value"}'})),
        )
    )

    # --- Group 18: Scanner allows safe values. ---
    checks.append(
        _check(
            "scanner_allows_benchmark_value",
            not _scan_c5d({"benchmark": "repoqa"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_dataset_release_value",
            not _scan_c5d({"dataset_release": "repoqa-2024-06-23"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_method_value",
            not _scan_c5d({"method": "bm25"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_language_filter_value",
            not _scan_c5d({"language_filter": "python"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_query_mode_value",
            not _scan_c5d({"query_mode": "needle_description"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_gold_target_mode_value",
            not _scan_c5d({"gold_target_mode": "needle_path_line_range"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_network_mode_value",
            not _scan_c5d({"network_mode": "local_explicit"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_aggregate_metrics",
            not _scan_c5d({"aggregate_metrics": {"mrr": 0.5}}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_failure_category_count",
            not _scan_c5d(
                {
                    "failure_category_counts": {
                        "repo_clone_failed": 1,
                        "asset_download_failed": 0,
                    }
                }
            ),
        )
    )

    # --- Group 19: Fail-closed generation. ---
    try:
        _enforce_c5d_no_forbidden(skeleton)
        checks.append(_check("fail_closed_clean_report_no_raise", True))
    except SystemExit:
        checks.append(_check("fail_closed_clean_report_no_raise", False))

    leaked_report = dict(skeleton)
    leaked_report["leaked_repo"] = "psf/black"
    try:
        _enforce_c5d_no_forbidden(leaked_report)
        checks.append(_check("fail_closed_leaked_repo_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_leaked_repo_raises", True))

    leaked_report2 = dict(skeleton)
    leaked_report2["best_method"] = "bm25"
    try:
        _enforce_c5d_no_forbidden(leaked_report2)
        checks.append(_check("fail_closed_best_method_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_best_method_raises", True))

    leaked_report3 = dict(skeleton)
    leaked_report3["winner"] = "bm25"
    try:
        _enforce_c5d_no_forbidden(leaked_report3)
        checks.append(_check("fail_closed_winner_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_winner_raises", True))

    leaked_report4 = dict(skeleton)
    leaked_report4["recommended_default"] = "bm25"
    try:
        _enforce_c5d_no_forbidden(leaked_report4)
        checks.append(_check("fail_closed_recommended_default_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_recommended_default_raises", True))

    leaked_report5 = dict(skeleton)
    leaked_report5["commit_sha"] = "0" * 40
    try:
        _enforce_c5d_no_forbidden(leaked_report5)
        checks.append(_check("fail_closed_commit_sha_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_commit_sha_raises", True))

    leaked_report6 = dict(skeleton)
    leaked_report6["needle_description"] = "leaked query"
    try:
        _enforce_c5d_no_forbidden(leaked_report6)
        checks.append(_check("fail_closed_needle_description_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_needle_description_raises", True))

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

    # --- Group 20: Public artifact self-scan is clean. ---
    checks.append(
        _check(
            "public_artifact_self_scan_clean",
            not _scan_c5d(skeleton),
        )
    )
    checks.append(
        _check(
            "unavailable_self_scan_clean",
            not _scan_c5d(unavail_dl),
        )
    )

    # --- Group 21: CLI argument surface. ---
    parser = build_parser()
    option_strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            option_strings.add(opt)
    for required_opt in (
        "--self-test",
        "--needle-limit",
        "--language-filter",
        "--method",
        "--openlocus",
        "--out",
    ):
        checks.append(
            _check(
                f"cli_has_option_{required_opt}",
                required_opt in option_strings,
            )
        )

    # --- Group 22: Aggregate runtime seconds present. ---
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
            "unavailable_report_has_null_runtime",
            unavail_dl.get("aggregate_runtime_seconds") is None,
        )
    )

    # --- Group 23: No winner/best_method/recommended_default anywhere. ---
    for field in FORBIDDEN_RECOMMENDATION_FIELDS:
        checks.append(
            _check(
                f"clean_report_missing_{field}",
                field not in skeleton,
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
    """Build the C5-D CLI parser."""
    ap = SafeArgumentParser(
        description=(
            "C5-D RepoQA BM25 retrieval performance smoke "
            "(public aggregate-only artifact; bounded RepoQA Python "
            "needle subset; transient /tmp asset download + clone + "
            "retrieval + score; bm25 only; no provider calls; no raw "
            "repo/commit/path/description/line/source/needle IDs/row "
            "IDs/hashes/winner/best_method/recommended_default "
            "committed)."
        )
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="run deterministic self-test groups and exit (no artifact written, no network)",
    )
    ap.add_argument(
        "--needle-limit",
        type=int,
        default=NEEDLE_LIMIT_DEFAULT,
        help=(
            "number of RepoQA Python needles to evaluate (default: "
            f"{NEEDLE_LIMIT_DEFAULT}; hard cap "
            f"{NEEDLE_LIMIT_HARD_CAP})"
        ),
    )
    ap.add_argument(
        "--language-filter",
        default=DEFAULT_LANGUAGE_FILTER,
        choices=ALLOWED_LANGUAGE_FILTERS,
        help=(
            "language filter category (default: python; allowed: "
            f"{', '.join(ALLOWED_LANGUAGE_FILTERS)}; C5-D does NOT "
            "silently fall back to all languages)"
        ),
    )
    ap.add_argument(
        "--method",
        default=DEFAULT_METHOD,
        choices=ALLOWED_METHODS,
        help=(
            "OpenLocus retrieval method (default: bm25; allowed: "
            f"{', '.join(ALLOWED_METHODS)})"
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

    needle_limit = _validate_needle_limit(args.needle_limit)
    language_filter = args.language_filter
    method = args.method
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
            needle_limit_requested=needle_limit,
            language_filter=language_filter,
            method=method,
            openlocus_binary_source=openlocus_source,
            network_mode="local_explicit",
        )
        _enforce_c5d_no_forbidden(report)
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
        report = _run_network_smoke(
            needle_limit=needle_limit,
            language_filter=language_filter,
            method=method,
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
            needle_limit_requested=needle_limit,
            language_filter=language_filter,
            method=method,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
        )

    _enforce_c5d_no_forbidden(report)
    _write_json(out_path, report)
    print(
        f"wrote artifact "
        f"(forbidden_scan={report['forbidden_scan']['status']}, "
        f"self_test_passed={report['self_test_passed']}, "
        f"status={report['status']}, "
        f"phase={report['phase']}, "
        f"method={report['method']}, "
        f"needles_seen={report['needles_seen']}, "
        f"needles_successful={report['needles_successful']})"
    )


if __name__ == "__main__":
    main()
