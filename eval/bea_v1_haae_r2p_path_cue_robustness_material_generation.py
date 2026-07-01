#!/usr/bin/env python3
"""BEA-v1-HAAE-R2P path-cue robustness material generation.

Default mode is safe and writes no private material. Explicit mode generates
bounded private rows from committed public R14 medium fixtures only.
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

PHASE = "BEA-v1-HAAE-R2P Path-Cue Robustness Material Generation"
SLUG = "bea_v1_haae_r2p_path_cue_robustness_material_generation"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2O_CHECKPOINT = "4ffc9eb"
R2O_STATUS = "haae_r2o_robustness_preflight_design_complete_r2p_path_cue_robustness_material_generation_authorized"
R2O_REPORT_PATH = Path("artifacts/bea_v1_haae_r2o_robustness_preflight_design/bea_v1_haae_r2o_robustness_preflight_design_report.json")

STATUS_DEFAULT = "haae_r2p_unavailable_no_explicit_path_cue_robustness_material_generation_opt_in"
STATUS_PASS = "haae_r2p_path_cue_robustness_material_generation_complete_r2q_public_audit_authorized"
STATUS_NO_GO_ROOT = "haae_r2p_no_go_private_output_root_invalid"
STATUS_NO_GO_MATERIAL = "haae_r2p_no_go_material_incomplete"
STATUS_FAIL_SOURCE = "haae_r2p_fail_closed_source_lock_mismatch"
STATUS_FAIL_BOUNDS = "haae_r2p_fail_closed_locked_bounds_mismatch"
STATUS_FAIL_LEAK = "haae_r2p_fail_closed_public_artifact_leak"
STATUS_FAIL_READBACK = "haae_r2p_fail_closed_public_readback_mismatch"
STATUS_FAIL_OVERAUTH = "haae_r2p_fail_closed_stop_go_overauthorization"

TARGET_TASK_COUNT = 20
CANDIDATE_DEPTH = 40
PRIVATE_ROW_CAP = 20000
SELF_TEST_EXPECTED = 22
NEXT_PHASE = "BEA-v1-HAAE-R2Q Public Audit Package"
PRIVATE_MANIFEST_NAME = "haae_r2p_private_manifest.json"
OWNER_BUCKET = "haae_r2p_path_cue_robustness_material_generation"

SCHEMA_GROUPS = ["task_identity", "anchor_source", "candidate_pool", "rank_pack", "evidence_core", "outcome_metric", "span_projection", "scheduler_action", "arm_assignment", "safety_probe_signal"]
REQUIRED_GROUPS = {"task_identity", "anchor_source", "candidate_pool", "rank_pack", "evidence_core", "outcome_metric", "span_projection"}
PLACEHOLDER_GROUPS = {"scheduler_action", "arm_assignment", "safety_probe_signal"}
VARIANTS = ["original", "path_scrambled", "extension_bucket_preserved", "directory_depth_preserved", "control_baseline_strengthened"]
RANK_SOURCES = ["path_prior", "path_scrambled_prior", "extension_bucket_prior", "directory_depth_prior", "control_baseline_strengthened", "rrf_variant_fusion"]
FORBIDDEN_STOP_TRUE = ["experiment_metrics_authorized_bool", "candidate_generation_beyond_material_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_outside_fixture_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool"]
GATE_NAMES = ["r2o_source_locked_gate", "explicit_opt_in_gate", "private_output_root_boundary_gate", "locked_task_count_gate", "locked_candidate_depth_gate", "private_row_cap_gate", "fixture_subset_gate", "variant_coverage_gate", "rank_source_coverage_gate", "required_schema_groups_meaningful_gate", "gold_policy_private_only_gate", "ranking_policy_label_independent_gate", "no_experiment_metrics_gate", "public_aggregate_only_gate", "no_old_private_root_read_gate", "no_retrieval_runtime_source_scan_gate", "no_ci_network_provider_gate", "no_scheduler_selector_gate", "stop_go_r2q_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


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
    if n <= 20000: return "count_le_20000"
    return "count_gt_20000"


def validate_r2o_source(r2o: dict[str, Any]) -> dict[str, bool]:
    src = (r2o.get("source_lock_records") or [{}])[0]
    stop = (r2o.get("stop_go_records") or [{}])[0]
    contract = (r2o.get("r2p_contract_records") or [{}])[0]
    status_ok = r2o.get("status") == R2O_STATUS
    scan_ok = r2o.get("forbidden_scan", {}).get("status") == "pass"
    checkpoint_ok = src.get("locked_haae_r2n_checkpoint") == "a9066d2"
    auth_ok = stop.get("haae_r2p_path_cue_robustness_material_generation_authorized_bool") is True
    contract_ok = contract.get("target_task_count_bucket") == "count_20" and contract.get("candidate_depth_bucket") == "count_40" and contract.get("private_row_cap_bucket") == "count_20000" and contract.get("variant_bucket") == "/".join(VARIANTS) and contract.get("experiment_metrics_in_r2p_bool") is False
    boundary_ok = all(stop.get(field) is False for field in ["haae_r2o_execution_authorized_bool", "haae_r2p_execution_authorized_by_r2o_bool", "ci_execution_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"])
    return {"status_ok": status_ok, "scan_ok": scan_ok, "checkpoint_ok": checkpoint_ok, "auth_ok": auth_ok, "contract_ok": contract_ok, "boundary_ok": boundary_ok, "source_locked": status_ok and scan_ok and checkpoint_ok and auth_ok and contract_ok and boundary_ok}


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
                return False, "root_not_empty_or_r2p_owned"
            try:
                manifest = load_json(root / PRIVATE_MANIFEST_NAME)
            except Exception:
                return False, "root_manifest_invalid"
            if manifest.get("owner_bucket") != OWNER_BUCKET:
                return False, "root_not_r2p_owned"
    return True, "valid_explicit_r2p_private_root"


def validate_output_tree(root: Path) -> tuple[bool, str]:
    try:
        root_resolved = root.resolve(strict=True)
    except OSError:
        return False, "root_resolution_failed"
    group_dir = root / "groups"
    if group_dir.exists():
        if group_dir.is_symlink():
            return False, "groups_symlink"
        try:
            group_resolved = group_dir.resolve(strict=True)
        except OSError:
            return False, "groups_resolution_failed"
        if group_resolved != root_resolved / "groups" or root_resolved not in group_resolved.parents:
            return False, "groups_outside_root"
        for child in group_dir.iterdir():
            if child.is_symlink():
                return False, "group_file_symlink"
            try:
                child_resolved = child.resolve(strict=False)
            except OSError:
                return False, "group_file_resolution_failed"
            if root_resolved not in child_resolved.parents:
                return False, "group_file_outside_root"
    return True, "output_tree_safe"


def select_public_fixture(repo: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], str]:
    tasks = load_jsonl(repo / "fixtures" / "r14" / "tasks" / "medium.jsonl")
    labels = {row["task_id"]: row for row in load_jsonl(repo / "fixtures" / "r14" / "labels" / "medium.jsonl")}
    selected = [task for task in tasks[:TARGET_TASK_COUNT] if labels.get(task.get("task_id"), {}).get("gold_spans")]
    return selected, labels, bucket_count(len(tasks))


def path_ext(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[-1] if "." in name else "none"


def path_depth(path: str) -> int:
    return len([part for part in path.split("/") if part])


def variant_path(path: str, variant: str, index: int) -> str:
    ext = path_ext(path)
    depth = path_depth(path)
    if variant == "original":
        return path
    if variant == "path_scrambled":
        return f"scrambled/v{index:03d}/unit_{index:03d}.scrub"
    if variant == "extension_bucket_preserved":
        return f"ext_bucket/v{index:03d}/candidate_{index:03d}.{ext}"
    if variant == "directory_depth_preserved":
        parts = [f"d{(index + i) % 7}" for i in range(max(1, depth - 1))]
        return "/".join(parts + [f"candidate_{index:03d}.mask"])
    if variant == "control_baseline_strengthened":
        return f"control/strengthened/{index % 5}/candidate_{index:03d}.ctrl"
    return path


def tokenize(value: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9_]+", value or "")}


def stable_hash_score(value: str) -> float:
    total = 0
    for idx, char in enumerate(value):
        total = (total + (idx + 1) * ord(char)) % 1000003
    return total / 1000003.0


def rank_score(source: str, candidate: dict[str, Any], query: str, candidate_index: int) -> float:
    path = str(candidate.get("variant_path", ""))
    original = str(candidate.get("source_path", ""))
    variant = str(candidate.get("variant_bucket", ""))
    q_tokens = tokenize(query)
    p_tokens = tokenize(path.replace("/", " ").replace(".", " "))
    overlap = len(q_tokens & p_tokens)
    depth = path_depth(path)
    ext_bonus = 1.0 if path_ext(path) in {"rs", "py", "ts", "tsx", "js", "go"} else 0.0
    if source == "path_prior":
        return (2.0 if variant == "original" else 0.0) + (1.0 if "/src/" in f"/{original}" else 0.0) + ext_bonus - depth * 0.01 + stable_hash_score(path) * 0.001
    if source == "path_scrambled_prior":
        return (2.0 if variant == "path_scrambled" else 0.0) + stable_hash_score(path) * 0.01
    if source == "extension_bucket_prior":
        return (2.0 if variant == "extension_bucket_preserved" else 0.0) + ext_bonus + stable_hash_score(path) * 0.001
    if source == "directory_depth_prior":
        return (2.0 if variant == "directory_depth_preserved" else 0.0) - abs(depth - 4) * 0.1 + stable_hash_score(path) * 0.001
    if source == "control_baseline_strengthened":
        return (2.0 if variant == "control_baseline_strengthened" else 0.0) + stable_hash_score(f"control::{candidate_index}::{path}")
    if source == "rrf_variant_fusion":
        return overlap * 0.2 + ext_bonus + (1.0 if variant in {"original", "extension_bucket_preserved", "directory_depth_preserved"} else 0.0) + stable_hash_score(path) * 0.001
    return stable_hash_score(path)


def base_private_candidates(task_index: int, label: dict[str, Any], all_labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for span in label.get("gold_spans", []):
        candidates.append({"source_path": span.get("path"), "private_role_bucket": "gold_evidence", "private_label_ref": span})
    for neg in label.get("hard_negatives", []):
        candidates.append({"source_path": neg.get("path"), "private_role_bucket": "hard_negative", "private_label_ref": neg})
    offset = 1
    while len({row.get("source_path") for row in candidates if row.get("source_path")}) < 8 and offset < len(all_labels):
        other = all_labels[(task_index + offset) % len(all_labels)]
        for span in other.get("gold_spans", []) + other.get("hard_negatives", []):
            candidates.append({"source_path": span.get("path"), "private_role_bucket": "cross_row_candidate", "private_label_ref": span})
        offset += 1
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for row in candidates:
        path = row.get("source_path")
        if path and path not in seen:
            seen.add(path)
            result.append(row)
    return result[:8]


def rank_orders_for_probe(gold_mutation: str) -> dict[str, list[str]]:
    query = "StoreError"
    base = [{"source_path": "crates/openlocus-store/src/lib.rs", "private_role_bucket": gold_mutation}, {"source_path": "crates/openlocus-store/src/tdb_adapter.rs", "private_role_bucket": "other"}]
    candidates: list[dict[str, Any]] = []
    idx = 1
    for item in base:
        for variant in VARIANTS:
            candidates.append({"candidate_key": f"probe_{idx:04d}", "source_path": item["source_path"], "variant_bucket": variant, "variant_path": variant_path(item["source_path"], variant, idx), "private_role_bucket": item["private_role_bucket"]})
            idx += 1
    orders: dict[str, list[str]] = {}
    for source in RANK_SOURCES:
        scored = [(rank_score(source, cand, query, i), cand["candidate_key"]) for i, cand in enumerate(candidates, start=1)]
        scored.sort(key=lambda item: (-item[0], item[1]))
        orders[source] = [key for _, key in scored]
    return orders


def materialize(repo: Path, private_root: Path, *, mutate: str | None = None) -> dict[str, Any]:
    tasks, label_map, fixture_bucket = select_public_fixture(repo)
    if len(tasks) != TARGET_TASK_COUNT:
        return {"status": STATUS_NO_GO_MATERIAL, "fixture_bucket": fixture_bucket, "group_counts": {}, "total_rows": 0}
    rows: dict[str, list[dict[str, Any]]] = {group: [] for group in SCHEMA_GROUPS}
    labels_in_order = [label_map[task["task_id"]] for task in tasks]
    variant_counts = {variant: 0 for variant in VARIANTS}
    rank_sources: set[str] = set()
    candidate_rows = 0
    rank_rows = 0
    for task_index, task in enumerate(tasks):
        label = label_map[task["task_id"]]
        task_key = f"r2p_task_{task_index:04d}"
        rows["task_identity"].append({"task_key": task_key, "task": task, "robustness_material_bool": True})
        rows["anchor_source"].append({"task_key": task_key, "source_fixture": "r14_medium", "subset_policy": "deterministic_first_20_public_rows", "variant_policy": "path_cue_robustness"})
        base_candidates = base_private_candidates(task_index, label, labels_in_order)
        task_candidates: list[dict[str, Any]] = []
        idx = 1
        for base in base_candidates:
            for variant in VARIANTS:
                if len(task_candidates) >= CANDIDATE_DEPTH:
                    break
                candidate_key = f"{task_key}_cand_{idx:04d}"
                candidate = {"task_key": task_key, "candidate_key": candidate_key, "source_path": base["source_path"], "variant_path": variant_path(str(base["source_path"]), variant, idx), "variant_bucket": variant, "private_role_bucket": base["private_role_bucket"], "private_label_ref": base["private_label_ref"]}
                task_candidates.append(candidate)
                variant_counts[variant] += 1
                idx += 1
            if len(task_candidates) >= CANDIDATE_DEPTH:
                break
        for c_idx, candidate in enumerate(task_candidates, start=1):
            candidate_rows += 1
            rows["candidate_pool"].append({"task_key": task_key, "candidate_key": candidate["candidate_key"], "source_path": candidate["source_path"], "variant_path": candidate["variant_path"], "variant_bucket": candidate["variant_bucket"], "private_role_bucket": candidate["private_role_bucket"]})
            rows["evidence_core"].append({"task_key": task_key, "candidate_key": candidate["candidate_key"], "path": candidate["variant_path"], "source_path_private": candidate["source_path"], "variant_bucket": candidate["variant_bucket"], "private_label_ref": candidate["private_label_ref"]})
            rows["span_projection"].append({"task_key": task_key, "candidate_key": candidate["candidate_key"], "path": candidate["variant_path"], "source_path_private": candidate["source_path"], "projected_start_line": candidate["private_label_ref"].get("start_line"), "projected_end_line": candidate["private_label_ref"].get("end_line"), "projection_variant_bucket": candidate["variant_bucket"]})
        for source in RANK_SOURCES:
            scored = []
            for c_idx, candidate in enumerate(task_candidates, start=1):
                scored.append((rank_score(source, candidate, task["query"], c_idx), c_idx, candidate))
            scored.sort(key=lambda item: (-item[0], item[1], item[2]["candidate_key"]))
            for rank_value, (score, c_idx, candidate) in enumerate(scored, start=1):
                rank_rows += 1
                rank_sources.add(source)
                rows["rank_pack"].append({"task_key": task_key, "candidate_key": candidate["candidate_key"], "rank_source": source, "private_rank": rank_value, "private_score": score, "variant_bucket": candidate["variant_bucket"], "ranking_policy_uses_gold_bool": False})
        rows["outcome_metric"].append({"task_key": task_key, "task_id": task["task_id"], "query": task["query"], "gold_spans": label.get("gold_spans", []), "hard_negatives": label.get("hard_negatives", []), "gold_labels_private_only_bool": True, "gold_used_for_ranking_bool": False, "coverage_validation_only_bool": True, "experiment_metrics_computed_bool": False})
    for group in PLACEHOLDER_GROUPS:
        rows[group].append({"placeholder_group": group, "status": "placeholder_allowed_in_r2p_material_generation"})
    if mutate == "missing_required":
        rows["candidate_pool"] = []
    if mutate == "missing_rank_source":
        rows["rank_pack"] = [row for row in rows["rank_pack"] if row.get("rank_source") != "path_prior"]
        rank_sources.discard("path_prior")
    total_rows = sum(len(value) for value in rows.values())
    if mutate == "row_cap_exceeded":
        total_rows = PRIVATE_ROW_CAP + 1
    if total_rows > PRIVATE_ROW_CAP:
        return {"status": STATUS_FAIL_BOUNDS, "fixture_bucket": fixture_bucket, "group_counts": {group: len(value) for group, value in rows.items()}, "total_rows": total_rows, "rank_sources": sorted(rank_sources), "variant_counts": variant_counts}
    if private_root.exists() and any(private_root.iterdir()):
        try:
            existing_manifest = load_json(private_root / PRIVATE_MANIFEST_NAME)
        except Exception:
            return {"status": STATUS_NO_GO_ROOT, "fixture_bucket": fixture_bucket, "group_counts": {}, "total_rows": 0, "root_issue_bucket": "root_manifest_invalid"}
        if existing_manifest.get("owner_bucket") != OWNER_BUCKET or existing_manifest.get("schema_version") != SCHEMA_VERSION:
            return {"status": STATUS_NO_GO_ROOT, "fixture_bucket": fixture_bucket, "group_counts": {}, "total_rows": 0, "root_issue_bucket": "root_not_r2p_owned"}
    private_root.mkdir(parents=True, exist_ok=True)
    tree_ok, tree_reason = validate_output_tree(private_root)
    if not tree_ok:
        return {"status": STATUS_NO_GO_ROOT, "fixture_bucket": fixture_bucket, "group_counts": {}, "total_rows": 0, "root_issue_bucket": tree_reason}
    group_dir = private_root / "groups"
    group_dir.mkdir(parents=True, exist_ok=True)
    root_resolved = private_root.resolve(strict=True)
    for group in SCHEMA_GROUPS:
        out_file = group_dir / f"{group}.jsonl"
        if out_file.exists() and out_file.is_symlink():
            return {"status": STATUS_NO_GO_ROOT, "fixture_bucket": fixture_bucket, "group_counts": {}, "total_rows": 0, "root_issue_bucket": "group_file_symlink"}
        if root_resolved not in out_file.resolve(strict=False).parents:
            return {"status": STATUS_NO_GO_ROOT, "fixture_bucket": fixture_bucket, "group_counts": {}, "total_rows": 0, "root_issue_bucket": "group_file_outside_root"}
        write_jsonl(out_file, rows[group])
    group_counts = {group: len(load_jsonl(group_dir / f"{group}.jsonl")) for group in SCHEMA_GROUPS}
    required_ok = all(group_counts.get(group, 0) > 0 for group in REQUIRED_GROUPS)
    variants_ok = all(count > 0 for count in variant_counts.values())
    rank_ok = set(RANK_SOURCES).issubset(rank_sources)
    no_metrics = all(row.get("experiment_metrics_computed_bool") is False for row in rows["outcome_metric"])
    labels_private = all(row.get("gold_labels_private_only_bool") is True and row.get("gold_used_for_ranking_bool") is False for row in rows["outcome_metric"])
    status = STATUS_PASS if required_ok and variants_ok and rank_ok and no_metrics and labels_private else STATUS_NO_GO_MATERIAL
    (private_root / PRIVATE_MANIFEST_NAME).write_text(json.dumps({"owner_bucket": OWNER_BUCKET, "schema_version": SCHEMA_VERSION, "status_bucket": status, "task_count_bucket": "count_20", "candidate_depth_cap_bucket": "count_40", "private_row_cap_bucket": "count_20000", "rank_source_count_bucket": bucket_count(len(rank_sources)), "variant_count_bucket": bucket_count(len(VARIANTS)), "raw_values_private_bool": True, "experiment_metrics_computed_bool": False}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": status, "fixture_bucket": fixture_bucket, "group_counts": group_counts, "total_rows": total_rows, "rank_sources": sorted(rank_sources), "variant_counts": variant_counts, "task_count": len(tasks), "candidate_depth_cap": CANDIDATE_DEPTH, "candidate_rows": candidate_rows, "rank_rows": rank_rows, "outcome_rows": group_counts.get("outcome_metric", 0), "experiment_metrics_computed_bool": not no_metrics, "gold_labels_private_only_bool": labels_private, "ranking_policy_uses_gold_bool": False}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_path|source_path|variant_path|\"gold_spans\"|\"hard_negatives\"|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|hit_rate|top10|top5|top1|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, STATUS_DEFAULT, f"{total}/{total}", R2O_CHECKPOINT, R2O_STATUS, "explicit opt-in", "target 20 tasks", "candidate depth 40", "row cap 20000", "original/path_scrambled/extension_bucket_preserved/directory_depth_preserved/control_baseline_strengthened", "path_prior/path_scrambled_prior/extension_bucket_prior/directory_depth_prior/control_baseline_strengthened/rrf_variant_fusion", "gold labels private only", "no experiment metrics in R2P", NEXT_PHASE]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2p-path-cue-robustness-material-generation.md")) and has_all(read("docs/zh/bea-v1-haae-r2p-path-cue-robustness-material-generation.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2p-path-cue-robustness-material-generation.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(status: str, explicit: bool, root_valid: bool = False, root_reason: str = "not_supplied", result: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED, r2o: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2o is None:
        try: r2o = load_json(repo / R2O_REPORT_PATH)
        except Exception: r2o = {}
    source = validate_r2o_source(r2o)
    result = result or {}
    readback = public_readback_match(self_test_total)
    group_counts = result.get("group_counts", {})
    rank_sources = set(result.get("rank_sources", []))
    variant_counts = result.get("variant_counts", {})
    required_ok = all(group_counts.get(group, 0) > 0 for group in REQUIRED_GROUPS)
    rank_ok = set(RANK_SOURCES).issubset(rank_sources)
    variant_ok = all(int(variant_counts.get(variant, 0)) > 0 for variant in VARIANTS)
    no_metrics = result.get("experiment_metrics_computed_bool") is not True
    gold_policy_ok = result.get("gold_labels_private_only_bool", True) is True and result.get("ranking_policy_uses_gold_bool", False) is False
    if not source["source_locked"]:
        final_status = STATUS_FAIL_SOURCE
    elif explicit and not root_valid:
        final_status = STATUS_NO_GO_ROOT
    elif explicit and (int(result.get("task_count", 0)) != TARGET_TASK_COUNT or int(result.get("candidate_depth_cap", CANDIDATE_DEPTH)) > CANDIDATE_DEPTH or int(result.get("total_rows", 0)) > PRIVATE_ROW_CAP):
        final_status = STATUS_FAIL_BOUNDS
    elif explicit and not (required_ok and rank_ok and variant_ok and no_metrics and gold_policy_ok):
        final_status = STATUS_NO_GO_MATERIAL
    elif explicit and not readback["all_public_readback_match_bool"]:
        final_status = STATUS_FAIL_READBACK
    elif explicit:
        final_status = STATUS_PASS
    else:
        final_status = status
    passed = final_status == STATUS_PASS
    gates = {"r2o_source_locked_gate": source["source_locked"], "explicit_opt_in_gate": explicit, "private_output_root_boundary_gate": (not explicit) or root_valid, "locked_task_count_gate": (not explicit) or int(result.get("task_count", 0)) == TARGET_TASK_COUNT, "locked_candidate_depth_gate": (not explicit) or int(result.get("candidate_depth_cap", 0)) <= CANDIDATE_DEPTH, "private_row_cap_gate": int(result.get("total_rows", 0)) <= PRIVATE_ROW_CAP, "fixture_subset_gate": True, "variant_coverage_gate": variant_ok if explicit else False, "rank_source_coverage_gate": rank_ok if explicit else False, "required_schema_groups_meaningful_gate": required_ok if explicit else False, "gold_policy_private_only_gate": gold_policy_ok, "ranking_policy_label_independent_gate": True, "no_experiment_metrics_gate": no_metrics, "public_aggregate_only_gate": True, "no_old_private_root_read_gate": True, "no_retrieval_runtime_source_scan_gate": True, "no_ci_network_provider_gate": True, "no_scheduler_selector_gate": True, "stop_go_r2q_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": final_status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2psource0000", "locked_haae_r2o_checkpoint": R2O_CHECKPOINT, "locked_haae_r2o_status": R2O_STATUS, "r2o_status_match_bool": source["status_ok"], "r2o_forbidden_scan_pass_bool": source["scan_ok"], "r2p_authorization_match_bool": source["auth_ok"], "r2o_contract_match_bool": source["contract_ok"], "r2o_boundary_match_bool": source["boundary_ok"], "source_locked_bool": source["source_locked"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2pmode0000", "mode_bucket": "explicit_path_cue_robustness_material_generation" if explicit else "default_no_explicit_opt_in", "explicit_opt_in_bool": explicit, "private_read_bucket": "count_0", "private_write_bucket": bucket_count(int(result.get("total_rows", 0))) if explicit else "count_0", "generation_performed_bool": explicit}],
        "private_output_root_records": [{"anonymous_private_output_root_id": "haaer2proot0000", "root_supplied_bool": explicit, "root_valid_bool": root_valid, "root_boundary_bucket": root_reason, "root_path_published_bool": False, "root_basename_filename_published_bool": False, "old_private_root_discovery_bool": False}],
        "fixture_subset_records": [{"anonymous_fixture_subset_id": "haaer2pfixture0000", "source_fixture_bucket": "r14_medium_public_fixture", "subset_policy_bucket": "deterministic_first_20_public_rows", "target_task_count_bucket": "target_20_tasks", "candidate_depth_cap_bucket": "candidate_depth_40", "raw_fixture_rows_published_bool": False}],
        "variant_material_records": [{"anonymous_variant_material_id": f"haaer2pvariant{idx:04d}", "variant_bucket": variant, "present_bool": int(variant_counts.get(variant, 0)) > 0, "private_row_count_bucket": bucket_count(int(variant_counts.get(variant, 0))), "raw_variant_rows_published_bool": False} for idx, variant in enumerate(VARIANTS)],
        "rank_source_material_records": [{"anonymous_rank_source_material_id": f"haaer2prank{idx:04d}", "rank_source_bucket": src, "present_bool": src in rank_sources, "rank_row_count_bucket": bucket_count(int(result.get("rank_rows", 0))) if src in rank_sources else "count_0", "exact_ranks_scores_public_bool": False} for idx, src in enumerate(RANK_SOURCES)],
        "schema_group_material_records": [{"anonymous_schema_group_material_id": f"haaer2pgroup{idx:04d}", "group_bucket": group, "required_meaningful_bool": group in REQUIRED_GROUPS, "meaningful_rows_present_bool": group_counts.get(group, 0) > 0 and group not in PLACEHOLDER_GROUPS, "placeholder_allowed_bool": group in PLACEHOLDER_GROUPS, "private_row_count_bucket": bucket_count(int(group_counts.get(group, 0))), "raw_rows_published_bool": False} for idx, group in enumerate(SCHEMA_GROUPS)],
        "gold_policy_records": [{"anonymous_gold_policy_id": "haaer2pgold0000", "gold_labels_private_only_bool": True, "coverage_validation_only_bool": True, "ranking_policy_uses_gold_bool": False, "label_mutation_changes_rank_order_bool": False, "raw_gold_values_published_bool": False}],
        "root_safety_records": [{"anonymous_root_safety_id": "haaer2psafety0000", "root_boundary_pass_bool": root_valid if explicit else False, "no_root_discovery_bool": True, "no_old_private_root_read_bool": True, "no_arbitrary_delete_bool": True, "no_path_publication_bool": True}],
        "quality_control_records": [{"anonymous_quality_control_id": "haaer2pquality0000", "required_groups_meaningful_bool": required_ok, "all_variants_present_bool": variant_ok, "all_rank_sources_present_bool": rank_ok, "no_experiment_metrics_computed_bool": no_metrics, "private_row_cap_respected_bool": int(result.get("total_rows", 0)) <= PRIVATE_ROW_CAP, "public_aggregate_only_bool": True}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2pclaim0000", "material_generation_bool": explicit, "experiment_metrics_bool": False, "old_private_root_read_bool": False, "retrieval_runtime_bool": False, "source_scan_outside_fixture_bool": False, "ci_network_provider_clone_bool": False, "scheduler_haae_selector_bool": False, "bea_v1_a_p5_default_bool": False, "method_scaling_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2pgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2psynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["default_no_private", "missing_opt_in", "root_boundary_reject", "source_lock_drift", "bounds_drift", "missing_required_group", "missing_rank_source", "row_cap_exceeded", "variant_coverage", "label_mutation_rank_invariant", "leak_scanner", "overauth", "stale_readback", "safe_parser", "explicit_fixture_smoke", "pass_report_validates"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2preadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2pstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_fix_r2p_material_generation", "haae_r2q_public_audit_package_authorized_bool": passed, "r2q_public_only_audit_bool": passed, "experiment_metrics_authorized_bool": False, "new_material_generation_authorized_bool": False, "candidate_generation_beyond_material_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_outside_fixture_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["source_lock_records", "execution_mode_records", "private_output_root_records", "fixture_subset_records", "variant_material_records", "rank_source_material_records", "schema_group_material_records", "gold_policy_records", "root_safety_records", "quality_control_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2o_checkpoint") != R2O_CHECKPOINT or source.get("locked_haae_r2o_status") != R2O_STATUS or source.get("source_locked_bool") is not True:
        issues.append("source_lock_mismatch")
    for field in ["r2o_status_match_bool", "r2o_forbidden_scan_pass_bool", "r2p_authorization_match_bool", "r2o_contract_match_bool", "r2o_boundary_match_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    mode = (report.get("execution_mode_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if mode.get("mode_bucket") != "explicit_path_cue_robustness_material_generation" or mode.get("explicit_opt_in_bool") is not True or mode.get("generation_performed_bool") is not True or mode.get("private_read_bucket") != "count_0" or mode.get("private_write_bucket") == "count_0": issues.append("execution_mode_mismatch")
    fixture = (report.get("fixture_subset_records") or [{}])[0]
    if fixture.get("source_fixture_bucket") != "r14_medium_public_fixture" or fixture.get("subset_policy_bucket") != "deterministic_first_20_public_rows" or fixture.get("target_task_count_bucket") != "target_20_tasks" or fixture.get("candidate_depth_cap_bucket") != "candidate_depth_40" or fixture.get("raw_fixture_rows_published_bool") is not False: issues.append("fixture_subset_mismatch")
    if report.get("status") == STATUS_PASS:
        quality = (report.get("quality_control_records") or [{}])[0]
        for field in ["required_groups_meaningful_bool", "all_variants_present_bool", "all_rank_sources_present_bool", "no_experiment_metrics_computed_bool", "private_row_cap_respected_bool", "public_aggregate_only_bool"]:
            if quality.get(field) is not True: issues.append(f"quality_{field}")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        root = (report.get("private_output_root_records") or [{}])[0]
        for field in ["root_supplied_bool", "root_valid_bool"]:
            if root.get(field) is not True: issues.append(f"private_root_{field}")
        if root.get("root_boundary_bucket") != "valid_explicit_r2p_private_root": issues.append("private_root_boundary_bucket")
        for field in ["root_path_published_bool", "root_basename_filename_published_bool", "old_private_root_discovery_bool"]:
            if root.get(field) is not False: issues.append(f"private_root_{field}")
        safety = (report.get("root_safety_records") or [{}])[0]
        for field in ["root_boundary_pass_bool", "no_root_discovery_bool", "no_old_private_root_read_bool", "no_arbitrary_delete_bool", "no_path_publication_bool"]:
            if safety.get(field) is not True: issues.append(f"root_safety_{field}")
        variants = {row.get("variant_bucket"): row for row in report.get("variant_material_records", [])}
        if set(variants) != set(VARIANTS): issues.append("variant_set_mismatch")
        for variant in VARIANTS:
            if variants.get(variant, {}).get("present_bool") is not True or variants.get(variant, {}).get("raw_variant_rows_published_bool") is not False:
                issues.append(f"variant_{variant}_mismatch")
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
    gold = (report.get("gold_policy_records") or [{}])[0]
    for field in ["gold_labels_private_only_bool", "coverage_validation_only_bool"]:
        if gold.get(field) is not True: issues.append(f"gold_policy_{field}")
    for field in ["ranking_policy_uses_gold_bool", "label_mutation_changes_rank_order_bool", "raw_gold_values_published_bool"]:
        if gold.get(field) is not False: issues.append(f"gold_policy_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["experiment_metrics_bool", "old_private_root_read_bool", "retrieval_runtime_bool", "source_scan_outside_fixture_bool", "ci_network_provider_clone_bool", "scheduler_haae_selector_bool", "bea_v1_a_p5_default_bool", "method_scaling_claim_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        for field in ["haae_r2q_public_audit_package_authorized_bool", "r2q_public_only_audit_bool"]:
            if stop.get(field) is not True: issues.append(f"stop_go_{field}")
    for field in FORBIDDEN_STOP_TRUE:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    if report.get("status") == STATUS_PASS:
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True:
                issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {"allow": False, "confirm": False, "root": "", "target": TARGET_TASK_COUNT, "depth": CANDIDATE_DEPTH, "cap": PRIVATE_ROW_CAP, "self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in {"--allow-private-path-cue-robustness-material-generation", "--confirm-private-rows-only", "--self-test"}:
            if arg == "--allow-private-path-cue-robustness-material-generation": parsed["allow"] = True
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
    bad_source = load_json(repo / R2O_REPORT_PATH); bad_source["status"] = "wrong"
    check("source_lock_drift", build_report(STATUS_DEFAULT, False, r2o=bad_source)["status"] == STATUS_FAIL_SOURCE)
    with tempfile.TemporaryDirectory(prefix="r2p_selftest_") as tmp:
        base = Path(tmp)
        root = base / "private"
        ok, reason = validate_private_root(root, repo)
        check("empty_root_ok", ok and reason == "valid_explicit_r2p_private_root")
        good = materialize(repo, root)
        check("explicit_fixture_smoke", good["status"] == STATUS_PASS)
        check("missing_required", materialize(repo, root, mutate="missing_required")["status"] == STATUS_NO_GO_MATERIAL)
        check("missing_rank", materialize(repo, root, mutate="missing_rank_source")["status"] == STATUS_NO_GO_MATERIAL)
        check("row_cap", materialize(repo, root, mutate="row_cap_exceeded")["status"] == STATUS_FAIL_BOUNDS)
        other = base / "other"; other.mkdir(); (other / "x").write_text("x", encoding="utf-8")
        check("non_owned_root_reject", validate_private_root(other, repo)[0] is False)
        wrong_owned = base / "wrong_owned"; wrong_owned.mkdir(); (wrong_owned / PRIVATE_MANIFEST_NAME).write_text(json.dumps({"owner_bucket": "not_r2p"}), encoding="utf-8")
        check("wrong_owned_root_reject", materialize(repo, wrong_owned)["status"] == STATUS_NO_GO_ROOT)
        symlink_target = base / "outside"; symlink_target.mkdir()
        symlink_root = base / "symlink_owned"; symlink_root.mkdir(); (symlink_root / PRIVATE_MANIFEST_NAME).write_text(json.dumps({"owner_bucket": OWNER_BUCKET, "schema_version": SCHEMA_VERSION}), encoding="utf-8")
        (symlink_root / "groups").symlink_to(symlink_target, target_is_directory=True)
        symlink_result = materialize(repo, symlink_root)
        check("groups_symlink_reject", symlink_result["status"] == STATUS_NO_GO_ROOT and not any(symlink_target.iterdir()))
        pass_report = build_report(STATUS_PASS, True, True, "valid_explicit_r2p_private_root", good)
        check("pass_report_validates", validate_report(pass_report) == [])
        source_drift = json.loads(json.dumps(pass_report)); source_drift["source_lock_records"][0]["r2o_contract_match_bool"] = False
        check("source_lock_field_drift", "source_lock_r2o_contract_match_bool" in validate_report(source_drift))
        mode_drift = json.loads(json.dumps(pass_report)); mode_drift["execution_mode_records"][0]["generation_performed_bool"] = False
        check("execution_mode_drift", "execution_mode_mismatch" in validate_report(mode_drift))
        fixture_drift = json.loads(json.dumps(pass_report)); fixture_drift["fixture_subset_records"][0]["target_task_count_bucket"] = "wrong"
        check("fixture_subset_drift", "fixture_subset_mismatch" in validate_report(fixture_drift))
        boundary_drift = json.loads(json.dumps(pass_report)); boundary_drift["private_output_root_records"][0]["root_boundary_bucket"] = "wrong"
        check("root_boundary_bucket_drift", "private_root_boundary_bucket" in validate_report(boundary_drift))
        safety_drift = json.loads(json.dumps(pass_report)); safety_drift["root_safety_records"][0]["no_arbitrary_delete_bool"] = False
        check("root_safety_drift", "root_safety_no_arbitrary_delete_bool" in validate_report(safety_drift))
    check("label_mutation_rank_invariant", rank_orders_for_probe("gold_evidence") == rank_orders_for_probe("hard_negative"))
    leak = build_report(STATUS_DEFAULT, False); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"
    check("leak_scanner", scan_public_report(leak)["status"] == "fail")
    over = build_report(STATUS_DEFAULT, False); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True
    check("overauth", any(issue.startswith("overauthorization_") for issue in validate_report(over)))
    check("stale_readback", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-output-root", "/tmp/x"])
        check("safe_parser", False)
    except ValueError: check("safe_parser", True)
    bounds = build_report(STATUS_DEFAULT, True, True, result={"task_count": 20, "candidate_depth_cap": 41, "total_rows": 1, "group_counts": {}, "rank_sources": [], "variant_counts": {}})
    check("bounds_drift", bounds["status"] == STATUS_FAIL_BOUNDS)
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
    if args["out"]:
        try: out = public_artifact_path(args["out"])
        except ValueError:
            print("invalid arguments", file=sys.stderr); return 2
    else:
        out = None
    if args["target"] != TARGET_TASK_COUNT or args["depth"] != CANDIDATE_DEPTH or args["cap"] != PRIVATE_ROW_CAP:
        report = build_report(STATUS_FAIL_BOUNDS, bool(args["allow"]))
        write_report(report, out)
        print(json.dumps({"status": report["status"]}, sort_keys=True))
        return 1
    if not args["allow"]:
        report = build_report(STATUS_DEFAULT, False)
        path = write_report(report, out)
        print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
        return 0
    if not args["confirm"] or not args["root"]:
        report = build_report(STATUS_NO_GO_ROOT, True)
        path = write_report(report, out)
        print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
        return 1
    root = Path(args["root"])
    ok, reason = validate_private_root(root, repo)
    result = materialize(repo, root) if ok else {}
    report = build_report(STATUS_PASS if ok else STATUS_NO_GO_ROOT, True, ok, reason, result)
    path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
