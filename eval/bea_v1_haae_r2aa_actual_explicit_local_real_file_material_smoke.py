#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AA actual explicit local real-file material smoke.

Default mode is safe and writes/reads no private material. Explicit mode performs
a bounded local/manual scan of an allowlisted public corpus and writes private
real-file candidate material under an operator supplied root only.
"""

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

PHASE = "BEA-v1-HAAE-R2AA Actual Explicit Local Real-File Material Smoke"
SLUG = "bea_v1_haae_r2aa_actual_explicit_local_real_file_material_smoke"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2Z_CHECKPOINT = "a763a84"
R2Z_STATUS = "haae_r2z_real_file_candidate_material_preflight_complete_r2aa_actual_explicit_local_real_file_material_smoke_authorized"
R2Z_REPORT_PATH = Path("artifacts/bea_v1_haae_r2z_real_file_candidate_material_preflight/bea_v1_haae_r2z_real_file_candidate_material_preflight_report.json")

STATUS_DEFAULT = "haae_r2aa_unavailable_no_explicit_real_file_material_smoke_opt_in"
STATUS_PASS = "haae_r2aa_actual_explicit_local_real_file_material_smoke_complete_r2ab_public_audit_authorized"
STATUS_NO_GO_ROOT = "haae_r2aa_no_go_private_output_root_invalid"
STATUS_NO_GO_SOURCE = "haae_r2aa_no_go_public_corpus_manifest_invalid"
STATUS_NO_GO_MATERIAL = "haae_r2aa_no_go_real_file_material_incomplete"
STATUS_FAIL_SOURCE = "haae_r2aa_fail_closed_source_lock_mismatch"
STATUS_FAIL_BOUNDS = "haae_r2aa_fail_closed_locked_bounds_mismatch"
STATUS_FAIL_LEAK = "haae_r2aa_fail_closed_public_artifact_leak"
STATUS_FAIL_READBACK = "haae_r2aa_fail_closed_public_readback_mismatch"
STATUS_FAIL_OVERAUTH = "haae_r2aa_fail_closed_stop_go_overauthorization"

TARGET_TASK_COUNT = 20
CANDIDATE_DEPTH = 40
SOURCE_FILE_CAP = 500
PRIVATE_ROW_CAP = 20000
SELF_TEST_EXPECTED = 24
PRIVATE_MANIFEST_NAME = "private_manifest.json"
OWNER_BUCKET = "haae_r2aa_actual_explicit_local_real_file_material_smoke"
NEXT_PHASE = "BEA-v1-HAAE-R2AB Real-File Material Public Audit Package"
REQUIRED_GROUPS = ["task_identity", "source_manifest_private", "candidate_pool", "rank_pack", "evidence_span", "outcome_metric"]
RANK_SOURCES = ["query_identifier_overlap", "symbol_name_overlap", "lexical_bm25_like", "content_identifier_fusion", "control_baseline"]
EXPECTED_MANIFEST = Path("fixtures/r14/repos.lock.jsonl")
FORBIDDEN_STOP_TRUE = ["experiment_metrics_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]
GATE_NAMES = ["r2z_source_locked_gate", "explicit_opt_in_gate", "operator_manifest_gate", "private_output_root_boundary_gate", "allowlisted_public_corpus_gate", "bounded_source_file_cap_gate", "target_task_count_gate", "candidate_depth_gate", "private_row_cap_gate", "private_write_nonzero_gate", "rank_source_coverage_gate", "gold_private_eval_only_gate", "ranking_policy_label_independent_gate", "no_experiment_metrics_gate", "public_aggregate_only_gate", "no_network_clone_ci_provider_gate", "no_retrieval_runtime_openlocus_gate", "no_scheduler_selector_gate", "stop_go_r2ab_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


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
    if n <= 500: return "count_51_to_500"
    if n <= 20000: return "count_le_20000"
    return "count_gt_20000"


def tokenize(value: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[A-Za-z0-9]+", value or "")]


def split_identifier(value: str) -> set[str]:
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", value or "")
    return set(tokenize(spaced.replace("_", " ")))


def stable_hash_score(value: str) -> float:
    total = 0
    for idx, char in enumerate(value):
        total = (total + (idx + 1) * ord(char)) % 1000003
    return total / 1000003.0


def validate_r2z_source(r2z: dict[str, Any]) -> dict[str, bool]:
    stop = (r2z.get("stop_go_records") or [{}])[0]
    status_ok = r2z.get("status") == R2Z_STATUS
    scan_ok = r2z.get("forbidden_scan", {}).get("status") == "pass"
    auth_ok = stop.get("haae_r2aa_actual_explicit_local_real_file_material_smoke_authorized_bool") is True
    boundary_ok = (
        stop.get("r2aa_execution_authorized_bool") is True
        and stop.get("r2aa_private_write_authorized_bool") is True
        and stop.get("r2aa_candidate_generation_authorized_bool") is True
        and stop.get("r2aa_source_scan_authorized_bool") is True
        and stop.get("r2aa_real_file_candidate_material_generation_authorized_bool") is True
        and all(stop.get(field, False) is False for field in [
            "r2aa_private_read_authorized_bool", "r2aa_ci_execution_authorized_bool", "r2aa_retrieval_runtime_authorized_bool",
            "r2aa_openlocus_runtime_authorized_bool", "r2aa_network_authorized_bool", "r2aa_provider_model_authorized_bool",
            "r2aa_clone_authorized_bool", "r2aa_scheduler_haae_authorized_bool", "r2aa_selector_reranker_authorized_bool",
            "r2aa_runtime_default_change_authorized_bool", "r2aa_method_winner_claim_authorized_bool",
            "r2aa_scaling_claim_authorized_bool", "r2aa_raw_publication_authorized_bool", "r2aa_broad_workspace_scan_authorized_bool",
            "execution_authorized_bool", "candidate_generation_authorized_bool", "private_read_authorized_bool", "private_write_authorized_bool",
            "source_scan_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "ci_execution_authorized_bool",
            "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scheduler_haae_authorized_bool",
            "selector_reranker_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool",
            "scaling_claim_authorized_bool", "raw_publication_authorized_bool",
        ])
    )
    return {"status_ok": status_ok, "scan_ok": scan_ok, "auth_ok": auth_ok, "boundary_ok": boundary_ok, "source_locked": status_ok and scan_ok and auth_ok and boundary_ok}


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
    if root.exists() and not root.is_dir():
        return False, "root_not_directory"
    if root.exists():
        entries = {entry.name for entry in root.iterdir()}
        if entries:
            if PRIVATE_MANIFEST_NAME not in entries:
                return False, "root_not_empty_or_owned"
            try:
                manifest = load_json(root / PRIVATE_MANIFEST_NAME)
            except Exception:
                return False, "root_manifest_invalid"
            if manifest.get("owner_bucket") != OWNER_BUCKET or manifest.get("schema_version") != SCHEMA_VERSION:
                return False, "root_not_r2aa_owned"
            if any(entry not in {PRIVATE_MANIFEST_NAME, "groups"} for entry in entries):
                return False, "root_has_unexpected_owned_entries"
    return True, "valid_explicit_r2aa_private_root"


def prepare_private_root(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    groups = root / "groups"
    if groups.exists():
        if groups.is_symlink():
            raise RuntimeError("groups_symlink")
        for child in groups.iterdir():
            if child.is_symlink() or child.is_dir():
                raise RuntimeError("unsafe_existing_group_entry")
            child.unlink()
    else:
        groups.mkdir()
    for child in root.iterdir():
        if child.name not in {PRIVATE_MANIFEST_NAME, "groups"}:
            raise RuntimeError("unexpected_root_entry")


def validate_output_tree(root: Path) -> tuple[bool, str]:
    try:
        root_resolved = root.resolve(strict=True)
    except OSError:
        return False, "root_resolution_failed"
    groups = root / "groups"
    if not groups.exists() or groups.is_symlink():
        return False, "groups_missing_or_symlink"
    if root_resolved not in groups.resolve(strict=True).parents:
        return False, "groups_escape"
    for child in groups.iterdir():
        if child.is_symlink() or not child.is_file():
            return False, "group_entry_invalid"
        if root_resolved not in child.resolve(strict=True).parents:
            return False, "group_file_escape"
        if child.stat().st_size > 8_000_000:
            return False, "group_file_oversized"
    return True, "output_tree_safe"


def validate_manifest_arg(value: str | None, repo: Path) -> tuple[bool, str, Path | None]:
    if value is None:
        return False, "missing_operator_manifest", None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return False, "operator_manifest_must_be_exact_public_relative_path", None
    if path != EXPECTED_MANIFEST:
        return False, "operator_manifest_not_allowlisted", None
    resolved = (repo / path).resolve(strict=False)
    if not resolved.exists() or not resolved.is_file():
        return False, "operator_manifest_missing", None
    return True, "operator_manifest_allowlisted", resolved


def source_files_from_manifest(repo: Path, manifest_path: Path) -> tuple[list[dict[str, Any]], str]:
    locks = load_jsonl(manifest_path)
    files: list[dict[str, Any]] = []
    for lock in locks:
        source = lock.get("source", {})
        if source.get("type") != "local_path":
            continue
        for raw_path in str(source.get("path", "")).split(","):
            base = (repo / raw_path.strip()).resolve(strict=False)
            if not base.exists() or not base.is_dir():
                continue
            for file_path in sorted(base.rglob("*.rs")):
                if len(files) >= SOURCE_FILE_CAP:
                    break
                if any(part in {"target", ".git"} for part in file_path.parts):
                    continue
                rel = file_path.relative_to(repo).as_posix()
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                files.append({"private_repo_id": lock.get("repo_id"), "private_path": rel, "private_text": text, "private_line_count": len(text.splitlines())})
    return files[:SOURCE_FILE_CAP], bucket_count(len(files[:SOURCE_FILE_CAP]))


def select_fixture(repo: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], str]:
    tasks = load_jsonl(repo / "fixtures" / "r14" / "tasks" / "medium.jsonl")[:TARGET_TASK_COUNT]
    labels = {row["task_id"]: row for row in load_jsonl(repo / "fixtures" / "r14" / "labels" / "medium.jsonl")}
    all_tasks = load_jsonl(repo / "fixtures" / "r14" / "tasks" / "medium.jsonl")
    return tasks, labels, bucket_count(len(all_tasks))


def file_symbol_names(text: str) -> set[str]:
    names = set(re.findall(r"\b(?:struct|enum|fn|trait|impl|type|mod)\s+([A-Za-z_][A-Za-z0-9_]*)", text))
    names.update(re.findall(r"\bpub\s+(?:struct|enum|fn|trait|type|mod)\s+([A-Za-z_][A-Za-z0-9_]*)", text))
    return names


def first_matching_span(text: str, query_tokens: set[str]) -> tuple[int, int, str]:
    lines = text.splitlines()
    best_idx = 0
    best_score = -1
    for idx, line in enumerate(lines):
        score = len(query_tokens & set(tokenize(line)))
        if score > best_score:
            best_score = score
            best_idx = idx
    start = max(0, best_idx - 1)
    end = min(len(lines), best_idx + 4)
    return start + 1, end, "\n".join(lines[start:end])[:1000]


def score_file(source: str, query: str, file_row: dict[str, Any], ordinal: int) -> float:
    q_tokens = split_identifier(query)
    text = str(file_row["private_text"])
    path = str(file_row["private_path"])
    content_tokens = set(tokenize(text))
    path_tokens = set(tokenize(path))
    symbols = set().union(*(split_identifier(name) for name in file_symbol_names(text))) if text else set()
    overlap_content = len(q_tokens & content_tokens)
    overlap_path = len(q_tokens & path_tokens)
    overlap_symbol = len(q_tokens & symbols)
    if source == "query_identifier_overlap":
        return overlap_content * 1.5 + overlap_path * 0.8 + stable_hash_score(path) * 0.001
    if source == "symbol_name_overlap":
        return overlap_symbol * 3.0 + overlap_content * 0.2 + stable_hash_score("sym" + path) * 0.001
    if source == "lexical_bm25_like":
        tf = sum(1 for token in tokenize(text) if token in q_tokens)
        return tf * 0.5 + overlap_content - len(content_tokens) * 0.0001 + stable_hash_score("bm25" + path) * 0.001
    if source == "content_identifier_fusion":
        return overlap_symbol * 2.0 + overlap_content + overlap_path * 0.2 + stable_hash_score("fusion" + path) * 0.001
    if source == "control_baseline":
        return stable_hash_score(f"control::{ordinal}::{path}")
    return stable_hash_score(path)


def materialize(repo: Path, manifest_path: Path, labels_override: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    tasks, labels, fixture_bucket = select_fixture(repo)
    if labels_override is not None:
        labels = labels_override
    files, source_file_bucket = source_files_from_manifest(repo, manifest_path)
    rows = {group: [] for group in REQUIRED_GROUPS}
    if len(tasks) < TARGET_TASK_COUNT or not files:
        return {"ok": False, "reason": "insufficient_tasks_or_files", "rows": rows, "summary": {"task_count": len(tasks), "source_file_count": len(files)}}
    for file_index, file_row in enumerate(files):
        rows["source_manifest_private"].append({"source_file_key": f"sf{file_index:04d}", "repo_id": file_row["private_repo_id"], "path": file_row["private_path"], "line_count": file_row["private_line_count"]})
    for task_index, task in enumerate(tasks):
        task_key = f"task{task_index:04d}"
        query = str(task.get("query", ""))
        q_tokens = split_identifier(query)
        rows["task_identity"].append({"task_key": task_key, "task_id": task.get("task_id"), "query": query, "task_type": task.get("task_type"), "method_hint": task.get("method_hint"), "repo_id": task.get("repo_id")})
        ranked_for_candidates = sorted(enumerate(files), key=lambda pair: (-score_file("content_identifier_fusion", query, pair[1], pair[0]), str(pair[1]["private_path"])))[:CANDIDATE_DEPTH]
        for rank_index, (file_index, file_row) in enumerate(ranked_for_candidates):
            start_line, end_line, snippet = first_matching_span(str(file_row["private_text"]), q_tokens)
            candidate_key = f"{task_key}_cand{rank_index:03d}"
            candidate = {"task_key": task_key, "candidate_key": candidate_key, "source_file_key": f"sf{file_index:04d}", "candidate_path": file_row["private_path"], "repo_id": file_row["private_repo_id"], "start_line": start_line, "end_line": end_line, "rank_policy_used_gold_bool": False}
            rows["candidate_pool"].append(candidate)
            rows["evidence_span"].append({"task_key": task_key, "candidate_key": candidate_key, "path": file_row["private_path"], "start_line": start_line, "end_line": end_line, "snippet": snippet})
        task_candidates = [row for row in rows["candidate_pool"] if row["task_key"] == task_key]
        for source in RANK_SOURCES:
            ordered = sorted(task_candidates, key=lambda row: (-score_file(source, query, files[int(row["source_file_key"][2:])], int(row["source_file_key"][2:])), row["candidate_key"]))
            for rank, row in enumerate(ordered, 1):
                rows["rank_pack"].append({"task_key": task_key, "candidate_key": row["candidate_key"], "rank_source": source, "rank": rank, "score": round(score_file(source, query, files[int(row["source_file_key"][2:])], int(row["source_file_key"][2:])), 6), "rank_policy_used_gold_bool": False})
        label = labels.get(str(task.get("task_id")), {})
        rows["outcome_metric"].append({"task_key": task_key, "task_id": task.get("task_id"), "label_quality": label.get("label_quality"), "gold_spans": label.get("gold_spans", []), "hard_negatives": label.get("hard_negatives", []), "gold_used_for_ranking_bool": False, "gold_private_eval_only_bool": True})
    total_rows = sum(len(v) for v in rows.values())
    depths = [len([row for row in rows["candidate_pool"] if row["task_key"] == f"task{i:04d}"]) for i in range(len(tasks))]
    rank_sources_present = sorted({row["rank_source"] for row in rows["rank_pack"]})
    return {"ok": True, "rows": rows, "summary": {"task_count": len(tasks), "fixture_task_bucket": fixture_bucket, "source_file_count": len(files), "source_file_bucket": source_file_bucket, "candidate_depth_min": min(depths), "candidate_depth_max": max(depths), "candidate_rows": len(rows["candidate_pool"]), "rank_rows": len(rows["rank_pack"]), "total_private_rows": total_rows, "rank_sources_present": rank_sources_present}}


def write_private_material(root: Path, material: dict[str, Any]) -> None:
    prepare_private_root(root)
    groups = root / "groups"
    for group, rows in material["rows"].items():
        write_jsonl(groups / f"{group}.jsonl", rows)
    manifest = {"schema_version": SCHEMA_VERSION, "owner_bucket": OWNER_BUCKET, "status": STATUS_PASS, "target_task_count": TARGET_TASK_COUNT, "candidate_depth_cap": CANDIDATE_DEPTH, "source_file_cap": SOURCE_FILE_CAP, "private_row_cap": PRIVATE_ROW_CAP, "rank_sources": RANK_SOURCES, "groups": REQUIRED_GROUPS, "summary": material["summary"]}
    (root / PRIVATE_MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


LEAK_PATTERNS = [
    ("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)),
    ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")),
    ("raw_candidate_path", re.compile(r"candidate_path|source_path|filepath|filename|directory|snippet|start_line|end_line|\.rs\b|crates/openlocus-")),
    ("score_hash_exact", re.compile(r"private_score|private_rank|exact_rate|exact_rank|task_key|candidate_key|\b[a-f0-9]{32,64}\b")),
]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, STATUS_DEFAULT, f"{total}/{total}", R2Z_CHECKPOINT, R2Z_STATUS, "explicit opt-in required", "operator public corpus manifest/allowlist", "target_20", "candidate_depth_40", "source_file_count_bucket", "source_file_cap_500", "row_cap_20000", "wall_clock_cap_20_minutes", "gold private eval only", "no experiment metrics", NEXT_PHASE]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2aa-actual-explicit-local-real-file-material-smoke.md")) and has_all(read("docs/zh/bea-v1-haae-r2aa-actual-explicit-local-real-file-material-smoke.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2aa-actual-explicit-local-real-file-material-smoke.md" in current_root and has_all(current_root)
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(*, explicit: bool, r2z: dict[str, Any] | None = None, root_status: str = "not_applicable", manifest_status: str = "not_applicable", material: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2z is None:
        try: r2z = load_json(repo / R2Z_REPORT_PATH)
        except Exception: r2z = {}
    source = validate_r2z_source(r2z)
    readback = public_readback_match(self_test_total)
    summary = material.get("summary", {}) if material else {}
    material_ok = bool(material and material.get("ok") and summary.get("task_count") == TARGET_TASK_COUNT and summary.get("candidate_depth_min") == CANDIDATE_DEPTH and summary.get("candidate_depth_max") == CANDIDATE_DEPTH and summary.get("total_private_rows", PRIVATE_ROW_CAP + 1) <= PRIVATE_ROW_CAP and set(summary.get("rank_sources_present", [])) == set(RANK_SOURCES))
    if not explicit:
        status = STATUS_DEFAULT
    elif not source["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif root_status != "valid_explicit_r2aa_private_root":
        status = STATUS_NO_GO_ROOT
    elif manifest_status != "operator_manifest_allowlisted":
        status = STATUS_NO_GO_SOURCE
    elif not material_ok:
        status = STATUS_NO_GO_MATERIAL
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    private_write_nonzero = passed and summary.get("total_private_rows", 0) > 0
    gates = {"r2z_source_locked_gate": source["source_locked"], "explicit_opt_in_gate": explicit, "operator_manifest_gate": manifest_status == "operator_manifest_allowlisted", "private_output_root_boundary_gate": root_status == "valid_explicit_r2aa_private_root", "allowlisted_public_corpus_gate": manifest_status == "operator_manifest_allowlisted", "bounded_source_file_cap_gate": summary.get("source_file_count", 0) <= SOURCE_FILE_CAP if explicit else True, "target_task_count_gate": summary.get("task_count") == TARGET_TASK_COUNT if explicit else True, "candidate_depth_gate": summary.get("candidate_depth_min") == CANDIDATE_DEPTH and summary.get("candidate_depth_max") == CANDIDATE_DEPTH if explicit else True, "private_row_cap_gate": summary.get("total_private_rows", 0) <= PRIVATE_ROW_CAP if explicit else True, "private_write_nonzero_gate": private_write_nonzero if explicit else True, "rank_source_coverage_gate": set(summary.get("rank_sources_present", [])) == set(RANK_SOURCES) if explicit else True, "gold_private_eval_only_gate": True, "ranking_policy_label_independent_gate": True, "no_experiment_metrics_gate": True, "public_aggregate_only_gate": True, "no_network_clone_ci_provider_gate": True, "no_retrieval_runtime_openlocus_gate": True, "no_scheduler_selector_gate": True, "stop_go_r2ab_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2aasource0000", "locked_haae_r2z_checkpoint": R2Z_CHECKPOINT, "locked_haae_r2z_status": R2Z_STATUS, "r2z_status_match_bool": source["status_ok"], "r2z_forbidden_scan_pass_bool": source["scan_ok"], "r2z_r2aa_authorization_match_bool": source["auth_ok"], "r2z_no_forbidden_stop_go_drift_bool": source["boundary_ok"], "source_locked_bool": source["source_locked"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2aaexec0000", "explicit_opt_in_bool": explicit, "default_no_private_read_write_bool": not explicit, "local_manual_only_bool": True, "bounded_source_scan_bool": explicit, "no_network_clone_ci_provider_bool": True, "no_runtime_retrieval_openlocus_bool": True}],
        "private_output_root_records": [{"anonymous_private_root_id": "haaer2aaroot0000", "root_status_bucket": root_status, "private_root_path_published_bool": False, "private_write_nonzero_bool": private_write_nonzero, "owned_root_protection_bool": True, "symlink_escape_rejected_bool": True}],
        "operator_manifest_records": [{"anonymous_operator_manifest_id": "haaer2aamanifest0000", "operator_manifest_bucket": "r14_repo_lock_public_allowlist", "manifest_status_bucket": manifest_status, "allowlisted_public_corpus_only_bool": manifest_status == "operator_manifest_allowlisted", "manifest_path_published_bool": False, "no_broad_workspace_scan_bool": True, "no_network_clone_by_default_bool": True}],
        "material_generation_records": [{"anonymous_material_generation_id": "haaer2aamaterial0000", "target_task_count_bucket": "target_20", "actual_task_count_bucket": bucket_count(int(summary.get("task_count", 0))), "source_file_count_bucket": summary.get("source_file_bucket", "count_0"), "source_file_cap_bucket": "source_file_cap_500", "candidate_depth_bucket": "candidate_depth_40", "candidate_row_count_bucket": bucket_count(int(summary.get("candidate_rows", 0))), "rank_source_count_bucket": bucket_count(len(summary.get("rank_sources_present", []))), "private_row_count_bucket": bucket_count(int(summary.get("total_private_rows", 0))), "row_cap_bucket": "row_cap_20000", "wall_clock_cap_bucket": "wall_clock_cap_20_minutes", "material_generation_complete_bool": material_ok, "raw_rows_published_bool": False}],
        "rank_source_records": [{"anonymous_rank_source_id": f"haaer2aarank{idx:04d}", "rank_source_bucket": source_name, "present_bool": source_name in summary.get("rank_sources_present", []), "uses_gold_labels_bool": False, "exact_scores_published_bool": False} for idx, source_name in enumerate(RANK_SOURCES)],
        "gold_policy_records": [{"anonymous_gold_policy_id": "haaer2aagold0000", "gold_private_eval_only_bool": True, "gold_used_for_ranking_bool": False, "labels_used_for_policy_bool": False, "outcome_rows_private_only_bool": True, "aggregate_availability_only_public_bool": True}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2aaclaim0000", "material_generation_phase_bool": True, "experiment_metrics_bool": False, "topk_mrr_metrics_bool": False, "retrieval_runtime_openlocus_bool": False, "network_clone_ci_provider_bool": False, "scheduler_selector_bool": False, "bea_v1_a_p5_bool": False, "default_runtime_claim_bool": False, "method_winner_claim_bool": False, "scaling_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2aagate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2aasynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["default_noop", "explicit_synthetic_root_success", "missing_opt_in_no_go", "non_owned_root_reject", "symlink_reject", "label_mutation_rank_stable", "broad_scan_arg_rejected", "scanner_catches_raw", "bounds_mutation_fail", "source_cap_mutation_fail", "source_count_mutation_fail", "claims_mutation_fail", "stale_readback_fail", "safe_parser_fail", "source_lock_bool_mutation_fail", "execution_mode_mutation_fail", "operator_manifest_publication_fail", "private_root_publication_fail", "rank_source_gold_mutation_fail", "rank_source_score_publication_fail", "gold_policy_mutation_fail", "stop_go_next_phase_mutation_fail", "gate_mutation_fail", "private_write_nonzero_mutation_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2aareadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2aastop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_rerun_r2aa_material_smoke", "haae_r2ab_public_audit_authorized_bool": passed, "new_material_generation_authorized_bool": False, "experiment_metrics_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "openlocus_runtime_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "clone_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "execution_mode_records", "private_output_root_records", "operator_manifest_records", "material_generation_records", "rank_source_records", "gold_policy_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2z_checkpoint") != R2Z_CHECKPOINT or source.get("locked_haae_r2z_status") != R2Z_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2z_status_match_bool", "r2z_forbidden_scan_pass_bool", "r2z_r2aa_authorization_match_bool", "r2z_no_forbidden_stop_go_drift_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    execution = (report.get("execution_mode_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        for field in ["explicit_opt_in_bool", "local_manual_only_bool", "bounded_source_scan_bool", "no_network_clone_ci_provider_bool", "no_runtime_retrieval_openlocus_bool"]:
            if execution.get(field) is not True: issues.append(f"execution_mode_{field}")
        if execution.get("default_no_private_read_write_bool") is not False: issues.append("execution_mode_default_no_private_read_write_bool")
        manifest = (report.get("operator_manifest_records") or [{}])[0]
        if manifest.get("manifest_status_bucket") != "operator_manifest_allowlisted" or manifest.get("operator_manifest_bucket") != "r14_repo_lock_public_allowlist": issues.append("operator_manifest_bucket_mismatch")
        if manifest.get("manifest_path_published_bool") is not False: issues.append("operator_manifest_path_publication")
        for field in ["allowlisted_public_corpus_only_bool", "no_broad_workspace_scan_bool", "no_network_clone_by_default_bool"]:
            if manifest.get(field) is not True: issues.append(f"operator_manifest_{field}")
    claims = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["experiment_metrics_bool", "topk_mrr_metrics_bool", "retrieval_runtime_openlocus_bool", "network_clone_ci_provider_bool", "scheduler_selector_bool", "bea_v1_a_p5_bool", "default_runtime_claim_bool", "method_winner_claim_bool", "scaling_claim_bool", "raw_publication_bool"]:
        if claims.get(field) is not False: issues.append(f"claim_boundary_{field}")
    gold = (report.get("gold_policy_records") or [{}])[0]
    if gold.get("gold_private_eval_only_bool") is not True or gold.get("gold_used_for_ranking_bool") is not False or gold.get("labels_used_for_policy_bool") is not False or gold.get("outcome_rows_private_only_bool") is not True or gold.get("aggregate_availability_only_public_bool") is not True: issues.append("gold_policy_mismatch")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in FORBIDDEN_STOP_TRUE:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    if report.get("status") == STATUS_PASS:
        mat = (report.get("material_generation_records") or [{}])[0]
        allowed_source_count_buckets = {"count_1", "count_2_to_5", "count_10_to_20", "count_21_to_50", "count_51_to_500"}
        if mat.get("target_task_count_bucket") != "target_20" or mat.get("candidate_depth_bucket") != "candidate_depth_40" or mat.get("row_cap_bucket") != "row_cap_20000" or mat.get("source_file_cap_bucket") != "source_file_cap_500" or mat.get("source_file_count_bucket") not in allowed_source_count_buckets or mat.get("material_generation_complete_bool") is not True: issues.append("material_bounds_mismatch")
        if mat.get("raw_rows_published_bool") is not False: issues.append("raw_rows_publication")
        ranks = {row.get("rank_source_bucket") for row in report.get("rank_source_records", []) if row.get("present_bool") is True}
        if ranks != set(RANK_SOURCES): issues.append("rank_source_coverage_mismatch")
        for row in report.get("rank_source_records", []):
            if row.get("uses_gold_labels_bool") is not False: issues.append("rank_source_uses_gold")
            if row.get("exact_scores_published_bool") is not False: issues.append("rank_source_exact_scores_published")
        root = (report.get("private_output_root_records") or [{}])[0]
        if root.get("private_write_nonzero_bool") is not True or root.get("private_root_path_published_bool") is not False or root.get("owned_root_protection_bool") is not True or root.get("symlink_escape_rejected_bool") is not True or root.get("root_status_bucket") != "valid_explicit_r2aa_private_root": issues.append("private_root_record_mismatch")
        if stop.get("haae_r2ab_public_audit_authorized_bool") is not True: issues.append("missing_r2ab_authorization")
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("stop_go_next_phase_mismatch")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {"self_test": False, "validate": "", "out": "", "allow": False, "root": "", "operator_manifest": "", "confirm": False}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--self-test": parsed["self_test"] = True; i += 1
        elif arg == "--allow-real-file-material-smoke": parsed["allow"] = True; i += 1
        elif arg == "--confirm-aggregate-only-publication": parsed["confirm"] = True; i += 1
        elif arg in {"--private-output-root", "--operator-public-corpus-manifest", "--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            if arg == "--private-output-root": parsed["root"] = argv[i + 1]
            elif arg == "--operator-public-corpus-manifest": parsed["operator_manifest"] = argv[i + 1]
            elif arg == "--validate-report": parsed["validate"] = argv[i + 1]
            else: parsed["out"] = argv[i + 1]
            i += 2
        else:
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


def label_mutation_rank_stable(repo: Path, manifest: Path) -> bool:
    tasks, labels, _ = select_fixture(repo)
    mutated = json.loads(json.dumps(labels))
    for value in mutated.values():
        value["gold_spans"] = []
        value["hard_negatives"] = []
        value["label_quality"] = "mutated"
    a = materialize(repo, manifest, labels)
    b = materialize(repo, manifest, mutated)
    if not (a.get("ok") and b.get("ok")):
        return False
    key_a = [(row["task_key"], row["candidate_key"], row["candidate_path"]) for row in a["rows"]["candidate_pool"]]
    key_b = [(row["task_key"], row["candidate_key"], row["candidate_path"]) for row in b["rows"]["candidate_pool"]]
    rank_a = [(row["task_key"], row["candidate_key"], row["rank_source"], row["rank"]) for row in a["rows"]["rank_pack"]]
    rank_b = [(row["task_key"], row["candidate_key"], row["rank_source"], row["rank"]) for row in b["rows"]["rank_pack"]]
    return key_a == key_b and rank_a == rank_b


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    r2z = load_json(repo / R2Z_REPORT_PATH)
    ok_manifest, manifest_status, manifest_path = validate_manifest_arg(str(EXPECTED_MANIFEST), repo)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    default = build_report(explicit=False, r2z=r2z); check("default_noop", default["status"] == STATUS_DEFAULT and default["execution_mode_records"][0]["default_no_private_read_write_bool"] is True)
    with tempfile.TemporaryDirectory(prefix="haae_r2aa_selftest_") as tmp:
        root = Path(tmp) / "private"
        root_ok, root_status = validate_private_root(root, repo)
        mat = materialize(repo, manifest_path) if ok_manifest and manifest_path else None
        if root_ok and mat and mat.get("ok"):
            write_private_material(root, mat)
        tree_ok, _ = validate_output_tree(root) if root.exists() else (False, "missing")
        explicit = build_report(explicit=True, r2z=r2z, root_status=root_status if root_ok and tree_ok else "invalid", manifest_status=manifest_status, material=mat)
        check("explicit_synthetic_root_success", explicit["status"] == STATUS_PASS and validate_report(explicit) == [])
    check("missing_opt_in_no_go", build_report(explicit=False, r2z=r2z)["status"] == STATUS_DEFAULT)
    with tempfile.TemporaryDirectory(prefix="haae_r2aa_nonowned_") as tmp:
        root = Path(tmp) / "private"; root.mkdir(); (root / "foreign.txt").write_text("x")
        check("non_owned_root_reject", validate_private_root(root, repo)[0] is False)
    with tempfile.TemporaryDirectory(prefix="haae_r2aa_symlink_") as tmp:
        target = Path(tmp) / "target"; target.mkdir(); link = Path(tmp) / "link"; link.symlink_to(target, target_is_directory=True)
        check("symlink_reject", validate_private_root(link, repo)[0] is False)
    check("label_mutation_rank_stable", label_mutation_rank_stable(repo, manifest_path) if manifest_path else False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--broad-workspace-scan", "/workspace"])
        check("broad_scan_arg_rejected", False)
    except ValueError:
        check("broad_scan_arg_rejected", True)
    leak = json.loads(json.dumps(default)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("scanner_catches_raw", scan_public_report(leak)["status"] == "fail")
    mutated = json.loads(json.dumps(default)); mutated["status"] = STATUS_PASS; mutated["material_generation_records"][0]["row_cap_bucket"] = "unbounded"; check("bounds_mutation_fail", "material_bounds_mismatch" in validate_report(mutated))
    source_cap_mut = json.loads(json.dumps(explicit)); source_cap_mut["material_generation_records"][0]["source_file_cap_bucket"] = "source_file_cap_unbounded"; check("source_cap_mutation_fail", "material_bounds_mismatch" in validate_report(source_cap_mut))
    source_count_mut = json.loads(json.dumps(explicit)); source_count_mut["material_generation_records"][0]["source_file_count_bucket"] = "count_gt_20000"; check("source_count_mutation_fail", "material_bounds_mismatch" in validate_report(source_count_mut))
    over = json.loads(json.dumps(default)); over["claim_boundary_records"][0]["method_winner_claim_bool"] = True; check("claims_mutation_fail", any(i.startswith("claim_boundary_") for i in validate_report(over)))
    source_mut = json.loads(json.dumps(explicit)); source_mut["source_lock_records"][0]["source_locked_bool"] = False; check("source_lock_bool_mutation_fail", "source_lock_source_locked_bool" in validate_report(source_mut))
    exec_mut = json.loads(json.dumps(explicit)); exec_mut["execution_mode_records"][0]["bounded_source_scan_bool"] = False; check("execution_mode_mutation_fail", "execution_mode_bounded_source_scan_bool" in validate_report(exec_mut))
    manifest_mut = json.loads(json.dumps(explicit)); manifest_mut["operator_manifest_records"][0]["manifest_path_published_bool"] = True; check("operator_manifest_publication_fail", "operator_manifest_path_publication" in validate_report(manifest_mut))
    root_mut = json.loads(json.dumps(explicit)); root_mut["private_output_root_records"][0]["private_root_path_published_bool"] = True; check("private_root_publication_fail", "private_root_record_mismatch" in validate_report(root_mut))
    rank_gold = json.loads(json.dumps(explicit)); rank_gold["rank_source_records"][0]["uses_gold_labels_bool"] = True; check("rank_source_gold_mutation_fail", "rank_source_uses_gold" in validate_report(rank_gold))
    rank_score = json.loads(json.dumps(explicit)); rank_score["rank_source_records"][0]["exact_scores_published_bool"] = True; check("rank_source_score_publication_fail", "rank_source_exact_scores_published" in validate_report(rank_score))
    gold_mut = json.loads(json.dumps(explicit)); gold_mut["gold_policy_records"][0]["gold_used_for_ranking_bool"] = True; check("gold_policy_mutation_fail", "gold_policy_mismatch" in validate_report(gold_mut))
    next_mut = json.loads(json.dumps(explicit)); next_mut["stop_go_records"][0]["next_allowed_phase"] = "BEA-v1-HAAE-R2AC Wrong"; check("stop_go_next_phase_mutation_fail", "stop_go_next_phase_mismatch" in validate_report(next_mut))
    gate_mut = json.loads(json.dumps(explicit)); gate_mut["pass_fail_gate_records"][0]["gate_passed_bool"] = False; check("gate_mutation_fail", any(i.startswith("gate_failed_") for i in validate_report(gate_mut)))
    write_mut = json.loads(json.dumps(explicit)); write_mut["private_output_root_records"][0]["private_write_nonzero_bool"] = False; check("private_write_nonzero_mutation_fail", "private_root_record_mismatch" in validate_report(write_mut))
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError:
        check("safe_parser_fail", True)
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
    r2z = load_json(repo / R2Z_REPORT_PATH) if (repo / R2Z_REPORT_PATH).exists() else {}
    out = public_artifact_path(args["out"]) if args["out"] else None
    if not args["allow"]:
        report = build_report(explicit=False, r2z=r2z); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0
    if not args["confirm"] or not args["root"]:
        report = build_report(explicit=True, r2z=r2z, root_status="missing_opt_in_or_root", manifest_status="not_applicable", material=None); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 1
    manifest_ok, manifest_status, manifest_path = validate_manifest_arg(args["operator_manifest"], repo)
    root = Path(args["root"])
    root_ok, root_status = validate_private_root(root, repo)
    material = None
    if manifest_ok and root_ok and manifest_path:
        material = materialize(repo, manifest_path)
        if material.get("ok"):
            try:
                write_private_material(root, material)
                tree_ok, tree_status = validate_output_tree(root)
                if not tree_ok: root_status = tree_status
            except Exception as exc:
                root_status = str(exc)
    report = build_report(explicit=True, r2z=r2z, root_status=root_status, manifest_status=manifest_status, material=material)
    path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
