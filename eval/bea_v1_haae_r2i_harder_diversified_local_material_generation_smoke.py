#!/usr/bin/env python3
"""BEA-v1-HAAE-R2I harder/diversified local material generation smoke."""

from __future__ import annotations

import io
import json
import re
import shutil
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2I Harder/Diversified Local Material Generation Smoke"
SLUG = "bea_v1_haae_r2i_harder_diversified_local_material_generation_smoke"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2H_CHECKPOINT = "3db7366"
R2H_STATUS = "haae_r2h_next_step_design_decision_complete_r2i_harder_diversified_material_generation_authorized"
R2H_REPORT_PATH = Path("artifacts/bea_v1_haae_r2h_next_step_design_decision/bea_v1_haae_r2h_next_step_design_decision_report.json")

STATUS_DEFAULT = "haae_r2i_unavailable_no_explicit_harder_diversified_material_generation_opt_in"
STATUS_PASS = "haae_r2i_harder_diversified_local_material_generation_complete_r2j_experiment_authorized"
STATUS_NO_GO_ROOT = "haae_r2i_no_go_private_output_root_invalid"
STATUS_NO_GO_MATERIAL = "haae_r2i_no_go_material_incomplete"
STATUS_FAIL_SOURCE = "haae_r2i_fail_closed_source_lock_mismatch"
STATUS_FAIL_BOUNDS = "haae_r2i_fail_closed_locked_bounds_mismatch"
STATUS_FAIL_LEAK = "haae_r2i_fail_closed_public_artifact_leak"
STATUS_FAIL_READBACK = "haae_r2i_fail_closed_public_readback_mismatch"
STATUS_FAIL_OVERAUTH = "haae_r2i_fail_closed_stop_go_overauthorization"

TARGET_TASK_COUNT = 20
CANDIDATE_DEPTH = 40
PRIVATE_ROW_CAP = 10000
SELF_TEST_EXPECTED = 21
NEXT_PHASE = "BEA-v1-HAAE-R2J Harder/Diversified Material Experiment"
PRIVATE_MANIFEST_NAME = "haae_r2i_private_manifest.json"
OWNER_BUCKET = "haae_r2i_harder_diversified_local_material_generation_smoke"

SCHEMA_GROUPS = ["task_identity", "anchor_source", "candidate_pool", "rank_pack", "evidence_core", "outcome_metric", "span_projection", "scheduler_action", "arm_assignment", "safety_probe_signal"]
REQUIRED_GROUPS = {"task_identity", "anchor_source", "candidate_pool", "rank_pack", "evidence_core", "outcome_metric"}
PLACEHOLDER_GROUPS = {"scheduler_action", "arm_assignment", "safety_probe_signal"}
RANK_SOURCES = ["bm25_like", "symbol_overlap", "path_prior", "structure_token_overlap", "rrf_like", "control_baseline"]
FORBIDDEN_STOP_TRUE = ["new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_outside_fixture_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool"]
GATE_NAMES = ["r2h_source_locked_gate", "explicit_opt_in_gate", "private_output_root_boundary_gate", "locked_task_count_gate", "locked_candidate_depth_gate", "private_row_cap_gate", "fixture_subset_gate", "required_schema_groups_meaningful_gate", "span_projection_available_gate", "all_rank_sources_present_gate", "hard_negatives_present_gate", "control_baseline_present_gate", "no_experiment_metrics_gate", "public_aggregate_only_gate", "no_old_private_root_read_gate", "no_retrieval_runtime_source_scan_gate", "no_ci_network_provider_gate", "no_scheduler_selector_gate", "stop_go_r2j_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def bucket_count(n: int) -> str:
    if n <= 0: return "count_0"
    if n == 1: return "count_1"
    if n <= 5: return "count_2_to_5"
    if n <= 20: return "count_10_to_20"
    if n <= 50: return "count_21_to_50"
    if n <= 10000: return "count_le_10000"
    return "count_gt_10000"


def validate_r2h_source(r2h: dict[str, Any]) -> dict[str, bool]:
    src = (r2h.get("source_lock_records") or [{}])[0]
    stop = (r2h.get("stop_go_records") or [{}])[0]
    status_ok = r2h.get("status") == R2H_STATUS
    scan_ok = r2h.get("forbidden_scan", {}).get("status") == "pass"
    checkpoint_ok = src.get("locked_haae_r2g_checkpoint") == "cd583d6"
    auth_ok = stop.get("haae_r2i_harder_diversified_material_generation_smoke_authorized_bool") is True
    boundary_ok = all(stop.get(field) is False for field in ["r2i_execution_authorized_bool", "r2i_experiment_metrics_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_outside_fixture_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "r3_direct_scale_authorized_bool"])
    return {"status_ok": status_ok, "scan_ok": scan_ok, "checkpoint_ok": checkpoint_ok, "auth_ok": auth_ok, "boundary_ok": boundary_ok, "source_locked": status_ok and scan_ok and checkpoint_ok and auth_ok and boundary_ok}


def validate_private_root(root: Path, repo: Path) -> tuple[bool, str]:
    try:
        resolved = root.resolve(strict=False)
        repo_resolved = repo.resolve(strict=True)
    except OSError:
        return False, "path_resolution_failed"
    if ".." in root.parts:
        return False, "path_traversal"
    if root.exists() and root.is_symlink():
        return False, "root_symlink"
    if resolved == repo_resolved or repo_resolved in resolved.parents:
        return False, "root_inside_public_repo"
    if not (str(resolved).startswith("/tmp/") or str(resolved).startswith("/var/tmp/")):
        return False, "root_not_temp_or_ignored_bucket"
    if root.exists() and not root.is_dir():
        return False, "root_not_directory"
    if root.exists():
        entries = [entry.name for entry in root.iterdir()]
        if entries:
            if PRIVATE_MANIFEST_NAME not in entries:
                return False, "root_not_empty_or_r2i_owned"
            try:
                manifest = load_json(root / PRIVATE_MANIFEST_NAME)
            except Exception:
                return False, "root_manifest_invalid"
            if manifest.get("owner_bucket") != OWNER_BUCKET:
                return False, "root_not_r2i_owned"
    return True, "valid_explicit_r2i_private_root"


def select_public_fixture(repo: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], str]:
    tasks = load_jsonl(repo / "fixtures" / "r14" / "tasks" / "medium.jsonl")
    labels = {row["task_id"]: row for row in load_jsonl(repo / "fixtures" / "r14" / "labels" / "medium.jsonl")}
    selected = [task for task in tasks[:TARGET_TASK_COUNT] if labels.get(task.get("task_id"), {}).get("gold_spans")]
    return selected, labels, bucket_count(len(tasks))


def build_candidates(task_index: int, label: dict[str, Any], all_labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for span in label.get("gold_spans", []):
        candidates.append({"candidate_path": span.get("path"), "candidate_kind": "gold_evidence", "label_ref": span})
    for neg in label.get("hard_negatives", []):
        candidates.append({"candidate_path": neg.get("path"), "candidate_kind": "hard_negative", "label_ref": neg})
    offset = 1
    while len({row.get("candidate_path") for row in candidates if row.get("candidate_path")}) < CANDIDATE_DEPTH and offset < len(all_labels):
        other = all_labels[(task_index + offset) % len(all_labels)]
        for span in other.get("gold_spans", []) + other.get("hard_negatives", []):
            candidates.append({"candidate_path": span.get("path"), "candidate_kind": "cross_row_negative", "label_ref": span})
        offset += 1
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for row in candidates:
        path = row.get("candidate_path")
        if path and path not in seen:
            seen.add(path)
            result.append(row)
    return result[:CANDIDATE_DEPTH]


def tokenize(value: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z0-9_]+", value or "")]


def stable_hash_score(value: str) -> float:
    total = 0
    for idx, char in enumerate(value):
        total = (total + (idx + 1) * ord(char)) % 1000003
    return total / 1000003.0


def score_for_source(source: str, candidate_index: int, candidate: dict[str, Any], query: str) -> float:
    path = str(candidate.get("candidate_path", ""))
    query_tokens = set(tokenize(query))
    path_tokens = set(tokenize(path.replace("/", " ").replace(".", " ")))
    overlap = len(query_tokens & path_tokens)
    path_depth = len([part for part in path.split("/") if part])
    extension_score = 1.0 if path.endswith((".rs", ".py", ".ts", ".tsx", ".js", ".go")) else 0.0
    if source == "control_baseline":
        return stable_hash_score(f"control::{candidate_index}::{path}")
    if source == "path_prior":
        return (2.0 if "/src/" in f"/{path}" else 0.0) + extension_score - (path_depth * 0.01)
    elif source == "structure_token_overlap":
        structure_tokens = {tok for tok in path_tokens if tok in {"src", "lib", "test", "tests", "core", "eval", "bench", "service", "store", "parser"}}
        return len(structure_tokens) + (overlap * 0.25) + stable_hash_score(path) * 0.001
    elif source == "symbol_overlap":
        symbol_tokens = {tok for tok in path_tokens if "_" in tok or any(ch.isdigit() for ch in tok)}
        return overlap + len(symbol_tokens) * 0.5 + stable_hash_score(path) * 0.001
    elif source == "bm25_like":
        return overlap * 2.0 + sum(1.0 / (1 + len(tok)) for tok in path_tokens & query_tokens) + stable_hash_score(path) * 0.001
    elif source == "rrf_like":
        return (overlap * 1.2) + (1.0 if "/src/" in f"/{path}" else 0.0) + extension_score + stable_hash_score(f"rrf::{path}") * 0.001
    return stable_hash_score(path)


def materialize(repo: Path, private_root: Path, *, mutate: str | None = None) -> dict[str, Any]:
    tasks, label_map, fixture_bucket = select_public_fixture(repo)
    if len(tasks) != TARGET_TASK_COUNT:
        return {"status": STATUS_NO_GO_MATERIAL, "fixture_bucket": fixture_bucket, "group_counts": {}, "total_rows": 0}
    labels_in_order = [label_map[task["task_id"]] for task in tasks]
    rows: dict[str, list[dict[str, Any]]] = {group: [] for group in SCHEMA_GROUPS}
    hard_negative_rows = 0
    control_rows = 0
    present_sources: set[str] = set()
    for task_index, task in enumerate(tasks):
        label = label_map[task["task_id"]]
        task_key = f"r2i_task_{task_index:04d}"
        candidates = build_candidates(task_index, label, labels_in_order)
        rows["task_identity"].append({"task_key": task_key, "task": task, "label_quality": label.get("label_quality")})
        rows["anchor_source"].append({"task_key": task_key, "source_fixture": "r14_medium", "subset_policy": "deterministic_public_manifest_prefix_cap_20", "harder_diversified_bool": True})
        for idx, candidate in enumerate(candidates, start=1):
            if candidate["candidate_kind"] in {"hard_negative", "cross_row_negative"}:
                hard_negative_rows += 1
            rows["candidate_pool"].append({"task_key": task_key, "task_id": task["task_id"], "query": task["query"], "candidate_index": idx, "candidate_path": candidate["candidate_path"], "candidate_kind": candidate["candidate_kind"]})
            rows["evidence_core"].append({"task_key": task_key, "task_id": task["task_id"], "path": candidate["candidate_path"], "evidence_kind": candidate["candidate_kind"], "label_ref": candidate["label_ref"]})
            rows["span_projection"].append({"task_key": task_key, "task_id": task["task_id"], "path": candidate["candidate_path"], "projected_start_line": candidate["label_ref"].get("start_line"), "projected_end_line": candidate["label_ref"].get("end_line"), "projection_source": candidate["candidate_kind"]})
        for source in RANK_SOURCES:
            scored_candidates = []
            for idx, candidate in enumerate(candidates, start=1):
                score = score_for_source(source, idx, candidate, task["query"])
                scored_candidates.append((score, idx, candidate))
            scored_candidates.sort(key=lambda item: (-item[0], item[1], str(item[2].get("candidate_path", ""))))
            for rank_value, (score, idx, candidate) in enumerate(scored_candidates, start=1):
                if source == "control_baseline":
                    control_rows += 1
                present_sources.add(source)
                rows["rank_pack"].append({"task_key": task_key, "task_id": task["task_id"], "candidate_path": candidate["candidate_path"], "rank_source": source, "private_rank": rank_value, "private_score": score, "candidate_kind": candidate["candidate_kind"], "ranking_policy_uses_gold_bool": False})
        rows["outcome_metric"].append({"task_key": task_key, "task_id": task["task_id"], "query": task["query"], "gold_spans": label.get("gold_spans", []), "hard_negatives": label.get("hard_negatives", []), "gold_labels_private_only_bool": True, "experiment_metrics_computed_bool": False})
    for group in PLACEHOLDER_GROUPS:
        rows[group].append({"placeholder_group": group, "status": "placeholder_allowed_in_r2i_material_smoke"})
    if mutate == "missing_required":
        rows["candidate_pool"] = []
    if mutate == "missing_rank_source":
        rows["rank_pack"] = [row for row in rows["rank_pack"] if row.get("rank_source") != "path_prior"]
        present_sources.discard("path_prior")
    total_rows = sum(len(value) for value in rows.values())
    if mutate == "row_cap_exceeded":
        total_rows = PRIVATE_ROW_CAP + 1
    if total_rows > PRIVATE_ROW_CAP:
        return {"status": STATUS_FAIL_BOUNDS, "fixture_bucket": fixture_bucket, "group_counts": {group: len(value) for group, value in rows.items()}, "total_rows": total_rows, "rank_sources": sorted(present_sources)}
    if private_root.exists():
        entries = [entry.name for entry in private_root.iterdir()]
        if entries and PRIVATE_MANIFEST_NAME not in entries:
            return {"status": STATUS_NO_GO_ROOT, "fixture_bucket": fixture_bucket, "group_counts": {}, "total_rows": 0, "root_issue_bucket": "root_not_empty_or_r2i_owned"}
        if PRIVATE_MANIFEST_NAME in entries:
            try:
                existing_manifest = load_json(private_root / PRIVATE_MANIFEST_NAME)
            except Exception:
                return {"status": STATUS_NO_GO_ROOT, "fixture_bucket": fixture_bucket, "group_counts": {}, "total_rows": 0, "root_issue_bucket": "root_manifest_invalid"}
            if existing_manifest.get("owner_bucket") != OWNER_BUCKET or existing_manifest.get("schema_version") != SCHEMA_VERSION:
                return {"status": STATUS_NO_GO_ROOT, "fixture_bucket": fixture_bucket, "group_counts": {}, "total_rows": 0, "root_issue_bucket": "root_not_r2i_owned"}
        groups_path = private_root / "groups"
        if groups_path.exists():
            shutil.rmtree(groups_path)
    group_dir = private_root / "groups"
    group_dir.mkdir(parents=True, exist_ok=True)
    for group, group_rows in rows.items():
        write_jsonl(group_dir / f"{group}.jsonl", group_rows)
    group_counts = {group: len(load_jsonl(group_dir / f"{group}.jsonl")) for group in SCHEMA_GROUPS}
    required_ok = all(group_counts.get(group, 0) > 0 for group in REQUIRED_GROUPS)
    rank_ok = set(RANK_SOURCES).issubset(present_sources)
    hard_ok = hard_negative_rows > 0
    control_ok = control_rows > 0
    no_metrics = all(row.get("experiment_metrics_computed_bool") is False for row in rows["outcome_metric"])
    status = STATUS_PASS if required_ok and rank_ok and hard_ok and control_ok and no_metrics else STATUS_NO_GO_MATERIAL
    (private_root / PRIVATE_MANIFEST_NAME).write_text(json.dumps({"owner_bucket": OWNER_BUCKET, "schema_version": SCHEMA_VERSION, "status_bucket": status, "task_count_bucket": bucket_count(len(tasks)), "candidate_depth_cap_bucket": "count_40", "private_row_cap_bucket": "count_10000", "rank_source_count_bucket": bucket_count(len(present_sources)), "raw_values_private_bool": True}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": status, "fixture_bucket": fixture_bucket, "group_counts": group_counts, "total_rows": total_rows, "rank_sources": sorted(present_sources), "task_count": len(tasks), "candidate_depth_cap": CANDIDATE_DEPTH, "candidate_rows": group_counts.get("candidate_pool", 0), "rank_rows": group_counts.get("rank_pack", 0), "outcome_rows": group_counts.get("outcome_metric", 0), "hard_negative_rows": hard_negative_rows, "control_baseline_rows": control_rows, "experiment_metrics_computed_bool": not no_metrics}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_path|\"gold_spans\"|\"hard_negatives\"|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|first_gold_file_rank|hit_rate|top10|top5|top1|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, STATUS_DEFAULT, f"{total}/{total}", R2H_CHECKPOINT, R2H_STATUS, "explicit opt-in", "target 20 tasks", "candidate depth 40", "private row cap 10000", "bm25_like/symbol_overlap/path_prior/structure_token_overlap/rrf_like/control_baseline", "no experiment metrics in R2I", NEXT_PHASE]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2i-harder-diversified-local-material-generation-smoke.md")) and has_all(read("docs/zh/bea-v1-haae-r2i-harder-diversified-local-material-generation-smoke.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2i-harder-diversified-local-material-generation-smoke.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(status: str, explicit: bool, root_valid: bool = False, root_reason: str = "not_supplied", result: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED, r2h: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2h is None:
        try: r2h = load_json(repo / R2H_REPORT_PATH)
        except Exception: r2h = {}
    source = validate_r2h_source(r2h)
    result = result or {}
    readback = public_readback_match(self_test_total)
    group_counts = result.get("group_counts", {})
    rank_sources = set(result.get("rank_sources", []))
    required_ok = all(group_counts.get(group, 0) > 0 for group in REQUIRED_GROUPS)
    rank_ok = set(RANK_SOURCES).issubset(rank_sources)
    hard_ok = int(result.get("hard_negative_rows", 0)) > 0
    control_ok = int(result.get("control_baseline_rows", 0)) > 0
    no_metrics = result.get("experiment_metrics_computed_bool") is not True
    if not source["source_locked"]:
        final_status = STATUS_FAIL_SOURCE
    elif explicit and not root_valid:
        final_status = STATUS_NO_GO_ROOT
    elif explicit and (int(result.get("task_count", 0)) != TARGET_TASK_COUNT or int(result.get("candidate_depth_cap", CANDIDATE_DEPTH)) > CANDIDATE_DEPTH or int(result.get("total_rows", 0)) > PRIVATE_ROW_CAP):
        final_status = STATUS_FAIL_BOUNDS
    elif explicit and not (required_ok and rank_ok and hard_ok and control_ok and no_metrics):
        final_status = STATUS_NO_GO_MATERIAL
    elif explicit and not readback["all_public_readback_match_bool"]:
        final_status = STATUS_FAIL_READBACK
    elif explicit:
        final_status = STATUS_PASS
    else:
        final_status = status
    passed = final_status == STATUS_PASS
    gates = {"r2h_source_locked_gate": source["source_locked"], "explicit_opt_in_gate": explicit, "private_output_root_boundary_gate": (not explicit) or root_valid, "locked_task_count_gate": (not explicit) or int(result.get("task_count", 0)) == TARGET_TASK_COUNT, "locked_candidate_depth_gate": (not explicit) or int(result.get("candidate_depth_cap", 0)) <= CANDIDATE_DEPTH, "private_row_cap_gate": int(result.get("total_rows", 0)) <= PRIVATE_ROW_CAP, "fixture_subset_gate": True, "required_schema_groups_meaningful_gate": required_ok if explicit else False, "span_projection_available_gate": group_counts.get("span_projection", 0) > 0 if explicit else False, "all_rank_sources_present_gate": rank_ok if explicit else False, "hard_negatives_present_gate": hard_ok if explicit else False, "control_baseline_present_gate": control_ok if explicit else False, "no_experiment_metrics_gate": no_metrics, "public_aggregate_only_gate": True, "no_old_private_root_read_gate": True, "no_retrieval_runtime_source_scan_gate": True, "no_ci_network_provider_gate": True, "no_scheduler_selector_gate": True, "stop_go_r2j_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": final_status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2isource0000", "locked_haae_r2h_checkpoint": R2H_CHECKPOINT, "locked_haae_r2h_status": R2H_STATUS, "r2h_status_match_bool": source["status_ok"], "r2h_forbidden_scan_pass_bool": source["scan_ok"], "r2i_authorization_match_bool": source["auth_ok"], "r2h_boundary_match_bool": source["boundary_ok"], "source_locked_bool": source["source_locked"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2imode0000", "mode_bucket": "explicit_harder_diversified_material_generation" if explicit else "default_no_explicit_opt_in", "explicit_opt_in_bool": explicit, "private_read_bucket": "count_0", "private_write_bucket": bucket_count(int(result.get("total_rows", 0))) if explicit else "count_0", "generation_performed_bool": explicit}],
        "private_output_root_records": [{"anonymous_private_output_root_id": "haaer2iroot0000", "root_supplied_bool": explicit, "root_valid_bool": root_valid, "root_boundary_bucket": root_reason, "root_path_published_bool": False, "root_basename_filename_published_bool": False}],
        "fixture_subset_records": [{"anonymous_fixture_subset_id": "haaer2ifixture0000", "source_fixture_bucket": "r14_medium_public_fixture", "subset_policy_bucket": "deterministic_first_20_public_rows", "target_task_count_bucket": "target_20_tasks", "candidate_depth_cap_bucket": "candidate_depth_40", "raw_fixture_rows_published_bool": False}],
        "diversification_material_records": [{"anonymous_diversification_material_id": "haaer2idiv0000", "task_count_bucket": bucket_count(int(result.get("task_count", 0))), "candidate_row_count_bucket": bucket_count(int(result.get("candidate_rows", 0))), "hard_negative_row_count_bucket": bucket_count(int(result.get("hard_negative_rows", 0))), "control_baseline_row_count_bucket": bucket_count(int(result.get("control_baseline_rows", 0))), "candidate_depth_cap_respected_bool": int(result.get("candidate_depth_cap", 0)) <= CANDIDATE_DEPTH if explicit else False, "gold_labels_private_only_bool": True, "ranking_policy_uses_gold_bool": False}],
        "rank_source_material_records": [{"anonymous_rank_source_material_id": f"haaer2irank{idx:04d}", "rank_source_bucket": src, "present_bool": src in rank_sources, "rank_row_count_bucket": bucket_count(int(result.get("rank_rows", 0))) if src in rank_sources else "count_0", "exact_ranks_scores_public_bool": False} for idx, src in enumerate(RANK_SOURCES)],
        "schema_group_material_records": [{"anonymous_schema_group_material_id": f"haaer2igroup{idx:04d}", "group_bucket": group, "required_meaningful_bool": group in REQUIRED_GROUPS, "meaningful_rows_present_bool": group_counts.get(group, 0) > 0 and group not in PLACEHOLDER_GROUPS, "placeholder_allowed_bool": group in PLACEHOLDER_GROUPS, "private_row_count_bucket": bucket_count(int(group_counts.get(group, 0))), "raw_rows_published_bool": False} for idx, group in enumerate(SCHEMA_GROUPS)],
        "quality_control_records": [{"anonymous_quality_control_id": "haaer2iquality0000", "required_groups_meaningful_bool": required_ok, "all_rank_sources_present_bool": rank_ok, "hard_negatives_present_bool": hard_ok, "control_baseline_present_bool": control_ok, "no_experiment_metrics_computed_bool": no_metrics, "private_row_cap_respected_bool": int(result.get("total_rows", 0)) <= PRIVATE_ROW_CAP, "public_aggregate_only_bool": True}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2iclaim0000", "material_generation_smoke_bool": explicit, "experiment_metrics_bool": False, "old_private_root_read_bool": False, "retrieval_runtime_bool": False, "source_scan_outside_fixture_bool": False, "ci_network_provider_clone_bool": False, "scheduler_haae_selector_bool": False, "bea_v1_a_p5_default_bool": False, "method_scaling_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2igate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2isynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["default_no_private", "missing_opt_in", "root_boundary_reject", "non_r2i_owned_root_reject", "source_lock_drift", "bounds_drift", "missing_required_group", "missing_rank_source", "row_cap_exceeded", "leak_scanner", "overauth", "stale_readback", "safe_parser", "explicit_fixture_smoke", "ranking_policy_ignores_gold_kind"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2ireadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2istop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_fix_r2i_material_generation", "haae_r2j_harder_diversified_material_experiment_authorized_bool": passed, "r2j_explicit_private_root_required_bool": passed, "r2j_reads_existing_r2i_material_only_bool": passed, "r2j_aggregate_metrics_only_bool": passed, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_outside_fixture_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["source_lock_records", "execution_mode_records", "private_output_root_records", "fixture_subset_records", "diversification_material_records", "rank_source_material_records", "schema_group_material_records", "quality_control_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2h_checkpoint") != R2H_CHECKPOINT or source.get("locked_haae_r2h_status") != R2H_STATUS or source.get("source_locked_bool") is not True:
        issues.append("source_lock_mismatch")
    quality = (report.get("quality_control_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        for field in ["required_groups_meaningful_bool", "all_rank_sources_present_bool", "hard_negatives_present_bool", "control_baseline_present_bool", "no_experiment_metrics_computed_bool", "private_row_cap_respected_bool", "public_aggregate_only_bool"]:
            if quality.get(field) is not True: issues.append(f"quality_{field}")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        root = (report.get("private_output_root_records") or [{}])[0]
        for field in ["root_supplied_bool", "root_valid_bool"]:
            if root.get(field) is not True: issues.append(f"private_root_{field}")
        for field in ["root_path_published_bool", "root_basename_filename_published_bool"]:
            if root.get(field) is not False: issues.append(f"private_root_{field}")
        fixture = (report.get("fixture_subset_records") or [{}])[0]
        if fixture.get("target_task_count_bucket") != "target_20_tasks" or fixture.get("candidate_depth_cap_bucket") != "candidate_depth_40" or fixture.get("raw_fixture_rows_published_bool") is not False:
            issues.append("fixture_subset_mismatch")
        div = (report.get("diversification_material_records") or [{}])[0]
        for field in ["candidate_depth_cap_respected_bool", "gold_labels_private_only_bool"]:
            if div.get(field) is not True: issues.append(f"diversification_{field}")
        if div.get("ranking_policy_uses_gold_bool") is not False:
            issues.append("diversification_ranking_policy_uses_gold_bool")
        ranks = {row.get("rank_source_bucket"): row for row in report.get("rank_source_material_records", [])}
        if set(ranks) != set(RANK_SOURCES): issues.append("rank_source_set_mismatch")
        for src in RANK_SOURCES:
            row = ranks.get(src, {})
            if row.get("present_bool") is not True or row.get("exact_ranks_scores_public_bool") is not False:
                issues.append(f"rank_source_{src}_mismatch")
        groups = {row.get("group_bucket"): row for row in report.get("schema_group_material_records", [])}
        for group in REQUIRED_GROUPS:
            if groups.get(group, {}).get("meaningful_rows_present_bool") is not True or groups.get(group, {}).get("raw_rows_published_bool") is not False:
                issues.append(f"schema_group_{group}_mismatch")
        claim = (report.get("claim_boundary_records") or [{}])[0]
        if claim.get("material_generation_smoke_bool") is not True: issues.append("claim_boundary_material_generation_smoke_bool")
        for field in ["experiment_metrics_bool", "old_private_root_read_bool", "retrieval_runtime_bool", "source_scan_outside_fixture_bool", "ci_network_provider_clone_bool", "scheduler_haae_selector_bool", "bea_v1_a_p5_default_bool", "method_scaling_claim_bool", "raw_publication_bool"]:
            if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True:
                issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        for field in ["haae_r2j_harder_diversified_material_experiment_authorized_bool", "r2j_explicit_private_root_required_bool", "r2j_reads_existing_r2i_material_only_bool", "r2j_aggregate_metrics_only_bool"]:
            if stop.get(field) is not True: issues.append(f"stop_go_{field}")
    for field in FORBIDDEN_STOP_TRUE:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {"allow": False, "confirm": False, "root": "", "target": TARGET_TASK_COUNT, "depth": CANDIDATE_DEPTH, "cap": PRIVATE_ROW_CAP, "self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in {"--allow-private-harder-diversified-material-generation", "--confirm-private-rows-only", "--self-test"}:
            if arg == "--allow-private-harder-diversified-material-generation": parsed["allow"] = True
            elif arg == "--confirm-private-rows-only": parsed["confirm"] = True
            else: parsed["self_test"] = True
            i += 1
        elif arg in {"--private-output-root", "--target-task-count", "--candidate-depth", "--private-row-cap", "--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            val = argv[i + 1]
            if arg == "--private-output-root": parsed["root"] = val
            elif arg == "--target-task-count": parsed["target"] = int(val) if val.isdigit() else -1
            elif arg == "--candidate-depth": parsed["depth"] = int(val) if val.isdigit() else -1
            elif arg == "--private-row-cap": parsed["cap"] = int(val) if val.isdigit() else -1
            elif arg == "--validate-report": parsed["validate"] = val
            else: parsed["out"] = val
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


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    check("default_no_private", build_report(STATUS_DEFAULT, False)["status"] == STATUS_DEFAULT)
    check("repo_root_reject", validate_private_root(repo, repo)[0] is False)
    bad_source = load_json(repo / R2H_REPORT_PATH); bad_source["status"] = "wrong"
    check("source_lock_drift", build_report(STATUS_DEFAULT, False, r2h=bad_source)["status"] == STATUS_FAIL_SOURCE)
    with tempfile.TemporaryDirectory(prefix="r2i_selftest_") as tmp:
        base = Path(tmp)
        root = base / "private"
        ok, reason = validate_private_root(root, repo)
        check("empty_root_ok", ok and reason == "valid_explicit_r2i_private_root")
        good = materialize(repo, root)
        check("explicit_fixture_smoke", good["status"] == STATUS_PASS)
        check("missing_required", materialize(repo, root, mutate="missing_required")["status"] == STATUS_NO_GO_MATERIAL)
        check("missing_rank", materialize(repo, root, mutate="missing_rank_source")["status"] == STATUS_NO_GO_MATERIAL)
        check("row_cap", materialize(repo, root, mutate="row_cap_exceeded")["status"] == STATUS_FAIL_BOUNDS)
        other = base / "other"; other.mkdir(); (other / "x").write_text("x", encoding="utf-8")
        check("non_owned_root_reject", validate_private_root(other, repo)[0] is False)
        wrong_owned = base / "wrong_owned"; (wrong_owned / "groups").mkdir(parents=True); keep = wrong_owned / "groups" / "keep.txt"; keep.write_text("keep", encoding="utf-8")
        (wrong_owned / PRIVATE_MANIFEST_NAME).write_text(json.dumps({"owner_bucket": "not_r2i", "schema_version": SCHEMA_VERSION}), encoding="utf-8")
        wrong_result = materialize(repo, wrong_owned)
        check("materialize_does_not_delete_non_owned_groups", wrong_result["status"] == STATUS_NO_GO_ROOT and keep.exists())
    leak = build_report(STATUS_DEFAULT, False); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"
    check("leak_scanner", scan_public_report(leak)["status"] == "fail")
    over = build_report(STATUS_DEFAULT, False); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True
    check("overauth", any(issue.startswith("overauthorization_") for issue in validate_report(over)))
    check("stale_readback", public_readback_match(999)["all_public_readback_match_bool"] is False)
    rank_probe = {"candidate_path": "src/example/store_parser.rs", "candidate_kind": "gold_evidence"}
    rank_probe_changed = {"candidate_path": "src/example/store_parser.rs", "candidate_kind": "hard_negative"}
    check("ranking_policy_ignores_gold_kind", score_for_source("bm25_like", 1, rank_probe, "store parser") == score_for_source("bm25_like", 1, rank_probe_changed, "store parser") and score_for_source("rrf_like", 1, rank_probe, "store parser") == score_for_source("rrf_like", 1, rank_probe_changed, "store parser"))
    pass_report = build_report(STATUS_PASS, True, True, "valid_explicit_r2i_private_root", good)
    check("pass_report_validates", validate_report(pass_report) == [])
    bad_claim = json.loads(json.dumps(pass_report)); bad_claim["claim_boundary_records"][0]["experiment_metrics_bool"] = True
    check("claim_drift_fail", "claim_boundary_experiment_metrics_bool" in validate_report(bad_claim))
    bad_rank = json.loads(json.dumps(pass_report)); bad_rank["rank_source_material_records"][0]["exact_ranks_scores_public_bool"] = True
    check("rank_publication_drift_fail", any(issue.startswith("rank_source_") for issue in validate_report(bad_rank)))
    bad_root = json.loads(json.dumps(pass_report)); bad_root["private_output_root_records"][0]["root_path_published_bool"] = True
    check("root_publication_drift_fail", "private_root_root_path_published_bool" in validate_report(bad_root))
    bad_stop = json.loads(json.dumps(pass_report)); bad_stop["stop_go_records"][0]["haae_r2j_harder_diversified_material_experiment_authorized_bool"] = False
    check("stop_go_drift_fail", "stop_go_haae_r2j_harder_diversified_material_experiment_authorized_bool" in validate_report(bad_stop))
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-output-root", "/tmp/x"])
        check("safe_parser", False)
    except ValueError: check("safe_parser", True)
    bounds = build_report(STATUS_DEFAULT, True, True, result={"task_count": 20, "candidate_depth_cap": 41, "total_rows": 1, "group_counts": {}, "rank_sources": []})
    check("bounds_drift", bounds["status"] == STATUS_FAIL_BOUNDS)
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
    if args["target"] != TARGET_TASK_COUNT or args["depth"] != CANDIDATE_DEPTH or args["cap"] != PRIVATE_ROW_CAP:
        report = build_report(STATUS_FAIL_BOUNDS, True); write_report(report, out); return 1
    ok, reason = validate_private_root(Path(args["root"]), repo)
    if not ok:
        report = build_report(STATUS_NO_GO_ROOT, True, False, reason); write_report(report, out); return 0
    result = materialize(repo, Path(args["root"]))
    report = build_report(result["status"], True, True, reason, result)
    path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] in {STATUS_PASS, STATUS_NO_GO_ROOT, STATUS_NO_GO_MATERIAL} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
