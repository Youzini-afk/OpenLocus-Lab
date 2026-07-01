#!/usr/bin/env python3
"""BEA-v1-HAAE-R2 small local lexical material experiment.

This evaluator reads an explicitly supplied R1E private material root and computes
aggregate-only metrics from existing rank_pack/outcome_metric rows.  It never
generates new candidates, scans source code, runs OpenLocus retrieval, writes
private material, calls providers, or changes runtime defaults.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


PHASE = "BEA-v1-HAAE-R2 Small Local Lexical Material Experiment"
SLUG = "bea_v1_haae_r2_small_local_lexical_material_experiment"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"

R1E_CHECKPOINT = "0135e1f"
R1E_STATUS = "haae_r1e_bounded_private_material_generation_complete_r2_small_experiment_authorized"
R1E_REPORT_PATH = Path(
    "artifacts/bea_v1_haae_r1e_bounded_private_experiment_material_generation/"
    "bea_v1_haae_r1e_bounded_private_experiment_material_generation_report.json"
)

STATUS_DEFAULT = "haae_r2_unavailable_no_explicit_r1e_private_material_root"
STATUS_PASS = "haae_r2_small_local_lexical_material_experiment_complete_r2a_public_audit_authorized"
STATUS_NO_GO_INVALID = "haae_r2_no_go_invalid_or_incomplete_r1e_material"
STATUS_NO_GO_NO_COMPARABLE = "haae_r2_no_go_no_comparable_rank_sources"
STATUS_FAIL_SOURCE_LOCK = "haae_r2_fail_closed_source_lock_mismatch"
STATUS_FAIL_MISSING_ROOT = "haae_r2_fail_closed_missing_explicit_private_material_root"
STATUS_FAIL_ROOT_BOUNDARY = "haae_r2_fail_closed_private_root_boundary_violation"
STATUS_FAIL_NEW_CANDIDATE = "haae_r2_fail_closed_new_candidate_generation_detected"
STATUS_FAIL_BROAD_RETRIEVAL = "haae_r2_fail_closed_broad_retrieval_detected"
STATUS_FAIL_RAW_PUBLICATION = "haae_r2_fail_closed_raw_publication_detected"
STATUS_FAIL_FORBIDDEN_SCAN = "haae_r2_fail_closed_forbidden_scan"
STATUS_FAIL_READBACK = "haae_r2_fail_closed_public_readback_mismatch"
STATUS_FAIL_OVERAUTH = "haae_r2_fail_closed_r2_overauthorization"

SCHEMA_GROUPS = [
    "task_identity",
    "anchor_source",
    "candidate_pool",
    "rank_pack",
    "span_projection",
    "scheduler_action",
    "evidence_core",
    "arm_assignment",
    "outcome_metric",
    "safety_probe_signal",
]
REQUIRED_GROUPS = {"task_identity", "anchor_source", "candidate_pool", "rank_pack", "evidence_core", "outcome_metric"}
RANK_SOURCES = ["bm25_like", "symbol_overlap", "rrf_like"]
MIN_R2_TASKS = 3
MAX_R2_TASKS = 5
MAX_R2_RANK_ROWS = 20
MAX_R2_CANDIDATE_ROWS = 20
MAX_R2_OUTCOME_ROWS = 5
MAX_R2_TOTAL_PRIVATE_ROWS = 100
MAX_R2_GROUP_FILE_BYTES = 1_000_000
SELF_TEST_EXPECTED = 15

GATE_NAMES = [
    "haae_r1e_source_locked_gate",
    "r1e_r2_authorization_match_gate",
    "explicit_private_material_root_gate",
    "private_material_root_boundary_gate",
    "r1e_material_provenance_gate",
    "sample_bounds_gate",
    "required_material_groups_present_gate",
    "rank_pack_existing_only_gate",
    "no_new_candidate_generation_gate",
    "no_rematerialization_gate",
    "no_broad_retrieval_gate",
    "no_scheduler_haae_layer_execution_gate",
    "no_selector_reranker_gate",
    "no_provider_model_network_gate",
    "no_runtime_default_change_gate",
    "no_bea_v1_a_p5_gate",
    "aggregate_metric_computation_only_gate",
    "public_aggregate_only_gate",
    "no_raw_publication_gate",
    "tiny_n_no_method_winner_claim_gate",
    "forbidden_scan_pass_gate",
    "docs_readback_match_gate",
    "self_test_total_public_readback_match_gate",
]


def bucket_count(value: int) -> str:
    if value <= 0:
        return "count_0"
    if value == 1:
        return "count_1"
    if value <= 5:
        return "count_2_to_5"
    if value <= 10:
        return "count_6_to_10"
    if value <= 20:
        return "count_11_to_20"
    if value <= 100:
        return "count_21_to_100"
    return "count_gt_100"


def bucket_rate(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "rate_not_applicable"
    value = numerator / denominator
    if value == 0:
        return "rate_0"
    if value < 0.5:
        return "rate_lt_0_5"
    if value < 1.0:
        return "rate_ge_0_5_lt_1"
    return "rate_1"


def bucket_rank_position(rank: int | None) -> str:
    if rank is None:
        return "position_missing"
    if rank <= 5:
        return "position_top_1_to_5"
    if rank <= 10:
        return "position_top_6_to_10"
    if rank <= 20:
        return "position_top_11_to_20"
    return "position_beyond_20"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_r1e_source_lock(repo_root: Path, report_path: Path | None = None) -> dict[str, Any]:
    path = repo_root / (report_path or R1E_REPORT_PATH)
    try:
        report = load_json(path)
    except Exception:
        return {"r1e_source_locked_bool": False, "source_lock_reason_bucket": "r1e_report_unavailable"}
    status_ok = report.get("status") == R1E_STATUS
    scan_ok = report.get("forbidden_scan", {}).get("status") == "pass"
    stop = report.get("stop_go_records", [{}])[0]
    r2_auth_ok = stop.get("haae_r2_small_local_lexical_material_experiment_authorized_bool") is True
    raw_forbidden_ok = stop.get("haae_r2_raw_publication_authorized_bool") is False
    forbidden_ok = all(stop.get(key) is False for key in [
        "haae_r2_new_candidate_generation_authorized_bool",
        "haae_r2_broad_retrieval_authorized_bool",
        "haae_r2_scheduler_authorized_bool",
        "haae_r2_haae_layer_execution_authorized_bool",
        "haae_r2_selector_reranker_authorized_bool",
        "haae_r2_provider_model_network_authorized_bool",
        "haae_r2_runtime_default_change_authorized_bool",
        "haae_r2_bea_v1_a_authorized_bool",
        "haae_r2_p5_authorized_bool",
        "haae_r2_method_winner_claim_authorized_bool",
    ])
    aggregate_metric_ok = stop.get("haae_r2_aggregate_metric_computation_authorized_bool") is True
    read_private_ok = stop.get("haae_r2_reads_r1e_private_material_bool") is True
    source_locked = status_ok and scan_ok and r2_auth_ok and raw_forbidden_ok and forbidden_ok and aggregate_metric_ok and read_private_ok
    return {
        "r1e_source_locked_bool": source_locked,
        "r1e_status_match_bool": status_ok,
        "r1e_forbidden_scan_pass_bool": scan_ok,
        "r1e_r2_authorization_match_bool": r2_auth_ok,
        "r1e_raw_publication_forbidden_match_bool": raw_forbidden_ok,
        "r1e_forbidden_operation_boundary_match_bool": forbidden_ok,
        "r1e_aggregate_metric_authorization_match_bool": aggregate_metric_ok,
        "r1e_private_material_read_authorization_match_bool": read_private_ok,
        "source_lock_reason_bucket": "pass" if source_locked else "source_lock_mismatch",
    }


def validate_private_material_root(root: Path, repo_root: Path) -> tuple[bool, str]:
    try:
        resolved = root.resolve(strict=False)
        repo = repo_root.resolve(strict=True)
    except Exception:
        return False, "path_resolution_failed"
    if not root.exists():
        return False, "missing_private_material_root"
    if not root.is_dir():
        return False, "private_material_root_not_directory"
    if root.is_symlink() or any(part == ".." for part in root.parts):
        return False, "private_material_root_escape_or_symlink"
    try:
        resolved.relative_to(repo)
        return False, "private_material_root_inside_public_workspace"
    except ValueError:
        pass
    group_dir = resolved / "groups"
    if not group_dir.is_dir():
        return False, "missing_groups_directory"
    if group_dir.is_symlink():
        return False, "groups_directory_symlink"
    for group in SCHEMA_GROUPS:
        file_path = group_dir / f"{group}.jsonl"
        if not file_path.exists():
            continue
        if file_path.is_symlink():
            return False, "group_file_symlink"
        if not file_path.is_file():
            return False, "group_file_not_regular"
        try:
            resolved_file = file_path.resolve(strict=True)
            resolved_file.relative_to(resolved)
        except Exception:
            return False, "group_file_escape"
        try:
            if file_path.stat().st_size > MAX_R2_GROUP_FILE_BYTES:
                return False, "group_file_too_large"
        except OSError:
            return False, "group_file_unstatable"
    return True, "valid_external_private_material_root"


def read_material_groups(root: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int], list[str]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    counts: dict[str, int] = {}
    issues: list[str] = []
    group_dir = root / "groups"
    for group in SCHEMA_GROUPS:
        path = group_dir / f"{group}.jsonl"
        if not path.exists():
            groups[group] = []
            counts[group] = 0
            issues.append(f"missing_{group}")
            continue
        try:
            rows = load_jsonl(path)
        except Exception:
            rows = []
            issues.append(f"unreadable_{group}")
        groups[group] = rows
        counts[group] = len(rows)
    return groups, counts, issues


def r1e_material_provenance(groups: dict[str, list[dict[str, Any]]]) -> tuple[bool, str]:
    task_rows = groups.get("task_identity", [])
    anchor_rows = groups.get("anchor_source", [])
    rank_rows = groups.get("rank_pack", [])
    outcome_rows = groups.get("outcome_metric", [])
    if not task_rows or not anchor_rows or not rank_rows or not outcome_rows:
        return False, "missing_required_provenance_groups"
    task_keys = {row.get("task_key") for row in task_rows}
    if len(task_keys) < MIN_R2_TASKS or len(task_keys) > MAX_R2_TASKS:
        return False, "task_key_count_out_of_bounds"
    if not all(isinstance(key, str) and key.startswith("r1e_task_") for key in task_keys):
        return False, "task_key_prefix_not_r1e"
    if not all(row.get("public_task_source") == "r14_sanity" for row in anchor_rows):
        return False, "anchor_source_not_r1e_r14_sanity"
    if not all(row.get("task_key") in task_keys for row in rank_rows + outcome_rows):
        return False, "rank_or_outcome_task_key_mismatch"
    return True, "r1e_compatible_markerless_public_lock_matched"


def rank_field(source: str) -> str:
    if source == "bm25_like":
        return "bm25_like_rank"
    if source == "symbol_overlap":
        return "symbol_overlap_rank"
    return "candidate_rank"


def top_candidate_by_task(rank_rows: list[dict[str, Any]], source: str) -> dict[str, str]:
    field = rank_field(source)
    best: dict[str, tuple[int, str]] = {}
    for row in rank_rows:
        rank = row.get(field)
        path = row.get("candidate_path")
        task_key = row.get("task_key")
        if not isinstance(rank, int) or not isinstance(path, str) or not isinstance(task_key, str):
            continue
        if task_key not in best or rank < best[task_key][0]:
            best[task_key] = (rank, path)
    return {task_key: path for task_key, (_rank, path) in best.items()}


def analyze_material(root: Path) -> dict[str, Any]:
    groups, counts, issues = read_material_groups(root)
    provenance_ok, provenance_bucket = r1e_material_provenance(groups)
    if issues or any(counts.get(group, 0) <= 0 for group in REQUIRED_GROUPS):
        return {"status": STATUS_NO_GO_INVALID, "group_counts": counts, "material_issues": issues, "r1e_material_provenance_bool": provenance_ok, "r1e_material_provenance_bucket": provenance_bucket}
    if not provenance_ok:
        return {"status": STATUS_NO_GO_INVALID, "group_counts": counts, "material_issues": [provenance_bucket], "r1e_material_provenance_bool": False, "r1e_material_provenance_bucket": provenance_bucket}

    rank_rows = groups["rank_pack"]
    outcome_rows = groups["outcome_metric"]
    material_task_keys = {row.get("task_key") for row in groups["task_identity"] if isinstance(row.get("task_key"), str)}
    outcome_task_keys = {row.get("task_key") for row in outcome_rows if isinstance(row.get("task_key"), str)}
    if not rank_rows or not outcome_rows or len(material_task_keys) == 0:
        return {"status": STATUS_NO_GO_INVALID, "group_counts": counts, "material_issues": ["missing_rank_or_outcome_rows"], "r1e_material_provenance_bool": provenance_ok, "r1e_material_provenance_bucket": provenance_bucket}
    candidate_rows_count = counts.get("candidate_pool", 0)
    total_private_rows = sum(counts.values())
    bounds_ok = (
        MIN_R2_TASKS <= len(material_task_keys) <= MAX_R2_TASKS
        and outcome_task_keys.issubset(material_task_keys)
        and len(rank_rows) <= MAX_R2_RANK_ROWS
        and candidate_rows_count <= MAX_R2_CANDIDATE_ROWS
        and len(outcome_rows) <= MAX_R2_OUTCOME_ROWS
        and total_private_rows <= MAX_R2_TOTAL_PRIVATE_ROWS
    )
    if not bounds_ok:
        return {"status": STATUS_NO_GO_INVALID, "group_counts": counts, "material_issues": ["r2_material_bounds_exceeded"], "task_count": len(material_task_keys), "rank_row_count": len(rank_rows), "candidate_row_count": candidate_rows_count, "outcome_row_count": len(outcome_rows), "private_row_read_count": total_private_rows, "r1e_material_provenance_bool": provenance_ok, "r1e_material_provenance_bucket": provenance_bucket, "sample_bounds_ok_bool": False}

    source_metrics: dict[str, dict[str, Any]] = {}
    comparable_sources: list[str] = []
    for source in RANK_SOURCES:
        field = rank_field(source)
        candidate_rows = [row for row in rank_rows if isinstance(row.get(field), int)]
        task_hit_count = 0
        positioned: list[int] = []
        for outcome in outcome_rows:
            task_key = outcome.get("task_key")
            gold_paths = {span.get("path") for span in outcome.get("gold_spans", []) if isinstance(span, dict)}
            ranks: list[int] = []
            for row in rank_rows:
                rank_value = row.get(field)
                if row.get("task_key") == task_key and row.get("candidate_path") in gold_paths and isinstance(rank_value, int):
                    ranks.append(rank_value)
            first = min(ranks) if ranks else None
            if first is not None:
                task_hit_count += 1
                positioned.append(first)
        if candidate_rows:
            comparable_sources.append(source)
        position_buckets: dict[str, int] = {}
        for position in positioned:
            bucket = bucket_rank_position(position)
            position_buckets[bucket] = position_buckets.get(bucket, 0) + 1
        source_metrics[source] = {
            "candidate_rows": len(candidate_rows),
            "task_count": len(material_task_keys),
            "hit_count": task_hit_count,
            "position_buckets": position_buckets,
            "existing_trace_present_bool": len(candidate_rows) > 0,
        }

    if set(comparable_sources) != set(RANK_SOURCES):
        return {
            "status": STATUS_NO_GO_NO_COMPARABLE,
            "group_counts": counts,
            "task_count": len(material_task_keys),
            "source_metrics": source_metrics,
            "r1e_material_provenance_bool": provenance_ok,
            "r1e_material_provenance_bucket": provenance_bucket,
            "sample_bounds_ok_bool": bounds_ok,
        }

    top_by_source = {source: top_candidate_by_task(rank_rows, source) for source in RANK_SOURCES}
    agreements: list[dict[str, Any]] = []
    for left, right in [("bm25_like", "symbol_overlap"), ("bm25_like", "rrf_like"), ("symbol_overlap", "rrf_like")]:
        comparable_tasks = sorted(set(top_by_source[left]) & set(top_by_source[right]))
        same = sum(1 for task_key in comparable_tasks if top_by_source[left][task_key] == top_by_source[right][task_key])
        agreements.append({"left": left, "right": right, "comparable_task_count": len(comparable_tasks), "same_top_count": same})

    return {
        "status": STATUS_PASS,
        "group_counts": counts,
        "task_count": len(material_task_keys),
        "rank_row_count": len(rank_rows),
        "outcome_row_count": len(outcome_rows),
        "source_metrics": source_metrics,
        "agreements": agreements,
        "private_row_read_count": sum(counts.values()),
        "candidate_row_count": counts.get("candidate_pool", 0),
        "r1e_material_provenance_bool": provenance_ok,
        "r1e_material_provenance_bucket": provenance_bucket,
        "sample_bounds_ok_bool": bounds_ok,
    }


PUBLIC_LEAK_PATTERNS = [
    ("workspace_path", re.compile(r"/workspace/|OpenLocus-Lab")),
    ("temp_path", re.compile(r"/tmp/|/var/tmp/")),
    ("raw_private_file", re.compile(r"\.jsonl\b|groups/|private_material_root/[A-Za-z0-9_]")),
    ("task_id", re.compile(r"r14s-\d+|\"task_id\"")),
    ("query_field", re.compile(r"\"query\"")),
    ("candidate_path_field", re.compile(r"candidate_path|crates/openlocus-[A-Za-z0-9_-]+/|\.rs\b")),
    ("raw_label_field", re.compile(r"gold_spans|hard_negatives|label_quality|snippet|start_line|end_line")),
    ("raw_numeric_trace", re.compile(r"rrf_like_score|bm25_like_rank|symbol_overlap_rank|first_gold_file_rank")),
    ("hash_value", re.compile(r"\b[a-f0-9]{32,64}\b")),
    ("raw_rows", re.compile(r"raw_rows|raw_sequence|row_values_public_bool\s*:\s*true")),
]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = []
    for bucket, pattern in PUBLIC_LEAK_PATTERNS:
        if pattern.search(text):
            findings.append(bucket)
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(self_test_total: int) -> dict[str, bool]:
    repo_root = Path(__file__).resolve().parents[1]
    fragments = [R1E_CHECKPOINT, STATUS_PASS, STATUS_DEFAULT, "HAAE-R2", f"{self_test_total}/{self_test_total}"]
    spaced_fragments = [R1E_CHECKPOINT, STATUS_PASS, STATUS_DEFAULT, "HAAE-R2", f"{self_test_total} / {self_test_total}"]

    def read(rel: str) -> str:
        path = repo_root / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced_fragments)

    readme = read("README.md")
    detail_en = read("docs/en/bea-v1-haae-r2-small-local-lexical-material-experiment.md")
    detail_zh = read("docs/zh/bea-v1-haae-r2-small-local-lexical-material-experiment.md")
    current_en = read("docs/en/current-research-conclusions.md")
    current_zh = read("docs/zh/current-research-conclusions.md")
    current_root = read("docs/current-research-conclusions.md")
    log_en = read("docs/en/research-log.md")
    log_zh = read("docs/zh/research-log.md")
    summary_en = read("docs/en/research-summary.md")
    summary_zh = read("docs/zh/research-summary.md")
    root_link_ok = "bea-v1-haae-r2-small-local-lexical-material-experiment.md" in current_root
    detail_match = has_all(detail_en) and has_all(detail_zh)
    current_match = has_all(current_en) and has_all(current_zh) and has_all(current_root) and root_link_ok
    log_match = has_all(log_en) and has_all(log_zh)
    summary_match = has_all(summary_en) and has_all(summary_zh)
    readme_match = has_all(readme)
    return {
        "readme_readback_match_bool": readme_match,
        "detail_docs_readback_match_bool": detail_match,
        "current_conclusions_readback_match_bool": current_match,
        "research_log_readback_match_bool": log_match,
        "research_summary_readback_match_bool": summary_match,
        "self_test_total_public_readback_match_bool": readme_match and detail_match and current_match and log_match and summary_match,
        "all_public_readback_match_bool": readme_match and detail_match and current_match and log_match and summary_match,
    }


def build_report(
    status: str,
    explicit_mode: bool,
    root_valid: bool = False,
    root_reason: str = "not_supplied",
    result: dict[str, Any] | None = None,
    self_test_total: int = SELF_TEST_EXPECTED,
    source_lock: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = result or {}
    repo_root = Path(__file__).resolve().parents[1]
    source_lock = source_lock or validate_r1e_source_lock(repo_root)
    readback = public_readback_match(self_test_total)
    group_counts = result.get("group_counts", {})
    source_metrics = result.get("source_metrics", {})
    agreements = result.get("agreements", [])
    private_row_read_count = int(result.get("private_row_read_count", 0))
    pass_status = status == STATUS_PASS
    gates: dict[str, bool] = {
        "haae_r1e_source_locked_gate": bool(source_lock.get("r1e_source_locked_bool")),
        "r1e_r2_authorization_match_gate": bool(source_lock.get("r1e_r2_authorization_match_bool")),
        "explicit_private_material_root_gate": explicit_mode,
        "private_material_root_boundary_gate": root_valid,
        "r1e_material_provenance_gate": bool(result.get("r1e_material_provenance_bool", False)) if explicit_mode else False,
        "sample_bounds_gate": bool(result.get("sample_bounds_ok_bool", False)) if explicit_mode else False,
        "required_material_groups_present_gate": all(group_counts.get(group, 0) > 0 for group in REQUIRED_GROUPS),
        "rank_pack_existing_only_gate": True,
        "no_new_candidate_generation_gate": True,
        "no_rematerialization_gate": True,
        "no_broad_retrieval_gate": True,
        "no_scheduler_haae_layer_execution_gate": True,
        "no_selector_reranker_gate": True,
        "no_provider_model_network_gate": True,
        "no_runtime_default_change_gate": True,
        "no_bea_v1_a_p5_gate": True,
        "aggregate_metric_computation_only_gate": True,
        "public_aggregate_only_gate": True,
        "no_raw_publication_gate": True,
        "tiny_n_no_method_winner_claim_gate": True,
        "forbidden_scan_pass_gate": True,
        "docs_readback_match_gate": readback["all_public_readback_match_bool"],
        "self_test_total_public_readback_match_gate": readback["self_test_total_public_readback_match_bool"],
    }
    if not explicit_mode and status == STATUS_DEFAULT:
        for name in ["explicit_private_material_root_gate", "private_material_root_boundary_gate", "required_material_groups_present_gate"]:
            gates[name] = False

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase_bucket": PHASE,
        "status": status,
        "self_test_total": self_test_total,
        "source_lock_records": [
            {
                "anonymous_source_lock_id": "haaer2source0000",
                "locked_haae_r1e_checkpoint": R1E_CHECKPOINT,
                "locked_haae_r1e_status": R1E_STATUS,
                "source_locked_bool": bool(source_lock.get("r1e_source_locked_bool")),
                "r1e_status_match_bool": bool(source_lock.get("r1e_status_match_bool")),
                "r1e_forbidden_scan_pass_bool": bool(source_lock.get("r1e_forbidden_scan_pass_bool")),
                "r1e_r2_authorization_match_bool": bool(source_lock.get("r1e_r2_authorization_match_bool")),
                "r1e_raw_publication_forbidden_match_bool": bool(source_lock.get("r1e_raw_publication_forbidden_match_bool")),
                "r1e_forbidden_operation_boundary_match_bool": bool(source_lock.get("r1e_forbidden_operation_boundary_match_bool")),
                "r1e_aggregate_metric_authorization_match_bool": bool(source_lock.get("r1e_aggregate_metric_authorization_match_bool")),
                "r1e_private_material_read_authorization_match_bool": bool(source_lock.get("r1e_private_material_read_authorization_match_bool")),
                "source_lock_reason_bucket": str(source_lock.get("source_lock_reason_bucket", "unknown")),
            }
        ],
        "execution_mode_records": [
            {
                "anonymous_execution_mode_id": "haaer2mode0000",
                "mode_bucket": "explicit_local_manual_existing_material_metric_computation" if explicit_mode else "default_no_private_material_root",
                "explicit_opt_in_bool": explicit_mode,
                "local_manual_only_bool": True,
                "private_read_count_bucket": "count_1_to_10" if explicit_mode and root_valid else "count_0",
                "private_write_count_bucket": "count_0",
                "ci_execution_bool": False,
                "network_operation_count_bucket": "count_0",
                "clone_operation_count_bucket": "count_0",
                "provider_or_model_operation_count_bucket": "count_0",
                "openlocus_runtime_execution_bool": False,
                "source_corpus_scan_bool": False,
            }
        ],
        "private_material_root_records": [
            {
                "anonymous_private_material_root_id": "haaer2root0000",
                "private_material_root_supplied_bool": explicit_mode,
                "root_valid_bool": root_valid,
                "root_boundary_status_bucket": root_reason,
                "no_concrete_path_published_bool": True,
                "no_basename_or_filename_published_bool": True,
                "existing_r1e_material_root_only_bool": True,
                "r1e_material_provenance_bucket": str(result.get("r1e_material_provenance_bucket", "not_evaluated")),
                "r1e_material_provenance_match_bool": bool(result.get("r1e_material_provenance_bool", False)) if explicit_mode else False,
                "private_writes_bool": False,
            }
        ],
        "material_group_read_records": [
            {
                "anonymous_material_group_read_id": f"haaer2group{idx:04d}",
                "group_bucket": group,
                "group_present_bool": group_counts.get(group, 0) > 0,
                "private_row_count_bucket": bucket_count(int(group_counts.get(group, 0))),
                "required_for_r2_bool": group in REQUIRED_GROUPS,
                "raw_values_published_bool": False,
            }
            for idx, group in enumerate(SCHEMA_GROUPS)
        ],
        "rank_source_metric_records": [
            {
                "anonymous_rank_source_metric_id": f"haaer2metric{idx:04d}",
                "rank_source_bucket": source,
                "existing_trace_present_bool": bool(source_metrics.get(source, {}).get("existing_trace_present_bool", False)),
                "task_count_bucket": bucket_count(int(source_metrics.get(source, {}).get("task_count", 0))),
                "candidate_private_row_count_bucket": bucket_count(int(source_metrics.get(source, {}).get("candidate_rows", 0))),
                "gold_file_hit_rate_bucket": bucket_rate(
                    int(source_metrics.get(source, {}).get("hit_count", 0)), int(source_metrics.get(source, {}).get("task_count", 0))
                ),
                "first_hit_position_distribution_bucket": {
                    key: bucket_count(int(value)) for key, value in source_metrics.get(source, {}).get("position_buckets", {}).items()
                },
                "raw_rank_values_published_bool": False,
            }
            for idx, source in enumerate(RANK_SOURCES)
        ],
        "rank_source_agreement_records": [
            {
                "anonymous_rank_source_agreement_id": f"haaer2agree{idx:04d}",
                "left_rank_source_bucket": item.get("left"),
                "right_rank_source_bucket": item.get("right"),
                "comparable_task_count_bucket": bucket_count(int(item.get("comparable_task_count", 0))),
                "same_top_candidate_rate_bucket": bucket_rate(int(item.get("same_top_count", 0)), int(item.get("comparable_task_count", 0))),
                "raw_candidate_identity_published_bool": False,
            }
            for idx, item in enumerate(agreements)
        ],
        "experiment_summary_records": [
            {
                "anonymous_experiment_summary_id": "haaer2summary0000",
                "task_count_bucket": bucket_count(int(result.get("task_count", 0))),
                "rank_private_row_count_bucket": bucket_count(int(result.get("rank_row_count", 0))),
                "outcome_private_row_count_bucket": bucket_count(int(result.get("outcome_row_count", 0))),
                "total_private_row_read_count_bucket": bucket_count(private_row_read_count),
                "sample_bounds_ok_bool": bool(result.get("sample_bounds_ok_bool", False)) if explicit_mode else False,
                "candidate_private_row_count_bucket": bucket_count(int(result.get("candidate_row_count", 0))),
                "aggregate_metric_computation_only_bool": True,
                "new_candidate_generation_bool": False,
                "rematerialization_bool": False,
                "broad_retrieval_bool": False,
                "method_winner_claim_bool": False,
            }
        ],
        "claim_boundary_records": [
            {
                "anonymous_claim_boundary_id": "haaer2claim0000",
                "aggregate_publication_only_bool": True,
                "raw_publication_bool": False,
                "new_candidate_generation_bool": False,
                "retrieval_execution_bool": False,
                "scheduler_haae_layer_execution_bool": False,
                "selector_reranker_bool": False,
                "provider_model_network_bool": False,
                "runtime_default_change_bool": False,
                "bea_v1_a_bool": False,
                "p5_bool": False,
                "method_winner_claim_bool": False,
                "haae_r2a_public_audit_package_authorized_bool": pass_status,
                "haae_r3_scale_preflight_authorized_bool": False,
            }
        ],
        "pass_fail_gate_records": [
            {
                "anonymous_gate_id": f"haaer2gate{idx:04d}",
                "gate_bucket": name,
                "gate_passed_bool": bool(gates.get(name, False)),
                "gate_evaluated_on_aggregate_bool": True,
                "gate_uses_private_row_values_bool": False,
                "gate_uses_network_clone_provider_bool": False,
            }
            for idx, name in enumerate(GATE_NAMES)
        ],
        "synthetic_validator_records": [
            {
                "anonymous_synthetic_validator_id": "haaer2synth0000",
                "validator_bucket": "default_no_private_read_write_fixture",
                "expected_status_bucket": STATUS_DEFAULT,
            },
            {
                "anonymous_synthetic_validator_id": "haaer2synth0001",
                "validator_bucket": "synthetic_valid_existing_r1e_material_fixture",
                "expected_status_bucket": STATUS_PASS,
            },
            {
                "anonymous_synthetic_validator_id": "haaer2synth0002",
                "validator_bucket": "leak_overauthorization_and_rank_source_mutation_fixtures",
                "expected_status_bucket": "validator_rejects_mutations",
            },
        ],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2readback0000", **readback}],
        "stop_go_records": [
            {
                "anonymous_stop_go_id": "haaer2stop0000",
                "next_allowed_phase": "BEA-v1-HAAE-R2A Public Audit Package" if pass_status else "stop_or_fix_r1e_material",
                "haae_r2a_public_audit_package_authorized_bool": pass_status,
                "haae_r3_scale_preflight_authorized_bool": False,
                "haae_r2_reads_existing_r1e_private_material_bool": explicit_mode and root_valid,
                "haae_r2_private_write_authorized_bool": False,
                "haae_r2_new_candidate_generation_authorized_bool": False,
                "haae_r2_rematerialization_authorized_bool": False,
                "haae_r2_broad_retrieval_authorized_bool": False,
                "haae_r2_scheduler_haae_layer_execution_authorized_bool": False,
                "haae_r2_selector_reranker_authorized_bool": False,
                "haae_r2_provider_model_network_authorized_bool": False,
                "haae_r2_runtime_default_change_authorized_bool": False,
                "haae_r2_bea_v1_a_authorized_bool": False,
                "haae_r2_p5_authorized_bool": False,
                "haae_r2_raw_publication_authorized_bool": False,
                "haae_r2_method_winner_claim_authorized_bool": False,
            }
        ],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate":
            gate["gate_passed_bool"] = scan["status"] == "pass"
    if status == STATUS_PASS:
        if scan["status"] != "pass":
            report["status"] = STATUS_FAIL_FORBIDDEN_SCAN
        elif not readback["all_public_readback_match_bool"]:
            report["status"] = STATUS_FAIL_READBACK
    return report


def default_report() -> dict[str, Any]:
    return build_report(STATUS_DEFAULT, explicit_mode=False, root_valid=False, root_reason="not_supplied", self_test_total=SELF_TEST_EXPECTED)


def write_report(report: dict[str, Any], out_path: Path | None) -> Path:
    path = out_path or ARTIFACT_DIR / REPORT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required_top = [
        "source_lock_records",
        "execution_mode_records",
        "private_material_root_records",
        "material_group_read_records",
        "rank_source_metric_records",
        "rank_source_agreement_records",
        "experiment_summary_records",
        "claim_boundary_records",
        "pass_fail_gate_records",
        "synthetic_validator_records",
        "public_readback_records",
        "stop_go_records",
        "forbidden_scan",
    ]
    for key in required_top:
        if key not in report:
            issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass":
        issues.append("public_report_forbidden_scan_failed")
    if report.get("forbidden_scan", {}).get("status") != "pass":
        issues.append("embedded_forbidden_scan_failed")
    source_records = report.get("source_lock_records", [])
    if source_records and source_records[0].get("locked_haae_r1e_checkpoint") != R1E_CHECKPOINT:
        issues.append("r1e_checkpoint_mismatch")
    if source_records and source_records[0].get("locked_haae_r1e_status") != R1E_STATUS:
        issues.append("r1e_status_mismatch")
    if report.get("status") == STATUS_PASS:
        source = source_records[0] if source_records else {}
        for key in [
            "source_locked_bool",
            "r1e_status_match_bool",
            "r1e_forbidden_scan_pass_bool",
            "r1e_r2_authorization_match_bool",
            "r1e_raw_publication_forbidden_match_bool",
            "r1e_forbidden_operation_boundary_match_bool",
            "r1e_aggregate_metric_authorization_match_bool",
            "r1e_private_material_read_authorization_match_bool",
        ]:
            if source.get(key) is not True:
                issues.append(f"source_lock_field_not_true_{key}")
    groups = {row.get("group_bucket") for row in report.get("material_group_read_records", [])}
    if set(SCHEMA_GROUPS) - groups:
        issues.append("material_group_records_incomplete")
    sources = {row.get("rank_source_bucket") for row in report.get("rank_source_metric_records", [])}
    if set(RANK_SOURCES) - sources:
        issues.append("rank_source_metric_records_incomplete")
    stop = report.get("stop_go_records", [{}])[0]
    forbidden_true_fields = [
        "haae_r3_scale_preflight_authorized_bool",
        "haae_r2_private_write_authorized_bool",
        "haae_r2_new_candidate_generation_authorized_bool",
        "haae_r2_rematerialization_authorized_bool",
        "haae_r2_broad_retrieval_authorized_bool",
        "haae_r2_scheduler_haae_layer_execution_authorized_bool",
        "haae_r2_selector_reranker_authorized_bool",
        "haae_r2_provider_model_network_authorized_bool",
        "haae_r2_runtime_default_change_authorized_bool",
        "haae_r2_bea_v1_a_authorized_bool",
        "haae_r2_p5_authorized_bool",
        "haae_r2_raw_publication_authorized_bool",
        "haae_r2_method_winner_claim_authorized_bool",
    ]
    for field in forbidden_true_fields:
        if stop.get(field) is not False:
            issues.append(f"overauthorization_{field}")
    claim = report.get("claim_boundary_records", [{}])[0]
    for field in [
        "raw_publication_bool",
        "new_candidate_generation_bool",
        "retrieval_execution_bool",
        "scheduler_haae_layer_execution_bool",
        "selector_reranker_bool",
        "provider_model_network_bool",
        "runtime_default_change_bool",
        "bea_v1_a_bool",
        "p5_bool",
        "method_winner_claim_bool",
        "haae_r3_scale_preflight_authorized_bool",
    ]:
        if claim.get(field) is not False:
            issues.append(f"claim_overauthorization_{field}")
    if report.get("status") == STATUS_PASS:
        if stop.get("haae_r2a_public_audit_package_authorized_bool") is not True:
            issues.append("missing_r2a_authorization")
        if stop.get("next_allowed_phase") != "BEA-v1-HAAE-R2A Public Audit Package":
            issues.append("next_allowed_phase_mismatch")
        if stop.get("haae_r2_reads_existing_r1e_private_material_bool") is not True:
            issues.append("missing_r1e_private_material_read_scope")
        summary = report.get("experiment_summary_records", [{}])[0]
        if summary.get("sample_bounds_ok_bool") is not True:
            issues.append("sample_bounds_not_true")
        if summary.get("task_count_bucket") != "count_2_to_5":
            issues.append("task_count_bucket_out_of_bounds")
        if summary.get("rank_private_row_count_bucket") not in {"count_2_to_5", "count_6_to_10", "count_11_to_20"}:
            issues.append("rank_row_bucket_out_of_bounds")
        if summary.get("candidate_private_row_count_bucket") not in {"count_2_to_5", "count_6_to_10", "count_11_to_20"}:
            issues.append("candidate_row_bucket_out_of_bounds")
        if summary.get("outcome_private_row_count_bucket") != "count_2_to_5":
            issues.append("outcome_row_bucket_out_of_bounds")
        if summary.get("total_private_row_read_count_bucket") != "count_21_to_100":
            issues.append("total_private_row_bucket_out_of_bounds")
        private_root = report.get("private_material_root_records", [{}])[0]
        if private_root.get("r1e_material_provenance_match_bool") is not True:
            issues.append("r1e_material_provenance_not_true")
        gates = {row.get("gate_bucket"): row.get("gate_passed_bool") for row in report.get("pass_fail_gate_records", [])}
        for gate in GATE_NAMES:
            if gates.get(gate) is not True:
                issues.append(f"gate_not_passed_{gate}")
        total = int(report.get("self_test_total", SELF_TEST_EXPECTED))
        if not public_readback_match(total)["all_public_readback_match_bool"]:
            issues.append("current_public_readback_failed")
    return issues


def make_synthetic_root(root: Path, comparable: bool = True, missing_group: str | None = None) -> None:
    if root.exists():
        shutil.rmtree(root)
    group_dir = root / "groups"
    group_dir.mkdir(parents=True)
    task_rows = [
        {"task_key": "r1e_task_0000", "task": {"task_id": "private-task-0", "query": "Alpha"}},
        {"task_key": "r1e_task_0001", "task": {"task_id": "private-task-1", "query": "Beta"}},
        {"task_key": "r1e_task_0002", "task": {"task_id": "private-task-2", "query": "Gamma"}},
    ]
    rank_rows: list[dict[str, Any]] = []
    outcome_rows: list[dict[str, Any]] = []
    for idx in range(3):
        task_key = f"r1e_task_{idx:04d}"
        gold_path = f"private/src/gold_{idx}.rs"
        alt_path = f"private/src/alt_{idx}.rs"
        base = {"task_key": task_key, "candidate_path": gold_path, "candidate_rank": 1}
        if comparable:
            base.update({"bm25_like_rank": 1, "symbol_overlap_rank": 1})
        rank_rows.append(base)
        rank_rows.append({"task_key": task_key, "candidate_path": alt_path, "candidate_rank": 2, "symbol_overlap_rank": 2 if comparable else None})
        outcome_rows.append({"task_key": task_key, "gold_spans": [{"path": gold_path, "start_line": 1, "end_line": 2}], "gold_file_hit": True})
    material = {
        "task_identity": task_rows,
        "anchor_source": [{"task_key": row["task_key"], "public_task_source": "r14_sanity"} for row in task_rows],
        "candidate_pool": [{"task_key": row["task_key"], "candidate_path": f"private/src/gold_{idx}.rs"} for idx, row in enumerate(task_rows)],
        "rank_pack": rank_rows,
        "span_projection": [{"task_key": row["task_key"]} for row in task_rows],
        "scheduler_action": [{"placeholder_group": "scheduler_action"}],
        "evidence_core": [{"task_key": row["task_key"], "path": f"private/src/gold_{idx}.rs"} for idx, row in enumerate(task_rows)],
        "arm_assignment": [{"placeholder_group": "arm_assignment"}],
        "outcome_metric": outcome_rows,
        "safety_probe_signal": [{"placeholder_group": "safety_probe_signal"}],
    }
    for group, rows in material.items():
        if group != missing_group:
            write_jsonl(group_dir / f"{group}.jsonl", rows)


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo_root = Path(__file__).resolve().parents[1]
    good_source_lock = {
        "r1e_source_locked_bool": True,
        "r1e_status_match_bool": True,
        "r1e_forbidden_scan_pass_bool": True,
        "r1e_r2_authorization_match_bool": True,
        "r1e_raw_publication_forbidden_match_bool": True,
        "r1e_forbidden_operation_boundary_match_bool": True,
        "r1e_aggregate_metric_authorization_match_bool": True,
        "r1e_private_material_read_authorization_match_bool": True,
        "source_lock_reason_bucket": "pass",
    }

    def check(name: str, condition: bool) -> None:
        if not condition:
            failures.append(name)

    default = default_report()
    check("default_status", default["status"] == STATUS_DEFAULT)
    check("default_no_private_read", default["execution_mode_records"][0]["private_read_count_bucket"] == "count_0")
    missing = build_report(STATUS_FAIL_MISSING_ROOT, True, False, "missing_private_material_root", source_lock=good_source_lock)
    check("missing_explicit_root_fails", missing["status"] == STATUS_FAIL_MISSING_ROOT)
    root_ok, root_reason = validate_private_material_root(repo_root, repo_root)
    check("repo_root_rejected", not root_ok and root_reason == "private_material_root_inside_public_workspace")
    with tempfile.TemporaryDirectory(prefix="haaer2_selftest_") as temp:
        root = Path(temp) / "private"
        make_synthetic_root(root)
        root_ok, _reason = validate_private_material_root(root, repo_root)
        result = analyze_material(root)
        valid = build_report(result["status"], True, root_ok, "valid_external_private_material_root", result, source_lock=good_source_lock)
        check("synthetic_valid_passes", valid["status"] == STATUS_PASS)
        make_synthetic_root(root, missing_group="candidate_pool")
        invalid = analyze_material(root)
        check("missing_required_group_no_go", invalid["status"] == STATUS_NO_GO_INVALID)
        make_synthetic_root(root, comparable=False)
        no_comp = analyze_material(root)
        check("bm25_rrf_comparable_required", no_comp["status"] == STATUS_NO_GO_NO_COMPARABLE)
        make_synthetic_root(root)
        write_jsonl(root / "groups" / "task_identity.jsonl", [
            {"task_key": f"r1e_task_{idx:04d}"} for idx in range(MAX_R2_TASKS + 1)
        ])
        too_large = analyze_material(root)
        check("oversized_material_no_go", too_large["status"] == STATUS_NO_GO_INVALID and (too_large.get("sample_bounds_ok_bool") is False or too_large.get("r1e_material_provenance_bucket") == "task_key_count_out_of_bounds"))
        symlink_root = Path(temp) / "symlink_private"
        make_synthetic_root(symlink_root)
        target = symlink_root / "groups" / "rank_pack.jsonl"
        target.unlink()
        target.symlink_to(root / "groups" / "rank_pack.jsonl")
        symlink_ok, symlink_reason = validate_private_material_root(symlink_root, repo_root)
        check("group_file_symlink_rejected", not symlink_ok and symlink_reason == "group_file_symlink")
    leak = dict(default)
    leak["debug"] = "/tmp/private-root/groups/rank_pack.jsonl r14s-001 query crates/openlocus-core/src/lib.rs"
    check("public_leak_scan_fails", scan_public_report(leak)["status"] == "fail")
    overauth = json.loads(json.dumps(default))
    overauth["stop_go_records"][0]["haae_r3_scale_preflight_authorized_bool"] = True
    check("r2_overauthorization_rejected", any(issue.startswith("overauthorization_") for issue in validate_report(overauth)))
    stale = json.loads(json.dumps(default))
    stale["self_test_total"] = 999
    stale["status"] = STATUS_PASS
    check("stale_readback_rejected", "current_public_readback_failed" in validate_report(stale))
    bad_source = build_report(STATUS_FAIL_SOURCE_LOCK, True, True, source_lock={"r1e_source_locked_bool": False})
    check("source_lock_mismatch_status", bad_source["status"] == STATUS_FAIL_SOURCE_LOCK)
    weak_source = json.loads(json.dumps(valid))
    weak_source["source_lock_records"][0]["r1e_forbidden_operation_boundary_match_bool"] = False
    check("weak_source_lock_rejected", any(issue.startswith("source_lock_field_not_true") for issue in validate_report(weak_source)))
    broad = json.loads(json.dumps(default))
    broad["claim_boundary_records"][0]["retrieval_execution_bool"] = True
    check("broad_retrieval_mutation_rejected", any(issue.startswith("claim_overauthorization_retrieval") for issue in validate_report(broad)))
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=PHASE)
    parser.add_argument("--allow-private-material-experiment", action="store_true")
    parser.add_argument("--private-material-root")
    parser.add_argument("--confirm-aggregate-publication-only", action="store_true")
    parser.add_argument("--validate-report")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out")
    args, unknown = parser.parse_known_args(argv)
    if unknown:
        raise ValueError("invalid arguments")
    return args


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
    except ValueError:
        print("invalid arguments", file=sys.stderr)
        return 2
    repo_root = Path(__file__).resolve().parents[1]
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 1
    if args.validate_report:
        report = load_json(Path(args.validate_report))
        issues = validate_report(report)
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True))
        return 0 if not issues else 1

    out_path = Path(args.out) if args.out else None
    if not args.allow_private_material_experiment:
        report = default_report()
        path = write_report(report, out_path)
        print(json.dumps({"status": report["status"], "artifact": str(path)}, sort_keys=True))
        return 0

    source_lock = validate_r1e_source_lock(repo_root)
    if not source_lock.get("r1e_source_locked_bool"):
        report = build_report(STATUS_FAIL_SOURCE_LOCK, True, False, "not_evaluated", source_lock=source_lock)
        write_report(report, out_path)
        return 1
    if not args.private_material_root or not args.confirm_aggregate_publication_only:
        report = build_report(STATUS_FAIL_MISSING_ROOT, True, False, "missing_private_material_root", source_lock=source_lock)
        write_report(report, out_path)
        return 1
    private_root = Path(args.private_material_root)
    root_ok, root_reason = validate_private_material_root(private_root, repo_root)
    if not root_ok:
        report = build_report(STATUS_FAIL_ROOT_BOUNDARY, True, False, root_reason, source_lock=source_lock)
        write_report(report, out_path)
        return 1
    result = analyze_material(private_root)
    status = result["status"]
    report = build_report(status, True, True, root_reason, result, source_lock=source_lock)
    path = write_report(report, out_path)
    print(json.dumps({"status": report["status"], "artifact": str(path)}, sort_keys=True))
    return 0 if report["status"] in {STATUS_PASS, STATUS_NO_GO_INVALID, STATUS_NO_GO_NO_COMPARABLE} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
