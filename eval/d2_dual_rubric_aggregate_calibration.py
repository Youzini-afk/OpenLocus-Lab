#!/usr/bin/env python3
"""D2 Dual-Rubric Aggregate Calibration — proxy mappability + opt-in private smoke.

D2 is the bounded **proxy** aggregate calibration follow-on to D1. It does
NOT claim true E/S calibration. It operates in two strictly separated modes:

* **D2a (default, committed)**: public aggregate mappability inventory.
  Reads committed C3/B12 public aggregate artifacts only; does NOT read
  private records. Claim level: ``public_aggregate_mappability_only``.
  ``proxy_calibration_claimed=false``;
  ``true_e_s_calibration_claimed=false``.

* **D2b (opt-in, NOT committed)**: explicit local/private proxy
  calibration smoke. Requires
  ``--allow-private-records --input <path> --limit N --out /tmp/...``.
  Never serializes the input path/basename/file size/mtime. Emits
  aggregate proxy bucket counts with small-cell suppression only.
  Claim level: ``dual_rubric_proxy_calibration_smoke_only``.

Claim boundary (binding):

* This is **eval/diagnostic only**. It is NOT a runtime change, NOT a
  retriever/pack/model/backend/default-policy change, and NOT an
  EvidenceCore semantic change.
* Proxy scores (``proxy_e_score``, ``proxy_s_score``) are NOT true E/S
  calibration, NOT improved retrieval, NOT downstream agent value, NOT
  a benchmark result, NOT a default change, and NOT a runtime-clean
  general algorithm claim.
* Missing proxy fields become ``proxy_unmappable``, NOT negative
  evidence.
* Small-cell suppression (``k_min`` 3 or 5) for private aggregate
  crosstabs; rare cells are omitted.
* A strict forbidden-output scanner runs fail-closed before any
  artifact is written.

Proxy terminology (D2 never claims true E/S calibration):

* ``proxy_e_score`` / ``proxy_s_score``: small-integer proxy signals
  mapped from P21 outcome metrics (proxy E-like) and route features
  (proxy S-like), in memory only.
* ``proxy_e_band`` / ``proxy_s_band``: ``none`` / ``weak`` / ``high``.
* ``proxy_bucket``: ``proxy_primary_evidence`` /
  ``proxy_dependency_support`` / ``proxy_weak_candidates`` /
  ``proxy_abstained`` / ``proxy_unmappable``.

Run::

    python3 -m py_compile eval/d2_dual_rubric_aggregate_calibration.py
    python3 eval/d2_dual_rubric_aggregate_calibration.py --self-test
    python3 eval/d2_dual_rubric_aggregate_calibration.py \\
        --out artifacts/d2_dual_rubric_aggregate_calibration/\\
d2_dual_rubric_aggregate_calibration_report.json
    # D2b opt-in (private, /tmp only, NOT committed):
    python3 eval/d2_dual_rubric_aggregate_calibration.py \\
        --allow-private-records --input /tmp/private.json \\
        --limit 100 --out /tmp/d2b_proxy_smoke.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "d2_dual_rubric_aggregate_calibration.v1"
GENERATED_BY = "eval/d2_dual_rubric_aggregate_calibration.py"
RUBRIC_VERSION = "d2_proxy_dual_rubric_v1"

# D2a (default, committed): public aggregate mappability inventory.
CLAIM_LEVEL_D2A = "public_aggregate_mappability_only"
STATUS_D2A = "public_aggregate_mappability_only"
MODE_D2A = "public_inventory"

# D2b (opt-in, NOT committed): private proxy calibration smoke.
CLAIM_LEVEL_D2B = "dual_rubric_proxy_calibration_smoke_only"
STATUS_D2B = "proxy_smoke_completed"
MODE_D2B = "private_proxy_smoke"

PRIVATE_LOAD_ERROR_MESSAGE = (
    "error: failed to load private records "
    "(schema/privacy/parse error; details suppressed)"
)

DEFAULT_OUT = Path(
    "artifacts/d2_dual_rubric_aggregate_calibration/"
    "d2_dual_rubric_aggregate_calibration_report.json"
)

# ---------------------------------------------------------------------------
# Proxy rubric semantics
# ---------------------------------------------------------------------------

# Proxy E signals (semantic / direct-answer evidence proxies). Mapped from
# P21 outcome metrics of the candidate_baseline strategy, IN MEMORY ONLY.
# These are PROXY signals, NOT true E/S calibration.
PROXY_E_SIGNAL_NAMES: tuple[str, ...] = (
    "span_f0_5_high",       # span_f0_5 > 0.5
    "added_gold_span_pos",  # added_gold_span > 0
    "low_primary_fpr",      # primary_false_positive_rate < 0.3
)
PROXY_E_SCORE_MAX = len(PROXY_E_SIGNAL_NAMES)  # 3

# Proxy S signals (dependency / support-structure evidence proxies). Mapped
# from route_features, IN MEMORY ONLY.
PROXY_S_SIGNAL_NAMES: tuple[str, ...] = (
    "candidate_support_exists",
    "local_anchor",
    "rrf_backed_by_anchor",
    "symbol_regex_agree",   # file OR span
    "dense_support_present",
)
PROXY_S_SCORE_MAX = len(PROXY_S_SIGNAL_NAMES)  # 5

# Strategy whose outcome metrics are used as the proxy E source.
PROXY_E_STRATEGY = "candidate_baseline"

# Thresholds: deterministic small-integer bands (mirror D1 pattern).
PROXY_E_HIGH_MIN = 2
PROXY_S_HIGH_MIN = 2
PROXY_WEAK_MIN = 1

# Bands.
BAND_NONE = "none"
BAND_WEAK = "weak"
BAND_HIGH = "high"

# Proxy buckets (fail-closed classification order).
PROXY_BUCKET_PRIMARY_EVIDENCE = "proxy_primary_evidence"
PROXY_BUCKET_DEPENDENCY_SUPPORT = "proxy_dependency_support"
PROXY_BUCKET_WEAK_CANDIDATES = "proxy_weak_candidates"
PROXY_BUCKET_ABSTAINED = "proxy_abstained"
PROXY_BUCKET_UNMAPPABLE = "proxy_unmappable"

PROXY_BUCKET_NAMES: tuple[str, ...] = (
    PROXY_BUCKET_PRIMARY_EVIDENCE,
    PROXY_BUCKET_DEPENDENCY_SUPPORT,
    PROXY_BUCKET_WEAK_CANDIDATES,
    PROXY_BUCKET_ABSTAINED,
    PROXY_BUCKET_UNMAPPABLE,
)

# Reason codes (aggregate labels only, never row-level).
PROXY_REASON_E_HIGH = "proxy_e_high"
PROXY_REASON_S_HIGH_E_LOW = "proxy_s_high_e_below_high"
PROXY_REASON_WEAK = "proxy_weak_nonzero_e_or_s"
PROXY_REASON_NO_EVIDENCE = "proxy_no_evidence"
PROXY_REASON_MISSING_FIELDS = "proxy_missing_required_fields"

CLASSIFICATION_ORDER: tuple[str, ...] = (
    "missing_required_fields_to_proxy_unmappable",
    "proxy_e_high_is_proxy_primary_evidence",
    "proxy_s_high_e_below_high_is_proxy_dependency_support",
    "weak_nonzero_proxy_e_or_s_is_proxy_weak_candidates",
    "else_proxy_abstained",
)

# Small-cell suppression.
K_MIN_DEFAULT = 5
K_MIN_SELF_TEST = 3

# D2a public artifact classes (generic labels, NOT filesystem paths).
ARTIFACT_CLASSES_CHECKED: tuple[str, ...] = (
    "c3_public_aggregate",
    "b12_public_aggregate",
)

# ---------------------------------------------------------------------------
# No-claim / safety flags
# ---------------------------------------------------------------------------

NO_CLAIM_FLAGS: dict[str, bool] = {
    "promotion_ready": False,
    "default_should_change": False,
    "evidencecore_semantics_changed": False,
    "runtime_clean_general_algorithm_claimed": False,
    "downstream_agent_value_proven": False,
    "ood_temporal_supported": False,
    "quiver_systems_supported": False,
}

SAFETY_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
    "not_evidence": True,
    "runtime_behavior_changed": False,
    "retriever_changed": False,
    "pack_builder_changed": False,
    "model_calls_changed": False,
    "backend_changed": False,
    "default_policy_changed": False,
    "candidate_text_emitted": False,
    "paths_or_spans_emitted": False,
    "content_sha_emitted": False,
    "row_level_hashes_emitted": False,
    "per_candidate_rows_emitted": False,
}

# ---------------------------------------------------------------------------
# Forbidden-output scanner (D2-specific, fail-closed)
# ---------------------------------------------------------------------------

# Sensitive KEY names that must NEVER appear as dict keys anywhere in a
# public JSON output. These are row-level / candidate-leak / private-record
# field names. Extended beyond D1 with D2-specific private-record keys.
FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset(
    {
        # location / span
        "path", "span", "line_range", "start_line", "end_line",
        "start_byte", "end_byte", "line_ranges", "spans",
        # content / hash
        "content_sha", "content_hash", "hash", "digest", "sha256",
        "md5", "sha1",
        "snippet", "snippets", "excerpt", "excerpts", "candidate_text",
        "text", "code", "code_snippet", "source_code", "content", "body",
        # identifiers
        "task_id", "repo_id", "repo", "instance_id", "row_id",
        "record_id", "id", "name", "filename", "filepath",
        # labels / qrels
        "label", "labels", "qrels", "gold", "gold_label", "gold_labels",
        "gold_answer", "predicted_answer", "answer", "question",
        # prompts / responses
        "query", "prompt", "response", "model_response", "model_output",
        "provider_payload", "raw_payload", "api_response", "response_body",
        # rows / records
        "raw_rows", "rows", "records", "tasks", "row_values",
        # patches / tests
        "patch", "test_patch", "tests",
        # secrets
        "api_key", "api_token", "api_secret", "base_url", "provider_key",
        "authorization",
        # D2-specific private-record fields (C1/P21 private payload)
        "private_record_hash", "private_records", "private_rows",
        "p31_score_gold", "p31_candidate_pools", "p33b_anchor_subtypes",
        "candidate_id", "gold_spans", "raw_query", "raw_snippet",
        "raw_prompt", "raw_response",
    }
)

# Known-safe provenance value paths (allowlisted for hex_digest / path_like
# value checks only). The forbidden dict-key check is NOT relaxed by this.
SAFE_VALUE_KEY_NAMES: frozenset[str] = frozenset(
    {
        "schema_version",
        "generated_by",
        "generated_at",
        "claim_level",
        "rubric_version",
        "status",
        "mode",
    }
)

# Value patterns that indicate leaked row-level / candidate data.
_RE_URL_VALUE = re.compile(r"https?://", re.IGNORECASE)
_RE_HEX_DIGEST = re.compile(r"[A-Fa-f0-9]{32,}")
_RE_SECRET_LIKE = re.compile(
    r"(?:api[_-]?key|api[_-]?token|api[_-]?secret|base[_-]?url"
    r"|provider[_-]?key|authorization[_-]?bearer)",
    re.IGNORECASE,
)
_FILE_EXT = (
    r"py|rs|ts|tsx|js|jsx|go|java|c|cpp|cc|h|hpp|hh|md|json|toml|"
    r"yaml|yml|txt|sh|rb|php|kt|swift|patch|diff|csv|parquet|jsonl"
)
# Path-like strings, with OR without a leading slash (e.g. "src/foo.py",
# "foo.py", "/a/b.py", "/private/foo.jsonl").
_RE_FILE_PATH_VALUE = re.compile(
    rf"\b[A-Za-z0-9._/\-]+\.(?:{_FILE_EXT})\b"
)
# Raw line-range value: "12-34" or "12:34" (3-16 chars, digits + separator).
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


def _scan_forbidden(obj: Any, path: str = "$") -> list[dict[str, Any]]:
    """Strict recursive scanner for public JSON outputs.

    Returns a list of violation dicts with ``category`` and ``path``
    (JSON path), NEVER the leaked value itself. Fail-closed: any
    violation means the public output would leak.

    Rejects forbidden dict keys (path/span/content_sha/snippet/query/
    task_id/repo_id/repo/label/qrels/gold/prompt/response/private_*/etc.)
    anywhere, and rejects value patterns: URLs, 32/40/64-char hex
    digests, secret-like strings, path-like strings (``src/foo.py``,
    ``/private/foo.jsonl``), multiline strings, raw JSON fragments,
    and raw line-range strings (``12-34``).

    Allows generic aggregate reason_code / bucket / band strings only if
    they are not row-like.
    """
    violations: list[dict[str, Any]] = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            sub_path = f"{path}.{key_str}"
            if key_str in FORBIDDEN_KEY_NAMES:
                violations.append(
                    {"category": "forbidden_key", "path": sub_path}
                )
            violations.extend(_scan_forbidden(value, sub_path))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_scan_forbidden(value, f"{path}[{idx}]"))
    elif isinstance(obj, str):
        safe_value = _is_safe_value_path(path)
        if len(obj) > 256:
            violations.append({"category": "long_string", "path": path})
        elif _RE_URL_VALUE.search(obj) and not safe_value:
            violations.append({"category": "url_value", "path": path})
        elif not safe_value and _RE_HEX_DIGEST.search(obj):
            violations.append({"category": "hex_digest_value", "path": path})
        elif _RE_SECRET_LIKE.search(obj):
            violations.append({"category": "secret_like_value", "path": path})
        elif _RE_FILE_PATH_VALUE.search(obj) and not safe_value:
            violations.append({"category": "path_like_value", "path": path})
        elif "\n" in obj:
            violations.append({"category": "multiline_value", "path": path})
        elif _RE_RAW_JSON.search(obj):
            violations.append({"category": "raw_json_fragment", "path": path})
        else:
            # A raw line-range value: "12-34" or "12:34" (3-16 chars,
            # only digits + separator). Pure-digit strings like "1234"
            # are NOT flagged (they could be counts).
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


def _enforce_no_forbidden(obj: Any) -> None:
    """Fail-closed guard: raise SystemExit if any forbidden content leaks."""
    scan = _forbidden_scan_summary(obj)
    if scan["status"] != "pass":
        raise SystemExit(
            f"forbidden content leak; refusing to write artifact: "
            f"{scan['categories']}"
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


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Proxy scoring + classification
# ---------------------------------------------------------------------------


def compute_proxy_e_score(signals: dict[str, bool]) -> int:
    """Proxy E-score = count of true proxy E signals (range 0..MAX)."""
    return sum(1 for v in signals.values() if v)


def compute_proxy_s_score(signals: dict[str, bool]) -> int:
    """Proxy S-score = count of true proxy S signals (range 0..MAX)."""
    return sum(1 for v in signals.values() if v)


def proxy_band(score: int, high_min: int) -> str:
    """Map a raw proxy score to a band label."""
    if score >= high_min:
        return BAND_HIGH
    if score >= PROXY_WEAK_MIN:
        return BAND_WEAK
    return BAND_NONE


def classify_proxy(
    proxy_e_signals: dict[str, bool] | None,
    proxy_s_signals: dict[str, bool] | None,
) -> tuple[str, str]:
    """Classify proxy signals into a proxy_bucket + reason code.

    Fail-closed order:
      1. missing required proxy fields -> ``proxy_unmappable``.
      2. proxy_e high -> ``proxy_primary_evidence``.
      3. proxy_s high and proxy_e below high -> ``proxy_dependency_support``.
      4. weak nonzero proxy_e or proxy_s -> ``proxy_weak_candidates``.
      5. else -> ``proxy_abstained``.

    Missing proxy fields become ``proxy_unmappable``, NOT negative
    evidence (requirement 3).
    """
    if proxy_e_signals is None or proxy_s_signals is None:
        return PROXY_BUCKET_UNMAPPABLE, PROXY_REASON_MISSING_FIELDS

    e = compute_proxy_e_score(proxy_e_signals)
    s = compute_proxy_s_score(proxy_s_signals)

    if e >= PROXY_E_HIGH_MIN:
        return PROXY_BUCKET_PRIMARY_EVIDENCE, PROXY_REASON_E_HIGH
    if s >= PROXY_S_HIGH_MIN and e < PROXY_E_HIGH_MIN:
        return PROXY_BUCKET_DEPENDENCY_SUPPORT, PROXY_REASON_S_HIGH_E_LOW
    if e >= PROXY_WEAK_MIN or s >= PROXY_WEAK_MIN:
        return PROXY_BUCKET_WEAK_CANDIDATES, PROXY_REASON_WEAK
    return PROXY_BUCKET_ABSTAINED, PROXY_REASON_NO_EVIDENCE


# ---------------------------------------------------------------------------
# Proxy signal extraction from PrivateRecord (D2b only, in memory)
# ---------------------------------------------------------------------------


def _extract_proxy_e_signals(record: Any) -> dict[str, bool] | None:
    """Extract proxy E signals from the candidate_baseline outcome.

    Returns None if the outcome is missing/incomplete (proxy_unmappable).
    Operates IN MEMORY ONLY; never serializes the record.
    """
    outcome_present = getattr(record, "outcome_present", {}) or {}
    if not outcome_present.get(PROXY_E_STRATEGY, False):
        return None
    outcomes = getattr(record, "outcomes", {}) or {}
    outcome = outcomes.get(PROXY_E_STRATEGY, {})
    if not isinstance(outcome, dict):
        return None
    try:
        span_f0_5 = float(outcome.get("span_f0_5", 0.0))
        added_gold = float(outcome.get("added_gold_span", 0.0))
        primary_fpr = float(outcome.get("primary_false_positive_rate", 0.0))
    except (TypeError, ValueError):
        return None
    return {
        "span_f0_5_high": span_f0_5 > 0.5,
        "added_gold_span_pos": added_gold > 0,
        "low_primary_fpr": primary_fpr < 0.3,
    }


def _extract_proxy_s_signals(record: Any) -> dict[str, bool] | None:
    """Extract proxy S signals from route_features.

    Returns None if required core fields (candidate_support_exists,
    local_anchor) are missing (proxy_unmappable). Optional fields default
    to False.

    Operates IN MEMORY ONLY; never serializes the record.
    """
    rf = getattr(record, "route_features", None)
    if not isinstance(rf, dict):
        return None
    # Required core proxy S fields.
    if "candidate_support_exists" not in rf or "local_anchor" not in rf:
        return None
    try:
        candidate_support = bool(rf.get("candidate_support_exists", False))
        local_anchor = bool(rf.get("local_anchor", False))
        rrf_backed = bool(rf.get("rrf_backed_by_anchor", False))
        symbol_regex_file = bool(rf.get("symbol_regex_agree_file", False))
        symbol_regex_span = bool(rf.get("symbol_regex_agree_span", False))
        dense_support = bool(rf.get("dense_support_present", False))
    except (TypeError, ValueError):
        return None
    return {
        "candidate_support_exists": candidate_support,
        "local_anchor": local_anchor,
        "rrf_backed_by_anchor": rrf_backed,
        "symbol_regex_agree": symbol_regex_file or symbol_regex_span,
        "dense_support_present": dense_support,
    }


# ---------------------------------------------------------------------------
# Small-cell suppression
# ---------------------------------------------------------------------------


def _suppress_small_cells(
    crosstab: dict[str, int], k_min: int
) -> tuple[dict[str, int], bool, int]:
    """Suppress crosstab cells with count < k_min.

    Returns (suppressed_crosstab, small_cells_suppressed,
    suppressed_cell_count). Suppressed cells are OMITTED from the output
    crosstab (not collapsed into a labeled bucket, to avoid leaking the
    suppressed cell label). The suppressed_cell_count is the number of
    cells omitted (NOT the individual counts).
    """
    result: dict[str, int] = {}
    suppressed_count = 0
    for cell, count in crosstab.items():
        if count >= k_min:
            result[cell] = count
        else:
            suppressed_count += 1
    small_cells_suppressed = suppressed_count > 0
    return result, small_cells_suppressed, suppressed_count


# ---------------------------------------------------------------------------
# D2a: public aggregate mappability inventory (default, committed)
# ---------------------------------------------------------------------------


# Generic-label -> public artifact path mapping (paths are NOT serialized
# into the D2a artifact; only generic labels and booleans are emitted).
_D2A_PUBLIC_ARTIFACT_PATHS: dict[str, Path] = {
    "c3_public_aggregate": Path(
        "artifacts/c3_budgeted_evidence_acquisition/"
        "c3_budgeted_evidence_acquisition_report.json"
    ),
    "b12_public_aggregate": Path(
        "artifacts/b12_mechanism_decomposition/"
        "b12_public_aggregate_screen_report.json"
    ),
}


def _check_public_aggregate_artifact(
    label: str, path: Path
) -> dict[str, Any]:
    """Check a public aggregate artifact for proxy-relevant fields.

    Returns a dict with generic labels and booleans only. NEVER emits the
    filesystem path, content_sha, or any row-level field. The artifact is
    already a public aggregate; this check only inspects which aggregate
    field categories are present (no candidate-level proxy fields exist in
    public aggregates by construction).
    """
    present = path.is_file()
    info: dict[str, Any] = {
        "artifact_class": label,
        "present": present,
        "has_candidate_level_proxy_fields": False,
        "has_aggregate_proxy_relevant_fields": False,
    }
    if not present:
        return info
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        info["present"] = False
        info["read_error"] = True
        return info
    if not isinstance(data, dict):
        info["present"] = False
        info["read_error"] = True
        return info
    # Check for aggregate-level proxy-relevant field categories. These are
    # AGGREGATE fields (means, deltas, counts), NOT candidate-level fields.
    aggregate_proxy_relevant = False
    if label == "c3_public_aggregate":
        aggregate_proxy_relevant = (
            "allowed_runtime_features" in data
            or "baselines" in data
            or "deltas" in data
        )
    elif label == "b12_public_aggregate":
        aggregate_proxy_relevant = (
            "hypothesis_results" in data
            or "input_b11_summary" in data
        )
    info["has_aggregate_proxy_relevant_fields"] = bool(
        aggregate_proxy_relevant
    )
    # Public aggregates NEVER contain candidate-level proxy fields by
    # construction (they are aggregate-only).
    info["has_candidate_level_proxy_fields"] = False
    return info


def build_d2a_report(
    self_test_checks: list[dict[str, Any]] | None = None,
    self_test_passed: bool = False,
) -> dict[str, Any]:
    """Build the D2a public aggregate mappability inventory report.

    Default committed artifact. Reads committed C3/B12 public aggregate
    artifacts only; does NOT read private records.
    """
    public_artifacts_checked: dict[str, bool] = {}
    public_artifact_details: list[dict[str, Any]] = []
    present_count = 0
    aggregate_relevant_count = 0
    candidate_level_count = 0

    for label in ARTIFACT_CLASSES_CHECKED:
        path = _D2A_PUBLIC_ARTIFACT_PATHS.get(label)
        if path is None:
            continue
        info = _check_public_aggregate_artifact(label, path)
        public_artifacts_checked[label] = info["present"]
        public_artifact_details.append(info)
        if info["present"]:
            present_count += 1
        if info.get("has_aggregate_proxy_relevant_fields"):
            aggregate_relevant_count += 1
        if info.get("has_candidate_level_proxy_fields"):
            candidate_level_count += 1

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL_D2A,
        "rubric_version": RUBRIC_VERSION,
        "status": STATUS_D2A,
        "mode": MODE_D2A,
        "artifact_classes_checked": list(ARTIFACT_CLASSES_CHECKED),
        "public_artifacts_checked": public_artifacts_checked,
        "public_artifact_status_counts": {
            "present": present_count,
            "absent": len(ARTIFACT_CLASSES_CHECKED) - present_count,
        },
        "public_aggregate_details": public_artifact_details,
        # Proxy terminology (D2a never claims true E/S calibration).
        "proxy_field_terminology": {
            "proxy_e_score": (
                "proxy semantic/direct-answer evidence score "
                "(NOT true E calibration)"
            ),
            "proxy_s_score": (
                "proxy dependency/support-structure evidence score "
                "(NOT true S calibration)"
            ),
            "proxy_e_band": "none/weak/high band over proxy_e_score",
            "proxy_s_band": "none/weak/high band over proxy_s_score",
            "proxy_bucket": (
                "proxy_primary_evidence/proxy_dependency_support/"
                "proxy_weak_candidates/proxy_abstained/proxy_unmappable"
            ),
        },
        "proxy_e_signal_names": list(PROXY_E_SIGNAL_NAMES),
        "proxy_s_signal_names": list(PROXY_S_SIGNAL_NAMES),
        "proxy_bucket_names": list(PROXY_BUCKET_NAMES),
        "public_aggregates_have_candidate_level_proxy_fields": (
            candidate_level_count > 0
        ),
        "public_aggregates_have_aggregate_proxy_relevant_fields": (
            aggregate_relevant_count > 0
        ),
        "private_input_required_for_proxy_calibration": True,
        # D2a never claims proxy calibration or true E/S calibration.
        "proxy_calibration_claimed": False,
        "true_e_s_calibration_claimed": False,
        # D2a never reads private records.
        "private_records_read": False,
        "private_records_persisted": False,
        "local_input_path_emitted": False,
        # Self-test results.
        "self_test_checks": self_test_checks or [],
        "self_test_passed": self_test_passed,
        # No-claim + safety flags (flat, scaffold-only values).
        **NO_CLAIM_FLAGS,
        **SAFETY_FLAGS,
        "raw_private_records_read": False,
        "raw_private_records_persisted": False,
    }

    # Fail-closed forbidden scan before returning.
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_leak"
    return report


# ---------------------------------------------------------------------------
# D2b: private proxy calibration smoke (opt-in, NOT committed, /tmp only)
# ---------------------------------------------------------------------------


def calibrate_private_proxy(
    records: list[Any],
    *,
    input_path: Path | None = None,
    limit: int = 0,
    k_min: int = K_MIN_DEFAULT,
) -> dict[str, Any]:
    """Run D2b private proxy calibration smoke over loaded records.

    ``input_path`` is accepted for CLI plumbing but is NEVER serialized
    into the output artifact (no path, basename, file size, or mtime).
    Records are processed IN MEMORY ONLY; only aggregate proxy bucket
    counts and suppressed crosstabs are emitted.

    ``limit`` caps the number of records processed (0 = no cap).

    Returns a D2b report dict (NOT committed; caller writes to /tmp only).
    """
    # Cap records.
    if limit > 0:
        records = records[:limit]

    proxy_bucket_counts: dict[str, int] = {b: 0 for b in PROXY_BUCKET_NAMES}
    proxy_e_band_counts: dict[str, int] = {
        BAND_NONE: 0, BAND_WEAK: 0, BAND_HIGH: 0,
    }
    proxy_s_band_counts: dict[str, int] = {
        BAND_NONE: 0, BAND_WEAK: 0, BAND_HIGH: 0,
    }
    reason_counts: dict[str, int] = {}
    crosstab: dict[str, int] = {}

    for record in records:
        e_signals = _extract_proxy_e_signals(record)
        s_signals = _extract_proxy_s_signals(record)
        bucket, reason = classify_proxy(e_signals, s_signals)
        proxy_bucket_counts[bucket] += 1
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

        if e_signals is not None:
            e = compute_proxy_e_score(e_signals)
        else:
            e = 0
        if s_signals is not None:
            s = compute_proxy_s_score(s_signals)
        else:
            s = 0
        e_band = proxy_band(e, PROXY_E_HIGH_MIN)
        s_band = proxy_band(s, PROXY_S_HIGH_MIN)
        proxy_e_band_counts[e_band] += 1
        proxy_s_band_counts[s_band] += 1

        cell = f"{e_band}_x_{s_band}"
        crosstab[cell] = crosstab.get(cell, 0) + 1

    suppressed_crosstab, small_cells_suppressed, suppressed_cell_count = (
        _suppress_small_cells(crosstab, k_min)
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL_D2B,
        "rubric_version": RUBRIC_VERSION,
        "status": STATUS_D2B,
        "mode": MODE_D2B,
        "proxy_e_signal_names": list(PROXY_E_SIGNAL_NAMES),
        "proxy_s_signal_names": list(PROXY_S_SIGNAL_NAMES),
        "proxy_e_strategy": PROXY_E_STRATEGY,
        "proxy_e_score_max": PROXY_E_SCORE_MAX,
        "proxy_s_score_max": PROXY_S_SCORE_MAX,
        "thresholds": {
            "proxy_e_high_min": PROXY_E_HIGH_MIN,
            "proxy_s_high_min": PROXY_S_HIGH_MIN,
            "proxy_weak_min": PROXY_WEAK_MIN,
        },
        "classification_order": list(CLASSIFICATION_ORDER),
        "proxy_bucket_names": list(PROXY_BUCKET_NAMES),
        "private_record_count": len(records),
        "proxy_bucket_counts": proxy_bucket_counts,
        "proxy_e_band_counts": proxy_e_band_counts,
        "proxy_s_band_counts": proxy_s_band_counts,
        "proxy_e_s_band_crosstab": suppressed_crosstab,
        "small_cells_suppressed": small_cells_suppressed,
        "suppressed_cell_count": suppressed_cell_count,
        "k_min": k_min,
        "reason_code_counts": reason_counts,
        # D2b DID run proxy calibration (smoke), but NOT true E/S calibration.
        "proxy_calibration_claimed": True,
        "true_e_s_calibration_claimed": False,
        # D2b read private records transiently (in memory only).
        "private_records_read": True,
        "private_records_persisted": False,
        "local_input_path_emitted": False,
        # No-claim + safety flags.
        **NO_CLAIM_FLAGS,
        **SAFETY_FLAGS,
        "raw_private_records_read": True,
        "raw_private_records_persisted": False,
    }

    # Fail-closed forbidden scan before returning.
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_leak"
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return {"check": name, "passed": bool(ok)}


def _load_synthetic_private_records() -> tuple[list[Any], dict[str, Any]]:
    """Load synthetic P21 v1 private records (in memory) for self-test.

    Uses ``c1_private_records.build_synthetic_v1_payload`` + the C1
    loader. Records are NEVER serialized into any committed artifact.
    """
    import c1_private_records as c1
    payload = c1.build_synthetic_v1_payload()
    records, meta = c1.load_private_records_from_payload(
        payload, model_family="kimi"
    )
    return records, meta


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all D2 self-test groups. Returns (checks, all_passed)."""
    checks: list[dict[str, Any]] = []

    # --- Requirement 1: Default mode no private read. ---
    d2a = build_d2a_report([], False)
    checks.append(
        _check(
            "d2a_default_private_records_read_false",
            d2a["private_records_read"] is False,
        )
    )
    checks.append(
        _check(
            "d2a_default_proxy_calibration_claimed_false",
            d2a["proxy_calibration_claimed"] is False,
        )
    )
    checks.append(
        _check(
            "d2a_default_true_e_s_calibration_claimed_false",
            d2a["true_e_s_calibration_claimed"] is False,
        )
    )
    checks.append(
        _check(
            "d2a_default_mode_is_public_inventory",
            d2a["mode"] == MODE_D2A,
        )
    )
    checks.append(
        _check(
            "d2a_default_status_is_public_aggregate_mappability_only",
            d2a["status"] == STATUS_D2A,
        )
    )
    checks.append(
        _check(
            "d2a_default_local_input_path_emitted_false",
            d2a["local_input_path_emitted"] is False,
        )
    )

    # --- Requirement 2: Proxy naming boundary. ---
    # D2a artifact uses proxy_e/proxy_s terminology; no true E/S claim.
    d2a_blob = json.dumps(d2a, sort_keys=True)
    checks.append(
        _check(
            "d2a_artifact_uses_proxy_e_proxy_s_terminology",
            "proxy_e_score" in d2a_blob
            and "proxy_s_score" in d2a_blob
            and "proxy_e_band" in d2a_blob
            and "proxy_s_band" in d2a_blob
            and "proxy_bucket" in d2a_blob,
        )
    )
    checks.append(
        _check(
            "d2a_no_true_e_s_calibration_claim",
            d2a["true_e_s_calibration_claimed"] is False
            and d2a["proxy_calibration_claimed"] is False,
        )
    )

    # --- Requirement 3: Missing fields become proxy_unmappable. ---
    # A record with missing candidate_baseline outcome -> proxy_unmappable.
    e_missing = None  # simulates missing outcome
    s_present = {"candidate_support_exists": True, "local_anchor": True,
                 "rrf_backed_by_anchor": True, "symbol_regex_agree": True,
                 "dense_support_present": True}
    bucket_missing, reason_missing = classify_proxy(e_missing, s_present)
    checks.append(
        _check(
            "missing_proxy_e_fields_become_proxy_unmappable",
            bucket_missing == PROXY_BUCKET_UNMAPPABLE
            and reason_missing == PROXY_REASON_MISSING_FIELDS,
        )
    )
    # A record with missing proxy_s core fields -> proxy_unmappable.
    e_present = {"span_f0_5_high": True, "added_gold_span_pos": True,
                 "low_primary_fpr": True}
    bucket_missing_s, reason_missing_s = classify_proxy(e_present, None)
    checks.append(
        _check(
            "missing_proxy_s_fields_become_proxy_unmappable",
            bucket_missing_s == PROXY_BUCKET_UNMAPPABLE
            and reason_missing_s == PROXY_REASON_MISSING_FIELDS,
        )
    )
    # Missing fields are NOT negative evidence: a record with missing fields
    # is NOT classified as proxy_abstained (which would imply zero evidence
    # was observed). It is proxy_unmappable.
    checks.append(
        _check(
            "missing_fields_not_proxy_abstained",
            bucket_missing != PROXY_BUCKET_ABSTAINED,
        )
    )

    # --- Requirement 4: Synthetic private records produce aggregate proxy
    # buckets, no record IDs/raw fields emitted. ---
    records, _meta = _load_synthetic_private_records()
    d2b = calibrate_private_proxy(
        records,
        input_path=Path("/private/foo.jsonl"),
        limit=0,
        k_min=K_MIN_SELF_TEST,
    )
    checks.append(
        _check(
            "d2b_produces_proxy_bucket_counts",
            isinstance(d2b.get("proxy_bucket_counts"), dict)
            and sum(d2b["proxy_bucket_counts"].values()) == len(records),
        )
    )
    checks.append(
        _check(
            "d2b_produces_proxy_e_band_counts",
            isinstance(d2b.get("proxy_e_band_counts"), dict)
            and sum(d2b["proxy_e_band_counts"].values()) == len(records),
        )
    )
    checks.append(
        _check(
            "d2b_produces_proxy_s_band_counts",
            isinstance(d2b.get("proxy_s_band_counts"), dict)
            and sum(d2b["proxy_s_band_counts"].values()) == len(records),
        )
    )
    checks.append(
        _check(
            "d2b_proxy_calibration_claimed_true",
            d2b["proxy_calibration_claimed"] is True,
        )
    )
    checks.append(
        _check(
            "d2b_true_e_s_calibration_claimed_false",
            d2b["true_e_s_calibration_claimed"] is False,
        )
    )
    checks.append(
        _check(
            "d2b_private_records_read_true",
            d2b["private_records_read"] is True,
        )
    )
    checks.append(
        _check(
            "d2b_raw_private_records_read_true",
            d2b["raw_private_records_read"] is True,
        )
    )
    checks.append(
        _check(
            "d2b_private_records_persisted_false",
            d2b["private_records_persisted"] is False,
        )
    )
    # No record IDs / raw fields in D2b artifact.
    d2b_blob = json.dumps(d2b, sort_keys=True)
    forbidden_substrings = (
        "c1-selftest-",   # task_id prefix
        "py_fastapi",     # repo_id
        "ts_vite",        # repo_id
        "go_chi",         # repo_id
        "kimi",           # model_family (private-ish, but check)
    )
    # Note: "kimi" appears in route_features? No. model_family is not
    # emitted in D2b. Let's check no task_id/repo_id leaks.
    checks.append(
        _check(
            "d2b_no_record_ids_emitted",
            "c1-selftest-" not in d2b_blob
            and "py_fastapi" not in d2b_blob
            and "ts_vite" not in d2b_blob
            and "go_chi" not in d2b_blob,
        )
    )

    # --- Requirement 5: Small-cell suppression works. ---
    # With k_min=3 and 6 synthetic records, the crosstab has cells with
    # count < 3, so small_cells_suppressed should be True.
    checks.append(
        _check(
            "d2b_small_cell_suppression_applied",
            d2b["small_cells_suppressed"] is True,
        )
    )
    checks.append(
        _check(
            "d2b_suppressed_cells_omitted_from_crosstab",
            # Suppressed cells are NOT in the crosstab (omitted).
            all(count >= K_MIN_SELF_TEST
                for count in d2b["proxy_e_s_band_crosstab"].values()),
        )
    )
    # Test with k_min=1 (no suppression): all cells kept.
    d2b_nosuppress = calibrate_private_proxy(
        records, input_path=None, limit=0, k_min=1
    )
    checks.append(
        _check(
            "d2b_no_suppression_when_kmin_1",
            d2b_nosuppress["small_cells_suppressed"] is False,
        )
    )

    # --- Requirement 6: Forbidden scanner rejects all leak categories. ---
    def _has_cat(obj: Any, cat: str) -> bool:
        return any(v["category"] == cat for v in _scan_forbidden(obj))

    checks.append(
        _check(
            "scanner_rejects_task_id_key",
            _has_cat({"task_id": "abc"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_repo_id_key",
            _has_cat({"repo_id": "abc"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_repo_key",
            _has_cat({"repo": "abc"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_path_key",
            _has_cat({"path": "x"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_span_key",
            _has_cat({"span": "x"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_line_range_key",
            _has_cat({"line_range": "x"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_content_sha_key",
            _has_cat({"content_sha": "abc"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_snippet_key",
            _has_cat({"snippet": "abc"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_candidate_text_key",
            _has_cat({"candidate_text": "abc"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_query_key",
            _has_cat({"query": "abc"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_label_key",
            _has_cat({"label": "abc"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_qrels_key",
            _has_cat({"qrels": "abc"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_64_hex_digest_value",
            _has_cat({"x": "a" * 64}, "hex_digest_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_40_hex_digest_value",
            _has_cat({"x": "f" * 40}, "hex_digest_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_32_hex_digest_value",
            _has_cat({"x": "0123456789abcdef0123456789abcdef"}, "hex_digest_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_path_like_value",
            _has_cat({"x": "src/foo.py"}, "path_like_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_leading_slash_path_value",
            _has_cat({"x": "/a/b.py"}, "path_like_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_jsonl_path_value",
            _has_cat({"x": "/private/foo.jsonl"}, "path_like_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_line_range_value",
            _has_cat({"x": "12-34"}, "line_range_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_colon_line_range_value",
            _has_cat({"x": "12:34"}, "line_range_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_multiline_value",
            _has_cat({"x": "line one\nline two"}, "multiline_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_url_value",
            _has_cat({"x": "https://example.com/x"}, "url_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_raw_json_fragment",
            _has_cat({"x": '{"repo": "x"}'}, "raw_json_fragment"),
        )
    )
    # Pure-digit count strings must NOT be flagged.
    checks.append(
        _check(
            "scanner_allows_pure_digit_count_string",
            not _scan_forbidden({"x": "10"}),
        )
    )
    # Generic aggregate reason_code strings are allowed.
    checks.append(
        _check(
            "scanner_allows_aggregate_reason_code_string",
            not _scan_forbidden({"reason_code_counts": {"proxy_e_high": 1}}),
        )
    )

    # --- Requirement 7: Local input path never serialized. ---
    # calibrate_private_proxy received input_path=Path("/private/foo.jsonl")
    # but the D2b artifact must NOT contain the path or its basename.
    checks.append(
        _check(
            "d2b_local_input_path_not_serialized",
            "/private/foo.jsonl" not in d2b_blob,
        )
    )
    checks.append(
        _check(
            "d2b_local_input_basename_not_serialized",
            "foo.jsonl" not in d2b_blob,
        )
    )
    # Also verify no file size / mtime fields, and no standalone
    # "input_path" key (the local_input_path_emitted field is a boolean
    # flag, not a path value; check for a quoted JSON key instead).
    checks.append(
        _check(
            "d2b_no_input_size_or_mtime_fields",
            "input_file_size" not in d2b_blob
            and "input_file_mtime" not in d2b_blob
            and '"input_path"' not in d2b_blob
            and '"input_basename"' not in d2b_blob,
        )
    )

    # --- Requirement 8: Fail-closed generation on scanner leak. ---
    raised = False
    try:
        _enforce_no_forbidden(
            {"path": "src/foo.py", "content_sha": "a" * 64}
        )
    except SystemExit:
        raised = True
    checks.append(
        _check("fail_closed_generation_raises_on_leak", raised)
    )

    no_raise = True
    try:
        _enforce_no_forbidden(d2a)
    except SystemExit:
        no_raise = False
    checks.append(
        _check("fail_closed_clean_d2a_report_does_not_raise", no_raise)
    )

    no_raise_b = True
    try:
        _enforce_no_forbidden(d2b)
    except SystemExit:
        no_raise_b = False
    checks.append(
        _check("fail_closed_clean_d2b_report_does_not_raise", no_raise_b)
    )

    # --- Requirement 9: No-claim flags false. ---
    checks.append(
        _check(
            "no_claim_flags_all_false",
            all(v is False for v in NO_CLAIM_FLAGS.values()),
        )
    )
    checks.append(
        _check(
            "safety_flags_scaffold_only",
            SAFETY_FLAGS["aggregate_only_public_artifact"] is True
            and SAFETY_FLAGS["diagnostic_only"] is True
            and SAFETY_FLAGS["not_evidence"] is True
            and SAFETY_FLAGS["runtime_behavior_changed"] is False
            and SAFETY_FLAGS["retriever_changed"] is False
            and SAFETY_FLAGS["pack_builder_changed"] is False
            and SAFETY_FLAGS["model_calls_changed"] is False
            and SAFETY_FLAGS["backend_changed"] is False
            and SAFETY_FLAGS["default_policy_changed"] is False
            and SAFETY_FLAGS["candidate_text_emitted"] is False
            and SAFETY_FLAGS["paths_or_spans_emitted"] is False
            and SAFETY_FLAGS["content_sha_emitted"] is False
            and SAFETY_FLAGS["row_level_hashes_emitted"] is False
            and SAFETY_FLAGS["per_candidate_rows_emitted"] is False,
        )
    )

    # --- Additional: D2a forbidden scan clean. ---
    checks.append(
        _check(
            "d2a_forbidden_scan_clean",
            d2a["forbidden_scan"]["status"] == "pass"
            and d2a["forbidden_scan"]["violations_count"] == 0,
        )
    )
    checks.append(
        _check(
            "d2b_forbidden_scan_clean",
            d2b["forbidden_scan"]["status"] == "pass"
            and d2b["forbidden_scan"]["violations_count"] == 0,
        )
    )

    # --- Additional: D2a public aggregate mappability booleans. ---
    checks.append(
        _check(
            "d2a_public_aggregates_no_candidate_level_proxy_fields",
            d2a["public_aggregates_have_candidate_level_proxy_fields"] is False,
        )
    )
    checks.append(
        _check(
            "d2a_private_input_required_for_proxy_calibration",
            d2a["private_input_required_for_proxy_calibration"] is True,
        )
    )

    # --- Additional: CLI guard for --input without --allow-private-records. ---
    err_no_allow = _validate_cli_args(
        allow_private_records=False,
        input_path=Path("/private/foo.jsonl"),
        out_path=None,
        limit=0,
    )
    checks.append(
        _check(
            "cli_input_without_allow_private_records_rejected",
            err_no_allow is not None,
        )
    )
    err_allow_no_input = _validate_cli_args(
        allow_private_records=True,
        input_path=None,
        out_path=Path("/tmp/d2b.json"),
        limit=0,
    )
    checks.append(
        _check(
            "cli_allow_private_records_without_input_rejected",
            err_allow_no_input is not None,
        )
    )
    err_private_no_out = _validate_cli_args(
        allow_private_records=True,
        input_path=Path("/private/foo.jsonl"),
        out_path=None,
        limit=0,
    )
    checks.append(
        _check(
            "cli_allow_private_records_without_explicit_out_rejected",
            err_private_no_out is not None,
        )
    )
    err_private_committed_out = _validate_cli_args(
        allow_private_records=True,
        input_path=Path("/private/foo.jsonl"),
        out_path=DEFAULT_OUT,
        limit=0,
    )
    checks.append(
        _check(
            "cli_private_records_committed_out_rejected",
            err_private_committed_out is not None,
        )
    )
    err_private_tmp_out = _validate_cli_args(
        allow_private_records=True,
        input_path=Path("/private/foo.jsonl"),
        out_path=Path("/tmp/d2b.json"),
        limit=0,
    )
    checks.append(
        _check(
            "cli_private_records_tmp_out_allowed",
            err_private_tmp_out is None,
        )
    )
    sensitive_path = Path("/private/sensitive-name.jsonl")
    checks.append(
        _check(
            "cli_private_load_error_message_suppresses_path",
            str(sensitive_path) not in PRIVATE_LOAD_ERROR_MESSAGE
            and sensitive_path.name not in PRIVATE_LOAD_ERROR_MESSAGE,
        )
    )

    # --- Additional: proxy classification correctness. ---
    # E high -> proxy_primary_evidence.
    e_high = {"span_f0_5_high": True, "added_gold_span_pos": True,
              "low_primary_fpr": True}
    s_low = {"candidate_support_exists": False, "local_anchor": False,
             "rrf_backed_by_anchor": False, "symbol_regex_agree": False,
             "dense_support_present": False}
    b_ehigh, _ = classify_proxy(e_high, s_low)
    checks.append(
        _check(
            "proxy_e_high_is_proxy_primary_evidence",
            b_ehigh == PROXY_BUCKET_PRIMARY_EVIDENCE,
        )
    )
    # S high, E low -> proxy_dependency_support.
    e_low = {"span_f0_5_high": False, "added_gold_span_pos": False,
             "low_primary_fpr": False}
    s_high = {"candidate_support_exists": True, "local_anchor": True,
              "rrf_backed_by_anchor": True, "symbol_regex_agree": True,
              "dense_support_present": True}
    b_shigh, _ = classify_proxy(e_low, s_high)
    checks.append(
        _check(
            "proxy_s_high_e_low_is_proxy_dependency_support",
            b_shigh == PROXY_BUCKET_DEPENDENCY_SUPPORT,
        )
    )
    # E high beats S high.
    b_both_high, _ = classify_proxy(e_high, s_high)
    checks.append(
        _check(
            "proxy_e_high_beats_s_high",
            b_both_high == PROXY_BUCKET_PRIMARY_EVIDENCE,
        )
    )
    # Weak nonzero -> proxy_weak_candidates.
    e_weak = {"span_f0_5_high": False, "added_gold_span_pos": True,
              "low_primary_fpr": False}
    s_weak = {"candidate_support_exists": True, "local_anchor": False,
              "rrf_backed_by_anchor": False, "symbol_regex_agree": False,
              "dense_support_present": False}
    b_weak, _ = classify_proxy(e_weak, s_weak)
    checks.append(
        _check(
            "proxy_weak_nonzero_is_proxy_weak_candidates",
            b_weak == PROXY_BUCKET_WEAK_CANDIDATES,
        )
    )
    # No signals -> proxy_abstained.
    e_none = {"span_f0_5_high": False, "added_gold_span_pos": False,
              "low_primary_fpr": False}
    s_none = {"candidate_support_exists": False, "local_anchor": False,
              "rrf_backed_by_anchor": False, "symbol_regex_agree": False,
              "dense_support_present": False}
    b_none, _ = classify_proxy(e_none, s_none)
    checks.append(
        _check(
            "proxy_no_signals_is_proxy_abstained",
            b_none == PROXY_BUCKET_ABSTAINED,
        )
    )

    # --- Additional: D2b with synthetic records produces expected bucket
    # distribution. The C1 synthetic payload has 6 records, all with
    # candidate_support_exists=True, local_anchor=True,
    # rrf_backed_by_anchor=True (proxy_s_score=3, high). Records with
    # has_gold=True (idx 0,1,3,4) have added_gold_span>0 and primary_fpr<0.3
    # (proxy_e_score=2, high) -> proxy_primary_evidence. Records with
    # has_gold=False (idx 2,5) have proxy_e_score=1 (weak) ->
    # proxy_dependency_support. ---
    checks.append(
        _check(
            "d2b_synthetic_proxy_primary_evidence_count_4",
            d2b["proxy_bucket_counts"][PROXY_BUCKET_PRIMARY_EVIDENCE] == 4,
        )
    )
    checks.append(
        _check(
            "d2b_synthetic_proxy_dependency_support_count_2",
            d2b["proxy_bucket_counts"][PROXY_BUCKET_DEPENDENCY_SUPPORT] == 2,
        )
    )
    checks.append(
        _check(
            "d2b_synthetic_proxy_unmappable_count_0",
            d2b["proxy_bucket_counts"][PROXY_BUCKET_UNMAPPABLE] == 0,
        )
    )
    checks.append(
        _check(
            "d2b_synthetic_proxy_e_band_high_4",
            d2b["proxy_e_band_counts"][BAND_HIGH] == 4,
        )
    )
    checks.append(
        _check(
            "d2b_synthetic_proxy_e_band_weak_2",
            d2b["proxy_e_band_counts"][BAND_WEAK] == 2,
        )
    )
    checks.append(
        _check(
            "d2b_synthetic_proxy_s_band_high_6",
            d2b["proxy_s_band_counts"][BAND_HIGH] == 6,
        )
    )

    # --- Additional: limit caps records. ---
    d2b_limited = calibrate_private_proxy(
        records, input_path=None, limit=2, k_min=1
    )
    checks.append(
        _check(
            "d2b_limit_caps_record_count",
            d2b_limited["private_record_count"] == 2,
        )
    )

    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


# ---------------------------------------------------------------------------
# CLI argument validation
# ---------------------------------------------------------------------------


def _validate_cli_args(
    *,
    allow_private_records: bool,
    input_path: Path | None,
    out_path: Path | None,
    limit: int,
) -> str | None:
    """Validate CLI argument combinations for D2a vs D2b mode.

    Returns an error message string if invalid, or None if valid.

    * ``--input`` without ``--allow-private-records`` -> error (exit
      non-zero).
    * ``--allow-private-records`` without ``--input`` -> error (exit
      non-zero).
    * Both set -> D2b mode (valid).
    * Neither set -> D2a default mode (valid).
    """
    if input_path is not None and not allow_private_records:
        return (
            "--input requires --allow-private-records; refusing to read "
            "private records without explicit opt-in"
        )
    if allow_private_records and input_path is None:
        return (
            "--allow-private-records requires --input; no private input "
            "path provided"
        )
    if allow_private_records:
        if out_path is None:
            return (
                "--allow-private-records requires explicit --out under /tmp; "
                "refusing to use the committed artifact path"
            )
        try:
            resolved_out = out_path.resolve(strict=False)
            resolved_tmp = Path("/tmp").resolve(strict=False)
            resolved_out.relative_to(resolved_tmp)
        except (OSError, ValueError):
            return (
                "--allow-private-records requires --out under /tmp; "
                "refusing to write private-mode output elsewhere"
            )
    if limit < 0:
        return "--limit must be >= 0"
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(
        description="D2 dual-rubric aggregate calibration (proxy mappability)."
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="run deterministic self-test groups and exit (no artifact written)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "output artifact JSON path (D2a default: committed artifact; "
            "D2b requires explicit /tmp path)"
        ),
    )
    ap.add_argument(
        "--allow-private-records",
        action="store_true",
        help=(
            "opt-in D2b private proxy calibration smoke; requires --input; "
            "output should go to /tmp only (NOT committed)"
        ),
    )
    ap.add_argument(
        "--input",
        type=Path,
        default=None,
        help=(
            "path to a private P21 v1 records JSON file (D2b only; requires "
            "--allow-private-records); never serialized into any artifact"
        ),
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        help="cap on number of private records processed (0 = no cap)",
    )
    ap.add_argument(
        "--k-min",
        type=int,
        default=K_MIN_DEFAULT,
        help=f"small-cell suppression threshold (default: {K_MIN_DEFAULT})",
    )
    args = ap.parse_args()

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

    # Validate D2a vs D2b argument combinations.
    err = _validate_cli_args(
        allow_private_records=args.allow_private_records,
        input_path=args.input,
        out_path=args.out,
        limit=args.limit,
    )
    if err is not None:
        print(f"error: {err}", file=sys.stderr)
        sys.exit(2)

    if args.allow_private_records and args.input is not None:
        # D2b: private proxy calibration smoke (NOT committed; /tmp only).
        # Load private records using the C1 adapter (lazy import).
        import c1_private_records as c1
        input_path = args.input
        if not input_path.exists():
            print(
                f"error: --input path not found (path never serialized)",
                file=sys.stderr,
            )
            sys.exit(2)
        try:
            records, _meta = c1.load_private_records(input_path)
        except (c1.PrivateRecordError, FileNotFoundError, ValueError):
            print(PRIVATE_LOAD_ERROR_MESSAGE, file=sys.stderr)
            sys.exit(2)
        report = calibrate_private_proxy(
            records,
            input_path=input_path,
            limit=args.limit,
            k_min=args.k_min,
        )
        # Fail-closed guard immediately before writing.
        _enforce_no_forbidden(report)
        assert args.out is not None
        _write_json(args.out, report)
        print(
            "wrote D2b private proxy smoke to /tmp output "
            f"(forbidden_scan={report['forbidden_scan']['status']}, "
            f"private_record_count={report['private_record_count']}, "
            f"small_cells_suppressed={report['small_cells_suppressed']}) "
            f"[NOT committed; /tmp only]"
        )
        return

    # D2a: default public aggregate mappability inventory (committed).
    out_path = args.out if args.out is not None else DEFAULT_OUT
    checks, all_passed = run_self_test_checks()
    report = build_d2a_report(checks, all_passed)
    # Strict fail-closed guard immediately before writing the JSON artifact.
    _enforce_no_forbidden(report)
    _write_json(out_path, report)
    print(
        f"wrote {out_path} "
        f"(forbidden_scan={report['forbidden_scan']['status']}, "
        f"self_test_passed={report['self_test_passed']}, "
        f"status={report['status']})"
    )
    if report["self_test_passed"] is not True:
        raise SystemExit("self-test failed; refusing successful artifact exit")


if __name__ == "__main__":
    main()
