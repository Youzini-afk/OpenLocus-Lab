#!/usr/bin/env python3
"""C4.5 RepoQA Source / Schema-Contract Readiness (adapter deferred).

This module implements C4.5 source/schema-contract readiness for the
EvalPlus **RepoQA** benchmark (task: **Searching Needle Function / SNF**).
It is **not** an adapter module, **not** a schema-readiness module, and
**not** a benchmark-result module. The schema contract is known from
official source/docs/loader, but full adapter/row-map benchmark support
is **deferred** pending a conscious derived-qrels/version/license
decision. No RepoQA entry is added to ``eval/c4_external_benchmark_adapters.py``.

Wrong-target disambiguation (binding): the canonical target is EvalPlus
RepoQA/SNF, NOT ``Nutanix/RepoQA-neo4j``, ``microsoft/SCBench``
``scbench_repoqa``, ``CodeRepoQA``, ``SWE-QA-Bench``, ``CoReQA``,
``RepoExec``, ``RepoBench``, or ``SWE-QA-Pro``.

Public-artifact contract (binding):

* aggregate-only public output;
* NEVER download or decompress the monolithic ``.json.gz`` release asset;
* NEVER read or persist raw rows, repo names, function names, file paths,
  byte/line ranges, descriptions, questions, answers, labels, qrels,
  patches/tests, code snippets, content hashes, raw payloads, provider
  payloads, or row-level URLs;
* no row-level hashes (hashes are row-level derived data);
* no-claim flags all false: ``promotion_ready``,
  ``default_should_change``, ``evidencecore_semantics_changed``,
  ``runtime_clean_general_algorithm_claimed``,
  ``downstream_agent_value_proven``, ``ood_temporal_supported``,
  ``quiver_systems_supported``;
* ``adapter_support_claimed=false``,
  ``schema_readiness_claimed=false``,
  ``public_row_schema_readiness_claimed=false``,
  ``schema_contract_readiness_claimed=true``,
  ``row_map_smoke_attempted=false``, ``row_map_smoke_passed=false``,
  ``benchmark_result_claimed=false``;
* ``release_asset_downloaded=false``,
  ``release_asset_decompressed=false``,
  ``release_asset_body_read=false``,
  ``monolithic_json_rows_read=false``.

Claim boundary: this module emits ``claim_level =
source_schema_contract_readiness_adapter_deferred_only`` evidence. It
does NOT claim adapter support, schema readiness, public row schema
readiness, row-map smoke pass, benchmark result, downstream agent value,
OOD temporal support, or QuIVer systems support. The status is
``source_confirmed_schema_contract_ready_adapter_deferred`` (not
``pass``/``support``). Synthetic self-test fixtures confer NO empirical
support.

Run::

    python3 -m py_compile eval/c4_repoqa_source_readiness.py
    python3 eval/c4_repoqa_source_readiness.py --self-test
    python3 eval/c4_repoqa_source_readiness.py \\
        --out artifacts/c4_external_benchmark_adapters/\\
c4_repoqa_source_readiness_report.json
    python3 eval/c4_repoqa_source_readiness.py --offline \\
        --out /tmp/c4_repoqa_offline.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "c4_repoqa_source_readiness.v1"
GENERATED_BY = "eval/c4_repoqa_source_readiness.py"
CLAIM_LEVEL = "source_schema_contract_readiness_adapter_deferred_only"
BENCHMARK = "repoqa"
TARGET_STATUS = "source_confirmed_schema_contract_ready_adapter_deferred"

DEFAULT_OUT = Path(
    "artifacts/c4_external_benchmark_adapters/"
    "c4_repoqa_source_readiness_report.json"
)

# Bounded timeout for every HTTP probe.
PROBE_TIMEOUT_SECONDS = 10

# The exact target title (from arXiv:2406.06025 / OpenReview).
TARGET_TITLE = (
    "RepoQA: Evaluating Long Context Code Understanding"
    " via Searching Needle Function"
)
TARGET_TASK = "searching_needle_function"
ARXIV_ID = "2406.06025"
ARXIV_ABS_URL = "https://arxiv.org/abs/2406.06025"
ARXIV_PDF_URL = "https://arxiv.org/pdf/2406.06025"
OPENREVIEW_URL = "https://openreview.net/forum?id=hK9YSrFuGf"
HOMEPAGE_URL = "https://evalplus.github.io/repoqa.html"

# Code repo (source-level public URL, not row-level).
CODE_REPO_ID = "evalplus/repoqa"
CODE_REPO_URL = "https://github.com/evalplus/repoqa"
CODE_REPO_API_URL = "https://api.github.com/repos/evalplus/repoqa"

# Dataset release repo (source-level public URL, not row-level).
RELEASE_REPO_ID = "evalplus/repoqa_release"
RELEASE_REPO_URL = "https://github.com/evalplus/repoqa_release"
RELEASE_REPO_API_URL = "https://api.github.com/repos/evalplus/repoqa_release"

# Release tag / asset metadata (source-level, not row-level).
RELEASE_TAG_CURRENT = "2024-06-23"
RELEASE_TAG_PAPER = "2024-04-20"
RELEASE_API_URL_CURRENT = (
    f"https://api.github.com/repos/evalplus/repoqa_release"
    f"/releases/tags/{RELEASE_TAG_CURRENT}"
)
ASSET_URL_CURRENT = (
    f"https://github.com/evalplus/repoqa_release/releases/download/"
    f"{RELEASE_TAG_CURRENT}/repoqa-{RELEASE_TAG_CURRENT}.json.gz"
)
ASSET_URL_PAPER = (
    f"https://github.com/evalplus/repoqa_release/releases/download/"
    f"{RELEASE_TAG_PAPER}/repoqa-{RELEASE_TAG_PAPER}.json.gz"
)
ASSET_NAME_CURRENT = f"repoqa-{RELEASE_TAG_CURRENT}.json.gz"
ASSET_NAME_PAPER = f"repoqa-{RELEASE_TAG_PAPER}.json.gz"

# Wrong targets (binding disambiguation). These are exclusion metadata,
# not row-level data. Stored as reason strings only.
WRONG_TARGET_EXCLUSIONS: list[dict[str, str]] = [
    {
        "excluded_target": "Nutanix/RepoQA-neo4j",
        "exclusion_reason": (
            "unrelated HuggingFace dataset; not EvalPlus RepoQA/SNF"
        ),
    },
    {
        "excluded_target": "microsoft/SCBench:scbench_repoqa",
        "exclusion_reason": (
            "SCBench subset with a similar name; not EvalPlus RepoQA/SNF"
        ),
    },
    {
        "excluded_target": "CodeRepoQA",
        "exclusion_reason": (
            "similar name; different benchmark; not EvalPlus RepoQA/SNF"
        ),
    },
    {
        "excluded_target": "SWE-QA-Bench",
        "exclusion_reason": (
            "similar name; different benchmark; not EvalPlus RepoQA/SNF"
        ),
    },
    {
        "excluded_target": "CoReQA",
        "exclusion_reason": (
            "similar name; different benchmark; not EvalPlus RepoQA/SNF"
        ),
    },
    {
        "excluded_target": "RepoExec",
        "exclusion_reason": (
            "different benchmark; not EvalPlus RepoQA/SNF"
        ),
    },
    {
        "excluded_target": "RepoBench",
        "exclusion_reason": (
            "different benchmark; not EvalPlus RepoQA/SNF"
        ),
    },
    {
        "excluded_target": "SWE-QA-Pro",
        "exclusion_reason": (
            "different benchmark; not EvalPlus RepoQA/SNF"
        ),
    },
]

# Paper aggregate facts (paper-level, not row-level). From the RepoQA
# paper/homepage: 5 languages x 10 repos x 10 needles = 500 code-search
# tasks over 50 repositories.
PAPER_AGGREGATE_FACTS: dict[str, Any] = {
    "paper_aggregate_only": True,
    "languages_per_paper": 5,
    "repos_per_language_per_paper": 10,
    "needles_per_repo_per_paper": 10,
    "total_repos_per_paper": 50,
    "total_tasks_per_paper": 500,
}

# Version skew: paper describes 5 languages; current loader default
# (2024-06-23) adds Go support (6 languages). Recorded as source-level
# release metadata, not row-level data.
VERSION_SKEW: dict[str, Any] = {
    "paper_homepage_version": RELEASE_TAG_PAPER,
    "current_loader_default_version": RELEASE_TAG_CURRENT,
    "paper_languages": 5,
    "current_loader_languages": 6,
    "version_skew_noted": True,
    "go_added_in_current_loader_default": True,
}

# Schema contract field-name categories (schema-only observations, NOT
# row-level data). These are the field NAMES from the official
# source/docs/loader, recorded ONLY under explicit schema-contract
# containers. The forbidden scanner allows them here but rejects them
# as row-like dict keys/values elsewhere.
REPO_RECORD_CONTRACT_FIELDS: tuple[str, ...] = (
    "repo",
    "commit_sha",
    "entrypoint_path",
    "topic",
    "content",
    "dependency",
    "needles",
)
NEEDLE_CONTRACT_FIELDS: tuple[str, ...] = (
    "path",
    "name",
    "start_byte",
    "end_byte",
    "start_line",
    "end_line",
    "description",
)
TASK_RECORD_CONTRACT_FIELDS: tuple[str, ...] = (
    "language",
    "repo_record",
    "needles",
)
MODEL_OUTPUT_CONTRACT_FIELDS: tuple[str, ...] = (
    "model_name",
    "generation",
    "predicted_function",
)
ADAPTER_DERIVED_PRIVATE_FIELD_CATEGORIES: tuple[str, ...] = (
    "model_output",
    "predicted_function",
    "generation",
    "task_id",
)
SCHEMA_CONTRACT_FIELD_NAMES: tuple[str, ...] = (
    REPO_RECORD_CONTRACT_FIELDS + NEEDLE_CONTRACT_FIELDS
)

# Approved contract strings: the ONLY string values allowed inside
# schema-contract containers. Built from existing field-name constants.
# Any string not in this set appearing as a value inside a schema-contract
# container is a violation (unapproved_contract_string).
APPROVED_CONTRACT_STRINGS: frozenset[str] = frozenset(
    set(REPO_RECORD_CONTRACT_FIELDS)
    | set(NEEDLE_CONTRACT_FIELDS)
    | set(TASK_RECORD_CONTRACT_FIELDS)
    | set(MODEL_OUTPUT_CONTRACT_FIELDS)
    | set(ADAPTER_DERIVED_PRIVATE_FIELD_CATEGORIES)
    | set(SCHEMA_CONTRACT_FIELD_NAMES)
)

# Top-level no-claim flags. ALL must be false.
NO_CLAIM_FLAGS: tuple[str, ...] = (
    "promotion_ready",
    "default_should_change",
    "evidencecore_semantics_changed",
    "runtime_clean_general_algorithm_claimed",
    "downstream_agent_value_proven",
    "ood_temporal_supported",
    "quiver_systems_supported",
)

# ---------------------------------------------------------------------------
# Forbidden-output scanner (RepoQA source/schema-contract specific)
# ---------------------------------------------------------------------------

# Sensitive KEY names that must NEVER appear as dict keys anywhere in a
# public JSON output (except under schema-contract containers). These are
# RepoQA row-level data field names plus general row-level/payload field
# names.
FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset(
    {
        # RepoQA repo-record fields
        "repo",
        "commit_sha",
        "entrypoint_path",
        "topic",
        "content",
        "dependency",
        "needles",
        # RepoQA needle fields
        "path",
        "name",
        "start_byte",
        "end_byte",
        "start_line",
        "end_line",
        "description",
        # Row-level data containers
        "raw_rows",
        "row_level_values",
        "row_values",
        "rows",
        "records",
        "tasks",
        # Code/snippet fields
        "snippet",
        "snippets",
        "code_snippet",
        "source_code",
        "gold_code",
        # Q&A fields
        "answer",
        "question",
        "query",
        "gold_answer",
        "predicted_answer",
        # Label/qrel fields
        "qrels",
        "label",
        "labels",
        "gold_labels",
        # Patch/test fields
        "patch",
        "test_patch",
        "tests",
        # Hash/digest fields
        "content_sha",
        "hash",
        "digest",
        "sha256",
        "md5",
        # Raw payload fields
        "raw_payload",
        "provider_payload",
        "api_response",
        "response_body",
        # Model output fields
        "model_output",
        "model_response",
        # IDs
        "task_id",
        "instance_id",
        "row_id",
        # Secrets
        "api_key",
        "api_token",
        "api_secret",
        "base_url",
        "provider_key",
        "authorization",
    }
)

# Container key names under which sensitive field-name strings MAY appear
# as values (these are schema-only observations, NOT row-level data).
SCHEMA_ONLY_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "repo_record_contract_fields",
        "needle_contract_fields",
        "task_record_contract_fields",
        "model_output_contract_fields",
        "adapter_derived_private_field_categories",
        "schema_contract_field_names",
    }
)

# Known-safe provenance value paths (allowlisted for hex_digest/path_like
# value checks only).
SAFE_VALUE_KEY_NAMES: frozenset[str] = frozenset(
    {
        "schema_version",
        "generated_by",
        "claim_level",
        "benchmark",
        "target_title",
        "target_task",
        "arxiv_id",
        "arxiv_abs_url",
        "arxiv_pdf_url",
        "openreview_url",
        "homepage_url",
        "code_repo",
        "code_repo_url",
        "code_repo_api_url",
        "release_repo",
        "release_repo_url",
        "release_repo_api_url",
        "release_api_url",
        "asset_url_current",
        "asset_url_paper",
        "status",
    }
)

# Official source-level URLs that ARE allowed as values (verified public
# arXiv / OpenReview / homepage / GitHub / GitHub-API URLs, not row-level).
ALLOWED_SOURCE_URLS: frozenset[str] = frozenset(
    {
        ARXIV_ABS_URL,
        ARXIV_PDF_URL,
        OPENREVIEW_URL,
        HOMEPAGE_URL,
        CODE_REPO_URL,
        CODE_REPO_API_URL,
        RELEASE_REPO_URL,
        RELEASE_REPO_API_URL,
        RELEASE_API_URL_CURRENT,
        ASSET_URL_CURRENT,
        ASSET_URL_PAPER,
    }
)

# Value patterns that indicate leaked row-level data.
_RE_URL_VALUE = re.compile(r"https?://", re.IGNORECASE)
_RE_HEX_DIGEST = re.compile(r"[A-Fa-f0-9]{32,}")
_RE_SECRET_LIKE = re.compile(
    r"(?:api[_-]?key|api[_-]?token|api[_-]?secret|base[_-]?url"
    r"|provider[_-]?key|authorization[_-]?bearer)",
    re.IGNORECASE,
)
_FILE_EXT = (
    r"py|rs|ts|tsx|js|jsx|go|java|c|cpp|cc|h|hpp|hh|md|json|toml|"
    r"yaml|yml|txt|sh|rb|php|kt|swift|patch|diff|csv|parquet"
)
_RE_FILE_PATH_VALUE = re.compile(
    rf"/[A-Za-z0-9._/\-]+\.(?:{_FILE_EXT})\b"
)
_RE_LINE_RANGE_VALUE = re.compile(r"\b\d+\s*[:\-]\s*\d+\b")
# Raw JSON fragment: starts with {/[, then a quoted key, then :.
_RE_RAW_JSON = re.compile(r'^\s*[\{\[]\s*"[^"]+"\s*:')


def _path_last_key(path: str) -> str:
    """Extract the last key segment from a dotted JSON path."""
    last = path.rsplit(".", 1)[-1]
    return last.split("[")[0]


def _is_safe_value_path(path: str) -> bool:
    """Check if a JSON path ends with a known-safe value key."""
    return _path_last_key(path) in SAFE_VALUE_KEY_NAMES


def _is_allowed_source_url(value: str) -> bool:
    """Check if a string value is exactly an allowed source-level URL."""
    return value in ALLOWED_SOURCE_URLS


def _scan_forbidden(
    obj: Any,
    path: str = "$",
    in_schema_container: bool = False,
) -> list[dict[str, Any]]:
    """Strict recursive scanner for public JSON outputs.

    Returns a list of violation dicts with ``category`` and ``path``
    (JSON path), NEVER the leaked value itself. Fail-closed: any
    violation means the public output would leak.

    Allows official source-level URLs (arXiv / OpenReview / homepage /
    GitHub / GitHub-API / release-asset URLs) but forbids row-level URLs,
    paths, spans, snippets, raw payloads, content hashes, descriptions,
    questions, answers, and raw JSON fragments.

    Schema contract field names (``repo``, ``content``, ``needles``,
    ``path``, ``start_line``, ``description``, etc.) are allowed ONLY as
    exact string values from ``APPROVED_CONTRACT_STRINGS`` inside
    schema-contract containers. They are NEVER allowed as dict keys
    (the forbidden dict-key check is NOT relaxed inside schema-contract
    containers). Dict objects are forbidden inside schema-contract
    containers (row-like objects). Unapproved strings inside
    schema-contract containers are rejected.
    """
    violations: list[dict[str, Any]] = []

    if isinstance(obj, dict):
        # Forbid dict objects inside schema-contract containers
        # (row-like objects, e.g. [{"repo": "pytorch/pytorch"}]).
        if in_schema_container:
            violations.append(
                {
                    "category": "dict_in_schema_container",
                    "path": path,
                }
            )
        for key, value in obj.items():
            key_str = str(key)
            sub_path = f"{path}.{key_str}"
            is_schema_container = key_str in SCHEMA_ONLY_CONTAINER_KEYS
            # Forbid sensitive key names ANYWHERE as dict keys.
            # This check is NOT relaxed inside schema-contract containers:
            # field names are only allowed as list/string VALUES, never as
            # dict keys.
            if key_str in FORBIDDEN_KEY_NAMES:
                violations.append(
                    {
                        "category": "forbidden_key",
                        "path": sub_path,
                    }
                )
            violations.extend(
                _scan_forbidden(
                    value,
                    sub_path,
                    in_schema_container=is_schema_container
                    or in_schema_container,
                )
            )
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(
                _scan_forbidden(
                    value,
                    f"{path}[{idx}]",
                    in_schema_container=in_schema_container,
                )
            )
    elif isinstance(obj, str):
        safe_value = _is_safe_value_path(path)
        allowed_url = _is_allowed_source_url(obj)

        if in_schema_container:
            # In schema-contract containers, ONLY allow exact approved
            # contract strings from APPROVED_CONTRACT_STRINGS. Any other
            # string is a violation.
            if obj not in APPROVED_CONTRACT_STRINGS:
                violations.append(
                    {
                        "category": "unapproved_contract_string",
                        "path": path,
                    }
                )
            # Defense-in-depth: still check dangerous patterns even for
            # approved strings (approved set members won't match, but
            # this keeps the scanner robust if the set is ever extended).
            if "\n" in obj:
                violations.append(
                    {"category": "multiline_value", "path": path}
                )
            if _RE_URL_VALUE.search(obj) and not allowed_url:
                violations.append(
                    {"category": "url_value", "path": path}
                )
            if not safe_value and _RE_HEX_DIGEST.search(obj):
                violations.append(
                    {"category": "hex_digest_value", "path": path}
                )
            if _RE_FILE_PATH_VALUE.search(obj) and not safe_value:
                violations.append(
                    {"category": "path_like_value", "path": path}
                )
            if _RE_RAW_JSON.search(obj):
                violations.append(
                    {"category": "raw_json_fragment", "path": path}
                )
        else:
            # Non-schema-container context: full checks.
            if len(obj) > 256:
                violations.append(
                    {"category": "long_string", "path": path}
                )
            elif _RE_URL_VALUE.search(obj) and not allowed_url and not safe_value:
                violations.append(
                    {"category": "url_value", "path": path}
                )
            elif not safe_value and not allowed_url and _RE_HEX_DIGEST.search(obj):
                violations.append(
                    {"category": "hex_digest_value", "path": path}
                )
            elif _RE_SECRET_LIKE.search(obj):
                violations.append(
                    {"category": "secret_like_value", "path": path}
                )
            elif (
                _RE_FILE_PATH_VALUE.search(obj)
                and not safe_value
                and not allowed_url
            ):
                violations.append(
                    {"category": "path_like_value", "path": path}
                )
            elif "\n" in obj:
                violations.append(
                    {"category": "multiline_value", "path": path}
                )
            elif _RE_RAW_JSON.search(obj):
                violations.append(
                    {"category": "raw_json_fragment", "path": path}
                )
            else:
                # A raw line-range value: "12-34" or "12:34" (3-16
                # chars, only digits + separator). Pure-digit strings
                # like "1234" are NOT flagged (they could be counts).
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
    """Run the forbidden scanner and return a sanitized summary."""
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


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha256_json(obj: Any) -> str:
    return hashlib.sha256(_canonical_json(obj).encode("utf-8")).hexdigest()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Bounded HTTP probe (stdlib only)
# ---------------------------------------------------------------------------


def _http_get_json(
    url: str, timeout: int = PROBE_TIMEOUT_SECONDS
) -> tuple[Any, str, int | None]:
    """Bounded HTTP GET returning (parsed_json_or_None, status, http_code).

    status is "pass" on success, "unavailable" on network failure / non-200
    / timeout, or "partial" on parse failure.

    NEVER raises. NEVER returns the raw response body in error fields.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json, application/vnd.github+json",
                "User-Agent": (
                    "OpenLocus-C4-repoqa-source-readiness/0.1"
                    " (bounded; stdlib)"
                ),
            },
        )
        with urllib.request.urlopen(  # noqa: S310 - bounded source probe
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


def _http_probe_status(
    url: str, timeout: int = PROBE_TIMEOUT_SECONDS
) -> dict[str, Any]:
    """Bounded HTTP HEAD/GET returning only HTTP status (no body stored).

    Used for arXiv / OpenReview / homepage URL status probes.
    """
    try:
        req = urllib.request.Request(
            url,
            method="HEAD",
            headers={
                "User-Agent": (
                    "OpenLocus-C4-repoqa-source-readiness/0.1"
                    " (bounded; stdlib)"
                ),
            },
        )
        with urllib.request.urlopen(  # noqa: S310 - bounded source probe
            req, timeout=timeout
        ) as resp:
            return {
                "endpoint": "url_status",
                "url_safe_category": "official_source",
                "status": "pass",
                "http_code": resp.getcode(),
            }
    except urllib.error.HTTPError as exc:
        # Some servers reject HEAD (405); fall back to GET without
        # reading the body.
        if exc.code in (405, 403):
            try:
                req_get = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": (
                            "OpenLocus-C4-repoqa-source-readiness/0.1"
                            " (bounded; stdlib)"
                        ),
                    },
                )
                with urllib.request.urlopen(  # noqa: S310
                    req_get, timeout=timeout
                ) as resp:
                    return {
                        "endpoint": "url_status",
                        "url_safe_category": "official_source",
                        "status": "pass",
                        "http_code": resp.getcode(),
                    }
            except (urllib.error.HTTPError, urllib.error.URLError,
                    TimeoutError, ConnectionError, OSError):
                pass
        return {
            "endpoint": "url_status",
            "url_safe_category": "official_source",
            "status": "unavailable",
            "http_code": exc.code,
        }
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
        return {
            "endpoint": "url_status",
            "url_safe_category": "official_source",
            "status": "unavailable",
            "http_code": None,
        }


# ---------------------------------------------------------------------------
# Source probes (aggregate-only; no raw response bodies, no asset download)
# ---------------------------------------------------------------------------


def _probe_github_repo_api(
    endpoint_name: str, url: str
) -> dict[str, Any]:
    """Probe a GitHub repo API for aggregate metadata.

    Returns only: repo_public, license_spdx, default_branch, stars_count,
    is_fork. No raw response body is stored.
    """
    raw, status, http_code = _http_get_json(url)
    probe: dict[str, Any] = {
        "endpoint": endpoint_name,
        "status": status,
        "http_code": (http_code if isinstance(http_code, int) else None),
        "repo_public": None,
        "license_spdx": None,
        "default_branch": None,
        "stars_count": None,
        "is_fork": None,
    }
    if status != "pass" or not isinstance(raw, dict):
        return probe
    probe["repo_public"] = bool(raw.get("private") is False)
    probe["is_fork"] = bool(raw.get("fork", False))
    branch = raw.get("default_branch")
    if isinstance(branch, str):
        probe["default_branch"] = branch
    stars = raw.get("stargazers_count")
    if isinstance(stars, int):
        probe["stars_count"] = stars
    lic = raw.get("license")
    if isinstance(lic, dict):
        spdx = lic.get("spdx_id")
        if isinstance(spdx, str):
            probe["license_spdx"] = spdx
    return probe


def _probe_github_release_api(url: str) -> dict[str, Any]:
    """Probe a GitHub release API for release/asset metadata.

    Returns only: tag_name, draft, prerelease, published_at, and asset
    metadata (name, size, content_type, download_count). No raw response
    body is stored. No asset body is downloaded or decompressed.
    """
    raw, status, http_code = _http_get_json(url)
    probe: dict[str, Any] = {
        "endpoint": "github_release_api",
        "status": status,
        "http_code": (http_code if isinstance(http_code, int) else None),
        "release_tag": None,
        "release_draft": None,
        "release_prerelease": None,
        "release_published_at": None,
        "asset_count": None,
        "asset_metadata": [],
    }
    if status != "pass" or not isinstance(raw, dict):
        return probe
    tag = raw.get("tag_name")
    if isinstance(tag, str):
        probe["release_tag"] = tag
    probe["release_draft"] = bool(raw.get("draft", False))
    probe["release_prerelease"] = bool(raw.get("prerelease", False))
    pub = raw.get("published_at")
    if isinstance(pub, str):
        probe["release_published_at"] = pub
    assets = raw.get("assets")
    if isinstance(assets, list):
        probe["asset_count"] = len(assets)
        asset_meta: list[dict[str, Any]] = []
        for a in assets:
            if not isinstance(a, dict):
                continue
            meta: dict[str, Any] = {}
            aname = a.get("name")
            if isinstance(aname, str):
                meta["asset_name"] = aname
            asize = a.get("size")
            if isinstance(asize, int):
                meta["asset_size"] = asize
            act = a.get("content_type")
            if isinstance(act, str):
                meta["asset_content_type"] = act
            adc = a.get("download_count")
            if isinstance(adc, int):
                meta["asset_download_count"] = adc
            if meta:
                asset_meta.append(meta)
        probe["asset_metadata"] = asset_meta
    return probe


def run_source_probes(*, offline: bool = False) -> dict[str, Any]:
    """Run all bounded source probes. Returns aggregate-only status.

    In --offline mode, no network calls are made; all probes report
    status=offline and the report is built from confirmed static
    findings only.
    """
    if offline:
        return {
            "offline_mode": True,
            "network_calls": 0,
            "probes": [],
        }
    probes: list[dict[str, Any]] = []
    probes.append(
        _probe_github_repo_api("github_code_repo_api", CODE_REPO_API_URL)
    )
    probes.append(
        _probe_github_repo_api(
            "github_release_repo_api", RELEASE_REPO_API_URL
        )
    )
    probes.append(_probe_github_release_api(RELEASE_API_URL_CURRENT))
    # URL status probes (arXiv / homepage / OpenReview).
    probes.append(_http_probe_status(ARXIV_ABS_URL))
    probes.append(_http_probe_status(HOMEPAGE_URL))
    probes.append(_http_probe_status(OPENREVIEW_URL))
    return {
        "offline_mode": False,
        "network_calls": len(probes),
        "probes": probes,
    }


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def _build_report(
    *,
    probe_results: dict[str, Any],
    self_test: bool = False,
) -> dict[str, Any]:
    """Build the C4.5 source/schema-contract readiness report.

    The status is always
    source_confirmed_schema_contract_ready_adapter_deferred
    (not pass/support). No adapter support, schema readiness,
    public row schema readiness, row-map smoke, or benchmark result is
    claimed.
    """
    probes = probe_results.get("probes", [])
    code_repo_probe = next(
        (p for p in probes if p.get("endpoint") == "github_code_repo_api"),
        None,
    )
    release_repo_probe = next(
        (p for p in probes if p.get("endpoint") == "github_release_repo_api"),
        None,
    )
    release_api_probe = next(
        (p for p in probes if p.get("endpoint") == "github_release_api"),
        None,
    )

    # Determine source confirmation status.
    if probe_results.get("offline_mode"):
        source_confirmation_status = "offline_static_findings_only"
    elif any(p.get("status") == "pass" for p in probes):
        source_confirmation_status = "sources_confirmed_via_probe"
    else:
        source_confirmation_status = (
            "sources_confirmed_static_probes_unreachable"
        )

    # Extract release asset metadata from probe (if available).
    asset_name_current = ASSET_NAME_CURRENT
    asset_size_current = None
    asset_content_type_current = None
    if release_api_probe and release_api_probe.get("status") == "pass":
        for meta in release_api_probe.get("asset_metadata", []):
            if meta.get("asset_name") == ASSET_NAME_CURRENT:
                asset_size_current = meta.get("asset_size")
                asset_content_type_current = meta.get("asset_content_type")
                break

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "benchmark": BENCHMARK,
        "target_title": TARGET_TITLE,
        "target_task": TARGET_TASK,
        "claim_level": CLAIM_LEVEL,
        "self_test": bool(self_test),
        "aggregate_only_public_artifact": True,
        "not_evidence": True,
        "candidate_not_fact": True,
        # No-claim flags -- ALL false.
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "runtime_clean_general_algorithm_claimed": False,
        "downstream_agent_value_proven": False,
        "ood_temporal_supported": False,
        "quiver_systems_supported": False,
        # C4.5 specific claim flags.
        "adapter_support_claimed": False,
        "schema_readiness_claimed": False,
        "public_row_schema_readiness_claimed": False,
        "schema_contract_readiness_claimed": True,
        "row_map_smoke_attempted": False,
        "row_map_smoke_passed": False,
        "benchmark_result_claimed": False,
        # Metadata boundary flags.
        "release_asset_downloaded": False,
        "release_asset_decompressed": False,
        "release_asset_body_read": False,
        "monolithic_json_rows_read": False,
        # Status.
        "status": TARGET_STATUS,
        "source_confirmation_status": source_confirmation_status,
        # Wrong-target disambiguation.
        "wrong_target_disambiguated": True,
        "wrong_target_exclusions": WRONG_TARGET_EXCLUSIONS,
        # Official source URLs (source-level public URLs only).
        "arxiv_id": ARXIV_ID,
        "arxiv_abs_url": ARXIV_ABS_URL,
        "arxiv_pdf_url": ARXIV_PDF_URL,
        "openreview_url": OPENREVIEW_URL,
        "homepage_url": HOMEPAGE_URL,
        "code_repo": CODE_REPO_ID,
        "code_repo_url": CODE_REPO_URL,
        "code_repo_api_url": CODE_REPO_API_URL,
        "release_repo": RELEASE_REPO_ID,
        "release_repo_url": RELEASE_REPO_URL,
        "release_repo_api_url": RELEASE_REPO_API_URL,
        "release_api_url": RELEASE_API_URL_CURRENT,
        "asset_url_current": ASSET_URL_CURRENT,
        "asset_url_paper": ASSET_URL_PAPER,
        # Source probes.
        "source_probes": probe_results,
        # Release metadata (source-level, not row-level).
        "release_metadata": {
            "current_loader_default_tag": RELEASE_TAG_CURRENT,
            "current_loader_default_asset_name": asset_name_current,
            "current_loader_default_asset_size": asset_size_current,
            "current_loader_default_asset_content_type": (
                asset_content_type_current
            ),
            "paper_compatible_tag": RELEASE_TAG_PAPER,
            "paper_compatible_asset_name": ASSET_NAME_PAPER,
        },
        # Code repo metadata from probe.
        "code_repo_public": (
            code_repo_probe.get("repo_public") if code_repo_probe else None
        ),
        "code_repo_license_spdx": (
            code_repo_probe.get("license_spdx") if code_repo_probe else None
        ),
        "code_repo_default_branch": (
            code_repo_probe.get("default_branch")
            if code_repo_probe
            else None
        ),
        "code_repo_stars_count": (
            code_repo_probe.get("stars_count") if code_repo_probe else None
        ),
        # Release repo metadata from probe.
        "release_repo_public": (
            release_repo_probe.get("repo_public")
            if release_repo_probe
            else None
        ),
        "release_repo_license_spdx": (
            release_repo_probe.get("license_spdx")
            if release_repo_probe
            else None
        ),
        "release_repo_default_branch": (
            release_repo_probe.get("default_branch")
            if release_repo_probe
            else None
        ),
        # Version skew (source-level release metadata).
        "version_skew": dict(VERSION_SKEW),
        # Paper aggregate facts (paper-level, not row-level).
        "paper_aggregate_facts": dict(PAPER_AGGREGATE_FACTS),
        # Schema contract field-name categories (schema-only observations).
        "repo_record_contract_fields": list(REPO_RECORD_CONTRACT_FIELDS),
        "needle_contract_fields": list(NEEDLE_CONTRACT_FIELDS),
        "task_record_contract_fields": list(TASK_RECORD_CONTRACT_FIELDS),
        "model_output_contract_fields": list(MODEL_OUTPUT_CONTRACT_FIELDS),
        "adapter_derived_private_field_categories": list(
            ADAPTER_DERIVED_PRIVATE_FIELD_CATEGORIES
        ),
        "schema_contract_field_names": list(SCHEMA_CONTRACT_FIELD_NAMES),
        # Follow-up requirements.
        "follow_up_requirements": [
            "derived_qrels_design_decision",
            "version_selection_decision",
            "license_and_redistribution_statement",
            "row_map_smoke_design",
            "adapter_integration_decision",
        ],
        # Safety invariants.
        "raw_rows_persisted": False,
        "row_level_values_emitted": False,
        "row_level_hashes_emitted": False,
        "row_level_redistribution_allowed": False,
        "derived_label_publication_allowed": False,
        "raw_response_stored": False,
        "new_provider_calls": 0,
        "new_network_calls": probe_results.get("network_calls", 0),
    }

    # Fail-closed forbidden scan before returning.
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_leak"
    return report


def build_source_readiness_report(
    *, offline: bool = False, self_test: bool = False
) -> dict[str, Any]:
    """Build the C4.5 source/schema-contract readiness report."""
    probe_results = run_source_probes(offline=offline)
    report = _build_report(probe_results=probe_results, self_test=self_test)
    # Re-run forbidden scan after final assembly.
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        raise ValueError(
            "c4_repoqa_source_readiness report would leak "
            f"forbidden content: {scan['categories']}"
        )
    return report


# ---------------------------------------------------------------------------
# Self-test (no network)
# ---------------------------------------------------------------------------


def _self_test_wrong_target_disambiguation() -> None:
    """Wrong-target disambiguation rejects non-EvalPlus-RepoQA targets."""
    assert TARGET_TITLE.startswith("RepoQA")
    assert "Searching Needle Function" in TARGET_TITLE
    assert TARGET_TASK == "searching_needle_function"
    assert ARXIV_ID == "2406.06025"
    assert OPENREVIEW_URL == "https://openreview.net/forum?id=hK9YSrFuGf"
    assert CODE_REPO_ID == "evalplus/repoqa"
    assert RELEASE_REPO_ID == "evalplus/repoqa_release"
    # Wrong targets are excluded.
    excluded = {
        e["excluded_target"] for e in WRONG_TARGET_EXCLUSIONS
    }
    assert "Nutanix/RepoQA-neo4j" in excluded
    assert "microsoft/SCBench:scbench_repoqa" in excluded
    assert "CodeRepoQA" in excluded
    assert "RepoExec" in excluded
    assert "RepoBench" in excluded
    assert "SWE-QA-Pro" in excluded
    # None of the wrong targets is the canonical target.
    for e in WRONG_TARGET_EXCLUSIONS:
        assert e["excluded_target"] != CODE_REPO_ID
        assert e["excluded_target"] != RELEASE_REPO_ID
    print("self-test wrong-target disambiguation: ok")


def _self_test_offline_report_shape() -> None:
    """Offline report builds with deferred status, not pass/support."""
    report = build_source_readiness_report(offline=True, self_test=True)
    assert report["schema_version"] == SCHEMA_VERSION
    assert report["benchmark"] == BENCHMARK
    assert report["target_title"] == TARGET_TITLE
    assert report["claim_level"] == CLAIM_LEVEL
    # Status must be the deferred status (not pass/support).
    assert report["status"] == TARGET_STATUS, report["status"]
    assert report["status"] not in ("pass", "support")
    assert (
        report["source_confirmation_status"]
        == "offline_static_findings_only"
    )
    # C4.5 specific claim flags.
    assert report["adapter_support_claimed"] is False
    assert report["schema_readiness_claimed"] is False
    assert report["public_row_schema_readiness_claimed"] is False
    assert report["schema_contract_readiness_claimed"] is True
    assert report["row_map_smoke_attempted"] is False
    assert report["row_map_smoke_passed"] is False
    assert report["benchmark_result_claimed"] is False
    # Metadata boundary flags.
    assert report["release_asset_downloaded"] is False
    assert report["release_asset_decompressed"] is False
    assert report["release_asset_body_read"] is False
    assert report["monolithic_json_rows_read"] is False
    # No-claim flags all false.
    for flag in NO_CLAIM_FLAGS:
        assert report[flag] is False, (flag, report[flag])
    # Safety invariants.
    assert report["raw_rows_persisted"] is False
    assert report["row_level_values_emitted"] is False
    assert report["row_level_hashes_emitted"] is False
    assert report["row_level_redistribution_allowed"] is False
    assert report["derived_label_publication_allowed"] is False
    assert report["raw_response_stored"] is False
    assert report["aggregate_only_public_artifact"] is True
    assert report["not_evidence"] is True
    assert report["candidate_not_fact"] is True
    # Forbidden scan must pass.
    assert report["forbidden_scan"]["status"] == "pass", report["forbidden_scan"]
    assert report["forbidden_scan"]["violations_count"] == 0, report["forbidden_scan"]
    # Offline mode => 0 network calls.
    assert report["new_network_calls"] == 0
    assert report["source_probes"]["offline_mode"] is True
    # Schema contract containers present.
    assert "repo" in report["repo_record_contract_fields"]
    assert "content" in report["repo_record_contract_fields"]
    assert "needles" in report["repo_record_contract_fields"]
    assert "path" in report["needle_contract_fields"]
    assert "start_line" in report["needle_contract_fields"]
    assert "description" in report["needle_contract_fields"]
    # Version skew present.
    assert report["version_skew"]["version_skew_noted"] is True
    assert report["version_skew"]["paper_languages"] == 5
    assert report["version_skew"]["current_loader_languages"] == 6
    # Paper aggregate facts.
    assert report["paper_aggregate_facts"]["paper_aggregate_only"] is True
    assert report["paper_aggregate_facts"]["total_tasks_per_paper"] == 500
    print("self-test offline report shape: ok")


def _self_test_schema_contract_allowlist_vs_row_key_leak() -> None:
    """Schema-contract field names allowed in containers, forbidden as row keys."""
    # Field names ARE allowed as values under schema-contract containers.
    clean_with_schema = {
        "repo_record_contract_fields": ["repo", "content", "needles"],
        "needle_contract_fields": [
            "path", "name", "start_line", "end_line", "description",
        ],
        "schema_contract_field_names": ["repo", "path", "description"],
    }
    v = _scan_forbidden(clean_with_schema)
    assert v == [], v
    s = _forbidden_scan_summary(clean_with_schema)
    assert s["status"] == "pass", s

    # The SAME field names are FORBIDDEN as row-like dict keys elsewhere.
    bad_row_like = {
        "repo": "some/repo",
        "content": "code here",
        "needles": [],
        "path": "src/main.py",
        "description": "some text",
    }
    v2 = _scan_forbidden(bad_row_like)
    cats = {x["category"] for x in v2}
    assert "forbidden_key" in cats, cats
    assert len(v2) >= 5, len(v2)
    s2 = _forbidden_scan_summary(bad_row_like)
    assert s2["status"] == "fail", s2
    print("self-test schema-contract allowlist vs row-key leak: ok")


def _self_test_schema_container_strict_pass_fail() -> None:
    """Schema-contract containers: strict approved-set checks.

    Covers the oracle blocker cases:
    - PASS: approved contract strings in containers.
    - FAIL: unapproved function value in container.
    - FAIL: path-like value in container.
    - FAIL: dict row-like object in container.
    - FAIL: forbidden dict key NOT relaxed inside schema containers.
    """
    # PASS: approved contract strings in schema-contract containers.
    clean = {
        "repo_record_contract_fields": ["repo", "content", "needles"],
        "needle_contract_fields": [
            "path", "name", "start_byte", "end_byte",
            "start_line", "end_line", "description",
        ],
        "task_record_contract_fields": ["language", "repo_record", "needles"],
        "model_output_contract_fields": [
            "model_name", "generation", "predicted_function",
        ],
        "adapter_derived_private_field_categories": [
            "model_output", "predicted_function", "generation", "task_id",
        ],
        "schema_contract_field_names": ["repo", "path", "description"],
    }
    v = _scan_forbidden(clean)
    assert v == [], v
    s = _forbidden_scan_summary(clean)
    assert s["status"] == "pass", s

    # FAIL: unapproved row/function value in container.
    bad_func = {"needle_contract_fields": ["compute_loss"]}
    v = _scan_forbidden(bad_func)
    cats = {x["category"] for x in v}
    assert "unapproved_contract_string" in cats, cats
    s = _forbidden_scan_summary(bad_func)
    assert s["status"] == "fail", s

    # FAIL: path-like value in container.
    bad_path = {"schema_contract_field_names": ["src/main.py"]}
    v = _scan_forbidden(bad_path)
    cats = {x["category"] for x in v}
    assert "unapproved_contract_string" in cats, cats
    s = _forbidden_scan_summary(bad_path)
    assert s["status"] == "fail", s

    # FAIL: dict row-like object in container.
    bad_dict = {
        "repo_record_contract_fields": [{"repo": "pytorch/pytorch"}],
    }
    v = _scan_forbidden(bad_dict)
    cats = {x["category"] for x in v}
    assert "dict_in_schema_container" in cats, cats
    assert "forbidden_key" in cats, cats
    assert "unapproved_contract_string" in cats, cats
    s = _forbidden_scan_summary(bad_dict)
    assert s["status"] == "fail", s

    # FAIL: forbidden dict key NOT relaxed inside schema containers.
    # A dict with a forbidden key as a dict key inside a schema container
    # must still be rejected (field names are list/string values only,
    # never dict keys).
    bad_key_in_container = {
        "repo_record_contract_fields": {
            "repo": "pytorch/pytorch",
        },
    }
    v = _scan_forbidden(bad_key_in_container)
    cats = {x["category"] for x in v}
    assert "dict_in_schema_container" in cats, cats
    assert "forbidden_key" in cats, cats

    # FAIL: mixed approved + unapproved strings in container.
    bad_mixed = {
        "repo_record_contract_fields": ["repo", "compute_loss", "needles"],
    }
    v = _scan_forbidden(bad_mixed)
    cats = {x["category"] for x in v}
    assert "unapproved_contract_string" in cats, cats
    assert len(v) == 1, v  # only "compute_loss" is unapproved
    s = _forbidden_scan_summary(bad_mixed)
    assert s["status"] == "fail", s

    print("self-test schema container strict pass/fail: ok")


def _self_test_leak_injection_rejections() -> None:
    """Forbidden scanner rejects leaked repo/function names, paths, SHAs, ranges, etc."""
    _nl = chr(10)

    # Repo name leak (forbidden key + value).
    bad_repo = {"repo": "pytorch/pytorch"}
    v = _scan_forbidden(bad_repo)
    cats = {x["category"] for x in v}
    assert "forbidden_key" in cats, cats

    # Function name leak (forbidden key).
    bad_func = {"name": "compute_loss"}
    v = _scan_forbidden(bad_func)
    cats = {x["category"] for x in v}
    assert "forbidden_key" in cats, cats

    # File path leak (path-like value).
    bad_path = {"some_key": "/src/main.py"}
    v = _scan_forbidden(bad_path)
    cats = {x["category"] for x in v}
    assert "path_like_value" in cats, cats

    # Commit SHA leak (hex_digest + forbidden key).
    bad_sha = {"commit_sha": "a" * 40}
    v = _scan_forbidden(bad_sha)
    cats = {x["category"] for x in v}
    assert "forbidden_key" in cats, cats
    assert "hex_digest_value" in cats, cats

    # Line range leak.
    bad_range = {"some_key": "12-34"}
    v = _scan_forbidden(bad_range)
    cats = {x["category"] for x in v}
    assert "line_range_value" in cats, cats

    # Byte range leak (same pattern as line range).
    bad_byte = {"some_key": "100-200"}
    v = _scan_forbidden(bad_byte)
    cats = {x["category"] for x in v}
    assert "line_range_value" in cats, cats

    # Description leak (forbidden key).
    bad_desc = {"description": "This function does X"}
    v = _scan_forbidden(bad_desc)
    cats = {x["category"] for x in v}
    assert "forbidden_key" in cats, cats

    # Question leak (forbidden key).
    bad_q = {"question": "What does this do?"}
    v = _scan_forbidden(bad_q)
    cats = {x["category"] for x in v}
    assert "forbidden_key" in cats, cats

    # Answer leak (forbidden key).
    bad_a = {"answer": "42"}
    v = _scan_forbidden(bad_a)
    cats = {x["category"] for x in v}
    assert "forbidden_key" in cats, cats

    # Snippet leak (forbidden key + multiline).
    bad_snip = {"snippet": "def x():" + _nl + "  pass"}
    v = _scan_forbidden(bad_snip)
    cats = {x["category"] for x in v}
    assert "forbidden_key" in cats, cats
    assert "multiline_value" in cats, cats

    # Raw JSON fragment leak.
    bad_json = {"some_key": '{"repo": "x", "needles": []}'}
    v = _scan_forbidden(bad_json)
    cats = {x["category"] for x in v}
    assert "raw_json_fragment" in cats, cats

    # Content hash leak (forbidden key + hex_digest).
    bad_hash = {"content_sha": "b" * 64}
    v = _scan_forbidden(bad_hash)
    cats = {x["category"] for x in v}
    assert "forbidden_key" in cats, cats
    assert "hex_digest_value" in cats, cats

    # Provider payload leak (forbidden key).
    bad_pp = {"provider_payload": {"model": "gpt-4"}}
    v = _scan_forbidden(bad_pp)
    cats = {x["category"] for x in v}
    assert "forbidden_key" in cats, cats

    print("self-test leak injection rejections: ok")


def _self_test_release_metadata_allowed_content_forbidden() -> None:
    """Release asset metadata (name/size/tag) allowed; content sample/digest forbidden."""
    # Release metadata: allowed.
    good_release = {
        "release_metadata": {
            "current_loader_default_tag": "2024-06-23",
            "current_loader_default_asset_name": "repoqa-2024-06-23.json.gz",
            "current_loader_default_asset_size": 12345678,
            "current_loader_default_asset_content_type": "application/gzip",
            "paper_compatible_tag": "2024-04-20",
            "paper_compatible_asset_name": "repoqa-2024-04-20.json.gz",
        },
        "asset_url_current": ASSET_URL_CURRENT,
        "asset_url_paper": ASSET_URL_PAPER,
    }
    v = _scan_forbidden(good_release)
    assert v == [], v
    s = _forbidden_scan_summary(good_release)
    assert s["status"] == "pass", s

    # Content sample: forbidden (multiline).
    bad_content_sample = {
        "release_metadata": {
            "current_loader_default_tag": "2024-06-23",
            "current_loader_default_asset_name": "repoqa-2024-06-23.json.gz",
            "content_sample": "def foo():" + chr(10) + "  return 42",
        },
    }
    v = _scan_forbidden(bad_content_sample)
    cats = {x["category"] for x in v}
    assert "multiline_value" in cats, cats

    # Content digest: forbidden (hex_digest).
    bad_digest = {
        "release_metadata": {
            "current_loader_default_tag": "2024-06-23",
            "current_loader_default_asset_name": "repoqa-2024-06-23.json.gz",
            "content_digest": "c" * 64,
        },
    }
    v = _scan_forbidden(bad_digest)
    cats = {x["category"] for x in v}
    assert "hex_digest_value" in cats, cats

    print("self-test release metadata allowed, content sample/digest forbidden: ok")


def _self_test_source_urls_allowed() -> None:
    """Official source-level URLs are allowed by the forbidden scanner."""
    report = {
        "arxiv_abs_url": ARXIV_ABS_URL,
        "arxiv_pdf_url": ARXIV_PDF_URL,
        "openreview_url": OPENREVIEW_URL,
        "homepage_url": HOMEPAGE_URL,
        "code_repo_url": CODE_REPO_URL,
        "code_repo_api_url": CODE_REPO_API_URL,
        "release_repo_url": RELEASE_REPO_URL,
        "release_repo_api_url": RELEASE_REPO_API_URL,
        "release_api_url": RELEASE_API_URL_CURRENT,
        "asset_url_current": ASSET_URL_CURRENT,
        "asset_url_paper": ASSET_URL_PAPER,
    }
    violations = _scan_forbidden(report)
    assert violations == [], violations
    summary = _forbidden_scan_summary(report)
    assert summary["status"] == "pass", summary
    print("self-test source URLs allowed: ok")


def _self_test_report_aggregate_only() -> None:
    """The full offline report is aggregate-only and scanner-clean."""
    report = build_source_readiness_report(offline=True, self_test=True)
    report_json = json.dumps(report, sort_keys=True)
    # No row-level payload substrings.
    for forbidden_substring in (
        "pytorch",
        "def foo",
        "src/main.py",
        "12-34",
        "100-200",
        "What does this do",
        '{"repo"',
        "content_sample",
    ):
        assert forbidden_substring not in report_json, forbidden_substring
    # Re-scan to be sure.
    rescan = _forbidden_scan_summary(report)
    assert rescan["status"] == "pass", rescan
    print("self-test report aggregate-only: ok")


def _self_test_fail_closed_generation() -> None:
    """build_source_readiness_report must fail-closed if a leak is detected.

    We directly verify the fail-closed gate: call build_source_readiness_report
    after injecting a forbidden key into the report dict via a temporary
    wrapper, and confirm ValueError is raised.
    """
    import unittest.mock as mock

    real_build = _build_report

    def leaky_build(*, probe_results, self_test=False):
        report = real_build(
            probe_results=probe_results, self_test=self_test
        )
        report["repo"] = "leaked/repo"
        return report

    # Use __main__ or current module reference so the mock works whether
    # run as a script or imported as a module.
    mod_globals = _self_test_fail_closed_generation.__globals__
    original = mod_globals["_build_report"]
    mod_globals["_build_report"] = leaky_build
    try:
        try:
            build_source_readiness_report(offline=True, self_test=True)
            raise AssertionError("Expected ValueError for leaky report")
        except ValueError:
            pass
    finally:
        mod_globals["_build_report"] = original

    print("self-test fail-closed generation: ok")


def run_self_tests() -> dict[str, Any]:
    """Run all C4.5 self-tests. Returns a summary (no row-level data)."""
    _self_test_wrong_target_disambiguation()
    _self_test_offline_report_shape()
    _self_test_schema_contract_allowlist_vs_row_key_leak()
    _self_test_schema_container_strict_pass_fail()
    _self_test_leak_injection_rejections()
    _self_test_release_metadata_allowed_content_forbidden()
    _self_test_source_urls_allowed()
    _self_test_report_aggregate_only()
    _self_test_fail_closed_generation()
    return {
        "schema_version": SCHEMA_VERSION,
        "claim_level": CLAIM_LEVEL,
        "self_test_passed": True,
        "self_test_checks": {
            "wrong_target_disambiguation": True,
            "offline_report_shape": True,
            "schema_contract_allowlist_vs_row_key_leak": True,
            "schema_container_strict_pass_fail": True,
            "leak_injection_rejections": True,
            "release_metadata_allowed_content_forbidden": True,
            "source_urls_allowed": True,
            "report_aggregate_only": True,
            "fail_closed_generation": True,
        },
        "not_evidence": True,
        "candidate_not_fact": True,
        "aggregate_only_public_artifact": True,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "C4.5 RepoQA source/schema-contract readiness"
            " (adapter deferred; bounded)."
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the C4.5 self-test (synthetic fixtures; no network).",
    )
    parser.add_argument(
        "--source-readiness",
        action="store_true",
        help="build the source/schema-contract readiness report (default).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help=(
            "build the report from confirmed static findings only; no "
            "network probes."
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=(
            "path to write the report (default: "
            "artifacts/c4_external_benchmark_adapters/"
            "c4_repoqa_source_readiness_report.json)."
        ),
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if args.self_test and (args.source_readiness or args.offline):
        parser.error(
            "--self-test is mutually exclusive with --source-readiness / --offline"
        )
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.self_test:
        result = run_self_tests()
        print(json.dumps(result, indent=2, sort_keys=True))
        print(
            "C4.5 RepoQA source/schema-contract readiness self-test: PASS",
            file=sys.stderr,
        )
        return 0

    # Default + --source-readiness: build the report.
    report = build_source_readiness_report(
        offline=args.offline, self_test=False
    )
    _write_json(args.out, report)
    summary = {
        "schema_version": report["schema_version"],
        "benchmark": report["benchmark"],
        "target_title": report["target_title"],
        "claim_level": report["claim_level"],
        "status": report["status"],
        "source_confirmation_status": report["source_confirmation_status"],
        "adapter_support_claimed": report["adapter_support_claimed"],
        "schema_readiness_claimed": report["schema_readiness_claimed"],
        "public_row_schema_readiness_claimed": report[
            "public_row_schema_readiness_claimed"
        ],
        "schema_contract_readiness_claimed": report[
            "schema_contract_readiness_claimed"
        ],
        "row_map_smoke_attempted": report["row_map_smoke_attempted"],
        "benchmark_result_claimed": report["benchmark_result_claimed"],
        "release_asset_downloaded": report["release_asset_downloaded"],
        "release_asset_decompressed": report["release_asset_decompressed"],
        "release_asset_body_read": report["release_asset_body_read"],
        "monolithic_json_rows_read": report["monolithic_json_rows_read"],
        "wrong_target_disambiguated": report["wrong_target_disambiguated"],
        "aggregate_only_public_artifact": report[
            "aggregate_only_public_artifact"
        ],
        "not_evidence": report["not_evidence"],
        "forbidden_scan": report["forbidden_scan"],
        "new_network_calls": report["new_network_calls"],
        "offline_mode": report["source_probes"]["offline_mode"],
        "out": str(args.out),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if report["forbidden_scan"]["status"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
