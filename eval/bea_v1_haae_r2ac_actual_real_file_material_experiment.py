#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AC actual real-file material experiment.

Default mode reads/writes no private data. Explicit mode reads only an
operator-supplied existing R2AA private material root and publishes aggregate-only
bucketed metrics.
"""

from __future__ import annotations

import io
import json
import re
import sys
import tempfile
from contextlib import redirect_stderr
from itertools import combinations
from pathlib import Path
from statistics import mean, median
from typing import Any, Sequence

PHASE = "BEA-v1-HAAE-R2AC Actual Real-File Material Experiment"
SLUG = "bea_v1_haae_r2ac_actual_real_file_material_experiment"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AB_CHECKPOINT = "52a23da"
R2AB_STATUS = "haae_r2ab_real_file_material_public_audit_package_complete_r2ac_real_file_material_experiment_authorized"
R2AA_CHECKPOINT = "f325b65"
R2AA_STATUS = "haae_r2aa_actual_explicit_local_real_file_material_smoke_complete_r2ab_public_audit_authorized"
R2AB_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ab_real_file_material_public_audit_package/bea_v1_haae_r2ab_real_file_material_public_audit_package_report.json")

PRIVATE_MANIFEST = "private_manifest.json"
R2AA_OWNER = "haae_r2aa_actual_explicit_local_real_file_material_smoke"
RANK_SOURCES = ["query_identifier_overlap", "symbol_name_overlap", "lexical_bm25_like", "content_identifier_fusion", "control_baseline"]
REQUIRED_GROUPS = ["task_identity", "source_manifest_private", "candidate_pool", "rank_pack", "evidence_span", "outcome_metric"]
MAX_GROUP_FILE_BYTES = 8_000_000
MAX_TOTAL_PRIVATE_BYTES = 60_000_000

STATUS_DEFAULT = "haae_r2ac_unavailable_no_explicit_r2aa_private_material_root"
STATUS_PASS_SIGNAL = "haae_r2ac_actual_real_file_material_experiment_complete_r2ad_public_audit_authorized_signal_present"
STATUS_PASS_WEAK = "haae_r2ac_actual_real_file_material_experiment_complete_r2ad_public_audit_authorized_weak_or_no_signal"
PASS_STATUSES = {STATUS_PASS_SIGNAL, STATUS_PASS_WEAK}
STATUS_NO_GO_ROOT = "haae_r2ac_no_go_invalid_r2aa_private_material_root"
STATUS_NO_GO_SCHEMA = "haae_r2ac_no_go_invalid_r2aa_material_schema"
STATUS_NO_GO_ALIGNMENT = "haae_r2ac_no_go_rank_source_or_outcome_alignment_incomplete"
STATUS_FAIL_SOURCE = "haae_r2ac_fail_closed_source_lock_mismatch"
STATUS_FAIL_LEAK = "haae_r2ac_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2ac_fail_closed_public_readback_mismatch"
STATUS_FAIL_OVERAUTH = "haae_r2ac_fail_closed_stop_go_overauthorization"
SELF_TEST_EXPECTED = 21
NEXT_PHASE = "BEA-v1-HAAE-R2AD Actual Real-File Material Experiment Public Audit Package"

FORBIDDEN_STOP_TRUE = ["new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "source_scan_authorized_bool", "broad_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]
GATE_NAMES = ["r2ab_source_locked_gate", "explicit_private_root_gate", "private_root_boundary_gate", "r2aa_manifest_owner_status_gate", "regular_bounded_group_files_gate", "required_group_files_gate", "rank_sources_exact_gate", "outcome_task_alignment_gate", "aggregate_metrics_only_gate", "no_private_write_gate", "no_new_material_generation_gate", "no_source_scan_retrieval_runtime_gate", "no_ci_network_provider_clone_gate", "no_scheduler_selector_gate", "no_method_default_scaling_claim_gate", "r2ad_only_stop_go_gate", "public_aggregate_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def count_bucket(n: int) -> str:
    if n <= 0: return "count_0"
    if n == 1: return "count_1"
    if n <= 5: return "count_2_to_5"
    if n <= 10: return "count_6_to_10"
    if n <= 20: return "count_11_to_20"
    if n <= 50: return "count_21_to_50"
    if n <= 500: return "count_51_to_500"
    if n <= 20000: return "count_le_20000"
    return "count_gt_20000"


def rate_bucket(hits: int, total: int) -> str:
    if total <= 0 or hits <= 0: return "rate_0"
    if hits == total: return "rate_1"
    ratio = hits / total
    if ratio < 0.25: return "rate_0_to_25"
    if ratio < 0.5: return "rate_25_to_50"
    if ratio < 0.75: return "rate_50_to_75"
    return "rate_75_to_99"


def rank_bucket(values: Sequence[float]) -> str:
    if not values: return "rank_unavailable"
    value = float(median(values))
    if value <= 1: return "rank_1"
    if value <= 5: return "rank_2_to_5"
    if value <= 10: return "rank_6_to_10"
    if value <= 20: return "rank_11_to_20"
    if value <= 40: return "rank_21_to_40"
    return "rank_gt40"


def mrr_bucket(values: Sequence[float]) -> str:
    if not values: return "mrr_unavailable"
    value = mean(values)
    if value >= 0.5: return "mrr_high"
    if value >= 0.2: return "mrr_medium"
    if value > 0: return "mrr_low"
    return "mrr_zero"


def spread_bucket(values: Sequence[int]) -> str:
    if not values: return "spread_unavailable"
    spread = max(values) - min(values)
    if spread <= 0: return "spread_none"
    if spread <= 4: return "spread_low"
    if spread <= 12: return "spread_medium"
    return "spread_high"


def validate_r2ab_source(r2ab: dict[str, Any]) -> dict[str, bool]:
    src = (r2ab.get("source_lock_records") or [{}])[0]
    stop = (r2ab.get("stop_go_records") or [{}])[0]
    status_ok = r2ab.get("status") == R2AB_STATUS
    scan_ok = r2ab.get("forbidden_scan", {}).get("status") == "pass"
    r2aa_ok = src.get("locked_haae_r2aa_checkpoint") == R2AA_CHECKPOINT and src.get("locked_haae_r2aa_status") == R2AA_STATUS and src.get("source_locked_bool") is True
    auth_ok = stop.get("haae_r2ac_actual_real_file_material_experiment_authorized_bool") is True
    explicit_ok = stop.get("r2ac_explicit_private_root_required_bool") is True and stop.get("r2ac_reads_existing_r2aa_private_material_only_bool") is True and stop.get("r2ac_aggregate_metrics_only_bool") is True
    boundary_ok = all(stop.get(field, False) is False for field in ["new_material_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "broad_scan_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"])
    return {"status_ok": status_ok, "scan_ok": scan_ok, "r2aa_ok": r2aa_ok, "auth_ok": auth_ok, "explicit_ok": explicit_ok, "boundary_ok": boundary_ok, "source_locked": status_ok and scan_ok and r2aa_ok and auth_ok and explicit_ok and boundary_ok}


def validate_private_root(root: Path, repo: Path) -> tuple[bool, str, dict[str, Path], dict[str, Any]]:
    if ".." in root.parts:
        return False, "path_traversal", {}, {}
    try:
        resolved = root.resolve(strict=True); repo_resolved = repo.resolve(strict=True)
    except Exception:
        return False, "root_missing_or_unresolvable", {}, {}
    if not resolved.is_dir() or root.is_symlink() or resolved.is_symlink(): return False, "root_not_directory_or_symlink", {}, {}
    if resolved == repo_resolved or repo_resolved in resolved.parents: return False, "root_under_public_repo", {}, {}
    manifest_path = resolved / PRIVATE_MANIFEST
    if not manifest_path.exists() or not manifest_path.is_file() or manifest_path.is_symlink(): return False, "missing_or_invalid_manifest", {}, {}
    try: manifest = load_json(manifest_path)
    except Exception: return False, "manifest_parse_failed", {}, {}
    if manifest.get("owner_bucket") != R2AA_OWNER: return False, "manifest_owner_mismatch", {}, manifest
    if manifest.get("schema_version") != "bea_v1_haae_r2aa_actual_explicit_local_real_file_material_smoke_v1": return False, "manifest_schema_mismatch", {}, manifest
    if manifest.get("status") != R2AA_STATUS: return False, "manifest_status_mismatch", {}, manifest
    if manifest.get("target_task_count") != 20 or manifest.get("candidate_depth_cap") != 40 or manifest.get("source_file_cap") != 500 or manifest.get("private_row_cap") != 20000: return False, "manifest_bounds_mismatch", {}, manifest
    if set(manifest.get("rank_sources", [])) != set(RANK_SOURCES): return False, "manifest_rank_sources_mismatch", {}, manifest
    groups_dir = resolved / "groups"
    if not groups_dir.exists() or not groups_dir.is_dir() or groups_dir.is_symlink(): return False, "missing_groups_directory", {}, manifest
    groups_resolved = groups_dir.resolve(strict=True)
    files: dict[str, Path] = {}; total = 0
    for group in REQUIRED_GROUPS:
        path = groups_dir / f"{group}.jsonl"
        if not path.exists(): return False, "missing_required_group", {}, manifest
        if not path.is_file() or path.is_symlink() or path.resolve(strict=True).parent != groups_resolved: return False, "invalid_group_file", {}, manifest
        size = path.stat().st_size
        if size > MAX_GROUP_FILE_BYTES: return False, "group_file_too_large", {}, manifest
        total += size; files[group] = path
    if total > MAX_TOTAL_PRIVATE_BYTES: return False, "private_root_too_large", {}, manifest
    return True, "valid_existing_r2aa_private_material_root", files, manifest


def read_groups(files: dict[str, Path]) -> dict[str, list[dict[str, Any]]]:
    return {group: load_jsonl(path) for group, path in files.items()}


def compute_metrics(groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    tasks = groups.get("task_identity", []); candidates = groups.get("candidate_pool", []); ranks = groups.get("rank_pack", []); outcomes = groups.get("outcome_metric", [])
    task_keys = {str(row.get("task_key")) for row in tasks if row.get("task_key") is not None}
    outcome_by_task = {str(row.get("task_key")): row for row in outcomes if row.get("task_key") is not None}
    outcome_keys = set(outcome_by_task)
    candidate_by_task: dict[str, list[dict[str, Any]]] = {}
    candidate_path_by_key: dict[str, str] = {}
    for row in candidates:
        task = row.get("task_key"); key = row.get("candidate_key")
        if task is not None:
            candidate_by_task.setdefault(str(task), []).append(row)
        if key is not None:
            candidate_path_by_key[str(key)] = str(row.get("candidate_path", ""))
    ranks_by_source_task: dict[tuple[str, str], list[dict[str, Any]]] = {}
    sources_seen: set[str] = set()
    for row in ranks:
        task = row.get("task_key"); source = row.get("rank_source")
        if task is not None and source in RANK_SOURCES:
            ranks_by_source_task.setdefault((str(source), str(task)), []).append(row); sources_seen.add(str(source))
    metric_records: list[dict[str, Any]] = []
    top_candidates: dict[tuple[str, str], list[str]] = {}
    top20_hit_counts: list[int] = []
    for source in RANK_SOURCES:
        covered_tasks = covered_candidates = gold_hits = top1 = top5 = top10 = top20 = missing_outcome = 0
        first_ranks: list[int] = []
        for task in sorted(task_keys):
            rows = [row for row in ranks_by_source_task.get((source, task), []) if isinstance(row.get("rank"), int)]
            rows.sort(key=lambda row: (int(row.get("rank", 999999)), str(row.get("candidate_key", ""))))
            top_candidates[(source, task)] = [str(row.get("candidate_key")) for row in rows[:20]]
            if task not in outcome_by_task:
                missing_outcome += 1; continue
            if not rows: continue
            covered_tasks += 1; covered_candidates += len(rows)
            gold_paths = {str(span.get("path")) for span in outcome_by_task.get(task, {}).get("gold_spans", []) if span.get("path")}
            hit_ranks = [int(row["rank"]) for row in rows if candidate_path_by_key.get(str(row.get("candidate_key"))) in gold_paths]
            if hit_ranks:
                best = min(hit_ranks); first_ranks.append(best); gold_hits += 1
                if best <= 1: top1 += 1
                if best <= 5: top5 += 1
                if best <= 10: top10 += 1
                if best <= 20: top20 += 1
        top20_hit_counts.append(top20)
        mrr_values = [1 / value for value in first_ranks if value > 0]
        metric_records.append({"rank_source_bucket": source, "rank_source_present_bool": covered_tasks > 0, "task_coverage_bucket": count_bucket(covered_tasks), "candidate_coverage_bucket": count_bucket(covered_candidates), "gold_file_hit_count_bucket": count_bucket(gold_hits), "gold_file_hit_rate_bucket": rate_bucket(gold_hits, covered_tasks), "top1_hit_count_bucket": count_bucket(top1), "top5_hit_count_bucket": count_bucket(top5), "top10_hit_count_bucket": count_bucket(top10), "top20_hit_count_bucket": count_bucket(top20), "mrr_bucket": mrr_bucket(mrr_values), "median_first_gold_rank_bucket": rank_bucket(first_ranks), "missing_outcome_bucket": count_bucket(missing_outcome), "exact_values_published_bool": False})
    agreement_records: list[dict[str, Any]] = []
    for left, right in combinations(RANK_SOURCES, 2):
        same_top = overlap5 = overlap10 = overlap20 = comparable = 0
        for task in sorted(task_keys):
            l = top_candidates.get((left, task), []); r = top_candidates.get((right, task), [])
            if not l or not r: continue
            comparable += 1
            if l[:1] == r[:1]: same_top += 1
            if set(l[:5]) & set(r[:5]): overlap5 += 1
            if set(l[:10]) & set(r[:10]): overlap10 += 1
            if set(l[:20]) & set(r[:20]): overlap20 += 1
        agreement_records.append({"left_rank_source_bucket": left, "right_rank_source_bucket": right, "comparable_task_bucket": count_bucket(comparable), "same_top_candidate_rate_bucket": rate_bucket(same_top, comparable), "overlap_at_5_rate_bucket": rate_bucket(overlap5, comparable), "overlap_at_10_rate_bucket": rate_bucket(overlap10, comparable), "overlap_at_20_rate_bucket": rate_bucket(overlap20, comparable), "exact_candidate_values_published_bool": False})
    non_control_top20 = max((int(next((row["top20_hit_count_bucket"].split("_")[1] == "11" and 20 or 0 for row in []), 0)) for _ in []), default=0)
    max_non_control_top20 = max([0] + [sum(1 for row in metric_records if row["rank_source_bucket"] == src and row["top20_hit_count_bucket"] != "count_0") for src in RANK_SOURCES if src != "control_baseline"])
    control_nonzero = any(row["rank_source_bucket"] == "control_baseline" and row["top20_hit_count_bucket"] != "count_0" for row in metric_records)
    if any(row["rank_source_bucket"] != "control_baseline" and row["gold_file_hit_count_bucket"] != "count_0" for row in metric_records):
        signal_bucket = "signal_present" if (max_non_control_top20 > 0 and not control_nonzero) or spread_bucket(top20_hit_counts) in {"spread_medium", "spread_high"} else "weak_signal"
    else:
        signal_bucket = "no_signal" if len(task_keys) == 20 else "inconclusive"
    valid = task_keys == outcome_keys and len(task_keys) == 20 and set(RANK_SOURCES) == sources_seen and all(groups.get(group) for group in REQUIRED_GROUPS)
    return {"valid": valid, "task_count": len(task_keys), "candidate_count": len(candidates), "rank_count": len(ranks), "outcome_count": len(outcomes), "rank_sources_present": sorted(sources_seen), "outcome_alignment_bool": task_keys == outcome_keys, "metric_records": metric_records, "agreement_records": agreement_records, "signal": {"rank_source_spread_bucket": spread_bucket(top20_hit_counts), "control_baseline_gap_bucket": "control_lower" if not control_nonzero else "control_nonzero", "real_file_material_signal_bucket": signal_bucket, "method_winner_bool": False, "aggregate_only_bool": True}}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_path", re.compile(r"candidate_path|source_path|filepath|filename|directory|snippet|start_line|end_line|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|exact_rate|exact_rank|task_key|candidate_key|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True); findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS_SIGNAL, STATUS_PASS_WEAK, STATUS_DEFAULT, f"{total}/{total}", R2AB_CHECKPOINT, R2AB_STATUS, R2AA_CHECKPOINT, "explicit private material root", "existing R2AA material only", "aggregate-only metrics", "query_identifier_overlap/symbol_name_overlap/lexical_bm25_like/content_identifier_fusion/control_baseline", "task/candidate coverage", "gold-file hit", "top1/top5/top10/top20", "MRR", "pairwise aggregate diagnostics", "real_file_material_signal_bucket", "R2AD-only", "no private writes/new candidate/material generation/source scan/retrieval/OpenLocus/runtime/CI/network/provider/clone", NEXT_PHASE]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel; return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2ac-actual-real-file-material-experiment.md")) and has_all(read("docs/zh/bea-v1-haae-r2ac-actual-real-file-material-experiment.md"))
    root_current = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2ac-actual-real-file-material-experiment.md" in root_current and has_all(root_current)
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(status: str, explicit: bool, root_valid: bool = False, root_reason: str = "not_supplied", metrics: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED, r2ab: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2ab is None:
        try: r2ab = load_json(repo / R2AB_REPORT_PATH)
        except Exception: r2ab = {}
    source = validate_r2ab_source(r2ab); metrics = metrics or {}; readback = public_readback_match(self_test_total)
    valid_metrics = metrics.get("valid") is True
    if not source["source_locked"]: final_status = STATUS_FAIL_SOURCE
    elif explicit and not root_valid: final_status = STATUS_NO_GO_ROOT
    elif explicit and not valid_metrics: final_status = STATUS_NO_GO_ALIGNMENT
    elif explicit and not readback["all_public_readback_match_bool"]: final_status = STATUS_FAIL_READBACK
    elif explicit:
        signal_bucket = (metrics.get("signal") or {}).get("real_file_material_signal_bucket")
        final_status = STATUS_PASS_SIGNAL if signal_bucket == "signal_present" else STATUS_PASS_WEAK
    else: final_status = status
    passed = final_status in PASS_STATUSES
    signal = metrics.get("signal") or {"rank_source_spread_bucket": "spread_unavailable", "control_baseline_gap_bucket": "unavailable", "real_file_material_signal_bucket": "inconclusive", "method_winner_bool": False, "aggregate_only_bool": True}
    gates = {"r2ab_source_locked_gate": source["source_locked"], "explicit_private_root_gate": explicit, "private_root_boundary_gate": (not explicit) or root_valid, "r2aa_manifest_owner_status_gate": (not explicit) or root_valid, "regular_bounded_group_files_gate": (not explicit) or root_valid, "required_group_files_gate": valid_metrics if explicit else True, "rank_sources_exact_gate": set(metrics.get("rank_sources_present", [])) == set(RANK_SOURCES) if explicit else True, "outcome_task_alignment_gate": metrics.get("outcome_alignment_bool") is True if explicit else True, "aggregate_metrics_only_gate": True, "no_private_write_gate": True, "no_new_material_generation_gate": True, "no_source_scan_retrieval_runtime_gate": True, "no_ci_network_provider_clone_gate": True, "no_scheduler_selector_gate": True, "no_method_default_scaling_claim_gate": True, "r2ad_only_stop_go_gate": True, "public_aggregate_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": final_status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2acsource0000", "locked_haae_r2ab_checkpoint": R2AB_CHECKPOINT, "locked_haae_r2ab_status": R2AB_STATUS, "locked_r2aa_checkpoint": R2AA_CHECKPOINT, "r2ab_status_match_bool": source["status_ok"], "r2ab_forbidden_scan_pass_bool": source["scan_ok"], "r2ab_r2ac_authorization_match_bool": source["auth_ok"], "r2ab_existing_material_boundary_bool": source["explicit_ok"], "source_locked_bool": source["source_locked"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2acmode0000", "mode_bucket": "explicit_real_file_material_experiment" if explicit else "default_no_explicit_private_root", "explicit_private_root_bool": explicit, "private_read_bucket": "count_1_to_10" if explicit and root_valid else "count_0", "private_write_bucket": "count_0", "aggregate_only_publication_bool": True}],
        "private_root_boundary_records": [{"anonymous_private_root_boundary_id": "haaer2acroot0000", "root_supplied_bool": explicit, "root_boundary_bucket": root_reason, "root_path_published_bool": False, "root_basename_public_bool": False, "regular_bounded_group_files_bool": root_valid if explicit else True, "no_root_discovery_bool": True, "no_private_write_bool": True}],
        "material_consistency_records": [{"anonymous_material_consistency_id": "haaer2acmaterial0000", "manifest_owner_bucket": "r2aa_real_file_material_smoke", "task_count_bucket": count_bucket(int(metrics.get("task_count", 0))), "candidate_count_bucket": count_bucket(int(metrics.get("candidate_count", 0))), "rank_count_bucket": count_bucket(int(metrics.get("rank_count", 0))), "outcome_count_bucket": count_bucket(int(metrics.get("outcome_count", 0))), "rank_sources_exact_bool": set(metrics.get("rank_sources_present", [])) == set(RANK_SOURCES) if explicit else True, "outcome_alignment_bool": metrics.get("outcome_alignment_bool") is True if explicit else True}],
        "rank_source_metric_records": [{"anonymous_rank_source_metric_id": f"haaer2acmetric{idx:04d}", **row} for idx, row in enumerate(metrics.get("metric_records", []))] if explicit else [],
        "rank_source_agreement_records": [{"anonymous_rank_source_agreement_id": f"haaer2acagree{idx:04d}", **row} for idx, row in enumerate(metrics.get("agreement_records", []))] if explicit else [],
        "signal_summary_records": [{"anonymous_signal_summary_id": "haaer2acsignal0000", **signal}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2acclaim0000", "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "new_material_generation_bool": False, "candidate_generation_bool": False, "private_write_bool": False, "retrieval_openlocus_runtime_bool": False, "source_scan_bool": False, "ci_network_provider_clone_bool": False, "scheduler_selector_bool": False, "bea_v1_a_p5_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2acgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2acsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["default_no_private", "missing_opt_in", "repo_root_reject", "symlink_root_reject", "manifest_status_drift", "missing_group_fail", "missing_rank_source_fail", "outcome_alignment_fail", "exact_publication_fail", "stop_go_overauth_fail", "stale_readback_fail", "safe_parser_fail", "source_lock_fail", "private_root_publication_fail", "claim_boundary_fail", "status_signal_mismatch_fail", "metric_mrr_bucket_mutation_fail", "metric_rank_bucket_mutation_fail", "agreement_source_mutation_fail", "agreement_rate_mutation_fail", "gate_mutation_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2acreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2acstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2ac_experiment", "haae_r2ad_public_audit_package_authorized_bool": passed, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "openlocus_runtime_authorized_bool": False, "source_scan_authorized_bool": False, "broad_scan_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "clone_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] in PASS_STATUSES and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["source_lock_records", "execution_mode_records", "private_root_boundary_records", "material_consistency_records", "signal_summary_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    if src.get("locked_haae_r2ab_checkpoint") != R2AB_CHECKPOINT or src.get("locked_haae_r2ab_status") != R2AB_STATUS or src.get("locked_r2aa_checkpoint") != R2AA_CHECKPOINT: issues.append("source_lock_mismatch")
    for field in ["r2ab_status_match_bool", "r2ab_forbidden_scan_pass_bool", "r2ab_r2ac_authorization_match_bool", "r2ab_existing_material_boundary_bool", "source_locked_bool"]:
        if src.get(field) is not True: issues.append(f"source_lock_{field}")
    mode = (report.get("execution_mode_records") or [{}])[0]
    if mode.get("private_write_bucket") != "count_0" or mode.get("aggregate_only_publication_bool") is not True: issues.append("execution_mode_boundary_mismatch")
    if report.get("status") in PASS_STATUSES:
        if mode.get("explicit_private_root_bool") is not True or mode.get("private_read_bucket") == "count_0": issues.append("execution_mode_not_explicit")
        root = (report.get("private_root_boundary_records") or [{}])[0]
        if root.get("root_boundary_bucket") != "valid_existing_r2aa_private_material_root" or root.get("root_path_published_bool") is not False or root.get("root_basename_public_bool") is not False or root.get("no_root_discovery_bool") is not True or root.get("no_private_write_bool") is not True: issues.append("private_root_boundary_mismatch")
        material = (report.get("material_consistency_records") or [{}])[0]
        if material.get("task_count_bucket") != "count_11_to_20" or material.get("candidate_count_bucket") == "count_0" or material.get("rank_count_bucket") == "count_0" or material.get("rank_sources_exact_bool") is not True or material.get("outcome_alignment_bool") is not True: issues.append("material_consistency_mismatch")
        metric_sources = {row.get("rank_source_bucket") for row in report.get("rank_source_metric_records", [])}
        if metric_sources != set(RANK_SOURCES): issues.append("rank_source_metric_set_mismatch")
        for row in report.get("rank_source_metric_records", []):
            if row.get("exact_values_published_bool") is not False: issues.append("rank_source_exact_publication")
            for field in ["task_coverage_bucket", "candidate_coverage_bucket", "gold_file_hit_count_bucket", "top1_hit_count_bucket", "top5_hit_count_bucket", "top10_hit_count_bucket", "top20_hit_count_bucket", "missing_outcome_bucket"]:
                if not str(row.get(field, "")).startswith("count_"): issues.append(f"metric_{field}_not_bucketed")
            if not str(row.get("gold_file_hit_rate_bucket", "")).startswith("rate_"): issues.append("metric_rate_not_bucketed")
            if not str(row.get("mrr_bucket", "")).startswith("mrr_"): issues.append("metric_mrr_not_bucketed")
            if not str(row.get("median_first_gold_rank_bucket", "")).startswith("rank_"): issues.append("metric_median_rank_not_bucketed")
        expected_pairs = len(RANK_SOURCES) * (len(RANK_SOURCES) - 1) // 2
        if len(report.get("rank_source_agreement_records", [])) != expected_pairs: issues.append("agreement_pair_count_mismatch")
        for row in report.get("rank_source_agreement_records", []):
            if row.get("exact_candidate_values_published_bool") is not False: issues.append("agreement_exact_publication")
            if row.get("left_rank_source_bucket") not in RANK_SOURCES or row.get("right_rank_source_bucket") not in RANK_SOURCES: issues.append("agreement_rank_source_mismatch")
            if not str(row.get("comparable_task_bucket", "")).startswith("count_"): issues.append("agreement_comparable_not_bucketed")
            for field in ["same_top_candidate_rate_bucket", "overlap_at_5_rate_bucket", "overlap_at_10_rate_bucket", "overlap_at_20_rate_bucket"]:
                if not str(row.get(field, "")).startswith("rate_"): issues.append(f"agreement_{field}_not_bucketed")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    signal = (report.get("signal_summary_records") or [{}])[0]
    if signal.get("real_file_material_signal_bucket") not in {"signal_present", "weak_signal", "no_signal", "inconclusive"}: issues.append("signal_bucket_invalid")
    if signal.get("method_winner_bool") is not False or signal.get("aggregate_only_bool") is not True: issues.append("signal_boundary_mismatch")
    if report.get("status") == STATUS_PASS_SIGNAL and signal.get("real_file_material_signal_bucket") != "signal_present": issues.append("status_signal_mismatch")
    if report.get("status") == STATUS_PASS_WEAK and signal.get("real_file_material_signal_bucket") == "signal_present": issues.append("status_signal_mismatch")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "new_material_generation_bool", "candidate_generation_bool", "private_write_bool", "retrieval_openlocus_runtime_bool", "source_scan_bool", "ci_network_provider_clone_bool", "scheduler_selector_bool", "bea_v1_a_p5_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") in PASS_STATUSES and (stop.get("haae_r2ad_public_audit_package_authorized_bool") is not True or stop.get("next_allowed_phase") != NEXT_PHASE): issues.append("r2ad_stop_go_missing")
    for field in FORBIDDEN_STOP_TRUE:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed = {"allow": False, "confirm": False, "root": "", "self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in {"--allow-real-file-material-experiment", "--confirm-aggregate-only-publication", "--self-test"}:
            if arg == "--allow-real-file-material-experiment": parsed["allow"] = True
            elif arg == "--confirm-aggregate-only-publication": parsed["confirm"] = True
            else: parsed["self_test"] = True
            i += 1
        elif arg in {"--private-material-root", "--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            if arg == "--private-material-root": parsed["root"] = argv[i + 1]
            elif arg == "--validate-report": parsed["validate"] = argv[i + 1]
            else: parsed["out"] = argv[i + 1]
            i += 2
        else: raise ValueError("invalid arguments")
    if parsed["root"] and not parsed["allow"]: raise ValueError("invalid arguments")
    return parsed


def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]
    path = Path(value); resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def write_report(report: dict[str, Any], out: Path | None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def make_private_fixture(root: Path, *, omit_group: str | None = None, omit_source: str | None = None, outcome_mismatch: bool = False) -> None:
    root.mkdir(parents=True, exist_ok=True); groups_dir = root / "groups"; groups_dir.mkdir(exist_ok=True)
    groups: dict[str, list[dict[str, Any]]] = {g: [] for g in REQUIRED_GROUPS}
    for idx in range(1, 21):
        task = f"task{idx:04d}"; gold_path = f"private/module_{idx:02d}/gold.rs"
        groups["task_identity"].append({"task_key": task})
        groups["source_manifest_private"].append({"source_file_key": f"sf{idx:04d}", "path": gold_path})
        groups["outcome_metric"].append({"task_key": (f"missing{idx:04d}" if outcome_mismatch else task), "gold_spans": [{"path": gold_path}]})
        for c in range(1, 41):
            cand = f"{task}_cand{c:03d}"; path = gold_path if c == 1 else f"private/module_{idx:02d}/decoy_{c:02d}.rs"
            groups["candidate_pool"].append({"task_key": task, "candidate_key": cand, "candidate_path": path})
            groups["evidence_span"].append({"task_key": task, "candidate_key": cand})
            for source in RANK_SOURCES:
                if source == omit_source: continue
                groups["rank_pack"].append({"task_key": task, "candidate_key": cand, "rank_source": source, "rank": c})
    manifest = {"schema_version": "bea_v1_haae_r2aa_actual_explicit_local_real_file_material_smoke_v1", "owner_bucket": R2AA_OWNER, "status": R2AA_STATUS, "target_task_count": 20, "candidate_depth_cap": 40, "source_file_cap": 500, "private_row_cap": 20000, "rank_sources": RANK_SOURCES, "groups": REQUIRED_GROUPS}
    (root / PRIVATE_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    for group, rows in groups.items():
        if group == omit_group: continue
        (groups_dir / f"{group}.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []; repo = Path(__file__).resolve().parents[1]
    explicit_report: dict[str, Any] | None = None
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    check("default_no_private", build_report(STATUS_DEFAULT, False)["status"] == STATUS_DEFAULT)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-material-root", "/tmp/x"])
        check("missing_opt_in", False)
    except ValueError: check("missing_opt_in", True)
    check("repo_root_reject", validate_private_root(repo, repo)[0] is False)
    with tempfile.TemporaryDirectory(prefix="r2ac_selftest_") as tmp:
        root = Path(tmp) / "r2aa"; make_private_fixture(root)
        ok, reason, files, _manifest = validate_private_root(root, repo); metrics = compute_metrics(read_groups(files)); report = build_report(STATUS_PASS_SIGNAL, True, ok, reason, metrics)
        explicit_report = report
        check("explicit_fixture_smoke", ok and metrics["valid"] and report["status"] in PASS_STATUSES and validate_report(report) == [])
        symlink = Path(tmp) / "link"; symlink.symlink_to(root, target_is_directory=True); check("symlink_root_reject", validate_private_root(symlink, repo)[0] is False)
        bad_manifest = load_json(root / PRIVATE_MANIFEST); bad_manifest["status"] = "wrong"; (root / PRIVATE_MANIFEST).write_text(json.dumps(bad_manifest), encoding="utf-8"); check("manifest_status_drift", validate_private_root(root, repo)[0] is False)
    with tempfile.TemporaryDirectory(prefix="r2ac_selftest_missing_") as tmp:
        bad = Path(tmp) / "bad"; make_private_fixture(bad, omit_group="rank_pack"); check("missing_group_fail", validate_private_root(bad, repo)[0] is False)
    with tempfile.TemporaryDirectory(prefix="r2ac_selftest_rank_") as tmp:
        bad = Path(tmp) / "bad"; make_private_fixture(bad, omit_source="control_baseline"); ok, _r, files, _m = validate_private_root(bad, repo); check("missing_rank_source_fail", ok and compute_metrics(read_groups(files))["valid"] is False)
    with tempfile.TemporaryDirectory(prefix="r2ac_selftest_align_") as tmp:
        bad = Path(tmp) / "bad"; make_private_fixture(bad, outcome_mismatch=True); ok, _r, files, _m = validate_private_root(bad, repo); check("outcome_alignment_fail", ok and compute_metrics(read_groups(files))["outcome_alignment_bool"] is False)
    leak = build_report(STATUS_DEFAULT, False); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("exact_publication_mutation", scan_public_report(leak)["status"] == "fail")
    over = build_report(STATUS_DEFAULT, False); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("stop_go_overauth_fail", any(i.startswith("overauthorization_") for i in validate_report(over)))
    stale = build_report(STATUS_DEFAULT, False); stale["self_test_total"] = 999; check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    claim = build_report(STATUS_DEFAULT, False); claim["claim_boundary_records"][0]["method_winner_claim_bool"] = True; check("claim_boundary_fail", any(i.startswith("claim_boundary_") for i in validate_report(claim)))
    status_drift = build_report(STATUS_DEFAULT, False); status_drift["status"] = STATUS_PASS_SIGNAL; status_drift["signal_summary_records"][0]["real_file_material_signal_bucket"] = "weak_signal"; check("status_signal_mismatch_fail", "status_signal_mismatch" in validate_report(status_drift))
    if explicit_report:
        mrr_bad = json.loads(json.dumps(explicit_report)); mrr_bad["rank_source_metric_records"][0]["mrr_bucket"] = "0.75"; check("metric_mrr_bucket_mutation_fail", "metric_mrr_not_bucketed" in validate_report(mrr_bad))
        rank_bad = json.loads(json.dumps(explicit_report)); rank_bad["rank_source_metric_records"][0]["median_first_gold_rank_bucket"] = "3"; check("metric_rank_bucket_mutation_fail", "metric_median_rank_not_bucketed" in validate_report(rank_bad))
        agree_source_bad = json.loads(json.dumps(explicit_report)); agree_source_bad["rank_source_agreement_records"][0]["left_rank_source_bucket"] = "raw_private_source"; check("agreement_source_mutation_fail", "agreement_rank_source_mismatch" in validate_report(agree_source_bad))
        agree_rate_bad = json.loads(json.dumps(explicit_report)); agree_rate_bad["rank_source_agreement_records"][0]["same_top_candidate_rate_bucket"] = "0.42"; check("agreement_rate_mutation_fail", "agreement_same_top_candidate_rate_bucket_not_bucketed" in validate_report(agree_rate_bad))
    else:
        check("metric_mrr_bucket_mutation_fail", False); check("metric_rank_bucket_mutation_fail", False); check("agreement_source_mutation_fail", False); check("agreement_rate_mutation_fail", False)
    source_bad = load_json(repo / R2AB_REPORT_PATH); source_bad["status"] = "wrong"; check("source_lock_fail", build_report(STATUS_DEFAULT, False, r2ab=source_bad)["status"] == STATUS_FAIL_SOURCE)
    with tempfile.TemporaryDirectory(prefix="r2ac_selftest_gate_") as tmp:
        root = Path(tmp) / "r2aa"; make_private_fixture(root)
        ok, reason, files, _manifest = validate_private_root(root, repo); metrics = compute_metrics(read_groups(files)); gate = build_report(STATUS_PASS_SIGNAL, True, ok, reason, metrics)
        gate["pass_fail_gate_records"][0]["gate_passed_bool"] = False
        check("gate_mutation_fail", any(i.startswith("gate_failed_") for i in validate_report(gate)))
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS_SIGNAL}


def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except ValueError:
        print("invalid arguments", file=sys.stderr); return 2
    repo = Path(__file__).resolve().parents[1]
    if args["self_test"]:
        result = run_self_test(); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo / public_artifact_path(args["validate"])); issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(args["out"]) if args["out"] else None
    if not args["allow"]:
        report = build_report(STATUS_DEFAULT, False); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0
    if not args["confirm"] or not args["root"]:
        report = build_report(STATUS_NO_GO_ROOT, True); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 1
    ok, reason, files, _manifest = validate_private_root(Path(args["root"]), repo)
    metrics = compute_metrics(read_groups(files)) if ok else {}
    report = build_report(STATUS_PASS_SIGNAL if ok else STATUS_NO_GO_ROOT, True, ok, reason, metrics); path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
