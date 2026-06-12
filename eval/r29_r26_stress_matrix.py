#!/usr/bin/env python3
"""R29 R26 Auto-Stress Strategy Matrix Runner/Scorer.

Bounded implementation: evaluates failure surfaces across strategies on R26
auto-stress fixtures (1100 tasks). Does NOT change Rust core or EvidenceCore.

Architecture: strictly separated RUN and SCORE phases.
  Phase 1 (RUN): loads only public tasks + repo lock + R26 safety/manifest.
    Creates isolated benchmark roots by allowlist-copying source files.
    Runs base methods via openlocus CLI. Builds composite/guard strategies
    from base predictions. Runs dense_mock build/search and graph_basic.
    Never reads labels. Validates all citations while isolated roots exist.
    Writes all run artifacts before loading labels.
  Phase 2 (SCORE): loads predictions + labels. Computes metrics, failure
    clusters, span contribution, bucket regressions. Never invokes openlocus CLI.

Safety:
  - Runner never loads private labels/gold
  - Retrieval runs inside isolated temp roots (no fixtures/eval/docs/runs)
  - Repo lock content manifest re-verified (normalized hash)
  - Citation validation is fail-closed: every citation must be hash+range+path valid
  - Validator runs BEFORE isolated root cleanup
  - Predictions with forbidden prefixes are critical failures
  - R26 labels weak/mined/deterministic/stress; report has promotion_ready=false
  - Unknown repo_id is CRITICAL; runner refuses to fall back to the full workspace
  - Composite/guard strategies built from base predictions only; no CLI, no labels
  - No synthetic EvidenceCore channels added (no "RRF" channel in evidence)

Implemented strategies (16):
  Base R21-style (4):
    1. regex         - openlocus search regex
    2. bm25          - openlocus search bm25
    3. symbol        - openlocus search symbol
    4. rrf           - openlocus retrieve (RRF fusion)
  Composite R21-style (6):
    5. bm25_regex    - RRF fuse bm25+regex predictions
    6. bm25_symbol   - RRF fuse bm25+symbol predictions
    7. rrf_guarded_by_symbol
    8. rrf_guarded_by_regex
    9. rrf_guarded_by_symbol_regex
    10. query_noise_plus_rrf_agree_min (threshold=0.0)
  R24/R25-style (6):
    11. dense_mock   - openlocus dense build/search --provider mock
    12. dense_mock_plus_rrf - RRF fuse dense_mock + rrf
    13. graph_basic  - derive top path → openlocus impact --depth 1
    14. rrf_plus_graph - RRF fuse graph_basic + rrf
    15. rrf_plus_dense_mock - RRF fuse dense_mock + rrf
    16. rrf_plus_dense_mock_plus_graph - RRF fuse dense_mock + graph_basic + rrf

Unavailable strategies (4) - not run, status=unavailable:
    dense_real_if_available: unavailable, reason not_configured_or_policy_disabled
    tdb_quiver_if_available: unavailable, reason quiver_not_implemented
    tdb_quiver_plus_rrf: unavailable
    tdb_quiver_guarded_by_symbol_regex: unavailable
    fast_context_if_available: unavailable (not wired as standalone matrix strategy)

Usage:
    python3 eval/r29_r26_stress_matrix.py \\
        --workspace . \\
        --fixtures fixtures/r26_auto_stress \\
        --openlocus target/debug/openlocus \\
        --out runs/r29-r26-stress-matrix-report.json

    # --skip-run is disabled: must always run fresh.
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

SCHEMA_VERSION = "r29-v1"

# ── Strategy definitions ───────────────────────────────────────────────

BASE_STRATEGIES = ["regex", "bm25", "symbol", "rrf"]
COMPOSITE_STRATEGIES = [
    "bm25_regex",
    "bm25_symbol",
    "rrf_guarded_by_symbol",
    "rrf_guarded_by_regex",
    "rrf_guarded_by_symbol_regex",
    "query_noise_plus_rrf_agree_min",
]
R24_R25_STYLE_STRATEGIES = [
    "dense_mock",
    "dense_mock_plus_rrf",
    "graph_basic",
    "rrf_plus_graph",
    "rrf_plus_dense_mock",
    "rrf_plus_dense_mock_plus_graph",
]
ALL_IMPLEMENTED_STRATEGIES = (
    BASE_STRATEGIES + COMPOSITE_STRATEGIES + R24_R25_STYLE_STRATEGIES
)

UNAVAILABLE_STRATEGIES = {
    "dense_real_if_available": {
        "status": "unavailable",
        "reason": "not_configured_or_policy_disabled",
    },
    "tdb_quiver_if_available": {
        "status": "unavailable",
        "reason": "quiver_not_implemented",
    },
    "tdb_quiver_plus_rrf": {
        "status": "unavailable",
        "reason": "quiver_not_implemented",
    },
    "tdb_quiver_guarded_by_symbol_regex": {
        "status": "unavailable",
        "reason": "quiver_not_implemented",
    },
    "fast_context_if_available": {
        "status": "unavailable",
        "reason": "fast_context_is_4turn_orchestration_scaffold_not_standalone_matrix_strategy",
    },
}

# ── Source extensions / skip dirs ──────────────────────────────────────

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
    "R29_CANARY_fixture_label_secret_r29a1",
    "R29_CANARY_eval_benchmark_secret_r29b2",
    "R29_CANARY_docs_summary_secret_r29c3",
    "R29_CANARY_runs_prediction_secret_r29d4",
]

# ── Private-field denylist for artifact scan ────────────────────────────

PRIVATE_FIELD_DENYLIST = [
    "source_category",
    "risk_public",
    "intent_guess",
    "risk_tags",
    "oracle_type",
    "expected_behavior",
    "gold_spans",
    "hard_distractors",
    "must_not_primary",
    "why_this_is_hard",
    "which_strategy_it_targets",
]

# ── Policy exclude patterns ───────────────────────────────────────────

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


# ── Required failure cluster keys ─────────────────────────────────────

REQUIRED_FAILURE_CLUSTERS = [
    "RRF_INHERITED_BM25_FALSE_POSITIVE",
    "GUARD_RECALL_KILL",
    "SYMBOL_EXTRACTION_MISS",
    "REGEX_NORMALIZATION_BUG",
    "DENSE_MOCK_NOISE",
    "DENSE_SEMANTIC_TRAP_FALSE_POSITIVE",
    "GRAPH_NEIGHBOR_FALSE_POSITIVE",
    "GRAPH_ADDS_NO_GOLD",
    "HARD_DISTRACTOR_CONFUSION",
    "NEGATIVE_NONEXISTENT_FALSE_PRIMARY",
    "STALE_INDEX_LIKE_FALSE_PRIMARY",
    "TEST_SOURCE_CONFUSION",
    "FRONTEND_BACKEND_CONFUSION",
    "BENCHMARK_ORACLE_SUSPECT",
]


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


def file_provenance(path: Path) -> dict[str, Any]:
    """Provenance for non-JSONL source artifacts."""
    return {
        "path": str(path),
        "sha256": file_sha256(path),
        "bytes": path.stat().st_size,
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
            tmp_dir = tempfile.mkdtemp(prefix=f"r29-isolated-{repo_id}-fail-")
            return Path(tmp_dir), issues
    else:
        issues.append(f"CRITICAL: Repo {repo_id}: unsupported source type {source_type}")
        tmp_dir = tempfile.mkdtemp(prefix=f"r29-isolated-{repo_id}-fail-")
        return Path(tmp_dir), issues

    tmp_dir = tempfile.mkdtemp(prefix=f"r29-isolated-{repo_id}-")
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


def clean_runtime_artifacts(isolated: Path, preserve_dense: bool = False) -> None:
    """Remove transient OpenLocus artifacts. Optionally preserve dense embeddings."""
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
                prefix=f"r29-{strategy}-{repo_id}-citations-",
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


# ── RRF fusion ────────────────────────────────────────────────────────


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
        # Do not add synthetic RRF channel; EvidenceCore only accepts known channels
        e["channels"] = list(e.get("channels", []))
        result.append(e)
    return result


def rrf_fuse_three_predictions(
    pred_a: dict, pred_b: dict, pred_c: dict, k: int = 60
) -> list[dict]:
    """RRF fuse three prediction evidence lists."""
    score_map: dict[str, float] = {}
    evidence_map: dict[str, dict] = {}

    for pred in [pred_a, pred_b, pred_c]:
        for rank, e in enumerate(pred.get("evidence", [])):
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


# ── Composite strategy builders ────────────────────────────────────────


def build_composite_prediction(
    strategy: str,
    task: dict,
    base_predictions: dict[str, dict],
) -> dict:
    """Build composite/guard strategy prediction from base predictions.
    Never calls CLI, never reads labels."""
    task_id = task["test_id"]
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


# ── R24/R25-style: dense_mock and graph_basic ────────────────────────


def run_dense_build(openlocus: str, cwd: str) -> dict[str, Any]:
    """Run `openlocus dense build --provider mock --experimental --json`."""
    t0 = time.perf_counter()
    proc = subprocess.run(
        [openlocus, "dense", "build", "--provider", "mock", "--experimental", "--json"],
        check=False, text=True, capture_output=True, cwd=cwd,
    )
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
    """Run `openlocus dense search --provider mock --limit N --json <query>`."""
    t0 = time.perf_counter()
    proc = subprocess.run(
        [openlocus, "dense", "search", "--provider", "mock",
         "--limit", str(limit), "--json", query],
        check=False, text=True, capture_output=True, cwd=cwd,
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    result: dict[str, Any] = {}
    try:
        result = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        pass
    return result.get("evidence", []) if isinstance(result, dict) else []


def _extract_evidence_from_search_result(raw: Any) -> list[dict]:
    if isinstance(raw, dict) and "evidence" in raw:
        return raw["evidence"]
    if isinstance(raw, list):
        return raw
    return []


def derive_top_path(openlocus: str, query: str, cwd: str) -> tuple[str | None, str]:
    """Derive top path using symbol search, then regex fallback."""
    for method in ["symbol", "regex"]:
        cmd = [openlocus, "search", method, query, "--json"]
        proc = subprocess.run(cmd, check=False, text=True, capture_output=True, cwd=cwd)
        if proc.returncode != 0:
            continue
        try:
            raw = json.loads(proc.stdout.strip()) if proc.stdout.strip() else []
        except json.JSONDecodeError:
            continue
        evidence = _extract_evidence_from_search_result(raw)
        if evidence:
            top_path = evidence[0].get("path", "")
            if top_path:
                return top_path, method
    return None, "none"


def run_graph_impact(openlocus: str, top_path: str, cwd: str) -> list[dict]:
    """Run `openlocus impact <path> --depth 1 --json`."""
    proc = subprocess.run(
        [openlocus, "impact", top_path, "--depth", "1", "--json"],
        check=False, text=True, capture_output=True, cwd=cwd,
    )
    if proc.returncode != 0:
        return []
    try:
        result = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        return []
    return result.get("evidence", []) if isinstance(result, dict) else []


# ── Rejection / trace builders ────────────────────────────────────────


def build_rejections(predictions: list[dict], strategy: str) -> list[dict]:
    rejections = []
    for pred in predictions:
        evidence = pred.get("evidence", [])
        route = pred.get("route_decision", "")
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


def build_trace(predictions: list[dict], strategy: str) -> list[dict]:
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


# ── Phase 2: SCORE helpers ────────────────────────────────────────────


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


def span_precision_at_k(predictions: list[dict], gold: dict[str, dict], k: int) -> float:
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


def span_recall_at_k(predictions: list[dict], gold: dict[str, dict], k: int) -> float:
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
    nonempty = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        if task_id not in gold:
            continue
        label = gold[task_id]
        eb = label.get("expected_behavior", "")
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
    abstained = 0
    total = len(predictions)
    for pred in predictions:
        if not pred.get("evidence", []):
            abstained += 1
    return abstained / total if total else 0.0


def weak_candidate_rate(
    predictions: list[dict], gold: dict[str, dict]
) -> float:
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


# ── Span contribution analysis (R25-style) ────────────────────────────


def compute_span_contribution(
    expansion_predictions: list[dict],
    baseline_predictions: list[dict],
    gold: dict[str, dict],
    strategy_label: str,
) -> dict[str, Any]:
    baseline_by_task: dict[str, dict] = {p["task_id"]: p for p in baseline_predictions}
    total_added_gold = 0
    total_added_false = 0
    tasks_with_additions = 0
    tasks_expansion_blocked = 0

    for pred in expansion_predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        label = gold[task_id]
        gold_lines = build_gold_line_set(label)
        if not gold_lines:
            continue

        baseline_pred = baseline_by_task.get(task_id, {})
        baseline_lines: set[tuple[str, int]] = set()
        for e in baseline_pred.get("evidence", []):
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            path = e.get("path", "")
            for ln in range(start, end + 1):
                baseline_lines.add((path, ln))

        expansion_lines: set[tuple[str, int]] = set()
        for e in pred.get("evidence", []):
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            path = e.get("path", "")
            for ln in range(start, end + 1):
                expansion_lines.add((path, ln))

        added = expansion_lines - baseline_lines
        if not added:
            continue

        tasks_with_additions += 1
        added_gold = 0
        added_false = 0
        for (pp, pln) in added:
            matched = any(
                match_path(pp, gp, repo_id) and pln == gln
                for gp, gln in gold_lines
            )
            if matched:
                added_gold += 1
            else:
                added_false += 1

        total_added_gold += added_gold
        total_added_false += added_false
        if added_false > added_gold:
            tasks_expansion_blocked += 1

    default_expansion_blocked = total_added_false > total_added_gold

    return {
        f"{strategy_label}_added_gold_span": total_added_gold,
        f"{strategy_label}_added_false_span": total_added_false,
        f"{strategy_label}_tasks_with_additions": tasks_with_additions,
        f"{strategy_label}_default_expansion_blocked": default_expansion_blocked,
    }


# ── Score phase ───────────────────────────────────────────────────────


def score_predictions(
    predictions: list[dict],
    gold: dict[str, dict],
    citation_summary: dict[str, Any],
    strategy: str,
    rrf_predictions: list[dict] | None = None,
) -> dict[str, Any]:
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
    }

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

    metrics["primary_false_positive_rate"] = false_primary_on_negative_rate(predictions, gold)
    metrics["abstain_rate"] = abstain_rate(predictions)
    metrics["weak_candidate_rate"] = weak_candidate_rate(predictions, gold)
    metrics["must_not_primary_violation_rate"] = must_not_primary_violation_rate(predictions, gold)

    metrics["latency"] = compute_latency_stats(predictions)
    metrics["candidate_count_avg"] = compute_candidate_count_avg(predictions)
    metrics["materialized_span_count_avg"] = compute_materialized_span_count_avg(predictions)

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

    return metrics


def compute_bucket_metrics(
    predictions: list[dict],
    gold: dict[str, dict],
    citation_summary: dict[str, Any],
    strategy: str,
    bucket_key: str,
) -> dict[str, dict[str, Any]]:
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
        non_neg = {tid: g for tid, g in bucket_gold.items() if g.get("gold_spans")}
        neg = {tid: g for tid, g in bucket_gold.items() if not g.get("gold_spans")}
        m: dict[str, Any] = {"total_tasks": len(bucket_preds)}
        if non_neg:
            m["FileRecall@1"] = file_recall_at_k(bucket_preds, non_neg, 1)
            m["FileRecall@3"] = file_recall_at_k(bucket_preds, non_neg, 3)
            m["MRR"] = mrr(bucket_preds, non_neg)
            m["SpanF0.5"] = span_f_beta_at_k(bucket_preds, non_neg, 10, 0.5)
        if neg:
            m["no_gold_nonempty_rate"] = no_gold_nonempty_rate_at_k(bucket_preds, neg, 10)
        m["abstain_rate"] = abstain_rate(bucket_preds)
        m["primary_false_positive_rate"] = false_primary_on_negative_rate(bucket_preds, bucket_gold)
        m["must_not_primary_violation_rate"] = must_not_primary_violation_rate(bucket_preds, bucket_gold)
        result[bucket_val] = m
    return result


# ── Failure cluster computation ───────────────────────────────────────


def compute_failure_clusters(
    all_predictions: dict[str, list[dict]],
    gold: dict[str, dict],
) -> dict[str, dict[str, Any]]:
    """Compute required failure clusters."""
    clusters: dict[str, dict[str, Any]] = {}

    rrf_preds = {p["task_id"]: p for p in all_predictions.get("rrf", [])}
    bm25_preds = {p["task_id"]: p for p in all_predictions.get("bm25", [])}
    symbol_preds = {p["task_id"]: p for p in all_predictions.get("symbol", [])}
    regex_preds = {p["task_id"]: p for p in all_predictions.get("regex", [])}
    dense_preds = {p["task_id"]: p for p in all_predictions.get("dense_mock", [])}
    graph_preds = {p["task_id"]: p for p in all_predictions.get("graph_basic", [])}
    guarded_preds = {p["task_id"]: p for p in all_predictions.get("rrf_guarded_by_symbol", {})}

    # 1. RRF_INHERITED_BM25_FALSE_POSITIVE
    rrf_bm25_fp = []
    for tid, label in gold.items():
        if label.get("expected_behavior") not in ("abstain", "no_primary"):
            continue
        rrf_pred = rrf_preds.get(tid)
        if rrf_pred and rrf_pred.get("evidence"):
            rrf_bm25_fp.append(tid)
    clusters["RRF_INHERITED_BM25_FALSE_POSITIVE"] = {
        "count": len(rrf_bm25_fp),
        "affected_strategies": ["rrf", "bm25_regex", "bm25_symbol"],
        "representative_examples": rrf_bm25_fp[:10],
        "bucket_distribution": _bucket_dist(rrf_bm25_fp, gold, "source_category"),
        "suspected_cause": "RRF inherits BM25 false positives on negative/abstain tasks",
        "recommended_next_tests": ["Tune BM25 score thresholds", "Add negative-aware RRF guard"],
    }

    # 2. GUARD_RECALL_KILL
    guard_kill = []
    for tid, label in gold.items():
        if label.get("expected_behavior") != "primary_evidence":
            continue
        if not label.get("gold_spans"):
            continue
        rrf_pred = rrf_preds.get(tid)
        guard_pred = guarded_preds.get(tid)
        if not rrf_pred or not guard_pred:
            continue
        repo_id = label.get("repo_id", "")
        gold_paths = get_gold_paths(label)
        rrf_hit = any(
            match_path(e.get("path", ""), gp, repo_id)
            for e in rrf_pred.get("evidence", [])[:10]
            for gp in gold_paths
        )
        guard_hit = any(
            match_path(e.get("path", ""), gp, repo_id)
            for e in guard_pred.get("evidence", [])[:10]
            for gp in gold_paths
        )
        if rrf_hit and not guard_hit:
            guard_kill.append(tid)
    clusters["GUARD_RECALL_KILL"] = {
        "count": len(guard_kill),
        "affected_strategies": ["rrf_guarded_by_symbol"],
        "representative_examples": guard_kill[:10],
        "bucket_distribution": _bucket_dist(guard_kill, gold, "source_category"),
        "suspected_cause": "Symbol guard kills RRF recall when symbol has no evidence for primary tasks",
        "recommended_next_tests": ["Relax symbol guard with regex fallback", "Lower agreement threshold"],
    }

    # 3. SYMBOL_EXTRACTION_MISS
    symbol_miss = []
    for tid, label in gold.items():
        if not label.get("gold_spans"):
            continue
        sym_pred = symbol_preds.get(tid)
        if sym_pred and not sym_pred.get("evidence"):
            symbol_miss.append(tid)
    clusters["SYMBOL_EXTRACTION_MISS"] = {
        "count": len(symbol_miss),
        "affected_strategies": ["symbol"],
        "representative_examples": symbol_miss[:10],
        "bucket_distribution": _bucket_dist(symbol_miss, gold, "source_category"),
        "suspected_cause": "Heuristic symbol search fails to extract relevant symbols",
        "recommended_next_tests": ["Add TreeSitter AST symbol extraction", "Improve heuristic patterns"],
    }

    # 4. REGEX_NORMALIZATION_BUG
    regex_bug = []
    for tid, label in gold.items():
        if label.get("source_category") == "same_name_symbol":
            rx_pred = regex_preds.get(tid)
            if rx_pred and rx_pred.get("evidence"):
                repo_id = label.get("repo_id", "")
                gold_paths = get_gold_paths(label)
                top_hit = rx_pred["evidence"][0]
                hit_match = any(
                    match_path(top_hit.get("path", ""), gp, repo_id)
                    for gp in gold_paths
                )
                if not hit_match:
                    regex_bug.append(tid)
    clusters["REGEX_NORMALIZATION_BUG"] = {
        "count": len(regex_bug),
        "affected_strategies": ["regex"],
        "representative_examples": regex_bug[:10],
        "bucket_distribution": _bucket_dist(regex_bug, gold, "source_category"),
        "suspected_cause": "Regex normalization or boundary issues cause wrong-symbol match",
        "recommended_next_tests": ["Add word-boundary delimiters", "Cross-check with symbol search"],
    }

    # 5. DENSE_MOCK_NOISE
    dense_noise = []
    for tid, label in gold.items():
        if label.get("expected_behavior") in ("abstain", "no_primary"):
            d_pred = dense_preds.get(tid)
            if d_pred and d_pred.get("evidence"):
                dense_noise.append(tid)
    clusters["DENSE_MOCK_NOISE"] = {
        "count": len(dense_noise),
        "affected_strategies": ["dense_mock", "dense_mock_plus_rrf", "rrf_plus_dense_mock", "rrf_plus_dense_mock_plus_graph"],
        "representative_examples": dense_noise[:10],
        "bucket_distribution": _bucket_dist(dense_noise, gold, "source_category"),
        "suspected_cause": "Mock dense provider returns deterministic but semantically meaningless vectors",
        "recommended_next_tests": ["Replace mock with real embedding provider", "Filter dense candidates by lexical agreement"],
    }

    # 6. DENSE_SEMANTIC_TRAP_FALSE_POSITIVE
    dense_trap_fp = []
    for tid, label in gold.items():
        if label.get("source_category") in ("semantic_trap", "dense_quiver_specific_trap"):
            d_pred = dense_preds.get(tid)
            if d_pred and d_pred.get("evidence"):
                dense_trap_fp.append(tid)
    clusters["DENSE_SEMANTIC_TRAP_FALSE_POSITIVE"] = {
        "count": len(dense_trap_fp),
        "affected_strategies": ["dense_mock", "dense_mock_plus_rrf"],
        "representative_examples": dense_trap_fp[:10],
        "bucket_distribution": _bucket_dist(dense_trap_fp, gold, "source_category"),
        "suspected_cause": "Dense semantic search returns plausible-but-wrong matches for semantic traps",
        "recommended_next_tests": ["Test with real embedding provider", "Add lexical guard to dense results"],
    }

    # 7. GRAPH_NEIGHBOR_FALSE_POSITIVE
    graph_fp = []
    for tid, label in gold.items():
        if label.get("expected_behavior") in ("abstain", "no_primary"):
            g_pred = graph_preds.get(tid)
            if g_pred and g_pred.get("evidence"):
                graph_fp.append(tid)
    clusters["GRAPH_NEIGHBOR_FALSE_POSITIVE"] = {
        "count": len(graph_fp),
        "affected_strategies": ["graph_basic", "rrf_plus_graph", "rrf_plus_dense_mock_plus_graph"],
        "representative_examples": graph_fp[:10],
        "bucket_distribution": _bucket_dist(graph_fp, gold, "source_category"),
        "suspected_cause": "Graph neighbor expansion adds non-gold evidence from import/config edges",
        "recommended_next_tests": ["Filter graph evidence by query relevance", "Limit graph depth to 1"],
    }

    # 8. GRAPH_ADDS_NO_GOLD
    graph_no_gold = []
    rrf_by_task = rrf_preds
    for tid, label in gold.items():
        if not label.get("gold_spans"):
            continue
        g_pred = graph_preds.get(tid)
        rrf_pred = rrf_by_task.get(tid)
        if g_pred and rrf_pred:
            repo_id = label.get("repo_id", "")
            gold_paths = get_gold_paths(label)
            # RRF already hits gold
            rrf_hit = any(
                match_path(e.get("path", ""), gp, repo_id)
                for e in rrf_pred.get("evidence", [])[:10]
                for gp in gold_paths
            )
            # Graph adds evidence but none is gold
            graph_evidence = g_pred.get("evidence", [])
            if graph_evidence and rrf_hit:
                graph_hit = any(
                    match_path(e.get("path", ""), gp, repo_id)
                    for e in graph_evidence[:10]
                    for gp in gold_paths
                )
                if not graph_hit:
                    graph_no_gold.append(tid)
    clusters["GRAPH_ADDS_NO_GOLD"] = {
        "count": len(graph_no_gold),
        "affected_strategies": ["graph_basic", "rrf_plus_graph"],
        "representative_examples": graph_no_gold[:10],
        "bucket_distribution": _bucket_dist(graph_no_gold, gold, "source_category"),
        "suspected_cause": "Graph impact returns neighbor files that do not contain gold spans",
        "recommended_next_tests": ["Filter graph results by query term overlap", "Score graph evidence by relevance"],
    }

    # 9. HARD_DISTRACTOR_CONFUSION
    hd_confusion = []
    for tid, label in gold.items():
        hd_paths = get_hard_distractor_paths(label)
        if not hd_paths:
            continue
        for strat_name in ["rrf", "bm25"]:
            strat_preds = {p["task_id"]: p for p in all_predictions.get(strat_name, [])}
            pred = strat_preds.get(tid)
            if pred and pred.get("evidence"):
                repo_id = label.get("repo_id", "")
                top_path = pred["evidence"][0].get("path", "")
                for hdp in hd_paths:
                    if match_path(top_path, hdp, repo_id):
                        hd_confusion.append(tid)
                        break
    clusters["HARD_DISTRACTOR_CONFUSION"] = {
        "count": len(set(hd_confusion)),
        "affected_strategies": ["rrf", "bm25", "regex"],
        "representative_examples": list(set(hd_confusion))[:10],
        "bucket_distribution": _bucket_dist(list(set(hd_confusion)), gold, "source_category"),
        "suspected_cause": "Strategies rank hard distractor files above gold files",
        "recommended_next_tests": ["Add hard_distractor penalty scoring", "Cross-reference with must_not_primary"],
    }

    # 10. NEGATIVE_NONEXISTENT_FALSE_PRIMARY
    neg_fp = []
    for tid, label in gold.items():
        if label.get("source_category") != "negative_nonexistent":
            continue
        for strat_name in ["rrf", "bm25", "regex", "symbol"]:
            strat_preds = {p["task_id"]: p for p in all_predictions.get(strat_name, [])}
            pred = strat_preds.get(tid)
            if pred and pred.get("evidence"):
                neg_fp.append(tid)
                break
    clusters["NEGATIVE_NONEXISTENT_FALSE_PRIMARY"] = {
        "count": len(set(neg_fp)),
        "affected_strategies": ["rrf", "bm25", "regex", "symbol"],
        "representative_examples": list(set(neg_fp))[:10],
        "bucket_distribution": _bucket_dist(list(set(neg_fp)), gold, "source_category"),
        "suspected_cause": "Strategies return false primary evidence for queries about nonexistent features",
        "recommended_next_tests": ["Strengthen query noise detection", "Add abstain-on-low-confidence threshold"],
    }

    # 11. STALE_INDEX_LIKE_FALSE_PRIMARY
    stale_fp = []
    for tid, label in gold.items():
        if label.get("source_category") != "stale_index_like":
            continue
        rrf_pred = rrf_preds.get(tid)
        if rrf_pred and rrf_pred.get("evidence"):
            stale_fp.append(tid)
    clusters["STALE_INDEX_LIKE_FALSE_PRIMARY"] = {
        "count": len(stale_fp),
        "affected_strategies": ["rrf", "bm25"],
        "representative_examples": stale_fp[:10],
        "bucket_distribution": _bucket_dist(stale_fp, gold, "source_category"),
        "suspected_cause": "BM25/RRF return stale or renamed results that appear to match but are outdated",
        "recommended_next_tests": ["Add freshness verification to results", "Cross-check with current file state"],
    }

    # 12. TEST_SOURCE_CONFUSION
    test_conf = []
    for tid, label in gold.items():
        if label.get("source_category") != "test_source_confusion":
            continue
        rrf_pred = rrf_preds.get(tid)
        if rrf_pred and rrf_pred.get("evidence"):
            test_conf.append(tid)
    clusters["TEST_SOURCE_CONFUSION"] = {
        "count": len(test_conf),
        "affected_strategies": ["rrf", "bm25", "regex"],
        "representative_examples": test_conf[:10],
        "bucket_distribution": _bucket_dist(test_conf, gold, "source_category"),
        "suspected_cause": "Strategies return test files instead of source implementation files",
        "recommended_next_tests": ["Deprioritize test paths in ranking", "Add test/source path discrimination"],
    }

    # 13. FRONTEND_BACKEND_CONFUSION
    fb_conf = []
    for tid, label in gold.items():
        if label.get("source_category") != "frontend_backend_confusion":
            continue
        rrf_pred = rrf_preds.get(tid)
        if rrf_pred and rrf_pred.get("evidence"):
            fb_conf.append(tid)
    clusters["FRONTEND_BACKEND_CONFUSION"] = {
        "count": len(fb_conf),
        "affected_strategies": ["rrf", "bm25", "regex"],
        "representative_examples": fb_conf[:10],
        "bucket_distribution": _bucket_dist(fb_conf, gold, "source_category"),
        "suspected_cause": "Strategies return frontend code when backend code is the gold target (or vice versa)",
        "recommended_next_tests": ["Add language-aware routing", "Filter by expected implementation layer"],
    }

    # 14. BENCHMARK_ORACLE_SUSPECT
    oracle_suspect = []
    for tid, label in gold.items():
        if label.get("gold_spans"):
            rrf_hit = any(
                e.get("path")
                for e in rrf_preds.get(tid, {}).get("evidence", [])[:10]
            )
            sym_hit = any(
                e.get("path")
                for e in symbol_preds.get(tid, {}).get("evidence", [])[:10]
            )
            if not rrf_hit and not sym_hit:
                oracle_suspect.append(tid)
    clusters["BENCHMARK_ORACLE_SUSPECT"] = {
        "count": len(oracle_suspect),
        "affected_strategies": ["all"],
        "representative_examples": oracle_suspect[:10],
        "bucket_distribution": _bucket_dist(oracle_suspect, gold, "source_category"),
        "suspected_cause": "No strategy retrieves gold for these tasks; oracle/label may be incorrect",
        "recommended_next_tests": ["Human review of gold spans", "Verify query-target alignment"],
    }

    # Ensure all required keys exist
    for key in REQUIRED_FAILURE_CLUSTERS:
        if key not in clusters:
            clusters[key] = {
                "count": 0,
                "affected_strategies": [],
                "representative_examples": [],
                "bucket_distribution": {},
                "suspected_cause": "no instances observed",
                "recommended_next_tests": [],
            }

    return clusters


def _bucket_dist(task_ids: list[str], gold: dict[str, dict], bucket_key: str) -> dict[str, int]:
    dist: dict[str, int] = defaultdict(int)
    for tid in task_ids:
        label = gold.get(tid, {})
        val = label.get(bucket_key, "unknown")
        if isinstance(val, list):
            val = ",".join(str(v) for v in val) if val else "none"
        else:
            val = str(val)
        dist[val] += 1
    return dict(sorted(dist.items()))


# ── Bucket regressions ────────────────────────────────────────────────


def compute_bucket_regressions(
    all_predictions: dict[str, list[dict]],
    gold: dict[str, dict],
    baseline_strategy: str = "rrf",
) -> dict[str, Any]:
    """Compare candidate/guard/composite vs RRF baseline per bucket."""
    baseline_preds = {p["task_id"]: p for p in all_predictions.get(baseline_strategy, [])}
    bucket_keys = ["source_category", "expected_behavior", "oracle_type", "repo_id", "risk_tags"]
    total_regressions = 0
    strategies_with_regression: set[str] = set()
    worst_buckets: list[dict[str, Any]] = []
    regression_details: list[dict[str, Any]] = []

    candidate_strategies = [s for s in ALL_IMPLEMENTED_STRATEGIES if s != baseline_strategy]

    for strategy in candidate_strategies:
        strategy_preds = {p["task_id"]: p for p in all_predictions.get(strategy, [])}
        for bucket_key in bucket_keys:
            # Build buckets
            buckets: dict[str, list[str]] = defaultdict(list)
            for tid, label in gold.items():
                val = label.get(bucket_key, "unknown")
                if isinstance(val, list):
                    val = ",".join(str(v) for v in val) if val else "none"
                else:
                    val = str(val)
                buckets[val].append(tid)

            for bucket_val, task_ids in buckets.items():
                bucket_gold = {tid: gold[tid] for tid in task_ids}
                non_neg = {tid: g for tid, g in bucket_gold.items() if g.get("gold_spans")}
                neg = {tid: g for tid, g in bucket_gold.items() if not g.get("gold_spans")}

                if len(task_ids) < 5:
                    continue

                baseline_bucket = [baseline_preds.get(tid, {"evidence": []}) for tid in task_ids]
                strategy_bucket = [strategy_preds.get(tid, {"evidence": []}) for tid in task_ids]

                # Check regression types
                # 1. Recall drop
                if non_neg:
                    base_recall = file_recall_at_k(baseline_bucket, non_neg, 5)
                    strat_recall = file_recall_at_k(strategy_bucket, non_neg, 5)
                    if strat_recall < base_recall - 0.05:
                        total_regressions += 1
                        strategies_with_regression.add(strategy)
                        detail = {
                            "strategy": strategy,
                            "bucket_key": bucket_key,
                            "bucket_value": bucket_val,
                            "regression_type": "recall_drop",
                            "baseline_FileRecall@5": round(base_recall, 4),
                            "strategy_FileRecall@5": round(strat_recall, 4),
                        }
                        regression_details.append(detail)
                        worst_buckets.append(detail)

                # 2. False-primary increase
                base_fpr = false_primary_on_negative_rate(baseline_bucket, bucket_gold)
                strat_fpr = false_primary_on_negative_rate(strategy_bucket, bucket_gold)
                if strat_fpr > base_fpr + 0.05:
                    total_regressions += 1
                    strategies_with_regression.add(strategy)
                    detail = {
                        "strategy": strategy,
                        "bucket_key": bucket_key,
                        "bucket_value": bucket_val,
                        "regression_type": "false_primary_increase",
                        "baseline_fpr": round(base_fpr, 4),
                        "strategy_fpr": round(strat_fpr, 4),
                    }
                    regression_details.append(detail)
                    worst_buckets.append(detail)

                # 3. No-gold-nonempty increase
                if neg:
                    base_ngne = no_gold_nonempty_rate_at_k(baseline_bucket, neg, 10)
                    strat_ngne = no_gold_nonempty_rate_at_k(strategy_bucket, neg, 10)
                    if strat_ngne > base_ngne + 0.05:
                        total_regressions += 1
                        strategies_with_regression.add(strategy)
                        detail = {
                            "strategy": strategy,
                            "bucket_key": bucket_key,
                            "bucket_value": bucket_val,
                            "regression_type": "no_gold_nonempty_increase",
                            "baseline": round(base_ngne, 4),
                            "strategy_value": round(strat_ngne, 4),
                        }
                        regression_details.append(detail)
                        worst_buckets.append(detail)

                # 4. Must-not-primary increase
                base_mnp = must_not_primary_violation_rate(baseline_bucket, bucket_gold)
                strat_mnp = must_not_primary_violation_rate(strategy_bucket, bucket_gold)
                if strat_mnp > base_mnp + 0.05:
                    total_regressions += 1
                    strategies_with_regression.add(strategy)
                    detail = {
                        "strategy": strategy,
                        "bucket_key": bucket_key,
                        "bucket_value": bucket_val,
                        "regression_type": "must_not_primary_increase",
                        "baseline": round(base_mnp, 4),
                        "strategy_value": round(strat_mnp, 4),
                    }
                    regression_details.append(detail)
                    worst_buckets.append(detail)

                # 5. Abstain spike on primary_evidence
                pe_tasks = {tid: g for tid, g in bucket_gold.items() if g.get("expected_behavior") == "primary_evidence"}
                if pe_tasks:
                    base_abstain = sum(1 for tid in pe_tasks if not baseline_preds.get(tid, {}).get("evidence")) / len(pe_tasks)
                    strat_abstain = sum(1 for tid in pe_tasks if not strategy_preds.get(tid, {}).get("evidence")) / len(pe_tasks)
                    if strat_abstain > base_abstain + 0.10:
                        total_regressions += 1
                        strategies_with_regression.add(strategy)
                        detail = {
                            "strategy": strategy,
                            "bucket_key": bucket_key,
                            "bucket_value": bucket_val,
                            "regression_type": "abstain_spike_on_primary_evidence",
                            "baseline_abstain": round(base_abstain, 4),
                            "strategy_abstain": round(strat_abstain, 4),
                        }
                        regression_details.append(detail)
                        worst_buckets.append(detail)

    def regression_delta(detail: dict[str, Any]) -> float:
        if "baseline_FileRecall@5" in detail:
            return abs(detail.get("baseline_FileRecall@5", 0.0) - detail.get("strategy_FileRecall@5", 0.0))
        if "baseline_fpr" in detail:
            return abs(detail.get("baseline_fpr", 0.0) - detail.get("strategy_fpr", 0.0))
        if "baseline_abstain" in detail:
            return abs(detail.get("baseline_abstain", 0.0) - detail.get("strategy_abstain", 0.0))
        return abs(detail.get("baseline", 0.0) - detail.get("strategy_value", 0.0))

    worst_buckets.sort(key=regression_delta, reverse=True)

    return {
        "total_bucket_regressions": total_regressions,
        "strategies_with_bucket_regression": sorted(strategies_with_regression),
        "worst_buckets": worst_buckets[:20],
        "regression_details_count": len(regression_details),
    }


# ── Artifact safety scans ─────────────────────────────────────────────


def scan_artifacts_for_private_fields(
    runs_dir: Path, strategies: list[str]
) -> list[str]:
    issues: list[str] = []
    for strategy in strategies:
        for ftype in ["predictions", "evidence", "rejections", "trace"]:
            path = runs_dir / f"r29-r26-stress-{strategy}-{ftype}.jsonl"
            if not path.exists():
                continue
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                for field in PRIVATE_FIELD_DENYLIST:
                    if f'"{field}"' in line:
                        issues.append(
                            f"CRITICAL: private field '{field}' found in {path.name} "
                            f"line {line_no}"
                        )
    return issues


def scan_artifacts_for_canary_tokens(
    runs_dir: Path, strategies: list[str]
) -> list[str]:
    issues: list[str] = []
    for strategy in strategies:
        for ftype in ["predictions", "evidence", "rejections", "trace"]:
            path = runs_dir / f"r29-r26-stress-{strategy}-{ftype}.jsonl"
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            for token in CANARY_TOKENS:
                if token in content:
                    issues.append(
                        f"CRITICAL: canary token '{token}' found in {path.name}"
                    )
    return issues


def verify_artifact_manifest(manifest: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    checked = 0
    for strategy, artifacts in manifest.items():
        if not isinstance(artifacts, dict):
            continue
        for artifact_kind, info in artifacts.items():
            checked += 1
            if not isinstance(info, dict):
                continue
            raw_path = info.get("path", "")
            if not raw_path:
                continue
            path = Path(raw_path)
            if not path.exists():
                issues.append(f"CRITICAL: artifact manifest {strategy}.{artifact_kind} missing file {path}")
                continue
            actual = artifact_provenance(path)
            for field in ["sha256", "bytes", "jsonl_lines"]:
                if info.get(field) != actual.get(field):
                    issues.append(
                        f"CRITICAL: artifact manifest {strategy}.{artifact_kind} {field} mismatch "
                        f"expected={info.get(field)} actual={actual.get(field)}"
                    )
    return {"checked": checked, "passed": not issues}, issues


# ── R26 provenance validation ─────────────────────────────────────────


def validate_r26_provenance(
    fixtures_dir: Path,
) -> tuple[dict[str, Any], list[str]]:
    """Validate public R26 source artifacts before run.

    Deliberately does not read or hash labels. Label artifact validation happens
    only after the run phase has completed and all run artifacts/citations are
    written. This preserves the R29 runner/scorer boundary.
    """
    issues: list[str] = []
    provenance: dict[str, Any] = {}

    # Safety checks
    safety_path = fixtures_dir / "safety_checks.json"
    if not safety_path.exists():
        issues.append("CRITICAL: R26 safety_checks.json not found")
    else:
        try:
            safety = json.loads(safety_path.read_text(encoding="utf-8"))
            provenance["safety_checks_sha256"] = file_sha256(safety_path)
            if not safety.get("passed", False):
                issues.append("CRITICAL: R26 safety_checks.passed != true")
            provenance["safety_checks_passed"] = safety.get("passed", False)
        except (json.JSONDecodeError, OSError) as e:
            issues.append(f"CRITICAL: R26 safety_checks.json parse error: {e}")

    # Summary
    summary_path = fixtures_dir / "summary.json"
    if not summary_path.exists():
        issues.append("CRITICAL: R26 summary.json not found")
    else:
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            provenance["summary_sha256"] = file_sha256(summary_path)
            task_count = summary.get("total_tasks", 0)
            label_count = summary.get("total_labels", 0)
            if task_count != 1100:
                issues.append(f"CRITICAL: R26 summary.total_tasks={task_count} != 1100")
            provenance["task_count"] = task_count
            provenance["declared_label_count_deferred_to_score_phase"] = label_count
        except (json.JSONDecodeError, OSError) as e:
            issues.append(f"CRITICAL: R26 summary.json parse error: {e}")

    # Tasks SHA
    tasks_path = fixtures_dir / "tasks" / "auto_stress.jsonl"
    if tasks_path.exists():
        provenance["tasks_sha256"] = file_sha256(tasks_path)
    else:
        issues.append("CRITICAL: R26 tasks/auto_stress.jsonl not found")

    # Manifest checks
    manifest_path = fixtures_dir / "dataset_manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            provenance["manifest_sha256"] = file_sha256(manifest_path)
            if manifest.get("not_promotion_evidence") != True:
                issues.append("CRITICAL: R26 manifest not_promotion_evidence != true")
            if manifest.get("core_changes") != False:
                issues.append("CRITICAL: R26 manifest core_changes != false")
            if manifest.get("remote_calls", -1) != 0:
                issues.append(f"CRITICAL: R26 manifest remote_calls={manifest.get('remote_calls')} != 0")
            if manifest.get("dense_or_llm_claims") != False:
                issues.append("CRITICAL: R26 manifest dense_or_llm_claims != false")

            # Check task/label SHA match manifest if present
            gen_info = manifest.get("generation_info", {})
            expected_tasks_sha = gen_info.get("tasks_sha256", "")
            if expected_tasks_sha and tasks_path.exists():
                actual = file_sha256(tasks_path)
                if actual != expected_tasks_sha:
                    issues.append("CRITICAL: R26 tasks SHA mismatch with manifest")
        except (json.JSONDecodeError, OSError) as e:
            issues.append(f"CRITICAL: R26 dataset_manifest.json parse error: {e}")

    # Repos lock SHA
    repos_lock_path = fixtures_dir / "repos.lock.jsonl"
    if repos_lock_path.exists():
        provenance["repos_lock_sha256"] = file_sha256(repos_lock_path)
    else:
        issues.append("CRITICAL: R26 repos.lock.jsonl not found")

    provenance["r26_source_artifacts_validated"] = len(issues) == 0
    return provenance, issues


def validate_r26_labels_score_phase(
    fixtures_dir: Path,
    labels_list: list[dict[str, Any]],
    task_ids: set[str],
    r26_provenance: dict[str, Any],
    allow_extra_labels: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    """Validate R26 labels only after run artifacts are written."""
    issues: list[str] = []
    validation: dict[str, Any] = {
        "labels_loaded_after_run": True,
        "allow_extra_labels_for_limited_smoke": allow_extra_labels,
    }
    labels_path = fixtures_dir / "labels" / "auto_stress.jsonl"
    manifest_path = fixtures_dir / "dataset_manifest.json"

    if not labels_path.exists():
        issues.append("CRITICAL: R26 labels/auto_stress.jsonl not found in score phase")
        return validation, issues

    validation["labels_sha256"] = file_sha256(labels_path)
    validation["labels_count"] = len(labels_list)
    declared_label_count = r26_provenance.get("declared_label_count_deferred_to_score_phase")
    if declared_label_count != len(labels_list):
        issues.append(
            f"CRITICAL: R26 label count mismatch in score phase "
            f"(declared={declared_label_count}, loaded={len(labels_list)})"
        )
    if len(labels_list) != 1100:
        issues.append(f"CRITICAL: R26 labels count {len(labels_list)} != 1100")

    labels_by_id: dict[str, dict[str, Any]] = {}
    duplicate_ids: set[str] = set()
    for label in labels_list:
        tid = label.get("test_id") or label.get("task_id")
        if not isinstance(tid, str) or not tid:
            issues.append("CRITICAL: R26 label missing non-empty test_id/task_id")
            continue
        if tid in labels_by_id:
            duplicate_ids.add(tid)
        labels_by_id[tid] = label

    if duplicate_ids:
        issues.append(f"CRITICAL: duplicate R26 label ids in score phase: {sorted(duplicate_ids)[:10]}")
    missing_labels = sorted(task_ids - set(labels_by_id))
    extra_labels = sorted(set(labels_by_id) - task_ids)
    if missing_labels:
        issues.append(f"CRITICAL: labels missing for run tasks: {missing_labels[:10]}")
    if extra_labels and not allow_extra_labels:
        issues.append(f"CRITICAL: labels exist for tasks not run: {extra_labels[:10]}")
    validation["extra_labels_ignored_for_limited_smoke"] = len(extra_labels) if allow_extra_labels else 0

    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            expected_labels_sha = manifest.get("generation_info", {}).get("labels_sha256", "")
            if not expected_labels_sha:
                issues.append("CRITICAL: R26 manifest missing generation_info.labels_sha256")
            elif expected_labels_sha != validation["labels_sha256"]:
                issues.append("CRITICAL: R26 labels SHA mismatch with manifest in score phase")
        except (json.JSONDecodeError, OSError) as e:
            issues.append(f"CRITICAL: R26 dataset_manifest.json score-phase parse error: {e}")
    else:
        issues.append("CRITICAL: R26 dataset_manifest.json not found in score phase")

    validation["passed"] = len(issues) == 0
    return validation, issues


# ── Main ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="R29 R26 Auto-Stress Strategy Matrix Runner/Scorer"
    )
    parser.add_argument("--workspace", default=".", help="Workspace root directory")
    parser.add_argument("--fixtures", default="fixtures/r26_auto_stress", help="Fixtures directory relative to workspace")
    parser.add_argument("--openlocus", default="target/debug/openlocus", help="Path to openlocus binary")
    parser.add_argument("--out", default="runs/r29-r26-stress-matrix-report.json", help="Output path for JSON report")
    parser.add_argument("--strategies", default=None, help="Comma-separated strategies; default all implemented")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tasks (smoke test)")
    args = parser.parse_args()

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

    for s in strategies:
        if s not in ALL_IMPLEMENTED_STRATEGIES:
            print(f"ERROR: Unknown strategy '{s}'. Available: {ALL_IMPLEMENTED_STRATEGIES}", file=sys.stderr)
            sys.exit(1)

    if not fixtures_dir.exists():
        print(f"ERROR: Fixtures directory not found: {fixtures_dir}", file=sys.stderr)
        sys.exit(1)

    # ── R26 provenance validation ─────────────────────────────────────
    r26_provenance, r26_issues = validate_r26_provenance(fixtures_dir)
    safety_issues: list[str] = list(r26_issues)
    if r26_issues:
        print("ERROR: R26 public provenance validation failed before run", file=sys.stderr)
        for issue in r26_issues[:20]:
            print(f"  - {issue}", file=sys.stderr)
        sys.exit(1)

    # ── Load fixture data (RUN phase: tasks + repo lock only) ──────────

    repos: dict[str, dict] = {}
    lock_path = fixtures_dir / "repos.lock.jsonl"
    if not lock_path.exists():
        print(f"ERROR: repos.lock.jsonl not found: {lock_path}", file=sys.stderr)
        sys.exit(1)
    for entry in load_jsonl(lock_path):
        repos[entry["repo_id"]] = entry

    lock_issues, lock_info = validate_repo_lock(repos)
    safety_issues.extend(lock_issues)
    if lock_issues:
        print("ERROR: R26 repo lock validation failed before run", file=sys.stderr)
        for issue in lock_issues[:20]:
            print(f"  - {issue}", file=sys.stderr)
        sys.exit(1)
    for info in lock_info:
        print(f"  INFO: {info}")

    # Load tasks (public only, R26 uses test_id)
    tasks_path = fixtures_dir / "tasks" / "auto_stress.jsonl"
    if not tasks_path.exists():
        print(f"ERROR: tasks file not found: {tasks_path}", file=sys.stderr)
        sys.exit(1)
    tasks = load_jsonl(tasks_path)

    if args.limit:
        tasks = tasks[: args.limit]
        print(f"  --limit {args.limit}: using {len(tasks)} tasks")

    # Normalize task_id field: R26 uses test_id, runner uses task_id internally
    for task in tasks:
        if "task_id" not in task and "test_id" in task:
            task["task_id"] = task["test_id"]

    # Verify no gold info in tasks
    for task in tasks:
        for field in ["gold_spans", "gold_paths", "gold_lines", "hard_negatives", "hard_distractors",
                       "expected_behavior", "query_category", "risk_tags", "must_not_primary",
                       "source_category", "risk_public", "intent_guess", "oracle_type",
                       "why_this_is_hard", "which_strategy_it_targets"]:
            if field in task:
                safety_issues.append(f"LEAK: task {task.get('task_id', task.get('test_id', '?'))} contains {field}")
    leak_issues = [issue for issue in safety_issues if issue.startswith("LEAK:")]
    if leak_issues:
        print("ERROR: R26 public task schema contains private fields", file=sys.stderr)
        for issue in leak_issues[:20]:
            print(f"  - {issue}", file=sys.stderr)
        sys.exit(1)

    # Load dataset manifest
    manifest_path = fixtures_dir / "dataset_manifest.json"
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    print(f"R29 R26 Stress Matrix: {len(tasks)} tasks, {len(repos)} repos, {len(strategies)} strategies")
    print(f"  Phase 1: RUN (public tasks only, no labels)", flush=True)

    # ── Phase 1: RUN ──────────────────────────────────────────────────

    # Create isolated roots
    isolated_roots: dict[str, Path] = {}
    for repo_id, entry in repos.items():
        isolated, iso_issues = create_isolated_root(repo_id, entry)
        isolated_roots[repo_id] = isolated
        safety_issues.extend(iso_issues)

    # Canary check
    canary_summary, canary_issues = check_canary_retrieval(openlocus_path, isolated_roots)
    safety_issues.extend(canary_issues)

    all_predictions: dict[str, list[dict]] = {}
    all_rejections: dict[str, list[dict]] = {}
    all_traces: dict[str, list[dict]] = {}
    all_evidence: dict[str, list[dict]] = {}
    citation_summaries: dict[str, dict[str, Any]] = {}

    base_preds_by_task: dict[str, dict[str, dict]] = {}

    # ── Run base strategies ──────────────────────────────────────────
    for strategy in strategies:
        if strategy not in BASE_STRATEGIES:
            continue
        print(f"  Running base strategy: {strategy}", flush=True)
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
            result = run_query(openlocus_path, strategy, query, cwd)
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
            if len(predictions) % 100 == 0 or len(predictions) == len(tasks):
                print(
                    f"    {strategy}: {len(predictions)}/{len(tasks)} tasks",
                    flush=True,
                )

        # Validate citations before cleanup
        forbidden_issues = check_predictions_for_forbidden_paths(predictions, strategy)
        safety_issues.extend(forbidden_issues)

        citation_summary, citation_issues = validate_predictions_with_rust(
            openlocus_path, strategy, predictions, isolated_roots
        )
        citation_summaries[strategy] = citation_summary
        safety_issues.extend(citation_issues)

        all_predictions[strategy] = predictions
        all_evidence[strategy] = [
            {"task_id": p["task_id"], "repo_id": p.get("repo_id", ""), "evidence": p["evidence"]}
            for p in predictions
        ]
        all_rejections[strategy] = build_rejections(predictions, strategy)
        all_traces[strategy] = build_trace(predictions, strategy)

    # ── Run R24/R25-style strategies ──────────────────────────────────

    # dense_mock: build + search
    if "dense_mock" in strategies:
        print(f"  Running dense_mock (build + search)...", flush=True)
        dense_build_results: dict[str, dict] = {}
        for repo_id, isolated in isolated_roots.items():
            build_result = run_dense_build(openlocus_path, str(isolated))
            dense_build_results[repo_id] = build_result
            if not build_result["success"]:
                safety_issues.append(
                    f"CRITICAL: dense build failed for repo {repo_id}: "
                    f"{build_result.get('stderr', '')[:200]}"
                )
            # Preserve embeddings for search
            clean_runtime_artifacts(isolated, preserve_dense=True)
            print(
                f"    dense_mock build: {repo_id} records={build_result.get('record_count', 0)} success={build_result.get('success')}",
                flush=True,
            )

        dense_predictions: list[dict] = []
        for task in tasks:
            query = task["query"]
            task_id = task["task_id"]
            repo_id = task.get("repo_id", "")
            if repo_id not in isolated_roots:
                dense_predictions.append({
                    "task_id": task_id, "repo_id": repo_id, "query": query,
                    "strategy": "dense_mock", "evidence": [],
                    "latency_ms": 0, "returncode": -1,
                })
                continue
            cwd = str(isolated_roots[repo_id])
            evidence = run_dense_search(openlocus_path, query, cwd)
            clean_runtime_artifacts(isolated_roots[repo_id], preserve_dense=True)
            dense_predictions.append({
                "task_id": task_id, "repo_id": repo_id, "query": query,
                "strategy": "dense_mock", "evidence": evidence,
                "latency_ms": 0, "returncode": 0,
            })
            base_preds_by_task.setdefault(task_id, {})["dense_mock"] = dense_predictions[-1]
            if len(dense_predictions) % 100 == 0 or len(dense_predictions) == len(tasks):
                print(
                    f"    dense_mock search: {len(dense_predictions)}/{len(tasks)} tasks",
                    flush=True,
                )

        forbidden_issues = check_predictions_for_forbidden_paths(dense_predictions, "dense_mock")
        safety_issues.extend(forbidden_issues)
        citation_summary, citation_issues = validate_predictions_with_rust(
            openlocus_path, "dense_mock", dense_predictions, isolated_roots
        )
        citation_summaries["dense_mock"] = citation_summary
        safety_issues.extend(citation_issues)
        all_predictions["dense_mock"] = dense_predictions
        all_evidence["dense_mock"] = [
            {"task_id": p["task_id"], "repo_id": p.get("repo_id", ""), "evidence": p["evidence"]}
            for p in dense_predictions
        ]
        all_rejections["dense_mock"] = build_rejections(dense_predictions, "dense_mock")
        all_traces["dense_mock"] = build_trace(dense_predictions, "dense_mock")

    # graph_basic: derive top path → impact
    if "graph_basic" in strategies:
        print(f"  Running graph_basic (impact --depth 1)...", flush=True)
        graph_predictions: list[dict] = []
        for task in tasks:
            query = task["query"]
            task_id = task["task_id"]
            repo_id = task.get("repo_id", "")
            if repo_id not in isolated_roots:
                graph_predictions.append({
                    "task_id": task_id, "repo_id": repo_id, "query": query,
                    "strategy": "graph_basic", "evidence": [],
                    "latency_ms": 0, "returncode": -1,
                })
                continue
            cwd = str(isolated_roots[repo_id])
            top_path, method = derive_top_path(openlocus_path, query, cwd)
            clean_runtime_artifacts(isolated_roots[repo_id])
            evidence = []
            if top_path:
                evidence = run_graph_impact(openlocus_path, top_path, cwd)
                clean_runtime_artifacts(isolated_roots[repo_id])
            graph_predictions.append({
                "task_id": task_id, "repo_id": repo_id, "query": query,
                "strategy": "graph_basic", "evidence": evidence,
                "latency_ms": 0, "returncode": 0,
            })
            base_preds_by_task.setdefault(task_id, {})["graph_basic"] = graph_predictions[-1]
            if len(graph_predictions) % 100 == 0 or len(graph_predictions) == len(tasks):
                print(
                    f"    graph_basic: {len(graph_predictions)}/{len(tasks)} tasks",
                    flush=True,
                )

        forbidden_issues = check_predictions_for_forbidden_paths(graph_predictions, "graph_basic")
        safety_issues.extend(forbidden_issues)
        citation_summary, citation_issues = validate_predictions_with_rust(
            openlocus_path, "graph_basic", graph_predictions, isolated_roots
        )
        citation_summaries["graph_basic"] = citation_summary
        safety_issues.extend(citation_issues)
        all_predictions["graph_basic"] = graph_predictions
        all_evidence["graph_basic"] = [
            {"task_id": p["task_id"], "repo_id": p.get("repo_id", ""), "evidence": p["evidence"]}
            for p in graph_predictions
        ]
        all_rejections["graph_basic"] = build_rejections(graph_predictions, "graph_basic")
        all_traces["graph_basic"] = build_trace(graph_predictions, "graph_basic")

    # ── Build composite strategies from base predictions ───────────────
    for strategy in strategies:
        if strategy in COMPOSITE_STRATEGIES:
            print(f"  Building composite strategy: {strategy}", flush=True)
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

    # ── Build R24/R25 composite strategies ────────────────────────────
    rrf_by_task = base_preds_by_task  # already has rrf

    if "dense_mock_plus_rrf" in strategies and "dense_mock" in all_predictions and "rrf" in all_predictions:
        print(f"  Building dense_mock_plus_rrf...", flush=True)
        dm_preds = {p["task_id"]: p for p in all_predictions["dense_mock"]}
        rrf_preds = {p["task_id"]: p for p in all_predictions["rrf"]}
        predictions = []
        for task in tasks:
            task_id = task["task_id"]
            fused = rrf_fuse_predictions(dm_preds.get(task_id, {}), rrf_preds.get(task_id, {}))
            predictions.append({
                "task_id": task_id, "repo_id": task.get("repo_id", ""),
                "query": task.get("query", ""), "strategy": "dense_mock_plus_rrf",
                "evidence": fused, "latency_ms": 0, "returncode": 0,
            })
        all_predictions["dense_mock_plus_rrf"] = predictions
        all_evidence["dense_mock_plus_rrf"] = [
            {"task_id": p["task_id"], "repo_id": p.get("repo_id", ""), "evidence": p["evidence"]}
            for p in predictions
        ]
        all_rejections["dense_mock_plus_rrf"] = build_rejections(predictions, "dense_mock_plus_rrf")
        all_traces["dense_mock_plus_rrf"] = build_trace(predictions, "dense_mock_plus_rrf")

    if "rrf_plus_graph" in strategies and "graph_basic" in all_predictions and "rrf" in all_predictions:
        print(f"  Building rrf_plus_graph...", flush=True)
        graph_preds = {p["task_id"]: p for p in all_predictions["graph_basic"]}
        rrf_preds = {p["task_id"]: p for p in all_predictions["rrf"]}
        predictions = []
        for task in tasks:
            task_id = task["task_id"]
            fused = rrf_fuse_predictions(graph_preds.get(task_id, {}), rrf_preds.get(task_id, {}))
            predictions.append({
                "task_id": task_id, "repo_id": task.get("repo_id", ""),
                "query": task.get("query", ""), "strategy": "rrf_plus_graph",
                "evidence": fused, "latency_ms": 0, "returncode": 0,
            })
        all_predictions["rrf_plus_graph"] = predictions
        all_evidence["rrf_plus_graph"] = [
            {"task_id": p["task_id"], "repo_id": p.get("repo_id", ""), "evidence": p["evidence"]}
            for p in predictions
        ]
        all_rejections["rrf_plus_graph"] = build_rejections(predictions, "rrf_plus_graph")
        all_traces["rrf_plus_graph"] = build_trace(predictions, "rrf_plus_graph")

    if "rrf_plus_dense_mock" in strategies and "dense_mock" in all_predictions and "rrf" in all_predictions:
        print(f"  Building rrf_plus_dense_mock...", flush=True)
        dm_preds = {p["task_id"]: p for p in all_predictions["dense_mock"]}
        rrf_preds = {p["task_id"]: p for p in all_predictions["rrf"]}
        predictions = []
        for task in tasks:
            task_id = task["task_id"]
            fused = rrf_fuse_predictions(dm_preds.get(task_id, {}), rrf_preds.get(task_id, {}))
            predictions.append({
                "task_id": task_id, "repo_id": task.get("repo_id", ""),
                "query": task.get("query", ""), "strategy": "rrf_plus_dense_mock",
                "evidence": fused, "latency_ms": 0, "returncode": 0,
            })
        all_predictions["rrf_plus_dense_mock"] = predictions
        all_evidence["rrf_plus_dense_mock"] = [
            {"task_id": p["task_id"], "repo_id": p.get("repo_id", ""), "evidence": p["evidence"]}
            for p in predictions
        ]
        all_rejections["rrf_plus_dense_mock"] = build_rejections(predictions, "rrf_plus_dense_mock")
        all_traces["rrf_plus_dense_mock"] = build_trace(predictions, "rrf_plus_dense_mock")

    if "rrf_plus_dense_mock_plus_graph" in strategies and "dense_mock" in all_predictions and "graph_basic" in all_predictions and "rrf" in all_predictions:
        print(f"  Building rrf_plus_dense_mock_plus_graph...", flush=True)
        dm_preds = {p["task_id"]: p for p in all_predictions["dense_mock"]}
        graph_preds = {p["task_id"]: p for p in all_predictions["graph_basic"]}
        rrf_preds = {p["task_id"]: p for p in all_predictions["rrf"]}
        predictions = []
        for task in tasks:
            task_id = task["task_id"]
            fused = rrf_fuse_three_predictions(
                dm_preds.get(task_id, {}), graph_preds.get(task_id, {}), rrf_preds.get(task_id, {})
            )
            predictions.append({
                "task_id": task_id, "repo_id": task.get("repo_id", ""),
                "query": task.get("query", ""), "strategy": "rrf_plus_dense_mock_plus_graph",
                "evidence": fused, "latency_ms": 0, "returncode": 0,
            })
        all_predictions["rrf_plus_dense_mock_plus_graph"] = predictions
        all_evidence["rrf_plus_dense_mock_plus_graph"] = [
            {"task_id": p["task_id"], "repo_id": p.get("repo_id", ""), "evidence": p["evidence"]}
            for p in predictions
        ]
        all_rejections["rrf_plus_dense_mock_plus_graph"] = build_rejections(predictions, "rrf_plus_dense_mock_plus_graph")
        all_traces["rrf_plus_dense_mock_plus_graph"] = build_trace(predictions, "rrf_plus_dense_mock_plus_graph")

    # ── Validate citations for ALL strategies before cleanup ────────────
    for strategy in strategies:
        if strategy in BASE_STRATEGIES:
            continue  # Already validated above
        if strategy in citation_summaries:
            continue  # Already validated (dense_mock, graph_basic)
        predictions = all_predictions.get(strategy, [])
        if not predictions:
            citation_summaries[strategy] = {
                "citation_validity": 1.0,
                "citation_valid_count": 0,
                "citation_total_count": 0,
                "citation_invalid_count": 0,
                "citation_validator_invocations": 0,
                "citation_validation_mode": "fail_closed_hash_range_path",
                "citation_hash_checked": False,
                "citation_not_applicable": True,
                "citation_inherited_from_base": True,
                "citation_validated_by_rust": True,
            }
            continue

        # Validate composite/guard strategies
        forbidden_issues = check_predictions_for_forbidden_paths(predictions, strategy)
        safety_issues.extend(forbidden_issues)

        citation_summary, citation_issues = validate_predictions_with_rust(
            openlocus_path, strategy, predictions, isolated_roots
        )
        citation_summary["citation_inherited_from_base"] = True
        citation_summary["citation_validated_by_rust"] = True
        if citation_summary.get("citation_total_count", 0) == 0:
            citation_summary["citation_not_applicable"] = True
            citation_summary["citation_hash_checked"] = False
        else:
            citation_summary["citation_not_applicable"] = False
        citation_summaries[strategy] = citation_summary
        safety_issues.extend(citation_issues)

    # ── Write R29-owned artifacts ──────────────────────────────────────
    runs_dir = workspace / "runs"
    artifact_manifest: dict[str, Any] = {}
    for strategy in strategies:
        pred_path = runs_dir / f"r29-r26-stress-{strategy}-predictions.jsonl"
        evid_path = runs_dir / f"r29-r26-stress-{strategy}-evidence.jsonl"
        rej_path = runs_dir / f"r29-r26-stress-{strategy}-rejections.jsonl"
        trace_path = runs_dir / f"r29-r26-stress-{strategy}-trace.jsonl"

        write_jsonl(pred_path, all_predictions.get(strategy, []))
        write_jsonl(evid_path, all_evidence.get(strategy, []))
        write_jsonl(rej_path, all_rejections.get(strategy, []))
        write_jsonl(trace_path, all_traces.get(strategy, []))

        artifact_manifest[strategy] = {
            "predictions": artifact_provenance(pred_path),
            "evidence": artifact_provenance(evid_path),
            "rejections": artifact_provenance(rej_path),
            "trace": artifact_provenance(trace_path),
        }

    manifest_path_out = runs_dir / "r29-r26-stress-artifacts-manifest.json"
    manifest_path_out.parent.mkdir(parents=True, exist_ok=True)
    manifest_path_out.write_text(
        json.dumps(artifact_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # Verify artifact manifest
    manifest_verify, manifest_issues = verify_artifact_manifest(artifact_manifest)
    safety_issues.extend(manifest_issues)

    # Cleanup isolated roots (after citation validation)
    for isolated in isolated_roots.values():
        shutil.rmtree(isolated, ignore_errors=True)

    # ── Phase 2: SCORE ────────────────────────────────────────────────

    print(f"  Phase 2: SCORE (labels only, no CLI)", flush=True)

    # NOW load labels (after all run artifacts written + citations validated + manifest written)
    labels_path = fixtures_dir / "labels" / "auto_stress.jsonl"
    if not labels_path.exists():
        print(f"ERROR: labels file not found: {labels_path}", file=sys.stderr)
        sys.exit(1)
    labels_list = load_jsonl(labels_path)

    # Normalize label test_id → task_id
    for label in labels_list:
        if "task_id" not in label and "test_id" in label:
            label["task_id"] = label["test_id"]

    task_ids = {t["task_id"] for t in tasks}
    label_validation, label_validation_issues = validate_r26_labels_score_phase(
        fixtures_dir, labels_list, task_ids, r26_provenance,
        allow_extra_labels=args.limit is not None,
    )
    safety_issues.extend(label_validation_issues)
    if label_validation_issues:
        print("ERROR: R26 label validation failed in score phase", file=sys.stderr)
        for issue in label_validation_issues[:20]:
            print(f"  - {issue}", file=sys.stderr)
        sys.exit(1)

    gold = {l["task_id"]: l for l in labels_list}

    # Filter gold to only tasks we ran
    gold = {tid: g for tid, g in gold.items() if tid in task_ids}

    # Score all strategies
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

    # Safety gates
    critical_issues: list[str] = []
    warning_issues: list[str] = []
    for issue in safety_issues:
        if issue.startswith("CRITICAL:") or issue.startswith("LEAK:"):
            critical_issues.append(issue)
        elif issue.startswith("WARNING:"):
            warning_issues.append(issue)
        else:
            critical_issues.append(issue)

    for strategy, metrics in all_metrics.items():
        cit_total = metrics.get("citation_total_count", 0)
        if cit_total > 0 and metrics.get("citation_validity") != 1.0:
            critical_issues.append(
                f"CRITICAL: {strategy} citation_validity={metrics.get('citation_validity')} != 1.0"
            )

    # Artifact safety scans
    runs_dir = workspace / "runs"
    private_field_issues = scan_artifacts_for_private_fields(runs_dir, strategies)
    canary_token_issues = scan_artifacts_for_canary_tokens(runs_dir, strategies)
    if private_field_issues:
        critical_issues.extend(private_field_issues)
    if canary_token_issues:
        critical_issues.extend(canary_token_issues)

    # Bucket metrics
    bucket_metrics: dict[str, dict[str, dict[str, Any]]] = {}
    for strategy in strategies:
        predictions = all_predictions.get(strategy, [])
        citation_summary = citation_summaries.get(strategy, {})
        for bucket_key in ["source_category", "expected_behavior", "oracle_type", "repo_id", "risk_tags"]:
            bm = compute_bucket_metrics(predictions, gold, citation_summary, strategy, bucket_key)
            bucket_metrics.setdefault(strategy, {})[bucket_key] = bm

    # Failure clusters
    failure_clusters = compute_failure_clusters(all_predictions, gold)

    # Span contribution analysis (graph/dense/composites vs fresh RRF baseline)
    span_contributions: dict[str, Any] = {}
    rrf_baseline = all_predictions.get("rrf", [])
    for strategy in R24_R25_STYLE_STRATEGIES:
        if strategy == "rrf":
            continue
        preds = all_predictions.get(strategy, [])
        if preds:
            contrib = compute_span_contribution(preds, rrf_baseline, gold, strategy)
            span_contributions.update(contrib)

    # Bucket regressions
    bucket_regressions = compute_bucket_regressions(all_predictions, gold)

    # Citation validity check across all strategies
    citation_validity_all = True
    for strategy in strategies:
        cs = citation_summaries.get(strategy, {})
        if cs.get("citation_total_count", 0) > 0 and cs.get("citation_validity", 1.0) < 1.0:
            citation_validity_all = False
            break

    # ── Build report ──────────────────────────────────────────────────

    timestamp = datetime.now(timezone.utc).isoformat()

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": timestamp,
        "workspace": str(workspace),
        "openlocus": openlocus_path,
        "limit": args.limit,
        "promotion_ready": False,
        "not_promotion_evidence": True,
        "core_changes": False,
        "remote_calls": 0,
        "labels_loaded_after_run": True,
        "run_phase_public_only": True,
        "score_phase_labels_only": True,
        "r26_source_artifacts_validated": r26_provenance.get("r26_source_artifacts_validated", False),
        "r26_label_artifacts_validated_after_run": label_validation.get("passed", False),
        "citation_validity_all_strategies": 1.0 if citation_validity_all else 0.0,
        "quiver_implemented": False,
        "dense_mock_is_semantic_quality": False,
        "artifact_manifest_verified": manifest_verify.get("passed", False),
        "source_dataset_manifest": {
            "path": str(manifest_path),
            "not_promotion_evidence": manifest.get("not_promotion_evidence", True),
            "core_changes": manifest.get("core_changes", False),
            "remote_calls": manifest.get("remote_calls", 0),
            "dense_or_llm_claims": manifest.get("dense_or_llm_claims", False),
        },
        "r26_provenance": r26_provenance,
        "r26_label_validation_score_phase": label_validation,
        "safety_gates": {
            "all_passed": len(critical_issues) == 0,
            "critical_issues": critical_issues,
            "warning_issues": warning_issues,
            "issues": critical_issues + warning_issues,
            "canary_retrieval": canary_summary,
            "artifact_manifest_verified": manifest_verify,
            "artifact_manifest_path": str(manifest_path_out),
            "artifact_manifest_sha256": file_sha256(manifest_path_out),
            "artifact_private_field_scan": {
                "scanned": True,
                "issues_found": len(private_field_issues),
            },
            "artifact_canary_token_scan": {
                "scanned": True,
                "issues_found": len(canary_token_issues),
            },
        },
        "strategy_registry": {
            "implemented": strategies,
            "unavailable": UNAVAILABLE_STRATEGIES,
        },
        "metrics": all_metrics,
        "bucket_metrics": bucket_metrics,
        "failure_clusters": failure_clusters,
        "span_contributions": span_contributions,
        "bucket_regressions": bucket_regressions,
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
            "no_graph_baseline_inheritance": "fresh_rrf_baseline_not_inherited",
            "label_sha_validation": "score_phase_after_run_artifacts_written",
        },
        "tasks_count": len(tasks),
        "repos_count": len(repos),
        "labels_count": len(gold),
        "skip_run_supported": False,
    }

    out_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    # Also write MD report
    md_path = out_path.with_suffix(".md")
    md_lines = [
        f"# R29 R26 Auto-Stress Strategy Matrix Report",
        f"",
        f"- schema_version: {SCHEMA_VERSION}",
        f"- timestamp: {timestamp}",
        f"- promotion_ready: false",
        f"- not_promotion_evidence: true",
        f"- core_changes: false",
        f"- remote_calls: 0",
        f"- tasks: {len(tasks)}",
        f"- repos: {len(repos)}",
        f"- strategies_implemented: {len(strategies)}",
        f"- citation_validity_all_strategies: {1.0 if citation_validity_all else 0.0}",
        f"- quiver_implemented: false",
        f"- dense_mock_is_semantic_quality: false",
        f"- artifact_manifest_verified: {manifest_verify.get('passed', False)}",
        f"- r26_source_artifacts_validated: {r26_provenance.get('r26_source_artifacts_validated', False)}",
        f"- r26_label_artifacts_validated_after_run: {label_validation.get('passed', False)}",
        f"",
        f"## Strategies",
        f"",
        f"Implemented: {', '.join(strategies)}",
        f"",
        f"Unavailable: {', '.join(UNAVAILABLE_STRATEGIES.keys())}",
        f"",
        f"## Key Metrics (RRF baseline)",
        f"",
    ]
    rrf_m = all_metrics.get("rrf", {})
    for key in ["FileRecall@1", "FileRecall@3", "FileRecall@5", "MRR", "SpanF0.5",
                 "token_waste", "no_gold_nonempty_rate", "primary_false_positive_rate",
                 "abstain_rate", "must_not_primary_violation_rate", "hard_distractor_hit_rate"]:
        val = rrf_m.get(key)
        if val is not None:
            md_lines.append(f"- {key}: {val:.3f}" if isinstance(val, float) else f"- {key}: {val}")

    md_lines.extend([
        f"",
        f"## Failure Clusters",
        f"",
    ])
    for cluster_name, cluster_data in sorted(failure_clusters.items()):
        md_lines.append(f"- **{cluster_name}**: count={cluster_data.get('count', 0)}")

    md_lines.extend([
        f"",
        f"## Bucket Regressions",
        f"",
        f"- total_bucket_regressions: {bucket_regressions.get('total_bucket_regressions', 0)}",
        f"- strategies_with_regression: {len(bucket_regressions.get('strategies_with_bucket_regression', []))}",
        f"",
        f"## Safety",
        f"",
        f"- all_passed: {len(critical_issues) == 0}",
        f"- critical_issues: {len(critical_issues)}",
        f"- warning_issues: {len(warning_issues)}",
        f"",
        f"## Caveats",
        f"",
        f"- No promotion evidence. Failure-surface only.",
        f"- R26 labels are weak/mined/deterministic/stress; not human-verified.",
        f"- dense_mock is candidate-channel safety smoke, not semantic quality.",
        f"- graph_basic is deterministic depth=1, not precise call/type graph.",
        f"- QuIVer/TDB are unavailable; no fabricated numeric quality.",
    ])
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    # ── Print summary ─────────────────────────────────────────────────

    print(f"\n{'='*70}")
    print(f"R29 R26 Stress Matrix Results")
    print(f"{'='*70}")

    for strategy in strategies:
        m = all_metrics.get(strategy, {})
        print(f"\n  {strategy}:")
        for key in ["FileRecall@1", "FileRecall@3", "FileRecall@5", "MRR", "SpanF0.5",
                     "token_waste", "no_gold_nonempty_rate", "primary_false_positive_rate",
                     "abstain_rate", "must_not_primary_violation_rate", "hard_distractor_hit_rate",
                     "weak_candidate_rate", "guard_recall_kill_rate"]:
            val = m.get(key)
            if val is not None:
                if isinstance(val, float):
                    print(f"    {key}: {val:.3f}")
                else:
                    print(f"    {key}: {val}")
        print(f"    citation_validity: {m.get('citation_validity', 'N/A')}")

    print(f"\n  Failure Clusters:")
    for name, data in sorted(failure_clusters.items()):
        print(f"    {name}: count={data.get('count', 0)}")

    print(f"\n  Bucket Regressions: total={bucket_regressions.get('total_bucket_regressions', 0)}")

    if critical_issues:
        print(f"\n  CRITICAL Safety issues: {len(critical_issues)}")
        for issue in critical_issues[:20]:
            print(f"    - {issue}")
    if warning_issues:
        print(f"\n  WARNING: {len(warning_issues)} non-critical issues")
    if not critical_issues and not warning_issues:
        print(f"\n  Safety checks: ALL PASSED")

    print(f"\n  Report: {out_path}")
    print(f"  promotion_ready: False")
    print(f"  not_promotion_evidence: True")

    if critical_issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
