#!/usr/bin/env python3
"""R25 Graph+Dense Ablation.

Eval-layer ablation study: graph_basic, dense_mock, and combination strategies
on R20 auto-wide fixtures. Does NOT change Rust core or EvidenceCore.

Architecture: strictly separated RUN and SCORE phases.
  Phase 1 (RUN): loads only public tasks + repo lock. Creates isolated benchmark
    roots by allowlist-copying source files. Runs graph impact and dense mock
    strategies via openlocus CLI. Never reads labels.
  Phase 2 (SCORE): loads predictions + labels. Computes metrics.
    Never invokes openlocus CLI.

Strategies (6 implemented):
  1. no_graph          - R21 rrf baseline (load from R21 artifacts)
  2. graph_basic       - derive top path via public query (symbol then regex
                         fallback), then `openlocus impact <path> --depth 1 --json`
  3. rrf_plus_graph    - RRF fuse graph_basic + R21 rrf
  4. dense_mock        - candidate-channel safety smoke (like R24)
  5. rrf_plus_dense_mock - RRF fuse dense_mock + R21 rrf
  6. rrf_plus_dense_mock_plus_graph - RRF fuse dense_mock + graph_basic + R21 rrf

Unavailable strategies (explicit unavailable/not_measured):
  - quiver: quiver_not_implemented (no numeric 0 as quality result)
  - tdb: feature-gated placeholder, not_applicable for this ablation

New metrics:
  - added_gold_span, added_false_span: lines added by graph/dense that
    are/aren't in gold_spans (vs R21 rrf baseline)
  - graph_pollution_ratio: ratio of graph evidence on forbidden paths
  - graph_token_waste_delta: token waste change vs baseline
  - dense_added_gold_span, dense_added_false_span: dense contribution
  - combined_added_gold_span, combined_added_false_span: combined contribution
  - Rule: if added_false_span > added_gold_span, default expansion blocked

Safety:
  - labels not loaded until after run complete
  - citation validator hash/range/path for every strategy with evidence
  - artifact manifest path/sha/bytes/lines verified
  - artifact scans for private fields/canary tokens
  - promotion_ready=false, not_promotion_evidence=true, remote_calls=0
  - R20 labels weak/mined caveat

Usage:
    python3 eval/r25_graph_dense_ablation.py \\
        --workspace . \\
        --fixtures fixtures/r20_auto_wide \\
        --openlocus target/debug/openlocus \\
        --r21-report runs/r21-auto-wide-report.json \\
        --out runs/r25-graph-dense-ablation-report.json
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

SCHEMA_VERSION = "r25-v1"

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
    "R25_CANARY_fixture_label_secret_r25a1",
    "R25_CANARY_eval_benchmark_secret_r25b2",
    "R25_CANARY_docs_summary_secret_r25c3",
    "R25_CANARY_runs_prediction_secret_r25d4",
]

SEEDED_SOURCE_CANARY_FILE = "r25_canary_probe.py"

# ── Private-field denylist for artifact scan ────────────────────────────

PRIVATE_FIELD_DENYLIST = [
    "gold_spans", "gold_paths", "gold_lines", "hard_negatives",
    "hard_distractors", "expected_behavior", "query_category",
    "risk_tags", "must_not_primary", "oracle_type", "label_quality",
    "which_strategy_it_targets", "why_this_is_hard", "intent_guess",
    "caveat", "source_tier",
]

# ── Implemented strategies ─────────────────────────────────────────────

IMPLEMENTED_STRATEGIES = [
    "no_graph",
    "graph_basic",
    "rrf_plus_graph",
    "dense_mock",
    "rrf_plus_dense_mock",
    "rrf_plus_dense_mock_plus_graph",
]

UNAVAILABLE_STRATEGIES = {
    "quiver_recall": {
        "status": "unavailable",
        "reason": "quiver_not_implemented",
        "next_required_tests": [
            "Implement QuIVer retrieval adapter",
            "Run QuIVer on R20 dataset",
        ],
    },
    "quiver_precision": {
        "status": "not_measured",
        "reason": "quiver_not_implemented",
        "next_required_tests": [
            "Implement QuIVer retrieval adapter",
            "Score QuIVer against R20 labels",
        ],
    },
    "quiver_mrr": {
        "status": "not_measured",
        "reason": "quiver_not_implemented",
        "next_required_tests": [
            "Implement QuIVer retrieval adapter",
            "Score QuIVer against R20 labels",
        ],
    },
    "tdb_quiver_recall": {
        "status": "not_measured",
        "reason": "tdb_feature_gated_placeholder_not_applicable_for_ablation",
        "next_required_tests": [
            "Enable tdb feature and implement retrieval adapter",
            "Score TDB/QuIVer against R20 labels",
        ],
    },
    "tdb_quiver_precision": {
        "status": "not_measured",
        "reason": "tdb_feature_gated_placeholder_not_applicable_for_ablation",
        "next_required_tests": [
            "Enable tdb feature and implement retrieval adapter",
            "Score TDB/QuIVer against R20 labels",
        ],
    },
}


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


def count_jsonl_lines(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def verify_r21_artifact_manifest(runs_dir: Path) -> tuple[dict[str, Any], list[str]]:
    """Fail-closed verification of the R21 artifacts consumed by R25."""
    manifest_path = runs_dir / "r21-auto-wide-artifacts-manifest.json"
    issues: list[str] = []
    if not manifest_path.exists():
        return {"passed": False, "checked": 0, "manifest_path": str(manifest_path)}, [
            f"CRITICAL: R21 artifact manifest not found: {manifest_path}"
        ]

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"passed": False, "checked": 0, "manifest_path": str(manifest_path)}, [
            f"CRITICAL: R21 artifact manifest is not JSON: {exc}"
        ]

    checked = 0
    for strategy, artifacts in manifest.items():
        if not isinstance(artifacts, dict):
            issues.append(f"CRITICAL: R21 manifest {strategy}: entry is not object")
            continue
        for artifact_kind, info in artifacts.items():
            checked += 1
            if not isinstance(info, dict):
                issues.append(f"CRITICAL: R21 manifest {strategy}.{artifact_kind}: not object")
                continue
            raw_path = info.get("path", "")
            if not isinstance(raw_path, str) or not raw_path:
                issues.append(f"CRITICAL: R21 manifest {strategy}.{artifact_kind}: missing path")
                continue
            path = Path(raw_path)
            if not path.exists():
                issues.append(f"CRITICAL: R21 manifest {strategy}.{artifact_kind}: missing file {path}")
                continue
            actual_sha = file_sha256(path)
            actual_bytes = path.stat().st_size
            actual_lines = count_jsonl_lines(path)
            if info.get("sha256") != actual_sha:
                issues.append(f"CRITICAL: R21 manifest {strategy}.{artifact_kind}: sha mismatch")
            if info.get("bytes") != actual_bytes:
                issues.append(f"CRITICAL: R21 manifest {strategy}.{artifact_kind}: bytes mismatch")
            if info.get("jsonl_lines") != actual_lines:
                issues.append(f"CRITICAL: R21 manifest {strategy}.{artifact_kind}: jsonl_lines mismatch")

    rrf_pred = manifest.get("rrf", {}).get("predictions") if isinstance(manifest, dict) else None
    expected_rrf_path = (runs_dir / "r21-auto-wide-rrf-predictions.jsonl").resolve()
    if not isinstance(rrf_pred, dict):
        issues.append("CRITICAL: R21 manifest missing rrf.predictions")
    elif Path(rrf_pred.get("path", "")).resolve() != expected_rrf_path:
        issues.append("CRITICAL: R21 manifest rrf.predictions path mismatch")

    return {
        "passed": not issues,
        "checked": checked,
        "manifest_path": str(manifest_path),
        "manifest_sha256": file_sha256(manifest_path),
        "rrf_predictions_verified": isinstance(rrf_pred, dict) and not any("rrf.predictions" in i for i in issues),
    }, issues


def verify_artifact_manifest(manifest: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Fail-closed verification of artifact manifest path/sha/bytes/lines."""
    issues: list[str] = []
    checked = 0
    for strategy, artifacts in manifest.items():
        if not isinstance(artifacts, dict):
            issues.append(f"CRITICAL: artifact manifest entry for {strategy} is not an object")
            continue
        for artifact_kind, info in artifacts.items():
            checked += 1
            if not isinstance(info, dict):
                issues.append(
                    f"CRITICAL: artifact manifest {strategy}.{artifact_kind} is not an object"
                )
                continue
            raw_path = info.get("path", "")
            if not isinstance(raw_path, str) or not raw_path:
                issues.append(f"CRITICAL: artifact manifest {strategy}.{artifact_kind} missing path")
                continue
            path = Path(raw_path)
            if not path.exists():
                issues.append(
                    f"CRITICAL: artifact manifest {strategy}.{artifact_kind} missing file {path}"
                )
                continue
            actual = artifact_provenance(path)
            for field in ["sha256", "bytes", "jsonl_lines"]:
                if info.get(field) != actual.get(field):
                    issues.append(
                        f"CRITICAL: artifact manifest {strategy}.{artifact_kind} {field} mismatch "
                        f"expected={info.get(field)} actual={actual.get(field)}"
                    )
    return {"checked": checked, "passed": not issues}, issues


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
        extensions = set(entry.get("metadata", {}).get("extensions", list(SOURCE_EXTENSIONS)))
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
            tmp_dir = tempfile.mkdtemp(prefix=f"r25-isolated-{repo_id}-fail-")
            return Path(tmp_dir), issues
    else:
        issues.append(f"CRITICAL: Repo {repo_id}: unsupported source type {source_type}")
        tmp_dir = tempfile.mkdtemp(prefix=f"r25-isolated-{repo_id}-fail-")
        return Path(tmp_dir), issues

    tmp_dir = tempfile.mkdtemp(prefix=f"r25-isolated-{repo_id}-")
    isolated = Path(tmp_dir)

    (isolated / ".git").mkdir(exist_ok=True)
    policy_dir = isolated / ".openlocus"
    policy_dir.mkdir(exist_ok=True)

    policy_excludes = entry.get("policy", {}).get(
        "exclude",
        ["fixtures/**", "eval/**", "docs/**", "runs/**", ".openlocus/**",
         "target/**", "__pycache__/**", "*.tmp", "*.log", ".git/**",
         "node_modules/**", "dist/**", "build/**", ".venv/**"],
    )
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
    """Remove transient OpenLocus artifacts while preserving dense stores/audit."""
    openlocus_dir = isolated / ".openlocus"
    if not openlocus_dir.exists():
        return
    for child in openlocus_dir.iterdir():
        if child.name == "policy.toml":
            continue
        if child.name in {"embeddings", "audit"}:
            continue  # Preserve for dense operations
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            try:
                child.unlink()
            except OSError:
                pass


# ── CLI helpers ───────────────────────────────────────────────────────


def run_cli(openlocus: str, args: list[str], cwd: str) -> dict[str, Any]:
    """Run an openlocus CLI command and return parsed JSON + metadata."""
    t0 = time.perf_counter()
    proc = subprocess.run(args, check=False, text=True, capture_output=True, cwd=cwd)
    latency_ms = int((time.perf_counter() - t0) * 1000)

    result: dict[str, Any] = {}
    try:
        result = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        pass

    if isinstance(result, list):
        result = {"items": result}

    return {
        "result": result,
        "latency_ms": latency_ms,
        "returncode": proc.returncode,
        "stderr": proc.stderr[:500] if proc.stderr else "",
    }


# ── Graph basic: derive top path from public query ────────────────────


def _extract_evidence_from_search_result(result: dict[str, Any]) -> list[dict]:
    """Extract evidence list from a search CLI result.

    Search commands (symbol, regex, bm25) return a JSON array of evidence
    objects. The run_cli wrapper converts arrays to {"items": [...]}.
    Impact/retrieve commands return {"evidence": [...]}.
    """
    # Direct evidence key (impact, retrieve)
    if "evidence" in result and isinstance(result["evidence"], list):
        return result["evidence"]
    # Items key (search commands wrapped by run_cli)
    if "items" in result and isinstance(result["items"], list):
        return result["items"]
    # Fallback: if result itself looks like a list of evidence
    return []


def derive_top_path_symbol(openlocus: str, query: str, cwd: str) -> str | None:
    """Try symbol search to find top path. Returns path or None."""
    cli_result = run_cli(
        openlocus,
        [openlocus, "search", "symbol", query, "--json"],
        cwd,
    )
    if cli_result["returncode"] != 0:
        return None
    evidence = _extract_evidence_from_search_result(cli_result["result"])
    if evidence:
        top_path = evidence[0].get("path", "")
        if top_path:
            return top_path
    return None


def derive_top_path_regex(openlocus: str, query: str, cwd: str) -> str | None:
    """Regex fallback to find top path. Returns path or None."""
    cli_result = run_cli(
        openlocus,
        [openlocus, "search", "regex", query, "--json"],
        cwd,
    )
    if cli_result["returncode"] != 0:
        return None
    evidence = _extract_evidence_from_search_result(cli_result["result"])
    if evidence:
        top_path = evidence[0].get("path", "")
        if top_path:
            return top_path
    return None


def derive_top_path(openlocus: str, query: str, cwd: str) -> tuple[str | None, str]:
    """Derive top path using symbol search, then regex fallback.
    Returns (path, method_used)."""
    path = derive_top_path_symbol(openlocus, query, cwd)
    if path:
        return path, "symbol"
    path = derive_top_path_regex(openlocus, query, cwd)
    if path:
        return path, "regex"
    return None, "none"


def run_graph_impact(openlocus: str, top_path: str, cwd: str) -> list[dict]:
    """Run `openlocus impact <path> --depth 1 --json` and return evidence."""
    # Strip repo_id prefix if present (impact expects relative path in cwd)
    # If path is like "repo_id/src/foo.rs", we need just the part under the
    # repo_id folder since cwd is the isolated root which contains repo_id/
    cli_result = run_cli(
        openlocus,
        [openlocus, "impact", top_path, "--depth", "1", "--json"],
        cwd,
    )
    if cli_result["returncode"] != 0:
        return []
    return cli_result["result"].get("evidence", [])


# ── Dense mock ────────────────────────────────────────────────────────


def run_dense_build(openlocus: str, cwd: str) -> dict[str, Any]:
    """Run `openlocus dense build --provider mock --experimental --json` once."""
    cli_result = run_cli(
        openlocus,
        [openlocus, "dense", "build", "--provider", "mock", "--experimental", "--json"],
        cwd,
    )
    result = cli_result["result"]
    return {
        "success": result.get("success", False),
        "record_count": result.get("record_count", 0),
        "latency_ms": cli_result["latency_ms"],
        "returncode": cli_result["returncode"],
        "stderr": cli_result["stderr"],
    }


def run_dense_search(openlocus: str, query: str, cwd: str, limit: int = 10) -> list[dict]:
    """Run `openlocus dense search --provider mock --limit N --json <query>`."""
    cli_result = run_cli(
        openlocus,
        [openlocus, "dense", "search", "--provider", "mock",
         "--limit", str(limit), "--json", query],
        cwd,
    )
    if cli_result["returncode"] != 0:
        return []
    return cli_result["result"].get("evidence", [])


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


# ── Citation validation ───────────────────────────────────────────────


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
                prefix=f"r25-{strategy}-{repo_id}-citations-",
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
    if invalid != 0 or (total > 0 and rate < 1.0):
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


# ── Canary check ──────────────────────────────────────────────────────


def check_canary_retrieval(
    openlocus: str, isolated_roots: dict[str, Path]
) -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    checked = 0
    hits = 0
    failures = 0
    self_test_checked = 0
    self_test_hits = 0

    # Non-vacuous parser self-test: seed one temporary canary file, prove regex
    # search hits are detectable through the same extraction path, then remove it
    # before the real leakage scan.
    if isolated_roots:
        repo_id, isolated = next(iter(isolated_roots.items()))
        canary_file = isolated / repo_id / SEEDED_SOURCE_CANARY_FILE
        canary_file.parent.mkdir(parents=True, exist_ok=True)
        seeded_token = CANARY_TOKENS[0]
        canary_file.write_text(f"# temporary R25 canary {seeded_token}\n", encoding="utf-8")
        self_test_checked = 1
        cli_result = run_cli(
            openlocus,
            [openlocus, "search", "regex", seeded_token, "--json"],
            str(isolated),
        )
        evidence = _extract_evidence_from_search_result(cli_result["result"])
        if cli_result["returncode"] != 0 or not evidence:
            failures += 1
            issues.append(
                f"CRITICAL: source-leak canary self-test failed for repo {repo_id}; "
                f"returncode={cli_result['returncode']}"
            )
        else:
            self_test_hits = len(evidence)
        try:
            canary_file.unlink()
        except OSError:
            failures += 1
            issues.append(f"CRITICAL: failed to remove seeded source canary {canary_file}")
        clean_runtime_artifacts(isolated)

    for repo_id, isolated in isolated_roots.items():
        for token in CANARY_TOKENS:
            checked += 1
            cli_result = run_cli(
                openlocus,
                [openlocus, "search", "regex", token, "--json"],
                str(isolated),
            )
            clean_runtime_artifacts(isolated)
            if cli_result["returncode"] != 0:
                failures += 1
                issues.append(
                    f"CRITICAL: canary retrieval failed for repo {repo_id}: "
                    f"{cli_result.get('stderr', '')[:200]}"
                )
                continue
            evidence = _extract_evidence_from_search_result(cli_result["result"])
            if evidence:
                hits += len(evidence)
                paths = [e.get("path", "") for e in evidence[:5]]
                issues.append(
                    f"CRITICAL: canary token was retrievable in isolated repo {repo_id}; "
                    f"token={token}, paths={paths}"
                )

    return {
        "checked": checked,
        "self_test_checked": self_test_checked,
        "self_test_hits": self_test_hits,
        "hits": hits,
        "failures": failures,
        "passed": hits == 0 and failures == 0 and self_test_hits > 0,
    }, issues


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


# ── New R25 metrics: span contribution analysis ──────────────────────


def compute_span_contribution(
    expansion_predictions: list[dict],
    baseline_predictions: list[dict],
    gold: dict[str, dict],
    strategy_label: str,
) -> dict[str, Any]:
    """Compute added_gold_span, added_false_span for expansion vs baseline.

    For each task with gold_spans:
    - Baseline lines = lines in baseline prediction evidence
    - Expansion lines = lines in expansion prediction evidence
    - Added lines = expansion - baseline (set difference)
    - added_gold_span = number of added lines that are in gold
    - added_false_span = number of added lines that are NOT in gold
    """
    baseline_by_task: dict[str, dict] = {p["task_id"]: p for p in baseline_predictions}

    total_added_gold = 0
    total_added_false = 0
    tasks_with_additions = 0
    tasks_expansion_blocked = 0  # added_false > added_gold

    for pred in expansion_predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        label = gold[task_id]
        gold_lines = build_gold_line_set(label)
        if not gold_lines:
            continue

        # Build baseline line set
        baseline_pred = baseline_by_task.get(task_id, {})
        baseline_lines: set[tuple[str, int]] = set()
        for e in baseline_pred.get("evidence", []):
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            path = e.get("path", "")
            for ln in range(start, end + 1):
                baseline_lines.add((path, ln))

        # Build expansion line set
        expansion_lines: set[tuple[str, int]] = set()
        for e in pred.get("evidence", []):
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            path = e.get("path", "")
            for ln in range(start, end + 1):
                expansion_lines.add((path, ln))

        # Added lines = expansion - baseline
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
        f"{strategy_label}_tasks_expansion_blocked": tasks_expansion_blocked,
        f"{strategy_label}_default_expansion_blocked": default_expansion_blocked,
    }


def compute_graph_pollution_ratio(
    graph_predictions: list[dict],
) -> float:
    """Ratio of graph evidence on forbidden paths vs total graph evidence."""
    total_evidence = 0
    polluted_evidence = 0
    for pred in graph_predictions:
        for e in pred.get("evidence", []):
            total_evidence += 1
            path = e.get("path", "")
            for fp in FORBIDDEN_PREFIXES:
                forbidden_component = fp.strip("/")
                path_parts = path.replace("\\", "/").split("/")
                if path.startswith(fp) or forbidden_component in path_parts:
                    polluted_evidence += 1
                    break
    return polluted_evidence / total_evidence if total_evidence else 0.0


def compute_token_waste_delta(
    expansion_predictions: list[dict],
    baseline_predictions: list[dict],
    gold: dict[str, dict],
) -> float:
    """Token waste delta: expansion token_waste - baseline token_waste."""
    baseline_waste = token_waste_ratio_at_k(baseline_predictions, gold, 10)
    expansion_waste = token_waste_ratio_at_k(expansion_predictions, gold, 10)
    return expansion_waste - baseline_waste


# ── Score phase ───────────────────────────────────────────────────────


def score_predictions(
    predictions: list[dict],
    gold: dict[str, dict],
    citation_summary: dict[str, Any],
    strategy: str,
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

    return metrics


# ── Artifact safety scans ─────────────────────────────────────────────


def scan_artifacts_for_private_fields(
    runs_dir: Path, prefix: str
) -> list[str]:
    issues: list[str] = []
    for path in sorted(runs_dir.glob(f"{prefix}-*.jsonl")):
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
    runs_dir: Path
) -> list[str]:
    issues: list[str] = []
    for path in sorted(runs_dir.glob("r25-*.jsonl")):
        content = path.read_text(encoding="utf-8")
        for token in CANARY_TOKENS:
            if token in content:
                issues.append(
                    f"CRITICAL: canary token '{token}' found in {path.name}"
                )
    return issues


# ── Main ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="R25 Graph+Dense Ablation (eval-layer only)"
    )
    parser.add_argument("--workspace", default=".", help="Workspace root directory")
    parser.add_argument("--openlocus", default="target/debug/openlocus", help="Path to openlocus binary")
    parser.add_argument("--fixtures", default="fixtures/r20_auto_wide", help="Fixtures directory relative to workspace")
    parser.add_argument("--r21-report", default="runs/r21-auto-wide-report.json", help="R21 report for RRF baseline")
    parser.add_argument("--out", default="runs/r25-graph-dense-ablation-report.json", help="Output path for JSON report")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tasks (smoke test)")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    fixtures_dir = workspace / args.fixtures
    openlocus_path = str(Path(args.openlocus).resolve())
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = (workspace / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    r21_report_path = workspace / args.r21_report

    if not fixtures_dir.exists():
        print(f"ERROR: Fixtures directory not found: {fixtures_dir}", file=sys.stderr)
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
    safety_issues: list[str] = list(lock_issues)
    for info in lock_info:
        print(f"  INFO: {info}")

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

    print(f"R25 Graph+Dense Ablation: {len(tasks)} tasks, {len(repos)} repos")
    print(f"  Phase 1: RUN (public tasks only, no labels)")

    # ══════════════════════════════════════════════════════════════════
    # Create isolated roots
    # ══════════════════════════════════════════════════════════════════

    isolated_roots: dict[str, Path] = {}
    for repo_id, entry in repos.items():
        isolated, iso_issues = create_isolated_root(repo_id, entry)
        isolated_roots[repo_id] = isolated
        safety_issues.extend(iso_issues)

    # Source-leak canary check: before dense build, verify private canary tokens
    # do not appear in isolated copied source via regex search. This is not a
    # dense-path canary; R24 owns dense-path canary hardening.
    canary_summary, canary_issues = check_canary_retrieval(openlocus_path, isolated_roots)
    safety_issues.extend(canary_issues)

    # ══════════════════════════════════════════════════════════════════
    # 1) Load R21 RRF baseline predictions (no_graph strategy)
    # ══════════════════════════════════════════════════════════════════

    print(f"  1) Loading R21 RRF baseline (no_graph)...")

    r21_manifest_verification, r21_manifest_issues = verify_r21_artifact_manifest(
        workspace / "runs"
    )
    safety_issues.extend(r21_manifest_issues)
    if r21_manifest_issues:
        print("ERROR: R21 artifact manifest verification failed before RRF baseline use", file=sys.stderr)
        for issue in r21_manifest_issues[:20]:
            print(f"  - {issue}", file=sys.stderr)
        sys.exit(1)

    r21_rrf_predictions: list[dict] = []
    r21_rrf_by_task: dict[str, dict] = {}

    r21_rrf_pred_path = workspace / "runs" / "r21-auto-wide-rrf-predictions.jsonl"
    if r21_rrf_pred_path.exists():
        r21_rrf_predictions = load_jsonl(r21_rrf_pred_path)
        r21_rrf_by_task = {p["task_id"]: p for p in r21_rrf_predictions}
    else:
        print(f"ERROR: R21 RRF predictions not found at {r21_rrf_pred_path}", file=sys.stderr)
        sys.exit(1)

    # Build no_graph predictions from R21 RRF
    no_graph_predictions: list[dict] = []
    for task in tasks:
        task_id = task["task_id"]
        rrf_pred = r21_rrf_by_task.get(task_id, {})
        evidence = rrf_pred.get("evidence", [])
        no_graph_predictions.append({
            "task_id": task_id,
            "repo_id": task.get("repo_id", ""),
            "query": task.get("query", ""),
            "strategy": "no_graph",
            "evidence": evidence,
            "latency_ms": 0,
            "returncode": rrf_pred.get("returncode", 0),
        })

    # ══════════════════════════════════════════════════════════════════
    # 2) graph_basic: derive top path → openlocus impact --depth 1
    # ══════════════════════════════════════════════════════════════════

    print(f"  2) Running graph_basic (impact --depth 1)...")

    graph_basic_predictions: list[dict] = []
    graph_path_method_counts: dict[str, int] = defaultdict(int)
    graph_impact_failures = 0
    graph_impact_no_evidence = 0

    for task in tasks:
        query = task["query"]
        task_id = task["task_id"]
        repo_id = task.get("repo_id", "")

        if repo_id not in isolated_roots:
            safety_issues.append(
                f"CRITICAL: task {task_id} references unknown repo_id '{repo_id}'."
            )
            graph_basic_predictions.append({
                "task_id": task_id,
                "repo_id": repo_id,
                "query": query,
                "strategy": "graph_basic",
                "evidence": [],
                "top_path": None,
                "path_derivation_method": "none",
                "latency_ms": 0,
                "returncode": -1,
            })
            continue

        cwd = str(isolated_roots[repo_id])
        top_path, method = derive_top_path(openlocus_path, query, cwd)
        graph_path_method_counts[method] += 1
        clean_runtime_artifacts(isolated_roots[repo_id])

        evidence: list[dict] = []
        if top_path:
            # Run graph impact on the top path
            evidence = run_graph_impact(openlocus_path, top_path, cwd)
            clean_runtime_artifacts(isolated_roots[repo_id])
            if not evidence:
                graph_impact_no_evidence += 1
        else:
            graph_impact_failures += 1

        graph_basic_predictions.append({
            "task_id": task_id,
            "repo_id": repo_id,
            "query": query,
            "strategy": "graph_basic",
            "evidence": evidence,
            "top_path": top_path,
            "path_derivation_method": method,
            "latency_ms": 0,
            "returncode": 0,
        })

    print(f"      path methods: {dict(graph_path_method_counts)}")
    print(f"      impact failures: {graph_impact_failures}, no evidence: {graph_impact_no_evidence}")

    # ══════════════════════════════════════════════════════════════════
    # 3) rrf_plus_graph: RRF fuse graph_basic + R21 rrf
    # ══════════════════════════════════════════════════════════════════

    print(f"  3) Building rrf_plus_graph...")

    rrf_plus_graph_predictions: list[dict] = []
    for task in tasks:
        task_id = task["task_id"]
        repo_id = task.get("repo_id", "")
        graph_pred = {p["task_id"]: p for p in graph_basic_predictions}.get(task_id, {})
        rrf_pred = r21_rrf_by_task.get(task_id, {})
        fused_evidence = rrf_fuse_predictions(graph_pred, rrf_pred)
        rrf_plus_graph_predictions.append({
            "task_id": task_id,
            "repo_id": repo_id,
            "query": task.get("query", ""),
            "strategy": "rrf_plus_graph",
            "evidence": fused_evidence,
            "latency_ms": 0,
            "returncode": 0,
        })

    # ══════════════════════════════════════════════════════════════════
    # 4) dense_mock: candidate-channel safety smoke
    # ══════════════════════════════════════════════════════════════════

    print(f"  4) Running dense_mock (build + search)...")

    dense_build_results: dict[str, dict] = {}
    for repo_id, isolated in isolated_roots.items():
        build_result = run_dense_build(openlocus_path, str(isolated))
        dense_build_results[repo_id] = build_result
        if not build_result["success"]:
            safety_issues.append(
                f"CRITICAL: dense build failed for repo {repo_id}: "
                f"{build_result.get('stderr', '')[:200]}"
            )
        # Do NOT clean embeddings; dense search needs them
        clean_runtime_artifacts(isolated)

    dense_mock_predictions: list[dict] = []
    for task in tasks:
        query = task["query"]
        task_id = task["task_id"]
        repo_id = task.get("repo_id", "")

        if repo_id not in isolated_roots:
            dense_mock_predictions.append({
                "task_id": task_id,
                "repo_id": repo_id,
                "query": query,
                "strategy": "dense_mock",
                "evidence": [],
                "latency_ms": 0,
                "returncode": -1,
            })
            continue

        cwd = str(isolated_roots[repo_id])
        evidence = run_dense_search(openlocus_path, query, cwd)
        clean_runtime_artifacts(isolated_roots[repo_id])

        dense_mock_predictions.append({
            "task_id": task_id,
            "repo_id": repo_id,
            "query": query,
            "strategy": "dense_mock",
            "evidence": evidence,
            "latency_ms": 0,
            "returncode": 0,
        })

    # ══════════════════════════════════════════════════════════════════
    # 5) rrf_plus_dense_mock: RRF fuse dense_mock + R21 rrf
    # ══════════════════════════════════════════════════════════════════

    print(f"  5) Building rrf_plus_dense_mock...")

    rrf_plus_dense_mock_predictions: list[dict] = []
    for task in tasks:
        task_id = task["task_id"]
        repo_id = task.get("repo_id", "")
        dense_pred = {p["task_id"]: p for p in dense_mock_predictions}.get(task_id, {})
        rrf_pred = r21_rrf_by_task.get(task_id, {})
        fused_evidence = rrf_fuse_predictions(dense_pred, rrf_pred)
        rrf_plus_dense_mock_predictions.append({
            "task_id": task_id,
            "repo_id": repo_id,
            "query": task.get("query", ""),
            "strategy": "rrf_plus_dense_mock",
            "evidence": fused_evidence,
            "latency_ms": 0,
            "returncode": 0,
        })

    # ══════════════════════════════════════════════════════════════════
    # 6) rrf_plus_dense_mock_plus_graph: RRF fuse all three
    # ══════════════════════════════════════════════════════════════════

    print(f"  6) Building rrf_plus_dense_mock_plus_graph...")

    rrf_plus_dense_mock_plus_graph_predictions: list[dict] = []
    for task in tasks:
        task_id = task["task_id"]
        repo_id = task.get("repo_id", "")
        dense_pred = {p["task_id"]: p for p in dense_mock_predictions}.get(task_id, {})
        graph_pred = {p["task_id"]: p for p in graph_basic_predictions}.get(task_id, {})
        rrf_pred = r21_rrf_by_task.get(task_id, {})
        fused_evidence = rrf_fuse_three_predictions(dense_pred, graph_pred, rrf_pred)
        rrf_plus_dense_mock_plus_graph_predictions.append({
            "task_id": task_id,
            "repo_id": repo_id,
            "query": task.get("query", ""),
            "strategy": "rrf_plus_dense_mock_plus_graph",
            "evidence": fused_evidence,
            "latency_ms": 0,
            "returncode": 0,
        })

    # ══════════════════════════════════════════════════════════════════
    # Citation validation for all strategies before cleanup
    # ══════════════════════════════════════════════════════════════════

    print(f"  Citation validation (before cleanup)...")

    all_strategy_predictions = {
        "no_graph": no_graph_predictions,
        "graph_basic": graph_basic_predictions,
        "rrf_plus_graph": rrf_plus_graph_predictions,
        "dense_mock": dense_mock_predictions,
        "rrf_plus_dense_mock": rrf_plus_dense_mock_predictions,
        "rrf_plus_dense_mock_plus_graph": rrf_plus_dense_mock_plus_graph_predictions,
    }

    citation_summaries: dict[str, dict[str, Any]] = {}

    for strategy, predictions in all_strategy_predictions.items():
        forbidden_issues = check_predictions_for_forbidden_paths(predictions, strategy)
        safety_issues.extend(forbidden_issues)

        # no_graph evidence comes from R21 which was already validated
        if strategy == "no_graph":
            citation_summaries[strategy] = {
                "citation_validity": 1.0,
                "citation_valid_count": 0,
                "citation_total_count": 0,
                "citation_invalid_count": 0,
                "citation_validator_invocations": 0,
                "citation_validation_mode": "inherited_from_r21",
                "citation_inherited_from_base": True,
                "citation_hash_checked": True,
                "citation_not_applicable": True,
            }
            continue

        citation_summary, citation_issues = validate_predictions_with_rust(
            openlocus_path, strategy, predictions, isolated_roots
        )
        # For composite strategies, mark inheritance
        if strategy in ("rrf_plus_graph", "rrf_plus_dense_mock", "rrf_plus_dense_mock_plus_graph"):
            citation_summary["citation_inherited_from_base"] = True
            citation_summary["citation_validated_by_rust"] = True
            if citation_summary.get("citation_total_count", 0) == 0:
                citation_summary["citation_not_applicable"] = True
                citation_summary["citation_hash_checked"] = False
        citation_summaries[strategy] = citation_summary
        safety_issues.extend(citation_issues)

    # ══════════════════════════════════════════════════════════════════
    # Write R25-owned artifacts
    # ══════════════════════════════════════════════════════════════════

    runs_dir = workspace / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    artifact_manifest: dict[str, Any] = {}

    for strategy, predictions in all_strategy_predictions.items():
        pred_path = runs_dir / f"r25-{strategy}-predictions.jsonl"
        evid_path = runs_dir / f"r25-{strategy}-evidence.jsonl"
        trace_path = runs_dir / f"r25-{strategy}-trace.jsonl"

        evidence_list = [
            {"task_id": p["task_id"], "repo_id": p.get("repo_id", ""), "evidence": p.get("evidence", [])}
            for p in predictions
        ]
        trace_list = [
            {
                "task_id": p["task_id"],
                "repo_id": p.get("repo_id", ""),
                "query": p.get("query", ""),
                "strategy": strategy,
                "evidence_count": len(p.get("evidence", [])),
                "latency_ms": p.get("latency_ms", 0),
                "returncode": p.get("returncode", 0),
            }
            for p in predictions
        ]

        write_jsonl(pred_path, predictions)
        write_jsonl(evid_path, evidence_list)
        write_jsonl(trace_path, trace_list)

        artifact_manifest[strategy] = {
            "predictions": artifact_provenance(pred_path),
            "evidence": artifact_provenance(evid_path),
            "trace": artifact_provenance(trace_path),
        }

    # Write manifest
    manifest_out_path = runs_dir / "r25-artifacts-manifest.json"
    manifest_out_path.write_text(
        json.dumps(artifact_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifact_manifest_verification, artifact_manifest_issues = verify_artifact_manifest(
        artifact_manifest
    )
    safety_issues.extend(artifact_manifest_issues)

    # Cleanup isolated roots (after citation validation)
    for isolated in isolated_roots.values():
        shutil.rmtree(isolated, ignore_errors=True)

    # ══════════════════════════════════════════════════════════════════
    # Phase 2: SCORE (labels only, no CLI)
    # ══════════════════════════════════════════════════════════════════

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

    # Score all strategies
    strategy_metrics: dict[str, dict[str, Any]] = {}
    for strategy, predictions in all_strategy_predictions.items():
        metrics = score_predictions(
            predictions, gold, citation_summaries.get(strategy, {}), strategy
        )
        strategy_metrics[strategy] = metrics

    # ══════════════════════════════════════════════════════════════════
    # Compute new R25 metrics
    # ══════════════════════════════════════════════════════════════════

    print(f"  Computing R25 ablation metrics...")

    # Graph contribution metrics (graph_basic vs no_graph)
    graph_contribution = compute_span_contribution(
        graph_basic_predictions, no_graph_predictions, gold, "graph"
    )

    # Graph pollution ratio
    graph_pollution_ratio = compute_graph_pollution_ratio(graph_basic_predictions)

    # Graph token waste delta
    graph_token_waste_delta = compute_token_waste_delta(
        graph_basic_predictions, no_graph_predictions, gold
    )

    # Dense contribution metrics (dense_mock vs no_graph)
    dense_contribution = compute_span_contribution(
        dense_mock_predictions, no_graph_predictions, gold, "dense"
    )

    # Combined contribution metrics (rrf_plus_dense_mock_plus_graph vs no_graph)
    combined_contribution = compute_span_contribution(
        rrf_plus_dense_mock_plus_graph_predictions, no_graph_predictions, gold, "combined"
    )

    # RRF+graph contribution vs no_graph
    rrf_plus_graph_contribution = compute_span_contribution(
        rrf_plus_graph_predictions, no_graph_predictions, gold, "rrf_plus_graph"
    )

    # RRF+dense contribution vs no_graph
    rrf_plus_dense_contribution = compute_span_contribution(
        rrf_plus_dense_mock_predictions, no_graph_predictions, gold, "rrf_plus_dense"
    )

    # ══════════════════════════════════════════════════════════════════
    # Safety gates
    # ══════════════════════════════════════════════════════════════════

    critical_issues: list[str] = []
    warning_issues: list[str] = []
    for issue in safety_issues:
        if issue.startswith("CRITICAL:") or issue.startswith("LEAK:"):
            critical_issues.append(issue)
        elif issue.startswith("WARNING:"):
            warning_issues.append(issue)
        else:
            critical_issues.append(issue)

    # Citation validity gate
    for strategy, metrics in strategy_metrics.items():
        if metrics.get("citation_total_count", 0) > 0:
            if metrics.get("citation_validity", 0.0) != 1.0:
                critical_issues.append(
                    f"CRITICAL: {strategy} citation_validity={metrics.get('citation_validity')} != 1.0"
                )

    # Artifact safety scan
    private_field_issues = scan_artifacts_for_private_fields(runs_dir, "r25")
    canary_token_issues = scan_artifacts_for_canary_tokens(runs_dir)
    if private_field_issues:
        critical_issues.extend(private_field_issues)
    if canary_token_issues:
        critical_issues.extend(canary_token_issues)

    # ══════════════════════════════════════════════════════════════════
    # Build report
    # ══════════════════════════════════════════════════════════════════

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
        "dense_or_llm_claims": False,
        "labels_loaded_after_run": True,
        "description": (
            "R25 Graph+Dense Ablation. Eval-layer ablation study of graph_basic, "
            "dense_mock, and combination strategies on R20 auto-wide fixtures. "
            "dense_mock is non-semantic (mock blake3 vectors). QuIVer not implemented. "
            "TDB placeholder. Does NOT change Rust core or EvidenceCore."
        ),
        "source_dataset_manifest": {
            "path": str(manifest_path),
            "not_promotion_evidence": manifest.get("not_promotion_evidence", True),
            "core_changes": manifest.get("core_changes", False),
            "remote_calls": manifest.get("remote_calls", 0),
            "dense_or_llm_claims": manifest.get("dense_or_llm_claims", False),
        },
        "r21_report_used": str(r21_report_path) if r21_report_path.exists() else "not_found",
        "r21_artifact_manifest_verification": r21_manifest_verification,
        "strategies": {
            "implemented": IMPLEMENTED_STRATEGIES,
            "unavailable": UNAVAILABLE_STRATEGIES,
        },
        "metrics": strategy_metrics,
        "ablation_metrics": {
            "graph_contribution": graph_contribution,
            "graph_pollution_ratio": graph_pollution_ratio,
            "graph_token_waste_delta": graph_token_waste_delta,
            "dense_contribution": dense_contribution,
            "rrf_plus_graph_contribution": rrf_plus_graph_contribution,
            "rrf_plus_dense_contribution": rrf_plus_dense_contribution,
            "combined_contribution": combined_contribution,
        },
        "graph_basic_stats": {
            "path_method_counts": dict(graph_path_method_counts),
            "impact_failures": graph_impact_failures,
            "impact_no_evidence": graph_impact_no_evidence,
        },
        "dense_build_results": {
            k: {"success": v["success"], "record_count": v["record_count"]}
            for k, v in dense_build_results.items()
        },
        "quiver_diagnostics": UNAVAILABLE_STRATEGIES,
        "tdb_status": {
            "status": "not_applicable_for_ablation",
            "reason": "TDB is a feature-gated metadata/chunk store placeholder. "
                      "Not relevant to graph+dense ablation. tdb_stale_leak_count is not_applicable.",
        },
        "safety_gates": {
            "all_passed": len(critical_issues) == 0,
            "critical_issues": critical_issues,
            "warning_issues": warning_issues,
            "source_leak_canary": canary_summary,
            "artifact_private_field_scan": {
                "scanned": True,
                "issues_found": len(private_field_issues),
            },
            "artifact_canary_token_scan": {
                "scanned": True,
                "issues_found": len(canary_token_issues),
            },
            "artifact_manifest_verification": artifact_manifest_verification,
            "r21_artifact_manifest_verification": r21_manifest_verification,
        },
        "artifact_manifest": {
            "path": str(manifest_out_path),
            "sha256": file_sha256(manifest_out_path),
            "artifact_count": artifact_manifest_verification.get("checked", 0),
        },
        "phases": {
            "run": "public_tasks_only_no_labels",
            "score": "labels_only_no_cli",
            "isolation": "temp_root_per_repo_with_repo_id_folder",
            "citation_mode": "fail_closed_hash_range_path",
            "path_matching": "exact_or_single_repo_id_prefix",
            "policy": "isolated_policy_toml_from_repo_lock",
            "source_type": "external_local_absolute_path",
            "dense_provider": "mock_deterministic_blake3_vectors_not_semantic",
            "graph_depth": 1,
            "graph_path_derivation": "symbol_top_path_then_regex_fallback",
        },
        "labels_caveat": (
            "R20 labels are weak/mined (258 weak, 315 mined_high_confidence, 168 mined). "
            "Not human_reviewed. Not promotion evidence."
        ),
        "tasks_count": len(tasks),
        "repos_count": len(repos),
        "labels_count": len(gold),
    }

    out_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    # ── Print summary ─────────────────────────────────────────────────

    print(f"\n{'='*70}")
    print(f"R25 Graph+Dense Ablation Results")
    print(f"{'='*70}")

    print(f"\n  Strategies: {len(IMPLEMENTED_STRATEGIES)} implemented, "
          f"{len(UNAVAILABLE_STRATEGIES)} unavailable")

    metric_display = [
        "FileRecall@1", "FileRecall@3", "FileRecall@5", "MRR",
        "SpanF0.5", "SpanPrecision", "SpanRecall",
        "token_waste", "no_gold_nonempty_rate",
        "hard_distractor_hit_rate",
        "primary_false_positive_rate",
        "must_not_primary_violation_rate",
        "abstain_rate",
    ]

    for strategy in IMPLEMENTED_STRATEGIES:
        metrics = strategy_metrics.get(strategy, {})
        print(f"\n  {strategy}:")
        for key in metric_display:
            val = metrics.get(key)
            if val is not None:
                if isinstance(val, float):
                    print(f"    {key}: {val:.3f}")
                else:
                    print(f"    {key}: {val}")
        lat = metrics.get("latency", {})
        if lat:
            print(f"    latency_p50: {lat.get('p50', 0)}ms")
        print(f"    citation_validity: {metrics.get('citation_validity', 'N/A')}")

    # Print ablation metrics
    print(f"\n  Ablation Metrics:")
    print(f"    graph_pollution_ratio: {graph_pollution_ratio:.3f}")
    print(f"    graph_token_waste_delta: {graph_token_waste_delta:+.3f}")
    for label, contribution in [
        ("graph", graph_contribution),
        ("dense", dense_contribution),
        ("rrf_plus_graph", rrf_plus_graph_contribution),
        ("rrf_plus_dense", rrf_plus_dense_contribution),
        ("combined", combined_contribution),
    ]:
        ag = contribution.get(f"{label}_added_gold_span", 0)
        af = contribution.get(f"{label}_added_false_span", 0)
        blocked = contribution.get(f"{label}_default_expansion_blocked", False)
        print(f"    {label}: added_gold={ag}, added_false={af}, blocked={blocked}")

    # QuIVer/TDB status
    print(f"\n  QuIVer Diagnostics: all unavailable/not_measured (quiver_not_implemented)")
    print(f"  TDB: not_applicable_for_ablation")

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
    print(f"  dense_mock: non-semantic candidate-channel safety smoke only")
    print(f"  quiver_implemented: False (confirmed)")
    print(f"  tdb: not applicable for this ablation")

    if critical_issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
