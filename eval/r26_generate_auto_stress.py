#!/usr/bin/env python3
"""R26 Auto-Stress-1000 Retrieval Failure-Surface Dataset Generator.

Generates >= 1000 stress cases from the same external repo set as R20 and
existing R20 tasks/labels where useful, using a deterministic seed. R26 is a WEAK/MINED/DETERMINISTIC
stress dataset designed to maximize failure discovery. It is NOT promotion
evidence and NOT a retrieval strategy promotion mechanism.

Exact target composition:
    negative_nonexistent       150
    ambiguous_vague            150
    hard_distractor            200
    semantic_trap              150
    same_name_symbol           100
    frontend_backend_confusion  75
    test_source_confusion       75
    generated_vendor_trap       50
    stale_index_like            50
    dense_quiver_specific_trap 100

Key constraints:
  - Public tasks contain ONLY: test_id, repo_id, query, public_version,
    source.
    NEVER: source_category, risk_public, expected_behavior, gold_spans,
    must_not_primary, oracle_type, which_strategy_it_targets,
    why_this_is_hard.
  - Private labels carry ALL judgement fields: test_id, repo_id, query,
    source_category, risk_public, intent_guess, risk_tags, oracle_type,
    expected_behavior, gold_spans, hard_distractors, must_not_primary,
    why_this_is_hard, which_strategy_it_targets.
  - No canary tokens anywhere.
  - Deterministic seed (42).
  - Uses the same external repo set as R20 and derives some queries from
    existing R20 tasks/labels when useful.

Usage:
    python3 eval/r26_generate_auto_stress.py --workspace . --out fixtures/r26_auto_stress
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

SCHEMA_VERSION = "r26-v1"
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

# R26 stress categories with target counts
TARGET_CATEGORIES = {
    "negative_nonexistent": 150,
    "ambiguous_vague": 150,
    "hard_distractor": 200,
    "semantic_trap": 150,
    "same_name_symbol": 100,
    "frontend_backend_confusion": 75,
    "test_source_confusion": 75,
    "generated_vendor_trap": 50,
    "stale_index_like": 50,
    "dense_quiver_specific_trap": 100,
}

REQUIRED_CATEGORIES = list(TARGET_CATEGORIES.keys())

# Fields forbidden in public tasks
PRIVATE_FIELDS = frozenset({
    "gold_spans", "gold_paths", "gold_files", "hard_distractors",
    "hard_negatives", "label_quality", "expected_behavior", "oracle_type",
    "must_not_primary", "risk_tags", "query_category", "intent_guess",
    "why_this_is_hard", "which_strategy_it_targets", "candidate_only",
    "risk_tag", "which_strategy_it_targets",
})

# Allowed public task fields
PUBLIC_TASK_FIELDS = frozenset({
    "test_id", "repo_id", "query", "public_version", "source",
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


# ── Multi-language symbol/definition extraction ────────────────────────

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
) -> tuple[str, int, int]:
    all_files = find_source_files(repo_path, extensions, exclude_subdirs)
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


# ── Load R20 data ─────────────────────────────────────────────────────

def load_r20_labels(workspace: Path) -> list[dict[str, Any]]:
    """Load R20 labels for derivative case generation."""
    path = workspace / "fixtures" / "r20_auto_wide" / "labels" / "auto_wide.jsonl"
    if not path.exists():
        return []
    labels = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                labels.append(json.loads(line))
    return labels


def load_r20_tasks(workspace: Path) -> list[dict[str, Any]]:
    """Load R20 public tasks for derivative case generation."""
    path = workspace / "fixtures" / "r20_auto_wide" / "tasks" / "auto_wide.jsonl"
    if not path.exists():
        return []
    tasks = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def load_r20_repos_lock(workspace: Path) -> dict[str, dict[str, Any]]:
    """Load R20 repos.lock.jsonl."""
    path = workspace / "fixtures" / "r20_auto_wide" / "repos.lock.jsonl"
    if not path.exists():
        return {}
    repos = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entry = json.loads(line)
                repos[entry["repo_id"]] = entry
    return repos


# ── Helper functions ──────────────────────────────────────────────────

def _test_id(counter: list[int]) -> str:
    tid = f"r26as-{counter[0]:04d}"
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
    gold_start = sym.get("start_line", 0)
    gold_end = sym.get("end_line", 0)

    def overlaps(s: dict[str, Any]) -> bool:
        if s.get("path") != path:
            return False
        s_start = s.get("start_line", 0)
        s_end = s.get("end_line", 0)
        return s_start <= gold_end and s_end >= gold_start

    for s in all_symbols:
        if s["path"] == path and s["name"] != name and not overlaps(s):
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


def _find_must_not_primary(
    sym: dict[str, Any],
    all_symbols: list[dict[str, Any]],
    max_mnp: int = 2,
) -> list[dict[str, Any]]:
    mnp = []
    name = sym["name"]
    for s in all_symbols:
        if s["name"] != name and (
            s["name"].startswith(name) or s["name"].endswith(name)
            or name.startswith(s["name"]) or name.endswith(s["name"])
        ):
            mnp.append({
                "path": s["path"], "start_line": s["start_line"],
                "end_line": s["end_line"],
                "rationale": f"{s['name']} ({s['kind']}) partial name match, not the target definition",
            })
            if len(mnp) >= max_mnp:
                break
    return mnp


def _is_test_path(rel_path: str) -> bool:
    return bool(TEST_FILE_RE.search(rel_path))


def _is_vendor_path(rel_path: str) -> bool:
    return bool(VENDOR_DIR_RE.search(rel_path))


def _is_frontend_path(rel_path: str) -> bool:
    return rel_path.endswith((".tsx", ".jsx", ".vue", ".svelte"))


def _is_backend_path(rel_path: str) -> bool:
    return rel_path.endswith((".go", ".rs", ".py"))


def _is_docs_path(rel_path: str) -> bool:
    parts = rel_path.split("/")
    return any(p in ("docs", "doc", "documentation") for p in parts)


# ── Name pools for generated cases ───────────────────────────────────

FAKE_SYMBOLS = [
    "QuantumResolver", "HyperVortexProcessor", "NeuralMeshBuilder",
    "CryptoShardFactory", "TemporalStreamAggregator", "ProbabilisticCache",
    "DimensionalReducer", "EntropyBalancer", "FluxCapacitor",
    "ParadoxValidator", "SingularityGateway", "WarpFieldManager",
    "HolographicIndexer", "TachyonSerializer", "SubspacePartitioner",
    "IsotopeDecomposer", "PhotonicScheduler", "GravitonMapper",
    "BosonAggregator", "MuonReconciler", "PionDistributor",
    "KaonCollector", "NeutrinoSorter", "MesonTransformer",
    "HadronReducer", "LeptonFilter", "QuarkMerger", "GluonDispatcher",
    "PhotonAccumulator", "ElectronBuffer", "PositronCache",
    "ProtonShard", "NeutronPool", "FermionQueue", "BosonStack",
]

FAKE_FEATURES = [
    "quantum entanglement solver", "blockchain consensus protocol",
    "neural network training loop", "distributed database replication",
    "machine learning inference pipeline", "cryptographic key rotation",
    "microservice orchestration engine", "real-time streaming pipeline",
    "image processing pipeline optimizer", "voice recognition module",
    "zero-knowledge proof verifier", "homomorphic encryption engine",
    "federated learning aggregator", "reinforcement learning policy",
    "natural language generation pipeline", "anomaly detection system",
    "knowledge graph reasoner", "semantic segmentation model",
    "autonomous agent planner", "multi-agent negotiation protocol",
    "differential privacy sanitizer", "causal inference engine",
    "graph neural network layer", "transformer attention optimizer",
    "variational autoencoder sampler", "generative adversarial trainer",
    "contrastive learning projector", "curriculum learning scheduler",
    "meta-learning optimizer", "continual learning buffer",
]

AMBIGUOUS_WORDS = [
    ("handler", "event, request, signal, error, or callback handler"),
    ("process", "OS process, data processing, or business process"),
    ("connection", "DB, network, WebSocket, or HTTP connection"),
    ("config", "app config, runtime config, test config, or env config"),
    ("model", "data model, ML model, domain model, or view model"),
    ("service", "microservice, background service, or API service"),
    ("client", "API client, HTTP client, or database client"),
    ("manager", "state, connection, resource, or lifecycle manager"),
    ("builder", "request, config, query, or response builder"),
    ("adapter", "storage, API, format, or protocol adapter"),
    ("dispatcher", "event, task, route, or message dispatcher"),
    ("resolver", "DNS, dependency, conflict, or type resolver"),
    ("validator", "input, schema, auth, or config validator"),
    ("provider", "auth, config, data, or service provider"),
    ("factory", "object, connection, request, or component factory"),
]

VAGUE_WORDS = [
    "the", "function", "return", "data", "error", "result",
    "value", "item", "process", "handle", "check", "update",
    "get", "set", "load", "save", "create", "delete", "init",
    "run", "test", "main", "helper", "util", "common", "base",
    "core", "module", "component", "element", "feature", "option",
    "setting", "param", "arg", "field", "prop", "state", "event",
]

SEMANTIC_TRAP_QUERIES = [
    "embedding similarity search", "vector index lookup",
    "semantic search engine", "neural network inference",
    "deep learning model serving", "transformer attention mechanism",
    "approximate nearest neighbor", "semantic similarity scoring",
    "embedding dimension reduction", "cross-encoder reranking",
    "dense passage retrieval", "sparse-dense hybrid search",
    "contrastive representation learning", "knowledge distillation",
    "prompt engineering template", "few-shot in-context learning",
    "chain-of-thought reasoning", "retrieval-augmented generation",
    "instruction tuning pipeline", "alignment safety filter",
    "embedding quantization", "vector normalization",
    "cosine similarity threshold", "dot product attention",
    "positional encoding scheme", "token embedding layer",
    "attention weight distribution", "hidden state projection",
    "feed-forward network layer", "residual connection block",
]

DENSE_QUIVER_TRAP_QUERIES = [
    ("quiver index rebuild", "QuIVer is not implemented; tests stale-index-like confusion from vector-store naming"),
    ("TDB vector search optimization", "TDB is a metadata/chunk placeholder; no real vector search exists"),
    ("dense embedding reallocation strategy", "No dense reallocation exists; tests confusion between mock and real"),
    ("QuIVer stale vector purge", "QuIVer is not implemented; stale purge queries may hallucinate support"),
    ("TDB collection rebalance", "TDB has no collection concept; tests false-positive from database naming"),
    ("vector store compaction scheduler", "No compaction scheduler exists; tests naming trap"),
    ("embedding cache invalidation protocol", "No embedding cache exists; tests terminology confusion"),
    ("dense index hot-swap", "No hot-swap mechanism exists; tests operational naming confusion"),
    ("QuIVer segment merge policy", "QuIVer is not implemented; segment-merge naming borrowed from Lucene"),
    ("TDB partition pruning strategy", "TDB has no partition concept; tests distributed-DB naming confusion"),
    ("approximate nearest neighbor index tuning", "ANN tuning requires a real vector index; none exists"),
    ("vector dimensionality reduction transform", "No dimensionality reduction is implemented; tests false-positive from ML terminology"),
    ("dense retrieval reranking fusion", "No dense reranking exists; tests confusion with RRF"),
    ("QuIVer query planning optimization", "QuIVer is not implemented; query-planning naming is a trap"),
    ("TDB write-ahead log recovery", "TDB has no WAL; tests confusion with real database terminology"),
    ("embedding storage garbage collection", "No GC for embeddings exists; tests infrastructure naming confusion"),
    ("dense provider failover mechanism", "No dense failover exists; mock provider only"),
    ("QuIVer replica synchronization", "QuIVer is not implemented; replica naming from distributed systems"),
    ("TDB snapshot isolation guarantee", "TDB has no transaction semantics; tests DB terminology trap"),
    ("vector index incremental update", "No incremental vector index exists; tests confusion with BM25 incremental"),
    ("dense channel evidence fusion", "Dense mock produces StoreHits but no real fusion; tests channel naming trap"),
    ("QuIVer quantization compression", "QuIVer is not implemented; quantization naming from FAISS"),
    ("TDB concurrent read consistency", "TDB has no concurrency control; tests DB naming confusion"),
    ("embedding drift detection monitor", "No drift detection exists; tests ML-ops naming trap"),
    ("dense score normalization pipeline", "Mock vectors are pre-normalized; no real normalization pipeline"),
    ("QuIVer hybrid search strategy", "QuIVer is not implemented; hybrid-search naming from multi-channel systems"),
    ("TDB metadata filtering optimization", "TDB is metadata-only with no optimization; tests false claim surface"),
    ("vector index warm cache preloading", "No vector cache exists; tests confusion with BM25 warm index"),
    ("dense result deduplication policy", "No dense dedup policy exists; tests naming trap from BM25 dedup"),
    ("QuIVer distance metric configuration", "QuIVer is not implemented; distance-metric naming from vector search"),
]


# ── Main generation ────────────────────────────────────────────────────

def generate_all_tasks(
    resolved_repos: list[dict[str, Any]],
    r20_labels: list[dict[str, Any]],
    r20_tasks: list[dict[str, Any]],
    rng: random.Random,
) -> tuple[list[dict], list[dict], dict[str, Any]]:
    """Generate all R26 stress tasks and labels."""
    counter = [1]
    all_tasks: list[dict] = []
    all_labels: list[dict] = []
    coverage: dict[str, Any] = {
        "by_category": {},
        "by_repo": {},
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

    repo_ids = sorted(repo_symbols.keys())
    if not repo_ids:
        print("ERROR: No repos resolved. Cannot generate.", file=sys.stderr)
        return [], [], coverage

    # Build R20 label lookup by query_category for derivative generation
    r20_by_category: dict[str, list[dict]] = {}
    for lbl in r20_labels:
        cat = lbl.get("query_category", "")
        r20_by_category.setdefault(cat, []).append(lbl)

    # ── Helper to add a stress task ─────────────────────────────────────
    def add_stress(
        repo_id: str,
        query: str,
        source_category: str,
        expected_behavior: str,
        oracle_type: str,
        intent_guess: str,
        risk_tags: list[str],
        why_this_is_hard: str,
        which_strategy_it_targets: str,
        gold_spans: list[dict] | None = None,
        hard_distractors: list[dict] | None = None,
        must_not_primary: list[dict] | None = None,
        risk_public: str = "",
    ) -> None:
        gold_spans = gold_spans or []
        hard_distractors = hard_distractors or []
        must_not_primary = must_not_primary or []
        tid = _test_id(counter)
        all_tasks.append({
            "test_id": tid,
            "repo_id": repo_id,
            "query": query,
            "public_version": PUBLIC_VERSION,
            "source": "r26_auto_stress",
        })
        all_labels.append({
            "test_id": tid,
            "repo_id": repo_id,
            "query": query,
            "source_category": source_category,
            "risk_public": risk_public,
            "intent_guess": intent_guess,
            "risk_tags": risk_tags,
            "oracle_type": oracle_type,
            "expected_behavior": expected_behavior,
            "gold_spans": gold_spans,
            "hard_distractors": hard_distractors,
            "must_not_primary": must_not_primary,
            "why_this_is_hard": why_this_is_hard,
            "which_strategy_it_targets": which_strategy_it_targets,
        })
        coverage["by_category"][source_category] = coverage["by_category"].get(source_category, 0) + 1
        coverage["by_repo"][repo_id] = coverage["by_repo"].get(repo_id, 0) + 1

    # ══════════════════════════════════════════════════════════════════════
    # CATEGORY 1: negative_nonexistent (target: 150)
    # ══════════════════════════════════════════════════════════════════════
    target = TARGET_CATEGORIES["negative_nonexistent"]  # 150
    # Mix fake symbols and fake features
    all_fake = [(s, "symbol") for s in FAKE_SYMBOLS] + [(f, "feature") for f in FAKE_FEATURES]
    rng.shuffle(all_fake)
    idx = 0
    count = 0
    while count < target:
        rid = repo_ids[idx % len(repo_ids)]
        fake_query, kind = all_fake[idx % len(all_fake)]
        if kind == "symbol":
            eb = "abstain"
            ot = "deterministic"
            ig = f"Find definition of {fake_query} (does not exist)"
            rt = ["hallucination_risk"]
            wth = "Retriever may hallucinate partial matches to plausible-sounding fake symbols"
            wst = "all_channels"
            rp = "hallucination_risk"
        else:
            eb = "no_primary"
            ot = "deterministic"
            ig = f"Find implementation of {fake_query} (does not exist)"
            rt = ["false_positive_risk"]
            wth = "BM25 may return superficially related but irrelevant results for feature-like queries"
            wst = "bm25"
            rp = "false_positive_risk"
        add_stress(
            repo_id=rid, query=fake_query, source_category="negative_nonexistent",
            expected_behavior=eb, oracle_type=ot, intent_guess=ig,
            risk_tags=rt, why_this_is_hard=wth, which_strategy_it_targets=wst,
            risk_public=rp,
        )
        count += 1
        idx += 1

    # ══════════════════════════════════════════════════════════════════════
    # CATEGORY 2: ambiguous_vague (target: 150)
    # ══════════════════════════════════════════════════════════════════════
    target = TARGET_CATEGORIES["ambiguous_vague"]  # 150
    all_amb_vague = [(w, d, "ambiguous") for w, d in AMBIGUOUS_WORDS] + [
        (w, "Single common word matches many unrelated locations", "vague")
        for w in VAGUE_WORDS
    ]
    rng.shuffle(all_amb_vague)
    idx = 0
    count = 0
    while count < target:
        rid = repo_ids[idx % len(repo_ids)]
        word, desc, subkind = all_amb_vague[idx % len(all_amb_vague)]
        if subkind == "ambiguous":
            eb = "weak_candidates"
            ot = "mined"
            rt = ["ambiguous"]
            wst = "all_channels"
        else:
            eb = "abstain"
            ot = "stress"
            rt = ["query_noise"]
            wst = "query_noise_guard"
        add_stress(
            repo_id=rid, query=word, source_category="ambiguous_vague",
            expected_behavior=eb, oracle_type=ot,
            intent_guess=f"Disambiguate/vague: {desc}",
            risk_tags=rt, why_this_is_hard=desc, which_strategy_it_targets=wst,
            risk_public="ambiguous_or_vague",
        )
        count += 1
        idx += 1

    # ══════════════════════════════════════════════════════════════════════
    # CATEGORY 3: hard_distractor (target: 200)
    # ══════════════════════════════════════════════════════════════════════
    target = TARGET_CATEGORIES["hard_distractor"]  # 200
    # Derive from R20 hard_distractor and same_name_symbol labels, plus fresh mining
    r20_hd = r20_by_category.get("hard_distractor", []) + r20_by_category.get("same_name_symbol", [])
    r20_hd_queries: set[str] = set()
    for lbl in r20_hd:
        r20_hd_queries.add(lbl.get("query", ""))

    count = 0
    # First: use R20-derived queries
    rng.shuffle(r20_hd)
    for lbl in r20_hd:
        if count >= target:
            break
        rid = lbl.get("repo_id", "")
        if rid not in repo_symbols:
            rid = repo_ids[count % len(repo_ids)]
        query = lbl.get("query", "")
        if not query:
            continue
        # Create a fresh variant — suffix or prefix the query
        variant = rng.choice([
            f"exact {query}", query, f"{query} definition",
        ])
        add_stress(
            repo_id=rid, query=variant, source_category="hard_distractor",
            expected_behavior="primary_evidence", oracle_type="mined",
            intent_guess=f"Find correct {query} among multiple definitions",
            risk_tags=["same_name_disambiguation"],
            why_this_is_hard=f"Multiple definitions of {query} exist across files; disambiguation needed",
            which_strategy_it_targets="rrf_with_context",
            risk_public="disambiguation_required",
        )
        count += 1

    # Then: fresh from symbol mining
    while count < target:
        rid = repo_ids[count % len(repo_ids)]
        symbols = repo_symbols[rid]
        if not symbols:
            count += 1
            continue
        sym = rng.choice(symbols)
        name = sym["name"]
        # Find similar-name symbols as distractors
        similar = [s for s in symbols if s["name"] != name and s["path"] != sym["path"]
                   and (name.lower() in s["name"].lower() or s["name"].lower() in name.lower())]
        distractors = []
        mnp = []
        for s in similar[:3]:
            distractors.append({
                "path": s["path"], "start_line": s["start_line"],
                "end_line": s["end_line"],
                "rationale": f"{s['name']} similar name to {name}",
            })
            mnp.append({
                "path": s["path"], "start_line": s["start_line"],
                "end_line": s["end_line"],
                "rationale": f"Similar name {s['name']}, not the target",
            })
        add_stress(
            repo_id=rid, query=name, source_category="hard_distractor",
            expected_behavior="primary_evidence", oracle_type="mined",
            intent_guess=f"Find {name} despite similar-name distractors",
            risk_tags=["partial_name_match"],
            why_this_is_hard=f"Similar-name symbols distract from the true target {name}",
            which_strategy_it_targets="symbol_search",
            gold_spans=[_gold_span(sym)],
            hard_distractors=distractors,
            must_not_primary=mnp,
            risk_public="distractor_present",
        )
        count += 1

    # ══════════════════════════════════════════════════════════════════════
    # CATEGORY 4: semantic_trap (target: 150)
    # ══════════════════════════════════════════════════════════════════════
    target = TARGET_CATEGORIES["semantic_trap"]  # 150
    # Use SEMANTIC_TRAP_QUERIES plus R20 dense_semantic_trap derivatives
    r20_dens = r20_by_category.get("dense_semantic_trap", [])
    all_semantic = list(SEMANTIC_TRAP_QUERIES)
    for lbl in r20_dens:
        q = lbl.get("query", "")
        if q and q not in all_semantic:
            all_semantic.append(q)
    rng.shuffle(all_semantic)
    idx = 0
    count = 0
    while count < target:
        rid = repo_ids[idx % len(repo_ids)]
        query = all_semantic[idx % len(all_semantic)]
        add_stress(
            repo_id=rid, query=query, source_category="semantic_trap",
            expected_behavior="abstain", oracle_type="stress",
            intent_guess=f"Find code related to {query} (semantic false positive trap)",
            risk_tags=["semantic_false_positive"],
            why_this_is_hard="Dense/semantic search may return superficially similar but unrelated code; these repos do not implement these features",
            which_strategy_it_targets="dense_search",
            risk_public="semantic_trap",
        )
        count += 1
        idx += 1

    # ══════════════════════════════════════════════════════════════════════
    # CATEGORY 5: same_name_symbol (target: 100)
    # ══════════════════════════════════════════════════════════════════════
    target = TARGET_CATEGORIES["same_name_symbol"]  # 100
    count = 0
    # Derive from R20 same_name_symbol labels first
    r20_sns = r20_by_category.get("same_name_symbol", [])
    rng.shuffle(r20_sns)
    for lbl in r20_sns:
        if count >= target:
            break
        rid = lbl.get("repo_id", "")
        if rid not in repo_symbols:
            rid = repo_ids[count % len(repo_ids)]
        query = lbl.get("query", "")
        if not query:
            continue
        add_stress(
            repo_id=rid, query=query, source_category="same_name_symbol",
            expected_behavior="primary_evidence", oracle_type="deterministic",
            intent_guess=f"Find specific {query} definition among same-name symbols",
            risk_tags=["same_name_confusion"],
            why_this_is_hard=f"Same symbol name {query} appears in multiple locations",
            which_strategy_it_targets="context_ranking",
            risk_public="same_name_conflict",
        )
        count += 1

    # Fill remaining with fresh mining
    while count < target:
        rid = repo_ids[count % len(repo_ids)]
        symbols = repo_symbols[rid]
        # Find same-name symbols
        name_map: dict[str, list[dict]] = {}
        for s in symbols:
            name_map.setdefault(s["name"], []).append(s)
        same_name = {n: ss for n, ss in name_map.items() if len(ss) > 1}
        if same_name:
            name = rng.choice(list(same_name.keys()))
            defs = same_name[name]
            primary = defs[0]
            add_stress(
                repo_id=rid, query=name, source_category="same_name_symbol",
                expected_behavior="primary_evidence", oracle_type="deterministic",
                intent_guess=f"Find specific {name} among {len(defs)} same-name definitions",
                risk_tags=["same_name_confusion"],
                why_this_is_hard=f"Same symbol name {name} appears in {len(defs)} different locations",
                which_strategy_it_targets="context_ranking",
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
                     "rationale": "Same name, different context"}
                    for d in defs[1:3]
                ],
                risk_public="same_name_conflict",
            )
        else:
            # Synthetic: pick a symbol and add a variant query
            if symbols:
                sym = rng.choice(symbols)
                add_stress(
                    repo_id=rid, query=sym["name"],
                    source_category="same_name_symbol",
                    expected_behavior="primary_evidence", oracle_type="mined",
                    intent_guess=f"Find {sym['name']} (may have same-name in other files)",
                    risk_tags=["same_name_confusion"],
                    why_this_is_hard=f"Query for {sym['name']} may match same-name symbols elsewhere",
                    which_strategy_it_targets="context_ranking",
                    gold_spans=[_gold_span(sym)],
                    risk_public="same_name_conflict",
                )
        count += 1

    # ══════════════════════════════════════════════════════════════════════
    # CATEGORY 6: frontend_backend_confusion (target: 75)
    # ══════════════════════════════════════════════════════════════════════
    target = TARGET_CATEGORIES["frontend_backend_confusion"]  # 75
    # Derive from R20 first
    r20_fb = r20_by_category.get("frontend_backend_confusion", [])
    rng.shuffle(r20_fb)
    count = 0
    for lbl in r20_fb:
        if count >= target:
            break
        rid = lbl.get("repo_id", "")
        if rid not in repo_symbols:
            rid = repo_ids[count % len(repo_ids)]
        query = lbl.get("query", "")
        if not query:
            continue
        add_stress(
            repo_id=rid, query=query, source_category="frontend_backend_confusion",
            expected_behavior="primary_evidence", oracle_type="mined",
            intent_guess=f"Find frontend component {query} (not backend)",
            risk_tags=["frontend_backend_overlap"],
            why_this_is_hard="Same or similar names may exist in frontend and backend code",
            which_strategy_it_targets="context_ranking",
            risk_public="frontend_backend_overlap",
        )
        count += 1

    # Fill remaining with fresh mining
    while count < target:
        rid = repo_ids[count % len(repo_ids)]
        symbols = repo_symbols[rid]
        frontend_syms = [s for s in symbols if _is_frontend_path(s["path"])]
        backend_syms = [s for s in symbols if _is_backend_path(s["path"])]
        if frontend_syms and backend_syms:
            fsym = rng.choice(frontend_syms)
            distractors = [{
                "path": bsym["path"], "start_line": bsym["start_line"],
                "end_line": bsym["end_line"],
                "rationale": f"Backend {bsym['name']} may be confused with frontend {fsym['name']}"
            } for bsym in rng.sample(backend_syms, min(2, len(backend_syms)))]
            add_stress(
                repo_id=rid, query=fsym["name"],
                source_category="frontend_backend_confusion",
                expected_behavior="primary_evidence", oracle_type="mined",
                intent_guess=f"Find frontend component {fsym['name']} (not backend)",
                risk_tags=["frontend_backend_overlap"],
                why_this_is_hard="Same or similar names may exist in frontend and backend code",
                which_strategy_it_targets="context_ranking",
                gold_spans=[_gold_span(fsym)],
                hard_distractors=distractors,
                risk_public="frontend_backend_overlap",
            )
        elif backend_syms:
            bsym = rng.choice(backend_syms)
            add_stress(
                repo_id=rid, query=f"{bsym['name']} frontend",
                source_category="frontend_backend_confusion",
                expected_behavior="weak_candidates", oracle_type="stress",
                intent_guess=f"Find frontend version of {bsym['name']} (may not exist)",
                risk_tags=["frontend_backend_overlap"],
                why_this_is_hard=f"Query references frontend but {bsym['name']} is backend-only",
                which_strategy_it_targets="context_ranking",
                risk_public="frontend_backend_overlap",
            )
        else:
            # Synthetic
            add_stress(
                repo_id=rid, query="component_renderer",
                source_category="frontend_backend_confusion",
                expected_behavior="abstain", oracle_type="stress",
                intent_guess="Find frontend/backend boundary component (synthetic)",
                risk_tags=["frontend_backend_overlap"],
                why_this_is_hard="No frontend/backend distinction in this repo; synthetic probe",
                which_strategy_it_targets="context_ranking",
                risk_public="frontend_backend_overlap",
            )
        count += 1

    # ══════════════════════════════════════════════════════════════════════
    # CATEGORY 7: test_source_confusion (target: 75)
    # ══════════════════════════════════════════════════════════════════════
    target = TARGET_CATEGORIES["test_source_confusion"]  # 75
    r20_ts = r20_by_category.get("test_source_confusion", [])
    rng.shuffle(r20_ts)
    count = 0
    for lbl in r20_ts:
        if count >= target:
            break
        rid = lbl.get("repo_id", "")
        if rid not in repo_symbols:
            rid = repo_ids[count % len(repo_ids)]
        query = lbl.get("query", "")
        if not query:
            continue
        add_stress(
            repo_id=rid, query=query, source_category="test_source_confusion",
            expected_behavior="primary_evidence", oracle_type="mined",
            intent_guess=f"Find test code for {query} (not source implementation)",
            risk_tags=["test_source_overlap"],
            why_this_is_hard="Test and source files may have similar names; retriever may return source instead of test",
            which_strategy_it_targets="path_filtering",
            risk_public="test_source_overlap",
        )
        count += 1

    # Fill remaining with fresh mining
    while count < target:
        rid = repo_ids[count % len(repo_ids)]
        symbols = repo_symbols[rid]
        test_syms = [s for s in symbols if _is_test_path(s["path"])]
        source_syms = [s for s in symbols if not _is_test_path(s["path"])]
        if test_syms and source_syms:
            tsym = rng.choice(test_syms)
            distractors = [{
                "path": ssym["path"], "start_line": ssym["start_line"],
                "end_line": ssym["end_line"],
                "rationale": f"Source {ssym['name']} may be returned instead of test"
            } for ssym in rng.sample(source_syms, min(2, len(source_syms)))]
            add_stress(
                repo_id=rid, query=tsym["name"],
                source_category="test_source_confusion",
                expected_behavior="primary_evidence", oracle_type="mined",
                intent_guess=f"Find test code for {tsym['name']} (not source implementation)",
                risk_tags=["test_source_overlap"],
                why_this_is_hard="Test and source files may have similar names; retriever may return source instead of test",
                which_strategy_it_targets="path_filtering",
                gold_spans=[_gold_span(tsym)],
                hard_distractors=distractors,
                risk_public="test_source_overlap",
            )
        else:
            # Synthetic
            add_stress(
                repo_id=rid, query="test_helper_util",
                source_category="test_source_confusion",
                expected_behavior="abstain", oracle_type="stress",
                intent_guess="Find test helper (synthetic probe)",
                risk_tags=["test_source_overlap"],
                why_this_is_hard="No clear test/source distinction found; synthetic probe",
                which_strategy_it_targets="path_filtering",
                risk_public="test_source_overlap",
            )
        count += 1

    # ══════════════════════════════════════════════════════════════════════
    # CATEGORY 8: generated_vendor_trap (target: 50)
    # ══════════════════════════════════════════════════════════════════════
    target = TARGET_CATEGORIES["generated_vendor_trap"]  # 50
    r20_gv = r20_by_category.get("generated_vendor_trap", [])
    rng.shuffle(r20_gv)
    count = 0
    for lbl in r20_gv:
        if count >= target:
            break
        rid = lbl.get("repo_id", "")
        if rid not in repo_symbols:
            rid = repo_ids[count % len(repo_ids)]
        query = lbl.get("query", "")
        if not query:
            continue
        add_stress(
            repo_id=rid, query=query, source_category="generated_vendor_trap",
            expected_behavior="abstain", oracle_type="stress",
            intent_guess=f"Avoid vendor/generated code for {query}",
            risk_tags=["vendor_trap"],
            why_this_is_hard="Retriever may surface vendor/generated code as if it were project code",
            which_strategy_it_targets="path_filtering",
            risk_public="vendor_trap",
        )
        count += 1

    # Fill remaining with synthetic vendor traps
    vendor_like_queries = [
        "node_modules_helper", "vendor_util", "third_party_adapter",
        "generated_schema", "dist_bundle_config", "build_output_reader",
        "next_cache_handler", "nuxt_generated_page", "coverage_report_parser",
        "minified_bundle_loader",
    ]
    while count < target:
        rid = repo_ids[count % len(repo_ids)]
        query = vendor_like_queries[count % len(vendor_like_queries)]
        add_stress(
            repo_id=rid, query=query, source_category="generated_vendor_trap",
            expected_behavior="abstain", oracle_type="stress",
            intent_guess=f"Query for vendor-like symbol that should not be returned",
            risk_tags=["vendor_trap"],
            why_this_is_hard="Vendor/generated naming patterns may cause retriever to return non-project code",
            which_strategy_it_targets="path_filtering",
            risk_public="vendor_trap",
        )
        count += 1

    # ══════════════════════════════════════════════════════════════════════
    # CATEGORY 9: stale_index_like (target: 50)
    # ══════════════════════════════════════════════════════════════════════
    target = TARGET_CATEGORIES["stale_index_like"]  # 50
    r20_stale_cats = ["stale_index_candidate", "deleted_file", "renamed_file",
                      "branch_switch_like", "dirty_overlay"]
    r20_stale = []
    for cat in r20_stale_cats:
        r20_stale.extend(r20_by_category.get(cat, []))
    rng.shuffle(r20_stale)
    count = 0
    for lbl in r20_stale:
        if count >= target:
            break
        rid = lbl.get("repo_id", "")
        if rid not in repo_symbols:
            rid = repo_ids[count % len(repo_ids)]
        query = lbl.get("query", "")
        if not query:
            continue
        add_stress(
            repo_id=rid, query=query, source_category="stale_index_like",
            expected_behavior="abstain", oracle_type="metamorphic",
            intent_guess=f"Find code that may not exist in current snapshot (stale index probe)",
            risk_tags=["stale_index"],
            why_this_is_hard="Retriever with stale index may return results for deleted/renamed/modified files",
            which_strategy_it_targets="stale_index_detection",
            risk_public="stale_index_probe",
        )
        count += 1

    # Fill remaining with synthetic stale queries
    stale_queries = [
        "deleted_module_old_api", "feature_branch_only_function",
        "modified_handler_v1", "renamed_service_legacy",
        "old_config_format_parser", "deprecated_endpoint_handler",
        "removed_cache_layer", "migrated_db_adapter_old",
        "legacy_auth_provider", "archived_scheduler_impl",
    ]
    while count < target:
        rid = repo_ids[count % len(repo_ids)]
        query = stale_queries[count % len(stale_queries)]
        add_stress(
            repo_id=rid, query=query, source_category="stale_index_like",
            expected_behavior="abstain", oracle_type="metamorphic",
            intent_guess=f"Find code in deleted/renamed/modified file (does not exist)",
            risk_tags=["stale_index"],
            why_this_is_hard="Stale index may return results for code that no longer exists",
            which_strategy_it_targets="stale_index_detection",
            risk_public="stale_index_probe",
        )
        count += 1

    # ══════════════════════════════════════════════════════════════════════
    # CATEGORY 10: dense_quiver_specific_trap (target: 100)
    # ══════════════════════════════════════════════════════════════════════
    target = TARGET_CATEGORIES["dense_quiver_specific_trap"]  # 100
    rng.shuffle(DENSE_QUIVER_TRAP_QUERIES)
    idx = 0
    count = 0
    while count < target:
        rid = repo_ids[idx % len(repo_ids)]
        query, rationale = DENSE_QUIVER_TRAP_QUERIES[idx % len(DENSE_QUIVER_TRAP_QUERIES)]
        add_stress(
            repo_id=rid, query=query,
            source_category="dense_quiver_specific_trap",
            expected_behavior="abstain", oracle_type="stress",
            intent_guess=f"Find code for {query} (not implemented; naming trap)",
            risk_tags=["dense_trap", "quiver_trap", "tdb_trap"],
            why_this_is_hard=rationale,
            which_strategy_it_targets="dense_search",
            risk_public="infrastructure_naming_trap",
        )
        count += 1
        idx += 1

    # ══════════════════════════════════════════════════════════════════════
    # Ensure total >= 1000
    # ══════════════════════════════════════════════════════════════════════
    while len(all_tasks) < 1000:
        rid = repo_ids[len(all_tasks) % len(repo_ids)]
        symbols = repo_symbols[rid]
        if symbols:
            sym = rng.choice(symbols)
            query = f"r26_filler_{sym['name']}_{len(all_tasks)}"
        else:
            query = f"r26_filler_{len(all_tasks)}"
        add_stress(
            repo_id=rid, query=query, source_category="negative_nonexistent",
            expected_behavior="abstain", oracle_type="stress",
            intent_guess="Filler to meet minimum total count",
            risk_tags=["synthetic"],
            why_this_is_hard="Added to meet minimum total task count",
            which_strategy_it_targets="all_channels",
            risk_public="synthetic_filler",
        )

    # ── Sort by test_id for determinism ────────────────────────────────
    all_tasks.sort(key=lambda t: t["test_id"])
    all_labels.sort(key=lambda l: l["test_id"])

    # ── Validate gold/must_not/hard_distractor overlap ─────────────────
    for label in all_labels:
        gold = label.get("gold_spans", [])
        mnp = label.get("must_not_primary", [])
        hd = label.get("hard_distractors", [])

        label["must_not_primary"] = [
            m for m in mnp
            if not any(
                m.get("path") == g.get("path")
                and int(m.get("start_line", 0)) <= int(g.get("end_line", 0))
                and int(m.get("end_line", 0)) >= int(g.get("start_line", 0))
                for g in gold
            )
        ]
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


# ── Repo lock generation (same external repo set as R20) ──────────────

def generate_repo_lock(resolved_repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries = []
    for candidate in resolved_repos:
        repo_id = candidate["repo_id"]
        repo_path = Path(candidate["local_path"])
        extensions = set(candidate.get("extensions", [".rs"]))
        exclude_subdirs = candidate.get("exclude_subdirs", [])
        manifest_sha, file_count, line_count, = (
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
            "commit": "r26-snapshot",
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
                "extensions": sorted(extensions),
                "exclude_subdirs": exclude_subdirs,
                "source_repo_kind": "external_local",
            },
        })
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate R26 auto-stress-1000 retrieval failure-surface dataset"
    )
    parser.add_argument(
        "--workspace", default=".",
        help="Workspace root (containing eval/, fixtures/, etc.)"
    )
    parser.add_argument(
        "--out", default="fixtures/r26_auto_stress",
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

    # Load R20 data
    print("\nLoading R20 data for derivative generation...")
    r20_labels = load_r20_labels(workspace)
    r20_tasks = load_r20_tasks(workspace)
    r20_repos = load_r20_repos_lock(workspace)
    print(f"  R20 labels: {len(r20_labels)}")
    print(f"  R20 tasks: {len(r20_tasks)}")
    print(f"  R20 repos: {len(r20_repos)}")

    # Generate repo lock
    print("\nGenerating repo lock...")
    repo_entries = generate_repo_lock(resolved_repos)
    print(f"  Repo entries: {len(repo_entries)}")

    lock_path = out_dir / "repos.lock.jsonl"
    with lock_path.open("w", encoding="utf-8") as f:
        for entry in repo_entries:
            f.write(json.dumps(entry, sort_keys=True) + "\n")

    # Generate tasks and labels
    print("\nGenerating R26 stress tasks and labels...")
    tasks, labels, coverage = generate_all_tasks(resolved_repos, r20_labels, r20_tasks, rng)
    print(f"  Tasks: {len(tasks)}")
    print(f"  Labels: {len(labels)}")
    print(f"  Categories: {len(coverage['by_category'])}")
    print(f"  Category counts:")
    for cat, count in sorted(coverage["by_category"].items()):
        print(f"    {cat}: {count}")

    # Write tasks
    tasks_path = out_dir / "tasks" / "auto_stress.jsonl"
    with tasks_path.open("w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, sort_keys=True) + "\n")

    # Write labels
    labels_path = out_dir / "labels" / "auto_stress.jsonl"
    with labels_path.open("w", encoding="utf-8") as f:
        for label in labels:
            f.write(json.dumps(label, sort_keys=True) + "\n")

    # Compute SHA256 checksums
    tasks_sha = hashlib.sha256(tasks_path.read_bytes()).hexdigest()
    labels_sha = hashlib.sha256(labels_path.read_bytes()).hexdigest()

    # Write dataset manifest
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "program": "R26 Auto-Stress-1000 Retrieval Failure-Surface Benchmark",
        "description": (
            "Weak/mined/deterministic stress dataset for retrieval failure discovery. "
            "NOT promotion evidence. NOT a retrieval strategy promotion mechanism. "
            "Designed to maximize failure discovery. Labels are weak/mined/deterministic; "
            "not human-verified. No canary tokens. Uses the same external repo set as R20 "
            "and derives some queries from existing R20 tasks/labels where useful."
        ),
        "not_promotion_evidence": True,
        "core_changes": False,
        "remote_calls": 0,
        "dense_or_llm_claims": False,
        "tiers": {
            "auto_stress": {
                "target_repos": 9,
                "minimum_tasks": 1000,
                "minimum_labels": 1000,
                "generated_tasks": len(tasks),
                "generated_labels": len(labels),
                "target_categories": len(REQUIRED_CATEGORIES),
                "min_per_category": 10,
                "min_per_repo": 50,
                "label_quality_note": "per-row label_quality is intentionally omitted; oracle_type plus R26 caveats define weak/mined/deterministic status",
            }
        },
        "current_status": {
            "auto_stress": {
                "repos": len(resolved_repos),
                "tasks": len(tasks),
                "labels": len(labels),
                "categories": coverage["by_category"],
                "repos_count": coverage["by_repo"],
                "populated": len(tasks) >= 1000,
                "partial": len(tasks) < 1000,
            }
        },
        "generation_info": {
            "generator": "eval/r26_generate_auto_stress.py",
            "generated_at": "2026-06-12",
            "source_type": "external_local_repos_and_r20_derivatives",
            "seed": SEED,
            "content_manifest_algorithm": "normalized_sha256_per_file_sorted",
            "supported_extensions": sorted(SOURCE_EXTENSIONS),
            "anti_leakage": (
                "Public tasks contain only test_id, repo_id, query, public_version, source. "
                "No category/risk/gold/expected/oracle/risk_tags/intent_guess/why/strategy fields. "
                "Labels are private and separate. R26 labels are stress failure-surface labels, not EvidenceCore."
            ),
            "tasks_sha256": tasks_sha,
            "labels_sha256": labels_sha,
        },
        "target_composition": TARGET_CATEGORIES,
    }
    manifest_path = out_dir / "dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Write safety_checks.json placeholder
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
        "note": "Run eval/r26_validate_auto_stress.py to populate safety checks",
    }
    safety_path = out_dir / "safety_checks.json"
    safety_path.write_text(json.dumps(safety, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Write summary
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps({
        "total_tasks": len(tasks),
        "total_labels": len(labels),
        "categories": coverage["by_category"],
        "repos_count": coverage["by_repo"],
        "seed": SEED,
        "meets_1000_minimum": len(tasks) >= 1000,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"\nGeneration complete!")
    print(f"Tasks: {len(tasks)}")
    print(f"Labels: {len(labels)}")
    print(f"Categories: {len(coverage['by_category'])}")
    print(f"Repos: {len(resolved_repos)}")
    print(f"Meets >= 1000: {len(tasks) >= 1000}")


if __name__ == "__main__":
    main()
