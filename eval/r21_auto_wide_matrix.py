#!/usr/bin/env python3
"""R21 Auto-Wide Strategy Matrix Runner/Scorer.

Bounded implementation: evaluates failure surfaces across strategies on R20
auto-wide fixtures. Does NOT change Rust core or EvidenceCore.

Architecture: strictly separated RUN and SCORE phases.
  Phase 1 (RUN): loads only public tasks + repo lock. Creates isolated benchmark
    roots by allowlist-copying source files. Runs base methods via openlocus CLI.
    Builds composite/guard strategies from base predictions. Never reads labels.
  Phase 2 (SCORE): loads predictions + labels. Computes metrics.
    Never invokes openlocus CLI.

Safety:
  - Runner never loads private labels/gold
  - Retrieval runs inside isolated temp roots (no fixtures/eval/docs/runs)
  - Repo lock content manifest re-verified (normalized hash)
  - Citation validation is fail-closed: every citation must be hash+range+path valid
  - Validator runs BEFORE isolated root cleanup
  - Predictions with forbidden prefixes are critical failures
  - R20 labels weak/mined; report has promotion_ready=false, not_promotion_evidence=true
  - Unknown repo_id is CRITICAL; runner refuses to fall back to the full workspace
  - Composite/guard strategies built from base predictions only; no CLI, no labels

Implemented strategies (10):
  1. regex         - openlocus search regex
  2. bm25          - openlocus search bm25
  3. symbol        - openlocus search symbol
  4. rrf           - openlocus retrieve (RRF fusion)
  5. bm25_regex    - RRF fuse bm25+regex predictions
  6. bm25_symbol   - RRF fuse bm25+symbol predictions
  7. rrf_guarded_by_symbol
  8. rrf_guarded_by_regex
  9. rrf_guarded_by_symbol_regex
  10. query_noise_plus_rrf_agree_min (threshold=0.0, R18 helper)

 Unavailable strategies (10) - not run, status=unavailable:
  ast_chunk_bm25, ast_chunk_rrf, graph_basic, graph_rrf,
  dense_mock, dense_real_if_available, tdb_quiver_if_available,
  tdb_quiver_plus_rrf, tdb_quiver_guarded_by_symbol_regex,
  fast_context_if_available

Usage:
    python3 eval/r21_auto_wide_matrix.py \\
        --workspace . \\
        --fixtures fixtures/r20_auto_wide \\
        --openlocus target/debug/openlocus \\
        --out runs/r21-auto-wide-report.json \\
        --strategies regex,bm25,symbol,rrf,bm25_regex,bm25_symbol,rrf_guarded_by_symbol,rrf_guarded_by_regex,rrf_guarded_by_symbol_regex,query_noise_plus_rrf_agree_min

    # --skip-run is disabled: canary/citation validation cannot be bypassed.
    # Always run fresh to ensure safety gate integrity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Schema version ─────────────────────────────────────────────────────

SCHEMA_VERSION = "r21-v1"

# ── Base and composite strategy definitions ────────────────────────────

BASE_STRATEGIES = ["regex", "bm25", "symbol", "rrf"]
COMPOSITE_STRATEGIES = [
    "bm25_regex",
    "bm25_symbol",
    "rrf_guarded_by_symbol",
    "rrf_guarded_by_regex",
    "rrf_guarded_by_symbol_regex",
    "query_noise_plus_rrf_agree_min",
]
ALL_IMPLEMENTED_STRATEGIES = BASE_STRATEGIES + COMPOSITE_STRATEGIES

UNAVAILABLE_STRATEGIES = {
    "ast_chunk_bm25": "AST chunking is experimental opt-in; no R21 runner support",
    "ast_chunk_rrf": "Depends on ast_chunk_bm25; no R21 runner support",
    "graph_basic": "Graph depth=1 only; not evaluated in auto-wide matrix",
    "graph_rrf": "Depends on graph_basic; not evaluated in auto-wide matrix",
    "dense_mock": "Mock provider produces deterministic blake3 vectors; no retrieval quality",
    "dense_real_if_available": "No real embedding provider configured; remote denied by default",
    "tdb_quiver_if_available": "TDB behind optional feature gate; not in default build",
    "tdb_quiver_plus_rrf": "Depends on tdb_quiver_if_available",
    "tdb_quiver_guarded_by_symbol_regex": "Depends on tdb_quiver_if_available",
    "fast_context_if_available": "Fast-context is 4-turn orchestration scaffold; not a standalone strategy for matrix",
}

# ── Source extensions ──────────────────────────────────────────────────

SOURCE_EXTENSIONS = {".rs", ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".mjs"}

SKIP_DIR_NAMES = {
    "node_modules", "target", ".git", "dist", "build", ".venv",
    "__pycache__", ".next", ".nuxt", "runs", "fixtures", "eval",
    "docs", ".openlocus", "coverage", ".cache", ".mypy_cache",
    ".pytest_cache", ".tox", "venv", "env", ".env", ".idea",
    ".vscode", "out", "bin", "obj",
}

# ── Forbidden prefixes ────────────────────────────────────────────────

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

# ── Canary tokens ─────────────────────────────────────────────────────

CANARY_TOKENS = [
    "R21_CANARY_fixture_label_secret_1a2b",
    "R21_CANARY_eval_benchmark_secret_3c4d",
    "R21_CANARY_docs_summary_secret_5e6f",
    "R21_CANARY_runs_prediction_secret_7g8h",
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
    "coverage/**",
    "*.pyc",
]

# ── R17 query noise helpers (inlined for self-containment) ────────────

NEGATIVE_NOISE_MARKERS = [
    "FIXME_bogus",
    "TODO_nonexistent",
    "HACK_impossible",
    "nonexistent",
    "imaginary",
    "fake",
    "does_not_exist",
    "bogus",
    "_bogus_",
    "_nonexistent_",
    "_impossible_",
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

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

CAMEL_CASE_PATTERN = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
SNAKE_CASE_FUNC_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
CONTAINS_DOUBLE_COLON = re.compile(r"::")
SYMBOL_ISH_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_:.]*$")


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
        "inference", "rotation", "orchestration", "streaming", "pipeline",
        "protocol", "entanglement", "solver",
    }
    if len(parts) >= 3:
        noise_count = sum(1 for p in parts if p.lower() in noise_domain_keywords)
        if noise_count >= 1:
            return True
    return False


# ── Data loading ──────────────────────────────────────────────────────


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


def artifact_provenance(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return {
        "path": str(path),
        "sha256": file_sha256(path),
        "bytes": path.stat().st_size,
        "jsonl_lines": sum(1 for line in text.splitlines() if line.strip()),
    }


# ── Multi-language normalized content manifest ────────────────────────


def compute_normalized_manifest_sha(
    repo_path: Path, extensions: set[str] | None = None
) -> tuple[str, int, int]:
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


# ── Repo lock validation ──────────────────────────────────────────────


def validate_repo_lock(repos: dict[str, dict]) -> tuple[list[str], list[str]]:
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
        else:
            issues.append(f"CRITICAL: Repo {repo_id}: unsupported source type {source_type}")
            continue
        locked_sha = entry.get("content_manifest_sha", "")
        if not locked_sha:
            issues.append(f"CRITICAL: Repo {repo_id}: missing content_manifest_sha")
            continue
        extensions = set(entry.get("metadata", {}).get("extensions", [".rs"]))
        computed_sha, file_count, total_lines = compute_normalized_manifest_sha(
            repo_path, extensions
        )
        if computed_sha != locked_sha:
            issues.append(
                f"CRITICAL: Repo {repo_id}: content_manifest_sha MISMATCH "
                f"(locked={locked_sha[:16]}... computed={computed_sha[:16]}...)"
            )
        else:
            info.append(
                f"Repo {repo_id}: content_manifest_sha verified ({file_count} files, {total_lines} lines)"
            )
    return issues, info


# ── Isolated benchmark root ───────────────────────────────────────────


def create_isolated_root(repo_id: str, entry: dict) -> tuple[Path, list[str]]:
    issues: list[str] = []
    source = entry.get("source", {})
    source_type = source.get("type", "")
    if source_type == "local_absolute_path":
        source_path = Path(source.get("path", ""))
        if not source_path.exists():
            issues.append(f"CRITICAL: Repo {repo_id}: source path {source_path} missing")
            tmp_dir = tempfile.mkdtemp(prefix=f"r21-isolated-{repo_id}-fail-")
            return Path(tmp_dir), issues
    else:
        issues.append(f"CRITICAL: Repo {repo_id}: unsupported source type {source_type}")
        tmp_dir = tempfile.mkdtemp(prefix=f"r21-isolated-{repo_id}-fail-")
        return Path(tmp_dir), issues

    tmp_dir = tempfile.mkdtemp(prefix=f"r21-isolated-{repo_id}-")
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

    return isolated, issues


def clean_runtime_artifacts(isolated: Path) -> None:
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


# ── Phase 1: RUN ──────────────────────────────────────────────────────


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


def validate_predictions_with_rust(
    openlocus: str,
    strategy: str,
    predictions: list[dict],
    isolated_roots: dict[str, Path],
) -> tuple[dict[str, Any], list[str]]:
    """Validate Evidence citations with Rust while isolated roots still exist."""
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
            with tempfile.NamedTemporaryFile(
                "w",
                prefix=f"r21-{strategy}-{repo_id}-citations-",
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
                f"CRITICAL: {strategy}: citation validator failed for repo {repo_id}: "
                f"{proc.stderr[:300]}"
            )
            total += len(evidence)
            invalid += len(evidence)
            continue

        try:
            result = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except json.JSONDecodeError:
            issues.append(
                f"CRITICAL: {strategy}: citation validator returned non-JSON for repo {repo_id}"
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
                f"CRITICAL: {strategy}: citation validator total mismatch for repo {repo_id} "
                f"(expected {len(evidence)}, got {repo_total})"
            )
        if repo_invalid != 0:
            issues.append(
                f"CRITICAL: {strategy}: {repo_invalid} invalid citations for repo {repo_id}"
            )

    rate = valid / total if total else 1.0
    if invalid != 0 or rate < 1.0:
        issues.append(
            f"CRITICAL: {strategy}: citation validity must be 1.0 "
            f"(valid={valid}, total={total}, invalid={invalid})"
        )

    # Check freshness field availability
    freshness_available = False
    for pred in predictions:
        for e in pred.get("evidence", []):
            if "freshness" in e or "verified_current" in e:
                freshness_available = True
                break
        if freshness_available:
            break

    return {
        "citation_validity": rate,
        "citation_valid_count": valid,
        "citation_total_count": total,
        "citation_invalid_count": invalid,
        "citation_validator_invocations": invocations,
        "citation_validation_mode": "fail_closed_hash_range_path",
        "citation_hash_checked": total > 0 and invocations > 0,
        "citation_not_applicable": total == 0,
        "freshness_field_available": freshness_available,
        "verified_current_rate": None if not freshness_available else (1.0 if rate == 1.0 and total > 0 else 0.0),
    }, issues


def check_predictions_for_forbidden_paths(
    predictions: list[dict], strategy: str
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


def audit_isolated_roots_runtime(
    isolated_roots: dict[str, Path], stage: str
) -> list[str]:
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
                if fname.startswith(".r21-") or "-citations-" in fname:
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


# ── RRF fusion for composite strategies ────────────────────────────────


def rrf_fuse_predictions(
    pred_a: dict, pred_b: dict, k: int = 60
) -> list[dict]:
    """RRF fuse two prediction evidence lists."""
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
        # Do not add a synthetic RRF channel here. EvidenceCore only accepts
        # known retrieval channels (regex/path/bm25/dense/tree_sitter/lsp/scip/
        # graph/manual). Fusion is a ranking operation over already-materialized
        # evidence, not a new authoritative evidence channel.
        e["channels"] = list(e.get("channels", []))
        result.append(e)
    return result


# ── Composite strategy builders ────────────────────────────────────────


def build_composite_prediction(
    strategy: str,
    task: dict,
    base_predictions: dict[str, dict],  # task_id -> {strategy -> prediction}
) -> dict:
    """Build composite/guard strategy prediction from base predictions.

    Never calls CLI, never reads labels.
    """
    task_id = task["task_id"]
    query = task["query"]
    repo_id = task.get("repo_id", "")
    preds = base_predictions.get(task_id, {})

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

    elif strategy == "rrf_guarded_by_symbol":
        rrf_pred = preds.get("rrf", {})
        symbol_pred = preds.get("symbol", {})
        symbol_has = bool(symbol_pred and symbol_pred.get("evidence"))
        if symbol_has:
            evidence = rrf_pred.get("evidence", []) if rrf_pred else []
            selected_method = "rrf"
            route_decision = "rrf_guarded_symbol_present"
        else:
            evidence = []
            selected_method = "empty"
            route_decision = "rrf_guarded_no_symbol"

    elif strategy == "rrf_guarded_by_regex":
        rrf_pred = preds.get("rrf", {})
        regex_pred = preds.get("regex", {})
        regex_has = bool(regex_pred and regex_pred.get("evidence"))
        if regex_has:
            evidence = rrf_pred.get("evidence", []) if rrf_pred else []
            selected_method = "rrf"
            route_decision = "rrf_guarded_regex_present"
        else:
            evidence = []
            selected_method = "empty"
            route_decision = "rrf_guarded_no_regex"

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
            top_score = rrf_evidence[0].get("score", 0.0) if rrf_evidence else 0.0
            symbol_has = bool(symbol_pred and symbol_pred.get("evidence"))
            regex_has = bool(regex_pred and regex_pred.get("evidence"))
            threshold = 0.0
            if top_score >= threshold and (symbol_has or regex_has) and rrf_evidence:
                evidence = rrf_evidence
                selected_method = "rrf"
                route_decision = "query_noise_plus_rrf_agree_min_0.0"
            else:
                evidence = []
                selected_method = "empty"
                route_decision = "query_noise_plus_rrf_agree_min_0.0_empty"

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


# ── Rejection builder ─────────────────────────────────────────────────


def build_rejections(
    predictions: list[dict], strategy: str
) -> list[dict]:
    """Build rejections from predictions. No labels visible."""
    rejections = []
    for pred in predictions:
        evidence = pred.get("evidence", [])
        route = pred.get("route_decision", "")
        # Composite strategies may abstain
        if not evidence and route and "guard" in route.lower():
            rejections.append({
                "task_id": pred["task_id"],
                "repo_id": pred.get("repo_id", ""),
                "strategy": strategy,
                "phase": "route",
                "reason": route,
                "label_visible": False,
            })
        elif not evidence and pred.get("returncode", 0) != 0:
            rejections.append({
                "task_id": pred["task_id"],
                "repo_id": pred.get("repo_id", ""),
                "strategy": strategy,
                "phase": "cli_error",
                "reason": f"returncode={pred.get('returncode')}",
                "label_visible": False,
            })
    return rejections


# ── Trace builder ──────────────────────────────────────────────────────


def build_trace(predictions: list[dict], strategy: str) -> list[dict]:
    """Build run-visible trace entries. No labels/private fields."""
    trace = []
    for pred in predictions:
        trace.append({
            "task_id": pred["task_id"],
            "repo_id": pred.get("repo_id", ""),
            "query": pred.get("query", ""),
            "strategy": strategy,
            "selected_method": pred.get("selected_method", ""),
            "route_decision": pred.get("route_decision", ""),
            "evidence_count": len(pred.get("evidence", [])),
            "latency_ms": pred.get("latency_ms", 0),
            "returncode": pred.get("returncode", 0),
        })
    return trace


# ── Phase 1: RUN main ─────────────────────────────────────────────────


def run_phase(
    tasks: list[dict],
    openlocus: str,
    strategies: list[str],
    repos: dict[str, dict],
    workspace: Path,
) -> tuple[
    dict[str, list[dict]],
    dict[str, dict[str, Any]],
    dict[str, list[dict]],
    dict[str, list[dict]],
    dict[str, Any],
    list[str],
]:
    """Phase 1: Run retrieval for all tasks/strategies."""
    safety_issues: list[str] = []
    runs_dir = workspace / "runs"

    # Create isolated roots per repo
    isolated_roots: dict[str, Path] = {}
    for repo_id, entry in repos.items():
        isolated, iso_issues = create_isolated_root(repo_id, entry)
        isolated_roots[repo_id] = isolated
        safety_issues.extend(iso_issues)

    canary_summary, canary_issues = check_canary_retrieval(openlocus, isolated_roots)
    safety_issues.extend(canary_issues)

    all_predictions: dict[str, list[dict]] = {}
    all_rejections: dict[str, list[dict]] = {}
    all_traces: dict[str, list[dict]] = {}
    all_evidence: dict[str, list[dict]] = {}
    citation_summaries: dict[str, dict[str, Any]] = {}

    # Run base strategies first (they need CLI calls)
    base_preds_by_task: dict[str, dict[str, dict]] = {}  # task_id -> {strategy -> prediction}

    for strategy in strategies:
        if strategy in BASE_STRATEGIES:
            safety_issues.extend(audit_isolated_roots_runtime(isolated_roots, f"before-{strategy}"))
            predictions: list[dict] = []
            for task in tasks:
                query = task["query"]
                task_id = task["task_id"]
                repo_id = task.get("repo_id", "")

                if repo_id not in isolated_roots:
                    safety_issues.append(
                        f"CRITICAL: task {task_id} references unknown repo_id '{repo_id}'."
                    )
                    predictions.append({
                        "task_id": task_id,
                        "repo_id": repo_id,
                        "query": query,
                        "strategy": strategy,
                        "selected_method": strategy,
                        "route_decision": f"baseline_{strategy}",
                        "evidence": [],
                        "latency_ms": 0,
                        "returncode": -1,
                    })
                    continue

                cwd = str(isolated_roots[repo_id])
                result = run_query(openlocus, strategy, query, cwd)
                clean_runtime_artifacts(isolated_roots[repo_id])

                if result.get("returncode") != 0:
                    safety_issues.append(
                        f"WARNING: {strategy} query failed for task {task_id}: "
                        f"{result.get('stderr', '')[:300]}"
                    )

                pred = {
                    "task_id": task_id,
                    "repo_id": repo_id,
                    "query": query,
                    "strategy": strategy,
                    "selected_method": strategy,
                    "route_decision": f"baseline_{strategy}",
                    "evidence": result["evidence"],
                    "latency_ms": result["latency_ms"],
                    "returncode": result["returncode"],
                }
                predictions.append(pred)
                base_preds_by_task.setdefault(task_id, {})[strategy] = pred

            # Validate citations for base strategy BEFORE cleanup
            forbidden_issues = check_predictions_for_forbidden_paths(predictions, strategy)
            safety_issues.extend(forbidden_issues)

            citation_summary, citation_issues = validate_predictions_with_rust(
                openlocus, strategy, predictions, isolated_roots
            )
            citation_summaries[strategy] = citation_summary
            safety_issues.extend(citation_issues)
            safety_issues.extend(audit_isolated_roots_runtime(isolated_roots, f"after-{strategy}"))

            all_predictions[strategy] = predictions
            all_evidence[strategy] = [
                {"task_id": p["task_id"], "repo_id": p.get("repo_id", ""), "evidence": p["evidence"]}
                for p in predictions
            ]
            all_rejections[strategy] = build_rejections(predictions, strategy)
            all_traces[strategy] = build_trace(predictions, strategy)

    # Build composite strategies from base predictions
    for strategy in strategies:
        if strategy in COMPOSITE_STRATEGIES:
            predictions = []
            for task in tasks:
                pred = build_composite_prediction(strategy, task, base_preds_by_task)
                predictions.append(pred)

            all_predictions[strategy] = predictions
            all_evidence[strategy] = [
                {"task_id": p["task_id"], "repo_id": p.get("repo_id", ""), "evidence": p["evidence"]}
                for p in predictions
            ]
            all_rejections[strategy] = build_rejections(predictions, strategy)
            all_traces[strategy] = build_trace(predictions, strategy)

    # ── Validate citations for ALL strategies before cleanup ────────────
    # Composite/guard evidence is a subset of validated base predictions,
    # but we still run the Rust validator to get true per-strategy counts.
    # Guard strategies that pass through RRF evidence unchanged will validate
    # identically to RRF; fused strategies produce new evidence dicts.
    for strategy in strategies:
        if strategy in BASE_STRATEGIES:
            # Already validated above; skip re-validation
            continue
        # Composite/guard: validate selected evidence via Rust
        predictions = all_predictions[strategy]
        forbidden_issues = check_predictions_for_forbidden_paths(predictions, strategy)
        safety_issues.extend(forbidden_issues)

        citation_summary, citation_issues = validate_predictions_with_rust(
            openlocus, strategy, predictions, isolated_roots
        )
        # Override citation semantics for composite/guard strategies:
        # evidence was drawn from base-validated predictions, but we also
        # ran the Rust validator to confirm. Record both facts.
        citation_summary["citation_inherited_from_base"] = True
        citation_summary["citation_validated_by_rust"] = True
        # If the validator saw 0 evidence (guard abstained), mark properly
        if citation_summary.get("citation_total_count", 0) == 0:
            citation_summary["citation_not_applicable"] = True
            citation_summary["citation_hash_checked"] = False  # not bool-true: no hashes to check
        else:
            citation_summary["citation_not_applicable"] = False
            citation_summary["citation_hash_checked"] = citation_summary.get("citation_hash_checked", True)
        citation_summaries[strategy] = citation_summary
        safety_issues.extend(citation_issues)

    # Write R21-owned artifacts
    artifact_manifest: dict[str, Any] = {}
    for strategy in strategies:
        pred_path = runs_dir / f"r21-auto-wide-{strategy}-predictions.jsonl"
        evid_path = runs_dir / f"r21-auto-wide-{strategy}-evidence.jsonl"
        rej_path = runs_dir / f"r21-auto-wide-{strategy}-rejections.jsonl"
        trace_path = runs_dir / f"r21-auto-wide-{strategy}-trace.jsonl"

        write_jsonl(pred_path, all_predictions[strategy])
        write_jsonl(evid_path, all_evidence[strategy])
        write_jsonl(rej_path, all_rejections[strategy])
        write_jsonl(trace_path, all_traces[strategy])

        artifact_manifest[strategy] = {
            "predictions": artifact_provenance(pred_path),
            "evidence": artifact_provenance(evid_path),
            "rejections": artifact_provenance(rej_path),
            "trace": artifact_provenance(trace_path),
        }

    manifest_path = runs_dir / "r21-auto-wide-artifacts-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(artifact_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # Cleanup isolated roots (after citation validation)
    for isolated in isolated_roots.values():
        shutil.rmtree(isolated, ignore_errors=True)

    return all_predictions, citation_summaries, all_rejections, all_traces, canary_summary, safety_issues


# ── Phase 2: SCORE ────────────────────────────────────────────────────


def build_gold_line_set(label: dict) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for span in label.get("gold_spans", []):
        path = span.get("path", "")
        start = span.get("start_line", 0)
        end = span.get("end_line", 0)
        for ln in range(start, end + 1):
            result.add((path, ln))
    return result


def build_hard_distractor_line_set(label: dict) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for hd in label.get("hard_distractors", []):
        path = hd.get("path", "")
        start = hd.get("start_line", 0)
        end = hd.get("end_line", 0)
        if start > 0 and end >= start:
            for ln in range(start, end + 1):
                result.add((path, ln))
        elif path:
            result.add((path, 0))
    return result


def build_must_not_primary_line_set(label: dict) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for mnp in label.get("must_not_primary", []):
        path = mnp.get("path", "")
        start = mnp.get("start_line", 0)
        end = mnp.get("end_line", 0)
        if start > 0 and end >= start:
            for ln in range(start, end + 1):
                result.add((path, ln))
        elif path:
            result.add((path, 0))
    return result


def get_gold_paths(label: dict) -> set[str]:
    return {span.get("path", "") for span in label.get("gold_spans", [])}


def get_hard_distractor_paths(label: dict) -> set[str]:
    return {hd.get("path", "") for hd in label.get("hard_distractors", [])}


def match_path(pred_path: str, label_path: str, repo_id: str) -> bool:
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


def span_precision_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int
) -> float:
    total_prec = 0.0
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
        matched_lines: set[tuple[str, int]] = set()
        for (pp, pln) in pred_lines:
            for (gp, gln) in gold_lines:
                if match_path(pp, gp, repo_id) and pln == gln:
                    matched_lines.add((gp, gln))
        overlap = len(matched_lines)
        total_prec += overlap / len(pred_lines) if pred_lines else 0.0
    return total_prec / total if total else 0.0


def span_recall_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int
) -> float:
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
        matched_lines: set[tuple[str, int]] = set()
        for (pp, pln) in pred_lines:
            for (gp, gln) in gold_lines:
                if match_path(pp, gp, repo_id) and pln == gln:
                    matched_lines.add((gp, gln))
        overlap = len(matched_lines)
        total_rec += overlap / len(gold_lines) if gold_lines else 0.0
    return total_rec / total if total else 0.0


def span_f_beta_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int, beta: float = 0.5
) -> float:
    avg_prec = span_precision_at_k(predictions, gold, k)
    avg_rec = span_recall_at_k(predictions, gold, k)
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


def no_gold_nonempty_rate_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int
) -> float:
    """Rate of non-empty evidence on tasks where expected_behavior in {abstain,no_primary}
    and gold_spans is empty. Renamed from negative_nonempty for semantic clarity:
    denominator = tasks with no gold spans AND expected_behavior in {abstain,no_primary};
    numerator = those with non-empty evidence at k."""
    nonempty = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        if task_id not in gold:
            continue
        label = gold[task_id]
        eb = label.get("expected_behavior", "")
        # Only count tasks where expected_behavior is abstain or no_primary
        if eb not in ("abstain", "no_primary"):
            continue
        if label.get("gold_spans"):
            continue
        total += 1
        if pred.get("evidence", [])[:k]:
            nonempty += 1
    return nonempty / total if total else 0.0


def hard_distractor_hit_rate_at_k(
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
        hard_dist_lines = build_hard_distractor_line_set(label)
        hard_dist_paths = get_hard_distractor_paths(label)
        if not hard_dist_paths:
            continue
        total += 1
        for e in pred.get("evidence", [])[:k]:
            pred_path = e.get("path", "")
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            if start > 0 and end >= start:
                for ln in range(start, end + 1):
                    for (hp, hln) in hard_dist_lines:
                        if match_path(pred_path, hp, repo_id) and ln == hln:
                            hits += 1
                            break
                    else:
                        if any(
                            match_path(pred_path, hp, repo_id) and hln == 0
                            for hp, hln in hard_dist_lines
                        ):
                            hits += 1
                            break
                        continue
                    break
    return hits / total if total else 0.0


def false_primary_on_negative_rate(
    predictions: list[dict], gold: dict[str, dict]
) -> float:
    """primary_false_positive_rate: denominator labels expected_behavior in {abstain,no_primary};
    numerator top1 evidence exists."""
    false_primary = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        if task_id not in gold:
            continue
        label = gold[task_id]
        eb = label.get("expected_behavior", "")
        if eb not in ("abstain", "no_primary"):
            continue
        total += 1
        evidence = pred.get("evidence", [])
        if evidence:
            false_primary += 1
    return false_primary / total if total else 0.0


def abstain_rate(predictions: list[dict]) -> float:
    """Rate of empty evidence across all tasks."""
    abstained = 0
    total = len(predictions)
    for pred in predictions:
        if not pred.get("evidence", []):
            abstained += 1
    return abstained / total if total else 0.0


def weak_candidate_rate(
    predictions: list[dict], gold: dict[str, dict]
) -> float:
    """Rate of tasks where expected_behavior=weak_candidates and evidence is non-empty."""
    weak = 0
    weak_with_evidence = 0
    for pred in predictions:
        task_id = pred["task_id"]
        if task_id not in gold:
            continue
        label = gold[task_id]
        if label.get("expected_behavior", "") == "weak_candidates":
            weak += 1
            if pred.get("evidence", []):
                weak_with_evidence += 1
    return weak_with_evidence / weak if weak else 0.0


def must_not_primary_violation_rate(
    predictions: list[dict], gold: dict[str, dict]
) -> float:
    """Rate of tasks where top-1 evidence overlaps must_not_primary spans."""
    violations = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        label = gold[task_id]
        mnp_lines = build_must_not_primary_line_set(label)
        if not mnp_lines:
            continue
        total += 1
        evidence = pred.get("evidence", [])
        if not evidence:
            continue
        top = evidence[0]
        top_path = top.get("path", "")
        start = top.get("start_line", 0)
        end = top.get("end_line", 0)
        for ln in range(start, end + 1):
            for (mp, mln) in mnp_lines:
                if match_path(top_path, mp, repo_id) and ln == mln:
                    violations += 1
                    break
            else:
                continue
            break
    return violations / total if total else 0.0


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


def compute_candidate_count_avg(predictions: list[dict]) -> float:
    if not predictions:
        return 0.0
    return sum(len(p.get("evidence", [])) for p in predictions) / len(predictions)


def compute_materialized_span_count_avg(predictions: list[dict]) -> float:
    if not predictions:
        return 0.0
    total_spans = 0
    for p in predictions:
        for e in p.get("evidence", []):
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            if end >= start:
                total_spans += (end - start + 1)
            else:
                total_spans += 1
    return total_spans / len(predictions)


def compute_guard_recall_kill_rate(
    predictions_guarded: list[dict],
    predictions_raw_rrf: list[dict],
    gold: dict[str, dict],
) -> float | None:
    """guard_recall_kill_rate vs raw RRF: denominator primary_evidence labels where RRF hit gold@10;
    numerator guarded strategy misses gold@10."""
    denom = 0
    numer = 0

    guard_by_task = {p["task_id"]: p for p in predictions_guarded}
    rrf_by_task = {p["task_id"]: p for p in predictions_raw_rrf}

    for task_id, label in gold.items():
        if label.get("expected_behavior") != "primary_evidence":
            continue
        if not label.get("gold_spans"):
            continue

        repo_id = label.get("repo_id", "")
        gold_paths = get_gold_paths(label)

        # Check if RRF hits gold@10
        rrf_pred = rrf_by_task.get(task_id)
        if not rrf_pred:
            continue
        rrf_hit = False
        for e in rrf_pred.get("evidence", [])[:10]:
            pred_path = e.get("path", "")
            for gp in gold_paths:
                if match_path(pred_path, gp, repo_id):
                    rrf_hit = True
                    break
            if rrf_hit:
                break
        if not rrf_hit:
            continue

        denom += 1

        # Check if guarded misses gold@10
        guard_pred = guard_by_task.get(task_id)
        if not guard_pred:
            numer += 1
            continue
        guard_hit = False
        for e in guard_pred.get("evidence", [])[:10]:
            pred_path = e.get("path", "")
            for gp in gold_paths:
                if match_path(pred_path, gp, repo_id):
                    guard_hit = True
                    break
            if guard_hit:
                break
        if not guard_hit:
            numer += 1

    return numer / denom if denom > 0 else None


def score_predictions(
    predictions: list[dict],
    gold: dict[str, dict],
    citation_summary: dict[str, Any],
    strategy: str,
    rrf_predictions: list[dict] | None = None,
) -> dict[str, Any]:
    """Phase 2: Score predictions using private labels."""
    total = len(predictions)
    ok = sum(1 for p in predictions if p.get("returncode", 0) == 0)

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
        "citation_not_applicable": citation_summary.get("citation_not_applicable", False),
        "citation_inherited_from_base": citation_summary.get("citation_inherited_from_base", False),
        "citation_validated_by_rust": citation_summary.get("citation_validated_by_rust", False),
        "freshness_field_available": citation_summary.get("freshness_field_available", False),
        "verified_current_rate": citation_summary.get("verified_current_rate"),
        "source_materialization_rejection_rate": "unavailable_no_raw_candidate_denominator",
    }

    # EvidenceCore_rejection_rate: post-run validation rejection rate only
    # This is the citation invalid count / citation total count
    cit_total = citation_summary.get("citation_total_count", 0)
    cit_invalid = citation_summary.get("citation_invalid_count", 0)
    if cit_total > 0:
        metrics["EvidenceCore_rejection_rate"] = cit_invalid / cit_total
    else:
        metrics["EvidenceCore_rejection_rate"] = 0.0

    non_neg_gold = {tid: g for tid, g in gold.items() if g.get("gold_spans")}
    negative_gold = {tid: g for tid, g in gold.items() if not g.get("gold_spans")}
    evaluable_gold = {
        tid: g
        for tid, g in gold.items()
        if g.get("gold_spans") or g.get("hard_distractors")
    }

    if non_neg_gold:
        for k in [1, 3, 5]:
            metrics[f"FileRecall@{k}"] = file_recall_at_k(predictions, non_neg_gold, k)
        metrics["MRR"] = mrr(predictions, non_neg_gold)
        metrics["SpanF0.5"] = span_f_beta_at_k(predictions, non_neg_gold, 10, 0.5)
        metrics["SpanPrecision"] = span_precision_at_k(predictions, non_neg_gold, 10)
        metrics["SpanRecall"] = span_recall_at_k(predictions, non_neg_gold, 10)
        metrics["token_waste"] = token_waste_ratio_at_k(predictions, non_neg_gold, 10)

    if evaluable_gold:
        metrics["hard_distractor_hit_rate"] = hard_distractor_hit_rate_at_k(
            predictions, evaluable_gold, 10
        )

    if negative_gold:
        metrics["no_gold_nonempty_rate"] = no_gold_nonempty_rate_at_k(
            predictions, negative_gold, 10
        )

    # false_primary_on_negative: uses expected_behavior in {abstain, no_primary} as denominator
    metrics["false_primary_on_negative"] = false_primary_on_negative_rate(predictions, gold)
    # primary_false_positive_rate: explicit key requested by user; equals false_primary_on_negative
    metrics["primary_false_positive_rate"] = metrics["false_primary_on_negative"]
    metrics["abstain_rate"] = abstain_rate(predictions)
    metrics["weak_candidate_rate"] = weak_candidate_rate(predictions, gold)
    # must_not_primary_violation_rate: rate of tasks where top-1 evidence overlaps must_not_primary
    metrics["must_not_primary_violation_rate"] = must_not_primary_violation_rate(predictions, gold)

    metrics["latency"] = compute_latency_stats(predictions)
    metrics["candidate_count_avg"] = compute_candidate_count_avg(predictions)
    metrics["materialized_span_count_avg"] = compute_materialized_span_count_avg(predictions)

    # Guard recall kill rate for guard/composite strategies
    is_guard = strategy in (
        "rrf_guarded_by_symbol",
        "rrf_guarded_by_regex",
        "rrf_guarded_by_symbol_regex",
        "query_noise_plus_rrf_agree_min",
    )
    if is_guard and rrf_predictions is not None:
        metrics["guard_recall_kill_rate"] = compute_guard_recall_kill_rate(
            predictions, rrf_predictions, gold
        )
    else:
        metrics["guard_recall_kill_rate"] = None

    # Stale/policy denied (not available without EvidenceCore runtime data)
    metrics["stale_candidate_rejected"] = "unavailable_no_evidencecore_runtime_data"
    metrics["policy_denied_rejected"] = "unavailable_no_evidencecore_runtime_data"

    return metrics


def compute_bucket_metrics(
    predictions: list[dict],
    gold: dict[str, dict],
    citation_summary: dict[str, Any],
    strategy: str,
    bucket_key: str,
) -> dict[str, dict[str, Any]]:
    """Compute metrics bucketed by a label field."""
    # Group task_ids by bucket
    buckets: dict[str, list[str]] = defaultdict(list)
    for tid, label in gold.items():
        val = label.get(bucket_key, "unknown")
        if isinstance(val, list):
            val = ",".join(str(v) for v in val) if val else "none"
        else:
            val = str(val)
        buckets[val].append(tid)

    result: dict[str, dict[str, Any]] = {}
    for bucket_val, task_ids in sorted(buckets.items()):
        bucket_gold = {tid: gold[tid] for tid in task_ids}
        bucket_preds = [p for p in predictions if p["task_id"] in task_ids]
        if not bucket_preds:
            continue
        # Simplified metrics for buckets
        non_neg = {tid: g for tid, g in bucket_gold.items() if g.get("gold_spans")}
        neg = {tid: g for tid, g in bucket_gold.items() if not g.get("gold_spans")}
        m: dict[str, Any] = {
            "total_tasks": len(bucket_preds),
        }
        if non_neg:
            m["FileRecall@1"] = file_recall_at_k(bucket_preds, non_neg, 1)
            m["FileRecall@3"] = file_recall_at_k(bucket_preds, non_neg, 3)
            m["MRR"] = mrr(bucket_preds, non_neg)
            m["SpanF0.5"] = span_f_beta_at_k(bucket_preds, non_neg, 10, 0.5)
        if neg:
            m["no_gold_nonempty_rate"] = no_gold_nonempty_rate_at_k(bucket_preds, neg, 10)
        m["abstain_rate"] = abstain_rate(bucket_preds)
        m["false_primary_on_negative"] = false_primary_on_negative_rate(bucket_preds, bucket_gold)
        m["primary_false_positive_rate"] = m["false_primary_on_negative"]
        m["must_not_primary_violation_rate"] = must_not_primary_violation_rate(bucket_preds, bucket_gold)
        result[bucket_val] = m
    return result


# ── Private-field denylist for artifact scan ────────────────────────────

PRIVATE_FIELD_DENYLIST = [
    "gold_spans", "gold_paths", "gold_lines", "hard_negatives",
    "hard_distractors", "expected_behavior", "query_category",
    "risk_tags", "must_not_primary", "oracle_type", "label_quality",
    "which_strategy_it_targets", "why_this_is_hard", "intent_guess",
    "caveat", "source_tier",
]


def scan_artifacts_for_private_fields(
    runs_dir: Path, strategies: list[str]
) -> list[str]:
    """Scan all R21-owned JSONL artifacts for private label fields. Hard fail on any hit."""
    issues: list[str] = []
    for strategy in strategies:
        for ftype in ["predictions", "evidence", "rejections", "trace"]:
            path = runs_dir / f"r21-auto-wide-{strategy}-{ftype}.jsonl"
            if not path.exists():
                continue
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                for field in PRIVATE_FIELD_DENYLIST:
                    # Match field as JSON key: "field_name"
                    if f'"{field}"' in line:
                        issues.append(
                            f"CRITICAL: private field '{field}' found in {path.name} "
                            f"line {line_no}"
                        )
    return issues


def scan_artifacts_for_canary_tokens(
    runs_dir: Path, strategies: list[str]
) -> list[str]:
    """Scan all R21-owned JSONL artifacts for canary token strings. Hard fail on any hit."""
    issues: list[str] = []
    for strategy in strategies:
        for ftype in ["predictions", "evidence", "rejections", "trace"]:
            path = runs_dir / f"r21-auto-wide-{strategy}-{ftype}.jsonl"
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            for token in CANARY_TOKENS:
                if token in content:
                    issues.append(
                        f"CRITICAL: canary token '{token}' found in {path.name}"
                    )
    return issues


# ── Prediction/report consistency check ────────────────────────────────


def verify_prediction_report_consistency(
    all_metrics: dict[str, dict[str, Any]],
    predictions: list[dict],
    gold: dict[str, dict],
    citation_summary: dict[str, Any],
    strategy: str,
    rrf_predictions: list[dict] | None = None,
) -> list[str]:
    """Recompute metrics from artifact predictions and labels; compare to report metrics."""
    issues: list[str] = []
    recomputed = score_predictions(predictions, gold, citation_summary, strategy, rrf_predictions)

    numeric_keys = [
        "FileRecall@1", "FileRecall@3", "FileRecall@5", "MRR", "SpanF0.5",
        "SpanPrecision", "SpanRecall", "token_waste", "no_gold_nonempty_rate",
        "hard_distractor_hit_rate", "false_primary_on_negative",
        "primary_false_positive_rate", "must_not_primary_violation_rate",
        "abstain_rate", "weak_candidate_rate",
    ]
    # Exclude citation metrics from consistency check: they require Rust validator
    # against isolated roots which are cleaned up after the RUN phase.
    # citation_validity, EvidenceCore_rejection_rate, verified_current_rate
    # cannot be recomputed from predictions + labels alone.

    for key in numeric_keys:
        reported = all_metrics.get(key)
        recomputed_val = recomputed.get(key)
        if reported is None and recomputed_val is None:
            continue
        if reported is None or recomputed_val is None:
            issues.append(
                f"CRITICAL: {strategy}: metric presence mismatch for {key} "
                f"(reported={reported}, recomputed={recomputed_val})"
            )
            continue
        if isinstance(reported, (int, float)) and isinstance(recomputed_val, (int, float)):
            if abs(float(reported) - float(recomputed_val)) > 1e-9:
                issues.append(
                    f"CRITICAL: {strategy}: prediction/report metric mismatch for {key} "
                    f"(reported={reported}, recomputed={recomputed_val})"
                )
    return issues


# ── Failure surface summary ───────────────────────────────────────────


def compute_failure_surface_summary(
    all_metrics: dict[str, dict[str, Any]],
    gold: dict[str, dict],
) -> list[str]:
    """Summarize failure surfaces across strategies."""
    summary = []

    # 1. No-gold nonempty rate by strategy
    for strategy in ALL_IMPLEMENTED_STRATEGIES:
        m = all_metrics.get(strategy, {})
        neg = m.get("no_gold_nonempty_rate")
        if neg is not None and neg > 0.1:
            summary.append(
                f"{strategy}: high no_gold_nonempty_rate={neg:.3f} (false positives on no-gold tasks)"
            )

    # 2. Recall gaps
    rrf_recall = all_metrics.get("rrf", {}).get("FileRecall@1", 0.0)
    for strategy in ALL_IMPLEMENTED_STRATEGIES:
        m = all_metrics.get(strategy, {})
        recall1 = m.get("FileRecall@1")
        if recall1 is not None and rrf_recall > 0 and (rrf_recall - recall1) > 0.15:
            summary.append(
                f"{strategy}: FileRecall@1={recall1:.3f} is >0.15 below RRF={rrf_recall:.3f} (recall gap)"
            )

    # 3. Guard kill rate
    for strategy in COMPOSITE_STRATEGIES:
        m = all_metrics.get(strategy, {})
        kill = m.get("guard_recall_kill_rate")
        if kill is not None and kill > 0.1:
            summary.append(
                f"{strategy}: guard_recall_kill_rate={kill:.3f} (guard kills >10% of RRF recall)"
            )

    # 4. Label quality caveats
    label_qualities = set()
    for label in gold.values():
        lq = label.get("label_quality", "")
        if lq:
            label_qualities.add(lq)
    if "weak" in label_qualities:
        weak_count = sum(1 for l in gold.values() if l.get("label_quality") == "weak")
        summary.append(
            f"R20 labels contain {weak_count} weak labels; all metrics are failure-surface probes, not promotion evidence"
        )

    # 5. Citation issues
    for strategy in BASE_STRATEGIES:
        m = all_metrics.get(strategy, {})
        if m.get("citation_validity", 1.0) < 1.0:
            summary.append(f"{strategy}: citation_validity < 1.0 (CRITICAL)")

    if not summary:
        summary.append("No critical failure surfaces detected at summary level (detailed bucket metrics may still show failures)")

    return summary


# ── Main ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="R21 Auto-Wide Strategy Matrix Runner/Scorer"
    )
    parser.add_argument("--workspace", default=".", help="Workspace root directory")
    parser.add_argument("--fixtures", default="fixtures/r20_auto_wide", help="Fixtures directory relative to workspace")
    parser.add_argument("--openlocus", default="target/debug/openlocus", help="Path to openlocus binary")
    parser.add_argument("--out", default="runs/r21-auto-wide-report.json", help="Output path for JSON report")
    parser.add_argument("--strategies", default=None, help="Comma-separated strategies; default all implemented")
    parser.add_argument("--skip-run", action="store_true", help="DISABLED: canary/citation validation cannot be bypassed")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tasks (smoke test)")
    args = parser.parse_args()

    if args.skip_run:
        print(
            "ERROR: --skip-run is disabled. Canary and citation validation cannot be "
            "bypassed by reusing artifacts. Run fresh every time to ensure safety "
            "gate integrity. Set skip_run_supported=false in report.",
            file=sys.stderr,
        )
        sys.exit(1)

    workspace = Path(args.workspace).resolve()
    fixtures_dir = workspace / args.fixtures
    openlocus_path = str(Path(args.openlocus).resolve())
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = (workspace / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    strategies = (
        [s.strip() for s in args.strategies.split(",")]
        if args.strategies
        else list(ALL_IMPLEMENTED_STRATEGIES)
    )

    # Validate strategies
    for s in strategies:
        if s not in ALL_IMPLEMENTED_STRATEGIES:
            print(f"ERROR: Unknown strategy '{s}'. Available: {ALL_IMPLEMENTED_STRATEGIES}", file=sys.stderr)
            sys.exit(1)

    # ── Load fixture data (RUN phase: tasks + repo lock only) ──────────

    if not fixtures_dir.exists():
        print(f"ERROR: Fixtures directory not found: {fixtures_dir}", file=sys.stderr)
        sys.exit(1)

    # Load repo lock
    repos: dict[str, dict] = {}
    lock_path = fixtures_dir / "repos.lock.jsonl"
    if not lock_path.exists():
        print(f"ERROR: repos.lock.jsonl not found: {lock_path}", file=sys.stderr)
        sys.exit(1)
    for entry in load_jsonl(lock_path):
        repos[entry["repo_id"]] = entry

    # Validate repo lock
    lock_issues, lock_info = validate_repo_lock(repos)
    safety_issues: list[str] = list(lock_issues)
    for info in lock_info:
        print(f"  INFO: {info}")

    # Load tasks (public only)
    tasks_path = fixtures_dir / "tasks" / "auto_wide.jsonl"
    if not tasks_path.exists():
        print(f"ERROR: tasks file not found: {tasks_path}", file=sys.stderr)
        sys.exit(1)
    tasks = load_jsonl(tasks_path)

    if args.limit:
        tasks = tasks[: args.limit]
        print(f"  --limit {args.limit}: using {len(tasks)} tasks")

    # Verify no gold info in tasks
    for task in tasks:
        for field in ["gold_spans", "gold_paths", "gold_lines", "hard_negatives", "hard_distractors",
                       "expected_behavior", "query_category", "risk_tags", "must_not_primary"]:
            if field in task:
                safety_issues.append(f"LEAK: task {task['task_id']} contains {field}")

    # Load dataset manifest
    manifest_path = fixtures_dir / "dataset_manifest.json"
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    print(f"R21 Auto-Wide Matrix: {len(tasks)} tasks, {len(repos)} repos, {len(strategies)} strategies")
    print(f"  Phase 1: RUN (public tasks only, no labels)")

    # ── Phase 1: RUN ──────────────────────────────────────────────────

    all_predictions, citation_summaries, all_rejections, all_traces, canary_summary, run_issues = run_phase(
        tasks, openlocus_path, strategies, repos, workspace
    )
    safety_issues.extend(run_issues)

    # ── Phase 2: SCORE ────────────────────────────────────────────────

    print(f"  Phase 2: SCORE (labels only, no CLI)")

    labels_path = fixtures_dir / "labels" / "auto_wide.jsonl"
    if not labels_path.exists():
        print(f"ERROR: labels file not found: {labels_path}", file=sys.stderr)
        sys.exit(1)
    labels_list = load_jsonl(labels_path)
    gold = {l["task_id"]: l for l in labels_list}

    # Filter gold to only tasks we ran
    task_ids = {t["task_id"] for t in tasks}
    gold = {tid: g for tid, g in gold.items() if tid in task_ids}

    # Score all strategies. Every strategy must have an explicit citation
    # summary produced by RUN; missing summaries are a fail-closed harness error,
    # never a safe default.
    missing_citation_summaries = [s for s in strategies if s not in citation_summaries]
    if missing_citation_summaries:
        print(
            "CRITICAL: missing citation summaries for strategies: "
            + ",".join(missing_citation_summaries),
            file=sys.stderr,
        )
        sys.exit(1)

    all_metrics: dict[str, dict[str, Any]] = {}
    rrf_predictions = all_predictions.get("rrf", [])

    for strategy in strategies:
        predictions = all_predictions.get(strategy, [])
        citation_summary = citation_summaries[strategy]

        metrics = score_predictions(
            predictions, gold, citation_summary, strategy,
            rrf_predictions=rrf_predictions if strategy in COMPOSITE_STRATEGIES else None,
        )
        all_metrics[strategy] = metrics

    # Safety gates (separate CRITICAL from WARNING)
    critical_issues: list[str] = []
    warning_issues: list[str] = []
    for issue in safety_issues:
        if issue.startswith("CRITICAL:"):
            critical_issues.append(issue)
        elif issue.startswith("WARNING:"):
            warning_issues.append(issue)
        elif issue.startswith("LEAK:"):
            critical_issues.append(issue)
        else:
            critical_issues.append(issue)

    for strategy, metrics in all_metrics.items():
        cit_total = metrics.get("citation_total_count", 0)
        if cit_total > 0 and metrics.get("citation_validity") != 1.0:
            critical_issues.append(
                f"CRITICAL: {strategy} citation_validity={metrics.get('citation_validity')} != 1.0"
            )
        # citation_hash_checked: True means Rust validated hashes; False when no evidence to check;
        # "inherited" means composite strategy inherited from base but no direct Rust validation this run
        hash_checked = metrics.get("citation_hash_checked", False)
        not_applicable = metrics.get("citation_not_applicable", False)
        # Pass if: hash_checked is True, OR not_applicable (no evidence), OR inherited from base
        inherited = metrics.get("citation_inherited_from_base", False)
        if not (hash_checked is True or not_applicable is True or inherited):
            critical_issues.append(
                f"CRITICAL: {strategy} citation_hash_checked is not true and no valid explanation "
                f"(hash_checked={hash_checked}, not_applicable={not_applicable}, inherited={inherited})"
            )

    # Prediction/report consistency: reload from R21-owned JSONL artifacts,
    # verify artifact manifest sha/line_count, then recompute metrics.
    consistency_issues: list[str] = []
    runs_dir = workspace / "runs"
    art_manifest_path = runs_dir / "r21-auto-wide-artifacts-manifest.json"
    if art_manifest_path.exists():
        art_manifest = json.loads(art_manifest_path.read_text(encoding="utf-8"))
    else:
        art_manifest = {}

    disk_predictions_by_strategy: dict[str, list[dict]] = {}

    for strategy in strategies:
        # Reload predictions from disk artifact
        pred_path = runs_dir / f"r21-auto-wide-{strategy}-predictions.jsonl"
        if not pred_path.exists():
            consistency_issues.append(
                f"CRITICAL: {strategy}: prediction artifact missing at {pred_path}"
            )
            continue

        # Verify artifact manifest provenance
        if strategy in art_manifest:
            art_prov = art_manifest[strategy].get("predictions", {})
            expected_sha = art_prov.get("sha256", "")
            expected_lines = art_prov.get("jsonl_lines", 0)
            actual_sha = file_sha256(pred_path)
            actual_text = pred_path.read_text(encoding="utf-8")
            actual_lines = sum(1 for l in actual_text.splitlines() if l.strip())
            if expected_sha and actual_sha != expected_sha:
                consistency_issues.append(
                    f"CRITICAL: {strategy}: prediction artifact SHA mismatch "
                    f"(manifest={expected_sha[:16]}... actual={actual_sha[:16]}...)"
                )
            if expected_lines and actual_lines != expected_lines:
                consistency_issues.append(
                    f"CRITICAL: {strategy}: prediction artifact line count mismatch "
                    f"(manifest={expected_lines} actual={actual_lines})"
                )

        # Reload from disk, not in-memory
        disk_predictions = load_jsonl(pred_path)
        disk_predictions_by_strategy[strategy] = disk_predictions

    disk_rrf_predictions = disk_predictions_by_strategy.get("rrf", [])

    for strategy in strategies:
        disk_predictions = disk_predictions_by_strategy.get(strategy, [])
        citation_summary = citation_summaries[strategy]
        issues = verify_prediction_report_consistency(
            all_metrics[strategy], disk_predictions, gold, citation_summary, strategy,
            rrf_predictions=disk_rrf_predictions if strategy in COMPOSITE_STRATEGIES else None,
        )
        consistency_issues.extend(issues)

    if consistency_issues:
        critical_issues.extend(consistency_issues)

    # Bucket metrics
    bucket_metrics: dict[str, dict[str, dict[str, Any]]] = {}
    for strategy in strategies:
        predictions = all_predictions.get(strategy, [])
        citation_summary = citation_summaries.get(strategy, {})
        for bucket_key in ["query_category", "risk_tags", "expected_behavior", "repo_id"]:
            bucket_key_name = bucket_key if bucket_key != "repo_id" else "repo"
            bm = compute_bucket_metrics(predictions, gold, citation_summary, strategy, bucket_key)
            bucket_metrics.setdefault(strategy, {})[bucket_key_name] = bm

    # Language bucket (from repo lock)
    for strategy in strategies:
        predictions = all_predictions.get(strategy, [])
        # Group by language
        lang_buckets: dict[str, list[str]] = defaultdict(list)
        for tid, label in gold.items():
            rid = label.get("repo_id", "")
            if rid in repos:
                lang = repos[rid].get("language", {}).get("primary", "unknown")
            else:
                lang = "unknown"
            lang_buckets[lang].append(tid)

        lang_metrics: dict[str, dict[str, Any]] = {}
        for lang, task_ids_lang in sorted(lang_buckets.items()):
            lang_gold = {tid: gold[tid] for tid in task_ids_lang}
            lang_preds = [p for p in predictions if p["task_id"] in task_ids_lang]
            if not lang_preds:
                continue
            non_neg = {tid: g for tid, g in lang_gold.items() if g.get("gold_spans")}
            neg = {tid: g for tid, g in lang_gold.items() if not g.get("gold_spans")}
            m: dict[str, Any] = {"total_tasks": len(lang_preds)}
            if non_neg:
                m["FileRecall@1"] = file_recall_at_k(lang_preds, non_neg, 1)
                m["MRR"] = mrr(lang_preds, non_neg)
                m["SpanF0.5"] = span_f_beta_at_k(lang_preds, non_neg, 10, 0.5)
            if neg:
                m["no_gold_nonempty_rate"] = no_gold_nonempty_rate_at_k(lang_preds, neg, 10)
            lang_metrics[lang] = m
        bucket_metrics.setdefault(strategy, {})["language"] = lang_metrics

    # Failure surface summary
    failure_summary = compute_failure_surface_summary(all_metrics, gold)

    # Unavailable metrics
    unavailable_metrics: list[str] = [
        "verified_current_rate (freshness field unavailable in CLI output)",
        "source_materialization_rejection_rate (raw candidate denominator unavailable)",
        "stale_candidate_rejected (EvidenceCore runtime data not exposed)",
        "policy_denied_rejected (EvidenceCore runtime data not exposed)",
    ]

    # ── Build report ──────────────────────────────────────────────────

    timestamp = datetime.now(timezone.utc).isoformat()

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": timestamp,
        "workspace": str(workspace),
        "openlocus": openlocus_path,
        "skip_run": args.skip_run,
        "skip_run_supported": False,
        "limit": args.limit,
        "promotion_ready": False,
        "not_promotion_evidence": True,
        "source_dataset_manifest": {
            "path": str(manifest_path),
            "not_promotion_evidence": manifest.get("not_promotion_evidence", True),
            "core_changes": manifest.get("core_changes", False),
            "remote_calls": manifest.get("remote_calls", 0),
            "dense_or_llm_claims": manifest.get("dense_or_llm_claims", False),
            "label_quality": manifest.get("tiers", {}).get("auto_wide", {}).get(
                "label_quality", ["mined_high_confidence", "mined", "weak"]
            ),
        },
        "safety_gates": {
            "all_passed": len(critical_issues) == 0,
            "critical_issues": critical_issues,
            "warning_issues": warning_issues,
            "issues": critical_issues + warning_issues,
            "canary_retrieval": canary_summary,
            "prediction_report_consistency_checked": True,
            "prediction_report_consistency_issue_count": len(consistency_issues),
        },
        "strategy_registry": {
            "implemented": strategies,
            "unavailable": {
                name: reason for name, reason in UNAVAILABLE_STRATEGIES.items()
            },
        },
        "artifact_manifest": {
            "path": str(workspace / "runs" / "r21-auto-wide-artifacts-manifest.json"),
        },
        "metrics": all_metrics,
        "bucket_metrics": bucket_metrics,
        "unavailable_metrics": unavailable_metrics,
        "failure_surface_summary": failure_summary,
        "phases": {
            "run": "public_tasks_only_no_labels",
            "score": "labels_only_no_cli",
            "isolation": "temp_root_per_repo_with_repo_id_folder",
            "citation_mode": "fail_closed_hash_range_path",
            "path_matching": "exact_or_single_repo_id_prefix",
            "policy": "isolated_policy_toml_from_repo_lock",
            "source_type": "external_local_absolute_path",
            "composite_strategies": "built_from_base_predictions_no_cli_no_labels",
            "validator_before_cleanup": True,
        },
        "tasks_count": len(tasks),
        "repos_count": len(repos),
        "labels_count": len(gold),
        "remote_calls": 0,
        "dense_or_llm_claims": False,
        "core_changes": False,
    }

    out_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    # ── Final artifact safety scan ────────────────────────────────────
    # Scan all written R21-owned JSONL artifacts for private field leaks
    # and canary token presence. Hard fail on any hit.
    runs_dir = workspace / "runs"
    private_field_issues = scan_artifacts_for_private_fields(runs_dir, strategies)
    canary_token_issues = scan_artifacts_for_canary_tokens(runs_dir, strategies)
    if private_field_issues:
        critical_issues.extend(private_field_issues)
    if canary_token_issues:
        critical_issues.extend(canary_token_issues)
    # Re-check safety gates after artifact scan
    report["safety_gates"]["all_passed"] = len(critical_issues) == 0
    report["safety_gates"]["critical_issues"] = critical_issues
    report["safety_gates"]["artifact_private_field_scan"] = {
        "scanned": True,
        "issues_found": len(private_field_issues),
    }
    report["safety_gates"]["artifact_canary_token_scan"] = {
        "scanned": True,
        "issues_found": len(canary_token_issues),
    }
    # Rewrite report with updated safety gates
    out_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    # ── Print summary ─────────────────────────────────────────────────

    print(f"\n{'='*70}")
    print(f"R21 Auto-Wide Strategy Matrix Results")
    print(f"{'='*70}")

    metric_display = [
        "FileRecall@1", "FileRecall@3", "FileRecall@5", "MRR",
        "SpanF0.5", "SpanPrecision", "SpanRecall",
        "token_waste", "no_gold_nonempty_rate",
        "hard_distractor_hit_rate",
        "false_primary_on_negative", "primary_false_positive_rate",
        "must_not_primary_violation_rate",
        "abstain_rate", "weak_candidate_rate",
    ]

    for strategy in strategies:
        m = all_metrics.get(strategy, {})
        print(f"\n  {strategy}:")
        for key in metric_display:
            val = m.get(key)
            if val is not None:
                if isinstance(val, float):
                    print(f"    {key}: {val:.3f}")
                else:
                    print(f"    {key}: {val}")
        # Latency
        lat = m.get("latency", {})
        if lat:
            print(f"    latency_p50: {lat.get('p50', 0)}ms, p95: {lat.get('p95', 0)}ms")
        # Citation
        print(f"    citation_validity: {m.get('citation_validity', 'N/A')}")

    if failure_summary:
        print(f"\n  Failure Surface Summary:")
        for item in failure_summary:
            print(f"    - {item}")

    if critical_issues:
        print(f"\n  CRITICAL Safety issues: {len(critical_issues)}")
        for issue in critical_issues:
            print(f"    - {issue}")
    if warning_issues:
        print(f"\n  WARNING: {len(warning_issues)} non-critical issues")
        for issue in warning_issues:
            print(f"    - {issue}")
    if not critical_issues and not warning_issues:
        print(f"\n  Safety checks: ALL PASSED")

    print(f"\n  Report: {out_path}")
    print(f"  promotion_ready: False")
    print(f"  not_promotion_evidence: True")

    if critical_issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
