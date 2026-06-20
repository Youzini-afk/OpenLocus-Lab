#!/usr/bin/env python3
"""C4.4 CORE-Bench Source Readiness / No-Go (bounded).

This module implements C4.4 source readiness for the CORE-Bench benchmark
(arXiv:2606.11864v1 — ``CORE-Bench: A Comprehensive Benchmark for Code
Retrieval in the Era of Agentic Coding``). It is **not** an adapter or
schema-readiness module: the actual HF dataset files/schema are
unavailable, so this module only emits a **source-readiness no-go**
report.

Wrong-target disambiguation (binding): the target is the agentic-coding
CORE-Bench, NOT the older ``siegelz/core-bench`` scientific reproduction
benchmark. ``not_siegelz_core_bench=true`` and
``wrong_target_disambiguated=true``.

Public-artifact contract (binding):

* aggregate-only public output;
* NEVER write raw dataset rows, gold labels, qrels, corpus files, query
  files, row-level paths / spans / line ranges, snippets, problem
  statements, patches / tests, prompts / responses, provider payloads,
  content_sha, raw HF payloads, or response bodies;
* no row-level hashes (hashes are row-level derived data);
* no-claim flags all false: ``promotion_ready``,
  ``default_should_change``, ``evidencecore_semantics_changed``,
  ``runtime_clean_general_algorithm_claimed``,
  ``downstream_agent_value_proven``, ``ood_temporal_supported``,
  ``quiver_systems_supported``;
* ``adapter_support_claimed=false``,
  ``schema_readiness_claimed=false``, ``schema_smoke_passed=false``.

Claim boundary: this module emits ``claim_level =
source_readiness_no_go_only`` evidence. It does NOT claim adapter support,
schema readiness, benchmark result, downstream agent value, OOD temporal
support, or QuIVer systems support. The status is ``blocked_*`` (not
``pass`` / ``support``). Synthetic self-test fixtures confer NO empirical
support.

Run::

    python3 -m py_compile eval/c4_core_bench_source_readiness.py
    python3 eval/c4_core_bench_source_readiness.py --self-test
    python3 eval/c4_core_bench_source_readiness.py \\
        --out artifacts/c4_external_benchmark_adapters/\\
c4_core_bench_source_readiness_report.json
    python3 eval/c4_core_bench_source_readiness.py --offline \\
        --out /tmp/c4_core_bench_offline.json
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

SCHEMA_VERSION = "c4_core_bench_source_readiness.v1"
GENERATED_BY = "eval/c4_core_bench_source_readiness.py"
CLAIM_LEVEL = "source_readiness_no_go_only"
BENCHMARK = "core_bench"

DEFAULT_OUT = Path(
    "artifacts/c4_external_benchmark_adapters/"
    "c4_core_bench_source_readiness_report.json"
)

# Bounded timeout for every HTTP probe.
PROBE_TIMEOUT_SECONDS = 10

# The exact paper title (verbatim from arXiv:2606.11864v1).
TARGET_TITLE = (
    "CORE-Bench: A Comprehensive Benchmark for Code Retrieval in the "
    "Era of Agentic Coding"
)
ARXIV_ID = "2606.11864v1"
ARXIV_ABS_URL = "https://arxiv.org/abs/2606.11864"
ARXIV_HTML_URL = "https://arxiv.org/html/2606.11864v1"
ARXIV_PDF_URL = "https://arxiv.org/pdf/2606.11864"
DOI_URL = "https://doi.org/10.48550/arXiv.2606.11864"

# HF placeholder dataset repo (source-level public URL, not row-level).
HF_DATASET_ID = "zhangfw123/CORE-Bench"
HF_DATASET_URL = "https://huggingface.co/datasets/zhangfw123/CORE-Bench"
HF_API_DATASETS_URL = (
    "https://huggingface.co/api/datasets/zhangfw123/CORE-Bench"
)
HF_API_TREE_URL = (
    "https://huggingface.co/api/datasets/zhangfw123/CORE-Bench/tree/main"
)
_HF_DATASETS_SERVER = "https://datasets-server.huggingface.co"
DS_SERVER_IS_VALID_URL = (
    f"{_HF_DATASETS_SERVER}/is-valid?dataset="
    f"{urllib.parse.quote(HF_DATASET_ID, safe='/')}"
)
DS_SERVER_SPLITS_URL = (
    f"{_HF_DATASETS_SERVER}/splits?dataset="
    f"{urllib.parse.quote(HF_DATASET_ID, safe='/')}"
)
DS_SERVER_FIRST_ROWS_URL = (
    f"{_HF_DATASETS_SERVER}/first-rows?dataset="
    f"{urllib.parse.quote(HF_DATASET_ID, safe='/')}"
    "&config=default&split=train"
)

# The WRONG target (older scientific-reproduction benchmark). Used for
# disambiguation only; never probed.
WRONG_TARGET_DATASET_ID = "siegelz/core-bench"
WRONG_TARGET_NOTE = (
    "older scientific-reproduction benchmark; not the agentic-coding "
    "CORE-Bench targeted by C4.4"
)

# Source-level placeholder repo file names observed at the HF repo
# (NOT row-level paths; allowed only under placeholder_repo_files_observed).
PLACEHOLDER_REPO_FILES: tuple[str, ...] = (
    ".gitattributes",
    "README.md",
)

# Paper aggregate facts from arXiv Table 1 (paper-level, not row-level).
PAPER_AGGREGATE_FACTS: dict[str, Any] = {
    "paper_aggregate_only": True,
    "levels": (
        {
            "level": "code_understanding",
            "queries": 172961,
        },
        {
            "level": "issue_to_edit_localization",
            "queries": 5061,
            "repos": 632,
            "qrels": 52712,
        },
        {
            "level": "broader_context_retrieval",
            "queries": 2580,
            "repos": 97,
            "qrels": 106479,
        },
    ),
    "total_queries": 180602,
    "broader_context_labels": 106479,
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

# ---------------------------------------------------------------------------
# Forbidden-output scanner (source-readiness-specific)
# ---------------------------------------------------------------------------

# Sensitive KEY names that must NEVER appear as dict keys anywhere in a
# public JSON output. These are row-level data field names.
FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset(
    {
        "instance_id",
        "repo",
        "repo_path",
        "repo_dir",
        "repo_url",
        "base_commit",
        "gold_context",
        "patch",
        "test_patch",
        "problem_statement",
        "f2p",
        "p2p",
        "source",
        "ground_truth",
        "read_step_info",
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
        "api_key",
        "api_token",
        "api_secret",
        "base_url",
        "provider_key",
        "authorization",
    }
)

# Container key names whose CHILD KEYS are schema-only field-name
# observations used as count buckets.
SCHEMA_KEY_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "placeholder_repo_files_observed",
    }
)

# Container key names under which sensitive field-name strings MAY appear
# as values (these are schema-only observations).
SCHEMA_ONLY_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "placeholder_repo_files_observed",
    }
)

# Known-safe provenance value paths (allowlisted for hex_digest/path_like
# value checks only).
SAFE_VALUE_KEY_NAMES: frozenset[str] = frozenset(
    {
        "schema_version",
        "generated_by",
        "claim_level",
        "dataset_id",
        "target_title",
        "arxiv_id",
        "arxiv_abs_url",
        "arxiv_html_url",
        "arxiv_pdf_url",
        "doi_url",
        "hf_dataset_url",
        "hf_api_datasets_url",
        "hf_api_tree_url",
        "ds_server_is_valid_url",
        "ds_server_splits_url",
        "ds_server_first_rows_url",
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

# Official source-level URLs that ARE allowed as values (verified public
# arXiv / HF / DOI URLs, not row-level).
ALLOWED_SOURCE_URLS: frozenset[str] = frozenset(
    {
        ARXIV_ABS_URL,
        ARXIV_HTML_URL,
        ARXIV_PDF_URL,
        DOI_URL,
        HF_DATASET_URL,
        HF_API_DATASETS_URL,
        HF_API_TREE_URL,
        DS_SERVER_IS_VALID_URL,
        DS_SERVER_SPLITS_URL,
        DS_SERVER_FIRST_ROWS_URL,
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

    Allows official source-level URLs (arXiv / HF placeholder / DOI) but
    forbids row-level URLs, paths, spans, snippets, raw payloads.
    """
    violations: list[dict[str, Any]] = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            sub_path = f"{path}.{key_str}"
            is_schema_container = key_str in SCHEMA_ONLY_CONTAINER_KEYS
            # Forbid sensitive key names anywhere as dict keys, EXCEPT
            # when the parent is a schema-key container.
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
        allowed_url = _is_allowed_source_url(obj)
        # In schema-only containers, short field-name strings are allowed.
        if in_schema_container and len(obj) <= 64:
            if _RE_URL_VALUE.search(obj) and not allowed_url:
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
            elif "\n" in obj:
                violations.append(
                    {"category": "multiline_value", "path": path}
                )
        else:
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
                "User-Agent": "OpenLocus-C4-core-bench-source-readiness/0.1 (bounded; stdlib)",
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


# ---------------------------------------------------------------------------
# Source probes (aggregate-only; no raw response bodies)
# ---------------------------------------------------------------------------


def _probe_hf_dataset_api() -> dict[str, Any]:
    """Probe the HF dataset API for aggregate metadata.

    Returns only aggregate metadata: dataset_repo_public, gated, private,
    license tag/card, sibling/file count, and the limited set of
    placeholder repo file names (source-level, not row-level). No raw
    response body is stored.
    """
    raw, status, http_code = _http_get_json(HF_API_DATASETS_URL)
    probe: dict[str, Any] = {
        "endpoint": "hf_api_datasets",
        "status": status,
        "http_code": (http_code if isinstance(http_code, int) else None),
        "dataset_repo_public": None,
        "gated": None,
        "private": None,
        "license_tag": None,
        "card_license": None,
        "sibling_count": None,
        "placeholder_repo_files_observed": [],
    }
    if status != "pass" or not isinstance(raw, dict):
        return probe
    probe["dataset_repo_public"] = bool(raw.get("private") is False)
    probe["gated"] = bool(raw.get("gated", False))
    probe["private"] = bool(raw.get("private", False))
    # License tag (card-level field).
    card_data = raw.get("cardData")
    if isinstance(card_data, dict):
        lic = card_data.get("license")
        if isinstance(lic, str):
            probe["license_tag"] = lic
        elif isinstance(lic, list) and lic:
            probe["license_tag"] = lic[0] if isinstance(lic[0], str) else None
        probe["card_license"] = probe["license_tag"]
    # Siblings: only count, plus the known placeholder file names.
    siblings = raw.get("siblings")
    if isinstance(siblings, list):
        probe["sibling_count"] = len(siblings)
        observed_files: list[str] = []
        for s in siblings:
            if isinstance(s, dict) and isinstance(s.get("rfilename"), str):
                rfilename = s["rfilename"]
                if rfilename in PLACEHOLDER_REPO_FILES:
                    observed_files.append(rfilename)
        probe["placeholder_repo_files_observed"] = sorted(set(observed_files))
    return probe


def _probe_hf_tree_api() -> dict[str, Any]:
    """Probe the HF tree API for the repo file listing.

    Returns only the file count and known placeholder file names. No raw
    response body is stored.
    """
    raw, status, http_code = _http_get_json(HF_API_TREE_URL)
    probe: dict[str, Any] = {
        "endpoint": "hf_api_tree",
        "status": status,
        "http_code": (http_code if isinstance(http_code, int) else None),
        "tree_file_count": None,
        "placeholder_repo_files_observed": [],
    }
    if status != "pass" or not isinstance(raw, list):
        return probe
    probe["tree_file_count"] = len(raw)
    observed_files: list[str] = []
    for entry in raw:
        if isinstance(entry, dict) and isinstance(entry.get("path"), str):
            path_str = entry["path"]
            if path_str in PLACEHOLDER_REPO_FILES:
                observed_files.append(path_str)
    probe["placeholder_repo_files_observed"] = sorted(set(observed_files))
    return probe


def _probe_ds_server(
    endpoint_name: str, url: str
) -> dict[str, Any]:
    """Probe a datasets-server endpoint and return only aggregate status."""
    raw, status, http_code = _http_get_json(url)
    probe: dict[str, Any] = {
        "endpoint": endpoint_name,
        "status": status,
        "http_code": (http_code if isinstance(http_code, int) else None),
        "splits_available": None,
        "first_rows_available": None,
        "is_valid": None,
        "configs_observed_count": None,
    }
    if status != "pass" or raw is None:
        return probe
    if endpoint_name == "ds_server_is_valid" and isinstance(raw, dict):
        probe["is_valid"] = bool(raw.get("valid", False))
    elif endpoint_name == "ds_server_splits" and isinstance(raw, dict):
        splits = raw.get("splits")
        if isinstance(splits, list):
            probe["splits_available"] = len(splits) > 0
            probe["configs_observed_count"] = len(
                {s.get("config") for s in splits if isinstance(s, dict)}
            )
    elif endpoint_name == "ds_server_first_rows" and isinstance(raw, dict):
        features = raw.get("features")
        if isinstance(features, list):
            probe["first_rows_available"] = len(features) > 0
    return probe


def run_source_probes(*, offline: bool = False) -> dict[str, Any]:
    """Run all bounded source probes. Returns aggregate-only status.

    In ``--offline`` mode, no network calls are made; all probes report
    ``status=offline`` and the report is built from confirmed static
    findings only.
    """
    if offline:
        return {
            "offline_mode": True,
            "network_calls": 0,
            "probes": [],
        }
    probes: list[dict[str, Any]] = []
    probes.append(_probe_hf_dataset_api())
    probes.append(_probe_hf_tree_api())
    probes.append(_probe_ds_server("ds_server_is_valid", DS_SERVER_IS_VALID_URL))
    probes.append(_probe_ds_server("ds_server_splits", DS_SERVER_SPLITS_URL))
    probes.append(_probe_ds_server("ds_server_first_rows", DS_SERVER_FIRST_ROWS_URL))
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
    """Build the C4.4 source-readiness no-go report (aggregate-only)."""
    # Determine whether the placeholder state was confirmed.
    probes = probe_results.get("probes", [])
    hf_api_probe = next(
        (p for p in probes if p.get("endpoint") == "hf_api_datasets"), None
    )
    hf_tree_probe = next(
        (p for p in probes if p.get("endpoint") == "hf_api_tree"), None
    )
    ds_is_valid_probe = next(
        (p for p in probes if p.get("endpoint") == "ds_server_is_valid"), None
    )
    ds_splits_probe = next(
        (p for p in probes if p.get("endpoint") == "ds_server_splits"), None
    )
    ds_first_rows_probe = next(
        (p for p in probes if p.get("endpoint") == "ds_server_first_rows"), None
    )

    # Aggregate placeholder confirmation.
    placeholder_files_observed: list[str] = []
    if hf_api_probe:
        placeholder_files_observed.extend(
            hf_api_probe.get("placeholder_repo_files_observed", [])
        )
    if hf_tree_probe:
        placeholder_files_observed.extend(
            hf_tree_probe.get("placeholder_repo_files_observed", [])
        )
    placeholder_files_observed = sorted(set(placeholder_files_observed))

    dataset_repo_public = (
        hf_api_probe.get("dataset_repo_public") if hf_api_probe else None
    )
    license_tag = hf_api_probe.get("license_tag") if hf_api_probe else None
    sibling_count = (
        hf_api_probe.get("sibling_count") if hf_api_probe else None
    )

    # Determine the source-confirmation status.
    if probe_results.get("offline_mode"):
        source_confirmation_status = "offline_static_findings_only"
    elif (
        hf_api_probe
        and hf_api_probe.get("status") == "pass"
        and dataset_repo_public
        and (
            sibling_count is not None
            and sibling_count <= len(PLACEHOLDER_REPO_FILES) + 2
        )
        and (
            ds_first_rows_probe is None
            or ds_first_rows_probe.get("first_rows_available") is not True
        )
    ):
        source_confirmation_status = "paper_and_placeholder_confirmed_dataset_unavailable"
    elif hf_api_probe and hf_api_probe.get("status") == "pass":
        source_confirmation_status = "paper_and_placeholder_confirmed_dataset_unavailable"
    else:
        source_confirmation_status = "paper_confirmed_dataset_endpoint_unreachable"

    # Determine the overall status: always a no-go (blocked_*).
    if source_confirmation_status == "paper_and_placeholder_confirmed_dataset_unavailable":
        status = "blocked_dataset_placeholder_empty"
    elif source_confirmation_status == "paper_confirmed_dataset_endpoint_unreachable":
        status = "blocked_schema_unavailable"
    else:
        # Offline mode: still a no-go based on static findings.
        status = "blocked_schema_unavailable"

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "benchmark": BENCHMARK,
        "target_title": TARGET_TITLE,
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
        # Source-readiness no-go flags.
        "adapter_support_claimed": False,
        "schema_readiness_claimed": False,
        "schema_smoke_attempted": True,
        "schema_smoke_passed": False,
        "row_map_smoke_attempted": False,
        "row_map_smoke_passed": False,
        # Wrong-target disambiguation.
        "wrong_target_disambiguated": True,
        "not_siegelz_core_bench": True,
        "wrong_target_dataset_id": WRONG_TARGET_DATASET_ID,
        "wrong_target_note": WRONG_TARGET_NOTE,
        # Status.
        "status": status,
        "source_confirmation_status": source_confirmation_status,
        # Official source URLs (source-level public URLs only).
        "arxiv_id": ARXIV_ID,
        "arxiv_abs_url": ARXIV_ABS_URL,
        "arxiv_html_url": ARXIV_HTML_URL,
        "arxiv_pdf_url": ARXIV_PDF_URL,
        "doi_url": DOI_URL,
        "dataset_id": HF_DATASET_ID,
        "hf_dataset_url": HF_DATASET_URL,
        "hf_api_datasets_url": HF_API_DATASETS_URL,
        "hf_api_tree_url": HF_API_TREE_URL,
        "ds_server_is_valid_url": DS_SERVER_IS_VALID_URL,
        "ds_server_splits_url": DS_SERVER_SPLITS_URL,
        "ds_server_first_rows_url": DS_SERVER_FIRST_ROWS_URL,
        # Source probes.
        "source_probes": probe_results,
        # Aggregate placeholder observations.
        "dataset_repo_public": dataset_repo_public,
        "gated": (
            hf_api_probe.get("gated") if hf_api_probe else None
        ),
        "private": (
            hf_api_probe.get("private") if hf_api_probe else None
        ),
        "license_tag": license_tag,
        "sibling_count": sibling_count,
        "placeholder_repo_files_observed": placeholder_files_observed,
        "ds_server_is_valid": (
            ds_is_valid_probe.get("is_valid") if ds_is_valid_probe else None
        ),
        "ds_server_splits_available": (
            ds_splits_probe.get("splits_available")
            if ds_splits_probe
            else None
        ),
        "ds_server_first_rows_available": (
            ds_first_rows_probe.get("first_rows_available")
            if ds_first_rows_probe
            else None
        ),
        # Paper aggregate facts (paper-level, not row-level).
        "paper_aggregate_facts": dict(PAPER_AGGREGATE_FACTS),
        # Follow-up requirements (what would be needed to unblock).
        "follow_up_requirements": [
            "actual_dataset_files_published",
            "schema_and_splits_exposed",
            "qrels_corpus_query_files_published",
            "license_and_redistribution_statement",
            "official_github_or_project_page_confirmation",
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
    """Build the C4.4 source-readiness no-go report."""
    probe_results = run_source_probes(offline=offline)
    report = _build_report(probe_results=probe_results, self_test=self_test)
    # Re-run forbidden scan after final assembly.
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        raise ValueError(
            "c4_core_bench_source_readiness report would leak "
            f"forbidden content: {scan['categories']}"
        )
    return report


# ---------------------------------------------------------------------------
# Self-test (no network)
# ---------------------------------------------------------------------------


def _self_test_wrong_target_disambiguation() -> None:
    """Wrong-target disambiguation rejects siegelz/core-bench."""
    assert WRONG_TARGET_DATASET_ID == "siegelz/core-bench"
    assert HF_DATASET_ID == "zhangfw123/CORE-Bench"
    assert HF_DATASET_ID != WRONG_TARGET_DATASET_ID
    assert "siegelz" in WRONG_TARGET_DATASET_ID
    assert "siegelz" not in HF_DATASET_ID
    # The target title must be the agentic-coding CORE-Bench.
    assert "Agentic Coding" in TARGET_TITLE
    assert "Comprehensive Benchmark" in TARGET_TITLE
    print("self-test wrong-target disambiguation: ok")


def _self_test_offline_no_go_report() -> None:
    """Offline report builds a no-go with status not pass/support."""
    report = build_source_readiness_report(offline=True, self_test=True)
    assert report["schema_version"] == SCHEMA_VERSION
    assert report["benchmark"] == BENCHMARK
    assert report["target_title"] == TARGET_TITLE
    assert report["claim_level"] == CLAIM_LEVEL
    # Status must be a blocked_* (not pass/support).
    assert report["status"].startswith("blocked_"), report["status"]
    assert report["status"] not in ("pass", "support")
    assert report["source_confirmation_status"] == "offline_static_findings_only"
    # No-go flags.
    assert report["adapter_support_claimed"] is False
    assert report["schema_readiness_claimed"] is False
    assert report["schema_smoke_attempted"] is True
    assert report["schema_smoke_passed"] is False
    assert report["row_map_smoke_attempted"] is False
    assert report["row_map_smoke_passed"] is False
    # Wrong-target disambiguation.
    assert report["wrong_target_disambiguated"] is True
    assert report["not_siegelz_core_bench"] is True
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
    # Paper aggregate facts.
    assert report["paper_aggregate_facts"]["paper_aggregate_only"] is True
    assert report["paper_aggregate_facts"]["total_queries"] == 180602
    assert report["paper_aggregate_facts"]["broader_context_labels"] == 106479
    levels = report["paper_aggregate_facts"]["levels"]
    assert len(levels) == 3
    assert levels[0]["queries"] == 172961
    assert levels[1]["queries"] == 5061
    assert levels[2]["queries"] == 2580
    # Forbidden scan must pass.
    assert report["forbidden_scan"]["status"] == "pass", report["forbidden_scan"]
    assert report["forbidden_scan"]["violations_count"] == 0, report["forbidden_scan"]
    # Offline mode => 0 network calls.
    assert report["new_network_calls"] == 0
    assert report["source_probes"]["offline_mode"] is True
    print("self-test offline no-go report: ok")


def _self_test_forbidden_scan_rejects_injection() -> None:
    """Forbidden scanner rejects row-level path/range/snippet/content_sha."""
    _nl = chr(10)
    bad_report = {
        "instance_id": "leak",
        "repo": "src/leak.py",
        "patch": "diff --git a/x b/x" + _nl + "+leak" + _nl,
        "content_sha": "a" * 40,
        "gold_spans": [[1, 2]],
        "private_labels": "leak",
        "snippet": "fn main(){}",
        "ground_truth": {"patch": "leak"},
    }
    violations = _scan_forbidden(bad_report)
    cats = {v["category"] for v in violations}
    assert "forbidden_key" in cats, cats
    assert "hex_digest_value" in cats, cats
    assert "path_like_value" in cats, cats
    assert "multiline_value" in cats, cats
    summary = _forbidden_scan_summary(bad_report)
    assert summary["status"] == "fail"
    assert summary["violations_count"] > 0
    # Injected "12-34" line range must be rejected.
    bad_range = {"injected_range": "12-34"}
    range_violations = _scan_forbidden(bad_range)
    range_cats = {v["category"] for v in range_violations}
    assert "line_range_value" in range_cats, range_cats
    # A clean report with only source-level URLs passes.
    clean = {
        "schema_version": SCHEMA_VERSION,
        "arxiv_abs_url": ARXIV_ABS_URL,
        "hf_dataset_url": HF_DATASET_URL,
        "placeholder_repo_files_observed": [".gitattributes", "README.md"],
    }
    clean_violations = _scan_forbidden(clean)
    assert clean_violations == [], clean_violations
    clean_summary = _forbidden_scan_summary(clean)
    assert clean_summary["status"] == "pass"
    print("self-test forbidden scan rejects injection: ok")


def _self_test_source_urls_allowed() -> None:
    """Official source-level URLs are allowed by the forbidden scanner."""
    report = {
        "arxiv_abs_url": ARXIV_ABS_URL,
        "arxiv_html_url": ARXIV_HTML_URL,
        "arxiv_pdf_url": ARXIV_PDF_URL,
        "doi_url": DOI_URL,
        "hf_dataset_url": HF_DATASET_URL,
        "hf_api_datasets_url": HF_API_DATASETS_URL,
        "hf_api_tree_url": HF_API_TREE_URL,
        "ds_server_is_valid_url": DS_SERVER_IS_VALID_URL,
        "ds_server_splits_url": DS_SERVER_SPLITS_URL,
        "ds_server_first_rows_url": DS_SERVER_FIRST_ROWS_URL,
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
        "synthetic patch",
        "synthetic gold context",
        "src/main.py",
        "diff --git",
        "12-34",
        "1-10",
        "/tmp/synthetic",
    ):
        assert forbidden_substring not in report_json, forbidden_substring
    # Re-scan to be sure.
    rescan = _forbidden_scan_summary(report)
    assert rescan["status"] == "pass", rescan
    print("self-test report aggregate-only: ok")


def run_self_tests() -> dict[str, Any]:
    """Run all C4.4 self-tests. Returns a summary (no row-level data)."""
    _self_test_wrong_target_disambiguation()
    _self_test_offline_no_go_report()
    _self_test_forbidden_scan_rejects_injection()
    _self_test_source_urls_allowed()
    _self_test_report_aggregate_only()
    return {
        "schema_version": SCHEMA_VERSION,
        "claim_level": CLAIM_LEVEL,
        "self_test_passed": True,
        "self_test_checks": {
            "wrong_target_disambiguation": True,
            "offline_no_go_report": True,
            "forbidden_scan_rejects_injection": True,
            "source_urls_allowed": True,
            "report_aggregate_only": True,
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
        description="C4.4 CORE-Bench source readiness / no-go (bounded).",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the C4.4 self-test (synthetic fixtures; no network).",
    )
    parser.add_argument(
        "--source-readiness",
        action="store_true",
        help="build the source-readiness no-go report (default mode).",
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
            "c4_core_bench_source_readiness_report.json)."
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
            "C4.4 CORE-Bench source readiness self-test: PASS",
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
        "schema_smoke_passed": report["schema_smoke_passed"],
        "wrong_target_disambiguated": report["wrong_target_disambiguated"],
        "not_siegelz_core_bench": report["not_siegelz_core_bench"],
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
    # The status is always blocked_* (no-go); exit 0 because the no-go
    # report itself was generated successfully.
    if report["forbidden_scan"]["status"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
