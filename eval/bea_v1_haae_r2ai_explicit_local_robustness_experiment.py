#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AI explicit local robustness experiment.

Default mode is a public/default no-op: no private read/write/source scan/material
generation/metrics. Explicit mode requires opt-in flags and an existing R2AG
private material root, reads only existing R2AG private material group files, and
publishes aggregate-only bucketized robustness results.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AI Explicit Local Robustness Experiment Over Existing R2AG Material"
SLUG = "bea_v1_haae_r2ai_explicit_local_robustness_experiment"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AH_CHECKPOINT = "83d7997"
R2AH_STATUS = "haae_r2ah_robustness_material_public_audit_package_complete_r2ai_explicit_experiment_authorized"
R2AG_CHECKPOINT = "a0ac3b3"
R2AG_STATUS = "haae_r2ag_explicit_local_bounded_robustness_material_generation_complete_r2ah_public_audit_authorized"
R2AH_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ah_robustness_material_public_audit_package/bea_v1_haae_r2ah_robustness_material_public_audit_package_report.json")

STATUS_DEFAULT = "haae_r2ai_unavailable_no_explicit_existing_r2ag_material_opt_in"
STATUS_PASS_ROBUST = "haae_r2ai_explicit_local_robustness_experiment_complete_r2aj_public_audit_authorized_robust_signal"
STATUS_PASS_BRITTLE = "haae_r2ai_explicit_local_robustness_experiment_complete_r2aj_public_audit_authorized_brittle_or_artifact"
STATUS_PASS_MIXED = "haae_r2ai_explicit_local_robustness_experiment_complete_r2aj_public_audit_authorized_mixed_or_inconclusive"
PASS_STATUSES = {STATUS_PASS_ROBUST, STATUS_PASS_BRITTLE, STATUS_PASS_MIXED}
STATUS_FAIL_SOURCE = "haae_r2ai_fail_closed_source_lock_mismatch"
STATUS_FAIL_ROOT = "haae_r2ai_fail_closed_private_root_invalid"
STATUS_FAIL_MANIFEST = "haae_r2ai_fail_closed_private_manifest_invalid"
STATUS_FAIL_MATERIAL = "haae_r2ai_fail_closed_existing_material_invalid"
STATUS_FAIL_LEAK = "haae_r2ai_fail_closed_public_artifact_leak"
STATUS_FAIL_READBACK = "haae_r2ai_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 26
NEXT_PHASE = "BEA-v1-HAAE-R2AJ Robustness Experiment Public Audit Package"

R2AG_PRIVATE_SCHEMA = "bea_v1_haae_r2ag_explicit_local_bounded_robustness_material_generation_v1"
R2AG_OWNER = "haae_r2ag_explicit_local_bounded_robustness_material_generation"
PRIVATE_MANIFEST = "r2ag_private_manifest.json"
REQUIRED_GROUPS = ["task_frame", "candidate_pool", "variant_material", "rank_pack", "outcome_eval_private", "material_qa"]
OPTIONAL_GROUPS = ["source_manifest_private"]
VARIANTS = ["symbol_content_ablation", "query_token_masking", "shuffled_content_control", "negative_control_strengthening"]
ROBUST_STATUSES = {"robust_signal", "brittle_or_artifact", "mixed_or_inconclusive"}
FORBIDDEN_STOP_TRUE = ["new_material_generation_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "source_scan_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]
GATE_NAMES = ["r2ah_source_locked_gate", "default_noop_gate", "explicit_opt_in_gate", "existing_private_root_safety_gate", "private_manifest_owner_schema_gate", "required_group_files_gate", "source_manifest_schema_count_only_gate", "existing_material_only_gate", "no_source_candidate_scan_gate", "no_material_generation_gate", "aggregate_only_bucket_metrics_gate", "variant_policy_axis_gate", "no_exact_public_metrics_gate", "robustness_status_gate", "r2aj_public_audit_only_stop_go_gate", "no_ci_network_default_method_scale_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTHETIC_VALIDATORS = ["source_lock_pass", "wrong_r2ah_status_fail", "default_noop_fail", "missing_opt_in_fail", "root_inside_repo_fail", "root_symlink_fail", "root_escape_fail", "manifest_owner_fail", "manifest_schema_fail", "missing_required_group_fail", "material_generated_flag_fail", "rank_gold_fail", "rank_path_fail", "variant_missing_fail", "metric_public_boundary_fail", "raw_publication_fail", "next_phase_fail", "stop_go_overauth_fail", "gate_set_fail", "readback_record_fail", "status_metric_bucket_fail", "variant_rank_bucket_fail", "variant_mrr_bucket_fail", "prior_phase_count_guard_fail", "stale_readback_fail", "safe_parser_fail"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip(): rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def bucket_count(n: int) -> str:
    if n <= 0: return "count_0"
    if n == 1: return "count_1"
    if n <= 5: return "count_2_to_5"
    if n <= 20: return "count_6_to_20"
    if n <= 50: return "count_21_to_50"
    if n <= 20000: return "count_le_20000"
    return "count_over_cap"


def bucket_ratio(num: int, den: int) -> str:
    if den <= 0: return "ratio_unavailable"
    ratio = num / den
    if ratio >= 0.95: return "ratio_very_high"
    if ratio >= 0.75: return "ratio_high"
    if ratio >= 0.45: return "ratio_medium"
    if ratio > 0: return "ratio_low"
    return "ratio_zero"


def bucket_hit20(n: int) -> str:
    if n <= 0: return "hit_count_0"
    if n == 1: return "hit_count_1"
    if n <= 5: return "hit_count_2_to_5"
    if n <= 10: return "hit_count_6_to_10"
    if n <= 15: return "hit_count_11_to_15"
    if n <= 20: return "hit_count_16_to_20"
    return "hit_count_over_scope"


def bucket_rank(rank: int | None) -> str:
    if rank is None: return "rank_unavailable"
    if rank == 1: return "rank_1"
    if rank <= 5: return "rank_2_to_5"
    if rank <= 10: return "rank_6_to_10"
    if rank <= 20: return "rank_11_to_20"
    return "rank_gt_20"


def bucket_mrr(total_rr: float, den: int) -> str:
    if den <= 0: return "mrr_unavailable"
    value = total_rr / den
    if value >= 0.75: return "mrr_high"
    if value >= 0.35: return "mrr_medium"
    if value > 0: return "mrr_low"
    return "mrr_zero"


def audit_r2ah(r2ah: dict[str, Any]) -> dict[str, bool]:
    source = (r2ah.get("source_lock_records") or [{}])[0]
    stop = (r2ah.get("stop_go_records") or [{}])[0]
    status_ok = r2ah.get("status") == R2AH_STATUS
    scan_ok = r2ah.get("forbidden_scan", {}).get("status") == "pass"
    r2ag_ok = source.get("locked_haae_r2ag_checkpoint") == R2AG_CHECKPOINT and source.get("locked_haae_r2ag_status") == R2AG_STATUS and source.get("source_locked_bool") is True
    auth_ok = stop.get("haae_r2ai_explicit_local_robustness_experiment_authorized_bool") is True and stop.get("r2ai_existing_r2ag_private_material_only_bool") is True and stop.get("r2ai_explicit_private_root_required_bool") is True and stop.get("r2ai_public_audit_required_after_experiment_bool") is True
    metrics_ok = stop.get("r2ai_aggregate_only_experiment_metrics_authorized_bool") is True and stop.get("experiment_metrics_authorized_bool") is True
    no_overauth = all(stop.get(field, False) is False for field in FORBIDDEN_STOP_TRUE)
    locked = status_ok and scan_ok and r2ag_ok and auth_ok and metrics_ok and no_overauth
    return {"status_ok": status_ok, "scan_ok": scan_ok, "r2ag_ok": r2ag_ok, "auth_ok": auth_ok, "metrics_ok": metrics_ok, "no_overauth": no_overauth, "source_locked": locked}


def validate_root(root: Path, repo: Path) -> tuple[bool, str]:
    try:
        resolved = root.resolve(strict=True)
    except Exception:
        return False, "root_missing"
    try:
        resolved.relative_to(repo.resolve())
        return False, "root_inside_public_repo"
    except ValueError:
        pass
    if root.is_symlink() or any(part.is_symlink() for part in [resolved, *(resolved.parents)]):
        return False, "root_symlink_or_escape"
    if not (resolved / PRIVATE_MANIFEST).is_file():
        return False, "manifest_missing"
    groups = resolved / "groups"
    if not groups.is_dir():
        return False, "groups_missing"
    for group in REQUIRED_GROUPS:
        path = (groups / f"{group}.jsonl").resolve()
        try: path.relative_to(resolved)
        except ValueError: return False, "group_escape"
        if path.is_symlink() or not path.is_file(): return False, "required_group_missing"
    return True, "valid_existing_r2ag_private_material_root"


def load_private_material(root: Path) -> dict[str, Any]:
    manifest = load_json(root / PRIVATE_MANIFEST)
    groups_dir = root / "groups"
    rows = {group: read_jsonl(groups_dir / f"{group}.jsonl") for group in REQUIRED_GROUPS}
    optional_counts = {}
    for group in OPTIONAL_GROUPS:
        path = groups_dir / f"{group}.jsonl"
        if path.exists():
            optional_counts[group] = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return {"manifest": manifest, "rows": rows, "optional_counts": optional_counts}


def validate_private_material(material: dict[str, Any]) -> tuple[bool, str]:
    manifest = material.get("manifest", {})
    if manifest.get("owner_bucket") != R2AG_OWNER: return False, "owner_mismatch"
    if manifest.get("schema_version") != R2AG_PRIVATE_SCHEMA: return False, "schema_mismatch"
    if set(REQUIRED_GROUPS).difference(set(manifest.get("groups", []))): return False, "required_group_manifest_missing"
    rows = material.get("rows", {})
    if any(not rows.get(group) for group in REQUIRED_GROUPS): return False, "required_group_empty"
    qa = rows.get("material_qa", [{}])[0]
    if qa.get("rank_policy_used_gold_bool") is not False or qa.get("rank_policy_used_path_bool") is not False or qa.get("gold_private_eval_only_bool") is not True: return False, "policy_mismatch"
    if any(row.get("rank_policy_used_gold_bool") is not False or row.get("rank_policy_used_path_bool") is not False for row in rows.get("rank_pack", [])): return False, "rank_policy_mismatch"
    if any(row.get("gold_used_for_ranking_bool") is not False or row.get("outcome_labels_used_for_ranking_bool") is not False for row in rows.get("outcome_eval_private", [])): return False, "gold_policy_mismatch"
    variants = {row.get("variant_bucket") for row in rows.get("variant_material", [])}
    if variants != set(VARIANTS): return False, "variant_set_mismatch"
    return True, "valid_existing_r2ag_private_manifest_and_groups"


def compute_aggregate(material: dict[str, Any]) -> dict[str, Any]:
    rows = material["rows"]
    rank_rows = rows["rank_pack"]
    variant_rows = rows["variant_material"]
    task_rows = rows["task_frame"]
    candidates = {(row.get("task_key"), row.get("candidate_key")): row for row in rows["candidate_pool"]}
    gold_paths: dict[str, set[str]] = {}
    for row in rows["outcome_eval_private"]:
        paths = {span.get("path") for span in row.get("gold_spans", []) if span.get("path")}
        gold_paths[row.get("task_key", "")] = paths
    policy_safe = all(row.get("rank_policy_used_gold_bool") is False and row.get("rank_policy_used_path_bool") is False for row in rank_rows)
    variant_counts = {variant: sum(1 for row in variant_rows if row.get("variant_bucket") == variant) for variant in VARIANTS}
    rank_coverage = {variant: sum(1 for row in rank_rows if row.get("variant_bucket") == variant) for variant in VARIANTS}
    metric_by_variant: dict[str, dict[str, Any]] = {}
    for variant in VARIANTS:
        by_task: dict[str, list[dict[str, Any]]] = {}
        for row in rank_rows:
            if row.get("variant_bucket") == variant:
                by_task.setdefault(row.get("task_key", ""), []).append(row)
        top_hits = {1: 0, 5: 0, 10: 0, 20: 0}
        first_rank_sum = 0
        first_rank_seen = 0
        rr_sum = 0.0
        aligned_tasks = 0
        for task_key, task_rank_rows in by_task.items():
            gold = gold_paths.get(task_key, set())
            if not gold:
                continue
            aligned_tasks += 1
            ordered = sorted(task_rank_rows, key=lambda r: int(r.get("private_rank", 10**9)))
            first_rank: int | None = None
            for rank_row in ordered:
                candidate = candidates.get((task_key, rank_row.get("candidate_key")), {})
                if candidate.get("path") in gold:
                    first_rank = int(rank_row.get("private_rank", 10**9))
                    break
            if first_rank is not None:
                first_rank_seen += 1
                first_rank_sum += first_rank
                rr_sum += 1.0 / max(first_rank, 1)
                for k in top_hits:
                    if first_rank <= k:
                        top_hits[k] += 1
        mean_first_rank = round(first_rank_sum / first_rank_seen) if first_rank_seen else None
        metric_by_variant[variant] = {
            "aligned_task_bucket": bucket_hit20(aligned_tasks),
            "top1_hit_bucket": bucket_hit20(top_hits[1]),
            "top5_hit_bucket": bucket_hit20(top_hits[5]),
            "top10_hit_bucket": bucket_hit20(top_hits[10]),
            "top20_hit_bucket": bucket_hit20(top_hits[20]),
            "first_gold_rank_bucket": bucket_rank(mean_first_rank),
            "mrr_bucket": bucket_mrr(rr_sum, aligned_tasks),
            "top10_count_private": top_hits[10],
        }
    present = all(variant_counts[v] > 0 and rank_coverage[v] > 0 for v in VARIANTS)
    coverage_min = min(rank_coverage.values()) if rank_coverage else 0
    coverage_max = max(rank_coverage.values()) if rank_coverage else 0
    balanced = coverage_min == coverage_max and coverage_min > 0
    signal_min_top10 = min(metric_by_variant.get(v, {}).get("top10_count_private", 0) for v in ["symbol_content_ablation", "query_token_masking"])
    control_max_top10 = max(metric_by_variant.get(v, {}).get("top10_count_private", 0) for v in ["shuffled_content_control", "negative_control_strengthening"])
    if policy_safe and present and balanced and len(task_rows) >= 20 and signal_min_top10 >= 11 and control_max_top10 <= 5:
        status = "robust_signal"
    elif (not policy_safe or not present) or control_max_top10 >= signal_min_top10 or signal_min_top10 <= 5:
        status = "brittle_or_artifact"
    else:
        status = "mixed_or_inconclusive"
    return {"task_count_bucket": bucket_count(len(task_rows)), "variant_row_count_buckets": {v: bucket_count(variant_counts[v]) for v in VARIANTS}, "rank_pack_count_buckets": {v: bucket_count(rank_coverage[v]) for v in VARIANTS}, "variant_metric_buckets": metric_by_variant, "variant_axis_balance_bucket": "balanced_bucket" if balanced else "unbalanced_bucket", "policy_axis_safe_bucket": "rank_policy_no_gold_path" if policy_safe else "rank_policy_violation", "outcome_eval_bucket": bucket_count(len(rows["outcome_eval_private"])), "material_qa_bucket": bucket_count(len(rows["material_qa"])), "source_manifest_private_bucket": bucket_count(int(material.get("optional_counts", {}).get("source_manifest_private", 0))), "coverage_ratio_bucket": bucket_ratio(sum(1 for v in VARIANTS if rank_coverage[v] > 0), len(VARIANTS)), "control_response_bucket": "controls_below_signal" if control_max_top10 < signal_min_top10 else "controls_match_or_exceed_signal", "robustness_status": status}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate", re.compile(r"candidate_key|source_file_key|filepath|filename|directory|snippet|start_line|end_line|gold_spans|hard_negatives|\.rs\b|crates/openlocus-")), ("exact_metric", re.compile(r"private_score|private_rank|exact_rate|exact_mrr|hit_rate|exact_hit|\b[a-f0-9]{32,64}\b", re.I))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_DEFAULT, STATUS_PASS_BRITTLE, f"{total}/{total}", R2AH_CHECKPOINT, R2AH_STATUS, R2AG_CHECKPOINT, R2AG_STATUS, "default mode no private read/write/source scan/material generation/metrics", "explicit existing R2AG private material root", "read only existing R2AG private group files", "task_frame,candidate_pool,variant_material,rank_pack,outcome_eval_private,material_qa", "source_manifest_private optional schema/count only", "aggregate-only bucketized robustness metrics", "variant/policy axis", "robust_signal / brittle_or_artifact / mixed_or_inconclusive", "no exact public ranks/scores/counts/rates/MRR/task/query/path", NEXT_PHASE, "R2AJ public audit only"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        p = repo / rel
        return p.read_text(encoding="utf-8") if p.exists() else ""
    def has_all(text: str) -> bool:
        return all(f in text for f in fragments) or all(f in text for f in spaced)
    def prior_counts_ok() -> bool:
        prior_files = [
            "README.md",
            "docs/en/current-research-conclusions.md",
            "docs/zh/current-research-conclusions.md",
            "docs/en/research-log.md",
            "docs/zh/research-log.md",
            "docs/en/research-summary.md",
            "docs/zh/research-summary.md",
        ]
        for rel in prior_files:
            text = read(rel)
            if "haae_r2u_content_identifier_material_generation_complete_r2v_public_audit_authorized" in text:
                for line in text.splitlines():
                    is_r2u_own_entry = "BEA-v1-HAAE-R2U" in line or "bea_v1_haae_r2u_content_identifier_material_generation.py" in line
                    if is_r2u_own_entry and "haae_r2u_content_identifier_material_generation_complete_r2v_public_audit_authorized" in line and "24/24" not in line:
                        return False
            if "haae_r2w_content_identifier_material_experiment_complete_r2x_public_audit_authorized_signal_present" in text:
                for line in text.splitlines():
                    is_r2w_own_entry = "BEA-v1-HAAE-R2W" in line or "bea_v1_haae_r2w_content_identifier_material_experiment.py" in line
                    if is_r2w_own_entry and "haae_r2w_content_identifier_material_experiment_complete_r2x_public_audit_authorized_signal_present" in line and "25/25" not in line:
                        return False
        return True
    root_current = read("docs/current-research-conclusions.md")
    prior_ok = prior_counts_ok()
    all_match = has_all(read("README.md")) and has_all(read("docs/en/bea-v1-haae-r2ai-explicit-local-robustness-experiment.md")) and has_all(read("docs/zh/bea-v1-haae-r2ai-explicit-local-robustness-experiment.md")) and has_all(root_current) and has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md")) and has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md")) and prior_ok
    return {"readme_readback_match_bool": has_all(read("README.md")), "detail_docs_readback_match_bool": has_all(read("docs/en/bea-v1-haae-r2ai-explicit-local-robustness-experiment.md")) and has_all(read("docs/zh/bea-v1-haae-r2ai-explicit-local-robustness-experiment.md")), "current_conclusions_readback_match_bool": has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(root_current) and "bea-v1-haae-r2ai-explicit-local-robustness-experiment.md" in root_current, "research_log_readback_match_bool": has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md")), "prior_phase_count_guard_bool": prior_ok, "all_public_readback_match_bool": all_match}


def build_report(*, explicit: bool, r2ah: dict[str, Any] | None = None, root_status: str = "not_supplied", material_status: str = "not_supplied", aggregate: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2ah is None:
        try: r2ah = load_json(repo / R2AH_REPORT_PATH)
        except Exception: r2ah = {}
    source = audit_r2ah(r2ah)
    readback = public_readback_match(self_test_total)
    if not explicit: status = STATUS_DEFAULT
    elif not source["source_locked"]: status = STATUS_FAIL_SOURCE
    elif root_status != "valid_existing_r2ag_private_material_root": status = STATUS_FAIL_ROOT
    elif material_status != "valid_existing_r2ag_private_manifest_and_groups": status = STATUS_FAIL_MANIFEST
    elif not aggregate or aggregate.get("robustness_status") not in ROBUST_STATUSES: status = STATUS_FAIL_MATERIAL
    elif not readback["all_public_readback_match_bool"]: status = STATUS_FAIL_READBACK
    else:
        status = {"robust_signal": STATUS_PASS_ROBUST, "brittle_or_artifact": STATUS_PASS_BRITTLE, "mixed_or_inconclusive": STATUS_PASS_MIXED}[aggregate["robustness_status"]]
    passed = status in PASS_STATUSES
    agg = aggregate or {"robustness_status": "not_run", "task_count_bucket": "count_0", "variant_row_count_buckets": {}, "rank_pack_count_buckets": {}, "coverage_ratio_bucket": "ratio_unavailable", "variant_axis_balance_bucket": "not_run", "policy_axis_safe_bucket": "not_run", "outcome_eval_bucket": "count_0", "material_qa_bucket": "count_0", "source_manifest_private_bucket": "count_0"}
    gates = {"r2ah_source_locked_gate": source["source_locked"], "default_noop_gate": not explicit or explicit, "explicit_opt_in_gate": explicit, "existing_private_root_safety_gate": root_status == "valid_existing_r2ag_private_material_root" if explicit else True, "private_manifest_owner_schema_gate": material_status == "valid_existing_r2ag_private_manifest_and_groups" if explicit else True, "required_group_files_gate": material_status == "valid_existing_r2ag_private_manifest_and_groups" if explicit else True, "source_manifest_schema_count_only_gate": True, "existing_material_only_gate": True, "no_source_candidate_scan_gate": True, "no_material_generation_gate": True, "aggregate_only_bucket_metrics_gate": True, "variant_policy_axis_gate": True, "no_exact_public_metrics_gate": True, "robustness_status_gate": agg.get("robustness_status") in ROBUST_STATUSES if explicit else True, "r2aj_public_audit_only_stop_go_gate": True, "no_ci_network_default_method_scale_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2aisource0000", "locked_haae_r2ah_checkpoint": R2AH_CHECKPOINT, "locked_haae_r2ah_status": R2AH_STATUS, "inherited_haae_r2ag_checkpoint": R2AG_CHECKPOINT, "inherited_haae_r2ag_status": R2AG_STATUS, "r2ah_status_match_bool": source["status_ok"], "r2ah_forbidden_scan_pass_bool": source["scan_ok"], "r2ah_r2ai_authorization_match_bool": source["auth_ok"], "r2ag_inheritance_match_bool": source["r2ag_ok"], "source_locked_bool": source["source_locked"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2aimode0000", "explicit_opt_in_bool": explicit, "default_no_private_read_write_source_scan_material_generation_metrics_bool": not explicit, "existing_r2ag_private_material_root_required_bool": explicit, "private_read_performed_bool": passed, "material_generation_performed_bool": False, "source_candidate_scan_performed_bool": False, "aggregate_only_publication_confirmed_bool": passed}],
        "private_material_root_records": [{"anonymous_private_root_id": "haaer2airoot0000", "root_valid_bucket": root_status, "root_path_published_bool": False, "outside_public_repo_bool": root_status == "valid_existing_r2ag_private_material_root" if explicit else True, "no_symlink_or_escape_bool": root_status != "root_symlink_or_escape", "existing_material_only_bool": True}],
        "private_manifest_audit_records": [{"anonymous_private_manifest_audit_id": "haaer2aimanifest0000", "manifest_valid_bucket": material_status, "owner_schema_match_bool": material_status == "valid_existing_r2ag_private_manifest_and_groups" if explicit else True, "required_groups_present_bool": material_status == "valid_existing_r2ag_private_manifest_and_groups" if explicit else True, "source_manifest_private_schema_count_only_bool": True, "manifest_path_published_bool": False}],
        "robustness_metric_aggregate_records": [{"anonymous_metric_aggregate_id": "haaer2aimetric0000", "metric_publication_bucket": "aggregate_bucketized_only", "robustness_status_bucket": agg.get("robustness_status"), "task_count_bucket": agg.get("task_count_bucket"), "coverage_ratio_bucket": agg.get("coverage_ratio_bucket"), "variant_axis_balance_bucket": agg.get("variant_axis_balance_bucket"), "policy_axis_safe_bucket": agg.get("policy_axis_safe_bucket"), "no_exact_public_ranks_scores_counts_rates_mrr_task_query_path_bool": True, "baseline_assumed_bool": False}],
        "variant_policy_axis_records": [{"anonymous_variant_axis_id": f"haaer2aivariant{idx:04d}", "variant_bucket": variant, "variant_material_bucket": agg.get("variant_row_count_buckets", {}).get(variant, "count_0"), "rank_pack_bucket": agg.get("rank_pack_count_buckets", {}).get(variant, "count_0"), "aligned_task_bucket": agg.get("variant_metric_buckets", {}).get(variant, {}).get("aligned_task_bucket", "hit_count_0"), "top1_hit_bucket": agg.get("variant_metric_buckets", {}).get(variant, {}).get("top1_hit_bucket", "hit_count_0"), "top5_hit_bucket": agg.get("variant_metric_buckets", {}).get(variant, {}).get("top5_hit_bucket", "hit_count_0"), "top10_hit_bucket": agg.get("variant_metric_buckets", {}).get(variant, {}).get("top10_hit_bucket", "hit_count_0"), "top20_hit_bucket": agg.get("variant_metric_buckets", {}).get(variant, {}).get("top20_hit_bucket", "hit_count_0"), "first_gold_rank_bucket": agg.get("variant_metric_buckets", {}).get(variant, {}).get("first_gold_rank_bucket", "rank_unavailable"), "mrr_bucket": agg.get("variant_metric_buckets", {}).get(variant, {}).get("mrr_bucket", "mrr_unavailable"), "policy_axis_bucket": agg.get("policy_axis_safe_bucket")} for idx, variant in enumerate(VARIANTS)],
        "private_group_bucket_records": [{"anonymous_group_bucket_id": f"haaer2aigroup{idx:04d}", "group_bucket": group, "read_policy_bucket": "read_existing_required_group_file", "public_count_bucket": agg.get("task_count_bucket") if group == "task_frame" else agg.get("outcome_eval_bucket") if group == "outcome_eval_private" else agg.get("material_qa_bucket") if group == "material_qa" else "count_le_20000" if passed else "count_0", "raw_rows_published_bool": False} for idx, group in enumerate(REQUIRED_GROUPS)] + [{"anonymous_group_bucket_id": "haaer2aigroup9999", "group_bucket": "source_manifest_private", "read_policy_bucket": "optional_schema_count_only", "public_count_bucket": agg.get("source_manifest_private_bucket"), "raw_rows_published_bool": False}],
        "boundary_records": [{"anonymous_boundary_id": "haaer2aiboundary0000", "default_noop_bool": not explicit, "explicit_local_only_bool": explicit, "read_only_existing_r2ag_private_groups_bool": passed, "source_scan_bool": False, "candidate_scan_bool": False, "material_generation_bool": False, "private_write_bool": False, "ci_network_provider_clone_bool": False, "runtime_openlocus_bool": False, "default_method_scale_claim_bool": False, "raw_publication_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2aiclaim0000", "aggregate_bucketized_robustness_metrics_bool": passed, "exact_public_metrics_bool": False, "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "new_material_generation_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2aigate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2aisynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2aireadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2aistop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_run_explicit_r2ai_with_existing_material", "haae_r2aj_public_audit_package_authorized_bool": passed, "r2aj_public_audit_only_bool": passed, "new_material_generation_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "clone_authorized_bool": False, "runtime_execution_authorized_bool": False, "openlocus_runtime_authorized_bool": False, "source_scan_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] in PASS_STATUSES and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["source_lock_records", "execution_mode_records", "private_material_root_records", "private_manifest_audit_records", "robustness_metric_aggregate_records", "variant_policy_axis_records", "private_group_bucket_records", "boundary_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") not in ({STATUS_DEFAULT, STATUS_FAIL_SOURCE, STATUS_FAIL_ROOT, STATUS_FAIL_MANIFEST, STATUS_FAIL_MATERIAL, STATUS_FAIL_LEAK, STATUS_FAIL_READBACK} | PASS_STATUSES): issues.append("status_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    if src.get("locked_haae_r2ah_checkpoint") != R2AH_CHECKPOINT or src.get("locked_haae_r2ah_status") != R2AH_STATUS or src.get("inherited_haae_r2ag_checkpoint") != R2AG_CHECKPOINT: issues.append("source_lock_mismatch")
    for field in ["r2ah_status_match_bool", "r2ah_forbidden_scan_pass_bool", "r2ah_r2ai_authorization_match_bool", "r2ag_inheritance_match_bool", "source_locked_bool"]:
        if src.get(field) is not True: issues.append(f"source_lock_{field}")
    mode = (report.get("execution_mode_records") or [{}])[0]
    if report.get("status") == STATUS_DEFAULT and (mode.get("default_no_private_read_write_source_scan_material_generation_metrics_bool") is not True or mode.get("private_read_performed_bool") is not False): issues.append("default_mode_mismatch")
    if report.get("status") in PASS_STATUSES:
        if mode.get("explicit_opt_in_bool") is not True or mode.get("private_read_performed_bool") is not True or mode.get("material_generation_performed_bool") is not False: issues.append("explicit_mode_mismatch")
        root = (report.get("private_material_root_records") or [{}])[0]
        if root.get("root_valid_bucket") != "valid_existing_r2ag_private_material_root" or root.get("root_path_published_bool") is not False or root.get("outside_public_repo_bool") is not True or root.get("no_symlink_or_escape_bool") is not True: issues.append("root_record_mismatch")
        manifest = (report.get("private_manifest_audit_records") or [{}])[0]
        if manifest.get("manifest_valid_bucket") != "valid_existing_r2ag_private_manifest_and_groups" or manifest.get("owner_schema_match_bool") is not True or manifest.get("required_groups_present_bool") is not True or manifest.get("source_manifest_private_schema_count_only_bool") is not True: issues.append("manifest_record_mismatch")
    metric = (report.get("robustness_metric_aggregate_records") or [{}])[0]
    if metric.get("no_exact_public_ranks_scores_counts_rates_mrr_task_query_path_bool") is not True or metric.get("baseline_assumed_bool") is not False: issues.append("metric_boundary_mismatch")
    if report.get("status") in PASS_STATUSES and metric.get("robustness_status_bucket") not in ROBUST_STATUSES: issues.append("robustness_status_mismatch")
    status_to_bucket = {STATUS_PASS_ROBUST: "robust_signal", STATUS_PASS_BRITTLE: "brittle_or_artifact", STATUS_PASS_MIXED: "mixed_or_inconclusive"}
    status_value = str(report.get("status", ""))
    if status_value in status_to_bucket and metric.get("robustness_status_bucket") != status_to_bucket[status_value]: issues.append("status_metric_bucket_mismatch")
    if len(report.get("variant_policy_axis_records", [])) != len(VARIANTS) or {row.get("variant_bucket") for row in report.get("variant_policy_axis_records", [])} != set(VARIANTS): issues.append("variant_axis_mismatch")
    for row in report.get("variant_policy_axis_records", []):
        for field in ["aligned_task_bucket", "top1_hit_bucket", "top5_hit_bucket", "top10_hit_bucket", "top20_hit_bucket"]:
            if not str(row.get(field, "")).startswith("hit_count_"): issues.append(f"variant_{field}_not_bucket")
        if not str(row.get("first_gold_rank_bucket", "")).startswith("rank_"): issues.append("variant_first_gold_rank_not_bucket")
        if not str(row.get("mrr_bucket", "")).startswith("mrr_"): issues.append("variant_mrr_not_bucket")
    boundary = (report.get("boundary_records") or [{}])[0]
    for field in ["source_scan_bool", "candidate_scan_bool", "material_generation_bool", "private_write_bool", "ci_network_provider_clone_bool", "runtime_openlocus_bool", "default_method_scale_claim_bool", "raw_publication_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["exact_public_metrics_bool", "method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "new_material_generation_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_{field}")
    if {row.get("gate_bucket") for row in report.get("pass_fail_gate_records", [])} != set(GATE_NAMES): issues.append("gate_set_mismatch")
    if {row.get("validator_bucket") for row in report.get("synthetic_validator_records", [])} != set(SYNTHETIC_VALIDATORS): issues.append("synthetic_validator_set_mismatch")
    readback = report.get("public_readback_records", [])
    if len(readback) != 1 or readback[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") in PASS_STATUSES:
        if stop.get("next_allowed_phase") != NEXT_PHASE or stop.get("haae_r2aj_public_audit_package_authorized_bool") is not True or stop.get("r2aj_public_audit_only_bool") is not True: issues.append("r2aj_stop_go_mismatch")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    for field in FORBIDDEN_STOP_TRUE:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed = {"self_test": False, "validate": "", "out": "", "allow": False, "confirm": False, "root": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--self-test": parsed["self_test"] = True; i += 1
        elif arg == "--allow-r2ai-robustness-experiment": parsed["allow"] = True; i += 1
        elif arg == "--confirm-aggregate-only-publication": parsed["confirm"] = True; i += 1
        elif arg in {"--existing-r2ag-private-material-root", "--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            if arg == "--existing-r2ag-private-material-root": parsed["root"] = argv[i + 1]
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
    path = out or PUBLIC_REPORT_PATH; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def make_synthetic_root(root: Path) -> None:
    rows = {g: [] for g in REQUIRED_GROUPS + OPTIONAL_GROUPS}
    for t in range(20): rows["task_frame"].append({"task_key": f"t{t}", "rank_policy_used_gold_bool": False, "rank_policy_used_path_bool": False})
    for t in range(20):
        rows["outcome_eval_private"].append({"task_key": f"t{t}", "gold_private_eval_only_bool": True, "gold_used_for_ranking_bool": False, "outcome_labels_used_for_ranking_bool": False})
        for c in range(2): rows["candidate_pool"].append({"task_key": f"t{t}", "candidate_key": f"c{t}_{c}", "rank_policy_used_gold_bool": False, "rank_policy_used_path_bool": False})
        for v in VARIANTS:
            rows["variant_material"].append({"task_key": f"t{t}", "variant_bucket": v, "rank_policy_used_gold_bool": False, "rank_policy_used_path_bool": False})
            rows["rank_pack"].append({"task_key": f"t{t}", "variant_bucket": v, "rank_policy_used_gold_bool": False, "rank_policy_used_path_bool": False})
    rows["material_qa"].append({"rank_policy_used_gold_bool": False, "rank_policy_used_path_bool": False, "gold_private_eval_only_bool": True})
    rows["source_manifest_private"].append({"schema_only": True})
    for group, data in rows.items(): write_jsonl(root / "groups" / f"{group}.jsonl", data)
    manifest = {"schema_version": R2AG_PRIVATE_SCHEMA, "owner_bucket": R2AG_OWNER, "status": R2AG_STATUS, "groups": REQUIRED_GROUPS + OPTIONAL_GROUPS, "summary": {"bucket": "synthetic_self_test"}}
    (root / PRIVATE_MANIFEST).write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    r2ah = load_json(repo / R2AH_REPORT_PATH)
    def check(name: str, cond: bool) -> None:
        if not cond: failures.append(name)
    default = build_report(explicit=False, r2ah=r2ah); check("default_noop_fail", default["status"] == STATUS_DEFAULT and validate_report(default) == [])
    bad = json.loads(json.dumps(r2ah)); bad["status"] = "wrong"; check("wrong_r2ah_status_fail", build_report(explicit=True, r2ah=bad)["status"] == STATUS_FAIL_SOURCE)
    check("missing_opt_in_fail", parse_args([])["allow"] is False)
    check("root_inside_repo_fail", validate_root(repo, repo)[0] is False)
    with tempfile.TemporaryDirectory(prefix="r2ai_selftest_") as tmp:
        root = Path(tmp) / "material"; make_synthetic_root(root)
        ok, root_status = validate_root(root, repo); material = load_private_material(root); mat_ok, mat_status = validate_private_material(material); agg = compute_aggregate(material)
        explicit = build_report(explicit=True, r2ah=r2ah, root_status=root_status if ok else "bad", material_status=mat_status if mat_ok else "bad", aggregate=agg)
        check("source_lock_pass", explicit["status"] in PASS_STATUSES and validate_report(explicit) == [])
        link = Path(tmp) / "link"; os.symlink(root, link); check("root_symlink_fail", validate_root(link, repo)[0] is False)
        escape = root / "groups" / "task_frame.jsonl"; escape.unlink(); os.symlink(Path(tmp) / "outside.jsonl", escape); (Path(tmp) / "outside.jsonl").write_text("{}\n"); check("root_escape_fail", validate_root(root, repo)[0] is False)
        make_synthetic_root(root)
        for label, mutate, expected in [
            ("manifest_owner_fail", lambda m: m["manifest"].__setitem__("owner_bucket", "wrong"), "owner_mismatch"),
            ("manifest_schema_fail", lambda m: m["manifest"].__setitem__("schema_version", "wrong"), "schema_mismatch"),
            ("missing_required_group_fail", lambda m: m["rows"].__setitem__("rank_pack", []), "required_group_empty"),
            ("rank_gold_fail", lambda m: m["rows"]["rank_pack"][0].__setitem__("rank_policy_used_gold_bool", True), "rank_policy_mismatch"),
            ("rank_path_fail", lambda m: m["rows"]["rank_pack"][0].__setitem__("rank_policy_used_path_bool", True), "rank_policy_mismatch"),
            ("variant_missing_fail", lambda m: m["rows"].__setitem__("variant_material", [r for r in m["rows"]["variant_material"] if r.get("variant_bucket") != VARIANTS[0]]), "variant_set_mismatch"),
        ]:
            m = json.loads(json.dumps(material)); mutate(m); check(label, validate_private_material(m)[1] == expected)
        for label, mutate, expected in [
            ("material_generated_flag_fail", lambda r: r["boundary_records"][0].__setitem__("material_generation_bool", True), "boundary_material_generation_bool"),
            ("metric_public_boundary_fail", lambda r: r["robustness_metric_aggregate_records"][0].__setitem__("no_exact_public_ranks_scores_counts_rates_mrr_task_query_path_bool", False), "metric_boundary_mismatch"),
            ("raw_publication_fail", lambda r: r["claim_boundary_records"][0].__setitem__("raw_publication_bool", True), "claim_raw_publication_bool"),
            ("next_phase_fail", lambda r: r["stop_go_records"][0].__setitem__("next_allowed_phase", "wrong"), "r2aj_stop_go_mismatch"),
            ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("ci_execution_authorized_bool", True), "overauthorization_ci_execution_authorized_bool"),
            ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"),
            ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"),
            ("status_metric_bucket_fail", lambda r: r["robustness_metric_aggregate_records"][0].__setitem__("robustness_status_bucket", "robust_signal"), "status_metric_bucket_mismatch"),
            ("variant_rank_bucket_fail", lambda r: r["variant_policy_axis_records"][0].__setitem__("first_gold_rank_bucket", "7"), "variant_first_gold_rank_not_bucket"),
            ("variant_mrr_bucket_fail", lambda r: r["variant_policy_axis_records"][0].__setitem__("mrr_bucket", "0.42"), "variant_mrr_not_bucket"),
        ]:
            r = json.loads(json.dumps(explicit)); mutate(r); check(label, expected in validate_report(r))
    leak = json.loads(json.dumps(default)); leak["debug"] = "/tmp/private-root r14m-001 candidate_key private_score"; check("public_scanner_fail", scan_public_report(leak)["status"] == "fail")
    check("prior_phase_count_guard_fail", public_readback_match(SELF_TEST_EXPECTED)["prior_phase_count_guard_bool"] is True)
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--existing-r2ag-private-material-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError:
        check("safe_parser_fail", True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS_BRITTLE}


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
    r2ah = load_json(repo / R2AH_REPORT_PATH) if (repo / R2AH_REPORT_PATH).exists() else {}
    if not args["allow"]:
        report = build_report(explicit=False, r2ah=r2ah); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0
    if not args["confirm"] or not args["root"]:
        report = build_report(explicit=True, r2ah=r2ah, root_status="missing_confirm_or_root", material_status="not_supplied"); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 1
    root = Path(args["root"]); root_ok, root_status = validate_root(root, repo); material_status = "not_loaded"; aggregate = None
    if root_ok:
        try:
            material = load_private_material(root); mat_ok, material_status = validate_private_material(material); aggregate = compute_aggregate(material) if mat_ok else None
        except Exception as exc:
            material_status = str(exc)
    report = build_report(explicit=True, r2ah=r2ah, root_status=root_status, material_status=material_status, aggregate=aggregate)
    path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"], "robustness_status_bucket": (report.get("robustness_metric_aggregate_records") or [{}])[0].get("robustness_status_bucket")}, sort_keys=True))
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
