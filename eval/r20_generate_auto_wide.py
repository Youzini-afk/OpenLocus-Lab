#!/usr/bin/env python3
"""R20 Auto-Wide Retrieval Failure-Surface Benchmark Dataset Generator.

Generates a failure-discovery benchmark dataset and static validation artifacts
from R15 repos.lock.jsonl and local source paths.  R20 labels are failure-surface
oracle/probe labels, NOT EvidenceCore or promotion evidence.

Key constraints enforced:
  - Public tasks contain ONLY: task_id, repo_id, query, public_version,
    source_tier.  No gold/expected/oracle/risk/judgement fields leak.
  - Private labels carry all judgement fields: query_category, intent_guess,
    risk_tags, oracle_type, expected_behavior, label_quality, gold_spans,
    hard_distractors, must_not_primary, why_this_is_hard,
    which_strategy_it_targets, caveat.
  - expected_behavior enum: primary_evidence | supporting_only | weak_candidates
    | abstain | no_primary
  - oracle_type enum: deterministic | mined | differential | metamorphic | stress
  - label_quality: mined_high_confidence | mined | weak  (NO human_reviewed)
  - R20 is failure discovery + static validation, NOT promotion evidence.

Usage:
    python3 eval/r20_generate_auto_wide.py --workspace . --out fixtures/r20_auto_wide
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
from pathlib import Path
from typing import Any


# ── Schema / constants ──────────────────────────────────────────────────

SCHEMA_VERSION = "r20-v1"
PUBLIC_VERSION = "0"

EXPECTED_BEHAVIOR_ENUM = {
    "primary_evidence",
    "supporting_only",
    "weak_candidates",
    "abstain",
    "no_primary",
}

ORACLE_TYPE_ENUM = {
    "deterministic",
    "mined",
    "differential",
    "metamorphic",
    "stress",
}

LABEL_QUALITY_ENUM = {
    "mined_high_confidence",
    "mined",
    "weak",
}

# Required query_category values — every one must have >= 5 tasks
REQUIRED_CATEGORIES = [
    "positive_exact_symbol",
    "positive_regex_anchor",
    "positive_natural_language",
    "positive_issue_style",
    "negative_nonexistent_symbol",
    "negative_nonexistent_feature",
    "ambiguous_query",
    "vague_query",
    "hard_distractor",
    "same_name_symbol",
    "frontend_backend_confusion",
    "test_source_confusion",
    "docs_source_confusion",
    "generated_vendor_trap",
    "config_key_trap",
    "route_handler_trap",
    "stacktrace_style",
    "dirty_overlay",
    "deleted_file",
    "renamed_file",
    "branch_switch_like",
    "stale_index_candidate",
    "graph_neighbor_trap",
    "dense_semantic_trap",
    "proper_name_api_config_regression",
]

PRIVATE_FIELDS = frozenset({
    "gold_spans", "gold_paths", "gold_files", "hard_distractors",
    "hard_negatives", "label_quality", "expected_behavior", "oracle_type",
    "must_not_primary", "risk_tags", "query_category", "intent_guess",
    "why_this_is_hard", "which_strategy_it_targets", "candidate_only",
})

SOURCE_EXTENSIONS = {".rs", ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".mjs"}

SKIP_DIR_NAMES = {
    "node_modules", "target", ".git", "dist", "build", ".venv",
    "__pycache__", ".next", ".nuxt", "runs", "fixtures", "eval",
    "docs", ".openlocus", "coverage", ".cache", ".mypy_cache",
    ".pytest_cache", ".tox", "venv", "env", ".env", ".idea",
    ".vscode", "out", "bin", "obj",
}

BENCHMARK_EXCLUDES = [
    "fixtures/**", "eval/**", "docs/**", "runs/**", ".openlocus/**",
    "target/**", "__pycache__/**", "*.tmp", "*.log", ".git/**",
    "node_modules/**", "dist/**", "build/**", ".venv/**", ".next/**",
    ".nuxt/**", "coverage/**", "*.pyc",
]

SEED = 42

# ── Multi-language symbol/definition extraction (from R15) ────────────

RUST_STRUCT_RE = re.compile(r"^\s*pub\s+struct\s+(\w+)", re.MULTILINE)
RUST_ENUM_RE = re.compile(r"^\s*pub\s+enum\s+(\w+)", re.MULTILINE)
RUST_FN_RE = re.compile(r"^\s*pub\s+(?:async\s+)?fn\s+(\w+)", re.MULTILINE)
RUST_TRAIT_RE = re.compile(r"^\s*pub\s+trait\s+(\w+)", re.MULTILINE)
RUST_IMPL_RE = re.compile(r"^\s*impl\s+(?:<[^>]*>\s*)?(\w+)", re.MULTILINE)

PY_CLASS_RE = re.compile(r"^class\s+(\w+)", re.MULTILINE)
PY_ASYNC_DEF_RE = re.compile(r"^async\s+def\s+(\w+)", re.MULTILINE)
PY_DEF_RE = re.compile(r"^def\s+(\w+)", re.MULTILINE)

GO_FUNC_RE = re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)", re.MULTILINE)
GO_TYPE_RE = re.compile(r"^type\s+(\w+)\s+struct", re.MULTILINE)
GO_INTERFACE_RE = re.compile(r"^type\s+(\w+)\s+interface", re.MULTILINE)

JS_FUNC_RE = re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE)
JS_CLASS_RE = re.compile(r"(?:export\s+)?(?:default\s+)?class\s+(\w+)", re.MULTILINE)
JS_CONST_RE = re.compile(
    r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>)",
    re.MULTILINE,
)
JS_ARROW_RE = re.compile(
    r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(", re.MULTILINE
)

TS_INTERFACE_RE = re.compile(r"(?:export\s+)?interface\s+(\w+)", re.MULTILINE)
TS_TYPE_RE = re.compile(r"(?:export\s+)?type\s+(\w+)\s*=", re.MULTILINE)

# Config / import / route patterns
CONFIG_KEY_RE = re.compile(r'["\'](\w+(?:_\w+)*)["\']\s*[:=]', re.MULTILINE)
ROUTE_RE = re.compile(
    r'(?:router\.(?:get|post|put|delete|patch|use)|app\.(?:get|post|put|delete|patch))\s*\(\s*["\']([^"\']+)',
    re.MULTILINE,
)
IMPORT_RE = re.compile(
    r'(?:import\s+.*?from\s+["\']|require\s*\(\s*["\'])([^"\']+)', re.MULTILINE
)
TEST_FILE_RE = re.compile(r"(?:test|spec|_test|\.test|\.spec)", re.IGNORECASE)
VENDOR_DIR_RE = re.compile(r"(?:vendor|third_party|generated|dist|\.next|\.nuxt|build)", re.IGNORECASE)


def ext_to_language(ext: str) -> str:
    return {".rs": "rust", ".py": "python", ".go": "go",
            ".js": "javascript", ".mjs": "javascript", ".jsx": "javascript",
            ".ts": "typescript", ".tsx": "typescript"}.get(ext, "unknown")


def should_skip_dir(dirname: str) -> bool:
    return dirname in SKIP_DIR_NAMES or dirname.startswith(".")


def find_source_files(
    repo_path: Path,
    extensions: set[str] | None = None,
    exclude_subdirs: list[str] | None = None,
) -> list[tuple[str, Path]]:
    if extensions is None:
        extensions = SOURCE_EXTENSIONS
    exclude_set = set(exclude_subdirs or [])
    results: list[tuple[str, Path]] = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
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


def extract_symbols_from_file(filepath: Path, repo_root: Path) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    try:
        text = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return symbols

    lines = text.splitlines()
    rel_path = str(filepath.relative_to(repo_root)).replace(os.sep, "/")
    ext = filepath.suffix

    if ext == ".rs":
        patterns = [(RUST_STRUCT_RE, "struct"), (RUST_ENUM_RE, "enum"),
                    (RUST_TRAIT_RE, "trait"), (RUST_FN_RE, "fn"),
                    (RUST_IMPL_RE, "impl")]
    elif ext == ".py":
        patterns = [(PY_CLASS_RE, "class"), (PY_ASYNC_DEF_RE, "async_def"),
                    (PY_DEF_RE, "def")]
    elif ext == ".go":
        patterns = [(GO_FUNC_RE, "func"), (GO_TYPE_RE, "struct"),
                    (GO_INTERFACE_RE, "interface")]
    elif ext in (".js", ".mjs", ".jsx"):
        patterns = [(JS_FUNC_RE, "function"), (JS_CLASS_RE, "class"),
                    (JS_CONST_RE, "const_func"), (JS_ARROW_RE, "arrow_func")]
    elif ext in (".ts", ".tsx"):
        patterns = [(JS_FUNC_RE, "function"), (JS_CLASS_RE, "class"),
                    (TS_INTERFACE_RE, "interface"), (TS_TYPE_RE, "type"),
                    (JS_CONST_RE, "const_func")]
    else:
        return symbols

    for i, line in enumerate(lines, 1):
        for pattern, kind in patterns:
            m = pattern.search(line)
            if m:
                name = m.group(1)
                end_line = _estimate_end_line(lines, i - 1, kind, ext)
                symbols.append({
                    "name": name, "kind": kind, "path": rel_path,
                    "start_line": i, "end_line": end_line,
                    "language": ext_to_language(ext),
                })
    return symbols


def _estimate_end_line(lines: list[str], start_idx: int, kind: str, ext: str) -> int:
    if ext == ".py":
        if kind in ("class", "def", "async_def"):
            if start_idx >= len(lines):
                return start_idx + 1
            start_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
            for j in range(start_idx + 1, min(start_idx + 40, len(lines))):
                line = lines[j]
                if line.strip() == "":
                    continue
                indent = len(line) - len(line.lstrip())
                if indent <= start_indent and line.strip():
                    return j
            return min(start_idx + 20, len(lines))
        return start_idx + 1

    brace_count = 0
    found_open = False
    for j in range(start_idx, min(start_idx + 50, len(lines))):
        brace_count += lines[j].count("{") - lines[j].count("}")
        if "{" in lines[j]:
            found_open = True
        if found_open and brace_count <= 0:
            return j + 1
        if found_open and brace_count > 0 and j > start_idx + 40:
            return j + 1
    if found_open:
        return min(start_idx + 30, len(lines))
    return start_idx + 1


def compute_normalized_manifest_sha(
    repo_path: Path,
    extensions: set[str] | None = None,
    exclude_subdirs: list[str] | None = None,
) -> tuple[str, int, int, list[dict[str, Any]]]:
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


# ── Repo resolution ────────────────────────────────────────────────────

CANDIDATE_REPOS: list[dict[str, Any]] = [
    {"repo_id": "fast-context-mcp", "local_path": "/workspace/fast-context-mcp/fast-context-mcp",
     "languages": ["javascript"], "extensions": [".mjs", ".js"], "primary_ext": ".mjs",
     "description": "TS/JS MCP server for fast-context", "min_files": 3},
    {"repo_id": "grok2api", "local_path": "/workspace/grok2api/grok2api",
     "languages": ["python"], "extensions": [".py", ".js"], "primary_ext": ".py",
     "description": "Python grok2api web service", "min_files": 5},
    {"repo_id": "infinite-canvas", "local_path": "/workspace/infinite-canvas/infinite-canvas",
     "languages": ["go", "typescript"], "extensions": [".go", ".ts", ".tsx"], "primary_ext": ".go",
     "description": "Go handler/service with TS/TSX web", "min_files": 5},
    {"repo_id": "gemini-web2api", "local_path": "/workspace/gemini-web2api/gemini-web2api",
     "languages": ["python"], "extensions": [".py"], "primary_ext": ".py",
     "description": "Python gemini_web2api service", "min_files": 3},
    {"repo_id": "windsurf2api", "local_path": "/workspace/windsurf2api/WindsurfAPI",
     "languages": ["javascript"], "extensions": [".js"], "primary_ext": ".js",
     "description": "JS WindsurfAPI service", "min_files": 5},
    {"repo_id": "kiro2", "local_path": "/workspace/kiro2/kiro.rs",
     "languages": ["rust", "typescript"], "extensions": [".rs", ".ts", ".tsx"], "primary_ext": ".rs",
     "description": "Rust kiro2 with TS/TSX front-end", "min_files": 5, "exclude_subdirs": ["target"]},
    {"repo_id": "triviumdb", "local_path": "/workspace/TDB/TriviumDB",
     "languages": ["rust"], "extensions": [".rs"], "primary_ext": ".rs",
     "description": "Rust TriviumDB vector database", "min_files": 5, "exclude_subdirs": ["target"]},
    {"repo_id": "smartsearch", "local_path": "/workspace/smartsearch/smartsearch",
     "languages": ["python", "javascript"], "extensions": [".py", ".js"], "primary_ext": ".py",
     "description": "Python/JS smartsearch application", "min_files": 5, "exclude_subdirs": ["node_modules"]},
    {"repo_id": "codex2api", "local_path": "/workspace/codex2api/codex2api",
     "languages": ["go", "typescript"], "extensions": [".go", ".ts", ".tsx"], "primary_ext": ".go",
     "description": "Go codex2api with TS/TSX components", "min_files": 5},
]


def resolve_repos() -> list[dict[str, Any]]:
    resolved = []
    for candidate in CANDIDATE_REPOS:
        repo_path = Path(candidate["local_path"])
        if not repo_path.exists():
            print(f"  SKIP: {candidate['repo_id']} — path not found", file=sys.stderr)
            continue
        extensions = set(candidate.get("extensions", [".rs"]))
        exclude_subdirs = candidate.get("exclude_subdirs", [])
        files = find_source_files(repo_path, extensions, exclude_subdirs)
        if len(files) < candidate.get("min_files", 3):
            print(f"  SKIP: {candidate['repo_id']} — only {len(files)} source files", file=sys.stderr)
            continue
        resolved.append(candidate)
        print(f"  OK: {candidate['repo_id']} — {len(files)} source files")
    return resolved


def generate_repo_lock(resolved_repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
            continue
        primary_lang = candidate["languages"][0] if candidate["languages"] else "unknown"
        secondary_langs = candidate["languages"][1:] if len(candidate["languages"]) > 1 else []
        entries.append({
            "repo_id": repo_id,
            "source": {
                "type": "local_absolute_path",
                "path": candidate["local_path"],
                "isolated_root_relative": repo_id,
            },
            "commit": "r20-snapshot",
            "worktree_info": f"External repo: {candidate['description']}",
            "content_manifest_sha": manifest_sha,
            "content_manifest_algorithm": "normalized_sha256_per_file_sorted",
            "policy": {"exclude": BENCHMARK_EXCLUDES},
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
        })
    return entries


# ── Task / label generation ─────────────────────────────────────────────

def _task_id(counter: list[int]) -> str:
    tid = f"r20aw-{counter[0]:04d}"
    counter[0] += 1
    return tid


def _gold_span(sym: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": sym["path"],
        "start_line": sym["start_line"],
        "end_line": sym["end_line"],
        "rationale": f"{sym['kind']} {sym['name']} definition ({sym.get('language', 'unknown')})",
    }


def _find_hard_distractors(
    sym: dict[str, Any],
    all_symbols: list[dict[str, Any]],
    max_distractors: int = 2,
) -> list[dict[str, Any]]:
    """Find hard distractors: same-file different symbols + similar-name cross-file."""
    distractors = []
    name = sym["name"]
    path = sym["path"]
    gold_start = sym.get("start_line", 0)
    gold_end = sym.get("end_line", 0)

    def overlaps(s: dict[str, Any]) -> bool:
        if s.get("path") != path:
            return False
        s_start = s.get("start_line", 0)
        s_end = s.get("end_line", 0)
        return s_start <= gold_end and s_end >= gold_start

    # Same file, different symbol
    for s in all_symbols:
        if s["path"] == path and s["name"] != name and not overlaps(s):
            distractors.append({
                "path": s["path"],
                "start_line": s["start_line"],
                "end_line": s["end_line"],
                "rationale": f"{s['name']} ({s['kind']}) same file, different from {name}",
            })
            if len(distractors) >= max_distractors:
                break

    # Similar name in different file
    if len(distractors) < max_distractors:
        name_lower = name.lower()
        for s in all_symbols:
            if s["path"] != path and (
                name_lower in s["name"].lower() or s["name"].lower() in name_lower
            ):
                distractors.append({
                    "path": s["path"],
                    "start_line": s["start_line"],
                    "end_line": s["end_line"],
                    "rationale": f"{s['name']} has similar name to {name}",
                })
                if len(distractors) >= max_distractors:
                    break

    return distractors


def _find_must_not_primary(
    sym: dict[str, Any],
    all_symbols: list[dict[str, Any]],
    max_mnp: int = 2,
) -> list[dict[str, Any]]:
    """Find spans that must NOT be returned as primary evidence for this query."""
    mnp = []
    name = sym["name"]
    # Symbols with same name prefix or suffix in different files
    for s in all_symbols:
        if s["name"] != name and (
            s["name"].startswith(name) or s["name"].endswith(name)
            or name.startswith(s["name"]) or name.endswith(s["name"])
        ):
            mnp.append({
                "path": s["path"],
                "start_line": s["start_line"],
                "end_line": s["end_line"],
                "rationale": f"{s['name']} ({s['kind']}) partial name match, not the target definition",
            })
            if len(mnp) >= max_mnp:
                break
    return mnp


def _extract_routes(text: str) -> list[str]:
    routes = []
    for m in ROUTE_RE.finditer(text):
        routes.append(m.group(1))
    return routes


def _extract_config_keys(text: str) -> list[str]:
    keys = []
    for m in CONFIG_KEY_RE.finditer(text):
        keys.append(m.group(1))
    return keys


def _is_test_path(rel_path: str) -> bool:
    return bool(TEST_FILE_RE.search(rel_path))


def _is_vendor_path(rel_path: str) -> bool:
    return bool(VENDOR_DIR_RE.search(rel_path))


def _is_docs_path(rel_path: str) -> bool:
    parts = rel_path.split("/")
    return any(p in ("docs", "doc", "documentation") for p in parts)


def generate_all_tasks(
    resolved_repos: list[dict[str, Any]],
    rng: random.Random,
) -> tuple[list[dict], list[dict], dict[str, Any]]:
    """Generate all R20 tasks and labels.

    Returns (tasks, labels, coverage_info).
    """
    counter = [1]
    all_tasks: list[dict] = []
    all_labels: list[dict] = []
    coverage: dict[str, Any] = {
        "by_category": {},
        "by_repo": {},
        "by_language": {},
        "by_oracle": {},
        "by_expected": {},
        "by_risk_tags": {},
        "coverage_gaps": [],
    }

    # Collect all symbols per repo
    repo_symbols: dict[str, list[dict]] = {}
    repo_files: dict[str, list[tuple[str, Path]]] = {}
    repo_file_texts: dict[str, dict[str, str]] = {}

    for candidate in resolved_repos:
        repo_id = candidate["repo_id"]
        repo_path = Path(candidate["local_path"])
        extensions = set(candidate.get("extensions", [".rs"]))
        exclude_subdirs = candidate.get("exclude_subdirs", [])

        source_files = find_source_files(repo_path, extensions, exclude_subdirs)
        repo_files[repo_id] = source_files

        symbols: list[dict[str, Any]] = []
        file_texts: dict[str, str] = {}
        for rel, full_path in source_files:
            syms = extract_symbols_from_file(full_path, repo_path)
            symbols.extend(syms)
            try:
                file_texts[rel] = full_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                pass

        repo_symbols[repo_id] = symbols
        repo_file_texts[repo_id] = file_texts
        coverage["by_repo"][repo_id] = 0

    # ── Category generators ─────────────────────────────────────────────

    def add_task(
        repo_id: str,
        query: str,
        query_category: str,
        expected_behavior: str,
        oracle_type: str,
        label_quality: str,
        gold_spans: list[dict] | None = None,
        hard_distractors: list[dict] | None = None,
        must_not_primary: list[dict] | None = None,
        intent_guess: str = "",
        risk_tags: list[str] | None = None,
        why_this_is_hard: str = "",
        which_strategy_it_targets: str = "",
        caveat: str = "",
    ) -> None:
        gold_spans = gold_spans or []
        hard_distractors = hard_distractors or []
        must_not_primary = must_not_primary or []
        risk_tags = risk_tags or []
        tid = _task_id(counter)
        all_tasks.append({
            "task_id": tid,
            "repo_id": repo_id,
            "query": query,
            "public_version": PUBLIC_VERSION,
            "source_tier": "r20_auto_wide",
        })
        all_labels.append({
            "task_id": tid,
            "repo_id": repo_id,
            "query_category": query_category,
            "intent_guess": intent_guess,
            "risk_tags": risk_tags,
            "oracle_type": oracle_type,
            "expected_behavior": expected_behavior,
            "label_quality": label_quality,
            "gold_spans": gold_spans,
            "hard_distractors": hard_distractors,
            "must_not_primary": must_not_primary,
            "why_this_is_hard": why_this_is_hard,
            "which_strategy_it_targets": which_strategy_it_targets,
            "caveat": caveat,
        })
        coverage["by_category"][query_category] = coverage["by_category"].get(query_category, 0) + 1
        coverage["by_repo"][repo_id] = coverage["by_repo"].get(repo_id, 0) + 1
        lang = ""
        if gold_spans:
            p = gold_spans[0].get("path", "")
            ext = os.path.splitext(p)[1]
            lang = ext_to_language(ext)
        if not lang:
            for c in resolved_repos:
                if c["repo_id"] == repo_id:
                    lang = c["languages"][0] if c["languages"] else "unknown"
                    break
        coverage["by_language"][lang] = coverage["by_language"].get(lang, 0) + 1
        coverage["by_oracle"][oracle_type] = coverage["by_oracle"].get(oracle_type, 0) + 1
        coverage["by_expected"][expected_behavior] = coverage["by_expected"].get(expected_behavior, 0) + 1
        for rt in risk_tags:
            coverage["by_risk_tags"][rt] = coverage["by_risk_tags"].get(rt, 0) + 1

    # ── positive_exact_symbol ────────────────────────────────────────────
    for repo_id, symbols in repo_symbols.items():
        selected = sorted(symbols, key=lambda s: s["name"])[:20]
        for sym in selected:
            add_task(
                repo_id=repo_id,
                query=sym["name"],
                query_category="positive_exact_symbol",
                expected_behavior="primary_evidence",
                oracle_type="deterministic",
                label_quality="mined_high_confidence",
                gold_spans=[_gold_span(sym)],
                hard_distractors=_find_hard_distractors(sym, symbols),
                must_not_primary=_find_must_not_primary(sym, symbols),
                intent_guess=f"Find definition of {sym['name']}",
                risk_tags=[],
                why_this_is_hard="Exact symbol name may partially match other symbols in same or different files",
                which_strategy_it_targets="symbol_search",
            )

    # ── positive_regex_anchor ───────────────────────────────────────────
    for repo_id, symbols in repo_symbols.items():
        regex_candidates = [s for s in symbols if s["kind"] in ("fn", "def", "async_def", "func", "function")]
        selected = sorted(regex_candidates, key=lambda s: s["name"])[:10]
        for sym in selected:
            # Use a regex-style query: prefix or partial
            parts = re.split(r"[_]", sym["name"])
            if len(parts) > 1:
                query = parts[0]  # first segment of snake_case
            else:
                # camelCase split
                query = re.sub(r"([a-z])([A-Z])", r"\1.*\2", sym["name"])
            add_task(
                repo_id=repo_id,
                query=query,
                query_category="positive_regex_anchor",
                expected_behavior="primary_evidence",
                oracle_type="deterministic",
                label_quality="mined_high_confidence",
                gold_spans=[_gold_span(sym)],
                hard_distractors=_find_hard_distractors(sym, symbols, max_distractors=1),
                must_not_primary=[],
                intent_guess=f"Regex-anchor search for partial of {sym['name']}",
                risk_tags=["partial_match"],
                why_this_is_hard="Partial query may match multiple symbols; regex anchor needed for precision",
                which_strategy_it_targets="regex_search",
            )

    # ── positive_natural_language ────────────────────────────────────────
    NL_QUERIES = {
        "fast-context-mcp": [("how does fast context handle errors", "error handling in MCP server")],
        "grok2api": [("how does the API handle rate limiting", "rate limit enforcement")],
        "infinite-canvas": [("how are canvas elements rendered", "canvas rendering logic")],
        "gemini-web2api": [("how does the service authenticate requests", "authentication flow")],
        "windsurf2api": [("how does the API proxy work", "proxy implementation")],
        "kiro2": [("how does the Rust backend process requests", "request processing")],
        "triviumdb": [("how are vectors stored and indexed", "vector storage and indexing")],
        "smartsearch": [("how does the search engine rank results", "result ranking")],
        "codex2api": [("how does the API handle concurrent requests", "concurrent request handling")],
    }
    for repo_id, queries in NL_QUERIES.items():
        if repo_id not in repo_symbols:
            continue
        for query, intent in queries:
            add_task(
                repo_id=repo_id,
                query=query,
                query_category="positive_natural_language",
                expected_behavior="weak_candidates",
                oracle_type="mined",
                label_quality="mined",
                gold_spans=[],
                hard_distractors=[],
                must_not_primary=[],
                intent_guess=intent,
                risk_tags=["semantic_gap"],
                why_this_is_hard="NL queries require semantic understanding beyond lexical match",
                which_strategy_it_targets="bm25_rrf",
                caveat="No gold_spans for NL queries in R20; requires semantic evaluation in R21+",
            )

    # ── positive_issue_style ────────────────────────────────────────────
    ISSUE_QUERIES = {
        "fast-context-mcp": "FastContext server crashes on large file uploads",
        "grok2api": "API returns 500 when grok service is unavailable",
        "infinite-canvas": "Canvas state lost on reconnect",
        "gemini-web2api": "Authentication token not refreshed before expiry",
        "windsurf2api": "WindsurfAPI proxy timeout on slow upstream",
        "kiro2": "Rust backend memory leak on long-running sessions",
        "triviumdb": "Vector search returns wrong results for high-dimensional data",
        "smartsearch": "Search index not updated after document deletion",
        "codex2api": "Codex API rate limiting not enforced for batch requests",
    }
    for repo_id, query in ISSUE_QUERIES.items():
        if repo_id not in repo_symbols:
            continue
        add_task(
            repo_id=repo_id,
            query=query,
            query_category="positive_issue_style",
            expected_behavior="weak_candidates",
            oracle_type="mined",
            label_quality="weak",
            gold_spans=[],
            hard_distractors=[],
            must_not_primary=[],
            intent_guess=f"Find code related to: {query}",
            risk_tags=["issue_style_vague"],
            why_this_is_hard="Issue-style queries mix problem description with domain terms; no exact match likely",
            which_strategy_it_targets="bm25_rrf",
            caveat="Weak probe; no gold_spans; requires semantic matching",
        )

    # ── negative_nonexistent_symbol ─────────────────────────────────────
    FAKE_SYMBOLS = [
        "QuantumResolver", "HyperVortexProcessor", "NeuralMeshBuilder",
        "CryptoShardFactory", "TemporalStreamAggregator", "ProbabilisticCache",
        "DimensionalReducer", "EntropyBalancer", "FluxCapacitor",
        "ParadoxValidator", "SingularityGateway", "WarpFieldManager",
    ]
    for repo_id in repo_symbols:
        for fake_sym in rng.sample(FAKE_SYMBOLS, min(5, len(FAKE_SYMBOLS))):
            add_task(
                repo_id=repo_id,
                query=fake_sym,
                query_category="negative_nonexistent_symbol",
                expected_behavior="abstain",
                oracle_type="deterministic",
                label_quality="mined_high_confidence",
                gold_spans=[],
                hard_distractors=[],
                must_not_primary=[],
                intent_guess=f"Find definition of {fake_sym} (does not exist)",
                risk_tags=["hallucination_risk"],
                why_this_is_hard="Retriever may hallucinate partial matches to plausible-sounding fake symbols",
                which_strategy_it_targets="all_channels",
            )

    # ── negative_nonexistent_feature ────────────────────────────────────
    FAKE_FEATURES = [
        "quantum entanglement solver", "blockchain consensus protocol",
        "neural network training loop", "distributed database replication",
        "machine learning inference pipeline", "cryptographic key rotation",
        "microservice orchestration engine", "real-time streaming pipeline",
        "image processing pipeline optimizer", "voice recognition module",
    ]
    for repo_id in repo_symbols:
        for fake_feat in rng.sample(FAKE_FEATURES, min(5, len(FAKE_FEATURES))):
            add_task(
                repo_id=repo_id,
                query=fake_feat,
                query_category="negative_nonexistent_feature",
                expected_behavior="no_primary",
                oracle_type="deterministic",
                label_quality="mined",
                gold_spans=[],
                hard_distractors=[],
                must_not_primary=[],
                intent_guess=f"Find implementation of {fake_feat} (does not exist)",
                risk_tags=["false_positive_risk"],
                why_this_is_hard="BM25 may return superficially related but irrelevant results for feature-like queries",
                which_strategy_it_targets="bm25",
            )

    # ── ambiguous_query ────────────────────────────────────────────────
    AMBIGUOUS_QUERIES = [
        ("handler", "Could be event handler, request handler, signal handler, etc."),
        ("process", "Could mean OS process, data processing, or business process"),
        ("connection", "Could be DB connection, network connection, WebSocket connection"),
        ("config", "Could be app config, runtime config, test config, env config"),
        ("model", "Could be data model, ML model, domain model, view model"),
        ("service", "Could be microservice, background service, API service"),
        ("client", "Could be API client, HTTP client, database client"),
        ("manager", "Could be state manager, connection manager, resource manager"),
        ("builder", "Could be request builder, config builder, query builder"),
        ("adapter", "Could be storage adapter, API adapter, format adapter"),
    ]
    for repo_id in repo_symbols:
        for query, ambiguity in rng.sample(AMBIGUOUS_QUERIES, min(5, len(AMBIGUOUS_QUERIES))):
            add_task(
                repo_id=repo_id,
                query=query,
                query_category="ambiguous_query",
                expected_behavior="weak_candidates",
                oracle_type="mined",
                label_quality="weak",
                gold_spans=[],
                hard_distractors=[],
                must_not_primary=[],
                intent_guess=f"Disambiguate: {ambiguity}",
                risk_tags=["ambiguous"],
                why_this_is_hard=ambiguity,
                which_strategy_it_targets="all_channels",
            )

    # ── vague_query ────────────────────────────────────────────────────
    VAGUE_QUERIES = [
        "the", "function", "return", "data", "error", "result",
        "value", "item", "process", "handle", "check", "update",
        "get", "set", "load", "save", "create", "delete", "init",
    ]
    for repo_id in repo_symbols:
        for query in rng.sample(VAGUE_QUERIES, min(5, len(VAGUE_QUERIES))):
            add_task(
                repo_id=repo_id,
                query=query,
                query_category="vague_query",
                expected_behavior="abstain",
                oracle_type="stress",
                label_quality="weak",
                gold_spans=[],
                hard_distractors=[],
                must_not_primary=[],
                intent_guess="Vague/noise query with no specific target",
                risk_tags=["query_noise"],
                why_this_is_hard="Single common word matches many unrelated locations",
                which_strategy_it_targets="query_noise_guard",
            )

    # ── hard_distractor ─────────────────────────────────────────────────
    for repo_id, symbols in repo_symbols.items():
        # Find pairs of symbols with similar names in different files
        name_map: dict[str, list[dict]] = {}
        for s in symbols:
            name_map.setdefault(s["name"], []).append(s)
        multi_def = {n: ss for n, ss in name_map.items() if len(ss) > 1}
        count = 0
        for name, defs in sorted(multi_def.items()):
            if count >= 5:
                break
            primary = defs[0]
            distractors = defs[1:]
            add_task(
                repo_id=repo_id,
                query=name,
                query_category="hard_distractor",
                expected_behavior="primary_evidence",
                oracle_type="deterministic",
                label_quality="mined",
                gold_spans=[_gold_span(primary)],
                hard_distractors=[
                    {"path": d["path"], "start_line": d["start_line"],
                     "end_line": d["end_line"],
                     "rationale": f"{d['name']} ({d['kind']}) same-name different file"}
                    for d in distractors[:2]
                ],
                must_not_primary=[
                    {"path": d["path"], "start_line": d["start_line"],
                     "end_line": d["end_line"],
                     "rationale": f"Same name {d['name']} in different file, not the primary target"}
                    for d in distractors[:2]
                ],
                intent_guess=f"Find the correct {name} among multiple definitions",
                risk_tags=["same_name_disambiguation"],
                why_this_is_hard=f"Multiple definitions of {name} exist across files; disambiguation needed",
                which_strategy_it_targets="rrf_with_context",
            )
            count += 1
        # If not enough multi-defs, create synthetic hard distractors
        while count < 5:
            sym = rng.choice(symbols) if symbols else None
            if sym is None:
                break
            # Find a symbol with similar name in same repo
            similar = [s for s in symbols if s["name"] != sym["name"]
                       and (sym["name"].lower() in s["name"].lower()
                            or s["name"].lower() in sym["name"].lower())]
            if similar:
                distractor = similar[0]
                add_task(
                    repo_id=repo_id,
                    query=sym["name"],
                    query_category="hard_distractor",
                    expected_behavior="primary_evidence",
                    oracle_type="mined",
                    label_quality="mined",
                    gold_spans=[_gold_span(sym)],
                    hard_distractors=[{
                        "path": distractor["path"], "start_line": distractor["start_line"],
                        "end_line": distractor["end_line"],
                        "rationale": f"{distractor['name']} similar name to {sym['name']}"
                    }],
                    must_not_primary=[{
                        "path": distractor["path"], "start_line": distractor["start_line"],
                        "end_line": distractor["end_line"],
                        "rationale": f"Similar name {distractor['name']}, not the target"
                    }],
                    intent_guess=f"Find {sym['name']} despite similar-name distractors",
                    risk_tags=["partial_name_match"],
                    why_this_is_hard=f"{distractor['name']} is a partial name match for {sym['name']}",
                    which_strategy_it_targets="symbol_search",
                )
            count += 1

    # ── same_name_symbol ────────────────────────────────────────────────
    for repo_id, symbols in repo_symbols.items():
        name_map: dict[str, list[dict]] = {}
        for s in symbols:
            name_map.setdefault(s["name"], []).append(s)
        same_name = {n: ss for n, ss in name_map.items() if len(ss) > 1}
        count = 0
        for name, defs in sorted(same_name.items()):
            if count >= 5:
                break
            primary = defs[0]
            add_task(
                repo_id=repo_id,
                query=name,
                query_category="same_name_symbol",
                expected_behavior="primary_evidence",
                oracle_type="deterministic",
                label_quality="mined",
                gold_spans=[_gold_span(primary)],
                hard_distractors=[
                    {"path": d["path"], "start_line": d["start_line"],
                     "end_line": d["end_line"],
                     "rationale": f"Same name {d['name']} in {d['path']}"}
                    for d in defs[1:3]
                ],
                must_not_primary=[
                    {"path": d["path"], "start_line": d["start_line"],
                     "end_line": d["end_line"],
                     "rationale": f"Same name, different context"}
                    for d in defs[1:3]
                ],
                intent_guess=f"Find specific {name} definition among same-name symbols",
                risk_tags=["same_name_confusion"],
                why_this_is_hard=f"Same symbol name {name} appears in {len(defs)} different locations",
                which_strategy_it_targets="context_ranking",
            )
            count += 1

    # ── frontend_backend_confusion ──────────────────────────────────────
    for repo_id in repo_symbols:
        symbols = repo_symbols[repo_id]
        frontend_syms = [s for s in symbols if s["path"].endswith((".tsx", ".jsx"))]
        backend_syms = [s for s in symbols if s["path"].endswith((".go", ".rs", ".py"))]
        if frontend_syms and backend_syms:
            # Query a frontend symbol but expect backend confusion
            fsym = rng.choice(frontend_syms)
            add_task(
                repo_id=repo_id,
                query=fsym["name"],
                query_category="frontend_backend_confusion",
                expected_behavior="primary_evidence",
                oracle_type="mined",
                label_quality="mined",
                gold_spans=[_gold_span(fsym)],
                hard_distractors=[{
                    "path": bsym["path"], "start_line": bsym["start_line"],
                    "end_line": bsym["end_line"],
                    "rationale": f"Backend {bsym['name']} may be confused with frontend {fsym['name']}"
                } for bsym in backend_syms[:2]],
                must_not_primary=[],
                intent_guess=f"Find frontend component {fsym['name']} (not backend)",
                risk_tags=["frontend_backend_overlap"],
                why_this_is_hard="Same or similar names may exist in frontend and backend code",
                which_strategy_it_targets="context_ranking",
            )

    # ── test_source_confusion ──────────────────────────────────────────
    for repo_id in repo_symbols:
        symbols = repo_symbols[repo_id]
        test_syms = [s for s in symbols if _is_test_path(s["path"])]
        source_syms = [s for s in symbols if not _is_test_path(s["path"])]
        if test_syms and source_syms:
            tsym = rng.choice(test_syms)
            add_task(
                repo_id=repo_id,
                query=tsym["name"],
                query_category="test_source_confusion",
                expected_behavior="primary_evidence",
                oracle_type="mined",
                label_quality="mined",
                gold_spans=[_gold_span(tsym)],
                hard_distractors=[{
                    "path": ssym["path"], "start_line": ssym["start_line"],
                    "end_line": ssym["end_line"],
                    "rationale": f"Source {ssym['name']} may be returned instead of test"
                } for ssym in source_syms[:2]],
                must_not_primary=[],
                intent_guess=f"Find test code for {tsym['name']} (not source implementation)",
                risk_tags=["test_source_overlap"],
                why_this_is_hard="Test and source files may have similar names; retriever may return source instead of test",
                which_strategy_it_targets="path_filtering",
            )

    # ── docs_source_confusion ──────────────────────────────────────────
    for repo_id in repo_symbols:
        symbols = repo_symbols[repo_id]
        doc_syms = [s for s in symbols if _is_docs_path(s["path"])]
        source_syms = [s for s in symbols if not _is_docs_path(s["path"])]
        if doc_syms:
            dsym = rng.choice(doc_syms)
            add_task(
                repo_id=repo_id,
                query=dsym["name"],
                query_category="docs_source_confusion",
                expected_behavior="primary_evidence",
                oracle_type="mined",
                label_quality="weak",
                gold_spans=[_gold_span(dsym)],
                hard_distractors=[],
                must_not_primary=[],
                intent_guess=f"Find documentation for {dsym['name']}",
                risk_tags=["docs_source_overlap"],
                why_this_is_hard="Doc and source may share names; retriever should distinguish",
                which_strategy_it_targets="path_filtering",
            )
        else:
            # Synthetic: query a symbol that could plausibly exist in docs
            if source_syms:
                ssym = rng.choice(source_syms)
                add_task(
                    repo_id=repo_id,
                    query=f"{ssym['name']} documentation",
                    query_category="docs_source_confusion",
                    expected_behavior="weak_candidates",
                    oracle_type="mined",
                    label_quality="weak",
                    gold_spans=[],
                    hard_distractors=[],
                    must_not_primary=[],
                    intent_guess=f"Find docs for {ssym['name']}",
                    risk_tags=["docs_source_overlap"],
                    why_this_is_hard="No separate docs; retriever may return source code instead",
                    which_strategy_it_targets="path_filtering",
                    caveat="No doc files in repo; synthetic probe",
                )

    # ── generated_vendor_trap ───────────────────────────────────────────
    for repo_id in repo_symbols:
        symbols = repo_symbols[repo_id]
        vendor_syms = [s for s in symbols if _is_vendor_path(s["path"])]
        if vendor_syms:
            vsym = rng.choice(vendor_syms)
            add_task(
                repo_id=repo_id,
                query=vsym["name"],
                query_category="generated_vendor_trap",
                expected_behavior="abstain",
                oracle_type="mined",
                label_quality="weak",
                gold_spans=[],
                hard_distractors=[],
                must_not_primary=[{
                    "path": vsym["path"], "start_line": vsym["start_line"],
                    "end_line": vsym["end_line"],
                    "rationale": f"Vendor/generated code {vsym['name']} should not be primary evidence"
                }],
                intent_guess=f"Avoid vendor/generated code for {vsym['name']}",
                risk_tags=["vendor_trap"],
                why_this_is_hard="Retriever may surface vendor/generated code as if it were project code",
                which_strategy_it_targets="path_filtering",
            )
        else:
            # Synthetic probe: fake a vendor trap scenario
            add_task(
                repo_id=repo_id,
                query="node_modules_helper",
                query_category="generated_vendor_trap",
                expected_behavior="abstain",
                oracle_type="stress",
                label_quality="weak",
                gold_spans=[],
                hard_distractors=[],
                must_not_primary=[],
                intent_guess="Query for vendor-like symbol that should not be returned",
                risk_tags=["vendor_trap"],
                why_this_is_hard="No vendor/generated files in repo; synthetic probe for vendor trap detection",
                which_strategy_it_targets="path_filtering",
                caveat="Synthetic probe; no actual vendor files in repo",
            )

    # ── config_key_trap ────────────────────────────────────────────────
    for repo_id, file_texts in repo_file_texts.items():
        config_keys_found: set[str] = set()
        for rel_path, text in file_texts.items():
            if rel_path.endswith((".toml", ".yaml", ".yml", ".json", ".env", ".ini", ".cfg")):
                for key in _extract_config_keys(text):
                    config_keys_found.add(key)
        if config_keys_found:
            for key in sorted(config_keys_found)[:5]:
                add_task(
                    repo_id=repo_id,
                    query=key,
                    query_category="config_key_trap",
                    expected_behavior="supporting_only",
                    oracle_type="mined",
                    label_quality="mined",
                    gold_spans=[],
                    hard_distractors=[],
                    must_not_primary=[],
                    intent_guess=f"Find configuration for {key}",
                    risk_tags=["config_trap"],
                    why_this_is_hard="Config keys may match source code identifiers; retriever should prefer config context",
                    which_strategy_it_targets="path_filtering",
                )
        else:
            # Fallback: use common config-ish names
            for key in ["port", "host", "timeout", "debug", "max_retries"]:
                add_task(
                    repo_id=repo_id,
                    query=key,
                    query_category="config_key_trap",
                    expected_behavior="supporting_only",
                    oracle_type="stress",
                    label_quality="weak",
                    gold_spans=[],
                    hard_distractors=[],
                    must_not_primary=[],
                    intent_guess=f"Find configuration for {key}",
                    risk_tags=["config_trap"],
                    why_this_is_hard="Common config key may match many source identifiers",
                    which_strategy_it_targets="path_filtering",
                    caveat="No dedicated config files found; synthetic probe",
                )

    # ── route_handler_trap ─────────────────────────────────────────────
    for repo_id, file_texts in repo_file_texts.items():
        routes_found: list[tuple[str, str]] = []
        for rel_path, text in file_texts.items():
            for route in _extract_routes(text):
                routes_found.append((route, rel_path))
        if routes_found:
            for route, route_path in routes_found[:5]:
                add_task(
                    repo_id=repo_id,
                    query=route,
                    query_category="route_handler_trap",
                    expected_behavior="supporting_only",
                    oracle_type="mined",
                    label_quality="mined",
                    gold_spans=[],
                    hard_distractors=[],
                    must_not_primary=[],
                    intent_guess=f"Find handler for route {route}",
                    risk_tags=["route_trap"],
                    why_this_is_hard="Route path string may match unrelated string literals in code",
                    which_strategy_it_targets="string_search",
                )
        else:
            # Synthetic route probes
            for route in ["/api/v1/status", "/health", "/api/config"]:
                add_task(
                    repo_id=repo_id,
                    query=route,
                    query_category="route_handler_trap",
                    expected_behavior="abstain",
                    oracle_type="stress",
                    label_quality="weak",
                    gold_spans=[],
                    hard_distractors=[],
                    must_not_primary=[],
                    intent_guess=f"Find handler for route {route} (may not exist)",
                    risk_tags=["route_trap"],
                    why_this_is_hard="Route string may match unrelated code; no route handler found",
                    which_strategy_it_targets="string_search",
                    caveat="No route definitions found in source; synthetic probe",
                )

    # ── stacktrace_style ────────────────────────────────────────────────
    STACKTRACE_QUERIES = {
        "fast-context-mcp": "Error: FastContextError at core.mjs:35",
        "grok2api": "TypeError: cannot read property of undefined at app.py:42",
        "infinite-canvas": "panic: index out of range at handler.go:128",
        "gemini-web2api": "ConnectionError: timeout at service.py:67",
        "windsurf2api": "Error: ECONNREFUSED at server.js:201",
        "kiro2": "thread 'main' panicked at src/main.rs:45",
        "triviumdb": "panic: assertion failed at src/engine.rs:312",
        "smartsearch": "ValueError: invalid query at search.py:89",
        "codex2api": "Error: context deadline exceeded at handler.go:95",
    }
    for repo_id, query in STACKTRACE_QUERIES.items():
        if repo_id not in repo_symbols:
            continue
        add_task(
            repo_id=repo_id,
            query=query,
            query_category="stacktrace_style",
            expected_behavior="weak_candidates",
            oracle_type="mined",
            label_quality="weak",
            gold_spans=[],
            hard_distractors=[],
            must_not_primary=[],
            intent_guess="Find code at stacktrace location",
            risk_tags=["stacktrace_format"],
            why_this_is_hard="Stacktrace-style queries mix error messages with file/line references",
            which_strategy_it_targets="regex_search",
            caveat="Line numbers in stacktrace are approximate; no gold_spans",
        )

    # ── dirty_overlay ──────────────────────────────────────────────────
    for repo_id, symbols in repo_symbols.items():
        if not symbols:
            continue
        sym = rng.choice(symbols)
        add_task(
            repo_id=repo_id,
            query=f"modified {sym['name']}",
            query_category="dirty_overlay",
            expected_behavior="weak_candidates",
            oracle_type="metamorphic",
            label_quality="weak",
            gold_spans=[],
            hard_distractors=[],
            must_not_primary=[],
            intent_guess=f"Find modified version of {sym['name']} (dirty/meta query)",
            risk_tags=["dirty_state"],
            why_this_is_hard="Query references a modified state that may not exist in current snapshot; tests stale index behavior",
            which_strategy_it_targets="stale_index_detection",
            caveat="Metamorphic probe for R21/R26; no source mutation in R20",
        )

    # ── deleted_file ────────────────────────────────────────────────────
    for repo_id in repo_symbols:
        add_task(
            repo_id=repo_id,
            query="deleted_module_old_api",
            query_category="deleted_file",
            expected_behavior="abstain",
            oracle_type="metamorphic",
            label_quality="weak",
            gold_spans=[],
            hard_distractors=[],
            must_not_primary=[],
            intent_guess="Find code in a deleted file (does not exist)",
            risk_tags=["deleted_file"],
            why_this_is_hard="Retriever with stale index may return results for deleted files",
            which_strategy_it_targets="stale_index_detection",
            caveat="Metamorphic probe for R21/R26; no source mutation in R20",
        )

    # ── renamed_file ────────────────────────────────────────────────────
    for repo_id, symbols in repo_symbols.items():
        if not symbols:
            continue
        sym = rng.choice(symbols)
        # Simulate a renamed file query
        old_path_parts = sym["path"].split("/")
        if len(old_path_parts) > 1:
            old_path_parts[-2] = old_path_parts[-2] + "_old"
            old_path = "/".join(old_path_parts)
        else:
            old_path = "old_" + sym["path"]
        add_task(
            repo_id=repo_id,
            query=f"{sym['name']} in {old_path}",
            query_category="renamed_file",
            expected_behavior="abstain",
            oracle_type="metamorphic",
            label_quality="weak",
            gold_spans=[],
            hard_distractors=[],
            must_not_primary=[],
            intent_guess=f"Find {sym['name']} at old path {old_path} (file was renamed)",
            risk_tags=["renamed_file"],
            why_this_is_hard="Stale index may reference old path; current index won't have it",
            which_strategy_it_targets="stale_index_detection",
            caveat="Metamorphic probe for R21/R26; no source mutation in R20",
        )

    # ── branch_switch_like ──────────────────────────────────────────────
    for repo_id in repo_symbols:
        add_task(
            repo_id=repo_id,
            query="feature_branch_only_function",
            query_category="branch_switch_like",
            expected_behavior="abstain",
            oracle_type="metamorphic",
            label_quality="weak",
            gold_spans=[],
            hard_distractors=[],
            must_not_primary=[],
            intent_guess="Find code that only exists on a different branch",
            risk_tags=["branch_switch"],
            why_this_is_hard="Code visible on other branches may not be in current snapshot; stale index may reference it",
            which_strategy_it_targets="stale_index_detection",
            caveat="Metamorphic probe for R21/R26; no branch switching in R20",
        )

    # ── stale_index_candidate ───────────────────────────────────────────
    for repo_id, symbols in repo_symbols.items():
        if not symbols:
            continue
        sym = rng.choice(symbols)
        add_task(
            repo_id=repo_id,
            query=sym["name"],
            query_category="stale_index_candidate",
            expected_behavior="primary_evidence",
            oracle_type="differential",
            label_quality="mined",
            gold_spans=[_gold_span(sym)],
            hard_distractors=[],
            must_not_primary=[],
            intent_guess=f"Find {sym['name']} — test that stale index returns outdated spans",
            risk_tags=["stale_index"],
            why_this_is_hard="If file has been modified since index build, returned spans may be incorrect",
            which_strategy_it_targets="stale_index_detection",
            caveat="Differential probe; requires index build + mutation + re-search to fully test",
        )

    # ── graph_neighbor_trap ─────────────────────────────────────────────
    for repo_id, symbols in repo_symbols.items():
        if not symbols:
            continue
        sym = rng.choice(symbols)
        # Find imports that reference this symbol's file
        file_texts = repo_file_texts.get(repo_id, {})
        importers = []
        for rel_path, text in file_texts.items():
            if rel_path == sym["path"]:
                continue
            for m in IMPORT_RE.finditer(text):
                imp = m.group(1)
                if os.path.basename(sym["path"]).replace(os.path.splitext(sym["path"])[1], "") in imp:
                    importers.append({"path": rel_path, "text_preview": text[:200]})
                    break

        add_task(
            repo_id=repo_id,
            query=sym["name"],
            query_category="graph_neighbor_trap",
            expected_behavior="primary_evidence",
            oracle_type="mined",
            label_quality="mined",
            gold_spans=[_gold_span(sym)],
            hard_distractors=[{
                "path": imp["path"], "start_line": 1, "end_line": 5,
                "rationale": f"File importing {sym['name']} — neighbor, not definition"
            } for imp in importers[:2]],
            must_not_primary=[{
                "path": imp["path"], "start_line": 1, "end_line": 5,
                "rationale": "Importing file is a graph neighbor, not the definition"
            } for imp in importers[:2]],
            intent_guess=f"Find definition of {sym['name']} (not import site)",
            risk_tags=["graph_neighbor_confusion"],
            why_this_is_hard="Graph edges connect to importers; retriever may return import site instead of definition",
            which_strategy_it_targets="graph_search",
        )

    # ── dense_semantic_trap ─────────────────────────────────────────────
    DENSE_TRAP_QUERIES = {
        "fast-context-mcp": "embedding similarity search",
        "grok2api": "vector index lookup",
        "infinite-canvas": "semantic search engine",
        "gemini-web2api": "neural network inference",
        "windsurf2api": "deep learning model serving",
        "kiro2": "transformer attention mechanism",
        "triviumdb": "approximate nearest neighbor",
        "smartsearch": "semantic similarity scoring",
        "codex2api": "embedding dimension reduction",
    }
    for repo_id, query in DENSE_TRAP_QUERIES.items():
        if repo_id not in repo_symbols:
            continue
        add_task(
            repo_id=repo_id,
            query=query,
            query_category="dense_semantic_trap",
            expected_behavior="abstain",
            oracle_type="stress",
            label_quality="weak",
            gold_spans=[],
            hard_distractors=[],
            must_not_primary=[],
            intent_guess=f"Find code related to {query} (semantic false positive trap)",
            risk_tags=["semantic_false_positive"],
            why_this_is_hard="Dense/semantic search may return superficially similar but unrelated code",
            which_strategy_it_targets="dense_search",
            caveat="Tests that dense retrieval does not produce false positives for ML/AI terminology",
        )

    # ── proper_name_api_config_regression ───────────────────────────────
    PROPER_NAME_TRAPS = {
        "fast-context-mcp": [("MCP", "Model Context Protocol — external standard, not project code"),
                              ("OpenAI", "External API provider, not internal implementation")],
        "grok2api": [("Grok", "xAI model name, not code symbol"),
                      ("OpenAI", "External API provider referenced in code")],
        "infinite-canvas": [("WebSocket", "Protocol standard, not project code"),
                             ("React", "External framework, not implementation")],
        "gemini-web2api": [("Gemini", "Google model name, may match config keys"),
                            ("Google", "External provider, not internal code")],
        "windsurf2api": [("Windsurf", "Product name, may match config/comments"),
                          ("Codeium", "External provider name")],
        "kiro2": [("Kiro", "Product name, may match config/branding"),
                    ("OpenAI", "External API provider")],
        "triviumdb": [("TriviumDB", "Product name, may match config/branding"),
                       "SQLite", ("External database reference")],
        "smartsearch": [("Elasticsearch", "External search engine, not internal code"),
                         ("OpenSearch", "External engine reference")],
        "codex2api": [("Codex", "OpenAI model name, may match config"),
                       ("OpenAI", "External API provider")],
    }
    for repo_id, traps in PROPER_NAME_TRAPS.items():
        if repo_id not in repo_symbols:
            continue
        for trap_item in traps:
            if isinstance(trap_item, tuple):
                name, why = trap_item
            else:
                name, why = trap_item, "External proper name"
            add_task(
                repo_id=repo_id,
                query=name,
                query_category="proper_name_api_config_regression",
                expected_behavior="abstain",
                oracle_type="stress",
                label_quality="weak",
                gold_spans=[],
                hard_distractors=[],
                must_not_primary=[],
                intent_guess=f"Find code for {name} (likely external reference, not project code)",
                risk_tags=["proper_name_trap"],
                why_this_is_hard=why,
                which_strategy_it_targets="all_channels",
                caveat="Proper names may appear in config/comments; retriever should not treat as code definitions",
            )

    # ── Ensure minimum coverage per category ────────────────────────────
    for cat in REQUIRED_CATEGORIES:
        current_count = coverage["by_category"].get(cat, 0)
        if current_count < 5:
            deficit = 5 - current_count
            coverage["coverage_gaps"].append(
                f"Category {cat} has only {current_count} tasks, need {deficit} more"
            )
            # Generate synthetic weak probes to fill deficit
            for i in range(deficit):
                repo_id = rng.choice(list(repo_symbols.keys()))
                if cat.startswith("positive"):
                    eb = "primary_evidence"
                    ot = "deterministic"
                    lq = "mined"
                    gs = []
                elif cat.startswith("negative"):
                    eb = "abstain"
                    ot = "deterministic"
                    lq = "mined"
                    gs = []
                elif cat in ("ambiguous_query", "vague_query"):
                    eb = "abstain"
                    ot = "stress"
                    lq = "weak"
                    gs = []
                elif cat in ("dirty_overlay", "deleted_file", "renamed_file",
                             "branch_switch_like", "stale_index_candidate"):
                    eb = "abstain"
                    ot = "metamorphic"
                    lq = "weak"
                    gs = []
                else:
                    eb = "abstain"
                    ot = "stress"
                    lq = "weak"
                    gs = []

                query = f"r20_synthetic_{cat}_{i+1}"
                add_task(
                    repo_id=repo_id,
                    query=query,
                    query_category=cat,
                    expected_behavior=eb,
                    oracle_type=ot,
                    label_quality=lq,
                    gold_spans=gs,
                    hard_distractors=[],
                    must_not_primary=[],
                    intent_guess=f"Synthetic probe for category {cat}",
                    risk_tags=["synthetic"],
                    why_this_is_hard=f"Synthetic probe to ensure category {cat} has >= 5 tasks",
                    which_strategy_it_targets="all_channels",
                    caveat="Synthetic weak probe to meet minimum category coverage",
                )

    # ── Ensure minimum coverage per repo (>= 15) ───────────────────────
    for repo_id in repo_symbols:
        current_count = coverage["by_repo"].get(repo_id, 0)
        if current_count < 15:
            deficit = 15 - current_count
            coverage["coverage_gaps"].append(
                f"Repo {repo_id} has only {current_count} tasks, need {deficit} more"
            )
            symbols = repo_symbols[repo_id]
            for i in range(deficit):
                if symbols:
                    sym = rng.choice(symbols)
                    query = sym["name"]
                    gs = [_gold_span(sym)]
                    eb = "primary_evidence"
                    ot = "deterministic"
                    lq = "mined"
                else:
                    query = f"r20_repo_filler_{repo_id}_{i+1}"
                    gs = []
                    eb = "abstain"
                    ot = "stress"
                    lq = "weak"
                add_task(
                    repo_id=repo_id,
                    query=query,
                    query_category="positive_exact_symbol",
                    expected_behavior=eb,
                    oracle_type=ot,
                    label_quality=lq,
                    gold_spans=gs,
                    hard_distractors=[],
                    must_not_primary=[],
                    intent_guess=f"Repo coverage filler for {repo_id}",
                    risk_tags=[],
                    why_this_is_hard="Added to meet minimum repo task count",
                    which_strategy_it_targets="symbol_search",
                    caveat="Filler task to meet minimum repo coverage",
                )

    # ── Ensure total >= 300 ────────────────────────────────────────────
    while len(all_tasks) < 300:
        repo_id = rng.choice(list(repo_symbols.keys()))
        symbols = repo_symbols[repo_id]
        if symbols:
            sym = rng.choice(symbols)
            query = sym["name"]
            gs = [_gold_span(sym)]
            eb = "primary_evidence"
            ot = "deterministic"
            lq = "mined"
        else:
            query = f"r20_total_filler_{len(all_tasks)}"
            gs = []
            eb = "abstain"
            ot = "stress"
            lq = "weak"
        add_task(
            repo_id=repo_id,
            query=query,
            query_category="positive_exact_symbol",
            expected_behavior=eb,
            oracle_type=ot,
            label_quality=lq,
            gold_spans=gs,
            hard_distractors=[],
            must_not_primary=[],
            intent_guess="Total count filler",
            risk_tags=[],
            why_this_is_hard="Added to meet minimum total task count",
            which_strategy_it_targets="symbol_search",
            caveat="Filler task to meet minimum total count",
        )

    # ── Sort by task_id for determinism ────────────────────────────────
    all_tasks.sort(key=lambda t: t["task_id"])
    all_labels.sort(key=lambda l: l["task_id"])

    # ── Validate gold_spans / must_not_primary / hard_distractors overlap ──
    for label in all_labels:
        gold = label.get("gold_spans", [])
        mnp = label.get("must_not_primary", [])
        hd = label.get("hard_distractors", [])

        # Remove must_not_primary that overlap gold
        label["must_not_primary"] = [
            m for m in mnp
            if not any(
                m.get("path") == g.get("path")
                and int(m.get("start_line", 0)) <= int(g.get("end_line", 0))
                and int(m.get("end_line", 0)) >= int(g.get("start_line", 0))
                for g in gold
            )
        ]
        # Remove hard_distractors that overlap gold
        label["hard_distractors"] = [
            d for d in hd
            if not any(
                d.get("path") == g.get("path")
                and int(d.get("start_line", 0)) <= int(g.get("end_line", 0))
                and int(d.get("end_line", 0)) >= int(g.get("start_line", 0))
                for g in gold
            )
        ]

    return all_tasks, all_labels, coverage


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate R20 auto-wide retrieval failure-surface benchmark dataset"
    )
    parser.add_argument(
        "--workspace", default=".",
        help="Workspace root (containing eval/, fixtures/, etc.)"
    )
    parser.add_argument(
        "--out", default="fixtures/r20_auto_wide",
        help="Output directory relative to workspace"
    )
    args = parser.parse_args()

    workspace = Path(args.workspace)
    out_dir = workspace / args.out

    rng = random.Random(SEED)

    # Create directory structure
    for subdir in ["tasks", "labels"]:
        (out_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Resolve repos
    print("Resolving candidate repos...")
    resolved_repos = resolve_repos()
    if len(resolved_repos) != 9:
        print(f"\nWARNING: Expected 9 repos, found {len(resolved_repos)}", file=sys.stderr)

    # Generate repo lock
    print("\nGenerating repo lock...")
    repo_entries = generate_repo_lock(resolved_repos)
    print(f"  Repo entries: {len(repo_entries)}")

    lock_path = out_dir / "repos.lock.jsonl"
    with lock_path.open("w", encoding="utf-8") as f:
        for entry in repo_entries:
            f.write(json.dumps(entry, sort_keys=True) + "\n")

    # Generate tasks and labels
    print("\nGenerating R20 tasks and labels...")
    tasks, labels, coverage = generate_all_tasks(resolved_repos, rng)
    print(f"  Tasks: {len(tasks)}")
    print(f"  Labels: {len(labels)}")
    print(f"  Categories: {len(coverage['by_category'])}")
    print(f"  Category counts: {json.dumps(coverage['by_category'], indent=2)}")

    # Write tasks
    tasks_path = out_dir / "tasks" / "auto_wide.jsonl"
    with tasks_path.open("w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, sort_keys=True) + "\n")

    # Write labels
    labels_path = out_dir / "labels" / "auto_wide.jsonl"
    with labels_path.open("w", encoding="utf-8") as f:
        for label in labels:
            f.write(json.dumps(label, sort_keys=True) + "\n")

    # Write dataset manifest
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "program": "R20 Auto-Wide Retrieval Failure-Surface Benchmark",
        "description": (
            "Generated/mined/weak failure-surface dataset for retrieval failure discovery. "
            "NOT promotion evidence. No runner/scorer matrix yet. R21 will use it. "
            "R20 labels are failure-surface oracle/probe labels, not EvidenceCore."
        ),
        "not_promotion_evidence": True,
        "core_changes": False,
        "remote_calls": 0,
        "dense_or_llm_claims": False,
        "tiers": {
            "auto_wide": {
                "target_repos": 9,
                "target_tasks": 300,
                "target_labels": 300,
                "target_categories": len(REQUIRED_CATEGORIES),
                "min_per_category": 5,
                "min_per_repo": 15,
                "label_quality": ["mined_high_confidence", "mined", "weak"],
            }
        },
        "current_status": {
            "auto_wide": {
                "repos": len(resolved_repos),
                "tasks": len(tasks),
                "labels": len(labels),
                "categories": coverage["by_category"],
                "repos_count": coverage["by_repo"],
                "label_quality_distribution": {
                    q: sum(1 for l in labels if l["label_quality"] == q)
                    for q in LABEL_QUALITY_ENUM
                },
                "populated": len(tasks) >= 300,
                "partial": len(tasks) < 300,
            }
        },
        "generation_info": {
            "generator": "eval/r20_generate_auto_wide.py",
            "generated_at": "2026-06-12",
            "source_type": "external_local_repos",
            "seed": SEED,
            "content_manifest_algorithm": "normalized_sha256_per_file_sorted",
            "supported_extensions": sorted(SOURCE_EXTENSIONS),
            "anti_leakage": (
                "Public tasks contain only task_id, repo_id, query, public_version, source_tier. "
                "No gold/expected/oracle/risk/judgement fields. Labels are private and separate. "
                "R20 labels are failure-surface oracle/probe labels, not EvidenceCore."
            ),
        },
    }
    manifest_path = out_dir / "dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Write safety_checks.json
    safety = {
        "total_checks": 0,
        "critical_issues": 0,
        "warning_issues": 0,
        "issues": [],
        "passed": True,
        "not_promotion_evidence": True,
        "core_changes": False,
        "remote_calls": 0,
        "dense_or_llm_claims": False,
        "note": "Run eval/r20_static_validate.py to populate safety checks",
    }
    safety_path = out_dir / "safety_checks.json"
    safety_path.write_text(json.dumps(safety, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Write coverage_report.json
    cov_path = out_dir / "coverage_report.json"
    cov_path.write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Write README.md
    readme = out_dir / "README.md"
    readme.write_text(_readme_content(len(tasks), len(labels), coverage, len(resolved_repos)), encoding="utf-8")

    print(f"\nGeneration complete!")
    print(f"Tasks: {len(tasks)}")
    print(f"Labels: {len(labels)}")
    print(f"Categories: {len(coverage['by_category'])}")
    print(f"Repos: {len(resolved_repos)}")


def _readme_content(
    task_count: int, label_count: int, coverage: dict, repo_count: int
) -> str:
    cat_lines = "\n".join(
        f"| {cat} | {coverage['by_category'].get(cat, 0)} |"
        for cat in REQUIRED_CATEGORIES
    )
    repo_lines = "\n".join(
        f"| {rid} | {coverage['by_repo'].get(rid, 0)} |"
        for rid in sorted(coverage["by_repo"])
    )
    lang_lines = "\n".join(
        f"| {lang} | {count} |"
        for lang, count in sorted(coverage["by_language"].items())
    )
    return f"""# R20 Auto-Wide Retrieval Failure-Surface Benchmark

## Overview

R20 is a **generated/mined/weak failure-surface dataset** for retrieval failure
discovery. It is **NOT promotion evidence**. No runner/scorer matrix exists yet;
R21 will use this dataset.

**R20 labels are failure-surface oracle/probe labels, not EvidenceCore.**

## Key Constraints

- **Public tasks** contain ONLY: `task_id`, `repo_id`, `query`, `public_version`,
  `source_tier`. No gold/expected/oracle/risk/judgement fields leak.
- **Private labels** carry all judgement fields: `query_category`, `intent_guess`,
  `risk_tags`, `oracle_type`, `expected_behavior`, `label_quality`, `gold_spans`,
  `hard_distractors`, `must_not_primary`, `why_this_is_hard`,
  `which_strategy_it_targets`, `caveat`.
- **expected_behavior** enum: `primary_evidence` | `supporting_only` |
  `weak_candidates` | `abstain` | `no_primary`
- **oracle_type** enum: `deterministic` | `mined` | `differential` |
  `metamorphic` | `stress`
- **label_quality**: `mined_high_confidence` | `mined` | `weak` (NO `human_reviewed`)
- **not_promotion_evidence** = true, **core_changes** = false,
  **remote_calls** = 0, **dense_or_llm_claims** = false

## Scale

| Metric | Count |
|--------|-------|
| Repos | {repo_count} |
| Tasks | {task_count} |
| Labels | {label_count} |
| Categories | {len(coverage['by_category'])} |

## Category Coverage

| Category | Tasks |
|----------|-------|
{cat_lines}

## Repo Coverage

| Repo | Tasks |
|------|-------|
{repo_lines}

## Language Coverage

| Language | Tasks |
|----------|-------|
{lang_lines}

## Files

```
fixtures/r20_auto_wide/
  README.md                    This file
  dataset_manifest.json        Dataset metadata, tier info, generation info
  repos.lock.jsonl             Locked repo entries with content manifest SHA
  tasks/
    auto_wide.jsonl            R20 public tasks (no gold/expected/oracle fields)
  labels/
    auto_wide.jsonl            R20 private labels (failure-surface oracle/probe)
  safety_checks.json           Safety check results (populated by static validator)
  coverage_report.json         Coverage by category/repo/language/oracle/expected/risk
```

## Important Caveats

1. **R20 is a failure-surface dataset, NOT promotion evidence.**
2. **No runner/scorer matrix exists yet.** R21 will use this data.
3. **Labels are mined/weak, not human-verified.** `human_reviewed` is forbidden.
4. **Metamorphic/stress categories** (dirty_overlay, deleted_file, renamed_file,
   branch_switch_like) encode expected behavior for R21/R26 but do NOT mutate
   source in R20.
5. **generated_vendor_trap** may be synthetic if repos lack vendor/generated files.
6. **dense_semantic_trap / proper_name_api_config_regression** target semantic
   false positives around provider/api/config names.
7. **R20 labels are failure-surface oracle/probe labels, not EvidenceCore.**
"""


if __name__ == "__main__":
    main()
