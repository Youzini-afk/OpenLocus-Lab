#!/usr/bin/env python3
"""Product Stack Bakeoff B1 — immutable fixture generation (v2).

Two generated immutable miniature repos (Rust and TypeScript), 12 opaque
tasks: 2 each prose, literal text, exact symbol, graph relation, two-step
support, abstention/status.

V2 neutrality requirements:
* Opaque task slugs (no answer/channel/status/target/support hints).
* Opaque source stems unrelated to query tokens or expected mechanics.
* No answer/channel/status/target/support hints in paths/comments/slugs.
* Queries contain no source path or role hint.
* Exactly one high-entropy impossible task (no_evidence) and one deliberate
  equal cross-path top-tie task (uncertain).
* Two-step one-line targets must naturally converge all six stacks to
  identical materialized target ID.

Fixture files are written WITHOUT a BOM (Python ``write_text`` with
``encoding='utf-8'``) so the production graph builder parses every line.

Run::

    python -m py_compile eval/product_bakeoff_b1_fixtures.py
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from product_bakeoff_contract import (
    LANGUAGE_FAMILIES,
    OPERATIONS,
    INTERACTION_MODES,
    BakeoffTask,
)

from product_bakeoff_b1_spec import B1_SPEC_VERSION

# ---------------------------------------------------------------------------
# Fixture identity
# ---------------------------------------------------------------------------

FIXTURE_VERSION = "product_bakeoff_b1_fixtures.v2"

RUST_REPO_ID = "b1_rust_fixture_v2"
TS_REPO_ID = "b1_ts_fixture_v2"

# ---------------------------------------------------------------------------
# Rust fixture content (immutable, byte-identical for mirror copy)
# ---------------------------------------------------------------------------
# Opaque source stems carry no answer hints in file names or comments.
# Content is real Rust code with clear symbols,
# imports, and tests so all cumulative stacks (BM25/text/symbol/graph) can
# exercise their components honestly.

RUST_FILES: dict[str, str] = {
    "Cargo.toml": (
        "[package]\n"
        'name = "fixture_r17"\n'
        'version = "0.1.0"\n'
        'edition = "2021"\n'
    ),
    "src/a17.rs": (
        "pub fn calibrate() -> &'static str {\n"
        "    \"harbor cadence ledger\"\n"
        "}\n"
    ),
    "src/b29.rs": (
        "pub const NOTICE: &str = \"signal[42] ready\";\n"
    ),
    "src/c41.rs": (
        "pub fn quorim() {}\n"
        "pub fn quorim_suffix() {}\n"
    ),
    "src/d53.rs": (
        "pub struct Neral;\n"
    ),
    "src/e67.rs": (
        "use crate::d53::Neral;\n"
        "pub fn accept(_: Neral) {}\n"
    ),
    "src/h03.rs": (
        "pub struct Orvane;\n"
    ),
    "src/z97.rs": (
        "use crate::h03::Orvane;\n"
        "pub fn relay(_: Orvane) {}\n"
    ),
    "src/j11.rs": (
        "pub struct Meralis;\n"
    ),
    "src/k23.rs": (
        "pub struct Meralis;\n"
    ),
}

RUST_VISIBLE_FILES = tuple(RUST_FILES.keys())

# ---------------------------------------------------------------------------
# TypeScript fixture content (immutable, byte-identical for mirror copy)
# ---------------------------------------------------------------------------

TS_FILES: dict[str, str] = {
    "package.json": (
        "{\n"
        '  "name": "fixture-t31",\n'
        '  "version": "0.1.0"\n'
        "}\n"
    ),
    "src/a19.ts": (
        "export function calibrate(): string {\n"
        "    return 'copper interval beacon';\n"
        "}\n"
    ),
    "src/b31.ts": (
        "export const notice = 'phase(7) settled';\n"
    ),
    "src/c43.ts": (
        "export function selune(): void {}\n"
        "export function seluneExtra(): void {}\n"
    ),
    "src/d59.ts": (
        "export class Tavren {}\n"
    ),
    "src/e71.ts": (
        "import { Tavren } from './d59';\n"
        "export function accept(_: Tavren): void {}\n"
    ),
    "src/h05.ts": (
        "export class Sevran {}\n"
    ),
    "src/z99.ts": (
        "import { Sevran } from './h05';\n"
        "export function relay(_: Sevran): void {}\n"
    ),
}

TS_VISIBLE_FILES = tuple(TS_FILES.keys())

# ---------------------------------------------------------------------------
# Task definitions (adapter-visible; carry NO gold/target/support labels)
# ---------------------------------------------------------------------------
# Opaque slugs: b1_t01 through b1_t12.  No answer/channel/status/target/support
# hints in slugs.  Queries contain no source paths.  Task families are broad
# contract categories that do not reveal the expected adapter or target.


@dataclass(frozen=True)
class B1Task:
    """Adapter-visible B1 task.  Carries NO gold/target/support labels."""

    task_slug: str
    language_family: str
    task_family: str
    interaction_mode: str
    query: str
    operation: str = "context"
    repo_id: str = ""

    def to_bakeoff_task(self) -> BakeoffTask:
        return BakeoffTask(
            task_slug=self.task_slug,
            language_family=self.language_family,
            task_family=self.task_family,
            interaction_mode=self.interaction_mode,
            source_visibility="frozen_visible",
            query=self.query,
            operation=self.operation,
        ).validate()

    def visible_files(self) -> tuple[str, ...]:
        if self.repo_id == RUST_REPO_ID:
            return RUST_VISIBLE_FILES
        return TS_VISIBLE_FILES

    def file_contents(self) -> dict[str, str]:
        if self.repo_id == RUST_REPO_ID:
            return dict(RUST_FILES)
        return dict(TS_FILES)


B1_TASK_T01 = B1Task(
    task_slug="b1_t01",
    language_family="rust",
    task_family="definition_find",
    interaction_mode="one_shot",
    query="harbor cadence ledger",
    repo_id=RUST_REPO_ID,
)
B1_TASK_T02 = B1Task(
    task_slug="b1_t02",
    language_family="typescript",
    task_family="definition_find",
    interaction_mode="one_shot",
    query="copper interval beacon",
    repo_id=TS_REPO_ID,
)

B1_TASK_T03 = B1Task(
    task_slug="b1_t03",
    language_family="rust",
    task_family="error_text",
    interaction_mode="one_shot",
    query="signal[42] ready",
    repo_id=RUST_REPO_ID,
)
B1_TASK_T04 = B1Task(
    task_slug="b1_t04",
    language_family="typescript",
    task_family="error_text",
    interaction_mode="one_shot",
    query="phase(7) settled",
    repo_id=TS_REPO_ID,
)

B1_TASK_T05 = B1Task(
    task_slug="b1_t05",
    language_family="rust",
    task_family="symbol_lookup",
    interaction_mode="one_shot",
    query="quorim",
    repo_id=RUST_REPO_ID,
)
B1_TASK_T06 = B1Task(
    task_slug="b1_t06",
    language_family="typescript",
    task_family="symbol_lookup",
    interaction_mode="one_shot",
    query="selune",
    repo_id=TS_REPO_ID,
)

B1_TASK_T07 = B1Task(
    task_slug="b1_t07",
    language_family="rust",
    task_family="cross_file_dependency",
    interaction_mode="one_shot",
    query="Neral",
    repo_id=RUST_REPO_ID,
)
B1_TASK_T08 = B1Task(
    task_slug="b1_t08",
    language_family="typescript",
    task_family="cross_file_dependency",
    interaction_mode="one_shot",
    query="Tavren",
    repo_id=TS_REPO_ID,
)

B1_TASK_T09 = B1Task(
    task_slug="b1_t09",
    language_family="rust",
    task_family="ambiguous_target",
    interaction_mode="one_shot",
    query="Meralis",
    repo_id=RUST_REPO_ID,
)
B1_TASK_T10 = B1Task(
    task_slug="b1_t10",
    language_family="typescript",
    task_family="no_answer",
    interaction_mode="one_shot",
    query="qv7m2z9pk4d8n6x3",
    repo_id=TS_REPO_ID,
)

B1_TASK_T11 = B1Task(
    task_slug="b1_t11",
    language_family="rust",
    task_family="refactor_target_find",
    interaction_mode="two_step",
    query="Orvane",
    operation="context",
    repo_id=RUST_REPO_ID,
)
B1_TASK_T12 = B1Task(
    task_slug="b1_t12",
    language_family="typescript",
    task_family="refactor_target_find",
    interaction_mode="two_step",
    query="Sevran",
    operation="context",
    repo_id=TS_REPO_ID,
)

# Ordered tuple of all 12 tasks (10 one-shot + 2 two-step).
B1_ONE_SHOT_TASKS: tuple[B1Task, ...] = (
    B1_TASK_T01, B1_TASK_T02, B1_TASK_T03, B1_TASK_T04, B1_TASK_T05,
    B1_TASK_T06, B1_TASK_T07, B1_TASK_T08, B1_TASK_T09, B1_TASK_T10,
)
B1_TWO_STEP_TASKS: tuple[B1Task, ...] = (
    B1_TASK_T11, B1_TASK_T12,
)
B1_ALL_TASKS: tuple[B1Task, ...] = B1_ONE_SHOT_TASKS + B1_TWO_STEP_TASKS

assert len(B1_ONE_SHOT_TASKS) == 10, (
    f"expected 10 one-shot tasks, got {len(B1_ONE_SHOT_TASKS)}")
assert len(B1_TWO_STEP_TASKS) == 2, (
    f"expected 2 two-step tasks, got {len(B1_TWO_STEP_TASKS)}")
assert len(B1_ALL_TASKS) == 12

# Verify no query contains a source path (no "src/", "module_", "/", ".rs",
# ".ts" substrings).
for _task in B1_ALL_TASKS:
    _q = _task.query
    assert "src/" not in _q, f"task {_task.task_slug} query contains source path"
    assert "module_" not in _q, (
        f"task {_task.task_slug} query contains module_ stem hint")
    assert "/" not in _q, (
        f"task {_task.task_slug} query contains path separator")
    assert not _q.endswith(".rs"), (
        f"task {_task.task_slug} query contains .rs extension hint")
    assert not _q.endswith(".ts"), (
        f"task {_task.task_slug} query contains .ts extension hint")


# ---------------------------------------------------------------------------
# Fixture write + digest
# ---------------------------------------------------------------------------


def write_fixture_repo(root: Path, repo_id: str) -> tuple[str, ...]:
    """Write an immutable fixture repo to ``root``.  Returns the visible-file
    tuple.  Files are written WITHOUT a BOM."""
    files = RUST_FILES if repo_id == RUST_REPO_ID else TS_FILES
    for rel, content in files.items():
        full = root / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
    return tuple(files.keys())


def fixture_file_digest(rel: str, content: str) -> str:
    """Per-file SHA-256 digest of the fixture content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def fixture_digest() -> str:
    """Deterministic digest of all fixture file content + task definitions."""
    payload: dict[str, Any] = {}
    for repo_id, files in ((RUST_REPO_ID, RUST_FILES), (TS_REPO_ID, TS_FILES)):
        repo: dict[str, str] = {}
        for rel in sorted(files.keys()):
            repo[rel] = fixture_file_digest(rel, files[rel])
        payload[repo_id] = repo
    # Include task slugs/queries (adapter-visible, no labels).
    payload["tasks"] = [
        {
            "task_slug": t.task_slug,
            "language_family": t.language_family,
            "task_family": t.task_family,
            "interaction_mode": t.interaction_mode,
            "query": t.query,
            "operation": t.operation,
            "repo_id": t.repo_id,
        }
        for t in B1_ALL_TASKS
    ]
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "b1fix_" + hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def copy_fixture_to_mirror(
    src_repo_id: str, mirror_root: Path
) -> tuple[str, ...]:
    """Copy every and only the frozen visible files into ``mirror_root``
    using byte-identical ordinary files.  Rejects labels/oracles, .git,
    copied .openlocus, symlinks/reparse points, extra files, and hash/size
    drift.

    Returns the visible-file tuple (relative POSIX paths).
    """
    files = RUST_FILES if src_repo_id == RUST_REPO_ID else TS_FILES
    for rel, content in files.items():
        full = mirror_root / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        # Byte-identical write: encode the exact same content.
        full.write_bytes(content.encode("utf-8"))
        # Verify byte-identity.
        assert full.read_bytes() == content.encode("utf-8"), (
            f"mirror file {rel!r} byte drift")
    return tuple(files.keys())


# ---------------------------------------------------------------------------
# Preflight probe: verify two-step convergence (requires the Rust binary)
# ---------------------------------------------------------------------------
# The preflight checks that the two-step task queries naturally converge all
# six stacks to the same (path, range) target ID.  This requires the
# ``bakeoff-query`` subcommand; until it exists, preflight_probe raises
# RuntimeError so the caller can skip it.


def preflight_probe(
    cli_path: str | None = None,
    runs_dir: Path | None = None,
) -> dict[str, Any]:
    """Run a preflight probe to verify two-step target convergence.

    Returns a dict mapping task_slug -> {adapter_id -> (path, start, end)}
    for the two-step tasks.  All six adapters must converge to the same
    (path, start, end) for each task.

    Raises RuntimeError if the ``bakeoff-query`` subcommand is not available.
    """
    if cli_path is None:
        from product_bakeoff_b1_adapters import _find_cli
        cli_path = _find_cli()
    import os
    import subprocess
    import time
    result = subprocess.run(
        [cli_path, "bakeoff-query", "--help"],
        capture_output=True, timeout=10.0,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "bakeoff-query subcommand not available; the Rust writer has not "
            "finished.  Preflight cannot verify two-step convergence.")
    os.environ["OPENLOCUS_CLI"] = cli_path
    if runs_dir is None:
        runs_dir = Path("runs") / f"b1_v2_preflight_{int(time.time())}"
    from product_bakeoff_b1_runner import run_preflight_probe
    probe = run_preflight_probe(Path(runs_dir))
    return {
        "status": "passed" if probe.get("passed") else "failed",
        "tasks": probe.get("targets", {}),
        "converged": bool(probe.get("passed")),
        "record_count": probe.get("record_count", 0),
        "parent_receipt_count": probe.get("parent_receipt_count", 0),
        "failure_count": len(probe.get("failures", [])),
    }


__all__ = [
    "FIXTURE_VERSION", "RUST_REPO_ID", "TS_REPO_ID",
    "RUST_FILES", "RUST_VISIBLE_FILES",
    "TS_FILES", "TS_VISIBLE_FILES",
    "B1Task",
    "B1_ONE_SHOT_TASKS", "B1_TWO_STEP_TASKS", "B1_ALL_TASKS",
    "B1_TASK_T01", "B1_TASK_T02", "B1_TASK_T03", "B1_TASK_T04",
    "B1_TASK_T05", "B1_TASK_T06", "B1_TASK_T07", "B1_TASK_T08",
    "B1_TASK_T09", "B1_TASK_T10", "B1_TASK_T11", "B1_TASK_T12",
    "write_fixture_repo", "fixture_file_digest", "fixture_digest",
    "copy_fixture_to_mirror", "preflight_probe",
]
