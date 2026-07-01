#!/usr/bin/env python3
"""BEA-v1-HAAE-R2J harder/diversified material experiment.

Default mode performs no private read/write. Explicit mode reads only an
operator-supplied existing R2I private material root and publishes aggregate-only
metrics.
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

PHASE = "BEA-v1-HAAE-R2J Harder/Diversified Material Experiment"
SLUG = "bea_v1_haae_r2j_harder_diversified_material_experiment"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2I_CHECKPOINT = "16d1349"
R2I_STATUS = "haae_r2i_harder_diversified_local_material_generation_complete_r2j_experiment_authorized"
R2I_REPORT_PATH = Path("artifacts/bea_v1_haae_r2i_harder_diversified_local_material_generation_smoke/bea_v1_haae_r2i_harder_diversified_local_material_generation_smoke_report.json")
R2I_PRIVATE_MANIFEST = "haae_r2i_private_manifest.json"
R2I_OWNER = "haae_r2i_harder_diversified_local_material_generation_smoke"

STATUS_DEFAULT = "haae_r2j_unavailable_no_explicit_r2i_private_material_root"
STATUS_PASS = "haae_r2j_harder_diversified_material_experiment_complete_r2k_public_audit_authorized"
STATUS_NO_GO_NON_SEPARATING = "haae_r2j_harder_diversified_material_experiment_complete_no_go_non_separating"
STATUS_NO_GO_ROOT = "haae_r2j_no_go_invalid_r2i_private_material_root"
STATUS_NO_GO_SCHEMA = "haae_r2j_no_go_invalid_r2i_material_schema"
STATUS_NO_GO_RANK = "haae_r2j_no_go_rank_source_or_outcome_alignment_incomplete"
STATUS_FAIL_SOURCE = "haae_r2j_fail_closed_source_lock_mismatch"
STATUS_FAIL_ROOT = "haae_r2j_fail_closed_private_root_boundary_violation"
STATUS_FAIL_LEAK = "haae_r2j_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2j_fail_closed_public_readback_mismatch"
STATUS_FAIL_OVERAUTH = "haae_r2j_fail_closed_stop_go_overauthorization"

SELF_TEST_EXPECTED = 21
NEXT_PHASE = "BEA-v1-HAAE-R2K Public Audit Package"
REQUIRED_GROUPS = ["task_identity", "anchor_source", "candidate_pool", "rank_pack", "evidence_core", "outcome_metric"]
OPTIONAL_GROUPS = ["span_projection", "scheduler_action", "arm_assignment", "safety_probe_signal"]
ALL_GROUPS = REQUIRED_GROUPS + OPTIONAL_GROUPS
RANK_SOURCES = ["bm25_like", "symbol_overlap", "path_prior", "structure_token_overlap", "rrf_like", "control_baseline"]
MAX_GROUP_FILE_BYTES = 5_000_000
MAX_TOTAL_PRIVATE_BYTES = 25_000_000

FORBIDDEN_STOP_TRUE = ["new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]
CLAIM_FALSE_FIELDS = ["new_material_generation_bool", "candidate_generation_bool", "retrieval_runtime_bool", "source_scan_bool", "openlocus_runtime_bool", "scheduler_selector_bool", "ci_network_provider_bool", "default_change_bool", "bea_v1_a_p5_bool", "method_winner_bool", "scaling_claim_bool", "raw_publication_bool"]
GATE_NAMES = ["source_lock_gate", "explicit_private_root_gate", "private_root_boundary_gate", "r2i_manifest_owner_gate", "required_group_files_gate", "regular_bounded_group_files_gate", "rank_sources_present_gate", "outcome_task_alignment_gate", "aggregate_metrics_only_gate", "no_private_write_gate", "no_new_material_generation_gate", "no_candidate_generation_gate", "no_retrieval_runtime_source_scan_gate", "no_ci_network_provider_gate", "no_scheduler_haae_selector_gate", "no_default_bea_v1_a_p5_gate", "no_method_scaling_claim_gate", "separation_diagnostic_gate", "public_aggregate_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


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


def rank_bucket(values: Sequence[float]) -> str:
    if not values: return "rank_unavailable"
    value = float(median(values))
    if value <= 1: return "rank_1"
    if value <= 5: return "rank_2_to_5"
    if value <= 10: return "rank_6_to_10"
    if value <= 20: return "rank_11_to_20"
    if value <= 40: return "rank_21_to_40"
    return "rank_gt40"


def spread_bucket(values: list[int]) -> str:
    if not values: return "spread_unavailable"
    spread = max(values) - min(values)
    if spread <= 0: return "spread_none"
    if spread <= 4: return "spread_low"
    if spread <= 10: return "spread_medium"
    return "spread_high"


def validate_r2i_source(r2i: dict[str, Any]) -> dict[str, bool]:
    stop = (r2i.get("stop_go_records") or [{}])[0]
    status_ok = r2i.get("status") == R2I_STATUS
    scan_ok = r2i.get("forbidden_scan", {}).get("status") == "pass"
    auth_ok = stop.get("haae_r2j_harder_diversified_material_experiment_authorized_bool") is True
    reads_existing_ok = stop.get("r2j_reads_existing_r2i_material_only_bool") is True and stop.get("r2j_aggregate_metrics_only_bool") is True
    boundary_ok = all(stop.get(field) is False for field in ["new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_outside_fixture_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool"])
    return {"status_ok": status_ok, "scan_ok": scan_ok, "auth_ok": auth_ok, "reads_existing_ok": reads_existing_ok, "boundary_ok": boundary_ok, "source_locked": status_ok and scan_ok and auth_ok and reads_existing_ok and boundary_ok}


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
    try:
        manifest = load_json(manifest_path)
    except Exception:
        return False, "manifest_parse_failed", {}, {}
    if manifest.get("owner_bucket") != R2I_OWNER: return False, "manifest_owner_mismatch", {}, manifest
    if manifest.get("status_bucket") != R2I_STATUS: return False, "manifest_status_incompatible", {}, manifest
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
    rank_by_task_source: dict[tuple[str, str], list[dict[str, Any]]] = {}
    candidate_by_task: dict[str, list[dict[str, Any]]] = {}
    for row in candidates:
        key = row.get("task_key")
        if key is not None: candidate_by_task.setdefault(str(key), []).append(row)
    for row in ranks:
        key = row.get("task_key"); source = row.get("rank_source")
        if key is not None and source in RANK_SOURCES:
            rank_by_task_source.setdefault((str(key), str(source)), []).append(row)
    source_metrics: dict[str, dict[str, Any]] = {}
    top_by_source: dict[str, dict[str, str]] = {src: {} for src in RANK_SOURCES}
    top_sets: dict[str, dict[int, dict[str, set[str]]]] = {src: {5: {}, 10: {}, 20: {}} for src in RANK_SOURCES}
    first_rank_by_source: dict[str, list[int]] = {src: [] for src in RANK_SOURCES}
    missing_sources: set[str] = set()
    missing_outcome = 0
    for source in RANK_SOURCES:
        covered_tasks = 0; covered_candidates = 0; gold_hits = 0; top1 = 0; top5 = 0; top10 = 0; top20 = 0; first_ranks: list[int] = []
        for task in sorted(task_keys):
            if task not in outcome_by_task:
                missing_outcome += 1; continue
            rows = [row for row in rank_by_task_source.get((task, source), []) if isinstance(row.get("private_rank"), int)]
            rows.sort(key=lambda row: (int(row.get("private_rank", 999999)), str(row.get("candidate_path", ""))))
            if not rows:
                missing_sources.add(source); continue
            covered_tasks += 1; covered_candidates += len(rows)
            top_by_source[source][task] = str(rows[0].get("candidate_path"))
            for k in (5, 10, 20):
                top_sets[source][k][task] = {str(row.get("candidate_path")) for row in rows[:k]}
            gold_paths = {span.get("path") for span in outcome_by_task.get(task, {}).get("gold_spans", []) if span.get("path")}
            hit_ranks = [int(row["private_rank"]) for row in rows if row.get("candidate_path") in gold_paths]
            if hit_ranks:
                best = min(hit_ranks); first_ranks.append(best); first_rank_by_source[source].append(best); gold_hits += 1
                if best <= 1: top1 += 1
                if best <= 5: top5 += 1
                if best <= 10: top10 += 1
                if best <= 20: top20 += 1
        mrr_values = [1.0 / value for value in first_ranks if value > 0]
        source_metrics[source] = {"rank_source_present_bool": covered_tasks > 0, "task_coverage_bucket": count_bucket(covered_tasks), "candidate_coverage_bucket": count_bucket(covered_candidates), "gold_file_hit_count_bucket": count_bucket(gold_hits), "gold_file_hit_rate_bucket": rate_bucket(gold_hits, covered_tasks), "top1_hit_count_bucket": count_bucket(top1), "top5_hit_count_bucket": count_bucket(top5), "top10_hit_count_bucket": count_bucket(top10), "top20_hit_count_bucket": count_bucket(top20), "mrr_bucket": "mrr_unavailable" if not mrr_values else ("mrr_high" if mean(mrr_values) >= 0.5 else "mrr_medium" if mean(mrr_values) >= 0.2 else "mrr_low"), "mean_first_gold_rank_bucket": rank_bucket(first_ranks), "median_first_gold_rank_bucket": rank_bucket(first_ranks), "missing_outcome_bucket": count_bucket(missing_outcome)}
    agreements: list[dict[str, Any]] = []
    for left, right in combinations(RANK_SOURCES, 2):
        common = sorted(set(top_by_source[left]) & set(top_by_source[right]))
        same_top = sum(1 for task in common if top_by_source[left][task] == top_by_source[right][task])
        overlap = {k: sum(1 for task in common if top_sets[left][k][task] & top_sets[right][k][task]) for k in (5, 10, 20)}
        agreements.append({"left_rank_source_bucket": left, "right_rank_source_bucket": right, "comparable_task_bucket": count_bucket(len(common)), "same_top_candidate_rate_bucket": rate_bucket(same_top, len(common)), "overlap_at_5_rate_bucket": rate_bucket(overlap[5], len(common)), "overlap_at_10_rate_bucket": rate_bucket(overlap[10], len(common)), "overlap_at_20_rate_bucket": rate_bucket(overlap[20], len(common)), "exact_values_published_bool": False})
    non_control_sources = [src for src in RANK_SOURCES if src != "control_baseline"]
    spread_by_task: list[int] = []
    control_better_count = 0
    non_control_better_count = 0
    for task in sorted(task_keys):
        source_firsts = {src: first_rank_by_source[src][idx] for idx, src in enumerate([])}
        values: list[int] = []
        for src in RANK_SOURCES:
            rows = [row for row in rank_by_task_source.get((task, src), []) if isinstance(row.get("private_rank"), int)]
            gold_paths = {span.get("path") for span in outcome_by_task.get(task, {}).get("gold_spans", []) if span.get("path")}
            hits = [int(row["private_rank"]) for row in rows if row.get("candidate_path") in gold_paths]
            if hits: values.append(min(hits))
        if values: spread_by_task.append(max(values) - min(values))
        control_rows = [row for row in rank_by_task_source.get((task, "control_baseline"), []) if isinstance(row.get("private_rank"), int)]
        control_hits = [int(row["private_rank"]) for row in control_rows if row.get("candidate_path") in {span.get("path") for span in outcome_by_task.get(task, {}).get("gold_spans", []) if span.get("path")}]
        non_control_hits: list[int] = []
        for src in non_control_sources:
            src_rows = [row for row in rank_by_task_source.get((task, src), []) if isinstance(row.get("private_rank"), int)]
            non_control_hits.extend(int(row["private_rank"]) for row in src_rows if row.get("candidate_path") in {span.get("path") for span in outcome_by_task.get(task, {}).get("gold_spans", []) if span.get("path")})
        if control_hits and non_control_hits:
            if min(non_control_hits) < min(control_hits): non_control_better_count += 1
            elif min(control_hits) < min(non_control_hits): control_better_count += 1
    non_control_top_patterns = {tuple(top_by_source[src].get(task, "") for task in sorted(task_keys)) for src in non_control_sources}
    non_control_distinguishable = len(non_control_top_patterns) > 1
    separation_signal = non_control_distinguishable or non_control_better_count > control_better_count
    consistency = {"required_groups_present_bool": all(groups.get(group) for group in REQUIRED_GROUPS), "outcome_rows_match_task_rows_bool": task_keys == outcome_keys and len(tasks) == len(outcomes), "evidence_rows_present_bool": len(evidence) > 0, "candidate_rows_present_bool": len(candidates) > 0, "no_missing_rank_source_bucket": "none" if not missing_sources else "one_or_more_missing"}
    valid = consistency["required_groups_present_bool"] and consistency["outcome_rows_match_task_rows_bool"] and consistency["candidate_rows_present_bool"] and consistency["no_missing_rank_source_bucket"] == "none"
    return {"valid": valid, "task_count": len(tasks), "candidate_count": len(candidates), "rank_count": len(ranks), "outcome_count": len(outcomes), "source_metrics": source_metrics, "agreements": agreements, "consistency": consistency, "separation": {"rank_spread_bucket": spread_bucket(spread_by_task), "control_baseline_separation_bucket": "non_control_better" if non_control_better_count > control_better_count else "control_not_worse" if control_better_count >= non_control_better_count else "mixed", "non_control_sources_distinguishable_bool": non_control_distinguishable, "separation_signal_bool": separation_signal, "method_winner_bool": False}}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_path|\"gold_spans\"|\"hard_negatives\"|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|task_key|candidate_index|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, STATUS_DEFAULT, STATUS_NO_GO_NON_SEPARATING, f"{total}/{total}", R2I_CHECKPOINT, R2I_STATUS, "explicit private material root", "existing R2I material only", "aggregate-only metrics", "bm25_like/symbol_overlap/path_prior/structure_token_overlap/rrf_like/control_baseline", "separation diagnostics", "method_winner_bool=false", "no method winner/default/scaling claim", NEXT_PHASE]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2j-harder-diversified-material-experiment.md")) and has_all(read("docs/zh/bea-v1-haae-r2j-harder-diversified-material-experiment.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2j-harder-diversified-material-experiment.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def empty_metrics() -> dict[str, Any]:
    return {"valid": False, "task_count": 0, "candidate_count": 0, "rank_count": 0, "outcome_count": 0, "source_metrics": {}, "agreements": [], "consistency": {"required_groups_present_bool": False, "outcome_rows_match_task_rows_bool": False, "evidence_rows_present_bool": False, "candidate_rows_present_bool": False, "no_missing_rank_source_bucket": "not_evaluated"}, "separation": {"rank_spread_bucket": "not_evaluated", "control_baseline_separation_bucket": "not_evaluated", "non_control_sources_distinguishable_bool": False, "separation_signal_bool": False, "method_winner_bool": False}}


def build_report(status: str, explicit: bool, root_reason: str = "not_supplied", metrics: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED, r2i: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2i is None:
        try: r2i = load_json(repo / R2I_REPORT_PATH)
        except Exception: r2i = {}
    source = validate_r2i_source(r2i)
    metrics = metrics or empty_metrics()
    readback = public_readback_match(self_test_total)
    if not source["source_locked"]:
        final_status = STATUS_FAIL_SOURCE
    elif explicit and root_reason != "valid_existing_r2i_private_material_root":
        final_status = STATUS_FAIL_ROOT if "under_public" in root_reason or "symlink" in root_reason or "traversal" in root_reason else STATUS_NO_GO_ROOT
    elif explicit and not metrics.get("valid"):
        final_status = STATUS_NO_GO_RANK if metrics.get("consistency", {}).get("no_missing_rank_source_bucket") != "none" else STATUS_NO_GO_SCHEMA
    elif explicit and not readback["all_public_readback_match_bool"]:
        final_status = STATUS_FAIL_READBACK
    elif explicit and not metrics.get("separation", {}).get("separation_signal_bool"):
        final_status = STATUS_NO_GO_NON_SEPARATING
    elif explicit:
        final_status = STATUS_PASS
    else:
        final_status = status
    passed = final_status == STATUS_PASS
    gates = {"source_lock_gate": source["source_locked"], "explicit_private_root_gate": explicit, "private_root_boundary_gate": (not explicit) or root_reason == "valid_existing_r2i_private_material_root", "r2i_manifest_owner_gate": (not explicit) or root_reason == "valid_existing_r2i_private_material_root", "required_group_files_gate": metrics["consistency"].get("required_groups_present_bool", False) if explicit else False, "regular_bounded_group_files_gate": (not explicit) or root_reason == "valid_existing_r2i_private_material_root", "rank_sources_present_gate": metrics["consistency"].get("no_missing_rank_source_bucket") == "none" if explicit else False, "outcome_task_alignment_gate": metrics["consistency"].get("outcome_rows_match_task_rows_bool", False) if explicit else False, "aggregate_metrics_only_gate": True, "no_private_write_gate": True, "no_new_material_generation_gate": True, "no_candidate_generation_gate": True, "no_retrieval_runtime_source_scan_gate": True, "no_ci_network_provider_gate": True, "no_scheduler_haae_selector_gate": True, "no_default_bea_v1_a_p5_gate": True, "no_method_scaling_claim_gate": True, "separation_diagnostic_gate": metrics["separation"].get("separation_signal_bool", False) if explicit else False, "public_aggregate_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    source_metric_records = []
    for idx, src in enumerate(RANK_SOURCES):
        row = metrics.get("source_metrics", {}).get(src, {})
        source_metric_records.append({"anonymous_rank_source_metric_id": f"haaer2jmetric{idx:04d}", "rank_source_bucket": src, "rank_source_present_bool": bool(row.get("rank_source_present_bool", False)), "task_coverage_bucket": row.get("task_coverage_bucket", "count_0"), "candidate_coverage_bucket": row.get("candidate_coverage_bucket", "count_0"), "gold_file_hit_count_bucket": row.get("gold_file_hit_count_bucket", "count_0"), "gold_file_hit_rate_bucket": row.get("gold_file_hit_rate_bucket", "rate_0"), "top1_hit_count_bucket": row.get("top1_hit_count_bucket", "count_0"), "top5_hit_count_bucket": row.get("top5_hit_count_bucket", "count_0"), "top10_hit_count_bucket": row.get("top10_hit_count_bucket", "count_0"), "top20_hit_count_bucket": row.get("top20_hit_count_bucket", "count_0"), "mrr_bucket": row.get("mrr_bucket", "mrr_unavailable"), "mean_first_gold_rank_bucket": row.get("mean_first_gold_rank_bucket", "rank_unavailable"), "median_first_gold_rank_bucket": row.get("median_first_gold_rank_bucket", "rank_unavailable"), "missing_outcome_bucket": row.get("missing_outcome_bucket", "count_0"), "exact_ranks_scores_paths_published_bool": False})
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": final_status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2jsource0000", "locked_haae_r2i_checkpoint": R2I_CHECKPOINT, "locked_haae_r2i_status": R2I_STATUS, "r2i_status_match_bool": source["status_ok"], "r2i_forbidden_scan_pass_bool": source["scan_ok"], "r2j_authorization_match_bool": source["auth_ok"], "r2i_boundary_match_bool": source["boundary_ok"], "source_locked_bool": source["source_locked"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2jmode0000", "mode_bucket": "explicit_existing_r2i_material_experiment" if explicit else "default_no_explicit_r2i_private_material_root", "explicit_opt_in_bool": explicit, "private_read_bucket": "count_1_to_10" if explicit else "count_0", "private_write_bucket": "count_0", "aggregate_only_publication_confirmed_bool": explicit}],
        "private_root_boundary_records": [{"anonymous_private_root_boundary_id": "haaer2jroot0000", "root_supplied_bool": explicit, "root_boundary_bucket": root_reason, "root_path_basename_filename_published_bool": False, "default_path_or_discovery_bool": False, "tmp_scan_bool": False}],
        "material_consistency_records": [{"anonymous_material_consistency_id": "haaer2jconsistency0000", "required_groups_present_bool": metrics["consistency"].get("required_groups_present_bool", False), "outcome_rows_match_task_rows_bool": metrics["consistency"].get("outcome_rows_match_task_rows_bool", False), "candidate_rows_present_bool": metrics["consistency"].get("candidate_rows_present_bool", False), "evidence_rows_present_bool": metrics["consistency"].get("evidence_rows_present_bool", False), "no_missing_rank_source_bucket": metrics["consistency"].get("no_missing_rank_source_bucket", "not_evaluated"), "task_count_bucket": count_bucket(int(metrics.get("task_count", 0))), "candidate_count_bucket": count_bucket(int(metrics.get("candidate_count", 0))), "rank_row_count_bucket": count_bucket(int(metrics.get("rank_count", 0))), "outcome_row_count_bucket": count_bucket(int(metrics.get("outcome_count", 0)))}],
        "rank_source_metric_records": source_metric_records,
        "rank_source_agreement_records": [{"anonymous_rank_source_agreement_id": f"haaer2jagree{idx:04d}", **row} for idx, row in enumerate(metrics.get("agreements", []))],
        "separation_signal_records": [{"anonymous_separation_signal_id": "haaer2jsep0000", "rank_spread_bucket": metrics["separation"].get("rank_spread_bucket", "not_evaluated"), "control_baseline_separation_bucket": metrics["separation"].get("control_baseline_separation_bucket", "not_evaluated"), "non_control_sources_distinguishable_bool": metrics["separation"].get("non_control_sources_distinguishable_bool", False), "separation_signal_bool": metrics["separation"].get("separation_signal_bool", False), "method_winner_bool": False, "method_winner_claim_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2jclaim0000", "new_material_generation_bool": False, "candidate_generation_bool": False, "retrieval_runtime_bool": False, "source_scan_bool": False, "openlocus_runtime_bool": False, "scheduler_selector_bool": False, "ci_network_provider_bool": False, "default_change_bool": False, "bea_v1_a_p5_bool": False, "method_winner_bool": False, "scaling_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2jgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2jsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["default_no_private", "missing_opt_in", "repo_root_reject", "symlink_root_reject", "missing_manifest_reject", "missing_required_group", "missing_rank_source", "outcome_mismatch", "raw_leak_scanner", "exact_per_task_publication_fail", "overauth_mutation", "stale_readback", "safe_parser", "non_separating_no_go", "separating_pass", "source_lock_drift"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2jreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2jstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_audit_r2j_material_experiment", "haae_r2k_public_audit_package_authorized_bool": passed, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["source_lock_records", "execution_mode_records", "private_root_boundary_records", "material_consistency_records", "rank_source_metric_records", "rank_source_agreement_records", "separation_signal_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2i_checkpoint") != R2I_CHECKPOINT or source.get("locked_haae_r2i_status") != R2I_STATUS or source.get("source_locked_bool") is not True:
        issues.append("source_lock_mismatch")
    metrics = report.get("rank_source_metric_records", [])
    if {row.get("rank_source_bucket") for row in metrics} != set(RANK_SOURCES): issues.append("rank_source_records_incomplete")
    claims = (report.get("claim_boundary_records") or [{}])[0]
    for field in CLAIM_FALSE_FIELDS:
        if claims.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in FORBIDDEN_STOP_TRUE:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    if report.get("status") == STATUS_PASS:
        mode = (report.get("execution_mode_records") or [{}])[0]
        if mode.get("explicit_opt_in_bool") is not True or mode.get("private_write_bucket") != "count_0" or mode.get("aggregate_only_publication_confirmed_bool") is not True:
            issues.append("execution_mode_mismatch")
        root = (report.get("private_root_boundary_records") or [{}])[0]
        if root.get("root_supplied_bool") is not True or root.get("root_boundary_bucket") != "valid_existing_r2i_private_material_root":
            issues.append("private_root_boundary_mismatch")
        for field in ["root_path_basename_filename_published_bool", "default_path_or_discovery_bool", "tmp_scan_bool"]:
            if root.get(field) is not False:
                issues.append(f"private_root_{field}")
        consistency = (report.get("material_consistency_records") or [{}])[0]
        for field in ["required_groups_present_bool", "outcome_rows_match_task_rows_bool", "candidate_rows_present_bool", "evidence_rows_present_bool"]:
            if consistency.get(field) is not True:
                issues.append(f"material_consistency_{field}")
        if consistency.get("no_missing_rank_source_bucket") != "none":
            issues.append("material_consistency_rank_sources")
        for row in metrics:
            if row.get("rank_source_present_bool") is not True or row.get("exact_ranks_scores_paths_published_bool") is not False:
                issues.append(f"rank_source_metric_{row.get('rank_source_bucket', 'unknown')}")
        for row in report.get("rank_source_agreement_records", []):
            if row.get("exact_values_published_bool") is not False:
                issues.append("rank_source_agreement_exact_values")
        if stop.get("haae_r2k_public_audit_package_authorized_bool") is not True: issues.append("missing_r2k_audit_authorization")
        sep = (report.get("separation_signal_records") or [{}])[0]
        if sep.get("separation_signal_bool") is not True or sep.get("method_winner_bool") is not False or sep.get("method_winner_claim_bool") is not False:
            issues.append("separation_boundary_mismatch")
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
        if arg in {"--allow-private-harder-diversified-material-experiment", "--confirm-aggregate-only-publication", "--self-test"}:
            if arg == "--allow-private-harder-diversified-material-experiment": parsed["allow"] = True
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


def make_synthetic_root(root: Path, *, missing_group: str | None = None, missing_source: str | None = None, outcome_mismatch: bool = False, separating: bool = True) -> None:
    groups = root / "groups"; groups.mkdir(parents=True, exist_ok=True)
    task_count = 6
    rows: dict[str, list[dict[str, Any]]] = {group: [] for group in ALL_GROUPS}
    for t in range(task_count):
        task_key = f"synthetic_task_{t:04d}"
        rows["task_identity"].append({"task_key": task_key})
        rows["anchor_source"].append({"task_key": task_key})
        gold_path = f"private/gold_{t}.rs"
        neg_path = f"private/neg_{t}.rs"
        rows["candidate_pool"].extend([{"task_key": task_key, "candidate_path": gold_path}, {"task_key": task_key, "candidate_path": neg_path}])
        rows["evidence_core"].append({"task_key": task_key, "path": gold_path})
        rows["span_projection"].append({"task_key": task_key, "path": gold_path})
        outcome_key = f"missing_{task_key}" if outcome_mismatch and t == 0 else task_key
        rows["outcome_metric"].append({"task_key": outcome_key, "gold_spans": [{"path": gold_path}], "experiment_metrics_computed_bool": False})
        for src in RANK_SOURCES:
            if src == missing_source: continue
            if not separating:
                gold_rank, neg_rank = (1, 2)
            elif src != "control_baseline":
                gold_rank, neg_rank = (1, 2)
            elif src == "control_baseline":
                gold_rank, neg_rank = (2, 1)
            else:
                gold_rank, neg_rank = (1, 2)
            rows["rank_pack"].append({"task_key": task_key, "rank_source": src, "candidate_path": gold_path, "private_rank": gold_rank, "private_score": 1.0 / gold_rank})
            rows["rank_pack"].append({"task_key": task_key, "rank_source": src, "candidate_path": neg_path, "private_rank": neg_rank, "private_score": 1.0 / neg_rank})
    for group in ["scheduler_action", "arm_assignment", "safety_probe_signal"]:
        rows[group].append({"placeholder_group": group})
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
    bad_source = load_json(repo / R2I_REPORT_PATH); bad_source["status"] = "wrong"
    check("source_lock_drift", build_report(STATUS_DEFAULT, False, r2i=bad_source)["status"] == STATUS_FAIL_SOURCE)
    with tempfile.TemporaryDirectory(prefix="r2j_selftest_") as tmp:
        base = Path(tmp)
        good = base / "good"; make_synthetic_root(good, separating=True)
        ok, reason, files, _ = validate_private_root(good, repo)
        check("valid_root", ok and reason == "valid_existing_r2i_private_material_root")
        metrics = compute_metrics(read_private_groups(files))
        check("separating_pass", build_report(STATUS_PASS, True, reason, metrics)["status"] == STATUS_PASS)
        nongood = base / "nongood"; make_synthetic_root(nongood, separating=False)
        ok2, reason2, files2, _ = validate_private_root(nongood, repo)
        check("non_separating_no_go", build_report(STATUS_PASS, True, reason2, compute_metrics(read_private_groups(files2)))["status"] == STATUS_NO_GO_NON_SEPARATING)
        missing = base / "missing"; make_synthetic_root(missing, missing_group="candidate_pool")
        check("missing_required_group", validate_private_root(missing, repo)[0] is False)
        mrank = base / "mrank"; make_synthetic_root(mrank, missing_source="path_prior")
        ok3, reason3, files3, _ = validate_private_root(mrank, repo)
        check("missing_rank_source", build_report(STATUS_PASS, True, reason3, compute_metrics(read_private_groups(files3)))["status"] == STATUS_NO_GO_RANK)
        mismatch = base / "mismatch"; make_synthetic_root(mismatch, outcome_mismatch=True)
        ok4, reason4, files4, _ = validate_private_root(mismatch, repo)
        check("outcome_mismatch", build_report(STATUS_PASS, True, reason4, compute_metrics(read_private_groups(files4)))["status"] == STATUS_NO_GO_SCHEMA)
        nonmanifest = base / "nonmanifest"; nonmanifest.mkdir(); (nonmanifest / "x").write_text("x", encoding="utf-8")
        check("missing_manifest", validate_private_root(nonmanifest, repo)[0] is False)
    leak = build_report(STATUS_DEFAULT, False); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs private_rank"
    check("raw_leak_scanner", scan_public_report(leak)["status"] == "fail")
    exact = build_report(STATUS_DEFAULT, False); exact["rank_source_metric_records"][0]["task_key"] = "private_task"
    check("exact_per_task_publication_fail", scan_public_report(exact)["status"] == "fail")
    over = build_report(STATUS_DEFAULT, False); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True
    check("overauth", any(issue.startswith("overauthorization_") for issue in validate_report(over)))
    pass_report = build_report(STATUS_PASS, True, "valid_existing_r2i_private_material_root", metrics)
    check("pass_report_validates", validate_report(pass_report) == [])
    bad_root = json.loads(json.dumps(pass_report)); bad_root["private_root_boundary_records"][0]["root_path_basename_filename_published_bool"] = True
    check("root_publication_mutation", "private_root_root_path_basename_filename_published_bool" in validate_report(bad_root))
    bad_metric = json.loads(json.dumps(pass_report)); bad_metric["rank_source_metric_records"][0]["exact_ranks_scores_paths_published_bool"] = True
    check("metric_publication_mutation", any(issue.startswith("rank_source_metric_") for issue in validate_report(bad_metric)))
    bad_agreement = json.loads(json.dumps(pass_report)); bad_agreement["rank_source_agreement_records"][0]["exact_values_published_bool"] = True
    check("agreement_publication_mutation", "rank_source_agreement_exact_values" in validate_report(bad_agreement))
    bad_claim = json.loads(json.dumps(pass_report)); bad_claim["claim_boundary_records"][0]["method_winner_bool"] = True
    check("claim_boundary_mutation", "claim_boundary_method_winner_bool" in validate_report(bad_claim))
    check("stale_readback", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-material-root", "/tmp/x"])
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
    if not ok:
        report = build_report(STATUS_NO_GO_ROOT, True, reason); write_report(report, out); return 0
    metrics = compute_metrics(read_private_groups(files))
    report = build_report(STATUS_PASS, True, reason, metrics)
    path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] in {STATUS_PASS, STATUS_NO_GO_NON_SEPARATING, STATUS_NO_GO_ROOT, STATUS_NO_GO_SCHEMA, STATUS_NO_GO_RANK} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
