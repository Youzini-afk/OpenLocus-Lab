#!/usr/bin/env python3
"""R14 Smoke Test: Generate/Validate/Run R14-S baseline small matrix.

One-command pre-commit validation for the R14-S benchmark foundation.
This validates the pipeline works end-to-end; it does NOT produce
quality conclusions.

ALL checks are HARD FAIL. No best-effort. If canary, policy, citation,
or forbidden path checks fail, the test exits 1.

Usage:
    python3 eval/r14_smoke.py --openlocus target/debug/openlocus --workspace .

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
    parser = argparse.ArgumentParser(description="R14-S Smoke Test: HARD FAIL validation")
    parser.add_argument("--openlocus", default="target/debug/openlocus", help="Path to openlocus binary")
    parser.add_argument("--workspace", default=".", help="Path to OpenLocus-Lab workspace")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    openlocus = str((workspace / args.openlocus).resolve()) if not Path(args.openlocus).is_absolute() else args.openlocus
    results: list[dict] = []

    # ── Step 1: Validate fixtures exist ────────────────────────────────

    step("Step 1: Validate R14-S fixtures")

    fixtures_dir = workspace / "fixtures" / "r14"
    check(fixtures_dir.exists(), "R14 fixtures directory exists", results)

    manifest_path = fixtures_dir / "dataset_manifest.json"
    check(manifest_path.exists(), "dataset_manifest.json exists", results)

    repos_lock = fixtures_dir / "repos.lock.jsonl"
    check(repos_lock.exists(), "repos.lock.jsonl exists", results)

    tasks_sanity = fixtures_dir / "tasks" / "sanity.jsonl"
    check(tasks_sanity.exists(), "tasks/sanity.jsonl exists", results)

    labels_sanity = fixtures_dir / "labels" / "sanity.jsonl"
    check(labels_sanity.exists(), "labels/sanity.jsonl exists", results)

    readme = fixtures_dir / "README.md"
    check(readme.exists(), "README.md exists", results)

    # ── Step 2: Validate fixture contents ──────────────────────────────

    step("Step 2: Validate R14-S fixture contents")

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        check(manifest.get("schema_version") == "r14-v1", "Manifest schema_version is r14-v1", results)
        check("tiers" in manifest, "Manifest contains tier definitions", results)
        check("S" in manifest.get("tiers", {}), "Manifest contains S-tier definition", results)

        # Verify S-tier is populated
        s_status = manifest.get("current_status", {}).get("S", {})
        check(s_status.get("populated", False), "S-tier is marked populated", results)
        check(s_status.get("repos", 0) >= 4, f"S-tier has >= 4 repos ({s_status.get('repos', 0)})", results)
    else:
        check(False, "Manifest exists", results)

    if repos_lock.exists():
        repos = []
        for line in repos_lock.read_text(encoding="utf-8").splitlines():
            if line.strip():
                repos.append(json.loads(line))
        check(len(repos) >= 4, f"Repo lock has >= 4 entries (found {len(repos)})", results)

        for repo in repos:
            repo_id = repo.get("repo_id", "?")
            check(bool(repo.get("content_manifest_sha")), f"Repo {repo_id} has content_manifest_sha", results)
            check(bool(repo.get("policy", {}).get("exclude")), f"Repo {repo_id} has policy excludes", results)
            # Verify glob-style patterns
            excludes = repo.get("policy", {}).get("exclude", [])
            has_glob = any("/**" in exc or "*" in exc for exc in excludes)
            check(has_glob, f"Repo {repo_id} uses glob-style exclude patterns", results)
            # Verify content_manifest_algorithm
            check(
                repo.get("content_manifest_algorithm") == "normalized_sha256_per_file_sorted",
                f"Repo {repo_id} uses normalized manifest algorithm",
                results,
            )
    else:
        check(False, "Repo lock exists", results)

    if tasks_sanity.exists():
        tasks = []
        for line in tasks_sanity.read_text(encoding="utf-8").splitlines():
            if line.strip():
                tasks.append(json.loads(line))
        check(len(tasks) >= 40, f"Sanity tasks >= 40 (found {len(tasks)})", results)

        no_gold = all(
            "gold_spans" not in t and "gold_paths" not in t and "gold_lines" not in t and "hard_negatives" not in t
            for t in tasks
        )
        check(no_gold, "No gold info in public tasks (strict)", results)

        task_types = {t.get("task_type") for t in tasks}
        expected_types = {"exact_symbol", "implementation_search", "config_policy", "negative", "stress"}
        check(bool(expected_types & task_types), f"Tasks cover expected types (found: {task_types})", results)
    else:
        check(False, "Sanity tasks exist", results)

    if labels_sanity.exists():
        labels = []
        for line in labels_sanity.read_text(encoding="utf-8").splitlines():
            if line.strip():
                labels.append(json.loads(line))
        check(len(labels) >= 40, f"Sanity labels >= 40 (found {len(labels)})", results)
        check(all("gold_spans" in l for l in labels), "All labels have gold_spans field", results)
        check(all("label_quality" in l for l in labels), "All labels have label_quality field", results)

        hn_count = sum(len(l.get("hard_negatives", [])) for l in labels)
        check(hn_count >= 8, f"Hard negatives >= 8 (found {hn_count})", results)

        quality_dist: dict[str, int] = {}
        for l in labels:
            q = l.get("label_quality", "unknown")
            quality_dist[q] = quality_dist.get(q, 0) + 1
        print(f"  Label quality distribution: {quality_dist}")

        check(
            "human_reviewed" in quality_dist or "mined_high_confidence" in quality_dist,
            "Labels include human_reviewed or mined_high_confidence",
            results,
        )

        # Verify hard negatives have span-level info (path + start_line + end_line)
        hn_with_spans = 0
        hn_total = 0
        for l in labels:
            for hn in l.get("hard_negatives", []):
                hn_total += 1
                if hn.get("start_line", 0) > 0 and hn.get("end_line", 0) > 0:
                    hn_with_spans += 1
        if hn_total > 0:
            check(hn_with_spans > 0, f"Hard negatives include span-level info ({hn_with_spans}/{hn_total})", results)
    else:
        check(False, "Sanity labels exist", results)

    # ── Step 3: Run leakage check (HARD FAIL) ─────────────────────────

    step("Step 3: Run leakage check (HARD FAIL)")

    ret, output = run_cmd(
        ["python3", "eval/r14_leakage_check.py", "--manifest", str(manifest_path)],
        cwd=str(workspace),
        check=False,
    )
    check(ret == 0, "Leakage check passed (HARD FAIL)", results)

    safety_path = fixtures_dir / "safety_checks.json"
    if safety_path.exists():
        safety = json.loads(safety_path.read_text(encoding="utf-8"))
        check(safety.get("critical_issues", 1) == 0, "No critical leakage issues", results)
        check(safety.get("passed", False), "Safety checks passed=true", results)
        # Verify canary tokens were planted
        check(bool(safety.get("canary_tokens_planted")), "Canary tokens planted", results)
    else:
        check(False, "safety_checks.json generated", results)

    # ── Step 4: Validate openlocus binary ──────────────────────────────

    step("Step 4: Validate openlocus binary")

    quick_tmp = tempfile.TemporaryDirectory(prefix="r14-smoke-quick-")
    quick_root = Path(quick_tmp.name)
    (quick_root / ".git").mkdir()
    (quick_root / "src").mkdir()
    (quick_root / "src" / "lib.rs").write_text(
        "pub struct EvidenceCore {\n    pub path: String,\n}\n",
        encoding="utf-8",
    )

    ret, output = run_cmd([openlocus, "read", "src/lib.rs:1-1", "--json"], cwd=str(quick_root), check=False)
    check(ret == 0, "openlocus binary can read isolated quick fixture", results)

    # ── Step 5: Quick retrieval test ───────────────────────────────────

    step("Step 5: Quick retrieval test (one query per method)")

    methods = ["regex", "bm25", "symbol"]
    for method in methods:
        ret, output = run_cmd(
            [openlocus, "search", method, "EvidenceCore", "--json"],
            cwd=str(quick_root),
            check=False,
        )
        check(ret == 0, f"openlocus search {method} EvidenceCore returns 0", results)

    ret, output = run_cmd(
        [openlocus, "retrieve", "EvidenceCore", "--channels", "regex,bm25,symbol", "--json"],
        cwd=str(quick_root),
        check=False,
    )
    check(ret == 0, "openlocus retrieve EvidenceCore returns 0", results)
    quick_tmp.cleanup()

    # ── Step 6: Run benchmark (HARD FAIL) ─────────────────────────────

    step("Step 6: Run R14-S benchmark (HARD FAIL)")

    runs_dir = workspace / "runs"
    runs_dir.mkdir(exist_ok=True)
    for stale in runs_dir.glob("r14-*.json"):
        stale.unlink()
    for stale in runs_dir.glob("r14-*.jsonl"):
        stale.unlink()
    for stale in runs_dir.glob("r14-*.md"):
        stale.unlink()

    ret, output = run_cmd(
        [
            "python3", "eval/r14_benchmark.py",
            "--manifest", str(manifest_path),
            "--openlocus", openlocus,
            "--methods", "regex",
            "--repos-root", str(workspace),
            "--tier", "S",
            "--out", str(runs_dir / "r14-smoke-report.json"),
        ],
        cwd=str(workspace),
        check=False,
    )

    check(ret == 0, "R14-S benchmark completed (HARD FAIL)", results)

    report_path = runs_dir / "r14-smoke-report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        metrics = report.get("metrics", {}).get("regex", {})

        # Citation validity must be 1.0 (fail-closed)
        cv = metrics.get("citation_validity", 0)
        check(cv >= 1.0, f"Citation validity = 1.0 (got {cv:.3f}, HARD FAIL)", results)
        check(metrics.get("citation_hash_checked") is True, "Citation hash checked by Rust validator", results)
        check(metrics.get("citation_validation_mode") == "fail_closed_hash_range_path", "Citation mode is fail-closed", results)

        # No forbidden paths in predictions
        check(report.get("safety_passed", False), "Benchmark safety checks passed", results)
        canary_retrieval = report.get("canary_retrieval", {})
        check(canary_retrieval.get("passed") is True, "Canary retrieval returned zero hits", results)
        check(canary_retrieval.get("checked", 0) >= 4, "Canary retrieval checked tokens", results)

        # Verify runner/scorer isolation
        phases = report.get("phases", {})
        check(phases.get("run") == "public_tasks_only_no_labels", "Run phase: public tasks only", results)
        check(phases.get("score") == "labels_only_no_cli", "Score phase: labels only", results)
        check(phases.get("isolation") == "temp_root_per_repo", "Isolation: temp root per repo", results)
        check(phases.get("citation_mode") == "fail_closed_hash_range_path", "Citation: fail-closed", results)

        # Check for negative task metrics
        check("negative_nonempty_rate@10" in metrics, "Negative task metrics present", results)
    else:
        check(False, "Benchmark report generated", results)

    # ── Step 7: Canary token verification ──────────────────────────────

    step("Step 7: Canary token verification")

    # Verify canary file exists in labels
    canary_path = fixtures_dir / "labels" / "_canary.json"
    check(canary_path.exists(), "Canary token file exists in labels/", results)

    if canary_path.exists():
        canary = json.loads(canary_path.read_text(encoding="utf-8"))
        tokens = canary.get("canary_tokens", [])
        check(len(tokens) >= 4, f"Canary tokens present ({len(tokens)})", results)

        # Verify no canary token appears in any task file
        for tier_name in ["sanity", "medium", "large", "stress"]:
            tasks_path = fixtures_dir / "tasks" / f"{tier_name}.jsonl"
            if not tasks_path.exists():
                continue
            content = tasks_path.read_text(encoding="utf-8")
            for token in tokens:
                check(token not in content, f"Canary token NOT in tasks/{tier_name}.jsonl", results)

    # ── Step 8: Repo lock content manifest verification ────────────────

    step("Step 8: Repo lock content manifest verification")

    if repos_lock.exists():
        repos = []
        for line in repos_lock.read_text(encoding="utf-8").splitlines():
            if line.strip():
                repos.append(json.loads(line))

        for repo in repos:
            repo_id = repo.get("repo_id", "?")
            locked_sha = repo.get("content_manifest_sha", "")
            source = repo.get("source", {})
            paths_str = source.get("path", "")
            crate_dirs = [p.strip() for p in paths_str.split(",") if p.strip()]

            # Recompute
            all_files: list[tuple[str, Path]] = []
            for crate_dir in crate_dirs:
                crate_path = workspace / crate_dir
                if not crate_path.exists():
                    continue
                for dirpath, _dirnames, filenames in os.walk(crate_path):
                    for fname in filenames:
                        if fname.endswith(".rs"):
                            full = Path(dirpath) / fname
                            rel = str(full.relative_to(workspace)).replace(os.sep, "/")
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

    # ── Step 9: Predictions forbidden path check ──────────────────────

    step("Step 9: Predictions forbidden path check")

    forbidden_prefixes = ["fixtures/", "eval/", "docs/", "runs/", ".openlocus/", "target/"]
    pred_files = list(runs_dir.glob("r14-sanity-*-predictions.jsonl"))
    if pred_files:
        for pf in pred_files:
            predictions = []
            for line in pf.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    predictions.append(json.loads(line))
            for pred in predictions:
                for e in pred.get("evidence", []):
                    path = e.get("path", "")
                    for fp in forbidden_prefixes:
                        check(
                            not path.startswith(fp),
                            f"No prediction with forbidden prefix '{fp}' (task {pred.get('task_id', '?')})",
                            results,
                        )
    else:
        print("  ℹ️  No prediction files found to scan")

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

    print("\n  IMPORTANT: This smoke test validates the R14-S pipeline,")
    print("  NOT retrieval quality. R14-S is a safety foundation check.")
    print("  All checks are HARD FAIL. No best-effort.")

    if passed == total:
        print("\n  ✅ All smoke checks passed!")
        sys.exit(0)
    else:
        print(f"\n  ❌ {total - passed} checks failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
