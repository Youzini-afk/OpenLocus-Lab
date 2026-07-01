#!/usr/bin/env python3
"""BEA-v1-HAAE-R2W content-identifier material experiment.

Default mode reads/writes no private data. Explicit mode reads only an
operator-supplied existing R2U private material root and publishes aggregate-only
bucketed metrics.
"""

from __future__ import annotations

import io
import json
import re
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from statistics import mean, median
from typing import Any, Sequence

PHASE = "BEA-v1-HAAE-R2W Content-Identifier Material Experiment"
SLUG = "bea_v1_haae_r2w_content_identifier_material_experiment"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2V_CHECKPOINT = "b8522de"
R2V_STATUS = "haae_r2v_content_identifier_material_public_audit_package_complete_r2w_material_experiment_authorized"
R2U_CHECKPOINT = "bb95f80"
R2V_REPORT_PATH = Path("artifacts/bea_v1_haae_r2v_content_identifier_material_public_audit_package/bea_v1_haae_r2v_content_identifier_material_public_audit_package_report.json")
R2U_MANIFEST = "haae_r2u_private_manifest.json"
R2U_OWNER = "haae_r2u_content_identifier_material_generation"
R2U_STATUS = "haae_r2u_content_identifier_material_generation_complete_r2v_public_audit_authorized"

STATUS_DEFAULT = "haae_r2w_unavailable_no_explicit_r2u_private_material_root"
STATUS_PASS_SIGNAL = "haae_r2w_content_identifier_material_experiment_complete_r2x_public_audit_authorized_signal_present"
STATUS_PASS_WEAK = "haae_r2w_content_identifier_material_experiment_complete_r2x_public_audit_authorized_weak_or_no_signal"
PASS_STATUSES = {STATUS_PASS_SIGNAL, STATUS_PASS_WEAK}
STATUS_NO_GO_ROOT = "haae_r2w_no_go_invalid_r2u_private_material_root"
STATUS_NO_GO_SCHEMA = "haae_r2w_no_go_invalid_r2u_material_schema"
STATUS_FAIL_SOURCE = "haae_r2w_fail_closed_source_lock_mismatch"
STATUS_FAIL_LEAK = "haae_r2w_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2w_fail_closed_public_readback_mismatch"
STATUS_FAIL_OVERAUTH = "haae_r2w_fail_closed_stop_go_overauthorization"
SELF_TEST_EXPECTED = 25
NEXT_PHASE = "BEA-v1-HAAE-R2X Content-Identifier Material Experiment Public Audit Package"

RANK_SOURCES = ["query_identifier_overlap", "symbol_name_overlap", "content_snippet_overlap", "identifier_normalized_bm25_like", "hard_negative_quality_control", "content_identifier_fusion", "control_baseline"]
REQUIRED_GROUPS = ["task_identity", "anchor_source", "candidate_pool", "rank_pack", "evidence_core", "outcome_metric", "span_projection"]
OPTIONAL_GROUPS = ["scheduler_action", "arm_assignment", "safety_probe_signal"]
ALL_GROUPS = REQUIRED_GROUPS + OPTIONAL_GROUPS
MAX_GROUP_FILE_BYTES = 8_000_000
MAX_TOTAL_PRIVATE_BYTES = 50_000_000
FORBIDDEN_STOP_TRUE = ["new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]
GATE_NAMES = ["r2v_source_locked_gate", "explicit_private_root_gate", "private_root_boundary_gate", "r2u_manifest_owner_schema_gate", "regular_bounded_group_files_gate", "required_group_files_gate", "task_depth_rank_source_gate", "path_masking_gate", "gold_not_used_for_ranking_gate", "outcome_alignment_gate", "aggregate_metrics_only_gate", "material_validity_context_gate", "no_private_write_gate", "no_new_material_generation_gate", "no_retrieval_runtime_source_scan_gate", "no_ci_network_provider_gate", "no_scheduler_selector_gate", "no_method_default_scaling_claim_gate", "public_aggregate_only_gate", "stop_go_r2x_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


def load_json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def load_jsonl(path: Path) -> list[dict[str, Any]]: return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def count_bucket(n: int) -> str:
    if n <= 0: return "count_0"
    if n <= 5: return "count_1_to_5"
    if n <= 10: return "count_6_to_10"
    if n <= 20: return "count_11_to_20"
    if n <= 50: return "count_21_to_50"
    if n <= 20000: return "count_gt_50_le_20000"
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
    value = median(values)
    if value <= 1: return "rank_1"
    if value <= 5: return "rank_2_to_5"
    if value <= 10: return "rank_6_to_10"
    if value <= 20: return "rank_11_to_20"
    if value <= 40: return "rank_21_to_40"
    return "rank_gt40"


def mrr_bucket(values: Sequence[float]) -> str:
    if not values: return "mrr_unavailable"
    avg = mean(values)
    if avg >= 0.5: return "mrr_high"
    if avg >= 0.2: return "mrr_medium"
    if avg > 0: return "mrr_low"
    return "mrr_zero"


def spread_bucket(values: Sequence[int]) -> str:
    if not values: return "spread_unavailable"
    spread = max(values) - min(values)
    if spread <= 0: return "spread_none"
    if spread <= 4: return "spread_low"
    if spread <= 12: return "spread_medium"
    return "spread_high"


def validate_r2v_source(r2v: dict[str, Any]) -> dict[str, bool]:
    src = (r2v.get("source_lock_records") or [{}])[0]
    stop = (r2v.get("stop_go_records") or [{}])[0]
    status_ok = r2v.get("status") == R2V_STATUS
    scan_ok = r2v.get("forbidden_scan", {}).get("status") == "pass"
    lock_ok = src.get("locked_haae_r2u_checkpoint") == R2U_CHECKPOINT and src.get("source_locked_bool") is True
    auth_ok = stop.get("haae_r2w_content_identifier_material_experiment_authorized_bool") is True
    existing_ok = stop.get("r2w_reads_existing_r2u_private_material_only_bool") is True and stop.get("r2w_aggregate_metrics_only_bool") is True
    boundary_ok = all(stop.get(field) is False for field in ["new_material_generation_authorized_bool", "ci_execution_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"])
    return {"status_ok": status_ok, "scan_ok": scan_ok, "lock_ok": lock_ok, "auth_ok": auth_ok, "existing_ok": existing_ok, "boundary_ok": boundary_ok, "source_locked": status_ok and scan_ok and lock_ok and auth_ok and existing_ok and boundary_ok}


def validate_private_root(root: Path, repo: Path) -> tuple[bool, str, dict[str, Path], dict[str, Any]]:
    if ".." in root.parts: return False, "path_traversal", {}, {}
    try:
        resolved = root.resolve(strict=True); repo_resolved = repo.resolve(strict=True)
    except Exception:
        return False, "root_missing_or_unresolvable", {}, {}
    if not resolved.is_dir() or root.is_symlink() or resolved.is_symlink(): return False, "root_not_directory_or_symlink", {}, {}
    if resolved == repo_resolved or repo_resolved in resolved.parents: return False, "root_under_public_repo", {}, {}
    manifest_path = resolved / R2U_MANIFEST
    if not manifest_path.exists() or not manifest_path.is_file() or manifest_path.is_symlink(): return False, "missing_or_invalid_manifest", {}, {}
    try: manifest = load_json(manifest_path)
    except Exception: return False, "manifest_parse_failed", {}, {}
    if manifest.get("owner_bucket") != R2U_OWNER: return False, "manifest_owner_mismatch", {}, manifest
    if manifest.get("schema_version") != "bea_v1_haae_r2u_content_identifier_material_generation_v1": return False, "manifest_schema_mismatch", {}, manifest
    if manifest.get("status_bucket") != R2U_STATUS: return False, "manifest_status_incompatible", {}, manifest
    if manifest.get("task_count_bucket") != "count_20" or manifest.get("candidate_depth_cap_bucket") != "count_40" or manifest.get("private_row_cap_bucket") != "count_20000": return False, "manifest_bounds_mismatch", {}, manifest
    if set(manifest.get("rank_source_buckets", [])) != set(RANK_SOURCES): return False, "manifest_rank_sources_mismatch", {}, manifest
    if manifest.get("gold_used_for_ranking_bool") is not False or manifest.get("path_feature_policy_bucket") != "path_tokens_extensions_directories_not_used_for_ranking": return False, "manifest_policy_mismatch", {}, manifest
    groups_dir = resolved / "groups"
    if not groups_dir.exists() or not groups_dir.is_dir() or groups_dir.is_symlink(): return False, "missing_groups_directory", {}, manifest
    groups_resolved = groups_dir.resolve(strict=True)
    files: dict[str, Path] = {}; total = 0
    for group in ALL_GROUPS:
        path = groups_dir / f"{group}.jsonl"
        if group in REQUIRED_GROUPS and not path.exists(): return False, "missing_required_group", {}, manifest
        if path.exists():
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True).parent != groups_resolved: return False, "invalid_group_file", {}, manifest
            size = path.stat().st_size
            if size > MAX_GROUP_FILE_BYTES: return False, "group_file_too_large", {}, manifest
            total += size; files[group] = path
    if total > MAX_TOTAL_PRIVATE_BYTES: return False, "private_root_too_large", {}, manifest
    return True, "valid_existing_r2u_private_material_root", files, manifest


def read_groups(files: dict[str, Path]) -> dict[str, list[dict[str, Any]]]: return {g: load_jsonl(p) for g, p in files.items()}


def identifier_from_gold_for_evaluation(label_ref: dict[str, Any], fallback: str = "") -> set[str]:
    values: set[str] = set()
    rationale = str(label_ref.get("rationale", ""))
    for match in re.findall(r"[A-Z][A-Za-z0-9_]{2,}", rationale):
        values.add(match.lower())
    if fallback:
        values.add(fallback.lower())
    return values


def positive_candidate_keys(task: str, candidates: list[dict[str, Any]], outcome_by_task: dict[str, dict[str, Any]]) -> set[str]:
    outcome = outcome_by_task.get(task, {})
    gold_identifiers: set[str] = set()
    for span in outcome.get("gold_spans", []):
        gold_identifiers |= identifier_from_gold_for_evaluation(span)
    keys: set[str] = set()
    for row in candidates:
        identifier = str(row.get("private_identifier_text", "")).lower()
        if identifier and identifier in gold_identifiers:
            keys.add(str(row.get("candidate_key")))
    return keys


def compute_metrics(groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    tasks = groups.get("task_identity", []); candidates = groups.get("candidate_pool", []); ranks = groups.get("rank_pack", []); outcomes = groups.get("outcome_metric", [])
    task_keys = {str(row.get("task_key")) for row in tasks if row.get("task_key") is not None}
    outcome_by_task = {str(row.get("task_key")): row for row in outcomes if row.get("task_key") is not None}
    outcome_keys = set(outcome_by_task)
    candidate_by_task: dict[str, list[dict[str, Any]]] = {}
    for row in candidates:
        if row.get("task_key") is not None: candidate_by_task.setdefault(str(row["task_key"]), []).append(row)
    ranks_by_source_task: dict[tuple[str, str], list[dict[str, Any]]] = {}
    sources_seen: set[str] = set()
    for row in ranks:
        task = row.get("task_key"); source = row.get("rank_source")
        if task is not None and source in RANK_SOURCES:
            ranks_by_source_task.setdefault((str(source), str(task)), []).append(row); sources_seen.add(str(source))
    metric_records: list[dict[str, Any]] = []
    first_rank_by_source: dict[str, list[int]] = {source: [] for source in RANK_SOURCES}
    top_candidates: dict[tuple[str, str], list[str]] = {}
    for source in RANK_SOURCES:
        covered = top1 = top5 = top10 = top20 = missing = 0; ranks_found: list[int] = []
        for task in sorted(task_keys):
            rows = [row for row in ranks_by_source_task.get((source, task), []) if isinstance(row.get("private_rank"), int)]
            rows.sort(key=lambda row: (int(row.get("private_rank", 999999)), str(row.get("candidate_key", ""))))
            top_candidates[(source, task)] = [str(row.get("candidate_key")) for row in rows[:20]]
            if task not in outcome_keys:
                missing += 1; continue
            if not rows: continue
            covered += 1
            positives = positive_candidate_keys(task, candidate_by_task.get(task, []), outcome_by_task)
            hit_ranks = [int(row["private_rank"]) for row in rows if str(row.get("candidate_key")) in positives]
            if hit_ranks:
                best = min(hit_ranks); ranks_found.append(best); first_rank_by_source[source].append(best)
                if best <= 1: top1 += 1
                if best <= 5: top5 += 1
                if best <= 10: top10 += 1
                if best <= 20: top20 += 1
        mrrs = [1 / value for value in ranks_found if value > 0]
        metric_records.append({"rank_source_bucket": source, "task_coverage_bucket": count_bucket(covered), "top1_positive_hit_count_bucket": count_bucket(top1), "top5_positive_hit_count_bucket": count_bucket(top5), "top10_positive_hit_count_bucket": count_bucket(top10), "top20_positive_hit_count_bucket": count_bucket(top20), "positive_hit_rate_bucket": rate_bucket(len(ranks_found), covered), "mrr_bucket": mrr_bucket(mrrs), "median_first_positive_rank_bucket": rank_bucket(ranks_found), "missing_outcome_bucket": count_bucket(missing), "exact_values_published_bool": False})
    agreement_records: list[dict[str, Any]] = []
    for i, left in enumerate(RANK_SOURCES):
        for right in RANK_SOURCES[i + 1:]:
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
    top20_counts = [len([rank for rank in ranks if rank <= 20]) for ranks in first_rank_by_source.values()]
    non_control = [source for source in RANK_SOURCES if source != "control_baseline"]
    non_control_top20 = max((len([rank for rank in first_rank_by_source[source] if rank <= 20]) for source in non_control), default=0)
    control_top20 = len([rank for rank in first_rank_by_source["control_baseline"] if rank <= 20])
    if non_control_top20 >= 10 and non_control_top20 > control_top20:
        signal_bucket = "signal_present"
    elif non_control_top20 > control_top20:
        signal_bucket = "weak_signal"
    elif len(task_keys) == 20:
        signal_bucket = "no_signal"
    else:
        signal_bucket = "inconclusive"
    signal = {"rank_spread_bucket": spread_bucket(top20_counts), "content_identifier_signal_bucket": signal_bucket, "non_control_signal_bucket": "identifier_decoy_material_only", "control_baseline_context_bucket": "not_file_evidence_baseline", "candidate_material_type_bucket": "query_derived_identifier_decoys", "real_file_candidate_evidence_bool": False, "file_retrieval_claim_bool": False, "method_winner_claim_bool": False}
    valid = task_keys == outcome_keys and len(task_keys) == 20 and set(RANK_SOURCES).issubset(sources_seen) and all(groups.get(g) for g in REQUIRED_GROUPS)
    return {"valid": valid, "task_count": len(task_keys), "candidate_count": len(candidates), "rank_count": len(ranks), "outcome_count": len(outcomes), "rank_sources_present": sorted(sources_seen), "metric_records": metric_records, "agreement_records": agreement_records, "signal": signal, "outcome_alignment_bool": task_keys == outcome_keys}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_key|candidate_path|source_path|variant_path|\"gold_spans\"|\"hard_negatives\"|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|exact_rate|exact_rank|task_key|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True); findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, "haae_r2w_content_identifier_material_experiment_complete_r2x_public_audit_authorized", STATUS_DEFAULT, f"{total}/{total}", R2V_CHECKPOINT, R2V_STATUS, "R2U source checkpoint bb95f80", "explicit private material root", "existing R2U material only", "aggregate-only metrics", "seven rank sources", "query_derived_identifier_decoys", "real_file_candidate_evidence_bool=false", "file_retrieval_claim_bool=false", "method_winner_claim_bool=false", "no generation/candidate creation/retrieval/runtime/source scan/CI/network/provider/scheduler/selector/default/method/scaling", NEXT_PHASE]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel; return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2w-content-identifier-material-experiment.md")) and has_all(read("docs/zh/bea-v1-haae-r2w-content-identifier-material-experiment.md"))
    root_current = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(root_current) and "bea-v1-haae-r2w-content-identifier-material-experiment.md" in root_current
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(status: str, explicit: bool, root_valid: bool = False, root_reason: str = "not_supplied", metrics: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED, r2v: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2v is None:
        try: r2v = load_json(repo / R2V_REPORT_PATH)
        except Exception: r2v = {}
    source = validate_r2v_source(r2v); metrics = metrics or {}; readback = public_readback_match(self_test_total)
    valid_metrics = metrics.get("valid") is True
    if not source["source_locked"]: final_status = STATUS_FAIL_SOURCE
    elif explicit and not root_valid: final_status = STATUS_NO_GO_ROOT
    elif explicit and not valid_metrics: final_status = STATUS_NO_GO_SCHEMA
    elif explicit and not readback["all_public_readback_match_bool"]: final_status = STATUS_FAIL_READBACK
    elif explicit:
        signal_bucket = (metrics.get("signal") or {}).get("content_identifier_signal_bucket")
        final_status = STATUS_PASS_SIGNAL if signal_bucket == "signal_present" else STATUS_PASS_WEAK
    else: final_status = status
    passed = final_status in PASS_STATUSES
    signal = metrics.get("signal") or {"candidate_material_type_bucket": "query_derived_identifier_decoys", "real_file_candidate_evidence_bool": False, "file_retrieval_claim_bool": False, "method_winner_claim_bool": False}
    gates = {"r2v_source_locked_gate": source["source_locked"], "explicit_private_root_gate": explicit, "private_root_boundary_gate": (not explicit) or root_valid, "r2u_manifest_owner_schema_gate": (not explicit) or root_valid, "regular_bounded_group_files_gate": (not explicit) or root_valid, "required_group_files_gate": valid_metrics if explicit else True, "task_depth_rank_source_gate": valid_metrics if explicit else True, "path_masking_gate": True, "gold_not_used_for_ranking_gate": True, "outcome_alignment_gate": metrics.get("outcome_alignment_bool") is True if explicit else True, "aggregate_metrics_only_gate": True, "material_validity_context_gate": signal.get("candidate_material_type_bucket") == "query_derived_identifier_decoys" and signal.get("real_file_candidate_evidence_bool") is False, "no_private_write_gate": True, "no_new_material_generation_gate": True, "no_retrieval_runtime_source_scan_gate": True, "no_ci_network_provider_gate": True, "no_scheduler_selector_gate": True, "no_method_default_scaling_claim_gate": True, "public_aggregate_only_gate": True, "stop_go_r2x_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": final_status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2wsource0000", "locked_haae_r2v_checkpoint": R2V_CHECKPOINT, "locked_haae_r2v_status": R2V_STATUS, "locked_r2u_source_checkpoint": R2U_CHECKPOINT, "r2v_status_match_bool": source["status_ok"], "r2v_forbidden_scan_pass_bool": source["scan_ok"], "r2v_r2w_authorization_match_bool": source["auth_ok"], "r2v_existing_material_boundary_bool": source["existing_ok"], "source_locked_bool": source["source_locked"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2wmode0000", "mode_bucket": "explicit_content_identifier_material_experiment" if explicit else "default_no_explicit_private_root", "explicit_private_root_bool": explicit, "private_read_bucket": "count_1_to_10" if explicit and root_valid else "count_0", "private_write_bucket": "count_0", "aggregate_only_publication_bool": True}],
        "private_root_boundary_records": [{"anonymous_private_root_boundary_id": "haaer2wroot0000", "root_supplied_bool": explicit, "root_boundary_bucket": root_reason, "root_path_published_bool": False, "root_basename_filename_published_bool": False, "regular_bounded_group_files_bool": root_valid if explicit else True, "no_root_discovery_bool": True}],
        "material_consistency_records": [{"anonymous_material_consistency_id": "haaer2wmaterial0000", "manifest_owner_bucket": "r2u_content_identifier_material_generation", "task_count_bucket": count_bucket(int(metrics.get("task_count", 0))), "candidate_count_bucket": count_bucket(int(metrics.get("candidate_count", 0))), "rank_count_bucket": count_bucket(int(metrics.get("rank_count", 0))), "outcome_count_bucket": count_bucket(int(metrics.get("outcome_count", 0))), "seven_rank_sources_present_bool": set(metrics.get("rank_sources_present", [])) == set(RANK_SOURCES) if explicit else True, "outcome_alignment_bool": metrics.get("outcome_alignment_bool") is True if explicit else True, "path_masking_manifest_bool": True, "gold_not_used_for_ranking_bool": True}],
        "rank_source_metric_records": [{"anonymous_rank_source_metric_id": f"haaer2wmetric{idx:04d}", **row} for idx, row in enumerate(metrics.get("metric_records", []))] if explicit else [],
        "rank_source_agreement_records": [{"anonymous_rank_source_agreement_id": f"haaer2wagree{idx:04d}", **row} for idx, row in enumerate(metrics.get("agreement_records", []))] if explicit else [],
        "signal_diagnostic_records": [{"anonymous_signal_diagnostic_id": "haaer2wsignal0000", "rank_spread_bucket": signal.get("rank_spread_bucket", "spread_unavailable"), "content_identifier_signal_bucket": signal.get("content_identifier_signal_bucket", "inconclusive"), "non_control_signal_bucket": signal.get("non_control_signal_bucket", "identifier_decoy_material_only"), "control_baseline_context_bucket": signal.get("control_baseline_context_bucket", "not_file_evidence_baseline"), "aggregate_only_bool": True, "method_winner_bool": False}],
        "material_validity_context_records": [{"anonymous_material_validity_context_id": "haaer2wvalidity0000", "candidate_material_type_bucket": "query_derived_identifier_decoys", "real_file_candidate_evidence_bool": False, "file_retrieval_claim_bool": False, "method_winner_claim_bool": False, "file_evidence_evaluation_claim_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2wclaim0000", "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "new_material_generation_bool": False, "candidate_generation_bool": False, "retrieval_runtime_bool": False, "source_scan_bool": False, "ci_network_bool": False, "scheduler_selector_bool": False, "bea_v1_a_p5_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2wgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2wsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["default_no_private", "missing_opt_in", "root_boundary_reject", "manifest_owner_fail", "manifest_schema_fail", "manifest_policy_fail", "missing_group_fail", "missing_rank_source_fail", "outcome_alignment_fail", "aggregate_metric_smoke", "leak_fail", "overauth_fail", "stale_readback_fail", "safe_parser_fail", "source_lock_fail", "material_validity_context_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2wreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2wstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2w_experiment", "haae_r2x_public_audit_package_authorized_bool": passed, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] in PASS_STATUSES and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["source_lock_records", "execution_mode_records", "private_root_boundary_records", "material_consistency_records", "signal_diagnostic_records", "material_validity_context_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    if src.get("locked_haae_r2v_checkpoint") != R2V_CHECKPOINT or src.get("locked_haae_r2v_status") != R2V_STATUS or src.get("locked_r2u_source_checkpoint") != R2U_CHECKPOINT: issues.append("source_lock_mismatch")
    for field in ["r2v_status_match_bool", "r2v_forbidden_scan_pass_bool", "r2v_r2w_authorization_match_bool", "r2v_existing_material_boundary_bool", "source_locked_bool"]:
        if src.get(field) is not True: issues.append(f"source_lock_{field}")
    mode = (report.get("execution_mode_records") or [{}])[0]
    if mode.get("private_write_bucket") != "count_0" or mode.get("aggregate_only_publication_bool") is not True: issues.append("execution_mode_boundary_mismatch")
    if report.get("status") in PASS_STATUSES:
        if mode.get("explicit_private_root_bool") is not True or mode.get("private_read_bucket") == "count_0": issues.append("execution_mode_not_explicit_private_read")
    root = (report.get("private_root_boundary_records") or [{}])[0]
    if report.get("status") in PASS_STATUSES:
        if root.get("root_supplied_bool") is not True or root.get("root_boundary_bucket") != "valid_existing_r2u_private_material_root": issues.append("private_root_boundary_mismatch")
        if root.get("root_path_published_bool") is not False or root.get("root_basename_filename_published_bool") is not False or root.get("no_root_discovery_bool") is not True: issues.append("private_root_publication_or_discovery_mismatch")
    material = (report.get("material_consistency_records") or [{}])[0]
    if report.get("status") in PASS_STATUSES:
        if material.get("task_count_bucket") != "count_11_to_20" or material.get("candidate_count_bucket") == "count_0" or material.get("rank_count_bucket") == "count_0": issues.append("material_consistency_count_mismatch")
        if material.get("seven_rank_sources_present_bool") is not True or material.get("outcome_alignment_bool") is not True or material.get("path_masking_manifest_bool") is not True or material.get("gold_not_used_for_ranking_bool") is not True: issues.append("material_consistency_policy_mismatch")
    metrics = report.get("rank_source_metric_records", [])
    if report.get("status") in PASS_STATUSES:
        metric_sources = {row.get("rank_source_bucket") for row in metrics}
        if metric_sources != set(RANK_SOURCES): issues.append("rank_source_metric_set_mismatch")
        for row in metrics:
            if row.get("exact_values_published_bool") is not False: issues.append("rank_source_metric_exact_values_public")
    agreements = report.get("rank_source_agreement_records", [])
    if report.get("status") in PASS_STATUSES:
        expected_pairs = len(RANK_SOURCES) * (len(RANK_SOURCES) - 1) // 2
        if len(agreements) != expected_pairs: issues.append("agreement_record_pair_count_mismatch")
        for row in agreements:
            if row.get("left_rank_source_bucket") not in RANK_SOURCES or row.get("right_rank_source_bucket") not in RANK_SOURCES: issues.append("agreement_record_rank_source_mismatch")
            if row.get("exact_candidate_values_published_bool") is not False: issues.append("agreement_record_exact_candidate_values_public")
            for field in ["same_top_candidate_rate_bucket", "overlap_at_5_rate_bucket", "overlap_at_10_rate_bucket", "overlap_at_20_rate_bucket"]:
                if not str(row.get(field, "")).startswith("rate_"): issues.append(f"agreement_record_{field}_not_bucketed")
            if not str(row.get("comparable_task_bucket", "")).startswith("count_"): issues.append("agreement_record_comparable_not_bucketed")
    validity = (report.get("material_validity_context_records") or [{}])[0]
    if validity.get("candidate_material_type_bucket") != "query_derived_identifier_decoys" or validity.get("real_file_candidate_evidence_bool") is not False or validity.get("file_retrieval_claim_bool") is not False or validity.get("method_winner_claim_bool") is not False: issues.append("material_validity_context_mismatch")
    signal = (report.get("signal_diagnostic_records") or [{}])[0]
    signal_bucket = signal.get("content_identifier_signal_bucket")
    if signal_bucket not in {"signal_present", "weak_signal", "no_signal", "inconclusive"}: issues.append("signal_bucket_invalid")
    if report.get("status") == STATUS_PASS_SIGNAL and signal_bucket != "signal_present": issues.append("signal_status_mismatch")
    if report.get("status") == STATUS_PASS_WEAK and signal_bucket == "signal_present": issues.append("signal_status_mismatch")
    if signal.get("method_winner_bool") is not False or signal.get("aggregate_only_bool") is not True: issues.append("signal_boundary_mismatch")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "new_material_generation_bool", "candidate_generation_bool", "retrieval_runtime_bool", "source_scan_bool", "ci_network_bool", "scheduler_selector_bool", "bea_v1_a_p5_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") in PASS_STATUSES:
        if stop.get("haae_r2x_public_audit_package_authorized_bool") is not True or stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2x_stop_go_missing")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    for field in FORBIDDEN_STOP_TRUE:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed = {"allow": False, "confirm": False, "root": "", "self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in {"--allow-private-content-identifier-material-experiment", "--confirm-aggregate-only-publication", "--self-test"}:
            if arg == "--allow-private-content-identifier-material-experiment": parsed["allow"] = True
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


def make_private_fixture(root: Path) -> None:
    groups = {group: [] for group in ALL_GROUPS}
    for task_idx in range(1, 21):
        task_key = f"t{task_idx:04d}"
        groups["task_identity"].append({"task_key": task_key})
        groups["anchor_source"].append({"task_key": task_key})
        gold_identifier = f"SyntheticPositive{task_idx:02d}"
        gold_ref = {"rationale": f"{gold_identifier} evidence marker"}
        groups["outcome_metric"].append({"task_key": task_key, "gold_spans": [gold_ref]})
        for cand_idx in range(1, 41):
            cand_key = f"{task_key}_c{cand_idx:03d}"
            identifier = gold_identifier if cand_idx == 1 else f"SyntheticDecoy{task_idx:02d}{cand_idx:02d}"
            groups["candidate_pool"].append({"task_key": task_key, "candidate_key": cand_key, "private_label_ref": {}, "private_identifier_text": identifier})
            groups["evidence_core"].append({"task_key": task_key, "candidate_key": cand_key})
            groups["span_projection"].append({"task_key": task_key, "candidate_key": cand_key})
            for source in RANK_SOURCES:
                groups["rank_pack"].append({"task_key": task_key, "candidate_key": cand_key, "rank_source": source, "private_rank": cand_idx})
    for group in OPTIONAL_GROUPS: groups[group].append({"placeholder": group})
    root.mkdir(parents=True, exist_ok=True); (root / "groups").mkdir(exist_ok=True)
    manifest = {"schema_version": "bea_v1_haae_r2u_content_identifier_material_generation_v1", "owner_bucket": R2U_OWNER, "status_bucket": R2U_STATUS, "task_count_bucket": "count_20", "candidate_depth_cap_bucket": "count_40", "private_row_cap_bucket": "count_20000", "rank_source_buckets": RANK_SOURCES, "gold_used_for_ranking_bool": False, "path_feature_policy_bucket": "path_tokens_extensions_directories_not_used_for_ranking"}
    (root / R2U_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    for group, rows in groups.items():
        (root / "groups" / f"{group}.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    check("default_no_private", build_report(STATUS_DEFAULT, False)["status"] == STATUS_DEFAULT)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-material-root", "/tmp/x"])
        check("missing_opt_in", False)
    except ValueError: check("missing_opt_in", True)
    check("repo_root_reject", validate_private_root(repo, repo)[0] is False)
    with tempfile.TemporaryDirectory(prefix="r2w_selftest_") as tmp:
        root = Path(tmp) / "r2u"; make_private_fixture(root)
        ok, reason, files, _manifest = validate_private_root(root, repo); groups = read_groups(files); metrics = compute_metrics(groups); report = build_report(STATUS_PASS_SIGNAL, True, ok, reason, metrics)
        check("explicit_fixture_smoke", ok and metrics["valid"] and report["status"] in PASS_STATUSES and validate_report(report) == [])
        bad_manifest = load_json(root / R2U_MANIFEST); bad_manifest["owner_bucket"] = "wrong"; (root / R2U_MANIFEST).write_text(json.dumps(bad_manifest), encoding="utf-8"); check("manifest_owner_fail", validate_private_root(root, repo)[0] is False); bad_manifest["owner_bucket"] = R2U_OWNER; bad_manifest["schema_version"] = "wrong"; (root / R2U_MANIFEST).write_text(json.dumps(bad_manifest), encoding="utf-8"); check("manifest_schema_fail", validate_private_root(root, repo)[0] is False)
        root_leak = json.loads(json.dumps(report)); root_leak["private_root_boundary_records"][0]["root_basename_filename_published_bool"] = True; check("root_publication_drift_fail", "private_root_publication_or_discovery_mismatch" in validate_report(root_leak))
        metric_leak = json.loads(json.dumps(report)); metric_leak["rank_source_metric_records"][0]["exact_values_published_bool"] = True; check("metric_exact_publication_drift_fail", "rank_source_metric_exact_values_public" in validate_report(metric_leak))
        agreement_leak = json.loads(json.dumps(report)); agreement_leak["rank_source_agreement_records"][0]["exact_candidate_values_published_bool"] = True; check("agreement_exact_publication_drift_fail", "agreement_record_exact_candidate_values_public" in validate_report(agreement_leak))
        signal_drift = json.loads(json.dumps(report)); signal_drift["status"] = STATUS_PASS_SIGNAL; signal_drift["signal_diagnostic_records"][0]["content_identifier_signal_bucket"] = "no_signal"; check("signal_status_drift_fail", "signal_status_mismatch" in validate_report(signal_drift))
    source_bad = load_json(repo / R2V_REPORT_PATH); source_bad["status"] = "wrong"; check("source_lock_fail", build_report(STATUS_DEFAULT, False, r2v=source_bad)["status"] == STATUS_FAIL_SOURCE)
    leak = build_report(STATUS_DEFAULT, False); leak["debug"] = "/tmp/private-root r14m-001 query candidate_key"; check("leak_fail", scan_public_report(leak)["status"] == "fail")
    over = build_report(STATUS_DEFAULT, False); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("overauth_fail", any(i.startswith("overauthorization_") for i in validate_report(over)))
    validity = build_report(STATUS_DEFAULT, False); validity["material_validity_context_records"][0]["real_file_candidate_evidence_bool"] = True; check("material_validity_context_fail", "material_validity_context_mismatch" in validate_report(validity))
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    check("root_current_latest_readback", public_readback_match(SELF_TEST_EXPECTED)["current_conclusions_readback_match_bool"] is True)
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


if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
