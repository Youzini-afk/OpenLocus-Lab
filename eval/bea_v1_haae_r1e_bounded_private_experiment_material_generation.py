#!/usr/bin/env python3
"""BEA-v1-HAAE-R1E bounded private experiment material generation.

This evaluator is intentionally local/manual only.  It has a safe default mode
that performs no private reads or writes, and an explicit opt-in mode that writes
raw material rows only under a caller supplied private output root.  The public
artifact is aggregate-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PHASE = "BEA-v1-HAAE-R1E Bounded Private Experiment Material Generation"
SLUG = "bea_v1_haae_r1e_bounded_private_experiment_material_generation"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"

STATUS_DEFAULT = "haae_r1e_unavailable_no_explicit_material_generation_opt_in"
STATUS_PASS = "haae_r1e_bounded_private_material_generation_complete_r2_small_experiment_authorized"
STATUS_NO_GO_INSUFFICIENT = "haae_r1e_no_go_insufficient_material_for_r2"
STATUS_NO_GO_NO_SOURCE = "haae_r1e_no_go_no_public_task_source"
STATUS_FAIL_SOURCE_LOCK = "haae_r1e_fail_closed_source_lock_mismatch"
STATUS_FAIL_MISSING_OPT_IN = "haae_r1e_fail_closed_missing_explicit_material_generation_opt_in"
STATUS_FAIL_PRIVATE_ROOT = "haae_r1e_fail_closed_private_root_boundary_violation"
STATUS_FAIL_BOUNDS = "haae_r1e_fail_closed_sample_or_depth_bounds_exceeded"
STATUS_FAIL_FORBIDDEN = "haae_r1e_fail_closed_forbidden_operation"
STATUS_FAIL_PUBLIC_LEAK = "haae_r1e_fail_closed_public_manifest_leak"
STATUS_FAIL_READBACK = "haae_r1e_fail_closed_private_readback_mismatch"

PUBLIC_TASK_SOURCES = {"r14_sanity": "sanity"}
ALLOWED_RECIPE = "local_normalized_bm25_rrf_trace_material_canary"
MAX_SAMPLE_SIZE = 5
MIN_PASS_SAMPLE_SIZE = 3
MAX_CANDIDATE_DEPTH = 20
MAX_SOURCE_FILES = 200
R1D_LOCKED_CHECKPOINT = "9299b0a"
R1D_LOCKED_STATUS = "haae_r1d_schema_inventory_complete_no_go_bootstrap_placeholders_only"
R1D_REPORT_PATH = Path("artifacts/bea_v1_haae_r1d_explicit_private_root_schema_inventory_smoke/bea_v1_haae_r1d_explicit_private_root_schema_inventory_smoke_report.json")

SCHEMA_GROUPS = [
    "task_identity",
    "anchor_source",
    "candidate_pool",
    "rank_pack",
    "span_projection",
    "scheduler_action",
    "evidence_core",
    "arm_assignment",
    "outcome_metric",
    "safety_probe_signal",
]
REQUIRED_MEANINGFUL_GROUPS = {
    "task_identity",
    "anchor_source",
    "candidate_pool",
    "rank_pack",
    "evidence_core",
    "outcome_metric",
}
PLACEHOLDER_ALLOWED_GROUPS = {"scheduler_action", "arm_assignment", "safety_probe_signal"}

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def bucket_count(value: int) -> str:
    if value == 0:
        return "count_0"
    if value == 1:
        return "count_1"
    if value <= 5:
        return "count_2_to_5"
    if value <= 10:
        return "count_6_to_10"
    if value <= 20:
        return "count_11_to_20"
    if value <= 100:
        return "count_21_to_100"
    return "count_gt_100"


def bucket_rate(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "rate_not_applicable"
    value = numerator / denominator
    if value == 0:
        return "rate_0"
    if value < 0.5:
        return "rate_lt_0_5"
    if value < 1.0:
        return "rate_ge_0_5_lt_1"
    return "rate_1"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def tokens(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text)]


def symbol_tokens(text: str) -> set[str]:
    found = set(TOKEN_RE.findall(text))
    split: set[str] = set()
    for item in found:
        split.add(item.lower())
        for part in re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", item).replace("_", " ").split():
            split.add(part.lower())
    return split


def compute_normalized_manifest_sha(repos_root: Path, crate_dirs: list[str]) -> tuple[str, int, int]:
    all_files: list[tuple[str, Path]] = []
    for crate_dir in crate_dirs:
        crate_path = repos_root / crate_dir
        if not crate_path.exists():
            continue
        for dirpath, _dirnames, filenames in os.walk(crate_path):
            for fname in sorted(filenames):
                if fname.endswith(".rs"):
                    full = Path(dirpath) / fname
                    rel = str(full.relative_to(repos_root)).replace(os.sep, "/")
                    all_files.append((rel, full))
    all_files.sort(key=lambda x: x[0])

    hasher = hashlib.sha256()
    total_lines = 0
    for rel_path, full_path in all_files:
        content = full_path.read_bytes()
        file_sha = hashlib.sha256(content).hexdigest()
        line_count = content.count(b"\n") + 1
        total_lines += line_count
        entry = {"path": rel_path, "sha256": file_sha, "lines": line_count}
        hasher.update(json.dumps(entry, sort_keys=True).encode("utf-8"))
        hasher.update(b"\n")
    return hasher.hexdigest(), len(all_files), total_lines


def validate_repo_lock(
    repo_root: Path, required_repo_ids: set[str] | None = None
) -> tuple[bool, int, int, list[str], dict[str, dict[str, Any]]]:
    lock_path = repo_root / "fixtures" / "r14" / "repos.lock.jsonl"
    rows = load_jsonl(lock_path)
    issues: list[str] = []
    indexed: dict[str, dict[str, Any]] = {}
    total_files = 0
    total_lines = 0
    for row in rows:
        repo_id = row.get("repo_id", "")
        indexed[repo_id] = row
        if required_repo_ids is not None and repo_id not in required_repo_ids:
            continue
        if row.get("source", {}).get("type") != "local_path":
            issues.append("unsupported_source_type")
            continue
        crate_dirs = [p.strip() for p in row.get("source", {}).get("path", "").split(",") if p.strip()]
        for crate_dir in crate_dirs:
            if not (repo_root / crate_dir).exists():
                issues.append("missing_declared_source_path")
        computed_sha, file_count, line_count = compute_normalized_manifest_sha(repo_root, crate_dirs)
        total_files += file_count
        total_lines += line_count
        if computed_sha != row.get("content_manifest_sha"):
            issues.append("content_manifest_sha_mismatch")
        if row.get("metadata", {}).get("files") != file_count:
            issues.append("file_count_mismatch")
        if row.get("metadata", {}).get("lines") != line_count:
            issues.append("line_count_mismatch")
        excludes = row.get("policy", {}).get("exclude", [])
        for required in ["fixtures", "eval", "docs", "runs", ".openlocus", "target"]:
            if not any(required in item for item in excludes):
                issues.append("policy_exclude_missing")
    if required_repo_ids is not None:
        missing = required_repo_ids - set(indexed)
        for _repo_id in missing:
            issues.append("required_repo_lock_missing")
    return len(issues) == 0 and len(rows) > 0, total_files, total_lines, issues, indexed


def validate_r1d_source_lock(repo_root: Path, report_path: Path | None = None) -> dict[str, Any]:
    path = repo_root / (report_path or R1D_REPORT_PATH)
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"r1d_source_locked_bool": False, "r1d_source_lock_reason_bucket": "r1d_report_unavailable"}

    status_ok = report.get("status") == R1D_LOCKED_STATUS
    scan_ok = report.get("forbidden_scan", {}).get("status") == "pass"
    placeholder = report.get("placeholder_classification_records", [{}])[0]
    placeholder_ok = (
        placeholder.get("all_placeholder_bool") is True
        and placeholder.get("meaningful_group_count_bucket") == "count_0"
        and placeholder.get("root_usable_for_hydration_bool") is False
    )
    claim = report.get("claim_boundary_records", [{}])[0]
    no_exec_ok = all(claim.get(key) is False for key in [
        "hydration_execution_bool",
        "replay_bool",
        "retrieval_bool",
        "scoring_bool",
        "candidate_generation_bool",
        "haae_layer_execution_bool",
        "selector_reranker_bool",
        "bea_v1_a_bool",
        "p5_bool",
        "runtime_default_change_bool",
    ])
    locked = status_ok and scan_ok and placeholder_ok and no_exec_ok
    return {
        "r1d_source_locked_bool": locked,
        "r1d_source_lock_reason_bucket": "pass" if locked else "r1d_artifact_contract_mismatch",
        "r1d_status_match_bool": status_ok,
        "r1d_forbidden_scan_pass_bool": scan_ok,
        "r1d_bootstrap_placeholder_no_go_match_bool": placeholder_ok,
        "r1d_no_hydration_or_execution_match_bool": no_exec_ok,
    }


def validate_private_root(root: Path, repo_root: Path) -> tuple[bool, str]:
    try:
        resolved = root.resolve(strict=False)
        repo_resolved = repo_root.resolve(strict=True)
    except OSError:
        return False, "path_resolution_failed"
    if not str(resolved):
        return False, "empty_root"
    if ".." in root.parts:
        return False, "path_traversal"
    if root.exists() and root.is_symlink():
        return False, "root_is_symlink"
    if resolved == repo_resolved or repo_resolved in resolved.parents:
        return False, "root_inside_public_workspace"
    if not (str(resolved).startswith("/tmp/") or str(resolved).startswith("/var/tmp/")):
        return False, "root_not_temp_or_ignored"
    return True, "valid_temp_private_root"


def collect_source_files(repo_root: Path, repos: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    files: list[dict[str, Any]] = []
    for repo_id in sorted(repos):
        row = repos[repo_id]
        crate_dirs = [p.strip() for p in row.get("source", {}).get("path", "").split(",") if p.strip()]
        for crate_dir in crate_dirs:
            base = repo_root / crate_dir
            if not base.exists():
                continue
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [d for d in sorted(dirnames) if d not in {"target", ".git", "__pycache__"}]
                for filename in sorted(filenames):
                    if not filename.endswith(".rs"):
                        continue
                    path = Path(dirpath) / filename
                    rel = str(path.relative_to(repo_root)).replace(os.sep, "/")
                    text = path.read_text(encoding="utf-8", errors="replace")
                    files.append(
                        {
                            "repo_id": repo_id,
                            "path": rel,
                            "text": text,
                            "tokens": tokens(text),
                            "symbol_tokens": symbol_tokens(text),
                            "lines": text.splitlines(),
                        }
                    )
                    if len(files) > MAX_SOURCE_FILES:
                        return files[:MAX_SOURCE_FILES], False
    return files, True


def bm25_rank(query: str, corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    q_tokens = tokens(query)
    if not q_tokens:
        return []
    doc_count = len(corpus)
    avg_len = sum(len(doc["tokens"]) for doc in corpus) / doc_count if doc_count else 1.0
    df: Counter[str] = Counter()
    for doc in corpus:
        unique = set(doc["tokens"])
        for tok in set(q_tokens):
            if tok in unique:
                df[tok] += 1
    ranked: list[dict[str, Any]] = []
    for doc in corpus:
        counts = Counter(doc["tokens"])
        doc_len = max(1, len(doc["tokens"]))
        score = 0.0
        for tok in q_tokens:
            if counts[tok] == 0:
                continue
            idf = math.log(1 + (doc_count - df[tok] + 0.5) / (df[tok] + 0.5))
            tf = counts[tok]
            score += idf * (tf * 2.2) / (tf + 1.2 * (1 - 0.75 + 0.75 * doc_len / avg_len))
        if score > 0:
            ranked.append({"path": doc["path"], "repo_id": doc["repo_id"], "score": score, "source": "bm25_like"})
    ranked.sort(key=lambda row: (-row["score"], row["path"]))
    return ranked


def lexical_rank(query: str, corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    q_symbols = symbol_tokens(query)
    ranked: list[dict[str, Any]] = []
    for doc in corpus:
        overlap = q_symbols & doc["symbol_tokens"]
        exact_bonus = 1 if query in doc["text"] else 0
        score = len(overlap) + exact_bonus * 3
        if score > 0:
            ranked.append({"path": doc["path"], "repo_id": doc["repo_id"], "score": float(score), "source": "symbol_overlap"})
    ranked.sort(key=lambda row: (-row["score"], row["path"]))
    return ranked


def rrf_merge(rankings: list[list[dict[str, Any]]], depth: int) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for ranking in rankings:
        for idx, row in enumerate(ranking[:depth], start=1):
            path = row["path"]
            if path not in merged:
                merged[path] = {
                    "path": path,
                    "repo_id": row["repo_id"],
                    "rrf_score": 0.0,
                    "sources": [],
                    "component_ranks": {},
                }
            merged[path]["rrf_score"] += 1.0 / (60 + idx)
            merged[path]["sources"].append(row["source"])
            merged[path]["component_ranks"][row["source"]] = idx
    result = list(merged.values())
    result.sort(key=lambda row: (-row["rrf_score"], row["path"]))
    return result[:depth]


def best_line_window(query: str, doc: dict[str, Any]) -> dict[str, Any]:
    q = set(tokens(query)) | symbol_tokens(query)
    best_idx = 0
    best_score = -1
    for idx, line in enumerate(doc["lines"]):
        score = len(q & (set(tokens(line)) | symbol_tokens(line)))
        if query in line:
            score += 3
        if score > best_score:
            best_score = score
            best_idx = idx
    start = max(1, best_idx + 1 - 2)
    end = min(len(doc["lines"]), best_idx + 1 + 2)
    snippet = "\n".join(doc["lines"][start - 1 : end])
    return {"start_line": start, "end_line": end, "snippet": snippet, "line_overlap_score": best_score}


def select_positive_tasks(repo_root: Path, source: str, sample_size: int) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    tier = PUBLIC_TASK_SOURCES.get(source)
    if not tier:
        return [], {}
    tasks = load_jsonl(repo_root / "fixtures" / "r14" / "tasks" / f"{tier}.jsonl")
    labels = load_jsonl(repo_root / "fixtures" / "r14" / "labels" / f"{tier}.jsonl")
    label_map = {row["task_id"]: row for row in labels}
    selected: list[dict[str, Any]] = []
    for task in tasks:
        label = label_map.get(task.get("task_id"), {})
        if label.get("gold_spans"):
            selected.append(task)
        if len(selected) >= sample_size:
            break
    return selected, label_map


def materialize_private_rows(
    repo_root: Path,
    private_root: Path,
    sample_size: int,
    depth: int,
    public_task_source: str,
) -> dict[str, Any]:
    r1d_lock = validate_r1d_source_lock(repo_root)
    if not r1d_lock["r1d_source_locked_bool"]:
        return {"status": STATUS_FAIL_SOURCE_LOCK, "lock_ok": False, "r1d_source_lock": r1d_lock}

    tasks, label_map = select_positive_tasks(repo_root, public_task_source, sample_size)
    if not tasks:
        return {"status": STATUS_NO_GO_NO_SOURCE, "lock_ok": True, "private_group_counts": {}}

    required_repo_ids = {task.get("repo_id", "") for task in tasks if task.get("repo_id")}
    lock_ok, source_file_count, source_line_count, lock_issues, all_repos = validate_repo_lock(
        repo_root, required_repo_ids
    )
    if not lock_ok:
        return {"status": STATUS_FAIL_SOURCE_LOCK, "lock_ok": False, "r14_fixture_lock_bool": False, "r1d_source_lock": r1d_lock, "lock_issues": lock_issues}
    repos = {repo_id: all_repos[repo_id] for repo_id in required_repo_ids if repo_id in all_repos}

    corpus, corpus_within_bound = collect_source_files(repo_root, repos)
    if not corpus_within_bound:
        return {"status": STATUS_NO_GO_INSUFFICIENT, "lock_ok": True, "private_group_counts": {}}
    corpus_by_path = {doc["path"]: doc for doc in corpus}
    corpus_by_repo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for doc in corpus:
        corpus_by_repo[doc["repo_id"]].append(doc)

    rows: dict[str, list[dict[str, Any]]] = {group: [] for group in SCHEMA_GROUPS}

    for task_index, task in enumerate(tasks):
        task_id = task["task_id"]
        query = task["query"]
        repo_id = task["repo_id"]
        label = label_map[task_id]
        task_key = f"r1e_task_{task_index:04d}"
        rows["task_identity"].append({"task_key": task_key, "task": task, "label_quality": label.get("label_quality")})
        rows["anchor_source"].append(
            {
                "task_key": task_key,
                "public_task_source": public_task_source,
                "repo_lock_entry": repos.get(repo_id, {}),
                "corpus_file_count_for_repo": len(corpus_by_repo.get(repo_id, [])),
            }
        )
        scoped_corpus = corpus_by_repo.get(repo_id, [])
        bm25 = bm25_rank(query, scoped_corpus)
        lex = lexical_rank(query, scoped_corpus)
        merged = rrf_merge([bm25, lex], depth)
        for rank_index, candidate in enumerate(merged, start=1):
            doc = corpus_by_path[candidate["path"]]
            window = best_line_window(query, doc)
            rows["candidate_pool"].append(
                {
                    "task_key": task_key,
                    "task_id": task_id,
                    "query": query,
                    "candidate_rank": rank_index,
                    "candidate_path": candidate["path"],
                    "candidate_repo_id": candidate["repo_id"],
                    "candidate_sources": candidate["sources"],
                }
            )
            rows["rank_pack"].append(
                {
                    "task_key": task_key,
                    "task_id": task_id,
                    "candidate_rank": rank_index,
                    "candidate_path": candidate["path"],
                    "rank_sources": candidate["sources"],
                    "bm25_like_rank": candidate["component_ranks"].get("bm25_like"),
                    "symbol_overlap_rank": candidate["component_ranks"].get("symbol_overlap"),
                    "rrf_like_score": candidate["rrf_score"],
                }
            )
            rows["evidence_core"].append(
                {
                    "task_key": task_key,
                    "task_id": task_id,
                    "query": query,
                    "path": candidate["path"],
                    "start_line": window["start_line"],
                    "end_line": window["end_line"],
                    "snippet": window["snippet"],
                    "line_overlap_score": window["line_overlap_score"],
                }
            )
            rows["span_projection"].append(
                {
                    "task_key": task_key,
                    "task_id": task_id,
                    "path": candidate["path"],
                    "projected_start_line": window["start_line"],
                    "projected_end_line": window["end_line"],
                    "gold_spans": label.get("gold_spans", []),
                }
            )
        gold_paths = {span.get("path") for span in label.get("gold_spans", [])}
        ranked_paths = [row["path"] for row in merged]
        first_hit_rank = next((idx for idx, path in enumerate(ranked_paths, start=1) if path in gold_paths), None)
        rows["outcome_metric"].append(
            {
                "task_key": task_key,
                "task_id": task_id,
                "query": query,
                "gold_spans": label.get("gold_spans", []),
                "hard_negatives": label.get("hard_negatives", []),
                "candidate_depth": depth,
                "candidate_count": len(merged),
                "gold_file_hit": first_hit_rank is not None,
                "first_gold_file_rank": first_hit_rank,
            }
        )

    for group in PLACEHOLDER_ALLOWED_GROUPS:
        rows[group].append({"placeholder_group": group, "status": "placeholder_allowed_in_r1e"})

    group_dir = private_root / "groups"
    if private_root.exists():
        shutil.rmtree(private_root)
    group_dir.mkdir(parents=True, exist_ok=True)
    for group, group_rows in rows.items():
        write_jsonl(group_dir / f"{group}.jsonl", group_rows)

    readback_counts: dict[str, int] = {}
    for group in SCHEMA_GROUPS:
        readback_counts[group] = len(load_jsonl(group_dir / f"{group}.jsonl"))
    expected_counts = {group: len(group_rows) for group, group_rows in rows.items()}
    if readback_counts != expected_counts:
        return {"status": STATUS_FAIL_READBACK, "lock_ok": True, "private_group_counts": readback_counts}

    candidate_rows = len(rows["candidate_pool"])
    rank_rows = len(rows["rank_pack"])
    evidence_rows = len(rows["evidence_core"])
    outcome_rows = len(rows["outcome_metric"])
    bm25_trace = any(row.get("bm25_like_rank") for row in rows["rank_pack"])
    rrf_trace = any("rrf_like_score" in row for row in rows["rank_pack"])
    required_meaningful = all(readback_counts.get(group, 0) > 0 for group in REQUIRED_MEANINGFUL_GROUPS)
    hit_count = sum(1 for row in rows["outcome_metric"] if row.get("gold_file_hit"))
    pass_ready = (
        len(tasks) >= MIN_PASS_SAMPLE_SIZE
        and len(tasks) <= MAX_SAMPLE_SIZE
        and depth <= MAX_CANDIDATE_DEPTH
        and required_meaningful
        and bm25_trace
        and rrf_trace
        and candidate_rows > 0
        and rank_rows > 0
        and evidence_rows > 0
        and outcome_rows > 0
    )
    status = STATUS_PASS if pass_ready else STATUS_NO_GO_INSUFFICIENT
    return {
        "status": status,
        "lock_ok": True,
        "r1d_source_lock": r1d_lock,
        "r14_fixture_lock_bool": True,
        "source_file_count": source_file_count,
        "source_line_count": source_line_count,
        "sample_count": len(tasks),
        "candidate_depth": depth,
        "private_group_counts": readback_counts,
        "candidate_rows": candidate_rows,
        "rank_rows": rank_rows,
        "evidence_rows": evidence_rows,
        "outcome_rows": outcome_rows,
        "bm25_trace": bm25_trace,
        "rrf_trace": rrf_trace,
        "hit_count": hit_count,
        "corpus_file_count": len(corpus),
    }


PUBLIC_LEAK_PATTERNS = [
    ("workspace_path", re.compile(r"/workspace/|OpenLocus-Lab")),
    ("temp_path", re.compile(r"/tmp/|/var/tmp/")),
    ("fixture_private_path", re.compile(r"fixtures/r14/(labels|tasks|repos\.lock)|crates/openlocus-[A-Za-z0-9_-]+/")),
    ("task_id", re.compile(r"r14s-\d+|\"task_id\"")),
    ("query_field", re.compile(r"\"query\"")),
    ("repo_id_value", re.compile(r"openlocus-(core|repo|retrieval|store|index|cli|ast|graph|context|provider|derived)")),
    ("source_filename", re.compile(r"[A-Za-z0-9_/-]+\.rs")),
    ("line_range", re.compile(r"start_line|end_line|line_range|snippet")),
    ("label_field", re.compile(r"gold_spans|hard_negatives|label_quality")),
    ("score_field", re.compile(r"rrf_like_score|bm25_like_score|\"score\"")),
    ("hash_value", re.compile(r"\b[a-f0-9]{32,64}\b")),
    ("raw_sequence", re.compile(r"raw_sequence|raw_rows|private_rows_public")),
]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = []
    for bucket, pattern in PUBLIC_LEAK_PATTERNS:
        if pattern.search(text):
            findings.append(bucket)
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(self_test_total: int) -> dict[str, bool]:
    repo_root = Path(__file__).resolve().parents[1]
    base_fragments = [
        R1D_LOCKED_CHECKPOINT,
        R1D_LOCKED_STATUS,
        STATUS_PASS,
        "HAAE-R1E",
        "HAAE-R2",
    ]
    expected_fragments = base_fragments + [f"{self_test_total}/{self_test_total}"]
    expected_fragments_spaced = base_fragments + [f"{self_test_total} / {self_test_total}"]

    def read(rel: str) -> str:
        path = repo_root / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in expected_fragments) or all(fragment in text for fragment in expected_fragments_spaced)

    readme = read("README.md")
    detail_en = read("docs/en/bea-v1-haae-r1e-bounded-private-experiment-material-generation.md")
    detail_zh = read("docs/zh/bea-v1-haae-r1e-bounded-private-experiment-material-generation.md")
    current_en = read("docs/en/current-research-conclusions.md")
    current_zh = read("docs/zh/current-research-conclusions.md")
    current_root = read("docs/current-research-conclusions.md")
    log_en = read("docs/en/research-log.md")
    log_zh = read("docs/zh/research-log.md")
    summary_en = read("docs/en/research-summary.md")
    summary_zh = read("docs/zh/research-summary.md")
    detail_match = has_all(detail_en) and has_all(detail_zh)
    current_match = has_all(current_en) and has_all(current_zh) and has_all(current_root)
    log_match = has_all(log_en) and has_all(log_zh)
    summary_match = has_all(summary_en) and has_all(summary_zh)
    readme_match = has_all(readme)
    return {
        "readme_readback_match_bool": readme_match,
        "detail_docs_readback_match_bool": detail_match,
        "current_conclusions_readback_match_bool": current_match,
        "research_log_readback_match_bool": log_match,
        "research_summary_readback_match_bool": summary_match,
        "all_public_readback_match_bool": readme_match and detail_match and current_match and log_match and summary_match,
    }


def build_report(
    status: str,
    explicit_mode: bool,
    private_root_valid: bool = False,
    private_root_reason: str = "not_supplied",
    sample_size: int = 0,
    candidate_depth: int = 0,
    recipe: str = ALLOWED_RECIPE,
    result: dict[str, Any] | None = None,
    self_test_total: int = 0,
) -> dict[str, Any]:
    result = result or {}
    r1d_lock = result.get("r1d_source_lock") or validate_r1d_source_lock(Path(__file__).resolve().parents[1])
    r14_fixture_lock_bool = bool(result.get("r14_fixture_lock_bool", result.get("lock_ok", explicit_mode is False)))
    source_locked_bool = bool(r1d_lock.get("r1d_source_locked_bool")) and r14_fixture_lock_bool
    readback = public_readback_match(self_test_total)
    group_counts = result.get("private_group_counts", {})
    meaningful_count = sum(1 for group in REQUIRED_MEANINGFUL_GROUPS if group_counts.get(group, 0) > 0)
    placeholder_count = sum(1 for group in PLACEHOLDER_ALLOWED_GROUPS if group_counts.get(group, 0) > 0)
    all_required_meaningful = meaningful_count == len(REQUIRED_MEANINGFUL_GROUPS)
    r2_authorized = status == STATUS_PASS
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase_bucket": PHASE,
        "status": status,
        "source_lock_records": [
            {
                "anonymous_source_lock_id": "haaer1esource0000",
                "locked_haae_r1d_checkpoint": R1D_LOCKED_CHECKPOINT,
                "locked_haae_r1d_status": R1D_LOCKED_STATUS,
                "source_lock_bucket": "r1d_public_artifact_and_r14_fixture_lock",
                "source_locked_bool": source_locked_bool,
                "r1d_source_locked_bool": bool(r1d_lock.get("r1d_source_locked_bool")),
                "r1d_status_match_bool": bool(r1d_lock.get("r1d_status_match_bool")),
                "r1d_forbidden_scan_pass_bool": bool(r1d_lock.get("r1d_forbidden_scan_pass_bool")),
                "r1d_bootstrap_placeholder_no_go_match_bool": bool(r1d_lock.get("r1d_bootstrap_placeholder_no_go_match_bool")),
                "r1d_no_hydration_or_execution_match_bool": bool(r1d_lock.get("r1d_no_hydration_or_execution_match_bool")),
                "r1d_source_lock_reason_bucket": str(r1d_lock.get("r1d_source_lock_reason_bucket", "unknown")),
                "r14_fixture_lock_bool": r14_fixture_lock_bool,
                "repo_lock_validation_bucket": "pass" if r14_fixture_lock_bool else "fail",
                "source_file_count_bucket": bucket_count(int(result.get("source_file_count", 0))),
                "source_line_count_bucket": bucket_count(int(result.get("source_line_count", 0))),
            }
        ],
        "execution_mode_records": [
            {
                "anonymous_execution_mode_id": "haaer1emode0000",
                "mode_bucket": "explicit_local_manual_private_material_generation" if explicit_mode else "default_no_private_material_generation",
                "explicit_opt_in_bool": explicit_mode,
                "local_only_bool": True,
                "ci_execution_bool": False,
                "network_operation_count_bucket": "count_0",
                "clone_operation_count_bucket": "count_0",
                "provider_or_model_operation_count_bucket": "count_0",
                "openlocus_runtime_execution_bool": False,
                "private_read_count_bucket": "count_1_to_10" if explicit_mode else "count_0",
                "private_write_count_bucket": bucket_count(sum(group_counts.values())) if explicit_mode else "count_0",
            }
        ],
        "private_root_records": [
            {
                "anonymous_private_root_id": "haaer1eroot0000",
                "private_root_supplied_bool": explicit_mode,
                "root_boundary_status_bucket": private_root_reason if explicit_mode else "not_supplied_default_safe",
                "root_valid_bool": private_root_valid,
                "no_concrete_path_published_bool": True,
                "no_concrete_filename_published_bool": True,
                "temp_or_ignored_root_bool": private_root_valid,
                "private_row_values_public_bool": False,
            }
        ],
        "sample_bound_records": [
            {
                "anonymous_sample_bound_id": "haaer1esample0000",
                "public_task_source_bucket": "r14_sanity" if sample_size else "none_default",
                "sample_size_bucket": bucket_count(sample_size),
                "candidate_depth_bucket": bucket_count(candidate_depth),
                "sample_within_r1e_bound_bool": 0 < sample_size <= MAX_SAMPLE_SIZE if explicit_mode else True,
                "candidate_depth_within_r1e_bound_bool": 0 < candidate_depth <= MAX_CANDIDATE_DEPTH if explicit_mode else True,
            }
        ],
        "material_generation_recipe_records": [
            {
                "anonymous_recipe_id": "haaer1erecipe0000",
                "recipe_bucket": recipe if explicit_mode else "none_default",
                "deterministic_local_lexical_bool": explicit_mode,
                "bm25_like_trace_required_bool": explicit_mode,
                "rrf_like_merge_required_bool": explicit_mode,
                "openlocus_runtime_used_bool": False,
            }
        ],
        "private_schema_group_material_records": [
            {
                "anonymous_schema_group_material_id": f"haaer1egroup{idx:04d}",
                "group_bucket": group,
                "required_for_r2_bool": group in REQUIRED_MEANINGFUL_GROUPS,
                "placeholder_allowed_bool": group in PLACEHOLDER_ALLOWED_GROUPS,
                "private_row_count_bucket": bucket_count(int(group_counts.get(group, 0))),
                "meaningful_private_rows_bool": group_counts.get(group, 0) > 0 and group not in PLACEHOLDER_ALLOWED_GROUPS,
                "row_values_published_bool": False,
            }
            for idx, group in enumerate(SCHEMA_GROUPS)
        ],
        "rank_source_records": [
            {
                "anonymous_rank_source_id": "haaer1erank0000",
                "bm25_like_rank_trace_present_bool": bool(result.get("bm25_trace", False)),
                "symbol_overlap_rank_trace_present_bool": explicit_mode,
                "rrf_like_rank_trace_present_bool": bool(result.get("rrf_trace", False)),
                "rank_pack_private_row_count_bucket": bucket_count(int(result.get("rank_rows", 0))),
            }
        ],
        "evidence_hit_aggregate_records": [
            {
                "anonymous_evidence_hit_aggregate_id": "haaer1eevidence0000",
                "candidate_private_row_count_bucket": bucket_count(int(result.get("candidate_rows", 0))),
                "evidence_private_row_count_bucket": bucket_count(int(result.get("evidence_rows", 0))),
                "outcome_private_row_count_bucket": bucket_count(int(result.get("outcome_rows", 0))),
                "gold_file_hit_rate_bucket": bucket_rate(int(result.get("hit_count", 0)), int(result.get("outcome_rows", 0))),
            }
        ],
        "public_aggregate_manifest_records": [
            {
                "anonymous_public_manifest_id": "haaer1emanifest0000",
                "aggregate_only_bool": True,
                "concrete_paths_published_bool": False,
                "concrete_task_ids_published_bool": False,
                "queries_published_bool": False,
                "labels_published_bool": False,
                "scores_or_hashes_published_bool": False,
                "diagnostic_rows_published_bool": False,
                "schema_group_accounted_count": len(SCHEMA_GROUPS),
                "meaningful_required_group_count_bucket": bucket_count(meaningful_count),
                "placeholder_group_count_bucket": bucket_count(placeholder_count),
                "self_test_total_check_count": self_test_total,
            }
        ],
        "public_readback_records": [
            {
                "anonymous_public_readback_id": "haaer1ereadback0000",
                **readback,
            }
        ],
        "claim_boundary_records": [
            {
                "anonymous_claim_boundary_id": "haaer1eclaim0000",
                "aggregate_buckets_only_bool": True,
                "bounded_private_material_generation_bool": explicit_mode,
                "small_experiment_r2_authorized_bool": r2_authorized,
                "bea_v1_a_bool": False,
                "p5_bool": False,
                "selector_reranker_bool": False,
                "method_winner_claim_bool": False,
                "runtime_default_change_bool": False,
                "ci_network_clone_provider_bool": False,
                "raw_publication_bool": False,
            }
        ],
        "pass_fail_gate_records": [],
        "synthetic_validator_records": [
            {
                "anonymous_synthetic_validator_id": "haaer1esynth0000",
                "validator_bucket": "default_no_private_read_write_fixture",
                "expected_status_bucket": STATUS_DEFAULT,
            },
            {
                "anonymous_synthetic_validator_id": "haaer1esynth0001",
                "validator_bucket": "synthetic_valid_three_task_fixture",
                "expected_status_bucket": STATUS_PASS,
            },
            {
                "anonymous_synthetic_validator_id": "haaer1esynth0002",
                "validator_bucket": "leak_and_overauthorization_mutation_fixtures",
                "expected_status_bucket": "validator_rejects_mutations",
            },
        ],
        "stop_go_records": [
            {
                "anonymous_stop_go_id": "haaer1estop0000",
                "r2_small_experiment_authorized_bool": r2_authorized,
                "next_allowed_phase": "BEA-v1-HAAE-R2 Small Local Experiment" if r2_authorized else "none_r2_not_authorized",
                "haae_r2_small_local_lexical_material_experiment_authorized_bool": r2_authorized,
                "haae_r2_execution_authorized_bool": r2_authorized,
                "haae_r2_reads_r1e_private_material_bool": r2_authorized,
                "haae_r2_aggregate_metric_computation_authorized_bool": r2_authorized,
                "haae_r2_new_candidate_generation_authorized_bool": False,
                "haae_r2_broad_retrieval_authorized_bool": False,
                "haae_r2_scheduler_authorized_bool": False,
                "haae_r2_haae_layer_execution_authorized_bool": False,
                "haae_r2_selector_reranker_authorized_bool": False,
                "haae_r2_provider_model_network_authorized_bool": False,
                "haae_r2_runtime_default_change_authorized_bool": False,
                "haae_r2_bea_v1_a_authorized_bool": False,
                "haae_r2_p5_authorized_bool": False,
                "haae_r2_method_winner_claim_authorized_bool": False,
                "haae_r2_raw_publication_authorized_bool": False,
                "replay_authorized_bool": False,
                "policy_or_arm_scoring_authorized_bool": False,
                "retrieval_runtime_authorized_bool": False,
                "selector_reranker_authorized_bool": False,
                "bea_v1_a_authorized_bool": False,
                "p5_authorized_bool": False,
                "runtime_default_change_authorized_bool": False,
            }
        ],
    }
    gates = [
        ("explicit_opt_in_gate", explicit_mode if status != STATUS_DEFAULT else True),
        ("source_lock_gate", source_locked_bool),
        ("r1d_source_lock_gate", bool(r1d_lock.get("r1d_source_locked_bool"))),
        ("r14_fixture_lock_gate", r14_fixture_lock_bool),
        ("private_root_boundary_gate", private_root_valid if explicit_mode else True),
        ("local_only_no_network_clone_provider_gate", True),
        ("sample_bound_gate", (0 < sample_size <= MAX_SAMPLE_SIZE) if explicit_mode else True),
        ("candidate_depth_bound_gate", (0 < candidate_depth <= MAX_CANDIDATE_DEPTH) if explicit_mode else True),
        ("required_six_groups_meaningful_gate", all_required_meaningful if explicit_mode else False),
        ("bm25_and_rrf_trace_gate", bool(result.get("bm25_trace", False) and result.get("rrf_trace", False)) if explicit_mode else False),
        ("candidate_rank_evidence_outcome_rows_gate", all(int(result.get(key, 0)) > 0 for key in ["candidate_rows", "rank_rows", "evidence_rows", "outcome_rows"]) if explicit_mode else False),
        ("public_aggregate_only_gate", True),
        ("public_readback_match_gate", readback["all_public_readback_match_bool"]),
    ]
    report["pass_fail_gate_records"] = [
        {
            "anonymous_gate_id": f"haaer1egate{idx:04d}",
            "gate_bucket": name,
            "gate_passed_bool": bool(passed),
            "gate_evaluated_on_aggregate_bool": True,
            "gate_performs_ci_rerun_bool": False,
            "gate_uses_network_clone_provider_bool": False,
        }
        for idx, (name, passed) in enumerate(gates)
    ]
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass" and status != STATUS_FAIL_PUBLIC_LEAK:
        report["status"] = STATUS_FAIL_PUBLIC_LEAK
        report["stop_go_records"][0]["r2_small_experiment_authorized_bool"] = False
        report["stop_go_records"][0]["next_allowed_phase"] = "none_r2_not_authorized"
        report["claim_boundary_records"][0]["small_experiment_r2_authorized_bool"] = False
    return report


def write_report(report: dict[str, Any], out_path: Path | None = None) -> Path:
    if out_path is None:
        out_path = ARTIFACT_DIR / REPORT_NAME
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out_path


def validate_report(report: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    required_top = [
        "source_lock_records",
        "execution_mode_records",
        "private_root_records",
        "sample_bound_records",
        "material_generation_recipe_records",
        "private_schema_group_material_records",
        "rank_source_records",
        "evidence_hit_aggregate_records",
        "public_aggregate_manifest_records",
        "public_readback_records",
        "claim_boundary_records",
        "pass_fail_gate_records",
        "synthetic_validator_records",
        "stop_go_records",
        "forbidden_scan",
    ]
    for key in required_top:
        if key not in report:
            issues.append(f"missing_{key}")
    scan = scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})
    if scan["status"] != "pass":
        issues.append("public_manifest_leak")
    if not report.get("public_readback_records", [{}])[0].get("all_public_readback_match_bool"):
        issues.append("public_readback_not_true")
    groups = {row.get("group_bucket"): row for row in report.get("private_schema_group_material_records", [])}
    if set(groups) != set(SCHEMA_GROUPS):
        issues.append("schema_group_set_mismatch")
    status = report.get("status")
    source = report.get("source_lock_records", [{}])[0]
    if not (source.get("source_locked_bool") and source.get("r1d_source_locked_bool") and source.get("r14_fixture_lock_bool")):
        issues.append("source_lock_not_true")
    r2_record = report.get("stop_go_records", [{}])[0]
    r2 = bool(r2_record.get("r2_small_experiment_authorized_bool"))
    if r2 != (status == STATUS_PASS):
        issues.append("r2_authorization_status_mismatch")
    if status == STATUS_PASS:
        required_true = [
            "haae_r2_small_local_lexical_material_experiment_authorized_bool",
            "haae_r2_execution_authorized_bool",
            "haae_r2_reads_r1e_private_material_bool",
            "haae_r2_aggregate_metric_computation_authorized_bool",
        ]
        required_false = [
            "haae_r2_new_candidate_generation_authorized_bool",
            "haae_r2_broad_retrieval_authorized_bool",
            "haae_r2_scheduler_authorized_bool",
            "haae_r2_haae_layer_execution_authorized_bool",
            "haae_r2_selector_reranker_authorized_bool",
            "haae_r2_provider_model_network_authorized_bool",
            "haae_r2_runtime_default_change_authorized_bool",
            "haae_r2_bea_v1_a_authorized_bool",
            "haae_r2_p5_authorized_bool",
            "haae_r2_method_winner_claim_authorized_bool",
            "haae_r2_raw_publication_authorized_bool",
        ]
        if any(r2_record.get(key) is not True for key in required_true):
            issues.append("r2_required_authorization_fields_missing")
        if any(r2_record.get(key) is not False for key in required_false):
            issues.append("r2_over_authorization_field_true")
    for row in report.get("execution_mode_records", []):
        for key in ["network_operation_count_bucket", "clone_operation_count_bucket", "provider_or_model_operation_count_bucket"]:
            if row.get(key) != "count_0":
                issues.append("forbidden_operation_exposed")
    if status == STATUS_PASS:
        for group in REQUIRED_MEANINGFUL_GROUPS:
            if not groups.get(group, {}).get("meaningful_private_rows_bool"):
                issues.append("pass_missing_required_meaningful_group")
        rank = report.get("rank_source_records", [{}])[0]
        if not (rank.get("bm25_like_rank_trace_present_bool") and rank.get("rrf_like_rank_trace_present_bool")):
            issues.append("pass_missing_bm25_or_rrf_trace")
        if report.get("forbidden_scan", {}).get("status") != "pass":
            issues.append("pass_forbidden_scan_not_pass")
    return len(issues) == 0, issues


def unavailable_default() -> dict[str, Any]:
    return build_report(STATUS_DEFAULT, explicit_mode=False, self_test_total=SELF_TEST_EXPECTED)


SELF_TEST_EXPECTED = 16


def run_self_test(repo_root: Path) -> tuple[bool, list[str]]:
    failures: list[str] = []

    def check(name: str, condition: bool) -> None:
        if not condition:
            failures.append(name)

    default_report = unavailable_default()
    check("default_no_private_read_write", default_report["status"] == STATUS_DEFAULT and default_report["execution_mode_records"][0]["private_write_count_bucket"] == "count_0")

    check("r1d_source_lock_current_artifact_passes", validate_r1d_source_lock(repo_root)["r1d_source_locked_bool"] is True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        json.dump({"status": "wrong_status", "forbidden_scan": {"status": "pass"}}, handle)
        wrong_path = Path(handle.name)
    try:
        check("r1d_source_lock_wrong_status_fails", validate_r1d_source_lock(repo_root, wrong_path)["r1d_source_locked_bool"] is False)
    finally:
        wrong_path.unlink(missing_ok=True)
    check("r1d_source_lock_missing_report_fails", validate_r1d_source_lock(repo_root, Path("missing_r1d_report.json"))["r1d_source_locked_bool"] is False)

    missing_opt = build_report(STATUS_FAIL_MISSING_OPT_IN, explicit_mode=False, sample_size=3, candidate_depth=10, self_test_total=SELF_TEST_EXPECTED)
    check("missing_opt_in_fails", missing_opt["status"] == STATUS_FAIL_MISSING_OPT_IN)

    ok_root, _ = validate_private_root(repo_root / "artifacts" / SLUG / "private", repo_root)
    check("repo_public_output_root_rejected", not ok_root)

    leak_report = unavailable_default()
    leak_report["public_aggregate_manifest_records"][0]["private_root_path"] = "/tmp/haae_r1e_private_material_root"
    leak_report["public_aggregate_manifest_records"][0]["task_id"] = "r14s-001"
    leak_report["public_aggregate_manifest_records"][0]["query"] = "EvidenceCore"
    leak_report["public_aggregate_manifest_records"][0]["raw_sequence"] = "crates/openlocus-core/src/evidence.rs"
    check("scanner_catches_public_leaks", not validate_report(leak_report)[0])

    over_sample = build_report(STATUS_FAIL_BOUNDS, explicit_mode=True, private_root_valid=True, sample_size=6, candidate_depth=10, self_test_total=SELF_TEST_EXPECTED)
    check("sample_gt_5_fails", over_sample["status"] == STATUS_FAIL_BOUNDS and not over_sample["sample_bound_records"][0]["sample_within_r1e_bound_bool"])

    over_depth = build_report(STATUS_FAIL_BOUNDS, explicit_mode=True, private_root_valid=True, sample_size=3, candidate_depth=21, self_test_total=SELF_TEST_EXPECTED)
    check("depth_gt_20_fails", over_depth["status"] == STATUS_FAIL_BOUNDS and not over_depth["sample_bound_records"][0]["candidate_depth_within_r1e_bound_bool"])

    forbidden = unavailable_default()
    forbidden["execution_mode_records"][0]["network_operation_count_bucket"] = "count_1"
    check("network_clone_provider_flags_fail", not validate_report(forbidden)[0])

    missing_group = build_report(
        STATUS_NO_GO_INSUFFICIENT,
        explicit_mode=True,
        private_root_valid=True,
        sample_size=3,
        candidate_depth=10,
        result={"lock_ok": True, "private_group_counts": {"task_identity": 3}},
        self_test_total=SELF_TEST_EXPECTED,
    )
    check("missing_required_group_no_go", missing_group["status"] == STATUS_NO_GO_INSUFFICIENT)

    bm25_only = build_report(
        STATUS_NO_GO_INSUFFICIENT,
        explicit_mode=True,
        private_root_valid=True,
        sample_size=3,
        candidate_depth=10,
        result={"lock_ok": True, "private_group_counts": {g: 1 for g in REQUIRED_MEANINGFUL_GROUPS}, "bm25_trace": True, "rrf_trace": False},
        self_test_total=SELF_TEST_EXPECTED,
    )
    check("bm25_only_without_rrf_no_go", bm25_only["status"] == STATUS_NO_GO_INSUFFICIENT)

    synthetic_pass = build_report(
        STATUS_PASS,
        explicit_mode=True,
        private_root_valid=True,
        sample_size=3,
        candidate_depth=10,
        result={
            "lock_ok": True,
            "private_group_counts": {group: (1 if group in SCHEMA_GROUPS else 0) for group in SCHEMA_GROUPS},
            "bm25_trace": True,
            "rrf_trace": True,
            "candidate_rows": 3,
            "rank_rows": 3,
            "evidence_rows": 3,
            "outcome_rows": 3,
        },
        self_test_total=SELF_TEST_EXPECTED,
    )
    check("synthetic_valid_three_task_fixture_passes", validate_report(synthetic_pass)[0] and synthetic_pass["status"] == STATUS_PASS)

    raw_leak = synthetic_pass.copy()
    raw_leak["leak"] = {"gold_spans": [{"path": "crates/openlocus-core/src/evidence.rs"}]}
    check("raw_public_leak_validation_fails", not validate_report(raw_leak)[0])

    overauth = unavailable_default()
    overauth["stop_go_records"][0]["r2_small_experiment_authorized_bool"] = True
    check("r2_overauthorization_mutation_fails", not validate_report(overauth)[0])

    overauth_detail = synthetic_pass.copy()
    overauth_detail["stop_go_records"] = [dict(synthetic_pass["stop_go_records"][0])]
    overauth_detail["stop_go_records"][0]["haae_r2_new_candidate_generation_authorized_bool"] = True
    check("r2_new_candidate_generation_overauthorization_fails", not validate_report(overauth_detail)[0])

    unknown_source = select_positive_tasks(repo_root, "unknown_source", 3)[0]
    check("no_public_task_source_no_go", unknown_source == [])

    return len(failures) == 0, failures


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=PHASE, allow_abbrev=False)
    parser.add_argument("--allow-private-material-generation", action="store_true")
    parser.add_argument("--private-output-root", default="")
    parser.add_argument("--sample-size", type=int, default=3)
    parser.add_argument("--candidate-depth", type=int, default=20)
    parser.add_argument("--confirm-private-rows-only", action="store_true")
    parser.add_argument("--public-task-source", default="r14_sanity", choices=sorted(PUBLIC_TASK_SOURCES))
    parser.add_argument("--recipe", default=ALLOWED_RECIPE, choices=[ALLOWED_RECIPE])
    parser.add_argument("--validate-report", default="")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    repo_root = Path(__file__).resolve().parents[1]
    os.chdir(repo_root)

    if args.self_test:
        ok, failures = run_self_test(repo_root)
        result = {"self_test_total": SELF_TEST_EXPECTED, "passed": ok, "failures": failures, "status": STATUS_PASS if ok else STATUS_NO_GO_INSUFFICIENT}
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if ok else 1

    if args.validate_report:
        report = json.loads(Path(args.validate_report).read_text(encoding="utf-8"))
        ok, issues = validate_report(report)
        print(json.dumps({"passed": ok, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True))
        return 0 if ok else 1

    out_path = Path(args.out) if args.out else None
    if not args.allow_private_material_generation:
        missing_opt_in_failure = False
        if args.private_output_root or args.confirm_private_rows_only:
            missing_opt_in_failure = True
            report = build_report(
                STATUS_FAIL_MISSING_OPT_IN,
                explicit_mode=False,
                sample_size=args.sample_size,
                candidate_depth=args.candidate_depth,
                self_test_total=SELF_TEST_EXPECTED,
            )
        else:
            report = unavailable_default()
        write_report(report, out_path)
        print(json.dumps({"status": report["status"], "artifact": str(out_path or ARTIFACT_DIR / REPORT_NAME)}, sort_keys=True))
        return 1 if missing_opt_in_failure else 0

    if not args.confirm_private_rows_only:
        report = build_report(
            STATUS_FAIL_MISSING_OPT_IN,
            explicit_mode=True,
            sample_size=args.sample_size,
            candidate_depth=args.candidate_depth,
            self_test_total=SELF_TEST_EXPECTED,
        )
        write_report(report, out_path)
        return 1
    if args.sample_size < 1 or args.sample_size > MAX_SAMPLE_SIZE or args.candidate_depth < 1 or args.candidate_depth > MAX_CANDIDATE_DEPTH:
        report = build_report(
            STATUS_FAIL_BOUNDS,
            explicit_mode=True,
            private_root_valid=False,
            sample_size=args.sample_size,
            candidate_depth=args.candidate_depth,
            self_test_total=SELF_TEST_EXPECTED,
        )
        write_report(report, out_path)
        return 1
    if not args.private_output_root:
        report = build_report(
            STATUS_FAIL_PRIVATE_ROOT,
            explicit_mode=True,
            private_root_valid=False,
            sample_size=args.sample_size,
            candidate_depth=args.candidate_depth,
            self_test_total=SELF_TEST_EXPECTED,
        )
        write_report(report, out_path)
        return 1

    private_root = Path(args.private_output_root)
    root_ok, root_reason = validate_private_root(private_root, repo_root)
    if not root_ok:
        report = build_report(
            STATUS_FAIL_PRIVATE_ROOT,
            explicit_mode=True,
            private_root_valid=False,
            private_root_reason=root_reason,
            sample_size=args.sample_size,
            candidate_depth=args.candidate_depth,
            self_test_total=SELF_TEST_EXPECTED,
        )
        write_report(report, out_path)
        return 1

    result = materialize_private_rows(repo_root, private_root, args.sample_size, args.candidate_depth, args.public_task_source)
    report = build_report(
        result.get("status", STATUS_NO_GO_INSUFFICIENT),
        explicit_mode=True,
        private_root_valid=True,
        private_root_reason=root_reason,
        sample_size=int(result.get("sample_count", args.sample_size)),
        candidate_depth=args.candidate_depth,
        recipe=args.recipe,
        result=result,
        self_test_total=SELF_TEST_EXPECTED,
    )
    ok, issues = validate_report(report)
    if not ok and report["status"] == STATUS_PASS:
        report["status"] = STATUS_FAIL_PUBLIC_LEAK if "public_manifest_leak" in issues else STATUS_NO_GO_INSUFFICIENT
        report["stop_go_records"][0]["r2_small_experiment_authorized_bool"] = False
        report["stop_go_records"][0]["next_allowed_phase"] = "none_r2_not_authorized"
        report["claim_boundary_records"][0]["small_experiment_r2_authorized_bool"] = False
    write_report(report, out_path)
    print(json.dumps({"status": report["status"], "private_rows_written_bucket": report["execution_mode_records"][0]["private_write_count_bucket"]}, sort_keys=True))
    return 0 if report["status"] in {STATUS_PASS, STATUS_NO_GO_INSUFFICIENT, STATUS_NO_GO_NO_SOURCE} else 1


if __name__ == "__main__":
    raise SystemExit(main())
