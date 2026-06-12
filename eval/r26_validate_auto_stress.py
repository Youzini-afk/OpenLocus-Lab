#!/usr/bin/env python3
"""R26 Auto-Stress-1000 Retrieval Failure-Surface Benchmark Static Validator.

FAIL-CLOSED validator for R26 stress dataset. Any violation is an error.

Key validation rules:
  1. Public tasks must NOT contain any field outside PUBLIC_TASK_FIELDS (ERROR).
  2. Task IDs and label IDs must be bijective; no duplicates; no unknown repo_ids.
  3. Enum values must be valid (expected_behavior, oracle_type).
  4. Label required fields must all be present with correct types.
  5. expected_behavior=primary_evidence must have gold_spans.
  6. expected_behavior in (abstain, no_primary) must have empty gold_spans.
  7. must_not_primary must not overlap gold_spans.
  8. hard_distractors must not overlap gold_spans.
  9. Each required category must meet minimum count (10).
  10. Total tasks >= 1000.
  11. Each repo must have >= 50 tasks.
  12. No canary tokens in tasks or labels.
  13. dataset_manifest flags must be correct (not_promotion_evidence=true, etc.).
  14. No unknown categories.
  15. Schema separation: public tasks must not have private fields.
  16. Label-public task consistency (test_id, repo_id match).
  17. Uniqueness: no duplicate test_ids.
  18. Repo existence: all repo_ids must exist in repos.lock.
  19. Deterministic manifest checks: tasks_sha256 and labels_sha256 must match.

Usage:
    python3 eval/r26_validate_auto_stress.py --workspace . --fixtures fixtures/r26_auto_stress
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


# ── Constants ──────────────────────────────────────────────────────────

PRIVATE_FIELDS = frozenset({
    "gold_spans", "gold_paths", "gold_files", "hard_distractors",
    "hard_negatives", "label_quality", "expected_behavior", "oracle_type",
    "must_not_primary", "risk_tags", "query_category", "intent_guess",
    "why_this_is_hard", "which_strategy_it_targets", "candidate_only",
    "risk_tag", "source_category", "risk_public",
})

EXPECTED_BEHAVIOR_ENUM = {
    "primary_evidence", "supporting_only", "weak_candidates",
    "abstain", "no_primary",
}

ORACLE_TYPE_ENUM = {
    "deterministic", "mined", "differential", "metamorphic", "stress",
}

REQUIRED_CATEGORIES = {
    "negative_nonexistent",
    "ambiguous_vague",
    "hard_distractor",
    "semantic_trap",
    "same_name_symbol",
    "frontend_backend_confusion",
    "test_source_confusion",
    "generated_vendor_trap",
    "stale_index_like",
    "dense_quiver_specific_trap",
}

TARGET_COMPOSITION = {
    "negative_nonexistent": 150,
    "ambiguous_vague": 150,
    "hard_distractor": 200,
    "semantic_trap": 150,
    "same_name_symbol": 100,
    "frontend_backend_confusion": 75,
    "test_source_confusion": 75,
    "generated_vendor_trap": 50,
    "stale_index_like": 50,
    "dense_quiver_specific_trap": 100,
}

PUBLIC_TASK_FIELDS = frozenset({
    "test_id", "repo_id", "query", "public_version", "source",
})

LABEL_REQUIRED_FIELDS: dict[str, type] = {
    "test_id": str,
    "repo_id": str,
    "query": str,
    "source_category": str,
    "risk_public": str,
    "intent_guess": str,
    "risk_tags": list,
    "oracle_type": str,
    "expected_behavior": str,
    "gold_spans": list,
    "hard_distractors": list,
    "must_not_primary": list,
    "why_this_is_hard": str,
    "which_strategy_it_targets": str,
}

LABEL_ALLOWED_FIELDS = frozenset(LABEL_REQUIRED_FIELDS.keys())

CANARY_TOKENS = [
    "CANARY", "canary_token", "canary-token", "CANARY_TOKEN",
    "canary_trap", "CANARY_TRAP", "leak_canary", "LEAK_CANARY",
]

SOURCE_EXTENSIONS = {".rs", ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".mjs"}

SKIP_DIR_NAMES = {
    "node_modules", "target", ".git", "dist", "build", ".venv",
    "__pycache__", ".next", ".nuxt", "runs", "fixtures", "eval",
    "docs", ".openlocus", "coverage", ".cache", ".mypy_cache",
    ".pytest_cache", ".tox", "venv", "env", ".env", ".idea",
    ".vscode", "out", "bin", "obj",
}

MIN_TOTAL_TASKS = 1000
MIN_PER_CATEGORY = 10
MIN_PER_REPO = 50


# ── Helpers ────────────────────────────────────────────────────────────

def should_skip_dir(dirname: str) -> bool:
    return dirname in SKIP_DIR_NAMES or dirname.startswith(".")


def find_source_files(
    repo_path: Path,
    extensions: set[str] | None = None,
    exclude_subdirs: list[str] | None = None,
) -> list[tuple[str, Path]]:
    if extensions is None:
        extensions = SOURCE_EXTENSIONS
    exclude_set = set(exclude_subdirs or [])
    results: list[tuple[str, Path]] = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [
            d for d in dirnames
            if not should_skip_dir(d) and d not in exclude_set
        ]
        for fname in sorted(filenames):
            ext = os.path.splitext(fname)[1]
            if ext in extensions:
                full = Path(dirpath) / fname
                if full.is_symlink():
                    continue
                try:
                    rel = str(full.relative_to(repo_path)).replace(os.sep, "/")
                except ValueError:
                    continue
                results.append((rel, full))
    results.sort(key=lambda x: x[0])
    return results


def compute_normalized_manifest_sha(
    repo_path: Path,
    extensions: set[str] | None = None,
    exclude_subdirs: list[str] | None = None,
) -> tuple[str, int, int]:
    all_files = find_source_files(repo_path, extensions, exclude_subdirs)
    hasher = hashlib.sha256()
    file_count = 0
    total_lines = 0
    for rel_path, full_path in all_files:
        try:
            content = full_path.read_bytes()
            file_sha = hashlib.sha256(content).hexdigest()
            line_count = content.count(b"\n") + 1
        except OSError:
            continue
        entry = {"path": rel_path, "sha256": file_sha, "lines": line_count}
        entry_line = json.dumps(entry, sort_keys=True)
        hasher.update(entry_line.encode("utf-8"))
        hasher.update(b"\n")
        file_count += 1
        total_lines += line_count
    return hasher.hexdigest(), file_count, total_lines


def spans_overlap(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if a.get("path") != b.get("path"):
        return False
    a_start = int(a.get("start_line", 0))
    a_end = int(a.get("end_line", 0))
    b_start = int(b.get("start_line", 0))
    b_end = int(b.get("end_line", 0))
    if a_start <= 0 or a_end < a_start or b_start <= 0 or b_end < b_start:
        return False
    return a_start <= b_end and b_start <= a_end


def check_canary(text: str) -> bool:
    """Return True if canary token is found."""
    for token in CANARY_TOKENS:
        if token in text:
            return True
    return False


# ── Main validation ────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="R26 auto-stress-1000 static validator (fail-closed)"
    )
    parser.add_argument(
        "--workspace", default=".",
        help="Workspace root (containing eval/, fixtures/, etc.)"
    )
    parser.add_argument(
        "--fixtures", default="fixtures/r26_auto_stress",
        help="Fixtures directory relative to workspace"
    )
    args = parser.parse_args()

    workspace = Path(args.workspace)
    fixtures_dir = workspace / args.fixtures

    errors: list[str] = []
    warnings: list[str] = []

    # ── Check fixture directory exists ──────────────────────────────────
    if not fixtures_dir.exists():
        print(f"FAIL: fixtures directory not found: {fixtures_dir}", file=sys.stderr)
        sys.exit(1)

    # ── Load repo lock ─────────────────────────────────────────────────
    lock_path = fixtures_dir / "repos.lock.jsonl"
    if not lock_path.exists():
        print(f"FAIL: repos.lock.jsonl not found: {lock_path}", file=sys.stderr)
        sys.exit(1)

    repo_lock: dict[str, dict[str, Any]] = {}
    with lock_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"repos.lock.jsonl line {i}: JSON parse error: {e}")
                continue
            repo_id = entry.get("repo_id", "")
            if not repo_id:
                errors.append(f"repos.lock.jsonl line {i}: missing repo_id")
                continue
            if repo_id in repo_lock:
                errors.append(f"repos.lock.jsonl: duplicate repo_id '{repo_id}'")
            repo_lock[repo_id] = entry

    known_repo_ids = set(repo_lock.keys())

    repo_file_line_counts: dict[str, dict[str, int]] = {}
    repo_manifest_checks: dict[str, dict[str, Any]] = {}
    for repo_id, entry in repo_lock.items():
        source = entry.get("source", {})
        repo_path = Path(source.get("path", ""))
        extensions = set(entry.get("metadata", {}).get("extensions", list(SOURCE_EXTENSIONS)))
        exclude_subdirs = entry.get("metadata", {}).get("exclude_subdirs", [])
        file_lines: dict[str, int] = {}
        if source.get("type") == "local_absolute_path" and repo_path.exists():
            for rel_path, full_path in find_source_files(repo_path, extensions, exclude_subdirs):
                try:
                    content = full_path.read_bytes()
                except OSError:
                    continue
                file_lines[rel_path] = content.count(b"\n") + 1
        repo_file_line_counts[repo_id] = file_lines
        repo_manifest_checks[repo_id] = {
            "repo_path": str(repo_path),
            "extensions": sorted(extensions),
            "exclude_subdirs": exclude_subdirs,
        }

    # ── Load tasks ─────────────────────────────────────────────────────
    tasks_path = fixtures_dir / "tasks" / "auto_stress.jsonl"
    if not tasks_path.exists():
        print(f"FAIL: tasks file not found: {tasks_path}", file=sys.stderr)
        sys.exit(1)

    tasks: list[dict[str, Any]] = []
    task_ids: set[str] = set()
    with tasks_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                task = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"tasks/auto_stress.jsonl line {i}: JSON parse error: {e}")
                continue
            tid = task.get("test_id", "")
            if not tid:
                errors.append(f"tasks/auto_stress.jsonl line {i}: missing test_id")
                continue
            if tid in task_ids:
                errors.append(f"tasks/auto_stress.jsonl: duplicate test_id '{tid}'")
            task_ids.add(tid)
            tasks.append(task)

    # ── Load labels ────────────────────────────────────────────────────
    labels_path = fixtures_dir / "labels" / "auto_stress.jsonl"
    if not labels_path.exists():
        print(f"FAIL: labels file not found: {labels_path}", file=sys.stderr)
        sys.exit(1)

    labels: list[dict[str, Any]] = []
    label_ids: set[str] = set()
    with labels_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                label = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"labels/auto_stress.jsonl line {i}: JSON parse error: {e}")
                continue
            tid = label.get("test_id", "")
            if not tid:
                errors.append(f"labels/auto_stress.jsonl line {i}: missing test_id")
                continue
            if tid in label_ids:
                errors.append(f"labels/auto_stress.jsonl: duplicate test_id '{tid}'")
            label_ids.add(tid)
            labels.append(label)

    # ── Load manifest ──────────────────────────────────────────────────
    manifest_path = fixtures_dir / "dataset_manifest.json"
    if not manifest_path.exists():
        errors.append("dataset_manifest.json not found")
        manifest = {}
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            errors.append(f"dataset_manifest.json: parse error: {e}")
            manifest = {}

    # VALIDATION 1: Public tasks must NOT contain private/leak fields
    print("Checking public tasks for private field leaks...")
    for task in tasks:
        tid = task.get("test_id", "?")
        for field in PRIVATE_FIELDS:
            if field in task:
                errors.append(f"Task {tid}: public task contains private field '{field}'")
        for field in task:
            if field not in PUBLIC_TASK_FIELDS:
                errors.append(f"Task {tid}: unexpected public field '{field}' (not in PUBLIC_TASK_FIELDS)")
        for field in PUBLIC_TASK_FIELDS:
            if field not in task:
                errors.append(f"Task {tid}: missing required public field '{field}'")
                continue
            if not isinstance(task[field], str):
                errors.append(f"Task {tid}: public field '{field}' must be string")
            elif not task[field]:
                errors.append(f"Task {tid}: public field '{field}' must be non-empty")

    # VALIDATION 2: Task IDs and label IDs must be bijective
    print("Checking task/label ID bijection...")
    only_in_tasks = task_ids - label_ids
    only_in_labels = label_ids - task_ids
    if only_in_tasks:
        errors.append(f"Tasks without labels: {sorted(only_in_tasks)[:10]}")
    if only_in_labels:
        errors.append(f"Labels without tasks: {sorted(only_in_labels)[:10]}")

    # VALIDATION 3: No unknown repo_ids
    print("Checking repo_id validity...")
    for task in tasks:
        rid = task.get("repo_id", "")
        if rid and rid not in known_repo_ids:
            errors.append(f"Task {task.get('test_id', '?')}: unknown repo_id '{rid}'")
    for label in labels:
        rid = label.get("repo_id", "")
        if rid and rid not in known_repo_ids:
            errors.append(f"Label {label.get('test_id', '?')}: unknown repo_id '{rid}'")

    # VALIDATION 4: Enum validity
    print("Checking enum validity...")
    for label in labels:
        tid = label.get("test_id", "?")
        eb = label.get("expected_behavior", "")
        if eb and eb not in EXPECTED_BEHAVIOR_ENUM:
            errors.append(f"Label {tid}: invalid expected_behavior '{eb}'")
        ot = label.get("oracle_type", "")
        if ot and ot not in ORACLE_TYPE_ENUM:
            errors.append(f"Label {tid}: invalid oracle_type '{ot}'")

    # VALIDATION 5: Label required-field schema hard validation
    print("Checking label required-field schema...")
    for label in labels:
        tid = label.get("test_id", "?")
        for field in label:
            if field not in LABEL_ALLOWED_FIELDS:
                errors.append(f"Label {tid}: unexpected label field '{field}'")
        for field, expected_type in LABEL_REQUIRED_FIELDS.items():
            if field not in label:
                errors.append(f"Label {tid}: missing required field '{field}'")
            elif not isinstance(label[field], expected_type):
                errors.append(
                    f"Label {tid}: field '{field}' has wrong type "
                    f"(expected {expected_type.__name__}, got {type(label[field]).__name__})"
                )
        # String fields must be non-empty
        for str_field in (
            "test_id", "repo_id", "query", "source_category", "risk_public",
            "oracle_type", "expected_behavior", "why_this_is_hard",
            "which_strategy_it_targets",
        ):
            val = label.get(str_field, "")
            if isinstance(val, str) and not val:
                errors.append(f"Label {tid}: required string field '{str_field}' is empty")

    # VALIDATION 5b: Span references must point to locked source files with
    # valid line ranges. Empty span lists are allowed for negative/ambiguous
    # stress cases, but non-empty spans must be concrete and current.
    print("Checking span path/range validity against locked source files...")
    for label in labels:
        tid = label.get("test_id", "?")
        repo_id = label.get("repo_id", "")
        file_lines = repo_file_line_counts.get(repo_id, {})
        for span_field in ("gold_spans", "hard_distractors", "must_not_primary"):
            spans = label.get(span_field, [])
            if not isinstance(spans, list):
                continue
            for idx, span in enumerate(spans):
                if not isinstance(span, dict):
                    errors.append(f"Label {tid}: {span_field}[{idx}] is not an object")
                    continue
                path = span.get("path", "")
                start = span.get("start_line", 0)
                end = span.get("end_line", 0)
                if not isinstance(path, str) or not path:
                    errors.append(f"Label {tid}: {span_field}[{idx}] missing non-empty path")
                    continue
                if not isinstance(start, int) or not isinstance(end, int):
                    errors.append(f"Label {tid}: {span_field}[{idx}] start_line/end_line must be integers")
                    continue
                if start <= 0 or end < start:
                    errors.append(f"Label {tid}: {span_field}[{idx}] invalid line range {start}-{end}")
                    continue
                total_lines = file_lines.get(path)
                if total_lines is None:
                    errors.append(f"Label {tid}: {span_field}[{idx}] path not in locked source files: {path}")
                    continue
                if end > total_lines:
                    errors.append(
                        f"Label {tid}: {span_field}[{idx}] line range {start}-{end} exceeds {path} total_lines={total_lines}"
                    )

    # VALIDATION 6: expected_behavior=primary_evidence must have gold_spans
    print("Checking expected_behavior / gold_spans consistency...")
    for label in labels:
        tid = label.get("test_id", "?")
        eb = label.get("expected_behavior", "")
        gs = label.get("gold_spans", [])
        if eb == "primary_evidence" and not gs:
            errors.append(f"Label {tid}: expected_behavior=primary_evidence but gold_spans is empty")
        if eb in ("abstain", "no_primary") and gs:
            errors.append(f"Label {tid}: expected_behavior={eb} but gold_spans is non-empty ({len(gs)} spans)")

    # VALIDATION 7: must_not_primary must not overlap gold_spans
    print("Checking must_not_primary / gold_spans overlap...")
    for label in labels:
        tid = label.get("test_id", "?")
        gs = label.get("gold_spans", [])
        mnp = label.get("must_not_primary", [])
        for m in mnp:
            for g in gs:
                if spans_overlap(m, g):
                    errors.append(
                        f"Label {tid}: must_not_primary overlaps gold_span "
                        f"(path={m.get('path')}, lines={m.get('start_line')}-{m.get('end_line')})"
                    )

    # VALIDATION 8: hard_distractors must not overlap gold_spans
    print("Checking hard_distractors / gold_spans overlap...")
    for label in labels:
        tid = label.get("test_id", "?")
        gs = label.get("gold_spans", [])
        hd = label.get("hard_distractors", [])
        for d in hd:
            for g in gs:
                if spans_overlap(d, g):
                    errors.append(
                        f"Label {tid}: hard_distractor overlaps gold_span "
                        f"(path={d.get('path')}, lines={d.get('start_line')}-{d.get('end_line')})"
                    )

    # VALIDATION 9: Category distribution — exact target counts by category
    print("Checking category distribution...")
    category_counts: dict[str, int] = {}
    for label in labels:
        cat = label.get("source_category", "")
        if not cat:
            errors.append(f"Label {label.get('test_id', '?')}: missing source_category")
        if cat:
            category_counts[cat] = category_counts.get(cat, 0) + 1

    # Check for unknown categories
    for cat in category_counts:
        if cat not in REQUIRED_CATEGORIES:
            errors.append(f"Unknown category '{cat}' found in labels/tasks")

    # Check required categories have exact target counts. R26 is generated by a
    # deterministic generator, so drift from target composition should be a hard
    # failure rather than a warning.
    for cat in REQUIRED_CATEGORIES:
        count = category_counts.get(cat, 0)
        if count == 0:
            errors.append(f"Required category '{cat}' is missing (0 tasks)")
        elif count != TARGET_COMPOSITION[cat]:
            errors.append(
                f"Required category '{cat}' has {count} tasks (expected exact target {TARGET_COMPOSITION[cat]})"
            )

    # Keep an explicit target-composition check so adding categories or changing
    # target counts is fail-closed.
    for cat, target in TARGET_COMPOSITION.items():
        count = category_counts.get(cat, 0)
        if count != target:
            errors.append(f"Category '{cat}' count {count} != target {target}")

    # VALIDATION 10: Total tasks >= 1000
    print("Checking total task count...")
    if len(tasks) < MIN_TOTAL_TASKS:
        errors.append(f"Total tasks {len(tasks)} < {MIN_TOTAL_TASKS}")

    # VALIDATION 11: Each repo must have >= 50 tasks
    print("Checking minimum tasks per repo...")
    repo_task_counts: dict[str, int] = {}
    for task in tasks:
        rid = task.get("repo_id", "")
        if rid:
            repo_task_counts[rid] = repo_task_counts.get(rid, 0) + 1
    for rid in repo_lock:
        count = repo_task_counts.get(rid, 0)
        if count < MIN_PER_REPO:
            errors.append(f"Repo '{rid}' has only {count} tasks (need >= {MIN_PER_REPO})")

    # VALIDATION 12: No canary tokens
    print("Checking for canary tokens...")
    for task in tasks:
        tid = task.get("test_id", "?")
        task_str = json.dumps(task)
        if check_canary(task_str):
            errors.append(f"Task {tid}: canary token found in public task")
    for label in labels:
        tid = label.get("test_id", "?")
        label_str = json.dumps(label)
        if check_canary(label_str):
            errors.append(f"Label {tid}: canary token found in label")

    # VALIDATION 13: dataset_manifest flags
    print("Checking dataset_manifest flags...")
    if manifest.get("not_promotion_evidence") != True:
        errors.append("dataset_manifest: not_promotion_evidence != true")
    if manifest.get("core_changes") != False:
        errors.append("dataset_manifest: core_changes != false")
    if manifest.get("remote_calls", -1) != 0:
        errors.append(f"dataset_manifest: remote_calls != 0 (got {manifest.get('remote_calls')})")
    if manifest.get("dense_or_llm_claims") != False:
        errors.append("dataset_manifest: dense_or_llm_claims != false")

    # VALIDATION 14: No unknown categories
    # (Already checked in VALIDATION 9)

    # VALIDATION 15: Schema separation (already checked in VALIDATION 1)

    # VALIDATION 16: Label-public task consistency
    print("Checking label-public task consistency...")
    task_by_id = {t.get("test_id"): t for t in tasks}
    for label in labels:
        tid = label.get("test_id", "")
        if tid in task_by_id:
            task = task_by_id[tid]
            if label.get("repo_id") != task.get("repo_id"):
                errors.append(
                    f"Label {tid}: repo_id mismatch (task={task.get('repo_id')}, label={label.get('repo_id')})"
                )
            if label.get("query") != task.get("query"):
                errors.append(
                    f"Label {tid}: query mismatch between public task and private label"
                )

    # VALIDATION 16b: Manifest count consistency
    print("Checking manifest count consistency...")
    status = manifest.get("current_status", {}).get("auto_stress", {})
    if status.get("tasks") != len(tasks):
        errors.append(f"dataset_manifest: current_status.auto_stress.tasks != actual ({status.get('tasks')} vs {len(tasks)})")
    if status.get("labels") != len(labels):
        errors.append(f"dataset_manifest: current_status.auto_stress.labels != actual ({status.get('labels')} vs {len(labels)})")
    if status.get("repos") != len(repo_lock):
        errors.append(f"dataset_manifest: current_status.auto_stress.repos != actual ({status.get('repos')} vs {len(repo_lock)})")
    if status.get("categories") != category_counts:
        errors.append("dataset_manifest: current_status.auto_stress.categories != actual category distribution")
    if manifest.get("target_composition") != TARGET_COMPOSITION:
        errors.append("dataset_manifest: target_composition != validator TARGET_COMPOSITION")

    # VALIDATION 17: Uniqueness (already checked during load)

    # VALIDATION 18: Repo existence (already checked in VALIDATION 3)

    print("Checking repo content manifest SHA locks...")
    for repo_id, entry in repo_lock.items():
        source = entry.get("source", {})
        if source.get("type") != "local_absolute_path":
            errors.append(f"Repo {repo_id}: unsupported source type {source.get('type')!r}")
            continue
        repo_path = Path(source.get("path", ""))
        if not repo_path.exists():
            errors.append(f"Repo {repo_id}: source path does not exist: {repo_path}")
            continue
        locked_sha = entry.get("content_manifest_sha", "")
        if not locked_sha:
            errors.append(f"Repo {repo_id}: missing content_manifest_sha")
            continue
        extensions = set(entry.get("metadata", {}).get("extensions", list(SOURCE_EXTENSIONS)))
        exclude_subdirs = entry.get("metadata", {}).get("exclude_subdirs", [])
        computed_sha, file_count, total_lines = compute_normalized_manifest_sha(
            repo_path, extensions, exclude_subdirs
        )
        if computed_sha != locked_sha:
            errors.append(
                f"Repo {repo_id}: content_manifest_sha mismatch "
                f"(locked={locked_sha}, computed={computed_sha}, files={file_count}, lines={total_lines})"
            )

    # VALIDATION 19: Deterministic manifest checks
    print("Checking deterministic manifest SHA256 checksums...")
    gen_info = manifest.get("generation_info", {})
    expected_tasks_sha = gen_info.get("tasks_sha256", "")
    expected_labels_sha = gen_info.get("labels_sha256", "")
    if not expected_tasks_sha:
        errors.append("dataset_manifest: missing generation_info.tasks_sha256")
    else:
        actual_tasks_sha = hashlib.sha256(tasks_path.read_bytes()).hexdigest()
        if actual_tasks_sha != expected_tasks_sha:
            errors.append(
                f"tasks_sha256 mismatch (expected={expected_tasks_sha}, actual={actual_tasks_sha})"
            )
    if not expected_labels_sha:
        errors.append("dataset_manifest: missing generation_info.labels_sha256")
    else:
        actual_labels_sha = hashlib.sha256(labels_path.read_bytes()).hexdigest()
        if actual_labels_sha != expected_labels_sha:
            errors.append(
                f"labels_sha256 mismatch (expected={expected_labels_sha}, actual={actual_labels_sha})"
            )

    # ── Write safety_checks.json ────────────────────────────────────────
    print("Writing safety_checks.json...")
    safety = {
        "total_checks": 19,
        "critical_issues": len(errors),
        "warning_issues": len(warnings),
        "issues": errors + [f"WARNING: {w}" for w in warnings],
        "passed": len(errors) == 0,
        "not_promotion_evidence": manifest.get("not_promotion_evidence", False),
        "core_changes": manifest.get("core_changes", True),
        "remote_calls": manifest.get("remote_calls", -1),
        "dense_or_llm_claims": manifest.get("dense_or_llm_claims", True),
        "task_count": len(tasks),
        "label_count": len(labels),
        "repo_count": len(repo_lock),
        "category_count": len(category_counts),
        "categories_meeting_minimum": sum(
            1 for cat in REQUIRED_CATEGORIES if category_counts.get(cat, 0) >= MIN_PER_CATEGORY
        ),
        "expected_behavior_distribution": {},
        "oracle_type_distribution": {},
        "category_distribution": category_counts,
        "target_composition": TARGET_COMPOSITION,
        "validation_timestamp": "2026-06-12",
    }

    for label in labels:
        eb = label.get("expected_behavior", "unknown")
        safety["expected_behavior_distribution"][eb] = safety["expected_behavior_distribution"].get(eb, 0) + 1
        ot = label.get("oracle_type", "unknown")
        safety["oracle_type_distribution"][ot] = safety["oracle_type_distribution"].get(ot, 0) + 1

    safety_path = fixtures_dir / "safety_checks.json"
    safety_path.write_text(json.dumps(safety, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # ── Report ──────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"R26 Auto-Stress-1000 Static Validation Results")
    print(f"{'='*60}")
    print(f"Tasks: {len(tasks)}")
    print(f"Labels: {len(labels)}")
    print(f"Repos: {len(repo_lock)}")
    print(f"Categories: {len(category_counts)}")
    print(f"Critical errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    print(f"")
    print(f"Category distribution:")
    for cat in sorted(REQUIRED_CATEGORIES):
        count = category_counts.get(cat, 0)
        target = TARGET_COMPOSITION.get(cat, 0)
        status = "OK" if count >= MIN_PER_CATEGORY else "BELOW_MIN"
        print(f"  {status} {cat}: {count} (target={target}, min={MIN_PER_CATEGORY})")
    print(f"")
    print(f"Repo distribution:")
    for rid in sorted(repo_task_counts):
        count = repo_task_counts[rid]
        status = "OK" if count >= MIN_PER_REPO else "BELOW_MIN"
        print(f"  {status} {rid}: {count}")
    print(f"")
    print(f"Expected behavior distribution:")
    for eb, count in sorted(safety["expected_behavior_distribution"].items()):
        print(f"  {eb}: {count}")
    print(f"")
    print(f"Oracle type distribution:")
    for ot, count in sorted(safety["oracle_type_distribution"].items()):
        print(f"  {ot}: {count}")

    if errors:
        print(f"\n{'='*60}")
        print(f"CRITICAL ERRORS ({len(errors)}):")
        print(f"{'='*60}")
        for err in errors:
            print(f"  X {err}")

    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  ! {w}")

    if errors:
        print(f"\nVALIDATION FAILED: {len(errors)} critical errors")
        sys.exit(1)
    else:
        print(f"\nVALIDATION PASSED: all checks OK")
        sys.exit(0)


if __name__ == "__main__":
    main()
