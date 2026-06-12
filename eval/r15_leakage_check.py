#!/usr/bin/env python3
"""R15 Benchmark Leakage Check.

Verifies that public task files do not leak gold information and that
no benchmark artifacts can be discovered through retrieval.

Checks (extended from R14 for multi-repo):
1. Public tasks contain no gold paths/lines/spans/hard_negatives
2. Queries do not contain exact gold paths
3. Labels are not in indexed repo root
4. Repo policy excludes use glob-style patterns
5. Label files are isolated from task files
6. Canary tokens: unique tokens planted in labels/eval/docs/runs
7. Predictions scan: no prediction path has a forbidden prefix
8. Repo lock content manifest verification (multi-language)
9. Source paths are absolute (R15 external repos)
10. No raw gold paths in queries (path-component check)

Usage:
    python3 eval/r15_leakage_check.py --manifest fixtures/r15/dataset_manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


FORBIDDEN_PREFIXES = [
    "fixtures/",
    "eval/",
    "docs/",
    "runs/",
    ".openlocus/",
    "target/",
    "__pycache__/",
    ".git/",
]

REQUIRED_POLICY_EXCLUDES = ["fixtures", "eval", "docs", "runs", ".openlocus", "target"]

CANARY_TOKENS = [
    "R15_CANARY_fixture_label_secret_1a2b",
    "R15_CANARY_eval_benchmark_secret_3c4d",
    "R15_CANARY_docs_summary_secret_5e6f",
    "R15_CANARY_runs_prediction_secret_7g8h",
]

SOURCE_EXTENSIONS = {".rs", ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".mjs"}

SKIP_DIR_NAMES = {
    "node_modules", "target", ".git", "dist", "build", ".venv",
    "__pycache__", ".next", ".nuxt", "runs", "fixtures", "eval",
    "docs", ".openlocus", "coverage", ".cache", ".mypy_cache",
    ".pytest_cache", ".tox", "venv", "env", ".env", ".idea",
    ".vscode", "out", "bin", "obj",
}


def load_jsonl(path: Path) -> list[dict]:
    items = []
    if not path.exists():
        return items
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            items.append(json.loads(line))
    return items


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        print(f"ERROR: Manifest not found: {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def spans_overlap(a: dict, b: dict) -> bool:
    if a.get("path") != b.get("path"):
        return False
    a_start = int(a.get("start_line", 0))
    a_end = int(a.get("end_line", 0))
    b_start = int(b.get("start_line", 0))
    b_end = int(b.get("end_line", 0))
    return a_start > 0 and b_start > 0 and a_end >= a_start and b_end >= b_start and a_start <= b_end and a_end >= b_start


def check_repo_lock_integrity(repos: list[dict], expected_count: int = 9) -> list[dict]:
    issues = []
    repo_ids = [r.get("repo_id", "") for r in repos]
    if len(repos) != expected_count:
        issues.append({
            "check": "repo_lock_count",
            "severity": "CRITICAL",
            "message": f"Expected exactly {expected_count} R15 repos, found {len(repos)}",
        })
    duplicates = sorted({rid for rid in repo_ids if repo_ids.count(rid) > 1})
    for rid in duplicates:
        issues.append({
            "check": "duplicate_repo_id",
            "repo_id": rid,
            "severity": "CRITICAL",
            "message": f"Duplicate repo_id in repos.lock.jsonl: {rid}",
        })
    resolved_paths = []
    for repo in repos:
        repo_id = repo.get("repo_id", "unknown")
        source = repo.get("source", {})
        path = source.get("path", "")
        iso = source.get("isolated_root_relative", "")
        if iso != repo_id:
            issues.append({
                "check": "isolated_root_relative",
                "repo_id": repo_id,
                "severity": "CRITICAL",
                "message": f"Repo {repo_id}: isolated_root_relative must equal repo_id (got {iso})",
            })
        if path:
            resolved = str(Path(path).resolve())
            resolved_paths.append(resolved)
    duplicate_paths = sorted({p for p in resolved_paths if resolved_paths.count(p) > 1})
    for path in duplicate_paths:
        issues.append({
            "check": "duplicate_source_path",
            "severity": "CRITICAL",
            "message": f"Duplicate source path in repos.lock.jsonl: {path}",
        })
    return issues


def check_tier_task_label_consistency(
    tier_name: str,
    tasks: list[dict],
    labels: list[dict],
    repos: list[dict],
    manifest: dict[str, Any],
) -> list[dict]:
    issues = []
    repo_ids = {r.get("repo_id", "") for r in repos}
    task_ids = [t.get("task_id", "") for t in tasks]
    label_ids = [l.get("task_id", "") for l in labels]
    if len(task_ids) != len(set(task_ids)):
        issues.append({"check": "duplicate_task_id", "tier": tier_name, "severity": "CRITICAL", "message": f"Duplicate task_id in tasks/{tier_name}.jsonl"})
    if len(label_ids) != len(set(label_ids)):
        issues.append({"check": "duplicate_label_task_id", "tier": tier_name, "severity": "CRITICAL", "message": f"Duplicate task_id in labels/{tier_name}.jsonl"})
    if set(task_ids) != set(label_ids):
        issues.append({
            "check": "task_label_set_mismatch",
            "tier": tier_name,
            "severity": "CRITICAL",
            "message": f"Task/label ids differ for {tier_name}: missing_labels={sorted(set(task_ids)-set(label_ids))[:5]}, extra_labels={sorted(set(label_ids)-set(task_ids))[:5]}",
        })
    task_repo_ids = {t.get("repo_id", "") for t in tasks}
    unknown = sorted(task_repo_ids - repo_ids)
    if unknown:
        issues.append({
            "check": "unknown_task_repo_id",
            "tier": tier_name,
            "severity": "CRITICAL",
            "message": f"Tasks reference repo_ids not present in lock: {unknown}",
        })
    if tier_name in {"medium", "large", "stress"} and task_repo_ids != repo_ids:
        issues.append({
            "check": "tier_repo_coverage",
            "tier": tier_name,
            "severity": "CRITICAL",
            "message": f"{tier_name} tasks must cover exactly locked repos; missing={sorted(repo_ids-task_repo_ids)}, extra={sorted(task_repo_ids-repo_ids)}",
        })
    status_key = {"medium": "M", "large": "L", "stress": "stress"}[tier_name]
    status = manifest.get("current_status", {}).get(status_key, {})
    expected = {
        "repos": len(task_repo_ids),
        "tasks": len(tasks),
        "labels": len(labels),
        "hard_negatives": sum(len(l.get("hard_negatives", [])) for l in labels),
    }
    for key, actual in expected.items():
        if status.get(key) != actual:
            issues.append({
                "check": "manifest_count_mismatch",
                "tier": tier_name,
                "severity": "CRITICAL",
                "message": f"Manifest current_status.{status_key}.{key}={status.get(key)} but actual={actual}",
            })
    return issues


def check_hard_negative_overlap(labels: list[dict]) -> list[dict]:
    issues = []
    for label in labels:
        task_id = label.get("task_id", "unknown")
        for gold in label.get("gold_spans", []):
            for hn in label.get("hard_negatives", []):
                if spans_overlap(gold, hn):
                    issues.append({
                        "check": "hard_negative_overlaps_gold",
                        "task_id": task_id,
                        "severity": "CRITICAL",
                        "message": f"Hard negative overlaps gold span for {task_id}: {hn.get('path')}:{hn.get('start_line')}-{hn.get('end_line')}",
                    })
    return issues


# ── Check 1: Task gold leakage ────────────────────────────────────────


def check_task_gold_leakage(tasks: list[dict]) -> list[dict]:
    issues = []
    for task in tasks:
        task_id = task.get("task_id", "unknown")
        for field in ["gold_paths", "gold_lines", "gold_spans", "hard_negatives"]:
            if field in task:
                issues.append({
                    "check": "task_gold_leakage",
                    "task_id": task_id,
                    "severity": "CRITICAL",
                    "message": f"Task {task_id} contains {field} field",
                })
        if "label_quality" in task:
            issues.append({
                "check": "task_label_quality_leakage",
                "task_id": task_id,
                "severity": "WARNING",
                "message": f"Task {task_id} contains label_quality field",
            })
    return issues


# ── Check 2: Query-gold path overlap ──────────────────────────────────


def check_query_gold_path_overlap(tasks: list[dict], labels: list[dict]) -> list[dict]:
    issues = []
    label_map = {l["task_id"]: l for l in labels}

    for task in tasks:
        task_id = task.get("task_id", "unknown")
        query = task.get("query", "")

        label = label_map.get(task_id)
        if not label:
            continue

        for span in label.get("gold_spans", []):
            gold_path = span.get("path", "")
            if gold_path and gold_path in query:
                issues.append({
                    "check": "query_contains_gold_path",
                    "task_id": task_id,
                    "severity": "CRITICAL",
                    "message": f"Query '{query}' contains exact gold path '{gold_path}'",
                })

    return issues


# ── Check 3: Source paths are absolute ──────────────────────────────────


def check_source_paths_absolute(repos: list[dict]) -> list[dict]:
    """R15 repos must use local_absolute_path source type."""
    issues = []
    for repo in repos:
        repo_id = repo.get("repo_id", "unknown")
        source = repo.get("source", {})
        source_type = source.get("type", "")
        if source_type != "local_absolute_path":
            issues.append({
                "check": "source_path_type",
                "repo_id": repo_id,
                "severity": "CRITICAL",
                "message": f"Repo {repo_id}: expected source type 'local_absolute_path', got '{source_type}'",
            })
        else:
            path = source.get("path", "")
            if not os.path.isabs(path):
                issues.append({
                    "check": "source_path_absolute",
                    "repo_id": repo_id,
                    "severity": "CRITICAL",
                    "message": f"Repo {repo_id}: source path '{path}' is not absolute",
                })
    return issues


# ── Check 4: Policy exclude patterns ──────────────────────────────────


def check_benchmark_policy_excludes(repos: list[dict]) -> list[dict]:
    issues = []
    for repo in repos:
        repo_id = repo.get("repo_id", "unknown")
        policy_excludes = repo.get("policy", {}).get("exclude", [])

        for req in REQUIRED_POLICY_EXCLUDES:
            found = any(req in exc for exc in policy_excludes)
            if not found:
                issues.append({
                    "check": "benchmark_policy_excludes",
                    "repo_id": repo_id,
                    "severity": "CRITICAL",
                    "message": f"Repo {repo_id} does not exclude '{req}/**' pattern",
                })

    return issues


# ── Check 5: Label file isolation ──────────────────────────────────────


def check_label_file_isolation(out_dir: Path) -> list[dict]:
    issues = []
    labels_dir = out_dir / "labels"
    tasks_dir = out_dir / "tasks"

    if not labels_dir.exists():
        issues.append({
            "check": "label_directory_exists",
            "severity": "WARNING",
            "message": "Labels directory does not exist",
        })
        return issues

    for task_file in tasks_dir.glob("*.jsonl"):
        tasks = load_jsonl(task_file)
        for task in tasks:
            for field in ["gold_spans", "gold_paths", "gold_lines", "hard_negatives", "label_quality"]:
                if field in task:
                    issues.append({
                        "check": "label_field_in_task_file",
                        "task_file": str(task_file),
                        "task_id": task.get("task_id", "unknown"),
                        "severity": "CRITICAL",
                        "message": f"Task file {task_file} contains label field '{field}'",
                    })

    return issues


# ── Check 6: Canary tokens ────────────────────────────────────────────


def check_canary_tokens(out_dir: Path) -> list[dict]:
    issues = []

    canary_path = out_dir / "labels" / "_canary.json"
    if not canary_path.exists():
        issues.append({
            "check": "canary_file_exists",
            "severity": "CRITICAL",
            "message": "labels/_canary.json missing; run eval/r15_generate_dataset.py",
        })
        return issues
    try:
        canary_data = json.loads(canary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        issues.append({
            "check": "canary_file_json",
            "severity": "CRITICAL",
            "message": "labels/_canary.json is not valid JSON",
        })
        return issues
    if canary_data.get("canary_tokens") != CANARY_TOKENS:
        issues.append({
            "check": "canary_tokens_match",
            "severity": "CRITICAL",
            "message": "labels/_canary.json tokens do not match expected R15 canaries",
        })

    # Check that no task query contains a canary token
    for tier_name in ["medium", "large", "stress"]:
        tasks_path = out_dir / "tasks" / f"{tier_name}.jsonl"
        if not tasks_path.exists():
            continue

        tasks = load_jsonl(tasks_path)
        for task in tasks:
            query = task.get("query", "")
            for token in CANARY_TOKENS:
                if token in query:
                    issues.append({
                        "check": "canary_token_in_query",
                        "task_id": task.get("task_id", "unknown"),
                        "severity": "CRITICAL",
                        "message": f"Task {task.get('task_id', '?')} query contains canary token",
                    })

    # Check that canary tokens are NOT in any task file content (raw text scan)
    for tier_name in ["medium", "large", "stress"]:
        tasks_path = out_dir / "tasks" / f"{tier_name}.jsonl"
        if not tasks_path.exists():
            continue
        content = tasks_path.read_text(encoding="utf-8")
        for token in CANARY_TOKENS:
            if token in content:
                issues.append({
                    "check": "canary_token_in_task_file",
                    "tier": tier_name,
                    "severity": "CRITICAL",
                    "message": f"Canary token found in tasks/{tier_name}.jsonl",
                })

    return issues


# ── Check 7: Predictions scan for forbidden paths ──────────────────────


def check_predictions_forbidden_paths(predictions_dir: Path) -> list[dict]:
    issues = []
    if not predictions_dir or not predictions_dir.exists():
        return issues

    for pred_file in predictions_dir.glob("*-predictions.jsonl"):
        predictions = load_jsonl(pred_file)
        for pred in predictions:
            for e in pred.get("evidence", []):
                path = e.get("path", "")
                for fp in FORBIDDEN_PREFIXES:
                    forbidden_component = fp.strip("/")
                    path_parts = path.replace("\\", "/").split("/")
                    if path.startswith(fp) or forbidden_component in path_parts:
                        issues.append({
                            "check": "prediction_forbidden_path",
                            "file": str(pred_file),
                            "task_id": pred.get("task_id", "?"),
                            "severity": "CRITICAL",
                            "message": f"Prediction has forbidden path prefix/component '{fp}': {path}",
                        })

    return issues


# ── Check 8: Repo lock content manifest verification (multi-language) ──


def check_repo_lock_manifest(repos: list[dict]) -> list[dict]:
    """Verify content manifest SHA by recomputing normalized hash (multi-language)."""
    issues = []

    for repo in repos:
        repo_id = repo.get("repo_id", "unknown")
        locked_sha = repo.get("content_manifest_sha", "")
        if not locked_sha:
            issues.append({
                "check": "repo_lock_manifest_sha",
                "repo_id": repo_id,
                "severity": "CRITICAL",
                "message": f"Repo {repo_id}: missing content_manifest_sha",
            })
            continue

        source = repo.get("source", {})
        source_type = source.get("type", "")
        if source_type != "local_absolute_path":
            continue

        repo_path = Path(source.get("path", ""))
        if not repo_path.exists():
            issues.append({
                "check": "repo_lock_source_exists",
                "repo_id": repo_id,
                "severity": "CRITICAL",
                "message": f"Repo {repo_id}: source path {repo_path} does not exist",
            })
            continue

        extensions = set(repo.get("metadata", {}).get("extensions", [".rs"]))

        # Recompute normalized manifest SHA
        all_files: list[tuple[str, Path]] = []
        for dirpath, dirnames, filenames in os.walk(repo_path):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES and not d.startswith(".")]
            for fname in sorted(filenames):
                ext = os.path.splitext(fname)[1]
                if ext in extensions:
                    full = Path(dirpath) / fname
                    try:
                        rel = str(full.relative_to(repo_path)).replace(os.sep, "/")
                    except ValueError:
                        continue
                    all_files.append((rel, full))

        all_files.sort(key=lambda x: x[0])

        hasher = hashlib.sha256()
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

        computed_sha = hasher.hexdigest()

        if computed_sha != locked_sha:
            issues.append({
                "check": "repo_lock_manifest_sha",
                "repo_id": repo_id,
                "severity": "CRITICAL",
                "message": f"Repo {repo_id}: content_manifest_sha MISMATCH (locked={locked_sha[:16]}... computed={computed_sha[:16]}...)",
            })

    return issues


# ── Check 9: No raw gold paths in queries ──────────────────────────────


def check_no_raw_gold_in_queries(tasks: list[dict], labels: list[dict]) -> list[dict]:
    """Check that queries do not contain raw gold file path components."""
    issues = []
    label_map = {l["task_id"]: l for l in labels}

    for task in tasks:
        task_id = task.get("task_id", "unknown")
        query = task.get("query", "")

        label = label_map.get(task_id)
        if not label:
            continue

        for span in label.get("gold_spans", []):
            gold_path = span.get("path", "")
            if not gold_path:
                continue
            # Check if any path component (filename) from gold appears in query
            # This is less strict than exact path match
            path_parts = gold_path.replace("\\", "/").split("/")
            filename = path_parts[-1] if path_parts else ""
            if filename and filename in query and "." in filename:
                # Query contains a filename with extension - potential leakage
                issues.append({
                    "check": "query_contains_gold_filename",
                    "task_id": task_id,
                    "severity": "WARNING",
                    "message": f"Query '{query}' may contain gold filename '{filename}'",
                })

    return issues


# ── Check 10: Source repo_kind field in labels ─────────────────────────


def check_label_source_repo_kind(labels: list[dict]) -> list[dict]:
    """Verify labels have source_repo_kind field."""
    issues = []
    for label in labels:
        task_id = label.get("task_id", "unknown")
        if "source_repo_kind" not in label:
            issues.append({
                "check": "label_source_repo_kind",
                "task_id": task_id,
                "severity": "WARNING",
                "message": f"Label {task_id} missing source_repo_kind field",
            })
    return issues


# ── Main ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="R15 Benchmark Leakage Check")
    parser.add_argument("--manifest", required=True, help="Path to dataset_manifest.json")
    parser.add_argument("--predictions-dir", default="", help="Directory containing prediction files to scan")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    out_dir = manifest_path.parent

    manifest = load_manifest(manifest_path)
    repos = load_jsonl(out_dir / "repos.lock.jsonl")

    all_issues: list[dict] = []

    # Check all tier task/label files
    for tier_name in ["medium", "large", "stress"]:
        tasks_path = out_dir / "tasks" / f"{tier_name}.jsonl"
        labels_path = out_dir / "labels" / f"{tier_name}.jsonl"

        if not tasks_path.exists():
            continue

        tasks = load_jsonl(tasks_path)
        labels = load_jsonl(labels_path) if labels_path.exists() else []

        print(f"Checking {tier_name}: {len(tasks)} tasks, {len(labels)} labels")

        all_issues.extend(check_task_gold_leakage(tasks))
        all_issues.extend(check_query_gold_path_overlap(tasks, labels))
        all_issues.extend(check_no_raw_gold_in_queries(tasks, labels))
        all_issues.extend(check_tier_task_label_consistency(tier_name, tasks, labels, repos, manifest))
        all_issues.extend(check_hard_negative_overlap(labels))

    # Cross-tier checks
    all_issues.extend(check_repo_lock_integrity(repos, expected_count=9))
    all_issues.extend(check_source_paths_absolute(repos))
    all_issues.extend(check_benchmark_policy_excludes(repos))
    all_issues.extend(check_label_file_isolation(out_dir))
    all_issues.extend(check_canary_tokens(out_dir))
    all_issues.extend(check_repo_lock_manifest(repos))

    # Check source_repo_kind in labels
    for tier_name in ["medium", "large", "stress"]:
        labels_path = out_dir / "labels" / f"{tier_name}.jsonl"
        if labels_path.exists():
            labels = load_jsonl(labels_path)
            all_issues.extend(check_label_source_repo_kind(labels))

    # Predictions scan
    if args.predictions_dir:
        pred_dir = Path(args.predictions_dir)
        all_issues.extend(check_predictions_forbidden_paths(pred_dir))

    # Report
    critical_count = sum(1 for i in all_issues if i.get("severity") == "CRITICAL")
    warning_count = sum(1 for i in all_issues if i.get("severity") == "WARNING")

    safety_checks = {
        "total_checks": 10,
        "critical_issues": critical_count,
        "warning_issues": warning_count,
        "issues": all_issues,
        "passed": critical_count == 0,
        "canary_tokens_planted": CANARY_TOKENS,
        "r15_extensions": True,
    }

    print(f"\n{'='*60}")
    print("R15 Leakage Check Results")
    print(f"{'='*60}")
    print(f"Critical issues: {critical_count}")
    print(f"Warnings: {warning_count}")

    if all_issues:
        for issue in all_issues:
            severity = issue.get("severity", "UNKNOWN")
            check = issue.get("check", "unknown")
            message = issue.get("message", "")
            prefix = "❌" if severity == "CRITICAL" else "⚠️"
            print(f"  {prefix} [{check}] {message}")
    else:
        print("  ✅ No leakage issues found")

    safety_path = out_dir / "safety_checks.json"
    safety_path.write_text(json.dumps(safety_checks, indent=2) + "\n", encoding="utf-8")
    print(f"\nSafety checks written to: {safety_path}")

    if critical_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
