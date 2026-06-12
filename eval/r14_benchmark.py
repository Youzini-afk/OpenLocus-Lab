#!/usr/bin/env python3
"""R14 Scaled Multi-Repo Evidence Benchmark Runner/Scorer.

Runs retrieval methods against R14 benchmark tasks, computes metrics,
and outputs a JSON report and markdown summary.

Architecture: strictly separated RUN and SCORE phases.
  - Phase 1 (RUN): loads only public tasks + repo lock. Creates isolated
    benchmark roots. Runs retrieval CLI. Writes predictions. Never reads
    labels/gold.
  - Phase 2 (SCORE): loads predictions + private labels. Computes metrics.
    Never invokes retrieval CLI.

Safety:
- Runner never loads private labels/gold
- Retrieval runs inside isolated temp roots (no fixtures/eval/docs/runs)
- Repo lock content manifest is re-verified (normalized hash)
- Citation validation is fail-closed: every citation must be hash+range+path valid
- Predictions with forbidden prefixes are critical failures
- Fails closed on all safety issues

Usage:
    python3 eval/r14_benchmark.py \
        --manifest fixtures/r14/dataset_manifest.json \
        --openlocus target/debug/openlocus \
        --methods regex,bm25,symbol,rrf \
        --repos-root . \
        --out runs/r14-report.json
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


# ── Forbidden prefixes: any prediction path starting with these is CRITICAL ──

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
    "R14_CANARY_fixture_label_secret_7a3f",
    "R14_CANARY_eval_benchmark_secret_9b2e",
    "R14_CANARY_docs_summary_secret_4c1d",
    "R14_CANARY_runs_prediction_secret_8e5a",
]

# ── Canonical policy exclude patterns (glob-style) ──────────────────────

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
]


# ── Data loading ───────────────────────────────────────────────────────


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file into a list of dicts."""
    items = []
    if not path.exists():
        return items
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            items.append(json.loads(line))
    return items


def load_manifest(path: Path) -> dict[str, Any]:
    """Load dataset manifest JSON."""
    if not path.exists():
        print(f"ERROR: Manifest not found: {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def load_repo_lock(out_dir: Path) -> dict[str, dict]:
    """Load repos.lock.jsonl indexed by repo_id."""
    lock_path = out_dir / "repos.lock.jsonl"
    repos = {}
    for entry in load_jsonl(lock_path):
        repos[entry["repo_id"]] = entry
    return repos


# ── Normalized content manifest ────────────────────────────────────────


def compute_normalized_manifest_sha(
    repos_root: Path, crate_dirs: list[str]
) -> tuple[str, int, int, list[dict[str, Any]]]:
    """Compute normalized content manifest SHA for a set of crate dirs.

    Algorithm: sort all .rs files by relative path. For each file:
    - relative path (POSIX, forward-slash)
    - SHA-256 of file contents
    - line count
    Concatenate as JSON lines, SHA-256 the result.

    Returns (manifest_sha, file_count, total_lines, per_file_entries).
    """
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


# ── Repo lock validation (strict: recompute manifest) ──────────────────


def validate_repo_lock(
    repos: dict[str, dict], repos_root: Path
) -> tuple[list[str], list[str]]:
    """Validate repo lock entries with content manifest re-verification.

    Returns (issues, info_messages). issues with CRITICAL cause fail-closed.
    """
    issues: list[str] = []
    info: list[str] = []

    for repo_id, entry in repos.items():
        source = entry.get("source", {})
        if source.get("type") != "local_path":
            issues.append(f"CRITICAL: Repo {repo_id}: unsupported source type {source.get('type')}")
            continue

        paths_str = source.get("path", "")
        crate_dirs = [p.strip() for p in paths_str.split(",") if p.strip()]

        for p in crate_dirs:
            full_path = repos_root / p
            if not full_path.exists():
                issues.append(f"CRITICAL: Repo {repo_id}: path {p} does not exist at {full_path}")

        # Check policy exclude patterns are glob-style
        policy_excludes = entry.get("policy", {}).get("exclude", [])
        required_patterns = {"fixtures", "eval", "docs", "runs", ".openlocus", "target"}
        for req in required_patterns:
            found = any(req in exc for exc in policy_excludes)
            if not found:
                issues.append(
                    f"CRITICAL: Repo {repo_id}: policy exclude missing '{req}/**' pattern"
                )

        # Recompute normalized manifest SHA
        locked_sha = entry.get("content_manifest_sha", "")
        if not locked_sha:
            issues.append(f"CRITICAL: Repo {repo_id}: missing content_manifest_sha")
            continue

        computed_sha, file_count, total_lines, _per_file = compute_normalized_manifest_sha(
            repos_root, crate_dirs
        )

        if computed_sha != locked_sha:
            issues.append(
                f"CRITICAL: Repo {repo_id}: content_manifest_sha MISMATCH "
                f"(locked={locked_sha[:16]}... computed={computed_sha[:16]}...). "
                f"Repo content has changed since lock was created. "
                f"Run eval/r14_generate_dataset.py to refresh."
            )
        else:
            info.append(
                f"Repo {repo_id}: content_manifest_sha verified ({file_count} files, {total_lines} lines)"
            )

        # Verify file/line counts match metadata
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


# ── Isolated benchmark root ────────────────────────────────────────────


def create_isolated_root(
    repos_root: Path, repo_id: str, entry: dict
) -> tuple[Path, list[str]]:
    """Create an isolated temp root containing only declared source paths.

    Copies only the source paths declared in the repo lock. Never includes
    fixtures/, eval/, docs/, runs/, .openlocus/, target/ etc.

    Returns (isolated_root_path, issues).
    """
    issues: list[str] = []
    source = entry.get("source", {})
    paths_str = source.get("path", "")
    crate_dirs = [p.strip() for p in paths_str.split(",") if p.strip()]

    tmp_dir = tempfile.mkdtemp(prefix=f"r14-isolated-{repo_id}-")
    isolated = Path(tmp_dir)
    (isolated / ".git").mkdir(exist_ok=True)
    policy_dir = isolated / ".openlocus"
    policy_dir.mkdir(exist_ok=True)
    policy_excludes = entry.get("policy", {}).get("exclude", POLICY_EXCLUDE_PATTERNS)
    policy_content = {
        "index": {
            "include": ["**/*"],
            "exclude": policy_excludes,
            "include_gitignored": False,
            "index_generated": False,
        }
    }
    # Minimal TOML writer to avoid adding dependencies to this eval script.
    exclude_values = ", ".join(json.dumps(p) for p in policy_content["index"]["exclude"])
    (policy_dir / "policy.toml").write_text(
        "[index]\n"
        'include = ["**/*"]\n'
        f"exclude = [{exclude_values}]\n"
        "include_gitignored = false\n"
        "index_generated = false\n",
        encoding="utf-8",
    )

    for crate_dir in crate_dirs:
        src = repos_root / crate_dir
        if not src.exists():
            issues.append(f"CRITICAL: Repo {repo_id}: source path {crate_dir} missing for isolation")
            continue

        dst = isolated / crate_dir
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, symlinks=True)

    # Verify no forbidden directories leaked into the isolated root. Keep the
    # isolated benchmark policy file; it is required so CLI retrieval enforces
    # the lock policy instead of default workspace policy.
    for prefix in FORBIDDEN_PREFIXES:
        # Check if any top-level or nested forbidden dir exists
        for dirpath, dirnames, _filenames in os.walk(isolated):
            for d in list(dirnames):
                check_path = Path(dirpath) / d
                rel = str(check_path.relative_to(isolated)).replace(os.sep, "/") + "/"
                if rel == ".openlocus/":
                    continue
                for fp in FORBIDDEN_PREFIXES:
                    if rel.startswith(fp) or fp.rstrip("/") in rel:
                        # Remove the forbidden directory
                        shutil.rmtree(check_path, ignore_errors=True)
                        dirnames.remove(d)
                        break

    return isolated, issues


def check_canary_retrieval(
    openlocus: str, isolated_roots: dict[str, Path]
) -> tuple[dict[str, Any], list[str]]:
    """Query artifact-only canary tokens inside isolated roots.

    If retrieval is accidentally run against the workspace instead of an
    isolated root, these tokens are likely to be found in labels/eval/docs/runs
    artifacts and the benchmark must fail closed.
    """
    issues: list[str] = []
    checked = 0
    hits = 0
    failures = 0

    for repo_id, isolated in isolated_roots.items():
        for token in CANARY_TOKENS:
            checked += 1
            result = run_query(openlocus, "regex", token, str(isolated))
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


def cleanup_isolated_root(isolated: Path) -> None:
    """Remove an isolated temp root."""
    shutil.rmtree(isolated, ignore_errors=True)


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


# ── Phase 1: RUN (public tasks only, no labels) ────────────────────────


def run_query(
    openlocus: str,
    method: str,
    query: str,
    cwd: str,
    channels: str = "",
    index_mode: str = "temp",
) -> dict:
    """Run a single retrieval query via the OpenLocus CLI."""
    if method == "regex":
        cmd = [openlocus, "search", "regex", query, "--json"]
    elif method == "text":
        cmd = [openlocus, "search", "text", query, "--json"]
    elif method == "bm25":
        if index_mode == "persistent":
            cmd = [openlocus, "search", "bm25", query, "--index", "persistent", "--json"]
        else:
            cmd = [openlocus, "search", "bm25", query, "--json"]
    elif method == "symbol":
        cmd = [openlocus, "search", "symbol", query, "--json"]
    elif method == "rrf":
        cmd = [openlocus, "retrieve", query, "--json"]
        if channels:
            cmd.extend(["--channels", channels])
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


def validate_predictions_with_rust(
    openlocus: str,
    method: str,
    predictions: list[dict],
    isolated_roots: dict[str, Path],
) -> tuple[dict[str, Any], list[str]]:
    """Validate Evidence citations with the Rust validator while isolated roots exist.

    This keeps the RUN phase label-free while making citation validity a real
    hash/range/path gate. The scorer consumes this summary later; it does not
    recompute citations after the isolated roots have been cleaned up.
    """
    issues: list[str] = []
    total = 0
    valid = 0
    invalid = 0

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
            invalid += len(evidence)
            total += len(evidence)
            continue

        citation_file = isolated / f".r14-{method}-citations.json"
        citation_file.write_text(json.dumps(evidence) + "\n", encoding="utf-8")
        proc = subprocess.run(
            [openlocus, "citations", "validate", str(citation_file), "--json"],
            check=False,
            text=True,
            capture_output=True,
            cwd=str(isolated),
        )
        if proc.returncode != 0:
            issues.append(
                f"CRITICAL: {method}: citation validator failed for repo {repo_id}: "
                f"{proc.stderr[:300]}"
            )
            invalid += len(evidence)
            total += len(evidence)
            continue
        try:
            result = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except json.JSONDecodeError:
            issues.append(
                f"CRITICAL: {method}: citation validator returned non-JSON for repo {repo_id}"
            )
            invalid += len(evidence)
            total += len(evidence)
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
        "citation_validation_mode": "fail_closed_hash_range_path",
        "citation_hash_checked": True,
    }, issues


def run_predictions(
    tasks: list[dict],
    openlocus: str,
    methods: list[str],
    repos_root: Path,
    repos: dict[str, dict],
    channels: str,
    index_mode: str,
) -> tuple[dict[str, list[dict]], dict[str, dict[str, Any]], dict[str, Any], list[str]]:
    """Phase 1: Run retrieval for all tasks/methods. Returns (method->predictions, safety_issues).

    NEVER loads labels/gold. Only uses public tasks and repo lock.
    """
    safety_issues: list[str] = []

    # Create isolated roots per repo
    isolated_roots: dict[str, Path] = {}
    for repo_id, entry in repos.items():
        isolated, iso_issues = create_isolated_root(repos_root, repo_id, entry)
        isolated_roots[repo_id] = isolated
        safety_issues.extend(iso_issues)

    canary_summary, canary_issues = check_canary_retrieval(openlocus, isolated_roots)
    safety_issues.extend(canary_issues)

    all_predictions: dict[str, list[dict]] = {}
    citation_summaries: dict[str, dict[str, Any]] = {}

    for method in methods:
        predictions: list[dict] = []
        for task in tasks:
            query = task["query"]
            task_id = task["task_id"]
            repo_id = task.get("repo_id", "")

            # Run in the isolated root for this repo
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

            result = run_query(
                openlocus, method, query, cwd, channels, index_mode
            )
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

        # Check predictions for forbidden paths
        forbidden_issues = check_predictions_for_forbidden_paths(predictions, method)
        safety_issues.extend(forbidden_issues)

        citation_summary, citation_issues = validate_predictions_with_rust(
            openlocus, method, predictions, isolated_roots
        )
        citation_summaries[method] = citation_summary
        safety_issues.extend(citation_issues)

        all_predictions[method] = predictions

    # Cleanup isolated roots
    for isolated in isolated_roots.values():
        cleanup_isolated_root(isolated)

    return all_predictions, citation_summaries, canary_summary, safety_issues


# ── Phase 2: SCORE (labels only, no CLI calls) ────────────────────────


def build_gold_line_set(label: dict) -> set[tuple[str, int]]:
    """Build set of (path, line_number) from gold_spans."""
    result: set[tuple[str, int]] = set()
    for span in label.get("gold_spans", []):
        path = span.get("path", "")
        start = span.get("start_line", 0)
        end = span.get("end_line", 0)
        for ln in range(start, end + 1):
            result.add((path, ln))
    return result


def build_hard_negative_line_set(label: dict) -> set[tuple[str, int]]:
    """Build set of (path, line_number) from hard_negatives (span-aware)."""
    result: set[tuple[str, int]] = set()
    for hn in label.get("hard_negatives", []):
        path = hn.get("path", "")
        start = hn.get("start_line", 0)
        end = hn.get("end_line", 0)
        if start > 0 and end >= start:
            for ln in range(start, end + 1):
                result.add((path, ln))
        elif path:
            # File-level hard negative: no line range
            result.add((path, 0))
    return result


def get_gold_paths(label: dict) -> set[str]:
    """Get set of gold file paths from gold_spans."""
    return {span.get("path", "") for span in label.get("gold_spans", [])}


def get_hard_negative_paths(label: dict) -> set[str]:
    """Get set of hard negative file paths."""
    return {hn.get("path", "") for hn in label.get("hard_negatives", [])}


def file_recall_at_k(predictions: list[dict], gold: dict[str, dict], k: int) -> float:
    """Fraction of tasks where at least 1 gold file appears in top-k."""
    hits = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        if task_id not in gold:
            continue
        total += 1
        gold_paths = get_gold_paths(gold[task_id])
        if not gold_paths:
            continue
        pred_paths = set(e.get("path", "") for e in pred["evidence"][:k])
        if gold_paths & pred_paths:
            hits += 1
    return hits / total if total else 0.0


def mrr(predictions: list[dict], gold: dict[str, dict]) -> float:
    """Mean Reciprocal Rank based on file match."""
    total_rr = 0.0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        if task_id not in gold:
            continue
        total += 1
        gold_paths = get_gold_paths(gold[task_id])
        if not gold_paths:
            continue
        for rank, e in enumerate(pred["evidence"], 1):
            if e.get("path", "") in gold_paths:
                total_rr += 1.0 / rank
                break
    return total_rr / total if total else 0.0


def span_f_beta_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int, beta: float = 0.5
) -> float:
    """Span F-beta combining line precision and recall."""
    total_prec = 0.0
    total_rec = 0.0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
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

        overlap = gold_lines & pred_lines
        prec = len(overlap) / len(pred_lines) if pred_lines else 0.0
        rec = len(overlap) / len(gold_lines) if gold_lines else 0.0
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
    """Ratio of non-gold lines to total lines in top-k (lower is better)."""
    total_waste = 0.0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
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
                if (path, ln) not in gold_lines:
                    non_gold_lines += 1
        if all_pred_lines > 0:
            total_waste += non_gold_lines / all_pred_lines
    return total_waste / total if total else 0.0


def wrong_span_rate_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int
) -> float:
    """Fraction of evidence on a gold file with zero line overlap with gold spans."""
    total_wrong = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        if task_id not in gold:
            continue
        gold_paths = get_gold_paths(gold[task_id])
        gold_lines = build_gold_line_set(gold[task_id])
        if not gold_paths:
            continue
        for e in pred["evidence"][:k]:
            path = e.get("path", "")
            if path not in gold_paths:
                continue
            total += 1
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            has_overlap = any(
                (path, ln) in gold_lines for ln in range(start, end + 1)
            )
            if not has_overlap:
                total_wrong += 1
    return total_wrong / total if total else 0.0


def zero_overlap_evidence_rate_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int
) -> float:
    """Fraction of all top-k evidence with zero line overlap with any gold span."""
    total_wrong = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        if task_id not in gold:
            continue
        gold_lines = build_gold_line_set(gold[task_id])
        if not gold_lines:
            continue
        for e in pred["evidence"][:k]:
            total += 1
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            path = e.get("path", "")
            has_overlap = any(
                (path, ln) in gold_lines for ln in range(start, end + 1)
            )
            if not has_overlap:
                total_wrong += 1
    return total_wrong / total if total else 0.0


def hard_negative_hit_rate_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int
) -> float:
    """Span-aware hard negative hit rate: fraction of tasks where a hard negative
    SPAN (not just file) overlaps with top-k predictions (lower is better)."""
    hits = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        if task_id not in gold:
            continue
        label = gold[task_id]
        hard_neg_lines = build_hard_negative_line_set(label)
        hard_neg_paths = get_hard_negative_paths(label)
        if not hard_neg_paths:
            continue
        total += 1
        # Check span-level overlap
        for e in pred["evidence"][:k]:
            pred_path = e.get("path", "")
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            # Span-level hard negative hit. Only spanless hard negatives fall
            # back to file-level matching; spanful hard negatives require line
            # overlap so same-file gold evidence is not miscounted as a hard
            # negative hit.
            if start > 0 and end >= start:
                for ln in range(start, end + 1):
                    if (pred_path, ln) in hard_neg_lines:
                        hits += 1
                        break
                else:
                    if (pred_path, 0) in hard_neg_lines:
                        hits += 1
                        break
                    continue
                break
    return hits / total if total else 0.0


def negative_nonempty_rate_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int
) -> float:
    """For negative tasks: fraction that return any evidence in top-k (lower=better).

    A method returning results for negative tasks is producing false positives.
    """
    nonempty = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        if task_id not in gold:
            continue
        label = gold[task_id]
        if label.get("gold_spans"):
            continue  # Skip non-negative tasks
        total += 1
        if pred["evidence"][:k]:
            nonempty += 1
    return nonempty / total if total else 0.0


def compute_latency_stats(predictions: list[dict]) -> dict[str, Any]:
    """Compute latency p50/p95/max from predictions."""
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
    """Phase 2: Score predictions using private labels. Never invokes CLI."""
    total = len(predictions)
    ok = sum(1 for p in predictions if p.get("returncode") == 0)

    metrics: dict[str, Any] = {
        "total_tasks": total,
        "successful": ok,
        "success_rate": ok / total if total else 0.0,
    }

    # Citation validity is computed in RUN phase by Rust validator while the
    # isolated roots still exist. SCORE consumes the summary only; no CLI here.
    metrics["citation_validity"] = citation_summary.get("citation_validity", 0.0)
    metrics["citation_valid_count"] = citation_summary.get("citation_valid_count", 0)
    metrics["citation_total_count"] = citation_summary.get("citation_total_count", 0)
    metrics["citation_invalid_count"] = citation_summary.get("citation_invalid_count", 0)
    metrics["citation_validation_mode"] = citation_summary.get(
        "citation_validation_mode", "missing"
    )
    metrics["citation_hash_checked"] = citation_summary.get("citation_hash_checked", False)

    # File-level metrics (skip negative tasks with no gold)
    non_neg_gold = {
        tid: g for tid, g in gold.items() if g.get("gold_spans")
    }
    # Include tasks with hard_negatives for hard_negative_hit_rate
    evaluable_gold = {
        tid: g for tid, g in gold.items()
        if g.get("gold_spans") or g.get("hard_negatives")
    }
    # Negative tasks only
    negative_gold = {
        tid: g for tid, g in gold.items()
        if not g.get("gold_spans")
    }

    if non_neg_gold:
        for k in [1, 5, 10]:
            metrics[f"file_recall@{k}"] = file_recall_at_k(predictions, non_neg_gold, k)
        metrics["mrr"] = mrr(predictions, non_neg_gold)
        metrics["span_f0.5@10"] = span_f_beta_at_k(predictions, non_neg_gold, 10, 0.5)
        metrics["token_waste@10"] = token_waste_ratio_at_k(predictions, non_neg_gold, 10)
        metrics["wrong_span_rate@10"] = wrong_span_rate_at_k(predictions, non_neg_gold, 10)
        metrics["zero_overlap_evidence_rate@10"] = zero_overlap_evidence_rate_at_k(
            predictions, non_neg_gold, 10
        )

    if evaluable_gold:
        metrics["hard_negative_hit_rate@10"] = hard_negative_hit_rate_at_k(
            predictions, evaluable_gold, 10
        )

    if negative_gold:
        metrics["negative_nonempty_rate@10"] = negative_nonempty_rate_at_k(
            predictions, negative_gold, 10
        )

    # Latency
    metrics["latency"] = compute_latency_stats(predictions)

    # Store citation issues in metrics for upstream safety gate
    metrics["_citation_issues"] = []

    return metrics


# ── Report generation ──────────────────────────────────────────────────


def generate_markdown_summary(
    all_metrics: dict[str, dict[str, Any]],
    safety_issues: list[str],
    tier: str,
) -> str:
    """Generate a markdown summary of benchmark results."""
    lines = [
        f"# R14-{tier} Benchmark Summary",
        "",
        "**This is a benchmark foundation report, not a quality conclusion.**",
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

    # Metrics table
    lines.append("## Retrieval Metrics")
    lines.append("")
    metric_keys = [
        "file_recall@1", "file_recall@5", "file_recall@10",
        "mrr", "span_f0.5@10",
        "token_waste@10", "wrong_span_rate@10",
        "zero_overlap_evidence_rate@10",
        "hard_negative_hit_rate@10",
        "negative_nonempty_rate@10",
        "citation_validity",
        "success_rate",
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

    # Latency table
    lines.append("")
    lines.append("## Latency")
    lines.append("")
    lat_header = "| Method | p50 (ms) | p95 (ms) | max (ms) |"
    lat_sep = "|---|---|---|---|"
    lines.append(lat_header)
    lines.append(lat_sep)
    for method, method_metrics in all_metrics.items():
        lat = method_metrics.get("latency", {})
        lines.append(
            f"| {method} | {lat.get('p50', 0)} | {lat.get('p95', 0)} | {lat.get('max', 0)} |"
        )

    lines.append("")
    lines.append("## Caveats")
    lines.append("- R14-S is a foundation validation, not a quality conclusion.")
    lines.append("- Mined labels are not human-verified; line ranges may be imprecise.")
    lines.append("- Hard negatives are first-class data measuring precision under ambiguity.")
    lines.append("- Citation validity is a safety gate, not a quality metric.")
    lines.append("- No dense/LLM/graph quality claims are made.")

    return "\n".join(lines)


# ── Main ────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="R14 Scaled Multi-Repo Evidence Benchmark Runner/Scorer"
    )
    parser.add_argument("--manifest", required=True, help="Path to dataset_manifest.json")
    parser.add_argument("--openlocus", default="target/debug/openlocus", help="Path to openlocus binary")
    parser.add_argument("--methods", default="regex,bm25,symbol,rrf", help="Comma-separated methods")
    parser.add_argument("--channels", default="regex,bm25,symbol", help="Channels for RRF retrieve")
    parser.add_argument("--repos-root", default=".", help="Root directory for repos")
    parser.add_argument("--tier", default="S", choices=["S", "M", "L", "X"], help="Which tier to benchmark")
    parser.add_argument("--index-mode", default="temp", choices=["temp", "persistent"], help="BM25 index mode")
    parser.add_argument("--out", required=True, help="Output path for JSON report")
    parser.add_argument("--allow-local", action="store_true", help="Allow local repos")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)
    out_dir = manifest_path.parent
    repos_root = Path(args.repos_root).resolve()
    tier = args.tier

    tier_name = {"S": "sanity", "M": "medium", "L": "large", "X": "stress"}[tier]

    # ── Validate tier is populated ──────────────────────────────────────
    tier_status = manifest.get("current_status", {}).get(tier, {})
    if tier in ("L", "X") and tier_status.get("repos", 0) == 0:
        print(f"ERROR: R14-{tier} tier is not populated. Only structure is defined.", file=sys.stderr)
        print(f"  Run with --tier S or --tier M for populated tiers.", file=sys.stderr)
        sys.exit(1)

    # ── Load repo lock ──────────────────────────────────────────────────
    repos = load_repo_lock(out_dir)
    if not repos:
        print("ERROR: No repos found in repos.lock.jsonl", file=sys.stderr)
        sys.exit(1)

    # ── Validate repo lock (strict: recompute manifest) ─────────────────
    lock_issues, lock_info = validate_repo_lock(repos, repos_root)
    safety_issues: list[str] = list(lock_issues)
    for info in lock_info:
        print(f"  ℹ️  {info}")

    # ── Phase 1: RUN — load public tasks only (NO labels) ───────────────
    tasks_path = out_dir / "tasks" / f"{tier_name}.jsonl"
    tasks = load_jsonl(tasks_path)
    if not tasks:
        print(f"ERROR: No tasks found at {tasks_path}", file=sys.stderr)
        sys.exit(1)

    # Verify no gold info in tasks
    for task in tasks:
        for field in ["gold_spans", "gold_paths", "gold_lines", "hard_negatives"]:
            if field in task:
                safety_issues.append(
                    f"LEAK: task {task['task_id']} contains {field}"
                )

    print(f"R14-{tier} Benchmark: {len(tasks)} tasks, {len(repos)} repos")
    print(f"  Phase 1: RUN (public tasks only, no labels)")

    # Collect allowed source paths for citation validation
    allowed_source_paths: set[str] = set()
    for entry in repos.values():
        paths_str = entry.get("source", {}).get("path", "")
        for p in paths_str.split(","):
            p = p.strip()
            if p:
                allowed_source_paths.add(p + "/")

    openlocus_path = str(Path(args.openlocus).resolve())

    methods = [m.strip() for m in args.methods.split(",")]
    all_predictions, citation_summaries, canary_summary, run_issues = run_predictions(
        tasks, openlocus_path, methods, repos_root, repos,
        args.channels, args.index_mode,
    )
    safety_issues.extend(run_issues)

    # Store predictions
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for method, predictions in all_predictions.items():
        pred_path = out_path.parent / f"r14-{tier_name}-{method}-predictions.jsonl"
        with pred_path.open("w", encoding="utf-8") as f:
            for pred in predictions:
                f.write(json.dumps(pred) + "\n")

    # ── Phase 2: SCORE — load private labels (no CLI calls) ─────────────
    print(f"  Phase 2: SCORE (labels only, no CLI)")
    labels_path = out_dir / "labels" / f"{tier_name}.jsonl"
    labels_list = load_jsonl(labels_path)
    gold = {l["task_id"]: l for l in labels_list}

    all_metrics: dict[str, dict[str, Any]] = {}
    for method, predictions in all_predictions.items():
        metrics = score_predictions(
            predictions, gold, citation_summaries.get(method, {}), method
        )
        # Propagate citation issues to safety
        cv_issues = metrics.pop("_citation_issues", [])
        safety_issues.extend(cv_issues)
        all_metrics[method] = metrics

    # ── Safety gates (fail-closed) ──────────────────────────────────────

    for method, metrics in all_metrics.items():
        # Citation validity must be 1.0 (fail-closed: every citation must be valid)
        cv = metrics.get("citation_validity", 0.0)
        if cv < 1.0:
            safety_issues.append(
                f"CRITICAL: {method} citation_validity={cv:.3f} < 1.0. "
                f"Every citation must be hash+range+path valid. Fail-closed."
            )

    # ── Generate report ─────────────────────────────────────────────────

    report = {
        "schema_version": "r14-v1",
        "tier": tier,
        "tier_name": tier_name,
        "tasks": len(tasks),
        "repos": len(repos),
        "gold_labels": len(gold),
        "methods": methods,
        "metrics": all_metrics,
        "safety_issues": safety_issues,
        "safety_passed": len(safety_issues) == 0,
        "index_mode": args.index_mode,
        "canary_retrieval": canary_summary,
        "phases": {
            "run": "public_tasks_only_no_labels",
            "score": "labels_only_no_cli",
            "isolation": "temp_root_per_repo",
            "citation_mode": "fail_closed_hash_range_path",
            "policy": "isolated_policy_toml_from_repo_lock",
        },
    }

    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    md_path = out_path.with_suffix(".md")
    md_content = generate_markdown_summary(all_metrics, safety_issues, tier)
    md_path.write_text(md_content, encoding="utf-8")

    # Print summary
    print(f"\n{'='*60}")
    print(f"R14-{tier} Benchmark Results")
    print(f"{'='*60}")
    for method, metrics in all_metrics.items():
        print(f"\n{method}:")
        for key in [
            "file_recall@1", "file_recall@5", "file_recall@10",
            "mrr", "span_f0.5@10",
            "hard_negative_hit_rate@10", "negative_nonempty_rate@10",
            "citation_validity", "success_rate",
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

    # Fail closed on ANY safety issue
    if safety_issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
