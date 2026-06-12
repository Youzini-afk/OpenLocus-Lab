#!/usr/bin/env python3
"""R47 CI Task Generator: repo-lock.json → public tasks JSONL + private labels JSONL.

Deterministic; no network/LLM calls. Uses file manifest paths and source scanning
to auto-generate categories: positive, negative, ambiguous, hard_distractor,
stale-like, dense_quiver_trap.

Public tasks contain ONLY: test_id, repo_id, query, public_version, source.
Labels contain: gold_spans, hard_distractors, must_not_primary, expected_behavior,
source_category, risk_tags, oracle_type, why_this_is_hard,
which_strategy_it_targets as applicable.

Usage:
    python3 eval/ci_generate_tasks.py \\
        --repo-lock eval/ci_repos/repo-lock.json \\
        --out-dir eval/ci_output/tasks
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


# ── Schema ──────────────────────────────────────────────────────────────

SCHEMA_VERSION = "ci-v1"
PUBLIC_VERSION = "0"

SOURCE_EXTENSIONS = {
    ".rs", ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".mjs",
    ".java", ".kt", ".kts", ".cs", ".c", ".h", ".cpp", ".hpp",
    ".cc", ".cxx", ".rb",
}

SKIP_DIR_NAMES = {
    "node_modules", "target", ".git", "dist", "build", ".venv",
    "__pycache__", ".next", ".nuxt", "runs", "fixtures", "eval",
    "docs", ".openlocus", "coverage", ".cache", ".mypy_cache",
    ".pytest_cache", ".tox", "venv", "env", ".env", ".idea",
    ".vscode", "out", "bin", "obj",
}

PRIVATE_FIELDS = frozenset({
    "gold_spans", "gold_paths", "gold_files", "hard_distractors",
    "hard_negatives", "label_quality", "expected_behavior", "oracle_type",
    "must_not_primary", "risk_tags", "query_category", "intent_guess",
    "why_this_is_hard", "which_strategy_it_targets", "source_category",
    "risk_public",
})

PUBLIC_TASK_FIELDS = frozenset({
    "test_id", "repo_id", "query", "public_version", "source",
})

CATEGORIES = [
    "positive", "negative", "ambiguous", "hard_distractor",
    "stale-like", "dense_quiver_trap",
]

# ── Symbol extraction patterns ──────────────────────────────────────────

RUST_STRUCT_RE = re.compile(r"^\s*pub\s+struct\s+(\w+)", re.MULTILINE)
RUST_ENUM_RE = re.compile(r"^\s*pub\s+enum\s+(\w+)", re.MULTILINE)
RUST_FN_RE = re.compile(r"^\s*pub\s+(?:async\s+)?fn\s+(\w+)", re.MULTILINE)
RUST_TRAIT_RE = re.compile(r"^\s*pub\s+trait\s+(\w+)", re.MULTILINE)

PY_CLASS_RE = re.compile(r"^class\s+(\w+)", re.MULTILINE)
PY_DEF_RE = re.compile(r"^def\s+(\w+)", re.MULTILINE)
PY_ASYNC_DEF_RE = re.compile(r"^async\s+def\s+(\w+)", re.MULTILINE)

GO_FUNC_RE = re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)", re.MULTILINE)
GO_TYPE_RE = re.compile(r"^type\s+(\w+)\s+struct", re.MULTILINE)

JS_FUNC_RE = re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE)
JS_CLASS_RE = re.compile(r"(?:export\s+)?(?:default\s+)?class\s+(\w+)", re.MULTILINE)

TS_INTERFACE_RE = re.compile(r"(?:export\s+)?interface\s+(\w+)", re.MULTILINE)
JAVA_TYPE_RE = re.compile(r"^\s*(?:public\s+)?(?:class|interface|enum)\s+(\w+)", re.MULTILINE)
JAVA_METHOD_RE = re.compile(r"^\s*(?:public|protected|private)\s+(?:static\s+)?[\w<>\[\], ?]+\s+(\w+)\s*\(", re.MULTILINE)
KOTLIN_TYPE_RE = re.compile(r"^\s*(?:public\s+)?(?:data\s+)?(?:class|interface|object)\s+(\w+)", re.MULTILINE)
KOTLIN_FUN_RE = re.compile(r"^\s*(?:public\s+)?fun\s+(\w+)\s*\(", re.MULTILINE)
CS_TYPE_RE = re.compile(r"^\s*(?:public|internal)?\s*(?:sealed\s+|abstract\s+|static\s+)?(?:class|interface|struct|enum)\s+(\w+)", re.MULTILINE)
CS_METHOD_RE = re.compile(r"^\s*(?:public|internal|private|protected)\s+(?:static\s+|async\s+)*[\w<>\[\], ?]+\s+(\w+)\s*\(", re.MULTILINE)
C_FUNC_RE = re.compile(r"^\s*(?:static\s+|extern\s+)?[A-Za-z_][\w\s\*:&<>]*\s+(\w+)\s*\([^;]*\)\s*\{", re.MULTILINE)
RUBY_DEF_RE = re.compile(r"^\s*def\s+(?:self\.)?(\w+[!?=]?)", re.MULTILINE)
RUBY_TYPE_RE = re.compile(r"^\s*(?:class|module)\s+([A-Z]\w*)", re.MULTILINE)

TEST_FILE_RE = re.compile(r"(?:test|spec|_test|\.test|\.spec)", re.IGNORECASE)
VENDOR_DIR_RE = re.compile(r"(?:vendor|third_party|generated|dist|\.next|\.nuxt|build)", re.IGNORECASE)
FRONTEND_PATH_RE = re.compile(r"(?:frontend|client|web|ui|components|pages|app/|src/app)", re.IGNORECASE)
BACKEND_PATH_RE = re.compile(r"(?:backend|server|api|routes|controllers|handlers|views)", re.IGNORECASE)


# ── Fake symbols / semantic traps for negative and dense_quiver_trap ───

FAKE_SYMBOLS = [
    "QuantumResolver", "HyperVortexProcessor", "NeuralMeshBuilder",
    "CryptoShardFactory", "TemporalStreamAggregator", "ProbabilisticCache",
    "DimensionalReducer", "EntropyBalancer", "FluxCapacitor",
    "ParadoxValidator", "SingularityGateway", "WarpFieldManager",
    "HolographicIndexer", "TachyonSerializer", "SubspacePartitioner",
]

FAKE_FEATURES = [
    "quantum entanglement solver", "blockchain consensus protocol",
    "neural network training loop", "distributed database replication",
    "machine learning inference pipeline", "cryptographic key rotation",
    "microservice orchestration engine", "real-time streaming pipeline",
]

AMBIGUOUS_WORDS = [
    "handler", "process", "connection", "config", "model",
    "service", "client", "manager", "builder", "adapter",
]

VAGUE_WORDS = [
    "the", "function", "return", "data", "error", "result",
    "value", "item", "process", "handle", "check", "update",
]

DENSE_QUIVER_TRAP_QUERIES = [
    "quiver index rebuild", "TDB vector search optimization",
    "dense embedding reallocation strategy", "QuIVer stale vector purge",
    "TDB collection rebalance", "vector store compaction scheduler",
    "embedding cache invalidation protocol", "dense index hot-swap",
    "QuIVer segment merge policy", "TDB partition pruning strategy",
    "approximate nearest neighbor index tuning",
    "vector dimensionality reduction transform",
    "dense retrieval reranking fusion", "QuIVer query planning optimization",
    "TDB write-ahead log recovery", "embedding storage garbage collection",
    "dense provider failover mechanism", "QuIVer replica synchronization",
    "TDB snapshot isolation guarantee", "vector index incremental update",
]

STALE_LIKE_QUERIES = [
    "deprecated API endpoint", "legacy configuration format",
    "old database schema migration", "outdated cache invalidation",
    "stale index rebuild", "obsolete serialization format",
    "deprecated authentication flow", "legacy event handler",
    "old route definition", "outdated middleware chain",
    "deprecated plugin interface", "legacy data pipeline",
    "obsolete worker protocol", "stale connection pool",
    "deprecated message format", "legacy scheduler config",
]


# ── Helpers ─────────────────────────────────────────────────────────────

def ext_to_language(ext: str) -> str:
    return {
        ".rs": "rust", ".py": "python", ".go": "go",
        ".js": "javascript", ".mjs": "javascript", ".jsx": "javascript",
        ".ts": "typescript", ".tsx": "typescript",
        ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
        ".cs": "csharp", ".c": "c", ".h": "c", ".cpp": "cpp",
        ".hpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".rb": "ruby",
    }.get(ext, "unknown")


def find_source_files(
    repo_path: Path,
    extensions: set[str] | None = None,
) -> list[tuple[str, Path]]:
    if extensions is None:
        extensions = SOURCE_EXTENSIONS
    results: list[tuple[str, Path]] = []
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
                results.append((rel, full))
    results.sort(key=lambda x: x[0])
    return results


def extract_symbols(filepath: Path, repo_root: Path) -> list[dict[str, Any]]:
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
                     (RUST_TRAIT_RE, "trait"), (RUST_FN_RE, "fn")]
    elif ext == ".py":
        patterns = [(PY_CLASS_RE, "class"), (PY_ASYNC_DEF_RE, "async_def"),
                     (PY_DEF_RE, "def")]
    elif ext == ".go":
        patterns = [(GO_FUNC_RE, "func"), (GO_TYPE_RE, "struct")]
    elif ext in (".js", ".mjs", ".jsx"):
        patterns = [(JS_FUNC_RE, "function"), (JS_CLASS_RE, "class")]
    elif ext in (".ts", ".tsx"):
        patterns = [(JS_FUNC_RE, "function"), (JS_CLASS_RE, "class"),
                     (TS_INTERFACE_RE, "interface")]
    elif ext == ".java":
        patterns = [(JAVA_TYPE_RE, "type"), (JAVA_METHOD_RE, "method")]
    elif ext in (".kt", ".kts"):
        patterns = [(KOTLIN_TYPE_RE, "type"), (KOTLIN_FUN_RE, "function")]
    elif ext == ".cs":
        patterns = [(CS_TYPE_RE, "type"), (CS_METHOD_RE, "method")]
    elif ext in (".c", ".h", ".cpp", ".hpp", ".cc", ".cxx"):
        patterns = [(C_FUNC_RE, "function")]
    elif ext == ".rb":
        patterns = [(RUBY_TYPE_RE, "type"), (RUBY_DEF_RE, "method")]
    else:
        return symbols

    for i, line in enumerate(lines, 1):
        for pattern, kind in patterns:
            m = pattern.search(line)
            if m:
                name = m.group(1)
                end_line = min(i + 15, len(lines))
                symbols.append({
                    "name": name, "kind": kind, "path": rel_path,
                    "start_line": i, "end_line": end_line,
                    "language": ext_to_language(ext),
                })
    return symbols


def _test_id(counter: list[int]) -> str:
    tid = f"ci-{counter[0]:05d}"
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
    distractors = []
    name = sym["name"]
    path = sym["path"]
    for s in all_symbols:
        if s["path"] == path and s["name"] != name:
            distractors.append({
                "path": s["path"], "start_line": s["start_line"],
                "end_line": s["end_line"],
                "rationale": f"{s['name']} ({s['kind']}) same file, different from {name}",
            })
            if len(distractors) >= max_distractors:
                break
    if len(distractors) < max_distractors:
        name_lower = name.lower()
        for s in all_symbols:
            if s["path"] != path and (
                name_lower in s["name"].lower() or s["name"].lower() in name_lower
            ):
                distractors.append({
                    "path": s["path"], "start_line": s["start_line"],
                    "end_line": s["end_line"],
                    "rationale": f"{s['name']} has similar name to {name}",
                })
                if len(distractors) >= max_distractors:
                    break
    return distractors


def _is_test_path(rel_path: str) -> bool:
    return bool(TEST_FILE_RE.search(rel_path))


def _is_vendor_path(rel_path: str) -> bool:
    return bool(VENDOR_DIR_RE.search(rel_path))


# ── Load repo-lock.json ────────────────────────────────────────────────

def load_repo_lock(path: Path) -> dict[str, dict[str, Any]]:
    """Load repo-lock.json or repo-lock.jsonl."""
    text = path.read_text(encoding="utf-8")
    # JSONL format: check extension or detect multi-line JSON
    if path.suffix == ".jsonl" or (text.strip().startswith("{") and "\n{" in text):
        repos = {}
        for line in text.splitlines():
            if line.strip():
                entry = json.loads(line)
                repo_id = entry.get("repo_id", "")
                if repo_id:
                    repos[repo_id] = entry
        return repos
    # Single JSON object
    data = json.loads(text)
    # Support {"repos": {...}} wrapper
    if "repos" in data and isinstance(data["repos"], dict):
        return data["repos"]
    # Support a single repo-lock.json object.
    if "repo_id" in data and "source" in data:
        return {data["repo_id"]: data}
    return data


# ── Main generation ─────────────────────────────────────────────────────

def generate_tasks(
    repos: dict[str, dict[str, Any]],
    seed: int = 42,
    max_tasks_per_repo: int | None = None,
) -> tuple[list[dict], list[dict], dict[str, Any]]:
    """Generate CI benchmark tasks and labels from repo-lock."""
    import random
    rng = random.Random(seed)
    counter = [1]
    all_tasks: list[dict] = []
    all_labels: list[dict] = []
    coverage: dict[str, Any] = {"by_category": {}, "by_repo": {}, "by_risk_tag": {}}

    # Collect symbols per repo
    repo_symbols: dict[str, list[dict]] = {}
    repo_files: dict[str, list[tuple[str, Path]]] = {}

    for repo_id, entry in repos.items():
        source = entry.get("source", {})
        source_type = source.get("type", "")
        if source_type in ("local_absolute_path", "github_public"):
            repo_path = Path(source.get("path", ""))
        else:
            continue
        if not repo_path.exists():
            continue

        extensions = set(entry.get("metadata", {}).get("extensions", list(SOURCE_EXTENSIONS)))
        source_files = find_source_files(repo_path, extensions)
        repo_files[repo_id] = source_files

        symbols: list[dict[str, Any]] = []
        for rel, full_path in source_files:
            syms = extract_symbols(full_path, repo_path)
            symbols.extend(syms)

        repo_symbols[repo_id] = symbols
        coverage["by_repo"][repo_id] = 0

    repo_ids = sorted(repo_symbols.keys())
    if not repo_ids:
        print("WARNING: No repos resolved with symbols.", file=sys.stderr)
        return [], [], coverage

    def add_task(
        repo_id: str,
        query: str,
        source_category: str,
        expected_behavior: str,
        oracle_type: str,
        risk_tags: list[str] | None = None,
        why_this_is_hard: str = "",
        which_strategy_it_targets: str = "",
        gold_spans: list[dict] | None = None,
        hard_distractors: list[dict] | None = None,
        must_not_primary: list[dict] | None = None,
    ) -> None:
        if max_tasks_per_repo is not None and coverage["by_repo"].get(repo_id, 0) >= max_tasks_per_repo:
            return
        risk_tags = risk_tags or []
        gold_spans = gold_spans or []
        hard_distractors = hard_distractors or []
        must_not_primary = must_not_primary or []
        tid = _test_id(counter)
        all_tasks.append({
            "test_id": tid,
            "repo_id": repo_id,
            "query": query,
            "public_version": PUBLIC_VERSION,
            "source": "ci_harness",
        })
        all_labels.append({
            "test_id": tid,
            "repo_id": repo_id,
            "query": query,
            "source_category": source_category,
            "expected_behavior": expected_behavior,
            "oracle_type": oracle_type,
            "risk_tags": risk_tags,
            "gold_spans": gold_spans,
            "hard_distractors": hard_distractors,
            "must_not_primary": must_not_primary,
            "why_this_is_hard": why_this_is_hard,
            "which_strategy_it_targets": which_strategy_it_targets,
        })
        coverage["by_category"][source_category] = coverage["by_category"].get(source_category, 0) + 1
        coverage["by_repo"][repo_id] = coverage["by_repo"].get(repo_id, 0) + 1
        for tag in risk_tags:
            coverage["by_risk_tag"][tag] = coverage["by_risk_tag"].get(tag, 0) + 1

    # ── Category: positive ────────────────────────────────────────────
    for rid in repo_ids:
        symbols = repo_symbols[rid]
        for sym in symbols[:20]:
            distractors = _find_hard_distractors(sym, symbols)
            add_task(
                repo_id=rid,
                query=sym["name"],
                source_category="positive",
                expected_behavior="primary_evidence",
                oracle_type="deterministic",
                risk_tags=["exact_symbol_match"],
                why_this_is_hard="Exact symbol name; should be easily retrievable",
                which_strategy_it_targets="symbol",
                gold_spans=[_gold_span(sym)],
                hard_distractors=distractors,
            )

    # ── Category: negative ────────────────────────────────────────────
    all_fake = FAKE_SYMBOLS + FAKE_FEATURES
    for i, fake in enumerate(all_fake):
        rid = repo_ids[i % len(repo_ids)]
        if " " in fake:
            eb = "no_primary"
            wst = "bm25"
        else:
            eb = "abstain"
            wst = "all_channels"
        add_task(
            repo_id=rid,
            query=fake,
            source_category="negative",
            expected_behavior=eb,
            oracle_type="deterministic",
            risk_tags=["hallucination_risk"],
            why_this_is_hard="Query references non-existent symbol/feature; retriever may hallucinate",
            which_strategy_it_targets=wst,
        )

    # ── Category: ambiguous ──────────────────────────────────────────
    all_amb = AMBIGUOUS_WORDS + VAGUE_WORDS
    for i, word in enumerate(all_amb):
        rid = repo_ids[i % len(repo_ids)]
        if word in AMBIGUOUS_WORDS:
            eb = "weak_candidates"
            wst = "all_channels"
        else:
            eb = "abstain"
            wst = "query_noise_guard"
        add_task(
            repo_id=rid,
            query=word,
            source_category="ambiguous",
            expected_behavior=eb,
            oracle_type="stress",
            risk_tags=["ambiguous"],
            why_this_is_hard="Vague/ambiguous query matches many unrelated locations",
            which_strategy_it_targets=wst,
        )

    # ── Category: hard_distractor ────────────────────────────────────
    for rid in repo_ids:
        symbols = repo_symbols[rid]
        name_map: dict[str, list[dict]] = {}
        for s in symbols:
            name_map.setdefault(s["name"], []).append(s)
        same_name = {n: ss for n, ss in name_map.items() if len(ss) > 1}
        for name, defs in list(same_name.items())[:10]:
            primary = defs[0]
            distractors = [
                {"path": d["path"], "start_line": d["start_line"],
                 "end_line": d["end_line"],
                 "rationale": f"Same name {d['name']} in {d['path']}"}
                for d in defs[1:3]
            ]
            mnp = [
                {"path": d["path"], "start_line": d["start_line"],
                 "end_line": d["end_line"],
                 "rationale": "Same name, different context"}
                for d in defs[1:3]
            ]
            add_task(
                repo_id=rid,
                query=name,
                source_category="hard_distractor",
                expected_behavior="primary_evidence",
                oracle_type="deterministic",
                risk_tags=["same_name_disambiguation"],
                why_this_is_hard=f"Multiple definitions of {name} exist; disambiguation needed",
                which_strategy_it_targets="symbol_search",
                gold_spans=[_gold_span(primary)],
                hard_distractors=distractors,
                must_not_primary=mnp,
            )

        # R49: source/test confusion. Prefer production definitions as gold and
        # same-name test definitions as must-not-primary distractors.
        for name, defs in list(name_map.items())[:80]:
            prod_defs = [d for d in defs if not _is_test_path(d["path"])]
            test_defs = [d for d in defs if _is_test_path(d["path"])]
            if not prod_defs or not test_defs:
                continue
            primary = prod_defs[0]
            distractors = [
                {"path": d["path"], "start_line": d["start_line"],
                 "end_line": d["end_line"],
                 "rationale": f"Test definition named {d['name']} must not outrank source"}
                for d in test_defs[:2]
            ]
            add_task(
                repo_id=rid,
                query=name,
                source_category="hard_distractor",
                expected_behavior="primary_evidence",
                oracle_type="deterministic",
                risk_tags=["test_source_confusion", "same_name_symbol"],
                why_this_is_hard=f"{name} exists in source and tests; source should remain primary",
                which_strategy_it_targets="symbol_search",
                gold_spans=[_gold_span(primary)],
                hard_distractors=distractors,
                must_not_primary=distractors,
            )

        # R49: frontend/backend confusion. Use same-name symbols across UI/client
        # and server/API paths when available; keep backend/API as gold.
        for name, defs in list(name_map.items())[:100]:
            backend_defs = [d for d in defs if BACKEND_PATH_RE.search(d["path"])]
            frontend_defs = [d for d in defs if FRONTEND_PATH_RE.search(d["path"])]
            if not backend_defs or not frontend_defs:
                continue
            primary = backend_defs[0]
            distractors = [
                {"path": d["path"], "start_line": d["start_line"],
                 "end_line": d["end_line"],
                 "rationale": f"Frontend/client definition named {d['name']} is a distractor"}
                for d in frontend_defs[:2]
            ]
            add_task(
                repo_id=rid,
                query=name,
                source_category="hard_distractor",
                expected_behavior="primary_evidence",
                oracle_type="deterministic",
                risk_tags=["frontend_backend_confusion", "same_name_symbol"],
                why_this_is_hard=f"{name} exists in frontend/client and backend/API paths",
                which_strategy_it_targets="symbol_search",
                gold_spans=[_gold_span(primary)],
                hard_distractors=distractors,
                must_not_primary=distractors,
            )

        # R49: generated/vendor confusion. Prefer first-party definitions as gold
        # and same-name generated/vendor definitions as must-not-primary.
        for name, defs in list(name_map.items())[:120]:
            first_party_defs = [d for d in defs if not _is_vendor_path(d["path"])]
            vendor_defs = [d for d in defs if _is_vendor_path(d["path"])]
            if not first_party_defs or not vendor_defs:
                continue
            primary = first_party_defs[0]
            distractors = [
                {"path": d["path"], "start_line": d["start_line"],
                 "end_line": d["end_line"],
                 "rationale": f"Generated/vendor definition named {d['name']} is a distractor"}
                for d in vendor_defs[:2]
            ]
            add_task(
                repo_id=rid,
                query=name,
                source_category="hard_distractor",
                expected_behavior="primary_evidence",
                oracle_type="deterministic",
                risk_tags=["generated_vendor", "same_name_symbol"],
                why_this_is_hard=f"{name} exists in first-party and generated/vendor-like paths",
                which_strategy_it_targets="symbol_search",
                gold_spans=[_gold_span(primary)],
                hard_distractors=distractors,
                must_not_primary=distractors,
            )

    # ── Category: stale-like ─────────────────────────────────────────
    for i, query in enumerate(STALE_LIKE_QUERIES):
        rid = repo_ids[i % len(repo_ids)]
        add_task(
            repo_id=rid,
            query=query,
            source_category="stale-like",
            expected_behavior="abstain",
            oracle_type="stress",
            risk_tags=["stale_index_like", "stale_index_confusion"],
            why_this_is_hard="Query references deprecated/stale concepts; retriever may return outdated matches",
            which_strategy_it_targets="bm25",
        )

    # ── Category: dense_quiver_trap ──────────────────────────────────
    for i, query in enumerate(DENSE_QUIVER_TRAP_QUERIES):
        rid = repo_ids[i % len(repo_ids)]
        add_task(
            repo_id=rid,
            query=query,
            source_category="dense_quiver_trap",
            expected_behavior="abstain",
            oracle_type="stress",
            risk_tags=["dense_false_positive", "quiver_not_implemented"],
            why_this_is_hard="Query references vector/QuIVer features that do not exist; dense search may hallucinate",
            which_strategy_it_targets="dense_mock",
        )

    return all_tasks, all_labels, coverage


def validate_public_tasks(tasks: list[dict]) -> list[str]:
    """Ensure public tasks contain only allowed fields."""
    issues: list[str] = []
    for task in tasks:
        for key in task:
            if key not in PUBLIC_TASK_FIELDS:
                issues.append(
                    f"CRITICAL: Public task {task.get('test_id', '?')} contains "
                    f"private field '{key}'"
                )
        for pf in PRIVATE_FIELDS:
            if pf in task:
                issues.append(
                    f"CRITICAL: Public task {task.get('test_id', '?')} contains "
                    f"forbidden private field '{pf}'"
                )
    return issues


def write_jsonl(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="R47 CI Task Generator")
    parser.add_argument("--repo-lock", required=True, help="Path to repo-lock.json")
    parser.add_argument("--out-dir", required=True, help="Output directory for tasks/ and labels/")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic seed")
    parser.add_argument(
        "--max-tasks-per-repo",
        type=int,
        default=None,
        help="Optional cap for generated tasks per repo",
    )
    parser.add_argument(
        "--no-labels",
        action="store_true",
        help="Write public tasks/coverage only; use before RUN phase so labels do not exist yet",
    )
    args = parser.parse_args()

    repo_lock_path = Path(args.repo_lock)
    if not repo_lock_path.exists():
        print(f"ERROR: repo-lock not found: {repo_lock_path}", file=sys.stderr)
        sys.exit(1)

    repos = load_repo_lock(repo_lock_path)
    print(f"Loaded {len(repos)} repos from {repo_lock_path}")

    tasks, labels, coverage = generate_tasks(
        repos,
        seed=args.seed,
        max_tasks_per_repo=args.max_tasks_per_repo,
    )
    print(f"Generated {len(tasks)} tasks, {len(labels)} labels")

    # Validate public tasks have no private fields
    issues = validate_public_tasks(tasks)
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out_dir)
    tasks_dir = out_dir / "tasks"
    labels_dir = out_dir / "labels"

    write_jsonl(tasks_dir / "ci_tasks.jsonl", tasks)
    if not args.no_labels:
        write_jsonl(labels_dir / "ci_labels.jsonl", labels)

    # Write coverage summary
    coverage["schema_version"] = SCHEMA_VERSION
    coverage["total_tasks"] = len(tasks)
    coverage["total_labels"] = len(labels)
    coverage["public_field_scan"] = "clean" if not issues else "FAILED"
    (out_dir / "coverage.json").write_text(
        json.dumps(coverage, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Tasks written to {tasks_dir / 'ci_tasks.jsonl'}")
    if args.no_labels:
        print("Labels not written (--no-labels)")
    else:
        print(f"Labels written to {labels_dir / 'ci_labels.jsonl'}")
    print(f"Coverage: {json.dumps(coverage['by_category'], indent=2)}")


if __name__ == "__main__":
    main()
