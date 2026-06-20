#!/usr/bin/env python3
"""D1 Dual-Rubric Relevance — eval-layer scaffold only.

This module implements the **D1 dual-rubric relevance** diagnostic
scaffold. It separates candidate relevance into two deterministic
small-integer signals:

* **E-score**: semantic / direct-answer evidence (semantic direct match,
  answer-bearing span).
* **S-score**: dependency / support-structure evidence (import support,
  dependency-link support, caller support).

Citation validity, stale source/hash, uncited source, and explicit
no-evidence are **abstention gates** that fire *before* E/S bucket
assignment (per oracle review: invalid/stale citation must force
abstention, and primary evidence must require citation validity).

Claim boundary (binding):

* This is **eval/diagnostic scaffold only**. It is NOT a runtime change,
  NOT a retriever/pack/model/backend/default-policy change, and NOT an
  EvidenceCore semantic change.
* Claim level emitted: ``eval_layer_rubric_scaffold_only``.
* Rubric version: ``d1_dual_rubric_v0``.
* D1 uses **deterministic synthetic/source-backed fixtures only**. It
  does NOT read real P21/private records (deferred to a later D2
  calibration phase). Synthetic self-test fixtures confer NO empirical
  support, NO benchmark result, NO downstream agent value, NO
  runtime-clean general algorithm claim, NO OOD temporal support, and NO
  QuIVer systems support.

Public-artifact contract (binding):

* aggregate-only public output;
* NEVER emit task IDs, repo IDs/names, paths/spans/snippets, line/byte
  ranges, content hashes, raw candidate text, prompts/responses, raw
  private records, labels/qrels, or row-level derived hashes;
* a strict forbidden-output scanner runs fail-closed before the JSON
  artifact is written;
* no-claim flags all false; ``aggregate_only_public_artifact=true``,
  ``not_evidence=true``, ``diagnostic_only=true``.

Run::

    python3 -m py_compile eval/d1_dual_rubric_relevance.py
    python3 eval/d1_dual_rubric_relevance.py --self-test
    python3 eval/d1_dual_rubric_relevance.py \
        --out artifacts/d1_dual_rubric_relevance/\\
d1_dual_rubric_relevance_report.json
    python3 scripts/validate_docs_i18n.py
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

SCHEMA_VERSION = "d1_dual_rubric_relevance_report.v0"
GENERATED_BY = "eval/d1_dual_rubric_relevance.py"
CLAIM_LEVEL = "eval_layer_rubric_scaffold_only"
RUBRIC_VERSION = "d1_dual_rubric_v0"
TARGET_STATUS = "scaffold_only_self_test_passed"

DEFAULT_OUT = Path(
    "artifacts/d1_dual_rubric_relevance/"
    "d1_dual_rubric_relevance_report.json"
)

# ---------------------------------------------------------------------------
# Rubric semantics
# ---------------------------------------------------------------------------

# E-score signals (semantic / direct-answer evidence). Each contributes 1.
E_SIGNAL_NAMES: tuple[str, ...] = (
    "semantic_direct_match",
    "answer_bearing_span",
)
E_SCORE_MAX = len(E_SIGNAL_NAMES)  # 2

# S-score signals (dependency / support-structure evidence). Each +1.
S_SIGNAL_NAMES: tuple[str, ...] = (
    "import_support",
    "dependency_link_support",
    "caller_support",
)
S_SCORE_MAX = len(S_SIGNAL_NAMES)  # 3

# Thresholds: deterministic small-integer bands.
E_HIGH_MIN = 2
S_HIGH_MIN = 2
WEAK_MIN = 1

# Canonical buckets (in fail-closed classification order these are the
# possible assignment targets).
BUCKET_PRIMARY_EVIDENCE = "primary_evidence"
BUCKET_DEPENDENCY_SUPPORT = "dependency_support"
BUCKET_WEAK_CANDIDATES = "weak_candidates"
BUCKET_ABSTAINED = "abstained"

BUCKET_NAMES: tuple[str, ...] = (
    BUCKET_PRIMARY_EVIDENCE,
    BUCKET_DEPENDENCY_SUPPORT,
    BUCKET_WEAK_CANDIDATES,
    BUCKET_ABSTAINED,
)

# Legacy alias map (kept for backward compatibility with the existing
# expected-behavior enum used in fixtures/docs).
LEGACY_BUCKET_ALIASES: dict[str, str] = {
    BUCKET_DEPENDENCY_SUPPORT: "supporting_only",
    BUCKET_ABSTAINED: "abstain",
}

# Classification order (fail-closed). Step codes are aggregate reason
# labels only, never row-level data.
CLASSIFICATION_ORDER: tuple[str, ...] = (
    "abstain_gate_invalid_citation_stale_uncited_no_evidence",
    "primary_evidence_e_high_citation_valid",
    "dependency_support_s_high_e_below_high",
    "weak_candidates_nonzero_e_or_s",
    "abstain_else_no_evidence",
)

# Reason codes emitted by the classifier (aggregate labels only).
REASON_INVALID_CITATION = "invalid_citation"
REASON_STALE_SOURCE_OR_HASH = "stale_source_or_hash"
REASON_UNCITED_NO_EVIDENCE = "uncited_no_evidence"
REASON_EXPLICIT_NO_EVIDENCE = "explicit_no_evidence"
REASON_E_HIGH_CITATION_VALID = "e_high_citation_valid"
REASON_S_HIGH_E_BELOW_HIGH = "s_high_e_below_high"
REASON_WEAK_NONZERO_E_OR_S = "weak_nonzero_e_or_s"
REASON_NO_EVIDENCE = "no_evidence"

# Score bands.
BAND_NONE = "none"
BAND_WEAK = "weak"
BAND_HIGH = "high"

# ---------------------------------------------------------------------------
# No-claim / safety flags (all the change/leak booleans). All must be the
# scaffold-only values shown below.
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
    "raw_private_records_read": False,
    "raw_private_records_persisted": False,
    "row_level_hashes_emitted": False,
    "per_candidate_rows_emitted": False,
}

# ---------------------------------------------------------------------------
# Deterministic synthetic / source-backed fixtures (in-memory only).
#
# These fixtures are NEVER serialized into the public artifact except as
# aggregate counts. They confer NO empirical support. They do NOT read real
# P21/private records. Each fixture carries only synthetic boolean signals
# and an expected bucket used by the self-test.
# ---------------------------------------------------------------------------

# Signal keys are deliberately distinct from any forbidden key name.
_E = "e_signals"
_S = "s_signals"
_CV = "citation_valid"
_SS = "stale_source"
_UC = "uncited"
_NE = "explicit_no_evidence"
_XB = "expected_bucket"


def _e(t_sem: bool, t_ans: bool) -> dict[str, bool]:
    return {E_SIGNAL_NAMES[0]: t_sem, E_SIGNAL_NAMES[1]: t_ans}


def _s(a: bool, b: bool, c: bool) -> dict[str, bool]:
    return {
        S_SIGNAL_NAMES[0]: a,
        S_SIGNAL_NAMES[1]: b,
        S_SIGNAL_NAMES[2]: c,
    }


FIXTURES: list[dict[str, Any]] = [
    {
        _E: _e(True, True), _S: _s(False, False, False),
        _CV: True, _SS: False, _UC: False, _NE: False,
        _XB: BUCKET_PRIMARY_EVIDENCE,
    },
    {
        _E: _e(False, False), _S: _s(True, True, False),
        _CV: True, _SS: False, _UC: False, _NE: False,
        _XB: BUCKET_DEPENDENCY_SUPPORT,
    },
    {
        _E: _e(True, False), _S: _s(False, False, False),
        _CV: True, _SS: False, _UC: False, _NE: False,
        _XB: BUCKET_WEAK_CANDIDATES,
    },
    {
        _E: _e(False, False), _S: _s(True, False, False),
        _CV: True, _SS: False, _UC: False, _NE: False,
        _XB: BUCKET_WEAK_CANDIDATES,
    },
    {
        # E-high but INVALID citation -> must abstain (fail-closed).
        _E: _e(True, True), _S: _s(False, False, False),
        _CV: False, _SS: False, _UC: False, _NE: False,
        _XB: BUCKET_ABSTAINED,
    },
    {
        # Stale source/hash -> abstain before E/S bucket assignment.
        _E: _e(True, True), _S: _s(False, False, False),
        _CV: True, _SS: True, _UC: False, _NE: False,
        _XB: BUCKET_ABSTAINED,
    },
    {
        # Uncited / no citation -> abstain.
        _E: _e(True, True), _S: _s(False, False, False),
        _CV: True, _SS: False, _UC: True, _NE: False,
        _XB: BUCKET_ABSTAINED,
    },
    {
        # Explicit no-evidence -> abstain.
        _E: _e(True, True), _S: _s(False, False, False),
        _CV: True, _SS: False, _UC: False, _NE: True,
        _XB: BUCKET_ABSTAINED,
    },
    {
        # E+S both high, citation valid -> primary (E-high beats S-high).
        _E: _e(True, True), _S: _s(True, True, True),
        _CV: True, _SS: False, _UC: False, _NE: False,
        _XB: BUCKET_PRIMARY_EVIDENCE,
    },
    {
        # No signals at all, valid citation -> abstain (no evidence).
        _E: _e(False, False), _S: _s(False, False, False),
        _CV: True, _SS: False, _UC: False, _NE: False,
        _XB: BUCKET_ABSTAINED,
    },
]


# ---------------------------------------------------------------------------
# Scoring + classification
# ---------------------------------------------------------------------------


def compute_e_score(signals: dict[str, bool]) -> int:
    """E-score = count of true E signals (range 0..E_SCORE_MAX)."""
    return sum(1 for v in signals.values() if v)


def compute_s_score(signals: dict[str, bool]) -> int:
    """S-score = count of true S signals (range 0..S_SCORE_MAX)."""
    return sum(1 for v in signals.values() if v)


def score_band(score: int, high_min: int) -> str:
    """Map a raw score to a band label."""
    if score >= high_min:
        return BAND_HIGH
    if score >= WEAK_MIN:
        return BAND_WEAK
    return BAND_NONE


def classify(fixture: dict[str, Any]) -> tuple[str, str]:
    """Classify a fixture into a bucket + reason code (fail-closed order).

    Order:
      1. invalid citation / stale source/hash / uncited / explicit
         no-evidence -> abstained.
      2. E high and citation valid -> primary_evidence.
      3. S high and E below high -> dependency_support.
      4. weak nonzero E or S -> weak_candidates.
      5. else -> abstained.
    """
    citation_valid = bool(fixture[_CV])
    stale_source = bool(fixture[_SS])
    uncited = bool(fixture[_UC])
    explicit_no_evidence = bool(fixture[_NE])

    # Step 1: abstention gates (fail-closed before E/S bucket assignment).
    if not citation_valid:
        return BUCKET_ABSTAINED, REASON_INVALID_CITATION
    if stale_source:
        return BUCKET_ABSTAINED, REASON_STALE_SOURCE_OR_HASH
    if uncited:
        return BUCKET_ABSTAINED, REASON_UNCITED_NO_EVIDENCE
    if explicit_no_evidence:
        return BUCKET_ABSTAINED, REASON_EXPLICIT_NO_EVIDENCE

    e = compute_e_score(fixture[_E])
    s = compute_s_score(fixture[_S])

    # Step 2: E high and citation valid -> primary_evidence.
    if e >= E_HIGH_MIN:
        return BUCKET_PRIMARY_EVIDENCE, REASON_E_HIGH_CITATION_VALID
    # Step 3: S high and E below high -> dependency_support.
    if s >= S_HIGH_MIN and e < E_HIGH_MIN:
        return BUCKET_DEPENDENCY_SUPPORT, REASON_S_HIGH_E_BELOW_HIGH
    # Step 4: weak nonzero E or S -> weak_candidates.
    if e >= WEAK_MIN or s >= WEAK_MIN:
        return BUCKET_WEAK_CANDIDATES, REASON_WEAK_NONZERO_E_OR_S
    # Step 5: else -> abstained.
    return BUCKET_ABSTAINED, REASON_NO_EVIDENCE


# ---------------------------------------------------------------------------
# Forbidden-output scanner (D1 scaffold-specific, fail-closed)
# ---------------------------------------------------------------------------

# Sensitive KEY names that must NEVER appear as dict keys anywhere in a
# public JSON output. These are row-level / candidate-leak field names.
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
        "target_status",
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
    r"yaml|yml|txt|sh|rb|php|kt|swift|patch|diff|csv|parquet"
)
# Path-like strings, with OR without a leading slash (e.g. "src/foo.py",
# "foo.py", "/a/b.py"). Matches "src/foo.py" and "eval/x.py".
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
    task_id/repo_id/repo/label/qrels/gold/prompt/response/etc.) anywhere,
    and rejects value patterns: URLs, 32/40/64-char hex digests,
    secret-like strings, path-like strings (``src/foo.py``), multiline
    strings, raw JSON fragments, and raw line-range strings (``12-34``).

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


# ---------------------------------------------------------------------------
# Self-test checks (pure, no I/O; operate on in-memory fixtures/poisons)
# ---------------------------------------------------------------------------


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return {"check": name, "passed": bool(ok)}


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all D1 self-test groups. Returns (checks, all_passed)."""
    checks: list[dict[str, Any]] = []

    # Classify every fixture and assert the expected bucket.
    classified = [classify(f) for f in FIXTURES]
    expected_buckets = [f[_XB] for f in FIXTURES]
    actual_buckets = [c[0] for c in classified]

    checks.append(
        _check(
            "classify_e_high_valid_is_primary",
            classified[0] == (BUCKET_PRIMARY_EVIDENCE, REASON_E_HIGH_CITATION_VALID),
        )
    )
    checks.append(
        _check(
            "classify_s_high_e_low_is_dependency_support",
            classified[1] == (BUCKET_DEPENDENCY_SUPPORT, REASON_S_HIGH_E_BELOW_HIGH),
        )
    )
    checks.append(
        _check(
            "classify_weak_e_is_weak_candidates",
            classified[2] == (BUCKET_WEAK_CANDIDATES, REASON_WEAK_NONZERO_E_OR_S),
        )
    )
    checks.append(
        _check(
            "classify_weak_s_is_weak_candidates",
            classified[3] == (BUCKET_WEAK_CANDIDATES, REASON_WEAK_NONZERO_E_OR_S),
        )
    )
    checks.append(
        _check(
            "classify_e_high_invalid_citation_abstains",
            classified[4] == (BUCKET_ABSTAINED, REASON_INVALID_CITATION),
        )
    )
    checks.append(
        _check(
            "classify_stale_source_abstains",
            classified[5] == (BUCKET_ABSTAINED, REASON_STALE_SOURCE_OR_HASH),
        )
    )
    checks.append(
        _check(
            "classify_uncited_abstains",
            classified[6] == (BUCKET_ABSTAINED, REASON_UNCITED_NO_EVIDENCE),
        )
    )
    checks.append(
        _check(
            "classify_explicit_no_evidence_abstains",
            classified[7] == (BUCKET_ABSTAINED, REASON_EXPLICIT_NO_EVIDENCE),
        )
    )
    checks.append(
        _check(
            "classify_e_plus_s_high_is_primary_e_high_beats_s_high",
            classified[8] == (BUCKET_PRIMARY_EVIDENCE, REASON_E_HIGH_CITATION_VALID),
        )
    )
    checks.append(
        _check(
            "classify_no_evidence_abstains",
            classified[9] == (BUCKET_ABSTAINED, REASON_NO_EVIDENCE),
        )
    )
    checks.append(
        _check(
            "all_fixtures_match_expected_bucket",
            actual_buckets == expected_buckets,
        )
    )

    # Aggregate counts.
    fixture_count = len(FIXTURES)
    candidate_count = fixture_count
    bucket_counts: dict[str, int] = {b: 0 for b in BUCKET_NAMES}
    e_band_counts: dict[str, int] = {BAND_NONE: 0, BAND_WEAK: 0, BAND_HIGH: 0}
    s_band_counts: dict[str, int] = {BAND_NONE: 0, BAND_WEAK: 0, BAND_HIGH: 0}
    reason_counts: dict[str, int] = {}
    for f, (bucket, reason) in zip(FIXTURES, classified):
        bucket_counts[bucket] += 1
        e = compute_e_score(f[_E])
        s = compute_s_score(f[_S])
        e_band_counts[score_band(e, E_HIGH_MIN)] += 1
        s_band_counts[score_band(s, S_HIGH_MIN)] += 1
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    expected_bucket_counts = {
        BUCKET_PRIMARY_EVIDENCE: 2,
        BUCKET_DEPENDENCY_SUPPORT: 1,
        BUCKET_WEAK_CANDIDATES: 2,
        BUCKET_ABSTAINED: 5,
    }
    checks.append(
        _check(
            "bucket_counts_match_expected",
            bucket_counts == expected_bucket_counts,
        )
    )
    checks.append(_check("fixture_count_is_10", fixture_count == 10))
    checks.append(_check("candidate_count_is_10", candidate_count == 10))
    checks.append(
        _check(
            "e_score_band_counts_match",
            e_band_counts
            == {BAND_NONE: 3, BAND_WEAK: 1, BAND_HIGH: 6},
        )
    )
    checks.append(
        _check(
            "s_score_band_counts_match",
            s_band_counts
            == {BAND_NONE: 7, BAND_WEAK: 1, BAND_HIGH: 2},
        )
    )
    checks.append(
        _check(
            "reason_code_counts_total_matches_candidate_count",
            sum(reason_counts.values()) == candidate_count,
        )
    )
    expected_reason_counts = {
        REASON_E_HIGH_CITATION_VALID: 2,
        REASON_S_HIGH_E_BELOW_HIGH: 1,
        REASON_WEAK_NONZERO_E_OR_S: 2,
        REASON_INVALID_CITATION: 1,
        REASON_STALE_SOURCE_OR_HASH: 1,
        REASON_UNCITED_NO_EVIDENCE: 1,
        REASON_EXPLICIT_NO_EVIDENCE: 1,
        REASON_NO_EVIDENCE: 1,
    }
    checks.append(
        _check(
            "reason_code_counts_match_expected",
            reason_counts == expected_reason_counts,
        )
    )

    # Thresholds + aliases + classification order.
    checks.append(
        _check(
            "thresholds_correct",
            E_HIGH_MIN == 2 and S_HIGH_MIN == 2 and WEAK_MIN == 1,
        )
    )
    checks.append(
        _check(
            "legacy_alias_map_correct",
            LEGACY_BUCKET_ALIASES
            == {
                BUCKET_DEPENDENCY_SUPPORT: "supporting_only",
                BUCKET_ABSTAINED: "abstain",
            },
        )
    )
    checks.append(
        _check(
            "classification_order_e_high_beats_s_high",
            # Fixture 8 (E+S high) must be primary, not dependency_support.
            actual_buckets[8] == BUCKET_PRIMARY_EVIDENCE,
        )
    )

    # No-claim + safety flags.
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
            and SAFETY_FLAGS["raw_private_records_read"] is False
            and SAFETY_FLAGS["raw_private_records_persisted"] is False
            and SAFETY_FLAGS["row_level_hashes_emitted"] is False
            and SAFETY_FLAGS["per_candidate_rows_emitted"] is False,
        )
    )

    # Build a skeleton report (empty checks, no recursion into this
    # function) and scan it (must be clean). build_report() re-scans the
    # full report with the real checks list embedded before returning.
    skeleton = _build_report_core([], False)
    checks.append(
        _check(
            "forbidden_scan_clean_report_passes",
            skeleton["forbidden_scan"]["status"] == "pass"
            and skeleton["forbidden_scan"]["violations_count"] == 0,
        )
    )

    # --- Forbidden scanner injection tests (must FAIL the scan). ---
    def _has_cat(obj: Any, cat: str) -> bool:
        return any(v["category"] == cat for v in _scan_forbidden(obj))

    checks.append(
        _check(
            "forbidden_scan_rejects_path_key",
            _has_cat({"bucket_counts": {"primary_evidence": 2}, "path": "x"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_content_sha_key",
            _has_cat({"content_sha": "abc"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_query_key",
            _has_cat({"query": "abc"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_task_id_key",
            _has_cat({"task_id": "abc"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_repo_id_key",
            _has_cat({"repo_id": "abc"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_label_key",
            _has_cat({"label": "abc"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_qrels_key",
            _has_cat({"qrels": "abc"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_snippet_key",
            _has_cat({"snippet": "abc"}, "forbidden_key"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_64_hex_digest_value",
            _has_cat({"x": "a" * 64}, "hex_digest_value"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_40_hex_digest_value",
            _has_cat({"x": "f" * 40}, "hex_digest_value"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_32_hex_digest_value",
            _has_cat({"x": "0123456789abcdef0123456789abcdef"}, "hex_digest_value"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_path_like_value",
            _has_cat({"x": "src/foo.py"}, "path_like_value"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_leading_slash_path_value",
            _has_cat({"x": "/a/b.py"}, "path_like_value"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_line_range_value",
            _has_cat({"x": "12-34"}, "line_range_value"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_colon_line_range_value",
            _has_cat({"x": "12:34"}, "line_range_value"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_multiline_value",
            _has_cat({"x": "line one\nline two"}, "multiline_value"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_url_value",
            _has_cat({"x": "https://example.com/x"}, "url_value"),
        )
    )
    checks.append(
        _check(
            "forbidden_scan_rejects_raw_json_fragment",
            _has_cat({"x": '{"repo": "x"}'}, "raw_json_fragment"),
        )
    )
    # Pure-digit count strings must NOT be flagged as line ranges.
    checks.append(
        _check(
            "forbidden_scan_allows_pure_digit_count_string",
            not _scan_forbidden({"x": "10"}),
        )
    )
    # Generic aggregate reason_code strings are allowed (not row-like).
    checks.append(
        _check(
            "forbidden_scan_allows_aggregate_reason_code_string",
            not _scan_forbidden({"reason_code_counts": {"invalid_citation": 1}}),
        )
    )

    # --- Fail-closed generation tests. ---
    raised = False
    try:
        _enforce_no_forbidden({"path": "src/foo.py", "content_sha": "a" * 64})
    except SystemExit:
        raised = True
    checks.append(_check("fail_closed_generation_raises_on_leak", raised))

    no_raise = True
    try:
        _enforce_no_forbidden(skeleton)
    except SystemExit:
        no_raise = False
    checks.append(
        _check("fail_closed_clean_report_does_not_raise", no_raise)
    )

    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def _build_report_core(
    checks: list[dict[str, Any]], all_passed: bool
) -> dict[str, Any]:
    """Assemble the aggregate-only report payload from explicit checks.

    Computes the deterministic aggregates, embeds the supplied
    ``checks`` list, and runs the fail-closed forbidden scan. This is
    split out so ``run_self_test_checks`` can scan a skeleton payload
    (empty checks) without recursing through ``build_report``.
    """
    classified = [classify(f) for f in FIXTURES]

    bucket_counts: dict[str, int] = {b: 0 for b in BUCKET_NAMES}
    e_band_counts: dict[str, int] = {BAND_NONE: 0, BAND_WEAK: 0, BAND_HIGH: 0}
    s_band_counts: dict[str, int] = {BAND_NONE: 0, BAND_WEAK: 0, BAND_HIGH: 0}
    reason_counts: dict[str, int] = {}
    for f, (bucket, reason) in zip(FIXTURES, classified):
        bucket_counts[bucket] += 1
        e = compute_e_score(f[_E])
        s = compute_s_score(f[_S])
        e_band_counts[score_band(e, E_HIGH_MIN)] += 1
        s_band_counts[score_band(s, S_HIGH_MIN)] += 1
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "rubric_version": RUBRIC_VERSION,
        "status": TARGET_STATUS if all_passed else "self_test_failed",
        "thresholds": {
            "e_high_min": E_HIGH_MIN,
            "s_high_min": S_HIGH_MIN,
            "weak_min": WEAK_MIN,
            "e_score_max": E_SCORE_MAX,
            "s_score_max": S_SCORE_MAX,
        },
        "classification_order": list(CLASSIFICATION_ORDER),
        "bucket_names": list(BUCKET_NAMES),
        "legacy_bucket_aliases": dict(LEGACY_BUCKET_ALIASES),
        "fixture_count": len(FIXTURES),
        "candidate_count": len(FIXTURES),
        "bucket_counts": bucket_counts,
        "e_score_band_counts": e_band_counts,
        "s_score_band_counts": s_band_counts,
        "reason_code_counts": reason_counts,
        "self_test_checks": checks,
        "self_test_passed": all_passed,
        # No-claim + safety flags (flat, scaffold-only values).
        **NO_CLAIM_FLAGS,
        **SAFETY_FLAGS,
        "raw_private_records_read": False,
    }

    # Fail-closed forbidden scan before returning. The CLI runs
    # _enforce_no_forbidden again immediately before writing to disk.
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_leak"
    return report


def build_report() -> dict[str, Any]:
    """Assemble the aggregate-only public report (fail-closed scan).

    Runs the deterministic self-test checks and embeds their results,
    then assembles the full report payload (which re-scans itself).
    """
    checks, all_passed = run_self_test_checks()
    return _build_report_core(checks, all_passed)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(
        description="D1 dual-rubric relevance eval-layer scaffold."
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="run deterministic self-test groups and exit (no artifact written)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="output artifact JSON path",
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

    report = build_report()
    # Strict fail-closed guard immediately before writing the JSON artifact.
    _enforce_no_forbidden(report)
    _write_json(args.out, report)
    print(
        f"wrote {args.out} "
        f"(forbidden_scan={report['forbidden_scan']['status']}, "
        f"self_test_passed={report['self_test_passed']})"
    )
    if report["self_test_passed"] is not True:
        raise SystemExit("self-test failed; refusing successful artifact exit")


if __name__ == "__main__":
    main()
