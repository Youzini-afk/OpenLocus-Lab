#!/usr/bin/env python3
"""Phase 5B public-repo formal validation runner.

Protocol-preserving runner for the Phase 5A freeze.  The default execution path
is a safe two-step integration: ingest an already-frozen public task manifest and
repo-lock, run the seven frozen local acquisition/control labels, write private
rows only after explicit confirmation, and publish an aggregate-only report.

This file intentionally does not fetch repositories, generate tasks, add CI, call
providers/LLMs/search APIs, train models, or change runtime defaults.  Repository
fetch/task generation remain external Phase 5B hooks governed by the Phase 5A
freeze.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from ci_generate_tasks import validate_public_tasks as ci_validate_public_tasks
except Exception:  # pragma: no cover - import guard for direct embedding tests
    ci_validate_public_tasks = None

try:
    from ci_run_strategy_matrix import load_jsonl as ci_load_jsonl
    from ci_run_strategy_matrix import load_repo_lock as ci_load_repo_lock
except Exception:  # pragma: no cover
    ci_load_jsonl = None
    ci_load_repo_lock = None

try:
    from interventional_evidence_acquisition_phase1_hard_source_preflight import public_leak_errors
except Exception:  # pragma: no cover
    public_leak_errors = None


REPO = Path(__file__).resolve().parents[1]
PHASE = "interventional_evidence_acquisition_phase5b_public_repo_formal_validation"
SCHEMA_VERSION = "phase5b_public_repo_formal_validation_report_v1"
PRIVATE_ROW_SCHEMA_VERSION = "phase5b_public_repo_formal_validation_private_row_v1"
STATUS_COMPLETE = "phase5b_public_repo_formal_validation_complete_no_claim"
STATUS_CANARY = "phase5b_public_repo_formal_validation_canary_complete_no_claim"
STATUS_NO_GO = "phase5b_public_repo_formal_validation_no_go"
DEFAULT_REPORT = REPO / "artifacts" / "phase5b_public_repo_formal_validation" / "phase5b_public_repo_formal_validation_report.json"
DEFAULT_PRIVATE_BASE = REPO / "runs" / "phase5b_public_repo_formal_validation"

ALLOWED_LABELS: tuple[str, ...] = (
    "bm25_then_read_top1",
    "bm25_then_read_next_unique_file",
    "symbol_regex_then_read_top1",
    "symbol_regex_then_read_next_unique_file",
    "read_related_test_when_available",
    "stop",
    "abstain",
)
CONTROL_LABELS = {"stop", "abstain"}
ACQUISITION_LABELS = tuple(label for label in ALLOWED_LABELS if label not in CONTROL_LABELS)
TASK_TARGET = 120
TASK_MIN = 100
TASK_MAX = 150
REPO_TARGET_MIN = 10
REPO_TARGET_MAX = 12
REPO_HARD_MAX = 16
ROW_HARD_MAX = TASK_MAX * len(ALLOWED_LABELS)

SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs",
    ".rs", ".go", ".java", ".kt", ".kts", ".c", ".h", ".cpp",
    ".hpp", ".cc", ".cxx", ".hxx", ".cs", ".rb", ".php",
    ".swift", ".scala", ".clj",
}
SKIP_DIR_NAMES = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
    "build", "target", "coverage", ".next", ".nuxt", ".openlocus",
    "fixtures", "eval", "docs", "runs",
}
PRIVATE_PUBLIC_KEYS = {
    "task_id", "test_id", "private_task_id", "path", "paths", "range", "ranges",
    "hash", "hashes", "sha", "sha256", "snippet", "snippets", "manifest",
    "manifests", "run_dir", "run_dirs", "private_root", "private_rows_path",
}
PATH_SHAPED_RE = re.compile(r"(?:^|[A-Za-z]:)?(?:[\\/]|[A-Za-z0-9_.-]+[\\/])[A-Za-z0-9_.\\/-]+")
HASH_SHAPED_RE = re.compile(r"\b[a-fA-F0-9]{32,}\b")
RANGE_SHAPED_RE = re.compile(r"\b\d+\s*-\s*\d+\b")
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class Phase5BError(Exception):
    pass


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if ci_load_jsonl is not None:
        try:
            return ci_load_jsonl(path)
        except json.JSONDecodeError:
            # PowerShell can create BOM-prefixed JSONL in local canaries.
            pass
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_repo_lock(path: Path) -> dict[str, dict[str, Any]]:
    if ci_load_repo_lock is not None:
        try:
            return ci_load_repo_lock(path)
        except json.JSONDecodeError:
            # PowerShell can create BOM-prefixed JSON in local canaries.
            pass
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix == ".jsonl":
        repos: dict[str, dict[str, Any]] = {}
        for line in text.splitlines():
            if line.strip():
                entry = json.loads(line)
                repos[str(entry.get("repo_id"))] = entry
        return repos
    data = json.loads(text)
    if isinstance(data, dict) and "repos" in data and isinstance(data["repos"], dict):
        return data["repos"]
    if isinstance(data, dict) and "repo_id" in data:
        return {str(data["repo_id"]): data}
    if isinstance(data, dict):
        return data
    raise Phase5BError("repo lock must be JSON object or JSONL entries")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def bucket_count(count: int) -> str:
    """Coarse count bucket with no singleton `count_1` publication."""
    if count <= 0:
        return "count_0"
    if count < 2:
        return "count_nonzero_lt_2"
    if count <= 5:
        return "count_2_to_5"
    if count <= 20:
        return "count_6_to_20"
    if count <= 50:
        return "count_21_to_50"
    if count <= 99:
        return "count_51_to_99"
    if count <= TASK_MAX:
        return "count_hundred_to_task_cap"
    if count <= ROW_HARD_MAX:
        return "count_task_cap_to_row_cap"
    return "count_over_row_cap"


def bucket_repo_count(count: int) -> str:
    if count <= 0:
        return "count_0"
    if count < 2:
        return "count_nonzero_lt_2"
    if count <= 5:
        return "count_2_to_5"
    if count <= 9:
        return "count_6_to_9"
    if count <= 12:
        return "count_target_repo_range"
    if count <= REPO_HARD_MAX:
        return "count_above_target_within_cap"
    return "count_over_repo_cap"


def bucket_rate(success: int, total: int) -> str:
    if total <= 0 or success <= 0:
        return "rate_0"
    value = success / total
    if value < 0.25:
        return "rate_gt_0_lt_25pct"
    if value < 0.50:
        return "rate_25_to_50pct"
    if value < 0.75:
        return "rate_50_to_75pct"
    if value < 1.0:
        return "rate_75_to_lt_full"
    return "rate_full"


def tokenize(text: str) -> list[str]:
    return [tok.lower() for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]{1,}", text or "")]


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeError):
        return ""


def iter_source_files(repo_root: Path, extensions: set[str] | None = None) -> list[tuple[str, Path]]:
    extensions = extensions or SOURCE_EXTENSIONS
    files: list[tuple[str, Path]] = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIR_NAMES]
        base = Path(dirpath)
        for filename in filenames:
            full = base / filename
            if full.suffix.lower() not in extensions:
                continue
            try:
                rel = full.relative_to(repo_root).as_posix()
            except ValueError:
                continue
            files.append((rel, full))
    files.sort(key=lambda item: item[0])
    return files


def repo_root_for_task(task: dict[str, Any], repo_lock: dict[str, dict[str, Any]]) -> Path:
    repo_id = str(task.get("repo_id", ""))
    entry = repo_lock.get(repo_id)
    if not entry:
        raise Phase5BError("task references repo outside frozen lock")
    path = entry.get("source", {}).get("path")
    if not path:
        raise Phase5BError("repo lock entry missing local path")
    root = Path(path).resolve()
    if not root.exists() or not root.is_dir():
        raise Phase5BError("repo lock local path unavailable")
    return root


def candidate_score(query_tokens: list[str], rel_path: str, text: str) -> int:
    haystack = (rel_path + "\n" + text[:200000]).lower()
    return sum(haystack.count(token) for token in query_tokens)


def bm25_candidates(task: dict[str, Any], repo_lock: dict[str, dict[str, Any]]) -> list[str]:
    root = repo_root_for_task(task, repo_lock)
    qtokens = tokenize(str(task.get("query", "")))
    scored: list[tuple[int, str]] = []
    for rel, full in iter_source_files(root):
        text = safe_read_text(full)
        score = candidate_score(qtokens, rel, text)
        if score > 0:
            scored.append((score, rel))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [rel for _, rel in scored]


def symbol_regex_candidates(task: dict[str, Any], repo_lock: dict[str, dict[str, Any]]) -> list[str]:
    root = repo_root_for_task(task, repo_lock)
    query = str(task.get("query", ""))
    if not query:
        return []
    if IDENT_RE.match(query):
        pattern = re.compile(r"\b" + re.escape(query) + r"\b")
    else:
        pattern = re.compile(re.escape(query), re.IGNORECASE)
    matches: list[str] = []
    for rel, full in iter_source_files(root):
        text = safe_read_text(full)
        if pattern.search(text) or pattern.search(rel):
            matches.append(rel)
    return matches


def related_test_candidates(task: dict[str, Any], repo_lock: dict[str, dict[str, Any]]) -> list[str]:
    root = repo_root_for_task(task, repo_lock)
    qtokens = set(tokenize(str(task.get("query", ""))))
    matches: list[tuple[int, str]] = []
    for rel, full in iter_source_files(root):
        lowered = rel.lower()
        if not any(marker in lowered for marker in ("test", "spec", "__tests__")):
            continue
        text = safe_read_text(full).lower()
        score = sum(1 for token in qtokens if token in text or token in lowered)
        if score > 0:
            matches.append((score, rel))
    matches.sort(key=lambda item: (-item[0], item[1]))
    return [rel for _, rel in matches]


def select_candidate(task: dict[str, Any], repo_lock: dict[str, dict[str, Any]], action: str) -> str | None:
    if action == "bm25_then_read_top1":
        candidates = bm25_candidates(task, repo_lock)
        return candidates[0] if candidates else None
    if action == "bm25_then_read_next_unique_file":
        candidates = bm25_candidates(task, repo_lock)
        return candidates[1] if len(candidates) > 1 else None
    if action == "symbol_regex_then_read_top1":
        candidates = symbol_regex_candidates(task, repo_lock)
        return candidates[0] if candidates else None
    if action == "symbol_regex_then_read_next_unique_file":
        candidates = symbol_regex_candidates(task, repo_lock)
        return candidates[1] if len(candidates) > 1 else None
    if action == "read_related_test_when_available":
        candidates = related_test_candidates(task, repo_lock)
        return candidates[0] if candidates else None
    if action in CONTROL_LABELS:
        return None
    raise Phase5BError(f"unknown action label: {action}")


def choose_line_for_query(text: str, query: str) -> tuple[int, int]:
    lines = text.splitlines() or [""]
    tokens = tokenize(query)
    for index, line in enumerate(lines, start=1):
        lowered = line.lower()
        if any(token in lowered for token in tokens):
            return index, index
    return 1, 1


def materialize_candidate(repo_root: Path, rel_path: str, query: str) -> dict[str, Any] | None:
    full = (repo_root / rel_path).resolve()
    root = repo_root.resolve()
    if not str(full).startswith(str(root)) or not full.exists() or not full.is_file():
        return None
    text = safe_read_text(full)
    if text == "":
        return None
    start, end = choose_line_for_query(text, query)
    lines = text.splitlines()
    content = "\n".join(lines[start - 1:end]) + "\n"
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    reread_text = safe_read_text(full)
    reread_lines = reread_text.splitlines()
    reread_content = "\n".join(reread_lines[start - 1:end]) + "\n" if end <= len(reread_lines) else ""
    return {
        "path_private": rel_path,
        "start_line_private": start,
        "end_line_private": end,
        "content_sha256_private": digest,
        "content_byte_length": len(content.encode("utf-8")),
        "currentness_reread_match": reread_content == content,
        "range_content_match": hashlib.sha256(reread_content.encode("utf-8")).hexdigest() == digest,
    }


def label_gold_spans(label: dict[str, Any]) -> list[dict[str, Any]]:
    spans = label.get("gold_spans", [])
    return spans if isinstance(spans, list) else []


def ranges_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return max(a_start, b_start) <= min(a_end, b_end)


def task_tie(materialization: dict[str, Any] | None, label: dict[str, Any]) -> bool:
    if not materialization:
        return False
    rel = str(materialization.get("path_private", ""))
    start = int(materialization.get("start_line_private", 0))
    end = int(materialization.get("end_line_private", 0))
    for span in label_gold_spans(label):
        if rel != str(span.get("path", "")):
            continue
        try:
            gold_start = int(span.get("start_line", 0))
            gold_end = int(span.get("end_line", 0))
        except (TypeError, ValueError):
            continue
        if ranges_overlap(start, end, gold_start, gold_end):
            return True
    return False


def build_private_rows(
    tasks: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    repo_lock: dict[str, dict[str, Any]],
    *,
    canary: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    row_index = 0
    for task in tasks:
        task_id = str(task.get("test_id") or task.get("task_id") or "")
        if task_id not in labels:
            raise Phase5BError("private label missing for task")
        repo_root = repo_root_for_task(task, repo_lock)
        for action in ALLOWED_LABELS:
            candidate = select_candidate(task, repo_lock, action)
            materialization = materialize_candidate(repo_root, candidate, str(task.get("query", ""))) if candidate else None
            tied = task_tie(materialization, labels[task_id])
            current = bool(materialization and materialization.get("currentness_reread_match") and materialization.get("range_content_match"))
            evidence_success = bool(action not in CONTROL_LABELS and materialization and current and tied and materialization.get("content_byte_length", 0) > 0)
            candidate_found = bool(candidate)
            rows.append({
                "schema_version": PRIVATE_ROW_SCHEMA_VERSION,
                "phase": PHASE,
                "row_index": row_index,
                "private_task_id": task_id,
                "repo_id": str(task.get("repo_id", "")),
                "action_label": action,
                "assignment_mode": "deterministic_full_panel_all_frozen_labels",
                "canary_mode": canary,
                "candidate_found": candidate_found,
                "read_attempted": action not in CONTROL_LABELS and candidate_found,
                "materialized_current_source": materialization is not None,
                "evidence_success": evidence_success,
                "failure_bucket": "none" if evidence_success else (
                    "control_no_acquisition" if action in CONTROL_LABELS else (
                        "candidate_not_found" if not candidate_found else (
                            "no_task_tie" if materialization and current else "materialization_failed"
                        )
                    )
                ),
                "private_materialization": materialization or {},
                "evidencecore": {
                    "candidate_found_alone_is_evidence": False,
                    "success_requires_current_source_read": True,
                    "success_requires_materialization": True,
                    "success_requires_hash_currentness_task_tie": True,
                    "content_sha256_present": bool(materialization and materialization.get("content_sha256_private")),
                    "currentness_reread_match": bool(materialization and materialization.get("currentness_reread_match")),
                    "range_content_match": bool(materialization and materialization.get("range_content_match")),
                    "task_tie": tied,
                },
                "privacy": {
                    "private_row": True,
                    "public_artifact_allowed": False,
                    "provider_network_used": False,
                    "llm_used": False,
                    "search_api_used": False,
                    "remote_model_used": False,
                    "model_training_executed": False,
                    "runtime_default_changed": False,
                    "new_retrieval_family_added": False,
                },
            })
            row_index += 1
    return rows


def validate_public_tasks_for_phase(tasks: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if ci_validate_public_tasks is not None:
        errors.extend(ci_validate_public_tasks(tasks))
    for task in tasks:
        task_id = task.get("test_id") or task.get("task_id")
        if not task_id or not task.get("repo_id") or not task.get("query"):
            errors.append("public task missing required public fields")
        for key in task:
            if key in {"gold_spans", "hard_distractors", "must_not_primary", "expected_behavior", "oracle_type"}:
                errors.append("public task includes private label field")
    return errors


def validate_repo_lock_for_phase(repo_lock: dict[str, dict[str, Any]], used_repo_ids: set[str], *, canary: bool) -> list[str]:
    errors: list[str] = []
    if len(used_repo_ids) > REPO_HARD_MAX:
        errors.append("repo hard cap exceeded")
    for repo_id in used_repo_ids:
        entry = repo_lock.get(repo_id)
        if not entry:
            errors.append("used repo missing from lock")
            continue
        source = entry.get("source", {})
        source_type = source.get("type")
        if not canary and source_type != "github_public":
            errors.append("non-public-github source in formal mode")
        if canary and source_type not in {"github_public", "local_absolute_path"}:
            errors.append("unsupported canary repo source type")
        if not source.get("path"):
            errors.append("repo lock missing local path")
        if not canary and not entry.get("commit"):
            errors.append("formal repo lock missing commit sha")
        if not canary and not (source.get("repo") or source.get("clone_url")):
            errors.append("formal repo lock missing frozen url/repo")
    return errors


def validate_private_rows(rows: list[dict[str, Any]], task_count: int) -> list[str]:
    errors: list[str] = []
    if len(rows) > ROW_HARD_MAX:
        errors.append("row hard cap exceeded")
    if len(rows) != task_count * len(ALLOWED_LABELS):
        errors.append("rows must be exactly seven labels per task")
    by_task: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        action = row.get("action_label")
        if action not in ALLOWED_LABELS:
            errors.append("action label drift")
        by_task[str(row.get("private_task_id", ""))].add(str(action))
        if action in CONTROL_LABELS and row.get("evidence_success") is True:
            errors.append("stop/abstain success nonzero")
        privacy = row.get("privacy", {})
        for key in ("provider_network_used", "llm_used", "search_api_used", "remote_model_used", "model_training_executed", "runtime_default_changed", "new_retrieval_family_added"):
            if privacy.get(key) is not False:
                errors.append(f"private row forbidden execution flag: {key}")
        if row.get("evidence_success") is True:
            mat = row.get("private_materialization", {})
            ec = row.get("evidencecore", {})
            if row.get("materialized_current_source") is not True or not mat:
                errors.append("success without materialization")
            if not re.fullmatch(r"[a-f0-9]{64}", str(mat.get("content_sha256_private", ""))):
                errors.append("success without private content hash")
            for key in ("currentness_reread_match", "range_content_match", "task_tie"):
                if ec.get(key) is not True:
                    errors.append(f"success without {key}")
    for labels in by_task.values():
        if labels != set(ALLOWED_LABELS):
            errors.append("per-task label coverage drift")
    return sorted(set(errors))


def public_report_leak_errors(value: Any, parent: str = "$", key_name: str = "") -> list[str]:
    errors: list[str] = []
    if key_name.lower() in PRIVATE_PUBLIC_KEYS:
        errors.append(f"private-shaped key public at {parent}")
    if isinstance(value, dict):
        for key, child in value.items():
            errors.extend(public_report_leak_errors(child, f"{parent}.{key}" if parent != "$" else f"$.{key}", str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(public_report_leak_errors(child, f"{parent}[{index}]"))
    elif isinstance(value, str):
        if "count_1" in value:
            errors.append(f"singleton bucket public at {parent}")
        if HASH_SHAPED_RE.search(value) or RANGE_SHAPED_RE.search(value) or PATH_SHAPED_RE.search(value):
            # Allow frozen label strings with underscores; report must not publish paths/ranges/hashes.
            errors.append(f"private-shaped value public at {parent}")
    return errors


def build_report(
    rows: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    repo_lock: dict[str, dict[str, Any]],
    *,
    canary: bool,
    private_rows_written: bool,
    protocol_errors: list[str] | None = None,
) -> dict[str, Any]:
    protocol_errors = protocol_errors or []
    private_errors = validate_private_rows(rows, len(tasks))
    status = STATUS_NO_GO if protocol_errors or private_errors else (STATUS_CANARY if canary else STATUS_COMPLETE)
    action_counts = Counter(str(row["action_label"]) for row in rows)
    candidate_counts = Counter(str(row["action_label"]) for row in rows if row.get("candidate_found") is True)
    read_counts = Counter(str(row["action_label"]) for row in rows if row.get("read_attempted") is True)
    materialized_counts = Counter(str(row["action_label"]) for row in rows if row.get("materialized_current_source") is True)
    hash_current_counts = Counter(str(row["action_label"]) for row in rows if row.get("evidencecore", {}).get("content_sha256_present") and row.get("evidencecore", {}).get("currentness_reread_match") is True)
    success_counts = Counter(str(row["action_label"]) for row in rows if row.get("evidence_success") is True)
    failure_counts = Counter(str(row.get("failure_bucket", "unknown")) for row in rows if row.get("evidence_success") is not True)
    task_count = len(tasks)
    repo_count = len({str(task.get("repo_id", "")) for task in tasks})
    best_fixed = max(success_counts[label] for label in ALLOWED_LABELS)
    best_acquisition = max(success_counts[label] for label in ACQUISITION_LABELS)
    full_task_rule_ok = TASK_MIN <= task_count <= TASK_MAX if not canary else 0 < task_count <= TASK_MAX
    hard_gates = {
        "task_count_within_protocol": full_task_rule_ok,
        "task_hard_cap_preserved": task_count <= TASK_MAX,
        "row_hard_cap_preserved": len(rows) <= ROW_HARD_MAX,
        "repo_hard_cap_preserved": repo_count <= REPO_HARD_MAX,
        "seven_labels_exact": set(ALLOWED_LABELS) == set(action_counts),
        "stop_abstain_success_zero": success_counts["stop"] + success_counts["abstain"] == 0,
        "current_source_validation_for_success": not any(row.get("evidence_success") is True and row.get("evidencecore", {}).get("currentness_reread_match") is not True for row in rows),
        "no_provider_llm_search_api_remote_model": True,
        "no_training_or_runtime_default_change": True,
        "no_new_retrieval_family": True,
        "private_rows_schema_valid": not private_errors,
        "public_report_aggregate_only": True,
        "no_staged_runs_or_post_outcome_tuning": True,
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "execution_mode": {
            "canary": canary,
            "two_step_manifest_ingestion_runner": True,
            "repo_fetch_executed_by_this_runner": False,
            "task_generation_executed_by_this_runner": False,
            "phase5b_runner_implemented": True,
            "private_rows_written": private_rows_written,
        },
        "authorization_attestation": {
            "public_github_fetch_only_for_external_frozen_hook": True,
            "provider_network_authorized": False,
            "llm_authorized": False,
            "search_api_authorized": False,
            "remote_model_authorized": False,
            "training_authorized": False,
            "model_training_executed": False,
            "runtime_default_change_authorized": False,
            "runtime_default_changed": False,
            "new_retrieval_family_authorized": False,
            "new_retrieval_family_added": False,
            "method_selection_claimed": False,
            "promotion_claimed": False,
        },
        "frozen_protocol_summary": {
            "target_task_count": "one_hundred_twenty",
            "valid_task_range": "one_hundred_to_one_hundred_fifty",
            "task_hard_max": "one_hundred_fifty",
            "private_row_hard_max": "one_thousand_fifty",
            "repo_target_range": "ten_to_twelve",
            "repo_hard_max": "sixteen",
            "frozen_labels_exact": list(ALLOWED_LABELS),
            "urls_shas_strata_replacement_frozen_before_execution": True,
        },
        "aggregate_buckets": {
            "task_count_bucket": bucket_count(task_count),
            "row_count_bucket": bucket_count(len(rows)),
            "repo_count_bucket": bucket_repo_count(repo_count),
            "label_coverage_buckets": {label: bucket_count(action_counts[label]) for label in ALLOWED_LABELS},
            "candidate_found_buckets": {label: bucket_count(candidate_counts[label]) for label in ALLOWED_LABELS},
            "read_attempted_buckets": {label: bucket_count(read_counts[label]) for label in ALLOWED_LABELS},
            "materialized_current_source_buckets": {label: bucket_count(materialized_counts[label]) for label in ALLOWED_LABELS},
            "hash_currentness_pass_buckets": {label: bucket_count(hash_current_counts[label]) for label in ALLOWED_LABELS},
            "evidence_success_buckets": {label: bucket_count(success_counts[label]) for label in ALLOWED_LABELS},
            "failure_buckets": {name: bucket_count(count) for name, count in sorted(failure_counts.items())},
            "control_success_bucket": bucket_count(success_counts["stop"] + success_counts["abstain"]),
        },
        "baseline_comparison": {
            "comparison_scope": "best_fixed_local_or_acquisition_baseline_aggregate_only",
            "best_fixed_local_baseline_bucket": bucket_count(best_fixed),
            "best_fixed_acquisition_baseline_bucket": bucket_count(best_acquisition),
            "best_fixed_acquisition_rate_bucket": bucket_rate(best_acquisition, task_count),
            "selection_or_promotion_claim": "not_made",
            "signal_claim": "not_made",
        },
        "evidencecore_summary": {
            "candidate_found_alone_is_evidence": False,
            "success_requires_current_source_read": True,
            "success_requires_materialization": True,
            "success_requires_hash_currentness_task_tie": True,
            "stop_and_abstain_are_controls": True,
        },
        "privacy_summary": {
            "publication_level": "aggregate_only",
            "raw_private_rows_public": False,
            "raw_task_ids_public": False,
            "paths_public": False,
            "ranges_public": False,
            "hashes_public": False,
            "snippets_public": False,
            "run_dirs_public": False,
            "manifests_public": False,
            "singleton_buckets_public": False,
            "provider_payloads_public": False,
        },
        "hard_gates": hard_gates,
        "validation_summary": {
            "protocol_error_bucket": bucket_count(len(protocol_errors)),
            "private_row_error_bucket": bucket_count(len(private_errors)),
            "route_specific_public_report_validation": "pending",
            "central_privacy_scan": "pending",
            "self_test_available": True,
        },
        "execution_hook_limitations": {
            "repository_fetch_hook": "external_frozen_ci_helper_not_invoked_by_this_runner",
            "task_generation_hook": "external_frozen_ci_helper_not_invoked_by_this_runner",
            "formal_execution_requires_confirm_private_output": True,
        },
        "next_authorized_action": "run_formal_phase5b_only_after_self_test_or_canary_passes_and_private_output_is_confirmed",
    }
    central_errors = public_leak_errors(report) if public_leak_errors is not None else []
    route_errors = validate_report(report, include_pending=False, extra_public_errors=central_errors)
    report["validation_summary"]["central_privacy_scan"] = "passed" if not central_errors else "failed"
    report["validation_summary"]["route_specific_public_report_validation"] = "passed" if not route_errors else "failed"
    return report


def validate_report(report: Any, *, include_pending: bool = True, extra_public_errors: list[str] | None = None) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION or report.get("phase") != PHASE:
        errors.append("report identity drift")
    if report.get("status") not in {STATUS_COMPLETE, STATUS_CANARY, STATUS_NO_GO}:
        errors.append("status drift")
    auth = report.get("authorization_attestation", {})
    for key in (
        "provider_network_authorized", "llm_authorized", "search_api_authorized",
        "remote_model_authorized", "training_authorized", "model_training_executed",
        "runtime_default_change_authorized", "runtime_default_changed",
        "new_retrieval_family_authorized", "new_retrieval_family_added",
        "method_selection_claimed", "promotion_claimed",
    ):
        if auth.get(key) is not False:
            errors.append(f"authorization boundary failed: {key}")
    if set(report.get("frozen_protocol_summary", {}).get("frozen_labels_exact", [])) != set(ALLOWED_LABELS):
        errors.append("frozen action label set drift")
    for bucket_map_key in (
        "label_coverage_buckets", "candidate_found_buckets", "read_attempted_buckets",
        "materialized_current_source_buckets", "hash_currentness_pass_buckets",
        "evidence_success_buckets",
    ):
        if set(report.get("aggregate_buckets", {}).get(bucket_map_key, {})) != set(ALLOWED_LABELS):
            errors.append(f"aggregate action shape drift: {bucket_map_key}")
    if report.get("aggregate_buckets", {}).get("control_success_bucket") != "count_0":
        errors.append("stop/abstain success nonzero")
    evidence = report.get("evidencecore_summary", {})
    if evidence.get("candidate_found_alone_is_evidence") is not False:
        errors.append("candidate-found evidence boundary failed")
    for key in ("success_requires_current_source_read", "success_requires_materialization", "success_requires_hash_currentness_task_tie", "stop_and_abstain_are_controls"):
        if evidence.get(key) is not True:
            errors.append(f"EvidenceCore invariant failed: {key}")
    privacy = report.get("privacy_summary", {})
    if privacy.get("publication_level") != "aggregate_only":
        errors.append("publication level drift")
    for key in ("raw_private_rows_public", "raw_task_ids_public", "paths_public", "ranges_public", "hashes_public", "snippets_public", "run_dirs_public", "manifests_public", "singleton_buckets_public", "provider_payloads_public"):
        if privacy.get(key) is not False:
            errors.append(f"privacy boundary failed: {key}")
    gates = report.get("hard_gates", {})
    for key in ("task_hard_cap_preserved", "row_hard_cap_preserved", "repo_hard_cap_preserved", "seven_labels_exact", "stop_abstain_success_zero", "current_source_validation_for_success", "no_provider_llm_search_api_remote_model", "no_training_or_runtime_default_change", "no_new_retrieval_family", "private_rows_schema_valid", "public_report_aggregate_only", "no_staged_runs_or_post_outcome_tuning"):
        if gates.get(key) is not True:
            errors.append(f"hard gate failed: {key}")
    text = json.dumps(report, sort_keys=True)
    if "count_1" in text:
        errors.append("singleton count bucket leaked")
    errors.extend(public_report_leak_errors(report))
    if extra_public_errors:
        errors.extend(extra_public_errors)
    if include_pending:
        val = report.get("validation_summary", {})
        if val.get("central_privacy_scan") != "passed" or val.get("route_specific_public_report_validation") != "passed":
            errors.append("validation summary is not passed")
    return sorted(set(errors))


def write_report(report: dict[str, Any], output: Path) -> None:
    errors = validate_report(report)
    if errors:
        raise Phase5BError("public report validation failed: " + "; ".join(errors[:10]))
    write_json(output, report)


def prepare_inputs(tasks_path: Path, labels_path: Path, repo_lock_path: Path, *, task_limit: int | None, canary: bool) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    tasks = load_jsonl(tasks_path)
    labels_rows = load_jsonl(labels_path)
    repo_lock = load_repo_lock(repo_lock_path)
    if task_limit is not None:
        tasks = tasks[:task_limit]
    errors: list[str] = []
    errors.extend(validate_public_tasks_for_phase(tasks))
    task_count = len(tasks)
    if canary:
        if not (0 < task_count <= TASK_MAX):
            errors.append("canary task count outside allowed hard cap")
    else:
        if not (TASK_MIN <= task_count <= TASK_MAX):
            errors.append("formal task count outside valid protocol range")
    if task_count > TASK_MAX:
        errors.append("task hard cap exceeded")
    labels: dict[str, dict[str, Any]] = {}
    for label in labels_rows:
        task_id = str(label.get("test_id") or label.get("task_id") or "")
        if task_id:
            labels[task_id] = label
    for task in tasks:
        task_id = str(task.get("test_id") or task.get("task_id") or "")
        if task_id not in labels:
            errors.append("task missing private label")
    used_repos = {str(task.get("repo_id", "")) for task in tasks}
    errors.extend(validate_repo_lock_for_phase(repo_lock, used_repos, canary=canary))
    return tasks, labels, repo_lock, sorted(set(errors))


def execute(
    *,
    tasks_path: Path,
    labels_path: Path,
    repo_lock_path: Path,
    output: Path,
    private_base: Path,
    confirm_private_output: bool,
    task_limit: int | None,
    canary: bool,
) -> dict[str, Any]:
    tasks, labels, repo_lock, protocol_errors = prepare_inputs(tasks_path, labels_path, repo_lock_path, task_limit=task_limit, canary=canary)
    rows = build_private_rows(tasks, labels, repo_lock, canary=canary) if not protocol_errors else []
    private_errors = validate_private_rows(rows, len(tasks)) if rows else ([] if protocol_errors else ["no rows built"])
    if rows and not private_errors and confirm_private_output:
        root = private_base / time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        write_jsonl(root / "phase5b_private_rows.jsonl", rows)
        write_json(root / "phase5b_private_manifest.json", {"schema_version": "phase5b_private_manifest_v1", "row_count": len(rows), "task_count": len(tasks), "canary": canary})
        private_written = True
    elif rows and not confirm_private_output:
        raise Phase5BError("--confirm-private-output is required before writing Phase 5B private rows")
    else:
        private_written = False
    report = build_report(rows, tasks, repo_lock, canary=canary, private_rows_written=private_written, protocol_errors=protocol_errors + private_errors)
    write_report(report, output)
    return report


def make_selftest_fixture(base: Path) -> tuple[Path, Path, Path]:
    repo_root = base / "repo"
    src = repo_root / "src"
    tests = repo_root / "tests"
    src.mkdir(parents=True)
    tests.mkdir(parents=True)
    (src / "alpha.py").write_text("def alpha_target():\n    return 'alpha'\n\ndef beta_noise():\n    return 'beta'\n", encoding="utf-8")
    (tests / "test_alpha.py").write_text("from src.alpha import alpha_target\n\ndef test_alpha_target():\n    assert alpha_target() == 'alpha'\n", encoding="utf-8")
    repo_lock = {
        "repo_selftest": {
            "repo_id": "repo_selftest",
            "source": {"type": "local_absolute_path", "path": str(repo_root)},
            "commit": "selftest",
            "tier": "selftest",
        }
    }
    tasks = [{"test_id": "t_selftest_alpha", "repo_id": "repo_selftest", "query": "alpha_target", "public_version": "0", "source": "selftest", "task_bucket": "positive", "task_risk_tags": ["exact_symbol_match"]}]
    labels = [{"test_id": "t_selftest_alpha", "repo_id": "repo_selftest", "query": "alpha_target", "source_category": "positive", "expected_behavior": "primary_evidence", "oracle_type": "deterministic", "risk_tags": ["exact_symbol_match"], "gold_spans": [{"path": "src/alpha.py", "start_line": 1, "end_line": 2}], "hard_distractors": [], "must_not_primary": []}]
    repo_lock_path = base / "repo-lock.json"
    tasks_path = base / "tasks.jsonl"
    labels_path = base / "labels.jsonl"
    write_json(repo_lock_path, repo_lock)
    write_jsonl(tasks_path, tasks)
    write_jsonl(labels_path, labels)
    return tasks_path, labels_path, repo_lock_path


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory(prefix="phase5b_selftest_") as tmp:
        base = Path(tmp)
        tasks_path, labels_path, repo_lock_path = make_selftest_fixture(base)
        tasks, labels, repo_lock, protocol_errors = prepare_inputs(tasks_path, labels_path, repo_lock_path, task_limit=1, canary=True)
        checks.append(("canary_fixture_protocol_valid", not protocol_errors))
        rows = build_private_rows(tasks, labels, repo_lock, canary=True)
        checks.append(("private_rows_valid", not validate_private_rows(rows, len(tasks))))
        checks.append(("all_seven_labels_present", Counter(row["action_label"] for row in rows) == Counter({label: 1 for label in ALLOWED_LABELS})))
        checks.append(("control_success_zero", not any(row["action_label"] in CONTROL_LABELS and row["evidence_success"] for row in rows)))
        checks.append(("at_least_one_materialized_success", any(row["evidence_success"] for row in rows)))
        report = build_report(rows, tasks, repo_lock, canary=True, private_rows_written=False)
        checks.append(("public_report_valid", not validate_report(report)))
        leaked = copy.deepcopy(report)
        leaked["privacy_summary"]["paths_public"] = True
        checks.append(("privacy_mutation_rejected", bool(validate_report(leaked))))
        singleton = copy.deepcopy(report)
        singleton["aggregate_buckets"]["task_count_bucket"] = "count_1"
        checks.append(("singleton_bucket_rejected", bool(validate_report(singleton))))
        drift = copy.deepcopy(report)
        drift["frozen_protocol_summary"]["frozen_labels_exact"] = list(ALLOWED_LABELS[:-1])
        checks.append(("label_drift_rejected", bool(validate_report(drift))))
        control = copy.deepcopy(rows)
        for row in control:
            if row["action_label"] == "stop":
                row["evidence_success"] = True
                break
        checks.append(("control_success_private_rows_rejected", bool(validate_private_rows(control, len(tasks)))))
        cap = rows * 151
        checks.append(("row_cap_rejected", bool(validate_private_rows(cap, len(tasks)))))
    failed = [name for name, ok in checks if not ok]
    if failed:
        raise Phase5BError("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks), "failed_checks": []}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 5B public-repo formal validation runner")
    parser.add_argument("--self-test", action="store_true", help="run synthetic canary and validator mutation tests")
    parser.add_argument("--validate-report", type=Path, help="validate aggregate-only public Phase 5B report")
    parser.add_argument("--tasks", type=Path, help="public tasks JSONL from frozen task-generation hook")
    parser.add_argument("--labels", type=Path, help="private labels JSONL; used only for private scoring rows")
    parser.add_argument("--repo-lock", type=Path, help="frozen repo-lock JSON/JSONL with local clone paths")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT, help="public aggregate report path")
    parser.add_argument("--private-root", type=Path, default=DEFAULT_PRIVATE_BASE, help="ignored private output base")
    parser.add_argument("--confirm-private-output", action="store_true", help="required before writing private rows under runs/")
    parser.add_argument("--task-limit", type=int, default=TASK_TARGET, help="maximum tasks to execute from public manifest")
    parser.add_argument("--canary", action="store_true", help="relax minimum task/repo rules for tiny local canary only")
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
            print(f"Validation passed: {args.validate_report}")
            return 0
        if not args.tasks or not args.labels or not args.repo_lock:
            raise Phase5BError("execution requires --tasks, --labels, and --repo-lock")
        report = execute(
            tasks_path=args.tasks,
            labels_path=args.labels,
            repo_lock_path=args.repo_lock,
            output=args.output,
            private_base=args.private_root,
            confirm_private_output=args.confirm_private_output,
            task_limit=args.task_limit,
            canary=args.canary,
        )
        print(json.dumps({
            "status": report["status"],
            "public_report": str(args.output),
            "private_rows_written": report["execution_mode"]["private_rows_written"],
            "canary": report["execution_mode"]["canary"],
        }, indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, Phase5BError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
