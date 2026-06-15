#!/usr/bin/env python3
"""P52A Source Materialization / Local Verifier Prerequisite.

P52A is a narrow, bounded, local source-read bridge that exists only to diagnose
materialization prerequisites and source-required verifier availability.  It does
not implement a full verifier, does not pass/fail candidates, does not call an
LLM, and does not make remote calls.

Hard constraints:
* No remote calls; `remote_calls_by_p52a=0`.
* No LLM calls; `llm_calls_by_p52a=0`.
* No prompt construction; `prompt_construction_by_p52a=false`.
* Materialized candidate is NOT Evidence; `materialized_candidate_not_evidence=true`.
* Source read is NOT Evidence; `source_read_not_evidence=true`.
* Public/committed outputs are aggregate-only: no raw source, snippets, paths,
  spans, digests, task/candidate/repo identifiers, query text, or provider keys.
* Bounded local source reads with strict byte/line/file/candidate caps; raw text
  is discarded after counters and lightweight heuristics.
* Gold/outcomes are used only in explicitly-marked SCORE-phase diagnostics.
* No silent line-range clamping; invalid ranges are counted as invalid.
* Does not implement full verifier/pass/fail/evidence-valid.
"""

from __future__ import annotations

import argparse
import hashlib
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
import r32_embedding_view_bakeoff as r32

SCHEMA_VERSION = "p52a-source-materialization-prerequisite-v1"
GENERATED_BY = "eval/p52a_source_materialization_prerequisite.py"

DEFAULT_OUT = Path("artifacts/p52a_source_materialization_prerequisite/p52a_source_materialization_prerequisite_report.json")
DEFAULT_DOC = Path("docs/en/p52a-source-materialization-prerequisite.md")

MAX_CANDIDATES_PER_TASK = 8
MAX_TOTAL_CANDIDATES = 500
MAX_FILE_BYTES = 1_000_000
MAX_SPAN_LINES = 80
MAX_LINE_LENGTH = 2_000
MAX_TOTAL_BYTES_READ = 20_000_000

COMMENT_RE = re.compile(r"^\s*(#|//|/\*|\*|<!--|\"\"\"|''')")
SIGNATURE_RE = re.compile(
    r"^\s*(?:async\s+)?(?:def|fn|func|function|class|struct|enum|trait|interface|type|impl|module)\b",
    re.IGNORECASE,
)

FORBIDDEN_PUBLIC_KEYS = set(p52.FORBIDDEN_PUBLIC_KEYS) | {
    "task_id",
    "repo_id",
    "candidate_id",
    "path",
    "candidate_path",
    "source_root",
    "corpus_root",
    "repo_map",
    "start_line",
    "end_line",
    "content_sha",
    "sha",
    "hash",
    "digest_value",
    "gold",
    "gold_spans",
    "label",
    "labels",
    "query",
    "query_terms",
    "identifier",
    "symbol_text",
    "prompt",
    "snippet",
    "response",
    "source_text",
    "raw_text",
    "raw_source",
    "route_features",
    "provider",
    "provider_key",
    "base_url",
    "api_key",
    "records",
    "per_task",
    "per_candidate",
    "pack_items",
    "decision_records",
    "per_task_results",
    "digest",
}

P52A_SAFETY_FLAG_KEYS = set(p52.P52_SAFETY_FLAG_KEYS) | {
    # top-level flags
    "remote_calls_by_p52a",
    "llm_calls_by_p52a",
    "prompt_construction_by_p52a",
    "source_reads_attempted_by_p52a",
    "source_reads_bounded_by_p52a",
    "raw_source_stored",
    "raw_text_stored",
    "raw_snippets_stored",
    "raw_snippets_committed",
    "raw_snippets_sent_to_provider",
    "materialized_candidate_not_evidence",
    "source_read_not_evidence",
    "verifier_not_evidence",
    "raw_queries_in_artifact",
    "raw_candidate_paths_in_artifact",
    "raw_line_ranges_in_artifact",
    "raw_digests_in_artifact",
    # availability enums
    "source_root_availability",
    "repo_resolution_availability",
    "source_read_availability",
    "materialization_prerequisite_availability",
    # metric block names
    "source_materialization_metrics",
    "source_required_verifier_availability",
    "pack_materialization_metrics",
    "breakdowns",
    "score_phase_diagnostic_correlation",
    "candidate_denominator",
    "task_denominator",
    "source_read_attempt_count",
    "source_read_success_count",
    "source_read_success_rate",
    "source_read_budget_exceeded_count",
    "source_read_budget_exceeded_rate",
    "repo_resolution_rate",
    "candidate_path_resolved_to_file_rate",
    "candidate_path_resolved_to_file_count",
    "candidate_missing_file_rate",
    "candidate_missing_file_count",
    "candidate_invalid_path_rate",
    "candidate_invalid_path_count",
    "candidate_file_escape_reject_rate",
    "candidate_file_escape_reject_count",
    "candidate_file_too_large_rate",
    "candidate_file_too_large_count",
    "candidate_binary_or_decode_reject_rate",
    "candidate_binary_or_decode_reject_count",
    "candidate_secret_reject_rate",
    "candidate_secret_reject_count",
    "file_line_count_computable_rate",
    "file_line_count_computable_count",
    "line_range_present_rate",
    "line_range_present_count",
    "line_range_valid_rate",
    "line_range_valid_count",
    "line_range_invalid_start_count",
    "line_range_invalid_start_rate",
    "line_range_invalid_end_count",
    "line_range_invalid_end_rate",
    "line_range_reversed_count",
    "line_range_reversed_rate",
    "line_range_out_of_bounds_count",
    "line_range_out_of_bounds_rate",
    "line_range_clamped_count",
    "line_range_clamped_availability",
    "span_width_after_read_mean",
    "span_width_after_read_p95",
    "span_width_over_cap_count",
    "span_width_over_cap_rate",
    "content_digest_computable_rate",
    "content_digest_computable_count",
    "candidate_digest_present_rate",
    "candidate_digest_present_count",
    "candidate_digest_match_rate",
    "candidate_digest_match_count",
    "candidate_digest_mismatch_rate",
    "candidate_digest_mismatch_count",
    "candidate_digest_unavailable_rate",
    "candidate_digest_unavailable_count",
    "candidate_digest_semantics",
    "line_range_verified_against_current_file",
    "source_text_span_width_verified",
    "content_digest_verified",
    "comment_only_flag",
    "signature_like_line_heuristic",
    "ast_node_kind",
    "exact_identifier_in_span",
    "query_terms_in_span",
    "signature_match",
    "identifier_density",
    "term_density",
    "intent_identifier_match",
    "import_only_flag",
    "test_assertion_context",
    "availability",
    "checkable_count",
    "checkable_rate",
    "heuristic_positive_count",
    "heuristic_positive_rate",
    "unavailable_count",
    "unavailable_rate",
    "null_count",
    "null_rate",
    "value",
    "partial_heuristic_line_prefix_only",
    "partial_heuristic_regex_only",
    "unavailable_ast_parser_not_wired",
    "unavailable_raw_query_not_public",
    "unavailable_parser_not_wired",
    "diagnostic_only_not_evidencecore_validation",
    "not_performed_no_silent_clamp",
    "pack_denominator",
    "packs_with_all_candidates_resolved_rate",
    "packs_with_all_candidates_resolved_count",
    "packs_with_any_stale_digest_rate",
    "packs_with_any_stale_digest_count",
    "packs_with_any_invalid_range_rate",
    "packs_with_any_invalid_range_count",
    "packs_requiring_source_for_comment_or_signature_rate",
    "packs_requiring_source_for_comment_or_signature_count",
    "packs_with_materialization_prerequisite_available_rate",
    "packs_with_materialization_prerequisite_available_count",
    "by_candidate_strategy",
    "by_language",
    "by_source_class",
    "by_agreement_class",
    "by_rrf_backing",
    "by_public_bucket",
    "by_public_risk_tag",
    "gold_file_readable_rate",
    "gold_span_range_valid_rate",
    "gold_span_materialization_prerequisite_rate",
    "file_right_span_wrong_when_range_valid_rate",
    "no_gold_readable_candidate_rate",
    "no_gold_range_valid_candidate_rate",
    "not_used_for_materialization_decision",
    "repo_lock_source",
    "p52_report_source",
    "p52_quality_gate_status",
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


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P52A_SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def _read_optional_report(path: Path | None, report_name: str) -> dict[str, Any]:
    """Read optional upstream report and return only aggregate enum/status metadata."""
    source_key = f"{report_name}_report_source"
    status_key = f"{report_name}_quality_gate_status"
    not_provided = {
        source_key: "not_provided",
        status_key: "not_provided",
    }
    if path is None or not path.exists():
        return not_provided
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {source_key: "invalid_json", status_key: "not_provided"}

    result: dict[str, Any] = {source_key: "provided_report"}
    status = data.get("status") or data.get("quality_gate_status") or "not_provided"
    if not isinstance(status, str):
        status = "not_provided"
    result[status_key] = status
    return result


def _is_inside_root(full: Path, root: Path) -> bool:
    try:
        if root == full:
            return True
        # Path.parents includes direct ancestors; comparing as strings avoids OSError
        # on exotic paths while still being deterministic for resolved real paths.
        root_str = str(root)
        full_str = str(full)
        if full_str == root_str or full_str.startswith(root_str + os.sep):
            return True
        return False
    except Exception:
        return False


def _any_symlink_in_path(path: Path) -> bool:
    try:
        for part in [path, *path.parents]:
            if part.is_symlink():
                return True
        return False
    except Exception:
        return True


def _truncate_line(line: str) -> str:
    if len(line) > MAX_LINE_LENGTH:
        return line[:MAX_LINE_LENGTH]
    return line


def _has_signature_like_line(lines: list[str]) -> bool:
    for raw in lines:
        if SIGNATURE_RE.search(raw):
            return True
    return False


def _is_comment_only_span(lines: list[str]) -> bool:
    has_non_empty = False
    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            continue
        has_non_empty = True
        if not COMMENT_RE.match(raw):
            return False
    return has_non_empty


def _make_self_test_corpus(root: Path) -> dict[str, str]:
    """Create deterministic source files and return path->sha256 map."""
    contents: dict[str, str] = {}

    def add(rel: str, lines: list[str]) -> None:
        text = "\n".join(lines) + "\n"
        contents[rel] = text
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    app_lines: list[str] = []
    for i in range(1, 61):
        if i in (10, 11, 12, 13, 14, 15):
            app_lines.append(f"def handler_line_{i}():")
        elif i == 20:
            app_lines.append("class AppConfig:")
        elif i == 55:
            app_lines.append("    def validate(self):")
        elif i % 7 == 0:
            app_lines.append(f"# comment block line {i}")
        else:
            app_lines.append(f"value_{i} = {i}")
    add("py_flask/src/app.py", app_lines)

    noise_lines = [f"noise_{i} = {i}" for i in range(1, 21)]
    noise_lines[4] = "def noise_func():"
    add("js_express/src/noise.py", noise_lines)

    ambig_lines = [f"ambig_{i} = {i}" for i in range(1, 41)]
    ambig_lines[24] = "class AmbiguousTarget:"
    add("js_express/src/ambig.py", ambig_lines)

    # Extra file used for invalid-range / digest-mismatch diagnostics.
    add("py_flask/src/diag.py", [f"diag_{i} = {i}" for i in range(1, 11)])

    sha_map: dict[str, str] = {}
    for rel in contents:
        sha_map[rel] = hashlib.sha256((root / rel).read_bytes()).hexdigest()
    return sha_map


def _augment_self_test_records(records: list[dict[str, Any]], sha_map: dict[str, str]) -> list[dict[str, Any]]:
    """Inject deterministic content_sha values and an invalid-candidate task."""
    records = [dict(r) for r in records]

    def find_candidate(task_id: str, strategy: str, path: str, start: int, end: int) -> dict[str, Any] | None:
        for r in records:
            if r.get("task_id") != task_id:
                continue
            pool = r.get("p31_candidate_pools", {}).get(strategy, [])
            for cand in pool:
                if (
                    cand.get("path") == path
                    and cand.get("start_line") == start
                    and cand.get("end_line") == end
                ):
                    return cand
        return None

    # Correct digest for the first positive task anchor.
    c1 = find_candidate("p46-st-001", "candidate_baseline", "src/app.py", 10, 15)
    if c1 is not None:
        c1["content_sha"] = sha_map.get("py_flask/src/app.py")

    # Intentional mismatch for the second task.
    c2 = find_candidate("p46-st-002", "candidate_baseline", "src/app.py", 50, 55)
    if c2 is not None:
        c2["content_sha"] = "0" * 64

    # Task designed to exercise rejection paths.
    records.append({
        "task_id": "p52a-st-invalid",
        "repo_id": "py_flask",
        "task_bucket": "ambiguous",
        "task_risk_tags": ["ambiguous"],
        "score_group": "no_gold",
        "route_features": {"candidate_count": 6, "candidate_support_exists": True, "query_noise": 0.3},
        "p31_candidate_pools": {
            "candidate_baseline": [
                {"rank": 1, "path": "../escape.py", "start_line": 1, "end_line": 5, "candidate_id": "bad_escape"},
                {"rank": 2, "path": "src/app.py", "start_line": 0, "end_line": 5, "candidate_id": "bad_start"},
                {"rank": 3, "path": "src/app.py", "start_line": 5, "end_line": 3, "candidate_id": "bad_reversed"},
                {"rank": 4, "path": "src/app.py", "start_line": 50, "end_line": 200, "candidate_id": "bad_oob"},
                {"rank": 5, "path": "src/missing.py", "start_line": 1, "end_line": 5, "candidate_id": "bad_missing"},
                {"rank": 6, "path": "config/sk-abcdefghijklmnopqrstuv.txt", "start_line": 1, "end_line": 2, "candidate_id": "bad_secret"},
                {"rank": 7, "path": "src/diag.py", "start_line": 1, "end_line": 5, "content_sha": "0" * 64, "candidate_id": "bad_digest"},
            ],
        },
        "p31_score_gold": {"has_gold": False, "gold_spans": []},
    })
    return records


def _make_self_test_inputs() -> tuple[list[dict[str, Any]], Path, Path]:
    """Return ephemeral records, repo-lock path, and corpus root for self-test."""
    tmp = Path(tempfile.mkdtemp(prefix="p52a-self-test-"))
    root = tmp / "corpus"
    root.mkdir(parents=True, exist_ok=True)
    sha_map = _make_self_test_corpus(root)
    records = _augment_self_test_records(p46.make_self_test_records(), sha_map)

    lock = tmp / "repo-lock.json"
    lock_entries: list[dict[str, Any]] = []
    for repo_id in {"py_flask", "js_express"}:
        repo_path = root / repo_id
        if repo_path.exists():
            lock_entries.append({"repo_id": repo_id, "source": {"path": str(repo_path.resolve())}})
    lock.write_text(json.dumps(lock_entries, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return records, lock, root


def _determine_repo_roots(
    tasks: list[dict[str, Any]],
    repo_lock_path: Path | None,
    source_root: Path | None,
) -> tuple[dict[str, Path | None], dict[str, str]]:
    """Map each task to a resolved root and repo-resolution metadata.

    Never returns real paths in metadata; only enum/status strings.
    """
    repo_lock_source = "not_provided"
    repo_resolution: dict[str, Path | None] = {}
    lock_map: dict[str, Path] = {}

    if repo_lock_path is not None:
        if not repo_lock_path.exists():
            repo_lock_source = "not_provided"
        else:
            try:
                lock_map = r32.load_repo_lock(repo_lock_path)
                repo_lock_source = "provided"
            except Exception:
                repo_lock_source = "invalid_json"

    source_root_source = "not_provided"
    fallback_root: Path | None = None
    if source_root is not None:
        if not source_root.exists() or not source_root.is_dir():
            source_root_source = "invalid"
        elif not os.access(source_root, os.R_OK | os.X_OK):
            source_root_source = "inaccessible"
        else:
            source_root_source = "provided"
            fallback_root = source_root.resolve()

    for task in tasks:
        repo_id = _as_str(task.get("repo_id"))
        root: Path | None = None
        if lock_map and repo_id and repo_id in lock_map:
            root = lock_map[repo_id]
        elif fallback_root is not None:
            # Source-root fallback applies to all tasks.
            root = fallback_root
        repo_resolution[task["task_id"]] = root

    return repo_resolution, {
        "repo_lock_source": repo_lock_source,
        "source_root_source": source_root_source,
    }


def _resolve_candidate_path(path_str: str, root: Path) -> Path | None:
    """Return resolved path if safe; None if escape/symlink/invalid."""
    if not path_str:
        return None
    rel = Path(path_str)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    try:
        full = (root / rel).resolve()
    except Exception:
        return None
    if not _is_inside_root(full, root):
        return None
    if _any_symlink_in_path(full):
        return None
    return full


def _read_source_file(
    full: Path,
    total_bytes_read: int,
) -> tuple[str | None, bytes | None, int, str | None]:
    """Bounded, safe source-file read.  Returns (text, bytes, bytes_read, reason).

    Reason is None on success, otherwise a short aggregation token.
    """
    try:
        size = full.stat().st_size
    except Exception:
        return None, None, 0, "missing_file"
    if full.is_dir():
        return None, None, 0, "missing_file"
    if size > MAX_FILE_BYTES:
        return None, None, 0, "file_too_large"
    if total_bytes_read + size > MAX_TOTAL_BYTES_READ:
        return None, None, 0, "budget_exceeded"
    try:
        raw = full.read_bytes()
    except Exception:
        return None, None, 0, "missing_file"
    if b"\x00" in raw:
        return None, None, len(raw), "binary_or_decode"
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None, None, len(raw), "binary_or_decode"
    if r32.text_has_secret(text):
        return None, None, len(raw), "secret_reject"
    return text, raw, len(raw), None


def _process_candidate_source(
    task: dict[str, Any],
    cand: dict[str, Any],
    root: Path | None,
    total_bytes_read: int,
) -> tuple[dict[str, Any], int]:
    """Return outcome dict and updated total_bytes_read for one candidate."""
    path = _as_str(cand.get("_path"))
    start = _as_int(cand.get("_start")) or 0
    end = _as_int(cand.get("_end")) or 0
    content_sha = _as_str(cand.get("content_sha"))

    outcome: dict[str, Any] = {
        "source_root_unavailable": False,
        "path_invalid": False,
        "path_secret": False,
        "escape_reject": False,
        "missing_file": False,
        "file_too_large": False,
        "binary_or_decode": False,
        "secret_text": False,
        "budget_exceeded": False,
        "source_read_success": False,
        "line_count": None,
        "range_present": False,
        "range_valid": False,
        "range_invalid_start": False,
        "range_invalid_end": False,
        "range_reversed": False,
        "range_out_of_bounds": False,
        "span_width": None,
        "span_over_cap": False,
        "digest_present": bool(content_sha),
        "digest_match": None,
        "digest_mismatch": None,
        "heuristic_comment": None,
        "heuristic_signature": None,
        "language": "unknown",
    }

    if root is None:
        # No source root for this task; keep this distinct from missing files
        # under a known checkout. This is an unavailable-source condition, not a
        # failed source-read attempt.
        outcome["source_root_unavailable"] = True
        return outcome, total_bytes_read

    if not p46._has_valid_path({"path": path}):
        outcome["path_invalid"] = True
        return outcome, total_bytes_read

    if r32.text_has_secret(path):
        outcome["path_secret"] = True
        return outcome, total_bytes_read

    full = _resolve_candidate_path(path, root)
    if full is None:
        outcome["escape_reject"] = True
        return outcome, total_bytes_read

    text, raw, bytes_read, reason = _read_source_file(full, total_bytes_read)
    total_bytes_read += bytes_read

    if reason == "missing_file":
        outcome["missing_file"] = True
        return outcome, total_bytes_read
    if reason == "file_too_large":
        outcome["file_too_large"] = True
        return outcome, total_bytes_read
    if reason == "budget_exceeded":
        outcome["budget_exceeded"] = True
        return outcome, total_bytes_read
    if reason == "binary_or_decode":
        outcome["binary_or_decode"] = True
        return outcome, total_bytes_read
    if reason == "secret_reject":
        outcome["secret_text"] = True
        return outcome, total_bytes_read

    if text is None or raw is None:
        outcome["missing_file"] = True
        return outcome, total_bytes_read

    outcome["source_read_success"] = True
    outcome["line_count"] = len(text.splitlines())
    outcome["language"] = r32.ext_to_language(path)

    # Digest comparison is diagnostic only; the digest value is never stored.
    if content_sha:
        actual = hashlib.sha256(raw).hexdigest()
        if actual == content_sha:
            outcome["digest_match"] = True
        else:
            outcome["digest_mismatch"] = True

    # Range classification.
    if start != 0 or end != 0:
        outcome["range_present"] = True
        if start <= 0:
            outcome["range_invalid_start"] = True
        elif end <= 0:
            outcome["range_invalid_end"] = True
        elif end < start:
            outcome["range_reversed"] = True
        else:
            if outcome["line_count"] is not None and end <= outcome["line_count"]:
                outcome["range_valid"] = True
                outcome["span_width"] = end - start + 1
                if outcome["span_width"] > MAX_SPAN_LINES:
                    outcome["span_over_cap"] = True
                    return outcome, total_bytes_read
                # Bounded heuristics use only lines inside the declared span.
                lines = [
                    _truncate_line(line)
                    for i, line in enumerate(text.splitlines(), start=1)
                    if start <= i <= end
                ]
                outcome["heuristic_comment"] = _is_comment_only_span(lines)
                outcome["heuristic_signature"] = _has_signature_like_line(lines)
            else:
                outcome["range_out_of_bounds"] = True

    return outcome, total_bytes_read


def _materialization_prereq_ok(outcome: dict[str, Any]) -> bool:
    """Candidate-level prerequisite success, not Evidence validity."""
    return bool(
        outcome.get("source_read_success")
        and outcome.get("range_valid")
        and not outcome.get("span_over_cap")
        and outcome.get("digest_mismatch") is not True
    )


def _build_candidate_content_sha_lookup(tasks: list[dict[str, Any]]) -> dict[tuple[str, str, str, int, int], str]:
    """Map (task_id, strategy, lower_path, start, end) to a raw content_sha if any."""
    lookup: dict[tuple[str, str, str, int, int], str] = {}
    for task in tasks:
        tid = _as_str(task.get("task_id"))
        pools = task.get("p31_candidate_pools") or task.get("candidate_pool") or task.get("pools", {})
        if not isinstance(pools, dict):
            continue
        for strategy, items in pools.items():
            if not isinstance(items, list):
                continue
            for cand in items:
                if not isinstance(cand, dict):
                    continue
                path = str(cand.get("path") or "").lower()
                start = _as_int(cand.get("start_line")) or 0
                end = _as_int(cand.get("end_line")) or 0
                sha = _as_str(cand.get("content_sha"))
                key = (tid, str(strategy), path, start, end)
                if sha and key not in lookup:
                    lookup[key] = sha
    return lookup


def _enrich_candidates_with_digest(
    tasks: list[dict[str, Any]],
    normalized_tasks: list[dict[str, Any]],
) -> None:
    """Attach content_sha from raw pools onto normalized candidates in-place."""
    lookup = _build_candidate_content_sha_lookup(tasks)
    for nt in normalized_tasks:
        tid = _as_str(nt.get("task_id"))
        for cand in nt.get("_candidates", []):
            path = _as_str(cand.get("_path"))
            start = _as_int(cand.get("_start")) or 0
            end = _as_int(cand.get("_end")) or 0
            for strategy in cand.get("source_strategies", []):
                key = (tid, str(strategy), path, start, end)
                if key in lookup:
                    cand["content_sha"] = lookup[key]
                    break


def _source_materialization_metrics(
    outcomes: list[dict[str, Any]],
    candidate_denominator: int,
) -> dict[str, Any]:
    attempted = sum(
        1
        for o in outcomes
        if o["path_invalid"]
        or o["path_secret"]
        or o["escape_reject"]
        or o["source_read_success"]
        or o["missing_file"]
        or o["file_too_large"]
        or o["binary_or_decode"]
        or o["secret_text"]
        or o["budget_exceeded"]
    )
    success = sum(1 for o in outcomes if o["source_read_success"])
    budget_exceeded = sum(1 for o in outcomes if o["budget_exceeded"])
    source_root_unavailable = sum(1 for o in outcomes if o["source_root_unavailable"])

    resolved_count = sum(1 for o in outcomes if o["source_read_success"])
    missing_count = sum(1 for o in outcomes if o["missing_file"])
    invalid_path_count = sum(1 for o in outcomes if o["path_invalid"] or o["path_secret"])
    escape_count = sum(1 for o in outcomes if o["escape_reject"])
    too_large_count = sum(1 for o in outcomes if o["file_too_large"])
    binary_count = sum(1 for o in outcomes if o["binary_or_decode"])
    secret_count = sum(1 for o in outcomes if o["secret_text"] or o["path_secret"])

    line_count_computable = sum(1 for o in outcomes if o["line_count"] is not None)
    range_present = sum(1 for o in outcomes if o["range_present"])
    range_valid = sum(1 for o in outcomes if o["range_valid"])
    invalid_start = sum(1 for o in outcomes if o["range_invalid_start"])
    invalid_end = sum(1 for o in outcomes if o["range_invalid_end"])
    reversed_count = sum(1 for o in outcomes if o["range_reversed"])
    out_of_bounds = sum(1 for o in outcomes if o["range_out_of_bounds"])

    widths = [o["span_width"] for o in outcomes if o["span_width"] is not None]
    over_cap = sum(1 for o in outcomes if o["span_over_cap"])

    digest_present = sum(1 for o in outcomes if o["digest_present"])
    digest_match = sum(1 for o in outcomes if o["digest_match"] is True)
    digest_mismatch = sum(1 for o in outcomes if o["digest_mismatch"] is True)
    digest_unavailable = sum(1 for o in outcomes if not o["digest_present"])
    digest_computable = sum(1 for o in outcomes if o["digest_present"] and o["source_read_success"])

    return {
        "candidate_denominator": candidate_denominator,
        "source_read_attempt_count": attempted,
        "source_read_success_count": success,
        "source_read_success_rate": _rate(success, attempted),
        "source_read_budget_exceeded_count": budget_exceeded,
        "source_read_budget_exceeded_rate": _rate(budget_exceeded, candidate_denominator),
        "source_root_unavailable_count": source_root_unavailable,
        "source_root_unavailable_rate": _rate(source_root_unavailable, candidate_denominator),
        "repo_resolution_rate": _rate(resolved_count, candidate_denominator),
        "candidate_path_resolved_to_file_rate": _rate(resolved_count, candidate_denominator),
        "candidate_path_resolved_to_file_count": resolved_count,
        "candidate_missing_file_rate": _rate(missing_count, candidate_denominator),
        "candidate_missing_file_count": missing_count,
        "candidate_invalid_path_rate": _rate(invalid_path_count, candidate_denominator),
        "candidate_invalid_path_count": invalid_path_count,
        "candidate_file_escape_reject_rate": _rate(escape_count, candidate_denominator),
        "candidate_file_escape_reject_count": escape_count,
        "candidate_file_too_large_rate": _rate(too_large_count, candidate_denominator),
        "candidate_file_too_large_count": too_large_count,
        "candidate_binary_or_decode_reject_rate": _rate(binary_count, candidate_denominator),
        "candidate_binary_or_decode_reject_count": binary_count,
        "candidate_secret_reject_rate": _rate(secret_count, candidate_denominator),
        "candidate_secret_reject_count": secret_count,
        "file_line_count_computable_rate": _rate(line_count_computable, candidate_denominator),
        "file_line_count_computable_count": line_count_computable,
        "line_range_present_rate": _rate(range_present, candidate_denominator),
        "line_range_present_count": range_present,
        "line_range_valid_rate": _rate(range_valid, candidate_denominator),
        "line_range_valid_count": range_valid,
        "line_range_invalid_start_count": invalid_start,
        "line_range_invalid_start_rate": _rate(invalid_start, candidate_denominator),
        "line_range_invalid_end_count": invalid_end,
        "line_range_invalid_end_rate": _rate(invalid_end, candidate_denominator),
        "line_range_reversed_count": reversed_count,
        "line_range_reversed_rate": _rate(reversed_count, candidate_denominator),
        "line_range_out_of_bounds_count": out_of_bounds,
        "line_range_out_of_bounds_rate": _rate(out_of_bounds, candidate_denominator),
        "line_range_clamped_count": None,
        "line_range_clamped_availability": "not_performed_no_silent_clamp",
        "span_width_after_read_mean": _avg([float(w) for w in widths]),
        "span_width_after_read_p95": _percentile(widths, 0.95),
        "span_width_over_cap_count": over_cap,
        "span_width_over_cap_rate": _rate(over_cap, candidate_denominator),
        "content_digest_computable_rate": _rate(digest_computable, candidate_denominator),
        "content_digest_computable_count": digest_computable,
        "candidate_digest_present_rate": _rate(digest_present, candidate_denominator),
        "candidate_digest_present_count": digest_present,
        "candidate_digest_match_rate": _rate(digest_match, candidate_denominator),
        "candidate_digest_match_count": digest_match,
        "candidate_digest_mismatch_rate": _rate(digest_mismatch, candidate_denominator),
        "candidate_digest_mismatch_count": digest_mismatch,
        "candidate_digest_unavailable_rate": _rate(digest_unavailable, candidate_denominator),
        "candidate_digest_unavailable_count": digest_unavailable,
        "candidate_digest_semantics": "diagnostic_only_not_evidencecore_validation",
    }


def _source_required_verifier_availability(
    outcomes: list[dict[str, Any]],
    candidate_denominator: int,
) -> dict[str, Any]:
    valid_count = sum(1 for o in outcomes if o["range_valid"])
    checkable_width = sum(1 for o in outcomes if o["range_valid"] and (o["span_width"] or 0) <= MAX_SPAN_LINES)
    digest_present_count = sum(1 for o in outcomes if o["digest_present"])
    digest_match_count = sum(1 for o in outcomes if o["digest_match"] is True)
    digest_mismatch_count = sum(1 for o in outcomes if o["digest_mismatch"] is True)

    checkable_comment = sum(1 for o in outcomes if o["heuristic_comment"] is not None)
    positive_comment = sum(1 for o in outcomes if o["heuristic_comment"] is True)
    checkable_signature = sum(1 for o in outcomes if o["heuristic_signature"] is not None)
    positive_signature = sum(1 for o in outcomes if o["heuristic_signature"] is True)

    def _null_unavailable(availability: str) -> dict[str, Any]:
        return {
            "availability": availability,
            "checkable_count": None,
            "checkable_rate": None,
            "null_count": candidate_denominator,
            "null_rate": 1.0 if candidate_denominator > 0 else None,
            "value": None,
        }

    return {
        "line_range_verified_against_current_file": {
            "availability": "available" if valid_count > 0 else "not_applicable_no_valid_range",
            "checkable_count": valid_count,
            "checkable_rate": _rate(valid_count, candidate_denominator),
        },
        "source_text_span_width_verified": {
            "availability": "available" if checkable_width > 0 else "not_applicable_no_valid_range",
            "checkable_count": checkable_width,
            "checkable_rate": _rate(checkable_width, candidate_denominator),
        },
        "content_digest_verified": {
            "availability": "available_if_candidate_digest_present",
            "checkable_count": digest_present_count,
            "checkable_rate": _rate(digest_present_count, candidate_denominator),
            "match_count": digest_match_count,
            "match_rate": _rate(digest_match_count, candidate_denominator),
            "mismatch_count": digest_mismatch_count,
            "mismatch_rate": _rate(digest_mismatch_count, candidate_denominator),
        },
        "comment_only_flag": {
            "availability": "partial_heuristic_line_prefix_only",
            "checkable_count": checkable_comment,
            "checkable_rate": _rate(checkable_comment, candidate_denominator),
            "heuristic_positive_count": positive_comment,
            "heuristic_positive_rate": _rate(positive_comment, candidate_denominator),
        },
        "signature_like_line_heuristic": {
            "availability": "partial_heuristic_regex_only",
            "checkable_count": checkable_signature,
            "checkable_rate": _rate(checkable_signature, candidate_denominator),
            "heuristic_positive_count": positive_signature,
            "heuristic_positive_rate": _rate(positive_signature, candidate_denominator),
        },
        "ast_node_kind": _null_unavailable("unavailable_ast_parser_not_wired"),
        "exact_identifier_in_span": _null_unavailable("unavailable_raw_query_not_public"),
        "query_terms_in_span": _null_unavailable("unavailable_raw_query_not_public"),
        "signature_match": _null_unavailable("unavailable_parser_not_wired"),
        "identifier_density": _null_unavailable("unavailable_parser_not_wired"),
        "term_density": _null_unavailable("unavailable_raw_query_not_public"),
        "intent_identifier_match": _null_unavailable("unavailable_raw_query_not_public"),
        "import_only_flag": _null_unavailable("unavailable_parser_not_wired"),
        "test_assertion_context": _null_unavailable("unavailable_parser_not_wired"),
    }


def _compute_strategy_packs(tasks: list[dict[str, Any]]) -> dict[tuple[int, str], dict[str, Any]]:
    """Build P49 packs per task/strategy in memory only."""
    packs: dict[tuple[int, str], dict[str, Any]] = {}
    for idx, task in enumerate(tasks):
        candidates = p49._normalize_candidates(task)
        for strategy in p49.PACK_STRATEGIES:
            packs[(idx, strategy)] = p49._build_pack(candidates, strategy)
    return packs


def _pack_materialization_metrics(
    tasks: list[dict[str, Any]],
    packs: dict[tuple[int, str], dict[str, Any]],
    outcomes_by_task_cand: dict[tuple[int, int], dict[str, Any]],
) -> dict[str, Any]:
    overall = {
        "pack_denominator": 0,
        "packs_with_all_candidates_resolved_count": 0,
        "packs_with_any_stale_digest_count": 0,
        "packs_with_any_invalid_range_count": 0,
        "packs_requiring_source_for_comment_or_signature_count": 0,
        "packs_with_materialization_prerequisite_available_count": 0,
    }
    by_strategy: dict[str, dict[str, Any]] = {
        strategy: {
            "pack_denominator": 0,
            "packs_with_all_candidates_resolved_count": 0,
            "packs_with_any_stale_digest_count": 0,
            "packs_with_any_invalid_range_count": 0,
            "packs_requiring_source_for_comment_or_signature_count": 0,
            "packs_with_materialization_prerequisite_available_count": 0,
        }
        for strategy in p49.PACK_STRATEGIES
    }

    for (task_idx, strategy), pack in packs.items():
        selected = pack.get("selected", [])
        if not selected:
            continue
        overall["pack_denominator"] += 1
        by_strategy[strategy]["pack_denominator"] += 1

        all_resolved = True
        any_stale = False
        any_invalid_range = False
        requires_source = False
        all_prereq = True

        for cand in selected:
            outcome = outcomes_by_task_cand.get((task_idx, cand.get("_id"))) or {}
            if not outcome.get("source_read_success"):
                all_resolved = False
                all_prereq = False
            if outcome.get("digest_mismatch"):
                any_stale = True
                all_prereq = False
            if outcome.get("span_over_cap"):
                all_prereq = False
            if not outcome.get("range_valid"):
                any_invalid_range = True
                all_prereq = False
            if cand.get("path_kind") == "source" and outcome.get("range_valid"):
                requires_source = True
        else:
            # Empty selected means the loop body did not run; all_* remain true.
            pass

        if all_resolved:
            overall["packs_with_all_candidates_resolved_count"] += 1
            by_strategy[strategy]["packs_with_all_candidates_resolved_count"] += 1
        if any_stale:
            overall["packs_with_any_stale_digest_count"] += 1
            by_strategy[strategy]["packs_with_any_stale_digest_count"] += 1
        if any_invalid_range:
            overall["packs_with_any_invalid_range_count"] += 1
            by_strategy[strategy]["packs_with_any_invalid_range_count"] += 1
        if requires_source:
            overall["packs_requiring_source_for_comment_or_signature_count"] += 1
            by_strategy[strategy]["packs_requiring_source_for_comment_or_signature_count"] += 1
        if all_prereq and selected:
            overall["packs_with_materialization_prerequisite_available_count"] += 1
            by_strategy[strategy]["packs_with_materialization_prerequisite_available_count"] += 1

    def finalize(block: dict[str, Any]) -> dict[str, Any]:
        denom = block["pack_denominator"]
        return {
            "pack_denominator": denom,
            "packs_with_all_candidates_resolved_rate": _rate(block["packs_with_all_candidates_resolved_count"], denom),
            "packs_with_all_candidates_resolved_count": block["packs_with_all_candidates_resolved_count"],
            "packs_with_any_stale_digest_rate": _rate(block["packs_with_any_stale_digest_count"], denom),
            "packs_with_any_stale_digest_count": block["packs_with_any_stale_digest_count"],
            "packs_with_any_invalid_range_rate": _rate(block["packs_with_any_invalid_range_count"], denom),
            "packs_with_any_invalid_range_count": block["packs_with_any_invalid_range_count"],
            "packs_requiring_source_for_comment_or_signature_rate": _rate(block["packs_requiring_source_for_comment_or_signature_count"], denom),
            "packs_requiring_source_for_comment_or_signature_count": block["packs_requiring_source_for_comment_or_signature_count"],
            "packs_with_materialization_prerequisite_available_rate": _rate(block["packs_with_materialization_prerequisite_available_count"], denom),
            "packs_with_materialization_prerequisite_available_count": block["packs_with_materialization_prerequisite_available_count"],
        }

    return {
        "task_wide": finalize(overall),
        "by_pack_strategy": {strategy: finalize(by_strategy[strategy]) for strategy in p49.PACK_STRATEGIES},
    }


def _breakdowns(
    tasks: list[dict[str, Any]],
    normalized_tasks: list[dict[str, Any]],
    outcomes_by_task_cand: dict[tuple[int, int], dict[str, Any]],
) -> dict[str, Any]:
    def make_bucket() -> dict[str, Any]:
        return {
            "candidate_count": 0,
            "source_read_success_count": 0,
            "range_valid_count": 0,
            "digest_match_count": 0,
        }

    breakdowns: dict[str, dict[str, dict[str, Any]]] = {
        "by_candidate_strategy": defaultdict(make_bucket),
        "by_path_kind": defaultdict(make_bucket),
        "by_language": defaultdict(make_bucket),
        "by_source_class": defaultdict(make_bucket),
        "by_agreement_class": defaultdict(make_bucket),
        "by_rrf_backing": defaultdict(make_bucket),
        "by_public_bucket": defaultdict(make_bucket),
        "by_public_risk_tag": defaultdict(make_bucket),
    }

    for task_idx, task in enumerate(normalized_tasks):
        bucket = p25.sanitize_public_bucket(task.get("task_bucket", "unknown"))
        risk_tags = task.get("task_risk_tags", [])
        for cand in task.get("_candidates", []):
            outcome = outcomes_by_task_cand.get((task_idx, cand.get("_id"))) or {}
            sub = cand.get("subtype") or {}
            source_class = sub.get("source_class") if isinstance(sub, dict) else "other"
            agreement_class = sub.get("agreement_class") if isinstance(sub, dict) else "other"
            rrf = "rrf_yes" if p49._has_rrf_backing(cand) else "rrf_no"

            dimensions: dict[str, str] = {
                "by_candidate_strategy": _as_str(cand.get("source_strategy") or "unknown"),
                "by_path_kind": _as_str(cand.get("path_kind") or "unknown"),
                "by_language": _as_str(outcome.get("language") or "unknown"),
                "by_source_class": _as_str(source_class or "other"),
                "by_agreement_class": _as_str(agreement_class or "other"),
                "by_rrf_backing": rrf,
                "by_public_bucket": bucket,
                "by_public_risk_tag": risk_tags[0] if risk_tags else "other",
            }

            for dim_name, dim_value in dimensions.items():
                b = breakdowns[dim_name][dim_value]
                b["candidate_count"] += 1
                if outcome.get("source_read_success"):
                    b["source_read_success_count"] += 1
                if outcome.get("range_valid"):
                    b["range_valid_count"] += 1
                if outcome.get("digest_match") is True:
                    b["digest_match_count"] += 1

    def finalize_bucket(b: dict[str, Any]) -> dict[str, Any]:
        denom = b["candidate_count"]
        return {
            "candidate_count": denom,
            "source_read_success_rate": _rate(b["source_read_success_count"], denom),
            "range_valid_rate": _rate(b["range_valid_count"], denom),
            "digest_match_rate": _rate(b["digest_match_count"], denom),
        }

    result: dict[str, Any] = {}
    for dim_name, dim_map in breakdowns.items():
        result[dim_name] = {k: finalize_bucket(v) for k, v in sorted(dim_map.items())}
    return result


def _score_phase_diagnostics(
    tasks: list[dict[str, Any]],
    normalized_tasks: list[dict[str, Any]],
    packs: dict[tuple[int, str], dict[str, Any]],
    outcomes_by_task_cand: dict[tuple[int, int], dict[str, Any]],
) -> dict[str, Any]:
    positive_tasks = [
        (idx, t)
        for idx, t in enumerate(normalized_tasks)
        if t.get("has_gold") and t.get("has_gold_spans")
    ]
    no_gold_tasks = [t for t in normalized_tasks if not t.get("has_gold")]

    gold_file_readable = 0
    gold_span_range_valid = 0
    gold_span_prereq = 0
    frsw_range_valid_count = 0
    frsw_range_valid_denom = 0

    for task_idx, task in positive_tasks:
        label = task.get("label", {})
        for cand in task.get("_candidates", []):
            outcome = outcomes_by_task_cand.get((task_idx, cand.get("_id"))) or {}
            if p49._file_in_gold(cand, label) and outcome.get("source_read_success"):
                gold_file_readable += 1
                break
        else:
            continue
        for cand in task.get("_candidates", []):
            outcome = outcomes_by_task_cand.get((task_idx, cand.get("_id"))) or {}
            if p49._span_overlaps_gold(cand, label) and outcome.get("range_valid"):
                gold_span_range_valid += 1
                break
        for cand in task.get("_candidates", []):
            outcome = outcomes_by_task_cand.get((task_idx, cand.get("_id"))) or {}
            if p49._span_overlaps_gold(cand, label) and _materialization_prereq_ok(outcome):
                gold_span_prereq += 1
                break
        for cand in task.get("_candidates", []):
            outcome = outcomes_by_task_cand.get((task_idx, cand.get("_id"))) or {}
            if p49._file_in_gold(cand, label) and outcome.get("range_valid"):
                frsw_range_valid_denom += 1
                if not p49._span_overlaps_gold(cand, label):
                    frsw_range_valid_count += 1

    no_gold_readable = 0
    no_gold_range_valid = 0
    for task in no_gold_tasks:
        # Count once per task if any candidate across all packs satisfies condition.
        task_idx = normalized_tasks.index(task)
        if any(
            outcomes_by_task_cand.get((task_idx, c.get("_id")), {}).get("source_read_success")
            for c in task.get("_candidates", [])
        ):
            no_gold_readable += 1
        if any(
            outcomes_by_task_cand.get((task_idx, c.get("_id")), {}).get("range_valid")
            for c in task.get("_candidates", [])
        ):
            no_gold_range_valid += 1

    positive_denom = len(positive_tasks)
    no_gold_denom = len(no_gold_tasks)

    return {
        "not_used_for_materialization_decision": True,
        "gold_file_readable_rate": _rate(gold_file_readable, positive_denom),
        "gold_file_readable_count": gold_file_readable,
        "gold_span_range_valid_rate": _rate(gold_span_range_valid, positive_denom),
        "gold_span_range_valid_count": gold_span_range_valid,
        "gold_span_materialization_prerequisite_rate": _rate(gold_span_prereq, positive_denom),
        "gold_span_materialization_prerequisite_count": gold_span_prereq,
        "file_right_span_wrong_when_range_valid_rate": _rate(frsw_range_valid_count, frsw_range_valid_denom),
        "file_right_span_wrong_when_range_valid_count": frsw_range_valid_count,
        "no_gold_readable_candidate_rate": _rate(no_gold_readable, no_gold_denom),
        "no_gold_readable_candidate_count": no_gold_readable,
        "no_gold_range_valid_candidate_rate": _rate(no_gold_range_valid, no_gold_denom),
        "no_gold_range_valid_candidate_count": no_gold_range_valid,
    }


def _compute_source_read_outcomes(
    normalized_tasks: list[dict[str, Any]],
    repo_resolution: dict[str, Path | None],
) -> tuple[list[dict[str, Any]], dict[tuple[int, int], dict[str, Any]]]:
    """Return flat outcomes list and a lookup keyed by (task_idx, cand_id)."""
    outcomes: list[dict[str, Any]] = []
    outcomes_by_task_cand: dict[tuple[int, int], dict[str, Any]] = {}
    total_bytes_read = 0

    for task_idx, task in enumerate(normalized_tasks):
        tid = _as_str(task.get("task_id"))
        root = repo_resolution.get(tid)
        candidates = task.get("_candidates", [])
        # Enforce per-task cap deterministically.
        if len(candidates) > MAX_CANDIDATES_PER_TASK:
            candidates = candidates[:MAX_CANDIDATES_PER_TASK]
        for cand in candidates:
            outcome, total_bytes_read = _process_candidate_source(task, cand, root, total_bytes_read)
            outcomes.append(outcome)
            cid = cand.get("_id")
            if isinstance(cid, int):
                outcomes_by_task_cand[(task_idx, cid)] = outcome

    return outcomes, outcomes_by_task_cand


def _normalize_tasks(raw_records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Normalize raw records via P46 and attach in-memory candidate list."""
    normalized_tasks = [nt for nt in (p46.normalize_task(raw) for raw in raw_records) if nt]
    for task in normalized_tasks:
        candidates = p49._normalize_candidates(task)
        task["_candidates"] = candidates
    return normalized_tasks, raw_records


def _apply_global_candidate_cap(tasks: list[dict[str, Any]]) -> None:
    """Trim candidates per task so total stays under the global cap."""
    total = sum(len(t.get("_candidates", [])) for t in tasks)
    if total <= MAX_TOTAL_CANDIDATES:
        return
    # Trim proportionally and deterministically.
    per_task_allowance = max(1, MAX_TOTAL_CANDIDATES // max(1, len(tasks)))
    for task in tasks:
        task["_candidates"] = task["_candidates"][:per_task_allowance]


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
    p52_report_path: Path | None,
    p49_report_path: Path | None,
    p50_report_path: Path | None,
    p48_report_path: Path | None,
) -> dict[str, Any]:
    repo_resolution, repo_meta = _determine_repo_roots(normalized_tasks, repo_lock_path, source_root)

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

    p52_meta = _read_optional_report(p52_report_path, "p52")
    p49_meta = _read_optional_report(p49_report_path, "p49")
    p50_meta = _read_optional_report(p50_report_path, "p50")
    p48_meta = _read_optional_report(p48_report_path, "p48")

    _apply_global_candidate_cap(normalized_tasks)
    outcomes, outcomes_by_task_cand = _compute_source_read_outcomes(normalized_tasks, repo_resolution)

    candidate_denominator = len(outcomes)
    task_denominator = len(normalized_tasks)
    source_reads_attempted = any(
        o["source_read_success"]
        or o["path_invalid"]
        or o["path_secret"]
        or o["escape_reject"]
        or o["missing_file"]
        or o["file_too_large"]
        or o["binary_or_decode"]
        or o["secret_text"]
        or o["budget_exceeded"]
        for o in outcomes
    )

    resolved_tasks = sum(1 for t in normalized_tasks if repo_resolution.get(t["task_id"]) is not None)
    repo_resolution_availability = (
        "available"
        if task_denominator > 0 and resolved_tasks == task_denominator
        else "partial"
        if resolved_tasks > 0
        else "unavailable_no_repo_lock"
        if repo_meta["repo_lock_source"] == "not_provided" and repo_meta["source_root_source"] == "not_provided"
        else "unavailable_invalid_repo_lock"
        if repo_meta["repo_lock_source"] == "invalid_json"
        else "unavailable_no_repo_lock"
    )

    success_count = sum(1 for o in outcomes if o["source_read_success"])
    budget_exceeded_count = sum(1 for o in outcomes if o["budget_exceeded"])
    if candidate_denominator == 0:
        source_read_availability = "unavailable_no_source_root"
    elif success_count == 0:
        if budget_exceeded_count > 0:
            source_read_availability = "unavailable_budget_exceeded"
        elif repo_meta["source_root_source"] in {"not_provided", "invalid", "inaccessible"} and repo_meta["repo_lock_source"] != "provided":
            source_read_availability = "unavailable_no_source_root"
        else:
            source_read_availability = "partial"
    else:
        source_read_availability = "available" if success_count == candidate_denominator else "partial"

    prereq_ok_count = sum(1 for o in outcomes if _materialization_prereq_ok(o))
    materialization_prerequisite_availability = (
        "available"
        if candidate_denominator > 0 and prereq_ok_count == candidate_denominator
        else "partial"
        if prereq_ok_count > 0
        else "unavailable"
    )

    metric_blocks = {
        "source_materialization_metrics": _source_materialization_metrics(outcomes, candidate_denominator),
        "source_required_verifier_availability": _source_required_verifier_availability(outcomes, candidate_denominator),
    }

    packs = _compute_strategy_packs(normalized_tasks)
    metric_blocks["pack_materialization_metrics"] = _pack_materialization_metrics(normalized_tasks, packs, outcomes_by_task_cand)
    metric_blocks["breakdowns"] = _breakdowns(normalized_tasks, normalized_tasks, outcomes_by_task_cand)
    metric_blocks["score_phase_diagnostic_correlation"] = _score_phase_diagnostics(normalized_tasks, normalized_tasks, packs, outcomes_by_task_cand)

    conclusion_lines: list[str] = []
    if status not in {"ok", "self_test_only"}:
        conclusion_lines.append(
            "P52A Source Materialization / Local Verifier Prerequisite is ready; real per-task ephemeral P25 records and a repo root are required."
        )
        if reason:
            conclusion_lines.append(reason)
    else:
        if self_test:
            conclusion_lines.append(
                f"Self-test-only materialization prerequisite diagnosed {candidate_denominator} synthetic candidates across {task_denominator} tasks; this is not quality evidence."
            )
        else:
            conclusion_lines.append(
                f"P52A diagnosed materialization prerequisites for {candidate_denominator} candidates across {task_denominator} real ephemeral P25 records."
            )
        conclusion_lines.append(
            "P52A reads local source files only for bounded aggregate materialization diagnostics. "
            "Raw source text, snippets, digests, paths, and spans are not stored."
        )
        conclusion_lines.append(
            "Source read is not Evidence; materialized candidate is not Evidence; P52A does not validate EvidenceCore and does not produce verifier pass/fail or default/promotion claims."
        )
        conclusion_lines.append(
            f"Source-read availability: `{source_read_availability}`; materialization prerequisite availability: `{materialization_prerequisite_availability}`."
        )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": "P52A Source Materialization / Local Verifier Prerequisite",
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
        "materialized_candidate_not_evidence": True,
        "source_read_not_evidence": True,
        "verifier_not_evidence": True,
        "remote_calls_by_p52a": 0,
        "llm_calls_by_p52a": 0,
        "prompt_construction_by_p52a": False,
        "source_reads_attempted_by_p52a": source_reads_attempted,
        "source_reads_bounded_by_p52a": True,
        "raw_prompts_stored": False,
        "raw_query_stored": False,
        "raw_responses_stored": False,
        "raw_source_stored": False,
        "raw_text_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "aggregate_only_public_artifact": True,
        "score_phase_only_metrics": True,
        "private_labels_committed": False,
        "gold_spans_in_artifact": False,
        "provider_keys_in_artifact": False,
        "raw_queries_in_artifact": False,
        "raw_candidate_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "repo_lock_source": repo_meta["repo_lock_source"],
        "source_root_source": repo_meta["source_root_source"],
        "source_root_availability": repo_meta["source_root_source"].replace("_", "_") if repo_meta["source_root_source"] != "provided" else "provided",
        "repo_resolution_availability": repo_resolution_availability,
        "source_read_availability": source_read_availability,
        "materialization_prerequisite_availability": materialization_prerequisite_availability,
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
        raise RuntimeError(f"P52A public report validation failed: {errors}")
    return report


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("remote_calls_by_p52a") != 0:
        errors.append("remote_calls_by_p52a must be 0")
    if report.get("llm_calls_by_p52a") != 0:
        errors.append("llm_calls_by_p52a must be 0")
    if report.get("prompt_construction_by_p52a") is not False:
        errors.append("prompt_construction_by_p52a must be false")
    if report.get("source_reads_bounded_by_p52a") is not True:
        errors.append("source_reads_bounded_by_p52a must be true")

    expected_flags = {
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "materialized_candidate_not_evidence": True,
        "source_read_not_evidence": True,
        "verifier_not_evidence": True,
        "score_phase_only_metrics": True,
        "aggregate_only_public_artifact": True,
        "raw_prompts_stored": False,
        "raw_query_stored": False,
        "raw_responses_stored": False,
        "raw_source_stored": False,
        "raw_text_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "private_labels_committed": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
        "raw_queries_in_artifact": False,
        "raw_candidate_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
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
    lines: list[str] = ["# P52A Source Materialization / Local Verifier Prerequisite\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Remote calls by P52A: {report['remote_calls_by_p52a']}",
        f"- LLM calls by P52A: {report['llm_calls_by_p52a']}",
        f"- Prompt construction by P52A: {report['prompt_construction_by_p52a']}",
        f"- Source reads attempted by P52A: {report['source_reads_attempted_by_p52a']}",
        f"- Tasks: {report['task_count']} positive={report['positive_task_count']} no_gold={report['no_gold_task_count']}",
        f"- Repo lock source: `{report['repo_lock_source']}`",
        f"- Source root source: `{report['source_root_source']}`",
        f"- Source read availability: `{report['source_read_availability']}`",
        f"- Materialization prerequisite availability: `{report['materialization_prerequisite_availability']}`\n",
    ])

    if report["status"] not in {"ok", "self_test_only"}:
        lines.extend(["## Status", report.get("status_reason") or "", "", "Run with `--self-test` or supply ephemeral P25-policy records and a repo root.", ""])
        return "\n".join(lines)

    lines.extend([
        "## Purpose\n",
        "P52A reads local source files only for bounded aggregate materialization diagnostics. "
        "It is a SCORE-phase-only prerequisite evaluator, not a verifier pass/fail phase.",
        "",
        "## Methodology\n",
        "- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).",
        "- Resolve a safe, local repo root for each task from `--repo-lock` or `--source-root` fallback.",
        "- Normalize candidates with P46/P49 helpers, preserving only public metadata.",
        "- Perform bounded source reads per candidate, subject to byte/line/file/candidate caps and secret-path/text scans.",
        "- Discard raw text after aggregate counters and lightweight heuristics; never store source, snippets, digests, paths, or spans.",
        "- Rebuild P49 packs in-memory and report aggregate pack-level materialization diagnostics.",
        "- Gold/outcome signals are used only inside explicitly-marked SCORE-phase diagnostics `not_used_for_materialization_decision=true`.",
        "",
        "## Safety notes\n",
        "- P52A reads local source only for bounded aggregate materialization diagnostics.",
        "- P52A stores no raw source, snippets, digests, paths, or spans.",
        "- Source read is not Evidence.",
        "- Materialized candidate is not Evidence.",
        "- P52A does not validate EvidenceCore.",
        "- P52A does not produce verifier pass/fail or default/promotion claims.",
        "- P52A does not call an LLM, construct prompts, or make remote calls.",
        "",
    ])

    sm = report["metrics"]["source_materialization_metrics"]
    lines.append("## Source materialization metrics\n")
    lines.append("| Denom | Attempts | Success | Resolved | Missing | InvalidPath | Escape | TooLarge | Binary | Secret | RangeValid | DigestMatch |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    lines.append(
        f"| {sm['candidate_denominator']} | {sm['source_read_attempt_count']} | {sm['source_read_success_count']} | "
        f"{sm['candidate_path_resolved_to_file_count']} | {sm['candidate_missing_file_count']} | "
        f"{sm['candidate_invalid_path_count']} | {sm['candidate_file_escape_reject_count']} | "
        f"{sm['candidate_file_too_large_count']} | {sm['candidate_binary_or_decode_reject_count']} | "
        f"{sm['candidate_secret_reject_count']} | {sm['line_range_valid_count']} | {sm['candidate_digest_match_count']} |"
    )
    lines.append("")
    lines.append(
        f"- Span width after read (valid ranges): mean={_fmt_scalar(sm['span_width_after_read_mean'])}, p95={_fmt_scalar(sm['span_width_after_read_p95'])}; "
        f"over cap ({MAX_SPAN_LINES} lines): {sm['span_width_over_cap_count']}"
    )
    lines.append(
        f"- Line range clamped: `{sm['line_range_clamped_availability']}` (count={sm['line_range_clamped_count']}); invalid ranges are counted, not silently clamped."
    )
    lines.append("")

    sv = report["metrics"]["source_required_verifier_availability"]
    lines.append("## Source-required verifier availability\n")
    lines.append("| Verifier | Availability | Checkable | Positive |")
    lines.append("|---|---|---:|---:|")
    for key, block in sv.items():
        avail = block.get("availability", "n/a")
        checkable = block.get("checkable_count")
        positive = block.get("heuristic_positive_count") or block.get("match_count") or "n/a"
        lines.append(f"| {key} | `{avail}` | {_fmt_scalar(checkable)} | {_fmt_scalar(positive)} |")
    lines.append("")

    pm = report["metrics"]["pack_materialization_metrics"]["task_wide"]
    lines.append("## Pack materialization metrics (task-wide)\n")
    lines.append("| Denom | AllResolved | StaleDigest | InvalidRange | NeedsSource | PrereqAvail |")
    lines.append("|---:|---:|---:|---:|---:|---:|")
    lines.append(
        f"| {pm['pack_denominator']} | {_fmt_scalar(pm['packs_with_all_candidates_resolved_rate'])} | "
        f"{_fmt_scalar(pm['packs_with_any_stale_digest_rate'])} | {_fmt_scalar(pm['packs_with_any_invalid_range_rate'])} | "
        f"{_fmt_scalar(pm['packs_requiring_source_for_comment_or_signature_rate'])} | {_fmt_scalar(pm['packs_with_materialization_prerequisite_available_rate'])} |"
    )
    lines.append("")

    sp = report["metrics"]["score_phase_diagnostic_correlation"]
    lines.append("## SCORE-phase diagnostics (not used for materialization decisions)\n")
    lines.append("| GoldFileReadable | GoldSpanRangeValid | GoldSpanPrereq | FileRightSpanWrong | NoGoldReadable | NoGoldRangeValid |")
    lines.append("|---:|---:|---:|---:|---:|---:|")
    lines.append(
        f"| {_fmt_scalar(sp['gold_file_readable_rate'])} | {_fmt_scalar(sp['gold_span_range_valid_rate'])} | "
        f"{_fmt_scalar(sp['gold_span_materialization_prerequisite_rate'])} | {_fmt_scalar(sp['file_right_span_wrong_when_range_valid_rate'])} | "
        f"{_fmt_scalar(sp['no_gold_readable_candidate_rate'])} | {_fmt_scalar(sp['no_gold_range_valid_candidate_rate'])} |"
    )
    lines.append("")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="P52A Source Materialization / Local Verifier Prerequisite")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to ephemeral P25-policy JSON record files.")
    parser.add_argument("--repo-lock", type=Path, default=None, help="Repo lock JSON mapping repo_id -> source path.")
    parser.add_argument("--source-root", type=Path, default=None, help="Optional fallback repo root for all tasks.")
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
        "_p25_input_summary_marker": "Aggregate summary lacks per-task ephemeral records required for P52A source materialization diagnostics.",
        "_p25_input_empty_marker": "Input artifact did not contain per-task ephemeral records.",
        "_p25_unsupported_schema_marker": "P52A requires p25-policy-records-ephemeral-v1 input schema.",
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

    normalized_tasks, raw_records = _normalize_tasks(task_records)
    _enrich_candidates_with_digest(raw_records, normalized_tasks)

    if status == "ok" and not normalized_tasks:
        status = "insufficient_task_detail"
        reason = "Records lacked required fields for P52A normalization."

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
        p52_report_path=args.p52_report,
        p49_report_path=args.p49_report,
        p50_report_path=args.p50_report,
        p48_report_path=args.p48_report,
    )

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P52A report written to {args.out}")
    print(f"P52A markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
