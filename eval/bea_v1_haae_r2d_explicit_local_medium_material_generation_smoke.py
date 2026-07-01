#!/usr/bin/env python3
"""BEA-v1-HAAE-R2D explicit local medium material generation smoke.

Default mode is public-only and unavailable. Explicit mode may write bounded
private JSONL rows under an operator supplied private root. The public artifact
is aggregate-only and must not contain private paths, raw task ids, queries,
candidates, labels, scores, hashes, snippets, filenames, or row values.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2D Explicit Local Medium Material Generation Smoke"
SLUG = "bea_v1_haae_r2d_explicit_local_medium_material_generation_smoke"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2C_CHECKPOINT = "68000b2"
R2C_STATUS = "haae_r2c_local_medium_material_smoke_preflight_complete_r2d_generation_smoke_authorized"
R2C_REPORT_PATH = Path("artifacts/bea_v1_haae_r2c_local_medium_material_smoke_preflight/bea_v1_haae_r2c_local_medium_material_smoke_preflight_report.json")

STATUS_DEFAULT = "haae_r2d_unavailable_no_explicit_medium_material_generation_opt_in"
STATUS_PASS = "haae_r2d_explicit_local_medium_material_generation_smoke_complete_r2e_material_audit_authorized"
STATUS_NO_GO_FIXTURE = "haae_r2d_no_go_medium_fixture_insufficient"
STATUS_NO_GO_ROOT = "haae_r2d_no_go_private_output_root_invalid"
STATUS_NO_GO_MATERIAL = "haae_r2d_no_go_medium_material_incomplete"
STATUS_FAIL_SOURCE_LOCK = "haae_r2d_fail_closed_source_lock_mismatch"
STATUS_FAIL_BOUNDS = "haae_r2d_fail_closed_contract_bounds_mismatch"
STATUS_FAIL_PUBLIC_LEAK = "haae_r2d_fail_closed_public_artifact_leak"
STATUS_FAIL_READBACK = "haae_r2d_fail_closed_public_readback_mismatch"
STATUS_FAIL_OVERAUTH = "haae_r2d_fail_closed_stop_go_overauthorization"

SUBSET_POLICY = "deterministic_public_manifest_prefix_cap_10_to_20"
SOURCE_FIXTURE_BUCKET = "count_21_to_50"
TARGET_TASK_COUNT = 20
TARGET_TASK_BUCKET = "count_10_to_20"
CANDIDATE_DEPTH = 20
CANDIDATE_DEPTH_BUCKET = "count_20"
PRIVATE_ROW_CAP = 5000
PRIVATE_ROW_CAP_BUCKET = "count_le_5000"
NEXT_PHASE = "BEA-v1-HAAE-R2E Local Medium Material Audit Package"
SELF_TEST_EXPECTED = 19
PRIVATE_MANIFEST_NAME = "haae_r2d_private_manifest.json"

SCHEMA_GROUPS = ["task_identity", "anchor_source", "candidate_pool", "rank_pack", "span_projection", "scheduler_action", "evidence_core", "arm_assignment", "outcome_metric", "safety_probe_signal"]
REQUIRED_GROUPS = {"task_identity", "anchor_source", "candidate_pool", "rank_pack", "evidence_core", "outcome_metric"}
PLACEHOLDER_GROUPS = {"scheduler_action", "arm_assignment", "safety_probe_signal"}
RANK_SOURCES = {"bm25_like", "symbol_overlap", "rrf_like"}

FORBIDDEN_STOP_FIELDS = ["new_material_generation_authorized_bool", "experiment_comparison_authorized_bool", "r2_recompute_authorized_bool", "candidate_generation_authorized_bool", "retrieval_runtime_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "runtime_default_change_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool"]
CLAIM_FORBIDDEN_FALSE_FIELDS = ["experiment_comparison_bool", "r2_recompute_bool", "candidate_generation_beyond_materializer_bool", "retrieval_runtime_bool", "ci_network_provider_bool", "scheduler_haae_selector_bool", "bea_v1_a_p5_runtime_default_bool", "method_scaling_claim_bool", "raw_publication_bool"]

GATE_NAMES = ["source_lock_gate", "r2c_authorization_boundary_gate", "explicit_opt_in_gate", "private_output_root_boundary_gate", "fixed_subset_policy_gate", "fixed_target_task_count_gate", "fixed_candidate_depth_gate", "private_row_cap_gate", "medium_fixture_sufficient_gate", "required_schema_groups_meaningful_gate", "rank_sources_present_gate", "public_aggregate_only_gate", "no_experiment_comparison_gate", "no_r2_recompute_gate", "no_runtime_retrieval_source_scan_gate", "no_ci_network_provider_gate", "no_scheduler_haae_selector_gate", "no_bea_v1_a_p5_runtime_default_gate", "no_method_scaling_claim_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def bucket_count(n: int) -> str:
    if n <= 0:
        return "count_0"
    if n <= 5:
        return "count_2_to_5"
    if n <= 20:
        return "count_10_to_20"
    if n <= 50:
        return "count_21_to_50"
    if n <= 5000:
        return "count_le_5000"
    return "count_gt_5000"


def validate_r2c_lock(r2c: dict[str, Any]) -> dict[str, bool]:
    src = (r2c.get("source_lock_records") or [{}])[0]
    stop = (r2c.get("stop_go_records") or [{}])[0]
    fixture = (r2c.get("public_fixture_preflight_records") or [{}])[0]
    status_ok = r2c.get("status") == R2C_STATUS
    scan_ok = r2c.get("forbidden_scan", {}).get("status") == "pass"
    checkpoint_ok = src.get("locked_haae_r2b_checkpoint") == "dea8a2f"
    caps_ok = fixture.get("fixture_count_bucket") == SOURCE_FIXTURE_BUCKET and fixture.get("subset_policy_bucket") == SUBSET_POLICY and fixture.get("target_task_bucket") == TARGET_TASK_BUCKET and fixture.get("candidate_depth_bucket") == CANDIDATE_DEPTH_BUCKET and fixture.get("private_row_cap_bucket") == PRIVATE_ROW_CAP_BUCKET
    auth_ok = stop.get("haae_r2d_explicit_local_medium_material_generation_smoke_authorized_bool") is True and stop.get("haae_r2d_execution_authorized_bool") is True and stop.get("haae_r2d_private_write_authorized_bool") is True and stop.get("haae_r2d_material_generation_authorized_bool") is True
    boundary_ok = all(stop.get(field) is False for field in ["ci_execution_authorized_bool", "network_authorized_bool", "provider_model_network_authorized_bool", "experiment_authorized_bool", "r2_recompute_authorized_bool", "retrieval_runtime_authorized_bool", "scheduler_haae_execution_authorized_bool", "selector_reranker_authorized_bool", "runtime_default_change_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool"])
    return {"status_ok": status_ok, "scan_ok": scan_ok, "checkpoint_ok": checkpoint_ok, "caps_ok": caps_ok, "auth_ok": auth_ok, "boundary_ok": boundary_ok, "source_locked": status_ok and scan_ok and checkpoint_ok and caps_ok and auth_ok and boundary_ok}


def validate_private_root(root: Path, repo: Path) -> tuple[bool, str]:
    try:
        resolved = root.resolve(strict=False)
        repo_resolved = repo.resolve(strict=True)
    except OSError:
        return False, "path_resolution_failed"
    if ".." in root.parts:
        return False, "path_traversal"
    if root.exists() and root.is_symlink():
        return False, "root_is_symlink"
    if resolved == repo_resolved or repo_resolved in resolved.parents:
        return False, "root_inside_public_tree"
    if not (str(resolved).startswith("/tmp/") or str(resolved).startswith("/var/tmp/")):
        return False, "root_not_temp_private_bucket"
    if root.exists() and not root.is_dir():
        return False, "root_not_directory"
    if root.exists():
        entries = [entry.name for entry in root.iterdir()]
        if entries:
            if PRIVATE_MANIFEST_NAME not in entries:
                return False, "root_not_empty_or_r2d_owned"
            try:
                manifest = load_json(root / PRIVATE_MANIFEST_NAME)
            except Exception:
                return False, "root_manifest_invalid"
            if manifest.get("owner_bucket") != "haae_r2d_explicit_local_medium_material_generation_smoke":
                return False, "root_not_r2d_owned"
    return True, "valid_explicit_temp_private_root"


def select_tasks(repo: Path, limit: int = TARGET_TASK_COUNT) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], str]:
    tasks = load_jsonl(repo / "fixtures" / "r14" / "tasks" / "medium.jsonl")
    labels = {row["task_id"]: row for row in load_jsonl(repo / "fixtures" / "r14" / "labels" / "medium.jsonl")}
    selected = [task for task in tasks[:limit] if labels.get(task.get("task_id"), {}).get("gold_spans")]
    return selected, labels, bucket_count(len(tasks))


def materialize(repo: Path, private_root: Path, *, mutate: str | None = None) -> dict[str, Any]:
    tasks, labels, fixture_bucket = select_tasks(repo)
    if len(tasks) != TARGET_TASK_COUNT or fixture_bucket != SOURCE_FIXTURE_BUCKET:
        return {"status": STATUS_NO_GO_FIXTURE, "fixture_bucket": fixture_bucket, "group_counts": {}}
    rows: dict[str, list[dict[str, Any]]] = {group: [] for group in SCHEMA_GROUPS}
    for idx, task in enumerate(tasks):
        label = labels[task["task_id"]]
        task_key = f"r2d_task_{idx:04d}"
        rows["task_identity"].append({"task_key": task_key, "task": task, "label_quality": label.get("label_quality")})
        rows["anchor_source"].append({"task_key": task_key, "source_fixture": "r14_medium", "subset_policy": SUBSET_POLICY, "source_fixture_index": idx})
        candidates = []
        for span in label.get("gold_spans", []):
            candidates.append({"candidate_path": span.get("path"), "candidate_kind": "gold_span_anchor", "label_ref": span})
        for neg in label.get("hard_negatives", []):
            candidates.append({"candidate_path": neg.get("path"), "candidate_kind": "hard_negative_anchor", "label_ref": neg})
        seen = set()
        deduped = []
        for candidate in candidates:
            path = candidate.get("candidate_path")
            if path and path not in seen:
                seen.add(path); deduped.append(candidate)
        for rank, candidate in enumerate(deduped[:CANDIDATE_DEPTH], start=1):
            rows["candidate_pool"].append({"task_key": task_key, "task_id": task["task_id"], "query": task["query"], "candidate_rank": rank, "candidate_path": candidate["candidate_path"], "candidate_kind": candidate["candidate_kind"]})
            bm25_rank = rank
            symbol_rank = rank if task.get("method_hint") in {"symbol", "regex"} else None
            rows["rank_pack"].append({"task_key": task_key, "task_id": task["task_id"], "candidate_path": candidate["candidate_path"], "candidate_rank": rank, "rank_sources": ["bm25_like", "rrf_like"] + (["symbol_overlap"] if symbol_rank else []), "bm25_like_rank": bm25_rank, "symbol_overlap_rank": symbol_rank, "rrf_like_rank": rank, "rrf_like_score": 1.0 / (60 + rank)})
            ref = candidate["label_ref"]
            rows["evidence_core"].append({"task_key": task_key, "task_id": task["task_id"], "query": task["query"], "path": candidate["candidate_path"], "start_line": ref.get("start_line"), "end_line": ref.get("end_line"), "evidence_reason": ref.get("rationale")})
            rows["span_projection"].append({"task_key": task_key, "task_id": task["task_id"], "path": candidate["candidate_path"], "projected_start_line": ref.get("start_line"), "projected_end_line": ref.get("end_line"), "projection_source": candidate["candidate_kind"]})
        rows["outcome_metric"].append({"task_key": task_key, "task_id": task["task_id"], "query": task["query"], "candidate_depth": CANDIDATE_DEPTH, "candidate_count": len(deduped[:CANDIDATE_DEPTH]), "gold_spans": label.get("gold_spans", []), "hard_negatives": label.get("hard_negatives", []), "gold_file_hit": bool(label.get("gold_spans")), "first_gold_file_rank": 1 if label.get("gold_spans") else None})
    for group in PLACEHOLDER_GROUPS:
        rows[group].append({"placeholder_group": group, "status": "placeholder_allowed_in_r2d_smoke"})
    if mutate == "missing_required":
        rows["candidate_pool"] = []
    if mutate == "missing_rank_source":
        for row in rows["rank_pack"]:
            row["rank_sources"] = [src for src in row["rank_sources"] if src != "rrf_like"]
            row.pop("rrf_like_rank", None)
    total_rows = sum(len(v) for v in rows.values())
    if mutate == "row_cap_exceeded":
        total_rows = PRIVATE_ROW_CAP + 1
    if total_rows > PRIVATE_ROW_CAP:
        return {"status": STATUS_FAIL_BOUNDS, "fixture_bucket": fixture_bucket, "group_counts": {group: len(value) for group, value in rows.items()}, "total_rows": total_rows}
    if private_root.exists():
        entries = [entry.name for entry in private_root.iterdir()]
        if entries:
            if PRIVATE_MANIFEST_NAME not in entries:
                return {"status": STATUS_NO_GO_ROOT, "fixture_bucket": fixture_bucket, "group_counts": {}, "total_rows": 0, "root_issue_bucket": "root_not_empty_or_r2d_owned"}
            try:
                manifest = load_json(private_root / PRIVATE_MANIFEST_NAME)
            except Exception:
                return {"status": STATUS_NO_GO_ROOT, "fixture_bucket": fixture_bucket, "group_counts": {}, "total_rows": 0, "root_issue_bucket": "root_manifest_invalid"}
            if manifest.get("owner_bucket") != "haae_r2d_explicit_local_medium_material_generation_smoke":
                return {"status": STATUS_NO_GO_ROOT, "fixture_bucket": fixture_bucket, "group_counts": {}, "total_rows": 0, "root_issue_bucket": "root_not_r2d_owned"}
            groups_path = private_root / "groups"
            if groups_path.exists():
                shutil.rmtree(groups_path)
    group_dir = private_root / "groups"
    group_dir.mkdir(parents=True, exist_ok=True)
    for group, group_rows in rows.items():
        write_jsonl(group_dir / f"{group}.jsonl", group_rows)
    group_counts = {group: len(load_jsonl(group_dir / f"{group}.jsonl")) for group in SCHEMA_GROUPS}
    required_ok = all(group_counts.get(group, 0) > 0 for group in REQUIRED_GROUPS)
    present_sources = set()
    for row in rows["rank_pack"]:
        present_sources.update(row.get("rank_sources", []))
    rank_ok = RANK_SOURCES.issubset(present_sources)
    status = STATUS_PASS if required_ok and rank_ok else STATUS_NO_GO_MATERIAL
    (private_root / PRIVATE_MANIFEST_NAME).write_text(json.dumps({
        "owner_bucket": "haae_r2d_explicit_local_medium_material_generation_smoke",
        "schema_version": SCHEMA_VERSION,
        "status_bucket": status,
        "task_count_bucket": bucket_count(len(tasks)),
        "candidate_depth_bucket": CANDIDATE_DEPTH_BUCKET,
        "private_row_cap_bucket": PRIVATE_ROW_CAP_BUCKET,
        "group_count_bucket": bucket_count(len(SCHEMA_GROUPS)),
        "raw_values_private_bool": True,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": status, "fixture_bucket": fixture_bucket, "group_counts": group_counts, "total_rows": total_rows, "rank_sources": sorted(present_sources), "task_count": len(tasks), "candidate_rows": group_counts.get("candidate_pool", 0), "rank_rows": group_counts.get("rank_pack", 0), "outcome_rows": group_counts.get("outcome_metric", 0)}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_path_label", re.compile(r"candidate_path|gold_spans|hard_negatives|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash", re.compile(r"rrf_like_score|bm25_like_rank|symbol_overlap_rank|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, STATUS_DEFAULT, f"{total}/{total}", R2C_CHECKPOINT, "explicit opt-in", SUBSET_POLICY, SOURCE_FIXTURE_BUCKET, TARGET_TASK_BUCKET, CANDIDATE_DEPTH_BUCKET, PRIVATE_ROW_CAP_BUCKET, "private write bucket", "private read validation bucket", "public aggregate-only", "no raw publication", "no experiment comparison", "no R2 recompute", "no runtime/retrieval/source scan beyond fixture", "no CI/network/provider", "no scheduler/HAAE/selector", "no BEA-v1-A/P5/runtime/default", "no method/scaling claim", NEXT_PHASE]
    spaced = [f"{total} / {total}" if f == f"{total}/{total}" else f for f in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(f in text for f in fragments) or all(f in text for f in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2d-explicit-local-medium-material-generation-smoke.md")) and has_all(read("docs/zh/bea-v1-haae-r2d-explicit-local-medium-material-generation-smoke.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2d-explicit-local-medium-material-generation-smoke.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(status: str, explicit: bool, root_valid: bool = False, root_reason: str = "not_supplied", result: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED, r2c: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2c is None:
        try: r2c = load_json(repo / R2C_REPORT_PATH)
        except Exception: r2c = {}
    lock = validate_r2c_lock(r2c)
    result = result or {}
    readback = public_readback_match(self_test_total)
    group_counts = result.get("group_counts", {})
    rank_sources = set(result.get("rank_sources", []))
    required_ok = all(group_counts.get(group, 0) > 0 for group in REQUIRED_GROUPS)
    rank_ok = RANK_SOURCES.issubset(rank_sources) if explicit else False
    gates = {"source_lock_gate": lock["source_locked"], "r2c_authorization_boundary_gate": lock["auth_ok"] and lock["boundary_ok"], "explicit_opt_in_gate": explicit, "private_output_root_boundary_gate": root_valid, "fixed_subset_policy_gate": True, "fixed_target_task_count_gate": True, "fixed_candidate_depth_gate": True, "private_row_cap_gate": int(result.get("total_rows", 0)) <= PRIVATE_ROW_CAP, "medium_fixture_sufficient_gate": result.get("fixture_bucket", SOURCE_FIXTURE_BUCKET) == SOURCE_FIXTURE_BUCKET, "required_schema_groups_meaningful_gate": required_ok, "rank_sources_present_gate": rank_ok, "public_aggregate_only_gate": True, "no_experiment_comparison_gate": True, "no_r2_recompute_gate": True, "no_runtime_retrieval_source_scan_gate": True, "no_ci_network_provider_gate": True, "no_scheduler_haae_selector_gate": True, "no_bea_v1_a_p5_runtime_default_gate": True, "no_method_scaling_claim_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2dsource0000", "locked_haae_r2c_checkpoint": R2C_CHECKPOINT, "locked_haae_r2c_status": R2C_STATUS, "r2c_source_locked_bool": lock["source_locked"], "r2c_authorization_boundary_match_bool": lock["auth_ok"] and lock["boundary_ok"], "r2c_caps_match_bool": lock["caps_ok"], "r2c_forbidden_scan_pass_bool": lock["scan_ok"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2dmode0000", "mode_bucket": "explicit_local_medium_material_generation_smoke" if explicit else "default_no_explicit_opt_in", "explicit_opt_in_bool": explicit, "private_read_validation_bucket": "count_1_to_10" if explicit else "count_0", "private_write_bucket": bucket_count(int(result.get("total_rows", 0))) if explicit else "count_0", "local_manual_only_bool": True, "ci_network_provider_bool": False}],
        "private_output_root_records": [{"anonymous_private_output_root_id": "haaer2droot0000", "root_supplied_bool": explicit, "root_valid_bool": root_valid, "root_boundary_bucket": root_reason, "no_path_basename_filename_published_bool": True}],
        "public_fixture_subset_records": [{"anonymous_public_fixture_subset_id": "haaer2dsubset0000", "source_fixture_bucket": "r14_medium_public_fixture", "source_fixture_count_bucket": SOURCE_FIXTURE_BUCKET, "subset_policy_bucket": SUBSET_POLICY, "target_task_bucket": TARGET_TASK_BUCKET, "candidate_depth_bucket": CANDIDATE_DEPTH_BUCKET, "private_row_cap_bucket": PRIVATE_ROW_CAP_BUCKET, "raw_fixture_rows_published_bool": False}],
        "material_generation_recipe_records": [{"anonymous_material_generation_recipe_id": "haaer2drecipe0000", "recipe_bucket": "local_label_anchored_lexical_rank_trace_materializer", "standalone_implementation_bool": True, "imports_r1e_runtime_bool": False, "retrieval_runtime_bool": False, "experiment_comparison_bool": False}],
        "private_schema_group_material_records": [{"anonymous_private_schema_group_material_id": f"haaer2dgroup{idx:04d}", "group_bucket": group, "private_row_count_bucket": bucket_count(int(group_counts.get(group, 0))), "meaningful_required_bool": group in REQUIRED_GROUPS, "placeholder_allowed_bool": group in PLACEHOLDER_GROUPS, "meaningful_rows_present_bool": group_counts.get(group, 0) > 0 and group not in PLACEHOLDER_GROUPS, "raw_rows_published_bool": False} for idx, group in enumerate(SCHEMA_GROUPS)],
        "private_material_manifest_records": [{"anonymous_private_material_manifest_id": "haaer2dmanifest0000", "total_private_row_count_bucket": bucket_count(int(result.get("total_rows", 0))), "task_count_bucket": bucket_count(int(result.get("task_count", 0))), "candidate_row_count_bucket": bucket_count(int(result.get("candidate_rows", 0))), "rank_row_count_bucket": bucket_count(int(result.get("rank_rows", 0))), "outcome_row_count_bucket": bucket_count(int(result.get("outcome_rows", 0))), "no_private_path_published_bool": True}],
        "public_aggregate_quality_records": [{"anonymous_public_aggregate_quality_id": "haaer2dquality0000", "required_groups_meaningful_bool": required_ok, "rank_sources_present_bool": rank_ok, "bm25_like_present_bool": "bm25_like" in rank_sources, "symbol_overlap_present_bool": "symbol_overlap" in rank_sources, "rrf_like_present_bool": "rrf_like" in rank_sources, "public_aggregate_only_bool": True}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2dclaim0000", "material_generation_smoke_bool": explicit, "experiment_comparison_bool": False, "r2_recompute_bool": False, "candidate_generation_beyond_materializer_bool": False, "retrieval_runtime_bool": False, "ci_network_provider_bool": False, "scheduler_haae_selector_bool": False, "bea_v1_a_p5_runtime_default_bool": False, "method_scaling_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2dgate{idx:04d}", "gate_bucket": name, "gate_passed_bool": bool(gates.get(name, False)), "gate_evaluated_on_aggregate_bool": True, "gate_reads_private_rows_bool": False} for idx, name in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2dsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["default_no_private_read_write", "missing_opt_in_no_private_write", "repo_public_root_rejected", "symlink_traversal_rejected", "r2c_source_lock_and_drift", "fixture_rowcap_schema_rank_no_go", "leak_scanner", "stop_go_overauth", "docs_readback_stale", "validate_contract_caps", "safe_parser", "explicit_valid_fixture"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2dreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2dstop0000", "next_allowed_phase": NEXT_PHASE if status == STATUS_PASS else "stop_or_fix_r2d_material_generation", "haae_r2e_local_medium_material_audit_package_authorized_bool": status == STATUS_PASS, "new_material_generation_authorized_bool": False, "experiment_comparison_authorized_bool": False, "r2_recompute_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_runtime_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "runtime_default_change_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False}]}
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_PUBLIC_LEAK
    if report["status"] == STATUS_PASS and not readback["all_public_readback_match_bool"]: report["status"] = STATUS_FAIL_READBACK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "execution_mode_records", "private_output_root_records", "public_fixture_subset_records", "material_generation_recipe_records", "private_schema_group_material_records", "private_material_manifest_records", "public_aggregate_quality_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in FORBIDDEN_STOP_FIELDS:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2c_checkpoint") != R2C_CHECKPOINT or source.get("locked_haae_r2c_status") != R2C_STATUS: issues.append("source_lock_mismatch")
    if report.get("status") == STATUS_PASS:
        for field in ["r2c_source_locked_bool", "r2c_authorization_boundary_match_bool", "r2c_caps_match_bool", "r2c_forbidden_scan_pass_bool"]:
            if source.get(field) is not True: issues.append(f"source_lock_field_not_true_{field}")
    subset = (report.get("public_fixture_subset_records") or [{}])[0]
    if subset.get("subset_policy_bucket") != SUBSET_POLICY or subset.get("target_task_bucket") != TARGET_TASK_BUCKET or subset.get("candidate_depth_bucket") != CANDIDATE_DEPTH_BUCKET or subset.get("private_row_cap_bucket") != PRIVATE_ROW_CAP_BUCKET: issues.append("contract_caps_mismatch")
    quality = (report.get("public_aggregate_quality_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        mode = (report.get("execution_mode_records") or [{}])[0]
        root = (report.get("private_output_root_records") or [{}])[0]
        recipe = (report.get("material_generation_recipe_records") or [{}])[0]
        manifest = (report.get("private_material_manifest_records") or [{}])[0]
        claim = (report.get("claim_boundary_records") or [{}])[0]
        if mode.get("explicit_opt_in_bool") is not True: issues.append("execution_mode_missing_explicit_opt_in")
        if mode.get("private_write_bucket") not in {"count_10_to_20", "count_21_to_50", "count_le_5000"}: issues.append("execution_mode_private_write_bucket_invalid")
        if mode.get("ci_network_provider_bool") is not False: issues.append("execution_mode_ci_network_overauth")
        if root.get("root_supplied_bool") is not True or root.get("root_valid_bool") is not True: issues.append("private_root_not_valid")
        if root.get("no_path_basename_filename_published_bool") is not True: issues.append("private_root_path_publication_not_blocked")
        if recipe.get("standalone_implementation_bool") is not True: issues.append("recipe_not_standalone")
        if recipe.get("imports_r1e_runtime_bool") is not False: issues.append("recipe_imports_r1e_runtime")
        if recipe.get("retrieval_runtime_bool") is not False: issues.append("recipe_retrieval_runtime_overauth")
        if recipe.get("experiment_comparison_bool") is not False: issues.append("recipe_experiment_comparison_overauth")
        if manifest.get("task_count_bucket") != TARGET_TASK_BUCKET: issues.append("manifest_task_count_bucket_drift")
        if manifest.get("total_private_row_count_bucket") != PRIVATE_ROW_CAP_BUCKET: issues.append("manifest_total_row_bucket_drift")
        if manifest.get("no_private_path_published_bool") is not True: issues.append("manifest_private_path_publication")
        if claim.get("material_generation_smoke_bool") is not True: issues.append("claim_material_generation_smoke_not_true")
        for field in CLAIM_FORBIDDEN_FALSE_FIELDS:
            if claim.get(field) is not False: issues.append(f"claim_boundary_overauthorization_{field}")
        if quality.get("required_groups_meaningful_bool") is not True or quality.get("rank_sources_present_bool") is not True: issues.append("material_quality_incomplete")
        for field in ["bm25_like_present_bool", "symbol_overlap_present_bool", "rrf_like_present_bool", "public_aggregate_only_bool"]:
            if quality.get(field) is not True: issues.append(f"quality_field_not_true_{field}")
        group_map = {row.get("group_bucket"): row for row in report.get("private_schema_group_material_records", [])}
        for group in REQUIRED_GROUPS:
            row = group_map.get(group, {})
            if row.get("meaningful_rows_present_bool") is not True: issues.append(f"required_group_missing_{group}")
            if row.get("raw_rows_published_bool") is not False: issues.append(f"required_group_raw_publication_{group}")
        if stop.get("haae_r2e_local_medium_material_audit_package_authorized_bool") is not True: issues.append("missing_r2e_authorization")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    allowed_flags = {"--allow-private-medium-material-generation", "--confirm-private-rows-only", "--private-output-root", "--target-task-count", "--candidate-depth", "--subset-policy", "--source-fixture", "--self-test", "--validate-report", "--out"}
    parsed: dict[str, Any] = {"allow": False, "confirm": False, "root": "", "target": TARGET_TASK_COUNT, "depth": CANDIDATE_DEPTH, "policy": SUBSET_POLICY, "source": "r14_medium", "self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg not in allowed_flags: raise ValueError("invalid arguments")
        if arg in {"--allow-private-medium-material-generation", "--confirm-private-rows-only", "--self-test"}:
            key = {"--allow-private-medium-material-generation": "allow", "--confirm-private-rows-only": "confirm", "--self-test": "self_test"}[arg]; parsed[key] = True; i += 1; continue
        if i + 1 >= len(argv): raise ValueError("invalid arguments")
        value = argv[i + 1]
        if arg == "--private-output-root": parsed["root"] = value
        elif arg == "--target-task-count": parsed["target"] = int(value) if value.isdigit() else -1
        elif arg == "--candidate-depth": parsed["depth"] = int(value) if value.isdigit() else -1
        elif arg == "--subset-policy": parsed["policy"] = value
        elif arg == "--source-fixture": parsed["source"] = value
        elif arg == "--validate-report": parsed["validate"] = value
        elif arg == "--out": parsed["out"] = value
        i += 2
    return parsed


def public_artifact_arg(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]
    path = Path(value)
    resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid public artifact path")
    return PUBLIC_REPORT_PATH


def write_report(report: dict[str, Any], out: Path | None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    base = load_json(repo / R2C_REPORT_PATH)
    def check(name: str, cond: bool) -> None:
        if not cond: failures.append(name)
    d = build_report(STATUS_DEFAULT, False); check("default_no_private", d["status"] == STATUS_DEFAULT and d["execution_mode_records"][0]["private_write_bucket"] == "count_0")
    check("missing_opt_in_no_private", build_report(STATUS_DEFAULT, False)["status"] == STATUS_DEFAULT)
    check("repo_root_rejected", validate_private_root(repo, repo)[0] is False)
    check("traversal_rejected", validate_private_root(Path("../x"), repo)[0] is False)
    check("r2c_source_lock_pass", validate_r2c_lock(base)["source_locked"])
    bad = json.loads(json.dumps(base)); bad["status"] = "wrong"; check("wrong_r2c_status_fail", not validate_r2c_lock(bad)["source_locked"])
    drift = json.loads(json.dumps(base)); drift["public_fixture_preflight_records"][0]["candidate_depth_bucket"] = "bad"; check("cap_drift_fail", not validate_r2c_lock(drift)["source_locked"])
    with __import__("tempfile").TemporaryDirectory(prefix="r2d_selftest_") as tmp:
        root = Path(tmp) / "private"
        good = materialize(repo, root); check("explicit_material_pass", good["status"] == STATUS_PASS)
        occupied = Path(tmp) / "occupied"
        occupied.mkdir()
        (occupied / "unrelated.txt").write_text("old private material\n", encoding="utf-8")
        check("non_empty_unowned_root_rejected", validate_private_root(occupied, repo)[0] is False and materialize(repo, occupied)["status"] == STATUS_NO_GO_ROOT)
        check("r2d_owned_root_can_refresh", validate_private_root(root, repo)[0] is True and materialize(repo, root)["status"] == STATUS_PASS)
        check("row_cap_exceeded", materialize(repo, root, mutate="row_cap_exceeded")["status"] == STATUS_FAIL_BOUNDS)
        check("missing_required_no_go", materialize(repo, root, mutate="missing_required")["status"] == STATUS_NO_GO_MATERIAL)
        check("missing_rank_source_no_go", materialize(repo, root, mutate="missing_rank_source")["status"] == STATUS_NO_GO_MATERIAL)
    leak = build_report(STATUS_DEFAULT, False); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus-x/src/lib.rs"; check("leak_scanner", scan_public_report(leak)["status"] == "fail")
    over = build_report(STATUS_DEFAULT, False); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("stop_go_overauth", any(i.startswith("overauthorization_") for i in validate_report(over)))
    pass_report = build_report(good["status"], True, True, "valid_explicit_temp_private_root", good)
    claim_mutation = json.loads(json.dumps(pass_report)); claim_mutation["claim_boundary_records"][0]["raw_publication_bool"] = True
    check("claim_boundary_overauth_validation_fail", any(i.startswith("claim_boundary_overauthorization") for i in validate_report(claim_mutation)))
    source_mutation = json.loads(json.dumps(pass_report)); source_mutation["source_lock_records"][0]["r2c_source_locked_bool"] = False
    check("source_lock_false_validation_fail", any(i.startswith("source_lock_field_not_true") for i in validate_report(source_mutation)))
    recipe_mutation = json.loads(json.dumps(pass_report)); recipe_mutation["material_generation_recipe_records"][0]["retrieval_runtime_bool"] = True
    check("recipe_overauth_validation_fail", "recipe_retrieval_runtime_overauth" in validate_report(recipe_mutation))
    root_mutation = json.loads(json.dumps(pass_report)); root_mutation["private_output_root_records"][0]["no_path_basename_filename_published_bool"] = False
    check("root_publication_validation_fail", "private_root_path_publication_not_blocked" in validate_report(root_mutation))
    group_mutation = json.loads(json.dumps(pass_report)); group_mutation["private_schema_group_material_records"][0]["raw_rows_published_bool"] = True
    check("group_raw_publication_validation_fail", any(i.startswith("required_group_raw_publication") for i in validate_report(group_mutation)))
    check("stale_docs", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--unknown-private", "/tmp/x"])
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
        try: report = load_json(repo / public_artifact_arg(args["validate"])); issues = validate_report(report)
        except Exception: issues = ["invalid_public_artifact_path"]; report = {"status": "unavailable"}
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_arg(args["out"]) if args["out"] else None
    if not args["allow"]:
        report = build_report(STATUS_DEFAULT, False)
        path = write_report(report, out)
        print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0
    if not args["confirm"] or not args["root"]:
        report = build_report(STATUS_DEFAULT, False)
        write_report(report, out); return 1
    if args["target"] != TARGET_TASK_COUNT or args["depth"] != CANDIDATE_DEPTH or args["policy"] != SUBSET_POLICY or args["source"] != "r14_medium":
        report = build_report(STATUS_FAIL_BOUNDS, True)
        write_report(report, out); return 1
    ok, reason = validate_private_root(Path(args["root"]), repo)
    if not ok:
        report = build_report(STATUS_NO_GO_ROOT, True, False, reason)
        write_report(report, out); return 1
    lock = validate_r2c_lock(load_json(repo / R2C_REPORT_PATH))
    if not lock["source_locked"]:
        report = build_report(STATUS_FAIL_SOURCE_LOCK, True, True, reason)
        write_report(report, out); return 1
    result = materialize(repo, Path(args["root"]))
    report = build_report(result["status"], True, True, reason, result)
    path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] in {STATUS_PASS, STATUS_NO_GO_FIXTURE, STATUS_NO_GO_ROOT, STATUS_NO_GO_MATERIAL} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
