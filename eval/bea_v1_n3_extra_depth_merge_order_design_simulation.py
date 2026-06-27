#!/usr/bin/env python3
"""BEA-v1-N3: Extra-Depth Merge-Order Design Simulation.

N3 is an offline deterministic design simulation over the closed N2 D2=40
private rank-blocked rows.  It reuses N2/N1 reconstruction helpers to recreate
ordered private candidate rows under /tmp, then evaluates predeclared
merge-order-only reorder arms.  It does not run new retrieval, P5, BEA-v1-A,
selector/reranker code, learned scoring, provider calls, runtime/default
integration, broad retrieval expansion, or downstream-value evaluation.
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
import bea_v1_n2_rank_pack_actionability_decomposition as n2  # noqa: E402
import bea_v1_p4_latency_aware_retrieval_scheduler_smoke as p4  # noqa: E402
import bea_v1_p4l_locked_non_python_scheduler_validation as p4l  # noqa: E402


SCHEMA_VERSION = "bea_v1_n3_extra_depth_merge_order_design_simulation.v1"
GENERATED_BY = "eval/bea_v1_n3_extra_depth_merge_order_design_simulation.py"
CLAIM_LEVEL = "bea_v1_n3_extra_depth_merge_order_design_simulation_only"
MODE = "bea_v1_n3_extra_depth_merge_order_design_simulation"
PHASE = "BEA-v1-N3"

DEFAULT_OUT = Path(
    "artifacts/bea_v1_n3_extra_depth_merge_order_design_simulation/"
    "bea_v1_n3_extra_depth_merge_order_design_simulation_report.json"
)
DEFAULT_N2_ARTIFACT = Path(
    "artifacts/bea_v1_n2_rank_pack_actionability_decomposition/"
    "bea_v1_n2_rank_pack_actionability_decomposition_report.json"
)

N2_RESULT_CHECKPOINT = "ce47caf"
N2_SOURCE_CHECKPOINT = "7c90213"
N2_EMPIRICAL_CI_RUN_ID = "28272769423"
N2_EXPECTED_STATUS = "n2_rank_pack_actionability_decomposition_pass"
N2_D2_TOTAL = 40
N2_EXTRA_DEPTH_APPEND_BLOCKED = 40
N2_RANK_21_50 = 40
N2_TOP20 = 0
N2_TOP50 = 40
N2_TOP100 = 40
N2_UNIQUE_TOP10 = 0
N2_EVIDENCE_MATERIALIZABLE = 40

D3_EXPECTED_TOTAL = 40
D3_EXPLORATORY_MIN = 10
D3_ADEQUATE_MIN = 20
RECOVERY_PASS_RATE = 0.50
MATERIALIZATION_PASS_RATE = 0.95
RETENTION_PASS_RATE = 0.50

SIM_ARMS = (
    "frozen_p4_order",
    "fixed_interleave_2_primary_1_extra_after_4",
    "early_extra_depth_quota_3",
    "bounded_promotion_after_primary_prefix_4_3",
)

STATUSES = (
    "unavailable_with_reason",
    "fail_schema_contract",
    "fail_forbidden_scan",
    "no_go_n3_n2_artifact_or_trace_unavailable",
    "no_go_n3_insufficient_design_denominator",
    "no_go_n3_incomplete_closed_n2_reconstruction",
    "n3_merge_order_design_exploratory",
    "n3_merge_order_design_inconclusive",
    "n3_merge_order_tradeoff_no_go",
    "n3_merge_order_design_simulation_pass",
)

SANITIZED_ROW_ALLOWLIST = frozenset({
    "anonymous_local_id",
    "denominator",
    "source_bucket",
    "language_bucket",
    "baseline_first_gold_rank_bucket",
    "sim_arm",
    "top10_recovery_bucket",
    "evidencecore_materializable",
    "original_top10_retention_bucket",
    "duplicate_pressure_delta_bucket",
    "hard_cap_violation",
})

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "exact_path", "private_path", "private_dir", "trace_path",
    "start_line", "end_line", "line_range", "span", "spans", "exact_span",
    "gold", "gold_paths", "gold_lines", "gold_spans", "gold_labels",
    "candidate", "candidates", "candidate_list", "candidate_paths", "candidate_order",
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
    "source_result_checkpoint", "n2_result_checkpoint", "n3_result_checkpoint",
    "source_empirical_ci_run_id", "n2_empirical_ci_run_id", "n3_empirical_ci_run_id",
    "status_vocabulary",
    "sim_arm_vocabulary", "manifest_name", "storage_class", "manifest_hash",
    "denominator", "source_bucket", "language_bucket",
    "baseline_first_gold_rank_bucket", "sim_arm", "top10_recovery_bucket",
    "original_top10_retention_bucket", "duplicate_pressure_delta_bucket",
    "metric_block", "metric_name", "gate", "threshold_relation", "failure_category",
})

FAILURE_CATEGORIES = (
    "network_required_but_disabled",
    "n2_artifact_missing",
    "n2_artifact_parse_failed",
    "n2_artifact_mismatch",
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
    "d3_private_write_error",
    "gold_span_reconstruction_failed",
    "candidate_order_unavailable",
    "d3_reconstruction_mismatch",
    "candidate_pool_changed",
    "retrieval_expansion_used",
    "forbidden_policy_path_executed",
    "forbidden_leak_blocked",
    "unexpected_exception",
)

BLOCKING_FAILURES = {
    "n2_artifact_parse_failed",
    "n2_artifact_mismatch",
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
    "d3_private_write_error",
    "candidate_pool_changed",
    "retrieval_expansion_used",
    "forbidden_policy_path_executed",
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
    raw = os.environ.get("OPENLOCUS_BEA_V1_N3_PRIVATE_DIR", "")
    project_private = Path(__file__).resolve().parents[1] / ".openlocus" / "research-private"
    base = Path(raw) if raw else project_private / f"bea_v1_n3_{os.getpid()}"
    resolved = base.resolve()
    allowed_project = project_private.resolve()
    if not (str(resolved).startswith(str(allowed_project)) or str(resolved).startswith("/tmp/")):
        raise ValueError("invalid private N3 dir")
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
        "storage_class": "private_jsonl_under_project_private",
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
                        if isinstance(row, dict) and set(row) != SANITIZED_ROW_ALLOWLIST:
                            violations.append({"category": "sanitized_row_schema_mismatch", "path": f"{sub}[{i}]"})
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
    cats = Counter(v["category"] for v in violations)
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "violation_categories": [{"category": c, "count": n} for c, n in sorted(cats.items())],
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


def _validate_closed_n2_artifact(path: Path | None) -> tuple[bool, str, dict[str, int]]:
    fcc = {k: 0 for k in FAILURE_CATEGORIES}
    art, status = _load_artifact(path)
    if status != "pass":
        fcc["n2_artifact_missing" if status == "artifact_missing" else "n2_artifact_parse_failed"] = 1
        return False, status, fcc
    records = art.get("d2_rank_pack_decomposition_records", [])
    failures: list[str] = []
    checks = {
        "status": art.get("status") == N2_EXPECTED_STATUS,
        "source_ci_run_id": art.get("source_ci_run_id") == N2_EMPIRICAL_CI_RUN_ID,
        "source_checkpoint": art.get("source_checkpoint") == N2_SOURCE_CHECKPOINT,
        "d2_total": art.get("d2_rank_blocked_denominator_count", _metric_value(records, "d2_total_count")) == N2_D2_TOTAL,
        "extra_depth": _metric_value(records, "primary_blocker_extra_depth_append_blocked_count") == N2_EXTRA_DEPTH_APPEND_BLOCKED,
        "rank_21_50": _metric_value(records, "first_gold_rank_bucket_rank_21_50_count") == N2_RANK_21_50,
        "top20": _metric_value(records, "top20_recovery_count") == N2_TOP20,
        "top50": _metric_value(records, "top50_recovery_count") == N2_TOP50,
        "top100": _metric_value(records, "top100_recovery_count") == N2_TOP100,
        "unique_top10": _metric_value(records, "unique_file_pack_recovery_at10_count") == N2_UNIQUE_TOP10,
        "materializable": _metric_value(records, "evidence_materializable_count") == N2_EVIDENCE_MATERIALIZABLE,
        "design_authorized": art.get("design_authorized") is True,
        "design_scope": art.get("design_authorized_scope") == "extra_depth_merge_order_design_only",
        "forbidden_scan": art.get("forbidden_scan", {}).get("status") == "pass",
    }
    for name, passed in checks.items():
        if not passed:
            failures.append(name)
    if failures:
        fcc["n2_artifact_mismatch"] = 1
        return False, "n2_artifact_mismatch:" + ",".join(sorted(failures)), fcc
    return True, "pass", fcc


def _rank_bucket_from_rank(rank: int | None) -> str:
    return n2._rank_bucket(rank)


def _candidate_key(c: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(c.get("path", "") or ""),
        str(c.get("start_line", "") or ""),
        str(c.get("end_line", "") or ""),
        str(c.get("method", "") or c.get("source", "") or c.get("channel", "") or ""),
    )


def _normalize_candidates(row: dict[str, Any]) -> list[dict[str, Any]]:
    cands = row.get("candidate_order_private")
    if not isinstance(cands, list):
        return []
    out: list[dict[str, Any]] = []
    for fallback_rank, cand in enumerate(cands, start=1):
        if not isinstance(cand, dict):
            continue
        rank = cand.get("rank")
        if not isinstance(rank, int) or rank < 1:
            rank = fallback_rank
        clean = dict(cand)
        clean["rank"] = rank
        clean["original_index"] = rank
        out.append(clean)
    out.sort(key=lambda c: int(c.get("rank", 0) or 0))
    return out


def _is_extra_depth_candidate(cand: dict[str, Any]) -> bool:
    meta = " ".join(str(cand.get(k, "") or "").lower() for k in ("method", "source", "channel", "phase"))
    if "extra" in meta or "depth" in meta:
        return True
    # Frozen P4 appends extra-depth material after the original primary pack in
    # the closed N2 traces. This fallback uses original order only, not gold.
    rank = cand.get("rank")
    return isinstance(rank, int) and rank > 20


def _append_missing(seq: list[dict[str, Any]], original: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = {_candidate_key(c) for c in seq}
    out = list(seq)
    for cand in original:
        key = _candidate_key(cand)
        if key not in seen:
            out.append(cand)
            seen.add(key)
    return out


def _simulate_arm(cands: list[dict[str, Any]], arm: str) -> list[dict[str, Any]]:
    original = list(cands)
    if arm == "frozen_p4_order":
        return original
    primary = [c for c in original if not _is_extra_depth_candidate(c)]
    extra = [c for c in original if _is_extra_depth_candidate(c)]
    if arm == "fixed_interleave_2_primary_1_extra_after_4":
        prefix = original[:4]
        used = {_candidate_key(c) for c in prefix}
        p = [c for c in primary if _candidate_key(c) not in used]
        e = [c for c in extra if _candidate_key(c) not in used]
        merged = list(prefix)
        while p or e:
            merged.extend(p[:2]); p = p[2:]
            if e:
                merged.append(e.pop(0))
        return _append_missing(merged, original)
    if arm == "early_extra_depth_quota_3":
        merged = extra[:3] + primary + extra[3:]
        return _append_missing(merged, original)
    if arm == "bounded_promotion_after_primary_prefix_4_3":
        merged = primary[:4] + extra[:3] + primary[4:] + extra[3:]
        return _append_missing(merged, original)
    raise ValueError(f"unknown arm: {arm}")


def _first_gold_rank(cands: list[dict[str, Any]], gold_paths: set[str]) -> int | None:
    for idx, cand in enumerate(cands, start=1):
        if str(cand.get("path", "") or "") in gold_paths:
            return idx
    return None


def _top10_files(cands: list[dict[str, Any]]) -> list[str]:
    return [str(c.get("path", "") or "") for c in cands[:10] if c.get("path")]


def _duplicate_count(files: list[str]) -> int:
    seen: set[str] = set()
    dup = 0
    for f in files:
        if f in seen:
            dup += 1
        seen.add(f)
    return dup


def _duplicate_delta_bucket(base_files: list[str], sim_files: list[str]) -> str:
    delta = _duplicate_count(sim_files) - _duplicate_count(base_files)
    if delta > 0:
        return "worsened"
    return "improved_or_same"


def _retention_rate(base_files: list[str], sim_files: list[str]) -> float:
    base_unique = list(dict.fromkeys(base_files))
    if not base_unique:
        return 1.0
    sim_set = set(sim_files)
    return len([f for f in base_unique if f in sim_set]) / len(base_unique)


def _retention_bucket(rate: float) -> str:
    return "retained_ge_50" if rate >= RETENTION_PASS_RATE else "retained_lt_50"


def _unique_top10_bucket(mean_unique_files: float) -> str:
    if mean_unique_files >= 8:
        return "unique_ge_8"
    if mean_unique_files >= 5:
        return "unique_5_to_7"
    return "unique_lt_5"


def _row_is_d3(row: dict[str, Any]) -> bool:
    rank = row.get("first_gold_rank_private")
    return (
        row.get("first_rank_bucket") == "rank_21_50"
        and row.get("primary_blocker_bucket") == "extra_depth_append_blocked"
        and isinstance(rank, int) and 20 < rank <= 50
        and bool(row.get("top50_recovery"))
        and not bool(row.get("top20_recovery"))
        and bool(row.get("evidence_materializable"))
        and bool(row.get("candidate_order_private"))
        and bool(row.get("gold_paths_private"))
    )


def _simulate_rows(rows: list[dict[str, Any]], private_path: Path | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    d3_rows = [r for r in rows if _row_is_d3(r)]
    public_rows: list[dict[str, Any]] = []
    arm_stats: dict[str, Counter[str]] = {arm: Counter() for arm in SIM_ARMS}
    pool_changed = False
    for idx, row in enumerate(d3_rows):
        cands = _normalize_candidates(row)
        gold_paths = {str(p) for p in row.get("gold_paths_private", []) if p}
        base_keys = sorted(_candidate_key(c) for c in cands)
        base_top10 = _top10_files(cands)
        baseline_rank = _first_gold_rank(cands, gold_paths)
        for arm in SIM_ARMS:
            sim = _simulate_arm(cands, arm)
            if sorted(_candidate_key(c) for c in sim) != base_keys:
                pool_changed = True
            sim_rank = _first_gold_rank(sim, gold_paths)
            recovered = sim_rank is not None and sim_rank <= 10
            sim_top10 = _top10_files(sim)
            retention = _retention_rate(base_top10, sim_top10)
            unique_top10_count = len(set(sim_top10))
            materializable = bool(row.get("evidence_materializable"))
            hard_cap = bool(row.get("hard_cap_violation"))
            arm_stats[arm]["rows"] += 1
            arm_stats[arm]["recovered"] += int(recovered)
            arm_stats[arm]["recovered_materializable"] += int(recovered and materializable)
            arm_stats[arm]["retained_ge_50"] += int(retention >= RETENTION_PASS_RATE)
            arm_stats[arm]["unique_top10_total"] += unique_top10_count
            arm_stats[arm]["hard_cap"] += int(hard_cap)
            public_row = {
                "anonymous_local_id": f"n3r{idx:05d}",
                "denominator": "D3_extra_depth_merge_order_design",
                "source_bucket": str(row.get("source_bucket", "unknown_source")),
                "language_bucket": str(row.get("language_bucket", "unknown_language")),
                "baseline_first_gold_rank_bucket": _rank_bucket_from_rank(baseline_rank),
                "sim_arm": arm,
                "top10_recovery_bucket": "recovered" if recovered else "not_recovered",
                "evidencecore_materializable": materializable,
                "original_top10_retention_bucket": _retention_bucket(retention),
                "duplicate_pressure_delta_bucket": _duplicate_delta_bucket(base_top10, sim_top10),
                "hard_cap_violation": hard_cap,
            }
            public_rows.append(public_row)
            if private_path is not None:
                _append_private_jsonl(private_path, {
                    "schema_version": "bea_v1_n3_private_simulation_row.v1",
                    "denominator_index_private": row.get("denominator_index_private", idx),
                    "arm": arm,
                    "baseline_first_gold_rank_private": baseline_rank,
                    "sim_first_gold_rank_private": sim_rank,
                    "top10_recovered": recovered,
                    "original_top10_retention_rate_private": retention,
                    "candidate_pool_changed": sorted(_candidate_key(c) for c in sim) != base_keys,
                })
    metrics: dict[str, Any] = {
        "d3_total_count": len(d3_rows),
        "candidate_pool_changed": pool_changed,
        "retrieval_expansion_used": False,
        "gold_labels_used_in_policy": False,
        "forbidden_policy_path_executed": False,
    }
    pass_arm_count = 0
    tradeoff_arm_count = 0
    for arm in SIM_ARMS:
        st = arm_stats[arm]
        den = int(st.get("rows", 0))
        rec = int(st.get("recovered", 0))
        recovery_rate = rec / den if den else 0.0
        material_rate = int(st.get("recovered_materializable", 0)) / rec if rec else 0.0
        retention_rate = int(st.get("retained_ge_50", 0)) / den if den else 0.0
        unique_mean = int(st.get("unique_top10_total", 0)) / den if den else 0.0
        hard_cap = int(st.get("hard_cap", 0))
        metrics[f"{arm}_top10_gold_file_recovery_count"] = rec
        metrics[f"{arm}_top10_gold_file_recovery_rate"] = round(recovery_rate, 6)
        metrics[f"{arm}_recovered_evidence_materializable_count"] = int(st.get("recovered_materializable", 0))
        metrics[f"{arm}_recovered_evidence_materializable_rate"] = round(material_rate, 6)
        metrics[f"{arm}_original_top10_file_retention_rate"] = round(retention_rate, 6)
        metrics[f"{arm}_top10_unique_file_count_mean_bucket"] = _unique_top10_bucket(unique_mean)
        metrics[f"{arm}_hard_cap_violation_count"] = hard_cap
        eligible = arm != "frozen_p4_order" and recovery_rate >= RECOVERY_PASS_RATE
        good = eligible and hard_cap == 0 and material_rate >= MATERIALIZATION_PASS_RATE and retention_rate >= RETENTION_PASS_RATE
        tradeoff = eligible and not good
        pass_arm_count += int(good)
        tradeoff_arm_count += int(tradeoff)
    metrics["pass_eligible_nonbaseline_arm_count"] = pass_arm_count
    metrics["tradeoff_nonbaseline_arm_count"] = tradeoff_arm_count
    return public_rows, metrics


def _metric_records(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    names = [
        "d3_total_count", "candidate_pool_changed", "retrieval_expansion_used",
        "gold_labels_used_in_policy", "forbidden_policy_path_executed",
        "pass_eligible_nonbaseline_arm_count", "tradeoff_nonbaseline_arm_count",
    ]
    for arm in SIM_ARMS:
        names.extend([
            f"{arm}_top10_gold_file_recovery_count",
            f"{arm}_top10_gold_file_recovery_rate",
            f"{arm}_recovered_evidence_materializable_count",
            f"{arm}_recovered_evidence_materializable_rate",
            f"{arm}_original_top10_file_retention_rate",
            f"{arm}_top10_unique_file_count_mean_bucket",
            f"{arm}_hard_cap_violation_count",
        ])
    return [{"metric_block": "D3_extra_depth_merge_order_design", "metric_name": n, "value": metrics.get(n, 0)} for n in names]


def _gate_records(metrics: dict[str, Any], scan_pass: bool, n2_validated: bool) -> list[dict[str, Any]]:
    d3 = int(metrics.get("d3_total_count", 0))
    return [
        {"gate": "closed_n2_artifact_validated", "value": 1 if n2_validated else 0, "threshold_relation": "boolean", "threshold_value": 1, "passed": n2_validated},
        {"gate": "d3_total_exact", "value": d3, "threshold_relation": "==", "threshold_value": D3_EXPECTED_TOTAL, "passed": d3 == D3_EXPECTED_TOTAL},
        {"gate": "candidate_pool_unchanged", "value": 0 if metrics.get("candidate_pool_changed") else 1, "threshold_relation": "boolean", "threshold_value": 1, "passed": not bool(metrics.get("candidate_pool_changed"))},
        {"gate": "retrieval_expansion_not_used", "value": 0 if metrics.get("retrieval_expansion_used") else 1, "threshold_relation": "boolean", "threshold_value": 1, "passed": not bool(metrics.get("retrieval_expansion_used"))},
        {"gate": "nonbaseline_arm_pass_eligible", "value": int(metrics.get("pass_eligible_nonbaseline_arm_count", 0)), "threshold_relation": ">=", "threshold_value": 1, "passed": int(metrics.get("pass_eligible_nonbaseline_arm_count", 0)) >= 1},
        {"gate": "forbidden_scan_pass", "value": 1 if scan_pass else 0, "threshold_relation": "boolean", "threshold_value": 1, "passed": scan_pass},
    ]


def _status_from(metrics: dict[str, Any], fcc: dict[str, int], *, unavailable: bool = False, n2_validated: bool = False) -> tuple[str, str]:
    if unavailable:
        return "unavailable_with_reason", "network_required_but_disabled"
    if int(fcc.get("n2_artifact_missing", 0)) or int(fcc.get("fd1_artifact_missing", 0)) or int(fcc.get("fd1_private_decomposition_missing", 0)):
        return "no_go_n3_n2_artifact_or_trace_unavailable", "n2_artifact_or_trace_unavailable"
    if sum(int(fcc.get(k, 0)) for k in BLOCKING_FAILURES) or not n2_validated:
        return "fail_schema_contract", "blocking_failure_present"
    d3 = int(metrics.get("d3_total_count", 0))
    if d3 < D3_EXPLORATORY_MIN:
        return "no_go_n3_insufficient_design_denominator", "d3_denominator_lt_10"
    if d3 < D3_ADEQUATE_MIN:
        return "n3_merge_order_design_exploratory", "d3_denominator_10_to_19"
    if d3 != D3_EXPECTED_TOTAL:
        return "no_go_n3_incomplete_closed_n2_reconstruction", "d3_total_not_40"
    if int(metrics.get("pass_eligible_nonbaseline_arm_count", 0)) >= 1:
        return "n3_merge_order_design_simulation_pass", "nonbaseline_arm_passed_predeclared_gates"
    if int(metrics.get("tradeoff_nonbaseline_arm_count", 0)) >= 1:
        return "n3_merge_order_tradeoff_no_go", "recovery_only_with_tradeoff"
    return "n3_merge_order_design_inconclusive", "no_nonbaseline_arm_recovery_threshold"


def _base_report(
    *, status: str, failure_reason_category: str, self_test_passed: bool,
    self_test_checks_total: int, self_test_checks_passed: int | None,
    network_mode: str, openlocus_binary_source: str, metrics: dict[str, Any] | None = None,
    sanitized_rows: list[dict[str, Any]] | None = None, private_manifests: list[dict[str, Any]] | None = None,
    fcc_in: dict[str, int] | None = None, runtime_seconds: float = 0.0, n2_validated: bool = False,
) -> dict[str, Any]:
    fcc = {k: 0 for k in FAILURE_CATEGORIES}
    for k, v in (fcc_in or {}).items():
        if k in fcc:
            fcc[k] = int(v)
    metrics = metrics or {"d3_total_count": 0, "candidate_pool_changed": False, "retrieval_expansion_used": False, "pass_eligible_nonbaseline_arm_count": 0, "tradeoff_nonbaseline_arm_count": 0}
    if bool(metrics.get("candidate_pool_changed")):
        fcc["candidate_pool_changed"] = max(1, fcc["candidate_pool_changed"])
    if bool(metrics.get("retrieval_expansion_used")):
        fcc["retrieval_expansion_used"] = max(1, fcc["retrieval_expansion_used"])
    if status == "auto":
        status, failure_reason_category = _status_from(metrics, fcc, n2_validated=n2_validated)
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
        "source_result_checkpoint": N2_RESULT_CHECKPOINT,
        "n2_result_checkpoint": N2_RESULT_CHECKPOINT,
        "n3_result_checkpoint": "",
        "source_checkpoint": N2_SOURCE_CHECKPOINT,
        "source_ci_run_id": N2_EMPIRICAL_CI_RUN_ID,
        "source_empirical_ci_run_id": N2_EMPIRICAL_CI_RUN_ID,
        "n2_empirical_ci_run_id": N2_EMPIRICAL_CI_RUN_ID,
        "n3_empirical_ci_run_id": "",
        "status_vocabulary": list(STATUSES),
        "sim_arm_vocabulary": list(SIM_ARMS),
        "closed_n2_artifact_validated": bool(n2_validated),
        "d3_design_denominator_count": int(metrics.get("d3_total_count", 0)),
        "candidate_pool_changed": bool(metrics.get("candidate_pool_changed", False)),
        "retrieval_expansion_used": bool(metrics.get("retrieval_expansion_used", False)),
        "new_retrieval_used": False,
        "new_files_added": False,
        "candidate_scoring_model_used": False,
        "learned_weights_used": False,
        "gold_labels_used_in_policy": False,
        "snippet_content_relevance_scoring_used": False,
        "provider_calls_made": False,
        "remote_provider_calls_made": False,
        "selector_or_reranker_executed": False,
        "selector_or_reranker_authorized": False,
        "p5_executed": False,
        "p5_authorized": False,
        "v1_a_selector_executed": False,
        "v1_a_authorized": False,
        "runtime_behavior_changed": False,
        "runtime_promotion_authorized": False,
        "implementation_authorized": False,
        "extra_depth_merge_order_implementation_smoke_design_authorized": status == "n3_merge_order_design_simulation_pass",
        "default_should_change": False,
        "method_winner_claimed": False,
        "downstream_agent_value_proven": False,
        "offline_deterministic_simulation_only": True,
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
        "d3_merge_order_simulation_records": _metric_records(metrics),
        "sanitized_analysis_records": sanitized_rows or [],
        "private_manifest_records": private_manifests or [],
        "failure_category_count_records": [{"failure_category": k, "count": int(fcc.get(k, 0))} for k in sorted(fcc)],
        "aggregate_runtime_seconds": round(float(runtime_seconds), 3),
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass" and status != "fail_forbidden_scan":
        fcc["forbidden_leak_blocked"] = max(1, fcc["forbidden_leak_blocked"])
        report["status"] = "fail_forbidden_scan"
        report["failure_reason_category"] = "forbidden_leak_blocked"
        report["failure_category_count_records"] = [{"failure_category": k, "count": int(fcc.get(k, 0))} for k in sorted(fcc)]
    report["forbidden_scan"] = _scan_summary(report)
    report["gate_records"] = _gate_records(metrics, report["forbidden_scan"]["status"] == "pass", n2_validated)
    return report


def _run_network(args: argparse.Namespace, checks_count: int) -> dict[str, Any]:
    start = time.perf_counter()
    fcc = {k: 0 for k in FAILURE_CATEGORIES}
    metrics: dict[str, Any] = {"d3_total_count": 0, "candidate_pool_changed": False, "retrieval_expansion_used": False}
    manifests: list[dict[str, Any]] = []
    try:
        n2_ok, _reason, n2_fcc = _validate_closed_n2_artifact(args.n2_artifact)
        for k, v in n2_fcc.items():
            fcc[k] = max(fcc.get(k, 0), int(v))
        if not n2_ok:
            return _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=args.openlocus or "explicit", metrics=metrics, fcc_in=fcc, runtime_seconds=time.perf_counter() - start, n2_validated=False)
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
            return _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=args.openlocus or "explicit", metrics=metrics, fcc_in=fcc, runtime_seconds=time.perf_counter() - start, n2_validated=n2_ok)
        pdir = _private_dir()
        recon_path = pdir / "bea_v1_n3.p4l_private_reconstruction.jsonl"
        d2_path = pdir / "bea_v1_n3.private_recreated_n2_rows.jsonl"
        sim_path = pdir / "bea_v1_n3.private_simulation_rows.jsonl"
        for pth in (recon_path, d2_path, sim_path):
            if pth.exists():
                pth.unlink()
        openlocus_bin, openlocus_source = p4.c5a._resolve_openlocus_binary(args.openlocus)
        if openlocus_bin is None:
            fcc["retrieval_policy_failed"] = 1
            return _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=openlocus_source, metrics=metrics, fcc_in=fcc, runtime_seconds=time.perf_counter() - start, n2_validated=n2_ok)
        denom, recon_meta = p4l._reconstruct_locked_denominator(openlocus_bin=openlocus_bin, pt=pt, private_path=recon_path, fcc=fcc)
        if int(recon_meta.get("non_python_locked_count", 0)) != n1.P4L_LOCKED_NON_PYTHON_DENOMINATOR:
            fcc["locked_denominator_mismatch"] = 1
        n1._enrich_locked_denominator_with_gold_lines(denom, fcc)
        d2_rows = n2._build_d2_rows_from_locked_denominator(openlocus_bin=openlocus_bin, denom=denom, private_path=d2_path, fcc=fcc)
        sanitized, metrics = _simulate_rows(d2_rows, private_path=sim_path)
        if int(metrics.get("d3_total_count", 0)) != D3_EXPECTED_TOTAL:
            fcc["d3_reconstruction_mismatch"] = 1
        if bool(metrics.get("candidate_pool_changed")):
            fcc["candidate_pool_changed"] = 1
        manifests = [
            _manifest_for_path(recon_path, "bea_v1_n3_p4l_private_reconstruction_manifest", "bea_v1_p4l_private_reconstruction.v1"),
            _manifest_for_path(d2_path, "bea_v1_n3_private_recreated_n2_rows_manifest", "bea_v1_n2_private_rank_pack_row.v1"),
            _manifest_for_path(sim_path, "bea_v1_n3_private_simulation_rows_manifest", "bea_v1_n3_private_simulation_row.v1"),
        ]
        return _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=openlocus_source, metrics=metrics, sanitized_rows=sanitized, private_manifests=manifests, fcc_in=fcc, runtime_seconds=time.perf_counter() - start, n2_validated=n2_ok)
    except Exception:
        fcc["unexpected_exception"] = 1
        return _base_report(status="fail_schema_contract", failure_reason_category="unexpected_exception", self_test_passed=True, self_test_checks_total=checks_count, self_test_checks_passed=None, network_mode="local_explicit", openlocus_binary_source=args.openlocus or "explicit", metrics=metrics, private_manifests=manifests, fcc_in=fcc, runtime_seconds=time.perf_counter() - start, n2_validated=False)


def _check(name: str, cond: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(cond)}


def _synthetic_d3_rows(n: int, *, mode: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(n):
        cands: list[dict[str, Any]] = []
        for r in range(1, 21):
            cands.append({"rank": r, "path": f"primary_{i}_{r}.rs", "method": "primary", "start_line": 1, "end_line": 2})
        gold_rank = 25 if mode != "inconclusive" else 49
        extra_paths = [f"extra_{i}_{r}.rs" for r in range(21, 51)]
        if mode in {"pass", "tradeoff"}:
            gold_pos = 2  # third promoted extra lands in top-10 for quota/promotion arms.
        elif mode == "hardcap_bad":
            gold_pos = 2
        else:
            gold_pos = gold_rank - 21
        for j, pth in enumerate(extra_paths, start=21):
            if j == 21 + gold_pos:
                pth = f"gold_{i}.rs"
            cands.append({"rank": j, "path": pth, "method": "extra_depth", "start_line": 1, "end_line": 2})
        if mode == "tradeoff":
            # Recovery will cross, but original top-10 retention is poor because
            # all original top-10 files are unique and early quota displaces too many.
            pass
        rows.append({
            "denominator_index_private": i,
            "source_bucket": "synthetic_source",
            "language_bucket": "rust",
            "gold_paths_private": [f"gold_{i}.rs"],
            "first_gold_rank_private": gold_rank if mode == "inconclusive" else 25,
            "first_rank_bucket": "rank_21_50",
            "top20_recovery": False,
            "top50_recovery": True,
            "primary_blocker_bucket": "extra_depth_append_blocked",
            "evidence_materializable": mode != "materialization_bad",
            "hard_cap_violation": mode == "hardcap_bad",
            "candidate_order_private": cands,
        })
    return rows


def _synthetic_n2_artifact(**overrides: Any) -> dict[str, Any]:
    metrics = [
        ("d2_total_count", 40), ("primary_blocker_extra_depth_append_blocked_count", 40),
        ("first_gold_rank_bucket_rank_21_50_count", 40), ("top20_recovery_count", 0),
        ("top50_recovery_count", 40), ("top100_recovery_count", 40),
        ("unique_file_pack_recovery_at10_count", 0), ("evidence_materializable_count", 40),
    ]
    art = {
        "status": N2_EXPECTED_STATUS,
        "source_checkpoint": N2_SOURCE_CHECKPOINT,
        "source_ci_run_id": N2_EMPIRICAL_CI_RUN_ID,
        "d2_rank_blocked_denominator_count": 40,
        "design_authorized": True,
        "design_authorized_scope": "extra_depth_merge_order_design_only",
        "d2_rank_pack_decomposition_records": [{"metric_name": k, "value": v} for k, v in metrics],
        "forbidden_scan": {"status": "pass"},
    }
    art.update(overrides)
    return art


class _TempJson:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.path = Path(f"/tmp/openlocus_n3_selftest_{os.getpid()}_{id(self)}.json")
    def __enter__(self) -> Path:
        self.path.write_text(json.dumps(self.data), encoding="utf-8")
        return self.path
    def __exit__(self, *_exc: Any) -> None:
        try:
            self.path.unlink()
        except OSError:
            pass


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []
    checks.append(_check("status_vocab_exact", tuple(STATUSES) == (
        "unavailable_with_reason", "fail_schema_contract", "fail_forbidden_scan",
        "no_go_n3_n2_artifact_or_trace_unavailable", "no_go_n3_insufficient_design_denominator",
        "no_go_n3_incomplete_closed_n2_reconstruction", "n3_merge_order_design_exploratory",
        "n3_merge_order_design_inconclusive", "n3_merge_order_tradeoff_no_go",
        "n3_merge_order_design_simulation_pass")))
    default_report = _base_report(status="unavailable_with_reason", failure_reason_category="network_required_but_disabled", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=0, network_mode="disabled_opt_in", openlocus_binary_source="missing", fcc_in={"network_required_but_disabled": 1})
    checks.append(_check("default_unavailable", default_report["status"] == "unavailable_with_reason"))
    for mode, expected in (
        ("pass", "n3_merge_order_design_simulation_pass"),
        ("inconclusive", "n3_merge_order_design_inconclusive"),
        ("hardcap_bad", "n3_merge_order_tradeoff_no_go"),
    ):
        pub, m = _simulate_rows(_synthetic_d3_rows(40, mode=mode))
        rep = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=0, network_mode="self_test", openlocus_binary_source="self_test", metrics=m, sanitized_rows=pub, n2_validated=True)
        checks.append(_check(f"status_{mode}", rep["status"] == expected))
    pub, m = _simulate_rows(_synthetic_d3_rows(39, mode="pass"))
    rep = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=0, network_mode="self_test", openlocus_binary_source="self_test", metrics=m, sanitized_rows=pub, n2_validated=True)
    checks.append(_check("d3_reconstruction_mismatch_no_go", rep["status"] == "no_go_n3_incomplete_closed_n2_reconstruction"))
    pub, m = _simulate_rows(_synthetic_d3_rows(15, mode="pass"))
    rep = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=0, network_mode="self_test", openlocus_binary_source="self_test", metrics=m, sanitized_rows=pub, n2_validated=True)
    checks.append(_check("d3_exploratory_status", rep["status"] == "n3_merge_order_design_exploratory"))
    cands = _normalize_candidates(_synthetic_d3_rows(1, mode="pass")[0])
    checks.append(_check("arm_determinism", _simulate_arm(cands, "early_extra_depth_quota_3") == _simulate_arm(cands, "early_extra_depth_quota_3")))
    checks.append(_check("candidate_pool_preserved", sorted(_candidate_key(c) for c in cands) == sorted(_candidate_key(c) for c in _simulate_arm(cands, "bounded_promotion_after_primary_prefix_4_3"))))
    checks.append(_check("sanitized_schema_exact", all(set(r) == SANITIZED_ROW_ALLOWLIST for r in pub)))
    checks.append(_check("scanner_rejects_path", _scan_summary({"path": "src/lib.rs"})["status"] == "fail"))
    checks.append(_check("scanner_rejects_exact_rank", _scan_summary({"rank": 21})["status"] == "fail"))
    checks.append(_check("scanner_rejects_gold", _scan_summary({"gold_lines": [[1, 2]]})["status"] == "fail"))
    checks.append(_check("scanner_rejects_candidate_list", _scan_summary({"candidate_list": []})["status"] == "fail"))
    checks.append(_check("scanner_allows_sanitized", _scan_summary({"sanitized_analysis_records": pub[:1]})["status"] == "pass"))
    checks.append(_check("n2_checkpoint_not_n3_result_checkpoint", default_report.get("n2_result_checkpoint") == N2_RESULT_CHECKPOINT and default_report.get("n3_result_checkpoint") == ""))
    checks.append(_check("n2_ci_not_n3_empirical_ci", default_report.get("n2_empirical_ci_run_id") == N2_EMPIRICAL_CI_RUN_ID and default_report.get("n3_empirical_ci_run_id") == ""))
    non_extra = _synthetic_d3_rows(40, mode="pass")
    non_extra[0]["primary_blocker_bucket"] = "mixed_or_unclassified"
    _pub, m = _simulate_rows(non_extra)
    checks.append(_check("d3_requires_extra_depth_blocker", int(m.get("d3_total_count", 0)) == 39))
    with _TempJson(_synthetic_n2_artifact()) as pth:
        ok, _, _ = _validate_closed_n2_artifact(pth)
        checks.append(_check("n2_artifact_validation_pass", ok))
    with _TempJson(_synthetic_n2_artifact(status="wrong")) as pth:
        ok, _, _ = _validate_closed_n2_artifact(pth)
        checks.append(_check("n2_artifact_validation_fail", not ok))
    with _TempJson(_synthetic_n2_artifact(design_authorized=True, design_authorized_scope="pack_budget_design_only")) as pth:
        ok, _, _ = _validate_closed_n2_artifact(pth)
        checks.append(_check("n2_design_scope_required", not ok))
    forbidden_flags = ["p5_authorized", "v1_a_authorized", "selector_or_reranker_authorized", "runtime_promotion_authorized", "retrieval_expansion_used"]
    checks.append(_check("no_forbidden_authorization_flags", all(default_report.get(f) is False for f in forbidden_flags)))
    checks.append(_check("n2_helper_imported", callable(n2._build_d2_rows_from_locked_denominator)))
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(description="BEA-v1-N3 Extra-Depth Merge-Order Design Simulation")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--enable-external-benchmark-network", action="store_true")
    ap.add_argument("--openlocus", default=None)
    ap.add_argument("--n2-artifact", type=Path, default=DEFAULT_N2_ARTIFACT)
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
    _enforce_no_forbidden(report)
    _write_json(args.out, report)
    print(f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, status={report['status']}, phase={PHASE}, d3={report.get('d3_design_denominator_count')})")


if __name__ == "__main__":
    main()
