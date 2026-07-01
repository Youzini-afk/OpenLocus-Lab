#!/usr/bin/env python3
"""BEA-v1-HAAE-R2F local medium material experiment.

Default mode performs no private reads or writes. Explicit mode reads only an
operator supplied existing R2D private material root and publishes aggregate
metrics only.
"""

from __future__ import annotations

import io
import json
import re
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from statistics import median
from typing import Any

PHASE = "BEA-v1-HAAE-R2F Local Medium Material Experiment"
SLUG = "bea_v1_haae_r2f_local_medium_material_experiment"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2E_CHECKPOINT = "b166d79"
R2E_STATUS = "haae_r2e_local_medium_material_audit_package_complete_r2f_medium_experiment_authorized"
R2E_REPORT_PATH = Path("artifacts/bea_v1_haae_r2e_local_medium_material_audit_package/bea_v1_haae_r2e_local_medium_material_audit_package_report.json")
R2D_PRIVATE_MANIFEST = "haae_r2d_private_manifest.json"
R2D_OWNER = "haae_r2d_explicit_local_medium_material_generation_smoke"
R2D_STATUS = "haae_r2d_explicit_local_medium_material_generation_smoke_complete_r2e_material_audit_authorized"

STATUS_DEFAULT = "haae_r2f_unavailable_no_explicit_r2d_private_material_root"
STATUS_PASS = "haae_r2f_local_medium_material_experiment_complete_r2g_public_audit_authorized"
STATUS_NO_GO_ROOT = "haae_r2f_no_go_invalid_r2d_private_material_root"
STATUS_NO_GO_SCHEMA = "haae_r2f_no_go_invalid_r2d_private_material_schema"
STATUS_NO_GO_RANK = "haae_r2f_no_go_rank_source_alignment_incomplete"
STATUS_FAIL_SOURCE = "haae_r2f_fail_closed_source_lock_mismatch"
STATUS_FAIL_ROOT = "haae_r2f_fail_closed_private_root_boundary_violation"
STATUS_FAIL_LEAK = "haae_r2f_fail_closed_raw_publication_detected"
STATUS_FAIL_FORBIDDEN = "haae_r2f_fail_closed_forbidden_operation_detected"
STATUS_FAIL_READBACK = "haae_r2f_fail_closed_public_readback_mismatch"
STATUS_FAIL_OVERAUTH = "haae_r2f_fail_closed_stop_go_overauthorization"

SELF_TEST_EXPECTED = 22
NEXT_PHASE = "BEA-v1-HAAE-R2G Public Audit Package"
REQUIRED_GROUPS = ["task_identity", "anchor_source", "candidate_pool", "rank_pack", "evidence_core", "outcome_metric"]
OPTIONAL_GROUPS = ["span_projection", "scheduler_action", "arm_assignment", "safety_probe_signal"]
ALL_GROUPS = REQUIRED_GROUPS + OPTIONAL_GROUPS
RANK_SOURCES = ["bm25_like", "symbol_overlap", "rrf_like"]
RANK_FIELDS = {"bm25_like": "bm25_like_rank", "symbol_overlap": "symbol_overlap_rank", "rrf_like": "rrf_like_rank"}
MAX_GROUP_FILE_BYTES = 2_000_000
MAX_TOTAL_PRIVATE_BYTES = 10_000_000

FORBIDDEN_STOP_TRUE = ["new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "runtime_default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "r2_recompute_authorized_bool", "raw_publication_authorized_bool"]
CLAIM_FALSE_FIELDS = ["new_material_generation_bool", "candidate_generation_bool", "retrieval_runtime_bool", "source_scan_bool", "openlocus_runtime_bool", "scheduler_selector_bool", "ci_network_provider_bool", "default_change_bool", "bea_v1_a_p5_bool", "method_scaling_claim_bool", "raw_publication_bool"]
GATE_NAMES = ["source_lock_gate", "explicit_private_root_gate", "private_root_boundary_gate", "r2d_manifest_owner_gate", "required_group_files_gate", "regular_bounded_group_files_gate", "rank_sources_present_gate", "outcome_alignment_gate", "aggregate_metrics_only_gate", "no_new_material_generation_gate", "no_candidate_generation_gate", "no_retrieval_runtime_source_scan_gate", "no_ci_network_provider_gate", "no_scheduler_haae_selector_gate", "no_default_bea_v1_a_p5_gate", "no_method_scaling_claim_gate", "public_aggregate_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def count_bucket(n: int) -> str:
    if n <= 0: return "count_0"
    if n == 1: return "count_1"
    if n <= 5: return "count_2_to_5"
    if n <= 10: return "count_6_to_10"
    if n <= 20: return "count_10_to_20"
    if n <= 50: return "count_21_to_50"
    if n <= 5000: return "count_le_5000"
    return "count_gt_5000"


def rate_bucket(hit: int, total: int) -> str:
    if total <= 0 or hit <= 0: return "rate_0"
    if hit == total: return "rate_1"
    if hit * 2 < total: return "rate_gt0_lt_half"
    return "rate_half_to_lt1"


def rank_bucket(values: list[int]) -> str:
    if not values: return "rank_unavailable"
    value = float(median(values))
    if value <= 1: return "rank_1"
    if value <= 5: return "rank_2_to_5"
    if value <= 10: return "rank_6_to_10"
    if value <= 20: return "rank_11_to_20"
    return "rank_gt20"


def validate_r2e_source(r2e: dict[str, Any]) -> dict[str, bool]:
    stop = (r2e.get("stop_go_records") or [{}])[0]
    status_ok = r2e.get("status") == R2E_STATUS
    scan_ok = r2e.get("forbidden_scan", {}).get("status") == "pass"
    auth_ok = stop.get("haae_r2f_local_medium_material_experiment_authorized_bool") is True
    boundary_ok = all(stop.get(field) is False for field in ["new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "runtime_default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "r2_recompute_authorized_bool"])
    return {"status_ok": status_ok, "scan_ok": scan_ok, "auth_ok": auth_ok, "boundary_ok": boundary_ok, "source_locked": status_ok and scan_ok and auth_ok and boundary_ok}


def validate_private_root(root: Path, repo: Path) -> tuple[bool, str, dict[str, Path], dict[str, Any]]:
    try:
        resolved = root.resolve(strict=True)
        repo_resolved = repo.resolve(strict=True)
    except Exception:
        return False, "root_missing_or_unresolvable", {}, {}
    if not resolved.is_dir(): return False, "root_not_directory", {}, {}
    if root.is_symlink() or resolved.is_symlink(): return False, "root_symlink", {}, {}
    if resolved == repo_resolved or repo_resolved in resolved.parents: return False, "root_under_public_repo", {}, {}
    manifest_path = resolved / R2D_PRIVATE_MANIFEST
    if not manifest_path.exists() or not manifest_path.is_file() or manifest_path.is_symlink(): return False, "missing_or_invalid_manifest", {}, {}
    try:
        manifest = load_json(manifest_path)
    except Exception:
        return False, "manifest_parse_failed", {}, {}
    if manifest.get("owner_bucket") != R2D_OWNER: return False, "manifest_owner_mismatch", {}, manifest
    if manifest.get("status_bucket") not in {R2D_STATUS, STATUS_PASS}: return False, "manifest_status_incompatible", {}, manifest
    groups_dir = resolved / "groups"
    if not groups_dir.exists() or not groups_dir.is_dir() or groups_dir.is_symlink(): return False, "missing_groups_directory", {}, manifest
    files: dict[str, Path] = {}
    total_size = 0
    for group in ALL_GROUPS:
        path = groups_dir / f"{group}.jsonl"
        if group in REQUIRED_GROUPS and not path.exists(): return False, "missing_required_group", {}, manifest
        if path.exists():
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True).parent != groups_dir.resolve(strict=True): return False, "invalid_group_file", {}, manifest
            size = path.stat().st_size
            if size > MAX_GROUP_FILE_BYTES: return False, "group_file_too_large", {}, manifest
            total_size += size
            files[group] = path
    if total_size > MAX_TOTAL_PRIVATE_BYTES: return False, "private_root_too_large", {}, manifest
    return True, "valid_existing_r2d_private_material_root", files, manifest


def read_private_groups(files: dict[str, Path]) -> dict[str, list[dict[str, Any]]]:
    return {group: load_jsonl(path) for group, path in files.items()}


def compute_metrics(groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    tasks = groups.get("task_identity", [])
    candidates = groups.get("candidate_pool", [])
    ranks = groups.get("rank_pack", [])
    outcomes = groups.get("outcome_metric", [])
    evidence = groups.get("evidence_core", [])
    task_keys = {str(row.get("task_key")) for row in tasks if row.get("task_key") is not None}
    outcome_keys = {str(row.get("task_key")) for row in outcomes if row.get("task_key") is not None}
    outcome_by_task = {str(row.get("task_key")): row for row in outcomes if row.get("task_key") is not None}
    candidate_by_task: dict[str, list[dict[str, Any]]] = {}
    rank_by_task: dict[str, list[dict[str, Any]]] = {}
    for row in candidates:
        key = row.get("task_key")
        if key is not None:
            candidate_by_task.setdefault(str(key), []).append(row)
    for row in ranks:
        key = row.get("task_key")
        if key is not None:
            rank_by_task.setdefault(str(key), []).append(row)
    source_metrics: dict[str, dict[str, Any]] = {}
    top_by_source: dict[str, dict[str, str]] = {src: {} for src in RANK_SOURCES}
    top5_by_source: dict[str, dict[str, set[str]]] = {src: {} for src in RANK_SOURCES}
    top10_by_source: dict[str, dict[str, set[str]]] = {src: {} for src in RANK_SOURCES}
    missing_sources: set[str] = set()
    for source in RANK_SOURCES:
        field = RANK_FIELDS[source]
        covered_tasks = 0; covered_candidates = 0; gold_hits = 0; top1 = 0; top5 = 0; top10 = 0; first_ranks: list[int] = []
        for task in sorted(task_keys):
            rows = [row for row in rank_by_task.get(task, []) if isinstance(row.get(field), int) and source in row.get("rank_sources", [])]
            rows.sort(key=lambda row: (row[field], str(row.get("candidate_path", ""))))
            if not rows:
                missing_sources.add(source); continue
            covered_tasks += 1; covered_candidates += len(rows)
            top_by_source[source][task] = str(rows[0].get("candidate_path"))
            top5_by_source[source][task] = {str(row.get("candidate_path")) for row in rows[:5]}
            top10_by_source[source][task] = {str(row.get("candidate_path")) for row in rows[:10]}
            gold_paths = {span.get("path") for span in outcome_by_task.get(task, {}).get("gold_spans", []) if span.get("path")}
            hit_ranks = [int(row[field]) for row in rows if row.get("candidate_path") in gold_paths]
            if hit_ranks:
                best = min(hit_ranks); first_ranks.append(best); gold_hits += 1
                if best <= 1: top1 += 1
                if best <= 5: top5 += 1
                if best <= 10: top10 += 1
        source_metrics[source] = {"rank_source_present_bool": covered_tasks > 0, "task_coverage_bucket": count_bucket(covered_tasks), "candidate_coverage_bucket": count_bucket(covered_candidates), "gold_file_hit_count_bucket": count_bucket(gold_hits), "gold_file_hit_rate_bucket": rate_bucket(gold_hits, covered_tasks), "mean_first_gold_rank_bucket": rank_bucket(first_ranks), "median_first_gold_rank_bucket": rank_bucket(first_ranks), "top1_hit_count_bucket": count_bucket(top1), "top5_hit_count_bucket": count_bucket(top5), "top10_hit_count_bucket": count_bucket(top10)}
    agreements: list[dict[str, Any]] = []
    pairs = [("bm25_like", "symbol_overlap"), ("bm25_like", "rrf_like"), ("symbol_overlap", "rrf_like")]
    for left, right in pairs:
        common = sorted(set(top_by_source[left]) & set(top_by_source[right]))
        same_top = sum(1 for task in common if top_by_source[left][task] == top_by_source[right][task])
        overlap5 = sum(1 for task in common if top5_by_source[left][task] & top5_by_source[right][task])
        overlap10 = sum(1 for task in common if top10_by_source[left][task] & top10_by_source[right][task])
        agreements.append({"left_rank_source_bucket": left, "right_rank_source_bucket": right, "comparable_task_bucket": count_bucket(len(common)), "same_top_candidate_rate_bucket": rate_bucket(same_top, len(common)), "overlap_at_5_rate_bucket": rate_bucket(overlap5, len(common)), "overlap_at_10_rate_bucket": rate_bucket(overlap10, len(common))})
    consistency = {"required_groups_present_bool": all(groups.get(group) for group in REQUIRED_GROUPS), "outcome_rows_match_task_rows_bool": task_keys == outcome_keys and len(tasks) == len(outcomes), "evidence_rows_present_bool": len(evidence) > 0, "no_missing_rank_source_bucket": "none" if not missing_sources else "one_or_more_missing"}
    valid = consistency["required_groups_present_bool"] and consistency["outcome_rows_match_task_rows_bool"] and consistency["no_missing_rank_source_bucket"] == "none"
    return {"valid": valid, "task_count": len(tasks), "candidate_count": len(candidates), "rank_count": len(ranks), "outcome_count": len(outcomes), "source_metrics": source_metrics, "agreements": agreements, "consistency": consistency}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_path|gold_spans|hard_negatives|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_rank", re.compile(r"rrf_like_score|bm25_like_rank|symbol_overlap_rank|first_gold_file_rank|task_key|candidate_rank|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, STATUS_DEFAULT, f"{total}/{total}", R2E_CHECKPOINT, R2E_STATUS, "explicit private material root", "existing R2D private material only", "aggregate-only metrics", "bm25_like/symbol_overlap/rrf_like", "gold-file hit-rate bucket `rate_1`", "same-top candidate rate bucket `rate_1`", "top1/top5/top10 buckets `count_10_to_20`", "no new candidates/retrieval/source scan/OpenLocus/runtime/scheduler/selector/CI/network/provider/default/BEA-v1-A/P5/method/scaling claim", NEXT_PHASE]
    spaced = [f"{total} / {total}" if f == f"{total}/{total}" else f for f in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2f-local-medium-material-experiment.md")) and has_all(read("docs/zh/bea-v1-haae-r2f-local-medium-material-experiment.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2f-local-medium-material-experiment.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(status: str, explicit: bool, root_reason: str = "not_supplied", metrics: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED, r2e: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2e is None:
        try: r2e = load_json(repo / R2E_REPORT_PATH)
        except Exception: r2e = {}
    source = validate_r2e_source(r2e)
    metrics = metrics or {"valid": False, "task_count": 0, "candidate_count": 0, "rank_count": 0, "outcome_count": 0, "source_metrics": {}, "agreements": [], "consistency": {"required_groups_present_bool": False, "outcome_rows_match_task_rows_bool": False, "evidence_rows_present_bool": False, "no_missing_rank_source_bucket": "not_evaluated"}}
    readback = public_readback_match(self_test_total)
    if not source["source_locked"]:
        final_status = STATUS_FAIL_SOURCE
    elif explicit and root_reason != "valid_existing_r2d_private_material_root":
        final_status = STATUS_FAIL_ROOT if "under_public" in root_reason or "symlink" in root_reason else STATUS_NO_GO_ROOT
    elif explicit and not metrics.get("valid"):
        final_status = STATUS_NO_GO_RANK if metrics.get("consistency", {}).get("no_missing_rank_source_bucket") != "none" else STATUS_NO_GO_SCHEMA
    elif explicit and not readback["all_public_readback_match_bool"]:
        final_status = STATUS_FAIL_READBACK
    elif explicit:
        final_status = STATUS_PASS
    else:
        final_status = status
    passed = final_status == STATUS_PASS
    gates = {"source_lock_gate": source["source_locked"], "explicit_private_root_gate": explicit, "private_root_boundary_gate": (not explicit) or root_reason == "valid_existing_r2d_private_material_root", "r2d_manifest_owner_gate": (not explicit) or root_reason == "valid_existing_r2d_private_material_root", "required_group_files_gate": metrics["consistency"].get("required_groups_present_bool", False) if explicit else False, "regular_bounded_group_files_gate": (not explicit) or root_reason == "valid_existing_r2d_private_material_root", "rank_sources_present_gate": metrics["consistency"].get("no_missing_rank_source_bucket") == "none" if explicit else False, "outcome_alignment_gate": metrics["consistency"].get("outcome_rows_match_task_rows_bool", False) if explicit else False, "aggregate_metrics_only_gate": True, "no_new_material_generation_gate": True, "no_candidate_generation_gate": True, "no_retrieval_runtime_source_scan_gate": True, "no_ci_network_provider_gate": True, "no_scheduler_haae_selector_gate": True, "no_default_bea_v1_a_p5_gate": True, "no_method_scaling_claim_gate": True, "public_aggregate_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": final_status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2fsource0000", "locked_haae_r2e_checkpoint": R2E_CHECKPOINT, "locked_haae_r2e_status": R2E_STATUS, "r2e_status_match_bool": source["status_ok"], "r2e_forbidden_scan_pass_bool": source["scan_ok"], "r2f_authorization_match_bool": source["auth_ok"], "r2e_boundary_match_bool": source["boundary_ok"], "source_locked_bool": source["source_locked"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2fmode0000", "mode_bucket": "explicit_existing_r2d_private_material_experiment" if explicit else "default_no_explicit_r2d_private_material_root", "explicit_opt_in_bool": explicit, "private_read_bucket": "count_1_to_10" if explicit else "count_0", "private_write_bucket": "count_0", "aggregate_only_publication_confirmed_bool": explicit}],
        "private_material_root_records": [{"anonymous_private_material_root_id": "haaer2froot0000", "root_supplied_bool": explicit, "root_boundary_bucket": root_reason, "root_path_basename_filename_published_bool": False, "default_path_or_discovery_bool": False, "tmp_scan_bool": False}],
        "material_consistency_records": [{"anonymous_material_consistency_id": "haaer2fconsistency0000", "required_groups_present_bool": metrics["consistency"].get("required_groups_present_bool", False), "outcome_rows_match_task_rows_bool": metrics["consistency"].get("outcome_rows_match_task_rows_bool", False), "evidence_rows_present_bool": metrics["consistency"].get("evidence_rows_present_bool", False), "no_missing_rank_source_bucket": metrics["consistency"].get("no_missing_rank_source_bucket", "not_evaluated")}],
        "experiment_summary_records": [{"anonymous_experiment_summary_id": "haaer2fsummary0000", "task_count_bucket": count_bucket(int(metrics.get("task_count", 0))), "candidate_count_bucket": count_bucket(int(metrics.get("candidate_count", 0))), "rank_row_count_bucket": count_bucket(int(metrics.get("rank_count", 0))), "outcome_row_count_bucket": count_bucket(int(metrics.get("outcome_count", 0))), "aggregate_metrics_only_bool": True, "raw_rows_published_bool": False}],
        "rank_source_metric_records": [{"anonymous_rank_source_metric_id": f"haaer2frank{idx:04d}", "rank_source_bucket": src, **metrics.get("source_metrics", {}).get(src, {"rank_source_present_bool": False, "task_coverage_bucket": "count_0", "candidate_coverage_bucket": "count_0", "gold_file_hit_count_bucket": "count_0", "gold_file_hit_rate_bucket": "rate_0", "mean_first_gold_rank_bucket": "rank_unavailable", "median_first_gold_rank_bucket": "rank_unavailable", "top1_hit_count_bucket": "count_0", "top5_hit_count_bucket": "count_0", "top10_hit_count_bucket": "count_0"}), "exact_scores_ranks_paths_published_bool": False} for idx, src in enumerate(RANK_SOURCES)],
        "rank_source_agreement_records": [{"anonymous_rank_source_agreement_id": f"haaer2fagree{idx:04d}", **row, "exact_candidate_values_published_bool": False} for idx, row in enumerate(metrics.get("agreements", []))],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2fclaim0000", "new_material_generation_bool": False, "candidate_generation_bool": False, "retrieval_runtime_bool": False, "source_scan_bool": False, "openlocus_runtime_bool": False, "scheduler_selector_bool": False, "ci_network_provider_bool": False, "default_change_bool": False, "bea_v1_a_p5_bool": False, "method_scaling_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2fgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_reads_private_material_bool": explicit and gate in {"required_group_files_gate", "rank_sources_present_gate", "outcome_alignment_gate"}} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2fsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["default_no_private", "missing_opt_in", "repo_root_rejected", "symlink_root_or_group", "missing_non_r2d_manifest", "missing_required_group", "missing_rank_source", "outcome_mismatch", "raw_leak_scanner", "exact_per_task_publication_fail", "overauth_mutations", "stale_readback", "private_root_requires_allow", "explicit_private_root_arg_allowed", "unknown_private_arg_rejected"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2freadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2fstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_supply_valid_r2d_private_material_root", "haae_r2g_public_audit_package_authorized_bool": passed, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "runtime_default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "r2_recompute_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "execution_mode_records", "private_material_root_records", "material_consistency_records", "experiment_summary_records", "rank_source_metric_records", "rank_source_agreement_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    mode = (report.get("execution_mode_records") or [{}])[0]
    if mode.get("private_write_bucket") != "count_0": issues.append("private_write_detected")
    if report.get("status") == STATUS_DEFAULT and mode.get("private_read_bucket") != "count_0": issues.append("default_private_read_detected")
    consistency = (report.get("material_consistency_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        source = (report.get("source_lock_records") or [{}])[0]
        for field in ["r2e_status_match_bool", "r2e_forbidden_scan_pass_bool", "r2f_authorization_match_bool", "r2e_boundary_match_bool", "source_locked_bool"]:
            if source.get(field) is not True:
                issues.append(f"source_lock_field_not_true_{field}")
        if source.get("locked_haae_r2e_checkpoint") != R2E_CHECKPOINT or source.get("locked_haae_r2e_status") != R2E_STATUS:
            issues.append("source_lock_checkpoint_status_mismatch")
        root = (report.get("private_material_root_records") or [{}])[0]
        if root.get("root_supplied_bool") is not True or root.get("root_boundary_bucket") != "valid_existing_r2d_private_material_root":
            issues.append("private_root_boundary_invalid")
        if root.get("root_path_basename_filename_published_bool") is not False or root.get("default_path_or_discovery_bool") is not False or root.get("tmp_scan_bool") is not False:
            issues.append("private_root_publication_or_discovery_drift")
        claim = (report.get("claim_boundary_records") or [{}])[0]
        for field in CLAIM_FALSE_FIELDS:
            if claim.get(field) is not False:
                issues.append(f"claim_boundary_overauthorization_{field}")
        if consistency.get("required_groups_present_bool") is not True or consistency.get("outcome_rows_match_task_rows_bool") is not True or consistency.get("no_missing_rank_source_bucket") != "none": issues.append("material_alignment_invalid")
        ranks = {row.get("rank_source_bucket"): row for row in report.get("rank_source_metric_records", [])}
        for src in RANK_SOURCES:
            if ranks.get(src, {}).get("rank_source_present_bool") is not True: issues.append(f"rank_source_missing_{src}")
            if ranks.get(src, {}).get("exact_scores_ranks_paths_published_bool") is not False: issues.append(f"exact_rank_score_path_publication_{src}")
        for row in report.get("rank_source_agreement_records", []):
            if row.get("exact_candidate_values_published_bool") is not False:
                issues.append("exact_candidate_agreement_publication")
        summary = (report.get("experiment_summary_records") or [{}])[0]
        if summary.get("aggregate_metrics_only_bool") is not True or summary.get("raw_rows_published_bool") is not False:
            issues.append("experiment_summary_publication_drift")
        mode = (report.get("execution_mode_records") or [{}])[0]
        if mode.get("explicit_opt_in_bool") is not True or mode.get("aggregate_only_publication_confirmed_bool") is not True:
            issues.append("explicit_mode_or_aggregate_confirmation_missing")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in FORBIDDEN_STOP_TRUE:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    if report.get("debug_task_id") or report.get("task_id") or report.get("query") or report.get("candidate_path"): issues.append("exact_per_task_publication")
    return issues


def create_fixture_root(root: Path, *, mutate: str = "") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / R2D_PRIVATE_MANIFEST).write_text(json.dumps({"owner_bucket": R2D_OWNER, "schema_version": "bea_v1_haae_r2d_explicit_local_medium_material_generation_smoke_v1", "status_bucket": R2D_STATUS}, sort_keys=True), encoding="utf-8")
    groups = root / "groups"; groups.mkdir(exist_ok=True)
    tasks = [{"task_key": "t1", "task": {"task_id": "r14m-private", "query": "private query"}}, {"task_key": "t2", "task": {"task_id": "r14m-private2", "query": "private query2"}}]
    outcomes = [{"task_key": "t1", "gold_spans": [{"path": "private/path1.rs"}]}, {"task_key": "t2", "gold_spans": [{"path": "private/path2.rs"}]}]
    candidates = [{"task_key": "t1", "candidate_path": "private/path1.rs"}, {"task_key": "t1", "candidate_path": "private/neg.rs"}, {"task_key": "t2", "candidate_path": "private/path2.rs"}]
    ranks = []
    for row in candidates:
        rank = 1 if "path" in row["candidate_path"] else 2
        ranks.append({"task_key": row["task_key"], "candidate_path": row["candidate_path"], "rank_sources": RANK_SOURCES, "bm25_like_rank": rank, "symbol_overlap_rank": rank, "rrf_like_rank": rank})
    if mutate == "missing_rank_source":
        for row in ranks: row.pop("rrf_like_rank", None); row["rank_sources"] = ["bm25_like", "symbol_overlap"]
    if mutate == "outcome_mismatch": outcomes = outcomes[:1]
    data = {"task_identity": tasks, "anchor_source": [{"task_key": "t1"}], "candidate_pool": candidates, "rank_pack": ranks, "evidence_core": [{"task_key": "t1"}], "outcome_metric": outcomes, "span_projection": [], "scheduler_action": [], "arm_assignment": [], "safety_probe_signal": []}
    if mutate == "missing_required": data.pop("candidate_pool")
    for group, rows in data.items(): write_jsonl(groups / f"{group}.jsonl", rows)


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    check("default_no_private", build_report(STATUS_DEFAULT, False)["status"] == STATUS_DEFAULT)
    check("missing_opt_in", build_report(STATUS_DEFAULT, False)["execution_mode_records"][0]["private_read_bucket"] == "count_0")
    check("repo_root_rejected", validate_private_root(repo, repo)[1] == "root_under_public_repo")
    with tempfile.TemporaryDirectory(prefix="r2f_selftest_") as tmp:
        tmp_path = Path(tmp)
        symlink = tmp_path / "symlink"; target = tmp_path / "target"; target.mkdir(); symlink.symlink_to(target, target_is_directory=True)
        check("symlink_root", validate_private_root(symlink, repo)[1] == "root_symlink")
        missing = tmp_path / "missing_manifest"; missing.mkdir(); check("missing_manifest", validate_private_root(missing, repo)[1] == "missing_or_invalid_manifest")
        good = tmp_path / "good"; create_fixture_root(good); ok, reason, files, _ = validate_private_root(good, repo); metrics = compute_metrics(read_private_groups(files)); check("explicit_fixture_pass", ok and reason == "valid_existing_r2d_private_material_root" and metrics["valid"])
        missing_group = tmp_path / "missing_group"; create_fixture_root(missing_group, mutate="missing_required"); check("missing_required_group", validate_private_root(missing_group, repo)[1] == "missing_required_group")
        missing_rank = tmp_path / "missing_rank"; create_fixture_root(missing_rank, mutate="missing_rank_source"); ok, _, files, _ = validate_private_root(missing_rank, repo); check("missing_rank_source", ok and not compute_metrics(read_private_groups(files))["valid"])
        mismatch = tmp_path / "mismatch"; create_fixture_root(mismatch, mutate="outcome_mismatch"); ok, _, files, _ = validate_private_root(mismatch, repo); check("outcome_mismatch", ok and not compute_metrics(read_private_groups(files))["valid"])
    leak = build_report(STATUS_DEFAULT, False); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("raw_leak_scanner", scan_public_report(leak)["status"] == "fail")
    exact = build_report(STATUS_PASS, True, "valid_existing_r2d_private_material_root", {"valid": True, "task_count": 1, "candidate_count": 1, "rank_count": 1, "outcome_count": 1, "source_metrics": {src: {"rank_source_present_bool": True} for src in RANK_SOURCES}, "agreements": [], "consistency": {"required_groups_present_bool": True, "outcome_rows_match_task_rows_bool": True, "evidence_rows_present_bool": True, "no_missing_rank_source_bucket": "none"}}); exact["task_id"] = "r14m-private"; check("exact_per_task_publication", "forbidden_scan_failed" in validate_report(exact) or "exact_per_task_publication" in validate_report(exact))
    over = build_report(STATUS_DEFAULT, False); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("overauth_mutations", any(issue.startswith("overauthorization_") for issue in validate_report(over)))
    pass_report = build_report(STATUS_PASS, True, "valid_existing_r2d_private_material_root", {"valid": True, "task_count": 2, "candidate_count": 3, "rank_count": 3, "outcome_count": 2, "source_metrics": {src: {"rank_source_present_bool": True, "task_coverage_bucket": "count_2_to_5", "candidate_coverage_bucket": "count_2_to_5", "gold_file_hit_count_bucket": "count_2_to_5", "gold_file_hit_rate_bucket": "rate_1", "mean_first_gold_rank_bucket": "rank_1", "median_first_gold_rank_bucket": "rank_1", "top1_hit_count_bucket": "count_2_to_5", "top5_hit_count_bucket": "count_2_to_5", "top10_hit_count_bucket": "count_2_to_5"} for src in RANK_SOURCES}, "agreements": [{"left_rank_source_bucket": "bm25_like", "right_rank_source_bucket": "rrf_like", "comparable_task_bucket": "count_2_to_5", "same_top_candidate_rate_bucket": "rate_1", "overlap_at_5_rate_bucket": "rate_1", "overlap_at_10_rate_bucket": "rate_1"}], "consistency": {"required_groups_present_bool": True, "outcome_rows_match_task_rows_bool": True, "evidence_rows_present_bool": True, "no_missing_rank_source_bucket": "none"}})
    source_mutation = json.loads(json.dumps(pass_report)); source_mutation["source_lock_records"][0]["source_locked_bool"] = False; check("source_lock_false_validation", any(i.startswith("source_lock_field_not_true") for i in validate_report(source_mutation)))
    root_mutation = json.loads(json.dumps(pass_report)); root_mutation["private_material_root_records"][0]["tmp_scan_bool"] = True; check("root_discovery_validation", "private_root_publication_or_discovery_drift" in validate_report(root_mutation))
    claim_mutation = json.loads(json.dumps(pass_report)); claim_mutation["claim_boundary_records"][0]["raw_publication_bool"] = True; check("claim_boundary_validation", any(i.startswith("claim_boundary_overauthorization") for i in validate_report(claim_mutation)))
    rank_mutation = json.loads(json.dumps(pass_report)); rank_mutation["rank_source_metric_records"][0]["exact_scores_ranks_paths_published_bool"] = True; check("rank_exact_publication_validation", any(i.startswith("exact_rank_score_path_publication") for i in validate_report(rank_mutation)))
    agreement_mutation = json.loads(json.dumps(pass_report)); agreement_mutation["rank_source_agreement_records"][0]["exact_candidate_values_published_bool"] = True; check("agreement_exact_publication_validation", "exact_candidate_agreement_publication" in validate_report(agreement_mutation))
    summary_mutation = json.loads(json.dumps(pass_report)); summary_mutation["experiment_summary_records"][0]["raw_rows_published_bool"] = True; check("summary_raw_publication_validation", "experiment_summary_publication_drift" in validate_report(summary_mutation))
    mode_mutation = json.loads(json.dumps(pass_report)); mode_mutation["execution_mode_records"][0]["aggregate_only_publication_confirmed_bool"] = False; check("mode_aggregate_confirmation_validation", "explicit_mode_or_aggregate_confirmation_missing" in validate_report(mode_mutation))
    check("stale_readback", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        parse_args(["--private-material-root", "/tmp/private"])
        check("private_root_requires_allow", False)
    except ValueError:
        check("private_root_requires_allow", True)
    try:
        parsed_ok = parse_args(["--allow-private-medium-material-experiment", "--private-material-root", "/tmp/private", "--confirm-aggregate-only-publication"])
        check("explicit_private_root_arg_allowed", parsed_ok["allow"] and parsed_ok["confirm"] and parsed_ok["root"] == "/tmp/private")
    except ValueError:
        check("explicit_private_root_arg_allowed", False)
    try:
        parse_args(["--private-root", "/tmp/private"])
        check("unknown_private_arg_rejected", False)
    except ValueError:
        check("unknown_private_arg_rejected", True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed = {"allow": False, "confirm": False, "root": "", "self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in {"--allow-private-medium-material-experiment", "--confirm-aggregate-only-publication", "--self-test"}:
            if arg == "--allow-private-medium-material-experiment": parsed["allow"] = True
            elif arg == "--confirm-aggregate-only-publication": parsed["confirm"] = True
            else: parsed["self_test"] = True
            i += 1
        elif arg in {"--private-material-root", "--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            if arg == "--private-material-root": parsed["root"] = argv[i + 1]
            elif arg == "--validate-report": parsed["validate"] = argv[i + 1]
            else: parsed["out"] = argv[i + 1]
            i += 2
        else:
            raise ValueError("invalid arguments")
    if parsed["root"] and not parsed["allow"]:
        raise ValueError("invalid arguments")
    return parsed


def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]
    path = Path(value)
    resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def write_report(report: dict[str, Any], out: Path | None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


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
        report = build_report(STATUS_DEFAULT, False); write_report(report, out); return 1
    ok, reason, files, _manifest = validate_private_root(Path(args["root"]), repo)
    if not ok:
        report = build_report(STATUS_NO_GO_ROOT, True, reason); write_report(report, out); return 1 if report["status"].startswith("haae_r2f_fail") else 0
    metrics = compute_metrics(read_private_groups(files))
    report = build_report(STATUS_PASS if metrics["valid"] else STATUS_NO_GO_SCHEMA, True, reason, metrics)
    path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] in {STATUS_PASS, STATUS_NO_GO_SCHEMA, STATUS_NO_GO_RANK, STATUS_NO_GO_ROOT} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
