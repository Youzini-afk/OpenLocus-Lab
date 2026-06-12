#!/usr/bin/env python3
"""R15 External Multi-Repo Evidence Benchmark Runner/Scorer.

Extends R14 benchmark to support absolute repo source roots and multi-language
manifest. Reuses R14 scoring logic but adapts for external repos.

Architecture: strictly separated RUN and SCORE phases (same as R14).
  - Phase 1 (RUN): loads only public tasks + repo lock. Creates isolated
    benchmark roots by allowlist-copying source files under repo_id-specific folders.
    Runs retrieval CLI. Writes predictions. Never reads labels/gold.
  - Phase 2 (SCORE): loads predictions + private labels. Computes metrics.
    Never invokes retrieval CLI.

Safety (same as R14, extended for external repos):
- Runner never loads private labels/gold
- Retrieval runs inside isolated temp roots (no fixtures/eval/docs/runs)
- Repo lock content manifest is re-verified (normalized hash across all supported extensions)
- Citation validation is fail-closed: every citation must be hash+range+path valid
- Predictions with forbidden prefixes are critical failures
- Fails closed on all safety issues
- Unknown repo_id is CRITICAL; runner refuses to fall back to the full workspace
- Runner allowlist-copies source files into isolated roots under repo_id-specific folders
- External repos are READ-ONLY; never modified

Usage:
    python3 eval/r15_benchmark.py \
        --manifest fixtures/r15/dataset_manifest.json \
        --openlocus target/debug/openlocus \
        --methods regex,bm25,symbol,rrf \
        --tier M \
        --out runs/r15-report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


# ── Schema version ─────────────────────────────────────────────────────

SCHEMA_VERSION = "r15-v1"

# ── Supported source extensions for R15 ─────────────────────────────────

SOURCE_EXTENSIONS = {".rs", ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".mjs"}

SKIP_DIR_NAMES = {
    "node_modules", "target", ".git", "dist", "build", ".venv",
    "__pycache__", ".next", ".nuxt", "runs", "fixtures", "eval",
    "docs", ".openlocus", "coverage", ".cache", ".mypy_cache",
    ".pytest_cache", ".tox", "venv", "env", ".env", ".idea",
    ".vscode", "out", "bin", "obj",
}

# ── Forbidden prefixes ──────────────────────────────────────────────────

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

CANARY_TOKENS = [
    "R15_CANARY_fixture_label_secret_1a2b",
    "R15_CANARY_eval_benchmark_secret_3c4d",
    "R15_CANARY_docs_summary_secret_5e6f",
    "R15_CANARY_runs_prediction_secret_7g8h",
]

POLICY_EXCLUDE_PATTERNS = [
    "fixtures/**",
    "eval/**",
    "docs/**",
    "runs/**",
    ".openlocus/**",
    "target/**",
    "__pycache__/**",
    "*.tmp",
    "*.log",
    ".git/**",
    "node_modules/**",
    "dist/**",
    "build/**",
    ".venv/**",
    ".next/**",
    ".nuxt/**",
]


# ── Data loading ────────────────────────────────────────────────────────


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


def load_repo_lock(out_dir: Path) -> dict[str, dict]:
    lock_path = out_dir / "repos.lock.jsonl"
    repos = {}
    for entry in load_jsonl(lock_path):
        repos[entry["repo_id"]] = entry
    return repos


# ── Multi-language normalized content manifest ──────────────────────────


def compute_normalized_manifest_sha(
    repo_path: Path, extensions: set[str] | None = None
) -> tuple[str, int, int, list[dict[str, Any]]]:
    """Compute normalized content manifest SHA across all source files.

    Same algorithm as R14 but multi-language: sort all source files by relative
    path (POSIX). For each file: path, sha256, lines. Concatenate as sorted
    JSON lines, SHA-256 the result.
    """
    if extensions is None:
        extensions = SOURCE_EXTENSIONS

    all_files: list[tuple[str, Path]] = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES and not d.startswith(".")]
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
                all_files.append((rel, full))

    all_files.sort(key=lambda x: x[0])

    per_file: list[dict[str, Any]] = []
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

        per_file.append(entry)
        file_count += 1
        total_lines += line_count

    return hasher.hexdigest(), file_count, total_lines, per_file


# ── Repo lock validation ────────────────────────────────────────────────


def validate_repo_lock(
    repos: dict[str, dict],
) -> tuple[list[str], list[str]]:
    """Validate repo lock entries with content manifest re-verification."""
    issues: list[str] = []
    info: list[str] = []

    for repo_id, entry in repos.items():
        source = entry.get("source", {})
        source_type = source.get("type", "")

        if source_type == "local_absolute_path":
            repo_path = Path(source.get("path", ""))
            if not repo_path.exists():
                issues.append(f"CRITICAL: Repo {repo_id}: source path {repo_path} does not exist")
                continue
        elif source_type == "local_path":
            # Legacy R14-style relative path (shouldn't appear in R15 but handle gracefully)
            issues.append(f"CRITICAL: Repo {repo_id}: unexpected source type 'local_path' in R15")
            continue
        else:
            issues.append(f"CRITICAL: Repo {repo_id}: unsupported source type {source_type}")
            continue

        # Check policy exclude patterns
        policy_excludes = entry.get("policy", {}).get("exclude", [])
        required_patterns = {"fixtures", "eval", "docs", "runs", ".openlocus", "target"}
        for req in required_patterns:
            found = any(req in exc for exc in policy_excludes)
            if not found:
                issues.append(f"CRITICAL: Repo {repo_id}: policy exclude missing '{req}/**' pattern")

        # Recompute normalized manifest SHA (multi-language)
        locked_sha = entry.get("content_manifest_sha", "")
        if not locked_sha:
            issues.append(f"CRITICAL: Repo {repo_id}: missing content_manifest_sha")
            continue

        extensions = set(entry.get("metadata", {}).get("extensions", [".rs"]))
        computed_sha, file_count, total_lines, _per_file = compute_normalized_manifest_sha(
            repo_path, extensions
        )

        if computed_sha != locked_sha:
            issues.append(
                f"CRITICAL: Repo {repo_id}: content_manifest_sha MISMATCH "
                f"(locked={locked_sha[:16]}... computed={computed_sha[:16]}...). "
                f"Repo content has changed since lock was created."
            )
        else:
            info.append(
                f"Repo {repo_id}: content_manifest_sha verified ({file_count} files, {total_lines} lines)"
            )

        locked_files = entry.get("metadata", {}).get("files", 0)
        locked_lines = entry.get("metadata", {}).get("lines", 0)
        if locked_files != file_count:
            issues.append(
                f"CRITICAL: Repo {repo_id}: file count mismatch (locked={locked_files} actual={file_count})"
            )
        if locked_lines != total_lines:
            issues.append(
                f"CRITICAL: Repo {repo_id}: line count mismatch (locked={locked_lines} actual={total_lines})"
            )

    return issues, info


# ── Isolated benchmark root ──────────────────────────────────────────────


def create_isolated_root(
    repo_id: str, entry: dict
) -> tuple[Path, list[str]]:
    """Create an isolated temp root containing only declared external repo source.

    Copies the external repo into a repo_id-specific folder under the temp root.
    This preserves relative paths for retrieval verification.

    Returns (isolated_root_path, issues).
    """
    issues: list[str] = []
    source = entry.get("source", {})
    source_type = source.get("type", "")

    if source_type == "local_absolute_path":
        source_path = Path(source.get("path", ""))
        if not source_path.exists():
            issues.append(f"CRITICAL: Repo {repo_id}: source path {source_path} missing for isolation")
            tmp_dir = tempfile.mkdtemp(prefix=f"r15-isolated-{repo_id}-fail-")
            return Path(tmp_dir), issues
    else:
        issues.append(f"CRITICAL: Repo {repo_id}: unsupported source type {source_type} for isolation")
        tmp_dir = tempfile.mkdtemp(prefix=f"r15-isolated-{repo_id}-fail-")
        return Path(tmp_dir), issues

    tmp_dir = tempfile.mkdtemp(prefix=f"r15-isolated-{repo_id}-")
    isolated = Path(tmp_dir)

    # Create .git and .openlocus directories
    (isolated / ".git").mkdir(exist_ok=True)
    policy_dir = isolated / ".openlocus"
    policy_dir.mkdir(exist_ok=True)

    # Write policy.toml from repo lock
    policy_excludes = entry.get("policy", {}).get("exclude", POLICY_EXCLUDE_PATTERNS)
    exclude_values = ", ".join(json.dumps(p) for p in policy_excludes)
    (policy_dir / "policy.toml").write_text(
        "[index]\n"
        'include = ["**/*"]\n'
        f"exclude = [{exclude_values}]\n"
        "include_gitignored = false\n"
        "index_generated = false\n",
        encoding="utf-8",
    )

    # Copy only allowlisted source files into repo_id-specific folder. Never
    # copy the whole external repo and then delete artifacts: the isolation
    # boundary is an allowlist, not a cleanup pass.
    dst = isolated / repo_id
    extensions = set(entry.get("metadata", {}).get("extensions", list(SOURCE_EXTENSIONS)))
    copied = 0
    skipped_symlink = 0
    for dirpath, dirnames, filenames in os.walk(source_path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES and not d.startswith(".")]
        for fname in sorted(filenames):
            ext = os.path.splitext(fname)[1]
            if ext not in extensions:
                continue
            src_file = Path(dirpath) / fname
            if src_file.is_symlink():
                skipped_symlink += 1
                continue
            try:
                rel = src_file.relative_to(source_path)
            except ValueError:
                issues.append(f"CRITICAL: Repo {repo_id}: source file escaped root: {src_file}")
                continue
            dst_file = dst / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            copied += 1

    expected_files = int(entry.get("metadata", {}).get("files", 0))
    if copied != expected_files:
        issues.append(
            f"CRITICAL: Repo {repo_id}: isolated source copy file count mismatch "
            f"(expected {expected_files}, copied {copied}, skipped_symlink {skipped_symlink})"
        )

    # Fail closed if any forbidden component, symlink, or unexpected file type
    # exists in the isolated root. `.openlocus/policy.toml` and `.git/` marker
    # are the only non-source control files allowed.
    for dirpath, dirnames, filenames in os.walk(isolated):
        for d in dirnames:
            rel_dir = str((Path(dirpath) / d).relative_to(isolated)).replace(os.sep, "/")
            if rel_dir in {".git", ".openlocus"}:
                continue
            parts = rel_dir.split("/")
            if any(part in SKIP_DIR_NAMES for part in parts):
                issues.append(f"CRITICAL: Repo {repo_id}: forbidden directory in isolated root: {rel_dir}")
        for fname in filenames:
            full = Path(dirpath) / fname
            rel_file = str(full.relative_to(isolated)).replace(os.sep, "/")
            if rel_file == ".openlocus/policy.toml":
                continue
            if full.is_symlink():
                issues.append(f"CRITICAL: Repo {repo_id}: symlink in isolated root: {rel_file}")
                continue
            if not rel_file.startswith(f"{repo_id}/"):
                issues.append(f"CRITICAL: Repo {repo_id}: undeclared file in isolated root: {rel_file}")
                continue
            if Path(rel_file).suffix not in extensions:
                issues.append(f"CRITICAL: Repo {repo_id}: unexpected file extension in isolated root: {rel_file}")

    return isolated, issues


# ── Phase 1: RUN ─────────────────────────────────────────────────────────


def run_query(
    openlocus: str, method: str, query: str, cwd: str
) -> dict:
    """Run a single retrieval query via the OpenLocus CLI."""
    if method == "regex":
        cmd = [openlocus, "search", "regex", query, "--json"]
    elif method == "text":
        cmd = [openlocus, "search", "text", query, "--json"]
    elif method == "bm25":
        cmd = [openlocus, "search", "bm25", query, "--json"]
    elif method == "symbol":
        cmd = [openlocus, "search", "symbol", query, "--json"]
    elif method == "rrf":
        cmd = [openlocus, "retrieve", query, "--json"]
    else:
        return {
            "evidence": [],
            "latency_ms": 0,
            "returncode": -1,
            "stderr": f"unknown method: {method}",
        }

    t0 = time.perf_counter()
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True, cwd=cwd)
    latency_ms = int((time.perf_counter() - t0) * 1000)

    evidence: list[dict] = []
    try:
        raw = json.loads(proc.stdout) if proc.stdout.strip() else []
        if method == "rrf" and isinstance(raw, dict) and "evidence" in raw:
            evidence = raw["evidence"]
        elif isinstance(raw, list):
            evidence = raw
    except json.JSONDecodeError:
        pass

    return {
        "evidence": evidence,
        "latency_ms": latency_ms,
        "returncode": proc.returncode,
        "stderr": proc.stderr[:500] if proc.stderr else "",
    }


def check_canary_retrieval(
    openlocus: str, isolated_roots: dict[str, Path]
) -> tuple[dict[str, Any], list[str]]:
    """Query canary tokens inside isolated roots."""
    issues: list[str] = []
    checked = 0
    hits = 0
    failures = 0

    for repo_id, isolated in isolated_roots.items():
        for token in CANARY_TOKENS:
            checked += 1
            result = run_query(openlocus, "regex", token, str(isolated))
            clean_runtime_artifacts(isolated)
            if result.get("returncode") != 0:
                failures += 1
                issues.append(
                    f"CRITICAL: canary retrieval failed for repo {repo_id}: "
                    f"{result.get('stderr', '')[:200]}"
                )
                continue
            evidence = result.get("evidence", [])
            if evidence:
                hits += len(evidence)
                paths = [e.get("path", "") for e in evidence[:5]]
                issues.append(
                    f"CRITICAL: canary token was retrievable in isolated repo {repo_id}; "
                    f"token={token}, paths={paths}"
                )

    return {
        "checked": checked,
        "hits": hits,
        "failures": failures,
        "passed": hits == 0 and failures == 0,
    }, issues


def clean_runtime_artifacts(isolated: Path) -> None:
    """Remove CLI-generated runtime artifacts while preserving policy.toml.

    OpenLocus commands append traces under `.openlocus/traces`. Those traces are
    useful in normal operation but would pollute subsequent benchmark queries if
    left inside the isolated root. R15 treats them as runtime artifacts, not
    source data.
    """
    openlocus_dir = isolated / ".openlocus"
    if not openlocus_dir.exists():
        return
    for child in openlocus_dir.iterdir():
        if child.name == "policy.toml":
            continue
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            try:
                child.unlink()
            except OSError:
                pass


def validate_predictions_with_rust(
    openlocus: str,
    method: str,
    predictions: list[dict],
    isolated_roots: dict[str, Path],
) -> tuple[dict[str, Any], list[str]]:
    """Validate Evidence citations with Rust while isolated roots still exist.

    R15 predictions may use repo_id-prefixed paths because each external repo is
    copied under `<isolated>/<repo_id>/`. Running `openlocus citations validate`
    from the isolated root validates those paths against the exact bytes that
    retrieval saw, including content_sha and line ranges.
    """
    issues: list[str] = []
    total = 0
    valid = 0
    invalid = 0
    invocations = 0

    by_repo: dict[str, list[dict]] = {}
    for pred in predictions:
        repo_id = pred.get("repo_id", "")
        for evidence in pred.get("evidence", []):
            by_repo.setdefault(repo_id, []).append(evidence)

    for repo_id, evidence in by_repo.items():
        if not evidence:
            continue
        isolated = isolated_roots.get(repo_id)
        if isolated is None:
            issues.append(f"CRITICAL: {method}: missing isolated root for repo {repo_id}")
            total += len(evidence)
            invalid += len(evidence)
            continue

        tmp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                prefix=f"r15-{method}-{repo_id}-citations-",
                suffix=".json",
                delete=False,
                dir="/tmp/opencode",
                encoding="utf-8",
            ) as tmp:
                tmp.write(json.dumps(evidence) + "\n")
                tmp_name = tmp.name
            proc = subprocess.run(
                [openlocus, "citations", "validate", tmp_name, "--json"],
                check=False,
                text=True,
                capture_output=True,
                cwd=str(isolated),
            )
        finally:
            if tmp_name:
                try:
                    Path(tmp_name).unlink()
                except OSError:
                    pass
            clean_runtime_artifacts(isolated)
        invocations += 1
        if proc.returncode != 0:
            issues.append(
                f"CRITICAL: {method}: citation validator failed for repo {repo_id}: "
                f"{proc.stderr[:300]}"
            )
            total += len(evidence)
            invalid += len(evidence)
            continue

        try:
            result = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except json.JSONDecodeError:
            issues.append(
                f"CRITICAL: {method}: citation validator returned non-JSON for repo {repo_id}"
            )
            total += len(evidence)
            invalid += len(evidence)
            continue

        repo_total = int(result.get("total", 0))
        repo_valid = int(result.get("valid_count", 0))
        repo_invalid = int(result.get("invalid_count", 0))
        total += repo_total
        valid += repo_valid
        invalid += repo_invalid

        if repo_total != len(evidence):
            issues.append(
                f"CRITICAL: {method}: citation validator total mismatch for repo {repo_id} "
                f"(expected {len(evidence)}, got {repo_total})"
            )
        if repo_invalid != 0:
            issues.append(
                f"CRITICAL: {method}: {repo_invalid} invalid citations for repo {repo_id}"
            )

    rate = valid / total if total else 1.0
    if invalid != 0 or rate < 1.0:
        issues.append(
            f"CRITICAL: {method}: citation validity must be 1.0 "
            f"(valid={valid}, total={total}, invalid={invalid})"
        )

    return {
        "citation_validity": rate,
        "citation_valid_count": valid,
        "citation_total_count": total,
        "citation_invalid_count": invalid,
        "citation_validator_invocations": invocations,
        "citation_validation_mode": "fail_closed_hash_range_path",
        "citation_hash_checked": total > 0 and invocations > 0,
        "citation_not_applicable": total == 0,
    }, issues


def check_predictions_for_forbidden_paths(
    predictions: list[dict], method: str
) -> list[str]:
    """Check that no prediction contains forbidden path prefixes/components."""
    issues: list[str] = []
    for pred in predictions:
        for e in pred.get("evidence", []):
            path = e.get("path", "")
            for fp in FORBIDDEN_PREFIXES:
                forbidden_component = fp.strip("/")
                path_parts = path.replace("\\", "/").split("/")
                if path.startswith(fp) or forbidden_component in path_parts:
                    issues.append(
                        f"CRITICAL: {method} prediction for task {pred.get('task_id', '?')} "
                        f"has forbidden path prefix/component '{fp}': {path}"
                    )
    return issues


def audit_isolated_roots_runtime(isolated_roots: dict[str, Path], stage: str) -> list[str]:
    """Fail closed if benchmark/runtime artifacts appear in isolated roots."""
    issues: list[str] = []
    for repo_id, isolated in isolated_roots.items():
        for dirpath, dirnames, filenames in os.walk(isolated):
            for d in dirnames:
                rel_dir = str((Path(dirpath) / d).relative_to(isolated)).replace(os.sep, "/")
                if rel_dir in {".git", ".openlocus"}:
                    continue
                parts = rel_dir.split("/")
                if any(part in SKIP_DIR_NAMES for part in parts):
                    issues.append(
                        f"CRITICAL: runtime artifact audit ({stage}) found forbidden dir in repo {repo_id}: {rel_dir}"
                    )
            for fname in filenames:
                full = Path(dirpath) / fname
                rel_file = str(full.relative_to(isolated)).replace(os.sep, "/")
                if rel_file == ".openlocus/policy.toml":
                    continue
                if fname.startswith(".r15-") or "-citations-" in fname:
                    issues.append(
                        f"CRITICAL: runtime artifact audit ({stage}) found benchmark artifact in repo {repo_id}: {rel_file}"
                    )
                if full.is_symlink():
                    issues.append(
                        f"CRITICAL: runtime artifact audit ({stage}) found symlink in repo {repo_id}: {rel_file}"
                    )
                if not rel_file.startswith(f"{repo_id}/"):
                    issues.append(
                        f"CRITICAL: runtime artifact audit ({stage}) found undeclared file in repo {repo_id}: {rel_file}"
                    )
    return issues


def run_predictions(
    tasks: list[dict],
    openlocus: str,
    methods: list[str],
    repos: dict[str, dict],
) -> tuple[dict[str, list[dict]], dict[str, dict[str, Any]], dict[str, Any], list[str]]:
    """Phase 1: Run retrieval for all tasks/methods."""
    safety_issues: list[str] = []

    # Create isolated roots per repo
    isolated_roots: dict[str, Path] = {}
    for repo_id, entry in repos.items():
        isolated, iso_issues = create_isolated_root(repo_id, entry)
        isolated_roots[repo_id] = isolated
        safety_issues.extend(iso_issues)

    canary_summary, canary_issues = check_canary_retrieval(openlocus, isolated_roots)
    safety_issues.extend(canary_issues)

    all_predictions: dict[str, list[dict]] = {}
    citation_summaries: dict[str, dict[str, Any]] = {}

    for method in methods:
        safety_issues.extend(audit_isolated_roots_runtime(isolated_roots, f"before-{method}"))
        predictions: list[dict] = []
        for task in tasks:
            query = task["query"]
            task_id = task["task_id"]
            repo_id = task.get("repo_id", "")

            if repo_id not in isolated_roots:
                safety_issues.append(
                    f"CRITICAL: task {task_id} references unknown repo_id '{repo_id}'. "
                    "Refusing to fall back to the full workspace."
                )
                predictions.append(
                    {
                        "task_id": task_id,
                        "query": query,
                        "method": method,
                        "repo_id": repo_id,
                        "evidence": [],
                        "latency_ms": 0,
                        "returncode": -1,
                        "stderr": "unknown repo_id; fail-closed before CLI execution",
                    }
                )
                continue

            cwd = str(isolated_roots[repo_id])
            result = run_query(openlocus, method, query, cwd)
            clean_runtime_artifacts(isolated_roots[repo_id])

            if result.get("returncode") != 0:
                safety_issues.append(
                    f"CRITICAL: {method} query failed for task {task_id}: "
                    f"{result.get('stderr', '')[:300]}"
                )

            predictions.append(
                {
                    "task_id": task_id,
                    "query": query,
                    "method": method,
                    "repo_id": repo_id,
                    "evidence": result["evidence"],
                    "latency_ms": result["latency_ms"],
                    "returncode": result["returncode"],
                    "stderr": result["stderr"],
                }
            )

        forbidden_issues = check_predictions_for_forbidden_paths(predictions, method)
        safety_issues.extend(forbidden_issues)

        citation_summary, citation_issues = validate_predictions_with_rust(
            openlocus, method, predictions, isolated_roots
        )
        citation_summaries[method] = citation_summary
        safety_issues.extend(citation_issues)
        safety_issues.extend(audit_isolated_roots_runtime(isolated_roots, f"after-{method}"))

        all_predictions[method] = predictions

    # Cleanup isolated roots
    for isolated in isolated_roots.values():
        shutil.rmtree(isolated, ignore_errors=True)

    return all_predictions, citation_summaries, canary_summary, safety_issues


# ── Phase 2: SCORE ────────────────────────────────────────────────────────
# Reuse R14 scoring logic


def build_gold_line_set(label: dict) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for span in label.get("gold_spans", []):
        path = span.get("path", "")
        start = span.get("start_line", 0)
        end = span.get("end_line", 0)
        for ln in range(start, end + 1):
            result.add((path, ln))
    return result


def build_hard_negative_line_set(label: dict) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for hn in label.get("hard_negatives", []):
        path = hn.get("path", "")
        start = hn.get("start_line", 0)
        end = hn.get("end_line", 0)
        if start > 0 and end >= start:
            for ln in range(start, end + 1):
                result.add((path, ln))
        elif path:
            result.add((path, 0))
    return result


def get_gold_paths(label: dict) -> set[str]:
    return {span.get("path", "") for span in label.get("gold_spans", [])}


def get_hard_negative_paths(label: dict) -> set[str]:
    return {hn.get("path", "") for hn in label.get("hard_negatives", [])}


def match_path(pred_path: str, label_path: str, repo_id: str) -> bool:
    """Match prediction path against label path.

    In R15, predictions should be either label-relative or exactly one
    repo_id-prefixed path (`repo_id/<label_relative_path>`). Do not use
    arbitrary suffix matching, which can inflate scores for repeated paths.
    """
    if pred_path == label_path:
        return True
    if repo_id and pred_path == f"{repo_id}/{label_path}":
        return True
    return False


def file_recall_at_k(predictions: list[dict], gold: dict[str, dict], k: int) -> float:
    hits = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        total += 1
        gold_paths = get_gold_paths(gold[task_id])
        if not gold_paths:
            continue
        pred_paths = set()
        for e in pred["evidence"][:k]:
            pred_paths.add(e.get("path", ""))
        # Check exact or single repo_id-prefix matching
        for gp in gold_paths:
            for pp in pred_paths:
                if match_path(pp, gp, repo_id):
                    hits += 1
                    break
            else:
                continue
            break
    return hits / total if total else 0.0


def mrr(predictions: list[dict], gold: dict[str, dict]) -> float:
    total_rr = 0.0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        total += 1
        gold_paths = get_gold_paths(gold[task_id])
        if not gold_paths:
            continue
        for rank, e in enumerate(pred["evidence"], 1):
            pred_path = e.get("path", "")
            for gp in gold_paths:
                if match_path(pred_path, gp, repo_id):
                    total_rr += 1.0 / rank
                    break
            else:
                continue
            break
    return total_rr / total if total else 0.0


def span_f_beta_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int, beta: float = 0.5
) -> float:
    total_prec = 0.0
    total_rec = 0.0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        gold_lines = build_gold_line_set(gold[task_id])
        if not gold_lines:
            continue
        total += 1
        pred_lines: set[tuple[str, int]] = set()
        for e in pred["evidence"][:k]:
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            path = e.get("path", "")
            for ln in range(start, end + 1):
                pred_lines.add((path, ln))

        if not pred_lines:
            continue

        # Match with exact or strict repo_id-prefix path matching
        matched_lines: set[tuple[str, int]] = set()
        for (pp, pln) in pred_lines:
            for (gp, gln) in gold_lines:
                if match_path(pp, gp, repo_id) and pln == gln:
                    matched_lines.add((gp, gln))

        overlap = len(matched_lines)
        prec = overlap / len(pred_lines) if pred_lines else 0.0
        rec = overlap / len(gold_lines) if gold_lines else 0.0
        total_prec += prec
        total_rec += rec

    avg_prec = total_prec / total if total else 0.0
    avg_rec = total_rec / total if total else 0.0

    if avg_prec + avg_rec == 0:
        return 0.0
    beta2 = beta * beta
    return (1 + beta2) * avg_prec * avg_rec / (beta2 * avg_prec + avg_rec)


def token_waste_ratio_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int
) -> float:
    total_waste = 0.0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        gold_lines = build_gold_line_set(gold[task_id])
        if not gold_lines:
            continue
        total += 1
        all_pred_lines = 0
        non_gold_lines = 0
        for e in pred["evidence"][:k]:
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            path = e.get("path", "")
            for ln in range(start, end + 1):
                all_pred_lines += 1
                matched = any(
                    match_path(path, gp, repo_id) and ln == gln
                    for gp, gln in gold_lines
                )
                if not matched:
                    non_gold_lines += 1
        if all_pred_lines > 0:
            total_waste += non_gold_lines / all_pred_lines
    return total_waste / total if total else 0.0


def hard_negative_hit_rate_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int
) -> float:
    hits = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        label = gold[task_id]
        hard_neg_lines = build_hard_negative_line_set(label)
        hard_neg_paths = get_hard_negative_paths(label)
        if not hard_neg_paths:
            continue
        total += 1
        for e in pred["evidence"][:k]:
            pred_path = e.get("path", "")
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            if start > 0 and end >= start:
                for ln in range(start, end + 1):
                    for (hp, hln) in hard_neg_lines:
                        if match_path(pred_path, hp, repo_id) and ln == hln:
                            hits += 1
                            break
                    else:
                        if any(match_path(pred_path, hp, repo_id) and hln == 0 for hp, hln in hard_neg_lines):
                            hits += 1
                            break
                        continue
                    break
    return hits / total if total else 0.0


def negative_nonempty_rate_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int
) -> float:
    nonempty = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        if task_id not in gold:
            continue
        label = gold[task_id]
        if label.get("gold_spans"):
            continue
        total += 1
        if pred["evidence"][:k]:
            nonempty += 1
    return nonempty / total if total else 0.0


def compute_latency_stats(predictions: list[dict]) -> dict[str, Any]:
    latencies = sorted(p.get("latency_ms", 0) for p in predictions)
    if not latencies:
        return {"p50": 0, "p95": 0, "max": 0, "count": 0}

    def percentile(data: list, p: float) -> int:
        idx = int(len(data) * p / 100.0)
        return data[min(idx, len(data) - 1)]

    return {
        "p50": percentile(latencies, 50),
        "p95": percentile(latencies, 95),
        "max": latencies[-1],
        "count": len(latencies),
    }


def score_predictions(
    predictions: list[dict],
    gold: dict[str, dict],
    citation_summary: dict[str, Any],
    method: str,
) -> dict[str, Any]:
    """Phase 2: Score predictions using private labels."""
    total = len(predictions)
    ok = sum(1 for p in predictions if p.get("returncode") == 0)

    metrics: dict[str, Any] = {
        "total_tasks": total,
        "successful": ok,
        "success_rate": ok / total if total else 0.0,
        "citation_validity": citation_summary.get("citation_validity", 0.0),
        "citation_valid_count": citation_summary.get("citation_valid_count", 0),
        "citation_total_count": citation_summary.get("citation_total_count", 0),
        "citation_invalid_count": citation_summary.get("citation_invalid_count", 0),
        "citation_validator_invocations": citation_summary.get("citation_validator_invocations", 0),
        "citation_validation_mode": citation_summary.get("citation_validation_mode", "missing"),
        "citation_hash_checked": citation_summary.get("citation_hash_checked", False),
    }

    non_neg_gold = {tid: g for tid, g in gold.items() if g.get("gold_spans")}
    evaluable_gold = {tid: g for tid, g in gold.items() if g.get("gold_spans") or g.get("hard_negatives")}
    negative_gold = {tid: g for tid, g in gold.items() if not g.get("gold_spans")}

    if non_neg_gold:
        for k in [1, 5, 10]:
            metrics[f"file_recall@{k}"] = file_recall_at_k(predictions, non_neg_gold, k)
        metrics["mrr"] = mrr(predictions, non_neg_gold)
        metrics["span_f0.5@10"] = span_f_beta_at_k(predictions, non_neg_gold, 10, 0.5)
        metrics["token_waste@10"] = token_waste_ratio_at_k(predictions, non_neg_gold, 10)

    if evaluable_gold:
        metrics["hard_negative_hit_rate@10"] = hard_negative_hit_rate_at_k(
            predictions, evaluable_gold, 10
        )

    if negative_gold:
        metrics["negative_nonempty_rate@10"] = negative_nonempty_rate_at_k(
            predictions, negative_gold, 10
        )

    metrics["latency"] = compute_latency_stats(predictions)

    return metrics


# ── Report generation ──────────────────────────────────────────────────


def generate_markdown_summary(
    all_metrics: dict[str, dict[str, Any]],
    safety_issues: list[str],
) -> str:
    lines = [
        "# R15 Multi-Repo Benchmark Summary",
        "",
        "**This is a mined benchmark expansion, not a quality conclusion.**",
        "",
    ]

    if safety_issues:
        lines.append("## Safety Issues")
        for issue in safety_issues:
            lines.append(f"- ❌ {issue}")
        lines.append("")
    else:
        lines.append("## Safety Checks: ✅ All Passed")
        lines.append("")

    lines.append("## Retrieval Metrics")
    lines.append("")
    metric_keys = [
        "file_recall@1", "file_recall@5", "file_recall@10",
        "mrr", "span_f0.5@10",
        "token_waste@10",
        "hard_negative_hit_rate@10",
        "negative_nonempty_rate@10",
    ]

    header = "| Metric | " + " | ".join(all_metrics.keys()) + " |"
    separator = "|---|" + "|".join("---" for _ in all_metrics) + "|"
    lines.append(header)
    lines.append(separator)

    for key in metric_keys:
        row = f"| {key} |"
        for method_metrics in all_metrics.values():
            val = method_metrics.get(key)
            if val is None:
                row += " N/A |"
            elif isinstance(val, float):
                row += f" {val:.3f} |"
            else:
                row += f" {val} |"
        lines.append(row)

    lines.append("")
    lines.append("## Caveats")
    lines.append("- R15 is a mined benchmark expansion, not a quality conclusion.")
    lines.append("- Multi-language symbol extraction is heuristic; labels may be imprecise.")
    lines.append("- External local repos are workspace snapshots; not modified.")
    lines.append("- OpenLocus CLI may not support all file extensions (.mjs, .go, etc.).")
    lines.append("- Citation validity is checked by the Rust validator inside isolated roots.")

    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="R15 External Multi-Repo Evidence Benchmark Runner/Scorer"
    )
    parser.add_argument("--manifest", required=True, help="Path to dataset_manifest.json")
    parser.add_argument("--openlocus", default="target/debug/openlocus", help="Path to openlocus binary")
    parser.add_argument("--methods", default="regex,bm25", help="Comma-separated methods")
    parser.add_argument("--tier", default="M", choices=["M", "L", "stress"], help="Which tier to benchmark")
    parser.add_argument("--out", required=True, help="Output path for JSON report")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)
    out_dir = manifest_path.parent

    tier_name_map = {"M": "medium", "L": "large", "stress": "stress"}
    tier_name = tier_name_map[args.tier]

    # Validate tier is populated
    tier_status = manifest.get("current_status", {}).get(args.tier, {})
    if not tier_status.get("populated", False):
        print(
            f"ERROR: R15-{args.tier} tier is not populated.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load repo lock
    repos = load_repo_lock(out_dir)
    if not repos:
        print("ERROR: No repos found in repos.lock.jsonl", file=sys.stderr)
        sys.exit(1)

    # Validate repo lock
    lock_issues, lock_info = validate_repo_lock(repos)
    safety_issues: list[str] = list(lock_issues)
    for info in lock_info:
        print(f"  ℹ️  {info}")

    # Phase 1: RUN
    tasks_path = out_dir / "tasks" / f"{tier_name}.jsonl"
    tasks = load_jsonl(tasks_path)
    if not tasks:
        print(f"ERROR: No tasks found at {tasks_path}", file=sys.stderr)
        sys.exit(1)

    # Verify no gold info in tasks
    for task in tasks:
        for field in ["gold_spans", "gold_paths", "gold_lines", "hard_negatives"]:
            if field in task:
                safety_issues.append(f"LEAK: task {task['task_id']} contains {field}")

    print(f"R15-{args.tier} Benchmark: {len(tasks)} tasks, {len(repos)} repos")
    print(f"  Phase 1: RUN (public tasks only, no labels)")

    openlocus_path = str(Path(args.openlocus).resolve())
    methods = [m.strip() for m in args.methods.split(",")]

    all_predictions, citation_summaries, canary_summary, run_issues = run_predictions(
        tasks, openlocus_path, methods, repos
    )
    safety_issues.extend(run_issues)

    # Store predictions
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for method, predictions in all_predictions.items():
        pred_path = out_path.parent / f"r15-{tier_name}-{method}-predictions.jsonl"
        with pred_path.open("w", encoding="utf-8") as f:
            for pred in predictions:
                f.write(json.dumps(pred) + "\n")

    # Phase 2: SCORE
    print(f"  Phase 2: SCORE (labels only, no CLI)")
    labels_path = out_dir / "labels" / f"{tier_name}.jsonl"
    labels_list = load_jsonl(labels_path)
    gold = {l["task_id"]: l for l in labels_list}

    all_metrics: dict[str, dict[str, Any]] = {}
    for method, predictions in all_predictions.items():
        metrics = score_predictions(
            predictions, gold, citation_summaries.get(method, {}), method
        )
        all_metrics[method] = metrics

    # Safety gates
    for method, metrics in all_metrics.items():
        if metrics.get("citation_validity") != 1.0:
            safety_issues.append(
                f"CRITICAL: {method} citation_validity={metrics.get('citation_validity')} != 1.0"
            )
        if metrics.get("citation_hash_checked") is not True and metrics.get("citation_not_applicable") is not True:
            safety_issues.append(
                f"CRITICAL: {method} citation_hash_checked is not true"
            )

    # Generate report
    report = {
        "schema_version": SCHEMA_VERSION,
        "tier": args.tier,
        "tier_name": tier_name,
        "tasks": len(tasks),
        "repos": len(repos),
        "gold_labels": len(gold),
        "methods": methods,
        "metrics": all_metrics,
        "safety_issues": safety_issues,
        "safety_passed": len(safety_issues) == 0,
        "canary_retrieval": canary_summary,
        "phases": {
            "run": "public_tasks_only_no_labels",
            "score": "labels_only_no_cli",
            "isolation": "temp_root_per_repo_with_repo_id_folder",
            "citation_mode": "fail_closed_hash_range_path",
            "path_matching": "exact_or_single_repo_id_prefix",
            "policy": "isolated_policy_toml_from_repo_lock",
            "source_type": "external_local_absolute_path",
        },
    }

    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    md_path = out_path.with_suffix(".md")
    md_content = generate_markdown_summary(all_metrics, safety_issues)
    md_path.write_text(md_content, encoding="utf-8")

    # Print summary
    print(f"\n{'='*60}")
    print(f"R15-{args.tier} Benchmark Results")
    print(f"{'='*60}")
    for method, metrics in all_metrics.items():
        print(f"\n{method}:")
        for key in [
            "file_recall@1", "file_recall@5", "file_recall@10",
            "mrr", "span_f0.5@10",
            "hard_negative_hit_rate@10", "negative_nonempty_rate@10",
        ]:
            val = metrics.get(key)
            if val is not None:
                print(f"  {key}: {val:.3f}" if isinstance(val, float) else f"  {key}: {val}")

    if safety_issues:
        print(f"\n⚠️  Safety issues: {len(safety_issues)}")
        for issue in safety_issues:
            print(f"  - {issue}")
    else:
        print(f"\n✅ Safety checks passed")

    print(f"\nReport: {out_path}")
    print(f"Summary: {md_path}")

    if safety_issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
