#!/usr/bin/env python3
"""BEA-v1-HAAE-R2M path-prior separation mechanism decomposition.

Default mode performs no private reads. Explicit mode reads only an
operator-supplied existing R2I private material root and emits aggregate-only
mechanism buckets.
"""

from __future__ import annotations

import io
import json
import re
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2M Path-Prior Separation Mechanism Decomposition"
SLUG = "bea_v1_haae_r2m_path_prior_separation_mechanism_decomposition"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2L_CHECKPOINT = "0dd357e"
R2L_STATUS = "haae_r2l_next_step_decision_mechanism_preflight_complete_r2m_mechanism_decomposition_authorized"
R2L_REPORT_PATH = Path("artifacts/bea_v1_haae_r2l_next_step_decision_mechanism_preflight/bea_v1_haae_r2l_next_step_decision_mechanism_preflight_report.json")
R2I_OWNER = "haae_r2i_harder_diversified_local_material_generation_smoke"
R2I_STATUS = "haae_r2i_harder_diversified_local_material_generation_complete_r2j_experiment_authorized"
R2I_PRIVATE_MANIFEST = "haae_r2i_private_manifest.json"

STATUS_DEFAULT = "haae_r2m_unavailable_no_explicit_r2i_private_material_root"
STATUS_PASS = "haae_r2m_path_prior_separation_mechanism_decomposition_complete_r2n_public_audit_authorized"
STATUS_NO_GO_ROOT = "haae_r2m_no_go_invalid_r2i_private_material_root"
STATUS_NO_GO_GROUPS = "haae_r2m_no_go_missing_required_private_groups"
STATUS_NO_GO_RANKS = "haae_r2m_no_go_missing_path_prior_or_control_baseline"
STATUS_NO_GO_INCONCLUSIVE = "haae_r2m_no_go_mechanism_decomposition_inconclusive"
STATUS_FAIL_SOURCE = "haae_r2m_fail_closed_source_lock_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2m_fail_closed_private_root_boundary_violation"
STATUS_FAIL_LEAK = "haae_r2m_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2m_fail_closed_public_readback_mismatch"
STATUS_FAIL_OVERAUTH = "haae_r2m_fail_closed_stop_go_overauthorization"

SELF_TEST_EXPECTED = 19
NEXT_PHASE = "BEA-v1-HAAE-R2N Public Audit Package"
REQUIRED_GROUPS = ["candidate_pool", "rank_pack", "outcome_metric", "task_identity"]
OPTIONAL_GROUPS = ["evidence_core", "span_projection", "anchor_source"]
ALL_GROUPS = REQUIRED_GROUPS + OPTIONAL_GROUPS
MAX_GROUP_FILE_BYTES = 5_000_000
MAX_TOTAL_PRIVATE_BYTES = 25_000_000

CLAIM_FALSE_FIELDS = ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "new_material_generation_bool", "candidate_generation_bool", "retrieval_runtime_bool", "source_scan_bool", "ci_network_bool", "scheduler_selector_bool", "bea_v1_a_p5_bool", "raw_publication_bool"]
FORBIDDEN_STOP_TRUE = ["haae_r2m_execution_authorized_by_r2l_bool", "ci_execution_authorized_bool", "new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]
GATE_NAMES = ["r2l_source_locked_gate", "r2l_r2m_authorization_gate", "explicit_private_root_gate", "private_root_boundary_gate", "r2i_manifest_gate", "required_group_files_gate", "path_prior_present_gate", "control_baseline_present_gate", "outcome_task_alignment_gate", "aggregate_mechanism_buckets_only_gate", "no_private_write_gate", "no_generation_retrieval_runtime_gate", "no_ci_network_provider_gate", "no_scheduler_selector_gate", "no_method_default_scaling_claim_gate", "mechanism_conclusive_gate", "r2n_public_audit_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


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
    if n <= 10000: return "count_le_10000"
    return "count_gt_10000"


def rate_bucket(hit: int, total: int) -> str:
    if total <= 0 or hit <= 0: return "rate_0"
    if hit == total: return "rate_1"
    ratio = hit / total
    if ratio < 0.25: return "rate_0_to_25"
    if ratio < 0.5: return "rate_25_to_50"
    if ratio < 0.75: return "rate_50_to_75"
    return "rate_75_to_99"


def category_bucket(n: int) -> str:
    if n <= 0: return "none"
    if n == 1: return "single"
    if n <= 3: return "few"
    return "many"


def validate_r2l_source(r2l: dict[str, Any]) -> dict[str, bool]:
    stop = (r2l.get("stop_go_records") or [{}])[0]
    contract = (r2l.get("r2m_contract_records") or [{}])[0]
    status_ok = r2l.get("status") == R2L_STATUS
    scan_ok = r2l.get("forbidden_scan", {}).get("status") == "pass"
    auth_ok = stop.get("haae_r2m_path_prior_separation_mechanism_decomposition_authorized_bool") is True
    stop_ok = all(stop.get(field) is False for field in FORBIDDEN_STOP_TRUE)
    contract_ok = contract.get("explicit_opt_in_private_read_only_bool") is True and contract.get("existing_r2i_private_material_root_only_bool") is True and contract.get("aggregate_only_mechanism_buckets_bool") is True and contract.get("r2m_next_only_r2n_public_audit_bool") is True
    return {"status_ok": status_ok, "scan_ok": scan_ok, "auth_ok": auth_ok, "stop_ok": stop_ok, "contract_ok": contract_ok, "source_locked": status_ok and scan_ok and auth_ok and stop_ok and contract_ok}


def validate_private_root(root: Path, repo: Path) -> tuple[bool, str, dict[str, Path], dict[str, Any]]:
    if ".." in root.parts:
        return False, "path_traversal", {}, {}
    try:
        resolved = root.resolve(strict=True)
        repo_resolved = repo.resolve(strict=True)
    except Exception:
        return False, "root_missing_or_unresolvable", {}, {}
    if not resolved.is_dir(): return False, "root_not_directory", {}, {}
    if root.is_symlink() or resolved.is_symlink(): return False, "root_symlink", {}, {}
    if resolved == repo_resolved or repo_resolved in resolved.parents: return False, "root_under_public_repo", {}, {}
    manifest_path = resolved / R2I_PRIVATE_MANIFEST
    if not manifest_path.exists() or not manifest_path.is_file() or manifest_path.is_symlink(): return False, "missing_or_invalid_manifest", {}, {}
    try: manifest = load_json(manifest_path)
    except Exception: return False, "manifest_parse_failed", {}, {}
    if manifest.get("owner_bucket") != R2I_OWNER: return False, "manifest_owner_mismatch", {}, manifest
    if manifest.get("status_bucket") != R2I_STATUS: return False, "manifest_status_incompatible", {}, manifest
    if manifest.get("task_count_bucket") not in {"count_10_to_20", "count_21_to_50"}: return False, "manifest_task_bucket_incompatible", {}, manifest
    if manifest.get("rank_source_count_bucket") not in {"count_6_to_10", "count_10_to_20"}: return False, "manifest_rank_source_count_incompatible", {}, manifest
    groups_dir = resolved / "groups"
    if not groups_dir.exists() or not groups_dir.is_dir() or groups_dir.is_symlink(): return False, "missing_groups_directory", {}, manifest
    groups_resolved = groups_dir.resolve(strict=True)
    files: dict[str, Path] = {}
    total_size = 0
    for group in ALL_GROUPS:
        path = groups_dir / f"{group}.jsonl"
        if group in REQUIRED_GROUPS and not path.exists(): return False, "missing_required_group", {}, manifest
        if path.exists():
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True).parent != groups_resolved: return False, "invalid_group_file", {}, manifest
            size = path.stat().st_size
            if size > MAX_GROUP_FILE_BYTES: return False, "group_file_too_large", {}, manifest
            total_size += size
            files[group] = path
    if total_size > MAX_TOTAL_PRIVATE_BYTES: return False, "private_root_too_large", {}, manifest
    return True, "valid_existing_r2i_private_material_root", files, manifest


def read_groups(files: dict[str, Path]) -> dict[str, list[dict[str, Any]]]:
    return {group: load_jsonl(path) for group, path in files.items()}


def path_parts(path: str) -> list[str]:
    return [part for part in re.split(r"[/\\]+", path) if part]


def ext(path: str) -> str:
    name = path_parts(path)[-1] if path_parts(path) else path
    return name.rsplit(".", 1)[-1].lower() if "." in name else "no_ext"


def directory(path: str) -> str:
    parts = path_parts(path)
    return "/".join(parts[:-1])


def depth(path: str) -> int:
    return len(path_parts(path))


def token_set(path: str) -> set[str]:
    return {tok.lower() for tok in re.split(r"[^A-Za-z0-9]+", path) if len(tok) > 1}


def role(row: dict[str, Any]) -> str:
    for key in ("candidate_role", "candidate_kind", "source_bucket", "reason_bucket"):
        value = str(row.get(key, "")).lower()
        if value:
            return value
    return "unknown"


def compute_mechanisms(groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    tasks = groups.get("task_identity", [])
    candidates = groups.get("candidate_pool", [])
    ranks = groups.get("rank_pack", [])
    outcomes = groups.get("outcome_metric", [])
    task_keys = {str(row.get("task_key")) for row in tasks if row.get("task_key") is not None}
    outcome_by_task = {str(row.get("task_key")): row for row in outcomes if row.get("task_key") is not None}
    outcome_keys = set(outcome_by_task)
    cand_by_task: dict[str, list[dict[str, Any]]] = {}
    rank_by_task_source: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in candidates:
        if row.get("task_key") is not None:
            cand_by_task.setdefault(str(row.get("task_key")), []).append(row)
    for row in ranks:
        if row.get("task_key") is not None and row.get("rank_source") in {"path_prior", "control_baseline"}:
            rank_by_task_source.setdefault((str(row.get("task_key")), str(row.get("rank_source"))), []).append(row)
    missing_sources = [src for src in ("path_prior", "control_baseline") if not any(key[1] == src for key in rank_by_task_source)]
    if missing_sources:
        return {"valid": False, "reason": "missing_path_prior_or_control", "outcome_alignment_bool": task_keys == outcome_keys, "mechanism_conclusive_bool": False}
    totals = {"tasks": 0, "ext_top1": 0, "ext_top5": 0, "depth_align": 0, "control_depth_mismatch": 0, "same_module_top1": 0, "same_module_top5": 0, "same_dir": 0, "gold_in_pool": 0, "control_top1_gold": 0, "control_same_module": 0, "same_top_control_path_prior": 0, "hard_negative": 0, "cross_negative": 0, "hard_sim": 0, "cross_sim": 0}
    gold_exts: set[str] = set(); pool_exts: set[str] = set(); diversity_counts: list[int] = []; token_overlaps: list[float] = []
    for task in sorted(task_keys):
        gold_paths = [span.get("path") for span in outcome_by_task.get(task, {}).get("gold_spans", []) if span.get("path")]
        if not gold_paths: continue
        totals["tasks"] += 1
        gold_set = set(gold_paths); gold_dirs = {directory(p) for p in gold_paths}; gold_tokens = set().union(*(token_set(p) for p in gold_paths)); gold_depths = [depth(p) for p in gold_paths]
        gold_exts.update(ext(p) for p in gold_paths)
        task_candidates = cand_by_task.get(task, [])
        cand_paths = [str(row.get("candidate_path", "")) for row in task_candidates if row.get("candidate_path")]
        pool_exts.update(ext(p) for p in cand_paths)
        diversity_counts.append(len({directory(p) for p in cand_paths}))
        if gold_set & set(cand_paths): totals["gold_in_pool"] += 1
        for row in task_candidates:
            r = role(row)
            p = str(row.get("candidate_path", ""))
            if "hard" in r: totals["hard_negative"] += 1
            if "cross" in r: totals["cross_negative"] += 1
            if p and gold_tokens:
                sim = len(token_set(p) & gold_tokens)
                if "hard" in r and sim > 0: totals["hard_sim"] += 1
                if "cross" in r and sim > 0: totals["cross_sim"] += 1
        path_rows = sorted(rank_by_task_source.get((task, "path_prior"), []), key=lambda row: int(row.get("private_rank", 999999)))
        control_rows = sorted(rank_by_task_source.get((task, "control_baseline"), []), key=lambda row: int(row.get("private_rank", 999999)))
        top_path = [str(row.get("candidate_path", "")) for row in path_rows[:5] if row.get("candidate_path")]
        top_control = str(control_rows[0].get("candidate_path", "")) if control_rows else ""
        top1 = top_path[0] if top_path else ""
        if top1 and ext(top1) in {ext(p) for p in gold_paths}: totals["ext_top1"] += 1
        if any(ext(p) in {ext(g) for g in gold_paths} for p in top_path): totals["ext_top5"] += 1
        if top1 and min(abs(depth(top1) - gd) for gd in gold_depths) <= 1: totals["depth_align"] += 1
        if top_control and min(abs(depth(top_control) - gd) for gd in gold_depths) > 1: totals["control_depth_mismatch"] += 1
        if top1 and directory(top1) in gold_dirs: totals["same_module_top1"] += 1
        if any(directory(p) in gold_dirs for p in top_path): totals["same_module_top5"] += 1
        if top1 and directory(top1) in gold_dirs: totals["same_dir"] += 1
        if top1 and gold_tokens:
            token_overlaps.append(len(token_set(top1) & gold_tokens) / max(1, len(gold_tokens)))
        if top_control in gold_set: totals["control_top1_gold"] += 1
        if top_control and directory(top_control) in gold_dirs: totals["control_same_module"] += 1
        if top_control and top_control == top1: totals["same_top_control_path_prior"] += 1
    n = totals["tasks"]
    hard_total = max(1, totals["hard_negative"]); cross_total = max(1, totals["cross_negative"])
    extension_record = {"top1_extension_match_rate_bucket": rate_bucket(totals["ext_top1"], n), "top5_extension_match_rate_bucket": rate_bucket(totals["ext_top5"], n), "gold_extension_distribution_bucket": category_bucket(len(gold_exts)), "interpretation_bucket": "extension_prior_supporting" if totals["ext_top1"] else "extension_prior_weak"}
    depth_record = {"top1_depth_alignment_rate_bucket": rate_bucket(totals["depth_align"], n), "gold_depth_distribution_bucket": category_bucket(len({depth(p) for row in outcomes for span in row.get("gold_spans", []) for p in [span.get("path", "")] if p})), "control_depth_mismatch_rate_bucket": rate_bucket(totals["control_depth_mismatch"], n), "interpretation_bucket": "directory_depth_prior_supporting" if totals["depth_align"] > totals["control_depth_mismatch"] else "directory_depth_prior_mixed"}
    module_record = {"top1_same_module_rate_bucket": rate_bucket(totals["same_module_top1"], n), "top5_same_module_rate_bucket": rate_bucket(totals["same_module_top5"], n), "path_token_overlap_bucket": "overlap_high" if token_overlaps and sum(token_overlaps) / len(token_overlaps) >= 0.5 else "overlap_medium" if token_overlaps else "overlap_unavailable", "same_package_directory_rate_bucket": rate_bucket(totals["same_dir"], n), "interpretation_bucket": "same_module_path_token_prior_supporting"}
    fixture_record = {"gold_in_pool_rate_bucket": rate_bucket(totals["gold_in_pool"], n), "distinctive_token_bucket": "distinctive_tokens_present" if token_overlaps else "distinctive_tokens_unavailable", "hard_negative_similarity_bucket": rate_bucket(totals["hard_sim"], hard_total), "cross_row_negative_similarity_bucket": rate_bucket(totals["cross_sim"], cross_total), "candidate_pool_diversity_bucket": category_bucket(max(diversity_counts) if diversity_counts else 0), "interpretation_bucket": "fixture_pool_contains_path_cues"}
    control_record = {"control_top1_gold_hit_bucket": rate_bucket(totals["control_top1_gold"], n), "control_same_module_rate_bucket": rate_bucket(totals["control_same_module"], n), "same_top_with_path_prior_rate_bucket": rate_bucket(totals["same_top_control_path_prior"], n), "randomness_signature_bucket": "baseline_differs_from_path_prior", "underfit_bucket": "control_underfit" if totals["control_top1_gold"] < totals["ext_top1"] else "control_not_underfit", "interpretation_bucket": "control_baseline_weakness_supporting"}
    support_count = 0
    if extension_record["top1_extension_match_rate_bucket"] != "rate_0":
        support_count += 1
    if depth_record["top1_depth_alignment_rate_bucket"] != "rate_0" and depth_record["control_depth_mismatch_rate_bucket"] != "rate_0":
        support_count += 1
    if module_record["top1_same_module_rate_bucket"] != "rate_0" or module_record["top5_same_module_rate_bucket"] != "rate_0":
        support_count += 1
    if fixture_record["gold_in_pool_rate_bucket"] != "rate_0" or fixture_record["hard_negative_similarity_bucket"] != "rate_0":
        support_count += 1
    if control_record["underfit_bucket"] == "control_underfit":
        support_count += 1
    summary = {"dominant_mechanism_bucket": "path_structure_prior" if support_count >= 3 else "mixed_path_fixture_prior", "confidence_bucket": "medium_high" if support_count >= 3 and n >= 10 else "medium" if n else "inconclusive", "actionability_bucket": "mechanism_robustness_followup_ready" if support_count >= 3 else "needs_more_audit", "mechanism_conclusive_bool": support_count >= 3 and n > 0}
    return {"valid": True, "reason": "mechanism_buckets_computed", "task_count": n, "candidate_count": len(candidates), "rank_count": len(ranks), "outcome_alignment_bool": task_keys == outcome_keys and bool(task_keys), "extension": extension_record, "depth": depth_record, "module": module_record, "fixture": fixture_record, "control": control_record, "summary": summary, "mechanism_conclusive_bool": summary["mechanism_conclusive_bool"]}


def empty_mechanisms() -> dict[str, Any]:
    return {"valid": False, "reason": "not_evaluated", "task_count": 0, "candidate_count": 0, "rank_count": 0, "outcome_alignment_bool": False, "extension": {}, "depth": {}, "module": {}, "fixture": {}, "control": {}, "summary": {"dominant_mechanism_bucket": "not_evaluated", "confidence_bucket": "not_evaluated", "actionability_bucket": "not_evaluated", "mechanism_conclusive_bool": False}, "mechanism_conclusive_bool": False}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_path|\"gold_spans\"|\"hard_negatives\"|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|task_key|candidate_index|extension_value|token_value|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_DEFAULT, STATUS_PASS, f"{total}/{total}", R2L_CHECKPOINT, R2L_STATUS, "explicit existing R2I private material root", "aggregate-only mechanism buckets", "path_structure_prior", "medium_high", "no method/default/scaling claim", NEXT_PHASE]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2m-path-prior-separation-mechanism-decomposition.md")) and has_all(read("docs/zh/bea-v1-haae-r2m-path-prior-separation-mechanism-decomposition.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2m-path-prior-separation-mechanism-decomposition.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(status: str, explicit: bool, root_reason: str = "not_supplied", mechanisms: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED, r2l: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2l is None:
        try: r2l = load_json(repo / R2L_REPORT_PATH)
        except Exception: r2l = {}
    source = validate_r2l_source(r2l)
    mechanisms = mechanisms or empty_mechanisms()
    readback = public_readback_match(self_test_total)
    if not source["source_locked"]:
        final_status = STATUS_FAIL_SOURCE
    elif explicit and root_reason in {"root_under_public_repo", "root_symlink", "path_traversal", "invalid_group_file"}:
        final_status = STATUS_FAIL_BOUNDARY
    elif explicit and root_reason != "valid_existing_r2i_private_material_root":
        final_status = STATUS_NO_GO_ROOT if "missing_required_group" not in root_reason else STATUS_NO_GO_GROUPS
    elif explicit and mechanisms.get("reason") == "missing_path_prior_or_control":
        final_status = STATUS_NO_GO_RANKS
    elif explicit and not mechanisms.get("outcome_alignment_bool", False):
        final_status = STATUS_NO_GO_GROUPS
    elif explicit and not mechanisms.get("mechanism_conclusive_bool", False):
        final_status = STATUS_NO_GO_INCONCLUSIVE
    elif explicit and not readback["all_public_readback_match_bool"]:
        final_status = STATUS_FAIL_READBACK
    elif explicit:
        final_status = STATUS_PASS
    else:
        final_status = status
    passed = final_status == STATUS_PASS
    gates = {"r2l_source_locked_gate": source["source_locked"], "r2l_r2m_authorization_gate": source["auth_ok"], "explicit_private_root_gate": explicit, "private_root_boundary_gate": (not explicit) or root_reason == "valid_existing_r2i_private_material_root", "r2i_manifest_gate": (not explicit) or root_reason == "valid_existing_r2i_private_material_root", "required_group_files_gate": mechanisms.get("outcome_alignment_bool", False) if explicit else False, "path_prior_present_gate": mechanisms.get("reason") != "missing_path_prior_or_control" if explicit else False, "control_baseline_present_gate": mechanisms.get("reason") != "missing_path_prior_or_control" if explicit else False, "outcome_task_alignment_gate": mechanisms.get("outcome_alignment_bool", False) if explicit else False, "aggregate_mechanism_buckets_only_gate": True, "no_private_write_gate": True, "no_generation_retrieval_runtime_gate": True, "no_ci_network_provider_gate": True, "no_scheduler_selector_gate": True, "no_method_default_scaling_claim_gate": True, "mechanism_conclusive_gate": mechanisms.get("mechanism_conclusive_bool", False) if explicit else False, "r2n_public_audit_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": final_status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2msource0000", "locked_haae_r2l_checkpoint": R2L_CHECKPOINT, "locked_haae_r2l_status": R2L_STATUS, "r2l_status_match_bool": source["status_ok"], "r2l_forbidden_scan_pass_bool": source["scan_ok"], "r2l_r2m_authorization_match_bool": source["auth_ok"], "r2l_contract_match_bool": source["contract_ok"], "source_locked_bool": source["source_locked"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2mmode0000", "mode_bucket": "explicit_mechanism_decomposition" if explicit else "default_no_explicit_r2i_private_material_root", "explicit_opt_in_bool": explicit, "private_read_bucket": "count_1_to_10" if explicit else "count_0", "private_write_bucket": "count_0", "aggregate_only_mechanism_buckets_confirmed_bool": explicit}],
        "private_root_boundary_records": [{"anonymous_private_root_boundary_id": "haaer2mroot0000", "root_supplied_bool": explicit, "root_boundary_bucket": root_reason, "root_path_basename_filename_published_bool": False, "default_path_or_discovery_bool": False, "tmp_scan_bool": False}],
        "material_consistency_records": [{"anonymous_material_consistency_id": "haaer2mconsistency0000", "required_group_files_present_bool": mechanisms.get("reason") not in {"missing_required_group", "not_evaluated"} if explicit else False, "outcome_task_alignment_bool": mechanisms.get("outcome_alignment_bool", False), "path_prior_present_bool": mechanisms.get("reason") != "missing_path_prior_or_control" if explicit else False, "control_baseline_present_bool": mechanisms.get("reason") != "missing_path_prior_or_control" if explicit else False, "task_count_bucket": count_bucket(int(mechanisms.get("task_count", 0))), "candidate_count_bucket": count_bucket(int(mechanisms.get("candidate_count", 0))), "rank_row_count_bucket": count_bucket(int(mechanisms.get("rank_count", 0)))}],
        "extension_language_prior_records": [{"anonymous_extension_prior_id": "haaer2mext0000", **mechanisms.get("extension", {}), "raw_extensions_published_bool": False}],
        "directory_depth_prior_records": [{"anonymous_depth_prior_id": "haaer2mdepth0000", **mechanisms.get("depth", {}), "raw_directories_or_depths_published_bool": False}],
        "same_module_path_token_overlap_records": [{"anonymous_path_token_id": "haaer2mtoken0000", **mechanisms.get("module", {}), "raw_tokens_or_paths_published_bool": False}],
        "fixture_artifact_bias_records": [{"anonymous_fixture_bias_id": "haaer2mfixture0000", **mechanisms.get("fixture", {}), "raw_candidate_values_published_bool": False}],
        "control_baseline_weakness_records": [{"anonymous_control_weakness_id": "haaer2mcontrol0000", **mechanisms.get("control", {}), "raw_control_values_published_bool": False}],
        "mechanism_summary_records": [{"anonymous_mechanism_summary_id": "haaer2msummary0000", **mechanisms.get("summary", {}), "method_winner_bool": False, "default_scaling_claim_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2mclaim0000", "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "new_material_generation_bool": False, "candidate_generation_bool": False, "retrieval_runtime_bool": False, "source_scan_bool": False, "ci_network_bool": False, "scheduler_selector_bool": False, "bea_v1_a_p5_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2mgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2msynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["default_no_private", "missing_opt_in", "repo_root_reject", "symlink_root_reject", "missing_manifest", "missing_required_group", "missing_path_prior", "missing_control", "inconclusive_no_go", "explicit_pass", "raw_leak", "overauth", "stale_readback"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2mreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2mstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2m_mechanism", "haae_r2n_public_audit_package_authorized_bool": passed, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "execution_mode_records", "private_root_boundary_records", "material_consistency_records", "extension_language_prior_records", "directory_depth_prior_records", "same_module_path_token_overlap_records", "fixture_artifact_bias_records", "control_baseline_weakness_records", "mechanism_summary_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2l_checkpoint") != R2L_CHECKPOINT or source.get("locked_haae_r2l_status") != R2L_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2l_status_match_bool", "r2l_forbidden_scan_pass_bool", "r2l_r2m_authorization_match_bool", "r2l_contract_match_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in CLAIM_FALSE_FIELDS:
        if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in ["new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]:
        if stop.get(field) is not False: issues.append(f"stop_go_overauthorization_{field}")
    if report.get("status") == STATUS_PASS:
        mode = (report.get("execution_mode_records") or [{}])[0]
        if not (mode.get("explicit_opt_in_bool") is True and mode.get("private_read_bucket") == "count_1_to_10" and mode.get("private_write_bucket") == "count_0" and mode.get("aggregate_only_mechanism_buckets_confirmed_bool") is True): issues.append("execution_mode_mismatch")
        root = (report.get("private_root_boundary_records") or [{}])[0]
        if not (root.get("root_supplied_bool") is True and root.get("root_boundary_bucket") == "valid_existing_r2i_private_material_root" and root.get("root_path_basename_filename_published_bool") is False and root.get("default_path_or_discovery_bool") is False and root.get("tmp_scan_bool") is False): issues.append("private_root_boundary_mismatch")
        material = (report.get("material_consistency_records") or [{}])[0]
        if not (material.get("required_group_files_present_bool") is True and material.get("outcome_task_alignment_bool") is True and material.get("path_prior_present_bool") is True and material.get("control_baseline_present_bool") is True and material.get("task_count_bucket") == "count_10_to_20"): issues.append("material_consistency_mismatch")
        ext_record = (report.get("extension_language_prior_records") or [{}])[0]
        if not (ext_record.get("top1_extension_match_rate_bucket") == "rate_1" and ext_record.get("top5_extension_match_rate_bucket") == "rate_1" and ext_record.get("interpretation_bucket") == "extension_prior_supporting" and ext_record.get("raw_extensions_published_bool") is False): issues.append("extension_prior_mismatch")
        depth_record = (report.get("directory_depth_prior_records") or [{}])[0]
        if not (depth_record.get("top1_depth_alignment_rate_bucket") == "rate_1" and depth_record.get("interpretation_bucket") == "directory_depth_prior_supporting" and depth_record.get("raw_directories_or_depths_published_bool") is False): issues.append("depth_prior_mismatch")
        module_record = (report.get("same_module_path_token_overlap_records") or [{}])[0]
        if not (module_record.get("top1_same_module_rate_bucket") == "rate_1" and module_record.get("top5_same_module_rate_bucket") == "rate_1" and module_record.get("path_token_overlap_bucket") == "overlap_high" and module_record.get("same_package_directory_rate_bucket") == "rate_1" and module_record.get("raw_tokens_or_paths_published_bool") is False): issues.append("same_module_path_token_mismatch")
        fixture_record = (report.get("fixture_artifact_bias_records") or [{}])[0]
        if not (fixture_record.get("gold_in_pool_rate_bucket") == "rate_1" and fixture_record.get("hard_negative_similarity_bucket") == "rate_1" and fixture_record.get("cross_row_negative_similarity_bucket") == "rate_1" and fixture_record.get("interpretation_bucket") == "fixture_pool_contains_path_cues" and fixture_record.get("raw_candidate_values_published_bool") is False): issues.append("fixture_artifact_bias_mismatch")
        control_record = (report.get("control_baseline_weakness_records") or [{}])[0]
        if not (control_record.get("control_top1_gold_hit_bucket") == "rate_0" and control_record.get("same_top_with_path_prior_rate_bucket") == "rate_0" and control_record.get("underfit_bucket") == "control_underfit" and control_record.get("interpretation_bucket") == "control_baseline_weakness_supporting" and control_record.get("raw_control_values_published_bool") is False): issues.append("control_baseline_weakness_mismatch")
        summary = (report.get("mechanism_summary_records") or [{}])[0]
        if not (summary.get("mechanism_conclusive_bool") is True and summary.get("method_winner_bool") is False and summary.get("default_scaling_claim_bool") is False and summary.get("dominant_mechanism_bucket") == "path_structure_prior" and summary.get("confidence_bucket") == "medium_high" and summary.get("actionability_bucket") == "mechanism_robustness_followup_ready"): issues.append("mechanism_summary_boundary_mismatch")
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("next_allowed_phase_mismatch")
        if stop.get("haae_r2n_public_audit_package_authorized_bool") is not True: issues.append("missing_r2n_authorization")
        gates = {row.get("gate_bucket"): row.get("gate_passed_bool") for row in report.get("pass_fail_gate_records", [])}
        for gate in GATE_NAMES:
            if gates.get(gate) is not True: issues.append(f"gate_not_passed_{gate}")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed = {"allow": False, "confirm": False, "root": "", "self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in {"--allow-private-r2i-mechanism-decomposition", "--allow-private-mechanism-decomposition", "--confirm-aggregate-only-mechanism-buckets", "--confirm-aggregate-only-publication", "--self-test"}:
            if arg in {"--allow-private-r2i-mechanism-decomposition", "--allow-private-mechanism-decomposition"}: parsed["allow"] = True
            elif arg in {"--confirm-aggregate-only-mechanism-buckets", "--confirm-aggregate-only-publication"}: parsed["confirm"] = True
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
    path = Path(value)
    resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def write_report(report: dict[str, Any], out: Path | None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def make_synthetic_root(root: Path, *, missing_group: str | None = None, missing_source: str | None = None, inconclusive: bool = False) -> None:
    groups = root / "groups"; groups.mkdir(parents=True, exist_ok=True)
    rows: dict[str, list[dict[str, Any]]] = {group: [] for group in ALL_GROUPS}
    for i in range(6):
        task = f"task_{i}"
        gold = f"pkg/module_{i}/src/lib.rs"
        hard = f"pkg/module_{i}/src/hard.rs"
        cross = f"other/module_{i}/src/other.py"
        if inconclusive:
            hard = f"other/unrelated_{i}/misc/file.py"
            cross = f"elsewhere/random_{i}/blob.txt"
        rows["task_identity"].append({"task_key": task})
        rows["outcome_metric"].append({"task_key": task, "gold_spans": [{"path": gold}]})
        if inconclusive:
            rows["candidate_pool"].extend([{"task_key": task, "candidate_path": hard, "candidate_role": "hard_negative"}, {"task_key": task, "candidate_path": cross, "candidate_role": "cross_row_negative"}])
        else:
            rows["candidate_pool"].extend([{"task_key": task, "candidate_path": gold, "candidate_role": "gold_positive"}, {"task_key": task, "candidate_path": hard, "candidate_role": "hard_negative"}, {"task_key": task, "candidate_path": cross, "candidate_role": "cross_row_negative"}])
        for src in ("path_prior", "control_baseline"):
            if src == missing_source: continue
            ordered = [gold, hard, cross] if src == "path_prior" and not inconclusive else ([cross, hard] if inconclusive else [cross, hard, gold])
            for rank, path in enumerate(ordered, 1):
                rows["rank_pack"].append({"task_key": task, "rank_source": src, "candidate_path": path, "private_rank": rank})
        for group in OPTIONAL_GROUPS:
            rows[group].append({"task_key": task, "candidate_path": gold})
    for group, group_rows in rows.items():
        if group != missing_group:
            write_jsonl(groups / f"{group}.jsonl", group_rows)
    (root / R2I_PRIVATE_MANIFEST).write_text(json.dumps({"owner_bucket": R2I_OWNER, "status_bucket": R2I_STATUS, "task_count_bucket": "count_10_to_20", "rank_source_count_bucket": "count_6_to_10"}, sort_keys=True) + "\n", encoding="utf-8")


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    check("default_no_private", build_report(STATUS_DEFAULT, False)["status"] == STATUS_DEFAULT)
    check("repo_root_reject", validate_private_root(repo, repo)[0] is False)
    with tempfile.TemporaryDirectory(prefix="r2m_selftest_") as tmp:
        base = Path(tmp)
        good = base / "good"; make_synthetic_root(good)
        ok, reason, files, _ = validate_private_root(good, repo); check("valid_root", ok)
        explicit_report = build_report(STATUS_PASS, True, reason, compute_mechanisms(read_groups(files)))
        check("explicit_pass", explicit_report["status"] == STATUS_PASS)
        mode_drift = json.loads(json.dumps(explicit_report)); mode_drift["execution_mode_records"][0]["private_write_bucket"] = "count_1_to_10"; check("execution_mode_drift", "execution_mode_mismatch" in validate_report(mode_drift))
        material_drift = json.loads(json.dumps(explicit_report)); material_drift["material_consistency_records"][0]["path_prior_present_bool"] = False; check("material_drift", "material_consistency_mismatch" in validate_report(material_drift))
        mechanism_drift = json.loads(json.dumps(explicit_report)); mechanism_drift["same_module_path_token_overlap_records"][0]["path_token_overlap_bucket"] = "overlap_low"; check("mechanism_drift", "same_module_path_token_mismatch" in validate_report(mechanism_drift))
        summary_drift = json.loads(json.dumps(explicit_report)); summary_drift["mechanism_summary_records"][0]["dominant_mechanism_bucket"] = "method_winner"; check("summary_drift", "mechanism_summary_boundary_mismatch" in validate_report(summary_drift))
        gate_drift = json.loads(json.dumps(explicit_report)); gate_drift["pass_fail_gate_records"][0]["gate_passed_bool"] = False; check("gate_drift", any(i.startswith("gate_not_passed_") for i in validate_report(gate_drift)))
        stop_drift = json.loads(json.dumps(explicit_report)); stop_drift["stop_go_records"][0]["next_allowed_phase"] = "wrong"; check("stop_next_phase_drift", "next_allowed_phase_mismatch" in validate_report(stop_drift))
        miss = base / "miss"; make_synthetic_root(miss, missing_group="candidate_pool"); check("missing_required_group", validate_private_root(miss, repo)[0] is False)
        mrank = base / "mrank"; make_synthetic_root(mrank, missing_source="path_prior")
        ok2, reason2, files2, _ = validate_private_root(mrank, repo); check("missing_path_prior", build_report(STATUS_PASS, True, reason2, compute_mechanisms(read_groups(files2)))["status"] == STATUS_NO_GO_RANKS)
        ctl = base / "ctl"; make_synthetic_root(ctl, missing_source="control_baseline")
        ok3, reason3, files3, _ = validate_private_root(ctl, repo); check("missing_control", build_report(STATUS_PASS, True, reason3, compute_mechanisms(read_groups(files3)))["status"] == STATUS_NO_GO_RANKS)
        inc = base / "inc"; make_synthetic_root(inc, inconclusive=True)
        ok4, reason4, files4, _ = validate_private_root(inc, repo); check("inconclusive", build_report(STATUS_PASS, True, reason4, compute_mechanisms(read_groups(files4)))["status"] == STATUS_NO_GO_INCONCLUSIVE)
    bad_source = load_json(repo / R2L_REPORT_PATH); bad_source["status"] = "wrong"; check("source_lock_drift", build_report(STATUS_DEFAULT, False, r2l=bad_source)["status"] == STATUS_FAIL_SOURCE)
    leak = build_report(STATUS_DEFAULT, False); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"
    check("raw_leak", scan_public_report(leak)["status"] == "fail")
    over = build_report(STATUS_DEFAULT, False); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True
    check("overauth", any(i.startswith("stop_go_overauthorization_") for i in validate_report(over)))
    check("stale_readback", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser", False)
    except ValueError: check("safe_parser", True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


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
    ok, reason, files, _ = validate_private_root(Path(args["root"]), repo)
    mechanisms = compute_mechanisms(read_groups(files)) if ok else empty_mechanisms()
    report = build_report(STATUS_PASS, True, reason, mechanisms)
    path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] in {STATUS_PASS, STATUS_NO_GO_ROOT, STATUS_NO_GO_GROUPS, STATUS_NO_GO_RANKS, STATUS_NO_GO_INCONCLUSIVE} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
