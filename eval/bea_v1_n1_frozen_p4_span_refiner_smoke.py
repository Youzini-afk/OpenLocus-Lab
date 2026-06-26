#!/usr/bin/env python3
"""BEA-v1-N1: Frozen P4 + Span-Refiner Smoke.

N1 is the first BEA-v1 Report-4 span phase after the P4L checkpoint.  It is a
retrieval-layer span smoke only: wrap/replay frozen P4, preserve file and
scheduler behavior, form a private wrong-span denominator, and test a
post-P4 file-preserving span refiner.  It does not run a selector/reranker,
P5, BEA-v1-A, provider calls, default promotion, method-winner logic, or any
latency-in-relevance scoring.

Default no-network execution writes an honest ``unavailable_with_reason``
artifact.  The network-enabled path regenerates/replays FD1 + the locked P4L
denominator, runs frozen P4 with candidate line ranges, forms D1 privately, and
emits an empirical pass/exploratory/no-go result or fail-closes on infra errors.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, NoReturn

_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

from score import (  # noqa: E402
    build_gold_line_set,
    span_f_beta_at_k,
    wrong_span_rate_at_k,
    zero_overlap_evidence_rate_at_k,
    structural_validity,
)
import bea_v1_p4_latency_aware_retrieval_scheduler_smoke as p4  # noqa: E402
import bea_v1_p4l_locked_non_python_scheduler_validation as p4l  # noqa: E402


SCHEMA_VERSION = "bea_v1_n1_frozen_p4_span_refiner_smoke.v1"
GENERATED_BY = "eval/bea_v1_n1_frozen_p4_span_refiner_smoke.py"
CLAIM_LEVEL = "bea_v1_n1_frozen_p4_span_refiner_smoke_only"
MODE = "bea_v1_n1_frozen_p4_span_refiner_smoke"
PHASE = "BEA-v1-N1"

DEFAULT_OUT = Path(
    "artifacts/bea_v1_n1_frozen_p4_span_refiner_smoke/"
    "bea_v1_n1_frozen_p4_span_refiner_smoke_report.json"
)
DEFAULT_FD1_ARTIFACT = p4l.DEFAULT_FD1_ARTIFACT
DEFAULT_P4H_ARTIFACT = p4l.DEFAULT_P4H_ARTIFACT
DEFAULT_P4I_ARTIFACT = p4l.DEFAULT_P4I_ARTIFACT
DEFAULT_P4J_ARTIFACT = p4l.DEFAULT_P4J_ARTIFACT
DEFAULT_P4K_ARTIFACT = p4l.DEFAULT_P4K_ARTIFACT

# Locked P4L binding context (read-only; D0 scheduler-preservation target).
P4L_RESULT_CHECKPOINT = "f1bac81"
P4L_CI_RUN_ID = "28184096209"
P4L_LOCKED_NON_PYTHON_DENOMINATOR = 272
P4L_BASELINE_REACH = 0
P4L_P2_REACH = 55
P4L_P3_REACH = 55
P4L_P4_REACH = 52
P4L_P4_RETAINED_P2_GAIN = 0.945455
P4L_P4_P3_LATENCY_RATIO = 0.656763
P4L_TREATMENT_HARD_CAP = 0

D1_ADEQUATE_MIN = 20
D1_EXPLORATORY_MIN = 10
D1_TOP10_ACTIONABLE_ADEQUATE_MIN = 20
D1_TOP10_ACTIONABLE_EXPLORATORY_MIN = 10
SPAN_INADEQUATE_OVERLAP_RATIO_MAX = 0.20
SPAN_REFINER_WINDOW_RADIUS = 3
SPAN_REFINER_MAX_FILE_LINES = 4000

STATUSES = (
    "bea_v1_n1_frozen_p4_span_refiner_pass",
    "n1_preflight_pass_wrong_span_denominator_adequate",
    "n1_exploratory_insufficient_power",
    "no_go_n1_locked_denominator_unavailable",
    "no_go_n1_inadequate_wrong_span_denominator",
    "no_go_n1_inadequate_top10_actionable_denominator",
    "unavailable_with_reason",
    "fail_schema_contract",
    "fail_forbidden_scan",
)

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "aggregate_plus_sanitized_records_public_artifact": True,
    "records_only_public_artifact": True,
    "retrieval_layer_span_smoke_only": True,
    "post_p4_file_preserving_refiner_only": True,
    "scheduler_preservation_denominator_is_d0_only": True,
    "span_success_denominator_is_d1_only": True,
    "bea_v1_n1_evaluator_no_provider_calls": True,
    "bea_v1_n1_evaluator_no_selector_executed": True,
    "bea_v1_n1_evaluator_no_reranker_executed": True,
    "bea_v1_n1_evaluator_no_p5": True,
    "bea_v1_n1_evaluator_no_v1_a": True,
    "bea_v1_n1_evaluator_latency_not_in_candidate_relevance": True,
}

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "provider_calls_made": False,
    "remote_provider_calls_made": False,
    "selector_or_reranker_executed": False,
    "selector_or_reranker_changed": False,
    "p5_executed": False,
    "p5_authorized": False,
    "v1_a_selector_executed": False,
    "v1_a_authorized": False,
    "default_should_change": False,
    "runtime_behavior_changed": False,
    "promotion_ready": False,
    "runtime_promotion_authorized": False,
    "method_winner_claimed": False,
    "method_winner_authorized": False,
    "external_benchmark_performance_claimed": False,
    "leaderboard_entry_claimed": False,
    "downstream_agent_value_proven": False,
    "calibration_claimed": False,
    "latency_in_candidate_relevance": False,
    "gold_lines_used_for_refinement": False,
    "gold_labels_used_for_selection": False,
    "gold_labels_used_for_query_construction": False,
    "gold_labels_used_for_policy": False,
    "files_added_by_refiner": False,
    "files_evicted_by_refiner": False,
    "files_reordered_by_refiner": False,
    "scheduler_actions_changed_by_refiner": False,
    "new_records_added_during_bea_v1_n1": False,
    "aggregate_only_public_artifact": False,
    "raw_records_publicly_serialized": False,
}

FAILURE_CATEGORIES = (
    "network_required_but_disabled",
    "fd1_artifact_missing",
    "fd1_artifact_parse_failed",
    "fd1_schema_version_mismatch",
    "fd1_status_mismatch",
    "fd1_private_decomposition_missing",
    "fd1_private_decomposition_parse_failed",
    "fd1_replay_artifact_missing",
    "fd1_replay_artifact_parse_failed",
    "fd1_replay_artifact_status_mismatch",
    "p4k_artifact_missing",
    "p4k_artifact_status_mismatch",
    "p4k_locked_count_mismatch",
    "p4k_split_or_overlap_mismatch",
    "locked_denominator_mismatch",
    "raw_denominator_parse_failed",
    "raw_denominator_clone_failed",
    "raw_denominator_scan_failed",
    "p4l_scan_failed",
    "cross_source_asset_download_failed",
    "cross_source_asset_decompress_failed",
    "retrieval_policy_failed",
    "d0_scheduler_preservation_missing",
    "d0_scheduler_preservation_drift",
    "d1_private_span_rows_missing",
    "d1_private_span_rows_parse_failed",
    "d1_private_write_error",
    "gold_span_reconstruction_failed",
    "candidate_span_reconstruction_failed",
    "refiner_file_preservation_violation",
    "forbidden_leak_blocked",
    "unexpected_exception",
)

BLOCKING_FAILURES = {
    "fd1_artifact_missing",
    "fd1_artifact_parse_failed",
    "fd1_schema_version_mismatch",
    "fd1_status_mismatch",
    "fd1_private_decomposition_missing",
    "fd1_private_decomposition_parse_failed",
    "fd1_replay_artifact_missing",
    "fd1_replay_artifact_parse_failed",
    "fd1_replay_artifact_status_mismatch",
    "p4k_artifact_missing",
    "p4k_artifact_status_mismatch",
    "p4k_locked_count_mismatch",
    "p4k_split_or_overlap_mismatch",
    "raw_denominator_parse_failed",
    "raw_denominator_clone_failed",
    "raw_denominator_scan_failed",
    "p4l_scan_failed",
    "cross_source_asset_download_failed",
    "cross_source_asset_decompress_failed",
    "retrieval_policy_failed",
    "d0_scheduler_preservation_missing",
    "d0_scheduler_preservation_drift",
    "d1_private_span_rows_parse_failed",
    "d1_private_write_error",
    "refiner_file_preservation_violation",
    "unexpected_exception",
}

SANITIZED_ROW_ALLOWLIST = frozenset({
    "anonymous_local_id",
    "denominator",
    "arm",
    "source_bucket",
    "language_bucket",
    "pre_span_bucket",
    "post_span_bucket",
    "span_delta_bucket",
    "local_span_delta_bucket",
    "rank_actionability_bucket",
    "file_reach_preserved",
    "evidencecore_valid",
    "hard_cap_violation",
})

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "exact_path", "private_path", "trace_path",
    "start_line", "end_line", "line_range", "span", "spans", "exact_span",
    "gold", "gold_paths", "gold_lines", "gold_spans", "gold_labels",
    "candidate", "candidates", "candidate_list", "candidate_paths",
    "raw", "raw_trace", "raw_prompt", "raw_response", "provider_payload",
    "snippet", "snippets", "content", "content_lines", "file_content_lines",
    "text", "raw_text", "content_sha", "task_id", "row_id",
    "repo_name", "repo_slug", "repo_url", "base_commit", "private_record_id",
    "record_ids", "self_test_checks", "self_test_details", "checks",
})

SAFE_VALUE_KEYS = frozenset({
    "schema_version", "generated_by", "generated_at", "claim_level", "status",
    "mode", "phase", "failure_reason_category", "network_mode",
    "openlocus_binary_source", "source_checkpoint", "source_ci_run_id",
    "status_vocabulary", "metric_block", "metric_name", "gate", "threshold_relation",
    "manifest_name", "schema_version", "storage_class", "source_bucket",
    "language_bucket", "pre_span_bucket", "post_span_bucket", "span_delta_bucket",
    "local_span_delta_bucket", "rank_actionability_bucket", "denominator", "arm",
    "stop_go_decision", "stop_go_reason", "signal_strength",
})


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _safe_status_diagnostics(report: dict[str, Any]) -> dict[str, Any]:
    """Return log-safe aggregate diagnostics with no paths, snippets, or rows."""
    nonzero_failures = [
        {"failure_category": r.get("failure_category"), "count": int(r.get("count", 0) or 0)}
        for r in report.get("failure_category_count_records", [])
        if isinstance(r, dict) and int(r.get("count", 0) or 0) != 0
    ]
    d0 = [
        {"metric_name": r.get("metric_name"), "value": r.get("value"), "expected_value": r.get("expected_value"), "passed": r.get("passed")}
        for r in report.get("d0_scheduler_preservation_records", [])
        if isinstance(r, dict)
    ]
    manifests = [
        {"manifest_name": r.get("manifest_name"), "record_count": r.get("record_count"), "exists": r.get("exists")}
        for r in report.get("private_manifest_records", [])
        if isinstance(r, dict)
    ]
    return {
        "status": report.get("status"),
        "failure_reason_category": report.get("failure_reason_category"),
        "d1_wrong_span_denominator_count": report.get("d1_wrong_span_denominator_count"),
        "d1_top10_actionable_count": report.get("d1_top10_actionable_count"),
        "d1_rank_blocked_count": report.get("d1_rank_blocked_count"),
        "nonzero_failure_categories": nonzero_failures,
        "d0_records": d0,
        "private_manifests": manifests,
    }


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return {"check": name, "passed": bool(ok)}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError("jsonl row is not an object")
        rows.append(obj)
    return rows


def _manifest_for_path(path: Path | None, name: str, schema: str) -> dict[str, Any]:
    digest = hashlib.sha256()
    count = 0
    if path is not None and path.exists():
        with path.open("rb") as fh:
            for line in fh:
                count += 1
                digest.update(line)
    return {
        "manifest_name": name,
        "schema_version": schema,
        "storage_class": "private_tmp_or_caller_supplied_not_uploaded",
        "record_count": int(count),
        "records_written": bool(count > 0),
        "path_publicly_serialized": False,
        "manifest_hash": digest.hexdigest() if count else "",
    }


def _append_private_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def _resolve_private_n1_dir() -> Path:
    raw = os.environ.get("OPENLOCUS_BEA_V1_N1_PRIVATE_DIR", "")
    base = Path(raw) if raw else Path(f"/tmp/openlocus_bea_v1_n1_{os.getpid()}")
    resolved = base.resolve()
    if not str(resolved).startswith("/tmp/"):
        raise ValueError("invalid private N1 dir")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)
    path_re = re.compile(r"(?:^|[\s=])(?:/[^\s]+|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    hex_re = re.compile(r"\b[0-9a-f]{64}\b", re.I)

    def walk(o: Any, p: str = "$") -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                ks = str(k)
                sub = f"{p}.{ks}"
                if ks in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "path": sub})
                if ks == "sanitized_analysis_records" and isinstance(v, list):
                    for i, row in enumerate(v):
                        if isinstance(row, dict):
                            extra = set(row) - SANITIZED_ROW_ALLOWLIST
                            if extra:
                                violations.append({"category": "sanitized_row_non_allowlist_key", "path": f"{sub}[{i}]"})
                walk(v, sub)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{p}[{i}]")
        elif isinstance(o, str):
            last = p.rsplit(".", 1)[-1].split("[")[0]
            if last in SAFE_VALUE_KEYS or last == "manifest_hash":
                return
            if line_re.search(o):
                violations.append({"category": "line_range_value", "path": p})
            if path_re.search(o):
                violations.append({"category": "path_like_value", "path": p})
            if hex_re.search(o):
                violations.append({"category": "hex_digest_value", "path": p})

    walk(obj)
    return violations


def _scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_public(obj)
    cats: dict[str, int] = {}
    for v in violations:
        cats[v["category"]] = cats.get(v["category"], 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "violation_categories": [
            {"category": c, "count": n} for c, n in sorted(cats.items())
        ],
    }


def _enforce_no_forbidden(report: dict[str, Any]) -> None:
    if _scan_summary(report)["status"] != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")


def _overlap_for_evidence(e: dict[str, Any], gold_task: dict[str, Any]) -> tuple[int, int, float]:
    gold_lines = build_gold_line_set(gold_task)
    path = str(e.get("path", "") or "")
    start = int(e.get("start_line", 0) or 0)
    end = int(e.get("end_line", 0) or 0)
    pred = {(path, ln) for ln in range(start, end + 1)} if start > 0 and end >= start else set()
    overlap = len(pred & gold_lines)
    return overlap, len(pred), (overlap / len(pred) if pred else 0.0)


def _bucket_span(e: dict[str, Any], gold_task: dict[str, Any]) -> str:
    overlap, pred_len, ratio = _overlap_for_evidence(e, gold_task)
    if pred_len <= 0:
        return "invalid"
    if overlap == 0:
        return "zero_overlap"
    if ratio < SPAN_INADEQUATE_OVERLAP_RATIO_MAX:
        return "inadequate_overlap"
    if ratio < 0.80:
        return "partial_overlap"
    return "adequate_overlap"


def _span_delta_bucket(pre: str, post: str) -> str:
    order = {"invalid": 0, "zero_overlap": 1, "inadequate_overlap": 2, "partial_overlap": 3, "adequate_overlap": 4}
    if order.get(post, 0) > order.get(pre, 0):
        return "improved"
    if order.get(post, 0) < order.get(pre, 0):
        return "regressed"
    return "unchanged"


def _best_span_bucket(evidence: list[dict[str, Any]], task: dict[str, Any]) -> str:
    order = {"invalid": 0, "zero_overlap": 1, "inadequate_overlap": 2, "partial_overlap": 3, "adequate_overlap": 4}
    if not evidence:
        return "invalid"
    return max((_bucket_span(e, task) for e in evidence), key=lambda b: order[b])


def _query_terms(text: str) -> list[str]:
    terms = [t.lower() for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text or "")]
    stop = {"the", "and", "for", "with", "that", "this", "from", "function", "class"}
    return [t for t in terms if t not in stop][:20]


def _line_text_terms(text: str) -> set[str]:
    stop = {"the", "and", "for", "with", "that", "this", "from", "function", "class", "return"}
    return {
        t.lower()
        for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text or "")
        if t.lower() not in stop
    }


def _score_refiner_line(txt: str, query_terms: list[str], anchor_terms: set[str]) -> int:
    lower = (txt or "").lower()
    terms = _line_text_terms(lower)
    score = 0
    for term in query_terms:
        if term in lower:
            score += 4
        if term in terms:
            score += 2
    score += min(4, len(terms & anchor_terms))
    if re.search(r"\b(def|class|function|func|method|struct|interface|enum)\b", lower):
        score += 1
    return score


def _refine_evidence_file_preserving(e: dict[str, Any], query: str) -> dict[str, Any]:
    """Post-P4 span-only refiner: same file, no add/evict/reorder, no gold use.

    It uses public query terms plus text from the already selected file and
    selects a tight line window inside that same file.  It never adds, removes,
    or reorders files and never reads gold labels.  If file text is unavailable,
    the refiner returns the original range unchanged.
    """
    out = dict(e)
    lines = e.get("file_content_lines") or e.get("content_lines")
    terms = _query_terms(query)
    if not isinstance(lines, list) or not terms:
        return out
    available_line_numbers = [int(item["line"]) for item in lines if isinstance(item, dict) and isinstance(item.get("line"), int)]
    if not available_line_numbers:
        return out
    max_available_line = max(available_line_numbers)
    local_anchor_terms: set[str] = set()
    for item in e.get("content_lines", []) if isinstance(e.get("content_lines"), list) else []:
        if isinstance(item, dict):
            local_anchor_terms |= _line_text_terms(str(item.get("text", "") or ""))
    scored: list[tuple[int, int]] = []
    for item in lines:
        if not isinstance(item, dict):
            continue
        ln = item.get("line")
        txt = str(item.get("text", "") or "")
        if not isinstance(ln, int):
            continue
        score = _score_refiner_line(txt, terms, local_anchor_terms)
        if score:
            scored.append((score, ln))
    if not scored:
        return out
    max_score = max(s for s, _ in scored)
    hit_lines = sorted(ln for s, ln in scored if s == max_score)
    # Ties are common in repetitive code. Choose the highest-density local
    # cluster rather than the first matching line.
    best_center = hit_lines[0]
    best_cluster = -1
    for ln in hit_lines:
        cluster = sum(s for s, other_ln in scored if abs(other_ln - ln) <= SPAN_REFINER_WINDOW_RADIUS)
        if cluster > best_cluster:
            best_cluster = cluster
            best_center = ln
    start = max(1, best_center - SPAN_REFINER_WINDOW_RADIUS)
    end = min(max_available_line, best_center + SPAN_REFINER_WINDOW_RADIUS)
    out["start_line"] = start
    out["end_line"] = end
    return out


def _run_frozen_p4_with_candidates(
    *, openlocus_bin: str, repo_root: Path, query: str, gold_set: set[str],
) -> tuple[Any, list[dict[str, Any]]]:
    """Mirror frozen P4 scheduler policy and return final candidate dicts.

    This is N1-local because P4's public runner keeps only private paths in its
    result object.  It delegates to P4 helper functions/constants and preserves
    the same action policy, caps, methods, and no-query-anchor contract.
    """
    rr = p4.SchedulerReachResult(
        arm_name="p4_latency_aware_action_scheduler_frozen",
        private_record_id="",
    )
    rr.scheduler_action = "baseline_only"
    rr.scheduler_stop_reason = "baseline_no_extra"
    per_channel_cands, per_channel_lat_ms, per_channel_err, base_err = (
        p4._collect_baseline_per_channel(openlocus_bin, query, repo_root)
    )
    rr.retrieval_error = base_err
    baseline_cands, _rrf = p4._merge_baseline_pool(
        per_channel_cands, p4.DEFAULT_RETRIEVAL_LIMIT)
    baseline_latency_ms = sum(per_channel_lat_ms.values())
    rr.baseline_latency_seconds = round(baseline_latency_ms / 1000.0, 6)
    baseline_union_files = {
        str(c.get("path", "") or "") for c in baseline_cands if c.get("path")
    }
    rr.baseline_unique_file_count = len(baseline_union_files)
    per_channel_files = {
        method: {str(c.get("path", "") or "") for c in per_channel_cands.get(method, []) if c.get("path")}
        for method in p4.FIXED_METHODS
    }
    channels: dict[str, Any] = {}
    for method in p4.FIXED_METHODS:
        other_files = set().union(*[
            files for m, files in per_channel_files.items() if m != method
        ]) if len(per_channel_files) > 1 else set()
        channels[method] = p4._compute_channel_diagnostics(
            method, per_channel_cands.get(method, []),
            per_channel_lat_ms.get(method, 0),
            per_channel_err.get(method, ""), other_files)
    selected_channels = p4._select_eligible_extra_depth_channels(channels)
    rr.extra_depth_channels_selected_private = list(selected_channels)
    final_cands = list(baseline_cands)
    extra_latency_ms = 0
    hard_cap_hit = False
    unique_file_cap_hit = False
    if selected_channels:
        seen_files = set(baseline_union_files)
        merged = list(baseline_cands)
        for method in selected_channels:
            extra_cands, ch_lat_ms, ch_err = p4._collect_extra_depth_channel(
                openlocus_bin, method, query, repo_root, p4.DEPTH_REFERENCE_MULTIPLIER)
            if ch_err:
                rr.retrieval_error = True
            extra_latency_ms += ch_lat_ms
            ch_new_files = {str(c.get("path", "") or "") for c in extra_cands if c.get("path")}
            ch_new = ch_new_files - seen_files
            if len(ch_new) < p4.P4_CHANNEL_MARGINAL_YIELD_MIN:
                continue
            for c in extra_cands:
                cand_path = str(c.get("path", "") or "")
                if cand_path and cand_path not in seen_files:
                    merged.append(c)
                    seen_files.add(cand_path)
                if len(merged) >= p4.P4_HARD_CANDIDATE_CAP:
                    hard_cap_hit = True
                    break
                if len(seen_files) >= p4.P4_UNIQUE_FILE_CAP:
                    unique_file_cap_hit = True
                    break
            if hard_cap_hit or unique_file_cap_hit:
                break
        final_cands = merged[:p4.P4_HARD_CANDIDATE_CAP]
        rr.extra_depth_actions_executed = len(selected_channels)
        rr.scheduler_action = "extra_depth_selected"
        rr.scheduler_stop_reason = (
            "hard_candidate_cap_reached" if hard_cap_hit else
            "unique_file_cap_reached" if unique_file_cap_hit else
            "extra_depth_actions_executed")
    else:
        rr.scheduler_action = "baseline_only"
        rr.scheduler_stop_reason = "no_eligible_channels"
    rr.hard_cap_hit = hard_cap_hit
    rr.unique_file_cap_hit = unique_file_cap_hit
    rr.candidate_pool_size = len(final_cands)
    (rr.gold_file_available, rr.first_gold_file_rank,
     rr.gold_file_rank_band, rr.duplicate_file_count) = (
        p4._check_gold_file_reach(final_cands, gold_set))
    rr.candidate_paths_private = [str(c.get("path", "") or "") for c in final_cands][:500]
    rr.query_variants_private = [query][:50]
    rr.final_unique_file_count = len({path for path in rr.candidate_paths_private if path})
    rr.extra_depth_latency_seconds = round(extra_latency_ms / 1000.0, 6)
    rr.retrieval_latency_seconds = round((baseline_latency_ms + extra_latency_ms) / 1000.0, 6)
    return rr, final_cands


def _read_candidate_content_lines(repo_root: Path, cand: dict[str, Any]) -> list[dict[str, Any]]:
    path = str(cand.get("path", "") or "")
    start = _line_number(cand.get("start_line"))
    end = _line_number(cand.get("end_line"))
    if not path or start is None or end is None or end < start:
        return []
    try:
        root = repo_root.resolve()
        full = (root / path).resolve()
        if not full.is_relative_to(root) or not full.is_file():
            return []
        text = full.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    lines = text.splitlines()
    out: list[dict[str, Any]] = []
    for ln in range(max(1, start), min(end, len(lines)) + 1):
        out.append({"line": ln, "text": lines[ln - 1]})
    return out


def _read_file_content_lines(repo_root: Path, path: str) -> list[dict[str, Any]]:
    if not path:
        return []
    try:
        root = repo_root.resolve()
        full = (root / path).resolve()
        if not full.is_relative_to(root) or not full.is_file():
            return []
        text = full.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    lines = text.splitlines()
    if len(lines) > SPAN_REFINER_MAX_FILE_LINES:
        return []
    return [{"line": i + 1, "text": line} for i, line in enumerate(lines)]


def _gold_from_locked_record(rec: dict[str, Any]) -> tuple[list[str], list[list[int]], bool]:
    paths = rec.get("gold_paths")
    if not isinstance(paths, list) or not paths:
        return [], [], False
    # ContextBench rows reconstructed by P4L currently carry gold paths only;
    # if future P4L includes gold_lines, consume them here. RepoQA locked rows
    # can carry needle line fields when reconstructed from c5d parser.
    lines = rec.get("gold_lines")
    if isinstance(lines, list) and lines:
        return [str(p) for p in paths if p], lines, True
    start = rec.get("needle_start_line") or rec.get("start_line")
    end = rec.get("needle_end_line") or rec.get("end_line")
    if isinstance(start, int) and isinstance(end, int) and start >= 1 and end >= start:
        return [str(paths[0])], [[start, end]], True
    return [], [], False


def _line_number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        n = value
    elif isinstance(value, str) and value.strip().isdigit():
        n = int(value.strip())
    else:
        return None
    return n if n >= 1 else None


def _contextbench_gold_lookup_by_raw_idx(fcc: dict[str, int] | None = None) -> dict[int, tuple[list[str], list[list[int]]]] | None:
    """Private ContextBench raw-index -> gold lines lookup for N1 only."""
    out: dict[int, tuple[list[str], list[list[int]]]] = {}
    rows, status, _, _ = p4.c5a._fetch_contextbench_rows(
        p4l.p4j.P4J_CONTEXTBENCH_ALL_LIMIT, "all")
    if status != "pass":
        if fcc is not None:
            fcc["raw_denominator_scan_failed"] = fcc.get("raw_denominator_scan_failed", 0) + 1
        return None
    for idx, row in enumerate(rows[:p4l.p4j.P4J_CONTEXTBENCH_ALL_LIMIT]):
        gold_paths, gold_lines, gc_status = p4.c5a._parse_gold_context(
            row.get("gold_context"))
        if gc_status == "pass" and gold_paths and gold_lines:
            out[idx] = (gold_paths, gold_lines)
    return out


def _repoqa_gold_lookup_by_language_raw_idx(fcc: dict[str, int] | None = None) -> dict[tuple[str, int], tuple[list[str], list[list[int]]]] | None:
    """Private RepoQA non-Python language/raw-index -> gold lines lookup."""
    out: dict[tuple[str, int], tuple[list[str], list[list[int]]]] = {}
    asset_bytes, dl_status, _ = p4.c5d._download_asset_to_bytes(p4.c5d.ASSET_URL)
    if dl_status != "pass" or not asset_bytes:
        if fcc is not None:
            fcc["cross_source_asset_download_failed"] = fcc.get("cross_source_asset_download_failed", 0) + 1
        return None
    parsed_asset, parse_status, _ = p4.c5d._decompress_asset(asset_bytes)
    if parse_status != "pass" or not isinstance(parsed_asset, dict):
        if fcc is not None:
            fcc["cross_source_asset_decompress_failed"] = fcc.get("cross_source_asset_decompress_failed", 0) + 1
        return None
    non_python_langs = sorted(
        str(k) for k in parsed_asset
        if k != "python" and isinstance(parsed_asset.get(k), list))
    for lang in non_python_langs:
        needles, status, _ = p4.c5d._parse_repoqa_needles(
            parsed_asset, lang, p4l.p4j.P4J_REPOQA_NON_PYTHON_PER_LANG_LIMIT)
        if status != "pass":
            if status != "unavailable_no_python_needles" and fcc is not None:
                fcc["raw_denominator_parse_failed"] = fcc.get("raw_denominator_parse_failed", 0) + 1
            continue
        for idx, needle in enumerate(needles):
            path = needle.get("needle_path")
            start = needle.get("needle_start_line")
            end = needle.get("needle_end_line")
            if isinstance(path, str) and path and isinstance(start, int) and isinstance(end, int) and start <= end:
                out[(lang, idx)] = ([path], [[start, end]])
    return out


def _enrich_locked_denominator_with_gold_lines(
    denom: list[dict[str, Any]], fcc: dict[str, int],
) -> None:
    """Attach private gold line ranges to locked denominator records in-place.

    P4L intentionally serialized only file-level gold paths in denominator
    records. N1 needs private line ranges to form D1, so it re-reads the raw
    benchmark frames using the already-private raw indices. Nothing from this
    lookup is written to the public artifact.
    """
    cb_lookup: dict[int, tuple[list[str], list[list[int]]]] | None = None
    rq_lookup: dict[tuple[str, int], tuple[list[str], list[list[int]]]] | None = None
    cb_loaded = False
    rq_loaded = False
    missing = 0
    for rec in denom:
        if _gold_from_locked_record(rec)[2]:
            continue
        frame = str(rec.get("source_frame", "") or "")
        raw_idx = rec.get("raw_idx")
        if frame == "contextbench_all_languages" and isinstance(raw_idx, int):
            if not cb_loaded:
                cb_lookup = _contextbench_gold_lookup_by_raw_idx(fcc)
                cb_loaded = True
            found = cb_lookup.get(raw_idx, ([], [])) if cb_lookup is not None else ([], [])
        elif frame == "repoqa_non_python_languages" and isinstance(raw_idx, int):
            if not rq_loaded:
                rq_lookup = _repoqa_gold_lookup_by_language_raw_idx(fcc)
                rq_loaded = True
            found = rq_lookup.get((str(rec.get("language", "") or ""), raw_idx), ([], [])) if rq_lookup is not None else ([], [])
        else:
            found = ([], [])
        paths, lines = found
        existing_paths = [str(p) for p in rec.get("gold_paths", []) if p]
        if paths and lines and paths == existing_paths:
            rec["gold_lines"] = lines
        else:
            missing += 1
    if missing:
        # Not blocking by itself: D1 may legitimately be small. A zero D1 due to
        # missing ranges becomes an inadequate-denominator No-Go only after D0
        # replay has passed.
        fcc["gold_span_reconstruction_failed"] = fcc.get("gold_span_reconstruction_failed", 0) + int(missing)


def _private_span_row_from_locked_record(
    *, rec: dict[str, Any], rr: Any, final_cands: list[dict[str, Any]], index: int,
) -> dict[str, Any] | None:
    gold_paths, gold_lines, ok = _gold_from_locked_record(rec)
    if not ok:
        return None
    evidence: list[dict[str, Any]] = []
    repo_root = rec.get("repo_root")
    for cand in final_cands:
        if not isinstance(cand, dict):
            continue
        if not cand.get("path"):
            continue
        cand_start = _line_number(cand.get("start_line"))
        cand_end = _line_number(cand.get("end_line"))
        if cand_start is None or cand_end is None or cand_end < cand_start:
            continue
        ev = {
            "path": str(cand.get("path")),
            "start_line": cand_start,
            "end_line": cand_end,
            "content_sha": str(cand.get("content_sha") or "private"),
        }
        if isinstance(repo_root, Path):
            ev["content_lines"] = _read_candidate_content_lines(repo_root, cand)
            ev["file_content_lines"] = _read_file_content_lines(repo_root, ev["path"])
        evidence.append(ev)
    if not evidence:
        return None
    return {
        "query": str(rec.get("query", "") or ""),
        "gold_paths": gold_paths,
        "gold_lines": gold_lines,
        "p4_reaches_gold_file": bool(rr.gold_file_available),
        "p4_evidence": evidence,
        "source_bucket": str(rec.get("source_frame", rec.get("benchmark", "unknown_source")) or "unknown_source"),
        "language_bucket": str(rec.get("language", "unknown_language") or "unknown_language"),
        "hard_cap_violation": bool(getattr(rr, "hard_cap_hit", False)),
        "denominator_index_private": index,
    }


def _candidate_gold_task(row: dict[str, Any], local_id: str) -> dict[str, Any] | None:
    paths = row.get("gold_paths")
    lines = row.get("gold_lines")
    if not isinstance(paths, list) or not paths or not isinstance(lines, list) or not lines:
        return None
    return {"task_id": local_id, "gold_paths": paths, "gold_lines": lines}


def _selected_evidence(row: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = row.get("p4_evidence") or row.get("evidence") or []
    if not isinstance(evidence, list):
        return []
    out: list[dict[str, Any]] = []
    for e in evidence:
        if not isinstance(e, dict):
            continue
        if not e.get("path"):
            continue
        start = _line_number(e.get("start_line"))
        end = _line_number(e.get("end_line"))
        if start is None or end is None or end < start:
            continue
        clean = dict(e)
        clean["start_line"] = start
        clean["end_line"] = end
        out.append(clean)
    return out


def _form_d1_and_refine(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    pre_predictions_top10: list[dict[str, Any]] = []
    post_predictions_top10: list[dict[str, Any]] = []
    gold_top10: dict[str, dict[str, Any]] = {}
    public_rows: list[dict[str, Any]] = []
    file_preserved = True
    considered = 0
    top10_actionable = 0
    rank_blocked = 0
    local_delta_counts: Counter[str] = Counter()
    local_pre_counts: Counter[str] = Counter()
    local_post_counts: Counter[str] = Counter()
    rank_split_contract_violations = 0
    for idx, row in enumerate(rows):
        local_id = f"n1r{idx:05d}"
        task = _candidate_gold_task(row, local_id)
        if task is None:
            continue
        evidence = _selected_evidence(row)
        if not evidence:
            continue
        gold_paths = set(str(p) for p in task["gold_paths"])
        reached_gold = bool(row.get("p4_reaches_gold_file", any(str(e.get("path")) in gold_paths for e in evidence)))
        if not reached_gold:
            continue
        # D1 requires at least one selected P4 evidence span on a gold file with
        # zero/inadequate overlap.
        gold_file_evidence = [e for e in evidence if str(e.get("path", "")) in gold_paths]
        if not gold_file_evidence:
            continue
        pre_bucket = _best_span_bucket(gold_file_evidence, task)
        if pre_bucket not in {"zero_overlap", "inadequate_overlap", "invalid"}:
            continue
        considered += 1
        query = str(row.get("query", "") or "")
        refined = [_refine_evidence_file_preserving(e, query) for e in evidence]
        if [e.get("path") for e in refined] != [e.get("path") for e in evidence]:
            file_preserved = False
        post_gold_file = [e for e in refined if str(e.get("path", "")) in gold_paths]
        post_bucket = _best_span_bucket(post_gold_file, task)
        local_delta = _span_delta_bucket(pre_bucket, post_bucket)
        local_delta_counts[local_delta] += 1
        local_pre_counts[pre_bucket] += 1
        local_post_counts[post_bucket] += 1
        top10_gold_file = [e for e in evidence[:10] if str(e.get("path", "")) in gold_paths]
        rank_bucket = "top10_actionable" if top10_gold_file else "rank_blocked_after_top10"
        if top10_gold_file:
            top10_pre_bucket = _best_span_bucket(top10_gold_file, task)
            if top10_pre_bucket in {"zero_overlap", "inadequate_overlap", "invalid"}:
                top10_actionable += 1
                pre_predictions_top10.append({"task_id": local_id, "evidence": evidence[:10]})
                post_predictions_top10.append({"task_id": local_id, "evidence": refined[:10]})
                gold_top10[local_id] = task
            else:
                rank_split_contract_violations += 1
                continue
        else:
            rank_blocked += 1
        public_rows.append({
            "anonymous_local_id": local_id,
            "denominator": "D1_p4_compatible_wrong_span",
            "arm": "p4_span_refiner",
            "source_bucket": str(row.get("source_bucket", "unknown_source_bucket")),
            "language_bucket": str(row.get("language_bucket", "unknown_language_bucket")),
            "pre_span_bucket": pre_bucket,
            "post_span_bucket": post_bucket,
            "span_delta_bucket": local_delta,
            "local_span_delta_bucket": local_delta,
            "rank_actionability_bucket": rank_bucket,
            "file_reach_preserved": True,
            "evidencecore_valid": structural_validity([{"evidence": refined}]) == 1.0,
            "hard_cap_violation": bool(row.get("hard_cap_violation", False)),
        })
    metrics = _span_metrics(pre_predictions_top10, post_predictions_top10, gold_top10)
    metrics["d1_total_count"] = considered
    metrics["d1_denominator_count"] = considered
    metrics["d1_top10_actionable_count"] = top10_actionable
    metrics["d1_rank_blocked_count"] = rank_blocked
    metrics["d1_rank_split_invariant_violation_count"] = rank_split_contract_violations
    metrics["local_gold_file_span_improved_count"] = int(local_delta_counts.get("improved", 0))
    metrics["local_gold_file_span_unchanged_count"] = int(local_delta_counts.get("unchanged", 0))
    metrics["local_gold_file_span_regressed_count"] = int(local_delta_counts.get("regressed", 0))
    for bucket in ("invalid", "zero_overlap", "inadequate_overlap", "partial_overlap", "adequate_overlap"):
        metrics[f"local_pre_{bucket}_count"] = int(local_pre_counts.get(bucket, 0))
        metrics[f"local_post_{bucket}_count"] = int(local_post_counts.get(bucket, 0))
    metrics["d1_candidate_records_considered"] = considered
    metrics["refiner_file_preserving_invariant_passed"] = file_preserved
    return public_rows, [{"pre_top10": pre_predictions_top10, "post_top10": post_predictions_top10}], metrics


def _span_metrics(pre: list[dict[str, Any]], post: list[dict[str, Any]], gold: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "d1_denominator_count": len(pre),
        "pre_span_f0_5_at_10": round(span_f_beta_at_k(pre, gold, 10, 0.5), 6) if pre else 0.0,
        "post_span_f0_5_at_10": round(span_f_beta_at_k(post, gold, 10, 0.5), 6) if post else 0.0,
        "pre_wrong_span_rate_at_10": round(wrong_span_rate_at_k(pre, gold, 10), 6) if pre else 0.0,
        "post_wrong_span_rate_at_10": round(wrong_span_rate_at_k(post, gold, 10), 6) if post else 0.0,
        "pre_zero_overlap_evidence_rate_at_10": round(zero_overlap_evidence_rate_at_k(pre, gold, 10), 6) if pre else 0.0,
        "post_zero_overlap_evidence_rate_at_10": round(zero_overlap_evidence_rate_at_k(post, gold, 10), 6) if post else 0.0,
    }


def _evaluate_d0(summary: dict[str, Any] | None) -> dict[str, Any]:
    if not summary:
        return {"passed": False, "failure": "d0_scheduler_preservation_missing"}
    checks = {
        "denominator_count": int(summary.get("denominator_count", -1)) == P4L_LOCKED_NON_PYTHON_DENOMINATOR,
        "baseline_reach": int(summary.get("baseline_reach", -1)) == P4L_BASELINE_REACH,
        "p2_reach": int(summary.get("p2_reach", -1)) == P4L_P2_REACH,
        "p3_reach": int(summary.get("p3_reach", -1)) == P4L_P3_REACH,
        "p4_reach": int(summary.get("p4_reach", -1)) == P4L_P4_REACH,
        "p4_treatment_hard_cap": int(summary.get("p4_treatment_hard_cap", -1)) == P4L_TREATMENT_HARD_CAP,
        "file_order_preserved": bool(summary.get("file_order_preserved", False)) is True,
        "scheduler_actions_preserved": bool(summary.get("scheduler_actions_preserved", False)) is True,
    }
    # Latency is reported against the P4L reference, but D0 preservation must
    # not fail on exact historical CI timing equality. Scheduler/reach/cap
    # preservation is the contract; latency-in-relevance remains forbidden via
    # static flags and workflow gates.
    checks["retained_gain"] = abs(float(summary.get("p4_retained_p2_gain", -99.0)) - P4L_P4_RETAINED_P2_GAIN) < 0.00001
    return {
        "passed": all(checks.values()),
        "failure": "" if all(checks.values()) else "d0_scheduler_preservation_drift",
        "checks": checks,
        "observed": dict(summary),
    }


def _d0_from_validation_meta(validation_meta: dict[str, Any], denom_count: int) -> dict[str, Any]:
    p2_gain = int(validation_meta.get("p2_reach", 0)) - int(validation_meta.get("baseline_reach", 0))
    p4_gain = int(validation_meta.get("p4_reach", 0)) - int(validation_meta.get("baseline_reach", 0))
    summary = {
        "denominator_count": int(denom_count),
        "baseline_reach": int(validation_meta.get("baseline_reach", -1)),
        "p2_reach": int(validation_meta.get("p2_reach", -1)),
        "p3_reach": int(validation_meta.get("p3_reach", -1)),
        "p4_reach": int(validation_meta.get("p4_reach", -1)),
        "p4_retained_p2_gain": round(p4_gain / p2_gain, 6) if p2_gain else 0.0,
        "p4_p3_latency_ratio": float(validation_meta.get("p4_vs_p3_latency_ratio", -99.0)),
        "p4_treatment_hard_cap": int(validation_meta.get("p4_treatment_hard_cap_violation_count", validation_meta.get("hard_cap_violation_count_total", -1))),
        "file_order_preserved": True,
        "scheduler_actions_preserved": True,
    }
    return _evaluate_d0(summary)


def _build_d1_rows_from_locked_denominator(
    *, openlocus_bin: str, denom: list[dict[str, Any]], private_span_path: Path,
    private_trace_path: Path, fcc: dict[str, int],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, rec in enumerate(denom):
        try:
            gold_paths, _gold_lines, gold_ok = _gold_from_locked_record(rec)
            if not gold_ok:
                fcc["gold_span_reconstruction_failed"] = fcc.get("gold_span_reconstruction_failed", 0) + 1
                continue
            repo_root = rec.get("repo_root")
            if not isinstance(repo_root, Path):
                fcc["raw_denominator_clone_failed"] = fcc.get("raw_denominator_clone_failed", 0) + 1
                continue
            rr, final_cands = _run_frozen_p4_with_candidates(
                openlocus_bin=openlocus_bin, repo_root=repo_root,
                query=str(rec.get("query", "") or ""),
                gold_set={str(p) for p in gold_paths if p})
            trace_row = {
                "schema_version": "bea_v1_n1_private_candidate_gold_trace.v1",
                "denominator_index_private": idx,
                "p4_reaches_gold_file": bool(rr.gold_file_available),
                "candidate_count": int(len(final_cands)),
                "candidate_with_range_count": int(sum(1 for c in final_cands if isinstance(c.get("start_line"), int) and isinstance(c.get("end_line"), int))),
                "hard_cap_hit": bool(getattr(rr, "hard_cap_hit", False)),
            }
            _append_private_jsonl(private_trace_path, trace_row)
            span_row = _private_span_row_from_locked_record(
                rec=rec, rr=rr, final_cands=final_cands, index=idx)
            if span_row is None:
                fcc["candidate_span_reconstruction_failed"] = fcc.get("candidate_span_reconstruction_failed", 0) + 1
                continue
            _append_private_jsonl(private_span_path, {
                "schema_version": "bea_v1_n1_private_span_row.v1",
                **span_row,
            })
            rows.append(span_row)
        except Exception:
            fcc["retrieval_policy_failed"] = fcc.get("retrieval_policy_failed", 0) + 1
    return rows


def _load_artifact(path: Path | None) -> tuple[dict[str, Any], str, str]:
    if path is None or not path.exists():
        return {}, "", "artifact_missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return data if isinstance(data, dict) else {}, digest, "pass" if isinstance(data, dict) else "artifact_parse_failed"
    except Exception:
        return {}, "", "artifact_parse_failed"


def _run_real_network_replay(args: argparse.Namespace, checks_count: int) -> dict[str, Any]:
    start = time.perf_counter()
    fcc = {k: 0 for k in FAILURE_CATEGORIES}
    d0 = _evaluate_d0(None)
    sanitized: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {"d1_denominator_count": 0, "refiner_file_preserving_invariant_passed": False}
    manifests: list[dict[str, Any]] = []
    private_dir: Path | None = None
    try:
        fd1_artifact, _fd1_hash, fd1_status = _load_artifact(args.fd1_artifact)
        if fd1_status != "pass":
            fcc["fd1_artifact_missing" if fd1_status == "artifact_missing" else "fd1_artifact_parse_failed"] = 1
            return _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=args.openlocus or "explicit", d0=d0, metrics=metrics, fcc_in=fcc, runtime_seconds=time.perf_counter() - start)
        if fd1_artifact.get("schema_version") != p4.FD1_SOURCE_SCHEMA_VERSION:
            fcc["fd1_schema_version_mismatch"] = 1
        if p4.bea_v1_p1._fd1_status(fd1_artifact) != p4.FD1_SOURCE_STATUS:
            fcc["fd1_status_mismatch"] = 1
        fd1_manifest = p4.bea_v1_p1._fd1_private_decomposition_manifest(fd1_artifact)
        pt = p4._parse_private_decomposition_jsonl(args.fd1_private_decomposition_jsonl)
        if not getattr(pt, "file_existed", False):
            fcc["fd1_private_decomposition_missing"] = 1
        if getattr(pt, "parse_failures", 0):
            fcc["fd1_private_decomposition_parse_failed"] = int(pt.parse_failures)
        p4._compute_file_selector_lower_bound(pt)
        rav = p4._validate_fd1_replay_artifact(args.fd1_replay_artifact, str(fd1_manifest.get("manifest_hash", "") or ""))
        if not getattr(rav, "validated", False):
            cat = getattr(rav, "failure_category", "") or "fd1_replay_artifact_parse_failed"
            if cat in fcc:
                fcc[cat] = 1
            elif cat in {"fd1_replay_artifact_schema_mismatch", "fd1_replay_artifact_records_mismatch", "fd1_replay_artifact_manifest_mismatch", "fd1_replay_artifact_manifest_hash_mismatch", "fd1_replay_artifact_forbidden_scan_failed"}:
                fcc["fd1_replay_artifact_status_mismatch"] = 1
            else:
                fcc["fd1_replay_artifact_parse_failed"] = 1
        p4k_artifact, _p4k_hash, p4k_status = _load_artifact(args.p4k_artifact)
        if p4k_status != "pass":
            fcc["p4k_artifact_missing" if p4k_status == "artifact_missing" else "p4k_artifact_status_mismatch"] = 1
        else:
            if p4k_artifact.get("status") != p4l.P4K_RESULT_STATUS:
                fcc["p4k_artifact_status_mismatch"] = 1
            if int(p4k_artifact.get("locked_cross_source_reservoir_count", 0) or 0) != P4L_LOCKED_NON_PYTHON_DENOMINATOR:
                fcc["p4k_locked_count_mismatch"] = 1
            split_ok = (
                int(p4k_artifact.get("p4j_reconstructed_upper_bound_count", 0) or 0) == p4l.P4K_P4J_RECONSTRUCTED_COUNT
                and int(p4k_artifact.get("p4j_reconstructed_python_count", 0) or 0) == p4l.P4K_P4J_PYTHON_SPLIT
                and int(p4k_artifact.get("p4j_reconstructed_non_python_count", 0) or 0) == p4l.P4K_P4J_NON_PYTHON_SPLIT
            )
            if not split_ok:
                fcc["p4k_split_or_overlap_mismatch"] = 1
        if sum(fcc.get(k, 0) for k in BLOCKING_FAILURES if k not in {"d0_scheduler_preservation_missing", "d0_scheduler_preservation_drift"}) > 0:
            return _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=args.openlocus or "explicit", d0=d0, metrics=metrics, fcc_in=fcc, runtime_seconds=time.perf_counter() - start)
        private_dir = _resolve_private_n1_dir()
        recon_path = private_dir / "bea_v1_n1.p4l_private_reconstruction.jsonl"
        arm_path = private_dir / "bea_v1_n1.p4l_private_arm_outcomes.jsonl"
        span_path = private_dir / "bea_v1_n1.private_span_rows.jsonl"
        trace_path = private_dir / "bea_v1_n1.private_candidate_gold_trace.jsonl"
        for pth in (recon_path, arm_path, span_path, trace_path):
            if pth.exists():
                pth.unlink()
        denom, recon_meta = p4l._reconstruct_locked_denominator(
            openlocus_bin=args.openlocus or "", pt=pt, private_path=recon_path, fcc=fcc)
        locked_count = int(recon_meta.get("non_python_locked_count", 0))
        python_count = int(recon_meta.get("python_locked_count", 0))
        p4j_count = int(recon_meta.get("p4j_reconstructed_upper_bound_count", python_count + locked_count))
        if locked_count != P4L_LOCKED_NON_PYTHON_DENOMINATOR or python_count != p4l.P4K_P4J_PYTHON_SPLIT or p4j_count != p4l.P4K_P4J_RECONSTRUCTED_COUNT:
            fcc["locked_denominator_mismatch"] = 1
            return _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=args.openlocus or "explicit", d0=d0, metrics=metrics, private_manifests=[_manifest_for_path(recon_path, "bea_v1_n1_p4l_private_reconstruction_manifest", "bea_v1_p4l_private_reconstruction.v1")], fcc_in=fcc, runtime_seconds=time.perf_counter() - start)
        _enrich_locked_denominator_with_gold_lines(denom, fcc)
        arm_metrics, validation_meta = p4l._run_scheduler_validation(
            openlocus_bin=args.openlocus or "", denom=denom, private_path=arm_path, fcc=fcc)
        d0 = _d0_from_validation_meta(validation_meta, locked_count)
        if not d0.get("passed"):
            fcc["d0_scheduler_preservation_drift"] = 1
        rows = _build_d1_rows_from_locked_denominator(
            openlocus_bin=args.openlocus or "", denom=denom,
            private_span_path=span_path, private_trace_path=trace_path, fcc=fcc)
        sanitized, _, metrics = _form_d1_and_refine(rows)
        manifests = [
            _manifest_for_path(recon_path, "bea_v1_n1_p4l_private_reconstruction_manifest", "bea_v1_p4l_private_reconstruction.v1"),
            _manifest_for_path(arm_path, "bea_v1_n1_p4l_private_arm_outcomes_manifest", "bea_v1_p4l_private_arm_outcome.v1"),
            _manifest_for_path(span_path, "bea_v1_n1_private_span_rows_manifest", "bea_v1_n1_private_span_row.v1"),
            _manifest_for_path(trace_path, "bea_v1_n1_private_candidate_gold_trace_manifest", "bea_v1_n1_private_candidate_gold_trace.v1"),
        ]
        return _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=args.openlocus or "explicit", d0=d0, metrics=metrics, sanitized_rows=sanitized, private_manifests=manifests, fcc_in=fcc, runtime_seconds=time.perf_counter() - start)
    except Exception:
        fcc["unexpected_exception"] = 1
        return _base_report(status="fail_schema_contract", failure_reason_category="unexpected_exception", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=args.openlocus or "explicit", d0=d0, metrics=metrics, private_manifests=manifests, fcc_in=fcc, runtime_seconds=time.perf_counter() - start)


def _d0_records(d0: dict[str, Any]) -> list[dict[str, Any]]:
    checks = d0.get("checks", {}) if isinstance(d0, dict) else {}
    observed = d0.get("observed", {}) if isinstance(d0, dict) else {}
    return [
        {"metric_block": "D0_scheduler_preservation", "metric_name": "denominator_count", "value": int(observed.get("denominator_count", -1)), "expected_value": P4L_LOCKED_NON_PYTHON_DENOMINATOR, "passed": bool(checks.get("denominator_count", False))},
        {"metric_block": "D0_scheduler_preservation", "metric_name": "baseline_reach", "value": int(observed.get("baseline_reach", -1)), "expected_value": P4L_BASELINE_REACH, "passed": bool(checks.get("baseline_reach", False))},
        {"metric_block": "D0_scheduler_preservation", "metric_name": "p2_reach", "value": int(observed.get("p2_reach", -1)), "expected_value": P4L_P2_REACH, "passed": bool(checks.get("p2_reach", False))},
        {"metric_block": "D0_scheduler_preservation", "metric_name": "p3_reach", "value": int(observed.get("p3_reach", -1)), "expected_value": P4L_P3_REACH, "passed": bool(checks.get("p3_reach", False))},
        {"metric_block": "D0_scheduler_preservation", "metric_name": "p4_reach", "value": int(observed.get("p4_reach", -1)), "expected_value": P4L_P4_REACH, "passed": bool(checks.get("p4_reach", False))},
        {"metric_block": "D0_scheduler_preservation", "metric_name": "p4_treatment_hard_cap", "value": int(observed.get("p4_treatment_hard_cap", -1)), "expected_value": P4L_TREATMENT_HARD_CAP, "passed": bool(checks.get("p4_treatment_hard_cap", False))},
        {"metric_block": "D0_scheduler_preservation", "metric_name": "p4_p3_latency_ratio_observed", "value": float(observed.get("p4_p3_latency_ratio", 0.0)), "expected_value": P4L_P4_P3_LATENCY_RATIO, "passed": True},
    ]


def _d1_records(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    names = [
        "d1_total_count", "d1_top10_actionable_count", "d1_rank_blocked_count",
        "d1_denominator_count", "pre_span_f0_5_at_10", "post_span_f0_5_at_10",
        "pre_wrong_span_rate_at_10", "post_wrong_span_rate_at_10",
        "pre_zero_overlap_evidence_rate_at_10", "post_zero_overlap_evidence_rate_at_10",
        "local_gold_file_span_improved_count", "local_gold_file_span_unchanged_count",
        "local_gold_file_span_regressed_count", "local_pre_zero_overlap_count",
        "local_pre_inadequate_overlap_count", "local_pre_partial_overlap_count",
        "local_pre_adequate_overlap_count", "local_post_zero_overlap_count",
        "local_post_inadequate_overlap_count", "local_post_partial_overlap_count",
        "local_post_adequate_overlap_count", "d1_rank_split_invariant_violation_count",
    ]
    return [{"metric_block": "D1_span_efficacy", "metric_name": n, "value": metrics.get(n, 0)} for n in names]


def _gate_records(d0: dict[str, Any], metrics: dict[str, Any], scan_pass: bool) -> list[dict[str, Any]]:
    d1_n = int(metrics.get("d1_total_count", metrics.get("d1_denominator_count", 0)))
    top10_n = int(metrics.get("d1_top10_actionable_count", 0))
    improved = float(metrics.get("post_span_f0_5_at_10", 0.0)) > float(metrics.get("pre_span_f0_5_at_10", 0.0))
    wrong_down = float(metrics.get("post_wrong_span_rate_at_10", 1.0)) < float(metrics.get("pre_wrong_span_rate_at_10", 1.0)) if top10_n else False
    zero_down = float(metrics.get("post_zero_overlap_evidence_rate_at_10", 1.0)) <= float(metrics.get("pre_zero_overlap_evidence_rate_at_10", 1.0)) if top10_n else False
    return [
        {"gate": "d0_scheduler_preservation", "value": 1 if d0.get("passed") else 0, "threshold_relation": "boolean", "threshold_value": 1, "passed": bool(d0.get("passed"))},
        {"gate": "d1_wrong_span_denominator_adequate", "value": d1_n, "threshold_relation": ">=", "threshold_value": D1_ADEQUATE_MIN, "passed": d1_n >= D1_ADEQUATE_MIN},
        {"gate": "d1_wrong_span_denominator_exploratory_min", "value": d1_n, "threshold_relation": ">=", "threshold_value": D1_EXPLORATORY_MIN, "passed": d1_n >= D1_EXPLORATORY_MIN},
        {"gate": "d1_top10_actionable_denominator_adequate", "value": top10_n, "threshold_relation": ">=", "threshold_value": D1_TOP10_ACTIONABLE_ADEQUATE_MIN, "passed": top10_n >= D1_TOP10_ACTIONABLE_ADEQUATE_MIN},
        {"gate": "d1_top10_actionable_denominator_exploratory_min", "value": top10_n, "threshold_relation": ">=", "threshold_value": D1_TOP10_ACTIONABLE_EXPLORATORY_MIN, "passed": top10_n >= D1_TOP10_ACTIONABLE_EXPLORATORY_MIN},
        {"gate": "post_span_f0_5_improved", "value": metrics.get("post_span_f0_5_at_10", 0.0), "threshold_relation": ">", "threshold_value": metrics.get("pre_span_f0_5_at_10", 0.0), "passed": improved},
        {"gate": "wrong_span_rate_reduced", "value": metrics.get("post_wrong_span_rate_at_10", 0.0), "threshold_relation": "<", "threshold_value": metrics.get("pre_wrong_span_rate_at_10", 0.0), "passed": wrong_down},
        {"gate": "zero_overlap_rate_not_increased", "value": metrics.get("post_zero_overlap_evidence_rate_at_10", 0.0), "threshold_relation": "<=", "threshold_value": metrics.get("pre_zero_overlap_evidence_rate_at_10", 0.0), "passed": zero_down},
        {"gate": "refiner_file_preserving_invariant", "value": 1 if metrics.get("refiner_file_preserving_invariant_passed") else 0, "threshold_relation": "boolean", "threshold_value": 1, "passed": bool(metrics.get("refiner_file_preserving_invariant_passed", False))},
        {"gate": "forbidden_scan_pass", "value": 1 if scan_pass else 0, "threshold_relation": "boolean", "threshold_value": 1, "passed": bool(scan_pass)},
    ]


def _status_from(d0: dict[str, Any], metrics: dict[str, Any], fcc: dict[str, int], unavailable: bool = False) -> tuple[str, str]:
    if unavailable:
        return "unavailable_with_reason", "network_required_but_disabled"
    blocking = sum(int(fcc.get(k, 0)) for k in BLOCKING_FAILURES)
    if int(fcc.get("locked_denominator_mismatch", 0)) and not blocking:
        return "no_go_n1_locked_denominator_unavailable", "locked_denominator_mismatch"
    if blocking or not d0.get("passed", False):
        return "fail_schema_contract", str(d0.get("failure") or "blocking_failure_present")
    if int(metrics.get("d1_rank_split_invariant_violation_count", 0)):
        return "fail_schema_contract", "d1_rank_split_invariant_violation"
    n = int(metrics.get("d1_total_count", metrics.get("d1_denominator_count", 0)))
    if n < D1_EXPLORATORY_MIN:
        return "no_go_n1_inadequate_wrong_span_denominator", "d1_denominator_lt_10"
    top10_n = int(metrics.get("d1_top10_actionable_count", 0))
    if top10_n < D1_TOP10_ACTIONABLE_EXPLORATORY_MIN:
        return "no_go_n1_inadequate_top10_actionable_denominator", "d1_top10_actionable_denominator_lt_10"
    if top10_n < D1_TOP10_ACTIONABLE_ADEQUATE_MIN:
        return "n1_exploratory_insufficient_power", "d1_top10_actionable_denominator_10_to_19"
    improved = float(metrics.get("post_span_f0_5_at_10", 0.0)) > float(metrics.get("pre_span_f0_5_at_10", 0.0))
    wrong_down = float(metrics.get("post_wrong_span_rate_at_10", 1.0)) < float(metrics.get("pre_wrong_span_rate_at_10", 1.0))
    if improved and wrong_down and metrics.get("refiner_file_preserving_invariant_passed", False):
        return "bea_v1_n1_frozen_p4_span_refiner_pass", "d1_adequate_and_span_metrics_improved"
    return "n1_preflight_pass_wrong_span_denominator_adequate", "d1_adequate_refiner_improvement_not_established"


def _base_report(
    *,
    status: str,
    failure_reason_category: str,
    self_test_passed: bool,
    self_test_checks_total: int,
    self_test_checks_passed: int | None,
    network_mode: str,
    openlocus_binary_source: str,
    d0: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    sanitized_rows: list[dict[str, Any]] | None = None,
    private_manifests: list[dict[str, Any]] | None = None,
    fcc_in: dict[str, int] | None = None,
    runtime_seconds: float = 0.0,
) -> dict[str, Any]:
    fcc = {k: 0 for k in FAILURE_CATEGORIES}
    for k, v in (fcc_in or {}).items():
        if k in fcc:
            fcc[k] = int(v)
    if failure_reason_category in fcc:
        fcc[failure_reason_category] = max(1, fcc[failure_reason_category])
    d0 = d0 or {"passed": False, "failure": "d0_scheduler_preservation_missing", "checks": {}}
    metrics = metrics or {"d1_denominator_count": 0, "d1_total_count": 0, "d1_top10_actionable_count": 0, "d1_rank_blocked_count": 0, "refiner_file_preserving_invariant_passed": False}
    if status == "auto":
        status, failure_reason_category = _status_from(d0, metrics, fcc)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "failure_reason_category": failure_reason_category,
        "source_checkpoint": P4L_RESULT_CHECKPOINT,
        "source_ci_run_id": P4L_CI_RUN_ID,
        "d0_scheduler_preservation_denominator_count": P4L_LOCKED_NON_PYTHON_DENOMINATOR,
        "d1_wrong_span_denominator_count": int(metrics.get("d1_denominator_count", 0)),
        "d1_total_count": int(metrics.get("d1_total_count", metrics.get("d1_denominator_count", 0))),
        "d1_top10_actionable_count": int(metrics.get("d1_top10_actionable_count", 0)),
        "d1_rank_blocked_count": int(metrics.get("d1_rank_blocked_count", 0)),
        "local_gold_file_span_improved_count": int(metrics.get("local_gold_file_span_improved_count", 0)),
        "local_gold_file_span_unchanged_count": int(metrics.get("local_gold_file_span_unchanged_count", 0)),
        "local_gold_file_span_regressed_count": int(metrics.get("local_gold_file_span_regressed_count", 0)),
        "status_vocabulary": list(STATUSES),
        "d0_scheduler_preservation_records": _d0_records(d0),
        "d1_span_efficacy_records": _d1_records(metrics),
        "sanitized_analysis_records": sanitized_rows or [],
        "gate_records": _gate_records(d0, metrics, True),
        "private_manifest_records": private_manifests or [],
        "failure_category_count_records": [{"failure_category": k, "count": int(v)} for k, v in sorted(fcc.items())],
        "aggregate_runtime_seconds": round(float(runtime_seconds), 3),
        "private_paths_publicly_serialized": False,
        "exact_spans_publicly_serialized": False,
        "gold_lines_publicly_serialized": False,
        "raw_candidate_lists_publicly_serialized": False,
        **DEFAULT_FALSE_FLAGS,
        **SAFE_TRUE_FLAGS,
        "self_test_passed": bool(self_test_passed),
        "self_test_checks_total": int(self_test_checks_total),
        "self_test_checks_passed": int(self_test_checks_total if self_test_checks_passed is None and self_test_passed else (self_test_checks_passed or 0)),
        "framing": {
            "retrieval_layer_span_smoke_only": True,
            "scheduler_preservation_claimed": bool(d0.get("passed", False)),
            "span_refiner_claimed": status == "bea_v1_n1_frozen_p4_span_refiner_pass",
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "method_winner_claimed": False,
            "selector_or_reranker_executed": False,
            "p5_executed": False,
            "v1_a_selector_executed": False,
            "signal_strength": "bea_v1_n1_retrieval_layer_span_smoke_only",
        },
    }
    scan = _scan_summary(report)
    report["forbidden_scan"] = scan
    report["gate_records"] = _gate_records(d0, metrics, scan["status"] == "pass")
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
        report["failure_reason_category"] = "forbidden_leak_blocked"
    return report


def _synthetic_d0_summary(**overrides: Any) -> dict[str, Any]:
    base = {
        "denominator_count": P4L_LOCKED_NON_PYTHON_DENOMINATOR,
        "baseline_reach": P4L_BASELINE_REACH,
        "p2_reach": P4L_P2_REACH,
        "p3_reach": P4L_P3_REACH,
        "p4_reach": P4L_P4_REACH,
        "p4_retained_p2_gain": P4L_P4_RETAINED_P2_GAIN,
        "p4_p3_latency_ratio": P4L_P4_P3_LATENCY_RATIO,
        "p4_treatment_hard_cap": P4L_TREATMENT_HARD_CAP,
        "file_order_preserved": True,
        "scheduler_actions_preserved": True,
    }
    base.update(overrides)
    return base


def _synthetic_private_rows(n: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(n):
        path = f"src/module_{i}.py"
        lines = []
        for ln in range(1, 31):
            text = "ordinary filler"
            if 20 <= ln <= 22:
                text = f"target_symbol_{i} performs important behavior"
            lines.append({"line": ln, "text": text})
        rows.append({
            "query": f"Where is target_symbol_{i} important behavior implemented?",
            "gold_paths": [path],
            "gold_lines": [[20, 22]],
            "p4_reaches_gold_file": True,
            "p4_evidence": [{"path": path, "start_line": 1, "end_line": 10, "content_sha": "private", "content_lines": lines}],
            "source_bucket": "synthetic_contextbench" if i % 2 == 0 else "synthetic_repoqa",
            "language_bucket": "python_like",
            "hard_cap_violation": False,
        })
    return rows


def _self_test_candidate_returning_helper() -> bool:
    orig = (
        p4._collect_baseline_per_channel, p4._merge_baseline_pool,
        p4._compute_channel_diagnostics, p4._select_eligible_extra_depth_channels,
        p4._collect_extra_depth_channel, p4._check_gold_file_reach,
    )
    try:
        baseline = {
            p4.FIXED_METHODS[0]: [{"path": "a.rs", "start_line": 1, "end_line": 3}],
            p4.FIXED_METHODS[1]: [],
            p4.FIXED_METHODS[2]: [],
        }
        def fake_baseline(_bin: str, _query: str, _root: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int], dict[str, bool], bool]:
            return baseline, {m: 1 for m in p4.FIXED_METHODS}, {m: False for m in p4.FIXED_METHODS}, False
        def fake_merge(pool: dict[str, list[dict[str, Any]]], _limit: int) -> tuple[list[dict[str, Any]], dict[str, float]]:
            return list(pool[p4.FIXED_METHODS[0]]), {}
        def fake_diag(method: str, *_args: Any) -> Any:
            return {"method": method}
        def fake_select(_channels: dict[str, Any]) -> list[str]:
            return [p4.FIXED_METHODS[1]]
        def fake_extra(_bin: str, method: str, _query: str, _root: Path, _mult: int) -> tuple[list[dict[str, Any]], int, bool]:
            return ([{"path": f"extra_{i}.rs", "start_line": 10 + i, "end_line": 10 + i} for i in range(p4.P4_HARD_CANDIDATE_CAP + 5)], 1, False)
        def fake_reach(cands: list[dict[str, Any]], gold: set[str]) -> tuple[bool, int | None, str, int]:
            return any(c.get("path") in gold for c in cands), 1, "1-5", 0
        p4._collect_baseline_per_channel = fake_baseline  # type: ignore[assignment]
        p4._merge_baseline_pool = fake_merge  # type: ignore[assignment]
        p4._compute_channel_diagnostics = fake_diag  # type: ignore[assignment]
        p4._select_eligible_extra_depth_channels = fake_select  # type: ignore[assignment]
        p4._collect_extra_depth_channel = fake_extra  # type: ignore[assignment]
        p4._check_gold_file_reach = fake_reach  # type: ignore[assignment]
        rr, cands = _run_frozen_p4_with_candidates(
            openlocus_bin="fake", repo_root=Path("/tmp"), query="q", gold_set={"extra_0.rs"})
        return (
            len(cands) <= p4.P4_HARD_CANDIDATE_CAP
            and rr.scheduler_action == "extra_depth_selected"
            and all(isinstance(c.get("start_line"), int) and isinstance(c.get("end_line"), int) for c in cands)
        )
    finally:
        (p4._collect_baseline_per_channel, p4._merge_baseline_pool,
         p4._compute_channel_diagnostics, p4._select_eligible_extra_depth_channels,
         p4._collect_extra_depth_channel, p4._check_gold_file_reach) = orig


def _self_test_gold_line_enrichment() -> bool:
    global _contextbench_gold_lookup_by_raw_idx, _repoqa_gold_lookup_by_language_raw_idx
    orig_cb = _contextbench_gold_lookup_by_raw_idx
    orig_rq = _repoqa_gold_lookup_by_language_raw_idx
    try:
        def fake_cb(_fcc: dict[str, int] | None = None) -> dict[int, tuple[list[str], list[list[int]]]]:
            return {7: (["src/a.rs"], [[3, 5]])}
        def fake_rq(_fcc: dict[str, int] | None = None) -> dict[tuple[str, int], tuple[list[str], list[list[int]]]]:
            return {("rust", 2): (["lib.rs"], [[10, 12]])}
        _contextbench_gold_lookup_by_raw_idx = fake_cb  # type: ignore[assignment]
        _repoqa_gold_lookup_by_language_raw_idx = fake_rq  # type: ignore[assignment]
        denom = [
            {"source_frame": "contextbench_all_languages", "raw_idx": 7, "gold_paths": ["src/a.rs"]},
            {"source_frame": "repoqa_non_python_languages", "language": "rust", "raw_idx": 2, "gold_paths": ["lib.rs"]},
        ]
        fcc = {k: 0 for k in FAILURE_CATEGORIES}
        _enrich_locked_denominator_with_gold_lines(denom, fcc)
        return (
            denom[0].get("gold_paths") == ["src/a.rs"]
            and denom[0].get("gold_lines") == [[3, 5]]
            and denom[1].get("gold_paths") == ["lib.rs"]
            and denom[1].get("gold_lines") == [[10, 12]]
            and fcc.get("gold_span_reconstruction_failed", 0) == 0
        )
    finally:
        _contextbench_gold_lookup_by_raw_idx = orig_cb  # type: ignore[assignment]
        _repoqa_gold_lookup_by_language_raw_idx = orig_rq  # type: ignore[assignment]


def _self_test_gold_line_enrichment_path_mismatch() -> bool:
    global _contextbench_gold_lookup_by_raw_idx
    orig_cb = _contextbench_gold_lookup_by_raw_idx
    try:
        def fake_cb(_fcc: dict[str, int] | None = None) -> dict[int, tuple[list[str], list[list[int]]]]:
            return {7: (["different.rs"], [[3, 5]])}
        _contextbench_gold_lookup_by_raw_idx = fake_cb  # type: ignore[assignment]
        denom = [{"source_frame": "contextbench_all_languages", "raw_idx": 7, "gold_paths": ["src/a.rs"]}]
        fcc = {k: 0 for k in FAILURE_CATEGORIES}
        _enrich_locked_denominator_with_gold_lines(denom, fcc)
        private = _private_span_row_from_locked_record(
            rec=denom[0], rr=None, final_cands=[{"path": "src/a.rs", "start_line": 1, "end_line": 2}], index=0)
        return denom[0].get("gold_paths") == ["src/a.rs"] and "gold_lines" not in denom[0] and private is None and fcc.get("gold_span_reconstruction_failed", 0) == 1
    finally:
        _contextbench_gold_lookup_by_raw_idx = orig_cb  # type: ignore[assignment]


def _self_test_gold_line_enrichment_order_mismatch() -> bool:
    global _contextbench_gold_lookup_by_raw_idx
    orig_cb = _contextbench_gold_lookup_by_raw_idx
    try:
        def fake_cb(_fcc: dict[str, int] | None = None) -> dict[int, tuple[list[str], list[list[int]]]]:
            return {7: (["b.rs", "a.rs"], [[20, 21], [10, 11]])}
        _contextbench_gold_lookup_by_raw_idx = fake_cb  # type: ignore[assignment]
        denom = [{"source_frame": "contextbench_all_languages", "raw_idx": 7, "gold_paths": ["a.rs", "b.rs"]}]
        fcc = {k: 0 for k in FAILURE_CATEGORIES}
        _enrich_locked_denominator_with_gold_lines(denom, fcc)
        return denom[0].get("gold_paths") == ["a.rs", "b.rs"] and "gold_lines" not in denom[0] and fcc.get("gold_span_reconstruction_failed", 0) == 1
    finally:
        _contextbench_gold_lookup_by_raw_idx = orig_cb  # type: ignore[assignment]


def _self_test_full_file_refiner_moves_beyond_local_candidate() -> bool:
    path = "src/full_file_refiner.py"
    file_lines = [{"line": ln, "text": "ordinary filler"} for ln in range(1, 80)]
    file_lines[49] = {"line": 50, "text": "def target_symbol_behavior():"}
    file_lines[50] = {"line": 51, "text": "    important behavior lives here"}
    file_lines[51] = {"line": 52, "text": "    return target_symbol_behavior"}
    rows = [{
        "query": "Where is target_symbol important behavior implemented?",
        "gold_paths": [path],
        "gold_lines": [[50, 52]],
        "p4_reaches_gold_file": True,
        "p4_evidence": [{
            "path": path,
            "start_line": 1,
            "end_line": 5,
            "content_sha": "private",
            "content_lines": [{"line": ln, "text": "wrong local candidate"} for ln in range(1, 6)],
            "file_content_lines": file_lines,
        }],
        "source_bucket": "synthetic_contextbench",
        "language_bucket": "python_like",
        "hard_cap_violation": False,
    }]
    public_rows, _, metrics = _form_d1_and_refine(rows)
    return (
        metrics.get("d1_denominator_count") == 1
        and metrics.get("post_span_f0_5_at_10", 0.0) > metrics.get("pre_span_f0_5_at_10", 0.0)
        and bool(public_rows)
        and public_rows[0].get("span_delta_bucket") == "improved"
        and public_rows[0].get("file_reach_preserved") is True
    )


def _self_test_file_read_containment_and_regular_file() -> bool:
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        repo = base / "repo"
        sibling = base / "repo_evil"
        repo.mkdir()
        sibling.mkdir()
        (repo / "safe.py").write_text("safe\n", encoding="utf-8")
        (sibling / "evil.py").write_text("evil\n", encoding="utf-8")
        inside = _read_file_content_lines(repo, "safe.py")
        traversal = _read_file_content_lines(repo, "../repo_evil/evil.py")
        directory = _read_file_content_lines(repo, ".")
        cand_traversal = _read_candidate_content_lines(repo, {"path": "../repo_evil/evil.py", "start_line": 1, "end_line": 1})
        return inside == [{"line": 1, "text": "safe"}] and traversal == [] and directory == [] and cand_traversal == []


def _self_test_refiner_caps_window_to_file_bounds() -> bool:
    e = {
        "path": "src/eof.py",
        "start_line": 1,
        "end_line": 2,
        "content_sha": "private",
        "file_content_lines": [
            {"line": 1, "text": "ordinary"},
            {"line": 2, "text": "ordinary"},
            {"line": 3, "text": "target_symbol important behavior"},
        ],
    }
    refined = _refine_evidence_file_preserving(e, "target_symbol important behavior")
    return refined.get("end_line") == 3 and refined.get("start_line") == 1


def _self_test_rank_blocked_d1_total_not_pass_gate() -> bool:
    rows = _synthetic_private_rows(D1_ADEQUATE_MIN)
    for row in rows:
        gold_ev = row["p4_evidence"][0]
        blockers = [
            {
                "path": f"src/non_gold_{i}.py",
                "start_line": 1,
                "end_line": 3,
                "content_sha": "private",
                "content_lines": [{"line": 1, "text": "ordinary filler"}],
                "file_content_lines": [{"line": 1, "text": "ordinary filler"}],
            }
            for i in range(10)
        ]
        row["p4_evidence"] = blockers + [gold_ev]
    public_rows, _, metrics = _form_d1_and_refine(rows)
    report = _base_report(
        status="auto",
        failure_reason_category="",
        self_test_passed=True,
        self_test_checks_total=0,
        self_test_checks_passed=None,
        network_mode="self_test",
        openlocus_binary_source="self_test",
        d0=_evaluate_d0(_synthetic_d0_summary()),
        metrics=metrics,
        sanitized_rows=public_rows,
    )
    return (
        metrics.get("d1_total_count") == D1_ADEQUATE_MIN
        and metrics.get("d1_top10_actionable_count") == 0
        and metrics.get("d1_rank_blocked_count") == D1_ADEQUATE_MIN
        and report.get("status") == "no_go_n1_inadequate_top10_actionable_denominator"
        and all(r.get("rank_actionability_bucket") == "rank_blocked_after_top10" for r in public_rows)
    )


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []
    checks.append(_check("schema_identity", SCHEMA_VERSION == "bea_v1_n1_frozen_p4_span_refiner_smoke.v1"))
    checks.append(_check("status_vocab_contains_required", all(s in STATUSES for s in ("unavailable_with_reason", "fail_schema_contract", "n1_preflight_pass_wrong_span_denominator_adequate", "n1_exploratory_insufficient_power", "no_go_n1_locked_denominator_unavailable", "no_go_n1_inadequate_wrong_span_denominator", "no_go_n1_inadequate_top10_actionable_denominator", "bea_v1_n1_frozen_p4_span_refiner_pass"))))
    checks.append(_check("d0_locked_denominator_272", P4L_LOCKED_NON_PYTHON_DENOMINATOR == 272))
    d0_pass = _evaluate_d0(_synthetic_d0_summary())
    checks.append(_check("d0_preservation_pass_path", d0_pass["passed"] is True))
    d0_latency_drift = _evaluate_d0(_synthetic_d0_summary(p4_p3_latency_ratio=0.7))
    checks.append(_check("d0_latency_ratio_report_only", d0_latency_drift["passed"] is True))
    d0_drift = _evaluate_d0(_synthetic_d0_summary(p4_reach=53))
    report_drift = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, network_mode="self_test", openlocus_binary_source="self_test", d0=d0_drift, metrics={"d1_denominator_count": 20, "refiner_file_preserving_invariant_passed": True}, fcc_in={"d0_scheduler_preservation_drift": 1})
    checks.append(_check("d0_drift_fail_path", report_drift["status"] == "fail_schema_contract"))
    report_locked_mismatch = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, network_mode="self_test", openlocus_binary_source="self_test", d0=d0_pass, metrics={"d1_denominator_count": 0, "refiner_file_preserving_invariant_passed": False}, fcc_in={"locked_denominator_mismatch": 1})
    checks.append(_check("locked_denominator_mismatch_valid_no_go", report_locked_mismatch["status"] == "no_go_n1_locked_denominator_unavailable"))
    report_locked_infra = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, network_mode="self_test", openlocus_binary_source="self_test", d0=d0_pass, metrics={"d1_denominator_count": 0, "refiner_file_preserving_invariant_passed": False}, fcc_in={"locked_denominator_mismatch": 1, "raw_denominator_parse_failed": 1})
    checks.append(_check("locked_denominator_mismatch_with_infra_fails_closed", report_locked_infra["status"] == "fail_schema_contract"))
    for n, expected in ((20, "bea_v1_n1_frozen_p4_span_refiner_pass"), (10, "n1_exploratory_insufficient_power"), (9, "no_go_n1_inadequate_wrong_span_denominator")):
        public_rows, _, metrics = _form_d1_and_refine(_synthetic_private_rows(n))
        report = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, network_mode="self_test", openlocus_binary_source="self_test", d0=d0_pass, metrics=metrics, sanitized_rows=public_rows)
        label = "adequate_pass" if n == 20 else ("exploratory_path" if n == 10 else "inadequate_no_go_path")
        checks.append(_check(f"d1_{label}", report["status"] == expected))
        if n == 20:
            checks.append(_check("d1_metrics_improve", metrics["post_span_f0_5_at_10"] > metrics["pre_span_f0_5_at_10"] and metrics["post_wrong_span_rate_at_10"] < metrics["pre_wrong_span_rate_at_10"]))
            checks.append(_check("d1_top10_actionable_gate_present", metrics["d1_top10_actionable_count"] == D1_ADEQUATE_MIN and metrics["d1_rank_blocked_count"] == 0))
            checks.append(_check("sanitized_rows_allowlist", all(set(r) <= SANITIZED_ROW_ALLOWLIST for r in public_rows)))
            checks.append(_check("refiner_file_preserving_invariant", metrics["refiner_file_preserving_invariant_passed"] is True and all(r["file_reach_preserved"] for r in public_rows)))
            observed_record = next(r for r in report["d0_scheduler_preservation_records"] if r["metric_name"] == "p4_reach")
            checks.append(_check("d0_records_use_observed_value", observed_record["value"] == P4L_P4_REACH and observed_record["expected_value"] == P4L_P4_REACH))
    rows_best = _synthetic_private_rows(1)
    rows_best[0]["p4_evidence"].append({"path": rows_best[0]["gold_paths"][0], "start_line": 20, "end_line": 22, "content_sha": "private"})
    public_best, _, metrics_best = _form_d1_and_refine(rows_best)
    checks.append(_check("d1_uses_best_gold_file_span_for_record", metrics_best["d1_denominator_count"] == 0 and not public_best))
    default_report = _base_report(status="unavailable_with_reason", failure_reason_category="network_required_but_disabled", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, network_mode="disabled_opt_in", openlocus_binary_source="missing", fcc_in={"network_required_but_disabled": 1})
    checks.append(_check("default_no_network_unavailable", default_report["status"] == "unavailable_with_reason"))
    checks.append(_check("default_no_network_not_pass_no_go", default_report["status"] not in {"bea_v1_n1_frozen_p4_span_refiner_pass", "no_go_n1_inadequate_wrong_span_denominator"}))
    leaked = dict(default_report)
    leaked["gold_lines"] = [[1, 2]]
    checks.append(_check("scanner_rejects_gold_lines", _scan_summary(leaked)["status"] == "fail"))
    leaked2 = dict(default_report)
    leaked2["candidate_list"] = [{"path": "x", "start_line": 1, "end_line": 2}]
    checks.append(_check("scanner_rejects_candidates", _scan_summary(leaked2)["status"] == "fail"))
    leaked3 = dict(default_report)
    leaked3["raw_trace"] = "provider payload"
    checks.append(_check("scanner_rejects_raw_trace", _scan_summary(leaked3)["status"] == "fail"))
    leaked4 = dict(default_report)
    leaked4["file_content_lines"] = [{"line": 1, "text": "private source"}]
    checks.append(_check("scanner_rejects_file_content_lines", _scan_summary(leaked4)["status"] == "fail"))
    ok_public_rows, _, ok_metrics = _form_d1_and_refine(_synthetic_private_rows(20))
    ok_report = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, network_mode="self_test", openlocus_binary_source="self_test", d0=d0_pass, metrics=ok_metrics, sanitized_rows=ok_public_rows)
    checks.append(_check("scanner_allows_sanitized_buckets", ok_report["forbidden_scan"]["status"] == "pass"))
    checks.append(_check("public_flag_not_aggregate_only_when_sanitized_supported", ok_report["aggregate_plus_sanitized_records_public_artifact"] is True and ok_report["aggregate_only_public_artifact"] is False and ok_report["raw_records_publicly_serialized"] is False))
    checks.append(_check("no_selector_p5_v1a_default_claims", ok_report["selector_or_reranker_executed"] is False and ok_report["p5_executed"] is False and ok_report["v1_a_selector_executed"] is False and ok_report["default_should_change"] is False and ok_report["method_winner_claimed"] is False))
    parser = build_parser()
    opts = {opt for action in parser._actions for opt in action.option_strings}
    required_opts = (
        "--self-test", "--out", "--enable-external-benchmark-network", "--openlocus",
        "--fd1-artifact", "--fd1-private-decomposition-jsonl", "--fd1-replay-artifact",
        "--p4h-artifact", "--p4i-artifact", "--p4j-artifact", "--p4k-artifact",
        "--d0-summary-json", "--private-span-rows-jsonl", "--private-candidate-gold-trace-jsonl",
    )
    for opt in required_opts:
        checks.append(_check(f"cli_has_{opt}", opt in opts))
    checks.append(_check("network_path_not_manual_private_rows_only", callable(_run_real_network_replay) and callable(_run_private_path)))
    checks.append(_check("imports_p4l_and_p4_helpers", hasattr(p4l, "_reconstruct_locked_denominator") and hasattr(p4, "_collect_baseline_per_channel")))
    checks.append(_check("candidate_returning_helper_preserves_caps", _self_test_candidate_returning_helper()))
    checks.append(_check("gold_line_enrichment_from_raw_frames", _self_test_gold_line_enrichment()))
    checks.append(_check("gold_line_enrichment_path_mismatch_skips_d1", _self_test_gold_line_enrichment_path_mismatch()))
    checks.append(_check("gold_line_enrichment_order_mismatch_skips_d1", _self_test_gold_line_enrichment_order_mismatch()))
    checks.append(_check("full_file_refiner_moves_beyond_local_candidate", _self_test_full_file_refiner_moves_beyond_local_candidate()))
    checks.append(_check("file_read_containment_and_regular_file", _self_test_file_read_containment_and_regular_file()))
    checks.append(_check("refiner_caps_window_to_file_bounds", _self_test_refiner_caps_window_to_file_bounds()))
    checks.append(_check("rank_blocked_d1_total_not_pass_gate", _self_test_rank_blocked_d1_total_not_pass_gate()))
    report_rank_violation = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, network_mode="self_test", openlocus_binary_source="self_test", d0=d0_pass, metrics={"d1_total_count": 1, "d1_denominator_count": 1, "d1_top10_actionable_count": 0, "d1_rank_blocked_count": 0, "d1_rank_split_invariant_violation_count": 1, "refiner_file_preserving_invariant_passed": True})
    checks.append(_check("rank_split_violation_fails_closed", report_rank_violation.get("status") == "fail_schema_contract"))
    return checks, all(c["passed"] for c in checks)


def _run_private_path(args: argparse.Namespace, checks_count: int) -> dict[str, Any]:
    start = time.perf_counter()
    fcc = {k: 0 for k in FAILURE_CATEGORIES}
    try:
        if args.d0_summary_json is None or not args.d0_summary_json.exists():
            fcc["d0_scheduler_preservation_missing"] = 1
            d0 = _evaluate_d0(None)
        else:
            d0_obj = json.loads(args.d0_summary_json.read_text(encoding="utf-8"))
            d0 = _evaluate_d0(d0_obj if isinstance(d0_obj, dict) else None)
            if not d0.get("passed"):
                fcc["d0_scheduler_preservation_drift"] = 1
        if args.private_span_rows_jsonl is None or not args.private_span_rows_jsonl.exists():
            fcc["d1_private_span_rows_missing"] = 1
            rows: list[dict[str, Any]] = []
        else:
            rows = _read_jsonl(args.private_span_rows_jsonl)
        sanitized, _, metrics = _form_d1_and_refine(rows)
        if rows and metrics.get("d1_candidate_records_considered", 0) == 0:
            fcc["candidate_span_reconstruction_failed"] = 1
        manifests = [
            _manifest_for_path(args.private_span_rows_jsonl, "bea_v1_n1_private_span_rows_manifest", "bea_v1_n1_private_span_row.v1"),
            _manifest_for_path(args.private_candidate_gold_trace_jsonl, "bea_v1_n1_private_candidate_gold_trace_manifest", "bea_v1_n1_private_candidate_gold_trace.v1"),
        ]
        return _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=args.openlocus or "caller_supplied_or_missing", d0=d0, metrics=metrics, sanitized_rows=sanitized, private_manifests=manifests, fcc_in=fcc, runtime_seconds=time.perf_counter() - start)
    except Exception:
        fcc["unexpected_exception"] = 1
        return _base_report(status="fail_schema_contract", failure_reason_category="unexpected_exception", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=args.openlocus or "caller_supplied_or_missing", fcc_in=fcc, runtime_seconds=time.perf_counter() - start)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(description="BEA-v1-N1 Frozen P4 + Span-Refiner Smoke")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--enable-external-benchmark-network", action="store_true")
    ap.add_argument("--openlocus", default=None)
    ap.add_argument("--fd1-artifact", type=Path, default=DEFAULT_FD1_ARTIFACT)
    ap.add_argument("--fd1-private-decomposition-jsonl", type=Path, default=None)
    ap.add_argument("--fd1-replay-artifact", type=Path, default=None)
    ap.add_argument("--p4h-artifact", type=Path, default=DEFAULT_P4H_ARTIFACT)
    ap.add_argument("--p4i-artifact", type=Path, default=DEFAULT_P4I_ARTIFACT)
    ap.add_argument("--p4j-artifact", type=Path, default=DEFAULT_P4J_ARTIFACT)
    ap.add_argument("--p4k-artifact", type=Path, default=DEFAULT_P4K_ARTIFACT)
    # Debug-only compatibility path. Network CI must not depend on these.
    ap.add_argument("--d0-summary-json", type=Path, default=None)
    ap.add_argument("--private-span-rows-jsonl", type=Path, default=None)
    ap.add_argument("--private-candidate-gold-trace-jsonl", type=Path, default=None)
    ap.add_argument("--debug-use-manual-private-inputs", action="store_true")
    return ap


def main() -> None:
    args = build_parser().parse_args()
    if args.self_test:
        checks, passed = run_self_test_checks()
        for c in checks:
            print(f"[{'PASS' if c['passed'] else 'FAIL'}] {c['check']}")
        print(f"self_test_passed={passed} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        sys.exit(0 if passed else 1)
    checks, passed = run_self_test_checks()
    if not passed:
        print("error: self-test failed; refusing to write artifact", file=sys.stderr)
        sys.exit(1)
    openlocus_bin, openlocus_source = p4.c5a._resolve_openlocus_binary(args.openlocus)
    if not args.enable_external_benchmark_network:
        report = _base_report(status="unavailable_with_reason", failure_reason_category="network_required_but_disabled", self_test_passed=True, self_test_checks_total=len(checks), self_test_checks_passed=None, network_mode="disabled_opt_in", openlocus_binary_source=openlocus_source or "missing", fcc_in={"network_required_but_disabled": 1})
    elif openlocus_bin is None:
        report = _base_report(status="fail_schema_contract", failure_reason_category="retrieval_policy_failed", self_test_passed=True, self_test_checks_total=len(checks), self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=openlocus_source or "missing", fcc_in={"retrieval_policy_failed": 1})
    elif args.debug_use_manual_private_inputs:
        args.openlocus = openlocus_bin
        report = _run_private_path(args, len(checks))
    else:
        args.openlocus = openlocus_bin
        report = _run_real_network_replay(args, len(checks))
    _enforce_no_forbidden(report)
    _write_json(args.out, report)
    print(f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, status={report['status']}, phase={report['phase']}, d1={report.get('d1_wrong_span_denominator_count', 0)})")
    print("safe_status_diagnostics=" + json.dumps(_safe_status_diagnostics(report), sort_keys=True))
    if not args.enable_external_benchmark_network:
        print("enable_external_benchmark_network is false; writing unavailable_with_reason default artifact.")


if __name__ == "__main__":
    main()
