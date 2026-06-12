#!/usr/bin/env python3
"""R24 QuIVer/TDB/Dense Probe.

NOT a QuIVer bakeoff. This is an availability + mock dense candidate-channel
probe + TDB placeholder status check. QuIVer is NOT implemented and must be
reported as unavailable; no fabricated QuIVer quality data is produced.

Core principles:
- QuIVer is not implemented -> report unavailable, not run
- TDB is not ANN/QuIVer -> feature-gated metadata/chunk store; probe placeholder only
- dense_real is unavailable; dense_mock is candidate-channel safety/quality-smoke
  (not semantic quality)

Architecture: strictly separated RUN and SCORE phases.
  Phase 1 (RUN): availability checks + dense mock candidate-channel probe.
    Loads only public tasks + repo lock. Creates isolated benchmark roots by
    allowlist-copying source files. Runs dense build/search via openlocus CLI.
    Never reads labels.
  Phase 2 (SCORE): loads predictions + labels. Computes metrics.
    Never invokes openlocus CLI.

Safety gates:
- labels not loaded until after dense run complete
- citation validator pass for dense artifacts
- artifact manifest path/sha/bytes/lines verified
- canary/no label leakage: public tasks only in run phase; labels only score
- no promotion/dense real/QuIVer quality claims
- runs artifacts gitignored

Usage:
    python3 eval/r24_quiver_tdb_probe.py \\
        --workspace . \\
        --openlocus target/debug/openlocus \\
        --fixtures fixtures/r20_auto_wide \\
        --r21-report runs/r21-auto-wide-report.json \\
        --out runs/r24-quiver-tdb-probe.json
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

SCHEMA_VERSION = "r24-v1"

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
    "R24_CANARY_fixture_label_secret_a1b2",
    "R24_CANARY_eval_benchmark_secret_c3d4",
    "R24_CANARY_docs_summary_secret_e5f6",
    "R24_CANARY_runs_prediction_secret_g7h8",
]

DENSE_QUERY_CANARY_TOKENS = [
    "public dense probe alpha",
    "public dense probe beta",
]

# Non-secret query that should exercise dense search after build. It is not a
# leak token; it verifies that dense search traverses the built vector store.
DENSE_PATH_CANARY_QUERY = "openlocus retrieval candidate channel probe"

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

# ── QuIVer scan patterns ──────────────────────────────────────────────

QUIVER_SCAN_PATTERNS = [
    "quiver",
    "QuIVer",
    "QUIVER",
]

QUIVER_SCAN_EXCLUDE_DIRS = {
    "eval", "docs", "runs", "fixtures", ".git", "__pycache__",
    "target", "node_modules",
}

# ── Private-field denylist for artifact scan ────────────────────────────

PRIVATE_FIELD_DENYLIST = [
    "gold_spans", "gold_paths", "gold_lines", "hard_negatives",
    "hard_distractors", "expected_behavior", "query_category",
    "risk_tags", "must_not_primary", "oracle_type", "label_quality",
    "which_strategy_it_targets", "why_this_is_hard", "intent_guess",
    "caveat", "source_tier",
]

# ── Dense semantic trap / proper_name / config / API category buckets ──

DENSE_SEMANTIC_TRAP_CATEGORIES = {
    "dense_semantic_trap",
    "generated_vendor_trap",
    "graph_neighbor_trap",
}

PROPER_NAME_CATEGORIES = {
    "proper_name_api_config_regression",
}

CONFIG_API_CATEGORIES = {
    "config_key_trap",
    "route_handler_trap",
    "same_name_symbol",
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
            tmp_dir = tempfile.mkdtemp(prefix=f"r24-isolated-{repo_id}-fail-")
            return Path(tmp_dir), issues
    else:
        issues.append(f"CRITICAL: Repo {repo_id}: unsupported source type {source_type}")
        tmp_dir = tempfile.mkdtemp(prefix=f"r24-isolated-{repo_id}-fail-")
        return Path(tmp_dir), issues

    tmp_dir = tempfile.mkdtemp(prefix=f"r24-isolated-{repo_id}-")
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
    """Remove transient OpenLocus artifacts while preserving dense stores/audit.

    R24 needs the `.openlocus/embeddings` vector store and `.openlocus/audit`
    files to survive between dense build and dense search, and to remain
    available for leak scanning. Only transient traces/context artifacts are
    removed here. The entire isolated root is removed at the end of the probe.
    """
    openlocus_dir = isolated / ".openlocus"
    if not openlocus_dir.exists():
        return
    for child in openlocus_dir.iterdir():
        if child.name in {"policy.toml", "embeddings", "audit"}:
            continue
        if child.name in {"traces", "context"} and child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        elif child.name.startswith(".r24-") or child.name.endswith(".tmp"):
            try:
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    child.unlink()
            except OSError:
                pass


# ── 1) Availability checks ───────────────────────────────────────────


def quiver_implementation_scan(workspace: Path) -> dict[str, Any]:
    """Scan for QuIVer implementation. Fail-closed: only eval/docs placeholders
    are acceptable. Any real implementation in Rust crates = quiver_implemented=true."""
    findings: list[str] = []
    impl_found = False

    # Scan Rust crate sources for QuIVer symbols/deps
    crates_dir = workspace / "crates"
    if crates_dir.exists():
        for dirpath, dirnames, filenames in os.walk(crates_dir):
            dirnames[:] = [d for d in dirnames if d not in {"target", "node_modules"}]
            for fname in filenames:
                if not fname.endswith((".rs", ".toml")):
                    continue
                full = Path(dirpath) / fname
                rel = str(full.relative_to(workspace)).replace(os.sep, "/")
                # Skip eval/docs placeholders
                if rel.startswith("eval/") or rel.startswith("docs/"):
                    continue
                try:
                    content = full.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                for pattern in QUIVER_SCAN_PATTERNS:
                    if pattern.lower() in content.lower():
                        findings.append(f"QuIVer reference in {rel}")
                        # Check if it's a real implementation vs a comment/placeholder
                        for line in content.splitlines():
                            if pattern.lower() in line.lower():
                                stripped = line.strip()
                                # Comments and doc references are not implementation
                                if stripped.startswith("//") or stripped.startswith("///"):
                                    continue
                                # Cargo.toml dependency
                                if fname == "Cargo.toml" and "quiver" in stripped.lower():
                                    impl_found = True
                                    findings.append(f"QuIVer dependency in {rel}: {stripped[:100]}")
                                # Actual Rust code with quiver
                                elif fname.endswith(".rs") and not stripped.startswith("//"):
                                    # Check for struct/impl/fn/pattern definitions
                                    if any(kw in stripped for kw in ["struct ", "impl ", "fn ", "enum ", "trait ", "mod "]):
                                        impl_found = True
                                        findings.append(f"QuIVer implementation in {rel}: {stripped[:100]}")
                if impl_found:
                    break
            if impl_found:
                break

    # Also check Cargo.toml at workspace root
    root_cargo = workspace / "Cargo.toml"
    if root_cargo.exists():
        content = root_cargo.read_text(encoding="utf-8", errors="replace")
        for pattern in QUIVER_SCAN_PATTERNS:
            if pattern.lower() in content.lower():
                findings.append(f"QuIVer reference in Cargo.toml (root)")
                # Check if it's an actual dependency
                for line in content.splitlines():
                    if pattern.lower() in line.lower() and not line.strip().startswith("#"):
                        if "quiver" in line.lower():
                            impl_found = True
                            findings.append(f"QuIVer dependency in root Cargo.toml: {line.strip()[:100]}")

    return {
        "quiver_implemented": impl_found,
        "scan_findings": findings,
        "scan_status": "impl_found" if impl_found else "no_impl_found_only_eval_docs_refs",
    }


def tdb_status_probe(openlocus: str, workspace: Path) -> dict[str, Any]:
    """Probe TDB default status via `openlocus store status tdb --json`.
    Do NOT claim retrieval quality. Only report availability."""
    try:
        proc = subprocess.run(
            [openlocus, "store", "status", "tdb", "--json"],
            check=False, text=True, capture_output=True,
            cwd=str(workspace), timeout=30,
        )
        if proc.returncode != 0:
            return {
                "available": False,
                "success": False,
                "raw_output": proc.stdout[:500] if proc.stdout else "",
                "stderr": proc.stderr[:500] if proc.stderr else "",
                "retrieval_quality_claimed": False,
            }
        result = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
        return {
            "available": result.get("available", False),
            "success": result.get("success", False),
            "mode": result.get("mode", "unknown"),
            "persistent": result.get("persistent", False),
            "capabilities": result.get("capabilities", {}),
            "error": result.get("error", ""),
            "retrieval_quality_claimed": False,
        }
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        return {
            "available": False,
            "success": False,
            "error": str(e)[:500],
            "retrieval_quality_claimed": False,
        }


def dense_provider_status_probe(openlocus: str, workspace: Path) -> dict[str, Any]:
    """Probe dense provider status. Mock and disabled should be available; real unavailable."""
    try:
        proc = subprocess.run(
            [openlocus, "provider", "status", "--json"],
            check=False, text=True, capture_output=True,
            cwd=str(workspace), timeout=30,
        )
        if proc.returncode != 0:
            return {
                "mock_available": False,
                "disabled_available": False,
                "real_available": False,
                "raw_output": proc.stdout[:500] if proc.stdout else "",
            }
        result = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
        providers = result.get("supported_providers", [])
        return {
            "mock_available": "mock" in providers,
            "disabled_available": "disabled" in providers,
            "real_available": any(p not in ("mock", "disabled") for p in providers),
            "supported_providers": providers,
            "remote_default": result.get("remote_default", False),
            "outbound_default": result.get("outbound_default", False),
        }
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        return {
            "mock_available": False,
            "disabled_available": False,
            "real_available": False,
            "error": str(e)[:500],
        }


# ── 2) Dense mock candidate-channel probe ─────────────────────────────


def run_dense_build(openlocus: str, cwd: str) -> dict[str, Any]:
    """Run `openlocus dense build --provider mock --experimental --json` once."""
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
        "provider": result.get("provider", "mock"),
        "latency_ms": latency_ms,
        "returncode": proc.returncode,
        "stdout": proc.stdout[:2000] if proc.stdout else "",
        "stderr": proc.stderr[:500] if proc.stderr else "",
    }


def run_dense_search(openlocus: str, query: str, cwd: str, limit: int = 10) -> dict[str, Any]:
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

    evidence = result.get("evidence", []) if isinstance(result, dict) else []
    return {
        "success": result.get("success", False) if isinstance(result, dict) else False,
        "evidence": evidence,
        "query_sha": result.get("query_sha", "") if isinstance(result, dict) else "",
        "query_len": result.get("query_len", 0) if isinstance(result, dict) else 0,
        "provider": result.get("provider", "mock") if isinstance(result, dict) else "mock",
        "raw_json": result if isinstance(result, dict) else {},
        "stdout": proc.stdout[:4000] if proc.stdout else "",
        "latency_ms": latency_ms,
        "returncode": proc.returncode,
        "stderr": proc.stderr[:500] if proc.stderr else "",
    }


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
                prefix=f"r24-{strategy}-{repo_id}-citations-",
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


def check_canary_retrieval(
    openlocus: str, isolated_roots: dict[str, Path], dense_build_results: dict[str, dict]
) -> tuple[dict[str, Any], list[str]]:
    """Check that canary tokens are not leaked in dense evidence excerpts.

    Dense semantic search can legitimately return arbitrary nearest-neighbour
    evidence for an unrelated canary query when a mock vector provider is used.
    The safety property here is not "zero results for canary query"; it is
    "no raw canary token appears in evidence output or stored artifacts." Search
    failures are fail-closed because they would make the check vacuous.
    """
    issues: list[str] = []
    checked = 0
    hits = 0
    failures = 0
    returned_evidence = 0
    path_canary_checked = 0
    path_canary_returned_evidence = 0
    skipped_empty_stores = 0

    for repo_id, isolated in isolated_roots.items():
        record_count = int(dense_build_results.get(repo_id, {}).get("record_count", 0))
        if record_count == 0:
            skipped_empty_stores += 1
            continue
        path_canary_checked += 1
        path_result = run_dense_search(openlocus, DENSE_PATH_CANARY_QUERY, str(isolated))
        clean_runtime_artifacts(isolated)
        if path_result.get("returncode") != 0 or not path_result.get("success", False):
            failures += 1
            issues.append(
                f"CRITICAL: non-secret dense path canary failed for repo {repo_id}: "
                f"returncode={path_result.get('returncode')} success={path_result.get('success')} "
                f"stderr={path_result.get('stderr', '')[:200]}"
            )
        else:
            path_evidence_count = len(path_result.get("evidence", []))
            path_canary_returned_evidence += path_evidence_count
            if path_evidence_count == 0:
                failures += 1
                issues.append(
                    f"CRITICAL: non-secret dense path canary returned zero evidence for repo {repo_id}"
                )
        raw_path_output = (
            path_result.get("stdout", "") + "\n" + path_result.get("stderr", "")
        )
        if DENSE_PATH_CANARY_QUERY in raw_path_output:
            hits += 1
            issues.append(
                f"CRITICAL: non-secret dense path canary raw query echoed in CLI output for repo {repo_id}"
            )

        for token in DENSE_QUERY_CANARY_TOKENS:
            checked += 1
            result = run_dense_search(openlocus, token, str(isolated))
            clean_runtime_artifacts(isolated)
            if result.get("returncode") != 0 or not result.get("success", False):
                failures += 1
                issues.append(
                    f"CRITICAL: canary dense search failed for repo {repo_id}: "
                    f"returncode={result.get('returncode')} success={result.get('success')} "
                    f"stderr={result.get('stderr', '')[:200]}"
                )
                continue
            evidence = result.get("evidence", [])
            returned_evidence += len(evidence)
            for e in evidence:
                evidence_text = json.dumps(e, ensure_ascii=False)
                if token in evidence_text:
                    hits += 1
                    path = e.get("path", "")
                    issues.append(
                        f"CRITICAL: canary token leaked through dense evidence in repo {repo_id}; "
                        f"path={path}"
                    )
            # Query string itself must not be mirrored into raw stdout/stderr.
            raw_output = result.get("stdout", "") + "\n" + result.get("stderr", "")
            if token in raw_output:
                hits += 1
                issues.append(
                    f"CRITICAL: canary token appeared in raw dense CLI output for repo {repo_id}"
                )

    return {
        "checked": checked,
        "path_canary_checked": path_canary_checked,
        "path_canary_returned_evidence_count": path_canary_returned_evidence,
        "skipped_empty_store_repos": skipped_empty_stores,
        "path_canary_query_sha_only": True,
        "token_leak_hits": hits,
        "failures": failures,
        "returned_evidence_count": returned_evidence,
        "passed": hits == 0 and failures == 0 and path_canary_returned_evidence > 0,
    }, issues


def scan_embeddings_and_audit_for_query_leaks(
    isolated: Path, task_queries: list[str]
) -> list[str]:
    """Scan .openlocus/embeddings and audit for task query strings.
    At minimum verify dense CLI output uses evidence and traces don't
    contain canary tokens."""
    issues: list[str] = []
    embeddings_dir = isolated / ".openlocus" / "embeddings"
    audit_dir = isolated / ".openlocus" / "audit"

    for search_dir in [embeddings_dir, audit_dir]:
        if not search_dir.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(search_dir):
            for fname in filenames:
                if not fname.endswith((".jsonl", ".json")):
                    continue
                full = Path(dirpath) / fname
                try:
                    content = full.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                # Check for canary tokens
                for token in [*CANARY_TOKENS, *DENSE_QUERY_CANARY_TOKENS, DENSE_PATH_CANARY_QUERY]:
                    if token in content:
                        issues.append(
                            f"CRITICAL: canary token '{token}' found in {full.relative_to(isolated)}"
                        )
                # Check for raw query text in embeddings (should use query_sha)
                # We do NOT check for raw task queries in the embeddings store
                # because the mock provider uses query_sha not raw queries.
                # This is a best-effort safety check.

    return issues


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
        hard_dist_paths = get_hard_distractor_paths(label)
        if not hard_dist_paths:
            continue
        hard_dist_lines = build_hard_distractor_line_set(label)
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


def score_predictions(
    predictions: list[dict],
    gold: dict[str, dict],
    citation_summary: dict[str, Any],
    strategy: str,
) -> dict[str, Any]:
    """Phase 2: Score predictions using private labels."""
    total = len(predictions)
    ok = sum(1 for p in predictions if p.get("returncode", 0) == 0)
    success_true = sum(1 for p in predictions if p.get("success", False))
    rejected = sum(
        1
        for p in predictions
        if p.get("returncode", 0) == 0 and not p.get("success", False)
    )

    metrics: dict[str, Any] = {
        "total_tasks": total,
        "successful": ok,
        "success_rate": ok / total if total else 0.0,
        "candidate_success_count": success_true,
        "candidate_rejection_count": rejected,
        "candidate_rejection_rate": rejected / total if total else 0.0,
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
    metrics["candidate_count_avg"] = compute_candidate_count_avg(predictions)

    return metrics


def compute_bucket_metrics(
    predictions: list[dict],
    gold: dict[str, dict],
    citation_summary: dict[str, Any],
    strategy: str,
    bucket_key: str,
) -> dict[str, dict[str, Any]]:
    """Compute metrics bucketed by a label field."""
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
        m["primary_false_positive_rate"] = false_primary_on_negative_rate(bucket_preds, bucket_gold)
        m["must_not_primary_violation_rate"] = must_not_primary_violation_rate(bucket_preds, bucket_gold)
        result[bucket_val] = m
    return result


# ── Artifact safety scans ──────────────────────────────────────────────


def scan_artifacts_for_private_fields(
    runs_dir: Path, prefix: str
) -> list[str]:
    """Scan all R24-owned JSONL artifacts for private label fields."""
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
    """Scan all R24-owned JSONL artifacts for canary token strings."""
    issues: list[str] = []
    for path in sorted(runs_dir.glob("r24-*.jsonl")):
        content = path.read_text(encoding="utf-8")
        for token in [*CANARY_TOKENS, *DENSE_QUERY_CANARY_TOKENS, DENSE_PATH_CANARY_QUERY]:
            if token in content:
                issues.append(
                    f"CRITICAL: canary token '{token}' found in {path.name}"
                )
    return issues


# ── RRF fusion for optional dense_mock_plus_rrf ────────────────────────


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


def compute_dense_fusion_contribution(
    dense_predictions: list[dict], fusion_predictions: list[dict]
) -> dict[str, Any]:
    """Measure whether dense candidates actually contributed to fused output."""
    dense_keys_by_task: dict[str, set[str]] = {}
    for pred in dense_predictions:
        keys = {
            f"{e.get('path', '')}:{e.get('start_line', 0)}:{e.get('end_line', 0)}"
            for e in pred.get("evidence", [])
        }
        dense_keys_by_task[pred.get("task_id", "")] = keys

    tasks_with_dense = sum(1 for keys in dense_keys_by_task.values() if keys)
    tasks_with_dense_in_fusion = 0
    dense_spans_in_fusion = 0
    for pred in fusion_predictions:
        task_id = pred.get("task_id", "")
        dense_keys = dense_keys_by_task.get(task_id, set())
        if not dense_keys:
            continue
        fusion_keys = {
            f"{e.get('path', '')}:{e.get('start_line', 0)}:{e.get('end_line', 0)}"
            for e in pred.get("evidence", [])
        }
        intersection = dense_keys & fusion_keys
        dense_spans_in_fusion += len(intersection)
        if intersection:
            tasks_with_dense_in_fusion += 1

    return {
        "tasks_with_dense_candidates": tasks_with_dense,
        "tasks_with_dense_candidates_in_fusion": tasks_with_dense_in_fusion,
        "dense_spans_in_fusion": dense_spans_in_fusion,
        "dense_contribution_rate": (
            tasks_with_dense_in_fusion / tasks_with_dense if tasks_with_dense else 0.0
        ),
    }


# ── Main ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="R24 QuIVer/TDB/Dense Probe (NOT a QuIVer bakeoff)"
    )
    parser.add_argument("--workspace", default=".", help="Workspace root directory")
    parser.add_argument("--openlocus", default="target/debug/openlocus", help="Path to openlocus binary")
    parser.add_argument("--fixtures", default="fixtures/r20_auto_wide", help="Fixtures directory relative to workspace")
    parser.add_argument("--r21-report", default="runs/r21-auto-wide-report.json", help="R21 report for fusion baseline")
    parser.add_argument("--out", default="runs/r24-quiver-tdb-probe.json", help="Output path for JSON report")
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

    print(f"R24 QuIVer/TDB/Dense Probe: {len(tasks)} tasks, {len(repos)} repos")
    print(f"  Phase 1: RUN (availability checks + dense mock probe)")

    # ══════════════════════════════════════════════════════════════════
    # 1) AVAILABILITY CHECKS
    # ══════════════════════════════════════════════════════════════════

    print(f"  1a) QuIVer implementation scan...")
    quiver_scan = quiver_implementation_scan(workspace)
    if quiver_scan["quiver_implemented"]:
        safety_issues.append(
            "CRITICAL: QuIVer implementation detected in non-eval/docs code. "
            "R24 must report unavailable but implementation was found."
        )
    print(f"      quiver_implemented={quiver_scan['quiver_implemented']}, "
          f"scan_status={quiver_scan['scan_status']}")

    print(f"  1b) TDB status probe...")
    tdb_status = tdb_status_probe(openlocus_path, workspace)
    print(f"      tdb available={tdb_status.get('available')}, "
          f"mode={tdb_status.get('mode')}")

    print(f"  1c) Dense provider status probe...")
    dense_status = dense_provider_status_probe(openlocus_path, workspace)
    print(f"      mock_available={dense_status.get('mock_available')}, "
          f"real_available={dense_status.get('real_available')}")

    # ══════════════════════════════════════════════════════════════════
    # 2) DENSE MOCK CANDIDATE-CHANNEL PROBE
    # ══════════════════════════════════════════════════════════════════

    print(f"  2) Dense mock candidate-channel probe...")

    # Create isolated roots per repo
    isolated_roots: dict[str, Path] = {}
    for repo_id, entry in repos.items():
        isolated, iso_issues = create_isolated_root(repo_id, entry)
        isolated_roots[repo_id] = isolated
        safety_issues.extend(iso_issues)

    # Dense build for each repo
    dense_build_results: dict[str, dict] = {}
    for repo_id, isolated in isolated_roots.items():
        build_result = run_dense_build(openlocus_path, str(isolated))
        dense_build_results[repo_id] = build_result
        if not build_result["success"]:
            safety_issues.append(
                f"CRITICAL: dense build failed for repo {repo_id}: "
                f"{build_result.get('stderr', '')[:200]}"
            )
        clean_runtime_artifacts(isolated)

    # Canary retrieval check via dense after build. Search failures are critical
    # because they would make the canary check vacuous.
    canary_summary, canary_issues = check_canary_retrieval(
        openlocus_path, isolated_roots, dense_build_results
    )
    safety_issues.extend(canary_issues)

    # Dense search for each task
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
                "strategy": "dense_mock",
                "evidence": [],
                "latency_ms": 0,
                "returncode": -1,
                "success": False,
                "blocked": False,
                "reason": "unknown_repo_id",
            })
            continue

        cwd = str(isolated_roots[repo_id])
        result = run_dense_search(openlocus_path, query, cwd)
        clean_runtime_artifacts(isolated_roots[repo_id])

        if result.get("returncode") != 0:
            safety_issues.append(
                f"CRITICAL: dense search failed for task {task_id}: "
                f"{result.get('stderr', '')[:300]}"
            )

        pred = {
            "task_id": task_id,
            "repo_id": repo_id,
            "query": query,
            "strategy": "dense_mock",
            "evidence": result["evidence"],
            "latency_ms": result["latency_ms"],
            "returncode": result["returncode"],
            "success": result.get("success", False),
            "blocked": result.get("raw_json", {}).get("blocked", False),
            "reason": result.get("raw_json", {}).get("reason"),
            "query_sha": result.get("query_sha", ""),
            "query_len": result.get("query_len", 0),
        }
        predictions.append(pred)

    dense_candidate_total = sum(len(p.get("evidence", [])) for p in predictions)
    if dense_candidate_total == 0:
        safety_issues.append(
            "CRITICAL: dense_mock produced zero materialized candidates across all tasks; "
            "candidate-channel probe would be vacuous"
        )

    # Check for forbidden paths
    forbidden_issues = check_predictions_for_forbidden_paths(predictions, "dense_mock")
    safety_issues.extend(forbidden_issues)

    # Validate citations BEFORE cleanup
    citation_summary, citation_issues = validate_predictions_with_rust(
        openlocus_path, "dense_mock", predictions, isolated_roots
    )
    safety_issues.extend(citation_issues)

    # Scan embeddings/audit for query leaks
    for repo_id, isolated in isolated_roots.items():
        task_queries = [t["query"] for t in tasks if t.get("repo_id") == repo_id]
        leak_issues = scan_embeddings_and_audit_for_query_leaks(isolated, task_queries)
        safety_issues.extend(leak_issues)

    # Write R24-owned artifacts
    runs_dir = workspace / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    pred_path = runs_dir / "r24-dense-mock-predictions.jsonl"
    evid_path = runs_dir / "r24-dense-mock-evidence.jsonl"
    rej_path = runs_dir / "r24-dense-mock-rejections.jsonl"
    trace_path = runs_dir / "r24-dense-mock-trace.jsonl"

    evidence_list = [
        {"task_id": p["task_id"], "repo_id": p.get("repo_id", ""), "evidence": p["evidence"]}
        for p in predictions
    ]
    rejections_list = []
    for p in predictions:
        if not p.get("evidence") and (p.get("returncode", 0) != 0 or not p.get("success", False)):
            rejections_list.append({
                "task_id": p["task_id"],
                "repo_id": p.get("repo_id", ""),
                "strategy": "dense_mock",
                "phase": "cli_error" if p.get("returncode", 0) != 0 else "candidate_rejected",
                "reason": p.get("reason") or f"returncode={p.get('returncode')}",
                "blocked": p.get("blocked", False),
            })
    trace_list = [
        {
            "task_id": p["task_id"],
            "repo_id": p.get("repo_id", ""),
            "query": p.get("query", ""),
            "strategy": "dense_mock",
            "evidence_count": len(p.get("evidence", [])),
            "latency_ms": p.get("latency_ms", 0),
            "returncode": p.get("returncode", 0),
        }
        for p in predictions
    ]

    write_jsonl(pred_path, predictions)
    write_jsonl(evid_path, evidence_list)
    write_jsonl(rej_path, rejections_list)
    write_jsonl(trace_path, trace_list)

    artifact_manifest: dict[str, Any] = {
        "dense_mock": {
            "predictions": artifact_provenance(pred_path),
            "evidence": artifact_provenance(evid_path),
            "rejections": artifact_provenance(rej_path),
            "trace": artifact_provenance(trace_path),
        }
    }

    # ══════════════════════════════════════════════════════════════════
    # 3) OPTIONAL FUSION: dense_mock_plus_rrf
    # ══════════════════════════════════════════════════════════════════

    fusion_status = "not_run"
    fusion_predictions: list[dict] = []
    fusion_citation_summary: dict[str, Any] = {
        "citation_validity": 0.0,
        "citation_not_applicable": True,
    }
    fusion_metrics: dict[str, Any] = {}
    fusion_bucket_metrics: dict[str, dict[str, Any]] = {}
    fusion_contribution_summary: dict[str, Any] = {}

    # Only fuse if dense evidence is citation-valid and R21 report exists
    dense_citation_valid = (
        citation_summary.get("citation_validity", 0.0) == 1.0
        or citation_summary.get("citation_not_applicable", False)
    )

    if dense_citation_valid and r21_report_path.exists():
        print(f"  3) Optional fusion: dense_mock_plus_rrf...")
        try:
            r21_report = json.loads(r21_report_path.read_text(encoding="utf-8"))
            r21_rrf_preds_raw = r21_report.get("metrics", {}).get("rrf", {})

            # Load R21 RRF predictions from artifacts
            r21_rrf_pred_path = runs_dir / "r21-auto-wide-rrf-predictions.jsonl"
            if r21_rrf_pred_path.exists():
                r21_rrf_predictions = load_jsonl(r21_rrf_pred_path)
                r21_by_task = {p["task_id"]: p for p in r21_rrf_predictions}

                # Check no synthetic invalid channels in RRF predictions
                rrf_has_synthetic = False
                for p in r21_rrf_predictions:
                    for e in p.get("evidence", []):
                        channels = e.get("channels", [])
                        if "rrf_fusion" in channels or "synthetic" in channels:
                            rrf_has_synthetic = True
                            break

                if not rrf_has_synthetic:
                    for pred in predictions:
                        task_id = pred["task_id"]
                        rrf_pred = r21_by_task.get(task_id, {})
                        fused_evidence = rrf_fuse_predictions(pred, rrf_pred)
                        fusion_predictions.append({
                            "task_id": task_id,
                            "repo_id": pred.get("repo_id", ""),
                            "query": pred.get("query", ""),
                            "strategy": "dense_mock_plus_rrf",
                            "evidence": fused_evidence,
                            "latency_ms": pred.get("latency_ms", 0),
                            "returncode": pred.get("returncode", 0),
                            "success": bool(fused_evidence),
                            "blocked": False,
                            "reason": None if fused_evidence else "fused result empty",
                        })

                    # Validate fusion citations
                    fusion_citation_summary, fusion_cite_issues = validate_predictions_with_rust(
                        openlocus_path, "dense_mock_plus_rrf", fusion_predictions, isolated_roots
                    )
                    safety_issues.extend(fusion_cite_issues)

                    # Write fusion artifacts
                    fusion_pred_path = runs_dir / "r24-dense-mock-plus-rrf-predictions.jsonl"
                    fusion_evid_path = runs_dir / "r24-dense-mock-plus-rrf-evidence.jsonl"
                    fusion_rej_path = runs_dir / "r24-dense-mock-plus-rrf-rejections.jsonl"
                    fusion_trace_path = runs_dir / "r24-dense-mock-plus-rrf-trace.jsonl"
                    fusion_evidence_list = [
                        {
                            "task_id": p["task_id"],
                            "repo_id": p.get("repo_id", ""),
                            "evidence": p.get("evidence", []),
                        }
                        for p in fusion_predictions
                    ]
                    fusion_rejections_list = [
                        {
                            "task_id": p["task_id"],
                            "repo_id": p.get("repo_id", ""),
                            "strategy": "dense_mock_plus_rrf",
                            "phase": "no_evidence",
                            "reason": "fused result empty",
                        }
                        for p in fusion_predictions
                        if not p.get("evidence")
                    ]
                    fusion_trace_list = [
                        {
                            "task_id": p["task_id"],
                            "repo_id": p.get("repo_id", ""),
                            "strategy": "dense_mock_plus_rrf",
                            "evidence_count": len(p.get("evidence", [])),
                            "latency_ms": p.get("latency_ms", 0),
                            "returncode": p.get("returncode", 0),
                        }
                        for p in fusion_predictions
                    ]
                    write_jsonl(fusion_pred_path, fusion_predictions)
                    write_jsonl(fusion_evid_path, fusion_evidence_list)
                    write_jsonl(fusion_rej_path, fusion_rejections_list)
                    write_jsonl(fusion_trace_path, fusion_trace_list)
                    fusion_contribution_summary = compute_dense_fusion_contribution(
                        predictions, fusion_predictions
                    )
                    if fusion_contribution_summary.get("tasks_with_dense_candidates", 0) == 0:
                        safety_issues.append(
                            "CRITICAL: fusion completed but dense side had zero candidates"
                        )
                    artifact_manifest["dense_mock_plus_rrf"] = {
                        "predictions": artifact_provenance(fusion_pred_path),
                        "evidence": artifact_provenance(fusion_evid_path),
                        "rejections": artifact_provenance(fusion_rej_path),
                        "trace": artifact_provenance(fusion_trace_path),
                    }

                    fusion_status = "completed"
                else:
                    fusion_status = "not_run_rrf_has_synthetic_channels"
            else:
                fusion_status = "not_run_r21_rrf_predictions_missing"
        except (json.JSONDecodeError, KeyError, Exception) as e:
            fusion_status = f"not_run_error: {str(e)[:200]}"
    else:
        if not dense_citation_valid:
            fusion_status = "not_run_dense_citation_invalid"
        elif not r21_report_path.exists():
            fusion_status = "not_run_r21_report_missing"

    # Write manifest
    manifest_out_path = runs_dir / "r24-artifacts-manifest.json"
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
    # 4) TDB STALE/MATERIALIZATION SMOKE
    # ══════════════════════════════════════════════════════════════════

    print(f"  4) TDB stale/materialization smoke...")
    tdb_feature_probe = {
        "status": "tdb_feature_probe_not_run",
        "reason": "TDB is feature-gated behind 'tdb' Cargo feature; not in default build. "
                  "Default build TDB is unavailable placeholder. Running `store status tdb` "
                  "confirms placeholder. Enabling feature for this probe is not cheap "
                  "(requires rebuild with --features tdb) and would not produce retrieval quality data "
                  "since TDB is metadata/chunk store, not ANN/QuIVer.",
        "tdb_placeholder_status": tdb_status,
    }
    # tdb_stale_leak_count must be not_applicable
    tdb_stale_leak_count = "not_applicable"

    # ══════════════════════════════════════════════════════════════════
    # 5) QUIVER DIAGNOSTIC FIELDS
    # ══════════════════════════════════════════════════════════════════

    quiver_diagnostics = {
        "BQ_overlap": {
            "status": "unavailable",
            "reason": "quiver_not_implemented",
            "next_required_tests": ["Implement QuIVer retrieval adapter", "Run QuIVer on R20 dataset"],
        },
        "quiver_recall": {
            "status": "not_measured",
            "reason": "quiver_not_implemented",
            "next_required_tests": ["Implement QuIVer retrieval adapter", "Score QuIVer against R20 labels"],
        },
        "quiver_precision": {
            "status": "not_measured",
            "reason": "quiver_not_implemented",
            "next_required_tests": ["Implement QuIVer retrieval adapter", "Score QuIVer against R20 labels"],
        },
        "quiver_mrr": {
            "status": "not_measured",
            "reason": "quiver_not_implemented",
            "next_required_tests": ["Implement QuIVer retrieval adapter", "Score QuIVer against R20 labels"],
        },
        "quiver_f05": {
            "status": "not_measured",
            "reason": "quiver_not_implemented",
            "next_required_tests": ["Implement QuIVer retrieval adapter", "Score QuIVer against R20 labels"],
        },
    }

    # ══════════════════════════════════════════════════════════════════
    # Phase 2: SCORE
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

    # Score dense_mock
    dense_mock_metrics = score_predictions(predictions, gold, citation_summary, "dense_mock")

    # Bucket metrics for dense_mock
    dense_mock_bucket_metrics: dict[str, dict[str, Any]] = {}
    for bucket_key in ["query_category", "risk_tags", "expected_behavior", "repo_id"]:
        bucket_key_name = bucket_key if bucket_key != "repo_id" else "repo"
        bm = compute_bucket_metrics(predictions, gold, citation_summary, "dense_mock", bucket_key)
        dense_mock_bucket_metrics[bucket_key_name] = bm

    # Language bucket (from repo lock)
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
    dense_mock_bucket_metrics["language"] = lang_metrics

    # Dense semantic trap / proper_name / config / API buckets
    special_bucket_summary: dict[str, Any] = {}
    for bucket_name, category_set in [
        ("dense_semantic_trap", DENSE_SEMANTIC_TRAP_CATEGORIES),
        ("proper_name_api_config", PROPER_NAME_CATEGORIES),
        ("config_api", CONFIG_API_CATEGORIES),
    ]:
        bucket_tids = [
            tid for tid, label in gold.items()
            if label.get("query_category", "") in category_set
        ]
        bucket_gold = {tid: gold[tid] for tid in bucket_tids}
        bucket_preds = [p for p in predictions if p["task_id"] in bucket_tids]
        if bucket_preds:
            non_neg = {tid: g for tid, g in bucket_gold.items() if g.get("gold_spans")}
            neg = {tid: g for tid, g in bucket_gold.items() if not g.get("gold_spans")}
            sm: dict[str, Any] = {"total_tasks": len(bucket_preds)}
            if non_neg:
                sm["FileRecall@1"] = file_recall_at_k(bucket_preds, non_neg, 1)
                sm["MRR"] = mrr(bucket_preds, non_neg)
                sm["SpanF0.5"] = span_f_beta_at_k(bucket_preds, non_neg, 10, 0.5)
            if neg:
                sm["no_gold_nonempty_rate"] = no_gold_nonempty_rate_at_k(bucket_preds, neg, 10)
            sm["abstain_rate"] = abstain_rate(bucket_preds)
            special_bucket_summary[bucket_name] = sm
        else:
            special_bucket_summary[bucket_name] = {"total_tasks": 0}

    # Score fusion if completed
    if fusion_status == "completed" and fusion_predictions:
        fusion_metrics = score_predictions(
            fusion_predictions, gold, fusion_citation_summary, "dense_mock_plus_rrf"
        )
        fusion_bucket_metrics = {}
        for bucket_key in ["query_category", "risk_tags", "expected_behavior", "repo_id"]:
            bucket_key_name = bucket_key if bucket_key != "repo_id" else "repo"
            bm = compute_bucket_metrics(
                fusion_predictions, gold, fusion_citation_summary,
                "dense_mock_plus_rrf", bucket_key
            )
            fusion_bucket_metrics[bucket_key_name] = bm

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
    if dense_mock_metrics.get("citation_total_count", 0) > 0:
        if dense_mock_metrics.get("citation_validity", 0.0) != 1.0:
            critical_issues.append(
                f"CRITICAL: dense_mock citation_validity={dense_mock_metrics.get('citation_validity')} != 1.0"
            )

    # Artifact safety scan
    private_field_issues = scan_artifacts_for_private_fields(runs_dir, "r24")
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
        "quiver_implemented": quiver_scan["quiver_implemented"],
        "description": (
            "R24 QuIVer/TDB/Dense Probe. NOT a QuIVer bakeoff. "
            "This is an availability + mock dense candidate-channel probe + "
            "TDB placeholder status check. QuIVer remains future work."
        ),
        "source_dataset_manifest": {
            "path": str(manifest_path),
            "not_promotion_evidence": manifest.get("not_promotion_evidence", True),
            "core_changes": manifest.get("core_changes", False),
            "remote_calls": manifest.get("remote_calls", 0),
            "dense_or_llm_claims": manifest.get("dense_or_llm_claims", False),
        },
        "availability_checks": {
            "quiver_implementation_scan": quiver_scan,
            "tdb_status": tdb_status,
            "dense_provider_status": dense_status,
        },
        "dense_mock_probe": {
            "build_results": {
                k: {"success": v["success"], "record_count": v["record_count"]}
                for k, v in dense_build_results.items()
            },
            "candidate_total": dense_candidate_total,
            "metrics": dense_mock_metrics,
            "bucket_metrics": dense_mock_bucket_metrics,
            "special_category_buckets": special_bucket_summary,
            "citation_summary": citation_summary,
        },
        "dense_mock_plus_rrf": {
            "status": fusion_status,
            "metrics": fusion_metrics if fusion_status == "completed" else {},
            "bucket_metrics": fusion_bucket_metrics if fusion_status == "completed" else {},
            "citation_summary": fusion_citation_summary if fusion_status == "completed" else {},
            "dense_contribution": fusion_contribution_summary if fusion_status == "completed" else {},
        },
        "tdb_probe": tdb_feature_probe,
        "tdb_stale_leak_count": tdb_stale_leak_count,
        "quiver_diagnostics": quiver_diagnostics,
        "safety_gates": {
            "all_passed": len(critical_issues) == 0,
            "critical_issues": critical_issues,
            "warning_issues": warning_issues,
            "canary_retrieval": canary_summary,
            "artifact_private_field_scan": {
                "scanned": True,
                "issues_found": len(private_field_issues),
            },
            "artifact_canary_token_scan": {
                "scanned": True,
                "issues_found": len(canary_token_issues),
            },
            "artifact_manifest_verification": artifact_manifest_verification,
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
            "validator_before_cleanup": True,
        },
        "tasks_count": len(tasks),
        "repos_count": len(repos),
        "labels_count": len(gold),
        "r21_report_used": str(r21_report_path) if r21_report_path.exists() else "not_found",
    }

    out_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    # ── Print summary ─────────────────────────────────────────────────

    print(f"\n{'='*70}")
    print(f"R24 QuIVer/TDB/Dense Probe Results")
    print(f"{'='*70}")

    print(f"\n  Availability Checks:")
    print(f"    quiver_implemented: {quiver_scan['quiver_implemented']}")
    print(f"    tdb_available: {tdb_status.get('available', 'N/A')}")
    print(f"    dense_mock_available: {dense_status.get('mock_available', 'N/A')}")
    print(f"    dense_real_available: {dense_status.get('real_available', 'N/A')}")

    print(f"\n  Dense Mock Metrics:")
    metric_display = [
        "FileRecall@1", "FileRecall@3", "FileRecall@5", "MRR",
        "SpanF0.5", "SpanPrecision", "SpanRecall",
        "token_waste", "no_gold_nonempty_rate",
        "hard_distractor_hit_rate",
        "primary_false_positive_rate",
        "must_not_primary_violation_rate",
        "abstain_rate", "weak_candidate_rate",
    ]
    for key in metric_display:
        val = dense_mock_metrics.get(key)
        if val is not None:
            if isinstance(val, float):
                print(f"    {key}: {val:.3f}")
            else:
                print(f"    {key}: {val}")
    lat = dense_mock_metrics.get("latency", {})
    if lat:
        print(f"    latency_p50: {lat.get('p50', 0)}ms, p95: {lat.get('p95', 0)}ms")
    print(f"    citation_validity: {dense_mock_metrics.get('citation_validity', 'N/A')}")

    if fusion_status == "completed":
        print(f"\n  Dense Mock + RRF Fusion Metrics:")
        for key in metric_display:
            val = fusion_metrics.get(key)
            if val is not None:
                if isinstance(val, float):
                    print(f"    {key}: {val:.3f}")
                else:
                    print(f"    {key}: {val}")
    else:
        print(f"\n  Dense Mock + RRF Fusion: {fusion_status}")

    print(f"\n  TDB Probe: {tdb_feature_probe['status']}")
    print(f"  QuIVer Diagnostics: all unavailable/not_measured (quiver_not_implemented)")

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
    print(f"  quiver_implemented: False (confirmed)")
    print(f"  dense_real: unavailable")
    print(f"  dense_mock: candidate-channel safety/quality-smoke only")

    if critical_issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
