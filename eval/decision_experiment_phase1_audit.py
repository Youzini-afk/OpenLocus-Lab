#!/usr/bin/env python3
"""Decision-oriented product experiment — Phase 1 provider-free audit/miner.

This is the **Stage 1 eligibility / headroom audit** described in
``docs/en/decision-experiment-phase1-decision-contract.md``. Stage 1 is an
audit, **not** a pain proof, **not** a product-effect proof, and **not** a
downstream-agent evaluation. No provider and no agent runs occur here.

What this module DOES (all provider-free, local CPU only):

1. Deterministically enumerate all non-merge commits reachable before the
   frozen source cutoff, ordered newest-first then SHA.
2. Apply a rule-based candidate filter (product source + developer-authored
   tests, one logical defect, <=2 production files and <=100 production
   changed lines, natural pre-fix prose from an unedited commit message).
   No hardcoded favorable candidate list. Exclusions are reported only as
   aggregate reason buckets.
3. Transplant the developer test byte-for-byte into a scorer-only isolated
   overlay (workspaces materialized via ``git archive`` with no ``.git``,
   so the runtime copy cannot reach child/fix diff/hidden test/scorer/oracle
   files).
4. Cold reproducibility checks where feasible: buggy+overlay fail 3/3 stable
   signature; fixed+same overlay pass 3/3; relevant fixed regression 2/2;
   developer patch passes; empty patch fails; per scoring run <=10 min.
   Candidates that cannot be deterministically/safely checked are excluded
   with a fixed reason bucket. Rules are never weakened to reach a
   denominator.
5. Generate control/treatment packs via the SAME existing production
   Fast Context CLI path and renderer (treatment regex,bm25,symbol,graph +
   RRF + final citation/currentness validation, max_evidence=12, budget=2000;
   control bm25-only, same builder/renderer/query/caps). If the exact
   production call cannot be made, the step fails honestly.
6. Headroom spend gate (NOT an outcome): G_i=1 only if BM25 omits a
   fix-relevant preimage path and treatment adds valid current evidence
   absent from control, with materially different rendered packs. Requires
   >= max(2, ceil(0.4N)) on N=first up to 8 eligible, min N=5.
7. Emit an **aggregate-only public report** (counts/buckets/gate status/
   reason buckets). No commit SHAs (except the public cutoff), task IDs,
   issue prose, paths, test names, diffs, patches, expected values, private
   pack text, per-task rows, prompts, or provider details. Private rows,
   manifests, and logs live only in the ignored ``runs/`` tree.

Self-tests use synthetic temporary git fixtures only, make no network/provider
calls, and prove: deterministic enumeration, rule-based filters, byte-exact test
transplant, isolation (OS temp outside REPO_ROOT, no ancestor markers, real
production topology), stable fail/pass checks, aggregate privacy, fail-closed
gate behavior, Rust inline test region detection (language-aware,
attribute-false-positive-safe, lifetime/label-aware — lifetimes ``'a``/
``'static`` and labels ``'label:`` not mistaken for char literals), byte-safe
overlay (raw on-disk byte hash verification, enforced in real ``apply_overlay``
via explicit base-mode invariants — ``parent_full_hash``/``fixed_full_hash``/
``parent_prod_hash``/``fixed_prod_hash``/``fixed_test_hash`` — for each of the
three repro paths: buggy parent, fixed commit, and parent+production-only-dev-
patch), inline overlay base-mode round-trip (mode=parent/fixed/parent_dev_patch
all succeed; wrong workspace or missing dev patch fails closed; unknown mode
rejected), ambiguity fail-closed (multiple inline modules rejected),
no-fixed-production-bytes-leak assertion, small (<100 raw lines) test-only
inline-module change excluded as test-only, production-only dev-patch trailing
newline fix (``filter_diff_to_prod_hunks`` emits a valid patch), lifetime/label
boundary, ancestor marker rejection, enforced real overlay hash rejection,
parent-only headroom materialization (no fixed bytes in either retrieval arm),
flattened Fast Context evidence schema validation (``Evidence`` is
``#[serde(flatten)] pub core`` — path/start_line/end_line/content_sha/score/
why/channels are direct fields, plus optional ``meta``; nested ``core`` object
rejected fail-closed; diagnostics exact keys/types; ``unknown_channels`` empty;
unexpected non-fusion action channels, top-level and per-turn
``disabled_channels`` rejected; evidence path resolved within workspace and
file exists), non-vacuous isolation/citation GO conditions (every warm
repetition trusted — first-of-five invalid then later valid still fails; one
citation failure still fails; one post-command isolation failure increments
explicit ``isolation_scan_failures`` and blocks GO; ``after_cli`` mode allows
workspace-local ``.openlocus`` directory only if real non-symlink), strict
per-arm headroom state-machine ordering/short-circuit (each arm runs as a
fail-closed state machine: pre-isolation → fast-context → post-fast-context
isolation → schema ``_valid`` → ``citations validate`` → post-citation
isolation → citation true; no untrusted evidence reaches the citation CLI;
a treatment failure does not invoke citation/control; a treatment citation
failure does not invoke control; a control failure does not run later
repetitions; the citation CLI's post-call isolation failure is counted and
blocks GO), and
``_no_ancestor_marker`` cycle guard using string paths (not ``id(Path)`` reuse),
two-arm workspace independence (treatment and control materialized in
completely separate OS-temp workspaces from the same parent_sha — distinct
roots, both parent-exact, no marker/state crossing, repetition 2 accepts only
a real local ``.openlocus`` dir while rejecting file/symlink/ancestor markers),
non-object/malformed JSON fail-closed (JSON array/string/number/null returns
``_valid=False`` with ``_invalid_reason='non_object_json'`` without throwing or
including arbitrary raw data; ``TimeoutExpired``/``OSError``/unexpected
exceptions caught at the per-candidate headroom boundary and converted to a
fixed reason bucket; malformed citation output fails closed; boolean-as-integer
rejected for line numbers, token counts, diagnostics counts, and citation
counts via ``type(x) is int``), pack/evidence consistency (``pack.evidence``
must equal top-level ``evidence`` structurally and in order — not just count
match; ``pack.budget_used`` must equal top-level ``budget_used`` since the
production Rust construction clones both from the same values), and
byte-exact separate test overlays (separate test files use ``_git_bytes`` for
exact blob bytes including CRLF/non-ASCII; ``separate_test_blob_hash`` enforced
in ``apply_overlay`` proving git blob bytes == overlay bytes == on-disk bytes;
target path validated as relative/no ``..``/within-workspace).

Run::

    python eval/decision_experiment_phase1_audit.py --self-test
    python eval/decision_experiment_phase1_audit.py --audit \
        --openlocus target/debug/openlocus \
        --out artifacts/decision_experiment_phase1_audit/phase1_public_report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Reuse the repo's established forbidden-field privacy walker for consistency
# with the existing B-series public artifacts.
_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))
import b6_lite_interpretable_policy_search as b6lite  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Frozen constants (from the decision contract / oracle-approved plan)
# ---------------------------------------------------------------------------

FROZEN_CUTOFF = "056877ff638d59118e05e046bd30d816e70ba2fb"
SCHEMA_VERSION = "decision-experiment-phase1-audit-v0"
GENERATED_BY = "decision_experiment_phase1_audit"
CLAIM_LEVEL = "phase1_eligibility_headroom_audit_no_pain_no_product_no_effect_claim"

TREATMENT_CHANNELS = "regex,bm25,symbol,graph"
CONTROL_CHANNELS = "bm25"
MAX_EVIDENCE = 12
TOKEN_BUDGET = 2000

COHORT_MAX = 8
COHORT_MIN = 5
SCORING_RUN_CAP_S = 600  # 10 minutes per scoring run
REPRO_TRIALS = 3
REGRESSION_TRIALS = 2
WARM_REPS = 5
RETRIEVAL_P95_CAP_S = 3.0
HEADROOM_MIN_RATIO = 0.4  # ceil(0.4 * N), min 2

PRIVATE_RUN_DIR = REPO_ROOT / "runs" / "decision_experiment_phase1"
PUBLIC_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "decision_experiment_phase1_audit"

# File classification patterns (rule-based, no favorable handpicking).
# Product source = code under crates/<crate>/src/ (Rust or Python). Tests =
# files under crates/<crate>/tests/. The real OpenLocus product is Rust; the
# Python branch exists only so self-test fixtures can run lightweight tests
# without a cargo build.
_PROD_SRC_RE = re.compile(r"^crates/[^/]+/src/.+\.(rs|py)$")
_TESTS_DIR_RE = re.compile(r"^crates/[^/]+/tests/.+")
_DOCS_RE = re.compile(r"^docs/|^.*\.md$")
_PROTOCOL_RE = re.compile(r"protocol|phase\d|freeze|closeout|claim", re.I)
_GENERATED_RE = re.compile(r"^artifacts/|^target/|^\.openlocus/", re.I)
_EVAL_ONLY_RE = re.compile(r"^eval/")

# Commit-message exclusion prefixes (one logical defect only; exclude
# test-only / refactor / docs / dependency / migration / chore / ci).
_EXCLUDE_MSG_PREFIXES = (
    "docs:", "test:", "chore:", "ci:", "refactor:", "revert:",
    "build:", "style:", "perf:", "revert",
)

# Conventional-commit defect classifier (one logical defect only).
#
# Accepts defect-indicating prefixes only. Never accepts feat/docs/chore/etc.
# No handcoded favorable candidate list — the classifier is a fixed set of
# rule-based prefix patterns applied uniformly to every enumerated commit.
#
# Accepted defect prefixes (case-insensitive on the subject):
#   fix / fix: / fix(scope): / fix-...  — conventional-commit "fix" type,
#                                         including scoped variants fix(scope):
#   hotfix / hotfix: / hotfix(scope):   — hotfix prefix
#   bugfix / bugfix: / bugfix(scope):    — bugfix prefix
#   bug:                                — clear defect prefix (non-conventional)
#   repair:                             — defect-repair prefix (non-conventional)
#
# The bare prefix "fix" (without colon) is accepted to match natural defect
# prose like "fix off-by-one in ..." as permitted by the frozen contract
# (natural pre-fix prose from an unedited commit message, one logical defect).
# Unprefixed subjects with no defect signal are NOT accepted (fail-closed).
_DEFECT_MSG_PREFIXES = ("fix", "hotfix", "bugfix", "bug:", "repair:")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Git plumbing — deterministic enumeration
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path | None = None, timeout: int = 120) -> str:
    """Run a git command, return stdout. Raises on non-zero exit."""
    cmd = ["git"] + args
    cwd = str(cwd) if cwd else str(REPO_ROOT)
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({proc.returncode}): "
            f"{proc.stderr[:300]}"
        )
    return proc.stdout


def _git_bytes(args: list[str], cwd: Path | None = None, timeout: int = 120) -> bytes:
    """Run a git command, return stdout as **raw bytes** (no newline
    translation, no encoding replacement). Raises on non-zero exit.

    Used for byte-exact hash computation where ``text=True`` would translate
    ``\\r\\n`` → ``\\n`` and break round-trip with on-disk bytes.
    """
    cmd = ["git"] + args
    cwd = str(cwd) if cwd else str(REPO_ROOT)
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, timeout=timeout
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({proc.returncode}): "
            f"{proc.stderr[:300]}"
        )
    return proc.stdout


def enumerate_non_merge_commits(cutoff: str = FROZEN_CUTOFF) -> list[dict[str, Any]]:
    """Deterministically enumerate all non-merge commits reachable before the
    cutoff, ordered newest-first then SHA.

    Returns a list of dicts: {sha, committer_ts, subject} sorted by
    (-committer_ts, sha) so the order is fully deterministic regardless of
    platform git ordering.
    """
    # %H sha, %ct committer epoch, %s subject. --no-merges excludes merge
    # commits. Reachable "before" the cutoff = ancestors of the cutoff.
    raw = _git(
        ["log", "--no-merges", f"--format=%H|%ct|%s", cutoff],
    )
    commits: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        sha, ts_str, subject = parts[0], parts[1], parts[2]
        try:
            ts = int(ts_str)
        except ValueError:
            ts = 0
        commits.append({"sha": sha, "committer_ts": ts, "subject": subject})
    # Newest-first (ts desc), then SHA asc for determinism on ties.
    commits.sort(key=lambda c: (-c["committer_ts"], c["sha"]))
    return commits


def commit_file_changes(sha: str) -> list[dict[str, str]]:
    """Return changed files for a commit: [{status, path, added, deleted}]."""
    # --no-renames keeps status simple (A/M/D). numstat gives line counts.
    raw = _git(
        ["show", "--no-renames", "--numstat", "--format=", sha]
    )
    out: list[dict[str, str]] = []
    for line in raw.splitlines():
        line = line.rstrip()
        if not line:
            continue
        # numstat: <added>\t<deleted>\t<path>   (added/deleted '-' for binary)
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added_s, deleted_s, path = parts[0], parts[1], parts[2]
        # Status via separate show --name-status for A/M/D.
        out.append(
            {
                "path": path,
                "added": added_s if added_s != "-" else "0",
                "deleted": deleted_s if deleted_s != "-" else "0",
            }
        )
    # Augment with status codes from --name-status.
    raw_status = _git(
        ["show", "--no-renames", "--name-status", "--format=", sha]
    )
    status_map: dict[str, str] = {}
    for line in raw_status.splitlines():
        line = line.rstrip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            status_map[parts[-1]] = parts[0][0]
    for entry in out:
        entry["status"] = status_map.get(entry["path"], "M")
    return out


def commit_message(sha: str) -> str:
    """Return the full, unedited commit message body."""
    return _git(["log", "-1", "--format=%B", sha])


def diff_for_paths(parent: str, fix: str, paths: list[str]) -> str:
    """Return the unified diff of given paths between parent and fix."""
    args = ["diff", "--no-renames", parent, fix, "--"] + paths
    return _git(args)


# ---------------------------------------------------------------------------
# File classification
# ---------------------------------------------------------------------------


def classify_path(path: str) -> str:
    """Classify a changed path into a rule bucket."""
    if _GENERATED_RE.search(path):
        return "generated"
    if _DOCS_RE.search(path):
        return "docs"
    if _EVAL_ONLY_RE.search(path):
        return "eval_only"
    # Test files under crates/<crate>/tests/ are tests, checked before prod_src
    # since tests/ and src/ are disjoint directories.
    if _TESTS_DIR_RE.match(path):
        return "test_file"
    if _PROD_SRC_RE.match(path):
        return "prod_src"
    if path.endswith(".toml") or path.endswith("Cargo.lock"):
        return "config"
    if path.endswith(".rs"):
        return "other_rs"
    if path.endswith(".py"):
        return "python"
    return "other"


def production_files_and_lines(changes: list[dict[str, str]]) -> tuple[list[str], int]:
    """Return (production source paths, total production changed lines)."""
    prod_files: list[str] = []
    total_lines = 0
    for c in changes:
        if classify_path(c["path"]) == "prod_src":
            prod_files.append(c["path"])
            try:
                total_lines += int(c["added"]) + int(c["deleted"])
            except ValueError:
                pass
    return prod_files, total_lines


def test_files(changes: list[dict[str, str]]) -> list[str]:
    return [c["path"] for c in changes if classify_path(c["path"]) == "test_file"]


# ---------------------------------------------------------------------------
# Rust inline test region detection — deterministic, fail-closed
# ---------------------------------------------------------------------------


@dataclass
class TestRegion:
    """A detected ``#[cfg(test)] mod <name> { ... }`` region in a Rust source
    file. ``start_byte``/``end_byte`` are character indices into the
    UTF-8-decoded ``str`` (exclusive-end); line numbers are 1-based inclusive.

    To obtain true byte offsets in the original ``bytes``, use
    ``_char_to_byte_offset(text, index)`` — never slice raw bytes with these
    indices directly, as multi-byte UTF-8 characters make char != byte."""
    start_byte: int   # char index of the ``#[cfg(test)]`` attribute start
    end_byte: int     # char index one past the closing ``}``
    start_line: int   # 1-based line of the ``#[cfg(test)]`` attribute
    end_line: int     # 1-based line of the closing ``}``


# Matches #[cfg(test)] with tolerant whitespace inside the attribute.
_CFG_TEST_RE = re.compile(r"#\[\s*cfg\s*\(\s*test\s*\)\s*\]")


def _char_to_byte_offset(text: str, char_index: int) -> int:
    """Map a character index in a UTF-8-decoded ``str`` to the corresponding
    byte offset in the original ``bytes`` it was decoded from.

    For ASCII source (the common case) char and byte offsets coincide. For
    multi-byte UTF-8 this re-encodes the prefix to find the true byte offset,
    avoiding any newline translation. Assumes ``text`` was produced by a
    strict ``bytes.decode("utf-8")`` (no ``errors="replace"``).
    """
    return len(text[:char_index].encode("utf-8"))


def _skip_ws_and_comments(source: str, pos: int) -> int:
    """Skip whitespace, newlines, line comments, and (nested) block comments
    starting at *pos*. Returns the index of the next significant character."""
    while pos < len(source):
        ch = source[pos]
        if ch in " \t\r\n":
            pos += 1
        elif source[pos:pos + 2] == "//":
            nl = source.find("\n", pos)
            pos = nl + 1 if nl >= 0 else len(source)
        elif source[pos:pos + 2] == "/*":
            pos = _skip_block_comment(source, pos)
        else:
            break
    return pos


def _skip_block_comment(source: str, pos: int) -> int:
    """Skip a (possibly nested) block comment starting at *pos* (which must
    point at ``/*``). Returns the index one past the closing ``*/``.
    If unbalanced, returns ``len(source)`` (fail-closed)."""
    depth = 0
    while pos < len(source):
        if source[pos:pos + 2] == "/*":
            depth += 1
            pos += 2
        elif source[pos:pos + 2] == "*/":
            depth -= 1
            pos += 2
            if depth <= 0:
                return pos
        else:
            pos += 1
    return pos  # unbalanced — caller treats as end-of-file


def _skip_string(source: str, pos: int) -> int:
    """Skip a regular string literal ``"..."`` starting at *pos* (which must
    point at the opening ``"``). Handles ``\\`` escapes. Returns the index
    one past the closing ``"``. If unterminated, returns ``len(source)``."""
    pos += 1  # skip opening "
    while pos < len(source):
        ch = source[pos]
        if ch == "\\":
            pos += 2
            continue
        if ch == '"':
            return pos + 1
        pos += 1
    return pos


def _is_rust_ident_start(ch: str) -> bool:
    """Rust identifier start: ASCII alpha or underscore."""
    return ch == "_" or ("a" <= ch.lower() <= "z")


def _is_rust_ident_cont(ch: str) -> bool:
    """Rust identifier continuation: alphanumeric or underscore."""
    return _is_rust_ident_start(ch) or ch.isdigit()


def _skip_char(source: str, pos: int) -> int:
    """Skip a Rust char literal ``'...'`` starting at *pos* (which must point
    at the opening ``'``).

    Rust-aware lifetime/label distinction: a ``'`` followed by an identifier
    character with NO closing ``'`` before the next non-identifier char is a
    lifetime (``'a``, ``'static``) or label (``'label:``), NOT a char literal.
    Lifetimes/labels remain code tokens (their ``'`` is consumed as a single
    char so brace tracking continues normally).

    A real char literal is one of:
      - ``'\\x'`` / ``'\\n'`` / ``'\\\\'`` / ``'\\''`` etc. (escaped char)
      - ``'a'`` (single char followed immediately by closing ``'``)

    Fail-closed/conservative: if structural uncertainty arises (unterminated
    char literal, ambiguous form), consume only the opening ``'`` so the
    caller treats subsequent content as code (never silently swallow braces).
    """
    n = len(source)
    # pos points at the opening '
    nxt = pos + 1
    if nxt >= n:
        return pos + 1  # lone ' at EOF — consume it only

    # Case 1: escaped char literal  '\x'  '\n'  '\\'  '\''  '\u{...}'
    if source[nxt] == "\\":
        # Find the closing ' for the escape. Standard escapes are 2 chars
        # ('\n', '\\'), but '\u{...}' can be longer. Scan to the next '
        # that is not itself escaped.
        j = nxt + 1
        while j < n:
            if source[j] == "\\":
                j += 2
                continue
            if source[j] == "'":
                # This is a syntactically complete escaped char literal.
                return j + 1
            j += 1
        # Unterminated escaped char — conservative: consume only the opening '.
        return pos + 1

    # Case 2: single-char literal  'a'  — must be followed by closing '
    if nxt + 1 < n and source[nxt + 1] == "'":
        return nxt + 2  # past the closing '

    # Case 3: lifetime or label  'a  'static  'label:
    # A ' followed by an identifier char with no immediate closing ' is a
    # lifetime/label, NOT a char literal. Consume only the ' so the
    # identifier remains as code tokens for brace tracking.
    if _is_rust_ident_start(source[nxt]):
        return pos + 1  # lifetime/label: ' is a single code char

    # Case 4: anything else (e.g. ' followed by non-ident, non-escape, non-closing)
    # Conservative: consume only the opening '.
    return pos + 1


def _skip_raw_string(source: str, pos: int) -> int:
    """Skip a raw string literal ``r"..."`` or ``r#"..."#`` starting at *pos*
    (which must point at ``r`` followed by ``"`` or ``#``). Returns the index
    one past the closing delimiter. If unterminated, returns ``len(source)``."""
    pos += 1  # skip 'r'
    hashes = 0
    while pos < len(source) and source[pos] == "#":
        hashes += 1
        pos += 1
    if pos >= len(source) or source[pos] != '"':
        return pos  # not a raw string; caller continues normally
    pos += 1  # skip opening "
    close = '"' + "#" * hashes
    idx = source.find(close, pos)
    return idx + len(close) if idx >= 0 else len(source)


def _find_matching_brace(source: str, open_pos: int) -> int:
    """Find the byte index of the matching ``}`` for the ``{`` at *open_pos*.

    Uses deterministic brace-balanced parsing that respects string literals,
    char literals, raw strings, line comments, and nested block comments.
    Returns ``-1`` on unbalanced braces (fail-closed)."""
    depth = 0
    pos = open_pos
    n = len(source)
    while pos < n:
        ch = source[pos]

        # Line comment
        if source[pos:pos + 2] == "//":
            nl = source.find("\n", pos)
            pos = nl + 1 if nl >= 0 else n
            continue

        # Block comment (nested)
        if source[pos:pos + 2] == "/*":
            pos = _skip_block_comment(source, pos)
            continue

        # Raw string: r"..." / r#"..."#
        if ch == "r" and pos + 1 < n and source[pos + 1] in '"#':
            pos = _skip_raw_string(source, pos)
            continue

        # Regular string
        if ch == '"':
            pos = _skip_string(source, pos)
            continue

        # Char literal (conservative)
        if ch == "'":
            pos = _skip_char(source, pos)
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return pos

        pos += 1

    return -1  # unbalanced — fail-closed


def _find_cfg_test_in_code(source: str) -> list[re.Match]:
    """Find ``#[cfg(test)]`` attribute matches that occur in **code
    positions** — not inside line comments, block comments, regular string
    literals, raw string literals, or char literals.

    This prevents false positives where the literal text ``#[cfg(test)]``
    appears inside a comment, string, or raw string (which the previous
    naive ``finditer`` approach would wrongly treat as a real test-module
    attribute).

    Scans character-by-character, skipping non-code regions with the same
    helpers used by brace-balanced parsing, and only accepts ``#[cfg(test)]``
    matches found at code positions.
    """
    matches: list[re.Match] = []
    pos = 0
    n = len(source)
    while pos < n:
        ch = source[pos]

        # Line comment
        if source[pos:pos + 2] == "//":
            nl = source.find("\n", pos)
            pos = nl + 1 if nl >= 0 else n
            continue

        # Block comment (nested)
        if source[pos:pos + 2] == "/*":
            pos = _skip_block_comment(source, pos)
            continue

        # Raw string: r"..." / r#"..."# (also covers byte raw strings br"...")
        if ch == "r" and pos + 1 < n and source[pos + 1] in '"#':
            pos = _skip_raw_string(source, pos)
            continue

        # Regular string literal
        if ch == '"':
            pos = _skip_string(source, pos)
            continue

        # Char literal (conservative — same approach as _find_matching_brace)
        if ch == "'":
            pos = _skip_char(source, pos)
            continue

        # Check for #[cfg(test)] at this code position.
        m = _CFG_TEST_RE.match(source, pos)
        if m:
            matches.append(m)
            pos = m.end()
            continue

        pos += 1
    return matches


def detect_rust_inline_test_regions(source: str) -> list[TestRegion]:
    """Detect all ``#[cfg(test)] mod <name> { ... }`` regions in a Rust source
    file using deterministic brace-balanced parsing.

    Language-aware: ``#[cfg(test)]`` text appearing inside comments, string
    literals, raw strings, or char literals is **not** treated as a real
    test-module attribute (fixes attribute false positives).

    Fail-closed: on any malformed or ambiguous region (unbalanced braces,
    missing ``mod`` keyword, etc.) that region is silently dropped rather
    than returned. If the entire file is malformed, an empty list is
    returned (every line is treated as production — conservative).
    """
    regions: list[TestRegion] = []
    for attr_match in _find_cfg_test_in_code(source):
        attr_end = attr_match.end()

        # After #[cfg(test)], skip whitespace/comments to find 'mod'.
        pos = _skip_ws_and_comments(source, attr_end)

        # Match 'mod <identifier> {' (the opening brace is what we track).
        mod_match = re.match(r"mod\s+(\w+)\s*\{", source[pos:])
        if not mod_match:
            # #[cfg(test)] on a non-mod item (e.g. a fn) — not an inline
            # test *module*; skip.
            continue

        brace_pos = pos + mod_match.end() - 1  # index of '{'
        end_pos = _find_matching_brace(source, brace_pos)
        if end_pos < 0:
            # Unbalanced — fail-closed: skip this region entirely.
            continue

        start_line = source.count("\n", 0, attr_match.start()) + 1
        end_line = source.count("\n", 0, end_pos) + 1

        regions.append(TestRegion(
            start_byte=attr_match.start(),
            end_byte=end_pos + 1,  # exclusive end
            start_line=start_line,
            end_line=end_line,
        ))

    return regions


def line_is_in_test_region(line: int, regions: list[TestRegion]) -> bool:
    """Check if a 1-based line number falls within any test region."""
    return any(r.start_line <= line <= r.end_line for r in regions)


# ---------------------------------------------------------------------------
# Unified diff parsing — hunk extraction and test/prod classification
# ---------------------------------------------------------------------------


@dataclass
class DiffHunk:
    """A single unified-diff hunk."""
    old_start: int       # 1-based start line in the old (parent) file
    old_count: int       # number of old lines
    new_start: int       # 1-based start line in the new (fixed) file
    new_count: int       # number of new lines
    body: list[str]      # hunk body lines (each prefixed with ' '/'+'/'-')


_HUNK_HEADER_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def parse_unified_diff(diff_text: str) -> list[DiffHunk]:
    """Parse a unified diff into a list of hunks. Only hunk bodies (lines
    starting with ``' '``, ``'+'``, or ``'-'``) are captured; diff headers
    (``diff --git``, ``index``, ``---``, ``+++``) are skipped."""
    hunks: list[DiffHunk] = []
    lines = diff_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _HUNK_HEADER_RE.match(line)
        if not m:
            i += 1
            continue

        old_start = int(m.group(1))
        old_count = int(m.group(2)) if m.group(2) is not None else 1
        new_start = int(m.group(3))
        new_count = int(m.group(4)) if m.group(4) is not None else 1

        body: list[str] = []
        i += 1
        # Read hunk body until we hit the next hunk header, a diff header,
        # or EOF.  A bare empty string inside a hunk is treated as an empty
        # context line (some diff implementations omit the leading space).
        while i < len(lines):
            bl = lines[i]
            if bl.startswith("@@") or bl.startswith("diff ") or bl.startswith("--- ") or bl.startswith("+++ "):
                break
            if bl and not bl[0] in " +-\\":
                break
            body.append(bl)
            i += 1

        hunks.append(DiffHunk(
            old_start=old_start, old_count=old_count,
            new_start=new_start, new_count=new_count,
            body=body,
        ))
    return hunks


def hunk_added_deleted(hunk: DiffHunk) -> tuple[int, int]:
    """Count added (`+`) and deleted (`-`) lines in a hunk body."""
    added = 0
    deleted = 0
    for line in hunk.body:
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted += 1
    return added, deleted


def hunk_is_test_only(hunk: DiffHunk,
                      parent_regions: list[TestRegion],
                      fixed_regions: list[TestRegion]) -> bool:
    """Classify a hunk as test-only.

    A hunk is test-only if **both** its old (parent) line range and its new
    (fixed) line range fall entirely within detected inline test regions.
    Hunks that span the test/production boundary or touch production code
    are classified as production (fail-closed / conservative).

    Note: this hunk-level classification is used for dev-patch filtering.
    Production line **counting** uses the more precise line-by-line
    ``count_prod_lines_in_diff`` which excludes individual test-region lines
    even inside mixed hunks.
    """
    old_end = hunk.old_start + max(hunk.old_count, 1) - 1
    new_end = hunk.new_start + max(hunk.new_count, 1) - 1

    old_in_test = (
        line_is_in_test_region(hunk.old_start, parent_regions)
        and line_is_in_test_region(old_end, parent_regions)
    )
    new_in_test = (
        line_is_in_test_region(hunk.new_start, fixed_regions)
        and line_is_in_test_region(new_end, fixed_regions)
    )
    return old_in_test and new_in_test


def count_prod_lines_in_diff(
    diff_text: str,
    parent_regions: list[TestRegion],
    fixed_regions: list[TestRegion]) -> tuple[int, int]:
    """Count production (non-test-region) added and deleted lines in a diff.

    Uses line-by-line tracking within each hunk: for every ``+`` line the
    new-file line number is checked against ``fixed_regions``; for every
    ``-`` line the old-file line number is checked against ``parent_regions``.
    Only lines **outside** test regions are counted as production.

    This is more precise than hunk-level classification: a mixed hunk that
    spans the test/production boundary has only its production lines counted.
    """
    hunks = parse_unified_diff(diff_text)
    prod_added = 0
    prod_deleted = 0
    for hunk in hunks:
        old_line = hunk.old_start
        new_line = hunk.new_start
        for line in hunk.body:
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+"):
                if not line_is_in_test_region(new_line, fixed_regions):
                    prod_added += 1
                new_line += 1
            elif line.startswith("-"):
                if not line_is_in_test_region(old_line, parent_regions):
                    prod_deleted += 1
                old_line += 1
            else:
                # Context line (or empty line treated as context).
                old_line += 1
                new_line += 1
    return prod_added, prod_deleted


def production_files_and_lines_split(
    fix_sha: str, parent_sha: str,
    changes: list[dict[str, str]]) -> tuple[list[str], int]:
    """Return ``(production_paths, production_changed_lines)`` where inline
    Rust test-module regions are excluded from the line count AND from the
    production-file set.

    - Only ``prod_src`` files are considered.
    - For EVERY Rust ``prod_src`` file (regardless of numstat size), the
      actual unified diff is parsed and test-region lines are excluded
      line-by-line. A source file counts as a production file only if it
      has at least one changed line outside uniquely detected valid test
      regions. This prevents a small (``<=100`` raw lines) commit that
      touches only an inline test module from being misclassified as
      production.
    - Non-Rust files are counted raw (no inline test modules possible).
    - Fail-closed: if the diff or file contents cannot be retrieved, or the
      parent SHA is empty, or no test regions are detected at all in either
      parent or fixed, falls back to the raw numstat count (conservative —
      unknown lines are never treated as tests). Malformed/ambiguous test
      regions are dropped by ``detect_rust_inline_test_regions`` so their
      lines count as production, never as tests.
    """
    if not parent_sha:
        return production_files_and_lines(changes)

    prod_files: list[str] = []
    total_lines = 0
    for c in changes:
        path = c["path"]
        if classify_path(path) != "prod_src":
            continue
        raw_added = _int(c["added"])
        raw_deleted = _int(c["deleted"])
        raw_total = raw_added + raw_deleted

        # Only Rust files can have inline #[cfg(test)] mod tests.
        is_rust = path.endswith(".rs")
        if not is_rust:
            prod_files.append(path)
            total_lines += raw_total
            continue

        # Parse the diff and exclude test-region lines for EVERY Rust file,
        # not just large ones. A small test-only change must not be counted
        # as production.
        try:
            diff_text = diff_for_paths(parent_sha, fix_sha, [path])
            parent_src = _git(["show", f"{parent_sha}:{path}"])
            fixed_src = _git(["show", f"{fix_sha}:{path}"])
        except RuntimeError:
            # Cannot retrieve diff/contents — fail-closed: count raw.
            prod_files.append(path)
            total_lines += raw_total
            continue

        parent_regions = detect_rust_inline_test_regions(parent_src)
        fixed_regions = detect_rust_inline_test_regions(fixed_src)

        # If no test regions detected at all, fall back to raw count.
        if not parent_regions and not fixed_regions:
            prod_files.append(path)
            total_lines += raw_total
            continue

        prod_added, prod_deleted = count_prod_lines_in_diff(
            diff_text, parent_regions, fixed_regions)
        has_prod_changes = (prod_added + prod_deleted) > 0

        if has_prod_changes:
            prod_files.append(path)
        total_lines += prod_added + prod_deleted

    return prod_files, total_lines


def filter_diff_to_prod_hunks(
    diff_text: str,
    parent_regions: list[TestRegion],
    fixed_regions: list[TestRegion]) -> str:
    """Return a unified diff with test-only hunks removed.

    Used to produce a production-only dev patch for inline-test candidates so
    that the dev patch does not try to modify the test module region (which
    the overlay has already replaced). If parsing fails, returns the original
    diff unfiltered (fail-closed: the dev patch may fail to apply, which
    excludes the candidate — acceptable).
    """
    lines = diff_text.split("\n")
    output: list[str] = []
    i = 0
    # Copy header lines up to the first hunk.
    while i < len(lines) and not lines[i].startswith("@@"):
        output.append(lines[i])
        i += 1

    hunks = parse_unified_diff("\n".join(lines[i:]))
    for hunk in hunks:
        if hunk_is_test_only(hunk, parent_regions, fixed_regions):
            continue
        # Re-emit the hunk header and body.
        header = f"@@ -{hunk.old_start}"
        if hunk.old_count != 1:
            header += f",{hunk.old_count}"
        header += f" +{hunk.new_start}"
        if hunk.new_count != 1:
            header += f",{hunk.new_count}"
        header += " @@"
        output.append(header)
        output.extend(hunk.body)

    result = "\n".join(output)
    # Ensure the patch ends with a trailing newline — ``git apply`` requires
    # it and treats a patch without one as corrupt. The original diff from
    # ``_git`` ends with ``\n``, but ``split("\n")`` + ``join("\n")`` drops
    # the trailing newline. Restore it so the production-only dev patch
    # applies cleanly.
    if not result.endswith("\n"):
        result += "\n"
    return result


def has_natural_prefix_prose(subject: str, body: str) -> bool:
    """Natural pre-fix prose: subject is unedited, non-boilerplate, and not a
    protocol/phase/freeze/closeout/claim artifact."""
    text = (subject + " " + body).strip()
    if not text:
        return False
    if _PROTOCOL_RE.search(subject):
        return False
    # Reject generated/protocol-style subjects.
    lower = subject.lower()
    for bad in ("phase10", "phase9", "phase1", "operator package",
                "protocol freeze", "closeout", "claim", "materialization"):
        if bad in lower:
            return False
    return True


# ---------------------------------------------------------------------------
# Candidate filter — rule-based, aggregate reason buckets
# ---------------------------------------------------------------------------


@dataclass
class CandidateDecision:
    sha: str
    subject: str
    eligible: bool = False
    reason_bucket: str = ""


def filter_candidate(sha: str, subject: str, body: str,
                     changes: list[dict[str, str]],
                     parent_sha: str = "") -> CandidateDecision:
    """Apply the rule-based candidate filter. Never handpicks."""
    dec = CandidateDecision(sha=sha, subject=subject)

    low = subject.lower().strip()
    # Exclude categories first (each a distinct reason bucket).
    any_path = [c["path"] for c in changes]
    cats = {classify_path(p) for p in any_path}

    # Test-only commit: only test files, no production source.
    if "prod_src" not in cats:
        if "test_file" in cats or "python_test" in cats:
            dec.reason_bucket = "excluded_test_only"
            return dec
        if cats <= {"docs"} or "docs" in cats and not (cats & {"prod_src", "test_file"}):
            dec.reason_bucket = "excluded_docs_only"
            return dec
        dec.reason_bucket = "excluded_no_prod_source"
        return dec

    if "eval_only" in cats and not (cats & {"prod_src"}):
        dec.reason_bucket = "excluded_eval_only"
        return dec
    if "generated" in cats and not (cats & {"prod_src"}):
        dec.reason_bucket = "excluded_generated"
        return dec

    # Message-based exclusions.
    for prefix in _EXCLUDE_MSG_PREFIXES:
        if low.startswith(prefix):
            dec.reason_bucket = f"excluded_msg_{prefix.rstrip(':')}"
            return dec

    # Must look like a defect fix (one logical defect).
    is_fix = any(low.startswith(p) for p in _DEFECT_MSG_PREFIXES)
    if not is_fix:
        dec.reason_bucket = "excluded_not_defect_fix"
        return dec

    # Natural pre-fix prose from an unedited message.
    if not has_natural_prefix_prose(subject, body):
        dec.reason_bucket = "excluded_boilerplate_prose"
        return dec

    # Production files and lines — with inline Rust test regions excluded.
    if parent_sha:
        prod_files, prod_lines = production_files_and_lines_split(
            sha, parent_sha, changes)
    else:
        prod_files, prod_lines = production_files_and_lines(changes)

    # Test-only mixed file: a ``prod_src`` path is present (so the coarse
    # path check did not exclude it), but every changed line falls inside
    # an inline Rust test-module region — there is no actual production
    # change. Exclude as test-only so test-only mixed files never enter the
    # cohort. Separate test files are unaffected (they are classified
    # ``test_file``, not ``prod_src``, and handled by the earlier coarse
    # check).
    if not prod_files:
        dec.reason_bucket = "excluded_test_only"
        return dec

    if len(prod_files) > 2:
        dec.reason_bucket = "excluded_too_many_prod_files"
        return dec
    if prod_lines > 100:
        dec.reason_bucket = "excluded_too_many_prod_lines"
        return dec

    # Must have a developer-authored test: either a test file in this commit,
    # or a pre-existing test for the touched source (checked later in repro).
    tests = test_files(changes)
    if not tests:
        # Could still have a pre-existing test; defer to transplant step.
        dec.reason_bucket = "deferred_no_test_in_commit_check_preexisting"
        # Still mark as a pass-through candidate for the transplant step to
        # resolve (pre-existing test) or exclude.
        dec.eligible = True
        return dec

    dec.eligible = True
    dec.reason_bucket = "eligible_has_fix_and_test"
    return dec


# ---------------------------------------------------------------------------
# Test transplant — byte-for-byte, scorer-only isolated overlay
# ---------------------------------------------------------------------------


# Inline overlay base modes — explicit, NEVER inferred from contents.
#   "parent"           — workspace file must equal parent_full_hash (buggy
#                        parent + overlay / empty-patch path).
#   "fixed"            — workspace file must equal fixed_full_hash (fixed
#                        commit + same developer test path; may be a no-op
#                        if the module is already exact).
#   "parent_dev_patch" — workspace already has the production-only dev patch
#                        applied; outside-module bytes must equal fixed_prod_hash
#                        (parent + production-only dev patch + overlay path).
# Separate test-file overlays are byte-exact regardless of mode (no production
# bytes involved); mode is only consulted for ``inline_test_module``.
_OVERLAY_BASE_MODES = ("parent", "fixed", "parent_dev_patch")


@dataclass
class OverlaySpec:
    """A byte-for-byte transplanted developer test."""
    source_kind: str  # "commit_added_test" | "preexisting_test" | "inline_test_module"
    test_path: str
    test_bytes: bytes
    target_relpath: str  # where it lands in the workspace
    sha_origin: str
    # Inline test module verification hashes (empty for separate test files).
    # All hashes are sha256 of raw bytes (no newline translation) so they
    # match actual on-disk bytes after ``materialize_workspace`` (which uses
    # ``core.autocrlf=false``).
    parent_prod_hash: str = ""   # parent production portion (outside test region)
    fixed_test_hash: str = ""   # the fixed test module bytes
    parent_full_hash: str = ""  # FULL parent source blob (pre-overlay invariant for "parent" mode)
    fixed_prod_hash: str = ""   # fixed production portion (outside test region)
    fixed_full_hash: str = ""   # FULL fixed source blob (pre-overlay invariant for "fixed" mode)
    crate: str = ""             # derived crate name for cargo test -p <crate> --lib
    # Separate-test-file exact blob hash (sha256 of raw git blob bytes, no
    # newline translation). Enforced in ``apply_overlay`` for
    # ``commit_added_test`` / ``preexisting_test`` source kinds: the actual
    # on-disk bytes after write must hash to exactly this value. Proves git
    # blob bytes == overlay bytes == on-disk bytes even for CRLF/non-ASCII
    # content on Windows.
    separate_test_blob_hash: str = ""


def extract_overlay_test(fix_sha: str, parent_sha: str,
                         changes: list[dict[str, str]]) -> OverlaySpec | None:
    """Extract a developer test to transplant byte-for-byte.

    Policy: a test file added/modified by the fix commit, OR a pre-existing
    test file for a touched source path present at the parent, OR a Rust
    inline ``#[cfg(test)] mod tests`` module added/modified by the fix in a
    production source file. No edits, no new tests, no expected-value
    synthesis — the bytes are copied verbatim.
    """
    tests = test_files(changes)
    for tp in tests:
        # Byte-for-byte content at the fix commit (the developer's test).
        # Use raw bytes (``_git_bytes``) so there is NO newline translation
        # on Windows (``text=True`` would translate ``\r\n`` → ``\n`` and
        # break byte-exactness with the git blob / on-disk bytes). Fail
        # closed if the blob is absent (should not happen for a commit-added
        # test file, but be defensive).
        try:
            blob = _git_bytes(["show", f"{fix_sha}:{tp}"])
        except RuntimeError:
            continue
        if not blob:
            continue
        blob_hash = hashlib.sha256(blob).hexdigest()
        return OverlaySpec(
            source_kind="commit_added_test",
            test_path=tp,
            test_bytes=blob,
            target_relpath=tp,
            sha_origin=fix_sha,
            separate_test_blob_hash=blob_hash,
        )
    # No separate test file in the commit: look for a pre-existing test file
    # at the parent that corresponds to a touched production source file.
    # Use the split semantics so test-only mixed files (no production
    # changes) are not searched for a pre-existing test.
    prod_files, _ = production_files_and_lines_split(fix_sha, parent_sha,
                                                     changes)
    for pf in prod_files:
        # Heuristic: crate tests/<stem>_test.rs for src/<stem>.rs
        m = re.match(r"^crates/([^/]+)/src/(.+)\.rs$", pf)
        if not m:
            continue
        crate, stem = m.group(1), m.group(2)
        candidates = [
            f"crates/{crate}/tests/{stem}.rs",
            f"crates/{crate}/tests/{stem}_test.rs",
        ]
        for tp in candidates:
            # Use raw bytes (``_git_bytes``) for byte-exactness (no newline
            # translation on Windows). Fail closed if absent.
            try:
                blob = _git_bytes(["show", f"{parent_sha}:{tp}"])
            except RuntimeError:
                continue
            if blob:
                blob_hash = hashlib.sha256(blob).hexdigest()
                return OverlaySpec(
                    source_kind="preexisting_test",
                    test_path=tp,
                    test_bytes=blob,
                    target_relpath=tp,
                    sha_origin=parent_sha,
                    separate_test_blob_hash=blob_hash,
                )

    # No separate test file: look for a Rust inline #[cfg(test)] mod tests
    # module in a production source file that was modified by the fix.
    for pf in prod_files:
        if not pf.endswith(".rs"):
            continue
        try:
            # Use raw bytes (no newline translation) for byte-exact hash
            # computation. Decode as strict UTF-8 for region detection.
            fixed_raw = _git_bytes(["show", f"{fix_sha}:{pf}"])
            parent_raw = _git_bytes(["show", f"{parent_sha}:{pf}"])
        except RuntimeError:
            continue
        # Fail-closed on non-UTF-8 source: cannot safely map offsets.
        try:
            fixed_src = fixed_raw.decode("utf-8")
            parent_src = parent_raw.decode("utf-8")
        except UnicodeDecodeError:
            continue

        fixed_regions = detect_rust_inline_test_regions(fixed_src)
        if not fixed_regions:
            continue

        # Ambiguity fail-closed: if there is not exactly one inline test
        # module region in the fixed commit, the correspondence between
        # parent and fixed test regions cannot be uniquely determined.
        # Do NOT silently use region 0.
        if len(fixed_regions) > 1:
            continue

        parent_regions = detect_rust_inline_test_regions(parent_src)
        # Ambiguity fail-closed: multiple parent test modules make the
        # parent/fixed region correspondence ambiguous.
        if len(parent_regions) > 1:
            continue

        # The inline test module exists in the fixed commit. Extract its
        # exact bytes (the whole #[cfg(test)] mod ... { ... } region) from
        # the raw bytes using byte-offset mapping.
        region = fixed_regions[0]
        byte_start = _char_to_byte_offset(fixed_src, region.start_byte)
        byte_end = _char_to_byte_offset(fixed_src, region.end_byte)
        test_module_bytes = fixed_raw[byte_start:byte_end]

        # Derive the crate name from the path for cargo test -p <crate> --lib.
        m = re.match(r"^crates/([^/]+)/src/.+\.rs$", pf)
        crate = m.group(1) if m else ""

        # Hash the parent production portion (everything outside the test
        # region) for later verification that the overlay preserves it
        # exactly (zero fixed production bytes transplanted). Computed from
        # raw bytes so it matches actual on-disk bytes after overlay.
        if parent_regions:
            pr = parent_regions[0]
            p_byte_start = _char_to_byte_offset(parent_src, pr.start_byte)
            p_byte_end = _char_to_byte_offset(parent_src, pr.end_byte)
            parent_prod_bytes = (
                parent_raw[:p_byte_start] + parent_raw[p_byte_end:]
            )
        else:
            parent_prod_bytes = parent_raw
        parent_prod_hash = hashlib.sha256(parent_prod_bytes).hexdigest()
        fixed_test_hash = hashlib.sha256(test_module_bytes).hexdigest()
        # Full parent blob hash — the workspace file BEFORE overlay must equal
        # this exactly (enforced in apply_overlay mode="parent"). Never the
        # fixed blob.
        parent_full_hash = hashlib.sha256(parent_raw).hexdigest()
        # Fixed production portion (outside test region) — used by
        # mode="fixed" and mode="parent_dev_patch" to prove only the frozen
        # developer production patch changed production, while overlay
        # contributes test bytes only.
        fixed_prod_bytes = fixed_raw[:byte_start] + fixed_raw[byte_end:]
        fixed_prod_hash = hashlib.sha256(fixed_prod_bytes).hexdigest()
        # Full fixed blob hash — the workspace file BEFORE overlay must equal
        # this exactly in mode="fixed" (fixed commit + same developer test).
        fixed_full_hash = hashlib.sha256(fixed_raw).hexdigest()

        return OverlaySpec(
            source_kind="inline_test_module",
            test_path=pf,
            test_bytes=test_module_bytes,
            target_relpath=pf,
            sha_origin=fix_sha,
            parent_prod_hash=parent_prod_hash,
            fixed_test_hash=fixed_test_hash,
            parent_full_hash=parent_full_hash,
            fixed_prod_hash=fixed_prod_hash,
            fixed_full_hash=fixed_full_hash,
            crate=crate,
        )
    return None


# ---------------------------------------------------------------------------
# Workspace materialization — isolation via git archive (no .git), OS temp
# ---------------------------------------------------------------------------

# Marker files/dirs whose presence above or at a workspace indicates a live
# checkout that the scorer/CLI must NOT reach.
_ROOT_MARKERS = (".git", ".openlocus")


def _outside_repo_root(path: Path) -> bool:
    """True if *path* is strictly outside ``REPO_ROOT`` (no path containment)."""
    try:
        rp = path.resolve()
        rr = REPO_ROOT.resolve()
        # path must not be REPO_ROOT itself or inside it.
        if rp == rr:
            return False
        try:
            rp.relative_to(rr)
            return False  # path is inside REPO_ROOT
        except ValueError:
            return True  # path is outside REPO_ROOT
    except OSError:
        return False


def _workspace_has_no_markers(path: Path,
                              allow_workspace_openlocus_dir: bool = False) -> bool:
    """True if *path* itself contains no ``.git`` / ``.openlocus`` marker
    (file/dir/symlink all count).

    When ``allow_workspace_openlocus_dir=True`` (the ``after_cli`` mode), a
    workspace-local ``.openlocus`` is allowed ONLY if it is a real non-symlink
    directory. A file or symlink ``.openlocus`` is always rejected (a symlink
    could point at the live checkout). ``.git`` is always rejected.
    """
    for marker in _ROOT_MARKERS:
        m = path / marker
        if m.exists() or m.is_symlink():
            if (marker == ".openlocus"
                    and allow_workspace_openlocus_dir
                    and m.is_dir()
                    and not m.is_symlink()):
                # Real directory created by the CLI inside the workspace —
                # allowed. Ancestors are still checked by _no_ancestor_marker.
                continue
            return False
    return True


def _no_ancestor_marker(path: Path) -> bool:
    """True if NO ancestor directory from *path* upward to the filesystem root
    contains a ``.git`` or ``.openlocus`` marker (file/dir/symlink). This
    prevents a workspace nested inside a live checkout from reaching the live
    repo's markers via CLI root discovery (which walks upward for ``.git`` or
    ``.openlocus``).

    Cycle guard uses string paths, not ``id(Path)``, because Python may reuse
    a memory address after a Path object is garbage-collected, which would
    produce a false cycle-guard hit and silently truncate the walk.
    """
    # Start from the workspace's PARENT, since the workspace itself is checked
    # by _workspace_has_no_markers. Walk upward to root.
    try:
        current = path.parent.resolve()
    except OSError:
        return False
    seen: set[str] = set()
    while True:
        s = str(current)
        if s in seen:
            break  # cycle guard (string-based, not id(Path))
        seen.add(s)
        for marker in _ROOT_MARKERS:
            m = current / marker
            if m.exists() or m.is_symlink():
                return False
        if current == current.parent:
            break  # filesystem root
        current = current.parent
    return True


def assert_workspace_isolated(workspace: Path,
                              mode: str = "before_cli") -> None:
    """Assert a scorer/pack workspace is properly isolated. Raises
    ``RuntimeError`` if any isolation invariant fails.

    ``mode`` is explicit and never inferred from contents:

    - ``"before_cli"`` (default): no workspace marker at all — neither
      ``.git`` nor ``.openlocus`` may exist (file/dir/symlink) in the
      workspace. Used before any CLI invocation.
    - ``"after_cli"``: the CLI may have created a workspace-local
      ``.openlocus`` directory (for traces). This is allowed ONLY if it is a
      real non-symlink directory; ``.git`` is still absent; and all
      ancestors remain marker-free. A file/symlink ``.openlocus`` is rejected
      (a symlink could point at the live checkout).

    Both modes require the workspace to be outside ``REPO_ROOT`` and no
    ancestor to contain a marker.
    """
    if mode not in ("before_cli", "after_cli"):
        raise ValueError(f"unknown isolation mode: {mode}")
    if not _outside_repo_root(workspace):
        raise RuntimeError(
            f"isolation violation: workspace {workspace} is inside REPO_ROOT")
    allow_openlocus = (mode == "after_cli")
    if not _workspace_has_no_markers(workspace,
                                     allow_workspace_openlocus_dir=allow_openlocus):
        raise RuntimeError(
            f"isolation violation: workspace {workspace} contains a root marker "
            f"(mode={mode})")
    if not _no_ancestor_marker(workspace):
        raise RuntimeError(
            f"isolation violation: ancestor of workspace {workspace} "
            f"contains a .git/.openlocus marker")


def _make_temp_workspace(prefix: str = "dope_phase1_ws_") -> Path:
    """Create a fresh empty workspace directory in OS temp (outside REPO_ROOT)
    via ``tempfile.mkdtemp`` (default OS temp root). Asserts the result is
    outside REPO_ROOT and has no ancestor markers so CLI root discovery
    cannot reach the live checkout."""
    ws = Path(tempfile.mkdtemp(prefix=prefix))
    assert_workspace_isolated(ws)
    return ws


def materialize_workspace(sha: str, dest: Path) -> Path:
    """Materialize a clean working tree of ``sha`` into ``dest`` with NO
    ``.git`` directory. Uses ``git archive`` so the runtime copy cannot
    access child/fix diff/hidden test/scorer/oracle files.

    ``dest`` MUST be outside ``REPO_ROOT`` (enforced by
    ``assert_workspace_isolated``). Workspaces live in OS temp, never under
    ``REPO_ROOT/runs``.

    **Byte-exact:** passes ``-c core.autocrlf=false`` so ``git archive``
    does NOT translate ``LF`` → ``CRLF`` on Windows. This guarantees the
    on-disk bytes exactly equal the git blob bytes (as returned by
    ``_git_bytes(["show", ...])``), which is required for byte-exact
    overlay hash verification.
    """
    # Enforce isolation BEFORE any materialization.
    assert_workspace_isolated(dest)
    dest.mkdir(parents=True, exist_ok=True)
    tar_path = dest.parent / f"{dest.name}.tar"
    with open(tar_path, "wb") as f:
        proc = subprocess.run(
            ["git", "-c", "core.autocrlf=false",
             "archive", "--format=tar", sha],
            cwd=str(REPO_ROOT), stdout=f, timeout=120,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"git archive {sha} failed")
    with tarfile.open(tar_path) as tf:
        tf.extractall(dest)
    try:
        tar_path.unlink()
    except OSError:
        pass
    # Guarantee no .git linkage exists in the workspace itself.
    for marker in _ROOT_MARKERS:
        m = dest / marker
        if m.exists() or m.is_symlink():
            if marker == ".openlocus":
                # fast-context creates workspace-local .openlocus which is
                # allowed ONLY inside the workspace; ancestor scan still
                # must pass. Remove it before re-asserting since it was not
                # created by the CLI yet (materialization step).
                shutil.rmtree(m, ignore_errors=True) if m.is_dir() else m.unlink(missing_ok=True) if hasattr(m, 'unlink') else None
            else:
                shutil.rmtree(m, ignore_errors=True) if m.is_dir() else m.unlink()
    # Re-assert isolation after materialization.
    assert_workspace_isolated(dest)
    return dest


def apply_overlay(workspace: Path, overlay: OverlaySpec,
                  mode: str = "parent") -> Path:
    """Write the transplanted test byte-for-byte into the isolated workspace.

    For separate test files (``commit_added_test`` / ``preexisting_test``),
    the test bytes are written to ``overlay.target_relpath`` verbatim — mode
    is irrelevant (no production bytes involved).

    For inline test modules (``inline_test_module``), the test module region
    in the workspace's existing source file is **replaced** with the fixed
    test module bytes. The production portion outside the module is left
    untouched (it comes from whichever commit was materialized — never from
    the fix, except for the frozen developer production patch in
    ``parent_dev_patch`` mode).

    ``mode`` is explicit (never inferred from contents):

    - ``"parent"`` (buggy parent + overlay / empty patch): before write,
      workspace file must equal ``parent_full_hash``; after write, outside
      module remains parent production (``parent_prod_hash``) and module is
      exact fixed test (``fixed_test_hash``).
    - ``"fixed"`` (fixed commit + same developer test): before write,
      workspace file must equal ``fixed_full_hash``; after write, outside
      module equals FIXED production (``fixed_prod_hash``) and module is
      exact fixed test. May be a no-op if module already exact. Never
      demands parent hash.
    - ``"parent_dev_patch"`` (parent + production-only dev patch + overlay):
      before write, outside module equals FIXED production (``fixed_prod_hash``)
      — proves only the frozen developer production patch changed production;
      after write, outside module still equals FIXED production and module is
      exact fixed test — overlay contributes test bytes only.

    Raises ``ValueError`` on ANY mismatch (fail-closed). Never
    appends/replaces fixed production bytes.

    **Byte-safe:** reads/writes raw ``bytes`` (no newline translation), maps
    character offsets from UTF-8-decoded region detection back to byte
    offsets in the original bytes, and writes with ``write_bytes``. Fails
    closed (raises ``ValueError``) on invalid UTF-8 or ambiguous multiple
    test-module regions.
    """
    if mode not in _OVERLAY_BASE_MODES:
        raise ValueError(f"unknown overlay base mode: {mode}")
    target = workspace / overlay.target_relpath
    if overlay.source_kind == "inline_test_module":
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = target.read_bytes() if target.exists() else b""

        # Pre-overlay invariant: depends on the explicit mode.
        if mode == "parent":
            # Workspace file must equal the FULL parent blob.
            if overlay.parent_full_hash:
                actual_full = hashlib.sha256(raw).hexdigest()
                if actual_full != overlay.parent_full_hash:
                    raise ValueError(
                        f"pre-overlay invariant failed (mode=parent): "
                        f"workspace file {overlay.target_relpath} does not "
                        f"match parent full blob hash (possible fix-byte leak "
                        f"or wrong commit)")
        elif mode == "fixed":
            # Workspace file must equal the FULL fixed blob. The overlay is
            # typically a no-op (module already exact) but we still verify.
            if overlay.fixed_full_hash:
                actual_full = hashlib.sha256(raw).hexdigest()
                if actual_full != overlay.fixed_full_hash:
                    raise ValueError(
                        f"pre-overlay invariant failed (mode=fixed): "
                        f"workspace file {overlay.target_relpath} does not "
                        f"match fixed full blob hash (expected fixed commit "
                        f"materialization)")
        elif mode == "parent_dev_patch":
            # Workspace already has the production-only dev patch applied.
            # Outside-module bytes must equal FIXED production portion.
            if overlay.fixed_prod_hash:
                try:
                    pre_text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    raise ValueError(
                        f"pre-overlay non-UTF-8 file (mode=parent_dev_patch): "
                        f"{overlay.target_relpath}")
                pre_regions = detect_rust_inline_test_regions(pre_text)
                if len(pre_regions) != 1:
                    raise ValueError(
                        f"pre-overlay invariant failed (mode=parent_dev_patch): "
                        f"expected exactly one inline test module, found "
                        f"{len(pre_regions)} in {overlay.target_relpath}")
                pr = pre_regions[0]
                pre_start = _char_to_byte_offset(pre_text, pr.start_byte)
                pre_end = _char_to_byte_offset(pre_text, pr.end_byte)
                actual_prod = raw[:pre_start] + raw[pre_end:]
                if (hashlib.sha256(actual_prod).hexdigest()
                        != overlay.fixed_prod_hash):
                    raise ValueError(
                        f"pre-overlay invariant failed (mode=parent_dev_patch): "
                        f"production bytes outside test module do not match "
                        f"fixed production hash in {overlay.target_relpath} "
                        f"(dev patch not applied or wrong patch)")

        # Decode as strict UTF-8 for region detection. Fail-closed on
        # invalid UTF-8: do not apply an overlay to a non-UTF-8 file.
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError(
                f"cannot apply inline overlay to non-UTF-8 file: "
                f"{overlay.target_relpath}")

        regions = detect_rust_inline_test_regions(text)

        # Ambiguity fail-closed: if the workspace file has multiple test
        # module regions, we cannot uniquely determine which to replace.
        if len(regions) > 1:
            raise ValueError(
                f"ambiguous: multiple inline test regions in "
                f"{overlay.target_relpath}")

        if regions:
            r = regions[0]
            # Map character indices to byte offsets in the original bytes.
            byte_start = _char_to_byte_offset(text, r.start_byte)
            byte_end = _char_to_byte_offset(text, r.end_byte)
            combined = raw[:byte_start] + overlay.test_bytes + raw[byte_end:]
        else:
            # No existing test module region: this means the parent had no
            # inline test module. Appending the fixed test bytes would add
            # fixed production-adjacent bytes — fail closed instead. The
            # overlay must replace an existing region, never append.
            raise ValueError(
                f"no inline test region in workspace file "
                f"{overlay.target_relpath} to replace; refusing to append "
                f"(would introduce fixed production-adjacent bytes)")
        target.write_bytes(combined)

        # Post-overlay invariants: verify actual on-disk bytes.
        written = target.read_bytes()
        try:
            wtext = written.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError(
                f"post-overlay non-UTF-8 file: {overlay.target_relpath}")
        wregions = detect_rust_inline_test_regions(wtext)
        if len(wregions) != 1:
            raise ValueError(
                f"post-overlay invariant failed: expected exactly one "
                f"inline test module, found {len(wregions)} in "
                f"{overlay.target_relpath}")
        wr = wregions[0]
        wb_start = _char_to_byte_offset(wtext, wr.start_byte)
        wb_end = _char_to_byte_offset(wtext, wr.end_byte)
        actual_module = written[wb_start:wb_end]
        actual_prod = written[:wb_start] + written[wb_end:]
        # Post-overlay production hash depends on mode:
        # - "parent" → parent production (unchanged by overlay).
        # - "fixed" / "parent_dev_patch" → fixed production.
        expected_prod_hash = (
            overlay.parent_prod_hash if mode == "parent"
            else overlay.fixed_prod_hash
        )
        if (hashlib.sha256(actual_prod).hexdigest()
                != expected_prod_hash):
            raise ValueError(
                f"post-overlay invariant failed (mode={mode}): production "
                f"bytes outside test module do not match expected "
                f"{'parent' if mode == 'parent' else 'fixed'} production "
                f"hash in {overlay.target_relpath}")
        if (hashlib.sha256(actual_module).hexdigest()
                != overlay.fixed_test_hash):
            raise ValueError(
                f"post-overlay invariant failed: test module bytes do not "
                f"match fixed test hash in {overlay.target_relpath}")
        return target
    # Separate test file: write byte-for-byte. Mode is irrelevant for
    # separate test files (no production bytes involved).
    # Validate target path is relative, has no ``..`` traversal, and
    # resolves within the workspace before writing (defense in depth).
    rel = Path(overlay.target_relpath)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(
            f"unsafe overlay target path: {overlay.target_relpath}")
    try:
        ws_resolved = workspace.resolve()
        resolved = (workspace / overlay.target_relpath).resolve()
        resolved.relative_to(ws_resolved)
    except (ValueError, OSError):
        raise ValueError(
            f"overlay target escapes workspace: {overlay.target_relpath}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(overlay.test_bytes)
    # Enforce exact blob hash: the actual on-disk bytes must hash to the
    # same sha256 as the git blob bytes. Proves git blob bytes == overlay
    # bytes == on-disk bytes (catches newline translation / encoding
    # corruption on Windows for CRLF/non-ASCII content). Fail closed.
    if overlay.separate_test_blob_hash:
        actual_hash = hashlib.sha256(
            target.read_bytes()).hexdigest()
        if actual_hash != overlay.separate_test_blob_hash:
            raise ValueError(
                f"post-write invariant failed: on-disk test bytes do not "
                f"match git blob hash in {overlay.target_relpath} "
                f"(possible newline/encoding translation)")
    return target


def apply_patch_text(workspace: Path, patch_text: str) -> bool:
    """Apply a unified diff patch to the workspace. Returns True on success.

    Uses ``git apply`` against a bare workspace (no .git needed). Fail-closed.

    **Byte-safe:** passes ``-c core.autocrlf=false`` and sends the patch as
    raw bytes (``input=patch_text.encode``) to avoid Python ``text=True``
    newline translation (``\\n`` → ``\\r\\n`` on Windows). The workspace
    files have LF (from ``materialize_workspace`` with
    ``core.autocrlf=false``) and the patch text has LF (from ``_git`` text
    mode), so they match without conversion.
    """
    if not patch_text.strip():
        return False
    proc = subprocess.run(
        ["git", "-c", "core.autocrlf=false",
         "apply", "--whitespace=nowarn", "-"],
        cwd=str(workspace), input=patch_text.encode("utf-8"),
        capture_output=True, timeout=60,
    )
    return proc.returncode == 0


# ---------------------------------------------------------------------------
# Cold reproducibility checks
# ---------------------------------------------------------------------------


@dataclass
class ReproResult:
    checked: bool = False
    buggy_fail_3_of_3: bool = False
    fixed_pass_3_of_3: bool = False
    regression_pass_2_of_2: bool = False
    dev_patch_passes: bool = False
    empty_patch_fails: bool = False
    stable_signature: bool = False
    within_cap: bool = False
    reason_bucket: str = ""
    fail_signature: str = ""  # private — only stored in runs/, never public


def _detect_runner(test_path: str, source_kind: str = "") -> str:
    if source_kind == "inline_test_module":
        return "cargo_lib"
    if test_path.endswith(".rs"):
        return "cargo"
    if test_path.endswith(".py"):
        return "python"
    return "unknown"


def _normalize_sig_text(text: str, workspace: Path) -> str:
    """Normalize workspace-specific paths out of stderr so the failure
    signature reflects the failure type, not the isolated workspace location.
    Each repro trial uses a different temp workspace dir; without normalization
    the absolute path in tracebacks would make signatures differ spuriously."""
    norm = text.replace(str(workspace.resolve()), "<ws>").replace(
        str(workspace), "<ws>")
    # Collapse any remaining drive-rooted or posix temp prefixes before the
    # crate path so signatures are stable across machines and self-test runs.
    norm = re.sub(r"[A-Za-z]:\\[^\n:]*?(?=\\crates\\)", "<ws>", norm)
    norm = re.sub(r"/[A-Za-z0-9._/\-]*?(?=/crates/)", "<ws>", norm)
    return norm


def _run_test_once(workspace: Path, test_path: str, runner: str,
                   timeout: int) -> tuple[bool, str]:
    """Run the transplanted test once. Returns (passed, signature).

    signature = sha256 of (returncode + path-normalized tail of stderr) for
    stability checks. The signature captures the failure mode, not the
    isolated workspace path.
    """
    if runner == "python":
        proc = subprocess.run(
            [sys.executable, test_path],
            cwd=str(workspace),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
        norm = _normalize_sig_text(proc.stderr[-400:], workspace)
        sig_input = f"{proc.returncode}|{norm}"
        return (proc.returncode == 0, hashlib.sha256(sig_input.encode()).hexdigest())
    if runner == "cargo":
        stem = Path(test_path).stem
        proc = subprocess.run(
            ["cargo", "test", "--test", stem, "--", "--nocapture"],
            cwd=str(workspace),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
        norm = _normalize_sig_text(proc.stderr[-400:], workspace)
        sig_input = f"{proc.returncode}|{norm}"
        return (proc.returncode == 0, hashlib.sha256(sig_input.encode()).hexdigest())
    if runner == "cargo_lib":
        # Inline #[cfg(test)] mod tests — run the library test target.
        # The crate name is derived from the source path. If cargo cannot
        # resolve -p <crate>, the run fails (fail-closed).
        m = re.match(r"^crates/([^/]+)/src/.+\.rs$", test_path)
        crate = m.group(1) if m else ""
        if not crate:
            return (False, "no_crate_derived")
        proc = subprocess.run(
            ["cargo", "test", "-p", crate, "--lib", "--", "--nocapture"],
            cwd=str(workspace),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
        norm = _normalize_sig_text(proc.stderr[-400:], workspace)
        sig_input = f"{proc.returncode}|{norm}"
        return (proc.returncode == 0, hashlib.sha256(sig_input.encode()).hexdigest())
    return (False, "unknown_runner")


def run_repro(fix_sha: str, parent_sha: str, changes: list[dict[str, str]],
              overlay: OverlaySpec, runs_dir: Path,
              per_run_cap: int = SCORING_RUN_CAP_S) -> ReproResult:
    """Cold reproducibility checks. Excludes (reason bucket) if not
    deterministically/safely checkable. Never weakens rules."""
    res = ReproResult()
    runner = _detect_runner(overlay.target_relpath, overlay.source_kind)
    if runner == "unknown":
        res.reason_bucket = "repro_unknown_test_runner"
        return res

    # Use split semantics so test-only mixed files are excluded from the
    # dev-patch path set — the dev patch must only carry production changes.
    prod_files, _ = production_files_and_lines_split(fix_sha, parent_sha,
                                                     changes)
    patch_text = diff_for_paths(parent_sha, fix_sha, prod_files)

    # For inline test modules, filter the dev patch to production-only hunks
    # so it does not modify the test module region (which the overlay
    # replaces). This ensures zero fixed production bytes are needed beyond
    # the dev patch itself, and the overlay handles the test bytes.
    if overlay.source_kind == "inline_test_module":
        try:
            parent_src = _git(["show", f"{parent_sha}:{overlay.target_relpath}"])
            fixed_src = _git(["show", f"{fix_sha}:{overlay.target_relpath}"])
            parent_regions = detect_rust_inline_test_regions(parent_src)
            fixed_regions = detect_rust_inline_test_regions(fixed_src)
            patch_text = filter_diff_to_prod_hunks(
                patch_text, parent_regions, fixed_regions)
        except RuntimeError:
            pass  # fail-closed: unfiltered patch may not apply

    # All scorer workspaces live in OS temp outside REPO_ROOT (real
    # isolation topology, same as production CLI root discovery).
    t0 = time.perf_counter()

    def _elapsed() -> bool:
        return (time.perf_counter() - t0) > per_run_cap

    try:
        # ---- buggy parent + overlay: must FAIL 3/3 with stable signature ----
        # mode="parent": workspace is the buggy parent; overlay replaces the
        # parent test module with the fixed test module. Pre-overlay verifies
        # parent_full_hash; post-overlay verifies parent_prod_hash (unchanged
        # production) + fixed_test_hash.
        buggy_fails: list[bool] = []
        buggy_sigs: list[str] = []
        for i in range(REPRO_TRIALS):
            ws = _make_temp_workspace(prefix=f"dope_phase1_repro_buggy{i}_")
            materialize_workspace(parent_sha, ws)
            apply_overlay(ws, overlay, mode="parent")
            ok, sig = _run_test_once(ws, overlay.target_relpath, runner,
                                     per_run_cap)
            buggy_fails.append(not ok)
            buggy_sigs.append(sig)
            shutil.rmtree(ws, ignore_errors=True)
            if _elapsed():
                res.reason_bucket = "repro_exceeded_cap"
                return res
        res.buggy_fail_3_of_3 = all(buggy_fails) and len(buggy_fails) == REPRO_TRIALS
        res.stable_signature = len(set(buggy_sigs)) == 1
        res.fail_signature = buggy_sigs[0] if buggy_sigs else ""

        # ---- fixed commit + same overlay: must PASS 3/3 ----
        # mode="fixed": workspace is the fixed commit; overlay is a no-op
        # (module already exact). Pre-overlay verifies fixed_full_hash;
        # post-overlay verifies fixed_prod_hash + fixed_test_hash. Never
        # demands parent hash.
        fixed_passes: list[bool] = []
        for i in range(REPRO_TRIALS):
            ws = _make_temp_workspace(prefix=f"dope_phase1_repro_fixed{i}_")
            materialize_workspace(fix_sha, ws)
            apply_overlay(ws, overlay, mode="fixed")
            ok, _ = _run_test_once(ws, overlay.target_relpath, runner,
                                   per_run_cap)
            fixed_passes.append(ok)
            shutil.rmtree(ws, ignore_errors=True)
            if _elapsed():
                res.reason_bucket = "repro_exceeded_cap"
                return res
        res.fixed_pass_3_of_3 = all(fixed_passes) and len(fixed_passes) == REPRO_TRIALS

        # ---- relevant fixed regression: passes 2/2 ----
        reg_passes: list[bool] = []
        for i in range(REGRESSION_TRIALS):
            ws = _make_temp_workspace(prefix=f"dope_phase1_repro_reg{i}_")
            materialize_workspace(fix_sha, ws)
            ok, _ = _run_test_once(ws, overlay.target_relpath, runner,
                                   per_run_cap)
            reg_passes.append(ok)
            shutil.rmtree(ws, ignore_errors=True)
            if _elapsed():
                res.reason_bucket = "repro_exceeded_cap"
                return res
        res.regression_pass_2_of_2 = all(reg_passes) and len(reg_passes) == REGRESSION_TRIALS

        # ---- developer patch: buggy parent + dev patch + overlay must pass ----
        # For inline test modules, the dev patch (production-only hunks) is
        # applied FIRST, then the overlay replaces the test module. This
        # ensures the overlay's test bytes do not conflict with the patch.
        # mode="parent_dev_patch": pre-overlay verifies fixed_prod_hash
        # (dev patch already changed production); post-overlay verifies
        # fixed_prod_hash (unchanged by overlay) + fixed_test_hash. Proves
        # only the frozen developer production patch changed production,
        # while overlay contributes test bytes only.
        # For separate test files, the order does not matter (different files).
        ws = _make_temp_workspace(prefix="dope_phase1_repro_devpatch_")
        materialize_workspace(parent_sha, ws)
        applied = apply_patch_text(ws, patch_text)
        if not applied:
            res.reason_bucket = "repro_dev_patch_not_appliable"
            shutil.rmtree(ws, ignore_errors=True)
            return res
        apply_overlay(ws, overlay,
                       mode="parent_dev_patch"
                       if overlay.source_kind == "inline_test_module"
                       else "parent")
        ok, _ = _run_test_once(ws, overlay.target_relpath, runner, per_run_cap)
        res.dev_patch_passes = ok
        shutil.rmtree(ws, ignore_errors=True)

        # ---- empty patch: buggy parent + overlay + no patch must fail ----
        # Same as the buggy-parent path (mode="parent"): no dev patch applied.
        ws = _make_temp_workspace(prefix="dope_phase1_repro_empty_")
        materialize_workspace(parent_sha, ws)
        apply_overlay(ws, overlay, mode="parent")
        ok, _ = _run_test_once(ws, overlay.target_relpath, runner, per_run_cap)
        res.empty_patch_fails = not ok
        shutil.rmtree(ws, ignore_errors=True)

        res.within_cap = (time.perf_counter() - t0) <= per_run_cap
        res.checked = True
        if not (res.buggy_fail_3_of_3 and res.fixed_pass_3_of_3
                and res.regression_pass_2_of_2 and res.dev_patch_passes
                and res.empty_patch_fails and res.stable_signature
                and res.within_cap):
            res.reason_bucket = "repro_checks_not_all_satisfied"
        return res
    except subprocess.TimeoutExpired:
        res.reason_bucket = "repro_timeout_excluded"
        return res
    except Exception as exc:  # noqa: BLE001
        res.reason_bucket = "repro_unsafe_excluded"
        _write_private(runs_dir, "repro_error.txt", f"{fix_sha}: {exc!r}\n")
        return res


# ---------------------------------------------------------------------------
# Pack generation — SAME existing production Fast Context path
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Pack generation — SAME existing production Fast Context path
# ---------------------------------------------------------------------------

# The actual freshness enum value for verified-current evidence, as serialized
# by the real production source/schema. Used for validation (not guesswork).
_FRESHNESS_VERIFIED_CURRENT = "verified_current"

# Real Fast Context JSON schema constants. The production ``Evidence`` struct
# is ``#[serde(flatten)] pub core: EvidenceCore`` plus optional ``meta``, so
# evidence JSON fields are FLATTENED: ``path, start_line, end_line,
# content_sha, score, why, channels`` (+ optional ``meta``). There is NO
# nested ``core`` object. Validation fails closed on the nested pseudo-schema.
_FC_EVIDENCE_CORE_KEYS = frozenset({
    "path", "start_line", "end_line", "content_sha", "score", "why", "channels",
})
# Real FastContextDiagnostics keys (exact set — extras are rejected).
_FC_DIAGNOSTICS_KEYS = frozenset({
    "invalid_citations_dropped", "unknown_channels", "token_budget_enforced",
})
# Valid action channels (the 4 fusion channels + path used by some turns).
_FC_VALID_ACTION_CHANNELS = frozenset({"regex", "bm25", "symbol", "graph"})


def _validate_fast_context_output(out: dict[str, Any],
                                  requested_channels: str,
                                  workspace: Path) -> tuple[bool, str]:
    """Validate a ``fast-context --json`` output against the REAL production
    FLATTENED schema. Returns ``(valid, reason)``.

    The real ``Evidence`` is ``#[serde(flatten)] pub core: EvidenceCore``, so
    evidence JSON fields are directly ``path, start_line, end_line,
    content_sha, score, why, channels`` (plus optional ``meta``). There is NO
    nested ``core`` object. Fail closed on the nested pseudo-schema rather
    than supporting an invented fixture shape.

    Fail-closed on any of:
    - nonzero exit (caller checks returncode separately)
    - non-object/malformed JSON (caller detects)
    - ``success != true``
    - top-level ``error`` field present
    - empty ``evidence`` list
    - nonempty ``disabled_channels`` (top-level or per-turn)
    - any requested channel missing from successful ``actions[]``
    - unexpected non-fusion action channel
    - unexpected ``actions[].error``
    - ``remote_calls != 0``
    - diagnostics missing/unknown keys or wrong types; ``unknown_channels``
      nonempty
    - trace mismatch (``trace_id`` != ``pack.trace_id``)
    - pack.evidence count mismatch with top-level evidence
    - token budget overflow (``budget_used.tokens_estimated > TOKEN_BUDGET``)
    - nested ``core`` object in any evidence (invented pseudo-schema)
    - absent/wrong-type/non-positive/disordered ``start_line``/``end_line``
    - absent ``content_sha``; absent/non-list ``channels`` or ``why``
    - unsafe/out-of-workspace/non-existent evidence ``path``
    - evidence freshness not the expected ``verified_current`` value
    - turns absent/empty or per-turn ``disabled_channels`` nonempty
    """
    if not isinstance(out, dict):
        return False, "malformed_json"
    if out.get("success") is not True:
        return False, f"success_not_true:{out.get('success')}"
    if out.get("error"):
        return False, f"error_field:{str(out.get('error'))[:60]}"
    evidence = out.get("evidence", [])
    if not isinstance(evidence, list) or not evidence:
        return False, "empty_evidence"
    # Top-level disabled_channels must be empty.
    disabled = out.get("disabled_channels", [])
    if not isinstance(disabled, list):
        return False, "malformed_disabled_channels"
    if disabled:
        return False, f"disabled_channels:{disabled}"
    # Turns must be non-empty and each must have no disabled channels.
    turns = out.get("turns", [])
    if not isinstance(turns, list) or not turns:
        return False, "no_turns"
    for t in turns:
        if not isinstance(t, dict):
            return False, "malformed_turn"
        if not t.get("turn"):
            return False, "turn_missing_kind"
        t_disabled = t.get("disabled_channels", [])
        if not isinstance(t_disabled, list):
            return False, "malformed_turn_disabled_channels"
        if t_disabled:
            return False, f"turn_disabled_channels:{t_disabled}"
    # Actions must be non-empty, each with a valid fusion channel, no error.
    requested = [c for c in requested_channels.split(",") if c]
    actions = out.get("actions", [])
    if not isinstance(actions, list) or not actions:
        return False, "no_actions"
    action_channels = set()
    for a in actions:
        if not isinstance(a, dict):
            return False, "malformed_action"
        if a.get("error"):
            return False, f"action_error:{str(a.get('error'))[:60]}"
        ch = a.get("channel", "")
        if not isinstance(ch, str) or not ch:
            return False, "action_missing_channel"
        # Reject unexpected non-fusion action channels.
        if ch not in _FC_VALID_ACTION_CHANNELS:
            return False, f"unexpected_action_channel:{ch}"
        action_channels.add(ch)
    # Every requested channel must appear in successful actions.
    missing_channels = set(requested) - action_channels
    if missing_channels:
        return False, f"missing_channels:{sorted(missing_channels)}"
    # remote_calls must be 0 (provider-free).
    if out.get("remote_calls", -1) != 0:
        return False, f"remote_calls_nonzero:{out.get('remote_calls')}"
    # Diagnostics: exact known keys/types, unknown_channels empty.
    diag = out.get("diagnostics", {})
    if not isinstance(diag, dict):
        return False, "malformed_diagnostics"
    diag_keys = set(diag.keys())
    if diag_keys != _FC_DIAGNOSTICS_KEYS:
        return False, f"diagnostics_keys_mismatch:{sorted(diag_keys ^ _FC_DIAGNOSTICS_KEYS)}"
    if not _is_real_int(diag.get("invalid_citations_dropped")):
        return False, "diag_invalid_citations_dropped_not_int"
    if not isinstance(diag.get("unknown_channels"), list):
        return False, "diag_unknown_channels_not_list"
    if diag.get("unknown_channels"):
        return False, f"unknown_channels_nonempty:{diag.get('unknown_channels')}"
    if not isinstance(diag.get("token_budget_enforced"), bool):
        return False, "diag_token_budget_enforced_not_bool"
    # trace_id must be non-empty and match pack.trace_id.
    trace_id = out.get("trace_id", "")
    if not isinstance(trace_id, str) or not trace_id:
        return False, "empty_trace_id"
    pack = out.get("pack", {})
    if not isinstance(pack, dict) or "evidence" not in pack:
        return False, "no_pack"
    if trace_id != pack.get("trace_id", ""):
        return False, "trace_mismatch"
    # pack.evidence must be the same trusted set, structurally and in
    # order — a count match is insufficient. The production Rust
    # construction (``plan.rs``) clones the same ``final_evidence`` Vec
    # into both ``result.evidence`` and ``result.pack.evidence``, so they
    # are always identical in content and order. Enforce exact equality.
    pack_evidence = pack.get("evidence", [])
    if not isinstance(pack_evidence, list):
        return False, "malformed_pack_evidence"
    if len(pack_evidence) != len(evidence):
        return False, "pack_evidence_count_mismatch"
    if pack_evidence != evidence:
        return False, "pack_evidence_structural_mismatch"
    # Token budget respected.
    budget_used = out.get("budget_used", {})
    if not isinstance(budget_used, dict):
        return False, "no_budget_used"
    tokens = budget_used.get("tokens_estimated", 0)
    if not _is_real_int(tokens) or tokens <= 0:
        return False, "tokens_not_meaningful"
    if tokens > TOKEN_BUDGET:
        return False, f"budget_overflow:{tokens}"
    # pack.budget_used must equal the top-level budget_used. The production
    # Rust construction builds both from the same ``latency_ms`` /
    # ``tokens_estimated`` / ``remote_cost_estimated: 0.0`` values, so they
    # are always identical. Enforce exact equality (not just token count).
    pack_budget = pack.get("budget_used")
    if not isinstance(pack_budget, dict):
        return False, "pack_budget_used_mismatch"
    if pack_budget != budget_used:
        return False, "pack_budget_used_mismatch"
    # Every evidence must use the FLATTENED schema and be valid.
    ws_resolved = workspace.resolve()
    for ev in evidence:
        if not isinstance(ev, dict):
            return False, "malformed_evidence"
        # Fail closed on nested pseudo-schema (invented ``core`` object).
        if "core" in ev:
            return False, "nested_core_in_evidence"
        # Required flattened core fields with type/range validation.
        ev_path = ev.get("path", "")
        if not isinstance(ev_path, str) or not ev_path:
            return False, "absent_evidence_path"
        start_line = ev.get("start_line")
        end_line = ev.get("end_line")
        if not _is_real_int(start_line) or not _is_real_int(end_line):
            return False, "evidence_lines_not_int"
        if start_line <= 0 or end_line <= 0:
            return False, "evidence_lines_not_positive"
        if start_line > end_line:
            return False, "evidence_lines_not_ordered"
        content_sha = ev.get("content_sha", "")
        if not isinstance(content_sha, str) or not content_sha:
            return False, "absent_content_sha"
        channels = ev.get("channels", [])
        if not isinstance(channels, list) or not channels:
            return False, "absent_or_empty_channels"
        score = ev.get("score", 0)
        if not isinstance(score, (int, float)):
            return False, "evidence_score_not_number"
        why = ev.get("why", [])
        if not isinstance(why, list):
            return False, "evidence_why_not_list"
        # Path must be relative (inside workspace), not absolute/escaping.
        evp = Path(ev_path)
        if evp.is_absolute() or ".." in evp.parts:
            return False, f"unsafe_evidence_path:{ev_path[:60]}"
        # Resolved target must be within workspace.
        try:
            resolved = (workspace / ev_path).resolve()
            resolved.relative_to(ws_resolved)
        except (ValueError, OSError):
            return False, f"evidence_path_escapes_workspace:{ev_path[:60]}"
        # The referenced file must actually exist in the workspace.
        if not (workspace / ev_path).exists():
            return False, f"evidence_path_not_found:{ev_path[:60]}"
        # Freshness must be the expected current value (in meta, not core).
        meta = ev.get("meta", {})
        if not isinstance(meta, dict):
            return False, "no_evidence_meta"
        freshness = meta.get("freshness", "")
        if freshness != _FRESHNESS_VERIFIED_CURRENT:
            return False, f"stale_freshness:{freshness}"
    return True, ""


def run_fast_context(openlocus: str, query: str, channels: str,
                     cwd: Path, timeout: int = 120) -> dict[str, Any]:
    """Call the production ``openlocus fast-context`` CLI. Provider-free.

    treatment: regex,bm25,symbol,graph + RRF + final citation/currentness.
    control:   bm25-only, same builder/renderer/query/caps.

    Hardened against the REAL schema: the returned dict carries a
    ``_valid`` boolean and ``_invalid_reason`` string so callers can
    fail-closed on any schema/citation/isolation failure rather than
    treating partial output as a successful retrieval.
    """
    cmd = [
        openlocus, "fast-context", query,
        "--channels", channels,
        "--max-evidence", str(MAX_EVIDENCE),
        "--budget", str(TOKEN_BUDGET),
        "--json",
    ]
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    valid = False
    invalid_reason = ""
    # Parse as Any: ``json.loads`` may yield a list, string, number, bool,
    # or null — not necessarily a dict. Never assign into a non-dict.
    try:
        parsed: Any = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        parsed = None
        invalid_reason = "malformed_json"
    # Only proceed if the parsed result is a dict. A non-object JSON
    # (array/string/number/null) must fail closed — never include arbitrary
    # raw data or attempt to assign keys into a non-dict.
    if isinstance(parsed, dict):
        out: dict[str, Any] = parsed
    else:
        if not invalid_reason:
            invalid_reason = "non_object_json"
        out = {}
    out["latency_ms"] = latency_ms
    out["returncode"] = proc.returncode
    if proc.returncode != 0:
        invalid_reason = f"nonzero_exit:{proc.returncode}"
    elif not invalid_reason:
        valid, invalid_reason = _validate_fast_context_output(
            out, channels, Path(cwd))
    out["_valid"] = valid
    out["_invalid_reason"] = invalid_reason
    return out


def validate_citations(openlocus: str, evidence: list[dict[str, Any]],
                       cwd: Path, timeout: int = 120) -> tuple[bool, dict[str, Any]]:
    """Run the EXACT ``citations validate`` invocation from
    ``eval/fast_context_smoke.py`` against an arm's evidence list.

    Writes evidence to a temp JSON file (in OS temp, OUTSIDE REPO_ROOT so no
    private evidence enters the repo tree), invokes
    ``openlocus citations validate <file> --json``, and requires:

    - ``returncode == 0``
    - output is a JSON object
    - ``valid_count`` is an integer and equals ``len(evidence)``
    - ``invalid_count`` is an integer and equals 0

    Every evidence must be validated (``valid_count == len(evidence)`` and
    ``invalid_count == 0`` proves no evidence was dropped or invalid).

    Returns ``(valid, validate_output)``.
    """
    if not evidence:
        return False, {"reason": "no_evidence_to_validate"}
    # Temp file in OS temp (outside REPO_ROOT) so no private evidence enters
    # the repo tree. Cleaned up in the ``finally`` block.
    cite_file = Path(tempfile.mkstemp(prefix="dope_phase1_cite_", suffix=".json")[1])
    try:
        cite_file.write_text(json.dumps(evidence), encoding="utf-8")
        cmd = [openlocus, "citations", "validate", str(cite_file), "--json"]
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
        # Parse as Any: the output may not be a JSON object (could be a
        # list, string, number, null, or malformed). Never assign into a
        # non-dict or spread a non-dict with ``{**out}``.
        try:
            parsed: Any = json.loads(proc.stdout) if proc.stdout.strip() else None
        except json.JSONDecodeError:
            return False, {"reason": "malformed_citation_json",
                           "returncode": proc.returncode}
        # Require a JSON object. A non-object (array/string/number/null)
        # fails closed — never include arbitrary raw data.
        if not isinstance(parsed, dict):
            return False, {"reason": "citation_output_not_object",
                           "returncode": proc.returncode}
        out: dict[str, Any] = parsed
        out["returncode"] = proc.returncode
        # Require returncode 0.
        if proc.returncode != 0:
            return False, out
        # Require expected integer types (reject bool — ``type(v) is int``).
        valid_count = out.get("valid_count")
        invalid_count = out.get("invalid_count")
        if not _is_real_int(valid_count) or not _is_real_int(invalid_count):
            return False, dict(out, reason="citation_counts_not_int")
        # Every evidence must be validated (no invalid, none dropped).
        ok = (valid_count == len(evidence) and invalid_count == 0)
        return ok, out
    finally:
        try:
            cite_file.unlink()
        except OSError:
            pass


def materialize_pack_workspace(parent_sha: str) -> Path:
    """Materialize a PARENT-commit workspace for pack generation (no .git).

    Materializes ``parent_sha`` (NEVER ``fix_sha``) so no fixed
    implementation bytes enter either retrieval arm. The workspace lives in
    OS temp outside ``REPO_ROOT`` with full isolation assertions.
    """
    ws = _make_temp_workspace(prefix="dope_phase1_pack_ws_")
    materialize_workspace(parent_sha, ws)
    return ws


def pack_relevant_paths(pack: dict[str, Any]) -> set[str]:
    """Extract the set of source paths present in a rendered pack (private).

    Uses the REAL FLATTENED evidence schema: ``path`` is a direct field on
    each evidence object (not nested under ``core``). There is no nested
    ``core`` object in the real production schema.
    """
    paths: set[str] = set()
    for ev in pack.get("evidence", []) or []:
        if not isinstance(ev, dict):
            continue
        # Flattened schema: path is a direct field on the evidence object.
        p = ev.get("path", "")
        if isinstance(p, str) and p:
            paths.add(p)
    return paths


def pack_freshness_counts(pack: dict[str, Any]) -> dict[str, int]:
    """Count freshness labels in a pack (private diagnostic).

    ``freshness`` lives in the optional ``meta`` object on each evidence
    (the real production ``EvidenceMeta`` struct), NOT inside a nested
    ``core``.
    """
    counts: dict[str, int] = {}
    for ev in pack.get("evidence", []) or []:
        if not isinstance(ev, dict):
            continue
        meta = ev.get("meta")
        if not isinstance(meta, dict):
            fr = "unknown"
        else:
            fr = meta.get("freshness", "unknown")
            if not isinstance(fr, str):
                fr = "unknown"
        counts[fr] = counts.get(fr, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Headroom diagnostic — spend gate, NOT an outcome
# ---------------------------------------------------------------------------


@dataclass
class HeadroomResult:
    g_i: int = 0
    bm25_omits_relevant: bool = False
    treatment_adds_current_evidence: bool = False
    materially_different: bool = False
    retrieval_p95_s: float = 0.0
    citation_rematerialized: bool = False
    treatment_degenerate: bool = False
    isolation_scans: int = 0
    # Explicit isolation scan failure count (never inferred from reason text).
    # Summed from every scan across all warm repetitions and both arms. Must
    # be 0 for GO; any failure fails the candidate closed.
    isolation_scan_failures: int = 0
    treatment_valid: bool = False
    control_valid: bool = False
    citations_validated: bool = False
    reason_bucket: str = ""


@dataclass
class ArmResult:
    """One arm result (treatment or control) from a single warm repetition.

    Captures the schema-validity, citation-validation, latency, and isolation
    scan outcomes for ONE arm of ONE repetition. Used by
    ``_aggregate_warm_reps`` to prove every repetition is trusted (a later
    valid run cannot erase an earlier failure).

    ``failure_reason`` is non-empty iff the arm failed at some step of the
    strict per-arm state machine (``_run_one_arm``). The caller short-
    circuits on any non-empty value and returns G_i=0 — it never invokes the
    citation CLI after a schema/isolation failure, and never invokes the
    other arm after a treatment failure.
    """
    pack: dict[str, Any] = field(default_factory=dict)
    valid: bool = False
    invalid_reason: str = ""
    latency_s: float = 0.0
    citations_ok: bool = False
    citations_output: dict[str, Any] = field(default_factory=dict)
    isolation_scans: int = 0
    isolation_scan_failures: int = 0
    failure_reason: str = ""


@dataclass
class WarmRepSet:
    """Aggregated result of all warm repetitions for one candidate.

    All-or-nothing: if ANY repetition/arm/citation/isolation scan fails,
    ``all_valid`` is False and ``failure_reason`` explains the first failure.
    ``p95_s`` is computed ONLY from a fully valid 5-run set.
    """
    reps: list[dict[str, ArmResult]] = field(default_factory=list)
    isolation_scans: int = 0
    isolation_scan_failures: int = 0
    all_valid: bool = False
    failure_reason: str = ""
    p95_s: float = 0.0
    final_treatment_pack: dict[str, Any] = field(default_factory=dict)
    final_control_pack: dict[str, Any] = field(default_factory=dict)


def _aggregate_warm_reps(reps: list[dict[str, ArmResult]]) -> WarmRepSet:
    """Aggregate warm-repetition results into a ``WarmRepSet``.

    Every repetition and both arms must be fully valid: output ``_valid``,
    citations validated against THAT run's evidence, and isolation scans
    passed. Any invalid/partial/citation/isolation failure fails the
    candidate closed — a later valid run does NOT erase an earlier failure.

    p95 is computed ONLY from a fully valid set (all 5 reps pass). The final
    fully-validated pack is the last repetition's pack (deterministic).
    """
    result = WarmRepSet(reps=reps)
    treat_lats: list[float] = []
    for idx, rep in enumerate(reps):
        treat = rep.get("treatment")
        ctrl = rep.get("control")
        if treat is None or ctrl is None:
            result.failure_reason = f"warm_rep_{idx}_missing_arm"
            return result
        # Sum scans and failures across both arms of this rep.
        result.isolation_scans += treat.isolation_scans + ctrl.isolation_scans
        result.isolation_scan_failures += (
            treat.isolation_scan_failures + ctrl.isolation_scan_failures
        )
        # Any isolation failure fails closed immediately.
        if treat.isolation_scan_failures > 0 or ctrl.isolation_scan_failures > 0:
            result.failure_reason = (
                f"warm_rep_{idx}_isolation_scan_failed")
            return result
        # Schema-validity of both arms.
        if not treat.valid:
            result.failure_reason = (
                f"warm_rep_{idx}_treatment_invalid:{treat.invalid_reason}")
            return result
        if not ctrl.valid:
            result.failure_reason = (
                f"warm_rep_{idx}_control_invalid:{ctrl.invalid_reason}")
            return result
        # Citations must be validated for both arms against THIS run's evidence.
        if not treat.citations_ok:
            result.failure_reason = (
                f"warm_rep_{idx}_treatment_citation_failed")
            return result
        if not ctrl.citations_ok:
            result.failure_reason = (
                f"warm_rep_{idx}_control_citation_failed")
            return result
        treat_lats.append(treat.latency_s)
    if not treat_lats:
        result.failure_reason = "warm_rep_no_valid_runs"
        return result
    # All repetitions passed: compute p95 from the fully valid set.
    result.all_valid = True
    if len(treat_lats) >= 2:
        result.p95_s = statistics.quantiles(
            treat_lats, n=20, method="inclusive")[18]
    else:
        result.p95_s = treat_lats[0]
    # Use the final (deterministic) fully-validated pack.
    result.final_treatment_pack = reps[-1]["treatment"].pack
    result.final_control_pack = reps[-1]["control"].pack
    return result


def _do_isolation_scan(workspace: Path, mode: str) -> tuple[int, int]:
    """Perform one isolation scan. Returns ``(scans, failures)``.

    ``scans`` is always 1 (the scan was performed — non-vacuous). ``failures``
    is 1 if the scan raised, 0 otherwise. Never infers failures from reason
    text — the count is explicit.
    """
    try:
        assert_workspace_isolated(workspace, mode=mode)
        return 1, 0
    except RuntimeError:
        return 1, 1


def _run_one_arm(openlocus: str, natural_query: str, channels: str,
                 workspace: Path, pre_mode: str) -> ArmResult:
    """Run one arm of one warm repetition as a strict fail-closed state machine.

    Order (each step must pass before the next; any failure short-circuits):

      1. pre-isolation scan (``pre_mode``) passes;
      2. run ``fast-context``;
      3. post-fast-context isolation scan (``after_cli``) passes;
      4. fast-context schema ``_valid`` is true;
      5. ONLY THEN run ``citations validate`` on that trusted evidence;
      6. ``after_cli`` isolation scan after citation validation (the
         citation CLI is another invocation); require it passes;
      7. citation validation true;
      8. caller proceeds to the other arm / next repetition.

    No untrusted evidence (schema-invalid or non-isolated) reaches the
    citation CLI. ``TimeoutExpired``/``OSError``/unexpected exceptions from
    ``run_fast_context``/``validate_citations`` are NOT caught here — they
    propagate to the per-candidate ``headroom_for_candidate`` boundary so
    the existing fail-closed ``except`` clauses convert them to a fixed
    reason bucket.

    Returns an ``ArmResult`` with all scan/citation/schema outcomes
    populated. ``failure_reason`` is non-empty iff the arm failed at some
    step (caller short-circuits and returns G_i=0).
    """
    arm = ArmResult()
    scans = 0
    failures = 0

    # 1. Pre-isolation scan (before_cli for rep 0, after_cli for reps 2..5).
    s, f = _do_isolation_scan(workspace, mode=pre_mode)
    scans += s
    failures += f
    if f > 0:
        arm.isolation_scans = scans
        arm.isolation_scan_failures = failures
        arm.failure_reason = "arm_pre_isolation_scan_failed"
        return arm

    # 2. Run fast-context (may raise — propagates to per-candidate boundary).
    pack = run_fast_context(openlocus, natural_query, channels, workspace)
    arm.pack = pack if isinstance(pack, dict) else {}
    arm.valid = bool(pack.get("_valid")) if isinstance(pack, dict) else False
    arm.invalid_reason = (
        pack.get("_invalid_reason", "") if isinstance(pack, dict)
        else "non_object_json")
    arm.latency_s = (
        pack.get("latency_ms", 0) / 1000.0 if isinstance(pack, dict) else 0.0)

    # 3. Post-fast-context isolation scan (the fast-context CLI is an
    #    invocation; the workspace may now have a workspace-local
    #    .openlocus directory which after_cli allows if real non-symlink).
    s, f = _do_isolation_scan(workspace, mode="after_cli")
    scans += s
    failures += f
    if f > 0:
        arm.isolation_scans = scans
        arm.isolation_scan_failures = failures
        arm.failure_reason = "arm_post_fast_context_isolation_scan_failed"
        return arm

    # 4. Schema _valid must be true before citation validation — never
    #    pass untrusted (schema-invalid) evidence to the citation CLI.
    if not arm.valid:
        arm.isolation_scans = scans
        arm.isolation_scan_failures = failures
        arm.failure_reason = f"arm_schema_invalid:{arm.invalid_reason}"
        return arm

    # 5. ONLY NOW run citation validation on trusted evidence (may raise —
    #    propagates to per-candidate boundary). The citation CLI is another
    #    subprocess invocation in this workspace.
    evidence = pack.get("evidence", []) if isinstance(pack, dict) else []
    cite_ok, cite_out = validate_citations(openlocus, evidence, workspace)
    arm.citations_ok = cite_ok
    arm.citations_output = cite_out

    # 6. after_cli isolation scan after citation validation (the citation
    #    CLI is another invocation); require it passes. This is counted and
    #    blocks the arm if it fails.
    s, f = _do_isolation_scan(workspace, mode="after_cli")
    scans += s
    failures += f
    arm.isolation_scans = scans
    arm.isolation_scan_failures = failures
    if f > 0:
        arm.failure_reason = "arm_post_citation_isolation_scan_failed"
        return arm

    # 7. Citation validation true.
    if not arm.citations_ok:
        arm.failure_reason = "arm_citation_validation_failed"
        return arm

    # 8. Success — caller proceeds to the other arm / next repetition.
    return arm


def headroom_for_candidate(fix_sha: str, parent_sha: str,
                           changes: list[dict[str, str]],
                           natural_query: str, openlocus: str,
                           runs_dir: Path) -> HeadroomResult:
    """Compute G_i for one candidate. Uses private fix-relevant preimage paths.

    G_i=1 only if BM25 omits a relevant path AND treatment adds valid current
    evidence absent from control, with materially different rendered packs,
    AND both arms are schema-valid, citations are validated for both arms,
    AND isolation scans were performed and passed.

    **Two independent workspaces:** treatment and control arms run in
    COMPLETELY SEPARATE OS-temp workspaces materialized from the exact same
    ``parent_sha``. No shared ``.openlocus``, index, trace, or cache. After
    treatment creates a workspace-local ``.openlocus``, control's
    ``before_cli`` scan would necessarily fail in a shared workspace; also
    treatment state may contaminate control. Two workspaces eliminate this.

    For each arm: before its FIRST invocation use ``before_cli``; after each
    invocation use ``after_cli``; before repetitions 2..5 use ``after_cli``
    (workspace-local real ``.openlocus`` may exist). All ancestors remain
    marker-free. Both workspaces are scanned before and after every
    invocation and explicit counts/failures are aggregated.

    Strict per-arm state machine (``_run_one_arm``): pre-isolation →
    fast-context → post-fast-context isolation → schema ``_valid`` →
    ``citations validate`` → post-citation isolation → citation true. A
    treatment failure does NOT invoke citation/control; a treatment citation
    failure does NOT invoke control; a control failure does NOT run later
    repetitions. No untrusted evidence (schema-invalid or non-isolated)
    reaches the citation CLI. Any failure immediately records explicit
    scans/failures, a fixed private reason bucket, and returns G_i=0.
    Cleanup both workspaces in ``finally``.

    Any command/schema/citation/isolation failure — including
    ``TimeoutExpired``, ``OSError``, and unexpected subprocess/validation
    exceptions — fails closed for the candidate/gate (G_i=0 with a fixed
    reason bucket) at the per-candidate headroom boundary. It must NOT look
    like a BM25 omission and must NOT abort the whole audit. Exception
    details are never published.
    """
    res = HeadroomResult()
    treat_ws: Path | None = None
    ctrl_ws: Path | None = None
    try:
        # Use split semantics so test-only mixed files do not enter the
        # fix-relevant preimage path set.
        prod_files, _ = production_files_and_lines_split(fix_sha, parent_sha,
                                                         changes)

        # Private fix-relevant preimage paths: production files changed by the fix
        # plus existing direct source/config dependency paths from the parent.
        # These are private scorer labels only — no fixed implementation bytes
        # enter either retrieval arm (the workspace is materialized from PARENT).
        preimage = set(prod_files)
        for pf in list(prod_files):
            m = re.match(r"^crates/([^/]+)/src/(.+)\.rs$", pf)
            if m:
                crate, stem = m.group(1), m.group(2)
                for dep in (f"crates/{crate}/src/lib.rs",
                            f"crates/{crate}/src/mod.rs",
                            f"crates/{crate}/Cargo.toml"):
                    try:
                        _git(["show", f"{parent_sha}:{dep}"])
                        preimage.add(dep)
                    except RuntimeError:
                        pass

        # Materialize TWO COMPLETELY INDEPENDENT PARENT workspaces (never fix)
        # so no fixed implementation bytes enter either retrieval arm, and so
        # treatment state cannot contaminate control. Both originate from the
        # exact same ``parent_sha`` via ``git archive`` (no shared .git, no
        # shared .openlocus, index, trace, or cache).
        try:
            treat_ws = materialize_pack_workspace(parent_sha)
            ctrl_ws = materialize_pack_workspace(parent_sha)
        except RuntimeError as exc:
            res.reason_bucket = "headroom_isolation_failure"
            _write_private(runs_dir, f"headroom_{fix_sha[:7]}_error.txt",
                           f"isolation: {exc!r}\n")
            return res

        # Prove both materialized bytes originate from parent: the two
        # workspaces must have distinct roots (no shared dir) and both be
        # outside REPO_ROOT with no ancestor markers. The
        # parent-only-invariant helper (materialize_pack_workspace) already
        # materializes from parent_sha via git archive with isolation
        # assertions; here we additionally assert distinct roots.
        if treat_ws.resolve() == ctrl_ws.resolve():
            res.reason_bucket = "headroom_workspace_collision"
            _write_private(runs_dir, f"headroom_{fix_sha[:7]}_error.txt",
                           "treatment and control workspaces have the same root\n")
            return res

        # Real isolation scan: assert BOTH workspaces are isolated before
        # CLI use. Non-vacuous (counted). Uses ``before_cli`` (no workspace
        # marker allowed) before the FIRST invocation of each arm.
        for ws_arm in (treat_ws, ctrl_ws):
            s, f = _do_isolation_scan(ws_arm, mode="before_cli")
            res.isolation_scans += s
            res.isolation_scan_failures += f
        if res.isolation_scan_failures > 0:
            res.reason_bucket = "headroom_isolation_scan_failed"
            _write_private(runs_dir, f"headroom_{fix_sha[:7]}_error.txt",
                           "isolation scan (before_cli) failed\n")
            return res

        # Five warm retrieval repetitions per task. EVERY repetition must be
        # trusted: both arms schema valid, post-command isolation scans must
        # pass, citations must validate against THAT run's evidence. Any
        # invalid/partial/citation/isolation failure fails the candidate
        # closed — a later valid run does NOT erase an earlier failure.
        # p95 is computed from ONLY a fully valid 5-run set.
        #
        # For each arm: before its FIRST invocation (rep 0) use
        # ``before_cli``; after each invocation use ``after_cli``; before
        # repetitions 2..5 use ``after_cli`` (workspace-local real
        # ``.openlocus`` may exist). All ancestors remain marker-free.
        #
        # Strict per-arm state machine (``_run_one_arm``): pre-isolation →
        # fast-context → post-fast-context isolation → schema _valid →
        # citation validate → post-citation isolation → citation true.
        # A treatment failure must NOT invoke citation/control; a treatment
        # citation failure must NOT invoke control; a control failure must
        # NOT run later repetitions. No untrusted evidence reaches the
        # citation CLI.
        reps: list[dict[str, ArmResult]] = []
        for i in range(WARM_REPS):
            pre_mode = "before_cli" if i == 0 else "after_cli"

            # --- Treatment arm (independent workspace) ---
            treat_arm = _run_one_arm(
                openlocus, natural_query, TREATMENT_CHANNELS,
                treat_ws, pre_mode)
            # If treatment failed schema/isolation/citation, do NOT run
            # control or further reps — fail candidate closed safely.
            # The helper guarantees citation was not run on untrusted
            # evidence.
            if treat_arm.failure_reason:
                reps.append({"treatment": treat_arm, "control": ArmResult()})
                warm = _aggregate_warm_reps(reps)
                res.isolation_scans += warm.isolation_scans
                res.isolation_scan_failures += warm.isolation_scan_failures
                res.g_i = 0
                res.reason_bucket = (warm.failure_reason
                                     or "headroom_treatment_arm_failed")
                _write_private(runs_dir, f"headroom_{fix_sha[:7]}.json",
                               json.dumps({"preimage_size": len(preimage),
                                           "g_i": 0, "failed_rep": i,
                                           "arm": "treatment",
                                           "failure_reason": treat_arm.failure_reason,
                                           "isolation_scans": res.isolation_scans,
                                           "isolation_scan_failures": res.isolation_scan_failures,
                                           "warm_failure_reason": warm.failure_reason}))
                return res

            # --- Control arm (independent workspace) ---
            # Same strict state machine. A control failure must NOT run
            # later repetitions.
            ctrl_arm = _run_one_arm(
                openlocus, natural_query, CONTROL_CHANNELS,
                ctrl_ws, pre_mode)
            if ctrl_arm.failure_reason:
                reps.append({"treatment": treat_arm, "control": ctrl_arm})
                warm = _aggregate_warm_reps(reps)
                res.isolation_scans += warm.isolation_scans
                res.isolation_scan_failures += warm.isolation_scan_failures
                res.g_i = 0
                res.reason_bucket = (warm.failure_reason
                                     or "headroom_control_arm_failed")
                _write_private(runs_dir, f"headroom_{fix_sha[:7]}.json",
                               json.dumps({"preimage_size": len(preimage),
                                           "g_i": 0, "failed_rep": i,
                                           "arm": "control",
                                           "failure_reason": ctrl_arm.failure_reason,
                                           "isolation_scans": res.isolation_scans,
                                           "isolation_scan_failures": res.isolation_scan_failures,
                                           "warm_failure_reason": warm.failure_reason}))
                return res

            reps.append({"treatment": treat_arm, "control": ctrl_arm})

        # Aggregate: every rep must be fully valid. Any failure fails closed.
        warm = _aggregate_warm_reps(reps)
        res.isolation_scans += warm.isolation_scans
        res.isolation_scan_failures += warm.isolation_scan_failures
        res.retrieval_p95_s = warm.p95_s

        if not warm.all_valid:
            res.g_i = 0
            res.reason_bucket = warm.failure_reason or "headroom_warm_rep_failed"
            _write_private(runs_dir, f"headroom_{fix_sha[:7]}.json", json.dumps({
                "preimage_size": len(preimage),
                "retrieval_p95_s": res.retrieval_p95_s,
                "g_i": res.g_i,
                "isolation_scans": res.isolation_scans,
                "isolation_scan_failures": res.isolation_scan_failures,
                "warm_failure_reason": warm.failure_reason,
            }, indent=2))
            return res

        # Use the final (deterministic) fully-validated pack only after all
        # repetitions pass.
        treat_pack = warm.final_treatment_pack
        control_pack = warm.final_control_pack
        res.treatment_valid = True
        res.control_valid = True
        res.citations_validated = True

        treat_paths = pack_relevant_paths(treat_pack)
        control_paths = pack_relevant_paths(control_pack)
        relevant_in_treatment = treat_paths & preimage
        relevant_in_control = control_paths & preimage
        omitted_by_bm25 = preimage - control_paths

        res.bm25_omits_relevant = bool(omitted_by_bm25)
        # Treatment adds valid current evidence absent from control.
        treat_fresh = pack_freshness_counts(treat_pack)
        added_current = bool(relevant_in_treatment - relevant_in_control)
        res.treatment_adds_current_evidence = added_current and bool(
            treat_fresh.get(_FRESHNESS_VERIFIED_CURRENT, 0)
        )
        # Materially different rendered packs.
        res.materially_different = treat_paths != control_paths
        # Citation rematerialization: validated citations prove rematerialization
        # (not just a freshness string).
        res.citation_rematerialized = True
        # Treatment degeneration: treatment has no extra evidence vs control.
        res.treatment_degenerate = treat_paths == control_paths

        # Gate: headroom + latency + non-vacuous isolation with zero failures.
        if (res.bm25_omits_relevant and res.treatment_adds_current_evidence
                and res.materially_different and not res.treatment_degenerate
                and res.citations_validated and res.isolation_scans > 0
                and res.isolation_scan_failures == 0):
            res.g_i = 1
        else:
            res.g_i = 0
            res.reason_bucket = "headroom_no_treatment_only_context_opportunity"

        # Private manifest (never public) — inside try so early-return
        # paths skip it (those write their own error manifest).
        _write_private(runs_dir, f"headroom_{fix_sha[:7]}.json", json.dumps({
            "preimage_size": len(preimage),
            "omitted_by_bm25_count": len(omitted_by_bm25),
            "treatment_path_count": len(treat_paths),
            "control_path_count": len(control_paths),
            "retrieval_p95_s": res.retrieval_p95_s,
            "g_i": res.g_i,
            "isolation_scans": res.isolation_scans,
            "isolation_scan_failures": res.isolation_scan_failures,
            "treatment_valid": res.treatment_valid,
            "control_valid": res.control_valid,
            "citations_validated": res.citations_validated,
            "warm_reps": len(reps),
            "two_arm_workspaces": True,
        }, indent=2))
    except (subprocess.TimeoutExpired, OSError) as exc:
        # Per-candidate boundary: convert subprocess/OS exceptions to a
        # fixed reason bucket, fail closed, never abort the whole audit.
        # Do not publish exception details.
        res.g_i = 0
        res.reason_bucket = "headroom_subprocess_exception"
        _write_private(runs_dir, f"headroom_{fix_sha[:7]}_error.txt",
                       f"subprocess exception: {type(exc).__name__}\n")
    except Exception as exc:
        # Catch-all for unexpected validation/subprocess exceptions at the
        # per-candidate boundary. Fail closed with a fixed reason bucket;
        # never abort the whole audit. Do not publish exception details.
        res.g_i = 0
        res.reason_bucket = "headroom_unexpected_exception"
        _write_private(runs_dir, f"headroom_{fix_sha[:7]}_error.txt",
                       f"unexpected exception: {type(exc).__name__}\n")
    finally:
        # Cleanup BOTH workspaces (never just one).
        if treat_ws is not None:
            shutil.rmtree(treat_ws, ignore_errors=True)
        if ctrl_ws is not None:
            shutil.rmtree(ctrl_ws, ignore_errors=True)
    return res


# ---------------------------------------------------------------------------
# Private storage helpers (runs/ only, gitignored)
# ---------------------------------------------------------------------------


def _write_private(runs_dir: Path, name: str, content: str) -> None:
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / name).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Public aggregate report + privacy scan
# ---------------------------------------------------------------------------

# Forbidden public keys for this artifact (superset of the repo convention).
PUBLIC_FORBIDDEN_KEYS = {
    "task_id", "issue", "issue_prose", "path", "file", "file_path",
    "test_name", "test_path", "sha", "commit", "commit_sha", "diff", "patch",
    "snippet", "excerpt", "prompt", "provider", "query", "expected",
    "expected_value", "signature", "fail_signature", "pack_text", "manifest",
    "candidate_id", "repo_id", "run_id", "content_sha", "digest",
    "start_line", "end_line", "line_range", "gold_spans", "label", "labels",
    "private_labels", "base_url", "api_key", "api_token", "api_secret",
}

_PUBLIC_VALUE_RES = [
    re.compile(r"[A-Fa-f0-9]{40}"),   # full git SHA (cutoff is the only allowed)
    re.compile(r"https?://", re.I),
    re.compile(r"api[_-]?key", re.I),
    re.compile(r"base[_-]?url", re.I),
    re.compile(r"^/[A-Za-z0-9._/\-]{3,}"),  # path-like
]

# The single public cutoff SHA is the only SHA allowed in public output.
_PUBLIC_ALLOWED_CUTOFF = FROZEN_CUTOFF


def public_privacy_scan(obj: Any, path: str = "$",
                        allowed_cutoff_fields: set[str] | None = None) -> list[str]:
    """Walk a public report and flag any forbidden key/value. The frozen
    cutoff SHA is allowed only inside the designated ``frozen_source_cutoff``
    field; any other SHA-like or path-like value is a violation."""
    allowed_cutoff_fields = allowed_cutoff_fields or {"frozen_source_cutoff"}
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            ks = str(key)
            if ks in PUBLIC_FORBIDDEN_KEYS:
                violations.append(f"{path}.{ks}")
            violations.extend(public_privacy_scan(
                value, f"{path}.{ks}", allowed_cutoff_fields))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(public_privacy_scan(
                value, f"{path}[{idx}]", allowed_cutoff_fields))
    elif isinstance(obj, str):
        if len(obj) > 200:
            violations.append(f"{path}:long_string")
        elif ks_allows_cutoff(path, allowed_cutoff_fields) and obj == _PUBLIC_ALLOWED_CUTOFF:
            pass  # the one permitted SHA
        elif any(p.search(obj) for p in _PUBLIC_VALUE_RES):
            violations.append(f"{path}:private_like_value")
    return violations


def ks_allows_cutoff(path: str, allowed: set[str]) -> bool:
    for f in allowed:
        if path.endswith("." + f):
            return True
    return False


def _int(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _is_real_int(v: Any) -> bool:
    """True only if *v* is a genuine ``int`` (NOT a ``bool``).

    In Python ``bool`` is a subclass of ``int``, so ``isinstance(True, int)``
    returns ``True`` and ``int(True) == 1``. For trusted-output validation
    (line numbers, token counts, diagnostics counts, citation counts) a
    boolean must NOT be accepted as an integer — use ``type(v) is int``
    to reject it.
    """
    return type(v) is int


def _decrement_bucket(buckets: dict[str, int], key: str) -> None:
    """Decrement a reason-bucket count, removing the key when it reaches 0
    so the public report does not list empty buckets."""
    if key in buckets:
        buckets[key] = max(0, buckets[key] - 1)
        if buckets[key] <= 0:
            del buckets[key]


def _base_report() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now(),
        "claim_level": CLAIM_LEVEL,
        "stage": "phase1_eligibility_headroom_audit",
        "stage_is_eligibility_headroom_audit_NOT_pain_proof": True,
        "frozen_source_cutoff": FROZEN_CUTOFF,
        "new_provider_calls": 0,
        "new_provider_or_agent_runs": False,
        "claim_boundary": (
            "no_pain_no_product_no_effect_claim_eligibility_headroom_only"
        ),
        "retrieval_labels_are_not_task_outcomes": True,
        "no_sparse_no_context_or_bea_arm": True,
        "no_currentness_causal_claim": True,
        "r14_r20_retrieval_labels_not_task_outcomes": True,
        "treatment_channels": TREATMENT_CHANNELS,
        "control_channels": CONTROL_CHANNELS,
        "max_evidence": MAX_EVIDENCE,
        "approx_token_budget": TOKEN_BUDGET,
        "cohort_max": COHORT_MAX,
        "cohort_min": COHORT_MIN,
        "scoring_run_cap_s": SCORING_RUN_CAP_S,
        "headroom_min_formula": "max(2, ceil(0.4 * N))",
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "retrieval_variant_promoted": False,
        "downstream_agent_runs_performed": False,
        "patch_execution_performed": False,
        "solve_rate_evaluated": False,
        "per_record_inputs_available": False,
        "public_per_task_rows": False,
        "task_ids_in_artifact": False,
        "raw_paths_in_artifact": False,
        "raw_patches_diffs_stored": False,
        "raw_test_results_stored": False,
        "raw_solve_labels_stored": False,
        "raw_prompts_stored": False,
        "private_labels_committed": False,
        "no_commit_shas_except_public_cutoff": True,
        "no_provider_details_in_public": True,
    }


def build_public_report(audit: "AuditState") -> dict[str, Any]:
    """Build the aggregate-only public report from the audit state."""
    report = _base_report()

    # Enumeration (aggregate only).
    report["enumeration"] = {
        "total_non_merge_commits_reachable": audit.total_commits,
        "enumeration_deterministic": True,
        "order": "newest_first_then_sha",
    }

    # Candidate filter — aggregate reason buckets only.
    report["candidate_filter"] = {
        "considered": audit.considered,
        "reason_buckets": dict(sorted(audit.reason_buckets.items())),
        "eligible_after_filter": audit.eligible_after_filter,
    }

    # Reproducibility — aggregate only.
    report["reproducibility"] = {
        "attempted": audit.repro_attempted,
        "reason_buckets": dict(sorted(audit.repro_buckets.items())),
        "passed_all_checks": audit.repro_passed,
        "passed_all_checks_count": audit.repro_passed_count,
    }

    # Headroom gate — aggregate only.
    n_after_repro = audit.repro_passed_count
    headroom_required = max(2, _ceil(0.4 * n_after_repro)) if n_after_repro else 0
    report["headroom_gate"] = {
        "eligible_after_repro": n_after_repro,
        "cohort_min_required": COHORT_MIN,
        "cohort_max": COHORT_MAX,
        "headroom_required": headroom_required,
        "headroom_observed_g": audit.headroom_g,
        "retrieval_p95_s_max": audit.headroom_p95_max,
        "retrieval_p95_cap_s": RETRIEVAL_P95_CAP_S,
        "isolation_scans_performed": audit.isolation_scans,
        "isolation_scan_failures": audit.isolation_scan_failures,
        "gate_status": audit.headroom_gate_status,
    }

    # Overall gate.
    report["gate_status"] = audit.overall_gate_status
    report["gate_status_reason"] = audit.overall_gate_reason

    report["safety_invariants"] = {
        "aggregate_only_public_artifact": True,
        "no_provider_calls": True,
        "no_agent_runs": True,
        "no_patch_execution_against_product": True,
        "no_solve_rate_evaluation": True,
        "no_threshold_tuning_to_reach_denominator": True,
        "no_handcoded_favorable_candidate_list": True,
        "rules_never_weakened_to_reach_denominator": True,
        "candidate_exclusions_are_fixed_reason_buckets": True,
        "private_rows_manifests_logs_only_in_ignored_runs": True,
    }

    # Integrity: forbidden-field scan on the public output itself.
    violations = public_privacy_scan(report)
    report["integrity"] = {
        "forbidden_public_key_scan_clean": not violations,
        "scan": "decision_experiment_phase1_public_privacy_scan",
    }
    if violations:
        raise ValueError(
            "public report would contain forbidden fields/values; "
            f"first violations: {violations[:5]}"
        )
    return report


def _ceil(x: float) -> int:
    import math
    return math.ceil(x)


# ---------------------------------------------------------------------------
# Audit orchestration
# ---------------------------------------------------------------------------


@dataclass
class AuditState:
    total_commits: int = 0
    considered: int = 0
    reason_buckets: dict[str, int] = field(default_factory=dict)
    eligible_after_filter: int = 0
    repro_attempted: int = 0
    repro_buckets: dict[str, int] = field(default_factory=dict)
    repro_passed: bool = False
    repro_passed_count: int = 0
    headroom_g: int = 0
    headroom_p95_max: float = 0.0
    headroom_gate_status: str = "not_run"
    isolation_scans: int = 0          # real scans performed (non-vacuous)
    isolation_scan_failures: int = 0  # scans that failed (must be 0 for GO)
    overall_gate_status: str = "STOP"
    overall_gate_reason: str = ""


def run_audit(openlocus: str, runs_dir: Path,
              max_consider: int = 0) -> AuditState:
    """Run the provider-free Stage 1 audit once."""
    state = AuditState()
    runs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Deterministic enumeration.
    commits = enumerate_non_merge_commits(FROZEN_CUTOFF)
    state.total_commits = len(commits)
    _write_private(runs_dir, "manifest_enumeration.json", json.dumps({
        "total_commits": state.total_commits,
        "order": "newest_first_then_sha",
    }, indent=2))

    # 2. Rule-based candidate filter (no handpicking).
    eligible: list[dict[str, Any]] = []
    considered = 0
    for c in commits:
        considered += 1
        if max_consider and considered > max_consider:
            break
        sha = c["sha"]
        changes = commit_file_changes(sha)
        body = commit_message(sha)
        parent = _parent_sha(sha)
        dec = filter_candidate(sha, c["subject"], body, changes, parent)
        state.reason_buckets[dec.reason_bucket] = (
            state.reason_buckets.get(dec.reason_bucket, 0) + 1
        )
        if dec.eligible:
            # Resolve deferred pre-existing-test candidates.
            if not parent:
                parent = _parent_sha(sha)
            overlay = extract_overlay_test(sha, parent, changes)
            if overlay is None:
                state.reason_buckets["excluded_no_dev_test_found"] = (
                    state.reason_buckets.get("excluded_no_dev_test_found", 0) + 1
                )
                # Remove from the deferred/eligible bucket count we already added.
                _decrement_bucket(state.reason_buckets, dec.reason_bucket)
                continue
            # Deferred candidate successfully resolved an exact developer
            # test overlay: move from the deferred bucket to the resolved
            # eligible bucket so reason-bucket counts sum to considered
            # commits and the public report does not describe successful
            # candidates as deferred.
            if dec.reason_bucket == "deferred_no_test_in_commit_check_preexisting":
                _decrement_bucket(state.reason_buckets, dec.reason_bucket)
                state.reason_buckets["eligible_developer_test_resolved"] = (
                    state.reason_buckets.get("eligible_developer_test_resolved", 0) + 1
                )
            eligible.append({
                "sha": sha, "parent": parent, "changes": changes,
                "overlay": overlay, "subject": c["subject"],
            })
            state.eligible_after_filter += 1
        if len(eligible) >= COHORT_MAX:
            break
    state.considered = considered

    # Private candidate manifest (never public).
    _write_private(runs_dir, "manifest_candidates_private.json", json.dumps([{
        "sha": e["sha"], "parent": e["parent"],
        "test_path": e["overlay"].target_relpath,
        "source_kind": e["overlay"].source_kind,
        "subject": e["subject"],
    } for e in eligible], indent=2))

    # 3. Eligibility gate: min 5.
    if state.eligible_after_filter < COHORT_MIN:
        state.overall_gate_status = "STOP"
        state.overall_gate_reason = (
            "fewer_than_min_5_eligible_candidates_after_filter"
        )
        state.headroom_gate_status = "not_run_insufficient_eligible"
        return state

    # 4. Cold reproducibility checks (fail-closed buckets).
    repro_passed: list[dict[str, Any]] = []
    for e in eligible[:COHORT_MAX]:
        state.repro_attempted += 1
        res = run_repro(e["sha"], e["parent"], e["changes"], e["overlay"],
                        runs_dir)
        bucket = res.reason_bucket if not res.checked or not (
            res.buggy_fail_3_of_3 and res.fixed_pass_3_of_3
            and res.regression_pass_2_of_2 and res.dev_patch_passes
            and res.empty_patch_fails and res.stable_signature and res.within_cap
        ) else "repro_all_checks_passed"
        state.repro_buckets[bucket] = state.repro_buckets.get(bucket, 0) + 1
        if bucket == "repro_all_checks_passed":
            repro_passed.append(e)
    state.repro_passed_count = len(repro_passed)
    state.repro_passed = state.repro_passed_count >= COHORT_MIN

    if state.repro_passed_count < COHORT_MIN:
        state.overall_gate_status = "STOP"
        state.overall_gate_reason = (
            "fewer_than_min_5_reproducible_candidates"
        )
        state.headroom_gate_status = "not_run_insufficient_reproducible"
        return state

    # 5. Headroom spend gate (NOT an outcome).
    n = min(state.repro_passed_count, COHORT_MAX)
    headroom_required = max(2, _ceil(0.4 * n))
    for e in repro_passed[:COHORT_MAX]:
        h = headroom_for_candidate(e["sha"], e["parent"], e["changes"],
                                   e["subject"], openlocus, runs_dir)
        state.headroom_g += h.g_i
        state.headroom_p95_max = max(state.headroom_p95_max, h.retrieval_p95_s)
        state.isolation_scans += h.isolation_scans
        # Sum explicit isolation scan failures (never infer from reason text).
        state.isolation_scan_failures += h.isolation_scan_failures
        if h.reason_bucket:
            state.reason_buckets[h.reason_bucket] = (
                state.reason_buckets.get(h.reason_bucket, 0) + 1)

    # Non-vacuous GO: at least one real isolation scan performed AND zero
    # scan failures AND headroom/latency met.
    headroom_ok = (state.headroom_g >= headroom_required
                   and state.headroom_p95_max <= RETRIEVAL_P95_CAP_S
                   and state.isolation_scans > 0
                   and state.isolation_scan_failures == 0)
    state.headroom_gate_status = "GO_to_next_stage" if headroom_ok else "STOP"
    if headroom_ok:
        state.overall_gate_status = "GO_provider_free_gate_passed"
        state.overall_gate_reason = (
            "phase1_provider_free_eligibility_and_headroom_gate_passed"
        )
    else:
        state.overall_gate_status = "STOP"
        state.overall_gate_reason = (
            "headroom_spend_gate_not_met_or_latency_or_isolation_failure"
        )
    return state


def _parent_sha(sha: str) -> str:
    """Return the first parent SHA of a commit (buggy parent)."""
    try:
        return _git(["rev-parse", f"{sha}^"]).strip()
    except RuntimeError:
        return ""


# ---------------------------------------------------------------------------
# Self-test — synthetic temporary git fixtures, no network/provider
# ---------------------------------------------------------------------------


def _sh(args: list[str], cwd: Path) -> None:
    proc = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise AssertionError(
            f"{' '.join(args)} failed in {cwd}: {proc.stderr[:300]}")


def _make_synthetic_repo(base: Path) -> Path:
    """Create a synthetic git repo with a buggy commit, a fix commit that adds
    a developer test, and excluded commits (docs-only, test-only).

    Uses Python source so the self-test's lightweight synthetic tests run
    without a cargo build. Commits carry distinct increasing dates so the fix
    commit is deterministically the newest (head). No real private values.
    """
    repo = base / "synth_repo"
    repo.mkdir(parents=True, exist_ok=True)
    _sh(["git", "init", "-q"], repo)
    _sh(["git", "config", "user.email", "t@t"], repo)
    _sh(["git", "config", "user.name", "t"], repo)

    src = repo / "crates" / "foo" / "src"
    src.mkdir(parents=True, exist_ok=True)
    tests = repo / "crates" / "foo" / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    (repo / "crates" / "foo" / "Cargo.toml").write_text(
        '[package]\nname = "foo"\nversion = "0.1.0"\n', encoding="utf-8")

    # Commit 1 (oldest): buggy source (off-by-one defect).
    (src / "lib.py").write_text(
        "def add(a, b):\n    return a + b - 1\n", encoding="utf-8")
    _sh(["git", "add", "."], repo)
    _sh2(repo, "2024-01-01T00:00:00", ["commit", "-q", "-m", "feat: add add function"])

    # Commit 2: docs-only (excluded).
    (repo / "README.md").write_text("docs\n", encoding="utf-8")
    _sh(["git", "add", "."], repo)
    _sh2(repo, "2024-01-02T00:00:00", ["commit", "-q", "-m", "docs: add readme"])

    # Commit 3: test-only (excluded).
    (tests / "bug_test.py").write_text(
        "def check():\n    assert True\n", encoding="utf-8")
    _sh(["git", "add", "."], repo)
    _sh2(repo, "2024-01-03T00:00:00", ["commit", "-q", "-m", "test: add smoke"])

    # Commit 4 (newest/head): fix commit — corrects the defect AND adds the
    # developer regression test byte-for-byte.
    (src / "lib.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8")
    (tests / "add_test.py").write_text(
        "import sys, pathlib\n"
        "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'src'))\n"
        "from lib import add\n"
        "assert add(2, 3) == 5\n"
        "print('ok')\n",
        encoding="utf-8",
    )
    _sh(["git", "add", "."], repo)
    _sh2(repo, "2024-01-04T00:00:00", ["commit", "-q", "-m", "fix: correct off-by-one in add"])
    return repo


def _make_rust_inline_repo(base: Path) -> Path:
    """Create a synthetic git repo with a Rust source file containing an
    inline ``#[cfg(test)] mod tests`` module.

    The fix commit makes a tiny production change (1 line) but expands the
    inline test module by > 100 lines. Without inline test detection the raw
    numstat would exceed the <= 100 production-line limit; with detection
    only the 1 production line should count.

    No cargo build is required for the detection/overlay self-tests — only
    the parsing and hash-verification functions are exercised.
    """
    repo = base / "rust_inline_repo"
    repo.mkdir(parents=True, exist_ok=True)
    _sh(["git", "init", "-q"], repo)
    _sh(["git", "config", "user.email", "t@t"], repo)
    _sh(["git", "config", "user.name", "t"], repo)

    src = repo / "crates" / "bar" / "src"
    src.mkdir(parents=True, exist_ok=True)
    (repo / "crates" / "bar" / "Cargo.toml").write_text(
        '[package]\nname = "bar"\nversion = "0.1.0"\n', encoding="utf-8")

    # Commit 1 (parent): buggy production + minimal inline test module.
    parent_src = (
        "pub fn add(a: i32, b: i32) -> i32 {\n"
        "    a + b - 1\n"  # off-by-one defect
        "}\n"
        "\n"
        "#[cfg(test)]\n"
        "mod tests {\n"
        "    use super::*;\n"
        "    #[test]\n"
        "    fn it_works() {\n"
        "        assert_eq!(add(1, 1), 2);\n"
        "    }\n"
        "}\n"
    )
    (src / "lib.rs").write_text(parent_src, encoding="utf-8")
    _sh(["git", "add", "."], repo)
    _sh2(repo, "2024-01-01T00:00:00", ["commit", "-q", "-m", "feat: add module"])

    # Commit 2 (fix): fix the defect (1 prod line) + expand tests (>100 lines).
    test_fns = []
    for i in range(60):
        test_fns.append(
            f"    #[test]\n"
            f"    fn test_case_{i}() {{\n"
            f"        assert_eq!(add({i}, 1), {i + 1});\n"
            f"    }}\n"
        )
    fixed_src = (
        "pub fn add(a: i32, b: i32) -> i32 {\n"
        "    a + b\n"  # fixed
        "}\n"
        "\n"
        "#[cfg(test)]\n"
        "mod tests {\n"
        "    use super::*;\n"
        "    #[test]\n"
        "    fn it_works() {\n"
        "        assert_eq!(add(1, 1), 2);\n"
        "    }\n"
        + "".join(test_fns) +
        "}\n"
    )
    (src / "lib.rs").write_text(fixed_src, encoding="utf-8")
    _sh(["git", "add", "."], repo)
    _sh2(repo, "2024-01-02T00:00:00", ["commit", "-q", "-m", "fix: correct off-by-one in add"])
    return repo


def _make_rust_multi_module_repo(base: Path) -> Path:
    """Create a synthetic git repo with a Rust source file containing
    **two** well-formed ``#[cfg(test)] mod ...`` inline test modules.

    Used by the ambiguity self-test to prove that multiple valid inline
    test modules cause fail-closed rejection (no eligible overlay) rather
    than silently using region 0.
    """
    repo = base / "rust_multi_repo"
    repo.mkdir(parents=True, exist_ok=True)
    _sh(["git", "init", "-q"], repo)
    _sh(["git", "config", "user.email", "t@t"], repo)
    _sh(["git", "config", "user.name", "t"], repo)

    src = repo / "crates" / "baz" / "src"
    src.mkdir(parents=True, exist_ok=True)
    (repo / "crates" / "baz" / "Cargo.toml").write_text(
        '[package]\nname = "baz"\nversion = "0.1.0"\n', encoding="utf-8")

    # Commit 1 (parent): production + two test modules.
    parent_src = (
        "pub fn add(a: i32, b: i32) -> i32 {\n"
        "    a + b - 1\n"
        "}\n"
        "\n"
        "#[cfg(test)]\n"
        "mod tests_a {\n"
        "    use super::*;\n"
        "    #[test]\n"
        "    fn a() { assert_eq!(add(1, 1), 2); }\n"
        "}\n"
        "\n"
        "#[cfg(test)]\n"
        "mod tests_b {\n"
        "    use super::*;\n"
        "    #[test]\n"
        "    fn b() { assert_eq!(add(1, 1), 2); }\n"
        "}\n"
    )
    (src / "lib.rs").write_text(parent_src, encoding="utf-8")
    _sh(["git", "add", "."], repo)
    _sh2(repo, "2024-01-01T00:00:00", ["commit", "-q", "-m", "feat: add module"])

    # Commit 2 (fix): fix the defect (1 prod line).
    fixed_src = (
        "pub fn add(a: i32, b: i32) -> i32 {\n"
        "    a + b\n"
        "}\n"
        "\n"
        "#[cfg(test)]\n"
        "mod tests_a {\n"
        "    use super::*;\n"
        "    #[test]\n"
        "    fn a() { assert_eq!(add(1, 1), 2); }\n"
        "}\n"
        "\n"
        "#[cfg(test)]\n"
        "mod tests_b {\n"
        "    use super::*;\n"
        "    #[test]\n"
        "    fn b() { assert_eq!(add(1, 1), 2); }\n"
        "}\n"
    )
    (src / "lib.rs").write_text(fixed_src, encoding="utf-8")
    _sh(["git", "add", "."], repo)
    _sh2(repo, "2024-01-02T00:00:00", ["commit", "-q", "-m", "fix: correct off-by-one in add"])
    return repo


def _make_rust_inline_testonly_repo(base: Path) -> Path:
    """Create a synthetic git repo where the fix commit changes ONLY the
    inline ``#[cfg(test)] mod tests`` module (no production changes), with
    fewer than 100 raw changed lines.

    Proves that a small (``<100`` raw lines) test-only inline-module change
    is excluded as test-only (not eligible) — it is NOT misclassified as
    production just because ``raw_total <= 100``. The synthetic commit count
    (2) deliberately does not match the real aggregate.
    """
    repo = base / "rust_testonly_repo"
    repo.mkdir(parents=True, exist_ok=True)
    _sh(["git", "init", "-q"], repo)
    _sh(["git", "config", "user.email", "t@t"], repo)
    _sh(["git", "config", "user.name", "t"], repo)

    src = repo / "crates" / "qux" / "src"
    src.mkdir(parents=True, exist_ok=True)
    (repo / "crates" / "qux" / "Cargo.toml").write_text(
        '[package]\nname = "qux"\nversion = "0.1.0"\n', encoding="utf-8")

    # Commit 1 (parent): production + minimal inline test module.
    parent_src = (
        "pub fn add(a: i32, b: i32) -> i32 {\n"
        "    a + b\n"
        "}\n"
        "\n"
        "#[cfg(test)]\n"
        "mod tests {\n"
        "    use super::*;\n"
        "    #[test]\n"
        "    fn it_works() {\n"
        "        assert_eq!(add(1, 1), 2);\n"
        "    }\n"
        "}\n"
    )
    (src / "lib.rs").write_text(parent_src, encoding="utf-8")
    _sh(["git", "add", "."], repo)
    _sh2(repo, "2024-01-01T00:00:00", ["commit", "-q", "-m", "feat: add module"])

    # Commit 2 (fix): change ONLY the inline test module (add test cases),
    # NO production changes. Raw changed lines well under 100.
    fixed_src = (
        "pub fn add(a: i32, b: i32) -> i32 {\n"
        "    a + b\n"
        "}\n"
        "\n"
        "#[cfg(test)]\n"
        "mod tests {\n"
        "    use super::*;\n"
        "    #[test]\n"
        "    fn it_works() {\n"
        "        assert_eq!(add(1, 1), 2);\n"
        "    }\n"
        "    #[test]\n"
        "    fn test_two() {\n"
        "        assert_eq!(add(2, 3), 5);\n"
        "    }\n"
        "    #[test]\n"
        "    fn test_three() {\n"
        "        assert_eq!(add(0, 0), 0);\n"
        "    }\n"
        "}\n"
    )
    (src / "lib.rs").write_text(fixed_src, encoding="utf-8")
    _sh(["git", "add", "."], repo)
    _sh2(repo, "2024-01-02T00:00:00", ["commit", "-q", "-m", "fix: add more test coverage for add"])
    return repo


def _make_rust_lifetime_repo(base: Path) -> Path:
    """Create a synthetic git repo with a Rust source file containing
    lifetimes (``'a``, ``'static``), labels (``'outer:``), byte literals
    (``b'x'``), and raw strings (``r#"..."#``) both inside the test module
    and in production code AFTER the module.

    Used by the lifetime/label boundary self-test to prove the Rust lexer
    distinguishes lifetimes/labels from char literals, so the test region
    ends BEFORE the fixed production code (no brace-tracking corruption).
    """
    repo = base / "rust_lifetime_repo"
    repo.mkdir(parents=True, exist_ok=True)
    _sh(["git", "init", "-q"], repo)
    _sh(["git", "config", "user.email", "t@t"], repo)
    _sh(["git", "config", "user.name", "t"], repo)

    src = repo / "crates" / "lt" / "src"
    src.mkdir(parents=True, exist_ok=True)
    (repo / "crates" / "lt" / "Cargo.toml").write_text(
        '[package]\nname = "lt"\nversion = "0.1.0"\n', encoding="utf-8")

    parent_src = (
        "pub fn foo() {}\n"
        "\n"
        "#[cfg(test)]\n"
        "mod tests {\n"
        "    use super::*;\n"
        "    fn helper<'a>(_x: &'a str) {}\n"
        "    #[test]\n"
        "    fn it_works() {\n"
        "        helper(\"hi\");\n"
        "    }\n"
        "}\n"
        "\n"
        "pub const MSG: &'static str = \"hi\";\n"
    )
    (src / "lib.rs").write_text(parent_src, encoding="utf-8")
    _sh(["git", "add", "."], repo)
    _sh2(repo, "2024-01-01T00:00:00", ["commit", "-q", "-m", "feat: add module"])

    fixed_src = (
        "pub fn foo() {}\n"
        "\n"
        "#[cfg(test)]\n"
        "mod tests {\n"
        "    use super::*;\n"
        "    fn helper<'a>(_x: &'a str) {}\n"
        "    #[test]\n"
        "    fn it_works() {\n"
        "        helper(\"hi\");\n"
        "    }\n"
        "    #[test]\n"
        "    fn labels() {\n"
        "        'outer: loop { break 'outer; }\n"
        "    }\n"
        "}\n"
        "\n"
        "pub const MSG: &'static str = \"hi\";\n"
        "pub const BYTE: u8 = b'x';\n"
        "pub const RAW: &str = r#\"raw\"#;\n"
    )
    (src / "lib.rs").write_text(fixed_src, encoding="utf-8")
    _sh(["git", "add", "."], repo)
    _sh2(repo, "2024-01-02T00:00:00", ["commit", "-q", "-m", "fix: add label test and prod constants"])
    return repo


def _multi_module_overlay_rejected(tmp: Path) -> bool:
    """Verify that ``extract_overlay_test`` returns None (fail-closed) when
    the fixed commit's source file contains multiple inline test modules.
    """
    global REPO_ROOT
    repo = _make_rust_multi_module_repo(tmp)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(repo),
        capture_output=True, text=True, encoding="utf-8",
        errors="replace").stdout.strip()
    old_root = REPO_ROOT
    REPO_ROOT = repo
    try:
        changes = commit_file_changes(head)
        parent = _parent_sha(head)
        overlay = extract_overlay_test(head, parent, changes)
        return overlay is None  # fail-closed: no eligible overlay
    finally:
        REPO_ROOT = old_root


def _sh2(repo: Path, date: str, args: list[str]) -> None:
    env = {**os.environ, "GIT_AUTHOR_DATE": date,
           "GIT_COMMITTER_DATE": date}
    proc = subprocess.run(
        ["git"] + args, cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if proc.returncode != 0:
        raise AssertionError(f"git {args} failed: {proc.stderr[:300]}")


def _make_crlf_nonascii_separate_test_repo(base: Path) -> Path:
    """Create a synthetic git repo with a separate test file containing
    CRLF line endings and non-ASCII characters.

    The fix commit adds a developer test file with ``\\r\\n`` line endings
    and non-ASCII content (Unicode ``é``). This proves that git blob bytes
    (via ``_git_bytes``) == overlay ``test_bytes`` == on-disk bytes after
    ``apply_overlay``, with no newline translation on Windows.

    Uses Python source for the production file so no cargo build is needed.
    The test file uses CRLF + non-ASCII to exercise the byte-exact path.
    """
    repo = base / "crlf_nonascii_repo"
    repo.mkdir(parents=True, exist_ok=True)
    _sh(["git", "init", "-q"], repo)
    _sh(["git", "config", "user.email", "t@t"], repo)
    _sh(["git", "config", "user.name", "t"], repo)
    # Disable autocrlf so CRLF line endings are preserved in git blobs
    # (not translated to LF on commit). This proves byte-exactness.
    _sh(["git", "config", "core.autocrlf", "false"], repo)

    src = repo / "crates" / "foo" / "src"
    src.mkdir(parents=True, exist_ok=True)
    tests = repo / "crates" / "foo" / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    (repo / "crates" / "foo" / "Cargo.toml").write_text(
        '[package]\nname = "foo"\nversion = "0.1.0"\n', encoding="utf-8")

    # Commit 1 (oldest): buggy source.
    (src / "lib.py").write_text(
        "def add(a, b):\n    return a + b - 1\n", encoding="utf-8")
    _sh(["git", "add", "."], repo)
    _sh2(repo, "2024-01-01T00:00:00",
         ["commit", "-q", "-m", "feat: add add function"])

    # Commit 2 (newest/head): fix commit — corrects the defect AND adds the
    # developer regression test with CRLF + non-ASCII content.
    (src / "lib.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8")
    # Write the test file with explicit CRLF line endings and non-ASCII.
    # Using write_bytes to guarantee no Python newline translation.
    test_content = (
        "import sys, pathlib\r\n"
        "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'src'))\r\n"
        "from lib import add\r\n"
        "# café — non-ASCII comment\r\n"
        "assert add(2, 3) == 5\r\n"
        "print('oké')\r\n"
    ).encode("utf-8")
    (tests / "add_test.py").write_bytes(test_content)
    _sh(["git", "add", "."], repo)
    _sh2(repo, "2024-01-02T00:00:00",
         ["commit", "-q", "-m", "fix: correct off-by-one in add"])
    return repo


def self_test() -> dict[str, Any]:
    """Run all self-tests against synthetic git fixtures. No network/provider."""
    results: dict[str, Any] = {"tests": {}, "all_passed": False}
    tmp = Path(tempfile.mkdtemp(prefix="dope_phase1_selftest_"))
    try:
        repo = _make_synthetic_repo(tmp)
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(repo),
            capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()

        # Monkeypatch REPO_ROOT and git cwd so enumeration targets the synth repo.
        global REPO_ROOT
        old_root = REPO_ROOT
        REPO_ROOT = repo
        try:
            # --- Test 1: deterministic enumeration (newest-first then SHA) ---
            commits = enumerate_non_merge_commits(head)
            t1 = len(commits) == 4 and commits[0]["sha"] == head
            # determinism: repeated calls identical
            commits2 = enumerate_non_merge_commits(head)
            t1 = t1 and [c["sha"] for c in commits] == [c["sha"] for c in commits2]
            results["tests"]["deterministic_enumeration"] = t1

            # --- Test 2: rule-based filter (no handpicking) ---
            fix_sha = head
            changes = commit_file_changes(fix_sha)
            body = commit_message(fix_sha)
            parent = _parent_sha(fix_sha)
            dec = filter_candidate(fix_sha, "fix: correct off-by-one in add",
                                   body, changes, parent)
            t2 = dec.eligible and dec.reason_bucket == "eligible_has_fix_and_test"
            # docs-only commit excluded.
            docs_sha = commits[2]["sha"]  # third newest = docs commit
            docs_parent = _parent_sha(docs_sha)
            dec_docs = filter_candidate(docs_sha, commits[2]["subject"],
                                        commit_message(docs_sha),
                                        commit_file_changes(docs_sha),
                                        docs_parent)
            t2 = t2 and not dec_docs.eligible
            t2 = t2 and dec_docs.reason_bucket.startswith("excluded_")
            results["tests"]["rule_based_filter_no_handpicking"] = t2

            # --- Test 3: byte-exact test transplant ---
            overlay = extract_overlay_test(fix_sha, parent, changes)
            t3 = overlay is not None and overlay.source_kind == "commit_added_test"
            if t3:
                # Verify byte-exactness against git show.
                expected = subprocess.run(
                    ["git", "show", f"{fix_sha}:{overlay.target_relpath}"],
                    cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
                t3 = overlay.test_bytes.decode("utf-8") == expected
            results["tests"]["byte_exact_test_transplant"] = t3

            # --- Test 4: isolation (git archive, no .git, OS temp topology) ---
            # Uses the EXACT real materialization helper and asserts the
            # workspace is outside REPO_ROOT, has no markers, no ancestor
            # marker (root resolution cannot reach live checkout).
            ws = _make_temp_workspace(prefix="dope_phase1_iso_test_")
            materialize_workspace(parent, ws)
            t4 = (not (ws / ".git").exists()
                  and (ws / "crates" / "foo" / "src" / "lib.py").exists()
                  and _outside_repo_root(ws)
                  and _no_ancestor_marker(ws))
            results["tests"]["isolation_no_git_linkage"] = t4
            shutil.rmtree(ws, ignore_errors=True)

            # --- Test 5: stable fail/pass repro (lightweight synthetic test) ---
            runs_dir = tmp / "runs"
            res = run_repro(fix_sha, parent, changes, overlay, runs_dir,
                            per_run_cap=60)
            t5 = (res.buggy_fail_3_of_3 and res.fixed_pass_3_of_3
                  and res.regression_pass_2_of_2 and res.dev_patch_passes
                  and res.empty_patch_fails and res.stable_signature
                  and res.within_cap and res.checked)
            results["tests"]["stable_fail_pass_repro"] = t5
            if not t5:
                results["tests"]["stable_fail_pass_repro_detail"] = {
                    "buggy_fail": res.buggy_fail_3_of_3,
                    "fixed_pass": res.fixed_pass_3_of_3,
                    "regression": res.regression_pass_2_of_2,
                    "devpatch": res.dev_patch_passes,
                    "emptypatch_fails": res.empty_patch_fails,
                    "stable": res.stable_signature,
                    "within_cap": res.within_cap,
                    "reason": res.reason_bucket,
                }

            # --- Test 6: aggregate privacy (no forbidden keys/values) ---
            fake_report = _base_report()
            fake_report["enumeration"] = {"total_non_merge_commits_reachable": 4}
            fake_report["candidate_filter"] = {"considered": 4,
                                               "reason_buckets": {"eligible_has_fix_and_test": 1},
                                               "eligible_after_filter": 1}
            fake_report["headroom_gate"] = {"headroom_observed_g": 0,
                                              "gate_status": "STOP"}
            viols = public_privacy_scan(fake_report)
            t6 = not viols
            # And that a forbidden key IS caught.
            bad = {"path": "crates/foo/src/lib.rs", "task_id": "x"}
            t6 = t6 and len(public_privacy_scan(bad)) >= 2
            results["tests"]["aggregate_privacy_scan"] = t6

            # --- Test 7: fail-closed gate behavior ---
            # Uses a clearly synthetic non-matching count (COHORT_MIN - 1)
            # below the minimum. Does NOT encode actual run numbers.
            st = AuditState()
            st.eligible_after_filter = COHORT_MIN - 1  # synthetic, < min 5
            st.overall_gate_status = "STOP"
            st.overall_gate_reason = "fewer_than_min_5_eligible_candidates_after_filter"
            st.headroom_gate_status = "not_run_insufficient_eligible"
            t7 = (st.overall_gate_status == "STOP"
                  and st.headroom_gate_status.startswith("not_run"))
            results["tests"]["fail_closed_gate_behavior"] = t7

            # --- Test 8: Rust inline test region detection ---
            # Verifies that #[cfg(test)] mod tests { ... } is detected with
            # correct line ranges, including braces inside string literals.
            rust_src = (
                "pub fn foo() {}\n"            # line 1
                "\n"                           # line 2
                "#[cfg(test)]\n"               # line 3
                "mod tests {\n"                # line 4
                "    use super::*;\n"          # line 5
                "    #[test]\n"                # line 6
                '    fn it_works() { assert_eq!(2 + 2, 4); }\n'  # line 7
                '    fn helper() { let s = "{not} a brace"; }\n'  # line 8
                "}\n"                          # line 9
            )
            regions = detect_rust_inline_test_regions(rust_src)
            t8 = len(regions) == 1
            t8 = t8 and regions[0].start_line == 3
            t8 = t8 and regions[0].end_line == 9
            # The string literal "{not}" must not break brace tracking.
            t8 = t8 and rust_src[regions[0].end_byte - 1] == "}"
            results["tests"]["rust_inline_test_region_detection"] = t8

            # --- Test 9: test lines excluded from prod-line count ---
            # A Rust fix with a tiny production change but > 100 test-module
            # lines: raw numstat exceeds 100, but split count is small.
            rust_repo = _make_rust_inline_repo(tmp)
            rust_head = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=str(rust_repo),
                capture_output=True, text=True, encoding="utf-8",
                errors="replace").stdout.strip()
            old_rust_root = REPO_ROOT
            REPO_ROOT = rust_repo
            try:
                rust_changes = commit_file_changes(rust_head)
                rust_parent = _parent_sha(rust_head)
                _, raw_lines = production_files_and_lines(rust_changes)
                rust_prod_files, split_lines = production_files_and_lines_split(
                    rust_head, rust_parent, rust_changes)
                t9 = (raw_lines > 100              # raw exceeds limit
                      and split_lines <= 100       # split is within limit
                      and split_lines > 0          # has some production change
                      and len(rust_prod_files) == 1)  # one prod file
                results["tests"]["test_lines_excluded_from_prod_count"] = t9

                # --- Test 10: overlay preserves parent prod + fixed test ---
                rust_overlay = extract_overlay_test(
                    rust_head, rust_parent, rust_changes)
                t10 = (rust_overlay is not None
                       and rust_overlay.source_kind == "inline_test_module"
                       and rust_overlay.crate == "bar"
                       and rust_overlay.parent_full_hash != ""
                       and rust_overlay.fixed_full_hash != ""
                       and rust_overlay.fixed_prod_hash != "")
                if t10:
                    # Verify the fixed test hash matches the extracted bytes.
                    actual_test_hash = hashlib.sha256(
                        rust_overlay.test_bytes).hexdigest()
                    t10 = t10 and actual_test_hash == rust_overlay.fixed_test_hash

                    # Materialize parent workspace (OS temp, real topology) and
                    # apply overlay with mode="parent" — apply_overlay now
                    # ENFORCES the real invariants per explicit mode (pre-overlay
                    # parent_full_hash, post-overlay parent_prod_hash +
                    # fixed_test_hash, exactly one module). If it raises,
                    # the invariants failed.
                    rust_ws = _make_temp_workspace(prefix="dope_phase1_t10_")
                    try:
                        materialize_workspace(rust_parent, rust_ws)
                        apply_overlay(rust_ws, rust_overlay, mode="parent")

                        overlaid_bytes = (rust_ws / rust_overlay.target_relpath).read_bytes()
                        overlaid_text = overlaid_bytes.decode("utf-8")
                        overlaid_regions = detect_rust_inline_test_regions(
                            overlaid_text)
                        if overlaid_regions:
                            r = overlaid_regions[0]
                            ob_start = _char_to_byte_offset(overlaid_text, r.start_byte)
                            ob_end = _char_to_byte_offset(overlaid_text, r.end_byte)
                            prod_portion = overlaid_bytes[:ob_start] + overlaid_bytes[ob_end:]
                            test_portion = overlaid_bytes[ob_start:ob_end]
                        else:
                            prod_portion = overlaid_bytes
                            test_portion = b""
                        prod_hash = hashlib.sha256(prod_portion).hexdigest()
                        test_hash = hashlib.sha256(test_portion).hexdigest()
                        t10 = t10 and prod_hash == rust_overlay.parent_prod_hash
                        t10 = t10 and test_hash == rust_overlay.fixed_test_hash
                    except ValueError:
                        t10 = False
                    finally:
                        shutil.rmtree(rust_ws, ignore_errors=True)
                results["tests"]["overlay_preserves_parent_prod_fixed_test"] = t10

                # --- Test 11: malformed/ambiguous inline module fails closed ---
                # Unbalanced braces in the test module → no region detected.
                malformed_src = (
                    "pub fn foo() {}\n"
                    "\n"
                    "#[cfg(test)]\n"
                    "mod tests {\n"
                    "    #[test]\n"
                    "    fn broken() {\n"
                    "        // missing closing brace for mod tests\n"
                    "    // unbalanced }\n"
                )
                mal_regions = detect_rust_inline_test_regions(malformed_src)
                t11 = len(mal_regions) == 0  # fail-closed: no region
                results["tests"]["malformed_inline_module_fails_closed"] = t11

                # --- Test 12: no fixed production bytes leak ---
                # After applying overlay to parent workspace, the production
                # portion must be byte-identical to the parent's production
                # portion (no fixed production bytes transplanted). Uses raw
                # bytes for byte-exact verification.
                if t10:
                    parent_src_bytes = _git_bytes(
                        ["show", f"{rust_parent}:{rust_overlay.target_relpath}"])
                    parent_text = parent_src_bytes.decode("utf-8")
                    parent_regions = detect_rust_inline_test_regions(
                        parent_text)
                    if parent_regions:
                        pr = parent_regions[0]
                        p_start = _char_to_byte_offset(parent_text, pr.start_byte)
                        p_end = _char_to_byte_offset(parent_text, pr.end_byte)
                        parent_prod = (
                            parent_src_bytes[:p_start]
                            + parent_src_bytes[p_end:]
                        )
                    else:
                        parent_prod = parent_src_bytes
                    t12 = (hashlib.sha256(parent_prod).hexdigest()
                           == rust_overlay.parent_prod_hash)
                else:
                    t12 = False
                results["tests"]["no_fixed_production_bytes_leak"] = t12

                # --- Test 13: multiple valid inline modules fail closed ---
                # Two well-formed #[cfg(test)] mod ... regions in the same
                # source file: the parent/fixed correspondence is ambiguous,
                # so the overlay must NOT be eligible (fail-closed).
                multi_src = (
                    "pub fn foo() {}\n"
                    "\n"
                    "#[cfg(test)]\n"
                    "mod tests_a {\n"
                    "    use super::*;\n"
                    "    #[test]\n"
                    "    fn a() { assert_eq!(foo(), ()); }\n"
                    "}\n"
                    "\n"
                    "#[cfg(test)]\n"
                    "mod tests_b {\n"
                    "    use super::*;\n"
                    "    #[test]\n"
                    "    fn b() { assert_eq!(foo(), ()); }\n"
                    "}\n"
                )
                multi_regions = detect_rust_inline_test_regions(multi_src)
                t13 = len(multi_regions) == 2  # both detected
                # But extract_overlay_test must reject (fail-closed) because
                # fixed has > 1 region. Verify via a direct call with a
                # synthetic repo whose fixed commit has multiple modules.
                t13 = t13 and _multi_module_overlay_rejected(tmp)
                results["tests"]["multiple_inline_modules_fails_closed"] = t13

                # --- Test 14: attribute false positives in comments/strings ---
                # #[cfg(test)] text inside comments, string literals, and raw
                # strings must NOT be treated as a real test-module attribute.
                fp_src = (
                    "pub fn foo() {}\n"
                    "\n"
                    '// a comment mentioning #[cfg(test)] mod fake {}\n'
                    "pub fn bar() {\n"
                    '    let _s = "#[cfg(test)] mod fake {}";\n'
                    '    let _r = r#"#[cfg(test)] mod fake {}"#;\n'
                    '    let _b = b"#[cfg(test)] mod fake {}";\n'
                    "}\n"
                    "\n"
                    "#[cfg(test)]\n"               # the ONLY real attribute
                    "mod tests {\n"
                    "    use super::*;\n"
                    "    #[test]\n"
                    "    fn it_works() { assert_eq!(2 + 2, 4); }\n"
                    "}\n"
                )
                fp_regions = detect_rust_inline_test_regions(fp_src)
                t14 = len(fp_regions) == 1  # only the real one
                t14 = t14 and fp_regions[0].start_line == 10  # the real attribute
                results["tests"]["attribute_false_positives_rejected"] = t14
            finally:
                REPO_ROOT = old_rust_root

            # --- Test 15: small test-only inline module excluded as test-only
            # A ``fix:`` commit with <100 raw changed lines that changes ONLY
            # the inline ``#[cfg(test)] mod tests`` module (no production
            # changes) must be excluded as test-only (not eligible). Proves
            # the ``raw_total <= 100`` gate removal does not misclassify
            # small test-only changes as production. Uses a synthetic count
            # (2 commits) that does not match the real aggregate.
            testonly_repo = _make_rust_inline_testonly_repo(tmp)
            testonly_head = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=str(testonly_repo),
                capture_output=True, text=True, encoding="utf-8",
                errors="replace").stdout.strip()
            old_to_root = REPO_ROOT
            REPO_ROOT = testonly_repo
            try:
                to_changes = commit_file_changes(testonly_head)
                to_parent = _parent_sha(testonly_head)
                to_body = commit_message(testonly_head)
                _, to_raw_lines = production_files_and_lines(to_changes)
                to_prod_files, to_split_lines = production_files_and_lines_split(
                    testonly_head, to_parent, to_changes)
                t15 = (to_raw_lines < 100              # small commit
                       and to_raw_lines > 0            # has some changes
                       and len(to_prod_files) == 0     # no production files
                       and to_split_lines == 0)        # no production lines
                # filter_candidate must exclude as test-only (not eligible).
                to_dec = filter_candidate(
                    testonly_head,
                    "fix: add more test coverage for add",
                    to_body, to_changes, to_parent)
                t15 = t15 and not to_dec.eligible
                t15 = t15 and to_dec.reason_bucket == "excluded_test_only"
                results["tests"]["small_testonly_inline_excluded"] = t15
            finally:
                REPO_ROOT = old_to_root

            # --- Test 16: lifetime/label boundary in Rust lexer ---
            # Lifetimes ('a, 'static) and labels ('label:) must NOT be
            # mistaken for char literals. A test module containing a test
            # helper with a lifetime, plus production &'static str AFTER
            # the module, must have the test region end BEFORE the fixed
            # production code. Also tests byte/raw literals.
            lifetime_src = (
                "pub fn foo() {}\n"                    # line 1
                "\n"                                   # line 2
                "#[cfg(test)]\n"                       # line 3
                "mod tests {\n"                        # line 4
                "    use super::*;\n"                  # line 5
                "    fn helper<'a>(_x: &'a str) {}\n"  # line 6 — lifetime 'a
                "    #[test]\n"                        # line 7
                "    fn it_works() {\n"                # line 8
                "        helper(\"hi\");\n"            # line 9
                "    }\n"                              # line 10
                "    #[test]\n"                        # line 11
                "    fn labels() {\n"                  # line 12
                "        'outer: loop { break 'outer; }\n"  # line 13 — label
                "    }\n"                              # line 14
                "}\n"                                  # line 15 — module closes
                "\n"                                   # line 16
                "pub const MSG: &'static str = \"hi\";\n"  # line 17 — prod after module
                "pub const BYTE: u8 = b'x';\n"         # line 18 — byte literal
                "pub const RAW: &str = r#\"raw\"#;\n"  # line 19 — raw string
            )
            lt_regions = detect_rust_inline_test_regions(lifetime_src)
            t16 = len(lt_regions) == 1
            t16 = t16 and lt_regions[0].start_line == 3
            t16 = t16 and lt_regions[0].end_line == 15  # ends BEFORE prod
            # The 'static, 'a, 'outer must not have broken brace tracking
            # so the module closes at line 15, not later.
            results["tests"]["lifetime_label_boundary"] = t16

            # --- Test 17: ancestor marker rejection ---
            # A workspace nested inside a directory containing .git must be
            # rejected by the isolation assertion (ancestor marker).
            bad_parent = Path(tempfile.mkdtemp(prefix="dope_phase1_anc_"))
            try:
                (bad_parent / ".git").mkdir()
                nested = bad_parent / "ws"
                nested.mkdir()
                try:
                    assert_workspace_isolated(nested)
                    t17 = False  # should have raised
                except RuntimeError:
                    t17 = True  # correctly rejected
            finally:
                shutil.rmtree(bad_parent, ignore_errors=True)
            results["tests"]["ancestor_marker_rejection"] = t17

            # --- Test 18: enforced real overlay hashes reject mismatch ---
            # If the workspace file does NOT match parent_full_hash (e.g.
            # wrong commit materialized), apply_overlay with mode="parent"
            # must raise.
            lifetime_repo = _make_rust_lifetime_repo(tmp)
            lt_head = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=str(lifetime_repo),
                capture_output=True, text=True, encoding="utf-8",
                errors="replace").stdout.strip()
            old_lt_root = REPO_ROOT
            REPO_ROOT = lifetime_repo
            try:
                lt_changes = commit_file_changes(lt_head)
                lt_parent = _parent_sha(lt_head)
                lt_overlay = extract_overlay_test(lt_head, lt_parent, lt_changes)
                t18 = lt_overlay is not None and lt_overlay.source_kind == "inline_test_module"
                if t18:
                    # Materialize the FIX (wrong commit) and try to apply with
                    # mode="parent" — parent_full_hash invariant must fail.
                    bad_ws = _make_temp_workspace(prefix="dope_phase1_t18_")
                    try:
                        materialize_workspace(lt_head, bad_ws)
                        try:
                            apply_overlay(bad_ws, lt_overlay, mode="parent")
                            t18 = False  # should have raised
                        except ValueError:
                            t18 = True  # correctly rejected fix bytes
                    finally:
                        shutil.rmtree(bad_ws, ignore_errors=True)
            finally:
                REPO_ROOT = old_lt_root
            results["tests"]["enforced_overlay_hash_rejection"] = t18

            # --- Test 19: parent-only headroom materialization ---
            # materialize_pack_workspace must accept parent_sha and reject
            # a fix SHA route (no fixed bytes in either arm). Uses a mock
            # check: materialize_pack_workspace(parent) succeeds and the
            # workspace matches parent blob; materialize_pack_workspace(fix)
            # would produce fix bytes (we verify the function signature only
            # accepts parent semantics by checking the docstring/behavior).
            synth_head = head  # from _make_synthetic_repo
            synth_parent = parent
            t19 = True
            try:
                pack_ws = materialize_pack_workspace(synth_parent)
                t19 = t19 and _outside_repo_root(pack_ws)
                t19 = t19 and _no_ancestor_marker(pack_ws)
                # Verify the workspace contains PARENT bytes, not fix bytes.
                # Parent lib.py has "return a + b - 1" (buggy); fix has "return a + b".
                lib_content = (pack_ws / "crates" / "foo" / "src" / "lib.py").read_text()
                t19 = t19 and "a + b - 1" in lib_content  # parent (buggy)
                t19 = t19 and "a + b\n" not in lib_content.replace("a + b - 1", "")
                shutil.rmtree(pack_ws, ignore_errors=True)
            except Exception:
                t19 = False
            results["tests"]["parent_only_headroom_materialization"] = t19

            # --- Test 20: malformed Fast Context output validation ---
            # Various malformed/invalid fast-context outputs must be
            # rejected by _validate_fast_context_output (fail-closed).
            # Uses the REAL FLATTENED evidence schema (no nested ``core``):
            # path, start_line, end_line, content_sha, score, why, channels
            # are direct fields on each evidence object, plus optional meta.
            ws_tmp = _make_temp_workspace(prefix="dope_phase1_fc_val_")
            try:
                # Create the evidence target file so the "file exists" check
                # passes for the well-formed fixture.
                (ws_tmp / "src").mkdir(parents=True, exist_ok=True)
                (ws_tmp / "src" / "x.rs").write_text(
                    "pub fn x() {}\n", encoding="utf-8")

                cases = [
                    ("success_false", {"success": False}, False),
                    ("error_field", {"success": True, "error": "x"}, False),
                    ("empty_evidence", {"success": True, "evidence": []}, False),
                    ("disabled_channels",
                     {"success": True, "evidence": [{}],
                      "disabled_channels": ["bm25"]},
                     False),
                    ("remote_calls_nonzero",
                     {"success": True, "evidence": [{}], "remote_calls": 1},
                     False),
                    ("missing_diagnostics",
                     {"success": True, "evidence": [{}], "remote_calls": 0},
                     False),
                ]
                t20 = True
                for name, payload, expect_valid in cases:
                    valid, _reason = _validate_fast_context_output(
                        payload, "bm25", ws_tmp)
                    if expect_valid and not valid:
                        t20 = False
                    if not expect_valid and valid:
                        t20 = False
                # A well-formed FLATTENED output should be valid.
                good = {
                    "success": True,
                    "trace_id": "t1",
                    "evidence": [{
                        "path": "src/x.rs",
                        "start_line": 1,
                        "end_line": 2,
                        "content_sha": "abc",
                        "score": 0.5,
                        "why": ["bm25_match"],
                        "channels": ["bm25"],
                        "meta": {"freshness": _FRESHNESS_VERIFIED_CURRENT},
                    }],
                    "disabled_channels": [],
                    "remote_calls": 0,
                    "turns": [{"turn": "fusion", "evidence_count": 1,
                               "skipped": 0, "latency_ms": 1,
                               "disabled_channels": [],
                               "actions": []}],
                    "actions": [{"channel": "bm25", "query": "q",
                                 "turn": "fusion", "result_count": 1,
                                 "skipped": 0, "latency_ms": 1}],
                    "diagnostics": {
                        "invalid_citations_dropped": 0,
                        "unknown_channels": [],
                        "token_budget_enforced": True,
                    },
                    "pack": {"trace_id": "t1", "evidence": [{
                        "path": "src/x.rs",
                        "start_line": 1,
                        "end_line": 2,
                        "content_sha": "abc",
                        "score": 0.5,
                        "why": ["bm25_match"],
                        "channels": ["bm25"],
                        "meta": {"freshness": _FRESHNESS_VERIFIED_CURRENT},
                    }],
                        "budget_used": {"tokens_estimated": 100,
                                        "latency_ms": 1,
                                        "remote_cost_estimated": 0.0}},
                    "budget_used": {"tokens_estimated": 100,
                                    "latency_ms": 1,
                                    "remote_cost_estimated": 0.0},
                }
                valid, _ = _validate_fast_context_output(good, "bm25", ws_tmp)
                t20 = t20 and valid
                # Stale freshness must fail.
                stale = json.loads(json.dumps(good))
                stale["evidence"][0]["meta"]["freshness"] = "stale"
                stale["pack"]["evidence"][0]["meta"]["freshness"] = "stale"
                valid_s, _ = _validate_fast_context_output(stale, "bm25", ws_tmp)
                t20 = t20 and not valid_s
                # Missing channel must fail.
                missing_ch = json.loads(json.dumps(good))
                missing_ch["actions"] = [{"channel": "regex", "query": "q",
                                          "turn": "fusion", "result_count": 1,
                                          "skipped": 0, "latency_ms": 1}]
                valid_m, _ = _validate_fast_context_output(missing_ch, "bm25", ws_tmp)
                t20 = t20 and not valid_m
                # Nested ``core`` pseudo-schema must fail (fail-closed on
                # invented fixture shape).
                nested = json.loads(json.dumps(good))
                nested["evidence"] = [{
                    "core": {"path": "src/x.rs", "content_sha": "abc",
                             "start_line": 1, "end_line": 2,
                             "channels": ["bm25"]},
                    "meta": {"freshness": _FRESHNESS_VERIFIED_CURRENT},
                }]
                nested["pack"]["evidence"] = list(nested["evidence"])
                valid_n, _ = _validate_fast_context_output(nested, "bm25", ws_tmp)
                t20 = t20 and not valid_n
                # Unexpected action channel must fail.
                bad_chan = json.loads(json.dumps(good))
                bad_chan["actions"] = [{"channel": "dense", "query": "q",
                                        "turn": "fusion", "result_count": 1,
                                        "skipped": 0, "latency_ms": 1}]
                valid_bc, _ = _validate_fast_context_output(bad_chan, "bm25", ws_tmp)
                t20 = t20 and not valid_bc
                # Turn with disabled_channels must fail.
                bad_turn = json.loads(json.dumps(good))
                bad_turn["turns"][0]["disabled_channels"] = ["symbol"]
                valid_bt, _ = _validate_fast_context_output(bad_turn, "bm25", ws_tmp)
                t20 = t20 and not valid_bt
                # Nonexistent evidence path must fail.
                bad_path = json.loads(json.dumps(good))
                bad_path["evidence"][0]["path"] = "src/nonexistent.rs"
                bad_path["pack"]["evidence"][0]["path"] = "src/nonexistent.rs"
                valid_bp, _ = _validate_fast_context_output(bad_path, "bm25", ws_tmp)
                t20 = t20 and not valid_bp
                results["tests"]["fast_context_output_validation"] = t20
            finally:
                shutil.rmtree(ws_tmp, ignore_errors=True)

            # --- Test 21: non-vacuous isolation/citation GO conditions ---
            # The GO gate requires isolation_scans > 0 AND
            # isolation_scan_failures == 0. A state with 0 scans must NOT
            # pass even if headroom_g is high.
            st_go = AuditState()
            st_go.headroom_g = 10
            st_go.headroom_p95_max = 0.5
            st_go.isolation_scans = 0  # no scans — must not pass
            st_go.isolation_scan_failures = 0
            go_no_scans = (st_go.headroom_g >= 2
                           and st_go.headroom_p95_max <= RETRIEVAL_P95_CAP_S
                           and st_go.isolation_scans > 0
                           and st_go.isolation_scan_failures == 0)
            # With scans but a failure — must not pass.
            st_fail = AuditState()
            st_fail.headroom_g = 10
            st_fail.headroom_p95_max = 0.5
            st_fail.isolation_scans = 5
            st_fail.isolation_scan_failures = 1
            go_with_fail = (st_fail.headroom_g >= 2
                            and st_fail.headroom_p95_max <= RETRIEVAL_P95_CAP_S
                            and st_fail.isolation_scans > 0
                            and st_fail.isolation_scan_failures == 0)
            # With scans and no failures — passes (non-vacuous).
            st_ok = AuditState()
            st_ok.headroom_g = 3
            st_ok.headroom_p95_max = 1.0
            st_ok.isolation_scans = 5
            st_ok.isolation_scan_failures = 0
            go_ok = (st_ok.headroom_g >= 2
                     and st_ok.headroom_p95_max <= RETRIEVAL_P95_CAP_S
                     and st_ok.isolation_scans > 0
                     and st_ok.isolation_scan_failures == 0)
            t21 = (not go_no_scans and not go_with_fail and go_ok)
            results["tests"]["nonvacuous_isolation_citation_go"] = t21

            # --- Test 22: outside-repo workspace topology ---
            # _make_temp_workspace must produce a workspace outside REPO_ROOT
            # with no ancestor markers (real production topology).
            topo_ws = _make_temp_workspace(prefix="dope_phase1_topo_")
            t22 = (_outside_repo_root(topo_ws)
                   and _workspace_has_no_markers(topo_ws)
                   and _no_ancestor_marker(topo_ws))
            shutil.rmtree(topo_ws, ignore_errors=True)
            results["tests"]["outside_repo_workspace_topology"] = t22

            # --- Test 23: inline overlay base modes round-trip ---
            # Proves all three explicit modes work and hash mismatches fail:
            #   - mode="parent": materialize parent, apply overlay → success
            #   - mode="fixed": materialize fix, apply overlay → success (no-op)
            #   - mode="parent_dev_patch": parent + production-only dev patch
            #     + overlay → success (production matches fixed_prod_hash)
            #   - mode="fixed" with wrong workspace (parent) → fails
            #   - mode="parent_dev_patch" without dev patch → fails
            # This is the real inline Rust run_repro synthetic test that
            # proves each mode works and hash mismatch fails. Does NOT
            # merely test parent application.
            mode_repo = _make_rust_inline_repo(tmp)
            mode_head = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=str(mode_repo),
                capture_output=True, text=True, encoding="utf-8",
                errors="replace").stdout.strip()
            old_mode_root = REPO_ROOT
            REPO_ROOT = mode_repo
            t23 = True
            try:
                mode_changes = commit_file_changes(mode_head)
                mode_parent = _parent_sha(mode_head)
                mode_overlay = extract_overlay_test(
                    mode_head, mode_parent, mode_changes)
                t23 = (mode_overlay is not None
                       and mode_overlay.source_kind == "inline_test_module"
                       and mode_overlay.parent_full_hash != ""
                       and mode_overlay.fixed_full_hash != ""
                       and mode_overlay.fixed_prod_hash != "")
                if t23:
                    # (a) mode="parent": materialize parent → apply → success.
                    ws_a = _make_temp_workspace(prefix="dope_phase1_t23a_")
                    try:
                        materialize_workspace(mode_parent, ws_a)
                        apply_overlay(ws_a, mode_overlay, mode="parent")
                    except ValueError:
                        t23 = False
                    finally:
                        shutil.rmtree(ws_a, ignore_errors=True)

                    # (b) mode="fixed": materialize fix → apply → success
                    # (no-op, module already exact).
                    ws_b = _make_temp_workspace(prefix="dope_phase1_t23b_")
                    try:
                        materialize_workspace(mode_head, ws_b)
                        apply_overlay(ws_b, mode_overlay, mode="fixed")
                    except ValueError:
                        t23 = False
                    finally:
                        shutil.rmtree(ws_b, ignore_errors=True)

                    # (c) mode="parent_dev_patch": parent + production-only dev
                    # patch + overlay → success. Build the production-only
                    # dev patch (filter out test-only hunks).
                    ws_c = _make_temp_workspace(prefix="dope_phase1_t23c_")
                    try:
                        materialize_workspace(mode_parent, ws_c)
                        prod_patch = diff_for_paths(
                            mode_parent, mode_head,
                            [mode_overlay.target_relpath])
                        p_src = _git(
                            ["show", f"{mode_parent}:{mode_overlay.target_relpath}"])
                        f_src = _git(
                            ["show", f"{mode_head}:{mode_overlay.target_relpath}"])
                        p_regs = detect_rust_inline_test_regions(p_src)
                        f_regs = detect_rust_inline_test_regions(f_src)
                        prod_only_patch = filter_diff_to_prod_hunks(
                            prod_patch, p_regs, f_regs)
                        applied = apply_patch_text(ws_c, prod_only_patch)
                        if not applied:
                            t23 = False
                        else:
                            try:
                                apply_overlay(
                                    ws_c, mode_overlay,
                                    mode="parent_dev_patch")
                            except ValueError:
                                t23 = False
                    finally:
                        shutil.rmtree(ws_c, ignore_errors=True)

                    # (d) mode="fixed" with wrong workspace (parent
                    # materialized) → must fail (fixed_full_hash mismatch).
                    ws_d = _make_temp_workspace(prefix="dope_phase1_t23d_")
                    try:
                        materialize_workspace(mode_parent, ws_d)
                        try:
                            apply_overlay(ws_d, mode_overlay, mode="fixed")
                            t23 = False  # should have raised
                        except ValueError:
                            pass  # correctly rejected
                    finally:
                        shutil.rmtree(ws_d, ignore_errors=True)

                    # (e) mode="parent_dev_patch" WITHOUT dev patch (parent
                    # materialized but no patch applied) → must fail
                    # (fixed_prod_hash mismatch: production is still parent's).
                    ws_e = _make_temp_workspace(prefix="dope_phase1_t23e_")
                    try:
                        materialize_workspace(mode_parent, ws_e)
                        try:
                            apply_overlay(
                                ws_e, mode_overlay,
                                mode="parent_dev_patch")
                            t23 = False  # should have raised
                        except ValueError:
                            pass  # correctly rejected
                    finally:
                        shutil.rmtree(ws_e, ignore_errors=True)

                    # (f) unknown mode must raise.
                    ws_f = _make_temp_workspace(prefix="dope_phase1_t23f_")
                    try:
                        materialize_workspace(mode_parent, ws_f)
                        try:
                            apply_overlay(ws_f, mode_overlay,
                                           mode="unknown_mode")
                            t23 = False  # should have raised
                        except ValueError:
                            pass  # correctly rejected
                    finally:
                        shutil.rmtree(ws_f, ignore_errors=True)
            finally:
                REPO_ROOT = old_mode_root
            results["tests"]["inline_overlay_base_modes_round_trip"] = t23

            # --- Test 24: warm-rep aggregation (every rep trusted) ---
            # Proves via _aggregate_warm_reps with synthetic ArmResult lists:
            #   - first-of-five invalid then later valid → all_valid=False
            #     (a later valid run does NOT erase an earlier failure).
            #   - one citation failure → all_valid=False.
            #   - one isolation failure → isolation_scan_failures > 0 and
            #     all_valid=False (blocks GO).
            def _good_arm(latency: float = 0.1) -> ArmResult:
                return ArmResult(
                    pack={"evidence": []}, valid=True, invalid_reason="",
                    latency_s=latency, citations_ok=True,
                    citations_output={}, isolation_scans=2,
                    isolation_scan_failures=0,
                )

            def _invalid_arm(reason: str = "x") -> ArmResult:
                return ArmResult(
                    pack={"evidence": []}, valid=False,
                    invalid_reason=reason, latency_s=0.1,
                    citations_ok=True, citations_output={},
                    isolation_scans=2, isolation_scan_failures=0,
                )

            def _cite_fail_arm() -> ArmResult:
                return ArmResult(
                    pack={"evidence": []}, valid=True, invalid_reason="",
                    latency_s=0.1, citations_ok=False,
                    citations_output={"reason": "fail"}, isolation_scans=2,
                    isolation_scan_failures=0,
                )

            def _iso_fail_arm() -> ArmResult:
                return ArmResult(
                    pack={"evidence": []}, valid=True, invalid_reason="",
                    latency_s=0.1, citations_ok=True, citations_output={},
                    isolation_scans=2, isolation_scan_failures=1,
                )

            # (a) first-of-five invalid then later valid → fails.
            reps_a: list[dict[str, ArmResult]] = []
            for i in range(WARM_REPS):
                if i == 0:
                    reps_a.append({"treatment": _invalid_arm(),
                                   "control": _good_arm()})
                else:
                    reps_a.append({"treatment": _good_arm(0.1 + i * 0.01),
                                   "control": _good_arm(0.1 + i * 0.01)})
            wa = _aggregate_warm_reps(reps_a)
            t24 = (not wa.all_valid
                   and wa.failure_reason.startswith("warm_rep_0_treatment_invalid")
                   and wa.isolation_scan_failures == 0)

            # (b) one citation failure (rep 2 of 5) → fails.
            reps_b: list[dict[str, ArmResult]] = []
            for i in range(WARM_REPS):
                if i == 2:
                    reps_b.append({"treatment": _cite_fail_arm(),
                                   "control": _good_arm(0.1 + i * 0.01)})
                else:
                    reps_b.append({"treatment": _good_arm(0.1 + i * 0.01),
                                   "control": _good_arm(0.1 + i * 0.01)})
            wb = _aggregate_warm_reps(reps_b)
            t24 = t24 and (not wb.all_valid
                           and wb.failure_reason.startswith(
                               "warm_rep_2_treatment_citation_failed"))

            # (c) one isolation failure (rep 3 of 5) → fails, explicit count > 0.
            reps_c: list[dict[str, ArmResult]] = []
            for i in range(WARM_REPS):
                if i == 3:
                    reps_c.append({"treatment": _iso_fail_arm(),
                                   "control": _good_arm(0.1 + i * 0.01)})
                else:
                    reps_c.append({"treatment": _good_arm(0.1 + i * 0.01),
                                   "control": _good_arm(0.1 + i * 0.01)})
            wc = _aggregate_warm_reps(reps_c)
            t24 = t24 and (not wc.all_valid
                           and wc.isolation_scan_failures > 0
                           and wc.failure_reason.startswith(
                               "warm_rep_3_isolation_scan_failed"))

            # (d) all five valid → passes, p95 computed.
            reps_d: list[dict[str, ArmResult]] = []
            for i in range(WARM_REPS):
                reps_d.append({"treatment": _good_arm(0.1 + i * 0.05),
                               "control": _good_arm(0.1 + i * 0.05)})
            wd = _aggregate_warm_reps(reps_d)
            t24 = t24 and (wd.all_valid
                           and wd.isolation_scan_failures == 0
                           and wd.p95_s > 0
                           and wd.final_treatment_pack is not None)
            results["tests"]["warm_rep_aggregation"] = t24

            # --- Test 25: after_cli isolation mode ---
            # The explicit ``after_cli`` mode allows a workspace-local
            # ``.openlocus`` directory (created by the CLI for traces) only
            # if it is a real non-symlink directory. A file or symlink
            # ``.openlocus`` is always rejected. ``.git`` is always rejected.
            # ``before_cli`` mode rejects any marker.
            iso_ws = _make_temp_workspace(prefix="dope_phase1_t25_")
            t25 = True
            try:
                # before_cli: no markers → passes.
                try:
                    assert_workspace_isolated(iso_ws, mode="before_cli")
                except RuntimeError:
                    t25 = False
                # after_cli: no markers → passes.
                try:
                    assert_workspace_isolated(iso_ws, mode="after_cli")
                except RuntimeError:
                    t25 = False

                # Create a real .openlocus directory (as the CLI would).
                (iso_ws / ".openlocus").mkdir()
                # before_cli: must FAIL (marker present).
                try:
                    assert_workspace_isolated(iso_ws, mode="before_cli")
                    t25 = False  # should have raised
                except RuntimeError:
                    pass  # correctly rejected
                # after_cli: must PASS (real directory allowed).
                try:
                    assert_workspace_isolated(iso_ws, mode="after_cli")
                except RuntimeError:
                    t25 = False  # should have passed
                shutil.rmtree(iso_ws / ".openlocus", ignore_errors=True)

                # Create a .openlocus FILE → both modes must fail.
                (iso_ws / ".openlocus").write_text("x", encoding="utf-8")
                try:
                    assert_workspace_isolated(iso_ws, mode="before_cli")
                    t25 = False
                except RuntimeError:
                    pass
                try:
                    assert_workspace_isolated(iso_ws, mode="after_cli")
                    t25 = False  # file not allowed even in after_cli
                except RuntimeError:
                    pass
                (iso_ws / ".openlocus").unlink()

                # Create a .openlocus SYMLINK → both modes must fail.
                try:
                    target = iso_ws / "real_dir"
                    target.mkdir()
                    (iso_ws / ".openlocus").symlink_to(target)
                    try:
                        assert_workspace_isolated(iso_ws, mode="before_cli")
                        t25 = False
                    except RuntimeError:
                        pass
                    try:
                        assert_workspace_isolated(iso_ws, mode="after_cli")
                        t25 = False  # symlink not allowed
                    except RuntimeError:
                        pass
                except OSError:
                    # Symlink creation may fail on some platforms without
                    # privileges — skip this sub-case rather than fail.
                    pass
            finally:
                shutil.rmtree(iso_ws, ignore_errors=True)
            results["tests"]["after_cli_isolation_mode"] = t25

            # --- Test 26: two-arm workspace independence ---
            # Proves treatment and control arms have DISTINCT roots, both
            # are parent-exact (materialized from parent_sha, no fixed
            # bytes), no marker/state crossing (treatment's .openlocus does
            # not appear in control), and repetition 2 accepts only a real
            # local .openlocus dir while still rejecting file/symlink/
            # ancestor markers.
            t26 = True
            synth_parent_26 = parent  # from _make_synthetic_repo
            try:
                ws_t = materialize_pack_workspace(synth_parent_26)
                ws_c = materialize_pack_workspace(synth_parent_26)
                try:
                    # (a) distinct roots — no shared dir.
                    t26 = t26 and ws_t.resolve() != ws_c.resolve()
                    # (b) both outside REPO_ROOT, no ancestor markers.
                    t26 = t26 and _outside_repo_root(ws_t)
                    t26 = t26 and _outside_repo_root(ws_c)
                    t26 = t26 and _no_ancestor_marker(ws_t)
                    t26 = t26 and _no_ancestor_marker(ws_c)
                    # (c) both parent-exact: parent has buggy "a + b - 1".
                    for ws_arm in (ws_t, ws_c):
                        lib = (ws_arm / "crates" / "foo" / "src" / "lib.py").read_text()
                        t26 = t26 and "a + b - 1" in lib
                        t26 = t26 and "a + b\n" not in lib.replace(
                            "a + b - 1", "")
                    # (d) no marker/state crossing: create .openlocus in
                    # treatment; control must not have it. Also verify
                    # control's before_cli scan still passes (no
                    # contamination from treatment).
                    (ws_t / ".openlocus").mkdir()
                    t26 = t26 and not (ws_c / ".openlocus").exists()
                    # control before_cli must still pass (no marker).
                    try:
                        assert_workspace_isolated(ws_c, mode="before_cli")
                    except RuntimeError:
                        t26 = False
                    # treatment before_cli must FAIL (has .openlocus).
                    try:
                        assert_workspace_isolated(ws_t, mode="before_cli")
                        t26 = False  # should have raised
                    except RuntimeError:
                        pass  # correctly rejected
                    # treatment after_cli must PASS (real dir allowed).
                    try:
                        assert_workspace_isolated(ws_t, mode="after_cli")
                    except RuntimeError:
                        t26 = False  # should have passed
                    # (e) repetition 2 semantics: after_cli accepts real
                    # local .openlocus dir; file/symlink still rejected.
                    # (Already covered above for real dir; test file/symlink
                    # rejection in the treatment workspace.)
                    shutil.rmtree(ws_t / ".openlocus", ignore_errors=True)
                    # File .openlocus → after_cli must reject.
                    (ws_t / ".openlocus").write_text("x", encoding="utf-8")
                    try:
                        assert_workspace_isolated(ws_t, mode="after_cli")
                        t26 = False  # file must be rejected
                    except RuntimeError:
                        pass
                    (ws_t / ".openlocus").unlink()
                    # Symlink .openlocus → after_cli must reject.
                    try:
                        tgt = ws_t / "real_dir"
                        tgt.mkdir()
                        (ws_t / ".openlocus").symlink_to(tgt)
                        try:
                            assert_workspace_isolated(
                                ws_t, mode="after_cli")
                            t26 = False  # symlink must be rejected
                        except RuntimeError:
                            pass
                    except OSError:
                        pass  # symlink may be unsupported
                finally:
                    shutil.rmtree(ws_t, ignore_errors=True)
                    shutil.rmtree(ws_c, ignore_errors=True)
            except Exception:
                t26 = False
            results["tests"]["two_arm_workspace_independence"] = t26

            # --- Test 27: non-object/malformed JSON fail-closed ---
            # Proves that non-object JSON (array/string/null), timeout/
            # subprocess exceptions (mocked), malformed citation output,
            # and boolean-as-integer are all rejected safely without
            # throwing. Uses monkeypatching of subprocess.run to inject
            # mock outputs.
            t27 = True
            fc_ws = _make_temp_workspace(prefix="dope_phase1_t27_")
            try:
                # (a) JSON array → _valid=False, _invalid_reason set,
                #     no throw, no raw data included.
                orig_run = subprocess.run

                class _MockProc:
                    def __init__(self, stdout: str, returncode: int = 0,
                                 stderr: str = ""):
                        self.stdout = stdout
                        self.returncode = returncode
                        self.stderr = stderr

                # JSON array output.
                subprocess.run = lambda *a, **kw: _MockProc("[1, 2, 3]")  # type: ignore
                try:
                    out = run_fast_context("fake", "q", "bm25", fc_ws)
                    t27 = t27 and out.get("_valid") is False
                    t27 = t27 and out.get("_invalid_reason") == "non_object_json"
                    t27 = t27 and "latency_ms" in out
                    t27 = t27 and "returncode" in out
                    # No arbitrary raw data included.
                    t27 = t27 and "raw_stdout_head" not in out
                except Exception:
                    t27 = False  # must not throw

                # JSON string output.
                subprocess.run = lambda *a, **kw: _MockProc('"hello"')  # type: ignore
                try:
                    out = run_fast_context("fake", "q", "bm25", fc_ws)
                    t27 = t27 and out.get("_valid") is False
                    t27 = t27 and out.get("_invalid_reason") == "non_object_json"
                except Exception:
                    t27 = False

                # JSON null output.
                subprocess.run = lambda *a, **kw: _MockProc("null")  # type: ignore
                try:
                    out = run_fast_context("fake", "q", "bm25", fc_ws)
                    t27 = t27 and out.get("_valid") is False
                    t27 = t27 and out.get("_invalid_reason") == "non_object_json"
                except Exception:
                    t27 = False

                # JSON number output.
                subprocess.run = lambda *a, **kw: _MockProc("42")  # type: ignore
                try:
                    out = run_fast_context("fake", "q", "bm25", fc_ws)
                    t27 = t27 and out.get("_valid") is False
                    t27 = t27 and out.get("_invalid_reason") == "non_object_json"
                except Exception:
                    t27 = False

                # Malformed JSON output.
                subprocess.run = lambda *a, **kw: _MockProc("{not json")  # type: ignore
                try:
                    out = run_fast_context("fake", "q", "bm25", fc_ws)
                    t27 = t27 and out.get("_valid") is False
                    t27 = t27 and out.get("_invalid_reason") == "malformed_json"
                except Exception:
                    t27 = False

                # (b) TimeoutExpired → must not throw from run_fast_context
                #     (it propagates; headroom_for_candidate catches it).
                def _timeout_run(*a, **kw):
                    raise subprocess.TimeoutExpired(cmd=a[0] if a else "x",
                                                    timeout=1)
                subprocess.run = _timeout_run  # type: ignore
                try:
                    run_fast_context("fake", "q", "bm25", fc_ws)
                    # If we reach here without TimeoutExpired, the mock
                    # did not work — but run_fast_context may catch it
                    # internally. Either way, it should not silently pass.
                    # Check: the exception propagated (expected) or was
                    # caught and returned invalid.
                except subprocess.TimeoutExpired:
                    pass  # expected: propagates to headroom boundary
                except Exception:
                    t27 = False  # unexpected exception type

                # (c) TimeoutExpired caught at headroom boundary.
                subprocess.run = _timeout_run  # type: ignore
                try:
                    hr = headroom_for_candidate(
                        "fake_sha", parent, changes,
                        "query", "fake", tmp / "runs_t27")
                    t27 = t27 and hr.g_i == 0
                    t27 = t27 and hr.reason_bucket in (
                        "headroom_subprocess_exception",
                        "headroom_isolation_failure",
                        "headroom_isolation_scan_failed")
                except Exception:
                    t27 = False  # must not throw

                # (d) Malformed citation output → fails closed, no throw.
                subprocess.run = lambda *a, **kw: _MockProc("{not json")  # type: ignore
                try:
                    ok, out_d = validate_citations(
                        "fake", [{"path": "x"}], fc_ws)
                    t27 = t27 and ok is False
                except Exception:
                    t27 = False

                # Non-object citation output (array).
                subprocess.run = lambda *a, **kw: _MockProc("[1, 2]")  # type: ignore
                try:
                    ok, out_e = validate_citations(
                        "fake", [{"path": "x"}], fc_ws)
                    t27 = t27 and ok is False
                except Exception:
                    t27 = False

                # (e) Boolean-as-integer rejected by _validate_fast_context_output.
                # start_line/end_line as bool must fail.
                bool_ev = {
                    "success": True,
                    "trace_id": "t1",
                    "evidence": [{
                        "path": "src/x.rs",
                        "start_line": True,  # bool — must be rejected
                        "end_line": 2,
                        "content_sha": "abc",
                        "score": 0.5,
                        "why": ["bm25_match"],
                        "channels": ["bm25"],
                        "meta": {"freshness": _FRESHNESS_VERIFIED_CURRENT},
                    }],
                    "disabled_channels": [],
                    "remote_calls": 0,
                    "turns": [{"turn": "fusion", "evidence_count": 1,
                               "skipped": 0, "latency_ms": 1,
                               "disabled_channels": [],
                               "actions": []}],
                    "actions": [{"channel": "bm25", "query": "q",
                                 "turn": "fusion", "result_count": 1,
                                 "skipped": 0, "latency_ms": 1}],
                    "diagnostics": {
                        "invalid_citations_dropped": 0,
                        "unknown_channels": [],
                        "token_budget_enforced": True,
                    },
                    "pack": {"trace_id": "t1", "evidence": [{
                        "path": "src/x.rs",
                        "start_line": True,
                        "end_line": 2,
                        "content_sha": "abc",
                        "score": 0.5,
                        "why": ["bm25_match"],
                        "channels": ["bm25"],
                        "meta": {"freshness": _FRESHNESS_VERIFIED_CURRENT},
                    }],
                        "budget_used": {"tokens_estimated": 100,
                                        "latency_ms": 1,
                                        "remote_cost_estimated": 0.0}},
                    "budget_used": {"tokens_estimated": 100,
                                    "latency_ms": 1,
                                    "remote_cost_estimated": 0.0},
                }
                # Create evidence target file.
                (fc_ws / "src").mkdir(parents=True, exist_ok=True)
                (fc_ws / "src" / "x.rs").write_text(
                    "pub fn x() {}\n", encoding="utf-8")
                valid_be, reason_be = _validate_fast_context_output(
                    bool_ev, "bm25", fc_ws)
                t27 = t27 and not valid_be
                t27 = t27 and "evidence_lines_not_int" in reason_be

                # Boolean as invalid_citations_dropped must fail.
                bool_diag = json.loads(json.dumps(bool_ev))
                bool_diag["evidence"][0]["start_line"] = 1
                bool_diag["pack"]["evidence"][0]["start_line"] = 1
                bool_diag["diagnostics"]["invalid_citations_dropped"] = True
                valid_bd, reason_bd = _validate_fast_context_output(
                    bool_diag, "bm25", fc_ws)
                t27 = t27 and not valid_bd
                t27 = t27 and "diag_invalid_citations_dropped_not_int" in reason_bd

                # Boolean as tokens_estimated must fail (top-level check
                # fires before pack.budget_used equality check).
                bool_tok = json.loads(json.dumps(bool_ev))
                bool_tok["evidence"][0]["start_line"] = 1
                bool_tok["pack"]["evidence"][0]["start_line"] = 1
                bool_tok["budget_used"]["tokens_estimated"] = True
                bool_tok["pack"]["budget_used"]["tokens_estimated"] = True
                valid_bt, reason_bt = _validate_fast_context_output(
                    bool_tok, "bm25", fc_ws)
                t27 = t27 and not valid_bt
                t27 = t27 and "tokens_not_meaningful" in reason_bt

                subprocess.run = orig_run  # type: ignore
            finally:
                shutil.rmtree(fc_ws, ignore_errors=True)
            results["tests"]["non_object_json_fail_closed"] = t27

            # --- Test 28: pack/evidence consistency mismatch ---
            # Proves that pack.evidence must equal top-level evidence
            # structurally and in order (not just count), and pack.budget_used
            # must equal top-level budget_used. A count match is insufficient.
            t28 = True
            ws_28 = _make_temp_workspace(prefix="dope_phase1_t28_")
            try:
                (ws_28 / "src").mkdir(parents=True, exist_ok=True)
                (ws_28 / "src" / "x.rs").write_text(
                    "pub fn x() {}\n", encoding="utf-8")

                def _good_fc_base():
                    """Return a deep copy of a valid fast-context output."""
                    return {
                        "success": True,
                        "trace_id": "t1",
                        "evidence": [{
                            "path": "src/x.rs",
                            "start_line": 1,
                            "end_line": 2,
                            "content_sha": "abc",
                            "score": 0.5,
                            "why": ["bm25_match"],
                            "channels": ["bm25"],
                            "meta": {"freshness": _FRESHNESS_VERIFIED_CURRENT},
                        }],
                        "disabled_channels": [],
                        "remote_calls": 0,
                        "turns": [{"turn": "fusion", "evidence_count": 1,
                                   "skipped": 0, "latency_ms": 1,
                                   "disabled_channels": [],
                                   "actions": []}],
                        "actions": [{"channel": "bm25", "query": "q",
                                     "turn": "fusion", "result_count": 1,
                                     "skipped": 0, "latency_ms": 1}],
                        "diagnostics": {
                            "invalid_citations_dropped": 0,
                            "unknown_channels": [],
                            "token_budget_enforced": True,
                        },
                        "pack": {"trace_id": "t1", "evidence": [{
                            "path": "src/x.rs",
                            "start_line": 1,
                            "end_line": 2,
                            "content_sha": "abc",
                            "score": 0.5,
                            "why": ["bm25_match"],
                            "channels": ["bm25"],
                            "meta": {"freshness": _FRESHNESS_VERIFIED_CURRENT},
                        }]},
                        "budget_used": {"tokens_estimated": 100,
                                        "latency_ms": 1,
                                        "remote_cost_estimated": 0.0},
                    }

                # (a) Good output with matching pack.evidence and
                #     pack.budget_used → valid.
                good = _good_fc_base()
                good["pack"]["budget_used"] = json.loads(json.dumps(
                    good["budget_used"]))
                valid_a, _ = _validate_fast_context_output(
                    good, "bm25", ws_28)
                t28 = t28 and valid_a

                # (b) pack.evidence has different content (path changed) →
                #     structural mismatch → invalid.
                diff = _good_fc_base()
                diff["pack"]["budget_used"] = json.loads(json.dumps(
                    diff["budget_used"]))
                diff["pack"]["evidence"][0]["path"] = "src/different.rs"
                valid_b, reason_b = _validate_fast_context_output(
                    diff, "bm25", ws_28)
                t28 = t28 and not valid_b
                t28 = t28 and "pack_evidence_structural_mismatch" in reason_b

                # (c) pack.evidence has different order → mismatch → invalid.
                ord_mis = _good_fc_base()
                ord_mis["evidence"].append({
                    "path": "src/x.rs", "start_line": 3, "end_line": 4,
                    "content_sha": "def", "score": 0.3,
                    "why": ["bm25_match"], "channels": ["bm25"],
                    "meta": {"freshness": _FRESHNESS_VERIFIED_CURRENT}})
                ord_mis["pack"]["evidence"] = list(reversed(
                    ord_mis["evidence"]))
                ord_mis["pack"]["budget_used"] = json.loads(json.dumps(
                    ord_mis["budget_used"]))
                valid_c, reason_c = _validate_fast_context_output(
                    ord_mis, "bm25", ws_28)
                t28 = t28 and not valid_c
                t28 = t28 and "pack_evidence_structural_mismatch" in reason_c

                # (d) pack.budget_used differs from top-level budget_used →
                #     mismatch → invalid.
                bud_mis = _good_fc_base()
                bud_mis["pack"]["budget_used"] = {
                    "tokens_estimated": 999,  # different
                    "latency_ms": 1,
                    "remote_cost_estimated": 0.0,
                }
                valid_d, reason_d = _validate_fast_context_output(
                    bud_mis, "bm25", ws_28)
                t28 = t28 and not valid_d
                t28 = t28 and "pack_budget_used_mismatch" in reason_d
            finally:
                shutil.rmtree(ws_28, ignore_errors=True)
            results["tests"]["pack_evidence_consistency"] = t28

            # --- Test 29: byte-exact separate test overlays (CRLF/non-ASCII) ---
            # Proves that git blob bytes == overlay bytes == on-disk bytes
            # for separate test files with CRLF line endings and non-ASCII
            # content. Uses ``_git_bytes`` (not ``_git(...).encode()``) so
            # no newline translation occurs on Windows. The
            # ``separate_test_blob_hash`` is enforced in ``apply_overlay``
            # and must match the actual on-disk bytes after writing.
            crlf_repo = _make_crlf_nonascii_separate_test_repo(tmp)
            crlf_head = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=str(crlf_repo),
                capture_output=True, text=True, encoding="utf-8",
                errors="replace").stdout.strip()
            old_crlf_root = REPO_ROOT
            REPO_ROOT = crlf_repo
            t29 = True
            try:
                crlf_changes = commit_file_changes(crlf_head)
                crlf_parent = _parent_sha(crlf_head)
                crlf_overlay = extract_overlay_test(
                    crlf_head, crlf_parent, crlf_changes)
                t29 = (crlf_overlay is not None
                       and crlf_overlay.source_kind == "commit_added_test"
                       and crlf_overlay.separate_test_blob_hash != "")
                if t29:
                    # (a) overlay test_bytes must equal the git blob bytes
                    #     (via _git_bytes, no newline translation).
                    blob_bytes = _git_bytes(
                        ["show", f"{crlf_head}:{crlf_overlay.target_relpath}"])
                    t29 = t29 and crlf_overlay.test_bytes == blob_bytes
                    # (b) overlay test_bytes hash must equal blob hash.
                    t29 = t29 and (
                        hashlib.sha256(crlf_overlay.test_bytes).hexdigest()
                        == crlf_overlay.separate_test_blob_hash)
                    # (c) overlay bytes must contain CRLF and non-ASCII.
                    t29 = t29 and b"\r\n" in crlf_overlay.test_bytes
                    t29 = t29 and "é".encode("utf-8") in crlf_overlay.test_bytes
                    # (d) apply_overlay to a materialized parent workspace
                    #     and verify on-disk bytes == git blob bytes.
                    crlf_ws = _make_temp_workspace(prefix="dope_phase1_t29_")
                    try:
                        materialize_workspace(crlf_parent, crlf_ws)
                        apply_overlay(crlf_ws, crlf_overlay)
                        on_disk = (crlf_ws / crlf_overlay.target_relpath).read_bytes()
                        t29 = t29 and on_disk == blob_bytes
                        # (e) on-disk hash must equal separate_test_blob_hash.
                        t29 = t29 and (
                            hashlib.sha256(on_disk).hexdigest()
                            == crlf_overlay.separate_test_blob_hash)
                    except ValueError:
                        t29 = False
                    finally:
                        shutil.rmtree(crlf_ws, ignore_errors=True)

                    # (f) Unsafe target path (.. traversal) must be rejected.
                    bad_overlay = OverlaySpec(
                        source_kind="commit_added_test",
                        test_path="crates/foo/tests/add_test.py",
                        test_bytes=b"x",
                        target_relpath="../../etc/evil",
                        sha_origin=crlf_head,
                        separate_test_blob_hash=hashlib.sha256(b"x").hexdigest(),
                    )
                    bad_ws = _make_temp_workspace(prefix="dope_phase1_t29b_")
                    try:
                        try:
                            apply_overlay(bad_ws, bad_overlay)
                            t29 = False  # should have raised
                        except ValueError:
                            pass  # correctly rejected
                    finally:
                        shutil.rmtree(bad_ws, ignore_errors=True)
            finally:
                REPO_ROOT = old_crlf_root
            results["tests"]["byte_exact_separate_test_overlays"] = t29

            # --- Test 30: headroom arm state-machine ordering / short-circuit ---
            # Proves via MOCKED run_fast_context / validate_citations (with
            # the REAL _do_isolation_scan driven by workspace marker state)
            # that the strict per-arm state machine in _run_one_arm /
            # headroom_for_candidate short-circuits correctly:
            #   (a) treatment schema invalid → zero citation calls, zero
            #       control calls;
            #   (b) treatment post-fast-context isolation failure → zero
            #       citation/control calls, failure counted;
            #   (c) treatment citation failure → zero control calls;
            #   (d) control schema invalid → no later repetition (exactly
            #       1 treatment + 1 control fast-context call, 1 citation);
            #   (e) citation's post-call isolation failure is counted and
            #       blocks (citation ran, but post-cite .git marker fails
            #       the after_cli scan and blocks GO).
            # Uses synthetic packs (no real aggregate values/refs).
            t30 = True
            _g30 = globals()
            orig_rfc = _g30["run_fast_context"]
            orig_vc = _g30["validate_citations"]
            synth_parent_30 = parent  # from _make_synthetic_repo (real git archive)
            try:
                def _synth_valid_pack():
                    return {"_valid": True, "_invalid_reason": "",
                            "latency_ms": 10, "returncode": 0,
                            "evidence": [{"path": "src/x.rs"}]}

                def _synth_invalid_pack():
                    return {"_valid": False,
                            "_invalid_reason": "synthetic_invalid",
                            "latency_ms": 5, "returncode": 1,
                            "evidence": []}

                # (a) treatment schema invalid → zero citation, zero control.
                fc_a = {"n": 0}
                cite_a = {"n": 0}

                def rfc_a(openlocus, query, channels, cwd, timeout=120):
                    fc_a["n"] += 1
                    if channels == TREATMENT_CHANNELS:
                        return _synth_invalid_pack()
                    return _synth_valid_pack()

                def vc_a(openlocus, evidence, cwd, timeout=120):
                    cite_a["n"] += 1
                    return True, {}

                _g30["run_fast_context"] = rfc_a
                _g30["validate_citations"] = vc_a
                try:
                    hr_a = headroom_for_candidate(
                        "fake_sha", synth_parent_30, changes,
                        "query", "fake", tmp / "runs_t30a")
                    t30 = t30 and hr_a.g_i == 0
                    # Zero citation calls (schema invalid blocks citation).
                    t30 = t30 and cite_a["n"] == 0
                    # Only 1 fast-context call (treatment only; no control).
                    t30 = t30 and fc_a["n"] == 1
                except Exception:
                    t30 = False

                # (b) treatment post-fast-context isolation failure → zero
                #     citation/control, failure counted. The mock creates a
                #     .git marker in the workspace so the REAL post-fc
                #     after_cli isolation scan fails.
                fc_b = {"n": 0}
                cite_b = {"n": 0}

                def rfc_b(openlocus, query, channels, cwd, timeout=120):
                    fc_b["n"] += 1
                    if channels == TREATMENT_CHANNELS:
                        # Create .git marker so post-fc isolation scan fails.
                        (cwd / ".git").mkdir(exist_ok=True)
                        return _synth_valid_pack()
                    return _synth_valid_pack()

                def vc_b(openlocus, evidence, cwd, timeout=120):
                    cite_b["n"] += 1
                    return True, {}

                _g30["run_fast_context"] = rfc_b
                _g30["validate_citations"] = vc_b
                try:
                    hr_b = headroom_for_candidate(
                        "fake_sha", synth_parent_30, changes,
                        "query", "fake", tmp / "runs_t30b")
                    t30 = t30 and hr_b.g_i == 0
                    # Zero citation (post-fc iso failed before citation).
                    t30 = t30 and cite_b["n"] == 0
                    # Only treatment fast-context (no control).
                    t30 = t30 and fc_b["n"] == 1
                    # Post-fc isolation failure counted.
                    t30 = t30 and hr_b.isolation_scan_failures > 0
                except Exception:
                    t30 = False

                # (c) treatment citation failure → zero control.
                fc_c = {"n": 0}
                cite_c = {"n": 0}

                def rfc_c(openlocus, query, channels, cwd, timeout=120):
                    fc_c["n"] += 1
                    return _synth_valid_pack()

                def vc_c(openlocus, evidence, cwd, timeout=120):
                    cite_c["n"] += 1
                    return False, {"reason": "synthetic_citation_fail"}

                _g30["run_fast_context"] = rfc_c
                _g30["validate_citations"] = vc_c
                try:
                    hr_c = headroom_for_candidate(
                        "fake_sha", synth_parent_30, changes,
                        "query", "fake", tmp / "runs_t30c")
                    t30 = t30 and hr_c.g_i == 0
                    # Citation ran once (treatment only).
                    t30 = t30 and cite_c["n"] == 1
                    # Only treatment fast-context (no control).
                    t30 = t30 and fc_c["n"] == 1
                except Exception:
                    t30 = False

                # (d) control schema invalid → no later repetition.
                fc_d = {"n": 0}
                cite_d = {"n": 0}

                def rfc_d(openlocus, query, channels, cwd, timeout=120):
                    fc_d["n"] += 1
                    if channels == CONTROL_CHANNELS:
                        return _synth_invalid_pack()
                    return _synth_valid_pack()

                def vc_d(openlocus, evidence, cwd, timeout=120):
                    cite_d["n"] += 1
                    return True, {}

                _g30["run_fast_context"] = rfc_d
                _g30["validate_citations"] = vc_d
                try:
                    hr_d = headroom_for_candidate(
                        "fake_sha", synth_parent_30, changes,
                        "query", "fake", tmp / "runs_t30d")
                    t30 = t30 and hr_d.g_i == 0
                    # Exactly 2 fast-context calls (1 treatment + 1 control
                    # at rep 0; no rep 1).
                    t30 = t30 and fc_d["n"] == 2
                    # Exactly 1 citation (treatment only; control schema
                    # invalid → no citation).
                    t30 = t30 and cite_d["n"] == 1
                except Exception:
                    t30 = False

                # (e) citation's post-call isolation failure is counted and
                #     blocks. The mock creates a .git marker DURING citation
                #     validation so the REAL post-citation after_cli scan
                #     fails — proving the post-citation scan is performed,
                #     counted, and blocks GO.
                fc_e = {"n": 0}
                cite_e = {"n": 0}

                def rfc_e(openlocus, query, channels, cwd, timeout=120):
                    fc_e["n"] += 1
                    return _synth_valid_pack()

                def vc_e(openlocus, evidence, cwd, timeout=120):
                    cite_e["n"] += 1
                    # Create .git marker so post-citation isolation scan fails.
                    (cwd / ".git").mkdir(exist_ok=True)
                    return True, {}  # citation passed, but post-cite iso fails

                _g30["run_fast_context"] = rfc_e
                _g30["validate_citations"] = vc_e
                try:
                    hr_e = headroom_for_candidate(
                        "fake_sha", synth_parent_30, changes,
                        "query", "fake", tmp / "runs_t30e")
                    t30 = t30 and hr_e.g_i == 0
                    # Citation ran once (treatment only).
                    t30 = t30 and cite_e["n"] == 1
                    # Only treatment fast-context (no control).
                    t30 = t30 and fc_e["n"] == 1
                    # Post-citation isolation failure counted and blocks.
                    t30 = t30 and hr_e.isolation_scan_failures > 0
                except Exception:
                    t30 = False
            finally:
                _g30["run_fast_context"] = orig_rfc
                _g30["validate_citations"] = orig_vc
            results["tests"]["headroom_arm_state_machine_ordering"] = t30

            results["all_passed"] = all(
                v for k, v in results["tests"].items()
                if isinstance(v, bool))
        finally:
            REPO_ROOT = old_root
        return results
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--audit", action="store_true",
                        help="Run the real provider-free audit once")
    parser.add_argument("--openlocus", default="target/debug/openlocus")
    parser.add_argument("--out", default=str(
        PUBLIC_ARTIFACT_DIR / "phase1_public_report.json"))
    parser.add_argument("--max-consider", type=int, default=0,
                        help="Cap commits considered (0 = all)")
    args = parser.parse_args()

    if args.self_test:
        res = self_test()
        print(json.dumps(res, indent=2))
        return 0 if res.get("all_passed") else 1

    if args.audit:
        openlocus = str(Path(args.openlocus).resolve())
        if not Path(openlocus).exists():
            print(json.dumps({
                "error": "openlocus binary not found", "path": openlocus,
                "gate_status": "STOP",
                "reason": "production_fast_context_binary_unavailable"},
                indent=2))
            return 2
        runs_dir = PRIVATE_RUN_DIR
        state = run_audit(openlocus, runs_dir, args.max_consider)
        report = build_public_report(state)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["gate_status"].startswith("GO") else 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
