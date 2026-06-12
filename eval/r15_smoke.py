#!/usr/bin/env python3
"""R15 Smoke Test: Validate/Leakage-Check/Small-Matrix Benchmark.

One-command validation for the R15 external multi-repo benchmark.
This validates the pipeline works end-to-end; it does NOT produce
quality conclusions.

ALL checks are HARD FAIL. No best-effort.

Usage:
    python3 eval/r15_smoke.py --workspace .

Exit codes:
    0: All checks passed
    1: Safety or critical failure
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SOURCE_EXTENSIONS = {".rs", ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".mjs"}

SKIP_DIR_NAMES = {
    "node_modules", "target", ".git", "dist", "build", ".venv",
    "__pycache__", ".next", ".nuxt", "runs", "fixtures", "eval",
    "docs", ".openlocus", "coverage", ".cache", ".mypy_cache",
    ".pytest_cache", ".tox", "venv", "env", ".env", ".idea",
    ".vscode", "out", "bin", "obj",
}


def run_cmd(cmd: list[str], cwd: str = ".", check: bool = True) -> tuple[int, str]:
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True, cwd=cwd)
    output = proc.stdout + proc.stderr
    return proc.returncode, output


def step(name: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


def check(condition: bool, name: str, results: list[dict]) -> bool:
    results.append({"name": name, "passed": condition})
    prefix = "✅" if condition else "❌"
    print(f"  {prefix} {name}")
    return condition


def main() -> None:
    parser = argparse.ArgumentParser(description="R15 Smoke Test: HARD FAIL validation")
    parser.add_argument("--openlocus", default="target/debug/openlocus", help="Path to openlocus binary")
    parser.add_argument("--workspace", default=".", help="Path to OpenLocus-Lab workspace")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    openlocus = str((workspace / args.openlocus).resolve()) if not Path(args.openlocus).is_absolute() else args.openlocus
    results: list[dict] = []

    # ── Step 1: Validate fixtures exist ────────────────────────────────

    step("Step 1: Validate R15 fixtures")

    fixtures_dir = workspace / "fixtures" / "r15"
    check(fixtures_dir.exists(), "R15 fixtures directory exists", results)

    manifest_path = fixtures_dir / "dataset_manifest.json"
    check(manifest_path.exists(), "dataset_manifest.json exists", results)

    repos_lock = fixtures_dir / "repos.lock.jsonl"
    check(repos_lock.exists(), "repos.lock.jsonl exists", results)

    tasks_medium = fixtures_dir / "tasks" / "medium.jsonl"
    check(tasks_medium.exists(), "tasks/medium.jsonl exists", results)

    labels_medium = fixtures_dir / "labels" / "medium.jsonl"
    check(labels_medium.exists(), "labels/medium.jsonl exists", results)

    readme = fixtures_dir / "README.md"
    check(readme.exists(), "README.md exists", results)

    safety_path = fixtures_dir / "safety_checks.json"
    check(safety_path.exists(), "safety_checks.json exists", results)

    # ── Step 2: Validate fixture contents ──────────────────────────────

    step("Step 2: Validate R15 fixture contents")

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        check(manifest.get("schema_version") == "r15-v1", "Manifest schema_version is r15-v1", results)
        check("tiers" in manifest, "Manifest contains tier definitions", results)
        check("M" in manifest.get("tiers", {}), "Manifest contains M-tier definition", results)

        m_status = manifest.get("current_status", {}).get("M", {})
        check(m_status.get("populated", False), "M-tier is marked populated", results)
        check(m_status.get("repos", 0) == 9, f"M-tier has exactly 9 repos ({m_status.get('repos', 0)})", results)
        check(m_status.get("tasks", 0) >= 120, f"M-tier has >= 120 tasks ({m_status.get('tasks', 0)})", results)
    else:
        check(False, "Manifest exists", results)

    if repos_lock.exists():
        repos = []
        for line in repos_lock.read_text(encoding="utf-8").splitlines():
            if line.strip():
                repos.append(json.loads(line))
        check(len(repos) == 9, f"Repo lock has exactly 9 entries (found {len(repos)})", results)
        repo_ids = [repo.get("repo_id") for repo in repos]
        check(len(repo_ids) == len(set(repo_ids)), "Repo lock has no duplicate repo_id", results)

        for repo in repos:
            repo_id = repo.get("repo_id", "?")
            check(bool(repo.get("content_manifest_sha")), f"Repo {repo_id} has content_manifest_sha", results)
            check(bool(repo.get("policy", {}).get("exclude")), f"Repo {repo_id} has policy excludes", results)
            check(
                repo.get("source", {}).get("type") == "local_absolute_path",
                f"Repo {repo_id} uses local_absolute_path source type",
                results,
            )
            source_path = repo.get("source", {}).get("path", "")
            check(
                os.path.isabs(source_path),
                f"Repo {repo_id} has absolute source path",
                results,
            )
            check(
                repo.get("content_manifest_algorithm") == "normalized_sha256_per_file_sorted",
                f"Repo {repo_id} uses normalized manifest algorithm",
                results,
            )
    else:
        check(False, "Repo lock exists", results)

    if tasks_medium.exists():
        tasks = []
        for line in tasks_medium.read_text(encoding="utf-8").splitlines():
            if line.strip():
                tasks.append(json.loads(line))
        check(len(tasks) >= 120, f"Medium tasks >= 120 (found {len(tasks)})", results)

        no_gold = all(
            "gold_spans" not in t and "gold_paths" not in t and "gold_lines" not in t and "hard_negatives" not in t
            for t in tasks
        )
        check(no_gold, "No gold info in public tasks (strict)", results)

        task_types = {t.get("task_type") for t in tasks}
        expected_types = {"exact_symbol", "implementation_search", "config_import", "negative", "stress"}
        check(bool(expected_types & task_types), f"Tasks cover expected types (found: {task_types})", results)

        # Verify multi-repo coverage
        repo_ids = {t.get("repo_id") for t in tasks}
        check(len(repo_ids) == 9, f"Tasks cover exactly 9 repos (found {len(repo_ids)})", results)
    else:
        check(False, "Medium tasks exist", results)

    if labels_medium.exists():
        labels = []
        for line in labels_medium.read_text(encoding="utf-8").splitlines():
            if line.strip():
                labels.append(json.loads(line))
        check(len(labels) >= 120, f"Medium labels >= 120 (found {len(labels)})", results)
        check(all("gold_spans" in l for l in labels), "All labels have gold_spans field", results)
        check(all("label_quality" in l for l in labels), "All labels have label_quality field", results)
        check(all("source_repo_kind" in l for l in labels), "All labels have source_repo_kind field", results)

        hn_count = sum(len(l.get("hard_negatives", [])) for l in labels)
        check(hn_count >= 24, f"Hard negatives >= 24 (found {hn_count})", results)

        overlap_count = 0
        for label in labels:
            for gold in label.get("gold_spans", []):
                gp = gold.get("path")
                gs = gold.get("start_line", 0)
                ge = gold.get("end_line", 0)
                for hn in label.get("hard_negatives", []):
                    if hn.get("path") == gp and hn.get("start_line", 0) <= ge and hn.get("end_line", 0) >= gs:
                        overlap_count += 1
        check(overlap_count == 0, f"Hard negatives do not overlap gold spans (found {overlap_count})", results)

        quality_dist: dict[str, int] = {}
        for l in labels:
            q = l.get("label_quality", "unknown")
            quality_dist[q] = quality_dist.get(q, 0) + 1
        print(f"  Label quality distribution: {quality_dist}")

        check(
            "mined_high_confidence" in quality_dist,
            "Labels include mined_high_confidence",
            results,
        )
    else:
        check(False, "Medium labels exist", results)

    # ── Step 3: Run leakage check (HARD FAIL) ─────────────────────────

    step("Step 3: Run leakage check (HARD FAIL)")

    ret, output = run_cmd(
        ["python3", "eval/r15_leakage_check.py", "--manifest", str(manifest_path)],
        cwd=str(workspace),
        check=False,
    )
    check(ret == 0, "Leakage check passed (HARD FAIL)", results)

    if safety_path.exists():
        safety = json.loads(safety_path.read_text(encoding="utf-8"))
        check(safety.get("critical_issues", 1) == 0, "No critical leakage issues", results)
        check(safety.get("passed", False), "Safety checks passed=true", results)
        check(bool(safety.get("canary_tokens_planted")), "Canary tokens planted", results)

    # ── Step 4: Validate openlocus binary exists ──────────────────────

    step("Step 4: Validate openlocus binary")

    openlocus_exists = Path(openlocus).exists()
    check(openlocus_exists, f"openlocus binary exists at {openlocus}", results)

    if openlocus_exists:
        quick_tmp = tempfile.TemporaryDirectory(prefix="r15-smoke-quick-")
        quick_root = Path(quick_tmp.name)
        (quick_root / ".git").mkdir()
        (quick_root / "src").mkdir()
        (quick_root / "src" / "lib.rs").write_text(
            "pub struct EvidenceCore {\n    pub path: String,\n}\n",
            encoding="utf-8",
        )

        ret, _output = run_cmd([openlocus, "read", "src/lib.rs:1-1", "--json"], cwd=str(quick_root), check=False)
        check(ret == 0, "openlocus binary can read isolated quick fixture", results)

        # ── Step 5: Quick retrieval test ───────────────────────────────

        step("Step 5: Quick retrieval test (regex, bm25)")

        ret, _output = run_cmd(
            [openlocus, "search", "regex", "EvidenceCore", "--json"],
            cwd=str(quick_root),
            check=False,
        )
        check(ret == 0, "openlocus search regex EvidenceCore returns 0", results)

        ret, _output = run_cmd(
            [openlocus, "search", "bm25", "EvidenceCore", "--json"],
            cwd=str(quick_root),
            check=False,
        )
        check(ret == 0, "openlocus search bm25 EvidenceCore returns 0", results)

        quick_tmp.cleanup()
    else:
        print("  ℹ️  Skipping retrieval test (openlocus binary not found)")

    # ── Step 6: Run benchmark (if binary available) ───────────────────

    if openlocus_exists:
        step("Step 6: Run R15-M benchmark small matrix (regex, bm25)")

        runs_dir = workspace / "runs"
        runs_dir.mkdir(exist_ok=True)
        for stale in runs_dir.glob("r15-smoke-report*"):
            stale.unlink()
        for stale in runs_dir.glob("r15-medium-*-predictions.jsonl"):
            stale.unlink()

        ret, output = run_cmd(
            [
                "python3", "eval/r15_benchmark.py",
                "--manifest", str(manifest_path),
                "--openlocus", openlocus,
                "--methods", "regex,bm25",
                "--tier", "M",
                "--out", str(runs_dir / "r15-smoke-report.json"),
            ],
            cwd=str(workspace),
            check=False,
        )

        if ret == 0:
            check(True, "R15-M benchmark completed successfully", results)

            report_path = runs_dir / "r15-smoke-report.json"
            if report_path.exists():
                report = json.loads(report_path.read_text(encoding="utf-8"))

                # Safety gates
                check(
                    report.get("safety_passed", False),
                    "Benchmark safety checks passed",
                    results,
                )
                canary_retrieval = report.get("canary_retrieval", {})
                check(
                    canary_retrieval.get("passed") is True,
                    "Canary retrieval returned zero hits",
                    results,
                )

                # Check metrics exist
                for method in ["regex", "bm25"]:
                    metrics = report.get("metrics", {}).get(method, {})
                    if metrics:
                        check(
                            "file_recall@1" in metrics,
                            f"{method}: file_recall@1 metric present",
                            results,
                        )
                        check(
                            "negative_nonempty_rate@10" in metrics,
                            f"{method}: negative_nonempty_rate@10 metric present",
                            results,
                        )
                        check(
                            metrics.get("citation_hash_checked") is True,
                            f"{method}: citation_hash_checked true",
                            results,
                        )
                        check(
                            metrics.get("citation_validity") == 1.0,
                            f"{method}: citation_validity = 1.0",
                            results,
                        )
                        check(
                            metrics.get("citation_validation_mode") == "fail_closed_hash_range_path",
                            f"{method}: citation validation mode fail-closed",
                            results,
                        )
        else:
            print(output[:2000])
            check(False, "R15-M benchmark completed successfully", results)
    else:
        step("Step 6: Run R15-M benchmark (SKIPPED - no openlocus binary)")
        print("  ℹ️  Skipping benchmark (openlocus binary not found)")

    # ── Step 7: Repo lock content manifest verification (spot-check) ────

    step("Step 7: Repo lock content manifest verification (spot-check)")

    if repos_lock.exists():
        repos = []
        for line in repos_lock.read_text(encoding="utf-8").splitlines():
            if line.strip():
                repos.append(json.loads(line))

        # Verify a few repos (not all — full verification is done by r15_leakage_check)
        verified_count = 0
        for repo in repos[:3]:  # Spot-check first 3 repos
            repo_id = repo.get("repo_id", "?")
            locked_sha = repo.get("content_manifest_sha", "")
            source = repo.get("source", {})
            source_type = source.get("type", "")

            if source_type != "local_absolute_path":
                continue

            repo_path = Path(source.get("path", ""))
            if not repo_path.exists():
                print(f"  ℹ️  Repo {repo_id}: source path {repo_path} not accessible, skipping manifest verification")
                continue

            extensions = set(repo.get("metadata", {}).get("extensions", [".rs"]))

            # Recompute multi-language manifest
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
            check(
                computed_sha == locked_sha,
                f"Repo {repo_id}: content_manifest_sha verified",
                results,
            )
            verified_count += 1

        check(verified_count >= 1, f"At least 1 repo manifest verified (checked {verified_count})", results)

    # ── Step 8: Canary token verification ──────────────────────────────

    step("Step 8: Canary token verification")

    canary_path = fixtures_dir / "labels" / "_canary.json"
    check(canary_path.exists(), "Canary token file exists in labels/", results)

    if canary_path.exists():
        canary = json.loads(canary_path.read_text(encoding="utf-8"))
        tokens = canary.get("canary_tokens", [])
        check(len(tokens) >= 4, f"Canary tokens present ({len(tokens)})", results)

        # Verify no canary token appears in any task file
        for tier_name in ["medium", "large", "stress"]:
            tasks_path = fixtures_dir / "tasks" / f"{tier_name}.jsonl"
            if not tasks_path.exists():
                continue
            content = tasks_path.read_text(encoding="utf-8")
            for token in tokens:
                check(token not in content, f"Canary token NOT in tasks/{tier_name}.jsonl", results)

    # ── Step 9: Multi-language coverage check ──────────────────────────

    step("Step 9: Multi-language coverage check")

    if repos_lock.exists():
        repos = []
        for line in repos_lock.read_text(encoding="utf-8").splitlines():
            if line.strip():
                repos.append(json.loads(line))

        languages: set[str] = set()
        for repo in repos:
            lang = repo.get("language", {})
            primary = lang.get("primary", "")
            if primary:
                languages.add(primary)
            for sec in lang.get("secondary", []):
                languages.add(sec)

        check(len(languages) >= 4, f"Multi-language coverage >= 4 languages (found {len(languages)}: {languages})", results)

        expected_langs = {"rust", "python", "go", "javascript", "typescript"}
        covered = languages & expected_langs
        check(
            len(covered) >= 4,
            f"Covers >= 4 of Rust/Python/Go/JS/TS (found {covered})",
            results,
        )

    # ── Summary ────────────────────────────────────────────────────────

    step("Summary")

    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    print(f"  Checks passed: {passed}/{total}")

    if passed < total:
        print("\n  Failed checks:")
        for r in results:
            if not r["passed"]:
                print(f"    ❌ {r['name']}")

    print("\n  IMPORTANT: This smoke test validates the R15 multi-repo pipeline,")
    print("  NOT retrieval quality. R15 is a mined benchmark expansion.")
    print("  All checks are HARD FAIL. No best-effort.")

    if passed == total:
        print("\n  ✅ All smoke checks passed!")
        sys.exit(0)
    else:
        print(f"\n  ❌ {total - passed} checks failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
