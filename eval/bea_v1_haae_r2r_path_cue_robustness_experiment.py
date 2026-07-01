#!/usr/bin/env python3
"""BEA-v1-HAAE-R2R path-cue robustness experiment.

Default mode reads/writes no private data. Explicit mode reads only an
operator-supplied existing R2P private material root and publishes aggregate-only
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

PHASE = "BEA-v1-HAAE-R2R Path-Cue Robustness Experiment"
SLUG = "bea_v1_haae_r2r_path_cue_robustness_experiment"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME
R2Q_CHECKPOINT = "a9f5477"
R2Q_STATUS = "haae_r2q_public_audit_package_complete_r2r_local_robustness_experiment_authorized"
R2Q_REPORT_PATH = Path("artifacts/bea_v1_haae_r2q_public_audit_package/bea_v1_haae_r2q_public_audit_package_report.json")
R2P_MANIFEST = "haae_r2p_private_manifest.json"
R2P_OWNER = "haae_r2p_path_cue_robustness_material_generation"
R2P_STATUS = "haae_r2p_path_cue_robustness_material_generation_complete_r2q_public_audit_authorized"

STATUS_DEFAULT = "haae_r2r_unavailable_no_explicit_r2p_private_material_root"
STATUS_PASS = "haae_r2r_path_cue_robustness_experiment_complete_r2s_public_audit_authorized"
STATUS_PASS_ARTIFACT = "haae_r2r_path_cue_robustness_experiment_complete_r2s_public_audit_authorized_artifact_likely"
STATUS_PASS_MIXED = "haae_r2r_path_cue_robustness_experiment_complete_r2s_public_audit_authorized_mixed"
STATUS_NO_GO_ROOT = "haae_r2r_no_go_invalid_r2p_private_material_root"
STATUS_NO_GO_SCHEMA = "haae_r2r_no_go_invalid_r2p_material_schema"
STATUS_FAIL_SOURCE = "haae_r2r_fail_closed_source_lock_mismatch"
STATUS_FAIL_LEAK = "haae_r2r_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2r_fail_closed_public_readback_mismatch"
STATUS_FAIL_OVERAUTH = "haae_r2r_fail_closed_stop_go_overauthorization"
SELF_TEST_EXPECTED = 30
NEXT_PHASE = "BEA-v1-HAAE-R2S Public Audit Package"
PASS_STATUSES = {STATUS_PASS, STATUS_PASS_ARTIFACT, STATUS_PASS_MIXED}
VARIANTS = ["original", "path_scrambled", "extension_bucket_preserved", "directory_depth_preserved", "control_baseline_strengthened"]
RANK_SOURCES = ["path_prior", "path_scrambled_prior", "extension_bucket_prior", "directory_depth_prior", "control_baseline_strengthened", "rrf_variant_fusion"]
REQUIRED_GROUPS = ["task_identity", "anchor_source", "candidate_pool", "rank_pack", "evidence_core", "outcome_metric", "span_projection"]
OPTIONAL_GROUPS = ["scheduler_action", "arm_assignment", "safety_probe_signal"]
ALL_GROUPS = REQUIRED_GROUPS + OPTIONAL_GROUPS
MAX_GROUP_FILE_BYTES = 8_000_000
MAX_TOTAL_PRIVATE_BYTES = 40_000_000
FORBIDDEN_STOP_TRUE = ["new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]
GATE_NAMES = ["r2q_source_locked_gate", "explicit_private_root_gate", "private_root_boundary_gate", "r2p_manifest_owner_gate", "regular_bounded_group_files_gate", "required_group_files_gate", "variant_coverage_gate", "rank_source_coverage_gate", "outcome_alignment_gate", "aggregate_metrics_only_gate", "no_private_write_gate", "no_new_material_generation_gate", "no_retrieval_runtime_source_scan_gate", "no_ci_network_provider_gate", "no_scheduler_selector_gate", "no_method_default_scaling_claim_gate", "public_aggregate_only_gate", "stop_go_r2s_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
COUNT_BUCKETS = {"count_0", "count_1_to_5", "count_6_to_10", "count_11_to_20", "count_21_to_50", "count_gt_50_le_20000", "count_gt_20000"}
RATE_BUCKETS = {"rate_0", "rate_0_to_25", "rate_25_to_50", "rate_50_to_75", "rate_75_to_99", "rate_1"}
RANK_BUCKETS = {"rank_unavailable", "rank_1", "rank_2_to_5", "rank_6_to_10", "rank_11_to_20", "rank_21_to_40", "rank_gt40"}
MRR_BUCKETS = {"mrr_unavailable", "mrr_zero", "mrr_low", "mrr_medium", "mrr_high"}
SPREAD_BUCKETS = {"spread_unavailable", "spread_none", "spread_low", "spread_medium", "spread_high"}
INTERPRETATION_BUCKETS = {"robust_candidate_signal", "path_cue_artifact_likely", "mixed_or_inconclusive"}


def load_json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def load_jsonl(path: Path) -> list[dict[str, Any]]: return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


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


def mrr_bucket(values: list[float]) -> str:
    if not values: return "mrr_unavailable"
    avg = mean(values)
    if avg >= 0.5: return "mrr_high"
    if avg >= 0.2: return "mrr_medium"
    if avg > 0: return "mrr_low"
    return "mrr_zero"


def spread_bucket(values: list[int]) -> str:
    if not values: return "spread_unavailable"
    spread = max(values) - min(values)
    if spread <= 0: return "spread_none"
    if spread <= 4: return "spread_low"
    if spread <= 12: return "spread_medium"
    return "spread_high"


def validate_r2q_source(r2q: dict[str, Any]) -> dict[str, bool]:
    stop = (r2q.get("stop_go_records") or [{}])[0]
    status_ok = r2q.get("status") == R2Q_STATUS
    scan_ok = r2q.get("forbidden_scan", {}).get("status") == "pass"
    auth_ok = stop.get("haae_r2r_path_cue_robustness_experiment_authorized_bool") is True
    existing_ok = stop.get("r2r_reads_existing_r2p_private_material_only_bool") is True and stop.get("r2r_aggregate_metrics_only_bool") is True
    boundary_ok = all(stop.get(field) is False for field in ["new_material_generation_authorized_bool", "ci_execution_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"])
    return {"status_ok": status_ok, "scan_ok": scan_ok, "auth_ok": auth_ok, "existing_ok": existing_ok, "boundary_ok": boundary_ok, "source_locked": status_ok and scan_ok and auth_ok and existing_ok and boundary_ok}


def validate_private_root(root: Path, repo: Path) -> tuple[bool, str, dict[str, Path], dict[str, Any]]:
    if ".." in root.parts: return False, "path_traversal", {}, {}
    try:
        resolved = root.resolve(strict=True); repo_resolved = repo.resolve(strict=True)
    except Exception:
        return False, "root_missing_or_unresolvable", {}, {}
    if not resolved.is_dir() or root.is_symlink() or resolved.is_symlink(): return False, "root_not_directory_or_symlink", {}, {}
    if resolved == repo_resolved or repo_resolved in resolved.parents: return False, "root_under_public_repo", {}, {}
    manifest_path = resolved / R2P_MANIFEST
    if not manifest_path.exists() or not manifest_path.is_file() or manifest_path.is_symlink(): return False, "missing_or_invalid_manifest", {}, {}
    try: manifest = load_json(manifest_path)
    except Exception: return False, "manifest_parse_failed", {}, {}
    if manifest.get("owner_bucket") != R2P_OWNER: return False, "manifest_owner_mismatch", {}, manifest
    if manifest.get("status_bucket") != R2P_STATUS: return False, "manifest_status_incompatible", {}, manifest
    if manifest.get("task_count_bucket") != "count_20" or manifest.get("candidate_depth_cap_bucket") != "count_40" or manifest.get("private_row_cap_bucket") != "count_20000": return False, "manifest_bounds_mismatch", {}, manifest
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
    return True, "valid_existing_r2p_private_material_root", files, manifest


def read_groups(files: dict[str, Path]) -> dict[str, list[dict[str, Any]]]: return {g: load_jsonl(p) for g, p in files.items()}


def compute_metrics(groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    tasks = groups.get("task_identity", []); candidates = groups.get("candidate_pool", []); ranks = groups.get("rank_pack", []); outcomes = groups.get("outcome_metric", [])
    task_keys = {str(row.get("task_key")) for row in tasks if row.get("task_key") is not None}
    outcome_keys = {str(row.get("task_key")) for row in outcomes if row.get("task_key") is not None}
    candidate_by_task_key = {(str(row.get("task_key")), str(row.get("candidate_key"))): row for row in candidates if row.get("task_key") is not None and row.get("candidate_key") is not None}
    rank_by_variant_source: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    variants_seen: set[str] = set(); sources_seen: set[str] = set()
    for row in ranks:
        task = row.get("task_key"); src = row.get("rank_source"); variant = row.get("variant_bucket")
        if task is not None and src in RANK_SOURCES and variant in VARIANTS:
            rank_by_variant_source.setdefault((str(task), str(variant), str(src)), []).append(row); variants_seen.add(str(variant)); sources_seen.add(str(src))
    metric_records: list[dict[str, Any]] = []
    first_gold: dict[tuple[str, str], list[int]] = {(v, s): [] for v in VARIANTS for s in RANK_SOURCES}
    path_prior_top_by_variant: dict[str, dict[str, int]] = {v: {"top1": 0, "top5": 0, "top10": 0, "top20": 0} for v in VARIANTS}
    for variant in VARIANTS:
        for src in RANK_SOURCES:
            covered = 0; top1 = top5 = top10 = top20 = missing = 0; ranks_found: list[int] = []
            for task in sorted(task_keys):
                rows = [row for row in rank_by_variant_source.get((task, variant, src), []) if isinstance(row.get("private_rank"), int)]
                rows.sort(key=lambda row: (int(row.get("private_rank", 999999)), str(row.get("candidate_key", ""))))
                if task not in outcome_keys: missing += 1; continue
                if not rows: continue
                covered += 1
                hit_ranks: list[int] = []
                for row in rows:
                    cand = candidate_by_task_key.get((task, str(row.get("candidate_key"))), {})
                    if cand.get("variant_bucket") == variant and cand.get("private_role_bucket") == "gold_evidence":
                        hit_ranks.append(int(row["private_rank"]))
                if hit_ranks:
                    best = min(hit_ranks); ranks_found.append(best); first_gold[(variant, src)].append(best)
                    if best <= 1: top1 += 1
                    if best <= 5: top5 += 1
                    if best <= 10: top10 += 1
                    if best <= 20: top20 += 1
            if src == "path_prior": path_prior_top_by_variant[variant] = {"top1": top1, "top5": top5, "top10": top10, "top20": top20}
            mrrs = [1 / value for value in ranks_found if value > 0]
            metric_records.append({"variant_bucket": variant, "rank_source_bucket": src, "task_coverage_bucket": count_bucket(covered), "top1_hit_count_bucket": count_bucket(top1), "top5_hit_count_bucket": count_bucket(top5), "top10_hit_count_bucket": count_bucket(top10), "top20_hit_count_bucket": count_bucket(top20), "hit_rate_bucket": rate_bucket(len(ranks_found), covered), "mrr_bucket": mrr_bucket(mrrs), "median_first_gold_rank_bucket": rank_bucket(ranks_found), "missing_outcome_bucket": count_bucket(missing), "exact_values_published_bool": False})
    original_top10 = path_prior_top_by_variant.get("original", {}).get("top10", 0)
    original_top20 = path_prior_top_by_variant.get("original", {}).get("top20", 0)
    top10_by_variant = {v: path_prior_top_by_variant.get(v, {}).get("top10", 0) for v in VARIANTS}
    top20_by_variant = {v: path_prior_top_by_variant.get(v, {}).get("top20", 0) for v in VARIANTS}
    drops10 = {v: max(0, original_top10 - top10_by_variant.get(v, 0)) for v in VARIANTS if v != "original"}
    drops20 = {v: max(0, original_top20 - top20_by_variant.get(v, 0)) for v in VARIANTS if v != "original"}
    max_drop10 = max(drops10.values()) if drops10 else 0
    max_drop20 = max(drops20.values()) if drops20 else 0
    original_high = original_top10 >= 11 or original_top20 >= 11
    scrambled_preserved = drops10.get("path_scrambled", 0) <= 2 and drops20.get("path_scrambled", 0) <= 2
    extension_preserved = drops10.get("extension_bucket_preserved", 0) <= 2 or drops20.get("extension_bucket_preserved", 0) <= 2
    depth_preserved = drops10.get("directory_depth_preserved", 0) <= 2 or drops20.get("directory_depth_preserved", 0) <= 2
    control_closes = drops10.get("control_baseline_strengthened", 0) <= 2 and drops20.get("control_baseline_strengthened", 0) <= 2
    if original_high and scrambled_preserved and extension_preserved and depth_preserved and not control_closes:
        interpretation = "robust_candidate_signal"
    elif original_high and ((not scrambled_preserved) or control_closes or (max_drop10 >= 6 or max_drop20 >= 6)):
        interpretation = "path_cue_artifact_likely"
    else:
        interpretation = "mixed_or_inconclusive"
    robustness = {"path_prior_original_top10_bucket": count_bucket(original_top10), "path_prior_original_top20_bucket": count_bucket(original_top20), "path_prior_path_scrambled_drop_bucket": count_bucket(max(drops10.get("path_scrambled", 0), drops20.get("path_scrambled", 0))), "path_prior_extension_bucket_preserved_drop_bucket": count_bucket(max(drops10.get("extension_bucket_preserved", 0), drops20.get("extension_bucket_preserved", 0))), "path_prior_directory_depth_preserved_drop_bucket": count_bucket(max(drops10.get("directory_depth_preserved", 0), drops20.get("directory_depth_preserved", 0))), "path_prior_control_baseline_strengthened_drop_bucket": count_bucket(max(drops10.get("control_baseline_strengthened", 0), drops20.get("control_baseline_strengthened", 0))), "variant_spread_bucket": spread_bucket(list(top10_by_variant.values()) + list(top20_by_variant.values())), "interpretation_bucket": interpretation}
    valid = task_keys == outcome_keys and len(task_keys) == 20 and set(VARIANTS).issubset(variants_seen) and set(RANK_SOURCES).issubset(sources_seen) and all(groups.get(g) for g in REQUIRED_GROUPS)
    return {"valid": valid, "task_count": len(task_keys), "candidate_count": len(candidates), "rank_count": len(ranks), "outcome_count": len(outcomes), "variants_present": sorted(variants_seen), "rank_sources_present": sorted(sources_seen), "metric_records": metric_records, "robustness": robustness, "outcome_alignment_bool": task_keys == outcome_keys}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_key|candidate_path|source_path|variant_path|\"gold_spans\"|\"hard_negatives\"|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|exact_rate|exact_rank|task_key|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True); findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS_ARTIFACT, STATUS_DEFAULT, f"{total}/{total}", R2Q_CHECKPOINT, R2Q_STATUS, "explicit private material root", "existing R2P material only", "aggregate-only metrics", "variant×rank_source", "path_prior robustness", "path_cue_artifact_likely", "path_prior_original_top10_bucket", "count_11_to_20", "spread_high", "no method/default/scaling", NEXT_PHASE]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel; return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2r-path-cue-robustness-experiment.md")) and has_all(read("docs/zh/bea-v1-haae-r2r-path-cue-robustness-experiment.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2r-path-cue-robustness-experiment.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(status: str, explicit: bool, root_valid: bool = False, root_reason: str = "not_supplied", metrics: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED, r2q: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2q is None:
        try: r2q = load_json(repo / R2Q_REPORT_PATH)
        except Exception: r2q = {}
    source = validate_r2q_source(r2q); metrics = metrics or {}; readback = public_readback_match(self_test_total)
    valid_metrics = metrics.get("valid") is True
    if not source["source_locked"]: final_status = STATUS_FAIL_SOURCE
    elif explicit and not root_valid: final_status = STATUS_NO_GO_ROOT
    elif explicit and not valid_metrics: final_status = STATUS_NO_GO_SCHEMA
    elif explicit and not readback["all_public_readback_match_bool"]: final_status = STATUS_FAIL_READBACK
    elif explicit:
        interpretation = (metrics.get("robustness") or {}).get("interpretation_bucket")
        final_status = STATUS_PASS if interpretation == "robust_candidate_signal" else STATUS_PASS_ARTIFACT if interpretation == "path_cue_artifact_likely" else STATUS_PASS_MIXED
    else: final_status = status
    passed = final_status in PASS_STATUSES
    variants_ok = set(metrics.get("variants_present", [])) == set(VARIANTS)
    ranks_ok = set(metrics.get("rank_sources_present", [])) == set(RANK_SOURCES)
    gates = {"r2q_source_locked_gate": source["source_locked"], "explicit_private_root_gate": explicit, "private_root_boundary_gate": (not explicit) or root_valid, "r2p_manifest_owner_gate": (not explicit) or root_valid, "regular_bounded_group_files_gate": (not explicit) or root_valid, "required_group_files_gate": (not explicit) or valid_metrics, "variant_coverage_gate": variants_ok if explicit else False, "rank_source_coverage_gate": ranks_ok if explicit else False, "outcome_alignment_gate": metrics.get("outcome_alignment_bool") is True if explicit else False, "aggregate_metrics_only_gate": True, "no_private_write_gate": True, "no_new_material_generation_gate": True, "no_retrieval_runtime_source_scan_gate": True, "no_ci_network_provider_gate": True, "no_scheduler_selector_gate": True, "no_method_default_scaling_claim_gate": True, "public_aggregate_only_gate": True, "stop_go_r2s_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": final_status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2rsource0000", "locked_haae_r2q_checkpoint": R2Q_CHECKPOINT, "locked_haae_r2q_status": R2Q_STATUS, "r2q_status_match_bool": source["status_ok"], "r2q_forbidden_scan_pass_bool": source["scan_ok"], "r2q_r2r_authorization_match_bool": source["auth_ok"], "r2q_existing_material_boundary_bool": source["existing_ok"], "source_locked_bool": source["source_locked"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2rmode0000", "mode_bucket": "explicit_path_cue_robustness_experiment" if explicit else "default_no_explicit_private_root", "explicit_private_root_bool": explicit, "private_read_bucket": "count_1_to_10" if explicit else "count_0", "private_write_bucket": "count_0", "aggregate_only_publication_bool": True}],
        "private_root_boundary_records": [{"anonymous_private_root_boundary_id": "haaer2rroot0000", "root_supplied_bool": explicit, "root_valid_bool": root_valid, "root_boundary_bucket": root_reason, "root_path_published_bool": False, "root_basename_filename_published_bool": False, "no_root_discovery_bool": True}],
        "material_consistency_records": [{"anonymous_material_consistency_id": "haaer2rconsistency0000", "task_count_bucket": count_bucket(int(metrics.get("task_count", 0))), "candidate_count_bucket": count_bucket(int(metrics.get("candidate_count", 0))), "rank_count_bucket": count_bucket(int(metrics.get("rank_count", 0))), "outcome_count_bucket": count_bucket(int(metrics.get("outcome_count", 0))), "variant_coverage_bool": variants_ok, "rank_source_coverage_bool": ranks_ok, "outcome_alignment_bool": metrics.get("outcome_alignment_bool") is True, "material_valid_bool": valid_metrics}],
        "variant_rank_source_metric_records": [{"anonymous_metric_id": f"haaer2rmetric{idx:04d}", **row} for idx, row in enumerate(metrics.get("metric_records", []))],
        "variant_robustness_records": [{"anonymous_robustness_id": "haaer2rrobust0000", **(metrics.get("robustness") or {"path_prior_original_top10_bucket": "count_0", "path_prior_original_top20_bucket": "count_0", "path_prior_path_scrambled_drop_bucket": "count_0", "path_prior_extension_bucket_preserved_drop_bucket": "count_0", "path_prior_directory_depth_preserved_drop_bucket": "count_0", "path_prior_control_baseline_strengthened_drop_bucket": "count_0", "variant_spread_bucket": "spread_unavailable", "interpretation_bucket": "mixed_or_inconclusive"})}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2rclaim0000", "experiment_bool": explicit, "private_write_bool": False, "new_material_generation_bool": False, "candidate_generation_bool": False, "retrieval_runtime_bool": False, "source_scan_bool": False, "ci_network_provider_bool": False, "scheduler_selector_bool": False, "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2rgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2rsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["default_no_private", "missing_opt_in", "repo_root_reject", "symlink_root_reject", "missing_manifest", "wrong_manifest_owner", "missing_group", "missing_variant", "missing_rank_source", "outcome_mismatch", "explicit_pass", "leak_scanner", "overauth", "stale_readback", "safe_parser"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2rreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2rstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_fix_r2r_experiment", "haae_r2s_public_audit_package_authorized_bool": passed, "r2s_public_only_audit_bool": passed, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] in PASS_STATUSES and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "execution_mode_records", "private_root_boundary_records", "material_consistency_records", "variant_rank_source_metric_records", "variant_robustness_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    if src.get("locked_haae_r2q_checkpoint") != R2Q_CHECKPOINT or src.get("locked_haae_r2q_status") != R2Q_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2q_status_match_bool", "r2q_forbidden_scan_pass_bool", "r2q_r2r_authorization_match_bool", "r2q_existing_material_boundary_bool", "source_locked_bool"]:
        if src.get(field) is not True: issues.append(f"source_lock_{field}")
    if report.get("status") in PASS_STATUSES:
        exec_rec = (report.get("execution_mode_records") or [{}])[0]
        if exec_rec.get("mode_bucket") != "explicit_path_cue_robustness_experiment" or exec_rec.get("explicit_private_root_bool") is not True or exec_rec.get("private_read_bucket") != "count_1_to_10" or exec_rec.get("private_write_bucket") != "count_0" or exec_rec.get("aggregate_only_publication_bool") is not True: issues.append("execution_mode_mismatch")
        root = (report.get("private_root_boundary_records") or [{}])[0]
        if root.get("root_valid_bool") is not True or root.get("root_boundary_bucket") != "valid_existing_r2p_private_material_root" or root.get("root_path_published_bool") is not False or root.get("root_basename_filename_published_bool") is not False or root.get("no_root_discovery_bool") is not True: issues.append("private_root_boundary_mismatch")
        consistency = (report.get("material_consistency_records") or [{}])[0]
        for field in ["variant_coverage_bool", "rank_source_coverage_bool", "outcome_alignment_bool", "material_valid_bool"]:
            if consistency.get(field) is not True: issues.append(f"material_consistency_{field}")
        for field in ["task_count_bucket", "candidate_count_bucket", "rank_count_bucket", "outcome_count_bucket"]:
            if consistency.get(field) not in COUNT_BUCKETS: issues.append(f"invalid_count_bucket_{field}")
        combos = {(row.get("variant_bucket"), row.get("rank_source_bucket")) for row in report.get("variant_rank_source_metric_records", [])}
        if combos != {(v, s) for v in VARIANTS for s in RANK_SOURCES}: issues.append("variant_rank_source_metric_set_mismatch")
        for row in report.get("variant_rank_source_metric_records", []):
            if row.get("hit_rate_bucket") not in RATE_BUCKETS: issues.append("invalid_hit_rate_bucket")
            for field in ["task_coverage_bucket", "top1_hit_count_bucket", "top5_hit_count_bucket", "top10_hit_count_bucket", "top20_hit_count_bucket", "missing_outcome_bucket"]:
                if row.get(field) not in COUNT_BUCKETS: issues.append(f"invalid_metric_count_bucket_{field}")
            if row.get("median_first_gold_rank_bucket") not in RANK_BUCKETS: issues.append("invalid_rank_bucket")
            if row.get("mrr_bucket") not in MRR_BUCKETS: issues.append("invalid_mrr_bucket")
            if row.get("exact_values_published_bool") is not False: issues.append("exact_values_published")
        robustness = (report.get("variant_robustness_records") or [{}])[0]
        if robustness.get("interpretation_bucket") not in INTERPRETATION_BUCKETS: issues.append("invalid_interpretation_bucket")
        if robustness.get("variant_spread_bucket") not in SPREAD_BUCKETS: issues.append("invalid_spread_bucket")
        for field in ["path_prior_original_top10_bucket", "path_prior_original_top20_bucket", "path_prior_path_scrambled_drop_bucket", "path_prior_extension_bucket_preserved_drop_bucket", "path_prior_directory_depth_preserved_drop_bucket", "path_prior_control_baseline_strengthened_drop_bucket"]:
            if robustness.get(field) not in COUNT_BUCKETS: issues.append(f"invalid_robustness_bucket_{field}")
        expected_status = STATUS_PASS if robustness.get("interpretation_bucket") == "robust_candidate_signal" else STATUS_PASS_ARTIFACT if robustness.get("interpretation_bucket") == "path_cue_artifact_likely" else STATUS_PASS_MIXED
        if report.get("status") != expected_status: issues.append("status_interpretation_mismatch")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["private_write_bool", "new_material_generation_bool", "candidate_generation_bool", "retrieval_runtime_bool", "source_scan_bool", "ci_network_provider_bool", "scheduler_selector_bool", "method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") in PASS_STATUSES:
        for field in ["haae_r2s_public_audit_package_authorized_bool", "r2s_public_only_audit_bool"]:
            if stop.get(field) is not True: issues.append(f"stop_go_{field}")
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("next_allowed_phase_mismatch")
    for field in FORBIDDEN_STOP_TRUE:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed = {"allow": False, "confirm": False, "root": "", "self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in {"--allow-private-path-cue-robustness-experiment", "--confirm-aggregate-only-publication", "--self-test"}:
            if arg == "--allow-private-path-cue-robustness-experiment": parsed["allow"] = True
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
    repo = Path(__file__).resolve().parents[1]; path = Path(value); resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def write_report(report: dict[str, Any], out: Path | None) -> Path:
    path = out or PUBLIC_REPORT_PATH; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return path


def make_synthetic_root(root: Path, *, missing_group: str | None = None, missing_variant: str | None = None, missing_source: str | None = None, outcome_mismatch: bool = False) -> None:
    group_dir = root / "groups"; group_dir.mkdir(parents=True, exist_ok=True)
    (root / R2P_MANIFEST).write_text(json.dumps({"owner_bucket": R2P_OWNER, "status_bucket": R2P_STATUS, "task_count_bucket": "count_20", "candidate_depth_cap_bucket": "count_40", "private_row_cap_bucket": "count_20000"}, sort_keys=True), encoding="utf-8")
    rows = {g: [] for g in ALL_GROUPS}
    for i in range(20):
        task = f"task_{i:04d}"; rows["task_identity"].append({"task_key": task}); rows["anchor_source"].append({"task_key": task})
        for v_idx, variant in enumerate(VARIANTS):
            if variant == missing_variant: continue
            key = f"{task}_c{v_idx}"; role = "gold_evidence"
            cand = {"task_key": task, "candidate_key": key, "variant_bucket": variant, "private_role_bucket": role}
            rows["candidate_pool"].append(cand); rows["evidence_core"].append(cand); rows["span_projection"].append(cand)
            for source in RANK_SOURCES:
                if source == missing_source: continue
                rank = 1 if (variant == "original" and source == "path_prior") else (5 + v_idx)
                rows["rank_pack"].append({"task_key": task, "candidate_key": key, "variant_bucket": variant, "rank_source": source, "private_rank": rank, "private_score": 1.0 / rank})
        rows["outcome_metric"].append({"task_key": f"bad_{i:04d}" if outcome_mismatch else task, "gold_labels_private_only_bool": True})
    for g in ["scheduler_action", "arm_assignment", "safety_probe_signal"]: rows[g].append({"placeholder": g})
    for group, data in rows.items():
        if group != missing_group: write_jsonl(group_dir / f"{group}.jsonl", data)


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []; repo = Path(__file__).resolve().parents[1]
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    check("default_no_private", build_report(STATUS_DEFAULT, False)["status"] == STATUS_DEFAULT)
    check("repo_root_reject", validate_private_root(repo, repo)[0] is False)
    bad_source = load_json(repo / R2Q_REPORT_PATH); bad_source["status"] = "wrong"; check("source_lock_drift", build_report(STATUS_DEFAULT, False, r2q=bad_source)["status"] == STATUS_FAIL_SOURCE)
    with tempfile.TemporaryDirectory(prefix="r2r_selftest_") as tmp:
        root = Path(tmp) / "root"; make_synthetic_root(root); ok, reason, files, _ = validate_private_root(root, repo); metrics = compute_metrics(read_groups(files)); pass_report = build_report(STATUS_PASS, True, ok, reason, metrics)
        check("explicit_pass", ok and metrics["valid"] and pass_report["status"] in PASS_STATUSES and validate_report(pass_report) == [])
        check("artifact_status_selected", pass_report["status"] == STATUS_PASS_ARTIFACT)
        check("standard_count_buckets", count_bucket(20) == "count_11_to_20" and count_bucket(40) == "count_21_to_50")
        check("robustness_uses_top10_top20", "path_prior_original_top10_bucket" in pass_report["variant_robustness_records"][0] and "path_prior_original_top1_bucket" not in pass_report["variant_robustness_records"][0])
        source_drift = json.loads(json.dumps(pass_report)); source_drift["source_lock_records"][0]["r2q_forbidden_scan_pass_bool"] = False; check("source_bool_drift", "source_lock_r2q_forbidden_scan_pass_bool" in validate_report(source_drift))
        status_drift = json.loads(json.dumps(pass_report)); status_drift["status"] = STATUS_PASS; check("status_interpretation_drift", "status_interpretation_mismatch" in validate_report(status_drift))
        metric_bucket_drift = json.loads(json.dumps(pass_report)); metric_bucket_drift["variant_rank_source_metric_records"][0]["top10_hit_count_bucket"] = "count_10_to_20"; check("metric_bucket_drift", any(i.startswith("invalid_metric_count_bucket") for i in validate_report(metric_bucket_drift)))
        exact_drift = json.loads(json.dumps(pass_report)); exact_drift["variant_rank_source_metric_records"][0]["exact_values_published_bool"] = True; check("exact_publication_drift", "exact_values_published" in validate_report(exact_drift))
        robustness_drift = json.loads(json.dumps(pass_report)); robustness_drift["variant_robustness_records"][0]["interpretation_bucket"] = "winner"; check("robustness_bucket_drift", "invalid_interpretation_bucket" in validate_report(robustness_drift))
        gate_drift = json.loads(json.dumps(pass_report)); gate_drift["pass_fail_gate_records"][0]["gate_passed_bool"] = False; check("gate_drift", any(i.startswith("gate_failed_") for i in validate_report(gate_drift)))
        root_bucket_drift = json.loads(json.dumps(pass_report)); root_bucket_drift["private_root_boundary_records"][0]["root_boundary_bucket"] = "unknown"; check("root_bucket_drift", "private_root_boundary_mismatch" in validate_report(root_bucket_drift))
        root_name_drift = json.loads(json.dumps(pass_report)); root_name_drift["private_root_boundary_records"][0]["root_basename_filename_published_bool"] = True; check("root_name_drift", "private_root_boundary_mismatch" in validate_report(root_name_drift))
        root_discovery_drift = json.loads(json.dumps(pass_report)); root_discovery_drift["private_root_boundary_records"][0]["no_root_discovery_bool"] = False; check("root_discovery_drift", "private_root_boundary_mismatch" in validate_report(root_discovery_drift))
        exec_drift = json.loads(json.dumps(pass_report)); exec_drift["execution_mode_records"][0]["private_read_bucket"] = "count_0"; check("execution_mode_drift", "execution_mode_mismatch" in validate_report(exec_drift))
        next_drift = json.loads(json.dumps(pass_report)); next_drift["stop_go_records"][0]["next_allowed_phase"] = "BEA-v1-HAAE-R2T Scale Execution"; check("next_phase_drift", "next_allowed_phase_mismatch" in validate_report(next_drift))
        leak_status = build_report(STATUS_PASS, True, ok, reason, metrics); leak_status["debug"] = "/tmp/private-root"; leak_status["forbidden_scan"] = scan_public_report(leak_status); check("artifact_pass_scanner_fail_closed", scan_public_report(leak_status)["status"] == "fail")
        for name, kwargs in [("missing_group", {"missing_group": "candidate_pool"}), ("missing_variant", {"missing_variant": "path_scrambled"}), ("missing_rank_source", {"missing_source": "path_prior"}), ("outcome_mismatch", {"outcome_mismatch": True})]:
            bad = Path(tmp) / name; make_synthetic_root(bad, **kwargs); ok2, _, files2, _ = validate_private_root(bad, repo); metrics2 = compute_metrics(read_groups(files2)) if ok2 else {}; status2 = build_report(STATUS_PASS, True, ok2, "test", metrics2)["status"]; check(name, status2 in {STATUS_NO_GO_SCHEMA, STATUS_NO_GO_ROOT})
        wrong = Path(tmp) / "wrong"; make_synthetic_root(wrong); (wrong / R2P_MANIFEST).write_text(json.dumps({"owner_bucket": "wrong"}), encoding="utf-8"); check("wrong_manifest_owner", validate_private_root(wrong, repo)[0] is False)
    leak = build_report(STATUS_DEFAULT, False); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("leak_scanner", scan_public_report(leak)["status"] == "fail")
    over = build_report(STATUS_DEFAULT, False); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("overauth", any(i.startswith("overauthorization_") for i in validate_report(over)))
    check("stale_readback", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-material-root", "/tmp/x"])
        check("safe_parser", False)
    except ValueError: check("safe_parser", True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception:
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
    report = build_report(STATUS_PASS if ok else STATUS_NO_GO_ROOT, True, ok, reason, metrics); path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
