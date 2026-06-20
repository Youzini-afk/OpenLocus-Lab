#!/usr/bin/env python3
"""C4.1/C4.2 External Benchmark Adapters — schema + row-mapping readiness.

This module implements C4.1 external benchmark adapter schema readiness
and C4.2 ContextBench verified subset row-mapping smoke. It is NOT
skeleton-only: it implements real synthetic in-memory row adapters that
separate ``public_task`` (aggregate-safe metadata) from ``private_label``
(row-level payload that is never serialized), deterministic spec hashing,
a strict forbidden-output scanner, bounded HF datasets-server schema smoke
via stdlib ``urllib`` only, a bounded real row-mapping smoke for the
ContextBench verified subset, and a no-network self-test.

Public-artifact contract (binding):

* aggregate-only public outputs;
* NEVER write raw benchmark rows, gold labels, row-level paths / spans
  / line ranges, snippets, problem statements, patch/test payload,
  prompts/responses, provider payloads, content_sha, raw HF payloads,
  or response bodies;
* no row-level hashes (hashes are row-level derived data);
* no-claim flags all false: ``promotion_ready``,
  ``default_should_change``, ``evidencecore_semantics_changed``,
  ``runtime_clean_general_algorithm_claimed``,
  ``downstream_agent_value_proven``, ``ood_temporal_supported``,
  ``quiver_systems_supported``;
* ContextBench dataset license unknown => row-level redistribution
  disabled;
* SWE-Explore HF dataset ``cc-by-nc-nd-4.0`` => row-level
  redistribution AND derived-label publication disabled.

Claim boundary: this module emits ``adapter_schema_readiness_only`` /
``adapter_row_mapping_readiness_only`` evidence. It does NOT claim
performance, promotion, default change, external benchmark result,
downstream agent value, OOD temporal support, or QuIVer systems support.
Synthetic self-test rows confer NO empirical support. Schema-smoke and
row-map-smoke (when run) only confirm that the public HF datasets-server
endpoints are reachable, parse, and that the adapter boundary holds;
they do NOT validate row-level semantics, labels, or downstream agent
value.

Run::

    python3 -m py_compile eval/c4_external_benchmark_adapters.py
    python3 eval/c4_external_benchmark_adapters.py --self-test
    python3 eval/c4_external_benchmark_adapters.py \\
        --out artifacts/c4_external_benchmark_adapters/\\
c4_external_benchmark_adapter_report.json
    python3 eval/c4_external_benchmark_adapters.py \\
        --benchmark contextbench --schema-smoke --limit 3 \\
        --out /tmp/c4_contextbench_schema.json
    python3 eval/c4_external_benchmark_adapters.py \\
        --benchmark swe_explore --schema-smoke --limit 3 \\
        --out /tmp/c4_swe_explore_schema.json
    python3 eval/c4_external_benchmark_adapters.py \\
        --row-map-smoke --benchmark contextbench \\
        --config contextbench_verified --split train --row-limit 10 \\
        --out artifacts/c4_external_benchmark_adapters/\\
c4_contextbench_verified_row_mapping_report.json
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

SCHEMA_VERSION = "c4_external_benchmark_adapters.v1"
GENERATED_BY = "eval/c4_external_benchmark_adapters.py"
CLAIM_LEVEL = "adapter_schema_readiness_only"

DEFAULT_OUT = Path(
    "artifacts/c4_external_benchmark_adapters/"
    "c4_external_benchmark_adapter_report.json"
)

# Hard cap on --limit (number of (config, split) pairs to probe with
# /first-rows during schema smoke). Anything above is clamped.
LIMIT_HARD_CAP = 10
LIMIT_DEFAULT = 3

# Hard cap on --row-limit (number of preview rows to row-map during
# the C4.2 row-mapping smoke). Anything above is clamped.
ROW_LIMIT_HARD_CAP = 20
ROW_LIMIT_DEFAULT = 10

# Bounded timeout for every HF datasets-server HTTP call.
SMOKE_TIMEOUT_SECONDS = 10

# HF datasets-server base (stdlib only; no extra deps).
_HF_DATASETS_SERVER = "https://datasets-server.huggingface.co"

# C4.2 row-mapping smoke constants. Only contextbench_verified/train is
# supported for row-map smoke; this is the verified subset.
ROW_MAP_CLAIM_LEVEL = "adapter_row_mapping_readiness_only"
ROW_MAP_SCHEMA_VERSION = "c4_contextbench_verified_row_mapping.v1"
ROW_MAP_DEFAULT_OUT = Path(
    "artifacts/c4_external_benchmark_adapters/"
    "c4_contextbench_verified_row_mapping_report.json"
)
ROW_MAP_ALLOWED_CONFIGS: frozenset[str] = frozenset(
    {"contextbench_verified"}
)

# Fixed failure-category enum for row-map smoke. Only these category
# labels may appear in the public artifact; never row-level values.
ROW_MAP_FAILURE_CATEGORIES: tuple[str, ...] = (
    "missing_required_field",
    "wrong_type",
    "mapping_error",
    "private_field_leak",
    "public_artifact_leak",
    "unexpected_exception",
    "no_rows_returned",
    "endpoint_unavailable",
)

# ---------------------------------------------------------------------------
# Benchmark specs (built-in known schema metadata; NO network required)
# ---------------------------------------------------------------------------

# ContextBench schema field names. These are SCHEMA-ONLY observations
# (the names of fields the public HF dataset exposes), NOT row values.
# They are safe to emit under ``field_names_schema_only``.
CONTEXTBENCH_DATASET_ID = "Contextbench/ContextBench"
CONTEXTBENCH_FIELD_NAMES: tuple[str, ...] = (
    "instance_id",
    "original_inst_id",
    "repo",
    "repo_url",
    "language",
    "base_commit",
    "gold_context",
    "patch",
    "test_patch",
    "problem_statement",
    "f2p",
    "p2p",
    "source",
)
# Row-level private categories detected in the ContextBench schema.
# Repo/commit locators and patch/test/problem/gold payloads are
# private; only their presence (not values) is recorded publicly.
CONTEXTBENCH_PRIVATE_FIELD_CATEGORIES: tuple[str, ...] = (
    "repo",
    "repo_url",
    "base_commit",
    "gold_context",
    "patch",
    "test_patch",
    "problem_statement",
    "f2p",
    "p2p",
)
CONTEXTBENCH_CONFIGS: tuple[dict[str, Any], ...] = (
    {
        "config": "default",
        "splits": ({"split": "train", "row_count": 1136},),
    },
    {
        "config": "contextbench_verified",
        "splits": ({"split": "train", "row_count": 500},),
    },
)
CONTEXTBENCH_LICENSE_STATUS = "unknown_dataset_license"
CONTEXTBENCH_FIELD_TYPE_SUMMARY = {"string": len(CONTEXTBENCH_FIELD_NAMES)}

# SWE-Explore schema field names (SCHEMA-ONLY observations).
SWE_EXPLORE_DATASET_ID = "SWE-Explore-Bench/SWE-Explore-Bench"
SWE_EXPLORE_FIELD_NAMES: tuple[str, ...] = (
    "instance_id",
    "repo_path",
    "repo_dir",
    "ground_truth",
    "read_step_info",
    "meta",
    "dataset",
)
# Nested/private categories detected in SWE-Explore. ground_truth and
# read_step_info are nested objects containing patches, file maps, and
# line ranges — all private.
SWE_EXPLORE_PRIVATE_FIELD_CATEGORIES: tuple[str, ...] = (
    "repo_path",
    "repo_dir",
    "ground_truth",
    "ground_truth.patch",
    "ground_truth.test_patch",
    "ground_truth.modified_files",
    "ground_truth.core_files",
    "ground_truth.line_ranges",
    "read_step_info",
    "read_step_info.file_maps",
    "read_step_info.line_ranges",
)
SWE_EXPLORE_CONFIGS: tuple[dict[str, Any], ...] = (
    {
        "config": "default",
        "splits": ({"split": "train", "row_count": 848},),
    },
)
SWE_EXPLORE_LICENSE_STATUS = "cc-by-nc-nd-4.0"
SWE_EXPLORE_FIELD_TYPE_SUMMARY = {
    "string": 4,
    "nested_object": 3,
}

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

# Safety invariants — ALL must be false.
SAFETY_INVARIANTS: tuple[str, ...] = (
    "raw_rows_persisted",
    "row_level_labels_persisted",
    "paths_spans_line_ranges_persisted",
    "snippets_persisted",
    "prompts_responses_persisted",
    "provider_payloads_persisted",
    "content_sha_persisted",
)

# ---------------------------------------------------------------------------
# Forbidden public-output scanner
# ---------------------------------------------------------------------------

# Sensitive KEY names that must NEVER appear as dict keys anywhere in a
# public JSON output. These are row-level data field names; they may
# appear ONLY as string values under explicit schema-only containers
# (``field_names_schema_only``, ``private_field_categories_detected``).
FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset(
    {
        # ContextBench row-level fields
        "instance_id",
        "original_inst_id",
        "repo",
        "repo_url",
        "base_commit",
        "gold_context",
        "patch",
        "test_patch",
        "problem_statement",
        "f2p",
        "p2p",
        "source",
        # SWE-Explore row-level fields
        "repo_path",
        "repo_dir",
        "ground_truth",
        "read_step_info",
        # Generic sensitive row-level fields
        "content_sha",
        "prompt",
        "response",
        "raw_response",
        "snippet",
        "snippets",
        "gold_spans",
        "gold_span",
        "label",
        "labels",
        "private_labels",
        "private_label",
        "decision_records",
        "candidate_meta",
        "raw_payload",
        "raw_rows",
        "row_level_values",
        "row_values",
        "issue_text",
        "issue_body",
        # Secret-like keys
        "api_key",
        "api_token",
        "api_secret",
        "base_url",
        "provider_key",
        "authorization",
    }
)

# Container key names under which sensitive field-name strings MAY
# appear as values (these are schema-only observations).
SCHEMA_ONLY_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "field_names_schema_only",
        "private_field_categories_detected",
    }
)

# Container key names whose CHILD KEYS are schema-only field-name
# observations (e.g. ``field_presence_counts.instance_id`` is a count of
# rows where the ``instance_id`` field was non-empty; the key name is a
# schema observation, NOT a row-level value). The forbidden_key check is
# relaxed for keys nested directly under these containers, because those
# keys are schema field names used as count buckets. The values under
# these containers are still scanned (they must be ints/counts only).
SCHEMA_KEY_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "field_presence_counts",
        "public_task_presence_counts",
        "private_field_presence_counts",
        "failure_category_counts",
    }
)

# Value patterns that indicate leaked row-level data.
_RE_URL_VALUE = re.compile(r"https?://", re.IGNORECASE)
_RE_HEX_DIGEST = re.compile(r"[A-Fa-f0-9]{32,}")
# Secret-like words inside string values.
_RE_SECRET_LIKE = re.compile(
    r"(?:api[_-]?key|api[_-]?token|api[_-]?secret|base[_-]?url"
    r"|provider[_-]?key|authorization[_-]?bearer)",
    re.IGNORECASE,
)
# File-path-like values: slash + chars + dot + extension. Catches
# ``src/foo.rs`` and ``a/b/c.py`` but NOT ``Contextbench/ContextBench``
# (no extension) or ``ground_truth.patch`` (no slash).
_FILE_EXT = (
    r"py|rs|ts|tsx|js|jsx|go|java|c|cpp|cc|h|hpp|hh|md|json|toml|"
    r"yaml|yml|txt|sh|rb|php|kt|swift|patch|diff|csv|parquet"
)
_RE_FILE_PATH_VALUE = re.compile(
    rf"/[A-Za-z0-9._/\-]+\.(?:{_FILE_EXT})\b"
)
# Line-range-like values: digits separated by colon/dash.
_RE_LINE_RANGE_VALUE = re.compile(r"\b\d+\s*[:\-]\s*\d+\b")


def _is_raw_line_range_value(value: str) -> bool:
    """Return true for a standalone raw line-range string.

    Public C4 outputs may mention schema field names that are private-label
    categories, but they must never carry raw spans/line ranges such as
    ``"12-34"`` or ``"12:34"``.
    """
    stripped = value.strip()
    return 3 <= len(stripped) <= 16 and bool(
        _RE_LINE_RANGE_VALUE.fullmatch(stripped)
    )

# Key names whose string values are known-safe spec/provenance
# identifiers (NOT row-level data). Their values are exempt from
# hex_digest and path_like value checks because:
#   * ``spec_hash`` is a deterministic SHA-256 of the spec (not a
#     row-level content_sha);
#   * ``generated_by`` is the module path that produced this report
#     (not a row-level file path);
#   * ``dataset_id`` is an official HF dataset identifier like
#     ``Org/Dataset`` (not a row-level path — and it carries no file
#     extension anyway);
#   * ``schema_version`` / ``claim_level`` are short identifier strings.
# These keys are NOT in FORBIDDEN_KEY_NAMES, so the forbidden_key
# check does not apply. The exemption only relaxes the hex_digest and
# path_like value checks for these specific value paths.
SAFE_VALUE_KEY_NAMES: frozenset[str] = frozenset(
    {
        "spec_hash",
        "generated_by",
        "schema_version",
        "claim_level",
        "dataset_id",
    }
)


def _path_last_key(path: str) -> str:
    """Extract the last key segment from a dotted JSON path."""
    last = path.rsplit(".", 1)[-1]
    # Strip array index suffixes like ``[0]``.
    return last.split("[")[0]


def _is_safe_value_path(path: str) -> bool:
    """Check if a JSON path ends with a known-safe value key."""
    return _path_last_key(path) in SAFE_VALUE_KEY_NAMES


def _is_schema_key_container(path: str) -> bool:
    """Check if the parent of the current key is a schema-key container.

    A schema-key container's child keys are schema-only field-name
    observations used as count buckets (e.g.
    ``field_presence_counts.instance_id`` is a count, not a row-level
    value). The forbidden_key check is relaxed for such keys.
    """
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in SCHEMA_KEY_CONTAINER_KEYS


def _scan_forbidden(
    obj: Any,
    path: str = "$",
    in_schema_container: bool = False,
) -> list[dict[str, Any]]:
    """Strict recursive scanner for public JSON outputs.

    Returns a list of violation dicts with ``category`` and ``path``
    (JSON path), NEVER the leaked value itself. Fail-closed: any
    violation means the public output would leak.

    Schema-only container keys (``field_names_schema_only``,
    ``private_field_categories_detected``) are allowed to hold
    sensitive field-name strings as values, because those are
    observations about schema, not row-level data.
    """
    violations: list[dict[str, Any]] = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            sub_path = f"{path}.{key_str}"
            is_schema_container = key_str in SCHEMA_ONLY_CONTAINER_KEYS
            # Forbid sensitive key names anywhere as dict keys, EXCEPT
            # when the parent is a schema-key container (the key is a
            # field-name-as-schema-observation used as a count bucket).
            if (
                key_str in FORBIDDEN_KEY_NAMES
                and not _is_schema_key_container(sub_path)
            ):
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
        # In schema-only containers, short field-name strings are
        # allowed (they describe schema, not row values).
        if in_schema_container and len(obj) <= 64:
            # Still reject obvious leaks: URLs, hex digests, file paths.
            if _RE_URL_VALUE.search(obj):
                violations.append(
                    {"category": "url_value", "path": path}
                )
            elif not safe_value and _RE_HEX_DIGEST.search(obj):
                violations.append(
                    {"category": "hex_digest_value", "path": path}
                )
            elif _RE_FILE_PATH_VALUE.search(obj) and not safe_value:
                violations.append(
                    {"category": "path_like_value", "path": path}
                )
            elif _is_raw_line_range_value(obj):
                violations.append(
                    {"category": "line_range_value", "path": path}
                )
            elif "\n" in obj:
                violations.append(
                    {"category": "multiline_value", "path": path}
                )
        else:
            if len(obj) > 256:
                violations.append(
                    {"category": "long_string", "path": path}
                )
            elif _RE_URL_VALUE.search(obj):
                violations.append(
                    {"category": "url_value", "path": path}
                )
            elif not safe_value and _RE_HEX_DIGEST.search(obj):
                violations.append(
                    {"category": "hex_digest_value", "path": path}
                )
            elif _RE_SECRET_LIKE.search(obj):
                violations.append(
                    {"category": "secret_like_value", "path": path}
                )
            elif _RE_FILE_PATH_VALUE.search(obj) and not safe_value:
                violations.append(
                    {"category": "path_like_value", "path": path}
                )
            elif "\n" in obj:
                violations.append(
                    {"category": "multiline_value", "path": path}
                )
            elif _is_raw_line_range_value(obj):
                violations.append(
                    {"category": "line_range_value", "path": path}
                )
    return violations


def _forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    """Run the forbidden scanner and return a sanitized summary.

    The summary contains ONLY status, total count, and per-category
    counts. NEVER leaked values or paths that reveal values.
    """
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
# Spec builder + deterministic spec hash
# ---------------------------------------------------------------------------


def _benchmark_spec(name: str) -> dict[str, Any]:
    """Return the deterministic built-in spec for a benchmark.

    Excludes: timestamps, network output, raw rows, local paths.
    Includes: dataset_id, configs, schema field names, private
    categories, license gating, field type summary.
    """
    if name == "contextbench":
        return {
            "dataset_id": CONTEXTBENCH_DATASET_ID,
            "configs": [
                {
                    "config": c["config"],
                    "splits": [dict(s) for s in c["splits"]],
                }
                for c in CONTEXTBENCH_CONFIGS
            ],
            "field_names_schema_only": list(CONTEXTBENCH_FIELD_NAMES),
            "field_type_summary": dict(CONTEXTBENCH_FIELD_TYPE_SUMMARY),
            "private_field_categories_detected": list(
                CONTEXTBENCH_PRIVATE_FIELD_CATEGORIES
            ),
            "license_status": CONTEXTBENCH_LICENSE_STATUS,
            "row_level_redistribution_allowed": False,
            "derived_label_publication_allowed": False,
        }
    if name == "swe_explore":
        return {
            "dataset_id": SWE_EXPLORE_DATASET_ID,
            "configs": [
                {
                    "config": c["config"],
                    "splits": [dict(s) for s in c["splits"]],
                }
                for c in SWE_EXPLORE_CONFIGS
            ],
            "field_names_schema_only": list(SWE_EXPLORE_FIELD_NAMES),
            "field_type_summary": dict(SWE_EXPLORE_FIELD_TYPE_SUMMARY),
            "private_field_categories_detected": list(
                SWE_EXPLORE_PRIVATE_FIELD_CATEGORIES
            ),
            "license_status": SWE_EXPLORE_LICENSE_STATUS,
            "row_level_redistribution_allowed": False,
            "derived_label_publication_allowed": False,
        }
    raise ValueError(f"unknown benchmark: {name}")


def build_spec() -> dict[str, Any]:
    """Return the deterministic C4 spec (no timestamps/network/raw rows)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "claim_level": CLAIM_LEVEL,
        "no_claim_flags": {flag: False for flag in NO_CLAIM_FLAGS},
        "safety_invariants": {inv: False for inv in SAFETY_INVARIANTS},
        "benchmarks": {
            "contextbench": _benchmark_spec("contextbench"),
            "swe_explore": _benchmark_spec("swe_explore"),
        },
    }


def compute_spec_hash() -> str:
    """Deterministic SHA-256 of the canonical spec."""
    return _sha256_json(build_spec())


# ---------------------------------------------------------------------------
# Synthetic in-memory row adapters (NEVER serialized with row values)
# ---------------------------------------------------------------------------


class ContextBenchPublicTask:
    """Aggregate-safe per-row public task summary.

    This is a synthetic in-memory representation only. It is NEVER
    serialized into a public artifact with row-level values. Only
    aggregate counts (across many rows) may flow into the public
    artifact, and only as booleans/counts.
    """

    __slots__ = (
        "field_count",
        "has_original_inst_id",
        "has_f2p",
        "has_p2p",
        "has_repo_locator",
        "has_private_label_payload",
        "language_category",
        "source_category",
    )

    def __init__(
        self,
        field_count: int,
        has_original_inst_id: bool,
        has_f2p: bool,
        has_p2p: bool,
        has_repo_locator: bool,
        has_private_label_payload: bool,
        language_category: str,
        source_category: str,
    ) -> None:
        self.field_count = field_count
        self.has_original_inst_id = has_original_inst_id
        self.has_f2p = has_f2p
        self.has_p2p = has_p2p
        self.has_repo_locator = has_repo_locator
        self.has_private_label_payload = has_private_label_payload
        self.language_category = language_category
        self.source_category = source_category


class ContextBenchPrivateLabel:
    """Private row-level payload for a ContextBench-like row.

    NEVER serialized into a public artifact. Used only for synthetic
    self-test and private in-memory validation.
    """

    __slots__ = (
        "instance_id",
        "original_inst_id",
        "repo",
        "repo_url",
        "base_commit",
        "gold_context",
        "patch",
        "test_patch",
        "problem_statement",
        "f2p",
        "p2p",
        "source",
    )

    def __init__(
        self,
        instance_id: str,
        original_inst_id: str,
        repo: str,
        repo_url: str,
        base_commit: str,
        gold_context: str,
        patch: str,
        test_patch: str,
        problem_statement: str,
        f2p: list[str],
        p2p: list[str],
        source: str,
    ) -> None:
        self.instance_id = instance_id
        self.original_inst_id = original_inst_id
        self.repo = repo
        self.repo_url = repo_url
        self.base_commit = base_commit
        self.gold_context = gold_context
        self.patch = patch
        self.test_patch = test_patch
        self.problem_statement = problem_statement
        self.f2p = f2p
        self.p2p = p2p
        self.source = source


def adapt_contextbench_row(
    row: dict[str, Any],
) -> tuple[ContextBenchPublicTask, ContextBenchPrivateLabel]:
    """Adapt a ContextBench-like row into (public_task, private_label).

    The public_task contains ONLY aggregate-safe metadata (presence
    booleans, field counts, categorical bucket). The private_label
    retains all row-level values. Neither is ever serialized with
    row-level values into a public artifact.
    """
    if not isinstance(row, dict):
        raise TypeError("contextbench row must be a dict")

    field_count = len(CONTEXTBENCH_FIELD_NAMES)
    has_original_inst_id = bool(row.get("original_inst_id"))
    has_f2p = bool(row.get("f2p"))
    has_p2p = bool(row.get("p2p"))
    has_repo_locator = bool(
        row.get("repo") or row.get("repo_url") or row.get("base_commit")
    )
    has_private_label_payload = bool(
        row.get("gold_context")
        or row.get("patch")
        or row.get("test_patch")
        or row.get("problem_statement")
        or row.get("f2p")
        or row.get("p2p")
    )
    # Categorical bucket only — never the raw value.
    language = row.get("language")
    language_category = (
        language if isinstance(language, str) and len(language) <= 16 else "other"
    )
    source = row.get("source")
    source_category = (
        source if isinstance(source, str) and len(source) <= 32 else "other"
    )

    public = ContextBenchPublicTask(
        field_count=field_count,
        has_original_inst_id=has_original_inst_id,
        has_f2p=has_f2p,
        has_p2p=has_p2p,
        has_repo_locator=has_repo_locator,
        has_private_label_payload=has_private_label_payload,
        language_category=language_category,
        source_category=source_category,
    )
    private = ContextBenchPrivateLabel(
        instance_id=str(row.get("instance_id", "")),
        original_inst_id=str(row.get("original_inst_id", "")),
        repo=str(row.get("repo", "")),
        repo_url=str(row.get("repo_url", "")),
        base_commit=str(row.get("base_commit", "")),
        gold_context=str(row.get("gold_context", "")),
        patch=str(row.get("patch", "")),
        test_patch=str(row.get("test_patch", "")),
        problem_statement=str(row.get("problem_statement", "")),
        f2p=list(row.get("f2p", []) or []),
        p2p=list(row.get("p2p", []) or []),
        source=str(row.get("source", "")),
    )
    return public, private


class SWE_EXPLOREPublicTask:
    """Aggregate-safe per-row public task summary for SWE-Explore-like rows."""

    __slots__ = (
        "field_count",
        "has_repo_path",
        "has_repo_dir",
        "has_ground_truth",
        "has_read_step_info",
        "has_meta",
        "dataset_category",
    )

    def __init__(
        self,
        field_count: int,
        has_repo_path: bool,
        has_repo_dir: bool,
        has_ground_truth: bool,
        has_read_step_info: bool,
        has_meta: bool,
        dataset_category: str,
    ) -> None:
        self.field_count = field_count
        self.has_repo_path = has_repo_path
        self.has_repo_dir = has_repo_dir
        self.has_ground_truth = has_ground_truth
        self.has_read_step_info = has_read_step_info
        self.has_meta = has_meta
        self.dataset_category = dataset_category


class SWE_EXPLOREPrivateLabel:
    """Private row-level payload for a SWE-Explore-like row.

    Includes ground_truth.* (patch/test_patch/modified_files/core_files/
    line_ranges), read_step_info, repo_path, repo_dir. NEVER serialized.
    """

    __slots__ = (
        "instance_id",
        "repo_path",
        "repo_dir",
        "ground_truth",
        "read_step_info",
        "meta",
        "dataset",
    )

    def __init__(
        self,
        instance_id: str,
        repo_path: str,
        repo_dir: str,
        ground_truth: dict[str, Any],
        read_step_info: dict[str, Any],
        meta: dict[str, Any],
        dataset: str,
    ) -> None:
        self.instance_id = instance_id
        self.repo_path = repo_path
        self.repo_dir = repo_dir
        self.ground_truth = ground_truth
        self.read_step_info = read_step_info
        self.meta = meta
        self.dataset = dataset


def adapt_swe_explore_row(
    row: dict[str, Any],
) -> tuple[SWE_EXPLOREPublicTask, SWE_EXPLOREPrivateLabel]:
    """Adapt a SWE-Explore-like row into (public_task, private_label)."""
    if not isinstance(row, dict):
        raise TypeError("swe_explore row must be a dict")

    field_count = len(SWE_EXPLORE_FIELD_NAMES)
    has_repo_path = bool(row.get("repo_path"))
    has_repo_dir = bool(row.get("repo_dir"))
    has_ground_truth = isinstance(row.get("ground_truth"), dict) and bool(
        row.get("ground_truth")
    )
    has_read_step_info = isinstance(row.get("read_step_info"), dict) and bool(
        row.get("read_step_info")
    )
    has_meta = isinstance(row.get("meta"), dict) and bool(row.get("meta"))
    dataset = row.get("dataset")
    dataset_category = (
        dataset if isinstance(dataset, str) and len(dataset) <= 32 else "other"
    )

    public = SWE_EXPLOREPublicTask(
        field_count=field_count,
        has_repo_path=has_repo_path,
        has_repo_dir=has_repo_dir,
        has_ground_truth=has_ground_truth,
        has_read_step_info=has_read_step_info,
        has_meta=has_meta,
        dataset_category=dataset_category,
    )
    gt_raw = row.get("ground_truth")
    rsi_raw = row.get("read_step_info")
    meta_raw = row.get("meta")
    private = SWE_EXPLOREPrivateLabel(
        instance_id=str(row.get("instance_id", "")),
        repo_path=str(row.get("repo_path", "")),
        repo_dir=str(row.get("repo_dir", "")),
        ground_truth=dict(gt_raw) if isinstance(gt_raw, dict) else {},
        read_step_info=dict(rsi_raw) if isinstance(rsi_raw, dict) else {},
        meta=dict(meta_raw) if isinstance(meta_raw, dict) else {},
        dataset=str(row.get("dataset", "")),
    )
    return public, private


# ---------------------------------------------------------------------------
# Line range normalization (synthetic self-test / private in-memory only)
# ---------------------------------------------------------------------------


class LineRangeError(ValueError):
    """Raised when a line range cannot be normalized (invalid range)."""


def normalize_line_range(value: Any) -> tuple[int, int]:
    """Normalize a line range to ``(start, end)`` ints.

    Accepts:
      * ``[start, end]`` list of 2 ints
      * ``(start, end)`` tuple
      * ``{"start": S, "end": E}`` dict
      * ``"S-E"`` / ``"S:E"`` string

    Rejects (raises LineRangeError):
      * start > end
      * start < 1 (line numbers are 1-indexed)
      * non-integer values
      * missing start/end
      * more than 2 elements in a list

    Line ranges are PRIVATE in-memory validation only; they are never
    written to public artifacts.
    """
    start: int | None = None
    end: int | None = None

    if isinstance(value, (list, tuple)):
        if len(value) != 2:
            raise LineRangeError(
                f"line range list must have exactly 2 elements; got {len(value)}"
            )
        start_raw, end_raw = value
    elif isinstance(value, dict):
        if "start" not in value or "end" not in value:
            raise LineRangeError(
                "line range dict must have 'start' and 'end' keys"
            )
        start_raw = value["start"]
        end_raw = value["end"]
    elif isinstance(value, str):
        stripped = value.strip()
        # Accept "S-E" or "S:E"; do NOT accept negative ranges.
        match = re.fullmatch(r"\s*(\d+)\s*[-:]\s*(\d+)\s*", stripped)
        if not match:
            raise LineRangeError(
                f"line range string must be 'S-E' or 'S:E'; got {value!r}"
            )
        start_raw = int(match.group(1))
        end_raw = int(match.group(2))
    else:
        raise LineRangeError(
            f"line range must be list/tuple/dict/str; got {type(value).__name__}"
        )

    # Coerce to int; reject bool (bool is a subclass of int).
    if isinstance(start_raw, bool) or isinstance(end_raw, bool):
        raise LineRangeError("line range values must not be bool")
    try:
        start = int(start_raw)
        end = int(end_raw)
    except (TypeError, ValueError) as exc:
        raise LineRangeError(
            f"line range values must be integers; got {start_raw!r}, {end_raw!r}"
        ) from exc

    if start < 1:
        raise LineRangeError(
            f"line range start must be >= 1; got {start}"
        )
    if end < 1:
        raise LineRangeError(
            f"line range end must be >= 1; got {end}"
        )
    if start > end:
        raise LineRangeError(
            f"line range start ({start}) must be <= end ({end})"
        )
    return (start, end)


# ---------------------------------------------------------------------------
# Synthetic row builders (self-test only; never serialized with values)
# ---------------------------------------------------------------------------


def _build_synthetic_contextbench_row(
    *, missing_optional: bool = False
) -> dict[str, Any]:
    """Build a synthetic ContextBench-like row for self-test.

    The values are deliberately synthetic placeholder strings. They
    are NEVER written to any public artifact; only the adapted
    public_task / private_label separation is validated.
    """
    row: dict[str, Any] = {
        "instance_id": "synthetic-contextbench-001",
        "original_inst_id": "synthetic-001",
        "repo": "synthetic/repo",
        "repo_url": "https://example.invalid/synthetic/repo",
        "language": "python",
        "base_commit": "0" * 40,
        "gold_context": "synthetic gold context placeholder",
        "patch": "synthetic patch placeholder",
        "test_patch": "synthetic test patch placeholder",
        "problem_statement": "synthetic problem statement placeholder",
        "f2p": ["synthetic_test_a"],
        "p2p": ["synthetic_test_b"],
        "source": "synthetic_self_test",
    }
    if missing_optional:
        # Drop optional fields to test missing-field handling.
        row.pop("original_inst_id", None)
        row.pop("f2p", None)
        row.pop("p2p", None)
    return row


def _build_synthetic_swe_explore_row(
    *, missing_optional: bool = False
) -> dict[str, Any]:
    """Build a synthetic SWE-Explore-like row for self-test."""
    row: dict[str, Any] = {
        "instance_id": "synthetic-swe-explore-001",
        "repo_path": "/tmp/synthetic/repo",
        "repo_dir": "synthetic-repo",
        "ground_truth": {
            "patch": "synthetic patch placeholder",
            "test_patch": "synthetic test patch placeholder",
            "modified_files": ["src/main.py", "src/util.py"],
            "core_files": ["src/main.py"],
            "line_ranges": {"src/main.py": [[1, 10], [20, 30]]},
        },
        "read_step_info": {
            "file_maps": {"src/main.py": [[1, 5]]},
            "line_ranges": {"src/util.py": [[3, 8]]},
        },
        "meta": {"version": "synthetic-1"},
        "dataset": "synthetic_self_test",
    }
    if missing_optional:
        row.pop("read_step_info", None)
        row.pop("meta", None)
    return row


# ---------------------------------------------------------------------------
# Bounded HF datasets-server schema smoke (stdlib urllib only)
# ---------------------------------------------------------------------------


def _http_get_json(
    url: str, timeout: int = SMOKE_TIMEOUT_SECONDS
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
                "User-Agent": "OpenLocus-C4-schema-smoke/0.1 (bounded; stdlib)",
            },
        )
        with urllib.request.urlopen(  # noqa: S310 - bounded schema smoke
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


def _safe_endpoint_name(endpoint: str) -> str:
    """Return a short, sanitized endpoint label (no URL)."""
    if endpoint == "info":
        return "info"
    if endpoint == "splits":
        return "splits"
    if endpoint == "first-rows":
        return "first_rows"
    return "unknown"


def _smoke_benchmark(
    dataset_id: str,
    limit: int,
    built_in_field_names: tuple[str, ...],
    built_in_private_categories: tuple[str, ...],
    built_in_field_type_summary: dict[str, int],
    built_in_configs: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    """Run a bounded schema smoke for one benchmark.

    Returns aggregate-only smoke status. Raw rows are parsed in
    function scope to derive field names/types/counts and are then
    discarded. No raw response body is stored or returned in errors.
    """
    smoke: dict[str, Any] = {
        "attempted": True,
        "dataset_id": dataset_id,
        "limit_requested": limit,
        "network_calls": 0,
        "info_status": "unavailable",
        "splits_status": "unavailable",
        "first_rows_status": "unavailable",
        "first_rows_failure_category": None,
        "row_level_data_returned": False,
        "raw_response_stored": False,
        "configs_observed_count": 0,
        "splits_observed_count": 0,
        "field_names_source": "built_in_fallback",
        "field_names_schema_only": list(built_in_field_names),
        "field_count": len(built_in_field_names),
        "field_type_summary": dict(built_in_field_type_summary),
        "private_field_categories_detected": list(
            built_in_private_categories
        ),
        "truncated_rows_observed": False,
    }

    base = _HF_DATASETS_SERVER

    # 1. /info
    info_url = (
        f"{base}/info?dataset={urllib.parse.quote(dataset_id, safe='/')}"
    )
    info, info_status, _ = _http_get_json(info_url)
    smoke["network_calls"] += 1
    if info_status == "pass" and isinstance(info, dict):
        smoke["info_status"] = "pass"

    # 2. /splits (source of truth for first-rows attempts)
    splits_url = (
        f"{base}/splits?dataset={urllib.parse.quote(dataset_id, safe='/')}"
    )
    splits, splits_status, _ = _http_get_json(splits_url)
    smoke["network_calls"] += 1
    config_split_pairs: list[tuple[str, str]] = []
    if splits_status == "pass" and isinstance(splits, dict):
        smoke["splits_status"] = "pass"
        for s in splits.get("splits", []) or []:
            if isinstance(s, dict):
                cfg = s.get("config")
                spl = s.get("split")
                if isinstance(cfg, str) and isinstance(spl, str):
                    config_split_pairs.append((cfg, spl))
    smoke["configs_observed_count"] = len(
        {c for c, _ in config_split_pairs}
    )
    smoke["splits_observed_count"] = len(config_split_pairs)

    # 3. /first-rows for each (config, split) up to limit. Parse
    #    features/schema and row count/truncation booleans only; raw
    #    rows remain local and are discarded immediately.
    probed = 0
    first_rows_ok = 0
    for cfg, spl in config_split_pairs:
        if probed >= limit:
            break
        fr_url = (
            f"{base}/first-rows?dataset="
            f"{urllib.parse.quote(dataset_id, safe='/')}"
            f"&config={urllib.parse.quote(cfg)}"
            f"&split={urllib.parse.quote(spl)}"
        )
        fr, fr_status, code = _http_get_json(fr_url)
        smoke["network_calls"] += 1
        probed += 1
        if fr_status == "pass" and isinstance(fr, dict):
            first_rows_ok += 1
            features = fr.get("features")
            if isinstance(features, list):
                names = [
                    f.get("name")
                    for f in features
                    if isinstance(f, dict) and f.get("name")
                ]
                if names:
                    # Use observed schema if it is non-empty.
                    smoke["field_names_schema_only"] = [
                        str(n) for n in names
                    ]
                    smoke["field_count"] = len(names)
                    smoke["field_names_source"] = "smoke_observed"
                    # Build a coarse type summary from _type fields.
                    type_summary: dict[str, int] = {}
                    for f in features:
                        if isinstance(f, dict):
                            t = f.get("type")
                            if isinstance(t, dict):
                                tname = str(t.get("_type", "object"))
                            elif isinstance(t, str):
                                tname = t
                            else:
                                tname = "unknown"
                            type_summary[tname] = (
                                type_summary.get(tname, 0) + 1
                            )
                    if type_summary:
                        smoke["field_type_summary"] = type_summary
            # Row count / truncation booleans (aggregate-only).
            if isinstance(fr.get("truncated"), bool):
                smoke["truncated_rows_observed"] = bool(fr["truncated"])
            # CRITICAL: do NOT retain fr["rows"] — discard immediately.
            # row_level_data_returned stays false.
        else:
            if code is not None:
                smoke["first_rows_failure_category"] = f"http_{code}"
            else:
                smoke["first_rows_failure_category"] = (
                    "network_or_parse_failure"
                )

    if probed == 0:
        smoke["first_rows_status"] = "unavailable"
        if not smoke["first_rows_failure_category"]:
            smoke["first_rows_failure_category"] = "no_splits_from_source_of_truth"
    elif first_rows_ok == 0:
        smoke["first_rows_status"] = "unavailable"
    elif first_rows_ok < probed:
        smoke["first_rows_status"] = "partial"
    else:
        smoke["first_rows_status"] = "pass"

    return smoke


def schema_smoke_contextbench(limit: int) -> dict[str, Any]:
    """Bounded schema smoke for ContextBench."""
    return _smoke_benchmark(
        dataset_id=CONTEXTBENCH_DATASET_ID,
        limit=limit,
        built_in_field_names=CONTEXTBENCH_FIELD_NAMES,
        built_in_private_categories=CONTEXTBENCH_PRIVATE_FIELD_CATEGORIES,
        built_in_field_type_summary=CONTEXTBENCH_FIELD_TYPE_SUMMARY,
        built_in_configs=CONTEXTBENCH_CONFIGS,
    )


def schema_smoke_swe_explore(limit: int) -> dict[str, Any]:
    """Bounded schema smoke for SWE-Explore."""
    return _smoke_benchmark(
        dataset_id=SWE_EXPLORE_DATASET_ID,
        limit=limit,
        built_in_field_names=SWE_EXPLORE_FIELD_NAMES,
        built_in_private_categories=SWE_EXPLORE_PRIVATE_FIELD_CATEGORIES,
        built_in_field_type_summary=SWE_EXPLORE_FIELD_TYPE_SUMMARY,
        built_in_configs=SWE_EXPLORE_CONFIGS,
    )


# ---------------------------------------------------------------------------
# Canonical aggregate report builder
# ---------------------------------------------------------------------------


def _observed_config_summary(
    spec_config: dict[str, Any],
    field_names: tuple[str, ...],
    field_type_summary: dict[str, int],
    private_categories: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "config": spec_config["config"],
        "splits": [dict(s) for s in spec_config["splits"]],
        "field_count": len(field_names),
        "field_type_summary": dict(field_type_summary),
        "field_names_schema_only": list(field_names),
        "private_field_categories_detected": list(private_categories),
    }


def _benchmark_report(
    name: str,
    spec: dict[str, Any],
    field_names: tuple[str, ...],
    field_type_summary: dict[str, int],
    private_categories: tuple[str, ...],
    configs: tuple[dict[str, Any], ...],
    smoke: dict[str, Any] | None,
    adapter_self_test_status: str,
) -> dict[str, Any]:
    license_status = spec["license_status"]
    row_level = bool(spec["row_level_redistribution_allowed"])
    derived = bool(spec["derived_label_publication_allowed"])

    if not row_level and not derived:
        public_release_status = "blocked_by_license"
    else:
        # We never actually allow release; fail closed.
        public_release_status = "blocked_by_license"

    observed_configs = [
        _observed_config_summary(
            c, field_names, field_type_summary, private_categories
        )
        for c in configs
    ]

    benchmark_report: dict[str, Any] = {
        "dataset_id": spec["dataset_id"],
        "discovery_status": "known_schema_only",
        "schema_smoke_status": (
            "not_attempted" if smoke is None else smoke["first_rows_status"]
        ),
        "adapter_self_test_status": adapter_self_test_status,
        "public_release_status": public_release_status,
        "license_status": license_status,
        "row_level_redistribution_allowed": row_level,
        "derived_label_publication_allowed": derived,
        "observed_configs": observed_configs,
    }
    if smoke is not None:
        benchmark_report["schema_smoke"] = smoke
    return benchmark_report


def build_canonical_report(
    *,
    self_test: bool = False,
    schema_smoke_results: dict[str, dict[str, Any]] | None = None,
    adapter_self_test_status: str = "pass",
) -> dict[str, Any]:
    """Build the canonical aggregate-only C4 report.

    Uses built-in known schema metadata + synthetic self-test status.
    No network calls (unless schema_smoke_results is provided).
    """
    spec_hash = compute_spec_hash()
    cb_spec = _benchmark_spec("contextbench")
    se_spec = _benchmark_spec("swe_explore")

    cb_smoke = (
        schema_smoke_results.get("contextbench")
        if schema_smoke_results
        else None
    )
    se_smoke = (
        schema_smoke_results.get("swe_explore")
        if schema_smoke_results
        else None
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "self_test": bool(self_test),
        "aggregate_only_public_artifact": True,
        "not_evidence": True,
        "candidate_not_fact": True,
        # No-claim flags — ALL false.
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "runtime_clean_general_algorithm_claimed": False,
        "downstream_agent_value_proven": False,
        "ood_temporal_supported": False,
        "quiver_systems_supported": False,
        "spec_hash": spec_hash,
        "safety_invariants": {inv: False for inv in SAFETY_INVARIANTS},
        "benchmarks": {
            "contextbench": _benchmark_report(
                "contextbench",
                cb_spec,
                CONTEXTBENCH_FIELD_NAMES,
                CONTEXTBENCH_FIELD_TYPE_SUMMARY,
                CONTEXTBENCH_PRIVATE_FIELD_CATEGORIES,
                CONTEXTBENCH_CONFIGS,
                cb_smoke,
                adapter_self_test_status,
            ),
            "swe_explore": _benchmark_report(
                "swe_explore",
                se_spec,
                SWE_EXPLORE_FIELD_NAMES,
                SWE_EXPLORE_FIELD_TYPE_SUMMARY,
                SWE_EXPLORE_PRIVATE_FIELD_CATEGORIES,
                SWE_EXPLORE_CONFIGS,
                se_smoke,
                adapter_self_test_status,
            ),
        },
        "schema_smoke_attempted": bool(schema_smoke_results),
        "new_provider_calls": 0,
        "new_network_calls": (
            sum(
                (r.get("network_calls", 0) if isinstance(r, dict) else 0)
                for r in (schema_smoke_results or {}).values()
            )
            if schema_smoke_results
            else 0
        ),
        "framing": {
            "promotion_readiness_claimed": False,
            "default_change_claimed": False,
            "external_benchmark_result_claimed": False,
            "downstream_agent_value_claimed": False,
            "ood_temporal_claimed": False,
            "quiver_systems_claimed": False,
            "evidencecore_semantics_change_claimed": False,
            "signal_strength": "adapter_schema_readiness_only_synthetic_self_test",
            "is_full_external_benchmark_evaluation": False,
        },
    }

    # Fail-closed forbidden scan. If the report would leak, fail.
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        raise ValueError(
            "c4_external_benchmark_adapters public report would leak "
            f"forbidden content: {scan['categories']}"
        )
    return report


def build_schema_smoke_report(
    benchmark: str,
    limit: int,
    *,
    self_test: bool = False,
) -> dict[str, Any]:
    """Build an aggregate-only schema-smoke report for one or all benchmarks.

    The smoke report follows the same aggregate-only boundary as the
    canonical report. Raw HF payloads are parsed in function scope
    and discarded; only field names/types/counts/status are emitted.
    """
    smoke_results: dict[str, dict[str, Any]] = {}
    if benchmark in ("contextbench", "all"):
        smoke_results["contextbench"] = schema_smoke_contextbench(limit)
    if benchmark in ("swe_explore", "all"):
        smoke_results["swe_explore"] = schema_smoke_swe_explore(limit)

    report = build_canonical_report(
        self_test=self_test,
        schema_smoke_results=smoke_results,
        adapter_self_test_status="pass",
    )
    report["schema_smoke"] = True
    report["benchmark_selected"] = benchmark
    report["limit_applied"] = limit

    # Re-run forbidden scan after adding smoke fields.
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        raise ValueError(
            "c4_external_benchmark_adapters smoke report would leak "
            f"forbidden content: {scan['categories']}"
        )
    return report


# ---------------------------------------------------------------------------
# C4.2 ContextBench verified subset row-mapping smoke (bounded; real rows
# stay in function scope / memory; only aggregate-only artifact emitted)
# ---------------------------------------------------------------------------


def _extract_first_rows(raw: Any) -> tuple[list[dict[str, Any]], list[str], bool]:
    """Extract (rows, field_names, truncated) from a datasets-server
    ``/first-rows`` JSON payload.

    Rows are returned to the caller ONLY so the caller can adapt each row
    in function scope and immediately discard the raw row. The caller MUST
    NOT persist raw rows. Field names are schema-only observations.
    """
    if not isinstance(raw, dict):
        return [], [], False
    features = raw.get("features")
    field_names: list[str] = []
    if isinstance(features, list):
        for f in features:
            if isinstance(f, dict) and isinstance(f.get("name"), str):
                field_names.append(f["name"])
    rows_raw = raw.get("rows")
    rows: list[dict[str, Any]] = []
    if isinstance(rows_raw, list):
        for r in rows_raw:
            # datasets-server wraps each row as {"row": {...}, "truncated_cells": [...]}
            if isinstance(r, dict) and isinstance(r.get("row"), dict):
                rows.append(r["row"])
            elif isinstance(r, dict):
                # Some payloads may return the row dict directly.
                rows.append(r)
    truncated = bool(raw.get("truncated", False))
    return rows, field_names, truncated


def _row_field_non_empty(row: dict[str, Any], field: str) -> bool:
    """Return True if ``row[field]`` is present and non-empty."""
    if field not in row:
        return False
    val = row.get(field)
    if val is None:
        return False
    if isinstance(val, str):
        return len(val) > 0
    if isinstance(val, (list, tuple, dict)):
        return len(val) > 0
    return True


# Public-task presence keys (aggregate-safe booleans only, never values).
_PUBLIC_TASK_PRESENCE_KEYS: tuple[str, ...] = (
    "has_original_inst_id",
    "has_f2p",
    "has_p2p",
    "has_repo_locator",
    "has_private_label_payload",
)

# Private-label fields whose presence (NOT value) is counted. These names
# are schema-only category labels; the corresponding values are never emitted.
_PRIVATE_LABEL_FIELDS: tuple[str, ...] = (
    "instance_id",
    "original_inst_id",
    "repo",
    "repo_url",
    "base_commit",
    "gold_context",
    "patch",
    "test_patch",
    "problem_statement",
    "f2p",
    "p2p",
    "source",
)


def _build_row_map_summary(
    rows: list[dict[str, Any]],
    *,
    dataset_id: str,
    config: str,
    split: str,
    row_limit_requested: int,
    observed_field_names: list[str] | None,
    truncated_rows: bool,
) -> dict[str, Any]:
    """Build the aggregate-only row-map summary from in-memory rows.

    Real rows live only in process memory and are not persisted. This
    function receives bounded in-memory rows, adapts them locally, and emits
    only field-presence counts plus fixed failure categories. No row-level
    values, hashes, paths, spans, or snippets are emitted.
    """
    rows_seen = 0
    rows_mapped = 0
    rows_failed = 0

    # field_presence_counts: schema field names -> count of non-empty rows.
    field_presence_counts: dict[str, int] = {fn: 0 for fn in CONTEXTBENCH_FIELD_NAMES}
    # public_task_presence_counts: aggregate booleans -> count of True.
    public_task_presence_counts: dict[str, int] = {k: 0 for k in _PUBLIC_TASK_PRESENCE_KEYS}
    # private_field_presence_counts: private category name -> count of non-empty.
    private_field_presence_counts: dict[str, int] = {fn: 0 for fn in _PRIVATE_LABEL_FIELDS}
    # failure_category_counts: fixed categories only.
    failure_category_counts: dict[str, int] = {c: 0 for c in ROW_MAP_FAILURE_CATEGORIES}

    # Track whether any private-label value leaked into a would-be public
    # field. We do this by ensuring the adapted public task object never
    # carries private attrs (already enforced by __slots__).
    private_label_isolation_verified = True
    adapter_assertions_passed = True

    for row in rows:
        rows_seen += 1
        try:
            row_failed = False
            if not isinstance(row, dict):
                failure_category_counts["wrong_type"] += 1
                rows_failed += 1
                continue
            # Adapt the row in function scope. The public/private objects
            # are local-only; neither is ever serialized with row values.
            public, private = adapt_contextbench_row(row)

            # Assert the public task carries NO private attrs.
            for priv_attr in _PRIVATE_LABEL_FIELDS:
                if hasattr(public, priv_attr):
                    private_label_isolation_verified = False
                    failure_category_counts["private_field_leak"] += 1
                    adapter_assertions_passed = False
                    row_failed = True

            # Assert the public task presence booleans are actual booleans.
            for pk in _PUBLIC_TASK_PRESENCE_KEYS:
                v = getattr(public, pk, None)
                if not isinstance(v, bool):
                    failure_category_counts["mapping_error"] += 1
                    adapter_assertions_passed = False
                    row_failed = True

            # Count field presence (non-empty) for schema field names.
            for fn in CONTEXTBENCH_FIELD_NAMES:
                if _row_field_non_empty(row, fn):
                    field_presence_counts[fn] += 1

            # Count public_task presence booleans.
            for pk in _PUBLIC_TASK_PRESENCE_KEYS:
                if bool(getattr(public, pk, False)):
                    public_task_presence_counts[pk] += 1

            # Count private-label field presence (NOT values).
            for pfn in _PRIVATE_LABEL_FIELDS:
                if _row_field_non_empty(row, pfn):
                    private_field_presence_counts[pfn] += 1

            if row_failed:
                rows_failed += 1
            else:
                rows_mapped += 1
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            failure_category_counts["mapping_error"] += 1
            rows_failed += 1
            # Record the exception category name only (never the message,
            # which could contain row values).
            _ = type(exc).__name__
        except Exception as exc:  # noqa: BLE001 - last resort
            failure_category_counts["unexpected_exception"] += 1
            rows_failed += 1
            _ = type(exc).__name__

    assertion_failure = (
        not private_label_isolation_verified
        or not adapter_assertions_passed
        or failure_category_counts["private_field_leak"] > 0
    )

    # Derive overall status. If isolation/assertion gates fail, fail closed
    # instead of reporting a passing smoke with false safety booleans.
    if rows_seen == 0:
        status = "unavailable"
        failure_category_counts["no_rows_returned"] = 1
    elif assertion_failure:
        status = "fail_schema_contract"
    elif rows_failed > 0 and rows_mapped == 0:
        status = "fail_schema_contract"
    elif rows_failed > 0:
        status = "partial"
    else:
        status = "pass"

    # Use observed field names if provided and non-empty, else built-in.
    emitted_field_names = (
        list(observed_field_names)
        if observed_field_names
        else list(CONTEXTBENCH_FIELD_NAMES)
    )

    summary: dict[str, Any] = {
        "mode": "contextbench_verified_row_mapping_smoke",
        "benchmark": "contextbench",
        "dataset_id": dataset_id,
        "config": config,
        "split": split,
        "row_limit_requested": row_limit_requested,
        "rows_seen": rows_seen,
        "rows_mapped": rows_mapped,
        "rows_failed": rows_failed,
        "truncated_rows_observed": bool(truncated_rows),
        "field_names_schema_only": emitted_field_names,
        "field_count": len(emitted_field_names),
        "field_presence_counts": field_presence_counts,
        "public_task_presence_counts": public_task_presence_counts,
        "private_field_presence_counts": private_field_presence_counts,
        "failure_category_counts": failure_category_counts,
        "private_label_isolation_verified": private_label_isolation_verified,
        "adapter_assertions_passed": adapter_assertions_passed,
        "raw_rows_persisted": False,
        "row_level_values_emitted": False,
        "row_level_hashes_emitted": False,
        "raw_response_stored": False,
        "status": status,
    }
    return summary


def _row_map_smoke_contextbench_verified(
    config: str,
    split: str,
    row_limit: int,
) -> dict[str, Any]:
    """Run the bounded C4.2 ContextBench verified subset row-mapping smoke.

    Reads real HF datasets-server ``/first-rows`` preview rows for
    ``contextbench_verified/train`` via ``_http_get_json()``. Each real row
    is adapted in function scope via ``adapt_contextbench_row``; raw rows
    are discarded immediately after adaptation. Only an aggregate-only
    summary is returned. On network/HF failure, a sanitized ``unavailable``
    status is produced (no raw response body).
    """
    base = _HF_DATASETS_SERVER
    fr_url = (
        f"{base}/first-rows?dataset="
        f"{urllib.parse.quote(CONTEXTBENCH_DATASET_ID, safe='/')}"
        f"&config={urllib.parse.quote(config)}"
        f"&split={urllib.parse.quote(split)}"
    )
    raw, status_code, http_code = _http_get_json(fr_url)

    # Build the report skeleton with standard no-claim flags.
    report: dict[str, Any] = {
        "schema_version": ROW_MAP_SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": ROW_MAP_CLAIM_LEVEL,
        "aggregate_only_public_artifact": True,
        "not_evidence": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "runtime_clean_general_algorithm_claimed": False,
        "downstream_agent_value_proven": False,
        "ood_temporal_supported": False,
        "quiver_systems_supported": False,
        "new_network_calls": 1,
        "new_provider_calls": 0,
        "endpoint_unavailable": status_code != "pass",
        "http_code_observed": (http_code if isinstance(http_code, int) else None),
    }

    if status_code != "pass" or raw is None:
        # Sanitized unavailable status; no raw response body.
        summary = _build_row_map_summary(
            [],
            dataset_id=CONTEXTBENCH_DATASET_ID,
            config=config,
            split=split,
            row_limit_requested=row_limit,
            observed_field_names=list(CONTEXTBENCH_FIELD_NAMES),
            truncated_rows=False,
        )
        summary["status"] = "unavailable"
        summary["failure_category_counts"]["endpoint_unavailable"] = 1
        report.update(summary)
    else:
        # Extract rows + schema in function scope; raw rows are local only.
        rows, observed_field_names, truncated = _extract_first_rows(raw)
        # Discard the raw payload immediately after extraction.
        del raw
        # Bound to row_limit.
        bounded_rows = rows[:row_limit]
        del rows
        summary = _build_row_map_summary(
            bounded_rows,
            dataset_id=CONTEXTBENCH_DATASET_ID,
            config=config,
            split=split,
            row_limit_requested=row_limit,
            observed_field_names=observed_field_names,
            truncated_rows=truncated,
        )
        # Discard the bounded rows immediately after aggregation.
        del bounded_rows
        report.update(summary)

    # Fail-closed forbidden scan before returning. If the public report
    # would leak, fail.
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        # Downgrade status and mark the leak.
        report["status"] = "fail_forbidden_leak"
        report["failure_category_counts"]["public_artifact_leak"] = (
            report["failure_category_counts"].get("public_artifact_leak", 0) + 1
        )
    return report


def build_row_map_smoke_report(
    config: str,
    split: str,
    row_limit: int,
    *,
    self_test: bool = False,
) -> dict[str, Any]:
    """Build the C4.2 row-mapping smoke report (aggregate-only)."""
    if config not in ROW_MAP_ALLOWED_CONFIGS:
        raise ValueError(
            f"row-map smoke only supports configs "
            f"{sorted(ROW_MAP_ALLOWED_CONFIGS)}; got {config!r}"
        )
    report = _row_map_smoke_contextbench_verified(config, split, row_limit)
    report["row_map_smoke"] = True
    report["benchmark_selected"] = "contextbench"
    report["config_selected"] = config
    report["split_selected"] = split
    report["row_limit_applied"] = row_limit
    report["self_test"] = bool(self_test)

    # Re-run forbidden scan after adding smoke fields.
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        raise ValueError(
            "c4_external_benchmark_adapters row-map report would leak "
            f"forbidden content: {scan['categories']}"
        )
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _self_test_contextbench_adapter_separation() -> None:
    """ContextBench synthetic row separates public aggregate metadata
    from private fields; repo/commit locators are not public."""
    row = _build_synthetic_contextbench_row()
    public, private = adapt_contextbench_row(row)

    # Public task carries aggregate-safe metadata only.
    assert public.field_count == len(CONTEXTBENCH_FIELD_NAMES)
    assert public.has_original_inst_id is True
    assert public.has_f2p is True
    assert public.has_p2p is True
    assert public.has_repo_locator is True
    assert public.has_private_label_payload is True
    assert public.language_category == "python"
    assert public.source_category == "synthetic_self_test"

    # Public task must NOT carry row-level repo/commit/patch values.
    assert not hasattr(public, "repo")
    assert not hasattr(public, "repo_url")
    assert not hasattr(public, "base_commit")
    assert not hasattr(public, "patch")
    assert not hasattr(public, "test_patch")
    assert not hasattr(public, "problem_statement")
    assert not hasattr(public, "gold_context")
    assert not hasattr(public, "f2p")
    assert not hasattr(public, "p2p")
    assert not hasattr(public, "instance_id")
    assert not hasattr(public, "original_inst_id")

    # Private label retains all row-level payload.
    assert private.instance_id == row["instance_id"]
    assert private.repo == row["repo"]
    assert private.repo_url == row["repo_url"]
    assert private.base_commit == row["base_commit"]
    assert private.patch == row["patch"]
    assert private.test_patch == row["test_patch"]
    assert private.problem_statement == row["problem_statement"]
    assert private.gold_context == row["gold_context"]
    assert private.f2p == row["f2p"]
    assert private.p2p == row["p2p"]

    # Missing optional fields handled gracefully.
    row_missing = _build_synthetic_contextbench_row(missing_optional=True)
    pub_m, priv_m = adapt_contextbench_row(row_missing)
    assert pub_m.has_original_inst_id is False
    assert pub_m.has_f2p is False
    assert pub_m.has_p2p is False
    assert priv_m.original_inst_id == ""
    assert priv_m.f2p == []
    print("self-test contextbench adapter separation: ok")


def _self_test_swe_explore_adapter_separation() -> None:
    """SWE-Explore synthetic row separates ground_truth.*, file maps,
    line ranges, read_step_info, repo paths."""
    row = _build_synthetic_swe_explore_row()
    public, private = adapt_swe_explore_row(row)

    assert public.field_count == len(SWE_EXPLORE_FIELD_NAMES)
    assert public.has_repo_path is True
    assert public.has_repo_dir is True
    assert public.has_ground_truth is True
    assert public.has_read_step_info is True
    assert public.has_meta is True
    assert public.dataset_category == "synthetic_self_test"

    # Public must NOT carry private nested objects.
    assert not hasattr(public, "ground_truth")
    assert not hasattr(public, "read_step_info")
    assert not hasattr(public, "repo_path")
    assert not hasattr(public, "repo_dir")
    assert not hasattr(public, "instance_id")

    # Private retains ground_truth.* and read_step_info.
    assert private.repo_path == row["repo_path"]
    assert private.repo_dir == row["repo_dir"]
    assert isinstance(private.ground_truth, dict)
    assert "patch" in private.ground_truth
    assert "test_patch" in private.ground_truth
    assert "modified_files" in private.ground_truth
    assert "core_files" in private.ground_truth
    assert "line_ranges" in private.ground_truth
    assert isinstance(private.read_step_info, dict)
    assert "file_maps" in private.read_step_info

    # Missing optional handled.
    row_missing = _build_synthetic_swe_explore_row(missing_optional=True)
    pub_m, priv_m = adapt_swe_explore_row(row_missing)
    assert pub_m.has_read_step_info is False
    assert pub_m.has_meta is False
    assert priv_m.read_step_info == {}
    assert priv_m.meta == {}
    print("self-test swe_explore adapter separation: ok")


def _self_test_line_range_normalization() -> None:
    """Line range normalization accepts valid and rejects invalid ranges."""
    # Valid forms.
    assert normalize_line_range([1, 10]) == (1, 10)
    assert normalize_line_range((5, 8)) == (5, 8)
    assert normalize_line_range({"start": 3, "end": 7}) == (3, 7)
    assert normalize_line_range("12-34") == (12, 34)
    assert normalize_line_range("12:34") == (12, 34)
    assert normalize_line_range([1, 1]) == (1, 1)

    # Invalid: start > end.
    for bad in ([10, 5], {"start": 10, "end": 5}, "10-5"):
        try:
            normalize_line_range(bad)
        except LineRangeError:
            pass
        else:
            raise AssertionError(f"expected LineRangeError for {bad!r}")

    # Invalid: start < 1.
    for bad in ([0, 5], {"start": -1, "end": 5}, "0-5"):
        try:
            normalize_line_range(bad)
        except LineRangeError:
            pass
        else:
            raise AssertionError(f"expected LineRangeError for {bad!r}")

    # Invalid: non-integer.
    for bad in (
        ["a", "b"],
        {"start": "x", "end": "y"},
        "not-a-range",
        123,
        None,
        [1, 2, 3],
        [1],
    ):
        try:
            normalize_line_range(bad)
        except LineRangeError:
            pass
        else:
            raise AssertionError(f"expected LineRangeError for {bad!r}")

    # Invalid: bool values.
    try:
        normalize_line_range([True, False])
    except LineRangeError:
        pass
    else:
        raise AssertionError("expected LineRangeError for bool range")
    print("self-test line range normalization: ok")


def _self_test_forbidden_scan_rejects_injection() -> None:
    """Forbidden scanner rejects injected row-level keys/values."""
    # Build a multiline patch value using chr(10) so the newline is
    # present at runtime without relying on escape-sequence handling
    # in the source literal.
    _nl = chr(10)
    multiline_patch = "diff --git a/x b/x" + _nl + "+leak" + _nl
    # Injected forbidden keys.
    bad_report = {
        "instance_id": "leak",
        "repo": "src/leak.py",
        "patch": multiline_patch,
        "problem_statement": "leak",
        "content_sha": "a" * 40,
        "gold_spans": [[1, 2]],
        "private_labels": "leak",
        "leaked_line_range_dash": "12-34",
        "leaked_line_range_colon": "12:34",
    }
    violations = _scan_forbidden(bad_report)
    cats = {v["category"] for v in violations}
    assert "forbidden_key" in cats, cats
    assert "hex_digest_value" in cats, cats
    assert "path_like_value" in cats, cats
    assert "multiline_value" in cats, cats
    assert "line_range_value" in cats, cats

    summary = _forbidden_scan_summary(bad_report)
    assert summary["status"] == "fail"
    assert summary["violations_count"] > 0
    assert "forbidden_key" in summary["categories"]

    # A clean report passes.
    clean = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": "Contextbench/ContextBench",
        "field_names_schema_only": ["instance_id", "patch", "repo_url"],
        "private_field_categories_detected": [
            "ground_truth",
            "ground_truth.patch",
        ],
    }
    clean_violations = _scan_forbidden(clean)
    assert clean_violations == [], clean_violations
    clean_summary = _forbidden_scan_summary(clean)
    assert clean_summary["status"] == "pass"
    assert clean_summary["violations_count"] == 0
    print("self-test forbidden scan rejects injection: ok")


def _self_test_no_claim_flags_exactly_false() -> None:
    """No-claim flags are exactly false in the canonical report."""
    report = build_canonical_report(self_test=True)
    for flag in NO_CLAIM_FLAGS:
        assert report[flag] is False, (flag, report[flag])
    for inv in SAFETY_INVARIANTS:
        assert report["safety_invariants"][inv] is False, (
            inv,
            report["safety_invariants"][inv],
        )
    assert report["aggregate_only_public_artifact"] is True
    assert report["not_evidence"] is True
    assert report["candidate_not_fact"] is True
    print("self-test no-claim flags exactly false: ok")


def _self_test_spec_hash_deterministic() -> None:
    """Spec hash is stable and excludes timestamps/network/raw rows."""
    h1 = compute_spec_hash()
    h2 = compute_spec_hash()
    assert h1 == h2, "spec hash must be deterministic"
    assert len(h1) == 64, "spec hash must be sha256 hex"
    # The spec dict itself must not contain timestamps or network output.
    spec = build_spec()
    spec_json = _canonical_json(spec)
    # No ISO-timestamp-like substring (rough check).
    assert "generated_at" not in spec_json
    assert "network_calls" not in spec_json
    assert "first_rows" not in spec_json
    # No raw row payloads.
    for forbidden_substring in (
        "synthetic patch",
        "synthetic gold context",
        "synthetic problem statement",
        "/tmp/synthetic",
        "src/main.py",
    ):
        assert forbidden_substring not in spec_json, forbidden_substring
    # The canonical report's spec_hash matches.
    report = build_canonical_report(self_test=True)
    assert report["spec_hash"] == h1
    print("self-test spec hash deterministic: ok")


def _self_test_aggregate_only_report() -> None:
    """Canonical report has no raw row values/labels/paths/spans/
    problem statements/patches."""
    report = build_canonical_report(self_test=True)
    # Forbidden scan must pass on the canonical report.
    assert report["forbidden_scan"]["status"] == "pass", report[
        "forbidden_scan"
    ]
    assert report["forbidden_scan"]["violations_count"] == 0

    # Re-scan to be sure (defensive).
    rescan = _forbidden_scan_summary(report)
    assert rescan["status"] == "pass", rescan

    # Spot-check: no row-level payload substrings anywhere in the report.
    report_json = json.dumps(report, sort_keys=True)
    for forbidden_substring in (
        "synthetic patch",
        "synthetic gold context",
        "synthetic problem statement",
        "synthetic test patch",
        "/tmp/synthetic",
        "src/main.py",
        "ground_truth.patch",
    ):
        # "ground_truth.patch" appears in private_field_categories_detected
        # as a schema-only category name (dotted field path, not a file
        # path). It is allowed under the schema-only container. So we
        # check that the scanner itself passes (done above) rather than
        # asserting the substring is absent.
        if forbidden_substring == "ground_truth.patch":
            # This IS allowed as a schema-only category name.
            continue
        assert forbidden_substring not in report_json, forbidden_substring

    # No-claim flags present and false.
    for flag in NO_CLAIM_FLAGS:
        assert report[flag] is False

    # Benchmarks have required status fields.
    for bench in ("contextbench", "swe_explore"):
        b = report["benchmarks"][bench]
        assert "discovery_status" in b
        assert "schema_smoke_status" in b
        assert "adapter_self_test_status" in b
        assert "public_release_status" in b
        assert b["public_release_status"] == "blocked_by_license"
        assert b["row_level_redistribution_allowed"] is False
        assert b["derived_label_publication_allowed"] is False
        assert b["license_status"] in (
            CONTEXTBENCH_LICENSE_STATUS,
            SWE_EXPLORE_LICENSE_STATUS,
        )
        # Observed configs carry schema-only field names.
        for cfg in b["observed_configs"]:
            assert "field_count" in cfg
            assert "field_type_summary" in cfg
            assert "field_names_schema_only" in cfg
            assert "private_field_categories_detected" in cfg
            assert isinstance(cfg["field_names_schema_only"], list)
    print("self-test aggregate-only report: ok")


def _self_test_forbidden_scan_injection_blocked_at_generation() -> None:
    """If the public report would leak, generation must fail (fail-closed)."""
    # Inject a forbidden key into a would-be report and confirm the
    # scanner catches it (simulating a leak before write).
    report = build_canonical_report(self_test=True)
    # Tamper: add a forbidden key with a leaked value. Use chr(10) for
    # the newline so the runtime value is genuinely multiline.
    _nl = chr(10)
    report["patch"] = "diff --git a/x b/x" + _nl + "+leak" + _nl
    report["instance_id"] = "leak-001"
    report["content_sha"] = "a" * 40
    scan = _forbidden_scan_summary(report)
    assert scan["status"] == "fail", scan
    assert scan["violations_count"] >= 3, scan
    assert "forbidden_key" in scan["categories"]
    print("self-test forbidden scan blocks leak at generation: ok")


def _self_test_schema_smoke_report_shape() -> None:
    """Schema-smoke report shape is aggregate-only and scanner-clean
    without performing network access."""
    # Use an injected aggregate-only synthetic smoke result so --self-test
    # remains genuinely no-network. Real HF calls are only behind explicit
    # --schema-smoke.
    synthetic_smoke = {
        "attempted": True,
        "dataset_id": CONTEXTBENCH_DATASET_ID,
        "limit_requested": 2,
        "network_calls": 0,
        "info_status": "pass",
        "splits_status": "pass",
        "first_rows_status": "pass",
        "first_rows_failure_category": None,
        "row_level_data_returned": False,
        "raw_response_stored": False,
        "configs_observed_count": 1,
        "splits_observed_count": 1,
        "field_names_source": "synthetic_no_network_self_test",
        "field_names_schema_only": list(CONTEXTBENCH_FIELD_NAMES),
        "field_count": len(CONTEXTBENCH_FIELD_NAMES),
        "field_type_summary": dict(CONTEXTBENCH_FIELD_TYPE_SUMMARY),
        "private_field_categories_detected": list(
            CONTEXTBENCH_PRIVATE_FIELD_CATEGORIES
        ),
        "truncated_rows_observed": False,
    }
    report = build_canonical_report(
        self_test=True,
        schema_smoke_results={"contextbench": synthetic_smoke},
        adapter_self_test_status="pass",
    )
    report["schema_smoke"] = True
    report["benchmark_selected"] = "contextbench"
    report["limit_applied"] = 2
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    assert report["schema_smoke"] is True
    assert report["benchmark_selected"] == "contextbench"
    assert report["limit_applied"] == 2
    assert report["forbidden_scan"]["status"] == "pass", report[
        "forbidden_scan"
    ]
    cb = report["benchmarks"]["contextbench"]
    assert "schema_smoke" in cb
    smoke = cb["schema_smoke"]
    assert smoke["attempted"] is True
    assert smoke["network_calls"] == 0
    assert smoke["row_level_data_returned"] is False
    assert smoke["raw_response_stored"] is False
    # Status is one of the allowed values.
    assert smoke["first_rows_status"] in ("pass", "partial", "unavailable")
    assert smoke["info_status"] in ("pass", "unavailable")
    assert smoke["splits_status"] in ("pass", "unavailable")
    # Field names present (from built-in fallback or smoke-observed).
    assert len(smoke["field_names_schema_only"]) > 0
    print("self-test schema smoke report shape: ok")


def _self_test_row_map_smoke_aggregate_only() -> None:
    """C4.2 row-map smoke aggregation is aggregate-only and
    sentinel-clean even with private sentinel values in rows.

    Uses no network: builds synthetic rows with sentinel private values
    (e.g. ``SECRET_REPO_SENTINEL``) and runs the in-memory aggregator.
    Asserts NONE of the sentinel strings appear in the report JSON, the
    forbidden scan passes, and the public artifact carries only counts /
    booleans / fixed failure categories.
    """
    # Sentinel private values that must NEVER appear in the public artifact.
    secret_repo = "SECRET_REPO_SENTINEL"
    secret_commit = "SECRET_COMMIT_SENTINEL"
    secret_patch = "SECRET_PATCH_SENTINEL"
    secret_problem = "SECRET_PROBLEM_STATEMENT_SENTINEL"
    secret_instance = "SECRET_INSTANCE_ID_SENTINEL"
    secret_gold = "SECRET_GOLD_CONTEXT_SENTINEL"
    secret_f2p = "SECRET_F2P_SENTINEL"

    synthetic_rows: list[dict[str, Any]] = []
    for i in range(3):
        row: dict[str, Any] = {
            "instance_id": secret_instance + str(i),
            "original_inst_id": secret_instance + "_orig_" + str(i),
            "repo": secret_repo + str(i),
            "repo_url": "https://example.invalid/" + secret_repo + str(i),
            "language": "python",
            "base_commit": secret_commit + str(i),
            "gold_context": secret_gold + str(i),
            "patch": secret_patch + str(i),
            "test_patch": secret_patch + "_test_" + str(i),
            "problem_statement": secret_problem + str(i),
            "f2p": [secret_f2p + str(i)],
            "p2p": [secret_f2p + "_p2p_" + str(i)],
            "source": "synthetic_self_test",
        }
        synthetic_rows.append(row)

    summary = _build_row_map_summary(
        synthetic_rows,
        dataset_id=CONTEXTBENCH_DATASET_ID,
        config="contextbench_verified",
        split="train",
        row_limit_requested=3,
        observed_field_names=list(CONTEXTBENCH_FIELD_NAMES),
        truncated_rows=False,
    )
    # All 3 rows should map successfully.
    assert summary["rows_seen"] == 3, summary["rows_seen"]
    assert summary["rows_mapped"] == 3, summary["rows_mapped"]
    assert summary["rows_failed"] == 0, summary["rows_failed"]
    assert summary["status"] == "pass", summary["status"]
    assert summary["private_label_isolation_verified"] is True
    assert summary["adapter_assertions_passed"] is True
    assert summary["raw_rows_persisted"] is False
    assert summary["row_level_values_emitted"] is False
    assert summary["row_level_hashes_emitted"] is False
    assert summary["raw_response_stored"] is False

    # Field presence counts: instance_id present in all 3.
    assert summary["field_presence_counts"]["instance_id"] == 3
    assert summary["field_presence_counts"]["repo"] == 3
    assert summary["field_presence_counts"]["patch"] == 3
    # Public task presence: all 3 have repo locator + private label payload.
    assert summary["public_task_presence_counts"]["has_repo_locator"] == 3
    assert summary["public_task_presence_counts"]["has_private_label_payload"] == 3
    assert summary["public_task_presence_counts"]["has_f2p"] == 3
    assert summary["public_task_presence_counts"]["has_p2p"] == 3
    # Private field presence: all private categories present in all 3.
    assert summary["private_field_presence_counts"]["repo"] == 3
    assert summary["private_field_presence_counts"]["base_commit"] == 3
    assert summary["private_field_presence_counts"]["gold_context"] == 3

    # CRITICAL: NONE of the sentinel strings may appear in the report JSON.
    summary_json = json.dumps(summary, sort_keys=True)
    for sentinel in (
        secret_repo,
        secret_commit,
        secret_patch,
        secret_problem,
        secret_instance,
        secret_gold,
        secret_f2p,
    ):
        assert sentinel not in summary_json, (
            f"sentinel {sentinel!r} leaked into row-map summary JSON"
        )
        # Also check the per-row indexed variants.
        for i in range(3):
            assert (sentinel + str(i)) not in summary_json, (
                f"sentinel {sentinel!r}{i} leaked into row-map summary JSON"
            )

    # Forbidden scan on the summary must pass (it's aggregate-only).
    scan = _forbidden_scan_summary(summary)
    assert scan["status"] == "pass", scan
    assert scan["violations_count"] == 0, scan

    # Injected leak with "12-34" (a raw line range) must still be rejected
    # by the forbidden scanner.
    leaked = dict(summary)
    leaked["injected_range"] = "12-34"
    leaked_scan = _forbidden_scan_summary(leaked)
    assert leaked_scan["status"] == "fail", leaked_scan

    # No-claim flags: build a full report skeleton and verify all false.
    report = {
        "schema_version": ROW_MAP_SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "claim_level": ROW_MAP_CLAIM_LEVEL,
        "aggregate_only_public_artifact": True,
        "not_evidence": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "runtime_clean_general_algorithm_claimed": False,
        "downstream_agent_value_proven": False,
        "ood_temporal_supported": False,
        "quiver_systems_supported": False,
        **summary,
    }
    for flag in NO_CLAIM_FLAGS:
        assert report[flag] is False, (flag, report[flag])
    # Forbidden scan on the full report.
    full_scan = _forbidden_scan_summary(report)
    assert full_scan["status"] == "pass", full_scan
    print("self-test row-map smoke aggregate-only: ok")


def _self_test_row_map_smoke_no_rows_unavailable() -> None:
    """When no rows are returned, the row-map smoke status is
    ``unavailable`` with the fixed failure category
    ``no_rows_returned`` counted, and the report stays aggregate-only."""
    summary = _build_row_map_summary(
        [],
        dataset_id=CONTEXTBENCH_DATASET_ID,
        config="contextbench_verified",
        split="train",
        row_limit_requested=3,
        observed_field_names=list(CONTEXTBENCH_FIELD_NAMES),
        truncated_rows=False,
    )
    assert summary["rows_seen"] == 0
    assert summary["rows_mapped"] == 0
    assert summary["status"] == "unavailable", summary["status"]
    assert summary["failure_category_counts"]["no_rows_returned"] == 1
    scan = _forbidden_scan_summary(summary)
    assert scan["status"] == "pass", scan
    print("self-test row-map smoke no-rows unavailable: ok")


def _self_test_row_map_smoke_isolation_failure_fail_closed() -> None:
    """A public/private isolation regression must not report PASS.

    The synthetic bad adapter returns a public task that exposes a private
    ``repo`` attribute. The row-map summary must fail closed with
    ``fail_schema_contract`` rather than producing ``status=pass`` with false
    safety booleans.
    """

    class BadPublicTask:
        def __init__(self) -> None:
            self.repo = "SECRET_REPO_SENTINEL"
            self.has_original_inst_id = True
            self.has_f2p = True
            self.has_p2p = True
            self.has_repo_locator = True
            self.has_private_label_payload = True

    original_adapter = globals()["adapt_contextbench_row"]

    def bad_adapter(
        row: dict[str, Any],
    ) -> tuple[Any, Any]:
        _ = row
        return BadPublicTask(), object()

    try:
        globals()["adapt_contextbench_row"] = bad_adapter
        summary = _build_row_map_summary(
            [_build_synthetic_contextbench_row()],
            dataset_id=CONTEXTBENCH_DATASET_ID,
            config="contextbench_verified",
            split="train",
            row_limit_requested=1,
            observed_field_names=list(CONTEXTBENCH_FIELD_NAMES),
            truncated_rows=False,
        )
    finally:
        globals()["adapt_contextbench_row"] = original_adapter

    assert summary["status"] == "fail_schema_contract", summary
    assert summary["rows_seen"] == 1, summary
    assert summary["rows_mapped"] == 0, summary
    assert summary["rows_failed"] == 1, summary
    assert summary["private_label_isolation_verified"] is False, summary
    assert summary["adapter_assertions_passed"] is False, summary
    assert summary["failure_category_counts"]["private_field_leak"] >= 1, summary
    # The sentinel is present only in the bad in-memory public object and must
    # not be emitted to the aggregate summary.
    assert "SECRET_REPO_SENTINEL" not in json.dumps(summary, sort_keys=True)
    scan = _forbidden_scan_summary(summary)
    assert scan["status"] == "pass", scan
    print("self-test row-map smoke isolation failure fail-closed: ok")


def run_self_tests() -> dict[str, Any]:
    """Run all C4 self-tests. Returns a summary (no row-level data)."""
    _self_test_contextbench_adapter_separation()
    _self_test_swe_explore_adapter_separation()
    _self_test_line_range_normalization()
    _self_test_forbidden_scan_rejects_injection()
    _self_test_no_claim_flags_exactly_false()
    _self_test_spec_hash_deterministic()
    _self_test_aggregate_only_report()
    _self_test_forbidden_scan_injection_blocked_at_generation()
    _self_test_schema_smoke_report_shape()
    _self_test_row_map_smoke_aggregate_only()
    _self_test_row_map_smoke_no_rows_unavailable()
    _self_test_row_map_smoke_isolation_failure_fail_closed()
    return {
        "schema_version": SCHEMA_VERSION,
        "claim_level": CLAIM_LEVEL,
        "self_test_passed": True,
        "self_test_checks": {
            "contextbench_adapter_separation": True,
            "swe_explore_adapter_separation": True,
            "line_range_normalization": True,
            "forbidden_scan_rejects_injection": True,
            "no_claim_flags_exactly_false": True,
            "spec_hash_deterministic": True,
            "aggregate_only_report": True,
            "forbidden_scan_injection_blocked_at_generation": True,
            "schema_smoke_report_shape": True,
            "row_map_smoke_aggregate_only": True,
            "row_map_smoke_no_rows_unavailable": True,
            "row_map_smoke_isolation_failure_fail_closed": True,
        },
        "spec_hash": compute_spec_hash(),
        "not_evidence": True,
        "candidate_not_fact": True,
        "aggregate_only_public_artifact": True,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="C4.1/C4.2 external benchmark adapters (schema + row-mapping readiness).",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the C4 self-test (synthetic fixtures; no network).",
    )
    parser.add_argument(
        "--benchmark",
        choices=("contextbench", "swe_explore", "all"),
        default="all",
        help="benchmark to operate on (default: all). Used by --schema-smoke.",
    )
    parser.add_argument(
        "--schema-smoke",
        action="store_true",
        help=(
            "run a bounded HF datasets-server schema smoke for the "
            "selected benchmark(s) and write an aggregate-only smoke "
            "report to --out. Requires explicit --out."
        ),
    )
    parser.add_argument(
        "--row-map-smoke",
        action="store_true",
        help=(
            "run the bounded C4.2 ContextBench verified subset row-mapping "
            "smoke: read real HF datasets-server /first-rows preview rows, "
            "adapt each in function scope, and emit an aggregate-only "
            "report. Real rows are never persisted."
        ),
    )
    parser.add_argument(
        "--config",
        default="contextbench_verified",
        help=(
            "config for --row-map-smoke (default: contextbench_verified; "
            "only contextbench_verified is supported for row-map smoke)."
        ),
    )
    parser.add_argument(
        "--split",
        default="train",
        help="split for --row-map-smoke (default: train).",
    )
    parser.add_argument(
        "--row-limit",
        type=int,
        default=ROW_LIMIT_DEFAULT,
        help=(
            f"max preview rows to row-map during --row-map-smoke "
            f"(default {ROW_LIMIT_DEFAULT}, hard cap "
            f"{ROW_LIMIT_HARD_CAP})."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=LIMIT_DEFAULT,
        help=(
            f"max (config, split) pairs to probe with /first-rows during "
            f"schema smoke (default {LIMIT_DEFAULT}, hard cap "
            f"{LIMIT_HARD_CAP})."
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=(
            "path to write the report (default: the canonical "
            "artifacts/c4_external_benchmark_adapters/"
            "c4_external_benchmark_adapter_report.json). For --row-map-smoke "
            "the default is artifacts/c4_external_benchmark_adapters/"
            "c4_contextbench_verified_row_mapping_report.json."
        ),
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)

    # Clamp --limit to hard cap.
    if args.limit < 1:
        parser.error(f"--limit must be >= 1; got {args.limit}")
    if args.limit > LIMIT_HARD_CAP:
        # Clamp, do not error (graceful).
        args.limit = LIMIT_HARD_CAP

    # Clamp --row-limit to hard cap.
    if args.row_limit < 1:
        parser.error(f"--row-limit must be >= 1; got {args.row_limit}")
    if args.row_limit > ROW_LIMIT_HARD_CAP:
        # Clamp, do not error (graceful).
        args.row_limit = ROW_LIMIT_HARD_CAP

    # Mutual exclusion: only one mode at a time.
    modes_active = sum(
        1 for m in (args.self_test, args.schema_smoke, args.row_map_smoke) if m
    )
    if modes_active > 1:
        parser.error(
            "--self-test, --schema-smoke, and --row-map-smoke are mutually "
            "exclusive"
        )

    # --schema-smoke requires explicit --out to avoid overwriting the
    # canonical aggregate report.
    if args.schema_smoke and args.out == DEFAULT_OUT:
        parser.error(
            "--schema-smoke requires an explicit --out to avoid "
            "overwriting the canonical aggregate report"
        )

    # --row-map-smoke: only contextbench_verified is supported. If --out
    # is still the C4.1 default, switch to the C4.2 default artifact path.
    if args.row_map_smoke:
        if args.config not in ROW_MAP_ALLOWED_CONFIGS:
            parser.error(
                f"--row-map-smoke only supports config(s) "
                f"{sorted(ROW_MAP_ALLOWED_CONFIGS)}; got {args.config!r}"
            )
        if args.out == DEFAULT_OUT:
            args.out = ROW_MAP_DEFAULT_OUT
        if args.benchmark not in ("contextbench", "all"):
            parser.error(
                "--row-map-smoke only supports --benchmark contextbench "
                "(or all); got " + repr(args.benchmark)
            )
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.self_test:
        result = run_self_tests()
        print(json.dumps(result, indent=2, sort_keys=True))
        print(
            "C4 external benchmark adapters self-test: PASS",
            file=sys.stderr,
        )
        return 0

    if args.schema_smoke:
        report = build_schema_smoke_report(
            benchmark=args.benchmark,
            limit=args.limit,
            self_test=False,
        )
        _write_json(args.out, report)
        summary = {
            "schema_version": report["schema_version"],
            "claim_level": report["claim_level"],
            "schema_smoke": report["schema_smoke"],
            "benchmark_selected": report["benchmark_selected"],
            "limit_applied": report["limit_applied"],
            "aggregate_only_public_artifact": report[
                "aggregate_only_public_artifact"
            ],
            "not_evidence": report["not_evidence"],
            "forbidden_scan": report["forbidden_scan"],
            "new_network_calls": report["new_network_calls"],
            "out": str(args.out),
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    if args.row_map_smoke:
        report = build_row_map_smoke_report(
            config=args.config,
            split=args.split,
            row_limit=args.row_limit,
            self_test=False,
        )
        _write_json(args.out, report)
        summary = {
            "schema_version": report["schema_version"],
            "claim_level": report["claim_level"],
            "row_map_smoke": report["row_map_smoke"],
            "benchmark_selected": report["benchmark_selected"],
            "config_selected": report["config_selected"],
            "split_selected": report["split_selected"],
            "row_limit_applied": report["row_limit_applied"],
            "rows_seen": report["rows_seen"],
            "rows_mapped": report["rows_mapped"],
            "rows_failed": report["rows_failed"],
            "status": report["status"],
            "aggregate_only_public_artifact": report[
                "aggregate_only_public_artifact"
            ],
            "not_evidence": report["not_evidence"],
            "candidate_not_fact": report["candidate_not_fact"],
            "private_label_isolation_verified": report[
                "private_label_isolation_verified"
            ],
            "adapter_assertions_passed": report["adapter_assertions_passed"],
            "forbidden_scan": report["forbidden_scan"],
            "new_network_calls": report["new_network_calls"],
            "out": str(args.out),
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        if (
            report["status"] != "pass"
            or report["forbidden_scan"]["status"] != "pass"
            or not report["private_label_isolation_verified"]
            or not report["adapter_assertions_passed"]
        ):
            return 1
        return 0

    # Default: canonical aggregate report (no network).
    report = build_canonical_report(self_test=False)
    _write_json(args.out, report)
    summary = {
        "schema_version": report["schema_version"],
        "claim_level": report["claim_level"],
        "aggregate_only_public_artifact": report[
            "aggregate_only_public_artifact"
        ],
        "not_evidence": report["not_evidence"],
        "candidate_not_fact": report["candidate_not_fact"],
        "spec_hash": report["spec_hash"],
        "forbidden_scan": report["forbidden_scan"],
        "new_provider_calls": report["new_provider_calls"],
        "new_network_calls": report["new_network_calls"],
        "benchmarks": {
            bench: {
                "discovery_status": report["benchmarks"][bench][
                    "discovery_status"
                ],
                "schema_smoke_status": report["benchmarks"][bench][
                    "schema_smoke_status"
                ],
                "adapter_self_test_status": report["benchmarks"][bench][
                    "adapter_self_test_status"
                ],
                "public_release_status": report["benchmarks"][bench][
                    "public_release_status"
                ],
                "license_status": report["benchmarks"][bench][
                    "license_status"
                ],
                "row_level_redistribution_allowed": report["benchmarks"][
                    bench
                ]["row_level_redistribution_allowed"],
                "derived_label_publication_allowed": report["benchmarks"][
                    bench
                ]["derived_label_publication_allowed"],
            }
            for bench in ("contextbench", "swe_explore")
        },
        "out": str(args.out),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
