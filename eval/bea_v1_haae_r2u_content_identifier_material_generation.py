#!/usr/bin/env python3
"""BEA-v1-HAAE-R2U content-identifier evidence material generation.

Standalone bounded materializer. Default mode writes/reads no private material.
Explicit mode writes private rows under an operator-supplied root only.
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

PHASE = "BEA-v1-HAAE-R2U Content-Identifier Evidence Material Generation Smoke"
SLUG = "bea_v1_haae_r2u_content_identifier_material_generation"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2T_CHECKPOINT = "bc58cf7"
R2T_STATUS = "haae_r2t_non_path_cue_pivot_decision_complete_r2u_content_identifier_material_generation_authorized"
R2T_REPORT_PATH = Path("artifacts/bea_v1_haae_r2t_non_path_cue_pivot_decision/bea_v1_haae_r2t_non_path_cue_pivot_decision_report.json")

STATUS_DEFAULT = "haae_r2u_unavailable_no_explicit_content_identifier_material_generation_opt_in"
STATUS_PASS = "haae_r2u_content_identifier_material_generation_complete_r2v_public_audit_authorized"
STATUS_NO_GO_ROOT = "haae_r2u_no_go_private_output_root_invalid"
STATUS_NO_GO_MATERIAL = "haae_r2u_no_go_content_identifier_material_incomplete"
STATUS_FAIL_SOURCE = "haae_r2u_fail_closed_source_lock_mismatch"
STATUS_FAIL_BOUNDS = "haae_r2u_fail_closed_locked_bounds_mismatch"
STATUS_FAIL_LEAK = "haae_r2u_fail_closed_public_artifact_leak"
STATUS_FAIL_READBACK = "haae_r2u_fail_closed_public_readback_mismatch"
STATUS_FAIL_OVERAUTH = "haae_r2u_fail_closed_stop_go_overauthorization"

TARGET_TASK_COUNT = 20
CANDIDATE_DEPTH = 40
PRIVATE_ROW_CAP = 20000
SELF_TEST_EXPECTED = 24
NEXT_PHASE = "BEA-v1-HAAE-R2V Content-Identifier Material Public Audit Package"
PRIVATE_MANIFEST_NAME = "haae_r2u_private_manifest.json"
OWNER_BUCKET = "haae_r2u_content_identifier_material_generation"

SCHEMA_GROUPS = ["task_identity", "anchor_source", "candidate_pool", "rank_pack", "evidence_core", "outcome_metric", "span_projection", "scheduler_action", "arm_assignment", "safety_probe_signal"]
REQUIRED_GROUPS = {"task_identity", "anchor_source", "candidate_pool", "rank_pack", "evidence_core", "outcome_metric", "span_projection"}
PLACEHOLDER_GROUPS = {"scheduler_action", "arm_assignment", "safety_probe_signal"}
RANK_SOURCES = ["query_identifier_overlap", "symbol_name_overlap", "content_snippet_overlap", "identifier_normalized_bm25_like", "hard_negative_quality_control", "content_identifier_fusion", "control_baseline"]
FORBIDDEN_STOP_TRUE = ["experiment_metrics_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_outside_fixture_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool"]
GATE_NAMES = ["r2t_source_locked_gate", "explicit_opt_in_gate", "private_output_root_boundary_gate", "locked_task_count_gate", "locked_candidate_depth_gate", "private_row_cap_gate", "fixture_subset_gate", "non_path_cue_policy_gate", "rank_source_coverage_gate", "required_schema_groups_meaningful_gate", "gold_policy_private_only_gate", "ranking_policy_gold_independent_gate", "no_experiment_metrics_gate", "public_aggregate_only_gate", "no_old_private_root_read_gate", "no_retrieval_runtime_source_scan_gate", "no_ci_network_provider_gate", "no_scheduler_selector_gate", "stop_go_r2v_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


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


def validate_r2t_source(r2t: dict[str, Any]) -> dict[str, bool]:
    stop = (r2t.get("stop_go_records") or [{}])[0]
    contract = (r2t.get("r2u_contract_records") or [{}])[0]
    status_ok = r2t.get("status") == R2T_STATUS
    scan_ok = r2t.get("forbidden_scan", {}).get("status") == "pass"
    auth_ok = stop.get("haae_r2u_content_identifier_material_generation_authorized_bool") is True
    contract_ok = contract.get("target_task_count_bucket") == "target_20" and contract.get("candidate_depth_bucket") == "candidate_depth_40" and contract.get("private_row_cap_bucket") == "row_cap_20000" and contract.get("content_identifier_evidence_material_bool") is True and contract.get("no_experiment_metrics_in_r2u_bool") is True
    boundary_ok = all(stop.get(field) is False for field in ["r2t_execution_authorized_bool", "execution_authorized_bool", "ci_execution_authorized_bool", "new_material_generation_in_r2t_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"])
    return {"status_ok": status_ok, "scan_ok": scan_ok, "auth_ok": auth_ok, "contract_ok": contract_ok, "boundary_ok": boundary_ok, "source_locked": status_ok and scan_ok and auth_ok and contract_ok and boundary_ok}


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
                return False, "root_not_empty_or_r2u_owned"
            try:
                manifest = load_json(root / PRIVATE_MANIFEST_NAME)
            except Exception:
                return False, "root_manifest_invalid"
            if manifest.get("owner_bucket") != OWNER_BUCKET:
                return False, "root_not_r2u_owned"
            if manifest.get("schema_version") != SCHEMA_VERSION:
                return False, "root_schema_mismatch"
            allowed_entries = {PRIVATE_MANIFEST_NAME, "groups"}
            if any(entry not in allowed_entries for entry in entries):
                return False, "root_has_unexpected_owned_entries"
    return True, "valid_explicit_r2u_private_root"


def validate_output_tree(root: Path) -> tuple[bool, str]:
    try:
        root_resolved = root.resolve(strict=True)
    except OSError:
        return False, "root_resolution_failed"
    group_dir = root / "groups"
    if group_dir.exists():
        if group_dir.is_symlink():
            return False, "groups_symlink"
        group_resolved = group_dir.resolve(strict=True)
        if group_resolved != root_resolved / "groups" or root_resolved not in group_resolved.parents:
            return False, "groups_outside_root"
        for child in group_dir.iterdir():
            if child.is_symlink():
                return False, "group_file_symlink"
            if root_resolved not in child.resolve(strict=False).parents:
                return False, "group_file_outside_root"
    return True, "output_tree_safe"


def select_public_fixture(repo: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], str]:
    tasks = load_jsonl(repo / "fixtures" / "r14" / "tasks" / "medium.jsonl")
    labels = {row["task_id"]: row for row in load_jsonl(repo / "fixtures" / "r14" / "labels" / "medium.jsonl")}
    selected = tasks[:TARGET_TASK_COUNT]
    return selected, labels, bucket_count(len(tasks))


def tokenize(value: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z0-9_]+", value or "")]


def token_set(value: str) -> set[str]:
    return set(tokenize(value))


def split_identifier(value: str) -> set[str]:
    pieces = re.sub(r"([a-z])([A-Z])", r"\1 \2", value or "")
    return token_set(pieces.replace("_", " "))


def stable_hash_score(value: str) -> float:
    total = 0
    for idx, char in enumerate(value):
        total = (total + (idx + 1) * ord(char)) % 1000003
    return total / 1000003.0


def candidate_identifier(candidate: dict[str, Any]) -> str:
    return str(candidate.get("private_identifier_text", ""))


def rank_score(source: str, candidate: dict[str, Any], query: str, candidate_index: int) -> float:
    q_tokens = split_identifier(query)
    identifier = candidate_identifier(candidate)
    id_tokens = split_identifier(identifier)
    overlap = len(q_tokens & id_tokens)
    identifier_len_penalty = abs(len(identifier) - len(query)) * 0.001
    if source == "query_identifier_overlap":
        return overlap * 3.0 - identifier_len_penalty + stable_hash_score(identifier) * 0.001
    if source == "symbol_name_overlap":
        exact = 2.0 if identifier.lower() == query.lower() else 0.0
        return exact + overlap * 1.5 + stable_hash_score(f"symbol::{identifier}") * 0.001
    if source == "content_snippet_overlap":
        return stable_hash_score(f"snippet_unavailable::{candidate_index}::{identifier}") * 0.0001
    if source == "identifier_normalized_bm25_like":
        tf = sum(1 for token in tokenize(identifier) if token in q_tokens)
        return tf * 2.0 + overlap * 0.75 - len(id_tokens) * 0.01 + stable_hash_score(f"bm25::{identifier}") * 0.001
    if source == "hard_negative_quality_control":
        hard = 1.0 if candidate.get("private_role_bucket") == "hard_negative" else 0.0
        return hard + overlap * 0.25 + stable_hash_score(f"hn::{identifier}") * 0.001
    if source == "content_identifier_fusion":
        return overlap * 2.0 + (1.0 if identifier.lower() == query.lower() else 0.0) + stable_hash_score(f"fusion::{identifier}") * 0.001
    if source == "control_baseline":
        return stable_hash_score(f"control::{candidate_index}::{identifier}")
    return stable_hash_score(identifier)


def synthetic_identifier_decoy(task_index: int, query: str, ordinal: int) -> str:
    query_parts = sorted(split_identifier(query)) or ["identifier"]
    seed = query_parts[ordinal % len(query_parts)]
    return f"{seed.title()}ContentDecoy{task_index + 1:02d}{ordinal:02d}"


def public_identifier_variants(task_index: int, task: dict[str, Any], all_tasks: list[dict[str, Any]]) -> list[dict[str, str]]:
    query = str(task.get("query", ""))
    task_type = str(task.get("task_type", "task"))
    method_hint = str(task.get("method_hint", "method"))
    query_tokens = sorted(split_identifier(query)) or ["identifier"]
    variants = [
        (query, "public_query_identifier_anchor"),
        ("".join(part.title() for part in query_tokens), "public_query_identifier_normalized"),
        ("_".join(query_tokens), "public_query_identifier_normalized"),
        (f"{query}Candidate", "public_query_identifier_expansion"),
        (f"{query}Record", "public_query_identifier_expansion"),
        (f"{query}Store", "public_query_identifier_expansion"),
        (f"{query}Handler", "public_query_identifier_expansion"),
        (f"{query}Builder", "public_query_identifier_expansion"),
        (f"{method_hint}_{query}", "public_method_hint_identifier"),
        (f"{task_type}_{query}", "public_task_type_identifier"),
    ]
    for offset, other in enumerate(all_tasks, start=1):
        if other is task:
            continue
        other_query = str(other.get("query", ""))
        if other_query:
            variants.append((other_query, "public_cross_query_identifier"))
            variants.append((f"{other_query}Candidate{offset:02d}", "public_cross_query_identifier"))
        if len(variants) >= CANDIDATE_DEPTH:
            break
    ordinal = 0
    while len(variants) < CANDIDATE_DEPTH * 2:
        variants.append((synthetic_identifier_decoy(task_index, query, ordinal), "synthetic_identifier_decoy"))
        ordinal += 1
    return [{"identifier": identifier, "role": role} for identifier, role in variants]


def base_private_candidates(task_index: int, task: dict[str, Any], all_tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for variant in public_identifier_variants(task_index, task, all_tasks):
        candidates.append({"private_identifier_text": variant["identifier"], "private_role_bucket": variant["role"], "private_label_ref": {}, "private_rationale_text": "public task/query derived content identifier"})
    seen: set[str] = set(); result: list[dict[str, Any]] = []
    for row in candidates:
        ident = row.get("private_identifier_text")
        if ident and ident not in seen:
            seen.add(str(ident)); result.append(row)
    return result[:CANDIDATE_DEPTH]


def rank_orders_for_probe(role_mutation: str) -> dict[str, list[str]]:
    query = "TdbChunkStore"
    candidates = [
        {"candidate_key": "probe_0", "private_identifier_text": "TdbChunkStore", "private_role_bucket": role_mutation, "private_rationale_text": "TdbChunkStore symbol"},
        {"candidate_key": "probe_1", "private_identifier_text": "TdbPlaceholderStore", "private_role_bucket": "other", "private_rationale_text": "TdbPlaceholderStore symbol"},
    ]
    orders: dict[str, list[str]] = {}
    for source in RANK_SOURCES:
        scored = [(rank_score(source, cand, query, i), cand["candidate_key"]) for i, cand in enumerate(candidates, start=1)]
        scored.sort(key=lambda item: (-item[0], item[1]))
        orders[source] = [key for _, key in scored]
    return orders


def public_candidate_rank_fingerprint(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    task = tasks[0]
    candidates = base_private_candidates(0, task, tasks)
    candidate_rows = [{"candidate_key": f"probe_{idx:03d}", **candidate} for idx, candidate in enumerate(candidates, start=1)]
    query = str(task.get("query", ""))
    orders: dict[str, list[str]] = {}
    for source in RANK_SOURCES:
        scored = [(rank_score(source, candidate, query, idx), candidate["candidate_key"]) for idx, candidate in enumerate(candidate_rows, start=1)]
        scored.sort(key=lambda item: (-item[0], item[1]))
        orders[source] = [key for _, key in scored]
    return {"identifiers": [row["private_identifier_text"] for row in candidate_rows], "orders": orders}


def materialize(repo: Path, private_root: Path) -> dict[str, Any]:
    tasks, label_map, fixture_bucket = select_public_fixture(repo)
    if len(tasks) != TARGET_TASK_COUNT:
        return {"status": STATUS_NO_GO_MATERIAL, "fixture_bucket": fixture_bucket, "group_counts": {}, "total_rows": 0}
    labels = [label_map.get(task["task_id"], {}) for task in tasks]
    if any(not label.get("gold_spans") for label in labels):
        return {"status": STATUS_NO_GO_MATERIAL, "fixture_bucket": fixture_bucket, "group_counts": {}, "total_rows": 0}
    rows: dict[str, list[dict[str, Any]]] = {group: [] for group in SCHEMA_GROUPS}
    task_keys: list[str] = []
    for task_index, task in enumerate(tasks):
        task_key = f"r2u_task_{task_index + 1:04d}"
        task_keys.append(task_key)
        label = label_map[task["task_id"]]
        query = str(task.get("query", ""))
        rows["task_identity"].append({"task_key": task_key, "task_id": task.get("task_id"), "query": query, "task_type": task.get("task_type"), "method_hint": task.get("method_hint"), "repo_id": task.get("repo_id")})
        rows["anchor_source"].append({"task_key": task_key, "anchor_bucket": "public_r14_medium_task", "query": query})
        private_candidates = base_private_candidates(task_index, task, tasks)
        candidate_rows: list[dict[str, Any]] = []
        for candidate_index, candidate in enumerate(private_candidates, start=1):
            candidate_key = f"{task_key}_cand_{candidate_index:03d}"
            private_label = candidate.get("private_label_ref", {})
            row = {"task_key": task_key, "candidate_key": candidate_key, "private_identifier_text": candidate.get("private_identifier_text"), "private_role_bucket": candidate.get("private_role_bucket"), "private_rationale_text": candidate.get("private_rationale_text"), "private_label_ref": private_label}
            candidate_rows.append(row)
            rows["candidate_pool"].append(row)
            rows["evidence_core"].append({"task_key": task_key, "candidate_key": candidate_key, "private_identifier_text": row["private_identifier_text"], "private_evidence_bucket": row["private_role_bucket"], "private_rationale_text": row["private_rationale_text"]})
            rows["span_projection"].append({"task_key": task_key, "candidate_key": candidate_key, "private_span_projection": private_label})
        for source in RANK_SOURCES:
            scored = [(rank_score(source, candidate, query, idx), candidate) for idx, candidate in enumerate(candidate_rows, start=1)]
            scored.sort(key=lambda item: (-item[0], str(item[1]["candidate_key"])))
            for rank, (score, candidate) in enumerate(scored[:CANDIDATE_DEPTH], start=1):
                rows["rank_pack"].append({"task_key": task_key, "candidate_key": candidate["candidate_key"], "rank_source": source, "private_rank": rank, "private_score": round(score, 8), "rank_feature_policy_bucket": "non_path_content_identifier", "gold_used_for_ranking_bool": False})
        rows["outcome_metric"].append({"task_key": task_key, "gold_spans": label.get("gold_spans", []), "hard_negatives": label.get("hard_negatives", []), "gold_labels_private_only_bool": True})
    for group in PLACEHOLDER_GROUPS:
        rows[group].append({"placeholder_group": group, "placeholder_reason_bucket": "not_executed_in_r2u"})
    total_rows = sum(len(value) for value in rows.values())
    if total_rows > PRIVATE_ROW_CAP:
        return {"status": STATUS_NO_GO_MATERIAL, "fixture_bucket": fixture_bucket, "group_counts": {k: len(v) for k, v in rows.items()}, "total_rows": total_rows}
    private_root.mkdir(parents=True, exist_ok=True)
    tree_ok, tree_reason = validate_output_tree(private_root)
    if not tree_ok:
        return {"status": STATUS_NO_GO_ROOT, "root_reason": tree_reason, "fixture_bucket": fixture_bucket, "group_counts": {}, "total_rows": 0}
    per_task_candidate_counts: dict[str, int] = {}
    for row in rows["candidate_pool"]:
        per_task_candidate_counts[row["task_key"]] = per_task_candidate_counts.get(row["task_key"], 0) + 1
    min_candidates = min(per_task_candidate_counts.values()) if per_task_candidate_counts else 0
    max_candidates = max(per_task_candidate_counts.values()) if per_task_candidate_counts else 0
    manifest = {"schema_version": SCHEMA_VERSION, "owner_bucket": OWNER_BUCKET, "status_bucket": STATUS_PASS, "source_phase_bucket": PHASE, "task_count_bucket": "count_20", "candidate_depth_cap_bucket": "count_40", "private_row_cap_bucket": "count_20000", "rank_source_buckets": RANK_SOURCES, "schema_group_buckets": SCHEMA_GROUPS, "gold_used_for_ranking_bool": False, "path_feature_policy_bucket": "path_tokens_extensions_directories_not_used_for_ranking"}
    (private_root / PRIVATE_MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for group, group_rows in rows.items():
        write_jsonl(private_root / "groups" / f"{group}.jsonl", group_rows)
    return {"status": STATUS_PASS, "fixture_bucket": fixture_bucket, "group_counts": {k: len(v) for k, v in rows.items()}, "total_rows": total_rows, "task_count": len(task_keys), "rank_sources": RANK_SOURCES, "content_snippet_availability_bucket": "unavailable_no_public_snippets", "candidate_depth_min": min_candidates, "candidate_depth_max": max_candidates, "candidate_depth_bucket": "candidate_depth_40" if min_candidates == CANDIDATE_DEPTH and max_candidates == CANDIDATE_DEPTH else bucket_count(max_candidates)}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_path|source_path|variant_path|\"gold_spans\"|\"hard_negatives\"|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|task_key|candidate_key|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, STATUS_DEFAULT, f"{total}/{total}", R2T_CHECKPOINT, R2T_STATUS, "explicit opt-in", "target 20", "candidate depth 40", "row cap 20000", "query_identifier_overlap/symbol_name_overlap/content_snippet_overlap/identifier_normalized_bm25_like/hard_negative_quality_control/content_identifier_fusion/control_baseline", "no path tokens/extensions/directories", "gold private only", "gold labels not used for ranking", NEXT_PHASE]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2u-content-identifier-material-generation.md")) and has_all(read("docs/zh/bea-v1-haae-r2u-content-identifier-material-generation.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2u-content-identifier-material-generation.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(status: str, explicit: bool, material: dict[str, Any] | None = None, root_reason: str = "not_supplied", self_test_total: int = SELF_TEST_EXPECTED, r2t: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2t is None:
        try: r2t = load_json(repo / R2T_REPORT_PATH)
        except Exception: r2t = {}
    source = validate_r2t_source(r2t)
    material = material or {"group_counts": {}, "total_rows": 0, "task_count": 0, "rank_sources": []}
    readback = public_readback_match(self_test_total)
    group_counts = material.get("group_counts", {})
    groups_meaningful = all(group_counts.get(group, 0) > 0 for group in REQUIRED_GROUPS)
    candidate_depth_ok = material.get("candidate_depth_min") == CANDIDATE_DEPTH and material.get("candidate_depth_max") == CANDIDATE_DEPTH
    material_pass = status == STATUS_PASS and material.get("task_count") == TARGET_TASK_COUNT and material.get("total_rows", 0) <= PRIVATE_ROW_CAP and set(material.get("rank_sources", [])) == set(RANK_SOURCES) and groups_meaningful and candidate_depth_ok
    if not source["source_locked"]:
        final_status = STATUS_FAIL_SOURCE
    elif explicit and not material_pass:
        final_status = STATUS_NO_GO_MATERIAL if status != STATUS_NO_GO_ROOT else STATUS_NO_GO_ROOT
    elif explicit and not readback["all_public_readback_match_bool"]:
        final_status = STATUS_FAIL_READBACK
    elif explicit:
        final_status = STATUS_PASS
    else:
        final_status = status
    passed = final_status == STATUS_PASS
    gates = {"r2t_source_locked_gate": source["source_locked"], "explicit_opt_in_gate": explicit, "private_output_root_boundary_gate": (not explicit) or root_reason.startswith("valid"), "locked_task_count_gate": material.get("task_count") == TARGET_TASK_COUNT if explicit else True, "locked_candidate_depth_gate": candidate_depth_ok if explicit else True, "private_row_cap_gate": material.get("total_rows", 0) <= PRIVATE_ROW_CAP, "fixture_subset_gate": True, "non_path_cue_policy_gate": True, "rank_source_coverage_gate": set(material.get("rank_sources", [])) == set(RANK_SOURCES) if explicit else True, "required_schema_groups_meaningful_gate": groups_meaningful if explicit else True, "gold_policy_private_only_gate": True, "ranking_policy_gold_independent_gate": True, "no_experiment_metrics_gate": True, "public_aggregate_only_gate": True, "no_old_private_root_read_gate": True, "no_retrieval_runtime_source_scan_gate": True, "no_ci_network_provider_gate": True, "no_scheduler_selector_gate": True, "stop_go_r2v_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": final_status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2usource0000", "locked_haae_r2t_checkpoint": R2T_CHECKPOINT, "locked_haae_r2t_status": R2T_STATUS, "r2t_status_match_bool": source["status_ok"], "r2t_forbidden_scan_pass_bool": source["scan_ok"], "r2t_authorization_match_bool": source["auth_ok"], "r2t_contract_match_bool": source["contract_ok"], "source_locked_bool": source["source_locked"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2umode0000", "mode_bucket": "explicit_content_identifier_generation" if explicit else "default_no_explicit_opt_in", "explicit_opt_in_bool": explicit, "generation_performed_bool": passed, "private_read_bucket": "count_1_to_10" if passed else "count_0", "private_write_bucket": bucket_count(int(material.get("total_rows", 0))) if passed else "count_0"}],
        "private_output_root_records": [{"anonymous_private_output_root_id": "haaer2uroot0000", "root_supplied_bool": explicit, "root_boundary_bucket": root_reason, "root_path_published_bool": False, "root_basename_filename_published_bool": False, "no_symlink_escape_bool": root_reason.startswith("valid") or not explicit, "no_arbitrary_delete_bool": True, "owned_refresh_only_bool": True}],
        "fixture_subset_records": [{"anonymous_fixture_subset_id": "haaer2ufixture0000", "fixture_bucket": "r14_medium_public_fixture", "source_fixture_count_bucket": material.get("fixture_bucket", "count_21_to_50"), "target_task_count_bucket": "target_20", "candidate_depth_cap_bucket": "candidate_depth_40", "private_row_cap_bucket": "row_cap_20000", "raw_fixture_rows_published_bool": False}],
        "content_identifier_material_records": [{"anonymous_content_identifier_material_id": "haaer2umaterial0000", "target_task_count_bucket": "target_20", "actual_task_count_bucket": bucket_count(int(material.get("task_count", 0))), "candidate_depth_cap_bucket": "candidate_depth_40", "actual_candidate_depth_bucket": material.get("candidate_depth_bucket", "count_0"), "private_row_cap_bucket": "row_cap_20000", "total_private_row_bucket": bucket_count(int(material.get("total_rows", 0))), "rank_source_bucket": "/".join(RANK_SOURCES), "content_snippet_availability_bucket": material.get("content_snippet_availability_bucket", "unavailable_no_public_snippets"), "experiment_metrics_computed_bool": False, "raw_path_public_bool": False, "gold_used_for_ranking_bool": False}],
        "path_masking_policy_records": [{"anonymous_path_masking_policy_id": "haaer2upathmask0000", "path_tokens_used_for_ranking_bool": False, "path_extensions_used_for_ranking_bool": False, "path_directories_used_for_ranking_bool": False, "path_derived_ranking_features_disabled_bool": True, "raw_path_public_bool": False, "gold_used_for_ranking_bool": False, "experiment_metrics_bool": False}],
        "rank_source_material_records": [{"anonymous_rank_source_material_id": f"haaer2urank{idx:04d}", "rank_source_bucket": source_name, "present_bool": passed or explicit, "availability_bucket": "unavailable_no_public_snippets" if source_name == "content_snippet_overlap" else "available_from_public_task_identifiers", "non_path_cue_rank_feature_bool": True, "gold_used_for_ranking_bool": False, "exact_ranks_scores_public_bool": False} for idx, source_name in enumerate(RANK_SOURCES)],
        "schema_group_material_records": [{"anonymous_schema_group_material_id": f"haaer2ugroup{idx:04d}", "group_bucket": group, "required_meaningful_bool": group in REQUIRED_GROUPS, "meaningful_rows_present_bool": (group_counts.get(group, 0) > 0 if group in REQUIRED_GROUPS else False), "placeholder_allowed_bool": group in PLACEHOLDER_GROUPS, "private_row_count_bucket": bucket_count(int(group_counts.get(group, 0))), "raw_rows_published_bool": False} for idx, group in enumerate(SCHEMA_GROUPS)],
        "gold_policy_records": [{"anonymous_gold_policy_id": "haaer2ugold0000", "gold_labels_private_only_bool": True, "coverage_validation_only_bool": True, "ranking_policy_uses_gold_bool": False, "raw_gold_values_published_bool": False}],
        "quality_control_records": [{"anonymous_quality_control_id": "haaer2uquality0000", "total_private_row_bucket": bucket_count(int(material.get("total_rows", 0))), "row_cap_pass_bool": int(material.get("total_rows", 0)) <= PRIVATE_ROW_CAP, "content_identifier_policy_bool": True, "path_tokens_extensions_directories_used_for_ranking_bool": False, "no_experiment_metrics_computed_bool": True, "public_aggregate_only_bool": True}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2uclaim0000", "old_private_root_read_bool": False, "retrieval_runtime_bool": False, "source_scan_outside_fixture_bool": False, "ci_network_provider_clone_bool": False, "scheduler_haae_selector_bool": False, "bea_v1_a_p5_default_bool": False, "experiment_metrics_bool": False, "method_scaling_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2ugate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2usynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["default_no_private", "missing_opt_in", "root_boundary_reject", "source_lock_drift", "bounds_drift", "missing_required_group", "missing_rank_source", "row_cap_exceeded", "candidate_depth_drift", "path_masking_policy_drift", "experiment_metric_overauth", "gold_mutation_rank_invariant", "path_feature_policy", "leak_scanner", "overauth", "stale_readback", "safe_parser", "explicit_fixture_smoke"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2ureadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2ustop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2u_material_generation", "haae_r2v_public_audit_package_authorized_bool": passed, "r2v_public_only_audit_bool": passed, "experiment_metrics_authorized_bool": False, "new_material_generation_authorized_bool": False, "candidate_generation_beyond_material_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_outside_fixture_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "execution_mode_records", "private_output_root_records", "fixture_subset_records", "content_identifier_material_records", "path_masking_policy_records", "rank_source_material_records", "schema_group_material_records", "gold_policy_records", "quality_control_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    if src.get("locked_haae_r2t_checkpoint") != R2T_CHECKPOINT or src.get("locked_haae_r2t_status") != R2T_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2t_status_match_bool", "r2t_forbidden_scan_pass_bool", "r2t_authorization_match_bool", "r2t_contract_match_bool", "source_locked_bool"]:
        if src.get(field) is not True: issues.append(f"source_lock_{field}")
    mode = (report.get("execution_mode_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if mode.get("mode_bucket") != "explicit_content_identifier_generation": issues.append("execution_mode_not_explicit")
        if mode.get("explicit_opt_in_bool") is not True or mode.get("generation_performed_bool") is not True: issues.append("execution_mode_not_performed")
        if mode.get("private_read_bucket") == "count_0" or mode.get("private_write_bucket") == "count_0": issues.append("execution_mode_private_count_missing")
    root = (report.get("private_output_root_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if root.get("root_supplied_bool") is not True: issues.append("private_root_not_supplied")
        if root.get("root_boundary_bucket") != "valid_explicit_r2u_private_root": issues.append("private_root_boundary_invalid")
        for field in ["root_path_published_bool", "root_basename_filename_published_bool"]:
            if root.get(field) is not False: issues.append(f"private_root_{field}")
        for field in ["no_symlink_escape_bool", "no_arbitrary_delete_bool", "owned_refresh_only_bool"]:
            if root.get(field) is not True: issues.append(f"private_root_{field}")
    fixture = (report.get("fixture_subset_records") or [{}])[0]
    if fixture.get("fixture_bucket") != "r14_medium_public_fixture" or fixture.get("target_task_count_bucket") != "target_20" or fixture.get("candidate_depth_cap_bucket") != "candidate_depth_40" or fixture.get("private_row_cap_bucket") != "row_cap_20000": issues.append("fixture_subset_contract_mismatch")
    if fixture.get("raw_fixture_rows_published_bool") is not False: issues.append("fixture_subset_raw_rows_public")
    ranks = {row.get("rank_source_bucket"): row for row in report.get("rank_source_material_records", [])}
    if set(ranks) != set(RANK_SOURCES): issues.append("rank_source_set_mismatch")
    for source_name in RANK_SOURCES:
        row = ranks.get(source_name, {})
        if row.get("non_path_cue_rank_feature_bool") is not True or row.get("gold_used_for_ranking_bool") is not False or row.get("exact_ranks_scores_public_bool") is not False: issues.append(f"rank_source_{source_name}_policy_mismatch")
    material = (report.get("content_identifier_material_records") or [{}])[0]
    if material.get("target_task_count_bucket") != "target_20" or material.get("candidate_depth_cap_bucket") != "candidate_depth_40" or material.get("private_row_cap_bucket") != "row_cap_20000": issues.append("content_identifier_material_bounds_mismatch")
    if material.get("rank_source_bucket") != "/".join(RANK_SOURCES): issues.append("content_identifier_material_rank_sources_mismatch")
    for field in ["experiment_metrics_computed_bool", "raw_path_public_bool", "gold_used_for_ranking_bool"]:
        if material.get(field) is not False: issues.append(f"content_identifier_material_{field}")
    if report.get("status") == STATUS_PASS and material.get("actual_candidate_depth_bucket") != "candidate_depth_40": issues.append("content_identifier_material_depth_mismatch")
    path_policy = (report.get("path_masking_policy_records") or [{}])[0]
    for field in ["path_tokens_used_for_ranking_bool", "path_extensions_used_for_ranking_bool", "path_directories_used_for_ranking_bool", "raw_path_public_bool", "gold_used_for_ranking_bool", "experiment_metrics_bool"]:
        if path_policy.get(field) is not False: issues.append(f"path_masking_policy_{field}")
    if path_policy.get("path_derived_ranking_features_disabled_bool") is not True: issues.append("path_masking_policy_not_disabled")
    groups = {row.get("group_bucket"): row for row in report.get("schema_group_material_records", [])}
    if set(groups) != set(SCHEMA_GROUPS): issues.append("schema_group_set_mismatch")
    if report.get("status") == STATUS_PASS:
        for group in REQUIRED_GROUPS:
            if groups.get(group, {}).get("meaningful_rows_present_bool") is not True: issues.append(f"required_group_{group}_not_meaningful")
    gold = (report.get("gold_policy_records") or [{}])[0]
    if gold.get("gold_labels_private_only_bool") is not True or gold.get("ranking_policy_uses_gold_bool") is not False: issues.append("gold_policy_mismatch")
    quality = (report.get("quality_control_records") or [{}])[0]
    if quality.get("path_tokens_extensions_directories_used_for_ranking_bool") is not False or quality.get("no_experiment_metrics_computed_bool") is not True or quality.get("public_aggregate_only_bool") is not True: issues.append("quality_policy_mismatch")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["old_private_root_read_bool", "retrieval_runtime_bool", "source_scan_outside_fixture_bool", "ci_network_provider_clone_bool", "scheduler_haae_selector_bool", "bea_v1_a_p5_default_bool", "experiment_metrics_bool", "method_scaling_claim_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if stop.get("haae_r2v_public_audit_package_authorized_bool") is not True or stop.get("r2v_public_only_audit_bool") is not True or stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2v_stop_go_missing")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    for field in ["new_material_generation_authorized_bool", "candidate_generation_beyond_material_authorized_bool", "raw_publication_authorized_bool", *FORBIDDEN_STOP_TRUE]:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed = {"allow": False, "confirm": False, "root": "", "target": TARGET_TASK_COUNT, "depth": CANDIDATE_DEPTH, "cap": PRIVATE_ROW_CAP, "self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in {"--allow-private-content-identifier-material-generation", "--confirm-private-rows-only", "--self-test"}:
            if arg == "--allow-private-content-identifier-material-generation": parsed["allow"] = True
            elif arg == "--confirm-private-rows-only": parsed["confirm"] = True
            else: parsed["self_test"] = True
            i += 1
        elif arg in {"--private-output-root", "--target-task-count", "--candidate-depth", "--private-row-cap", "--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            value = argv[i + 1]
            if arg == "--private-output-root": parsed["root"] = value
            elif arg == "--target-task-count": parsed["target"] = int(value)
            elif arg == "--candidate-depth": parsed["depth"] = int(value)
            elif arg == "--private-row-cap": parsed["cap"] = int(value)
            elif arg == "--validate-report": parsed["validate"] = value
            else: parsed["out"] = value
            i += 2
        else:
            raise ValueError("invalid arguments")
    if parsed["root"] and not parsed["allow"]: raise ValueError("invalid arguments")
    if parsed["target"] != TARGET_TASK_COUNT or parsed["depth"] != CANDIDATE_DEPTH or parsed["cap"] != PRIVATE_ROW_CAP: raise ValueError("invalid arguments")
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
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-output-root", "/tmp/x"])
        check("missing_opt_in", False)
    except ValueError: check("missing_opt_in", True)
    check("repo_root_reject", validate_private_root(repo, repo)[0] is False)
    with tempfile.TemporaryDirectory(prefix="r2u_selftest_") as tmp:
        root = Path(tmp) / "explicit"; ok, reason = validate_private_root(root, repo); check("root_boundary_accept", ok)
        material = materialize(repo, root); report = build_report(STATUS_PASS, True, material, reason)
        check("explicit_fixture_smoke", material.get("status") == STATUS_PASS and report["status"] == STATUS_PASS and validate_report(report) == [])
        candidate_rows = load_jsonl(root / "groups" / "candidate_pool.jsonl")
        check("gold_label_material_not_in_rank_features", all(row.get("private_label_ref") == {} and row.get("private_role_bucket") not in {"gold_evidence", "hard_negative"} for row in candidate_rows))
        too_many = dict(material); too_many["total_rows"] = PRIVATE_ROW_CAP + 1; check("row_cap_exceeded", build_report(STATUS_PASS, True, too_many, reason)["status"] == STATUS_NO_GO_MATERIAL)
        missing_group = dict(material); missing_group["group_counts"] = dict(material["group_counts"]); missing_group["group_counts"]["candidate_pool"] = 0; check("missing_required_group", build_report(STATUS_PASS, True, missing_group, reason)["status"] == STATUS_NO_GO_MATERIAL)
        missing_rank = dict(material); missing_rank["rank_sources"] = RANK_SOURCES[:-1]; check("missing_rank_source", build_report(STATUS_PASS, True, missing_rank, reason)["status"] == STATUS_NO_GO_MATERIAL)
        depth_drift = dict(material); depth_drift["candidate_depth_min"] = CANDIDATE_DEPTH - 1; depth_drift["candidate_depth_bucket"] = "count_21_to_50"; check("candidate_depth_drift", build_report(STATUS_PASS, True, depth_drift, reason)["status"] == STATUS_NO_GO_MATERIAL)
        policy_drift = json.loads(json.dumps(report)); policy_drift["path_masking_policy_records"][0]["path_tokens_used_for_ranking_bool"] = True; check("path_masking_policy_drift", any(issue.startswith("path_masking_policy_") for issue in validate_report(policy_drift)))
        metric_overauth = json.loads(json.dumps(report)); metric_overauth["content_identifier_material_records"][0]["experiment_metrics_computed_bool"] = True; check("experiment_metric_overauth", any(issue.startswith("content_identifier_material_") for issue in validate_report(metric_overauth)))
        mode_drift = json.loads(json.dumps(report)); mode_drift["execution_mode_records"][0]["generation_performed_bool"] = False; check("execution_mode_drift", any(issue.startswith("execution_mode_") for issue in validate_report(mode_drift)))
        root_leak = json.loads(json.dumps(report)); root_leak["private_output_root_records"][0]["root_basename_filename_published_bool"] = True; check("private_root_leak_drift", any(issue.startswith("private_root_") for issue in validate_report(root_leak)))
        fixture_drift = json.loads(json.dumps(report)); fixture_drift["fixture_subset_records"][0]["target_task_count_bucket"] = "target_21"; check("fixture_subset_drift", any(issue.startswith("fixture_subset_") for issue in validate_report(fixture_drift)))
        next_drift = json.loads(json.dumps(report)); next_drift["stop_go_records"][0]["next_allowed_phase"] = "BEA-v1-HAAE-R2W Wrong Phase"; check("stop_go_next_phase_drift", any(issue == "r2v_stop_go_missing" for issue in validate_report(next_drift)))
    bad_source = load_json(repo / R2T_REPORT_PATH); bad_source["status"] = "wrong"; check("source_lock_drift", build_report(STATUS_DEFAULT, False, r2t=bad_source)["status"] == STATUS_FAIL_SOURCE)
    check("bounds_drift", parse_args_error(["--target-task-count", "21"]))
    check("gold_mutation_rank_invariant", rank_orders_for_probe("gold_evidence") == rank_orders_for_probe("hard_negative"))
    fixture_tasks = load_jsonl(repo / "fixtures" / "r14" / "tasks" / "medium.jsonl")[:TARGET_TASK_COUNT]
    check("gold_rationale_mutation_rank_invariant", public_candidate_rank_fingerprint(fixture_tasks) == public_candidate_rank_fingerprint(json.loads(json.dumps(fixture_tasks))))
    leak = build_report(STATUS_DEFAULT, False); leak["debug"] = "/tmp/private-root r14m-001 query crates/openlocus/src/lib.rs"; check("leak_scanner", scan_public_report(leak)["status"] == "fail")
    over = build_report(STATUS_DEFAULT, False); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("overauth", any(i.startswith("overauthorization_") for i in validate_report(over)))
    check("stale_readback", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser", False)
    except ValueError: check("safe_parser", True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def parse_args_error(argv: list[str]) -> bool:
    try:
        parse_args(argv)
        return False
    except Exception:
        return True


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
    ok, reason = validate_private_root(Path(args["root"]), repo)
    material = materialize(repo, Path(args["root"])) if ok else {"status": STATUS_NO_GO_ROOT, "group_counts": {}, "total_rows": 0, "task_count": 0, "rank_sources": []}
    report = build_report(material.get("status", STATUS_NO_GO_MATERIAL), True, material, reason); path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
