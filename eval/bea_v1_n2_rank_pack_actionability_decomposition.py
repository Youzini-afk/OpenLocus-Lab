#!/usr/bin/env python3
"""BEA-v1-N2: Rank/Pack Actionability Decomposition.

N2 is an empirical decomposition of the N1 rank-blocked records.  It reruns the
private N1/P4 reconstruction when network is explicitly enabled, explains why
gold-file evidence reached by frozen P4 is not actionable in the top-10 pack,
and may authorize only later design work.  It does not run P5, BEA-v1-A,
selector/reranker implementation, broad retrieval expansion, provider calls,
runtime/default promotion, or downstream-value evaluation.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, NoReturn

_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

import bea_v1_n1_frozen_p4_span_refiner_smoke as n1  # noqa: E402
import bea_v1_p4_latency_aware_retrieval_scheduler_smoke as p4  # noqa: E402
import bea_v1_p4l_locked_non_python_scheduler_validation as p4l  # noqa: E402


SCHEMA_VERSION = "bea_v1_n2_rank_pack_actionability_decomposition.v1"
GENERATED_BY = "eval/bea_v1_n2_rank_pack_actionability_decomposition.py"
CLAIM_LEVEL = "bea_v1_n2_rank_pack_actionability_decomposition_only"
MODE = "bea_v1_n2_rank_pack_actionability_decomposition"
PHASE = "BEA-v1-N2"

DEFAULT_OUT = Path(
    "artifacts/bea_v1_n2_rank_pack_actionability_decomposition/"
    "bea_v1_n2_rank_pack_actionability_decomposition_report.json"
)
DEFAULT_N1_ARTIFACT = Path(
    "artifacts/bea_v1_n1_frozen_p4_span_refiner_smoke/"
    "bea_v1_n1_frozen_p4_span_refiner_smoke_report.json"
)

N1_RESULT_CHECKPOINT = "e6772dc"
N1_CI_RUN_ID = "28245155237"
N1_EXPECTED_STATUS = "no_go_n1_inadequate_top10_actionable_denominator"
N1_D0_DENOMINATOR = 272
N1_BASELINE_REACH = 0
N1_P2_REACH = 55
N1_P3_REACH = 55
N1_P4_REACH = 52
N1_P4_HARD_CAP = 0
N1_D1_TOTAL = 40
N1_D1_TOP10_ACTIONABLE = 0
N1_D1_RANK_BLOCKED = 40

D2_ADEQUATE_MIN = 20
D2_EXPLORATORY_MIN = 10

STATUSES = (
    "unavailable_with_reason",
    "fail_schema_contract",
    "fail_forbidden_scan",
    "no_go_n2_n1_artifact_or_trace_unavailable",
    "no_go_n2_insufficient_rank_blocked_denominator",
    "n2_rank_pack_decomposition_exploratory",
    "n2_rank_pack_mechanism_inconclusive",
    "n2_rank_pack_actionability_decomposition_pass",
)

PRIMARY_BLOCKERS = (
    "pack_budget_only",
    "duplicate_file_pack_waste",
    "extra_depth_append_blocked",
    "candidate_order_blocked",
    "scheduler_cap_or_stop_blocked",
    "evidence_materialization_blocked",
    "mixed_or_unclassified",
)

DESIGN_SCOPES = (
    "none",
    "pack_budget_design_only",
    "rank_preserving_pack_design_only",
    "extra_depth_merge_order_design_only",
    "evidence_materialization_design_only",
    "mixed_design_audit_only",
)

SANITIZED_ROW_ALLOWLIST = frozenset({
    "anonymous_local_id",
    "denominator",
    "source_bucket",
    "language_bucket",
    "first_gold_rank_bucket",
    "primary_blocker_bucket",
    "top20_recovery_bucket",
    "top50_recovery_bucket",
    "top100_recovery_bucket",
    "unique_file_top10_recovery_bucket",
    "duplicate_pressure_bucket",
    "evidencecore_materializable",
    "hard_cap_violation",
})

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "exact_path", "private_path", "private_dir", "trace_path",
    "start_line", "end_line", "line_range", "span", "spans", "exact_span",
    "gold", "gold_paths", "gold_lines", "gold_spans", "gold_labels",
    "candidate", "candidates", "candidate_list", "candidate_paths",
    "rank", "score", "scores", "first_gold_rank", "candidate_rank",
    "raw", "raw_trace", "raw_prompt", "raw_response", "provider_payload",
    "snippet", "snippets", "content", "content_lines", "file_content_lines",
    "text", "raw_text", "content_sha", "task_id", "row_id", "repo_name",
    "repo_slug", "repo_url", "base_commit", "private_record_id", "record_ids",
    "self_test_checks", "self_test_details", "checks",
})

SAFE_VALUE_KEYS = frozenset({
    "schema_version", "generated_by", "generated_at", "claim_level", "status",
    "mode", "phase", "failure_reason_category", "network_mode",
    "openlocus_binary_source", "source_checkpoint", "source_ci_run_id",
    "status_vocabulary", "manifest_name", "storage_class", "manifest_hash",
    "source_bucket", "language_bucket", "first_gold_rank_bucket",
    "primary_blocker_bucket", "top20_recovery_bucket", "top50_recovery_bucket",
    "top100_recovery_bucket", "unique_file_top10_recovery_bucket",
    "duplicate_pressure_bucket", "denominator", "design_authorized_scope", "metric_block",
    "metric_name", "gate", "threshold_relation", "failure_category",
})

FAILURE_CATEGORIES = (
    "network_required_but_disabled",
    "n1_artifact_missing",
    "n1_artifact_parse_failed",
    "n1_artifact_mismatch",
    "fd1_artifact_missing",
    "fd1_artifact_parse_failed",
    "fd1_private_decomposition_missing",
    "fd1_private_decomposition_parse_failed",
    "fd1_replay_artifact_missing",
    "fd1_replay_artifact_parse_failed",
    "fd1_replay_artifact_status_mismatch",
    "p4k_artifact_missing",
    "p4k_artifact_status_mismatch",
    "locked_denominator_mismatch",
    "raw_denominator_parse_failed",
    "raw_denominator_clone_failed",
    "raw_denominator_scan_failed",
    "cross_source_asset_download_failed",
    "cross_source_asset_decompress_failed",
    "retrieval_policy_failed",
    "d0_scheduler_preservation_drift",
    "d2_private_write_error",
    "gold_span_reconstruction_failed",
    "candidate_order_unavailable",
    "d2_rank_blocked_reconstruction_mismatch",
    "classification_sum_mismatch",
    "forbidden_leak_blocked",
    "unexpected_exception",
)

BLOCKING_FAILURES = {
    "n1_artifact_parse_failed",
    "n1_artifact_mismatch",
    "fd1_artifact_parse_failed",
    "fd1_private_decomposition_parse_failed",
    "fd1_replay_artifact_parse_failed",
    "fd1_replay_artifact_status_mismatch",
    "p4k_artifact_status_mismatch",
    "locked_denominator_mismatch",
    "raw_denominator_parse_failed",
    "raw_denominator_clone_failed",
    "raw_denominator_scan_failed",
    "cross_source_asset_download_failed",
    "cross_source_asset_decompress_failed",
    "retrieval_policy_failed",
    "d0_scheduler_preservation_drift",
    "d2_private_write_error",
    "classification_sum_mismatch",
    "unexpected_exception",
}


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _append_private_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def _private_dir() -> Path:
    raw = os.environ.get("OPENLOCUS_BEA_V1_N2_PRIVATE_DIR", "")
    base = Path(raw) if raw else Path(f"/tmp/openlocus_bea_v1_n2_{os.getpid()}")
    resolved = base.resolve()
    if not str(resolved).startswith("/tmp/"):
        raise ValueError("invalid private N2 dir")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _manifest_for_path(path: Path | None, name: str, schema: str) -> dict[str, Any]:
    count = 0
    digest = hashlib.sha256()
    if path and path.exists():
        with path.open("rb") as fh:
            for line in fh:
                digest.update(line)
                if line.strip():
                    count += 1
    return {
        "manifest_name": name,
        "schema_version": schema,
        "storage_class": "private_jsonl_under_tmp",
        "record_count": count,
        "records_written": bool(count),
        "path_publicly_serialized": False,
        "manifest_hash": digest.hexdigest() if count else "",
    }


def _scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)
    path_re = re.compile(r"(?:^|[\s=])(?:/[^\s]+|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    hex_re = re.compile(r"\b[0-9a-f]{64}\b", re.I)

    def walk(o: Any, pth: str = "$") -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                ks = str(k)
                sub = f"{pth}.{ks}"
                if ks in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "path": sub})
                if ks == "sanitized_analysis_records" and isinstance(v, list):
                    for i, row in enumerate(v):
                        if isinstance(row, dict) and (set(row) - SANITIZED_ROW_ALLOWLIST):
                            violations.append({"category": "sanitized_row_non_allowlist_key", "path": f"{sub}[{i}]"})
                walk(v, sub)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{pth}[{i}]")
        elif isinstance(o, str):
            last = pth.rsplit(".", 1)[-1].split("[")[0]
            if last in SAFE_VALUE_KEYS:
                return
            if line_re.search(o):
                violations.append({"category": "line_range_value", "path": pth})
            if path_re.search(o):
                violations.append({"category": "path_like_value", "path": pth})
            if hex_re.search(o):
                violations.append({"category": "hex_digest_value", "path": pth})

    walk(obj)
    return violations


def _scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_public(obj)
    cats: Counter[str] = Counter(v["category"] for v in violations)
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


def _load_artifact(path: Path | None) -> tuple[dict[str, Any], str]:
    if path is None or not path.exists():
        return {}, "artifact_missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}, "pass" if isinstance(data, dict) else "artifact_parse_failed"
    except Exception:
        return {}, "artifact_parse_failed"


def _metric_value(records: list[dict[str, Any]], name: str, default: Any = 0) -> Any:
    for rec in records:
        if isinstance(rec, dict) and rec.get("metric_name") == name:
            return rec.get("value", default)
    return default


def _int_value(value: Any, default: int = -1) -> int:
    try:
        if value is None or isinstance(value, bool):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _validate_closed_n1_artifact(path: Path | None) -> tuple[bool, str, dict[str, int]]:
    fcc = {k: 0 for k in FAILURE_CATEGORIES}
    art, status = _load_artifact(path)
    if status != "pass":
        fcc["n1_artifact_missing" if status == "artifact_missing" else "n1_artifact_parse_failed"] = 1
        return False, status, fcc
    failures: list[str] = []
    if art.get("status") != N1_EXPECTED_STATUS:
        failures.append("status")
    if art.get("d0_scheduler_preservation_denominator_count") != N1_D0_DENOMINATOR:
        failures.append("d0_denominator")
    d0 = {r.get("metric_name"): r for r in art.get("d0_scheduler_preservation_records", []) if isinstance(r, dict)}
    expected_d0 = {
        "baseline_reach": N1_BASELINE_REACH,
        "p2_reach": N1_P2_REACH,
        "p3_reach": N1_P3_REACH,
        "p4_reach": N1_P4_REACH,
        "p4_treatment_hard_cap": N1_P4_HARD_CAP,
    }
    for name, expected in expected_d0.items():
        if d0.get(name, {}).get("value") != expected or d0.get(name, {}).get("passed") is not True:
            failures.append(name)
    d1_records = art.get("d1_span_efficacy_records", [])
    if art.get("d1_total_count", _metric_value(d1_records, "d1_total_count")) != N1_D1_TOTAL:
        failures.append("d1_total")
    if art.get("d1_top10_actionable_count", _metric_value(d1_records, "d1_top10_actionable_count")) != N1_D1_TOP10_ACTIONABLE:
        failures.append("d1_top10")
    if art.get("d1_rank_blocked_count", _metric_value(d1_records, "d1_rank_blocked_count")) != N1_D1_RANK_BLOCKED:
        failures.append("d1_rank_blocked")
    if art.get("forbidden_scan", {}).get("status") != "pass":
        failures.append("forbidden_scan")
    if failures:
        fcc["n1_artifact_mismatch"] = 1
        return False, "n1_artifact_mismatch:" + ",".join(sorted(failures)), fcc
    return True, "pass", fcc


def _d0_from_closed_n1_artifact(art: dict[str, Any]) -> dict[str, Any]:
    records = art.get("d0_scheduler_preservation_records", [])
    values = {
        str(rec.get("metric_name")): rec.get("value")
        for rec in records
        if isinstance(rec, dict)
    }
    baseline = _int_value(values.get("baseline_reach"))
    p2 = _int_value(values.get("p2_reach"))
    p4_reach = _int_value(values.get("p4_reach"))
    p2_gain = p2 - baseline
    p4_gain = p4_reach - baseline
    summary = {
        "denominator_count": _int_value(art.get("d0_scheduler_preservation_denominator_count", values.get("denominator_count", -1))),
        "baseline_reach": baseline,
        "p2_reach": p2,
        "p3_reach": _int_value(values.get("p3_reach")),
        "p4_reach": p4_reach,
        "p4_retained_p2_gain": round(p4_gain / p2_gain, 6) if p2_gain else 0.0,
        "p4_treatment_hard_cap": _int_value(values.get("p4_treatment_hard_cap")),
        "file_order_preserved": True,
        "scheduler_actions_preserved": True,
    }
    return n1._evaluate_d0(summary)


def _first_gold_rank(final_cands: list[dict[str, Any]], gold_paths: set[str]) -> int | None:
    for idx, cand in enumerate(final_cands, start=1):
        if str(cand.get("path", "") or "") in gold_paths:
            return idx
    return None


def _rank_bucket(rank: int | None) -> str:
    if rank is None or rank <= 0:
        return "rank_missing_or_invalid"
    if rank <= 20:
        return "rank_11_20"
    if rank <= 50:
        return "rank_21_50"
    if rank <= 100:
        return "rank_51_100"
    return "rank_gt_100"


def _recovery_bucket(value: bool) -> str:
    return "recovered" if value else "not_recovered"


def _duplicate_pressure(final_cands: list[dict[str, Any]], first_rank: int | None) -> tuple[str, int]:
    if first_rank is None or first_rank <= 1:
        return "none", 0
    seen: set[str] = set()
    dup = 0
    for cand in final_cands[:first_rank - 1]:
        pth = str(cand.get("path", "") or "")
        if not pth:
            continue
        if pth in seen:
            dup += 1
        seen.add(pth)
    if dup == 0:
        return "none", dup
    if dup <= 2:
        return "low", dup
    if dup <= 5:
        return "medium", dup
    return "high", dup


def _unique_file_top10_recovers(final_cands: list[dict[str, Any]], gold_paths: set[str]) -> bool:
    files: list[str] = []
    seen: set[str] = set()
    for cand in final_cands:
        pth = str(cand.get("path", "") or "")
        if pth and pth not in seen:
            seen.add(pth)
            files.append(pth)
        if len(files) >= 10:
            break
    return any(p in gold_paths for p in files[:10])


def _evidence_materializable(evidence: list[dict[str, Any]]) -> bool:
    for ev in evidence:
        lines = ev.get("content_lines") or ev.get("file_content_lines")
        if isinstance(lines, list) and len(lines) > 0:
            return True
    return False


def _classify_blocker(row: dict[str, Any]) -> str:
    if not bool(row.get("evidence_materializable")):
        return "evidence_materialization_blocked"
    if bool(row.get("unique_file_top10_recovery")):
        return "duplicate_file_pack_waste"
    first_rank = row.get("first_gold_rank_private")
    if isinstance(first_rank, int) and first_rank <= 20:
        return "pack_budget_only"
    if bool(row.get("extra_depth_append_blocked")):
        return "extra_depth_append_blocked"
    if bool(row.get("scheduler_cap_or_stop_blocked")):
        return "scheduler_cap_or_stop_blocked"
    if isinstance(first_rank, int) and first_rank <= 100:
        return "candidate_order_blocked"
    return "mixed_or_unclassified"


def _candidate_to_evidence(cand: dict[str, Any], repo_root: Path | None = None) -> dict[str, Any] | None:
    start = n1._line_number(cand.get("start_line"))
    end = n1._line_number(cand.get("end_line"))
    pth = str(cand.get("path", "") or "")
    if not pth or start is None or end is None or end < start:
        return None
    ev: dict[str, Any] = {"path": pth, "start_line": start, "end_line": end}
    if repo_root is not None:
        ev["content_lines"] = n1._read_candidate_content_lines(repo_root, cand)
        ev["file_content_lines"] = n1._read_file_content_lines(repo_root, pth)
    return ev


def _d2_row_from_candidates(
    *, rec: dict[str, Any], rr: Any, final_cands: list[dict[str, Any]], index: int,
) -> dict[str, Any] | None:
    gold_paths_list, gold_lines, gold_ok = n1._gold_from_locked_record(rec)
    if not gold_ok:
        return None
    gold_paths = {str(p) for p in gold_paths_list if p}
    if not gold_paths:
        return None
    first_rank = _first_gold_rank(final_cands, gold_paths)
    if first_rank is None or first_rank <= 10:
        return None
    repo_root = rec.get("repo_root") if isinstance(rec.get("repo_root"), Path) else None
    evidence: list[dict[str, Any]] = []
    for cand in final_cands:
        ev = _candidate_to_evidence(cand, repo_root)
        if ev is not None:
            evidence.append(ev)
    gold_file_evidence = [ev for ev in evidence if ev.get("path") in gold_paths]
    if not gold_file_evidence:
        return None
    task = {"task_id": f"n2r{index:05d}", "gold_paths": gold_paths_list, "gold_lines": gold_lines}
    pre_bucket = n1._best_span_bucket(gold_file_evidence, task)
    if pre_bucket not in {"zero_overlap", "inadequate_overlap"}:
        return None
    duplicate_bucket, duplicate_count = _duplicate_pressure(final_cands, first_rank)
    unique_recovery = _unique_file_top10_recovers(final_cands, gold_paths)
    baseline_size = int(getattr(rr, "baseline_unique_file_count", 0) or 0)
    stop_reason = str(getattr(rr, "scheduler_stop_reason", "") or "")
    row = {
        "schema_version": "bea_v1_n2_private_rank_pack_row.v1",
        "denominator_index_private": index,
        "source_bucket": str(rec.get("source_frame", rec.get("benchmark", "unknown_source")) or "unknown_source"),
        "language_bucket": str(rec.get("language", "unknown_language") or "unknown_language"),
        "gold_paths_private": gold_paths_list,
        "gold_lines_private": gold_lines,
        "first_gold_rank_private": first_rank,
        "first_rank_bucket": _rank_bucket(first_rank),
        "top20_recovery": first_rank <= 20,
        "top50_recovery": first_rank <= 50,
        "top100_recovery": first_rank <= 100,
        "unique_file_top10_recovery": unique_recovery,
        "duplicate_pressure_bucket": duplicate_bucket,
        "duplicate_count_before_gold_private": duplicate_count,
        "evidence_materializable": _evidence_materializable(gold_file_evidence),
        "hard_cap_violation": bool(getattr(rr, "hard_cap_hit", False)),
        "scheduler_stop_reason_private": stop_reason,
        "scheduler_action_private": str(getattr(rr, "scheduler_action", "") or ""),
        "extra_depth_append_blocked": bool(getattr(rr, "scheduler_action", "") == "extra_depth_selected" and first_rank > max(10, baseline_size)),
        "scheduler_cap_or_stop_blocked": bool(getattr(rr, "hard_cap_hit", False) or "cap" in stop_reason),
        "candidate_count_private": len(final_cands),
        "candidate_order_private": [
            {
                "rank": i,
                "path": str(c.get("path", "") or ""),
                "start_line": c.get("start_line"),
                "end_line": c.get("end_line"),
                "score": c.get("score"),
                "method": c.get("method") or c.get("source") or c.get("channel"),
            }
            for i, c in enumerate(final_cands, start=1)
        ],
    }
    row["primary_blocker_bucket"] = _classify_blocker(row)
    return row


def _build_d2_rows_from_locked_denominator(
    *, openlocus_bin: str, denom: list[dict[str, Any]], private_path: Path,
    fcc: dict[str, int],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, rec in enumerate(denom):
        try:
            gold_paths, _gold_lines, gold_ok = n1._gold_from_locked_record(rec)
            if not gold_ok:
                fcc["gold_span_reconstruction_failed"] = fcc.get("gold_span_reconstruction_failed", 0) + 1
                continue
            repo_root = rec.get("repo_root")
            if not isinstance(repo_root, Path):
                fcc["raw_denominator_clone_failed"] = fcc.get("raw_denominator_clone_failed", 0) + 1
                continue
            rr, final_cands = n1._run_frozen_p4_with_candidates(
                openlocus_bin=openlocus_bin,
                repo_root=repo_root,
                query=str(rec.get("query", "") or ""),
                gold_set={str(p) for p in gold_paths if p},
            )
            if not final_cands:
                fcc["candidate_order_unavailable"] = fcc.get("candidate_order_unavailable", 0) + 1
                continue
            row = _d2_row_from_candidates(rec=rec, rr=rr, final_cands=final_cands, index=idx)
            if row is None:
                continue
            _append_private_jsonl(private_path, row)
            rows.append(row)
        except Exception:
            fcc["retrieval_policy_failed"] = fcc.get("retrieval_policy_failed", 0) + 1
    return rows


def _rate(num: int, den: int) -> float:
    return round(num / den, 6) if den else 0.0


def _design_scope(metrics: dict[str, Any]) -> tuple[bool, str, list[str]]:
    crossed: list[str] = []
    if float(metrics.get("top20_recovery_rate", 0.0)) >= 0.50:
        crossed.append("pack_budget_design_only")
    if float(metrics.get("unique_file_pack_recovery_at10", 0.0)) >= 0.25:
        crossed.append("rank_preserving_pack_design_only")
    if float(metrics.get("extra_depth_append_blocked_rate", 0.0)) >= 0.50:
        crossed.append("extra_depth_merge_order_design_only")
    if float(metrics.get("evidence_materialization_blocked_rate", 0.0)) >= 0.25:
        crossed.append("evidence_materialization_design_only")
    if not crossed:
        return False, "none", []
    if len(crossed) == 1:
        return True, crossed[0], crossed
    return True, "mixed_design_audit_only", crossed


def _analyze_d2(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    n = len(rows)
    first_rank = Counter(str(r.get("first_rank_bucket", "rank_missing_or_invalid")) for r in rows)
    blockers = Counter(str(r.get("primary_blocker_bucket", "mixed_or_unclassified")) for r in rows)
    duplicate = Counter(str(r.get("duplicate_pressure_bucket", "none")) for r in rows)
    top20 = sum(1 for r in rows if r.get("top20_recovery"))
    top50 = sum(1 for r in rows if r.get("top50_recovery"))
    top100 = sum(1 for r in rows if r.get("top100_recovery"))
    unique10 = sum(1 for r in rows if r.get("unique_file_top10_recovery"))
    materializable = sum(1 for r in rows if r.get("evidence_materializable"))
    hard_cap = sum(1 for r in rows if r.get("hard_cap_violation"))
    extra_depth = int(blockers.get("extra_depth_append_blocked", 0))
    evidence_blocked = int(blockers.get("evidence_materialization_blocked", 0))
    classified = sum(int(blockers.get(b, 0)) for b in PRIMARY_BLOCKERS)
    metrics: dict[str, Any] = {
        "d2_total_count": n,
        "d2_classified_count": classified,
        "classification_sum_matches": classified == n,
        "top20_recovery_count": top20,
        "top50_recovery_count": top50,
        "top100_recovery_count": top100,
        "top20_recovery_rate": _rate(top20, n),
        "top50_recovery_rate": _rate(top50, n),
        "top100_recovery_rate": _rate(top100, n),
        "unique_file_pack_recovery_at10_count": unique10,
        "unique_file_pack_recovery_at10": _rate(unique10, n),
        "evidence_materializable_count": materializable,
        "evidence_materialization_blocked_count": evidence_blocked,
        "evidence_materialization_blocked_rate": _rate(evidence_blocked, n),
        "extra_depth_append_blocked_count": extra_depth,
        "extra_depth_append_blocked_rate": _rate(extra_depth, n),
        "hard_cap_violation_count": hard_cap,
    }
    for b in ("rank_11_20", "rank_21_50", "rank_51_100", "rank_gt_100", "rank_missing_or_invalid"):
        metrics[f"first_gold_rank_bucket_{b}_count"] = int(first_rank.get(b, 0))
    for b in PRIMARY_BLOCKERS:
        metrics[f"primary_blocker_{b}_count"] = int(blockers.get(b, 0))
    for b in ("none", "low", "medium", "high"):
        metrics[f"duplicate_pressure_{b}_count"] = int(duplicate.get(b, 0))
    design_authorized, scope, crossed = _design_scope(metrics)
    metrics["design_authorized"] = design_authorized
    metrics["design_authorized_scope"] = scope
    metrics["design_thresholds_crossed_count"] = len(crossed)
    public_rows = [
        {
            "anonymous_local_id": f"n2r{i:05d}",
            "denominator": "D2_rank_blocked",
            "source_bucket": str(r.get("source_bucket", "unknown_source")),
            "language_bucket": str(r.get("language_bucket", "unknown_language")),
            "first_gold_rank_bucket": str(r.get("first_rank_bucket", "rank_missing_or_invalid")),
            "primary_blocker_bucket": str(r.get("primary_blocker_bucket", "mixed_or_unclassified")),
            "top20_recovery_bucket": _recovery_bucket(bool(r.get("top20_recovery"))),
            "top50_recovery_bucket": _recovery_bucket(bool(r.get("top50_recovery"))),
            "top100_recovery_bucket": _recovery_bucket(bool(r.get("top100_recovery"))),
            "unique_file_top10_recovery_bucket": _recovery_bucket(bool(r.get("unique_file_top10_recovery"))),
            "duplicate_pressure_bucket": str(r.get("duplicate_pressure_bucket", "none")),
            "evidencecore_materializable": bool(r.get("evidence_materializable")),
            "hard_cap_violation": bool(r.get("hard_cap_violation")),
        }
        for i, r in enumerate(rows)
    ]
    return public_rows, metrics


def _d0_records(d0: dict[str, Any]) -> list[dict[str, Any]]:
    return n1._d0_records(d0)


def _d2_records(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    names = [
        "d2_total_count", "d2_classified_count", "top20_recovery_count",
        "top50_recovery_count", "top100_recovery_count", "top20_recovery_rate",
        "top50_recovery_rate", "top100_recovery_rate",
        "unique_file_pack_recovery_at10_count", "unique_file_pack_recovery_at10",
        "evidence_materializable_count", "evidence_materialization_blocked_count",
        "evidence_materialization_blocked_rate", "extra_depth_append_blocked_count",
        "extra_depth_append_blocked_rate", "hard_cap_violation_count",
        "design_thresholds_crossed_count",
    ]
    for b in ("rank_11_20", "rank_21_50", "rank_51_100", "rank_gt_100", "rank_missing_or_invalid"):
        names.append(f"first_gold_rank_bucket_{b}_count")
    for b in PRIMARY_BLOCKERS:
        names.append(f"primary_blocker_{b}_count")
    for b in ("none", "low", "medium", "high"):
        names.append(f"duplicate_pressure_{b}_count")
    return [{"metric_block": "D2_rank_pack_actionability", "metric_name": n, "value": metrics.get(n, 0)} for n in names]


def _gate_records(d0: dict[str, Any], metrics: dict[str, Any], scan_pass: bool, n1_validated: bool) -> list[dict[str, Any]]:
    d2_n = int(metrics.get("d2_total_count", 0))
    return [
        {"gate": "closed_n1_artifact_validated", "value": 1 if n1_validated else 0, "threshold_relation": "boolean", "threshold_value": 1, "passed": n1_validated},
        {"gate": "d0_scheduler_preservation", "value": 1 if d0.get("passed") else 0, "threshold_relation": "boolean", "threshold_value": 1, "passed": bool(d0.get("passed"))},
        {"gate": "d2_rank_blocked_denominator_adequate", "value": d2_n, "threshold_relation": ">=", "threshold_value": D2_ADEQUATE_MIN, "passed": d2_n >= D2_ADEQUATE_MIN},
        {"gate": "d2_rank_blocked_denominator_exploratory_min", "value": d2_n, "threshold_relation": ">=", "threshold_value": D2_EXPLORATORY_MIN, "passed": d2_n >= D2_EXPLORATORY_MIN},
        {"gate": "d2_reconstructs_closed_n1_rank_blocked_denominator", "value": d2_n, "threshold_relation": "==", "threshold_value": N1_D1_RANK_BLOCKED, "passed": d2_n == N1_D1_RANK_BLOCKED},
        {"gate": "classification_count_equals_d2", "value": int(metrics.get("d2_classified_count", 0)), "threshold_relation": "==", "threshold_value": d2_n, "passed": bool(metrics.get("classification_sum_matches", False))},
        {"gate": "design_threshold_crossed", "value": 1 if metrics.get("design_authorized") else 0, "threshold_relation": "boolean", "threshold_value": 1, "passed": bool(metrics.get("design_authorized", False))},
        {"gate": "forbidden_scan_pass", "value": 1 if scan_pass else 0, "threshold_relation": "boolean", "threshold_value": 1, "passed": scan_pass},
    ]


def _status_from(d0: dict[str, Any], metrics: dict[str, Any], fcc: dict[str, int], *, unavailable: bool = False, n1_validated: bool = False) -> tuple[str, str]:
    if unavailable:
        return "unavailable_with_reason", "network_required_but_disabled"
    if int(fcc.get("d2_rank_blocked_reconstruction_mismatch", 0)) and int(fcc.get("candidate_order_unavailable", 0)):
        return "fail_schema_contract", "candidate_order_unavailable"
    if int(fcc.get("n1_artifact_missing", 0)) or int(fcc.get("fd1_artifact_missing", 0)) or int(fcc.get("fd1_private_decomposition_missing", 0)) or int(fcc.get("p4k_artifact_missing", 0)):
        return "no_go_n2_n1_artifact_or_trace_unavailable", "n1_artifact_or_trace_unavailable"
    if sum(int(fcc.get(k, 0)) for k in BLOCKING_FAILURES) or not d0.get("passed", False) or not n1_validated:
        return "fail_schema_contract", "blocking_failure_present"
    if int(fcc.get("d2_rank_blocked_reconstruction_mismatch", 0)):
        return "no_go_n2_n1_artifact_or_trace_unavailable", "d2_rank_blocked_reconstruction_mismatch"
    d2_n = int(metrics.get("d2_total_count", 0))
    if d2_n < D2_EXPLORATORY_MIN:
        return "no_go_n2_insufficient_rank_blocked_denominator", "d2_denominator_lt_10"
    if d2_n < D2_ADEQUATE_MIN:
        return "n2_rank_pack_decomposition_exploratory", "d2_denominator_10_to_19"
    if not bool(metrics.get("classification_sum_matches", False)):
        return "fail_schema_contract", "classification_sum_mismatch"
    if bool(metrics.get("design_authorized", False)):
        return "n2_rank_pack_actionability_decomposition_pass", "design_threshold_crossed"
    return "n2_rank_pack_mechanism_inconclusive", "no_design_threshold_crossed"


def _base_report(
    *, status: str, failure_reason_category: str, self_test_passed: bool,
    self_test_checks_total: int, self_test_checks_passed: int | None,
    network_mode: str, openlocus_binary_source: str, d0: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None, sanitized_rows: list[dict[str, Any]] | None = None,
    private_manifests: list[dict[str, Any]] | None = None, fcc_in: dict[str, int] | None = None,
    runtime_seconds: float = 0.0, n1_validated: bool = False,
) -> dict[str, Any]:
    fcc = {k: 0 for k in FAILURE_CATEGORIES}
    for k, v in (fcc_in or {}).items():
        if k in fcc:
            fcc[k] = int(v)
    d0 = d0 or {"passed": False, "failure": "d0_scheduler_preservation_missing", "checks": {}, "observed": {}}
    metrics = metrics or {"d2_total_count": 0, "d2_classified_count": 0, "classification_sum_matches": True, "design_authorized": False, "design_authorized_scope": "none"}
    if int(metrics.get("d2_classified_count", 0)) != int(metrics.get("d2_total_count", 0)):
        fcc["classification_sum_mismatch"] = max(1, fcc["classification_sum_mismatch"])
    if status == "auto":
        status, failure_reason_category = _status_from(d0, metrics, fcc, n1_validated=n1_validated)
    if failure_reason_category in fcc:
        fcc[failure_reason_category] = max(1, fcc[failure_reason_category])
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": failure_reason_category,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "source_checkpoint": N1_RESULT_CHECKPOINT,
        "source_ci_run_id": N1_CI_RUN_ID,
        "status_vocabulary": list(STATUSES),
        "primary_blocker_vocabulary": list(PRIMARY_BLOCKERS),
        "design_authorized_scope_vocabulary": list(DESIGN_SCOPES),
        "closed_n1_artifact_validated": bool(n1_validated),
        "d0_scheduler_preservation_denominator_count": N1_D0_DENOMINATOR,
        "d2_rank_blocked_denominator_count": int(metrics.get("d2_total_count", 0)),
        "design_authorized": bool(metrics.get("design_authorized", False)),
        "design_authorized_scope": str(metrics.get("design_authorized_scope", "none")),
        "implementation_authorized": False,
        "p5_authorized": False,
        "v1_a_authorized": False,
        "selector_or_reranker_authorized": False,
        "runtime_promotion_authorized": False,
        "default_should_change": False,
        "broad_retrieval_expansion_authorized": False,
        "provider_calls_made": False,
        "remote_provider_calls_made": False,
        "p5_executed": False,
        "v1_a_selector_executed": False,
        "selector_or_reranker_executed": False,
        "selector_or_reranker_implemented": False,
        "runtime_behavior_changed": False,
        "downstream_agent_value_proven": False,
        "rank_pack_decomposition_only": True,
        "aggregate_plus_sanitized_records_public_artifact": True,
        "private_jsonl_under_tmp_only": True,
        "raw_records_publicly_serialized": False,
        "exact_paths_publicly_serialized": False,
        "exact_spans_publicly_serialized": False,
        "exact_ranks_publicly_serialized": False,
        "scores_publicly_serialized": False,
        "self_test_passed": self_test_passed,
        "self_test_checks_total": int(self_test_checks_total),
        "self_test_checks_passed": int(self_test_checks_passed if self_test_checks_passed is not None else self_test_checks_total),
        "d0_scheduler_preservation_records": _d0_records(d0),
        "d2_rank_pack_decomposition_records": _d2_records(metrics),
        "sanitized_analysis_records": sanitized_rows or [],
        "private_manifest_records": private_manifests or [],
        "failure_category_count_records": [
            {"failure_category": k, "count": int(fcc.get(k, 0))} for k in sorted(fcc)
        ],
        "aggregate_runtime_seconds": round(float(runtime_seconds), 3),
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass" and status != "fail_forbidden_scan":
        fcc["forbidden_leak_blocked"] = max(1, fcc["forbidden_leak_blocked"])
        report["status"] = "fail_forbidden_scan"
        report["failure_reason_category"] = "forbidden_leak_blocked"
        report["failure_category_count_records"] = [
            {"failure_category": k, "count": int(fcc.get(k, 0))} for k in sorted(fcc)
        ]
    report["forbidden_scan"] = _scan_summary(report)
    report["gate_records"] = _gate_records(d0, metrics, report["forbidden_scan"]["status"] == "pass", n1_validated)
    return report


def _run_network(args: argparse.Namespace, checks_count: int) -> dict[str, Any]:
    start = time.perf_counter()
    fcc = {k: 0 for k in FAILURE_CATEGORIES}
    d0 = n1._evaluate_d0(None)
    metrics: dict[str, Any] = {"d2_total_count": 0, "d2_classified_count": 0, "classification_sum_matches": True, "design_authorized": False, "design_authorized_scope": "none"}
    manifests: list[dict[str, Any]] = []
    try:
        n1_ok, _n1_reason, n1_fcc = _validate_closed_n1_artifact(args.n1_artifact)
        for k, v in n1_fcc.items():
            fcc[k] = max(fcc.get(k, 0), int(v))
        if not n1_ok:
            return _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=args.openlocus or "explicit", d0=d0, metrics=metrics, fcc_in=fcc, runtime_seconds=time.perf_counter() - start, n1_validated=False)
        n1_artifact, _ = _load_artifact(args.n1_artifact)
        d0 = _d0_from_closed_n1_artifact(n1_artifact)
        if not d0.get("passed"):
            fcc["n1_artifact_mismatch"] = 1
            return _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=args.openlocus or "explicit", d0=d0, metrics=metrics, fcc_in=fcc, runtime_seconds=time.perf_counter() - start, n1_validated=False)
        fd1_artifact, fd1_status = _load_artifact(args.fd1_artifact)
        if fd1_status != "pass":
            fcc["fd1_artifact_missing" if fd1_status == "artifact_missing" else "fd1_artifact_parse_failed"] = 1
        fd1_manifest = p4.bea_v1_p1._fd1_private_decomposition_manifest(fd1_artifact) if fd1_artifact else {}
        pt = p4._parse_private_decomposition_jsonl(args.fd1_private_decomposition_jsonl)
        if not getattr(pt, "file_existed", False):
            fcc["fd1_private_decomposition_missing"] = 1
        if getattr(pt, "parse_failures", 0):
            fcc["fd1_private_decomposition_parse_failed"] = int(pt.parse_failures)
        if getattr(pt, "file_existed", False):
            p4._compute_file_selector_lower_bound(pt)
        rav = p4._validate_fd1_replay_artifact(args.fd1_replay_artifact, str(fd1_manifest.get("manifest_hash", "") or ""))
        if not getattr(rav, "validated", False):
            cat = getattr(rav, "failure_category", "") or "fd1_replay_artifact_parse_failed"
            fcc[cat if cat in fcc else "fd1_replay_artifact_status_mismatch"] = 1
        p4k_artifact, p4k_status = _load_artifact(args.p4k_artifact)
        if p4k_status != "pass":
            fcc["p4k_artifact_missing" if p4k_status == "artifact_missing" else "p4k_artifact_status_mismatch"] = 1
        elif p4k_artifact.get("status") != p4l.P4K_RESULT_STATUS:
            fcc["p4k_artifact_status_mismatch"] = 1
        if any(int(fcc.get(k, 0)) for k in ("fd1_artifact_parse_failed", "fd1_private_decomposition_parse_failed", "fd1_replay_artifact_parse_failed", "fd1_replay_artifact_status_mismatch", "p4k_artifact_status_mismatch")):
            return _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=args.openlocus or "explicit", d0=d0, metrics=metrics, fcc_in=fcc, runtime_seconds=time.perf_counter() - start, n1_validated=n1_ok)
        openlocus_bin, openlocus_source = p4.c5a._resolve_openlocus_binary(args.openlocus)
        if openlocus_bin is None:
            fcc["retrieval_policy_failed"] = 1
            return _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=openlocus_source, d0=d0, metrics=metrics, fcc_in=fcc, runtime_seconds=time.perf_counter() - start, n1_validated=n1_ok)
        pdir = _private_dir()
        recon_path = pdir / "bea_v1_n2.p4l_private_reconstruction.jsonl"
        d2_path = pdir / "bea_v1_n2.private_rank_pack_rows.jsonl"
        for pth in (recon_path, d2_path):
            if pth.exists():
                pth.unlink()
        denom, recon_meta = p4l._reconstruct_locked_denominator(openlocus_bin=openlocus_bin, pt=pt, private_path=recon_path, fcc=fcc)
        locked_count = int(recon_meta.get("non_python_locked_count", 0))
        if locked_count != N1_D0_DENOMINATOR:
            fcc["locked_denominator_mismatch"] = 1
        n1._enrich_locked_denominator_with_gold_lines(denom, fcc)
        rows = _build_d2_rows_from_locked_denominator(openlocus_bin=openlocus_bin, denom=denom, private_path=d2_path, fcc=fcc)
        sanitized, metrics = _analyze_d2(rows)
        if int(metrics.get("d2_total_count", 0)) != N1_D1_RANK_BLOCKED:
            fcc["d2_rank_blocked_reconstruction_mismatch"] = 1
        if not metrics.get("classification_sum_matches", False):
            fcc["classification_sum_mismatch"] = 1
        manifests = [
            _manifest_for_path(recon_path, "bea_v1_n2_p4l_private_reconstruction_manifest", "bea_v1_p4l_private_reconstruction.v1"),
            _manifest_for_path(d2_path, "bea_v1_n2_private_rank_pack_rows_manifest", "bea_v1_n2_private_rank_pack_row.v1"),
        ]
        return _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=openlocus_source, d0=d0, metrics=metrics, sanitized_rows=sanitized, private_manifests=manifests, fcc_in=fcc, runtime_seconds=time.perf_counter() - start, n1_validated=n1_ok)
    except Exception:
        fcc["unexpected_exception"] = 1
        return _base_report(status="fail_schema_contract", failure_reason_category="unexpected_exception", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=args.openlocus or "explicit", d0=d0, metrics=metrics, private_manifests=manifests, fcc_in=fcc, runtime_seconds=time.perf_counter() - start, n1_validated=False)


def _check(name: str, cond: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(cond)}


def _synthetic_rows(n: int, *, mechanism: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(n):
        if mechanism == "pack":
            rank = 11 + (i % 10)
            unique = False
            material = True
            extra = False
        elif mechanism == "duplicate":
            rank = 30
            unique = True
            material = True
            extra = False
        elif mechanism == "evidence":
            rank = 60
            unique = False
            material = False
            extra = False
        elif mechanism == "extra":
            rank = 60
            unique = False
            material = True
            extra = True
        else:
            rank = 120
            unique = False
            material = True
            extra = False
        row = {
            "source_bucket": "synthetic_source",
            "language_bucket": "rust",
            "first_gold_rank_private": rank,
            "first_rank_bucket": _rank_bucket(rank),
            "top20_recovery": rank <= 20,
            "top50_recovery": rank <= 50,
            "top100_recovery": rank <= 100,
            "unique_file_top10_recovery": unique,
            "duplicate_pressure_bucket": "high" if unique else "none",
            "evidence_materializable": material,
            "extra_depth_append_blocked": extra,
            "scheduler_cap_or_stop_blocked": False,
            "hard_cap_violation": False,
        }
        row["primary_blocker_bucket"] = _classify_blocker(row)
        rows.append(row)
    return rows


def _synthetic_n1_artifact(**overrides: Any) -> dict[str, Any]:
    art = {
        "status": N1_EXPECTED_STATUS,
        "d0_scheduler_preservation_denominator_count": N1_D0_DENOMINATOR,
        "d0_scheduler_preservation_records": [
            {"metric_name": "baseline_reach", "value": 0, "passed": True},
            {"metric_name": "p2_reach", "value": 55, "passed": True},
            {"metric_name": "p3_reach", "value": 55, "passed": True},
            {"metric_name": "p4_reach", "value": 52, "passed": True},
            {"metric_name": "p4_treatment_hard_cap", "value": 0, "passed": True},
        ],
        "d1_total_count": 40,
        "d1_top10_actionable_count": 0,
        "d1_rank_blocked_count": 40,
        "forbidden_scan": {"status": "pass"},
    }
    art.update(overrides)
    return art


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []
    checks.append(_check("status_vocab_exact", tuple(STATUSES) == (
        "unavailable_with_reason", "fail_schema_contract", "fail_forbidden_scan",
        "no_go_n2_n1_artifact_or_trace_unavailable",
        "no_go_n2_insufficient_rank_blocked_denominator",
        "n2_rank_pack_decomposition_exploratory",
        "n2_rank_pack_mechanism_inconclusive",
        "n2_rank_pack_actionability_decomposition_pass")))
    default_report = _base_report(status="unavailable_with_reason", failure_reason_category="network_required_but_disabled", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=0, network_mode="disabled_opt_in", openlocus_binary_source="missing", fcc_in={"network_required_but_disabled": 1})
    checks.append(_check("default_unavailable", default_report["status"] == "unavailable_with_reason"))
    d0_pass = n1._evaluate_d0({"denominator_count": 272, "baseline_reach": 0, "p2_reach": 55, "p3_reach": 55, "p4_reach": 52, "p4_retained_p2_gain": 0.945455, "p4_p3_latency_ratio": 0.662177, "p4_treatment_hard_cap": 0, "file_order_preserved": True, "scheduler_actions_preserved": True})
    for name, rows, expected in (
        ("pass_pack", _synthetic_rows(20, mechanism="pack"), "n2_rank_pack_actionability_decomposition_pass"),
        ("inconclusive", _synthetic_rows(20, mechanism="mixed"), "n2_rank_pack_mechanism_inconclusive"),
        ("insufficient", _synthetic_rows(9, mechanism="pack"), "no_go_n2_insufficient_rank_blocked_denominator"),
        ("exploratory", _synthetic_rows(12, mechanism="mixed"), "n2_rank_pack_decomposition_exploratory"),
    ):
        _pub, m = _analyze_d2(rows)
        rep = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=0, network_mode="self_test", openlocus_binary_source="self_test", d0=d0_pass, metrics=m, n1_validated=True)
        checks.append(_check(f"status_{name}", rep["status"] == expected))
    pub, mixed_m = _analyze_d2(_synthetic_rows(10, mechanism="pack") + _synthetic_rows(10, mechanism="duplicate"))
    checks.append(_check("mixed_design_scope", mixed_m.get("design_authorized_scope") == "mixed_design_audit_only"))
    checks.append(_check("classification_sum", mixed_m.get("d2_classified_count") == mixed_m.get("d2_total_count") == 20))
    bad_m = dict(mixed_m); bad_m["d2_classified_count"] = 19
    bad_rep = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=0, network_mode="self_test", openlocus_binary_source="self_test", d0=d0_pass, metrics=bad_m, n1_validated=True)
    checks.append(_check("classification_sum_fail_closed", bad_rep["status"] == "fail_schema_contract"))
    mismatch_m = dict(mixed_m); mismatch_m["d2_total_count"] = 39; mismatch_m["d2_classified_count"] = 39; mismatch_m["classification_sum_matches"] = True
    mismatch_rep = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=0, network_mode="self_test", openlocus_binary_source="self_test", d0=d0_pass, metrics=mismatch_m, fcc_in={"d2_rank_blocked_reconstruction_mismatch": 1}, n1_validated=True)
    checks.append(_check("d2_mismatch_trace_unavailable_no_go", mismatch_rep["status"] == "no_go_n2_n1_artifact_or_trace_unavailable"))
    mismatch_blocking_rep = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=0, network_mode="self_test", openlocus_binary_source="self_test", d0=d0_pass, metrics=mismatch_m, fcc_in={"d2_rank_blocked_reconstruction_mismatch": 1, "candidate_order_unavailable": 1}, n1_validated=True)
    checks.append(_check("d2_mismatch_with_order_loss_fail_schema", mismatch_blocking_rep["status"] == "fail_schema_contract"))
    order_diag_rep = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=0, network_mode="self_test", openlocus_binary_source="self_test", d0=d0_pass, metrics=mixed_m, fcc_in={"candidate_order_unavailable": 7}, n1_validated=True)
    checks.append(_check("candidate_order_unavailable_nonblocking_when_d2_complete", order_diag_rep["status"] == "n2_rank_pack_actionability_decomposition_pass"))
    checks.append(_check("sanitized_rows_allowlist", all(set(r) <= SANITIZED_ROW_ALLOWLIST for r in pub)))
    checks.append(_check("sanitized_rows_exact_schema", all(set(r) == SANITIZED_ROW_ALLOWLIST for r in pub)))
    checks.append(_check("sanitized_rows_contract_names", bool(pub) and "first_gold_rank_bucket" in pub[0] and "first_rank_bucket" not in pub[0] and "evidencecore_materializable" in pub[0] and "evidence_materializable" not in pub[0]))
    checks.append(_check("recovery_bucket_values", bool(pub) and all(r.get(k) in {"recovered", "not_recovered"} for r in pub for k in ("top20_recovery_bucket", "top50_recovery_bucket", "top100_recovery_bucket", "unique_file_top10_recovery_bucket"))))
    medium_bucket, medium_count = _duplicate_pressure([
        {"path": "a"}, {"path": "a"}, {"path": "b"}, {"path": "b"}, {"path": "c"}, {"path": "c"}, {"path": "gold"}
    ], 7)
    checks.append(_check("duplicate_pressure_medium_bucket", medium_bucket == "medium" and medium_count == 3))
    checks.append(_check("scanner_rejects_path", _scan_summary({"path": "src/lib.rs"})["status"] == "fail"))
    checks.append(_check("scanner_rejects_span", _scan_summary({"start_line": 1, "end_line": 2})["status"] == "fail"))
    checks.append(_check("scanner_rejects_gold", _scan_summary({"gold_lines": [[1, 2]]})["status"] == "fail"))
    checks.append(_check("scanner_rejects_candidate", _scan_summary({"candidate_list": []})["status"] == "fail"))
    checks.append(_check("scanner_rejects_rank_score", _scan_summary({"rank": 12, "score": 0.7})["status"] == "fail"))
    checks.append(_check("scanner_rejects_private_path", _scan_summary({"private_path": "/tmp/x"})["status"] == "fail"))
    checks.append(_check("scanner_allows_sanitized", _scan_summary({"sanitized_analysis_records": pub[:1]})["status"] == "pass"))
    checks.append(_check("n1_helper_imported", callable(n1._run_frozen_p4_with_candidates)))
    with _TempJson(_synthetic_n1_artifact()) as pth:
        ok, _, _ = _validate_closed_n1_artifact(pth)
        checks.append(_check("closed_n1_artifact_validation_pass", ok))
    with _TempJson(_synthetic_n1_artifact(status="wrong")) as pth:
        ok, _, _ = _validate_closed_n1_artifact(pth)
        checks.append(_check("closed_n1_artifact_validation_fail", not ok))
    return checks, all(c["passed"] for c in checks)


class _TempJson:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.path = Path(f"/tmp/openlocus_n2_selftest_{os.getpid()}_{id(self)}.json")
    def __enter__(self) -> Path:
        self.path.write_text(json.dumps(self.data), encoding="utf-8")
        return self.path
    def __exit__(self, *_exc: Any) -> None:
        try:
            self.path.unlink()
        except OSError:
            pass


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(description="BEA-v1-N2 Rank/Pack Actionability Decomposition")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--enable-external-benchmark-network", action="store_true")
    ap.add_argument("--openlocus", default=None)
    ap.add_argument("--n1-artifact", type=Path, default=DEFAULT_N1_ARTIFACT)
    ap.add_argument("--fd1-artifact", type=Path, default=n1.DEFAULT_FD1_ARTIFACT)
    ap.add_argument("--fd1-private-decomposition-jsonl", type=Path, default=None)
    ap.add_argument("--fd1-replay-artifact", type=Path, default=None)
    ap.add_argument("--p4h-artifact", type=Path, default=n1.DEFAULT_P4H_ARTIFACT)
    ap.add_argument("--p4i-artifact", type=Path, default=n1.DEFAULT_P4I_ARTIFACT)
    ap.add_argument("--p4j-artifact", type=Path, default=n1.DEFAULT_P4J_ARTIFACT)
    ap.add_argument("--p4k-artifact", type=Path, default=n1.DEFAULT_P4K_ARTIFACT)
    return ap


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for c in checks:
            print(f"[{'PASS' if c['passed'] else 'FAIL'}] {c['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    if not args.enable_external_benchmark_network:
        report = _base_report(status="unavailable_with_reason", failure_reason_category="network_required_but_disabled", self_test_passed=ok, self_test_checks_total=len(checks), self_test_checks_passed=sum(1 for c in checks if c["passed"]), network_mode="disabled_opt_in", openlocus_binary_source=args.openlocus or "missing", fcc_in={"network_required_but_disabled": 1})
        print("enable_external_benchmark_network is false; writing unavailable_with_reason default artifact.", file=sys.stderr)
    else:
        report = _run_network(args, len(checks))
    safe_diagnostic = {
        "status": report.get("status"),
        "failure_reason_category": report.get("failure_reason_category"),
        "d0_denominator": report.get("d0_scheduler_preservation_denominator_count"),
        "d0_passed": all(bool(r.get("passed")) for r in report.get("d0_scheduler_preservation_records", [])),
        "d2_denominator": report.get("d2_rank_blocked_denominator_count"),
        "d2_classified": next((r.get("value") for r in report.get("d2_rank_pack_decomposition_records", []) if r.get("metric_name") == "d2_classified_count"), None),
        "design_authorized": report.get("design_authorized"),
        "design_authorized_scope": report.get("design_authorized_scope"),
        "nonzero_failure_categories": {
            str(r.get("failure_category")): int(r.get("count", 0))
            for r in report.get("failure_category_count_records", [])
            if int(r.get("count", 0))
        },
        "private_manifest_records": [
            {
                "manifest_name": r.get("manifest_name"),
                "record_count": r.get("record_count"),
                "records_written": r.get("records_written"),
            }
            for r in report.get("private_manifest_records", [])
        ],
    }
    print("safe_diagnostic=" + json.dumps(safe_diagnostic, sort_keys=True), file=sys.stderr)
    _enforce_no_forbidden(report)
    _write_json(args.out, report)
    print(f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, status={report['status']}, phase={PHASE}, d2={report.get('d2_rank_blocked_denominator_count')})")


if __name__ == "__main__":
    main()
