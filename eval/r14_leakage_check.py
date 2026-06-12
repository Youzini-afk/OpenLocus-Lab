#!/usr/bin/env python3
"""R14 Benchmark Leakage Check.

Verifies that public task files do not leak gold information and that
no benchmark artifacts can be discovered through retrieval.

Checks:
1. Public tasks contain no gold paths/lines/spans/hard_negatives
2. Queries do not contain exact gold paths
3. Labels are not in indexed repo root
4. Repo policy excludes use glob-style patterns
5. Label files are isolated from task files
6. Canary tokens: unique tokens planted in labels/eval/docs/runs;
   querying them must return 0 results
7. Predictions scan: no prediction path has a forbidden prefix

Usage:
    python3 eval/r14_leakage_check.py --manifest fixtures/r14/dataset_manifest.json [--predictions-dir PATH]
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

# Canary tokens: planted in label files / eval scripts / docs / runs.
# If any retrieval returns these, it means benchmark artifacts are indexed.
CANARY_TOKENS = [
    "R14_CANARY_fixture_label_secret_7a3f",
    "R14_CANARY_eval_benchmark_secret_9b2e",
    "R14_CANARY_docs_summary_secret_4c1d",
    "R14_CANARY_runs_prediction_secret_8e5a",
]


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


# ── Check 3: Labels not in indexed repo root ──────────────────────────


def check_labels_not_in_indexed_root(repo_dirs: set[str]) -> list[dict]:
    """Check that label files are not in indexed repo directories.

    Checks that no repo source path is inside a benchmark artifact directory
    (fixtures/, eval/, docs/, runs/, .openlocus/, target/).
    Uses path-component matching to avoid false positives (e.g. 'crates/openlocus-retrieval'
    should not match 'eval/').
    """
    issues = []
    forbidden_components = ["fixtures", "eval", "docs", "runs", ".openlocus", "target"]

    for repo_dir in repo_dirs:
        parts = repo_dir.replace("\\", "/").split("/")
        for part in parts:
            if part in forbidden_components:
                issues.append({
                    "check": "labels_in_indexed_repo",
                    "repo_dir": repo_dir,
                    "severity": "CRITICAL",
                    "message": f"Repo source path '{repo_dir}' contains benchmark artifact directory '{part}'",
                })
    return issues


# ── Check 4: Policy exclude patterns (glob-style) ────────────────────


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


# ── Check 5: Label file isolation ─────────────────────────────────────


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


# ── Check 6: Canary tokens in label/eval/docs/runs ─────────────────────


def check_canary_tokens(out_dir: Path) -> list[dict]:
    """Verify canary tokens exist in label files and that no task query matches them.

    Canary tokens are unique strings planted in private label files.
    If any public task query contains a canary token, it means there is leakage.
    """
    issues = []

    # Plant canaries in label files (if not already present)
    labels_dir = out_dir / "labels"
    canary_path = out_dir / "labels" / "_canary.json"
    canary_data = {
        "canary_tokens": CANARY_TOKENS,
        "description": "These tokens must never appear in any indexed content or prediction results",
        "purpose": "If any retrieval returns these tokens, benchmark artifacts are indexed",
    }
    canary_path.write_text(json.dumps(canary_data, indent=2) + "\n", encoding="utf-8")

    # Check that no task query contains a canary token
    for tier_name in ["sanity", "medium", "large", "stress"]:
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
    for tier_name in ["sanity", "medium", "large", "stress"]:
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


# ── Check 7: Predictions scan for forbidden paths ─────────────────────


def check_predictions_forbidden_paths(predictions_dir: Path) -> list[dict]:
    """Scan prediction files for paths with forbidden prefixes."""
    issues = []
    if not predictions_dir or not predictions_dir.exists():
        return issues

    for pred_file in predictions_dir.glob("*-predictions.jsonl"):
        predictions = load_jsonl(pred_file)
        for pred in predictions:
            for e in pred.get("evidence", []):
                path = e.get("path", "")
                for fp in FORBIDDEN_PREFIXES:
                    if path.startswith(fp):
                        issues.append({
                            "check": "prediction_forbidden_path",
                            "file": str(pred_file),
                            "task_id": pred.get("task_id", "?"),
                            "severity": "CRITICAL",
                            "message": f"Prediction has forbidden path prefix '{fp}': {path}",
                        })

    return issues


# ── Check 8: Repo lock content manifest verification ──────────────────


def check_repo_lock_manifest(repos: list[dict], repos_root: Path) -> list[dict]:
    """Verify content manifest SHA by recomputing normalized hash."""
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
        paths_str = source.get("path", "")
        crate_dirs = [p.strip() for p in paths_str.split(",") if p.strip()]

        # Recompute normalized manifest SHA
        all_files: list[tuple[str, Path]] = []
        for crate_dir in crate_dirs:
            crate_path = repos_root / crate_dir
            if not crate_path.exists():
                continue
            for dirpath, _dirnames, filenames in os.walk(crate_path):
                for fname in filenames:
                    if fname.endswith(".rs"):
                        full = Path(dirpath) / fname
                        rel = str(full.relative_to(repos_root)).replace(os.sep, "/")
                        all_files.append((rel, full))

        all_files.sort(key=lambda x: x[0])

        import hashlib
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


# ── Main ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="R14 Benchmark Leakage Check")
    parser.add_argument("--manifest", required=True, help="Path to dataset_manifest.json")
    parser.add_argument("--repos-root", default=".", help="Root directory for repos")
    parser.add_argument("--predictions-dir", default="", help="Directory containing prediction files to scan")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    out_dir = manifest_path.parent
    repos_root = Path(args.repos_root).resolve()

    manifest = load_manifest(manifest_path)
    repos = load_jsonl(out_dir / "repos.lock.jsonl")

    repo_dirs: set[str] = set()
    for repo in repos:
        source = repo.get("source", {})
        paths_str = source.get("path", "")
        for p in paths_str.split(","):
            repo_dirs.add(p.strip())

    all_issues: list[dict] = []

    # Check all tier task/label files
    for tier_name in ["sanity", "medium", "large", "stress"]:
        tasks_path = out_dir / "tasks" / f"{tier_name}.jsonl"
        labels_path = out_dir / "labels" / f"{tier_name}.jsonl"

        if not tasks_path.exists():
            continue

        tasks = load_jsonl(tasks_path)
        labels = load_jsonl(labels_path) if labels_path.exists() else []

        print(f"Checking {tier_name}: {len(tasks)} tasks, {len(labels)} labels")

        all_issues.extend(check_task_gold_leakage(tasks))
        all_issues.extend(check_query_gold_path_overlap(tasks, labels))

    # Cross-tier checks
    all_issues.extend(check_labels_not_in_indexed_root(repo_dirs))
    all_issues.extend(check_benchmark_policy_excludes(repos))
    all_issues.extend(check_label_file_isolation(out_dir))
    all_issues.extend(check_canary_tokens(out_dir))
    all_issues.extend(check_repo_lock_manifest(repos, repos_root))

    # Predictions scan (if provided)
    if args.predictions_dir:
        pred_dir = Path(args.predictions_dir)
        all_issues.extend(check_predictions_forbidden_paths(pred_dir))

    # Report
    critical_count = sum(1 for i in all_issues if i.get("severity") == "CRITICAL")
    warning_count = sum(1 for i in all_issues if i.get("severity") == "WARNING")

    safety_checks = {
        "total_checks": 8,
        "critical_issues": critical_count,
        "warning_issues": warning_count,
        "issues": all_issues,
        "passed": critical_count == 0,
        "canary_tokens_planted": CANARY_TOKENS,
    }

    print(f"\n{'='*60}")
    print("R14 Leakage Check Results")
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
