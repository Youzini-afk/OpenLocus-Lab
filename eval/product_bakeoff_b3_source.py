#!/usr/bin/env python3
"""Closed source-bundle binding for the executable B3 control plane.

The preregistration and engine-integration artifacts intentionally bind smaller
historical source sets.  This module binds the complete source surface that is
allowed to qualify, author, freeze, launch, observe, score, and publish B3.
Private inputs are never part of this digest.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]

B3_CONTROL_SOURCE_VERSION = "product_bakeoff_b3_control_source.v2"
B3_CONTROL_SOURCE_PATHS = (
    ".github/workflows/product-bakeoff-b3-control.yml",
    "Cargo.lock",
    "crates/openlocus-cli/src/bakeoff_query.rs",
    "crates/openlocus-cli/src/lib.rs",
    "crates/openlocus-ast/src/symbol.rs",
    "crates/openlocus-context/src/plan.rs",
    "crates/openlocus-graph/src/graph.rs",
    "crates/openlocus-index/src/persistent.rs",
    "crates/openlocus-retrieval/src/bm25_search.rs",
    "crates/openlocus-retrieval/src/regex_search.rs",
    "crates/openlocus-retrieval/src/rrf.rs",
    "crates/openlocus-retrieval/src/symbol_search.rs",
    "eval/ci_clone_and_lock_repo.py",
    "eval/product_bakeoff_contract.py",
    "eval/product_bakeoff_b1_adapters.py",
    "eval/product_bakeoff_b1_fixtures.py",
    "eval/product_bakeoff_b1_runner.py",
    "eval/product_bakeoff_b1_spec.py",
    "eval/product_bakeoff_b2_adapters.py",
    "eval/product_bakeoff_b2_author.py",
    "eval/product_bakeoff_b2_corpus.py",
    "eval/product_bakeoff_b2_oracle.py",
    "eval/product_bakeoff_b2_protocol.py",
    "eval/product_bakeoff_b2_runner.py",
    "eval/product_bakeoff_b2_scorer.py",
    "eval/product_bakeoff_b21_corpus.py",
    "eval/product_bakeoff_b21_protocol.py",
    "eval/product_bakeoff_b21_runner.py",
    "eval/product_bakeoff_b21_scorer.py",
    "eval/product_bakeoff_b23_protocol.py",
    "eval/product_bakeoff_b23_runner_qualification.py",
    "eval/product_bakeoff_b24_corpus.py",
    "eval/product_bakeoff_b24_protocol.py",
    "eval/product_bakeoff_b24_runner.py",
    "eval/product_bakeoff_b25_protocol.py",
    "eval/product_bakeoff_b25_query_gate.py",
    "eval/product_bakeoff_b25_runtime_qualification.py",
    "eval/product_bakeoff_b3_repeatability.py",
    "eval/product_bakeoff_b3_protocol.py",
    "eval/product_bakeoff_b3_runner.py",
    "eval/product_bakeoff_b3_scorer.py",
    "eval/product_bakeoff_b3_source.py",
    "eval/product_bakeoff_b3_runtime_qualification.py",
    "eval/product_bakeoff_b3_corpus.py",
    "eval/product_bakeoff_b3_readiness.py",
    "eval/product_bakeoff_b3_publication.py",
    "eval/product_bakeoff_b3_execution.py",
    "eval/product_bakeoff_b3_cli.py",
    "eval/product_bakeoff_b3_control_integration.py",
    "eval/product_bakeoff_conformance.py",
    "eval/product_bakeoff_oracle.py",
    "eval/product_bakeoff_terminal_archive.py",
    "scripts/product_bakeoff_b3_linux_longrun.sh",
    "scripts/public_artifact_privacy_audit.py",
    "scripts/validate_docs_i18n.py",
)


class B3SourceError(ValueError):
    """Fail-closed B3 source-bundle error."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def source_rows(repo_root: Path | None = None) -> tuple[dict[str, Any], ...]:
    root = (repo_root or REPO).resolve(strict=True)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for relative in B3_CONTROL_SOURCE_PATHS:
        if relative in seen:
            raise B3SourceError(f"duplicate B3 control source entry: {relative}")
        seen.add(relative)
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise B3SourceError(f"missing or unsafe B3 control source: {relative}")
        resolved = path.resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise B3SourceError("B3 control source escapes checkout") from exc
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        rows.append(
            {
                "source": relative,
                "normalized_bytes": len(raw),
                "normalized_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return tuple(rows)


def control_source_bundle_digest(repo_root: Path | None = None) -> str:
    payload = {
        "version": B3_CONTROL_SOURCE_VERSION,
        "sources": source_rows(repo_root),
    }
    return "b3controlsrc_" + hashlib.sha256(_canonical(payload)).hexdigest()


def source_rows_at_checkpoint(
    checkpoint: str, repo_root: Path | None = None
) -> tuple[dict[str, Any], ...]:
    if not re.fullmatch(r"[0-9a-f]{40}", checkpoint):
        raise B3SourceError("B3 source checkpoint must be a full commit SHA")
    root = (repo_root or REPO).resolve(strict=True)
    rows: list[dict[str, Any]] = []
    for relative in B3_CONTROL_SOURCE_PATHS:
        tree = subprocess.run(
            ["git", "ls-tree", checkpoint, "--", relative],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        fields = tree.stdout.strip().split()
        if tree.returncode != 0 or len(fields) < 4 or fields[1] != "blob":
            raise B3SourceError(f"B3 source absent from checkpoint: {relative}")
        if fields[0] not in {"100644", "100755"}:
            raise B3SourceError(f"unsafe B3 source mode at checkpoint: {relative}")
        blob = subprocess.run(
            ["git", "show", f"{checkpoint}:{relative}"],
            cwd=root,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if blob.returncode != 0:
            raise B3SourceError(f"B3 source blob unreadable at checkpoint: {relative}")
        raw = blob.stdout.replace(b"\r\n", b"\n")
        rows.append(
            {
                "source": relative,
                "normalized_bytes": len(raw),
                "normalized_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return tuple(rows)


def validate_source_checkpoint(
    checkpoint: str, repo_root: Path | None = None
) -> None:
    if source_rows(repo_root) != source_rows_at_checkpoint(checkpoint, repo_root):
        raise B3SourceError("current B3 control source differs from qualified checkpoint")


def run_self_test() -> dict[str, Any]:
    rows = source_rows()
    checks = {
        "paths_unique": len(rows) == len(set(B3_CONTROL_SOURCE_PATHS)),
        "all_nonempty": all(row["normalized_bytes"] > 0 for row in rows),
        "digest_prefixed": control_source_bundle_digest().startswith("b3controlsrc_"),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    rows = source_rows()
    checks = {
        "duplicate_policy_representable": len(B3_CONTROL_SOURCE_PATHS)
        == len(set(B3_CONTROL_SOURCE_PATHS)),
        "normalized_hashes_closed": all(
            set(row) == {"source", "normalized_bytes", "normalized_sha256"}
            for row in rows
        ),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B3_CONTROL_SOURCE_PATHS",
    "B3_CONTROL_SOURCE_VERSION",
    "B3SourceError",
    "control_source_bundle_digest",
    "source_rows",
    "source_rows_at_checkpoint",
    "validate_source_checkpoint",
]
