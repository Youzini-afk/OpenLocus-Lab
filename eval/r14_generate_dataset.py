#!/usr/bin/env python3
"""R14 Scaled Multi-Repo Evidence Benchmark Dataset Generator.

Generates/refreshes R14 benchmark data from the current workspace and available
local repos. Avoids label leakage: public tasks contain no gold path/line info;
labels are private and separate.

The content_manifest_sha uses a normalized algorithm:
  - Sort all .rs files by relative path (POSIX)
  - For each file: {path, sha256, lines} as sorted JSON line
  - SHA-256 of the concatenated lines

Usage:
    python3 eval/r14_generate_dataset.py [--workspace PATH] [--out-dir PATH] [--tier S|M|L|X|all]
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

SCHEMA_VERSION = "r14-v1"

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
]


# ── Normalized content manifest ────────────────────────────────────────


def compute_normalized_manifest_sha(
    workspace: Path, crate_dirs: list[str]
) -> tuple[str, int, int, list[dict[str, Any]]]:
    """Compute normalized content manifest SHA.

    Algorithm: sort all .rs files by relative path (POSIX). For each file:
    - relative path (POSIX, forward-slash)
    - SHA-256 of file contents
    - line count
    Concatenate as sorted JSON lines, SHA-256 the result.

    Returns (manifest_sha, file_count, total_lines, per_file_entries).
    """
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


# ── Symbol extraction ──────────────────────────────────────────────────

RUST_STRUCT_RE = re.compile(r"^\s*pub\s+struct\s+(\w+)", re.MULTILINE)
RUST_ENUM_RE = re.compile(r"^\s*pub\s+enum\s+(\w+)", re.MULTILINE)
RUST_FN_RE = re.compile(r"^\s*pub\s+(?:async\s+)?fn\s+(\w+)", re.MULTILINE)
RUST_TRAIT_RE = re.compile(r"^\s*pub\s+trait\s+(\w+)", re.MULTILINE)


def find_rust_files(root: Path) -> list[Path]:
    """Find all Rust source files in a directory tree."""
    files = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in filenames:
            if fname.endswith(".rs"):
                files.append(Path(dirpath) / fname)
    return sorted(files)


def extract_symbols(filepath: Path, repo_root: Path) -> list[dict[str, Any]]:
    """Extract public symbols from a Rust file with line ranges."""
    symbols = []
    try:
        text = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return symbols

    lines = text.splitlines()
    rel_path = str(filepath.relative_to(repo_root))

    for i, line in enumerate(lines, 1):
        for pattern, kind in [
            (RUST_STRUCT_RE, "struct"),
            (RUST_ENUM_RE, "enum"),
            (RUST_TRAIT_RE, "trait"),
            (RUST_FN_RE, "fn"),
        ]:
            m = pattern.match(line)
            if m:
                name = m.group(1)
                end_line = i
                for j in range(i, min(i + 30, len(lines) + 1)):
                    if j > i:
                        next_line = lines[j - 1].strip()
                        if not next_line or (
                            next_line.startswith("pub ")
                            and not next_line.startswith("pub(crate)")
                        ):
                            end_line = j - 1
                            break
                else:
                    end_line = min(i + 20, len(lines))

                brace_count = 0
                found_open = False
                for j in range(i - 1, min(i + 29, len(lines))):
                    brace_count += lines[j].count("{") - lines[j].count("}")
                    if "{" in lines[j]:
                        found_open = True
                    if found_open and brace_count <= 0:
                        end_line = j + 1
                        break

                symbols.append(
                    {
                        "name": name,
                        "kind": kind,
                        "path": rel_path,
                        "start_line": i,
                        "end_line": end_line,
                    }
                )

    return symbols


def find_hard_negatives(
    symbol: dict[str, Any],
    all_symbols: list[dict[str, Any]],
    max_negatives: int = 2,
) -> list[dict[str, Any]]:
    """Find hard negatives for a symbol: similar names or same-file different symbols."""
    negatives = []
    name = symbol["name"]
    path = symbol["path"]

    for s in all_symbols:
        if s["path"] == path and s["name"] != name:
            negatives.append(
                {
                    "path": s["path"],
                    "start_line": s["start_line"],
                    "end_line": s["end_line"],
                    "rationale": f"{s['name']} ({s['kind']}) is in same file but different from {name}",
                }
            )
            if len(negatives) >= max_negatives:
                break

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

    return negatives


# ── Repo lock generation ───────────────────────────────────────────────


def generate_repo_lock(
    workspace: Path, repo_groups: dict[str, list[str]]
) -> list[dict[str, Any]]:
    """Generate repos.lock.jsonl entries with normalized content manifest."""
    entries = []
    for repo_id, crate_dirs in repo_groups.items():
        # Compute normalized content manifest SHA
        manifest_sha, file_count, line_count, per_file = compute_normalized_manifest_sha(
            workspace, crate_dirs
        )

        if file_count == 0:
            print(f"WARNING: No .rs files found for repo {repo_id}", file=sys.stderr)
            continue

        entries.append(
            {
                "repo_id": repo_id,
                "source": {
                    "type": "local_path",
                    "path": ",".join(crate_dirs),
                },
                "commit": "r14-snapshot",
                "worktree_info": f"OpenLocus-Lab workspace sub-crates: {', '.join(crate_dirs)}",
                "content_manifest_sha": manifest_sha,
                "content_manifest_algorithm": "normalized_sha256_per_file_sorted",
                "policy": {
                    "exclude": BENCHMARK_EXCLUDES,
                },
                "language": {
                    "primary": "rust",
                    "secondary": [],
                    "tier": "S",
                },
                "metadata": {
                    "files": file_count,
                    "lines": line_count,
                    "description": f"OpenLocus {repo_id} sub-crates",
                    "per_file_count": len(per_file),
                },
            }
        )

    return entries


# ── Task generation ────────────────────────────────────────────────────

NEGATIVE_QUERIES = [
    ("quantum_entanglement_solver", "openlocus-core"),
    ("neural_network_training_loop", "openlocus-retrieval"),
    ("blockchain_consensus_protocol", "openlocus-store"),
    ("distributed_database_replication", "openlocus-retrieval"),
    ("machine_learning_inference", "openlocus-core"),
    ("web_server_http_handler", "openlocus-retrieval"),
    ("microservice_orchestration", "openlocus-store"),
    ("cryptographic_key_rotation", "openlocus-core"),
]

STRESS_QUERIES = [
    ("error handling", "openlocus-store"),
    ("search implementation", "openlocus-retrieval"),
    ("data storage", "openlocus-store"),
    ("retrieval quality", "openlocus-store"),
    ("index persistence", "openlocus-retrieval"),
    ("code evidence", "openlocus-core"),
    ("embedding search", "openlocus-store"),
    ("workspace configuration", "openlocus-cli"),
    ("file scanning", "openlocus-core"),
    ("path validation safety", "openlocus-core"),
]

CONFIG_QUERIES = [
    ("Policy exclude patterns", "openlocus-core"),
    ("default ignore patterns", "openlocus-core"),
    ("content hashing implementation", "openlocus-core"),
    ("persistent index manifest", "openlocus-retrieval"),
    ("embedding policy gate", "openlocus-store"),
    ("graph edge kinds", "openlocus-store"),
]

CROSS_REPO_QUERIES = [
    ("main entry point", "openlocus-cli"),
    ("configuration loading", "openlocus-cli"),
]


def method_hint_for_symbol(kind: str) -> str:
    if kind in ("struct", "enum", "trait"):
        return "symbol"
    elif kind == "fn":
        return "regex"
    return "regex"


def generate_exact_symbol_tasks(
    symbols: list[dict[str, Any]],
    repo_id: str,
    task_prefix: str,
    start_id: int,
) -> tuple[list[dict], list[dict], int]:
    tasks = []
    labels = []
    task_id = start_id

    for sym in symbols:
        if sym["kind"] in ("struct", "enum", "trait"):
            task_type = "exact_symbol"
        else:
            task_type = "implementation_search"

        tid = f"{task_prefix}-{task_id:03d}"
        task_id += 1

        tasks.append(
            {
                "task_id": tid,
                "query": sym["name"],
                "task_type": task_type,
                "method_hint": method_hint_for_symbol(sym["kind"]),
                "repo_id": repo_id,
            }
        )

        hard_negs = find_hard_negatives(sym, symbols, max_negatives=2)
        labels.append(
            {
                "task_id": tid,
                "label_quality": "mined_high_confidence",
                "gold_spans": [
                    {
                        "path": sym["path"],
                        "start_line": sym["start_line"],
                        "end_line": sym["end_line"],
                        "rationale": f"{sym['kind']} {sym['name']} definition",
                    }
                ],
                "hard_negatives": hard_negs,
            }
        )

    return tasks, labels, task_id


def generate_negative_tasks(
    task_prefix: str, start_id: int
) -> tuple[list[dict], list[dict], int]:
    tasks = []
    labels = []
    task_id = start_id

    for query, repo_id in NEGATIVE_QUERIES:
        tid = f"{task_prefix}-{task_id:03d}"
        task_id += 1
        tasks.append(
            {"task_id": tid, "query": query, "task_type": "negative",
             "method_hint": "regex", "repo_id": repo_id}
        )
        labels.append(
            {"task_id": tid, "label_quality": "human_reviewed",
             "gold_spans": [], "hard_negatives": []}
        )

    return tasks, labels, task_id


def generate_stress_tasks(
    task_prefix: str, start_id: int
) -> tuple[list[dict], list[dict], int]:
    tasks = []
    labels = []
    task_id = start_id

    for query, repo_id in STRESS_QUERIES:
        tid = f"{task_prefix}-{task_id:03d}"
        task_id += 1
        tasks.append(
            {"task_id": tid, "query": query, "task_type": "stress",
             "method_hint": "bm25", "repo_id": repo_id}
        )
        labels.append(
            {"task_id": tid, "label_quality": "weak",
             "gold_spans": [], "hard_negatives": []}
        )

    return tasks, labels, task_id


# ── Main generation ────────────────────────────────────────────────────


def generate_tier_s(workspace: Path, out_dir: Path) -> dict[str, Any]:
    print("Generating R14-S tier...")

    repo_groups = {
        "openlocus-core": ["crates/openlocus-core", "crates/openlocus-repo"],
        "openlocus-retrieval": ["crates/openlocus-retrieval", "crates/openlocus-ast", "crates/openlocus-index"],
        "openlocus-store": ["crates/openlocus-store", "crates/openlocus-derived", "crates/openlocus-graph", "crates/openlocus-context", "crates/openlocus-provider"],
        "openlocus-cli": ["crates/openlocus-cli"],
    }

    repo_entries = generate_repo_lock(workspace, repo_groups)
    print(f"  Repo entries: {len(repo_entries)}")

    all_tasks = []
    all_labels = []
    task_id = 1

    for repo_id, crate_dirs in repo_groups.items():
        all_symbols = []
        for crate_dir in crate_dirs:
            crate_path = workspace / crate_dir
            if crate_path.exists():
                for rs_file in find_rust_files(crate_path):
                    syms = extract_symbols(rs_file, workspace)
                    all_symbols.extend(syms)

        print(f"  {repo_id}: {len(all_symbols)} symbols extracted")
        selected = all_symbols[:10]
        tasks, labels, task_id = generate_exact_symbol_tasks(selected, repo_id, "r14s", task_id)
        all_tasks.extend(tasks)
        all_labels.extend(labels)

    for query, repo_id in CONFIG_QUERIES:
        tid = f"r14s-{task_id:03d}"
        task_id += 1
        all_tasks.append({"task_id": tid, "query": query, "task_type": "config_policy", "method_hint": "bm25", "repo_id": repo_id})
        all_labels.append({"task_id": tid, "label_quality": "mined", "gold_spans": [], "hard_negatives": []})

    for query, repo_id in CROSS_REPO_QUERIES:
        tid = f"r14s-{task_id:03d}"
        task_id += 1
        all_tasks.append({"task_id": tid, "query": query, "task_type": "cross_repo", "method_hint": "bm25", "repo_id": repo_id})
        all_labels.append({"task_id": tid, "label_quality": "mined", "gold_spans": [], "hard_negatives": []})

    neg_tasks, neg_labels, task_id = generate_negative_tasks("r14s", task_id)
    all_tasks.extend(neg_tasks)
    all_labels.extend(neg_labels)

    stress_tasks, stress_labels, task_id = generate_stress_tasks("r14s", task_id)
    all_tasks.extend(stress_tasks)
    all_labels.extend(stress_labels)

    lock_path = out_dir / "repos.lock.jsonl"
    with lock_path.open("w", encoding="utf-8") as f:
        for entry in repo_entries:
            f.write(json.dumps(entry) + "\n")

    tasks_path = out_dir / "tasks" / "sanity.jsonl"
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    with tasks_path.open("w", encoding="utf-8") as f:
        for task in all_tasks:
            f.write(json.dumps(task) + "\n")

    labels_path = out_dir / "labels" / "sanity.jsonl"
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
        "repos": len(repo_entries),
        "tasks": len(all_tasks),
        "labels": len(all_labels),
        "hard_negatives": hard_neg_count,
        "label_quality_distribution": quality_dist,
        "populated": True,
    }


def generate_tier_m(workspace: Path, out_dir: Path) -> dict[str, Any]:
    print("Generating R14-M tier (partial - uses S-tier repos)...")

    repo_groups = {
        "openlocus-core": ["crates/openlocus-core", "crates/openlocus-repo"],
        "openlocus-retrieval": ["crates/openlocus-retrieval", "crates/openlocus-ast", "crates/openlocus-index"],
        "openlocus-store": ["crates/openlocus-store", "crates/openlocus-derived", "crates/openlocus-graph", "crates/openlocus-context", "crates/openlocus-provider"],
        "openlocus-cli": ["crates/openlocus-cli"],
    }

    all_tasks = []
    all_labels = []
    task_id = 1

    for repo_id, crate_dirs in repo_groups.items():
        all_symbols = []
        for crate_dir in crate_dirs:
            crate_path = workspace / crate_dir
            if crate_path.exists():
                for rs_file in find_rust_files(crate_path):
                    syms = extract_symbols(rs_file, workspace)
                    all_symbols.extend(syms)

        selected = all_symbols[:20]
        tasks, labels, task_id = generate_exact_symbol_tasks(selected, repo_id, "r14m", task_id)
        all_tasks.extend(tasks)
        all_labels.extend(labels)

    neg_tasks, neg_labels, task_id = generate_negative_tasks("r14m", task_id)
    all_tasks.extend(neg_tasks)
    all_labels.extend(neg_labels)

    stress_tasks, stress_labels, task_id = generate_stress_tasks("r14m", task_id)
    all_tasks.extend(stress_tasks)
    all_labels.extend(stress_labels)

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
    print("  NOTE: M-tier currently uses same repos as S-tier. Full M requires 8+ repos.")

    return {
        "repos": len(repo_groups),
        "tasks": len(all_tasks),
        "labels": len(all_labels),
        "hard_negatives": hard_neg_count,
        "label_quality_distribution": quality_dist,
        "populated": True,
        "partial": True,
        "note": "M-tier uses same repos as S with additional mined tasks; full M requires 8+ repos",
    }


def generate_tier_l(workspace: Path, out_dir: Path) -> dict[str, Any]:
    print("Generating R14-L tier (placeholder - requires additional repos)...")

    all_tasks = []
    all_labels = []
    task_id = 1

    impl_queries = [
        ("evidence freshness verification", "openlocus-store"),
        ("store backend capabilities", "openlocus-store"),
        ("tantivy index schema fields", "openlocus-retrieval"),
        ("chunk window line boundaries", "openlocus-retrieval"),
        ("tree-sitter node types", "openlocus-retrieval"),
        ("import resolution heuristic", "openlocus-store"),
        ("test heuristic file linking", "openlocus-store"),
        ("embedding vector normalization", "openlocus-store"),
        ("secret scanning patterns", "openlocus-store"),
        ("audit event logging", "openlocus-store"),
    ]

    for query, repo_id in impl_queries:
        tid = f"r14l-{task_id:03d}"
        task_id += 1
        all_tasks.append({"task_id": tid, "query": query, "task_type": "implementation_search", "method_hint": "bm25", "repo_id": repo_id})
        all_labels.append({"task_id": tid, "label_quality": "weak", "gold_spans": [], "hard_negatives": []})

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

    print(f"  Tasks: {len(all_tasks)} (placeholder)")
    print(f"  Labels: {len(all_labels)} (weak)")
    print("  NOTE: L-tier requires additional repos beyond current workspace.")

    return {
        "repos": 0,
        "tasks": len(all_tasks),
        "labels": len(all_labels),
        "hard_negatives": 0,
        "populated": False,
        "note": "L-tier is placeholder with weak labels; requires additional repos beyond current workspace",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate R14 benchmark dataset from workspace repos")
    parser.add_argument("--workspace", default=".", help="Path to OpenLocus-Lab workspace root")
    parser.add_argument("--out-dir", default="fixtures/r14", help="Output directory for generated data")
    parser.add_argument("--tier", default="all", choices=["S", "M", "L", "X", "all"], help="Which tier to generate")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    out_dir = Path(args.out_dir)

    if not (workspace / "Cargo.toml").exists():
        print(f"ERROR: {workspace} does not appear to be an OpenLocus workspace", file=sys.stderr)
        sys.exit(1)

    for subdir in ["tasks", "labels", "taxonomy", "expected_failures"]:
        (out_dir / subdir).mkdir(parents=True, exist_ok=True)

    results: dict[str, Any] = {}

    if args.tier in ("S", "all"):
        results["S"] = generate_tier_s(workspace, out_dir)

    if args.tier in ("M", "all"):
        results["M"] = generate_tier_m(workspace, out_dir)

    if args.tier in ("L", "all"):
        results["L"] = generate_tier_l(workspace, out_dir)

    if args.tier == "X":
        print("X-tier generation not yet implemented. Requires external repo sources.")
        results["X"] = {"repos": 0, "tasks": 0, "labels": 0, "hard_negatives": 0, "populated": False,
                        "note": "X-tier requires external repo sources"}

    manifest_path = out_dir / "dataset_manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {"schema_version": SCHEMA_VERSION, "program": "R14 Scaled Multi-Repo Evidence Benchmark"}

    if "current_status" not in manifest:
        manifest["current_status"] = {}

    for tier, stats in results.items():
        manifest["current_status"][tier] = stats

    manifest["generation_info"] = {
        "generator": "eval/r14_generate_dataset.py",
        "generated_at": "2026-06-12",
        "source_workspace": str(workspace),
        "content_manifest_algorithm": "normalized_sha256_per_file_sorted",
        "anti_leakage": "public tasks contain no gold paths/lines; labels are private; benchmark policy excludes fixtures/eval/docs/runs/.openlocus/target",
    }

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print("\nGeneration complete!")
    print(f"Results: {json.dumps(results, indent=2)}")


if __name__ == "__main__":
    main()
