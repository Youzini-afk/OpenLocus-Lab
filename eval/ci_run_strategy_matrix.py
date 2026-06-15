#!/usr/bin/env python3
"""R48 CI Run Strategy Matrix: RUN phase only.

Inputs: public tasks JSONL + repo-lock.json + openlocus binary + out-dir + strategies.
Runs implemented strategies. Validates citations fail-closed.
Artifact private-field scan over RUN artifacts must be clean.
Unavailable strategies output reason-only status with no metrics/quality numbers.
Does NOT use labels.

Implemented strategies (11):
  Base (4): regex, bm25, symbol, rrf
  Composite (4): bm25_regex, bm25_symbol, query_noise_plus_rrf_agree_min,
                 rrf_guarded_by_symbol_regex
  Extended (3): dense_mock, ast_chunk_bm25, graph_basic

Unavailable (2): dense_real, QuIVer — reason-only, no metrics.

Usage:
    python3 eval/ci_run_strategy_matrix.py \\
        --tasks eval/ci_output/tasks/ci_tasks.jsonl \\
        --repo-lock eval/ci_output/repo-lock.json \\
        --openlocus target/debug/openlocus \\
        --out-dir eval/ci_output/run \\
        --strategies regex,bm25,symbol,rrf
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Schema ──────────────────────────────────────────────────────────────

SCHEMA_VERSION = "ci-run-v1"

SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs",
    ".rs", ".go", ".java", ".kt", ".kts",
    ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".hxx",
    ".cs", ".fs", ".fsi",
    ".rb", ".php", ".swift", ".scala", ".clj",
    ".sh", ".bash", ".zsh",
    ".yaml", ".yml", ".toml", ".json", ".cfg", ".ini",
    ".md", ".rst", ".txt",
    ".css", ".scss", ".less", ".html", ".svg",
}

SKIP_DIR_NAMES = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", "target", "coverage", ".next", ".nuxt",
    ".openlocus", "fixtures", "eval", "docs", "runs",
}

FORBIDDEN_PREFIXES = [
    "fixtures/", "eval/", "docs/", "runs/", ".openlocus/",
    "target/", "__pycache__/", ".git/",
]

PRIVATE_FIELD_DENYLIST = [
    "source_category", "risk_public", "intent_guess", "risk_tags",
    "oracle_type", "expected_behavior", "gold_spans",
    "hard_distractors", "must_not_primary", "why_this_is_hard",
    "which_strategy_it_targets",
]

POLICY_EXCLUDE_PATTERNS = [
    "fixtures/**", "eval/**", "docs/**", "runs/**", ".openlocus/**",
    "target/**", "__pycache__/**", "*.tmp", "*.log", ".git/**",
    "node_modules/**", "dist/**", "build/**", ".venv/**",
    ".next/**", ".nuxt/**", "coverage/**", "*.pyc",
]

QUERY_TIMEOUT_SECONDS = float(os.environ.get("OPENLOCUS_CI_QUERY_TIMEOUT_SECONDS", "30"))
BUILD_TIMEOUT_SECONDS = float(os.environ.get("OPENLOCUS_CI_BUILD_TIMEOUT_SECONDS", "300"))

# All implemented strategies
ALL_IMPLEMENTED_STRATEGIES = [
    "regex", "bm25", "symbol", "rrf",
    "bm25_regex", "bm25_symbol",
    "query_noise_plus_rrf_agree_min",
    "rrf_guarded_by_symbol_regex",
    "dense_mock", "ast_chunk_bm25", "graph_basic",
]

# Unavailable strategies — reason-only, no metrics
UNAVAILABLE_STRATEGIES = {
    "dense_real": {
        "status": "unavailable",
        "reason": "not_configured_or_policy_disabled",
    },
    "DenseReal": {
        "status": "unavailable",
        "reason": "not_configured_or_policy_disabled",
    },
    "dense_real_if_available": {
        "status": "unavailable",
        "reason": "not_configured_or_policy_disabled",
    },
    "QuIVer": {
        "status": "unavailable",
        "reason": "quiver_not_implemented",
    },
    "quiver_if_available": {
        "status": "unavailable",
        "reason": "quiver_not_implemented",
    },
    "tdb_quiver_if_available": {
        "status": "unavailable",
        "reason": "quiver_not_implemented",
    },
}

PUBLIC_TASK_FIELDS = frozenset({"test_id", "task_id", "repo_id", "query", "public_version", "source", "task_bucket", "task_risk_tags"})

# ── Noise detection (inlined from R17) ─────────────────────────────────

NEGATIVE_NOISE_MARKERS = [
    "FIXME_bogus", "TODO_nonexistent", "HACK_impossible",
    "nonexistent", "imaginary", "fake", "does_not_exist",
    "bogus", "_bogus_", "_nonexistent_", "_impossible_",
]

COMMON_WORDS = {
    "function", "error", "handler", "configuration", "the", "return",
    "initialization", "serialization", "validation", "logging", "testing",
    "routing", "parsing", "buffering", "cleanup", "settings", "setup",
    "import", "dependencies", "module", "exports", "server", "route",
    "definitions", "types", "client", "connection", "builder", "pattern",
    "handling", "search", "implementation", "data", "storage", "api",
    "endpoint", "request", "management", "processing", "startup",
    "response", "event", "model", "interface",
}

UUID_PATTERN = __import__("re").compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    __import__("re").IGNORECASE,
)


def is_negative_noise_query(query: str) -> bool:
    q = query.strip()
    for marker in NEGATIVE_NOISE_MARKERS:
        if marker.lower() in q.lower():
            return True
    if q.lower() in COMMON_WORDS:
        return True
    if UUID_PATTERN.match(q):
        return True
    return False


def is_vague_multi_word_query(query: str) -> bool:
    q = query.strip()
    if " " not in q:
        return False
    tokens = q.split()
    return all(token.lower() in COMMON_WORDS for token in tokens) and len(tokens) >= 2


def is_compound_snake_case_noise(query: str) -> bool:
    q = query.strip()
    if " " in q or "_" not in q:
        return False
    parts = [p for p in q.split("_") if p]
    noise_domain_keywords = {
        "quantum", "neural", "blockchain", "distributed", "machine",
        "cryptographic", "microservice", "training", "consensus", "replication",
    }
    if len(parts) >= 3:
        noise_count = sum(1 for p in parts if p.lower() in noise_domain_keywords)
        if noise_count >= 1:
            return True
    return False


# ── Data loading ────────────────────────────────────────────────────────


def load_jsonl(path: Path) -> list[dict]:
    items = []
    if not path.exists():
        return items
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            items.append(json.loads(line))
    return items


def write_jsonl(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, sort_keys=True) + "\n")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_source_manifest(
    source_path: Path,
    extensions: set[str],
    max_indexed_bytes: int | None = None,
) -> dict[str, Any]:
    """Recompute the repo-lock file manifest in RUN using R46 semantics."""
    file_entries: list[dict[str, Any]] = []
    total_bytes = 0
    file_count = 0
    found_extensions: set[str] = set()
    truncated_by_byte_cap = False
    for dirpath, dirnames, filenames in os.walk(source_path, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
        for fname in sorted(filenames):
            ext = os.path.splitext(fname)[1].lower()
            if ext not in extensions:
                continue
            fpath = Path(dirpath) / fname
            try:
                st = fpath.stat()
            except OSError:
                continue
            if max_indexed_bytes is not None and total_bytes + st.st_size > max_indexed_bytes:
                truncated_by_byte_cap = True
                continue
            try:
                h = hashlib.sha256()
                with fpath.open("rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
                rel_path = str(fpath.relative_to(source_path)).replace(os.sep, "/")
                try:
                    line_count = fpath.read_bytes().count(b"\n") + 1
                except OSError:
                    line_count = 0
            except OSError:
                continue
            file_entries.append({
                "path": rel_path,
                "sha256": h.hexdigest(),
                "bytes": st.st_size,
                "lines": line_count,
            })
            total_bytes += st.st_size
            file_count += 1
            found_extensions.add(ext)
    file_entries.sort(key=lambda item: item["path"])
    aggregate = "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in file_entries)
    return {
        "content_manifest_sha": hashlib.sha256(aggregate.encode("utf-8")).hexdigest(),
        "indexed_file_count": file_count,
        "indexed_bytes": total_bytes,
        "extensions": sorted(found_extensions),
        "file_manifest": file_entries,
        "truncated_by_byte_cap": truncated_by_byte_cap,
    }


# ── Repo lock loading ───────────────────────────────────────────────────


def load_repo_lock(path: Path) -> dict[str, dict]:
    """Load repo-lock.json or .jsonl."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        repos = {}
        for line in text.splitlines():
            if line.strip():
                entry = json.loads(line)
                repo_id = entry.get("repo_id", "")
                if repo_id:
                    repos[repo_id] = entry
        return repos
    data = json.loads(text)
    if "repos" in data and isinstance(data["repos"], dict):
        return data["repos"]
    if "repo_id" in data and "source" in data:
        return {data["repo_id"]: data}
    return data


def validate_public_tasks(tasks: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    for task in tasks:
        task_id = task.get("test_id") or task.get("task_id") or "?"
        for key in task:
            if key not in PUBLIC_TASK_FIELDS:
                issues.append(f"LEAK: public task {task_id} contains non-public field '{key}'")
        for field in PRIVATE_FIELD_DENYLIST:
            if field in task:
                issues.append(f"LEAK: public task {task_id} contains private field '{field}'")
    return issues


# ── Isolated benchmark root ─────────────────────────────────────────────


def create_isolated_root(repo_id: str, entry: dict) -> tuple[Path, list[str]]:
    issues: list[str] = []
    source = entry.get("source", {})
    source_type = source.get("type", "")
    if source_type in ("local_absolute_path", "github_public"):
        source_path = Path(source.get("path", ""))
        if not source_path.exists():
            issues.append(f"CRITICAL: Repo {repo_id}: source path {source_path} missing")
            tmp_dir = tempfile.mkdtemp(prefix=f"ci-isolated-{repo_id}-fail-")
            return Path(tmp_dir), issues
    else:
        issues.append(f"CRITICAL: Repo {repo_id}: unsupported source type {source_type}")
        tmp_dir = tempfile.mkdtemp(prefix=f"ci-isolated-{repo_id}-fail-")
        return Path(tmp_dir), issues

    tmp_dir = tempfile.mkdtemp(prefix=f"ci-isolated-{repo_id}-")
    isolated = Path(tmp_dir)

    (isolated / ".git").mkdir(exist_ok=True)
    policy_dir = isolated / ".openlocus"
    policy_dir.mkdir(exist_ok=True)

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

    extensions = set(entry.get("metadata", {}).get("extensions", list(SOURCE_EXTENSIONS)))
    max_indexed_bytes = entry.get("metadata", {}).get("max_indexed_bytes")
    recomputed = compute_source_manifest(source_path, extensions, max_indexed_bytes)
    expected_sha = entry.get("content_manifest_sha")
    if expected_sha and recomputed["content_manifest_sha"] != expected_sha:
        issues.append(
            f"CRITICAL: Repo {repo_id}: content_manifest_sha mismatch "
            f"(lock={expected_sha}, actual={recomputed['content_manifest_sha']})"
        )
    expected_files = int(entry.get("indexed_file_count") or entry.get("metadata", {}).get("files", 0))
    if expected_files and recomputed["indexed_file_count"] != expected_files:
        issues.append(
            f"CRITICAL: Repo {repo_id}: indexed_file_count mismatch "
            f"(lock={expected_files}, actual={recomputed['indexed_file_count']})"
        )
    expected_bytes = int(entry.get("indexed_bytes") or entry.get("metadata", {}).get("bytes", 0))
    if expected_bytes and recomputed["indexed_bytes"] != expected_bytes:
        issues.append(
            f"CRITICAL: Repo {repo_id}: indexed_bytes mismatch "
            f"(lock={expected_bytes}, actual={recomputed['indexed_bytes']})"
        )

    dst = isolated / repo_id
    copied = 0
    for dirpath, dirnames, filenames in os.walk(source_path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
        for fname in sorted(filenames):
            ext = os.path.splitext(fname)[1]
            if ext not in extensions:
                continue
            src_file = Path(dirpath) / fname
            try:
                rel = src_file.relative_to(source_path)
            except ValueError:
                issues.append(f"CRITICAL: Repo {repo_id}: source file escaped root: {src_file}")
                continue
            dst_file = dst / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            copied += 1

    if expected_files and copied != expected_files:
        issues.append(
            f"CRITICAL: Repo {repo_id}: isolated source copy file count mismatch "
            f"(expected {expected_files}, copied {copied})"
        )

    return isolated, issues


def clean_runtime_artifacts(isolated: Path, preserve_dense: bool = False) -> None:
    openlocus_dir = isolated / ".openlocus"
    if not openlocus_dir.exists():
        return
    for child in openlocus_dir.iterdir():
        if child.name == "policy.toml":
            continue
        if preserve_dense and child.name in {"embeddings", "audit"}:
            continue
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            try:
                child.unlink()
            except OSError:
                pass


def clean_preserve_policy(isolated: Path) -> None:
    """Drop all runtime artifacts except policy.toml.

    This is intentionally stricter than ``clean_runtime_artifacts`` with
    ``preserve_dense`` and is used before building strategy-specific indexes so
    one strategy cannot accidentally reuse another strategy's runtime state.
    """
    clean_runtime_artifacts(isolated, preserve_dense=False)


# ── Base query execution ────────────────────────────────────────────────


def run_query(openlocus: str, method: str, query: str, cwd: str) -> dict:
    if method == "regex":
        cmd = [openlocus, "search", "regex", query, "--json"]
    elif method == "bm25":
        cmd = [openlocus, "search", "bm25", query, "--json"]
    elif method == "symbol":
        cmd = [openlocus, "search", "symbol", query, "--json"]
    elif method == "rrf":
        cmd = [openlocus, "retrieve", query, "--json"]
    else:
        return {"evidence": [], "latency_ms": 0, "returncode": -1,
                "stderr": f"unknown method: {method}"}

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd, check=False, text=True, capture_output=True, cwd=cwd,
            timeout=QUERY_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "evidence": [],
            "latency_ms": latency_ms,
            "returncode": 124,
            "stderr": f"timeout after {QUERY_TIMEOUT_SECONDS}s: {exc}",
        }
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


# ── RRF fusion ──────────────────────────────────────────────────────────


def rrf_fuse_predictions(pred_a: dict, pred_b: dict, k: int = 60) -> list[dict]:
    score_map: dict[str, float] = {}
    evidence_map: dict[str, dict] = {}

    for rank, e in enumerate(pred_a.get("evidence", [])):
        key = f"{e.get('path', '')}:{e.get('start_line', 0)}:{e.get('end_line', 0)}"
        score_map[key] = score_map.get(key, 0.0) + 1.0 / (k + rank + 1)
        if key not in evidence_map:
            evidence_map[key] = dict(e)

    for rank, e in enumerate(pred_b.get("evidence", [])):
        key = f"{e.get('path', '')}:{e.get('start_line', 0)}:{e.get('end_line', 0)}"
        score_map[key] = score_map.get(key, 0.0) + 1.0 / (k + rank + 1)
        if key not in evidence_map:
            evidence_map[key] = dict(e)

    sorted_keys = sorted(score_map.keys(), key=lambda x: -score_map[x])
    result = []
    for key in sorted_keys:
        e = dict(evidence_map[key])
        e["score"] = score_map[key]
        e["channels"] = list(e.get("channels", []))
        result.append(e)
    return result


# ── Composite strategy builder ──────────────────────────────────────────


def build_composite_prediction(
    strategy: str, task: dict, base_predictions: dict[str, dict],
) -> dict:
    task_id = task["test_id"]
    query = task.get("query", "")
    repo_id = task.get("repo_id", "")
    # ``base_predictions`` here is already the per-task map
    # strategy -> prediction.  The caller stores the all-task map separately.
    preds = base_predictions

    evidence: list[dict] = []
    selected_method = ""
    route_decision = ""

    if strategy == "bm25_regex":
        bm25_pred = preds.get("bm25", {})
        regex_pred = preds.get("regex", {})
        evidence = rrf_fuse_predictions(bm25_pred, regex_pred)
        selected_method = "rrf"
        route_decision = "composite_bm25_regex_rrf"

    elif strategy == "bm25_symbol":
        bm25_pred = preds.get("bm25", {})
        symbol_pred = preds.get("symbol", {})
        evidence = rrf_fuse_predictions(bm25_pred, symbol_pred)
        selected_method = "rrf"
        route_decision = "composite_bm25_symbol_rrf"

    elif strategy == "query_noise_plus_rrf_agree_min":
        noise = (
            is_negative_noise_query(query)
            or is_vague_multi_word_query(query)
            or is_compound_snake_case_noise(query)
        )
        if noise:
            evidence = []
            selected_method = "empty"
            route_decision = "query_noise_guard"
        else:
            rrf_pred = preds.get("rrf", {})
            symbol_pred = preds.get("symbol", {})
            regex_pred = preds.get("regex", {})
            rrf_evidence = rrf_pred.get("evidence", []) if rrf_pred else []
            symbol_has = bool(symbol_pred and symbol_pred.get("evidence"))
            regex_has = bool(regex_pred and regex_pred.get("evidence"))
            threshold = 0.0
            if rrf_evidence and (symbol_has or regex_has):
                evidence = rrf_evidence
                selected_method = "rrf"
                route_decision = "query_noise_plus_rrf_agree_min_0.0"
            else:
                evidence = []
                selected_method = "empty"
                route_decision = "query_noise_plus_rrf_agree_min_0.0_empty"

    elif strategy == "rrf_guarded_by_symbol_regex":
        rrf_pred = preds.get("rrf", {})
        symbol_pred = preds.get("symbol", {})
        regex_pred = preds.get("regex", {})
        symbol_has = bool(symbol_pred and symbol_pred.get("evidence"))
        regex_has = bool(regex_pred and regex_pred.get("evidence"))
        if symbol_has or regex_has:
            evidence = rrf_pred.get("evidence", []) if rrf_pred else []
            selected_method = "rrf"
            route_decision = "rrf_guarded_symbol_or_regex_present"
        else:
            evidence = []
            selected_method = "empty"
            route_decision = "rrf_guarded_no_symbol_no_regex"

    elif strategy == "dense_mock_plus_rrf":
        dense_pred = preds.get("dense_mock", {})
        rrf_pred = preds.get("rrf", {})
        evidence = rrf_fuse_predictions(dense_pred, rrf_pred)
        selected_method = "rrf"
        route_decision = "composite_dense_mock_plus_rrf"

    return {
        "task_id": task_id,
        "repo_id": repo_id,
        "query": query,
        "strategy": strategy,
        "selected_method": selected_method,
        "route_decision": route_decision,
        "evidence": evidence,
        "latency_ms": 0,
        "returncode": 0,
    }


# ── Dense mock ──────────────────────────────────────────────────────────


def run_dense_build(openlocus: str, cwd: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [openlocus, "dense", "build", "--provider", "mock", "--experimental", "--json"],
            check=False, text=True, capture_output=True, cwd=cwd,
            timeout=BUILD_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "success": False,
            "record_count": 0,
            "latency_ms": latency_ms,
            "returncode": 124,
            "stderr": f"timeout after {BUILD_TIMEOUT_SECONDS}s: {exc}",
        }
    latency_ms = int((time.perf_counter() - t0) * 1000)
    result = {}
    try:
        result = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        pass
    return {
        "success": result.get("success", False),
        "record_count": result.get("record_count", 0),
        "latency_ms": latency_ms,
        "returncode": proc.returncode,
        "stderr": proc.stderr[:500] if proc.stderr else "",
    }


def run_dense_search(openlocus: str, query: str, cwd: str, limit: int = 10) -> list[dict]:
    try:
        proc = subprocess.run(
            [openlocus, "dense", "search", "--provider", "mock",
             "--limit", str(limit), "--json", query],
            check=False, text=True, capture_output=True, cwd=cwd,
            timeout=QUERY_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return []
    result: dict[str, Any] = {}
    try:
        result = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        pass
    return result.get("evidence", []) if isinstance(result, dict) else []


# ── Graph basic ─────────────────────────────────────────────────────────


def derive_top_path(openlocus: str, query: str, cwd: str) -> tuple[str | None, str]:
    for method in ["symbol", "regex"]:
        cmd = [openlocus, "search", method, query, "--json"]
        try:
            proc = subprocess.run(
                cmd, check=False, text=True, capture_output=True, cwd=cwd,
                timeout=QUERY_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            continue
        if proc.returncode != 0:
            continue
        try:
            raw = json.loads(proc.stdout.strip()) if proc.stdout.strip() else []
        except json.JSONDecodeError:
            continue
        evidence = raw.get("evidence", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
        if evidence:
            top_path = evidence[0].get("path", "")
            if top_path:
                return top_path, method
    return None, "none"


def run_graph_impact(openlocus: str, top_path: str, cwd: str) -> list[dict]:
    try:
        proc = subprocess.run(
            [openlocus, "impact", top_path, "--depth", "1", "--json"],
            check=False, text=True, capture_output=True, cwd=cwd,
            timeout=QUERY_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return []
    if proc.returncode != 0:
        return []
    try:
        result = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        return []
    return result.get("evidence", []) if isinstance(result, dict) else []


# ── AST chunk BM25 ──────────────────────────────────────────────────────


def run_ast_build(openlocus: str, cwd: str) -> dict[str, Any]:
    """Build a persistent AST-chunked index once for one isolated repo."""
    clean_preserve_policy(Path(cwd))
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [openlocus, "index", "build", "--chunk-strategy", "ast", "--json"],
            check=False, text=True, capture_output=True, cwd=cwd,
            timeout=BUILD_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "success": False,
            "latency_ms": latency_ms,
            "returncode": 124,
            "stderr": f"timeout after {BUILD_TIMEOUT_SECONDS}s: {exc}",
            "summary": {},
        }
    latency_ms = int((time.perf_counter() - t0) * 1000)
    result: dict[str, Any] = {}
    try:
        result = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        pass
    return {
        "success": proc.returncode == 0,
        "latency_ms": latency_ms,
        "returncode": proc.returncode,
        "stderr": proc.stderr[:500] if proc.stderr else "",
        "summary": result,
    }


def run_ast_chunk_bm25(openlocus: str, query: str, cwd: str) -> dict:
    """AST-chunked BM25: query a pre-built persistent AST index.

    This uses existing CLI surfaces only; no Rust/EvidenceCore changes.
    """
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [openlocus, "search", "bm25", query, "--index", "persistent", "--json"],
            check=False, text=True, capture_output=True, cwd=cwd,
            timeout=QUERY_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "evidence": [],
            "latency_ms": latency_ms,
            "returncode": 124,
            "stderr": f"timeout after {QUERY_TIMEOUT_SECONDS}s: {exc}",
        }
    latency_ms = int((time.perf_counter() - t0) * 1000)
    evidence: list[dict] = []
    try:
        raw = json.loads(proc.stdout) if proc.stdout.strip() else []
        if isinstance(raw, list):
            evidence = raw
        elif isinstance(raw, dict) and "evidence" in raw:
            evidence = raw["evidence"]
    except json.JSONDecodeError:
        pass
    return {
        "evidence": evidence,
        "latency_ms": latency_ms,
        "returncode": proc.returncode,
        "stderr": proc.stderr[:500] if proc.stderr else "",
    }


# ── Citation validation ────────────────────────────────────────────────


def validate_predictions_with_rust(
    openlocus: str,
    strategy: str,
    predictions: list[dict],
    isolated_roots: dict[str, Path],
) -> tuple[dict[str, Any], list[str]]:
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
            issues.append(f"CRITICAL: {strategy}: missing isolated root for repo {repo_id}")
            total += len(evidence)
            invalid += len(evidence)
            continue

        tmp_name: str | None = None
        try:
            tmp_parent = Path(os.environ.get("RUNNER_TEMP") or tempfile.gettempdir())
            tmp_parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w", prefix=f"ci-{strategy}-{repo_id}-citations-",
                suffix=".json", delete=False, dir=tmp_parent,
                encoding="utf-8",
            ) as tmp:
                tmp.write(json.dumps(evidence) + "\n")
                tmp_name = tmp.name
            try:
                proc = subprocess.run(
                    [openlocus, "citations", "validate", tmp_name, "--json"],
                    check=False, text=True, capture_output=True,
                    cwd=str(isolated), timeout=BUILD_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired:
                issues.append(f"CRITICAL: {strategy}: citation validator timed out for repo {repo_id}")
                total += len(evidence)
                invalid += len(evidence)
                continue
        finally:
            if tmp_name:
                try:
                    Path(tmp_name).unlink()
                except OSError:
                    pass
            clean_runtime_artifacts(isolated)

        invocations += 1
        if proc.returncode != 0:
            issues.append(f"CRITICAL: {strategy}: citation validator failed for repo {repo_id}")
            total += len(evidence)
            invalid += len(evidence)
            continue

        try:
            result = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except json.JSONDecodeError:
            issues.append(f"CRITICAL: {strategy}: citation validator non-JSON for repo {repo_id}")
            total += len(evidence)
            invalid += len(evidence)
            continue

        repo_total = int(result.get("total", 0))
        repo_valid = int(result.get("valid_count", 0))
        repo_invalid = int(result.get("invalid_count", 0))
        total += repo_total
        valid += repo_valid
        invalid += repo_invalid

        if repo_invalid != 0:
            issues.append(f"CRITICAL: {strategy}: {repo_invalid} invalid citations for repo {repo_id}")

    rate = valid / total if total else 1.0
    if invalid != 0 or rate < 1.0:
        issues.append(
            f"CRITICAL: {strategy}: citation validity must be 1.0 "
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


# ── Forbidden path check ───────────────────────────────────────────────


def check_predictions_for_forbidden_paths(
    predictions: list[dict], strategy: str,
) -> list[str]:
    issues: list[str] = []
    for pred in predictions:
        for e in pred.get("evidence", []):
            path = e.get("path", "")
            for fp in FORBIDDEN_PREFIXES:
                forbidden_component = fp.strip("/")
                path_parts = path.replace("\\", "/").split("/")
                if path.startswith(fp) or forbidden_component in path_parts:
                    issues.append(
                        f"CRITICAL: {strategy} prediction for task {pred.get('task_id', '?')} "
                        f"has forbidden path prefix/component '{fp}': {path}"
                    )
    return issues


# ── Private field scan ──────────────────────────────────────────────────


def scan_artifacts_for_private_fields(out_dir: Path) -> tuple[dict[str, Any], list[str]]:
    """Scan all run artifacts for private fields."""
    issues: list[str] = []
    scanned_files = 0
    total_lines = 0
    violations = 0

    for jsonl_path in sorted(out_dir.rglob("*.jsonl")):
        scanned_files += 1
        for line_no, line in enumerate(jsonl_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            total_lines += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            for field in PRIVATE_FIELD_DENYLIST:
                if field in obj:
                    violations += 1
                    issues.append(
                        f"CRITICAL: Private field '{field}' found in {jsonl_path.name}:{line_no}"
                    )
            # Also check nested evidence
            for e in obj.get("evidence", []):
                for field in PRIVATE_FIELD_DENYLIST:
                    if field in e:
                        violations += 1
                        issues.append(
                            f"CRITICAL: Private field '{field}' in evidence in {jsonl_path.name}:{line_no}"
                        )

    return {
        "scanned_files": scanned_files,
        "total_lines": total_lines,
        "violations": violations,
        "clean": violations == 0,
    }, issues


# ── Main RUN phase ─────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="R48 CI Run Strategy Matrix")
    parser.add_argument("--tasks", required=True, help="Public tasks JSONL")
    parser.add_argument("--repo-lock", required=True, help="repo-lock.json path")
    parser.add_argument("--openlocus", required=True, help="Path to openlocus binary")
    parser.add_argument("--out-dir", required=True, help="Output directory for run artifacts")
    parser.add_argument(
        "--strategies",
        default=",".join(ALL_IMPLEMENTED_STRATEGIES),
        help="Comma-separated strategies to run",
    )
    parser.add_argument("--limit", type=int, default=0, help="Limit number of tasks (0=all)")
    parser.add_argument("--shard-id", type=int, default=0, help="Task shard id for large CI matrices")
    parser.add_argument("--shard-count", type=int, default=1, help="Total task shard count")
    args = parser.parse_args()

    openlocus = str(Path(args.openlocus).resolve())
    if not Path(openlocus).exists():
        print(f"ERROR: openlocus binary not found: {openlocus}", file=sys.stderr)
        sys.exit(1)

    tasks = load_jsonl(Path(args.tasks))
    if not tasks:
        print("ERROR: No tasks loaded", file=sys.stderr)
        sys.exit(1)

    public_task_issues = validate_public_tasks(tasks)
    if public_task_issues:
        for issue in public_task_issues[:50]:
            print(issue, file=sys.stderr)
        sys.exit(1)

    if args.limit > 0:
        tasks = tasks[:args.limit]
    if args.shard_count < 1:
        print("ERROR: --shard-count must be >= 1", file=sys.stderr)
        sys.exit(1)
    if args.shard_id < 0 or args.shard_id >= args.shard_count:
        print("ERROR: --shard-id must be in [0, shard_count)", file=sys.stderr)
        sys.exit(1)
    if args.shard_count > 1:
        tasks = [task for idx, task in enumerate(tasks) if idx % args.shard_count == args.shard_id]
        if not tasks:
            print("ERROR: shard selected no tasks", file=sys.stderr)
            sys.exit(1)

    repos = load_repo_lock(Path(args.repo_lock))
    strategies = [s.strip() for s in args.strategies.split(",") if s.strip()]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_issues: list[str] = []

    # Validate strategies
    for s in strategies:
        if s not in ALL_IMPLEMENTED_STRATEGIES and s not in UNAVAILABLE_STRATEGIES:
            all_issues.append(f"WARNING: Unknown strategy: {s}")

    if os.environ.get("OPENLOCUS_ALLOW_REMOTE") != "1":
        for remote_strategy in [
            "dense_real", "DenseReal", "dense_real_if_available",
            "QuIVer", "quiver_if_available", "tdb_quiver_if_available",
        ]:
            if remote_strategy in strategies:
                UNAVAILABLE_STRATEGIES[remote_strategy]["reason"] = "requires_workflow_dispatch_and_OPENLOCUS_ALLOW_REMOTE_1"

    # Create isolated roots
    isolated_roots: dict[str, Path] = {}
    for repo_id, entry in repos.items():
        isolated, issues = create_isolated_root(repo_id, entry)
        isolated_roots[repo_id] = isolated
        all_issues.extend(issues)

    # Run base strategies
    base_predictions: dict[str, dict[str, dict]] = {}  # strategy -> task_id -> prediction
    run_artifacts: dict[str, list[dict]] = {}  # strategy -> list of predictions

    dense_build_results: dict[str, dict[str, Any]] = {}
    if "dense_mock" in strategies:
        for repo_id, isolated in isolated_roots.items():
            dense_build_results[repo_id] = run_dense_build(openlocus, str(isolated))
            if not dense_build_results[repo_id].get("success", False):
                all_issues.append(
                    f"WARNING: dense_mock build failed for repo {repo_id}: "
                    f"{dense_build_results[repo_id].get('stderr', '')[:200]}"
                )
            clean_runtime_artifacts(isolated, preserve_dense=True)

    ast_build_results: dict[str, dict[str, Any]] = {}
    if "ast_chunk_bm25" in strategies:
        for repo_id, isolated in isolated_roots.items():
            ast_build_results[repo_id] = run_ast_build(openlocus, str(isolated))
            if not ast_build_results[repo_id].get("success", False):
                all_issues.append(
                    f"WARNING: ast_chunk_bm25 build failed for repo {repo_id}: "
                    f"{ast_build_results[repo_id].get('stderr', '')[:200]}"
                )

    for strategy in strategies:
        if strategy in UNAVAILABLE_STRATEGIES:
            continue
        if strategy in ("bm25_regex", "bm25_symbol", "query_noise_plus_rrf_agree_min",
                        "rrf_guarded_by_symbol_regex", "dense_mock_plus_rrf"):
            continue  # Composite, built later

        predictions: list[dict] = []
        task_preds: dict[str, dict] = {}

        for task in tasks:
            task_id = task["test_id"]
            repo_id = task.get("repo_id", "")
            query = task.get("query", "")
            isolated = isolated_roots.get(repo_id)
            if isolated is None:
                predictions.append({
                    "task_id": task_id, "repo_id": repo_id, "query": query,
                    "strategy": strategy, "evidence": [],
                    "latency_ms": 0, "returncode": -1,
                    "stderr": "no isolated root",
                })
                continue

            if strategy in ("regex", "bm25", "symbol", "rrf"):
                result = run_query(openlocus, strategy, query, str(isolated))
                pred = {
                    "task_id": task_id, "repo_id": repo_id, "query": query,
                    "strategy": strategy, "evidence": result["evidence"],
                    "latency_ms": result["latency_ms"],
                    "returncode": result["returncode"],
                }
                clean_runtime_artifacts(isolated)

            elif strategy == "dense_mock":
                build_result = dense_build_results.get(repo_id, {"success": False, "returncode": -1})
                if not build_result.get("success", False):
                    pred = {
                        "task_id": task_id, "repo_id": repo_id, "query": query,
                        "strategy": strategy, "evidence": [],
                        "latency_ms": build_result.get("latency_ms", 0),
                        "returncode": build_result.get("returncode", -1),
                    }
                    predictions.append(pred)
                    task_preds[task_id] = pred
                    clean_runtime_artifacts(isolated, preserve_dense=True)
                    continue
                dense_evidence = run_dense_search(openlocus, query, str(isolated))
                pred = {
                    "task_id": task_id, "repo_id": repo_id, "query": query,
                    "strategy": strategy, "evidence": dense_evidence,
                    "latency_ms": 0, "returncode": 0,
                }
                clean_runtime_artifacts(isolated, preserve_dense=True)

            elif strategy == "ast_chunk_bm25":
                build_result = ast_build_results.get(repo_id, {"success": False, "returncode": -1})
                if not build_result.get("success", False):
                    pred = {
                        "task_id": task_id, "repo_id": repo_id, "query": query,
                        "strategy": strategy, "evidence": [],
                        "latency_ms": build_result.get("latency_ms", 0),
                        "returncode": build_result.get("returncode", -1),
                    }
                    predictions.append(pred)
                    task_preds[task_id] = pred
                    continue
                result = run_ast_chunk_bm25(openlocus, query, str(isolated))
                pred = {
                    "task_id": task_id, "repo_id": repo_id, "query": query,
                    "strategy": strategy, "evidence": result["evidence"],
                    "latency_ms": result["latency_ms"],
                    "returncode": result["returncode"],
                }

            elif strategy == "graph_basic":
                top_path, method = derive_top_path(openlocus, query, str(isolated))
                if top_path:
                    graph_evidence = run_graph_impact(openlocus, top_path, str(isolated))
                else:
                    graph_evidence = []
                pred = {
                    "task_id": task_id, "repo_id": repo_id, "query": query,
                    "strategy": strategy, "evidence": graph_evidence,
                    "latency_ms": 0, "returncode": 0,
                    "selected_method": method,
                }
                clean_runtime_artifacts(isolated)

            else:
                pred = {
                    "task_id": task_id, "repo_id": repo_id, "query": query,
                    "strategy": strategy, "evidence": [],
                    "latency_ms": 0, "returncode": -1,
                    "stderr": f"unhandled strategy: {strategy}",
                }

            predictions.append(pred)
            task_preds[task_id] = pred

        base_predictions[strategy] = task_preds
        run_artifacts[strategy] = predictions
        write_jsonl(out_dir / f"{strategy}-predictions.jsonl", predictions)
        print(f"  Strategy {strategy}: {len(predictions)} predictions")

    # Build composite strategies
    composite_strategies = [s for s in strategies if s in (
        "bm25_regex", "bm25_symbol", "query_noise_plus_rrf_agree_min",
        "rrf_guarded_by_symbol_regex", "dense_mock_plus_rrf",
    )]

    for strategy in composite_strategies:
        predictions: list[dict] = []
        task_preds: dict[str, dict] = {}

        for task in tasks:
            task_id = task["test_id"]
            # Gather base predictions for this task
            task_base_preds: dict[str, dict] = {}
            for base_strat, base_tp in base_predictions.items():
                if task_id in base_tp:
                    task_base_preds[base_strat] = base_tp[task_id]

            pred = build_composite_prediction(strategy, task, task_base_preds)
            predictions.append(pred)
            task_preds[task_id] = pred

        base_predictions[strategy] = task_preds
        run_artifacts[strategy] = predictions
        write_jsonl(out_dir / f"{strategy}-predictions.jsonl", predictions)
        print(f"  Strategy {strategy}: {len(predictions)} predictions (composite)")

    # Validate citations for all implemented strategies
    citation_summaries: dict[str, dict[str, Any]] = {}
    for strategy in strategies:
        if strategy in UNAVAILABLE_STRATEGIES:
            continue
        preds = run_artifacts.get(strategy, [])
        if not preds:
            continue
        forbidden_issues = check_predictions_for_forbidden_paths(preds, strategy)
        all_issues.extend(forbidden_issues)

        cit_summary, cit_issues = validate_predictions_with_rust(
            openlocus, strategy, preds, isolated_roots,
        )
        citation_summaries[strategy] = cit_summary
        all_issues.extend(cit_issues)

    requested_unavailable = {
        strat: UNAVAILABLE_STRATEGIES[strat]
        for strat in strategies
        if strat in UNAVAILABLE_STRATEGIES
    }

    # Write unavailable strategy status files only for requested strategies.
    for strat, info in requested_unavailable.items():
        status_path = out_dir / f"{strat}-status.json"
        status_path.write_text(
            json.dumps({
                "strategy": strat,
                "status": info["status"],
                "reason": info["reason"],
            }, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

    # Private field scan on all run artifacts
    scan_result, scan_issues = scan_artifacts_for_private_fields(out_dir)
    all_issues.extend(scan_issues)

    # Write run manifest
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "strategies_run": [s for s in strategies if s not in UNAVAILABLE_STRATEGIES],
        "unavailable_strategies": {k: v["reason"] for k, v in requested_unavailable.items()},
        "total_tasks": len(tasks),
        "shard_id": args.shard_id,
        "shard_count": args.shard_count,
        "citation_summaries": citation_summaries,
        "private_field_scan": scan_result,
        "issues_count": len(all_issues),
        "run_score_separation": True,
        "labels_used": False,
    }
    (out_dir / "run-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # Print issues
    if all_issues:
        print(f"\n{len(all_issues)} issues found:", file=sys.stderr)
        for issue in all_issues:
            print(f"  {issue}", file=sys.stderr)

    critical_count = sum(1 for i in all_issues if i.startswith("CRITICAL:"))
    if critical_count > 0:
        print(f"\nFATAL: {critical_count} critical issues. Run phase failed.", file=sys.stderr)
        sys.exit(1)

    print(f"\nRun phase complete. Manifest: {out_dir / 'run-manifest.json'}")


if __name__ == "__main__":
    main()
