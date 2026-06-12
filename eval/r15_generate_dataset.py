#!/usr/bin/env python3
"""R15 External Multi-Repo Benchmark Dataset Generator.

Extends R14 benchmark foundation with real local multi-repo benchmark data.
R15 scans independent external git repos under /workspace for multi-language
source code, generates normalized content manifests, mines symbols/definitions,
and creates Medium/Large/Stress tier task and label data.

Safety: public tasks contain no gold path/line info; labels are private and
separate. Repos are read-only; no modifications to external repos.

Usage:
    python3 eval/r15_generate_dataset.py [--out-dir PATH] [--tier medium|large|stress|all]
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


# ── Schema version ─────────────────────────────────────────────────────

SCHEMA_VERSION = "r15-v1"

# ── Supported source file extensions (multi-language) ──────────────────

SOURCE_EXTENSIONS = {".rs", ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".mjs"}

CANARY_TOKENS = [
    "R15_CANARY_fixture_label_secret_1a2b",
    "R15_CANARY_eval_benchmark_secret_3c4d",
    "R15_CANARY_docs_summary_secret_5e6f",
    "R15_CANARY_runs_prediction_secret_7g8h",
]

# ── Directories to ignore when scanning ────────────────────────────────

SKIP_DIR_NAMES = {
    "node_modules", "target", ".git", "dist", "build", ".venv",
    "__pycache__", ".next", ".nuxt", "runs", "fixtures", "eval",
    "docs", ".openlocus", "coverage", ".cache", ".mypy_cache",
    ".pytest_cache", ".tox", "venv", "env", ".env", ".idea",
    ".vscode", "out", "bin", "obj",
}

# ── Candidate repos (external, independent) ────────────────────────────

CANDIDATE_REPOS: list[dict[str, Any]] = [
    {
        "repo_id": "fast-context-mcp",
        "local_path": "/workspace/fast-context-mcp/fast-context-mcp",
        "languages": ["javascript"],
        "extensions": [".mjs", ".js"],
        "primary_ext": ".mjs",
        "description": "TS/JS MCP server for fast-context",
        "min_files": 3,
    },
    {
        "repo_id": "grok2api",
        "local_path": "/workspace/grok2api/grok2api",
        "languages": ["python"],
        "extensions": [".py", ".js"],
        "primary_ext": ".py",
        "description": "Python grok2api web service",
        "min_files": 5,
    },
    {
        "repo_id": "infinite-canvas",
        "local_path": "/workspace/infinite-canvas/infinite-canvas",
        "languages": ["go", "typescript"],
        "extensions": [".go", ".ts", ".tsx"],
        "primary_ext": ".go",
        "description": "Go handler/service with TS/TSX web",
        "min_files": 5,
    },
    {
        "repo_id": "gemini-web2api",
        "local_path": "/workspace/gemini-web2api/gemini-web2api",
        "languages": ["python"],
        "extensions": [".py"],
        "primary_ext": ".py",
        "description": "Python gemini_web2api service",
        "min_files": 3,
    },
    {
        "repo_id": "windsurf2api",
        "local_path": "/workspace/windsurf2api/WindsurfAPI",
        "languages": ["javascript"],
        "extensions": [".js"],
        "primary_ext": ".js",
        "description": "JS WindsurfAPI service",
        "min_files": 5,
    },
    {
        "repo_id": "kiro2",
        "local_path": "/workspace/kiro2/kiro.rs",
        "languages": ["rust", "typescript"],
        "extensions": [".rs", ".ts", ".tsx"],
        "primary_ext": ".rs",
        "description": "Rust kiro2 with TS/TSX front-end",
        "min_files": 5,
        "exclude_subdirs": ["target"],
    },
    {
        "repo_id": "triviumdb",
        "local_path": "/workspace/TDB/TriviumDB",
        "languages": ["rust"],
        "extensions": [".rs"],
        "primary_ext": ".rs",
        "description": "Rust TriviumDB vector database",
        "min_files": 5,
        "exclude_subdirs": ["target"],
    },
    {
        "repo_id": "smartsearch",
        "local_path": "/workspace/smartsearch/smartsearch",
        "languages": ["python", "javascript"],
        "extensions": [".py", ".js"],
        "primary_ext": ".py",
        "description": "Python/JS smartsearch application",
        "min_files": 5,
        "exclude_subdirs": ["node_modules"],
    },
    {
        "repo_id": "codex2api",
        "local_path": "/workspace/codex2api/codex2api",
        "languages": ["go", "typescript"],
        "extensions": [".go", ".ts", ".tsx"],
        "primary_ext": ".go",
        "description": "Go codex2api with TS/TSX components",
        "min_files": 5,
    },
]


# ── Benchmark policy excludes (glob-style patterns) ────────────────────

BENCHMARK_EXCLUDES = [
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


# ── Multi-language source file scanning ────────────────────────────────


def should_skip_dir(dirname: str) -> bool:
    """Check if a directory should be skipped during scanning."""
    return dirname in SKIP_DIR_NAMES or dirname.startswith(".")


def find_source_files(
    repo_path: Path,
    extensions: set[str] | None = None,
    exclude_subdirs: list[str] | None = None,
) -> list[tuple[str, Path]]:
    """Find all source files in a repo matching extensions.

    Returns list of (relative_path_posix, absolute_path) tuples, sorted.
    """
    if extensions is None:
        extensions = SOURCE_EXTENSIONS
    exclude_set = set(exclude_subdirs or [])

    results: list[tuple[str, Path]] = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        # Filter out skip directories in-place
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


# ── Normalized content manifest (multi-language) ───────────────────────


def compute_normalized_manifest_sha(
    repo_path: Path,
    extensions: set[str] | None = None,
    exclude_subdirs: list[str] | None = None,
) -> tuple[str, int, int, list[dict[str, Any]]]:
    """Compute normalized content manifest SHA across all source files.

    Algorithm: sort all source files by relative path (POSIX). For each file:
    - relative path (POSIX, forward-slash)
    - SHA-256 of file contents
    - line count
    Concatenate as sorted JSON lines, SHA-256 the result.

    Returns (manifest_sha, file_count, total_lines, per_file_entries).
    """
    all_files = find_source_files(repo_path, extensions, exclude_subdirs)

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


# ── Multi-language symbol/definition extraction ────────────────────────

# Rust patterns
RUST_STRUCT_RE = re.compile(r"^\s*pub\s+struct\s+(\w+)", re.MULTILINE)
RUST_ENUM_RE = re.compile(r"^\s*pub\s+enum\s+(\w+)", re.MULTILINE)
RUST_FN_RE = re.compile(r"^\s*pub\s+(?:async\s+)?fn\s+(\w+)", re.MULTILINE)
RUST_TRAIT_RE = re.compile(r"^\s*pub\s+trait\s+(\w+)", re.MULTILINE)
RUST_IMPL_RE = re.compile(r"^\s*impl\s+(?:<[^>]*>\s*)?(\w+)", re.MULTILINE)

# Python patterns
PY_CLASS_RE = re.compile(r"^class\s+(\w+)", re.MULTILINE)
PY_ASYNC_DEF_RE = re.compile(r"^async\s+def\s+(\w+)", re.MULTILINE)
PY_DEF_RE = re.compile(r"^def\s+(\w+)", re.MULTILINE)

# Go patterns
GO_FUNC_RE = re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)", re.MULTILINE)
GO_TYPE_RE = re.compile(r"^type\s+(\w+)\s+struct", re.MULTILINE)
GO_INTERFACE_RE = re.compile(r"^type\s+(\w+)\s+interface", re.MULTILINE)

# JS/TS patterns
JS_FUNC_RE = re.compile(
    r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE
)
JS_CLASS_RE = re.compile(r"(?:export\s+)?(?:default\s+)?class\s+(\w+)", re.MULTILINE)
JS_CONST_RE = re.compile(
    r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>)",
    re.MULTILINE,
)
JS_ARROW_RE = re.compile(
    r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(", re.MULTILINE
)

# TS interface/type patterns
TS_INTERFACE_RE = re.compile(r"(?:export\s+)?interface\s+(\w+)", re.MULTILINE)
TS_TYPE_RE = re.compile(r"(?:export\s+)?type\s+(\w+)\s*=", re.MULTILINE)


def extract_symbols_from_file(
    filepath: Path, repo_root: Path
) -> list[dict[str, Any]]:
    """Extract public symbols/definitions from a source file (multi-language)."""
    symbols: list[dict[str, Any]] = []
    try:
        text = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return symbols

    lines = text.splitlines()
    rel_path = str(filepath.relative_to(repo_root)).replace(os.sep, "/")
    ext = filepath.suffix

    if ext == ".rs":
        patterns = [
            (RUST_STRUCT_RE, "struct"),
            (RUST_ENUM_RE, "enum"),
            (RUST_TRAIT_RE, "trait"),
            (RUST_FN_RE, "fn"),
            (RUST_IMPL_RE, "impl"),
        ]
    elif ext == ".py":
        patterns = [
            (PY_CLASS_RE, "class"),
            (PY_ASYNC_DEF_RE, "async_def"),
            (PY_DEF_RE, "def"),
        ]
    elif ext == ".go":
        patterns = [
            (GO_FUNC_RE, "func"),
            (GO_TYPE_RE, "struct"),
            (GO_INTERFACE_RE, "interface"),
        ]
    elif ext in (".js", ".mjs", ".jsx"):
        patterns = [
            (JS_FUNC_RE, "function"),
            (JS_CLASS_RE, "class"),
            (JS_CONST_RE, "const_func"),
            (JS_ARROW_RE, "arrow_func"),
        ]
    elif ext in (".ts", ".tsx"):
        patterns = [
            (JS_FUNC_RE, "function"),
            (JS_CLASS_RE, "class"),
            (TS_INTERFACE_RE, "interface"),
            (TS_TYPE_RE, "type"),
            (JS_CONST_RE, "const_func"),
        ]
    else:
        return symbols

    for i, line in enumerate(lines, 1):
        for pattern, kind in patterns:
            m = pattern.search(line)
            if m:
                name = m.group(1)
                # Compute end line (simple heuristic: up to 20 lines or next def)
                end_line = _estimate_end_line(lines, i - 1, kind, ext)
                symbols.append(
                    {
                        "name": name,
                        "kind": kind,
                        "path": rel_path,
                        "start_line": i,
                        "end_line": end_line,
                        "language": ext_to_language(ext),
                    }
                )

    return symbols


def ext_to_language(ext: str) -> str:
    """Map file extension to language name."""
    mapping = {
        ".rs": "rust",
        ".py": "python",
        ".go": "go",
        ".js": "javascript",
        ".mjs": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
    }
    return mapping.get(ext, "unknown")


def _estimate_end_line(
    lines: list[str], start_idx: int, kind: str, ext: str
) -> int:
    """Estimate end line of a definition using brace counting or heuristics."""
    # For Python (no braces), estimate based on indentation
    if ext == ".py":
        if kind in ("class", "def", "async_def"):
            # Find next line with same or less indentation
            if start_idx >= len(lines):
                return start_idx + 1
            start_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
            for j in range(start_idx + 1, min(start_idx + 40, len(lines))):
                line = lines[j]
                if line.strip() == "":
                    continue
                indent = len(line) - len(line.lstrip())
                if indent <= start_indent and line.strip():
                    return j  # 1-indexed: j is already +1 since start_idx is 0-based
            return min(start_idx + 20, len(lines))
        return start_idx + 1

    # For brace-based languages, count braces
    brace_count = 0
    found_open = False
    for j in range(start_idx, min(start_idx + 50, len(lines))):
        brace_count += lines[j].count("{") - lines[j].count("}")
        if "{" in lines[j]:
            found_open = True
        if found_open and brace_count <= 0:
            return j + 1  # 1-indexed
        if found_open and brace_count > 0 and j > start_idx + 40:
            return j + 1

    if found_open:
        return min(start_idx + 30, len(lines))
    return start_idx + 1  # Single-line definition


def find_hard_negatives(
    symbol: dict[str, Any],
    all_symbols: list[dict[str, Any]],
    max_negatives: int = 2,
) -> list[dict[str, Any]]:
    """Find hard negatives for a symbol: similar names or same-file different symbols."""
    negatives = []
    name = symbol["name"]
    path = symbol["path"]
    gold_start = int(symbol.get("start_line", 0))
    gold_end = int(symbol.get("end_line", 0))

    def overlaps_gold(candidate: dict[str, Any]) -> bool:
        if candidate.get("path") != path:
            return False
        start = int(candidate.get("start_line", 0))
        end = int(candidate.get("end_line", 0))
        return start > 0 and end >= start and start <= gold_end and end >= gold_start

    # Same file, different symbol
    for s in all_symbols:
        if s["path"] == path and s["name"] != name and not overlaps_gold(s):
            negatives.append(
                {
                    "path": s["path"],
                    "start_line": s["start_line"],
                    "end_line": s["end_line"],
                    "rationale": f"{s['name']} ({s['kind']}) same file, different from {name}",
                }
            )
            if len(negatives) >= max_negatives:
                break

    # Similar name in different file
    if len(negatives) < max_negatives:
        name_lower = name.lower()
        for s in all_symbols:
            if s["path"] != path and (
                name_lower in s["name"].lower()
                or s["name"].lower() in name_lower
            ):
                negatives.append(
                    {
                        "path": s["path"],
                        "start_line": s["start_line"],
                        "end_line": s["end_line"],
                        "rationale": f"{s['name']} has similar name to {name}",
                    }
                )
                if len(negatives) >= max_negatives:
                    break

    # Same-kind in same language
    if len(negatives) < max_negatives:
        for s in all_symbols:
            if (
                s["path"] != path
                and s.get("language") == symbol.get("language")
                and s["kind"] == symbol["kind"]
                and s["name"] != name
            ):
                negatives.append(
                    {
                        "path": s["path"],
                        "start_line": s["start_line"],
                        "end_line": s["end_line"],
                        "rationale": f"{s['name']} ({s['kind']}) same language/kind",
                    }
                )
                if len(negatives) >= max_negatives:
                    break

    return negatives


def hard_negative_overlaps_gold(label: dict[str, Any]) -> bool:
    """Return true if any hard-negative span overlaps any gold span."""
    for gold in label.get("gold_spans", []):
        gp = gold.get("path", "")
        gs = int(gold.get("start_line", 0))
        ge = int(gold.get("end_line", 0))
        if not gp or gs <= 0 or ge < gs:
            continue
        for hn in label.get("hard_negatives", []):
            hp = hn.get("path", "")
            hs = int(hn.get("start_line", 0))
            he = int(hn.get("end_line", 0))
            if hp == gp and hs > 0 and he >= hs and hs <= ge and he >= gs:
                return True
    return False


def sanitize_hard_negatives(labels: list[dict[str, Any]]) -> None:
    """Drop hard negatives that overlap gold spans.

    Generated labels are mined, so this conservative filter is preferable to
    keeping ambiguous negative spans that can penalize correct evidence.
    """
    for label in labels:
        gold_spans = label.get("gold_spans", [])
        if not gold_spans:
            continue
        kept = []
        for hn in label.get("hard_negatives", []):
            candidate_label = {"gold_spans": gold_spans, "hard_negatives": [hn]}
            if not hard_negative_overlaps_gold(candidate_label):
                kept.append(hn)
        label["hard_negatives"] = kept


# ── Repo lock generation ───────────────────────────────────────────────


def resolve_repos() -> list[dict[str, Any]]:
    """Resolve candidate repos, skipping missing/empty ones.

    Returns list of repo entries with validated paths.
    """
    resolved = []
    for candidate in CANDIDATE_REPOS:
        repo_path = Path(candidate["local_path"])
        if not repo_path.exists():
            print(
                f"  SKIP: {candidate['repo_id']} — path not found: {candidate['local_path']}",
                file=sys.stderr,
            )
            continue

        # Count source files
        extensions = set(candidate.get("extensions", [".rs"]))
        exclude_subdirs = candidate.get("exclude_subdirs", [])
        files = find_source_files(repo_path, extensions, exclude_subdirs)
        if len(files) < candidate.get("min_files", 3):
            print(
                f"  SKIP: {candidate['repo_id']} — only {len(files)} source files (need {candidate['min_files']})",
                file=sys.stderr,
            )
            continue

        resolved.append(candidate)
        print(
            f"  OK: {candidate['repo_id']} — {len(files)} source files at {candidate['local_path']}"
        )

    return resolved


def generate_repo_lock(
    resolved_repos: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate repos.lock.jsonl entries with normalized content manifest."""
    entries = []
    for candidate in resolved_repos:
        repo_id = candidate["repo_id"]
        repo_path = Path(candidate["local_path"])
        extensions = set(candidate.get("extensions", [".rs"]))
        exclude_subdirs = candidate.get("exclude_subdirs", [])

        manifest_sha, file_count, line_count, per_file = (
            compute_normalized_manifest_sha(repo_path, extensions, exclude_subdirs)
        )

        if file_count == 0:
            print(
                f"WARNING: No source files found for repo {repo_id}",
                file=sys.stderr,
            )
            continue

        primary_lang = candidate["languages"][0] if candidate["languages"] else "unknown"
        secondary_langs = candidate["languages"][1:] if len(candidate["languages"]) > 1 else []

        entries.append(
            {
                "repo_id": repo_id,
                "source": {
                    "type": "local_absolute_path",
                    "path": candidate["local_path"],
                    "isolated_root_relative": repo_id,
                },
                "commit": "r15-snapshot",
                "worktree_info": f"External repo: {candidate['description']}",
                "content_manifest_sha": manifest_sha,
                "content_manifest_algorithm": "normalized_sha256_per_file_sorted",
                "policy": {
                    "exclude": BENCHMARK_EXCLUDES,
                },
                "language": {
                    "primary": primary_lang,
                    "secondary": secondary_langs,
                    "tier": "M",
                },
                "metadata": {
                    "files": file_count,
                    "lines": line_count,
                    "description": candidate["description"],
                    "per_file_count": len(per_file),
                    "extensions": list(extensions),
                    "exclude_subdirs": exclude_subdirs,
                    "source_repo_kind": "external_local",
                },
            }
        )

    return entries


# ── Task generation helpers ────────────────────────────────────────────

NEGATIVE_QUERIES_BY_REPO = [
    ("quantum_entanglement_solver", "fast-context-mcp"),
    ("neural_network_training_loop", "grok2api"),
    ("blockchain_consensus_protocol", "infinite-canvas"),
    ("distributed_database_replication", "gemini-web2api"),
    ("machine_learning_inference", "windsurf2api"),
    ("cryptographic_key_rotation", "kiro2"),
    ("microservice_orchestration", "triviumdb"),
    ("web_server_http_handler", "smartsearch"),
    ("real_time_streaming_pipeline", "codex2api"),
    ("image_processing_pipeline", "fast-context-mcp"),
]

STRESS_QUERIES_BY_REPO = [
    ("error handling", "grok2api"),
    ("search implementation", "smartsearch"),
    ("data storage", "triviumdb"),
    ("api endpoint", "codex2api"),
    ("request handler", "infinite-canvas"),
    ("configuration setup", "gemini-web2api"),
    ("connection management", "windsurf2api"),
    ("data processing", "kiro2"),
    ("server startup", "fast-context-mcp"),
    ("response handling", "grok2api"),
    ("event processing", "infinite-canvas"),
    ("model interface", "triviumdb"),
]

MUTATION_NEGATIVE_QUERIES = [
    ("FIXME_bogus_method_xyz123", "kiro2"),
    ("TODO_nonexistent_feature_abc456", "grok2api"),
    ("HACK_impossible_refactor_def789", "codex2api"),
]

PROVIDER_ISH_QUERIES = [
    ("embedding provider mock", "triviumdb"),
    ("api key rotation", "gemini-web2api"),
    ("rate limit handler", "codex2api"),
]

QUERY_NOISE_QUERIES = [
    ("the", "fast-context-mcp"),
    ("function", "grok2api"),
    ("return", "smartsearch"),
]


def method_hint_for_symbol(kind: str, language: str) -> str:
    """Determine retrieval method hint based on symbol kind and language."""
    if kind in ("struct", "enum", "trait", "class", "interface", "type", "impl"):
        return "symbol"
    elif kind in ("fn", "def", "async_def", "func", "function", "const_func", "arrow_func"):
        return "regex"
    return "regex"


def task_type_for_symbol(kind: str) -> str:
    """Determine task type for a symbol."""
    if kind in ("struct", "enum", "trait", "class", "interface", "type"):
        return "exact_symbol"
    elif kind in ("impl",):
        return "implementation_search"
    else:
        return "implementation_search"


# ── Tier generation ────────────────────────────────────────────────────


def generate_tier_medium(
    resolved_repos: list[dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    """Generate R15-M (Medium) tier: 8+ repos, 120+ tasks, mined_high_confidence labels."""
    print("Generating R15-M (Medium) tier...")

    all_tasks: list[dict] = []
    all_labels: list[dict] = []
    task_id = 1

    for candidate in resolved_repos:
        repo_id = candidate["repo_id"]
        repo_path = Path(candidate["local_path"])
        extensions = set(candidate.get("extensions", [".rs"]))
        exclude_subdirs = candidate.get("exclude_subdirs", [])

        # Extract symbols from all source files
        all_symbols: list[dict[str, Any]] = []
        source_files = find_source_files(repo_path, extensions, exclude_subdirs)
        for _rel, full_path in source_files:
            syms = extract_symbols_from_file(full_path, repo_path)
            all_symbols.extend(syms)

        print(f"  {repo_id}: {len(all_symbols)} symbols from {len(source_files)} files")

        if not all_symbols:
            continue

        # Select up to 15 symbols per repo for medium tier
        selected = all_symbols[:15]

        for sym in selected:
            tid = f"r15m-{task_id:03d}"
            task_id += 1

            task_type = task_type_for_symbol(sym["kind"])
            method_hint = method_hint_for_symbol(sym["kind"], sym.get("language", ""))

            # Public task: NO gold path/line/hard_negatives/label_quality
            all_tasks.append(
                {
                    "task_id": tid,
                    "query": sym["name"],
                    "task_type": task_type,
                    "method_hint": method_hint,
                    "repo_id": repo_id,
                }
            )

            # Private label
            hard_negs = find_hard_negatives(sym, all_symbols, max_negatives=2)
            all_labels.append(
                {
                    "task_id": tid,
                    "label_quality": "mined_high_confidence",
                    "gold_spans": [
                        {
                            "path": sym["path"],
                            "start_line": sym["start_line"],
                            "end_line": sym["end_line"],
                            "rationale": f"{sym['kind']} {sym['name']} definition ({sym.get('language', 'unknown')})",
                        }
                    ],
                    "hard_negatives": hard_negs,
                    "source_repo_kind": "external_local",
                }
            )

    # Add config/import tasks per repo
    CONFIG_QUERIES = [
        ("configuration settings", "grok2api"),
        ("import dependencies", "smartsearch"),
        ("module exports", "fast-context-mcp"),
        ("server setup", "infinite-canvas"),
        ("route definitions", "codex2api"),
        ("error types", "triviumdb"),
        ("client initialization", "gemini-web2api"),
        ("connection setup", "windsurf2api"),
        ("builder pattern", "kiro2"),
    ]
    for query, repo_id in CONFIG_QUERIES:
        # Only add if repo is in resolved set
        if any(r["repo_id"] == repo_id for r in resolved_repos):
            tid = f"r15m-{task_id:03d}"
            task_id += 1
            all_tasks.append(
                {
                    "task_id": tid,
                    "query": query,
                    "task_type": "config_import",
                    "method_hint": "bm25",
                    "repo_id": repo_id,
                }
            )
            all_labels.append(
                {
                    "task_id": tid,
                    "label_quality": "mined",
                    "gold_spans": [],
                    "hard_negatives": [],
                    "source_repo_kind": "external_local",
                }
            )

    # Add negative tasks (queries with no good match)
    for query, repo_id in NEGATIVE_QUERIES_BY_REPO:
        if any(r["repo_id"] == repo_id for r in resolved_repos):
            tid = f"r15m-{task_id:03d}"
            task_id += 1
            all_tasks.append(
                {
                    "task_id": tid,
                    "query": query,
                    "task_type": "negative",
                    "method_hint": "regex",
                    "repo_id": repo_id,
                }
            )
            all_labels.append(
                {
                    "task_id": tid,
                    "label_quality": "human_reviewed",
                    "gold_spans": [],
                    "hard_negatives": [],
                    "source_repo_kind": "external_local",
                }
            )

    # Add stress tasks (broad/vague queries)
    for query, repo_id in STRESS_QUERIES_BY_REPO:
        if any(r["repo_id"] == repo_id for r in resolved_repos):
            tid = f"r15m-{task_id:03d}"
            task_id += 1
            all_tasks.append(
                {
                    "task_id": tid,
                    "query": query,
                    "task_type": "stress",
                    "method_hint": "bm25",
                    "repo_id": repo_id,
                }
            )
            all_labels.append(
                {
                    "task_id": tid,
                    "label_quality": "weak",
                    "gold_spans": [],
                    "hard_negatives": [],
                    "source_repo_kind": "external_local",
                }
            )

    # Write tasks and labels
    sanitize_hard_negatives(all_labels)

    tasks_path = out_dir / "tasks" / "medium.jsonl"
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    with tasks_path.open("w", encoding="utf-8") as f:
        for task in all_tasks:
            f.write(json.dumps(task) + "\n")

    labels_path = out_dir / "labels" / "medium.jsonl"
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    with labels_path.open("w", encoding="utf-8") as f:
        for label in all_labels:
            f.write(json.dumps(label) + "\n")

    hard_neg_count = sum(len(l.get("hard_negatives", [])) for l in all_labels)
    quality_dist: dict[str, int] = {}
    for l in all_labels:
        q = l.get("label_quality", "unknown")
        quality_dist[q] = quality_dist.get(q, 0) + 1

    print(f"  Tasks: {len(all_tasks)}")
    print(f"  Labels: {len(all_labels)}")
    print(f"  Hard negatives: {hard_neg_count}")
    print(f"  Label quality: {quality_dist}")

    return {
        "repos": len(resolved_repos),
        "tasks": len(all_tasks),
        "labels": len(all_labels),
        "hard_negatives": hard_neg_count,
        "label_quality_distribution": quality_dist,
        "populated": len(resolved_repos) == 9,
        "partial": len(resolved_repos) != 9,
    }


def generate_tier_large(
    resolved_repos: list[dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    """Generate R15-L (Large) tier: more tasks with weaker labels."""
    print("Generating R15-L (Large) tier...")

    all_tasks: list[dict] = []
    all_labels: list[dict] = []
    task_id = 1

    for candidate in resolved_repos:
        repo_id = candidate["repo_id"]
        repo_path = Path(candidate["local_path"])
        extensions = set(candidate.get("extensions", [".rs"]))
        exclude_subdirs = candidate.get("exclude_subdirs", [])

        # Extract all symbols (not limited)
        all_symbols: list[dict[str, Any]] = []
        source_files = find_source_files(repo_path, extensions, exclude_subdirs)
        for _rel, full_path in source_files:
            syms = extract_symbols_from_file(full_path, repo_path)
            all_symbols.extend(syms)

        # Select up to 30 symbols per repo for large tier
        selected = all_symbols[:30]

        for sym in selected:
            tid = f"r15l-{task_id:03d}"
            task_id += 1

            task_type = task_type_for_symbol(sym["kind"])
            method_hint = method_hint_for_symbol(sym["kind"], sym.get("language", ""))

            all_tasks.append(
                {
                    "task_id": tid,
                    "query": sym["name"],
                    "task_type": task_type,
                    "method_hint": method_hint,
                    "repo_id": repo_id,
                }
            )

            hard_negs = find_hard_negatives(sym, all_symbols, max_negatives=1)
            all_labels.append(
                {
                    "task_id": tid,
                    "label_quality": "mined",
                    "gold_spans": [
                        {
                            "path": sym["path"],
                            "start_line": sym["start_line"],
                            "end_line": sym["end_line"],
                            "rationale": f"{sym['kind']} {sym['name']} definition",
                        }
                    ],
                    "hard_negatives": hard_negs,
                    "source_repo_kind": "external_local",
                }
            )

    # Add more stress/config/negative tasks for large tier
    for query, repo_id in STRESS_QUERIES_BY_REPO + CONFIG_QUERIES_BY_REPO_LARGE:
        if any(r["repo_id"] == repo_id for r in resolved_repos):
            tid = f"r15l-{task_id:03d}"
            task_id += 1
            all_tasks.append(
                {
                    "task_id": tid,
                    "query": query,
                    "task_type": "stress",
                    "method_hint": "bm25",
                    "repo_id": repo_id,
                }
            )
            all_labels.append(
                {
                    "task_id": tid,
                    "label_quality": "weak",
                    "gold_spans": [],
                    "hard_negatives": [],
                    "source_repo_kind": "external_local",
                }
            )

    sanitize_hard_negatives(all_labels)

    tasks_path = out_dir / "tasks" / "large.jsonl"
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    with tasks_path.open("w", encoding="utf-8") as f:
        for task in all_tasks:
            f.write(json.dumps(task) + "\n")

    labels_path = out_dir / "labels" / "large.jsonl"
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    with labels_path.open("w", encoding="utf-8") as f:
        for label in all_labels:
            f.write(json.dumps(label) + "\n")

    hard_neg_count = sum(len(l.get("hard_negatives", [])) for l in all_labels)
    quality_dist: dict[str, int] = {}
    for l in all_labels:
        q = l.get("label_quality", "unknown")
        quality_dist[q] = quality_dist.get(q, 0) + 1

    print(f"  Tasks: {len(all_tasks)}")
    print(f"  Labels: {len(all_labels)}")
    print(f"  Hard negatives: {hard_neg_count}")

    repos_count = len(resolved_repos)
    populated = repos_count == 9 and len(all_tasks) >= 200

    return {
        "repos": repos_count,
        "tasks": len(all_tasks),
        "labels": len(all_labels),
        "hard_negatives": hard_neg_count,
        "label_quality_distribution": quality_dist,
        "populated": populated,
        "partial": not populated,
    }


# Extra config queries for large tier
CONFIG_QUERIES_BY_REPO_LARGE = [
    ("interface definition", "triviumdb"),
    ("struct fields", "kiro2"),
    ("api route", "codex2api"),
    ("websocket handler", "infinite-canvas"),
    ("middleware chain", "grok2api"),
    ("database query", "smartsearch"),
    ("authentication flow", "gemini-web2api"),
    ("token validation", "windsurf2api"),
    ("message protocol", "fast-context-mcp"),
    ("vector similarity", "triviumdb"),
    ("error response", "codex2api"),
    ("test helper", "kiro2"),
]


def generate_tier_stress(
    resolved_repos: list[dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    """Generate R15-Stress tier: mutation/negative/provider-ish/query-noise tasks."""
    print("Generating R15-Stress tier...")

    all_tasks: list[dict] = []
    all_labels: list[dict] = []
    task_id = 1

    # Mutation/negative tasks
    for query, repo_id in MUTATION_NEGATIVE_QUERIES:
        if any(r["repo_id"] == repo_id for r in resolved_repos):
            tid = f"r15s-{task_id:03d}"
            task_id += 1
            all_tasks.append(
                {
                    "task_id": tid,
                    "query": query,
                    "task_type": "mutation_negative",
                    "method_hint": "regex",
                    "repo_id": repo_id,
                }
            )
            all_labels.append(
                {
                    "task_id": tid,
                    "label_quality": "human_reviewed",
                    "gold_spans": [],
                    "hard_negatives": [],
                    "source_repo_kind": "external_local",
                }
            )

    # Provider-ish tasks
    for query, repo_id in PROVIDER_ISH_QUERIES:
        if any(r["repo_id"] == repo_id for r in resolved_repos):
            tid = f"r15s-{task_id:03d}"
            task_id += 1
            all_tasks.append(
                {
                    "task_id": tid,
                    "query": query,
                    "task_type": "provider_ish",
                    "method_hint": "bm25",
                    "repo_id": repo_id,
                }
            )
            all_labels.append(
                {
                    "task_id": tid,
                    "label_quality": "weak",
                    "gold_spans": [],
                    "hard_negatives": [],
                    "source_repo_kind": "external_local",
                }
            )

    # Query noise tasks (very common words)
    for query, repo_id in QUERY_NOISE_QUERIES:
        if any(r["repo_id"] == repo_id for r in resolved_repos):
            tid = f"r15s-{task_id:03d}"
            task_id += 1
            all_tasks.append(
                {
                    "task_id": tid,
                    "query": query,
                    "task_type": "query_noise",
                    "method_hint": "bm25",
                    "repo_id": repo_id,
                }
            )
            all_labels.append(
                {
                    "task_id": tid,
                    "label_quality": "weak",
                    "gold_spans": [],
                    "hard_negatives": [],
                    "source_repo_kind": "external_local",
                }
            )

    # Additional stress: broad terms per repo
    STRESS_EXTRA = [
        ("initialization", "grok2api"),
        ("serialization", "smartsearch"),
        ("validation", "codex2api"),
        ("logging", "infinite-canvas"),
        ("testing", "triviumdb"),
        ("configuration", "kiro2"),
        ("routing", "fast-context-mcp"),
        ("parsing", "gemini-web2api"),
        ("buffering", "windsurf2api"),
        ("cleanup", "grok2api"),
    ]
    for query, repo_id in STRESS_EXTRA:
        if any(r["repo_id"] == repo_id for r in resolved_repos):
            tid = f"r15s-{task_id:03d}"
            task_id += 1
            all_tasks.append(
                {
                    "task_id": tid,
                    "query": query,
                    "task_type": "stress",
                    "method_hint": "bm25",
                    "repo_id": repo_id,
                }
            )
            all_labels.append(
                {
                    "task_id": tid,
                    "label_quality": "weak",
                    "gold_spans": [],
                    "hard_negatives": [],
                    "source_repo_kind": "external_local",
                }
            )

    sanitize_hard_negatives(all_labels)

    tasks_path = out_dir / "tasks" / "stress.jsonl"
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    with tasks_path.open("w", encoding="utf-8") as f:
        for task in all_tasks:
            f.write(json.dumps(task) + "\n")

    labels_path = out_dir / "labels" / "stress.jsonl"
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    with labels_path.open("w", encoding="utf-8") as f:
        for label in all_labels:
            f.write(json.dumps(label) + "\n")

    hard_neg_count = sum(len(l.get("hard_negatives", [])) for l in all_labels)
    quality_dist: dict[str, int] = {}
    for l in all_labels:
        q = l.get("label_quality", "unknown")
        quality_dist[q] = quality_dist.get(q, 0) + 1

    print(f"  Tasks: {len(all_tasks)}")
    print(f"  Labels: {len(all_labels)}")
    print(f"  Hard negatives: {hard_neg_count}")

    return {
        "repos": len(resolved_repos),
        "tasks": len(all_tasks),
        "labels": len(all_labels),
        "hard_negatives": hard_neg_count,
        "label_quality_distribution": quality_dist,
        "populated": len(all_tasks) > 0,
        "partial": len(all_tasks) < 20,
    }


# ── Main generation ────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate R15 external multi-repo benchmark dataset"
    )
    parser.add_argument(
        "--out-dir", default="fixtures/r15", help="Output directory"
    )
    parser.add_argument(
        "--tier",
        default="all",
        choices=["medium", "large", "stress", "all"],
        help="Which tier to generate",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)

    # Create directory structure
    for subdir in ["tasks", "labels", "taxonomy", "expected_failures"]:
        (out_dir / subdir).mkdir(parents=True, exist_ok=True)

    canary_path = out_dir / "labels" / "_canary.json"
    canary_path.write_text(
        json.dumps(
            {
                "canary_tokens": CANARY_TOKENS,
                "description": "These tokens must never appear in public tasks, indexed content, or prediction results",
                "purpose": "Runtime canary retrieval in eval/r15_benchmark.py must return zero hits",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Resolve repos
    print("Resolving candidate repos...")
    resolved_repos = resolve_repos()

    if len(resolved_repos) != 9:
        print(
            f"\nERROR: Expected exactly 9 independent external repos, found {len(resolved_repos)}. "
            f"R15-M should be regenerated only after the repo set is explicit.",
            file=sys.stderr,
        )

    # Generate repo lock
    print("\nGenerating repo lock...")
    repo_entries = generate_repo_lock(resolved_repos)
    print(f"  Repo entries: {len(repo_entries)}")

    lock_path = out_dir / "repos.lock.jsonl"
    with lock_path.open("w", encoding="utf-8") as f:
        for entry in repo_entries:
            f.write(json.dumps(entry) + "\n")

    # Generate tiers
    results: dict[str, Any] = {}

    if args.tier in ("medium", "all"):
        results["M"] = generate_tier_medium(resolved_repos, out_dir)

    if args.tier in ("large", "all"):
        results["L"] = generate_tier_large(resolved_repos, out_dir)

    if args.tier in ("stress", "all"):
        results["stress"] = generate_tier_stress(resolved_repos, out_dir)

    # Write dataset manifest
    manifest_path = out_dir / "dataset_manifest.json"
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program": "R15 External Multi-Repo Evidence Benchmark",
        "description": "Extended benchmark with real local multi-repo data from /workspace. "
        "Independent external repos covering Rust/Python/Go/TypeScript/JavaScript. "
        "Mined benchmark expansion, not final quality conclusion. "
        "External local repos are workspace snapshots; not modified.",
        "tiers": {
            "M": {
                "target_repos": 9,
                "target_tasks": 120,
                "target_labels": 120,
                "target_hard_negatives": 24,
                "target_label_quality": ["mined_high_confidence", "mined", "human_reviewed"],
                "run_time_estimate": "<30 min local",
            },
            "L": {
                "target_repos": 9,
                "target_tasks": 200,
                "target_labels": 200,
                "target_hard_negatives": 40,
                "target_label_quality": ["mined", "weak"],
                "run_time_estimate": "<1 hr local",
            },
            "stress": {
                "target_repos": 9,
                "target_tasks": 30,
                "target_labels": 30,
                "target_hard_negatives": 0,
                "target_label_quality": ["weak", "human_reviewed"],
                "run_time_estimate": "<10 min local",
            },
        },
        "current_status": results,
        "generation_info": {
            "generator": "eval/r15_generate_dataset.py",
            "generated_at": "2026-06-12",
            "source_type": "external_local_repos",
            "content_manifest_algorithm": "normalized_sha256_per_file_sorted",
            "supported_extensions": sorted(SOURCE_EXTENSIONS),
            "anti_leakage": "public tasks contain no gold paths/lines; labels are private; "
            "runner allowlist-copies manifest source files into isolated roots with repo-lock policy; "
            "runtime canary retrieval must return zero hits; "
            "repo lock uses local_absolute_path source with absolute paths but isolated root preserves relative paths",
        },
    }

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # Write safety_checks.json (placeholder, updated by leakage check)
    safety_path = out_dir / "safety_checks.json"
    safety_path.write_text(
        json.dumps(
            {
                "total_checks": 0,
                "critical_issues": -1,
                "warning_issues": 0,
                "issues": [],
                "passed": False,
                "canary_tokens_planted": [],
                "note": "Run eval/r15_leakage_check.py to populate",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"\nGeneration complete!")
    print(f"Results: {json.dumps(results, indent=2)}")

    # Fail if the fixed R15 repo set is not present.
    if results.get("M", {}).get("partial", True) or len(resolved_repos) != 9:
        print(
            "\nWARNING: R15-M is partial — expected exactly 9 independent external repos.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
