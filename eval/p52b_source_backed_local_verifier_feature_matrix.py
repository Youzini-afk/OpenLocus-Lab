#!/usr/bin/env python3
"""P52B Source-Backed Local Verifier Feature Matrix.

P52B builds on P52A to compute deterministic, source-backed verifier feature
diagnostics from bounded local source reads.  It does not produce
Evidence/admission/pass-fail, does not call an LLM, does not make remote calls,
and does not construct prompts.  Gold spans and outcomes are used only inside
explicitly marked SCORE-phase diagnostics after feature extraction.

Hard constraints:
* No remote calls; `remote_calls_by_p52b=0`.
* No LLM calls; `llm_calls_by_p52b=0`.
* No prompt construction; `prompt_construction_by_p52b=false`.
* Source-feature buckets are diagnostics only; not Evidence.
* Materialized candidate is not Evidence; `materialized_candidate_not_evidence=true`.
* Public outputs are aggregate-only: no raw source, snippets, paths, spans,
  digests, task/candidate/repo identifiers, query text, or provider keys.
* Bounded local source reads; raw text is transient in memory.
* Gold/outcomes are used only in SCORE-phase diagnostics after feature 
  construction.
* Query-dependent and AST/parser features remain unavailable/null.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))
import p25_bucket_policy as p25
import p46_candidate_reach_cost_map as p46
import p49_contrastive_candidate_pack_scaffold as p49
import p52_metadata_local_verifier_scaffold as p52
import p52a_source_materialization_prerequisite as p52a

SCHEMA_VERSION = "p52b-source-backed-local-verifier-feature-matrix-v1"
GENERATED_BY = "eval/p52b_source_backed_local_verifier_feature_matrix.py"

DEFAULT_OUT = Path("artifacts/p52b_source_backed_local_verifier_feature_matrix/p52b_source_backed_local_verifier_feature_matrix_report.json")
DEFAULT_DOC = Path("docs/en/p52b-source-backed-local-verifier-feature-matrix.md")

MAX_SPAN_LINES = p52a.MAX_SPAN_LINES
MAX_LINE_LENGTH = p52a.MAX_LINE_LENGTH
MAX_TOTAL_BYTES_READ = p52a.MAX_TOTAL_BYTES_READ

# Source-feature bucket taxonomy.
SOURCE_FEATURE_BUCKETS = [
    "source_feature_low_risk",
    "source_feature_medium_risk",
    "source_feature_high_risk",
    "source_feature_unavailable",
]

# Heuristic regexes (line-prefix comment detection is reused from P52A).
ASSIGNMENT_RE = re.compile(r"(?<![=<>!])=(?!=)")
# Match calls only outside string/comments via a simple token heuristic.
CALL_RE = re.compile(r"\b(?:[A-Za-z_][A-Za-z0-9_]*|[])]\s*)\s*\(")
IMPORT_RE = re.compile(r"^\s*(import|from\s+\S+\s+import|require\s*\(|use\s+|#include|using\s+)", re.IGNORECASE)
TEST_ASSERT_RE = re.compile(
    r"\b(assert|expect|should|pytest|describe\(|it\(|test\(|unittest|TestCase)\b", re.IGNORECASE
)
CODE_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")

# Extend P52A forbidden-key set with P52B-specific keys that must never be
# emitted in the public artifact.
FORBIDDEN_PUBLIC_KEYS = set(p52a.FORBIDDEN_PUBLIC_KEYS) | {
    "repo_lock_path",
    "corpus_root",
    "raw_query",
    "query_terms",
    "identifier",
    "symbol_text",
    "provider",
    "base_url",
    "api_key",
    "provider_key",
}

# Safety-flag keys that are allowed in the public artifact even though their
# names overlap with forbidden substrings.
P52B_SAFETY_FLAG_KEYS = set(p52a.P52A_SAFETY_FLAG_KEYS) | {
    "remote_calls_by_p52b",
    "llm_calls_by_p52b",
    "prompt_construction_by_p52b",
    "source_reads_attempted_by_p52b",
    "source_reads_bounded_by_p52b",
    "raw_source_stored",
    "raw_text_stored",
    "raw_snippets_stored",
    "raw_snippets_sent_to_provider",
    "raw_paths_in_artifact",
    "raw_line_ranges_in_artifact",
    "raw_digests_in_artifact",
    "source_feature_not_evidence",
    "materialized_candidate_not_evidence",
    "verifier_not_evidence",
    "candidate_not_fact",
    "local_verifier_features_implemented",
    "local_verifier_score_available",
    "promotion_ready",
    "default_should_change",
    "evidencecore_semantics_changed",
    "aggregate_only_public_artifact",
    "score_phase_only_metrics",
    "source_materialization_metrics",
    "source_backed_feature_availability",
    "source_shape_features",
    "source_feature_bucket_v0",
    "pack_source_feature_diagnostics",
    "breakdowns",
    "score_phase_diagnostic_correlation",
    "by_slot_availability",
    "p52b_report_source",
    "p52a_report_source",
    "p52a_quality_gate_status",
    # metric block dimension keys
    "language_bucket",
    "source_class",
    "agreement_class",
    "rrf_backing",
    "public_bucket",
    "public_risk_tag",
    "p52_metadata_risk_bucket",
    "path_kind",
    "candidate_strategy",
    "pack_strategy",
    "source_class",
    "agreement_class",
    "by_source_class",
    "by_agreement_class",
    "by_rrf_backing",
    "by_public_bucket",
    "by_public_risk_tag",
    "by_p52_metadata_risk_bucket",
    "by_candidate_strategy",
    "by_pack_strategy",
    "by_path_kind",
    "by_language_bucket",
    "by_language",
    "by_source_class",
    "by_agreement_class",
    "by_rrf_backing",
    "by_public_bucket",
    "by_public_risk_tag",
    "by_p52_metadata_risk_bucket",
    "p52_low_risk_metadata_signal",
    "source_feature_low_risk",
    "source_feature_medium_risk",
    "source_feature_high_risk",
    "source_feature_unavailable",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _rate(num: int, den: int) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 6)


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 6) if values else None


def _percentile(values: list[int | float], p: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    if n == 1:
        return float(s[0])
    k = (n - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(s[int(k)])
    return float(s[f] * (c - k) + s[c] * (k - f))


def _as_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value == int(value):
            return int(value)
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str:
    return "" if value is None else str(value)


def _language_bucket(outcome_language: str) -> str:
    """Map P52A/r32 language to the public P52B bucket set."""
    if outcome_language in {"python"}:
        return "python"
    if outcome_language in {"javascript", "jsx", "mjs"}:
        return "javascript"
    if outcome_language in {"typescript", "tsx"}:
        return "typescript"
    if outcome_language in {"rust"}:
        return "rust"
    if outcome_language in {"go"}:
        return "go"
    if outcome_language in {"config", "toml", "yaml", "json", "ini"}:
        return "config"
    return "unknown"


def _classify_metadata_risk(cand: dict[str, Any], risk_tags: list[str]) -> str:
    """Wrap P52 metadata risk bucket for consistent reuse."""
    try:
        return p52._metadata_risk_bucket(cand, risk_tags)
    except Exception:
        return "metadata_unavailable"


def _make_self_test_corpus(root: Path) -> dict[str, str]:
    """Create deterministic source files and return path->sha256 map."""
    return p52a._make_self_test_corpus(root)


def _augment_self_test_records(records: list[dict[str, Any]], sha_map: dict[str, str]) -> list[dict[str, Any]]:
    """Wrap P52A self-test augmentation."""
    return p52a._augment_self_test_records(records, sha_map)


def _make_self_test_inputs() -> tuple[list[dict[str, Any]], Path, Path]:
    """Return ephemeral records, repo-lock path, and corpus root for self-test."""
    return p52a._make_self_test_inputs()


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P52B_SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def _read_optional_report(path: Path | None, report_name: str) -> dict[str, Any]:
    """Read optional upstream report and return only aggregate enum/status metadata."""
    return p52a._read_optional_report(path, report_name)


def _source_shape_features(lines: list[str]) -> dict[str, Any]:
    """Compute bounded source-shape heuristics from already-truncated lines.

    No raw text leaves this function; only lightweight booleans and counts.
    """
    nonempty_lines = [ln for ln in lines if ln.strip()]
    blank_lines = [ln for ln in lines if not ln.strip()]

    span_line_count = len(lines)
    span_char_count = sum(len(ln) for ln in lines)
    long_line_count = sum(1 for ln in lines if len(ln) >= MAX_LINE_LENGTH)

    comment_only = p52a._is_comment_only_span(lines)
    signature_like = p52a._has_signature_like_line(lines)

    def import_line(ln: str) -> bool:
        return bool(IMPORT_RE.match(ln))

    def assertion_line(ln: str) -> bool:
        return bool(TEST_ASSERT_RE.search(ln))

    def code_token_line(ln: str) -> bool:
        if p52a.COMMENT_RE.match(ln):
            return False
        return bool(CODE_TOKEN_RE.search(ln))

    def assignment_line(ln: str) -> bool:
        if p52a.COMMENT_RE.match(ln):
            return False
        return bool(ASSIGNMENT_RE.search(ln))

    def call_line(ln: str) -> bool:
        if p52a.COMMENT_RE.match(ln):
            return False
        return bool(CALL_RE.search(ln))

    def definition_line(ln: str) -> bool:
        if p52a.COMMENT_RE.match(ln):
            return False
        return bool(p52a.SIGNATURE_RE.match(ln))

    import_lines = [ln for ln in nonempty_lines if import_line(ln)]
    assertion_lines = [ln for ln in nonempty_lines if assertion_line(ln)]

    span_contains_code_like_token = any(code_token_line(ln) for ln in lines)
    span_contains_assignment_like_token = any(assignment_line(ln) for ln in lines)
    span_contains_call_like_token = any(call_line(ln) for ln in lines)
    span_contains_definition_keyword = any(definition_line(ln) for ln in lines)
    import_only_heuristic = bool(import_lines) and len(import_lines) == len(nonempty_lines)
    test_assertion_like_heuristic = bool(assertion_lines)

    def line_count_bin(width: int) -> str:
        if width <= 0:
            return "empty"
        if width == 1:
            return "1"
        if width <= 5:
            return "2_5"
        if width <= 20:
            return "6_20"
        if width <= MAX_SPAN_LINES:
            return "21_80"
        return "over_cap"

    def char_count_bin(chars: int) -> str:
        if chars <= 0:
            return "empty"
        if chars <= 100:
            return "1_100"
        if chars <= 500:
            return "101_500"
        if chars <= 2000:
            return "501_2000"
        if chars <= 10000:
            return "2001_10000"
        return "over_10000"

    return {
        "span_line_count": span_line_count,
        "span_char_count": span_char_count,
        "span_line_count_bin": line_count_bin(span_line_count),
        "span_char_count_bin": char_count_bin(span_char_count),
        "span_nonempty": bool(nonempty_lines),
        "span_blank_only": bool(span_line_count > 0 and not nonempty_lines),
        "span_comment_only_heuristic": comment_only,
        "span_contains_code_like_token": span_contains_code_like_token,
        "span_contains_assignment_like_token": span_contains_assignment_like_token,
        "span_contains_call_like_token": span_contains_call_like_token,
        "span_contains_definition_keyword": span_contains_definition_keyword,
        "signature_like_line_heuristic": signature_like,
        "import_only_heuristic": import_only_heuristic,
        "test_assertion_like_heuristic": test_assertion_like_heuristic,
        "long_line_truncated_count": long_line_count,
    }


def _read_bounded_span_lines(
    cand: dict[str, Any],
    root: Path | None,
    total_bytes_read: int,
) -> tuple[list[str] | None, int, str | None]:
    """Return bounded span lines, updated byte budget, and reason token.

    Reuses P52A path safety and bounded-file reads so safety logic is not
    duplicated.  Raw text is discarded after this call returns.
    """
    path = _as_str(cand.get("_path"))
    start = _as_int(cand.get("_start")) or 0
    end = _as_int(cand.get("_end")) or 0

    if root is None:
        return None, total_bytes_read, "source_root_unavailable"
    if not p46._has_valid_path({"path": path}):
        return None, total_bytes_read, "path_invalid"

    full = p52a._resolve_candidate_path(path, root)
    if full is None:
        return None, total_bytes_read, "escape_reject"

    text, raw, bytes_read, reason = p52a._read_source_file(full, total_bytes_read)
    total_bytes_read += bytes_read
    if reason is not None:
        return None, total_bytes_read, reason
    if text is None:
        return None, total_bytes_read, "missing_file"

    max_end = len(text.splitlines())
    if start <= 0 or end < start or end > max_end:
        return None, total_bytes_read, "range_invalid"

    width = end - start + 1
    if width > MAX_SPAN_LINES:
        return None, total_bytes_read, "span_over_cap"

    lines = [
        p52a._truncate_line(line)
        for i, line in enumerate(text.splitlines(), start=1)
        if start <= i <= end
    ]
    return lines, total_bytes_read, None


def _compute_source_shape_features(
    normalized_tasks: list[dict[str, Any]],
    repo_resolution: dict[str, Path | None],
    outcomes_by_task_cand: dict[tuple[int, int], dict[str, Any]],
) -> dict[tuple[int, int], dict[str, Any]]:
    """Compute bounded source-shape features for checkable candidates.

    Only candidates with resolved roots and successful source reads are
    considered; the read is repeated here under the same P52A byte/line/file
    caps (counts reset for this phase because raw text is transient).
    """
    features_by_task_cand: dict[tuple[int, int], dict[str, Any]] = {}
    total_bytes_read = 0

    for task_idx, task in enumerate(normalized_tasks):
        tid = _as_str(task.get("task_id"))
        root = repo_resolution.get(tid)
        for cand in task.get("_candidates", []):
            cid = cand.get("_id")
            if not isinstance(cid, int):
                continue
            outcome = outcomes_by_task_cand.get((task_idx, cid)) or {}
            # Only read if P52A outcome indicates success and valid bounded range.
            if not outcome.get("source_read_success") or not outcome.get("range_valid") or outcome.get("span_over_cap"):
                continue
            lines, total_bytes_read, reason = _read_bounded_span_lines(cand, root, total_bytes_read)
            if reason is not None or lines is None:
                continue
            features = _source_shape_features(lines)
            features["language_bucket"] = _language_bucket(outcome.get("language") or "unknown")
            features["path_kind"] = _as_str(cand.get("path_kind") or "unknown")
            features_by_task_cand[(task_idx, cid)] = features

    return features_by_task_cand


def _source_backed_feature_availability(
    candidate_denominator: int,
    bounded_span_candidates: int,
    feature_candidates: int,
) -> dict[str, Any]:
    def _unavailable_block() -> dict[str, Any]:
        return {
            "availability": "unavailable_ast_parser_not_wired",
            "checkable_count": None,
            "checkable_rate": None,
            "unavailable_count": candidate_denominator,
            "unavailable_rate": 1.0 if candidate_denominator > 0 else None,
            "value": None,
            "reason": "unavailable_parser_not_wired",
        }

    return {
        "candidate_denominator": candidate_denominator,
        "source_backed_feature_availability_rate": _rate(feature_candidates, candidate_denominator),
        "bounded_span_feature_candidate_denominator": bounded_span_candidates,
        "bounded_span_feature_availability_rate": _rate(bounded_span_candidates, candidate_denominator),
        "heuristic_feature_availability_rate": _rate(feature_candidates, candidate_denominator),
        "unavailable_ast_feature_availability": _unavailable_block(),
        "unavailable_query_feature_availability": {
            "availability": "unavailable_raw_query_not_public",
            "checkable_count": None,
            "checkable_rate": None,
            "unavailable_count": candidate_denominator,
            "unavailable_rate": 1.0 if candidate_denominator > 0 else None,
            "value": None,
            "reason": "unavailable_raw_query_not_public",
        },
    }


def _build_source_shape_metrics(
    candidate_denominator: int,
    feature_by_cand: dict[tuple[int, int], dict[str, Any]],
) -> dict[str, Any]:
    keys: list[tuple[str, str, bool]] = [
        ("span_nonempty", "positive", False),
        ("span_blank_only", "positive", False),
        ("span_comment_only_heuristic", "heuristic", True),
        ("span_contains_code_like_token", "positive", False),
        ("span_contains_assignment_like_token", "positive", False),
        ("span_contains_call_like_token", "positive", False),
        ("span_contains_definition_keyword", "positive", False),
        ("signature_like_line_heuristic", "heuristic", True),
        ("import_only_heuristic", "heuristic", True),
        ("test_assertion_like_heuristic", "heuristic", True),
    ]

    result: dict[str, Any] = {}
    checkable = len(feature_by_cand)
    for key, kind, partial in keys:
        positive = sum(1 for f in feature_by_cand.values() if f.get(key))
        block: dict[str, Any]
        if kind == "heuristic":
            block = {
                "availability": "partial_heuristic_line_prefix_only" if partial else "partial_heuristic_regex_only",
                "checkable_count": checkable,
                "checkable_rate": _rate(checkable, candidate_denominator),
                "heuristic_positive_count": positive,
                "heuristic_positive_rate": _rate(positive, checkable),
            }
        else:
            block = {
                "availability": "available",
                "checkable_count": checkable,
                "checkable_rate": _rate(checkable, candidate_denominator),
                "positive_count": positive,
                "positive_rate": _rate(positive, checkable),
            }
        result[key] = block

    # Width distribution (aggregate bins only).
    line_bin_counts: dict[str, int] = defaultdict(int)
    char_bin_counts: dict[str, int] = defaultdict(int)
    widths: list[int] = []
    chars: list[int] = []
    long_lines_total = 0
    for f in feature_by_cand.values():
        line_bin_counts[f.get("span_line_count_bin", "unknown")] += 1
        char_bin_counts[f.get("span_char_count_bin", "unknown")] += 1
        widths.append(f.get("span_line_count", 0))
        chars.append(f.get("span_char_count", 0))
        long_lines_total += f.get("long_line_truncated_count", 0)

    result["span_line_count_distribution"] = dict(line_bin_counts)
    result["span_char_count_distribution"] = dict(char_bin_counts)
    result["span_line_count_mean"] = _avg([float(w) for w in widths])
    result["span_line_count_p95"] = _percentile([float(w) for w in widths], 0.95)
    result["span_char_count_mean"] = _avg([float(c) for c in chars])
    result["span_char_count_p95"] = _percentile([float(c) for c in chars], 0.95)
    result["long_line_truncated_count"] = long_lines_total
    result["long_line_truncated_rate_per_checkable_span"] = _rate(long_lines_total, checkable)

    # Consistency diagnostics (aggregate only).
    consistency_total = 0
    consistent_count = 0
    source_with_test_assert = 0
    test_with_definition = 0
    doc_config_with_code = 0
    width_matches = 0

    for f in feature_by_cand.values():
        consistency_total += 1
        pk = f.get("path_kind") or "unknown"
        has_code = f.get("span_contains_code_like_token") or f.get("span_contains_definition_keyword")
        has_sig = f.get("signature_like_line_heuristic")
        is_test_assert = f.get("test_assertion_like_heuristic")

        if pk == "source" and (has_code or has_sig):
            consistent_count += 1
        elif pk == "test" and is_test_assert:
            consistent_count += 1
        elif pk in {"doc", "config"} and not has_code and not has_sig:
            consistent_count += 1
        elif pk in {"unknown", "generated_or_vendor"}:
            consistent_count += 1  # no expectation

        if pk == "source" and is_test_assert:
            source_with_test_assert += 1
        if pk == "test" and (has_sig or f.get("span_contains_definition_keyword")):
            test_with_definition += 1
        if pk in {"doc", "config"} and has_code:
            doc_config_with_code += 1

        sw = f.get("span_line_count", 0)
        if sw > 0 and sw <= MAX_SPAN_LINES:
            width_matches += 1

    result["path_kind_vs_source_shape_consistency"] = {
        "checkable_count": consistency_total,
        "checkable_rate": _rate(consistency_total, candidate_denominator),
        "consistent_count": consistent_count,
        "consistent_rate": _rate(consistent_count, consistency_total),
    }
    result["source_file_with_test_assertion_like_span"] = {
        "checkable_count": consistency_total,
        "positive_count": source_with_test_assert,
        "positive_rate": _rate(source_with_test_assert, consistency_total),
    }
    result["test_file_with_source_definition_like_span"] = {
        "checkable_count": consistency_total,
        "positive_count": test_with_definition,
        "positive_rate": _rate(test_with_definition, consistency_total),
    }
    result["doc_config_path_with_code_like_span"] = {
        "checkable_count": consistency_total,
        "positive_count": doc_config_with_code,
        "positive_rate": _rate(doc_config_with_code, consistency_total),
    }
    result["candidate_span_width_matches_read_width"] = {
        "checkable_count": consistency_total,
        "matching_count": width_matches,
        "matching_rate": _rate(width_matches, consistency_total),
    }

    # Unavailable AST/query-dependent features. Keep availability and reason
    # aligned; do not publish fake zeroes for unavailable verifier classes.
    unavailable_reasons = {
        "ast_node_kind": "unavailable_ast_parser_not_wired",
        "signature_match": "unavailable_signature_parser_not_wired",
        "identifier_density": "unavailable_identifier_extractor_not_wired",
        "symbol_definition_match": "unavailable_identifier_extractor_not_wired",
        "exact_identifier_in_span": "unavailable_raw_query_not_public",
        "query_terms_in_span": "unavailable_raw_query_not_public",
        "term_density": "unavailable_raw_query_not_public",
        "intent_identifier_match": "unavailable_raw_query_not_public",
        "semantic_query_match": "unavailable_raw_query_not_public",
    }
    for key, reason in unavailable_reasons.items():
        result[key] = {
            "availability": reason,
            "checkable_count": None,
            "checkable_rate": None,
            "unavailable_count": candidate_denominator,
            "unavailable_rate": 1.0 if candidate_denominator > 0 else None,
            "value": None,
            "reason": reason,
        }

    return result


def _source_feature_bucket(
    outcome: dict[str, Any],
    features: dict[str, Any] | None,
    cand: dict[str, Any],
    risk_tags: list[str],
) -> str:
    """Assign a candidate to a source-feature risk bucket.

    High-risk if source unreadable/range invalid/span over cap/digest mismatch/
    comment-only/blank-only/import-only/generated-vendor-unknown path kind/etc.
    Low-risk if readable + range valid + not over cap + no digest mismatch +
    nonempty + not comment-only + signature-like or code-like token present +
    favorable metadata subtype if available.  Else medium.
    Unavailable when no source root / unreadable without shape info.
    """
    path_kind = _as_str(cand.get("path_kind") or "unknown")

    if outcome.get("source_root_unavailable"):
        return "source_feature_unavailable"

    if (
        not outcome.get("source_read_success")
        or outcome.get("range_invalid_start")
        or outcome.get("range_invalid_end")
        or outcome.get("range_reversed")
        or outcome.get("range_out_of_bounds")
        or not outcome.get("range_valid")
        or outcome.get("span_over_cap")
    ):
        return "source_feature_high_risk"

    if outcome.get("digest_mismatch"):
        return "source_feature_high_risk"

    if path_kind in {"generated_or_vendor", "unknown"}:
        return "source_feature_high_risk"

    if features is None:
        # Readable and range valid but shape features not extractable; treat as
        # medium rather than unavailable because source was materialized.
        return "source_feature_medium_risk"

    if not features.get("span_nonempty") or features.get("span_blank_only"):
        return "source_feature_high_risk"
    if features.get("span_comment_only_heuristic") or features.get("import_only_heuristic"):
        return "source_feature_high_risk"

    has_code_shape = (
        features.get("signature_like_line_heuristic")
        or features.get("span_contains_definition_keyword")
        or features.get("span_contains_code_like_token")
        or features.get("span_contains_assignment_like_token")
        or features.get("span_contains_call_like_token")
    )

    if not has_code_shape:
        return "source_feature_medium_risk"

    metadata_bucket = _classify_metadata_risk(cand, risk_tags)
    if metadata_bucket == "metadata_low_risk":
        return "source_feature_low_risk"

    # Favorable metadata subtype is available but not strongly low-risk.
    subtype = cand.get("subtype") or {}
    if isinstance(subtype, dict):
        source_class = str(subtype.get("source_class") or "other")
        agreement = str(subtype.get("agreement_class") or "other")
        rrf = p49._has_rrf_backing(cand)
        if source_class == "symbol_regex_fusion" and agreement == "span_overlap" and rrf:
            return "source_feature_low_risk"

    return "source_feature_medium_risk"


def _source_feature_bucket_v0(
    normalized_tasks: list[dict[str, Any]],
    outcomes_by_task_cand: dict[tuple[int, int], dict[str, Any]],
    features_by_task_cand: dict[tuple[int, int], dict[str, Any]],
) -> dict[str, Any]:
    counts: dict[str, int] = {b: 0 for b in SOURCE_FEATURE_BUCKETS}
    candidate_denominator = 0

    for task_idx, task in enumerate(normalized_tasks):
        risk_tags = task.get("task_risk_tags", [])
        for cand in task.get("_candidates", []):
            cid = cand.get("_id")
            if not isinstance(cid, int):
                continue
            candidate_denominator += 1
            outcome = outcomes_by_task_cand.get((task_idx, cid)) or {}
            features = features_by_task_cand.get((task_idx, cid))
            bucket = _source_feature_bucket(outcome, features, cand, risk_tags)
            counts[bucket] += 1

    rates = {b: _rate(counts[b], candidate_denominator) for b in SOURCE_FEATURE_BUCKETS}
    return {
        "candidate_denominator": candidate_denominator,
        "risk_bucket_counts": {b: counts[b] for b in SOURCE_FEATURE_BUCKETS},
        "risk_bucket_rates": rates,
    }


def _pack_source_feature_diagnostics(
    normalized_tasks: list[dict[str, Any]],
    packs: dict[tuple[int, str], dict[str, Any]],
    outcomes_by_task_cand: dict[tuple[int, int], dict[str, Any]],
    features_by_task_cand: dict[tuple[int, int], dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate pack-level source-feature diagnostics by pack strategy.

    Slot tagging is not wired into P49's public contract; it is reported as an
    availability string rather than fabricated zeros.
    """
    overall = {
        "pack_denominator": 0,
        "pack_with_low_risk_anchor_count": 0,
        "pack_with_high_risk_candidate_count": 0,
        "pack_all_candidates_source_features_available_count": 0,
        "pack_any_source_feature_unavailable_count": 0,
        "pack_any_digest_mismatch_count": 0,
        "pack_any_comment_only_count": 0,
        "pack_any_import_only_count": 0,
        "pack_any_signature_like_count": 0,
        "pack_source_feature_diversity_count": 0,
    }

    by_strategy: dict[str, dict[str, Any]] = {
        strategy: {
            "pack_denominator": 0,
            "pack_with_low_risk_anchor_count": 0,
            "pack_with_high_risk_candidate_count": 0,
            "pack_all_candidates_source_features_available_count": 0,
            "pack_any_source_feature_unavailable_count": 0,
            "pack_any_digest_mismatch_count": 0,
            "pack_any_comment_only_count": 0,
            "pack_any_import_only_count": 0,
            "pack_any_signature_like_count": 0,
            "pack_source_feature_diversity_count": 0,
        }
        for strategy in p49.PACK_STRATEGIES
    }

    for (task_idx, strategy), pack in packs.items():
        task = normalized_tasks[task_idx]
        risk_tags = task.get("task_risk_tags", [])
        selected = pack.get("selected", [])
        if not selected:
            continue
        overall["pack_denominator"] += 1
        by_strategy[strategy]["pack_denominator"] += 1

        buckets_in_pack: set[str] = set()
        all_available = True
        any_source_feature_unavailable = False
        any_digest_mismatch = False
        any_comment_only = False
        any_import_only = False
        any_signature_like = False
        anchor_bucket: str | None = None
        any_high_risk = False

        for idx, cand in enumerate(selected):
            cid = cand.get("_id")
            if not isinstance(cid, int):
                continue
            outcome = outcomes_by_task_cand.get((task_idx, cid)) or {}
            features = features_by_task_cand.get((task_idx, cid))
            bucket = _source_feature_bucket(outcome, features, cand, risk_tags)
            buckets_in_pack.add(bucket)
            if features is None:
                any_source_feature_unavailable = True
                all_available = False
            if idx == 0:
                anchor_bucket = bucket
            if bucket == "source_feature_unavailable":
                any_source_feature_unavailable = True
                all_available = False
            if bucket == "source_feature_high_risk":
                any_high_risk = True
            if outcome.get("digest_mismatch"):
                any_digest_mismatch = True
            if features and features.get("span_comment_only_heuristic"):
                any_comment_only = True
            if features and features.get("import_only_heuristic"):
                any_import_only = True
            if features and features.get("signature_like_line_heuristic"):
                any_signature_like = True

        if anchor_bucket == "source_feature_low_risk":
            overall["pack_with_low_risk_anchor_count"] += 1
            by_strategy[strategy]["pack_with_low_risk_anchor_count"] += 1
        if any_high_risk:
            overall["pack_with_high_risk_candidate_count"] += 1
            by_strategy[strategy]["pack_with_high_risk_candidate_count"] += 1
        if all_available:
            overall["pack_all_candidates_source_features_available_count"] += 1
            by_strategy[strategy]["pack_all_candidates_source_features_available_count"] += 1
        if any_source_feature_unavailable:
            overall["pack_any_source_feature_unavailable_count"] += 1
            by_strategy[strategy]["pack_any_source_feature_unavailable_count"] += 1
        if any_digest_mismatch:
            overall["pack_any_digest_mismatch_count"] += 1
            by_strategy[strategy]["pack_any_digest_mismatch_count"] += 1
        if any_comment_only:
            overall["pack_any_comment_only_count"] += 1
            by_strategy[strategy]["pack_any_comment_only_count"] += 1
        if any_import_only:
            overall["pack_any_import_only_count"] += 1
            by_strategy[strategy]["pack_any_import_only_count"] += 1
        if any_signature_like:
            overall["pack_any_signature_like_count"] += 1
            by_strategy[strategy]["pack_any_signature_like_count"] += 1
        if len(buckets_in_pack) > 1:
            overall["pack_source_feature_diversity_count"] += 1
            by_strategy[strategy]["pack_source_feature_diversity_count"] += 1

    def finalize(block: dict[str, Any]) -> dict[str, Any]:
        denom = block["pack_denominator"]
        return {
            "pack_denominator": denom,
            "pack_with_low_risk_anchor_count": block["pack_with_low_risk_anchor_count"],
            "pack_with_low_risk_anchor_rate": _rate(block["pack_with_low_risk_anchor_count"], denom),
            "pack_with_high_risk_candidate_count": block["pack_with_high_risk_candidate_count"],
            "pack_with_high_risk_candidate_rate": _rate(block["pack_with_high_risk_candidate_count"], denom),
            "pack_all_candidates_source_features_available_count": block["pack_all_candidates_source_features_available_count"],
            "pack_all_candidates_source_features_available_rate": _rate(block["pack_all_candidates_source_features_available_count"], denom),
            "pack_any_source_feature_unavailable_count": block["pack_any_source_feature_unavailable_count"],
            "pack_any_source_feature_unavailable_rate": _rate(block["pack_any_source_feature_unavailable_count"], denom),
            "pack_any_digest_mismatch_count": block["pack_any_digest_mismatch_count"],
            "pack_any_digest_mismatch_rate": _rate(block["pack_any_digest_mismatch_count"], denom),
            "pack_any_comment_only_count": block["pack_any_comment_only_count"],
            "pack_any_comment_only_rate": _rate(block["pack_any_comment_only_count"], denom),
            "pack_any_import_only_count": block["pack_any_import_only_count"],
            "pack_any_import_only_rate": _rate(block["pack_any_import_only_count"], denom),
            "pack_any_signature_like_count": block["pack_any_signature_like_count"],
            "pack_any_signature_like_rate": _rate(block["pack_any_signature_like_count"], denom),
            "pack_source_feature_diversity_count": block["pack_source_feature_diversity_count"],
            "pack_source_feature_diversity_rate": _rate(block["pack_source_feature_diversity_count"], denom),
        }

    return {
        "by_slot_availability": "unavailable_slot_tagging_not_wired",
        "task_wide": finalize(overall),
        "by_pack_strategy": {strategy: finalize(by_strategy[strategy]) for strategy in p49.PACK_STRATEGIES},
    }


def _breakdowns(
    normalized_tasks: list[dict[str, Any]],
    packs: dict[tuple[int, str], dict[str, Any]],
    outcomes_by_task_cand: dict[tuple[int, int], dict[str, Any]],
    features_by_task_cand: dict[tuple[int, int], dict[str, Any]],
) -> dict[str, Any]:
    def make_bucket() -> dict[str, Any]:
        return {
            "candidate_count": 0,
            "source_read_success_count": 0,
            "range_valid_count": 0,
            "bounded_span_feature_count": 0,
            "digest_match_count": 0,
            "source_feature_low_risk_count": 0,
            "source_feature_medium_risk_count": 0,
            "source_feature_high_risk_count": 0,
            "source_feature_unavailable_count": 0,
        }

    breakdowns: dict[str, dict[str, dict[str, Any]]] = {
        "by_candidate_strategy": defaultdict(make_bucket),
        "by_pack_strategy": defaultdict(make_bucket),
        "by_path_kind": defaultdict(make_bucket),
        "by_language_bucket": defaultdict(make_bucket),
        "by_source_class": defaultdict(make_bucket),
        "by_agreement_class": defaultdict(make_bucket),
        "by_rrf_backing": defaultdict(make_bucket),
        "by_public_bucket": defaultdict(make_bucket),
        "by_public_risk_tag": defaultdict(make_bucket),
        "by_p52_metadata_risk_bucket": defaultdict(make_bucket),
    }

    for task_idx, task in enumerate(normalized_tasks):
        public_bucket = p25.sanitize_public_bucket(task.get("task_bucket", "unknown"))
        risk_tags = task.get("task_risk_tags", [])
        first_tag = risk_tags[0] if risk_tags else "other"

        for cand in task.get("_candidates", []):
            cid = cand.get("_id")
            if not isinstance(cid, int):
                continue
            outcome = outcomes_by_task_cand.get((task_idx, cid)) or {}
            features = features_by_task_cand.get((task_idx, cid))
            bucket = _source_feature_bucket(
                outcome,
                features,
                cand,
                risk_tags,
            )

            subtype = cand.get("subtype") or {}
            source_class = str(subtype.get("source_class")) if isinstance(subtype, dict) and subtype.get("source_class") in p46.SUBTYPE_SOURCE_CLASSES else "other"
            agreement_class = str(subtype.get("agreement_class")) if isinstance(subtype, dict) and subtype.get("agreement_class") in p46.SUBTYPE_AGREEMENT_CLASSES else "other"
            rrf = "rrf_yes" if p49._has_rrf_backing(cand) else "rrf_no"
            metadata_bucket = _classify_metadata_risk(cand, risk_tags)

            dims: dict[str, str] = {
                "by_candidate_strategy": _as_str(cand.get("source_strategy") or "unknown"),
                "by_path_kind": _as_str(cand.get("path_kind") or "unknown"),
                "by_language_bucket": _as_str(features.get("language_bucket") if features else "unread"),
                "by_source_class": source_class,
                "by_agreement_class": agreement_class,
                "by_rrf_backing": rrf,
                "by_public_bucket": public_bucket,
                "by_public_risk_tag": first_tag,
                "by_p52_metadata_risk_bucket": metadata_bucket,
            }

            # Pack strategy is derived from P49 packs in memory; a candidate may
            # appear in multiple strategies, so each strategy gets its own row.
            strategies = {
                strategy
                for (tidx, strategy), pack in packs.items()
                if tidx == task_idx and any(c.get("_id") == cid for c in pack.get("selected", []))
            }

            for dim_name, dim_value in dims.items():
                if dim_name == "by_pack_strategy":
                    continue
                b = breakdowns[dim_name][dim_value]
                b["candidate_count"] += 1
                if outcome.get("source_read_success"):
                    b["source_read_success_count"] += 1
                if outcome.get("range_valid"):
                    b["range_valid_count"] += 1
                if features is not None:
                    b["bounded_span_feature_count"] += 1
                if outcome.get("digest_match") is True:
                    b["digest_match_count"] += 1
                if bucket == "source_feature_low_risk":
                    b["source_feature_low_risk_count"] += 1
                elif bucket == "source_feature_medium_risk":
                    b["source_feature_medium_risk_count"] += 1
                elif bucket == "source_feature_high_risk":
                    b["source_feature_high_risk_count"] += 1
                elif bucket == "source_feature_unavailable":
                    b["source_feature_unavailable_count"] += 1

            for strategy in strategies or {"not_in_any_pack"}:
                b = breakdowns["by_pack_strategy"][strategy]
                b["candidate_count"] += 1
                if outcome.get("source_read_success"):
                    b["source_read_success_count"] += 1
                if outcome.get("range_valid"):
                    b["range_valid_count"] += 1
                if features is not None:
                    b["bounded_span_feature_count"] += 1
                if outcome.get("digest_match") is True:
                    b["digest_match_count"] += 1
                if bucket == "source_feature_low_risk":
                    b["source_feature_low_risk_count"] += 1
                elif bucket == "source_feature_medium_risk":
                    b["source_feature_medium_risk_count"] += 1
                elif bucket == "source_feature_high_risk":
                    b["source_feature_high_risk_count"] += 1
                elif bucket == "source_feature_unavailable":
                    b["source_feature_unavailable_count"] += 1

    def finalize_bucket(b: dict[str, Any]) -> dict[str, Any]:
        denom = b["candidate_count"]
        return {
            "candidate_count": denom,
            "source_read_success_rate": _rate(b["source_read_success_count"], denom),
            "range_valid_rate": _rate(b["range_valid_count"], denom),
            "bounded_span_feature_rate": _rate(b["bounded_span_feature_count"], denom),
            "digest_match_rate": _rate(b["digest_match_count"], denom),
            "source_feature_low_risk_rate": _rate(b["source_feature_low_risk_count"], denom),
            "source_feature_medium_risk_rate": _rate(b["source_feature_medium_risk_count"], denom),
            "source_feature_high_risk_rate": _rate(b["source_feature_high_risk_count"], denom),
            "source_feature_unavailable_rate": _rate(b["source_feature_unavailable_count"], denom),
        }

    result: dict[str, Any] = {}
    for dim_name, dim_map in breakdowns.items():
        result[dim_name] = {k: finalize_bucket(v) for k, v in sorted(dim_map.items())}
    return result


def _score_phase_diagnostics(
    normalized_tasks: list[dict[str, Any]],
    outcomes_by_task_cand: dict[tuple[int, int], dict[str, Any]],
    features_by_task_cand: dict[tuple[int, int], dict[str, Any]],
) -> dict[str, Any]:
    """SCORE-phase correlations of source-feature buckets with gold/outcomes.

    Not used for feature construction.
    """
    by_bucket_counts: dict[str, dict[str, int]] = {
        b: {
            "candidate_count": 0,
            "gold_file_count": 0,
            "gold_span_count": 0,
            "file_right_span_wrong_count": 0,
            "digest_mismatch_gold_span_count": 0,
            "comment_only_gold_span_count": 0,
            "signature_like_gold_span_count": 0,
        }
        for b in SOURCE_FEATURE_BUCKETS
    }

    positive_tasks = [
        (idx, t)
        for idx, t in enumerate(normalized_tasks)
        if t.get("has_gold") and t.get("has_gold_spans")
    ]
    no_gold_tasks = [t for t in normalized_tasks if not t.get("has_gold")]

    for task_idx, task in positive_tasks:
        label = task.get("label", {})
        risk_tags = task.get("task_risk_tags", [])
        for cand in task.get("_candidates", []):
            cid = cand.get("_id")
            if not isinstance(cid, int):
                continue
            outcome = outcomes_by_task_cand.get((task_idx, cid)) or {}
            features = features_by_task_cand.get((task_idx, cid))
            bucket = _source_feature_bucket(outcome, features, cand, risk_tags)
            counts = by_bucket_counts[bucket]
            counts["candidate_count"] += 1

            in_file = p49._file_in_gold(cand, label)
            in_span = p49._span_overlaps_gold(cand, label)
            if in_file:
                counts["gold_file_count"] += 1
            if in_span:
                counts["gold_span_count"] += 1
            if in_file and not in_span:
                counts["file_right_span_wrong_count"] += 1
            if in_span and outcome.get("digest_mismatch"):
                counts["digest_mismatch_gold_span_count"] += 1
            if in_span and features and features.get("span_comment_only_heuristic"):
                counts["comment_only_gold_span_count"] += 1
            if in_span and features and features.get("signature_like_line_heuristic"):
                counts["signature_like_gold_span_count"] += 1

    by_bucket: dict[str, Any] = {}
    for b in SOURCE_FEATURE_BUCKETS:
        counts = by_bucket_counts[b]
        denom = counts["candidate_count"]
        by_bucket[b] = {
            "candidate_count": denom,
            "gold_file_count": counts["gold_file_count"],
            "gold_file_rate": _rate(counts["gold_file_count"], denom),
            "gold_span_count": counts["gold_span_count"],
            "gold_span_rate": _rate(counts["gold_span_count"], denom),
            "file_right_span_wrong_count": counts["file_right_span_wrong_count"],
            "file_right_span_wrong_rate": _rate(counts["file_right_span_wrong_count"], denom),
            "digest_mismatch_gold_span_count": counts["digest_mismatch_gold_span_count"],
            "comment_only_gold_span_count": counts["comment_only_gold_span_count"],
            "signature_like_gold_span_count": counts["signature_like_gold_span_count"],
        }

    no_gold_high_risk = 0
    no_gold_low_risk = 0
    no_gold_denom = 0
    for task in no_gold_tasks:
        task_idx = normalized_tasks.index(task)
        risk_tags = task.get("task_risk_tags", [])
        seen: set[int] = set()
        for cand in task.get("_candidates", []):
            cid = cand.get("_id")
            if not isinstance(cid, int) or cid in seen:
                continue
            seen.add(cid)
            no_gold_denom += 1
            outcome = outcomes_by_task_cand.get((task_idx, cid)) or {}
            features = features_by_task_cand.get((task_idx, cid))
            bucket = _source_feature_bucket(outcome, features, cand, risk_tags)
            if bucket == "source_feature_high_risk":
                no_gold_high_risk += 1
            elif bucket == "source_feature_low_risk":
                no_gold_low_risk += 1

    digest_mismatch_gold_span_count = sum(
        by_bucket[b]["digest_mismatch_gold_span_count"] for b in SOURCE_FEATURE_BUCKETS
    )
    gold_span_total = sum(by_bucket[b]["gold_span_count"] for b in SOURCE_FEATURE_BUCKETS)
    comment_only_gold_span_count = sum(
        by_bucket[b]["comment_only_gold_span_count"] for b in SOURCE_FEATURE_BUCKETS
    )
    signature_like_gold_span_count = sum(
        by_bucket[b]["signature_like_gold_span_count"] for b in SOURCE_FEATURE_BUCKETS
    )

    return {
        "not_used_for_feature_construction": True,
        "diagnostic_correlation_only": True,
        "by_source_feature_bucket": by_bucket,
        "no_gold_high_risk_candidate_count": no_gold_high_risk,
        "no_gold_low_risk_candidate_count": no_gold_low_risk,
        "no_gold_candidate_denominator": no_gold_denom,
        "no_gold_high_risk_candidate_rate": _rate(no_gold_high_risk, no_gold_denom),
        "no_gold_low_risk_candidate_rate": _rate(no_gold_low_risk, no_gold_denom),
        "digest_mismatch_gold_span_count": digest_mismatch_gold_span_count,
        "digest_mismatch_gold_span_rate": _rate(digest_mismatch_gold_span_count, gold_span_total),
        "comment_only_gold_span_count": comment_only_gold_span_count,
        "comment_only_gold_span_rate": _rate(comment_only_gold_span_count, gold_span_total),
        "signature_like_gold_span_count": signature_like_gold_span_count,
        "signature_like_gold_span_rate": _rate(signature_like_gold_span_count, gold_span_total),
    }


def build_report(
    raw_records: list[dict[str, Any]],
    normalized_tasks: list[dict[str, Any]],
    *,
    self_test: bool,
    elapsed_ms: int,
    status: str,
    reason: str | None,
    input_source_count: int,
    insufficient_input_source_count: int,
    repo_lock_path: Path | None,
    source_root: Path | None,
    p52a_report_path: Path | None,
    p52_report_path: Path | None,
    p49_report_path: Path | None,
    p50_report_path: Path | None,
    p48_report_path: Path | None,
) -> dict[str, Any]:
    repo_resolution, repo_meta = p52a._determine_repo_roots(normalized_tasks, repo_lock_path, source_root)

    candidate_pool_availability = (
        "available"
        if normalized_tasks and all(t.get("has_candidate_pool") for t in normalized_tasks)
        else "partial"
        if normalized_tasks and any(t.get("has_candidate_pool") for t in normalized_tasks)
        else "missing_candidate_pool"
    )
    gold_span_availability = (
        "available"
        if normalized_tasks and all(t.get("has_gold_spans") for t in normalized_tasks if t["has_gold"])
        else "partial"
        if normalized_tasks and any(t.get("has_gold_spans") for t in normalized_tasks if t["has_gold"])
        else "missing_gold_spans"
    )
    reach_metrics_available = (
        candidate_pool_availability != "missing_candidate_pool"
        and gold_span_availability != "missing_gold_spans"
    )
    p31_h1_handoff_detected = bool(
        normalized_tasks and any(t.get("has_candidate_pool") and t.get("has_gold_spans") for t in normalized_tasks)
    )
    p31_h1_handoff_detected_count = sum(
        1 for t in normalized_tasks if t.get("has_candidate_pool") and t.get("has_gold_spans")
    )
    p33b_handoff_detected = bool(normalized_tasks and any(t.get("subtypes") for t in normalized_tasks))
    p33b_handoff_detected_count = sum(1 for t in normalized_tasks if t.get("subtypes"))

    p52a_meta = _read_optional_report(p52a_report_path, "p52a")
    p52_meta = _read_optional_report(p52_report_path, "p52")
    p49_meta = _read_optional_report(p49_report_path, "p49")
    p50_meta = _read_optional_report(p50_report_path, "p50")
    p48_meta = _read_optional_report(p48_report_path, "p48")

    p52a._apply_global_candidate_cap(normalized_tasks)
    outcomes, outcomes_by_task_cand = p52a._compute_source_read_outcomes(normalized_tasks, repo_resolution)

    candidate_denominator = len(outcomes)
    task_denominator = len(normalized_tasks)
    bounded_span_candidates = sum(
        1 for o in outcomes
        if o.get("source_read_success") and o.get("range_valid") and not o.get("span_over_cap")
    )

    features_by_task_cand = _compute_source_shape_features(
        normalized_tasks, repo_resolution, outcomes_by_task_cand
    )
    feature_candidates = len(features_by_task_cand)

    packs = p52a._compute_strategy_packs(normalized_tasks)

    source_materialization_metrics = p52a._source_materialization_metrics(outcomes, candidate_denominator)
    source_reads_attempted = (source_materialization_metrics.get("source_read_attempt_count") or 0) > 0

    metric_blocks: dict[str, Any] = {
        "source_materialization_metrics": source_materialization_metrics,
        "source_backed_feature_availability": _source_backed_feature_availability(
            candidate_denominator, bounded_span_candidates, feature_candidates
        ),
        "source_shape_features": _build_source_shape_metrics(candidate_denominator, features_by_task_cand),
        "source_feature_bucket_v0": _source_feature_bucket_v0(
            normalized_tasks, outcomes_by_task_cand, features_by_task_cand
        ),
        "pack_source_feature_diagnostics": _pack_source_feature_diagnostics(
            normalized_tasks, packs, outcomes_by_task_cand, features_by_task_cand
        ),
        "breakdowns": _breakdowns(normalized_tasks, packs, outcomes_by_task_cand, features_by_task_cand),
        "score_phase_diagnostic_correlation": _score_phase_diagnostics(
            normalized_tasks, outcomes_by_task_cand, features_by_task_cand
        ),
    }

    conclusion_lines: list[str] = []
    if status not in {"ok", "self_test_only"}:
        conclusion_lines.append(
            "P52B Source-Backed Local Verifier Feature Matrix is ready; real per-task ephemeral P25 records and a repo root are required."
        )
        if reason:
            conclusion_lines.append(reason)
    else:
        if self_test:
            conclusion_lines.append(
                f"Self-test-only source-backed feature matrix diagnosed {candidate_denominator} synthetic candidates across {task_denominator} tasks; this is not quality evidence."
            )
        else:
            conclusion_lines.append(
                f"P52B computed source-backed verifier feature diagnostics for {candidate_denominator} candidates across {task_denominator} real ephemeral P25 records."
            )
        conclusion_lines.append(
            "P52B reads local source files only for bounded aggregate source-shape heuristics. "
            "Raw source text, snippets, digests, paths, and spans are not stored."
        )
        conclusion_lines.append(
            "Source-feature buckets are diagnostics only; they are not Evidence, do not admit candidates, "
            "and do not produce a verifier pass/fail score or default/promotion claim."
        )
        conclusion_lines.append(
            f"Bounded-span feature availability: {metric_blocks['source_backed_feature_availability']['bounded_span_feature_candidate_denominator']}/{candidate_denominator}; "
            f"heuristic feature availability rate: {metric_blocks['source_backed_feature_availability']['heuristic_feature_availability_rate']}."
        )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": "P52B Source-Backed Local Verifier Feature Matrix",
        "status": status,
        "status_reason": reason,
        "self_test": self_test,
        "not_quality_evidence": bool(self_test),
        "real_evaluation": bool(status == "ok" and not self_test),
        "input_sources": ["self_test"] if self_test else ["p25-policy-records-ephemeral-v1"],
        "input_source_count": input_source_count,
        "insufficient_input_source_count": insufficient_input_source_count,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "source_feature_not_evidence": True,
        "materialized_candidate_not_evidence": True,
        "verifier_not_evidence": True,
        "local_verifier_features_implemented": True,
        "local_verifier_score_available": False,
        "remote_calls_by_p52b": 0,
        "llm_calls_by_p52b": 0,
        "prompt_construction_by_p52b": False,
        "source_reads_attempted_by_p52b": source_reads_attempted,
        "source_reads_bounded_by_p52b": True,
        "raw_prompts_stored": False,
        "raw_query_stored": False,
        "raw_responses_stored": False,
        "raw_source_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_snippets_stored": False,
        "raw_text_stored": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "private_labels_committed": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
        "aggregate_only_public_artifact": True,
        "score_phase_only_metrics": True,
        "elapsed_ms": elapsed_ms,
        "task_count": task_denominator,
        "positive_task_count": sum(1 for t in normalized_tasks if t["has_gold"]),
        "no_gold_task_count": sum(1 for t in normalized_tasks if not t["has_gold"]),
        "candidate_pool_availability": candidate_pool_availability,
        "gold_span_availability": gold_span_availability,
        "reach_metrics_available": reach_metrics_available,
        "p31_h1_handoff_detected": p31_h1_handoff_detected,
        "p31_h1_handoff_detected_count": p31_h1_handoff_detected_count,
        "p33b_handoff_detected": p33b_handoff_detected,
        "p33b_handoff_detected_count": p33b_handoff_detected_count,
        **p52a_meta,
        **p52_meta,
        **p49_meta,
        **p50_meta,
        **p48_meta,
        "metrics": metric_blocks,
        "conclusion": conclusion_lines,
        "validation": {"forbidden_key_scan_ok": True},
    }

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P52B public report validation failed: {errors}")
    return report


def validate_public_report(report: dict[str, Any]) -> list[str]:
    """Validate schema, safety flags, and recursive forbidden-key scan."""
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("remote_calls_by_p52b") != 0:
        errors.append("remote_calls_by_p52b must be 0")
    if report.get("llm_calls_by_p52b") != 0:
        errors.append("llm_calls_by_p52b must be 0")
    if report.get("prompt_construction_by_p52b") is not False:
        errors.append("prompt_construction_by_p52b must be false")
    if report.get("source_reads_bounded_by_p52b") is not True:
        errors.append("source_reads_bounded_by_p52b must be true")

    expected_flags = {
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "source_feature_not_evidence": True,
        "materialized_candidate_not_evidence": True,
        "verifier_not_evidence": True,
        "local_verifier_features_implemented": True,
        "local_verifier_score_available": False,
        "aggregate_only_public_artifact": True,
        "score_phase_only_metrics": True,
        "raw_prompts_stored": False,
        "raw_query_stored": False,
        "raw_responses_stored": False,
        "raw_source_stored": False,
        "raw_text_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_snippets_stored": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "private_labels_committed": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
    }
    for flag, expected in expected_flags.items():
        if report.get(flag) is not expected:
            errors.append(f"{flag} must be {expected}")

    if report.get("self_test") and report.get("not_quality_evidence") is not True:
        errors.append("self_test must set not_quality_evidence=true")

    for forbidden in ("tasks", "records", "per_task_results", "decision_records"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    errors.extend(_reject_forbidden_keys(report))
    return errors


def _fmt_scalar(x: Any) -> str:
    return f"{x:.4f}" if isinstance(x, (int, float)) else "n/a"


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = ["# P52B Source-Backed Local Verifier Feature Matrix\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Remote calls by P52B: {report['remote_calls_by_p52b']}",
        f"- LLM calls by P52B: {report['llm_calls_by_p52b']}",
        f"- Prompt construction by P52B: {report['prompt_construction_by_p52b']}",
        f"- Source reads attempted by P52B: {report['source_reads_attempted_by_p52b']}",
        f"- Tasks: {report['task_count']} positive={report['positive_task_count']} no_gold={report['no_gold_task_count']}",
        f"- Candidate pool availability: `{report['candidate_pool_availability']}`",
        f"- P52A report source: `{report.get('p52a_report_source')}`",
        f"- P49 report source: `{report.get('p49_report_source')}`",
        f"- P50 report source: `{report.get('p50_report_source')}`",
        f"- P48 report source: `{report.get('p48_report_source')}`\n",
    ])

    if report["status"] not in {"ok", "self_test_only"}:
        lines.extend(["## Status", report.get("status_reason") or "", "", "Run with `--self-test` or supply ephemeral P25-policy records and a repo root.", ""])
        return "\n".join(lines)

    lines.extend([
        "## Purpose\n",
        "P52B computes deterministic source-backed verifier feature diagnostics from bounded local source reads. "
        "It is a SCORE-phase-only feature matrix, not a verifier pass/fail phase and not an Evidence producer.",
        "",
        "## Methodology\n",
        "- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).",
        "- Resolve a safe, local repo root for each task from `--repo-lock` or `--source-root` fallback using P52A helpers.",
        "- Normalize candidates with P46/P49 helpers, preserving only public metadata.",
        "- Perform bounded source reads per candidate, subject to P52A byte/line/file/candidate caps and secret-path/text scans.",
        "- Discard raw text after aggregate source-shape heuristics; never store source, snippets, digests, paths, or spans.",
        "- Classify each candidate into a source-feature risk bucket using bounded source shape and available metadata subtype signals.",
        "- Rebuild P49 packs in-memory and report aggregate pack-level source-feature diagnostics.",
        "- Gold/outcome signals are used only inside explicitly-marked SCORE-phase diagnostics `not_used_for_feature_construction=true`.",
        "",
        "## Safety notes\n",
        "- P52B does not create Evidence.",
        "- P52B does not validate EvidenceCore.",
        "- P52B does not admit candidates or change defaults.",
        "- P52B does not produce a verifier pass/fail score or a local verifier score.",
        "- Source-feature buckets are diagnostic only.",
        "- P52B does not prove P51 quality and does not send source to providers.",
        "- P52B does not call an LLM, construct prompts, or make remote calls.",
        "- P52B stores no raw source, snippets, digests, paths, or spans.",
        "",
    ])

    sm = report["metrics"]["source_materialization_metrics"]
    lines.append("## Source materialization metrics (P52A carry-forward)\n")
    lines.append("| Denom | Attempts | Success | Resolved | RangeValid | DigestMatch |")
    lines.append("|---:|---:|---:|---:|---:|---:|")
    lines.append(
        f"| {sm['candidate_denominator']} | {sm['source_read_attempt_count']} | {sm['source_read_success_count']} | "
        f"{sm['candidate_path_resolved_to_file_count']} | {sm['line_range_valid_count']} | {sm['candidate_digest_match_count']} |"
    )
    lines.append("")

    av = report["metrics"]["source_backed_feature_availability"]
    lines.append("## Source-backed feature availability\n")
    lines.append("| Denom | BoundedSpanCandidates | BoundedSpanRate | HeuristicAvailRate |")
    lines.append("|---:|---:|---:|---:|")
    lines.append(
        f"| {av['candidate_denominator']} | {av['bounded_span_feature_candidate_denominator']} | "
        f"{_fmt_scalar(av['bounded_span_feature_availability_rate'])} | {_fmt_scalar(av['heuristic_feature_availability_rate'])} |"
    )
    lines.append("")

    sf = report["metrics"]["source_shape_features"]
    lines.append("## Source-shape heuristic features\n")
    lines.append("| Feature | Checkable | PositiveRate |")
    lines.append("|---|---|---:|")
    for key in [
        "span_nonempty",
        "span_blank_only",
        "span_comment_only_heuristic",
        "span_contains_code_like_token",
        "span_contains_assignment_like_token",
        "span_contains_call_like_token",
        "span_contains_definition_keyword",
        "signature_like_line_heuristic",
        "import_only_heuristic",
        "test_assertion_like_heuristic",
    ]:
        block = sf[key]
        denom = block.get("checkable_count")
        pos_rate = block.get("heuristic_positive_rate") if "heuristic_positive_rate" in block else block.get("positive_rate")
        lines.append(f"| {key} | {denom} | {_fmt_scalar(pos_rate)} |")
    lines.append("")

    cons = sf["path_kind_vs_source_shape_consistency"]
    lines.append("## Source-vs-metadata consistency\n")
    lines.append("| Checkable | Consistent | SourceTestAssert | TestDefinition | DocConfigCode | WidthMatches |")
    lines.append("|---:|---:|---:|---:|---:|---:|")
    lines.append(
        f"| {cons['checkable_count']} | {_fmt_scalar(cons['consistent_rate'])} | "
        f"{_fmt_scalar(sf['source_file_with_test_assertion_like_span']['positive_rate'])} | "
        f"{_fmt_scalar(sf['test_file_with_source_definition_like_span']['positive_rate'])} | "
        f"{_fmt_scalar(sf['doc_config_path_with_code_like_span']['positive_rate'])} | "
        f"{_fmt_scalar(sf['candidate_span_width_matches_read_width']['matching_rate'])} |"
    )
    lines.append("")

    fb = report["metrics"]["source_feature_bucket_v0"]
    lines.append("## Source-feature bucket v0\n")
    lines.append("| Bucket | Count | Rate |")
    lines.append("|---|---:|---:|")
    for b in SOURCE_FEATURE_BUCKETS:
        lines.append(f"| {b} | {fb['risk_bucket_counts'][b]} | {_fmt_scalar(fb['risk_bucket_rates'][b])} |")
    lines.append("")

    pm = report["metrics"]["pack_source_feature_diagnostics"]["task_wide"]
    lines.append("## Pack source-feature diagnostics (task-wide)\n")
    lines.append("| Denom | LowRiskAnchor | HighRiskCand | AllAvail | AnyUnavail | AnyDigestMismatch | AnyCommentOnly | AnyImportOnly | AnySignatureLike | Diversity |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    lines.append(
        f"| {pm['pack_denominator']} | {_fmt_scalar(pm['pack_with_low_risk_anchor_rate'])} | "
        f"{_fmt_scalar(pm['pack_with_high_risk_candidate_rate'])} | {_fmt_scalar(pm['pack_all_candidates_source_features_available_rate'])} | "
        f"{_fmt_scalar(pm['pack_any_source_feature_unavailable_rate'])} | {_fmt_scalar(pm['pack_any_digest_mismatch_rate'])} | "
        f"{_fmt_scalar(pm['pack_any_comment_only_rate'])} | {_fmt_scalar(pm['pack_any_import_only_rate'])} | "
        f"{_fmt_scalar(pm['pack_any_signature_like_rate'])} | {_fmt_scalar(pm['pack_source_feature_diversity_rate'])} |"
    )
    lines.append(f"- Slot tagging: `{report['metrics']['pack_source_feature_diagnostics']['by_slot_availability']}`")
    lines.append("")

    sp = report["metrics"]["score_phase_diagnostic_correlation"]
    lines.append("## SCORE-phase diagnostic correlations (not used for feature construction)\n")
    lines.append("| Bucket | Candidates | GoldFile | GoldSpan | FileRightSpanWrong |")
    lines.append("|---:|---:|---:|---:|---:|")
    for b in SOURCE_FEATURE_BUCKETS:
        block = sp["by_source_feature_bucket"][b]
        lines.append(
            f"| {b} | {block['candidate_count']} | {_fmt_scalar(block['gold_file_rate'])} | "
            f"{_fmt_scalar(block['gold_span_rate'])} | {_fmt_scalar(block['file_right_span_wrong_rate'])} |"
        )
    lines.append("")
    lines.append(
        f"- No-gold high-risk candidate rate: {_fmt_scalar(sp['no_gold_high_risk_candidate_rate'])} "
        f"({sp['no_gold_high_risk_candidate_count']}/{sp['no_gold_candidate_denominator']})"
    )
    lines.append(
        f"- No-gold low-risk candidate rate: {_fmt_scalar(sp['no_gold_low_risk_candidate_rate'])} "
        f"({sp['no_gold_low_risk_candidate_count']}/{sp['no_gold_candidate_denominator']})"
    )
    lines.append(
        f"- Digest-mismatch gold-span rate: {_fmt_scalar(sp['digest_mismatch_gold_span_rate'])} "
        f"({sp['digest_mismatch_gold_span_count']})"
    )
    lines.append(
        f"- Comment-only gold-span rate: {_fmt_scalar(sp['comment_only_gold_span_rate'])} "
        f"({sp['comment_only_gold_span_count']})"
    )
    lines.append(
        f"- Signature-like gold-span rate: {_fmt_scalar(sp['signature_like_gold_span_rate'])} "
        f"({sp['signature_like_gold_span_count']})"
    )
    lines.append("")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="P52B Source-Backed Local Verifier Feature Matrix")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to ephemeral P25-policy JSON record files.")
    parser.add_argument("--repo-lock", type=Path, default=None, help="Repo lock JSON mapping repo_id -> source path.")
    parser.add_argument("--source-root", type=Path, default=None, help="Optional fallback repo root for all tasks.")
    parser.add_argument("--p52a-report", type=Path, default=None, help="Optional P52A report for enum/status carry-forward.")
    parser.add_argument("--p52-report", type=Path, default=None, help="Optional P52 report for enum/status carry-forward.")
    parser.add_argument("--p49-report", type=Path, default=None, help="Optional P49 report for enum/status carry-forward.")
    parser.add_argument("--p50-report", type=Path, default=None, help="Optional P50 report for enum/status carry-forward.")
    parser.add_argument("--p48-report", type=Path, default=None, help="Optional P48 report for enum/status carry-forward.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    args = parser.parse_args()

    start = time.monotonic()
    input_paths: list[Path] = []
    raw_input_records: list[dict[str, Any]] = []
    self_test_lock: Path | None = None
    self_test_root: Path | None = None

    if args.self_test:
        input_paths.append(Path("self_test"))
        raw_input_records, self_test_lock, self_test_root = _make_self_test_inputs()
    elif args.input:
        input_paths = list(args.input)
        raw_input_records = p25.load_p21_inputs(input_paths, require_ephemeral_schema=True)
    else:
        parser.error("Specify --self-test or --input PATH [PATH ...]")

    status = "self_test_only" if args.self_test else "ok"
    reason: str | None = None
    insufficient_count = 0
    task_records: list[dict[str, Any]] = []

    marker_reasons = {
        "_p25_input_summary_marker": "Aggregate summary lacks per-task ephemeral records required for P52B source-backed feature diagnostics.",
        "_p25_input_empty_marker": "Input artifact did not contain per-task ephemeral records.",
        "_p25_unsupported_schema_marker": "P52B requires p25-policy-records-ephemeral-v1 input schema.",
    }
    for rec in raw_input_records:
        marker = next((m for m in marker_reasons if rec.get(m)), None)
        if marker:
            status = "insufficient_task_detail"
            reason = marker_reasons[marker]
            insufficient_count += 1
            continue
        task_records.append(rec)

    if not task_records and status == "ok":
        status = "insufficient_task_detail"
        reason = "No per-task records found."

    normalized_tasks, raw_records = p52a._normalize_tasks(task_records)
    p52a._enrich_candidates_with_digest(raw_records, normalized_tasks)

    if status == "ok" and not normalized_tasks:
        status = "insufficient_task_detail"
        reason = "Records lacked required fields for P52B normalization."

    repo_lock_path = args.repo_lock or self_test_lock
    source_root = args.source_root or self_test_root

    elapsed_ms = int((time.monotonic() - start) * 1000)

    report = build_report(
        raw_records,
        normalized_tasks,
        self_test=args.self_test,
        elapsed_ms=elapsed_ms,
        status=status,
        reason=reason,
        input_source_count=1 if args.self_test else max(1, len(args.input or [])),
        insufficient_input_source_count=insufficient_count,
        repo_lock_path=repo_lock_path,
        source_root=source_root,
        p52a_report_path=args.p52a_report,
        p52_report_path=args.p52_report,
        p49_report_path=args.p49_report,
        p50_report_path=args.p50_report,
        p48_report_path=args.p48_report,
    )

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P52B report written to {args.out}")
    print(f"P52B markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
