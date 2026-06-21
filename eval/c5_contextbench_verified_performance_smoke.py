#!/usr/bin/env python3
"""C5-A ContextBench Verified Retrieval Performance Smoke (Public Aggregate-Only).

This module implements the **C5-A external benchmark retrieval performance
smoke** over the ContextBench verified subset
(``Contextbench/ContextBench`` config ``contextbench_verified`` split
``train``). It is the first external-benchmark-shaped retrieval
performance smoke in the OpenLocus research track.

C5-A is explicitly **not** a rigorous benchmark result, **not** a
leaderboard entry, **not** a performance claim, **not** a promotion,
**not** a default/policy change, and **not** a runtime/retriever/pack/
backend/EvidenceCore semantic change. The committed artifact records
only aggregate retrieval metrics (file recall, MRR, span/line metrics,
zero-overlap, structural/citation validity when present) computed by
``eval/score.py`` over a bounded ContextBench verified subset.

Claim boundary (binding):

* Claim level: ``external_benchmark_retrieval_performance_smoke_only``.
* Status: ``pass`` | ``partial`` | ``unavailable_with_reason`` |
  ``fail_schema_contract`` | ``fail_forbidden_scan``.
* Mode: ``contextbench_verified_retrieval_performance_smoke``; phase ``C5-A``.
* This is **eval/diagnostic only**. It is NOT a benchmark result, NOT a
  leaderboard entry, NOT a performance claim, NOT a promotion, NOT a
  default change, NOT a runtime/retriever/pack/backend change, NOT an
  EvidenceCore semantic change, and NOT a downstream agent value claim.

Privacy / license boundary (binding):

* Raw ContextBench rows, queries/problem statements, repo URLs/names,
  base commits, gold paths/spans/contents, generated task/label/run
  JSONL, evidence rows, cloned repos, and stdout/stderr are kept
  **transient only** under ``/tmp`` or CI ephemeral workspace. They are
  NEVER committed or uploaded.
* Aggregate metric values from ``eval/score.py`` are safe to publish if
  aggregate only. No row-level records, no row IDs, no paths, no spans,
  no snippets, no content_sha, no stdout/stderr.
* ContextBench dataset license is unknown
  (``unknown_dataset_license``); row-level redistribution is disabled
  (``row_level_redistribution_allowed=false``) and derived row-level
  publication is disabled
  (``derived_row_level_publication_allowed=false``). Aggregate metrics
  publication is allowed as aggregate-only smoke
  (``aggregate_metrics_publication=aggregate_only_smoke``).

Network / CI policy (binding):

* Default no-network self-test passes without HuggingFace/GitHub.
* Real performance smoke requires public network access to HF
  datasets-server and GitHub repos. CI must be a separate explicit
  ``workflow_dispatch`` job with
  ``enable_external_benchmark_network=true``. It must NOT run on
  PR/push by default, must use no provider secrets/vars, and must
  upload only the aggregate report.

Run::

    python3 -m py_compile eval/c5_contextbench_verified_performance_smoke.py
    python3 eval/c5_contextbench_verified_performance_smoke.py --self-test
    python3 eval/c5_contextbench_verified_performance_smoke.py \\
        --row-limit 5 --method bm25 --query-mode first_paragraph \\
        --language-filter python \\
        --out artifacts/c5_contextbench_verified_performance_smoke/\\
c5_contextbench_verified_performance_smoke_report.json

If the network smoke cannot complete in the environment, the default
artifact records truthful ``unavailable_with_reason`` with a real
failure category (no stale/fake pass). Self-test/docs/diff-check still
pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
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

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "c5_contextbench_verified_performance_smoke.v1"
GENERATED_BY = "eval/c5_contextbench_verified_performance_smoke.py"
CLAIM_LEVEL = "external_benchmark_retrieval_performance_smoke_only"
MODE = "contextbench_verified_retrieval_performance_smoke"
PHASE = "C5-A"

DEFAULT_OUT = Path(
    "artifacts/c5_contextbench_verified_performance_smoke/"
    "c5_contextbench_verified_performance_smoke_report.json"
)

# Hard caps on row limit. Default 5; max 20.
ROW_LIMIT_DEFAULT = 5
ROW_LIMIT_HARD_CAP = 20

# Bounded timeouts for external operations.
HF_TIMEOUT_SECONDS = 15
CLONE_TIMEOUT_SECONDS = 300
CHECKOUT_TIMEOUT_SECONDS = 90
RETRIEVAL_TIMEOUT_SECONDS = 90
SCORE_TIMEOUT_SECONDS = 60

# HF datasets-server base (stdlib only; no extra deps).
_HF_DATASETS_SERVER = "https://datasets-server.huggingface.co"
_HF_DATASET_ID = "Contextbench/ContextBench"
_HF_CONFIG = "contextbench_verified"
_HF_SPLIT = "train"

# Methods supported by ``eval/run_retrieval.py`` without provider calls.
ALLOWED_METHODS: tuple[str, ...] = ("bm25", "regex", "text", "symbol")
DEFAULT_METHOD = "bm25"

# Query modes supported by the in-memory query sanitizer.
ALLOWED_QUERY_MODES: tuple[str, ...] = (
    "first_paragraph",
    "first_sentence",
    "raw",
)
DEFAULT_QUERY_MODE = "first_paragraph"

# Language filter categories supported. ``python`` is the default; the
# filter is a categorical bucket only — never the raw row value.
ALLOWED_LANGUAGE_FILTERS: tuple[str, ...] = (
    "python",
    "all",
)
DEFAULT_LANGUAGE_FILTER = "python"

# OpenLocus binary candidates (in order). Default is release; debug is
# the fallback if release is missing.
DEFAULT_OPENLOCUS_CANDIDATES: tuple[str, ...] = (
    "target/release/openlocus",
    "target/debug/openlocus",
)

# ---------------------------------------------------------------------------
# Safe booleans true (only when actually true). Exactly these MAY be true
# in the committed public artifact.
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "external_benchmark_rows_read": False,
    "repositories_materialized_transiently": False,
    "openlocus_retrieval_executed": False,
    "score_py_metrics_computed": False,
    "performance_smoke": False,
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
}

# ---------------------------------------------------------------------------
# No-claim / no-runtime-change flags (all MUST be false in the committed
# public artifact). C5-A runs NO provider, makes NO remote provider calls,
# proves NO downstream agent value, promotes NO candidate, changes NO
# runtime/retriever/pack/backend/default-policy/EvidenceCore semantics,
# and claims NO external benchmark performance.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
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
    "aggregate_metrics_publication": "aggregate_only_smoke",
}

# ---------------------------------------------------------------------------
# Fixed failure-category enum for the smoke. Only these category labels
# may appear in the public artifact; never row-level values.
# ---------------------------------------------------------------------------

FAILURE_CATEGORIES: tuple[str, ...] = (
    "network_fetch_failed",
    "row_parse_failed",
    "gold_context_parse_failed",
    "language_filter_excluded",
    "clone_failed",
    "checkout_failed",
    "task_jsonl_write_failed",
    "label_jsonl_write_failed",
    "retrieval_failed",
    "score_failed",
    "no_python_rows",
    "row_limit_capped",
    "scanner_self_test_failed",
    "forbidden_leak_blocked",
    "unexpected_exception",
)

# ---------------------------------------------------------------------------
# Metric allowlist. Only these aggregate metric names from ``score.py``
# may appear in the public artifact. No dynamic row IDs or paths.
# ---------------------------------------------------------------------------

SCORE_METRIC_ALLOWLIST: tuple[str, ...] = (
    "total_tasks",
    "successful",
    "success_rate",
    "avg_latency_ms",
    "structural_validity",
    "citation_validity",
    "citation_hash_checked",
    "citation_validation_mode",
    "file_recall@1",
    "file_recall@5",
    "file_recall@10",
    "file_precision@5",
    "file_precision@10",
    "mrr",
    "line_precision@10",
    "line_recall@10",
    "span_f0.5@10",
    "token_waste_ratio@10",
    "wrong_span_rate@10",
    "zero_overlap_evidence_rate@10",
)

# ---------------------------------------------------------------------------
# Public artifact scanner (strict, fail-closed). Modeled on B16-A: no
# contract containers with field-name tokens; no over-broad container
# exemption. Sensitive field-name tokens are NEVER emitted as keys
# anywhere and NEVER emitted as values outside the explicit safe-value
# key allowlist. The scanner runs ONLY against the final public aggregate
# artifact (NOT against in-memory task/label/run JSONL, which contain
# paths/spans/queries/gold).
# ---------------------------------------------------------------------------

# Sensitive KEY names that must NEVER appear as dict keys anywhere in a
# public artifact JSON. Superset of repo/commit/path/file/span/content/
# hash/identifier/patch/test/event-log/secret/raw-row keys.
FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset(
    {
        # location / path / workspace
        "path", "span", "line_range", "start_line", "end_line",
        "start_byte", "end_byte", "line_ranges", "spans",
        "file", "files", "filename", "filepath",
        "workspace_path", "workspace", "workspace_dir", "tmp_dir",
        "tmp_path", "target_file", "wrong_file", "wrong_cue_file",
        "target_module", "distractor_module", "test_module",
        "source_path", "module_path", "module",
        "repo_path", "repo_dir", "repo_root", "repo_url", "repo",
        "base_commit", "commit", "commit_sha",
        # content / hash
        "content", "content_sha", "content_hash", "hash", "digest",
        "sha256", "md5", "sha1",
        "snippet", "snippets", "excerpt", "excerpts",
        "code", "source_code", "code_snippet", "body", "text", "source",
        # identifiers
        "task_id", "task_index", "repo_id", "instance_id",
        "original_inst_id", "row_id", "record_id", "id", "name", "run_id",
        # packet-specific identifiers
        "packet_ref", "packet_id", "private_record_ref",
        "candidate_ref", "candidate_id", "candidate",
        # labels / qrels / annotations
        "label", "labels", "qrels", "gold", "gold_label", "gold_labels",
        "gold_context", "gold_paths", "gold_lines", "gold_spans",
        "hard_negative", "hard_negatives",
        # prompts / responses / model outputs
        "query", "query_text", "problem_statement", "prompt", "response",
        "model_response", "model_output", "provider_payload",
        "raw_payload", "api_response", "response_body",
        # rows / records / packets
        "raw_rows", "rows", "records", "runs", "per_run", "raw",
        "raw_data", "predictions", "candidates", "evidence",
        # patches / tests / output
        "patch", "diff", "test_patch", "tests", "test_output",
        "test_log", "test_stdout", "test_stderr", "stdout", "stderr",
        "returncode", "exit_code",
        # event logs / traces / errors
        "event_log", "events", "log", "trace", "raw_event", "raw_log",
        "stack_trace", "traceback", "error_message", "error",
        # secrets / provider
        "api_key", "api_token", "api_secret", "base_url", "provider_key",
        "authorization", "secret", "token", "credential", "password",
        "provider_url", "provider_base_url",
    }
)

# Known-safe provenance value paths (allowlisted for path-like / hex /
# path-like value checks only). The forbidden dict-key check is NOT
# relaxed by this. These keys MAY hold path-like values (e.g. the
# generator script path) without triggering the path-like value leak.
SAFE_VALUE_KEY_NAMES: frozenset[str] = frozenset(
    {
        "schema_version",
        "generated_by",
        "generated_at",
        "claim_level",
        "status",
        "mode",
        "phase",
        "method",
        "query_mode",
        "language_filter",
        "network_mode",
        "dataset_id",
        "config",
        "split",
        "failure_reason_category",
        "dataset_license_status",
        "aggregate_metrics_publication",
        "citation_validation_mode",
        "openlocus_binary_source",
    }
)

# Value patterns that indicate leaked repo/file/patch/test/event-log/
# secret/identifier data. C5-A rejects ALL URLs (no URL allowlist) per
# the fail-closed rule (repo URLs must NEVER leak).
_RE_URL_VALUE = re.compile(r"https?://", re.IGNORECASE)
_RE_HEX_DIGEST = re.compile(r"[A-Fa-f0-9]{32,}")
_RE_SECRET_LIKE = re.compile(
    r"(?:api[_-]?key|api[_-]?token|api[_-]?secret|base[_-]?url"
    r"|provider[_-]?key|provider[_-]?url|authorization[_-]?bearer"
    r"|secret|password|credential)",
    re.IGNORECASE,
)
_FILE_EXT = (
    r"py|rs|ts|tsx|js|jsx|go|java|c|cpp|cc|h|hpp|hh|md|json|toml|"
    r"yaml|yml|txt|sh|rb|php|kt|swift|patch|diff|csv|parquet|jsonl"
)
_RE_FILE_PATH_VALUE = re.compile(
    rf"\b[A-Za-z0-9._/\-]+\.(?:{_FILE_EXT})\b"
)
_RE_LINE_RANGE_VALUE = re.compile(r"\b\d+\s*[:\-]\s*\d+\b")
_RE_RAW_JSON = re.compile(r'^\s*[\{\[]\s*"[^"]+"\s*:')
# C5-A-specific leak patterns: /tmp workspace paths, task identifiers,
# patch/diff markers, stack traces, git URLs.
_RE_TMP_PATH_VALUE = re.compile(r"/tmp/")
_RE_TASK_ID_VALUE = re.compile(r"\btask[_\-\s]*\d+\b", re.IGNORECASE)
_RE_PATCH_MARKER = re.compile(r"^(---|\+\+\+|@@\s)", re.MULTILINE)
_RE_STACK_TRACE = re.compile(
    r"Traceback\s*\(most\s+recent\s+call\s+last\)", re.IGNORECASE
)
# Hex commit SHA (40 chars) or short SHA (7+ chars). Catches
# ``838e432e3e5519c5383d12018e6c78f8ec7833c1`` and similar.
_RE_COMMIT_SHA_VALUE = re.compile(r"\b[0-9a-f]{40}\b")
# Repo slug like ``astropy/astropy`` or ``django/django``.
_RE_REPO_SLUG_VALUE = re.compile(r"\b[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+\b")

# The sentinel used by self-tests; the scanner must never let it through
# in a committed/public output. Used as a value-leak canary.
_SECRET_SENTINEL = "SECRET_VALIDATOR_SENTINEL"

# Schema-key container keys whose CHILD KEYS are fixed schema-only
# category labels (NOT row-level values). The forbidden_key check is
# relaxed for keys nested directly under these containers, because those
# keys are fixed category labels used as count buckets. The values under
# these containers are still scanned (they must be ints/counts only).
SCHEMA_KEY_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "failure_category_counts",
        "metrics",
    }
)


def _path_last_key(path: str) -> str:
    """Extract the last key segment from a dotted JSON path."""
    last = path.rsplit(".", 1)[-1]
    return last.split("[")[0]


def _is_safe_value_path(path: str) -> bool:
    """Check if a JSON path ends with a known-safe value key."""
    return _path_last_key(path) in SAFE_VALUE_KEY_NAMES


def _is_schema_key_container(path: str) -> bool:
    """Check if the parent of the current key is a schema-key container."""
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in SCHEMA_KEY_CONTAINER_KEYS


def _scan_forbidden(
    obj: Any, path: str = "$"
) -> list[dict[str, Any]]:
    """Strict recursive scanner for public artifact JSON.

    Returns a list of violation dicts with ``category`` and ``path``
    (JSON path), NEVER the leaked value itself. Fail-closed: any
    violation means the output would leak.
    """
    violations: list[dict[str, Any]] = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            sub_path = f"{path}.{key_str}"
            # Forbid sensitive key names anywhere as dict keys, EXCEPT
            # when the parent is a schema-key container (the key is a
            # fixed category label used as a count bucket).
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
            # Sensitive field name as a VALUE is a leak.
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
        elif _SECRET_SENTINEL in obj:
            violations.append({"category": "sentinel_value", "path": path})
        elif not safe_value and _RE_REPO_SLUG_VALUE.search(obj):
            # Repo slug like ``astropy/astropy`` — would leak the repo
            # identity. Exempted for safe value paths (none of which
            # hold repo slugs in C5-A).
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
    """Run the public forbidden scanner and return a sanitized summary."""
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
    """Fail-closed guard: raise SystemExit if any forbidden content leaks."""
    scan = _forbidden_scan_summary(obj)
    if scan["status"] != "pass":
        raise SystemExit(
            "forbidden content leak; refusing to write artifact"
        )


def _refuse_on_self_test_failure(report: dict[str, Any]) -> None:
    """Refuse successful artifact generation if self-test failed."""
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


# ---------------------------------------------------------------------------
# HTTP helper (stdlib urllib only; bounded timeout; never raises)
# ---------------------------------------------------------------------------


def _http_get_json(
    url: str, timeout: int = HF_TIMEOUT_SECONDS
) -> tuple[Any, str, int | None]:
    """Bounded HTTP GET returning ``(parsed_json_or_None, status, http_code)``.

    ``status`` is ``"pass"`` on success, ``"unavailable"`` on network
    failure / non-200 / timeout, or ``"partial"`` on parse failure.

    NEVER raises. NEVER returns the raw response body in error fields.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "OpenLocus-C5-contextbench-smoke/0.1 (bounded; stdlib)",
            },
        )
        with urllib.request.urlopen(  # noqa: S310 - bounded smoke
            req, timeout=timeout
        ) as resp:
            code = resp.getcode()
            body = resp.read()
            try:
                parsed = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None, "partial", code
            if not isinstance(parsed, (dict, list)):
                return None, "partial", code
            return parsed, "pass", code
    except urllib.error.HTTPError as exc:
        return None, "unavailable", exc.code
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
        return None, "unavailable", None


# ---------------------------------------------------------------------------
# Row fetching from HF datasets-server /rows (paginated; transient).
# ---------------------------------------------------------------------------


def _fetch_contextbench_rows(
    row_limit: int, language_filter: str
) -> tuple[list[dict[str, Any]], str, int, dict[str, int]]:
    """Fetch bounded ContextBench verified rows from HF datasets-server.

    Returns ``(rows, status, network_calls, failure_category_counts)``.

    * ``rows``: bounded in-memory rows (transient; never persisted). The
      caller MUST discard them after adaptation/scoring.
    * ``status``: ``"pass"`` | ``"partial"`` | ``"unavailable"``.
    * ``network_calls``: count of HF HTTP calls made.
    * ``failure_category_counts``: fixed category counts (mutable).

    The rows are filtered in-memory by ``language_filter`` (categorical
    bucket only; ``"python"`` default; ``"all"`` disables filtering).
    """
    failure_counts: dict[str, int] = {c: 0 for c in FAILURE_CATEGORIES}
    network_calls = 0
    rows: list[dict[str, Any]] = []

    # Fetch rows in pages of 100 until we have row_limit matching rows or
    # the dataset is exhausted. Bound total pages to avoid runaway.
    max_pages = (row_limit // 100) + 2
    offset = 0
    seen_total = 0
    exhausted = False

    while len(rows) < row_limit and not exhausted and max_pages > 0:
        max_pages -= 1
        length = min(100, row_limit - len(rows) + 10)
        url = (
            f"{_HF_DATASETS_SERVER}/rows?dataset="
            f"{urllib.parse.quote(_HF_DATASET_ID, safe='/')}"
            f"&config={urllib.parse.quote(_HF_CONFIG)}"
            f"&split={urllib.parse.quote(_HF_SPLIT)}"
            f"&offset={offset}&length={length}"
        )
        raw, status, _ = _http_get_json(url)
        network_calls += 1

        if status != "pass" or not isinstance(raw, dict):
            failure_counts["network_fetch_failed"] += 1
            if not rows:
                return rows, "unavailable", network_calls, failure_counts
            return rows, "partial", network_calls, failure_counts

        rows_raw = raw.get("rows", [])
        if not isinstance(rows_raw, list) or len(rows_raw) == 0:
            exhausted = True
            break

        for r in rows_raw:
            row = r.get("row", r) if isinstance(r, dict) else {}
            if not isinstance(row, dict):
                failure_counts["row_parse_failed"] += 1
                continue
            # Language filter (categorical bucket only; never the raw
            # value beyond this scope).
            lang = row.get("language")
            if language_filter != "all":
                if not isinstance(lang, str) or lang != language_filter:
                    failure_counts["language_filter_excluded"] += 1
                    continue
            rows.append(row)
            if len(rows) >= row_limit:
                break

        seen_total += len(rows_raw)
        # Stop if the server reports the dataset is exhausted.
        if raw.get("partial") is True or len(rows_raw) < length:
            exhausted = True
        offset += len(rows_raw)
        # Bound by the reported total to avoid spinning.
        total = raw.get("num_rows_total")
        if isinstance(total, int) and offset >= total:
            exhausted = True

    # Cap to row_limit (defensive; should already be capped).
    if len(rows) > row_limit:
        rows = rows[:row_limit]
        failure_counts["row_limit_capped"] += 1

    if not rows:
        failure_counts["no_python_rows"] += 1
        return rows, "unavailable", network_calls, failure_counts

    if len(rows) < row_limit:
        return rows, "partial", network_calls, failure_counts

    return rows, "pass", network_calls, failure_counts


# ---------------------------------------------------------------------------
# Query sanitizer (in-memory only; never emits raw values to public).
# ---------------------------------------------------------------------------


_RE_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_RE_HTML_TAG = re.compile(r"<[^>]+>")
_RE_MARKDOWN_HEADER = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_RE_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_RE_ISSUE_TEMPLATE = re.compile(
    r"^\s*\*\*[^*]+\*\*\s*:", re.MULTILINE
)


def _sanitize_query(
    problem_statement: str, query_mode: str
) -> str:
    """Sanitize a problem_statement into a retrieval query (in-memory only).

    The query is NEVER written to the public artifact. It is used only
    to drive ``run_retrieval.py`` under a transient ``/tmp`` workspace.

    Modes:
    * ``first_paragraph``: take the first non-empty paragraph after
      stripping HTML comments, HTML tags, markdown headers, and code
      fences. Cap at 500 chars.
    * ``first_sentence``: take the first sentence (split on ``. ``)
      after sanitization. Cap at 200 chars.
    * ``raw``: sanitized text only (strip HTML comments/tags). Cap at
      1000 chars.
    """
    if not isinstance(problem_statement, str):
        return ""
    text = problem_statement
    # Strip HTML comments, HTML tags, markdown headers, code fences.
    text = _RE_HTML_COMMENT.sub(" ", text)
    text = _RE_HTML_TAG.sub(" ", text)
    text = _RE_CODE_FENCE.sub(" ", text)
    text = _RE_MARKDOWN_HEADER.sub(" ", text)
    # Collapse whitespace.
    text = " ".join(text.split())

    if query_mode == "raw":
        return text[:1000]

    if query_mode == "first_sentence":
        # Split on sentence boundaries.
        parts = re.split(r"(?<=[.!?])\s+", text)
        if parts and parts[0]:
            return parts[0][:200]
        return text[:200]

    # Default: first_paragraph.
    # Split into paragraphs on double-newline (after collapse, this is
    # empty; use single newline heuristic on the original text).
    raw = problem_statement
    raw = _RE_HTML_COMMENT.sub(" ", raw)
    raw = _RE_HTML_TAG.sub(" ", raw)
    raw = _RE_CODE_FENCE.sub(" ", raw)
    paragraphs = re.split(r"\n\s*\n", raw)
    for para in paragraphs:
        para = " ".join(para.split())
        if para and not _RE_ISSUE_TEMPLATE.match(para):
            # Skip pure template/instruction paragraphs.
            if len(para) > 20:
                return para[:500]
    # Fallback: first paragraph regardless.
    if paragraphs:
        return " ".join(paragraphs[0].split())[:500]
    return text[:500]


# ---------------------------------------------------------------------------
# Gold context parser (in-memory only; never emits raw values to public).
# ---------------------------------------------------------------------------


def _parse_gold_context(
    gold_context_raw: Any,
) -> tuple[list[str], list[list[int]], str]:
    """Parse a ContextBench ``gold_context`` into (gold_paths, gold_lines).

    ``gold_context`` is a JSON string parsing to a list of dicts with
    keys ``file``, ``start_line``, ``end_line``, ``content``. The
    ``content`` field is NEVER read or persisted; only paths and line
    ranges are extracted transiently for ``eval/score.py``.

    Returns ``(gold_paths, gold_lines, status)``. ``gold_lines`` is a
    list of ``[start, end]`` pairs aligned with ``gold_paths``. ``status``
    is ``"pass"`` | ``"gold_context_parse_failed"``.
    """
    if isinstance(gold_context_raw, str):
        try:
            parsed = json.loads(gold_context_raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return [], [], "gold_context_parse_failed"
    elif isinstance(gold_context_raw, list):
        parsed = gold_context_raw
    elif isinstance(gold_context_raw, dict):
        # Some rows may wrap gold_context in a dict; extract list.
        parsed = (
            parsed.get("gold_context", parsed)
            if isinstance(parsed := gold_context_raw, dict)
            else gold_context_raw
        )
        if isinstance(parsed, dict):
            parsed = []
    else:
        return [], [], "gold_context_parse_failed"

    if not isinstance(parsed, list):
        return [], [], "gold_context_parse_failed"

    gold_paths: list[str] = []
    gold_lines: list[list[int]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        file_path = item.get("file")
        start = item.get("start_line")
        end = item.get("end_line")
        if not isinstance(file_path, str) or not file_path:
            continue
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if start < 1 or end < 1 or start > end:
            continue
        gold_paths.append(file_path)
        gold_lines.append([start, end])
        # NEVER read or persist item.get("content").

    if not gold_paths:
        return [], [], "gold_context_parse_failed"
    return gold_paths, gold_lines, "pass"


# ---------------------------------------------------------------------------
# Transient task/label JSONL writers (under TemporaryDirectory only).
# ---------------------------------------------------------------------------


def _write_transient_jsonl(
    path: Path, records: list[dict[str, Any]]
) -> None:
    """Write a transient JSONL file under a TemporaryDirectory only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as dst:
        for rec in records:
            dst.write(json.dumps(rec) + "\n")


# ---------------------------------------------------------------------------
# Repo materialization (clone + checkout under TemporaryDirectory only).
# ---------------------------------------------------------------------------


def _resolve_openlocus_binary(
    explicit: str | None,
) -> tuple[str | None, str]:
    """Resolve the OpenLocus binary path to an ABSOLUTE path.

    Returns ``(absolute_path, source)``. If ``explicit`` is given and
    exists, use it. Otherwise try ``target/release/openlocus`` then
    ``target/debug/openlocus`` (resolved against the repo root inferred
    from this script's location). Returns ``(None, "missing")`` if none
    found. The returned path is ALWAYS absolute, because
    ``run_retrieval.py`` runs with ``--cwd <repo_root>`` and a relative
    binary path would not resolve.
    """
    repo_root = Path(__file__).resolve().parent.parent
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = (repo_root / p).resolve()
        if p.exists() and os.access(p, os.X_OK):
            return str(p), "explicit"
        return None, "explicit_missing"
    for cand in DEFAULT_OPENLOCUS_CANDIDATES:
        p = (repo_root / cand).resolve()
        if p.exists() and os.access(p, os.X_OK):
            return str(p), "default"
    return None, "missing"


def _clone_and_checkout(
    repo_url: str, base_commit: str, work_dir: Path
) -> tuple[bool, str, dict[str, int]]:
    """Clone ``repo_url`` at ``base_commit`` under ``work_dir`` (transient).

    Returns ``(success, failure_category, failure_counts)``. Uses
    ``git clone --filter=blob:none --no-checkout`` then
    ``git checkout <base_commit>``. Bounded timeouts.

    The cloned repo is NEVER committed or uploaded; it lives only under
    the caller's TemporaryDirectory.
    """
    failure_counts: dict[str, int] = {c: 0 for c in FAILURE_CATEGORIES}
    repo_dir = work_dir / "repo"

    # git clone --filter=blob:none --no-checkout <url> <dir>
    clone_cmd = [
        "git", "clone", "--filter=blob:none", "--no-checkout",
        repo_url, str(repo_dir),
    ]
    try:
        proc = subprocess.run(
            clone_cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=CLONE_TIMEOUT_SECONDS,
        )
        if proc.returncode != 0:
            failure_counts["clone_failed"] += 1
            return False, "clone_failed", failure_counts
    except subprocess.TimeoutExpired:
        failure_counts["clone_failed"] += 1
        return False, "clone_failed", failure_counts
    except (OSError, subprocess.SubprocessError):
        failure_counts["clone_failed"] += 1
        return False, "clone_failed", failure_counts

    # git checkout <base_commit>
    checkout_cmd = [
        "git", "-C", str(repo_dir), "checkout", base_commit,
    ]
    try:
        proc = subprocess.run(
            checkout_cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=CHECKOUT_TIMEOUT_SECONDS,
        )
        if proc.returncode != 0:
            failure_counts["checkout_failed"] += 1
            return False, "checkout_failed", failure_counts
    except subprocess.TimeoutExpired:
        failure_counts["checkout_failed"] += 1
        return False, "checkout_failed", failure_counts
    except (OSError, subprocess.SubprocessError):
        failure_counts["checkout_failed"] += 1
        return False, "checkout_failed", failure_counts

    return True, "pass", failure_counts


# ---------------------------------------------------------------------------
# Retrieval + scoring (subprocess; transient JSONL only).
# ---------------------------------------------------------------------------


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

    # Step 1: run_retrieval.py --dataset tasks.jsonl --out run.jsonl
    #         --openlocus <bin> --cwd <repo_root> --method <method>
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

    # Step 2: score.py --pred run.jsonl --dataset labels.jsonl
    #         --repo-root <repo_root>
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


def _filter_score_metrics(
    metrics: dict[str, Any]
) -> dict[str, Any]:
    """Filter score.py metrics to the fixed allowlist only.

    No dynamic row IDs or paths. Only aggregate numeric/boolean/string
    metric values from the allowlist are kept.
    """
    filtered: dict[str, Any] = {}
    for key in SCORE_METRIC_ALLOWLIST:
        if key in metrics:
            val = metrics[key]
            # Accept only bool, int, float, or short string.
            if isinstance(val, bool):
                filtered[key] = bool(val)
            elif isinstance(val, (int, float)):
                # Round floats to 6 decimals for stability.
                if isinstance(val, float):
                    filtered[key] = round(val, 6)
                else:
                    filtered[key] = int(val)
            elif isinstance(val, str) and len(val) <= 64:
                filtered[key] = str(val)
    return filtered


# ---------------------------------------------------------------------------
# Public report builder (fail-closed scan).
# ---------------------------------------------------------------------------


def _build_unavailable_report(
    failure_reason_category: str,
    *,
    self_test_passed: bool,
    row_limit_requested: int,
    method: str,
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
    """Build a truthful ``unavailable_with_reason`` report.

    Records the real failure category without row-level values. No
    stale/fake pass.
    """
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
    # In unavailable mode, none of the "actually true" empirical flags
    # may be true. aggregate_only_public_artifact and diagnostic_only
    # remain true.
    safe_true["external_benchmark_rows_read"] = rows_fetched > 0
    safe_true["repositories_materialized_transiently"] = False
    safe_true["openlocus_retrieval_executed"] = False
    safe_true["score_py_metrics_computed"] = False
    safe_true["performance_smoke"] = False

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": "unavailable_with_reason",
        "mode": MODE,
        "phase": PHASE,
        "method": method,
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
        # No metrics in unavailable mode.
        "metrics": {},
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
            "signal_strength": "external_benchmark_retrieval_performance_smoke_unavailable",
            "is_full_external_benchmark_evaluation": False,
        },
    }

    # Fail-closed forbidden scan.
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _build_pass_report(
    *,
    self_test_passed: bool,
    row_limit_requested: int,
    rows_fetched: int,
    rows_evaluated: int,
    rows_successful: int,
    rows_failed: int,
    method: str,
    query_mode: str,
    language_filter: str,
    openlocus_binary_source: str,
    network_mode: str,
    network_calls: int,
    metrics: dict[str, Any],
    failure_category_counts: dict[str, int],
    partial: bool,
) -> dict[str, Any]:
    """Build a pass/partial report with aggregate metrics."""
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    for k, v in failure_category_counts.items():
        if k in fcc:
            fcc[k] = int(v)

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["external_benchmark_rows_read"] = rows_fetched > 0
    safe_true["repositories_materialized_transiently"] = rows_successful > 0
    safe_true["openlocus_retrieval_executed"] = rows_successful > 0
    safe_true["score_py_metrics_computed"] = bool(metrics)
    safe_true["performance_smoke"] = rows_successful > 0 and bool(metrics)

    status = "partial" if (partial or rows_failed > 0) else "pass"

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "method": method,
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
        "metrics": metrics,
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
            "signal_strength": "external_benchmark_retrieval_performance_smoke_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
        },
    }

    # Fail-closed forbidden scan.
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


# ---------------------------------------------------------------------------
# Network smoke runner (transient /tmp workspace; aggregate-only output).
# ---------------------------------------------------------------------------


def _run_network_smoke(
    *,
    row_limit: int,
    method: str,
    query_mode: str,
    language_filter: str,
    openlocus_bin: str,
    openlocus_binary_source: str,
    network_mode: str,
    eval_dir: Path,
    self_test_passed: bool,
) -> dict[str, Any]:
    """Run the real network smoke (transient /tmp; aggregate-only output).

    On any failure (network, clone, retrieval, score), produces a
    truthful ``unavailable_with_reason`` report.
    """
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    network_calls = 0

    # Step 1: fetch rows from HF datasets-server.
    rows, fetch_status, nc, fcc_update = _fetch_contextbench_rows(
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
            method=method,
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
    all_metrics_records: list[dict[str, Any]] = []

    # Step 2: for each row, materialize repo + run retrieval + score.
    # Use a single TemporaryDirectory for all transient JSONL; clone
    # each repo into its own sub-TemporaryDirectory to allow cleanup
    # between rows.
    with tempfile.TemporaryDirectory(
        prefix="c5_contextbench_smoke_"
    ) as work_root_str:
        work_root = Path(work_root_str)
        tasks_jsonl = work_root / "tasks.jsonl"
        labels_jsonl = work_root / "labels.jsonl"
        run_jsonl = work_root / "run.jsonl"

        for idx, row in enumerate(rows):
            rows_evaluated += 1
            # Parse gold_context into gold_paths/gold_lines (transient).
            gold_paths, gold_lines, gc_status = _parse_gold_context(
                row.get("gold_context")
            )
            if gc_status != "pass":
                fcc["gold_context_parse_failed"] += 1
                rows_failed += 1
                continue

            # Sanitize query (transient; never written to public).
            query = _sanitize_query(
                row.get("problem_statement", ""), query_mode
            )
            if not query:
                fcc["row_parse_failed"] += 1
                rows_failed += 1
                continue

            repo_url = row.get("repo_url", "")
            base_commit = row.get("base_commit", "")
            if not isinstance(repo_url, str) or not isinstance(
                base_commit, str
            ) or not repo_url or not base_commit:
                fcc["row_parse_failed"] += 1
                rows_failed += 1
                continue

            # Materialize repo under a per-row TemporaryDirectory.
            with tempfile.TemporaryDirectory(
                prefix=f"c5_repo_{idx}_"
            ) as repo_root_str:
                repo_work_dir = Path(repo_root_str)
                clone_ok, clone_fail_cat, clone_fcc = (
                    _clone_and_checkout(
                        repo_url, base_commit, repo_work_dir
                    )
                )
                for k, v in clone_fcc.items():
                    if k in fcc:
                        fcc[k] += v
                if not clone_ok:
                    rows_failed += 1
                    # Continue to next row; we report partial.
                    continue

                repo_root = repo_work_dir / "repo"

                # Write transient task/label JSONL for this single row.
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
                    _write_transient_jsonl(
                        tasks_jsonl, [task_record]
                    )
                    _write_transient_jsonl(
                        labels_jsonl, [label_record]
                    )
                except OSError:
                    fcc["task_jsonl_write_failed"] += 1
                    rows_failed += 1
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
                    rows_failed += 1
                    continue

                all_metrics_records.append(metrics)
                rows_successful += 1

            # Cleanup the per-row run.jsonl for the next iteration.
            try:
                run_jsonl.unlink()
            except OSError:
                pass

    # Step 3: aggregate metrics across successful rows.
    if not all_metrics_records:
        return _build_unavailable_report(
            "retrieval_failed",
            self_test_passed=self_test_passed,
            row_limit_requested=row_limit,
            method=method,
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

    # Aggregate: compute mean of each allowlisted numeric metric.
    aggregate: dict[str, Any] = {}
    for key in SCORE_METRIC_ALLOWLIST:
        values: list[Any] = []
        for rec in all_metrics_records:
            if key in rec:
                values.append(rec[key])
        if not values:
            continue
        if all(isinstance(v, bool) for v in values):
            # Boolean: majority True => True (at least one True).
            aggregate[key] = any(values)
        elif all(isinstance(v, (int, float)) for v in values):
            nums = [float(v) for v in values]
            mean = sum(nums) / len(nums)
            if isinstance(mean, float):
                aggregate[key] = round(mean, 6)
            else:
                aggregate[key] = int(mean)
        elif all(isinstance(v, str) for v in values):
            # String: use the first value (e.g. citation_validation_mode).
            aggregate[key] = str(values[0])

    # Filter to allowlist (defensive).
    aggregate = _filter_score_metrics(aggregate)

    # Add aggregate counts.
    aggregate["total_tasks"] = rows_successful
    aggregate["successful"] = sum(
        1
        for rec in all_metrics_records
        if rec.get("successful", 0) > 0
    )
    aggregate["success_rate"] = (
        aggregate["successful"] / rows_successful
        if rows_successful > 0
        else 0.0
    )

    partial = rows_failed > 0 or rows_successful < row_limit

    return _build_pass_report(
        self_test_passed=self_test_passed,
        row_limit_requested=row_limit,
        rows_fetched=rows_fetched,
        rows_evaluated=rows_evaluated,
        rows_successful=rows_successful,
        rows_failed=rows_failed,
        method=method,
        query_mode=query_mode,
        language_filter=language_filter,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        network_calls=network_calls,
        metrics=aggregate,
        failure_category_counts=fcc,
        partial=partial,
    )


# ---------------------------------------------------------------------------
# Self-test (no network; synthetic rows + synthetic score data).
# ---------------------------------------------------------------------------


def _build_synthetic_row() -> dict[str, Any]:
    """Build a synthetic ContextBench-like row for self-test.

    Values are deliberately synthetic placeholder strings. They are
    NEVER written to any public artifact; only the public/private
    separation and aggregation logic are validated.
    """
    return {
        "instance_id": "synthetic-c5-001",
        "original_inst_id": "synthetic-001",
        "repo": "synthetic/repo",
        "repo_url": "https://example.invalid/synthetic/repo",
        "language": "python",
        "base_commit": "0" * 40,
        "gold_context": json.dumps(
            [
                {
                    "file": "src/main.py",
                    "start_line": 10,
                    "end_line": 20,
                    "content": "synthetic gold content placeholder",
                }
            ]
        ),
        "patch": "synthetic patch placeholder",
        "test_patch": "synthetic test patch placeholder",
        "problem_statement": (
            "Synthetic problem statement placeholder.\n\n"
            "This is the second paragraph with more detail.\n"
            "It should not leak into the public artifact."
        ),
        "f2p": ["synthetic_test_a"],
        "p2p": ["synthetic_test_b"],
        "source": "synthetic_self_test",
    }


def _build_synthetic_metrics() -> dict[str, Any]:
    """Build synthetic score.py metrics for self-test (aggregate only)."""
    return {
        "total_tasks": 1,
        "successful": 1,
        "success_rate": 1.0,
        "avg_latency_ms": 42.0,
        "structural_validity": 1.0,
        "citation_validity": 1.0,
        "citation_hash_checked": False,
        "citation_validation_mode": "path_range_only",
        "file_recall@1": 1.0,
        "file_recall@5": 1.0,
        "file_recall@10": 1.0,
        "file_precision@5": 1.0,
        "file_precision@10": 1.0,
        "mrr": 1.0,
        "line_precision@10": 0.5,
        "line_recall@10": 0.5,
        "span_f0.5@10": 0.5,
        "token_waste_ratio@10": 0.0,
        "wrong_span_rate@10": 0.0,
        "zero_overlap_evidence_rate@10": 0.0,
    }


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all C5-A self-test groups (no network; synthetic data)."""
    checks: list[dict[str, Any]] = []

    # --- Group 1: Artifact identity fields. ---
    skeleton = _build_pass_report(
        self_test_passed=True,
        row_limit_requested=1,
        rows_fetched=1,
        rows_evaluated=1,
        rows_successful=1,
        rows_failed=0,
        method=DEFAULT_METHOD,
        query_mode=DEFAULT_QUERY_MODE,
        language_filter=DEFAULT_LANGUAGE_FILTER,
        openlocus_binary_source="default",
        network_mode="local_explicit",
        network_calls=0,
        metrics=_filter_score_metrics(_build_synthetic_metrics()),
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES},
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
            "status_pass_when_self_test_passed",
            skeleton["status"] == "pass",
        )
    )

    # --- Group 2: Safe true flags (default-mode skeleton). ---
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
            "safe_true_external_benchmark_rows_read",
            skeleton.get("external_benchmark_rows_read") is True,
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
    checks.append(
        _check(
            "safe_true_performance_smoke",
            skeleton.get("performance_smoke") is True,
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

    # --- Group 5: Forbidden scanner rejects (fail-closed). ---
    checks.append(
        _check(
            "scanner_rejects_repo_url_value",
            bool(_scan_forbidden({"leaked": "https://github.com/foo/bar"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_repo_slug_value",
            bool(_scan_forbidden({"leaked": "astropy/astropy"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_commit_sha_value",
            bool(
                _scan_forbidden(
                    {"leaked": "838e432e3e5519c5383d12018e6c78f8ec7833c1"}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_repo_key",
            bool(_scan_forbidden({"repo": "astropy/astropy"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_repo_url_key",
            bool(_scan_forbidden({"repo_url": "x"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_base_commit_key",
            bool(_scan_forbidden({"base_commit": "x"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_instance_id_key",
            bool(_scan_forbidden({"instance_id": "x"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_problem_statement_key",
            bool(_scan_forbidden({"problem_statement": "x"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_gold_context_key",
            bool(_scan_forbidden({"gold_context": "x"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_gold_paths_key",
            bool(_scan_forbidden({"gold_paths": ["x"]})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_gold_lines_key",
            bool(_scan_forbidden({"gold_lines": [[1, 2]]})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_query_key",
            bool(_scan_forbidden({"query": "x"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_path_key",
            bool(_scan_forbidden({"path": "src/main.py"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_file_path_value",
            bool(_scan_forbidden({"leaked": "src/main.py"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_line_range_value",
            bool(_scan_forbidden({"leaked": "12-34"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_hex_digest_value",
            bool(
                _scan_forbidden(
                    {"leaked": "a" * 32}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_secret_like_value",
            bool(_scan_forbidden({"leaked": "api_key=sk-abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_tmp_path_value",
            bool(_scan_forbidden({"leaked": "/tmp/foo"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_task_id_value",
            bool(_scan_forbidden({"leaked": "task_001"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_patch_marker_value",
            bool(_scan_forbidden({"leaked": "--- a/foo.py\n+++ b/foo.py"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_stack_trace_value",
            bool(
                _scan_forbidden(
                    {"leaked": "Traceback (most recent call last)"}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_sentinel_value",
            bool(_scan_forbidden({"leaked": _SECRET_SENTINEL})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_multiline_value",
            bool(_scan_forbidden({"leaked": "line1\nline2"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_raw_json_fragment",
            bool(_scan_forbidden({"leaked": '{"key": "value"}'})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_long_string",
            bool(_scan_forbidden({"leaked": "x" * 300})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_forbidden_field_name_value",
            bool(_scan_forbidden({"leaked": "content_sha"})),
        )
    )

    # --- Group 6: Forbidden scanner allows safe values. ---
    checks.append(
        _check(
            "scanner_allows_method_value",
            not _scan_forbidden({"method": "bm25"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_query_mode_value",
            not _scan_forbidden({"query_mode": "first_paragraph"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_language_filter_value",
            not _scan_forbidden({"language_filter": "python"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_network_mode_value",
            not _scan_forbidden({"network_mode": "local_explicit"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_metric_value",
            not _scan_forbidden({"metrics": {"mrr": 0.5}}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_failure_category_count",
            not _scan_forbidden(
                {
                    "failure_category_counts": {
                        "clone_failed": 1,
                        "network_fetch_failed": 0,
                    }
                }
            ),
        )
    )

    # --- Group 7: Query sanitizer (in-memory; no raw value leak). ---
    sample_ps = (
        "## Title\n\n"
        "First paragraph with the actual problem description.\n\n"
        "<!-- hidden comment -->\n\n"
        "Second paragraph with more detail.\n\n"
        "```python\nprint('hello')\n```"
    )
    q1 = _sanitize_query(sample_ps, "first_paragraph")
    checks.append(
        _check(
            "sanitizer_first_paragraph_nonempty",
            isinstance(q1, str) and len(q1) > 0,
        )
    )
    checks.append(
        _check(
            "sanitizer_first_paragraph_no_html_comment",
            "<!--" not in q1 and "-->" not in q1,
        )
    )
    checks.append(
        _check(
            "sanitizer_first_paragraph_no_code_fence",
            "```" not in q1,
        )
    )
    checks.append(
        _check(
            "sanitizer_first_paragraph_no_markdown_header",
            "##" not in q1,
        )
    )
    q2 = _sanitize_query(sample_ps, "first_sentence")
    checks.append(
        _check(
            "sanitizer_first_sentence_nonempty",
            isinstance(q2, str) and len(q2) > 0,
        )
    )
    q3 = _sanitize_query(sample_ps, "raw")
    checks.append(
        _check(
            "sanitizer_raw_nonempty",
            isinstance(q3, str) and len(q3) > 0,
        )
    )
    checks.append(
        _check(
            "sanitizer_first_paragraph_capped",
            len(q1) <= 500,
        )
    )
    checks.append(
        _check(
            "sanitizer_first_sentence_capped",
            len(q2) <= 200,
        )
    )
    checks.append(
        _check(
            "sanitizer_raw_capped",
            len(q3) <= 1000,
        )
    )
    # Sanitizer does not emit raw values in public artifact (the query
    # itself is never written to the public artifact).
    sample_report_with_query = {"query": q1}
    checks.append(
        _check(
            "sanitizer_query_never_in_public_artifact",
            bool(_scan_forbidden(sample_report_with_query)),
        )
    )

    # --- Group 8: Gold context parser (in-memory; no raw value leak). ---
    row = _build_synthetic_row()
    gold_paths, gold_lines, gc_status = _parse_gold_context(
        row["gold_context"]
    )
    checks.append(
        _check(
            "gold_parser_pass_status",
            gc_status == "pass",
        )
    )
    checks.append(
        _check(
            "gold_parser_extracts_paths",
            len(gold_paths) == 1,
        )
    )
    checks.append(
        _check(
            "gold_parser_extracts_lines",
            len(gold_lines) == 1 and gold_lines[0] == [10, 20],
        )
    )
    checks.append(
        _check(
            "gold_parser_rejects_invalid_json",
            _parse_gold_context("not json")[2]
            == "gold_context_parse_failed",
        )
    )
    checks.append(
        _check(
            "gold_parser_rejects_missing_file",
            _parse_gold_context(
                json.dumps([{"start_line": 1, "end_line": 2}])
            )[2]
            == "gold_context_parse_failed",
        )
    )
    checks.append(
        _check(
            "gold_parser_rejects_inverted_range",
            _parse_gold_context(
                json.dumps(
                    [
                        {
                            "file": "x.py",
                            "start_line": 20,
                            "end_line": 10,
                        }
                    ]
                )
            )[2]
            == "gold_context_parse_failed",
        )
    )
    # gold_paths / gold_lines must never appear in public artifact.
    sample_report_with_gold = {
        "gold_paths": gold_paths,
        "gold_lines": gold_lines,
    }
    checks.append(
        _check(
            "gold_paths_never_in_public_artifact",
            bool(_scan_forbidden(sample_report_with_gold)),
        )
    )

    # --- Group 9: Score metric allowlist (no dynamic row IDs or paths). ---
    raw_metrics = _build_synthetic_metrics()
    # Inject a forbidden dynamic key that must be filtered out.
    raw_metrics["row_id"] = "should_be_filtered"
    raw_metrics["path"] = "src/main.py"
    raw_metrics["content_sha"] = "a" * 64
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
            "score_filter_includes_mrr",
            "mrr" in filtered,
        )
    )
    checks.append(
        _check(
            "score_filter_includes_file_recall",
            "file_recall@1" in filtered,
        )
    )

    # --- Group 10: Failure category counts fixed enum. ---
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    fcc["clone_failed"] = 1
    sample_fail_report = {
        "failure_category_counts": fcc,
    }
    checks.append(
        _check(
            "failure_category_counts_in_enum",
            not _scan_forbidden(sample_fail_report),
        )
    )
    # Inject a non-enum failure category — must be rejected by the
    # builder (it only accepts enum keys).
    bad_fcc = dict(fcc)
    bad_fcc["not_a_real_category"] = 1
    rebuilt = _build_unavailable_report(
        "clone_failed",
        self_test_passed=True,
        row_limit_requested=1,
        method=DEFAULT_METHOD,
        query_mode=DEFAULT_QUERY_MODE,
        language_filter=DEFAULT_LANGUAGE_FILTER,
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

    # --- Group 11: Row limit cap. ---
    checks.append(
        _check(
            "row_limit_default_5",
            ROW_LIMIT_DEFAULT == 5,
        )
    )
    checks.append(
        _check(
            "row_limit_hard_cap_20",
            ROW_LIMIT_HARD_CAP == 20,
        )
    )

    # --- Group 12: Unavailable report (truthful; no stale/fake pass). ---
    unavail = _build_unavailable_report(
        "network_fetch_failed",
        self_test_passed=True,
        row_limit_requested=5,
        method=DEFAULT_METHOD,
        query_mode=DEFAULT_QUERY_MODE,
        language_filter=DEFAULT_LANGUAGE_FILTER,
        openlocus_binary_source="default",
        network_mode="local_explicit",
        rows_fetched=0,
        network_calls=1,
        failure_category_counts=fcc,
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
            unavail["failure_reason_category"] == "network_fetch_failed",
        )
    )
    checks.append(
        _check(
            "unavailable_no_performance_smoke_flag",
            unavail["performance_smoke"] is False,
        )
    )
    checks.append(
        _check(
            "unavailable_no_external_benchmark_performance_claimed",
            unavail["external_benchmark_performance_claimed"] is False,
        )
    )
    checks.append(
        _check(
            "unavailable_no_metrics",
            unavail["metrics"] == {},
        )
    )
    checks.append(
        _check(
            "unavailable_forbidden_scan_pass",
            unavail["forbidden_scan"]["status"] == "pass",
        )
    )

    # --- Group 13: Fail-closed generation. ---
    try:
        _enforce_no_forbidden(skeleton)
        checks.append(
            _check("fail_closed_clean_report_no_raise", True)
        )
    except SystemExit:
        checks.append(
            _check("fail_closed_clean_report_no_raise", False)
        )

    leaked_report = dict(skeleton)
    leaked_report["leaked_repo"] = "astropy/astropy"
    try:
        _enforce_no_forbidden(leaked_report)
        checks.append(
            _check("fail_closed_leaked_report_raises", False)
        )
    except SystemExit:
        checks.append(
            _check("fail_closed_leaked_report_raises", True)
        )

    failed_self_test_report = dict(skeleton)
    failed_self_test_report["self_test_passed"] = False
    try:
        _refuse_on_self_test_failure(failed_self_test_report)
        checks.append(
            _check("refuse_on_self_test_failure_raises", False)
        )
    except SystemExit:
        checks.append(
            _check("refuse_on_self_test_failure_raises", True)
        )

    try:
        _refuse_on_self_test_failure(skeleton)
        checks.append(
            _check("refuse_on_self_test_pass_no_raise", True)
        )
    except SystemExit:
        checks.append(
            _check("refuse_on_self_test_pass_no_raise", False)
        )

    # --- Group 14: Public artifact self-scan is clean. ---
    checks.append(
        _check(
            "public_artifact_self_scan_clean",
            not _scan_forbidden(skeleton),
        )
    )
    checks.append(
        _check(
            "unavailable_self_scan_clean",
            not _scan_forbidden(unavail),
        )
    )

    # --- Group 15: CLI argument surface. ---
    parser = build_parser()
    option_strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            option_strings.add(opt)
    for required_opt in (
        "--self-test",
        "--row-limit",
        "--method",
        "--query-mode",
        "--language-filter",
        "--openlocus",
        "--out",
    ):
        checks.append(
            _check(
                f"cli_has_option_{required_opt}",
                required_opt in option_strings,
            )
        )

    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class SafeArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that never echoes unknown/private-looking args.

    A caller may pass a private-looking argument by mistake; default
    argparse would echo the unknown argument and value into stderr.
    Keep the usage line but replace the raw error with a fixed generic
    message.
    """

    def error(self, message: str) -> NoReturn:  # noqa: D401 - argparse signature
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    """Build the C5-A CLI parser."""
    ap = SafeArgumentParser(
        description=(
            "C5-A ContextBench verified retrieval performance smoke "
            "(public aggregate-only artifact; bounded ContextBench "
            "verified subset; transient /tmp clone + retrieval + score; "
            "no provider calls; no raw rows/queries/repo URLs/commits/"
            "gold paths/spans/generated JSONL/evidence rows/cloned repos/"
            "stdout/stderr committed)."
        )
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="run deterministic self-test groups and exit (no artifact written, no network)",
    )
    ap.add_argument(
        "--row-limit",
        type=int,
        default=ROW_LIMIT_DEFAULT,
        help=(
            "number of ContextBench verified rows to evaluate (default: "
            f"{ROW_LIMIT_DEFAULT}; hard cap {ROW_LIMIT_HARD_CAP})"
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
        "--query-mode",
        default=DEFAULT_QUERY_MODE,
        choices=ALLOWED_QUERY_MODES,
        help=(
            "query sanitizer mode (default: first_paragraph; allowed: "
            f"{', '.join(ALLOWED_QUERY_MODES)})"
        ),
    )
    ap.add_argument(
        "--language-filter",
        default=DEFAULT_LANGUAGE_FILTER,
        choices=ALLOWED_LANGUAGE_FILTERS,
        help=(
            "language filter category (default: python; allowed: "
            f"{', '.join(ALLOWED_LANGUAGE_FILTERS)})"
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


def _validate_row_limit(row_limit: int) -> int:
    """Validate and cap --row-limit to the hard cap."""
    if not isinstance(row_limit, int):
        raise SystemExit("invalid arguments")
    if row_limit < 1:
        raise SystemExit("invalid arguments")
    if row_limit > ROW_LIMIT_HARD_CAP:
        return ROW_LIMIT_HARD_CAP
    return row_limit


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
    method = args.method
    query_mode = args.query_mode
    language_filter = args.language_filter
    out_path = args.out if args.out is not None else DEFAULT_OUT

    # Self-test must pass before any artifact is written.
    checks, self_test_passed = run_self_test_checks()
    if not self_test_passed:
        # Refuse to write any artifact if self-test failed.
        print(
            "error: self-test failed; refusing to write artifact",
            file=sys.stderr,
        )
        sys.exit(1)

    # Resolve OpenLocus binary.
    openlocus_bin, openlocus_source = _resolve_openlocus_binary(
        args.openlocus
    )
    if openlocus_bin is None:
        # OpenLocus binary missing; produce truthful unavailable report.
        report = _build_unavailable_report(
            "retrieval_failed",
            self_test_passed=self_test_passed,
            row_limit_requested=row_limit,
            method=method,
            query_mode=query_mode,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_source,
            network_mode="local_explicit",
        )
        _enforce_no_forbidden(report)
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

    # Determine network mode (always local_explicit from CLI; CI uses
    # workflow_dispatch_opt_in).
    network_mode = "local_explicit"

    # Run the network smoke (transient /tmp; aggregate-only output).
    eval_dir = Path(__file__).resolve().parent
    try:
        report = _run_network_smoke(
            row_limit=row_limit,
            method=method,
            query_mode=query_mode,
            language_filter=language_filter,
            openlocus_bin=openlocus_bin,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
            eval_dir=eval_dir,
            self_test_passed=self_test_passed,
        )
    except (OSError, subprocess.SubprocessError):
        # Sanitize errors: do not print raw paths or subprocess output.
        report = _build_unavailable_report(
            "unexpected_exception",
            self_test_passed=self_test_passed,
            row_limit_requested=row_limit,
            method=method,
            query_mode=query_mode,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
        )

    # Strict fail-closed guard immediately before writing the JSON artifact.
    _enforce_no_forbidden(report)
    _write_json(out_path, report)
    print(
        f"wrote artifact "
        f"(forbidden_scan={report['forbidden_scan']['status']}, "
        f"self_test_passed={report['self_test_passed']}, "
        f"status={report['status']}, "
        f"phase={report['phase']}, "
        f"method={report['method']}, "
        f"rows_fetched={report['rows_fetched']}, "
        f"rows_successful={report['rows_successful']})"
    )


if __name__ == "__main__":
    main()
