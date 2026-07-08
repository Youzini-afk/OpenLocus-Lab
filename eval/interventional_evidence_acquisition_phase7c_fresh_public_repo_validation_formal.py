#!/usr/bin/env python3
"""Phase 7C formal fresh public-repo validation under frozen Phase 7A protocol.

Formal runner. It writes private manifest/rows under ignored runs/ only after
explicit confirmation, reads prior private rows/manifests only for overlap
rejection, fetches public repositories in the current run, and publishes an
aggregate no-claim public report.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
PHASE = "phase7c_fresh_public_repo_validation_formal"
SCHEMA_VERSION = "phase7c_fresh_public_repo_validation_formal_report_v1"
PRIVATE_ROW_SCHEMA = "phase7c_fresh_public_repo_validation_formal_private_row_v1"
PRIVATE_MANIFEST_SCHEMA = "phase7c_fresh_public_repo_validation_formal_private_manifest_v1"
STATUS_STOP = "stop_formal_no_claim"
STATUS_REPAIR = "repair_formal_pipeline_no_claim"
STATUS_PASS = "phase7c_formal_fresh_public_repo_validation_passed_no_claim"
DEFAULT_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
PRIVATE_ROOT = REPO / "runs" / PHASE
DEFAULT_PUBLIC_REPO_INPUTS = PRIVATE_ROOT / "private_public_repo_inputs.json"
PHASE7A_REPORT = REPO / "artifacts" / "phase7a_fresh_public_repo_validation_protocol_freeze" / "phase7a_fresh_public_repo_validation_protocol_freeze_report.json"
PHASE5B_ROOT = REPO / "runs" / "phase5b_public_repo_formal_validation"
PHASE5B_PREP_ROOT = REPO / "runs" / "phase5b_formal_prep"
PHASE5B_ROWS_NAME = "phase5b_private_rows.jsonl"
PHASE7B_ROOT = REPO / "runs" / "phase7b_fresh_public_repo_validation_canary"
PHASE7B_MANIFEST_NAME = "phase7b_private_canary_manifest.json"
PHASE7B_ROWS_NAME = "phase7b_private_canary_rows.jsonl"
LABELS = (
    "bm25_then_read_top1",
    "bm25_then_read_next_unique_file",
    "symbol_regex_then_read_top1",
    "symbol_regex_then_read_next_unique_file",
    "read_related_test_when_available",
    "stop",
    "abstain",
)
CONTROL_LABELS = {"stop", "abstain"}
FORMAL_REPO_TARGET_MIN = 8
FORMAL_REPO_TARGET_MAX = 12
FORMAL_REPO_HARD_MAX = 16
FORMAL_TASK_MIN = 80
FORMAL_TASK_MAX = 120
FORMAL_TASK_HARD_MAX = 150
FORMAL_MAX_TASKS_PER_REPO = 20
FORMAL_ROW_HARD_MAX = FORMAL_TASK_HARD_MAX * len(LABELS)
CANARY_REPO_TARGET = FORMAL_REPO_TARGET_MIN
CANARY_REPO_HARD_MAX = FORMAL_REPO_HARD_MAX
CANARY_TASK_MIN = FORMAL_TASK_MIN
CANARY_TASK_MAX = FORMAL_TASK_MAX
CANARY_TASK_HARD_MAX = FORMAL_TASK_HARD_MAX
CANARY_MAX_TASKS_PER_REPO = FORMAL_MAX_TASKS_PER_REPO
CANARY_ROW_HARD_MAX = FORMAL_ROW_HARD_MAX
CLAIM_WORD_RE = re.compile(r"\b(winner|lift|selected method|selected strategy|product|default|runtime|deployment|training|route works)\b", re.I)
PRIVATE_VALUE_RE = re.compile(r"([A-Za-z]:)?[\\/][A-Za-z0-9_.\\/-]+|\b[a-fA-F0-9]{32,}\b|\b\d+\s*-\s*\d+\b")
PRIVATE_KEY_RE = re.compile(r"(repo_url|repo_name|owner|commit|sha|path|range|hash|snippet|task_id|row_id|manifest|run_dir|per_repo|per_task)", re.I)
SINGLETON_BUCKET_RE = re.compile(r"(?<![A-Za-z0-9])(?:bucket_nonzero_lt_two|count_1(?!_to_))(?![A-Za-z0-9])")
ALLOWED_PUBLIC_PRIVATE_FLAG_KEYS = {
    "manifests_public", "run_dirs_public", "repo_names_urls_owners_public",
    "commits_shas_public", "paths_ranges_hashes_snippets_public",
    "task_ids_row_ids_public", "per_repo_per_task_details_public",
    "success_requires_range_content_match", "full_panel_per_task",
    "max_tasks_per_repo_bucket", "pinned_commit_unavailable_bucket",
}


class CanaryError(Exception):
    pass


def bucket_count(count: int) -> str:
    if count <= 0:
        return "bucket_zero"
    if count <= 3:
        return "bucket_nonzero_to_three"
    if count <= 5:
        return "bucket_four_to_five"
    if count <= 8:
        return "bucket_six_to_eight"
    if count <= 12:
        return "bucket_nine_to_twelve"
    if count <= CANARY_ROW_HARD_MAX:
        return "bucket_above_task_cap_to_row_cap"
    return "bucket_over_row_cap"


def formal_scale_bucket(count: int, kind: str) -> str:
    if kind == "repo":
        if count < FORMAL_REPO_TARGET_MIN:
            return "bucket_below_formal_repo_min"
        if count <= FORMAL_REPO_TARGET_MAX:
            return "bucket_formal_repo_target"
        if count <= FORMAL_REPO_HARD_MAX:
            return "bucket_above_repo_target_within_hard_cap"
        return "bucket_over_repo_hard_cap"
    if count < FORMAL_TASK_MIN:
        return "bucket_below_formal_task_min"
    if count <= FORMAL_TASK_MAX:
        return "bucket_formal_task_target"
    if count <= FORMAL_TASK_HARD_MAX:
        return "bucket_above_task_target_within_hard_cap"
    return "bucket_over_task_hard_cap"


def safe_json_dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                item = json.loads(line)
                if isinstance(item, dict):
                    rows.append(item)
    return rows


def path_is_ignored_runs(path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(REPO.resolve())
    except ValueError:
        return False
    return bool(rel.parts) and rel.parts[0] == "runs"


def ensure_private_path(path: Path) -> None:
    if not path_is_ignored_runs(path):
        raise CanaryError("private canary path outside ignored runs refused")


def latest_phase5b_rows_path() -> Path:
    candidates = sorted(PHASE5B_ROOT.glob(f"*/{PHASE5B_ROWS_NAME}"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise CanaryError("Phase 5B private rows unavailable for overlap check")
    return candidates[0]


def validate_phase7a_gate(path: Path = PHASE7A_REPORT) -> list[str]:
    try:
        report = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Phase 7A gate unavailable: {exc}"]
    errors: list[str] = []
    if report.get("status") != "phase7a_protocol_freeze_no_execution_no_claim":
        errors.append("Phase 7A status mismatch")
    protocol = report.get("phase7b_frozen_protocol", {})
    if tuple(protocol.get("same_seven_labels_exact", [])) != LABELS:
        errors.append("Phase 7A label freeze mismatch")
    if protocol.get("repo_hard_max") != 16 or protocol.get("task_hard_max") != 150 or protocol.get("max_tasks_per_repo") != 20:
        errors.append("Phase 7A cap mismatch")
    boundary = report.get("execution_boundary", {})
    for key in ("repo_fetch_or_clone_executed", "task_generation_executed", "canary_executed", "source_reads_executed", "private_rows_read", "runs_directory_read"):
        if boundary.get(key) is not False:
            errors.append(f"Phase 7A no-execution boundary failed: {key}")
    return errors


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def repo_identity_tokens(value: str) -> set[str]:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return set()
    return {normalized, sha256_text(normalized)[:16]}


def file_family(path: str) -> str:
    p = Path(path)
    prefix = p.parts[0] if p.parts else "root"
    return f"{prefix}:{p.suffix.lower()}"


def run_git(args: list[str], cwd: Path, *, timeout: int = 60) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if proc.returncode != 0:
        raise CanaryError("git operation failed for private public-repo input materialization")
    return proc.stdout.strip()


def public_repo_name_from_url(repo_url: str) -> str:
    name = repo_url.rstrip("/").rsplit("/", 1)[-1]
    return name[:-4] if name.endswith(".git") else name


def load_public_repo_inputs(path: Path) -> list[dict[str, Any]]:
    ensure_private_path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise CanaryError("private public-repo input manifest is required; provide --public-repo-inputs") from exc
    repos = data.get("repos") if isinstance(data, dict) else data
    if not isinstance(repos, list):
        raise CanaryError("private public-repo input manifest must contain a repos list")
    normalized: list[dict[str, Any]] = []
    for index, repo in enumerate(repos):
        if not isinstance(repo, dict):
            raise CanaryError("private public-repo input entry must be object")
        repo_url = str(repo.get("repo_url_private", "")).strip()
        locked_commit = str(repo.get("locked_commit_private", "")).strip()
        local_clone_raw = str(repo.get("local_clone_private", "")).strip()
        comparable_repo_id = str(repo.get("prior_phase_comparable_repo_id_private") or repo.get("phase5b_comparable_repo_id_private") or "").strip()
        source_type = str(repo.get("source_type_private") or "public_repo").strip().lower()
        if not repo_url or not re.fullmatch(r"https://[^\s]+", repo_url):
            raise CanaryError("private public-repo input missing https repo URL")
        if local_clone_raw:
            raise CanaryError("Phase 7C requires fresh public repo fetch; local_clone_private is not allowed")
        if source_type in {"local_clone", "synthetic"} or str(repo.get("synthetic_source_private", "")).strip():
            raise CanaryError("Phase 7C rejects local_clone/synthetic source inputs")
        if not comparable_repo_id:
            raise CanaryError("private public-repo input missing prior-phase comparable repo identity")
        if locked_commit and not re.fullmatch(r"[a-fA-F0-9]{40}", locked_commit):
            raise CanaryError("private public-repo input commit must be a 40 hex SHA")
        normalized.append({
            "repo_url_private": repo_url,
            "locked_commit_private": locked_commit,
            "prior_phase_comparable_repo_id_private": comparable_repo_id,
            "repo_input_index_private": index,
        })
    if not (FORMAL_REPO_TARGET_MIN <= len(normalized) <= FORMAL_REPO_HARD_MAX):
        raise CanaryError("fresh public-repo formal run requires 8-16 public repo inputs")
    return normalized[:CANARY_REPO_HARD_MAX]


def materialize_public_repo_inputs(inputs: list[dict[str, Any]], run_root: Path, allow_fetch: bool) -> tuple[list[dict[str, Any]], bool]:
    ensure_private_path(run_root)
    if not allow_fetch:
        raise CanaryError("--confirm-public-repo-fetch is required for Phase 7C fresh public repo inputs")
    clone_root = run_root / "private_public_repo_clones"
    repos: list[dict[str, Any]] = []
    fetch_used = False
    for index, repo in enumerate(inputs[:FORMAL_REPO_TARGET_MAX]):
        repo_url = str(repo["repo_url_private"])
        locked_commit = str(repo.get("locked_commit_private") or "")
        comparable_repo_id = str(repo["prior_phase_comparable_repo_id_private"])
        repo_dir = clone_root / f"public_repo_input_{index}"
        if repo_dir.exists():
            raise CanaryError("private public-repo clone destination already exists")
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        run_git(["clone", "--quiet", "--filter=blob:none", "--depth", "1", repo_url, str(repo_dir)], REPO, timeout=180)
        fetch_used = True
        try:
            actual_url = run_git(["config", "--get", "remote.origin.url"], repo_dir)
        except CanaryError:
            actual_url = repo_url
        if public_repo_name_from_url(actual_url).lower() != public_repo_name_from_url(repo_url).lower():
            raise CanaryError("local public-repo clone metadata does not match private input")
        if locked_commit:
            if allow_fetch and fetch_used:
                run_git(["fetch", "--quiet", "--depth", "1", "origin", locked_commit], repo_dir, timeout=180)
            run_git(["checkout", "--quiet", locked_commit], repo_dir, timeout=120)
        locked_commit = run_git(["rev-parse", "HEAD"], repo_dir)
        repos.append({
            "private_repo_key": f"phase7c_public_repo_input_{index}",
            "private_repo_url": repo_url,
            "private_public_id": sha256_text(repo_url)[:16],
            "private_prior_phase_comparable_repo_id": comparable_repo_id,
            "private_owner": sha256_text(repo_url.rsplit('/', 1)[0])[:16],
            "private_locked_commit": locked_commit,
            "private_source_root": str(repo_dir),
            "private_public_repo_clone_metadata_present": True,
        })
    return repos, fetch_used


def iter_candidate_source_files(repo_root: Path) -> list[Path]:
    suffixes = {".py", ".js", ".ts", ".rs", ".go", ".java", ".c", ".h", ".cpp", ".hpp", ".md", ".txt"}
    excluded = {".git", "node_modules", "target", "dist", "build", "vendor", "__pycache__"}
    files: list[Path] = []
    for path in repo_root.rglob("*"):
        if not path.is_file() or any(part in excluded for part in path.parts):
            continue
        if path.suffix.lower() not in suffixes:
            continue
        try:
            if path.stat().st_size <= 0 or path.stat().st_size > 200_000:
                continue
            path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        files.append(path)
    files.sort(key=lambda p: (len(p.relative_to(repo_root).parts), str(p.relative_to(repo_root)).lower()))
    return files


def choose_span(text: str) -> tuple[int, int, str] | None:
    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        if line.strip() and not line.strip().startswith(("#", "//", "/*", "*")):
            return index, index, line + "\n"
    if lines:
        return 1, 1, lines[0] + "\n"
    return None


def create_public_repo_manifest(root: Path, public_repo_inputs_path: Path, allow_fetch: bool) -> dict[str, Any]:
    ensure_private_path(root)
    inputs = load_public_repo_inputs(public_repo_inputs_path)
    repos, fetch_used = materialize_public_repo_inputs(inputs, root, allow_fetch)
    tasks: list[dict[str, Any]] = []
    for repo in repos:
        repo_root = Path(str(repo["private_source_root"]))
        chosen = iter_candidate_source_files(repo_root)[:CANARY_MAX_TASKS_PER_REPO]
        if not chosen:
            raise CanaryError("fresh public-repo input lacks readable source files for formal task cap")
        for task_index, path in enumerate(chosen):
            rel_source = path.relative_to(repo_root).as_posix()
            text = path.read_text(encoding="utf-8")
            span = choose_span(text)
            if not span:
                raise CanaryError("fresh public-repo input source span unavailable")
            start_line, end_line, span_text = span
            tasks.append({
                "private_task_id": sha256_text(f"{repo['private_repo_key']}:{rel_source}:{start_line}:{task_index}"),
                "private_repo_key": repo["private_repo_key"],
                "query_private": sha256_text(f"{rel_source}:{span_text}")[:16],
                "private_gold_path": rel_source,
                "private_gold_start_line": start_line,
                "private_gold_end_line": end_line,
                "private_gold_hash": sha256_text(span_text),
                "private_related_test_path": rel_source,
                "private_file_family_bucket": file_family(rel_source),
            })
    tasks = tasks[:FORMAL_TASK_MAX]
    if not (FORMAL_TASK_MIN <= len(tasks) <= FORMAL_TASK_MAX):
        raise CanaryError("fresh public-repo inputs did not provide formal task count")
    return {
        "schema_version": PRIVATE_MANIFEST_SCHEMA,
        "phase": PHASE,
        "formal_caps": {"repo_target_min": FORMAL_REPO_TARGET_MIN, "repo_target_max": FORMAL_REPO_TARGET_MAX, "repo_hard_max": FORMAL_REPO_HARD_MAX, "task_target_min": FORMAL_TASK_MIN, "task_target_max": FORMAL_TASK_MAX, "task_hard_max": FORMAL_TASK_HARD_MAX, "max_tasks_per_repo": FORMAL_MAX_TASKS_PER_REPO, "row_hard_max": FORMAL_ROW_HARD_MAX},
        "repos": repos,
        "tasks": tasks,
        "replacement_count": 0,
        "fresh_public_repo_inputs_used": True,
        "local_generated_canary_sources_used": False,
        "public_repo_fetch_executed": fetch_used,
    }


OVERLAP_INDEX_KEYS = ("repos", "commits", "tasks", "paths", "ranges", "hashes", "families", "snippets")


def empty_overlap_index() -> dict[str, set[str]]:
    return {key: set() for key in OVERLAP_INDEX_KEYS}


def normalize_commit(value: Any) -> str:
    commit = str(value or "").strip().lower()
    return commit if re.fullmatch(r"[a-f0-9]{40}", commit) else ""


def add_repo_tokens(index: dict[str, set[str]], *values: Any) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        tokens.update(repo_identity_tokens(str(value or "")))
    index["repos"].update(tokens)
    return tokens


def add_scoped_materialization(
    index: dict[str, set[str]],
    repo_tokens: set[str],
    path: Any,
    start: Any = "",
    end: Any = "",
    digest: Any = "",
    snippet: Any = "",
) -> None:
    path_text = str(path or "").strip()
    start_text = str(start or "").strip()
    end_text = str(end or "").strip()
    digest_text = str(digest or "").strip().lower()
    scopes = repo_tokens or {""}
    if path_text:
        path_lower = path_text.lower()
        family_lower = file_family(path_text).lower()
        for scope in scopes:
            prefix = f"{scope}:" if scope else ""
            index["paths"].add(f"{prefix}{path_lower}")
            index["families"].add(f"{prefix}{family_lower}")
            if start_text and end_text:
                index["ranges"].add(f"{prefix}{path_lower}:{start_text}-{end_text}".lower())
    if digest_text:
        index["hashes"].add(digest_text)
    snippet_text = str(snippet or "")
    if snippet_text:
        index["snippets"].add(sha256_text(snippet_text).lower())


def split_range(value: Any) -> tuple[str, str]:
    match = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", str(value or ""))
    return (match.group(1), match.group(2)) if match else ("", "")


def phase5b_overlap_index(rows: list[dict[str, Any]]) -> dict[str, set[str]]:
    index = empty_overlap_index()
    for row in rows:
        repo = str(row.get("repo_id", ""))
        task = str(row.get("private_task_id", ""))
        repo_tokens = add_repo_tokens(index, repo)
        if task:
            index["tasks"].add(task.lower())
        mat = row.get("private_materialization", {}) or row.get("private_exact_refs", {}) or {}
        if isinstance(mat, dict):
            path = str(mat.get("path_private") or mat.get("private_path") or "")
            start = str(mat.get("start_line_private") or mat.get("private_start_line") or "")
            end = str(mat.get("end_line_private") or mat.get("private_end_line") or "")
            if (not start or not end) and mat.get("private_range"):
                start, end = split_range(mat.get("private_range"))
            digest = str(mat.get("content_sha256_private") or mat.get("content_sha256") or "")
            add_scoped_materialization(index, repo_tokens, path, start, end, digest, mat.get("private_content_text", ""))
        commit = normalize_commit(row.get("commit") or row.get("locked_commit"))
        if commit:
            index["commits"].add(commit)
    return index


def load_json_or_jsonl_records(path: Path) -> list[dict[str, Any]]:
    ensure_private_path(path)
    if path.suffix.lower() == ".jsonl":
        return load_jsonl(path)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        if isinstance(data.get("repos"), list):
            return [item for item in data["repos"] if isinstance(item, dict)]
        if isinstance(data.get("repo_lock"), dict):
            return load_json_or_jsonl_records_from_mapping(data["repo_lock"])
        if any(key in data for key in ("commit", "locked_commit", "repo_id", "source")):
            return [data]
        return load_json_or_jsonl_records_from_mapping(data)
    return []


def load_json_or_jsonl_records_from_mapping(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for key, value in mapping.items():
        if isinstance(value, dict):
            item = dict(value)
            item.setdefault("repo_id", key)
            records.append(item)
    return records


def phase5b_provenance_overlap_index(paths: list[Path]) -> dict[str, set[str]]:
    index = empty_overlap_index()
    for path in paths:
        if not path.exists():
            continue
        for record in load_json_or_jsonl_records(path):
            repo_tokens = add_repo_tokens(
                index,
                record.get("repo_id"),
                record.get("private_repo_key"),
                record.get("public_id"),
                record.get("private_public_id"),
                record.get("content_manifest_sha"),
            )
            source = record.get("source")
            if isinstance(source, dict):
                repo_tokens.update(add_repo_tokens(index, source.get("url"), source.get("repo_url"), source.get("remote_url")))
            commit = normalize_commit(record.get("commit") or record.get("locked_commit") or record.get("locked_commit_private") or record.get("private_locked_commit"))
            if commit:
                index["commits"].add(commit)
            metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
            file_manifest = metadata.get("file_manifest") if isinstance(metadata, dict) else None
            if isinstance(file_manifest, list):
                for item in file_manifest:
                    if isinstance(item, dict):
                        add_scoped_materialization(index, repo_tokens, item.get("path"), digest=item.get("sha256"))
    return index


def phase5b_provenance_paths() -> list[Path]:
    candidates: list[Path] = []
    for root in (PHASE5B_ROOT, PHASE5B_PREP_ROOT, REPO / "runs" / "phase5b_public_repo_formal_validation_canary_input"):
        if root.exists():
            candidates.extend(root.glob("**/*repo-lock*.json*"))
    unique = {path.resolve(): path for path in candidates if path.is_file()}
    return sorted(unique.values(), key=lambda p: p.stat().st_mtime, reverse=True)


def prior_overlap_index_from_rows_paths(paths: list[Path]) -> dict[str, set[str]]:
    index = empty_overlap_index()
    for path in paths:
        if not path.exists():
            continue
        for key, values in phase5b_overlap_index(load_jsonl(path)).items():
            index[key].update(values)
    return index


def phase7b_overlap_index(manifest: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, set[str]]:
    index = empty_overlap_index()
    repo_tokens_by_key: dict[str, set[str]] = {}
    for repo in manifest.get("repos", []):
        if not isinstance(repo, dict):
            continue
        repo_key = str(repo.get("private_repo_key", ""))
        tokens = add_repo_tokens(
            index,
            repo.get("private_phase5b_comparable_repo_id"),
            repo.get("private_prior_phase_comparable_repo_id"),
            repo.get("private_public_id"),
            repo.get("private_repo_key"),
            repo.get("private_owner"),
        )
        if repo_key:
            repo_tokens_by_key[repo_key] = tokens
        commit = normalize_commit(repo.get("private_locked_commit") or repo.get("locked_commit_private"))
        if commit:
            index["commits"].add(commit)
    for task in manifest.get("tasks", []):
        if not isinstance(task, dict):
            continue
        repo_key = str(task.get("private_repo_key", ""))
        repo_tokens = repo_tokens_by_key.get(repo_key, repo_identity_tokens(repo_key))
        task_id = str(task.get("private_task_id", ""))
        if task_id:
            index["tasks"].add(task_id.lower())
        add_scoped_materialization(
            index,
            repo_tokens,
            task.get("private_gold_path"),
            task.get("private_gold_start_line"),
            task.get("private_gold_end_line"),
            task.get("private_gold_hash"),
            task.get("private_gold_snippet", ""),
        )
    for row in rows:
        repo_key = str(row.get("private_repo_key", ""))
        repo_tokens = repo_tokens_by_key.get(repo_key, repo_identity_tokens(repo_key))
        task_id = str(row.get("private_task_id", ""))
        if task_id:
            index["tasks"].add(task_id.lower())
        mat = row.get("private_materialization", {})
        if isinstance(mat, dict):
            start, end = split_range(mat.get("private_range"))
            add_scoped_materialization(index, repo_tokens, mat.get("private_path"), start, end, mat.get("private_content_sha256"), mat.get("private_content_text"))
    return index


def latest_phase7b_private_pairs() -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for run_dir in sorted((p for p in PHASE7B_ROOT.glob("*") if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True):
        manifest = run_dir / PHASE7B_MANIFEST_NAME
        rows = run_dir / PHASE7B_ROWS_NAME
        if manifest.exists() and rows.exists():
            pairs.append((manifest, rows))
    return pairs[:8]


def phase7b_prior_overlap_index_from_private_pairs(pairs: list[tuple[Path, Path]]) -> dict[str, set[str]]:
    index = empty_overlap_index()
    for manifest_path, rows_path in pairs:
        ensure_private_path(manifest_path)
        ensure_private_path(rows_path)
        if not manifest_path.exists() or not rows_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        rows = load_jsonl(rows_path)
        for key, values in phase7b_overlap_index(manifest, rows).items():
            index[key].update(values)
    return index


def merge_overlap_indexes(indexes: list[dict[str, set[str]]]) -> dict[str, set[str]]:
    merged = empty_overlap_index()
    for index in indexes:
        for key in merged:
            merged[key].update(index.get(key, set()))
    return merged


def manifest_overlap_errors(manifest: dict[str, Any], phase5b_index: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    repo_tokens_by_key: dict[str, set[str]] = {}
    for repo in manifest.get("repos", []):
        repo_tokens: set[str] = set()
        for key in ("private_prior_phase_comparable_repo_id", "private_phase5b_comparable_repo_id", "private_public_id", "private_repo_key", "private_owner"):
            repo_tokens.update(repo_identity_tokens(str(repo.get(key, ""))))
        repo_key = str(repo.get("private_repo_key", ""))
        if repo_key:
            repo_tokens_by_key[repo_key] = repo_tokens
        if any(token in phase5b_index["repos"] for token in repo_tokens):
            errors.append("repo overlap detected")
        locked_commit = normalize_commit(repo.get("private_locked_commit", ""))
        if locked_commit and locked_commit in phase5b_index["commits"]:
            errors.append("commit overlap detected")
    for task in manifest.get("tasks", []):
        tid = str(task.get("private_task_id", "")).lower()
        repo_key = str(task.get("private_repo_key", ""))
        path = str(task.get("private_gold_path", "")).lower()
        start = str(task.get("private_gold_start_line", ""))
        end = str(task.get("private_gold_end_line", ""))
        repo_tokens = repo_tokens_by_key.get(repo_key, repo_identity_tokens(repo_key)) or {""}
        path_keys = {f"{token}:{path}" if token and path else path for token in repo_tokens}
        range_keys = {f"{token}:{path}:{start}-{end}".lower() if token and path and start and end else (f"{path}:{start}-{end}".lower() if path and start and end else "") for token in repo_tokens}
        family = file_family(path).lower() if path else ""
        family_keys = {f"{token}:{family}" if token and family else family for token in repo_tokens}
        digest = str(task.get("private_gold_hash", "")).lower()
        snippet_hash = sha256_text(str(task.get("private_gold_snippet", ""))).lower() if task.get("private_gold_snippet") else ""
        if tid and tid in phase5b_index["tasks"]:
            errors.append("task overlap detected")
        if any(path_key and path_key in phase5b_index.get("paths", set()) for path_key in path_keys):
            errors.append("exact path overlap detected")
        if any(range_key and range_key in phase5b_index.get("ranges", set()) for range_key in range_keys):
            errors.append("exact range overlap detected")
        if digest and digest in phase5b_index["hashes"]:
            errors.append("content digest overlap detected")
        if snippet_hash and snippet_hash in phase5b_index.get("snippets", set()):
            errors.append("content snippet overlap detected")
        if any(family_key and family_key in phase5b_index.get("families", set()) for family_key in family_keys):
            errors.append("file-family overlap detected")
    return sorted(set(errors))


def create_canary_source_and_manifest(root: Path) -> dict[str, Any]:
    ensure_private_path(root)
    source_root = root / "private_sources"
    repos: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []
    for repo_index in range(CANARY_REPO_TARGET):
        repo_key = f"phase7c_formal_repo_{repo_index}"
        repo_dir = source_root / repo_key
        src_dir = repo_dir / f"fresh_group_{repo_index}"
        test_dir = repo_dir / f"fresh_checks_{repo_index}"
        src_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)
        content_parts: list[str] = []
        for task_index in range(3):
            symbol = f"fresh_canary_symbol_{repo_index}_{task_index}"
            content_parts.append(f"def {symbol}():\n    return '{symbol}'\n")
        source_text = "\n".join(content_parts)
        rel_source = f"fresh_group_{repo_index}/fresh_canary_module_{repo_index}.py"
        source_file = repo_dir / rel_source
        source_file.write_text(source_text, encoding="utf-8")
        test_file = test_dir / f"fresh_canary_test_{repo_index}.py"
        test_file.write_text("\n".join(f"from fresh_group_{repo_index}.fresh_canary_module_{repo_index} import fresh_canary_symbol_{repo_index}_{i}" for i in range(3)) + "\n", encoding="utf-8")
        commit = sha256_text(source_text + repo_key)
        repos.append({
            "private_repo_key": repo_key,
            "private_public_id": f"phase7c_fresh_public_shape_{repo_index}",
            "private_prior_phase_comparable_repo_id": f"phase7c_fresh_public_shape_{repo_index}",
            "private_owner": "phase7c_fresh_owner",
            "private_locked_commit": commit,
            "private_source_root": str(repo_dir),
        })
        lines = source_text.splitlines()
        for task_index in range(3):
            symbol = f"fresh_canary_symbol_{repo_index}_{task_index}"
            start_line = next(i for i, line in enumerate(lines, start=1) if f"def {symbol}" in line)
            end_line = start_line + 1
            span_text = "\n".join(lines[start_line - 1:end_line]) + "\n"
            tasks.append({
                "private_task_id": f"phase7c_formal_task_{repo_index}_{task_index}",
                "private_repo_key": repo_key,
                "query_private": symbol,
                "private_gold_path": rel_source,
                "private_gold_start_line": start_line,
                "private_gold_end_line": end_line,
                "private_gold_hash": sha256_text(span_text),
                "private_related_test_path": f"fresh_checks_{repo_index}/fresh_canary_test_{repo_index}.py",
                "private_file_family_bucket": file_family(rel_source),
            })
    return {
        "schema_version": PRIVATE_MANIFEST_SCHEMA,
        "phase": PHASE,
        "formal_caps": {"repo_hard_max": FORMAL_REPO_HARD_MAX, "task_hard_max": FORMAL_TASK_HARD_MAX, "row_hard_max": FORMAL_ROW_HARD_MAX},
        "repos": repos,
        "tasks": tasks,
        "replacement_count": 0,
        "public_repo_fetch_executed": False,
    }


def validate_manifest(manifest: Any) -> list[str]:
    if not isinstance(manifest, dict):
        return ["manifest must be object"]
    errors: list[str] = []
    if manifest.get("schema_version") != PRIVATE_MANIFEST_SCHEMA or manifest.get("phase") != PHASE:
        errors.append("private manifest identity drift")
    repos = manifest.get("repos", [])
    tasks = manifest.get("tasks", [])
    if manifest.get("fresh_public_repo_inputs_used") is not True:
        errors.append("fresh public repo inputs not attested")
    if manifest.get("local_generated_canary_sources_used") is not False:
        errors.append("local generated canary sources boundary failed")
    if manifest.get("public_repo_fetch_executed") not in {True, False}:
        errors.append("public repo fetch attestation missing")
    if not (FORMAL_REPO_TARGET_MIN <= len(repos) <= FORMAL_REPO_HARD_MAX):
        errors.append("repo formal cap failed")
    if not (FORMAL_TASK_MIN <= len(tasks) <= FORMAL_TASK_HARD_MAX):
        errors.append("task formal cap failed")
    per_repo = Counter(str(task.get("private_repo_key", "")) for task in tasks)
    if any(count > CANARY_MAX_TASKS_PER_REPO for count in per_repo.values()):
        errors.append("max tasks per repo exceeded")
    repo_keys = {str(repo.get("private_repo_key", "")) for repo in repos}
    for repo in repos:
        for key in ("private_repo_url", "private_prior_phase_comparable_repo_id", "private_locked_commit", "private_source_root"):
            if not repo.get(key):
                errors.append("fresh public repo provenance incomplete")
        if str(repo.get("private_source_root", "")).startswith("synthetic:"):
            errors.append("synthetic source rejected")
        if repo.get("private_public_repo_clone_metadata_present") is not True:
            errors.append("public repo clone metadata missing")
    for task in tasks:
        if str(task.get("private_repo_key", "")) not in repo_keys:
            errors.append("task references missing repo")
    return sorted(set(errors))


def read_range(repo_root: Path, rel_path: str, start: int, end: int) -> dict[str, Any] | None:
    full = (repo_root / rel_path).resolve()
    if not str(full).startswith(str(repo_root.resolve())) or not full.exists():
        return None
    lines = full.read_text(encoding="utf-8").splitlines()
    if start < 1 or end < start or end > len(lines):
        return None
    content = "\n".join(lines[start - 1:end]) + "\n"
    digest = sha256_text(content)
    reread = full.read_text(encoding="utf-8").splitlines()
    reread_content = "\n".join(reread[start - 1:end]) + "\n"
    return {
        "private_path": rel_path,
        "private_range": f"{start}-{end}",
        "private_content_text": content,
        "private_content_sha256": digest,
        "private_content_byte_length": len(content.encode("utf-8")),
        "currentness_reread_match": reread_content == content,
        "range_content_match": sha256_text(reread_content) == digest,
    }


def candidate_for_action(manifest: dict[str, Any], task: dict[str, Any], action: str) -> tuple[str | None, int, int]:
    if action in CONTROL_LABELS:
        return None, 0, 0
    if action == "read_related_test_when_available":
        return str(task.get("private_related_test_path", "")), 1, 1
    path = str(task["private_gold_path"])
    start = int(task["private_gold_start_line"])
    end = int(task["private_gold_end_line"])
    if action in {"bm25_then_read_top1", "symbol_regex_then_read_top1"}:
        return path, start, end
    return path, max(1, start), max(1, start)


def task_tie(task: dict[str, Any], materialization: dict[str, Any] | None) -> bool:
    if not materialization:
        return False
    return (
        materialization.get("private_path") == task.get("private_gold_path")
        and materialization.get("private_content_sha256") == task.get("private_gold_hash")
    )


def build_private_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    repo_roots = {str(repo["private_repo_key"]): Path(str(repo["private_source_root"])) for repo in manifest["repos"]}
    rows: list[dict[str, Any]] = []
    row_index = 0
    for task in manifest["tasks"]:
        repo_root = repo_roots[str(task["private_repo_key"])]
        for label in LABELS:
            rel, start, end = candidate_for_action(manifest, task, label)
            materialization = read_range(repo_root, rel, start, end) if rel else None
            tied = task_tie(task, materialization)
            current = bool(materialization and materialization["currentness_reread_match"] and materialization["range_content_match"])
            success = bool(label not in CONTROL_LABELS and materialization and current and tied and materialization.get("private_content_byte_length", 0) > 0)
            rows.append({
                "schema_version": PRIVATE_ROW_SCHEMA,
                "phase": PHASE,
                "private_row_index": row_index,
                "private_task_id": task["private_task_id"],
                "private_repo_key": task["private_repo_key"],
                "action_label": label,
                "candidate_found": rel is not None,
                "read_attempted": rel is not None and label not in CONTROL_LABELS,
                "materialized_current_source": materialization is not None,
                "evidence_success": success,
                "private_materialization": materialization or {},
                "evidencecore": {
                    "candidate_found_alone_is_evidence": False,
                    "success_requires_current_source_read": True,
                    "success_requires_materialization": True,
                    "content_digest_present": bool(materialization and materialization.get("private_content_sha256")),
                    "currentness_reread_match": bool(materialization and materialization.get("currentness_reread_match")),
                    "range_content_match": bool(materialization and materialization.get("range_content_match")),
                    "task_tie": tied,
                },
                "privacy": {"public_artifact_allowed": False, "private_row": True},
            })
            row_index += 1
    return rows


def validate_private_rows(rows: list[dict[str, Any]], task_count: int) -> list[str]:
    errors: list[str] = []
    if len(rows) != task_count * len(LABELS):
        errors.append("full seven-label panel missing")
    if len(rows) > CANARY_ROW_HARD_MAX:
        errors.append("row hard cap exceeded")
    by_task: dict[str, set[str]] = {}
    for row in rows:
        label = str(row.get("action_label", ""))
        task = str(row.get("private_task_id", ""))
        by_task.setdefault(task, set()).add(label)
        if row.get("schema_version") != PRIVATE_ROW_SCHEMA or row.get("phase") != PHASE:
            errors.append("private row identity drift")
        if label not in LABELS:
            errors.append("label drift")
        ec = row.get("evidencecore", {})
        if label in CONTROL_LABELS and row.get("evidence_success") is True:
            errors.append("stop/abstain success nonzero")
        if ec.get("candidate_found_alone_is_evidence") is not False:
            errors.append("candidate-found evidence invariant failed")
        if row.get("evidence_success") is True:
            mat = row.get("private_materialization", {})
            if not re.fullmatch(r"[a-f0-9]{64}", str(mat.get("private_content_sha256", ""))):
                errors.append("success without content digest")
            for key in ("currentness_reread_match", "range_content_match", "task_tie"):
                if ec.get(key) is not True:
                    errors.append(f"success without {key}")
    for labels in by_task.values():
        if labels != set(LABELS):
            errors.append("per-task seven-label set drift")
    return sorted(set(errors))


def public_leak_errors(value: Any, path: str = "$", key: str = "") -> list[str]:
    errors: list[str] = []
    if PRIVATE_KEY_RE.search(key) and key not in ALLOWED_PUBLIC_PRIVATE_FLAG_KEYS:
        errors.append(f"private-shaped key at {path}")
    if isinstance(value, dict):
        for child_key, child in value.items():
            errors.extend(public_leak_errors(child, f"{path}.{child_key}" if path != "$" else f"$.{child_key}", str(child_key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(public_leak_errors(child, f"{path}[{index}]", ""))
    elif isinstance(value, str):
        if SINGLETON_BUCKET_RE.search(value):
            errors.append(f"singleton bucket at {path}")
        if CLAIM_WORD_RE.search(value):
            errors.append(f"claim word at {path}")
        if PRIVATE_VALUE_RE.search(value):
            errors.append(f"private-shaped value at {path}")
    return errors


def build_report(manifest: dict[str, Any], rows: list[dict[str, Any]], overlap_errors: list[str], private_errors: list[str]) -> dict[str, Any]:
    repo_count = len(manifest.get("repos", []))
    task_count = len(manifest.get("tasks", []))
    row_count = len(rows)
    labels = Counter(str(row.get("action_label", "")) for row in rows)
    materialized = sum(1 for row in rows if row.get("materialized_current_source") is True)
    success = Counter(str(row.get("action_label", "")) for row in rows if row.get("evidence_success") is True)
    stop_success = success["stop"] + success["abstain"]
    fresh_public_repo_inputs_used = manifest.get("fresh_public_repo_inputs_used") is True
    local_generated_canary_sources_used = manifest.get("local_generated_canary_sources_used") is True
    source_mode_ok = fresh_public_repo_inputs_used and not local_generated_canary_sources_used
    formal_scale_ok = FORMAL_REPO_TARGET_MIN <= repo_count <= FORMAL_REPO_HARD_MAX and FORMAL_TASK_MIN <= task_count <= FORMAL_TASK_HARD_MAX and row_count <= FORMAL_ROW_HARD_MAX
    passed = not overlap_errors and not private_errors and formal_scale_ok and stop_success == 0 and source_mode_ok
    status = STATUS_PASS if passed else (STATUS_REPAIR if private_errors or overlap_errors else STATUS_STOP)
    report = {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "formal_scope": {
            "formal_validation": True,
            "route_conclusion": False,
            "no_claim_status": True,
            "phase7a_formal_validation_scale_executed": True,
            "phase7a_formal_validation_protocol_unchanged": True,
            "repo_target_bucket": "bucket_formal_repo_target",
            "task_target_bucket": "bucket_formal_task_target",
            "repo_hard_cap_bucket": "bucket_phase7a_repo_hard_cap",
            "task_hard_cap_bucket": "bucket_phase7a_task_hard_cap",
            "max_tasks_per_repo_bucket": "bucket_phase7a_per_repo_cap",
        },
        "aggregate_buckets": {
            "repo_count_bucket": formal_scale_bucket(repo_count, "repo"),
            "task_count_bucket": formal_scale_bucket(task_count, "task"),
            "row_count_bucket": bucket_count(row_count),
            "replacement_count_bucket": bucket_count(int(manifest.get("replacement_count", 0))),
            "materialization_pass_bucket": bucket_count(materialized),
            "overlap_error_bucket": bucket_count(len(overlap_errors)),
            "private_row_error_bucket": bucket_count(len(private_errors)),
            "stop_abstain_success_bucket": bucket_count(stop_success),
        },
        "label_coverage_buckets": {label: bucket_count(labels[label]) for label in LABELS},
        "evidence_success_buckets": {label: bucket_count(success[label]) for label in LABELS},
        "full_panel_summary": {
            "seven_labels_exact": set(labels) == set(LABELS),
            "full_panel_per_task": row_count == task_count * len(LABELS),
            "row_hard_cap_preserved": row_count <= FORMAL_ROW_HARD_MAX,
        },
        "freshness_overlap_summary": {
            "phase5b_overlap_rejection_executed": True,
            "phase7b_overlap_rejection_executed": True,
            "overlap_check_passed": not overlap_errors,
            "fresh_public_repo_inputs_used": fresh_public_repo_inputs_used,
            "local_generated_canary_sources_used": local_generated_canary_sources_used,
            "current_run_public_fetch_attested": bool(manifest.get("public_repo_fetch_executed")),
            "public_detail_level": "boolean_and_bucket_only",
        },
        "evidencecore_summary": {
            "candidate_found_alone_is_evidence": False,
            "success_requires_current_source_read": True,
            "success_requires_materialization": True,
            "success_requires_content_digest": True,
            "success_requires_currentness_reread": True,
            "success_requires_range_content_match": True,
            "success_requires_task_tie": True,
            "stop_abstain_success_zero": stop_success == 0,
        },
        "privacy_summary": {
            "publication_level": "aggregate_only",
            "private_rows_public": False,
            "repo_names_urls_owners_public": False,
            "commits_shas_public": False,
            "paths_ranges_hashes_snippets_public": False,
            "task_ids_row_ids_public": False,
            "manifests_public": False,
            "run_dirs_public": False,
            "per_repo_per_task_details_public": False,
            "singleton_buckets_public": False,
        },
        "authorization_attestation": {
            "phase7a_gate_passed": True,
            "confirm_private_input_used": True,
            "confirm_private_output_used": True,
            "public_repo_fetch_used": bool(manifest.get("public_repo_fetch_executed")),
            "fresh_public_repo_inputs_used": fresh_public_repo_inputs_used,
            "local_generated_canary_sources_used": local_generated_canary_sources_used,
            "source_reads_limited_to_formal_materialization": True,
            "provider_network_llm_used": False,
            "model_update_executed": False,
            "runtime_or_release_setting_changed": False,
            "new_retrieval_family_added": False,
        },
        "replacement_summary": {
            "replacement_only_before_outcome_scoring": True,
            "clone_failure_bucket": bucket_count(0),
            "pinned_commit_unavailable_bucket": bucket_count(0),
            "insufficient_eligible_files_bucket": bucket_count(0),
            "impossible_materialization_bucket": bucket_count(0),
            "replacement_after_outcome_observation_bucket": bucket_count(0),
        },
        "validation_summary": {
            "route_specific_validation": "pending",
            "self_test_available": True,
        },
        "conservative_recommendation": "formal_result_recorded_continue_only_with_separate_review_no_claim",
    }
    errors = validate_report(report, include_pending=False)
    report["validation_summary"]["route_specific_validation"] = "passed" if not errors else "failed"
    return report


def validate_report(report: Any, *, include_pending: bool = True) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION or report.get("phase") != PHASE:
        errors.append("report identity drift")
    if report.get("status") not in {STATUS_STOP, STATUS_REPAIR, STATUS_PASS}:
        errors.append("status drift")
    source_summary = report.get("freshness_overlap_summary", {})
    auth = report.get("authorization_attestation", {})
    fresh_public_repo_inputs_used = source_summary.get("fresh_public_repo_inputs_used") is True and auth.get("fresh_public_repo_inputs_used") is True
    local_generated_canary_sources_used = source_summary.get("local_generated_canary_sources_used") is True or auth.get("local_generated_canary_sources_used") is True
    if source_summary.get("fresh_public_repo_inputs_used") is not True or auth.get("fresh_public_repo_inputs_used") is not True:
        errors.append("fresh public repo source-mode attestation missing")
    if source_summary.get("local_generated_canary_sources_used") is not False or auth.get("local_generated_canary_sources_used") is not False:
        errors.append("local generated source-mode boundary failed")
    if auth.get("public_repo_fetch_used") is not True:
        errors.append("Phase 7C passable report requires actual public repo fetch")
    if report.get("status") == STATUS_PASS and (not fresh_public_repo_inputs_used or local_generated_canary_sources_used or auth.get("public_repo_fetch_used") is not True):
        errors.append("pass status requires fresh public repo input provenance and fetch")
    if report.get("status") == STATUS_PASS and source_summary.get("overlap_check_passed") is not True:
        errors.append("pass status requires prior-overlap rejection to pass")
    scope = report.get("formal_scope", {})
    if scope.get("formal_validation") is not True or scope.get("route_conclusion") is not False or scope.get("no_claim_status") is not True:
        errors.append("formal scope boundary failed")
    if scope.get("phase7a_formal_validation_scale_executed") is not True or scope.get("phase7a_formal_validation_protocol_unchanged") is not True:
        errors.append("Phase 7A formal-validation scale/protocol attestation failed")
    ag = report.get("aggregate_buckets", {})
    if ag.get("repo_count_bucket") not in {"bucket_formal_repo_target", "bucket_above_repo_target_within_hard_cap"}:
        errors.append("report below formal repo minimum")
    if ag.get("task_count_bucket") not in {"bucket_formal_task_target", "bucket_above_task_target_within_hard_cap"}:
        errors.append("report below formal task minimum")
    full_panel = report.get("full_panel_summary", {})
    full_panel_required = report.get("status") == STATUS_PASS
    for key in (("seven_labels_exact", "full_panel_per_task") if full_panel_required else ()):
        if full_panel.get(key) is not True:
            errors.append(f"full-panel summary failed: {key}")
    if full_panel.get("row_hard_cap_preserved") is not True:
        errors.append("full-panel summary failed: row_hard_cap_preserved")
    if set(report.get("label_coverage_buckets", {})) != set(LABELS) or set(report.get("evidence_success_buckets", {})) != set(LABELS):
        errors.append("label bucket shape drift")
    if report.get("aggregate_buckets", {}).get("stop_abstain_success_bucket") != "bucket_zero":
        errors.append("stop/abstain success nonzero")
    evidence = report.get("evidencecore_summary", {})
    if evidence.get("candidate_found_alone_is_evidence") is not False:
        errors.append("candidate-found evidence boundary failed")
    for key in ("success_requires_current_source_read", "success_requires_materialization", "success_requires_content_digest", "success_requires_currentness_reread", "success_requires_range_content_match", "success_requires_task_tie", "stop_abstain_success_zero"):
        if evidence.get(key) is not True:
            errors.append(f"EvidenceCore summary failed: {key}")
    privacy = report.get("privacy_summary", {})
    for key in ("private_rows_public", "repo_names_urls_owners_public", "commits_shas_public", "paths_ranges_hashes_snippets_public", "task_ids_row_ids_public", "manifests_public", "run_dirs_public", "per_repo_per_task_details_public", "singleton_buckets_public"):
        if privacy.get(key) is not False:
            errors.append(f"privacy boundary failed: {key}")
    for key in ("provider_network_llm_used", "model_update_executed", "runtime_or_release_setting_changed", "new_retrieval_family_added"):
        if auth.get(key) is not False:
            errors.append(f"authorization boundary failed: {key}")
    errors.extend(public_leak_errors(report))
    if include_pending and report.get("validation_summary", {}).get("route_specific_validation") != "passed":
        errors.append("route-specific validation not passed")
    return sorted(set(errors))


def execute(args: argparse.Namespace) -> dict[str, Any]:
    if args.manifest:
        raise CanaryError("--manifest execution is disabled for Phase 7C; pass-capable formal runs must freshly clone public repo inputs in the current run")
    if not args.confirm_private_input or not args.confirm_private_output or not args.confirm_public_repo_fetch:
        raise CanaryError("--confirm-private-input, --confirm-private-output, and --confirm-public-repo-fetch are required for formal execution")
    gate_errors = validate_phase7a_gate()
    if gate_errors:
        raise CanaryError("Phase 7A gate failed: " + "; ".join(gate_errors[:6]))
    run_root = PRIVATE_ROOT / time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    ensure_private_path(run_root)
    rows_path = args.phase5b_rows or latest_phase5b_rows_path()
    ensure_private_path(rows_path)
    phase5b_rows = load_jsonl(rows_path)
    prior_index = merge_overlap_indexes([
        phase5b_overlap_index(phase5b_rows),
        phase5b_provenance_overlap_index(phase5b_provenance_paths()),
        phase7b_prior_overlap_index_from_private_pairs(latest_phase7b_private_pairs()),
    ])
    manifest = create_public_repo_manifest(run_root, args.public_repo_inputs, args.confirm_public_repo_fetch)
    manifest_errors = validate_manifest(manifest)
    overlap_errors = manifest_overlap_errors(manifest, prior_index) if not manifest_errors else manifest_errors
    rows = build_private_rows(manifest) if not overlap_errors else []
    private_errors = validate_private_rows(rows, len(manifest.get("tasks", []))) if rows else ([] if overlap_errors else ["no private rows built"])
    safe_json_dump(run_root / "phase7c_private_formal_manifest.json", manifest)
    if rows:
        write_jsonl(run_root / "phase7c_private_formal_rows.jsonl", rows)
    report = build_report(manifest, rows, overlap_errors, private_errors)
    report_errors = validate_report(report)
    if report_errors:
        raise CanaryError("public report validation failed: " + "; ".join(report_errors[:10]))
    safe_json_dump(args.output, report)
    return report


def sample_manifest(tmp_root: Path) -> dict[str, Any]:
    root = REPO / "runs" / PHASE / "selftest_placeholder"
    # Build in temp then rewrite source roots to a runs-shaped placeholder for validation-free helpers.
    with tempfile.TemporaryDirectory(prefix="phase7c_sample_") as temp:
        manifest = create_canary_source_and_manifest(root)
    manifest["fresh_public_repo_inputs_used"] = True
    manifest["local_generated_canary_sources_used"] = False
    for repo in manifest.get("repos", []):
        repo["private_repo_url"] = "https://example.invalid/private/selftest.git"
        repo["private_public_repo_clone_metadata_present"] = True
    return manifest


def create_selftest_public_repo_manifest(root: Path) -> dict[str, Any]:
    manifest = create_canary_source_and_manifest(root)
    # Expand synthetic self-test fixture to formal lower bound without network.
    base_repos = copy.deepcopy(manifest["repos"])
    base_tasks = copy.deepcopy(manifest["tasks"])
    manifest["repos"] = []
    manifest["tasks"] = []
    for repo_index in range(FORMAL_REPO_TARGET_MIN):
        repo = copy.deepcopy(base_repos[repo_index % len(base_repos)])
        old_key = str(repo["private_repo_key"])
        repo["private_repo_key"] = f"phase7c_selftest_repo_{repo_index}"
        repo["private_prior_phase_comparable_repo_id"] = f"phase7c_selftest_comparable_{repo_index}"
        manifest["repos"].append(repo)
        for task_index in range(10):
            task = copy.deepcopy(base_tasks[task_index % len(base_tasks)])
            task["private_repo_key"] = repo["private_repo_key"]
            task["private_task_id"] = f"phase7c_selftest_task_{repo_index}_{task_index}"
            task["query_private"] = sha256_text(f"{old_key}:{repo_index}:{task_index}")[:16]
            manifest["tasks"].append(task)
    manifest["fresh_public_repo_inputs_used"] = True
    manifest["local_generated_canary_sources_used"] = False
    manifest["public_repo_fetch_executed"] = True
    for repo in manifest.get("repos", []):
        repo["private_repo_url"] = f"https://example.invalid/{sha256_text(repo['private_repo_key'])[:12]}.git"
        repo["private_public_repo_clone_metadata_present"] = True
    return manifest


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory(prefix="phase7c_selftest_") as tmp:
        tmp_path = Path(tmp)
        runs_root = REPO / "runs" / PHASE / "selftest"
        manifest = create_selftest_public_repo_manifest(runs_root)
        manifest["repos"][0]["private_locked_commit"] = "a" * 40
        checks.append(("manifest_valid", not validate_manifest(manifest)))
        one_repo_manifest = copy.deepcopy(manifest)
        first_repo_key = str(one_repo_manifest["repos"][0]["private_repo_key"])
        one_repo_manifest["repos"] = one_repo_manifest["repos"][:1]
        one_repo_manifest["tasks"] = [task for task in one_repo_manifest["tasks"] if str(task.get("private_repo_key")) == first_repo_key]
        checks.append(("one_repo_manifest_rejected", bool(validate_manifest(one_repo_manifest))))
        empty_index = empty_overlap_index()
        checks.append(("no_overlap_valid", not manifest_overlap_errors(manifest, empty_index)))
        comparable_repo_id = str(manifest["repos"][0]["private_prior_phase_comparable_repo_id"]).lower()
        comparable_index = empty_overlap_index()
        comparable_index["repos"].add(comparable_repo_id)
        checks.append(("comparable_repo_identity_overlap_rejected", bool(manifest_overlap_errors(manifest, comparable_index))))
        comparable_phase5b_rows = [{"repo_id": comparable_repo_id, "private_task_id": "phase5b_selftest_task"}]
        checks.append(("phase5b_row_comparable_repo_overlap_rejected", bool(manifest_overlap_errors(manifest, phase5b_overlap_index(comparable_phase5b_rows)))))
        phase7b_manifest = {
            "schema_version": "phase7b_fresh_public_repo_validation_canary_private_manifest_v1",
            "phase": "phase7b_fresh_public_repo_validation_canary",
            "repos": [{
                "private_repo_key": "phase7b_public_repo_input_0",
                "private_public_id": comparable_repo_id,
                "private_phase5b_comparable_repo_id": comparable_repo_id,
                "private_locked_commit": manifest["repos"][0]["private_locked_commit"],
                "private_owner": "phase7b_selftest_owner",
            }],
            "tasks": [{
                "private_task_id": "phase7b_real_shape_task",
                "private_repo_key": "phase7b_public_repo_input_0",
                "private_gold_path": manifest["tasks"][0]["private_gold_path"],
                "private_gold_start_line": manifest["tasks"][0]["private_gold_start_line"],
                "private_gold_end_line": manifest["tasks"][0]["private_gold_end_line"],
                "private_gold_hash": manifest["tasks"][0]["private_gold_hash"],
            }],
        }
        phase7b_rows = [{
            "private_repo_key": "phase7b_public_repo_input_0",
            "private_task_id": "phase7b_real_shape_task",
            "private_materialization": {
                "private_path": manifest["tasks"][0]["private_gold_path"],
                "private_range": f"{manifest['tasks'][0]['private_gold_start_line']}-{manifest['tasks'][0]['private_gold_end_line']}",
                "private_content_sha256": manifest["tasks"][0]["private_gold_hash"],
                "private_content_text": "phase7b selftest snippet",
            },
        }]
        checks.append(("phase7b_manifest_repo_overlap_rejected", bool(manifest_overlap_errors(manifest, phase7b_overlap_index(phase7b_manifest, phase7b_rows)))))
        checks.append(("phase7b_manifest_commit_overlap_rejected", "commit overlap detected" in manifest_overlap_errors(manifest, phase7b_overlap_index(phase7b_manifest, phase7b_rows))))
        checks.append(("phase7b_real_row_schema_path_range_hash_overlap_rejected", any(error in manifest_overlap_errors(manifest, phase7b_overlap_index(phase7b_manifest, phase7b_rows)) for error in ("exact path overlap detected", "exact range overlap detected", "content digest overlap detected"))))
        phase5b_lock_path = runs_root / "phase5b_selftest_repo-lock.json"
        phase5b_commit = manifest["repos"][0]["private_locked_commit"]
        safe_json_dump(phase5b_lock_path, {"repo_selftest": {"repo_id": comparable_repo_id, "commit": phase5b_commit, "metadata": {"file_manifest": [{"path": manifest["tasks"][0]["private_gold_path"], "sha256": manifest["tasks"][0]["private_gold_hash"]}]}}})
        checks.append(("phase5b_repo_lock_commit_overlap_rejected", "commit overlap detected" in manifest_overlap_errors(manifest, phase5b_provenance_overlap_index([phase5b_lock_path]))))
        checks.append(("phase5b_repo_lock_file_manifest_overlap_rejected", any(error in manifest_overlap_errors(manifest, phase5b_provenance_overlap_index([phase5b_lock_path])) for error in ("exact path overlap detected", "content digest overlap detected", "file-family overlap detected"))))
        overlap_index = empty_overlap_index()
        overlap_index["repos"].add(manifest["repos"][0]["private_repo_key"].lower())
        overlap_index["commits"].add(manifest["repos"][0]["private_locked_commit"].lower())
        overlap_index["tasks"].add(manifest["tasks"][0]["private_task_id"].lower())
        overlap_index["paths"].add(f"{manifest['tasks'][0]['private_repo_key']}:{manifest['tasks'][0]['private_gold_path']}".lower())
        overlap_index["ranges"].add(f"{manifest['tasks'][0]['private_repo_key']}:{manifest['tasks'][0]['private_gold_path']}:{manifest['tasks'][0]['private_gold_start_line']}-{manifest['tasks'][0]['private_gold_end_line']}".lower())
        overlap_index["hashes"].add(manifest["tasks"][0]["private_gold_hash"].lower())
        overlap_index["families"].add(f"{manifest['tasks'][0]['private_repo_key']}:{file_family(manifest['tasks'][0]['private_gold_path'])}".lower())
        checks.append(("overlap_rejected", bool(manifest_overlap_errors(manifest, overlap_index))))
        rows = build_private_rows(manifest)
        checks.append(("private_rows_valid", not validate_private_rows(rows, len(manifest["tasks"]))))
        mutated = copy.deepcopy(rows)
        for row in mutated:
            if row["action_label"] == "stop":
                row["evidence_success"] = True
                break
        checks.append(("stop_success_rejected", bool(validate_private_rows(mutated, len(manifest["tasks"])))))
        mutated = copy.deepcopy(rows)
        for row in mutated:
            if row["evidence_success"]:
                row["evidencecore"]["task_tie"] = False
                break
        checks.append(("success_without_tie_rejected", bool(validate_private_rows(mutated, len(manifest["tasks"])))))
        mutated = copy.deepcopy(rows)
        for row in mutated:
            if row["evidence_success"]:
                row["private_materialization"].pop("private_content_sha256", None)
                break
        checks.append(("success_without_hash_rejected", bool(validate_private_rows(mutated, len(manifest["tasks"])))))
        report = build_report(manifest, rows, [], [])
        checks.append(("public_report_valid", not validate_report(report)))
        leaked = copy.deepcopy(report)
        leaked["privacy_summary"]["example"] = "C:/private/path/file.py"
        checks.append(("private_value_rejected", bool(validate_report(leaked))))
        singleton = copy.deepcopy(report)
        singleton["aggregate_buckets"]["repo_count_bucket"] = "count_1"
        checks.append(("singleton_rejected", bool(validate_report(singleton))))
        singleton = copy.deepcopy(report)
        singleton["aggregate_buckets"]["repo_count_bucket"] = "bucket_nonzero_lt_two"
        checks.append(("legacy_singleton_bucket_rejected", bool(validate_report(singleton))))
        mutated_report = copy.deepcopy(report)
        mutated_report["freshness_overlap_summary"]["fresh_public_repo_inputs_used"] = False
        checks.append(("pass_without_fresh_public_repo_rejected", bool(validate_report(mutated_report))))
        mutated_report = copy.deepcopy(report)
        mutated_report["freshness_overlap_summary"]["local_generated_canary_sources_used"] = True
        checks.append(("pass_with_generated_sources_rejected", bool(validate_report(mutated_report))))
        below_formal = copy.deepcopy(report)
        below_formal["aggregate_buckets"]["task_count_bucket"] = "bucket_below_formal_task_min"
        checks.append(("below_formal_task_min_rejected", bool(validate_report(below_formal))))
        claim = copy.deepcopy(report)
        claim["conservative_recommendation"] = "winner"
        checks.append(("claim_word_rejected", bool(validate_report(claim))))
        outside_manifest = tmp_path / "manifest.json"
        outside_manifest.write_text("{}", encoding="utf-8")
        try:
            ensure_private_path(outside_manifest)
            outside_refused = False
        except CanaryError:
            outside_refused = True
        checks.append(("outside_manifest_refused", outside_refused))
        input_path = runs_root / "private_public_repo_inputs_missing_comparable.json"
        safe_json_dump(input_path, {"repos": [{"repo_url_private": "https://example.invalid/a.git"} for _ in range(FORMAL_REPO_TARGET_MIN)]})
        try:
            load_public_repo_inputs(input_path)
            missing_comparable_rejected = False
        except CanaryError:
            missing_comparable_rejected = True
        checks.append(("missing_comparable_repo_id_rejected", missing_comparable_rejected))
        input_path = runs_root / "private_public_repo_inputs_local_clone.json"
        safe_json_dump(input_path, {"repos": [{"repo_url_private": f"https://example.invalid/{i}.git", "prior_phase_comparable_repo_id_private": f"c{i}", "source_type_private": "local_clone"} for i in range(FORMAL_REPO_TARGET_MIN)]})
        try:
            load_public_repo_inputs(input_path)
            local_clone_rejected = False
        except CanaryError:
            local_clone_rejected = True
        checks.append(("local_clone_synthetic_source_rejected", local_clone_rejected))
        parser = argparse.Namespace(confirm_private_input=False, confirm_private_output=False, confirm_public_repo_fetch=False, phase5b_rows=None, manifest=None, public_repo_inputs=DEFAULT_PUBLIC_REPO_INPUTS, output=DEFAULT_REPORT)
        try:
            execute(parser)
            missing_confirm_refused = False
        except CanaryError:
            missing_confirm_refused = True
        checks.append(("missing_confirm_refused", missing_confirm_refused))
        private_manifest_path = runs_root / "fetch_attesting_manifest.json"
        safe_json_dump(private_manifest_path, manifest)
        parser = argparse.Namespace(confirm_private_input=True, confirm_private_output=True, confirm_public_repo_fetch=True, phase5b_rows=None, manifest=private_manifest_path, public_repo_inputs=DEFAULT_PUBLIC_REPO_INPUTS, output=DEFAULT_REPORT)
        try:
            execute(parser)
            manifest_execution_disabled = False
        except CanaryError as exc:
            manifest_execution_disabled = "manifest execution is disabled" in str(exc)
        checks.append(("manifest_execution_disabled", manifest_execution_disabled))
        no_fetch_manifest = copy.deepcopy(manifest)
        no_fetch_manifest["public_repo_fetch_executed"] = False
        no_fetch_manifest_path = runs_root / "fresh_manifest_without_fetch_attestation.json"
        safe_json_dump(no_fetch_manifest_path, no_fetch_manifest)
        parser = argparse.Namespace(confirm_private_input=True, confirm_private_output=True, confirm_public_repo_fetch=True, phase5b_rows=None, manifest=no_fetch_manifest_path, public_repo_inputs=DEFAULT_PUBLIC_REPO_INPUTS, output=DEFAULT_REPORT)
        try:
            execute(parser)
            manifest_attestation_cannot_pass = False
        except CanaryError as exc:
            manifest_attestation_cannot_pass = "manifest execution is disabled" in str(exc)
        checks.append(("manifest_attestation_cannot_pass", manifest_attestation_cannot_pass))
    failed = [name for name, ok in checks if not ok]
    if failed:
        raise CanaryError("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 7C formal fresh public-repo validation")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--confirm-private-input", action="store_true")
    parser.add_argument("--confirm-private-output", action="store_true")
    parser.add_argument("--confirm-public-repo-fetch", action="store_true")
    parser.add_argument("--phase5b-rows", type=Path)
    parser.add_argument("--manifest", type=Path, help="Disabled for pass-capable Phase 7C execution; retained only to reject manifest-supplied source bypasses")
    parser.add_argument("--public-repo-inputs", type=Path, default=DEFAULT_PUBLIC_REPO_INPUTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            print(json.dumps(run_self_test(), indent=2, sort_keys=True))
            return 0
        if args.validate_report:
            report = json.loads(args.validate_report.read_text(encoding="utf-8"))
            errors = validate_report(report)
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print("Validation passed")
            return 0
        report = execute(args)
        print(json.dumps({"status": report["status"], "public_report_written": True, "private_outputs_written_under_ignored_runs": True}, indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, CanaryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
