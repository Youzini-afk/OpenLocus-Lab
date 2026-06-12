#!/usr/bin/env python3
"""R20 Auto-Wide Retrieval Failure-Surface Benchmark Static Validator.

Validates the R20 dataset against strict schema and safety constraints.
This is a static validator only — no retrieval or scoring is performed.

This validator is FAIL-CLOSED: any violation is an error, not a warning.
Source paths must be accessible; manifest SHA must be verifiable;
public task fields are strictly limited; label schema is hard-validated.

Key validation rules:
  1. Public tasks must NOT contain any field outside PUBLIC_TASK_FIELDS (ERROR).
  2. Task IDs and label IDs must be bijective; no duplicates; no unknown repo_ids.
  3. Enum values must be valid (expected_behavior, oracle_type, label_quality).
  4. Label required fields must all be present with correct types.
  5. expected_behavior=primary_evidence must have gold_spans.
  6. expected_behavior in (abstain, no_primary) must have empty gold_spans.
  7. must_not_primary must not overlap gold_spans.
  8. hard_distractors must not overlap gold_spans.
  9. Path/range in gold_spans, hard_distractors, must_not_primary must exist
     in locked source and be in bounds.
  10. Repo lock content_manifest_sha must match recomputed SHA from source
      (source path inaccessible is ERROR, not warning).
  11. label_quality must NOT be human_reviewed.
  12. Required categories: all 25 must be present, each >= 5 tasks.
  13. Repo count >= 9, total tasks >= 300, every repo in repo_lock >= 15 tasks.
  14. dataset_manifest must have not_promotion_evidence=true,
      core_changes=false, remote_calls=0, dense_or_llm_claims=false.
  15. Writes safety_checks.json and coverage_report.json with counts.

Usage:
    python3 eval/r20_static_validate.py --workspace . --fixtures fixtures/r20_auto_wide
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
})

EXPECTED_BEHAVIOR_ENUM = {
    "primary_evidence", "supporting_only", "weak_candidates",
    "abstain", "no_primary",
}

ORACLE_TYPE_ENUM = {
    "deterministic", "mined", "differential", "metamorphic", "stress",
}

LABEL_QUALITY_ENUM = {
    "mined_high_confidence", "mined", "weak",
}

REQUIRED_CATEGORIES = [
    "positive_exact_symbol", "positive_regex_anchor",
    "positive_natural_language", "positive_issue_style",
    "negative_nonexistent_symbol", "negative_nonexistent_feature",
    "ambiguous_query", "vague_query", "hard_distractor",
    "same_name_symbol", "frontend_backend_confusion",
    "test_source_confusion", "docs_source_confusion",
    "generated_vendor_trap", "config_key_trap",
    "route_handler_trap", "stacktrace_style",
    "dirty_overlay", "deleted_file", "renamed_file",
    "branch_switch_like", "stale_index_candidate",
    "graph_neighbor_trap", "dense_semantic_trap",
    "proper_name_api_config_regression",
]

PUBLIC_TASK_FIELDS = {"task_id", "repo_id", "query", "public_version", "source_tier"}

SOURCE_EXTENSIONS = {".rs", ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".mjs"}

SKIP_DIR_NAMES = {
    "node_modules", "target", ".git", "dist", "build", ".venv",
    "__pycache__", ".next", ".nuxt", "runs", "fixtures", "eval",
    "docs", ".openlocus", "coverage", ".cache", ".mypy_cache",
    ".pytest_cache", ".tox", "venv", "env", ".env", ".idea",
    ".vscode", "out", "bin", "obj",
}

BENCHMARK_EXCLUDES = [
    "fixtures/**", "eval/**", "docs/**", "runs/**", ".openlocus/**",
    "target/**", "__pycache__/**", "*.tmp", "*.log", ".git/**",
    "node_modules/**", "dist/**", "build/**", ".venv/**", ".next/**",
    ".nuxt/**", "coverage/**", "*.pyc",
]


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
    """Check if two spans overlap on the same path."""
    if a.get("path") != b.get("path"):
        return False
    a_start = int(a.get("start_line", 0))
    a_end = int(a.get("end_line", 0))
    b_start = int(b.get("start_line", 0))
    b_end = int(b.get("end_line", 0))
    if a_start <= 0 or a_end < a_start or b_start <= 0 or b_end < b_start:
        return False
    return a_start <= b_end and b_start <= a_end


# ── Main validation ────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="R20 auto-wide retrieval failure-surface benchmark static validator"
    )
    parser.add_argument(
        "--workspace", default=".",
        help="Workspace root (containing eval/, fixtures/, etc.)"
    )
    parser.add_argument(
        "--fixtures", default="fixtures/r20_auto_wide",
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
    repo_line_counts: dict[str, dict[str, int]] = {}  # repo_id -> {rel_path: line_count}
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

    # ── Load tasks ─────────────────────────────────────────────────────
    tasks_path = fixtures_dir / "tasks" / "auto_wide.jsonl"
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
                errors.append(f"tasks/auto_wide.jsonl line {i}: JSON parse error: {e}")
                continue
            tid = task.get("task_id", "")
            if not tid:
                errors.append(f"tasks/auto_wide.jsonl line {i}: missing task_id")
                continue
            if tid in task_ids:
                errors.append(f"tasks/auto_wide.jsonl: duplicate task_id '{tid}'")
            task_ids.add(tid)
            tasks.append(task)

    # ── Load labels ────────────────────────────────────────────────────
    labels_path = fixtures_dir / "labels" / "auto_wide.jsonl"
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
                errors.append(f"labels/auto_wide.jsonl line {i}: JSON parse error: {e}")
                continue
            tid = label.get("task_id", "")
            if not tid:
                errors.append(f"labels/auto_wide.jsonl line {i}: missing task_id")
                continue
            if tid in label_ids:
                errors.append(f"labels/auto_wide.jsonl: duplicate task_id '{tid}'")
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

    # ── Validation 1: Public tasks must NOT contain private/leak fields ─
    print("Checking public tasks for private field leaks...")
    for i, task in enumerate(tasks):
        tid = task.get("task_id", f"line_{i}")
        for field in PRIVATE_FIELDS:
            if field in task:
                errors.append(f"Task {tid}: public task contains private field '{field}'")
        # Also check for any field not in allowed public fields — ERROR, not warning
        for field in task:
            if field not in PUBLIC_TASK_FIELDS:
                errors.append(f"Task {tid}: unexpected public field '{field}' (not in PUBLIC_TASK_FIELDS)")

    # ── Validation 2: Task IDs and label IDs must be bijective ──────────
    print("Checking task/label ID bijection...")
    task_id_set = set(t.get("task_id", "") for t in tasks)
    label_id_set = set(l.get("task_id", "") for l in labels)

    only_in_tasks = task_id_set - label_id_set
    only_in_labels = label_id_set - task_id_set
    if only_in_tasks:
        errors.append(f"Tasks without labels: {sorted(only_in_tasks)[:10]}")
    if only_in_labels:
        errors.append(f"Labels without tasks: {sorted(only_in_labels)[:10]}")

    # ── Validation 3: No unknown repo_ids ───────────────────────────────
    print("Checking repo_id validity...")
    for task in tasks:
        rid = task.get("repo_id", "")
        if rid and rid not in known_repo_ids:
            errors.append(f"Task {task.get('task_id', '?')}: unknown repo_id '{rid}'")
    for label in labels:
        rid = label.get("repo_id", "")
        if rid and rid not in known_repo_ids:
            errors.append(f"Label {label.get('task_id', '?')}: unknown repo_id '{rid}'")

    # ── Validation 4: Enum validity ────────────────────────────────────
    print("Checking enum validity...")
    label_by_id = {l["task_id"]: l for l in labels}
    for label in labels:
        tid = label.get("task_id", "?")
        eb = label.get("expected_behavior", "")
        if eb and eb not in EXPECTED_BEHAVIOR_ENUM:
            errors.append(f"Label {tid}: invalid expected_behavior '{eb}'")
        ot = label.get("oracle_type", "")
        if ot and ot not in ORACLE_TYPE_ENUM:
            errors.append(f"Label {tid}: invalid oracle_type '{ot}'")
        lq = label.get("label_quality", "")
        if lq and lq not in LABEL_QUALITY_ENUM:
            errors.append(f"Label {tid}: invalid label_quality '{lq}'")

    # ── Validation 5: Label required-field schema hard validation ─────────
    print("Checking label required-field schema...")
    LABEL_REQUIRED_FIELDS: dict[str, type] = {
        "task_id": str,
        "repo_id": str,
        "query_category": str,
        "intent_guess": str,
        "risk_tags": list,
        "oracle_type": str,
        "expected_behavior": str,
        "label_quality": str,
        "gold_spans": list,
        "hard_distractors": list,
        "must_not_primary": list,
        "why_this_is_hard": str,
        "which_strategy_it_targets": str,
        "caveat": str,
    }
    for label in labels:
        tid = label.get("task_id", "?")
        for field, expected_type in LABEL_REQUIRED_FIELDS.items():
            if field not in label:
                errors.append(f"Label {tid}: missing required field '{field}'")
            elif not isinstance(label[field], expected_type):
                errors.append(
                    f"Label {tid}: field '{field}' has wrong type "
                    f"(expected {expected_type.__name__}, got {type(label[field]).__name__})"
                )
        # String fields must be non-empty (except caveat which may be "")
        for str_field in ("task_id", "repo_id", "query_category", "oracle_type",
                          "expected_behavior", "label_quality", "why_this_is_hard",
                          "which_strategy_it_targets"):
            val = label.get(str_field, "")
            if isinstance(val, str) and not val:
                errors.append(f"Label {tid}: required string field '{str_field}' is empty")

    # ── Validation 6: expected_behavior=primary_evidence must have gold_spans
    print("Checking expected_behavior / gold_spans consistency...")
    for label in labels:
        tid = label.get("task_id", "?")
        eb = label.get("expected_behavior", "")
        gs = label.get("gold_spans", [])

        if eb == "primary_evidence" and not gs:
            errors.append(f"Label {tid}: expected_behavior=primary_evidence but gold_spans is empty")

        if eb in ("abstain", "no_primary") and gs:
            errors.append(f"Label {tid}: expected_behavior={eb} but gold_spans is non-empty ({len(gs)} spans)")

    # ── Validation 6: must_not_primary must not overlap gold_spans ──────
    print("Checking must_not_primary / gold_spans overlap...")
    for label in labels:
        tid = label.get("task_id", "?")
        gs = label.get("gold_spans", [])
        mnp = label.get("must_not_primary", [])
        for m in mnp:
            for g in gs:
                if spans_overlap(m, g):
                    errors.append(
                        f"Label {tid}: must_not_primary overlaps gold_span "
                        f"(path={m.get('path')}, lines={m.get('start_line')}-{m.get('end_line')})"
                    )

    # ── Validation 7: hard_distractors must not overlap gold_spans ─────
    print("Checking hard_distractors / gold_spans overlap...")
    for label in labels:
        tid = label.get("task_id", "?")
        gs = label.get("gold_spans", [])
        hd = label.get("hard_distractors", [])
        for d in hd:
            for g in gs:
                if spans_overlap(d, g):
                    errors.append(
                        f"Label {tid}: hard_distractor overlaps gold_span "
                        f"(path={d.get('path')}, lines={d.get('start_line')}-{d.get('end_line')})"
                    )

    # ── Validation 8: Path/range in gold_spans / hard_distractors / must_not_primary must exist in source ─
    print("Checking gold_span / hard_distractors / must_not_primary path/range validity against locked source...")
    # Build file content cache per repo
    repo_file_cache: dict[str, dict[str, Any]] = {}  # repo_id -> {rel_path: {"lines": N, "sha": str}}
    for repo_id, entry in repo_lock.items():
        source = entry.get("source", {})
        source_path = source.get("path", "")
        if not source_path or not Path(source_path).exists():
            errors.append(f"Repo {repo_id}: source path not accessible: {source_path}")
            continue
        repo_path = Path(source_path)
        extensions = set(entry.get("metadata", {}).get("extensions", [".rs"]))
        exclude_subdirs = entry.get("metadata", {}).get("exclude_subdirs", [])
        cache: dict[str, Any] = {}
        for rel, full_path in find_source_files(repo_path, extensions, exclude_subdirs):
            try:
                content = full_path.read_bytes()
                cache[rel] = {
                    "lines": content.count(b"\n") + 1,
                    "sha": hashlib.sha256(content).hexdigest(),
                }
            except OSError:
                pass
        repo_file_cache[repo_id] = cache

    def validate_span_list(label: dict[str, Any], field_name: str, display_name: str) -> None:
        tid = label.get("task_id", "?")
        rid = label.get("repo_id", "")
        spans = label.get(field_name, [])
        if not isinstance(spans, list):
            errors.append(f"Label {tid}: {field_name} must be a list")
            return
        cache = repo_file_cache.get(rid, {})
        for idx, span in enumerate(spans):
            if not isinstance(span, dict):
                errors.append(f"Label {tid}: {display_name}[{idx}] must be an object")
                continue
            path = span.get("path")
            start = span.get("start_line")
            end = span.get("end_line")
            if not isinstance(path, str) or not path:
                errors.append(f"Label {tid}: {display_name}[{idx}] missing non-empty path")
                continue
            if not isinstance(start, int) or not isinstance(end, int):
                errors.append(
                    f"Label {tid}: {display_name}[{idx}] start_line/end_line must be integers"
                )
                continue
            if path not in cache:
                errors.append(
                    f"Label {tid}: {display_name} path '{path}' not found in locked source for repo '{rid}'"
                )
                continue
            total_lines = cache[path]["lines"]
            if start < 1 or end < start or end > total_lines:
                errors.append(
                    f"Label {tid}: {display_name} range [{start},{end}] out of bounds "
                    f"for '{path}' (total_lines={total_lines})"
                )

    for label in labels:
        validate_span_list(label, "gold_spans", "gold_span")
        validate_span_list(label, "hard_distractors", "hard_distractor")
        validate_span_list(label, "must_not_primary", "must_not_primary")

    # ── Validation 9: Repo lock content_manifest_sha verification ──────
    print("Verifying repo lock content manifest SHA...")
    for repo_id, entry in repo_lock.items():
        expected_sha = entry.get("content_manifest_sha", "")
        source = entry.get("source", {})
        source_path = source.get("path", "")
        if not source_path or not Path(source_path).exists():
            errors.append(f"Repo {repo_id}: cannot verify manifest SHA — source path not accessible: {source_path}")
            continue
        extensions = set(entry.get("metadata", {}).get("extensions", [".rs"]))
        exclude_subdirs = entry.get("metadata", {}).get("exclude_subdirs", [])
        computed_sha, _, _ = compute_normalized_manifest_sha(
            Path(source_path), extensions, exclude_subdirs
        )
        if computed_sha != expected_sha:
            errors.append(
                f"Repo {repo_id}: content_manifest_sha mismatch "
                f"(expected={expected_sha}, computed={computed_sha})"
            )

    # ── Validation 10: label_quality must NOT be human_reviewed ─────────
    print("Checking label_quality != human_reviewed...")
    for label in labels:
        tid = label.get("task_id", "?")
        lq = label.get("label_quality", "")
        if lq == "human_reviewed":
            errors.append(f"Label {tid}: label_quality=human_reviewed is forbidden in R20")

    # ── Validation 11: Required categories coverage ─────────────────────
    print("Checking required category coverage...")
    category_counts: dict[str, int] = {}
    for label in labels:
        cat = label.get("query_category", "")
        if cat:
            category_counts[cat] = category_counts.get(cat, 0) + 1

    for cat in REQUIRED_CATEGORIES:
        count = category_counts.get(cat, 0)
        if count == 0:
            errors.append(f"Required category '{cat}' is missing (0 tasks)")
        elif count < 5:
            errors.append(f"Required category '{cat}' has only {count} tasks (need >= 5)")

    # ── Validation 12: Repo count >= 9, total >= 300, each repo >= 15 ──
    print("Checking scale requirements...")
    if len(repo_lock) < 9:
        errors.append(f"Repo count {len(repo_lock)} < 9")

    if len(tasks) < 300:
        errors.append(f"Total tasks {len(tasks)} < 300")

    repo_task_counts: dict[str, int] = {}
    for task in tasks:
        rid = task.get("repo_id", "")
        if rid:
            repo_task_counts[rid] = repo_task_counts.get(rid, 0) + 1
    # Check ALL repos in repo_lock, not just those with tasks
    for rid in repo_lock:
        count = repo_task_counts.get(rid, 0)
        if count < 15:
            errors.append(f"Repo '{rid}' has only {count} tasks (need >= 15)")

    # ── Validation 13: dataset_manifest flags ───────────────────────────
    print("Checking dataset_manifest flags...")
    if manifest.get("not_promotion_evidence") != True:
        errors.append("dataset_manifest: not_promotion_evidence != true")
    if manifest.get("core_changes") != False:
        errors.append("dataset_manifest: core_changes != false")
    if manifest.get("remote_calls", -1) != 0:
        errors.append(f"dataset_manifest: remote_calls != 0 (got {manifest.get('remote_calls')})")
    if manifest.get("dense_or_llm_claims") != False:
        errors.append("dataset_manifest: dense_or_llm_claims != false")

    # ── Write safety_checks.json ────────────────────────────────────────
    print("Writing safety_checks.json...")
    safety = {
        "total_checks": 14,
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
            1 for cat in REQUIRED_CATEGORIES if category_counts.get(cat, 0) >= 5
        ),
        "label_quality_distribution": {},
        "expected_behavior_distribution": {},
        "oracle_type_distribution": {},
        "validation_timestamp": "2026-06-12",
    }

    # Compute distributions
    for label in labels:
        lq = label.get("label_quality", "unknown")
        safety["label_quality_distribution"][lq] = safety["label_quality_distribution"].get(lq, 0) + 1
        eb = label.get("expected_behavior", "unknown")
        safety["expected_behavior_distribution"][eb] = safety["expected_behavior_distribution"].get(eb, 0) + 1
        ot = label.get("oracle_type", "unknown")
        safety["oracle_type_distribution"][ot] = safety["oracle_type_distribution"].get(ot, 0) + 1

    safety_path = fixtures_dir / "safety_checks.json"
    safety_path.write_text(json.dumps(safety, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # ── Write coverage_report.json ─────────────────────────────────────
    print("Writing coverage_report.json...")
    coverage: dict[str, Any] = {
        "by_category": category_counts,
        "by_repo": repo_task_counts,
        "by_language": {},
        "by_oracle": safety["oracle_type_distribution"],
        "by_expected": safety["expected_behavior_distribution"],
        "by_risk_tags": {},
        "coverage_gaps": [],
    }

    # Language distribution
    for task in tasks:
        rid = task.get("repo_id", "")
        if rid in repo_lock:
            langs = [repo_lock[rid].get("language", {}).get("primary", "unknown")]
            langs.extend(repo_lock[rid].get("language", {}).get("secondary", []))
        else:
            langs = ["unknown"]
        for lang in langs:
            coverage["by_language"][lang] = coverage["by_language"].get(lang, 0) + 1

    # Risk tags distribution
    for label in labels:
        for rt in label.get("risk_tags", []):
            coverage["by_risk_tags"][rt] = coverage["by_risk_tags"].get(rt, 0) + 1

    # Coverage gaps
    for cat in REQUIRED_CATEGORIES:
        count = category_counts.get(cat, 0)
        if count < 5:
            coverage["coverage_gaps"].append(
                f"Category '{cat}' has {count} tasks (need >= 5)"
            )
    for rid, count in repo_task_counts.items():
        if count < 15:
            coverage["coverage_gaps"].append(
                f"Repo '{rid}' has {count} tasks (need >= 15)"
            )

    cov_path = fixtures_dir / "coverage_report.json"
    cov_path.write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # ── Report ──────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"R20 Static Validation Results")
    print(f"{'='*60}")
    print(f"Tasks: {len(tasks)}")
    print(f"Labels: {len(labels)}")
    print(f"Repos: {len(repo_lock)}")
    print(f"Categories: {len(category_counts)}")
    print(f"Critical errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    print(f"")
    print(f"Category coverage:")
    for cat in REQUIRED_CATEGORIES:
        count = category_counts.get(cat, 0)
        status = "✓" if count >= 5 else "✗"
        print(f"  {status} {cat}: {count}")
    print(f"")
    print(f"Repo coverage:")
    for rid in sorted(repo_task_counts):
        count = repo_task_counts[rid]
        status = "✓" if count >= 15 else "✗"
        print(f"  {status} {rid}: {count}")
    print(f"")
    print(f"Label quality distribution:")
    for lq, count in sorted(safety["label_quality_distribution"].items()):
        print(f"  {lq}: {count}")
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
            print(f"  ✗ {err}")

    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠ {w}")

    if errors:
        print(f"\nVALIDATION FAILED: {len(errors)} critical errors")
        sys.exit(1)
    else:
        print(f"\nVALIDATION PASSED: all checks OK")
        sys.exit(0)


if __name__ == "__main__":
    main()
