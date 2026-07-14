#!/usr/bin/env python3
"""Private B2 real-repository admission and frozen-corpus primitives.

This module is safe for the RUN phase: it contains repository locks and
adapter-visible tasks, but no oracle labels.  Actual repository identities,
queries, local paths, and per-file rows remain under ignored ``runs/``.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from product_bakeoff_contract import BakeoffTask, ContractError
from product_bakeoff_b2_protocol import (
    B2_LANGUAGES,
    B2_SIZE_BANDS,
    B2_SIZE_BAND_VISIBLE_BYTES,
    B2_TASK_COUNT,
    B2_VISIBLE_FILE_COUNT_RANGE,
    b2_source_bundle_digest,
    b2_spec_digest,
    execution_schedule_digest,
    build_task_slots,
    task_slot_digest,
)


B2_REPO_LOCK_SCHEMA = "product_bakeoff_b2_private_repo_lock.v1"
B2_TASK_MANIFEST_SCHEMA = "product_bakeoff_b2_private_task_manifest.v1"
B2_VISIBLE_MANIFEST_SCHEMA = "product_bakeoff_b2_visible_manifest.v1"
B2_FREEZE_RECEIPT_SCHEMA = "product_bakeoff_b2_private_freeze_receipt.v1"
B2_CORPUS_VERSION = "product_bakeoff_b2_corpus.v1"

_GITHUB_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_RE = re.compile(r"^[a-z0-9]+_[0-9a-f]{16,64}$")
_QUERY_PATH_HINT_RE = re.compile(
    r"(?:[/\\]|(?:^|\s)[A-Za-z]:|\.(?:rs|py|ts|tsx|js|jsx)(?:$|\s)|:\d)"
)

# Text source/config files that the production scanner can honestly index.
# Generated/vendor/build/cache trees are excluded before extension checks.
VISIBLE_EXTENSIONS = frozenset(
    {
        ".rs", ".py", ".pyi", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
        ".toml", ".json", ".jsonc", ".yaml", ".yml", ".ini", ".cfg",
        ".md", ".rst", ".txt", ".html", ".css", ".scss",
    }
)
PRIMARY_EXTENSIONS = {
    "rust": frozenset({".rs"}),
    "python": frozenset({".py", ".pyi"}),
    "typescript": frozenset({".ts", ".tsx"}),
}
EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git", ".hg", ".svn", ".openlocus", ".venv", "venv", "env",
        "node_modules", "target", "dist", "build", "out", "coverage",
        ".next", ".nuxt", ".cache", ".pytest_cache", ".mypy_cache",
        ".ruff_cache", ".tox", "__pycache__", "vendor", "third_party",
        "third-party", "generated", "gen", "fixtures", "snapshots",
    }
)
EXCLUDED_FILE_NAMES = frozenset(
    {
        "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb",
        "cargo.lock", "poetry.lock", "pdm.lock", "uv.lock",
    }
)
SECRET_SUFFIXES = frozenset(
    {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".crt", ".cer"}
)
MAX_VISIBLE_FILE_BYTES = 4 * 1024 * 1024


class B2CorpusError(ValueError):
    """Fail-closed B2 corpus/admission error."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def prefixed_digest(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical(value)).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def b2_runtime_bundle_digest(cli_path: str | Path) -> str:
    binary = Path(cli_path)
    if binary.is_symlink() or not binary.is_file() or _is_reparse_or_link(binary):
        raise B2CorpusError("OpenLocus executable is missing or unsafe")
    raw = binary.read_bytes()
    payload = {
        "source_bundle_digest": b2_source_bundle_digest(),
        "binary_sha256": hashlib.sha256(raw).hexdigest(),
        "binary_bytes": len(raw),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
    }
    return prefixed_digest("b2run_", payload)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise B2CorpusError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_pairs
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise B2CorpusError(f"cannot load JSON {path}: {type(exc).__name__}") from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _is_reparse_or_link(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        info = os.lstat(path)
    except (OSError, ValueError, RuntimeError):
        return True
    return bool((getattr(info, "st_file_attributes", 0) or 0) & 0x400)


def validate_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise B2CorpusError("relative path must be a non-empty <=512-char string")
    if "\\" in value or "\x00" in value or value.startswith("/"):
        raise B2CorpusError(f"unsafe relative path {value!r}")
    if re.match(r"^[A-Za-z]:", value):
        raise B2CorpusError(f"drive-qualified path rejected: {value!r}")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise B2CorpusError(f"non-canonical relative path {value!r}")
    return value


def _safe_file(root: Path, rel: str) -> Path:
    validate_relative_path(rel)
    root_resolved = root.resolve(strict=True)
    full = root / rel
    try:
        resolved = full.resolve(strict=True)
        resolved.relative_to(root_resolved)
    except (OSError, RuntimeError, ValueError) as exc:
        raise B2CorpusError(f"path {rel!r} escapes or is missing") from exc
    if _is_reparse_or_link(full):
        raise B2CorpusError(f"path {rel!r} is a link/reparse point")
    try:
        info = os.lstat(full)
    except OSError as exc:
        raise B2CorpusError(f"cannot stat {rel!r}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise B2CorpusError(f"path {rel!r} is not a regular file")
    return full


def _allowed_filename(name: str) -> bool:
    lower = name.casefold()
    suffix = Path(name).suffix.casefold()
    if lower.startswith(".env") or lower in EXCLUDED_FILE_NAMES:
        return False
    if suffix in SECRET_SUFFIXES or lower.endswith((".min.js", ".min.css", ".map")):
        return False
    if lower.endswith((".snap", ".snapshot", ".generated.ts", ".generated.py")):
        return False
    return suffix in VISIBLE_EXTENSIONS


@dataclass(frozen=True)
class B2FileRecord:
    path: str
    bytes: int
    line_count: int
    sha256: str
    extension: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "bytes": self.bytes,
            "line_count": self.line_count,
            "sha256": self.sha256,
            "extension": self.extension,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "B2FileRecord":
        if set(raw) != {"path", "bytes", "line_count", "sha256", "extension"}:
            raise B2CorpusError("file record has non-closed shape")
        path = validate_relative_path(raw["path"])
        byte_count = raw["bytes"]
        line_count = raw["line_count"]
        sha = raw["sha256"]
        ext = raw["extension"]
        if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count < 0:
            raise B2CorpusError("file bytes must be nonnegative int")
        if not isinstance(line_count, int) or isinstance(line_count, bool) or line_count < 1:
            raise B2CorpusError("line_count must be positive int")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise B2CorpusError("file sha256 malformed")
        if not isinstance(ext, str) or ext != Path(path).suffix.casefold():
            raise B2CorpusError("file extension binding mismatch")
        return cls(path, byte_count, line_count, sha, ext)


@dataclass(frozen=True)
class B2PublicTask:
    slot_id: str
    task_slug: str
    repo_slot: str
    language: str
    size_band: str
    role: str
    task_family: str
    interaction_mode: str
    query: str
    operation: str = "context"

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "task_slug": self.task_slug,
            "repo_slot": self.repo_slot,
            "language": self.language,
            "size_band": self.size_band,
            "role": self.role,
            "task_family": self.task_family,
            "interaction_mode": self.interaction_mode,
            "query": self.query,
            "operation": self.operation,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "B2PublicTask":
        expected = {
            "slot_id", "task_slug", "repo_slot", "language", "size_band", "role",
            "task_family", "interaction_mode", "query", "operation",
        }
        if set(raw) != expected:
            raise B2CorpusError("task row has non-closed shape")
        task = cls(**{key: raw[key] for key in expected})
        task.validate()
        return task

    def validate(self) -> "B2PublicTask":
        slots = {slot.slot_id: slot for slot in build_task_slots()}
        slot = slots.get(self.slot_id)
        if slot is None:
            raise B2CorpusError(f"unknown task slot {self.slot_id!r}")
        expected = (
            slot.repo_slot, slot.language, slot.size_band, slot.role,
            slot.task_family, slot.interaction_mode,
        )
        observed = (
            self.repo_slot, self.language, self.size_band, self.role,
            self.task_family, self.interaction_mode,
        )
        if observed != expected:
            raise B2CorpusError(f"task slot binding mismatch for {self.slot_id}")
        if not re.fullmatch(r"b2_t[0-9]{2}_[0-9a-f]{12}", self.task_slug):
            raise B2CorpusError("task_slug must be opaque and digest-bound")
        if not isinstance(self.query, str) or not 1 <= len(self.query) <= 512:
            raise B2CorpusError("query must contain 1..512 characters")
        if _QUERY_PATH_HINT_RE.search(self.query):
            raise B2CorpusError("query contains a path/extension/line hint")
        if any(ord(char) < 32 for char in self.query):
            raise B2CorpusError("query contains control characters")
        if self.operation != "context":
            raise B2CorpusError("frozen B2 task rows must begin with context")
        self.to_bakeoff_task()
        return self

    def to_bakeoff_task(self, operation: str | None = None) -> BakeoffTask:
        op = operation or self.operation
        interaction = "two_step" if op == "support" else self.interaction_mode
        return BakeoffTask(
            task_slug=self.task_slug,
            language_family=self.language,
            task_family=self.task_family,
            interaction_mode=interaction,
            source_visibility="frozen_visible",
            query=self.query,
            operation=op,
        ).validate()


def scan_repository(root: Path) -> tuple[B2FileRecord, ...]:
    """Enumerate an admission-safe UTF-8 text corpus without silent skips."""
    root = root.resolve(strict=True)
    if not root.is_dir() or _is_reparse_or_link(root):
        raise B2CorpusError("candidate root must be a real non-link directory")
    records: list[B2FileRecord] = []

    def on_error(error: OSError) -> None:
        raise B2CorpusError(f"repository walk failed at {error.filename!r}") from error

    for dirpath, dirnames, filenames in os.walk(
        root, topdown=True, followlinks=False, onerror=on_error
    ):
        directory = Path(dirpath)
        kept: list[str] = []
        for name in sorted(dirnames):
            child = directory / name
            lower = name.casefold()
            if lower in EXCLUDED_DIR_NAMES or (name.startswith(".") and name != ".github"):
                continue
            if _is_reparse_or_link(child):
                raise B2CorpusError(f"link/reparse directory rejected: {child}")
            kept.append(name)
        dirnames[:] = kept
        for name in sorted(filenames):
            if not _allowed_filename(name):
                continue
            full = directory / name
            if _is_reparse_or_link(full):
                raise B2CorpusError(f"link/reparse file rejected: {full}")
            try:
                info_before = os.lstat(full)
            except OSError as exc:
                raise B2CorpusError(f"cannot stat candidate file {full}") from exc
            if not stat.S_ISREG(info_before.st_mode):
                raise B2CorpusError(f"special candidate file rejected: {full}")
            if info_before.st_size > MAX_VISIBLE_FILE_BYTES:
                continue
            try:
                raw = full.read_bytes()
                raw.decode("utf-8", errors="strict")
                info_after = os.lstat(full)
            except (OSError, UnicodeError) as exc:
                if isinstance(exc, UnicodeError):
                    continue
                raise B2CorpusError(f"cannot read candidate file {full}") from exc
            before_id = (
                info_before.st_dev, info_before.st_ino, info_before.st_mode,
                info_before.st_size,
            )
            after_id = (
                info_after.st_dev, info_after.st_ino, info_after.st_mode,
                info_after.st_size,
            )
            if before_id != after_id or b"\x00" in raw[:8192]:
                if before_id != after_id:
                    raise B2CorpusError(f"candidate file changed during read: {full}")
                continue
            rel = full.relative_to(root).as_posix()
            validate_relative_path(rel)
            records.append(
                B2FileRecord(
                    path=rel,
                    bytes=len(raw),
                    line_count=raw.count(b"\n") + 1,
                    sha256=hashlib.sha256(raw).hexdigest(),
                    extension=full.suffix.casefold(),
                )
            )
    records.sort(key=lambda row: row.path)
    if len({row.path for row in records}) != len(records):
        raise B2CorpusError("duplicate scanned path")
    return tuple(records)


def _run_git(args: Sequence[str], *, cwd: Path | None = None) -> str:
    try:
        completed = subprocess.run(
            ["git", "-c", "core.longpaths=true", *args],
            cwd=cwd, capture_output=True, text=True,
            timeout=1800, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise B2CorpusError(f"git command failed to launch: {type(exc).__name__}") from exc
    if completed.returncode != 0:
        raise B2CorpusError(
            f"git {' '.join(args[:2])} failed with returncode {completed.returncode}"
        )
    return completed.stdout.strip()


def clone_public_repo(repo: str, destination: Path) -> Path:
    if not isinstance(repo, str) or not _GITHUB_REPO_RE.fullmatch(repo):
        raise B2CorpusError(f"invalid GitHub repository slug {repo!r}")
    destination = destination.resolve(strict=False)
    if destination.exists():
        if not (destination / ".git").is_dir() or _is_reparse_or_link(destination):
            raise B2CorpusError("existing clone destination is not a safe git checkout")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    _run_git(
        [
            "clone", "--filter=blob:none", "--depth=1", "--no-recurse-submodules",
            f"https://github.com/{repo}.git", str(destination),
        ]
    )
    if not destination.is_dir() or _is_reparse_or_link(destination):
        raise B2CorpusError("clone did not produce a safe directory")
    return destination


def git_commit(root: Path) -> str:
    commit = _run_git(["rev-parse", "HEAD"], cwd=root)
    if not _COMMIT_RE.fullmatch(commit):
        raise B2CorpusError("git HEAD is not a full SHA-1 commit id")
    return commit


def require_git_worktree_clean(root: Path) -> None:
    if _run_git(["status", "--porcelain=v1", "--untracked-files=no"], cwd=root):
        raise B2CorpusError("candidate checkout has tracked modifications")


def visible_manifest_digest(files: Sequence[B2FileRecord]) -> str:
    return prefixed_digest("b2vis_", [row.to_dict() for row in files])


def validate_visible_band(
    language: str, size_band: str, files: Sequence[B2FileRecord]
) -> None:
    if language not in B2_LANGUAGES or size_band not in B2_SIZE_BANDS:
        raise B2CorpusError("unknown language/size band")
    count = len(files)
    total = sum(row.bytes for row in files)
    low_count, high_count = B2_VISIBLE_FILE_COUNT_RANGE
    low_bytes, high_bytes = B2_SIZE_BAND_VISIBLE_BYTES[size_band]
    if not low_count <= count <= high_count:
        raise B2CorpusError(
            f"visible file count {count} outside [{low_count},{high_count}]"
        )
    if not low_bytes <= total < high_bytes:
        raise B2CorpusError(
            f"visible bytes {total} outside [{low_bytes},{high_bytes}) for {size_band}"
        )
    primary = PRIMARY_EXTENSIONS[language]
    primary_rows = [row for row in files if row.extension in primary]
    if len(primary_rows) < 16:
        raise B2CorpusError("visible snapshot has fewer than 16 primary-language files")
    if sum(row.bytes for row in primary_rows) < min(128 * 1024, total // 10):
        raise B2CorpusError("primary-language material is too small for its stratum")


def repo_lock_identity_payload(lock: Mapping[str, Any]) -> dict[str, Any]:
    payload = json.loads(json.dumps(lock))
    payload.pop("repo_lock_digest", None)
    for repo in payload.get("repos", []):
        source = repo.get("source", {})
        source.pop("clone_root", None)
    return payload


def compute_repo_lock_digest(lock: Mapping[str, Any]) -> str:
    return prefixed_digest("b2repos_", repo_lock_identity_payload(lock))


def validate_repo_lock(lock: Any, *, require_sources: bool = False) -> dict[str, Any]:
    if not isinstance(lock, dict):
        raise B2CorpusError("repo lock must be an object")
    if set(lock) != {
        "schema_version", "corpus_version", "protocol_spec_digest",
        "task_slot_digest", "repo_lock_digest", "repos",
    }:
        raise B2CorpusError("repo lock has non-closed top-level shape")
    if lock["schema_version"] != B2_REPO_LOCK_SCHEMA:
        raise B2CorpusError("repo lock schema mismatch")
    if lock["corpus_version"] != B2_CORPUS_VERSION:
        raise B2CorpusError("corpus version mismatch")
    if lock["protocol_spec_digest"] != b2_spec_digest():
        raise B2CorpusError("repo lock protocol digest drift")
    if lock["task_slot_digest"] != task_slot_digest():
        raise B2CorpusError("repo lock task-slot digest drift")
    repos = lock["repos"]
    if not isinstance(repos, list) or len(repos) != len(B2_LANGUAGES) * len(B2_SIZE_BANDS):
        raise B2CorpusError("repo lock must contain exactly 12 repositories")
    expected_slots = {slot.repo_slot for slot in build_task_slots()}
    seen_slots: set[str] = set()
    source_identities: set[tuple[str, str]] = set()
    for repo in repos:
        if not isinstance(repo, dict) or set(repo) != {
            "repo_slot", "language", "size_band", "source", "commit",
            "license", "visible",
        }:
            raise B2CorpusError("repo row has non-closed shape")
        repo_slot = repo["repo_slot"]
        if repo_slot not in expected_slots or repo_slot in seen_slots:
            raise B2CorpusError("unknown or duplicate repo slot")
        seen_slots.add(repo_slot)
        if repo["language"] not in B2_LANGUAGES or repo["size_band"] not in B2_SIZE_BANDS:
            raise B2CorpusError("repo language/size band invalid")
        if repo_slot != f"b2_repo_{repo['language']}_{repo['size_band']}":
            raise B2CorpusError("repo slot does not bind language/size band")
        source = repo["source"]
        if not isinstance(source, dict) or set(source) != {"type", "repo", "clone_root"}:
            raise B2CorpusError("repo source has non-closed shape")
        if source["type"] != "github_public" or not _GITHUB_REPO_RE.fullmatch(source["repo"]):
            raise B2CorpusError("repo source identity invalid")
        identity = (source["repo"].casefold(), repo["commit"])
        if identity in source_identities:
            raise B2CorpusError("repository snapshots must be distinct identities")
        source_identities.add(identity)
        if not isinstance(source["clone_root"], str) or not source["clone_root"]:
            raise B2CorpusError("clone_root missing")
        if not isinstance(repo["commit"], str) or not _COMMIT_RE.fullmatch(repo["commit"]):
            raise B2CorpusError("commit id malformed")
        license_row = repo["license"]
        if not isinstance(license_row, dict) or set(license_row) != {"detected", "expected"}:
            raise B2CorpusError("license row has non-closed shape")
        if not isinstance(license_row["detected"], list) or not license_row["detected"]:
            raise B2CorpusError("detected license list must be nonempty")
        visible = repo["visible"]
        if not isinstance(visible, dict) or set(visible) != {
            "file_count", "bytes", "manifest_digest", "files",
        }:
            raise B2CorpusError("visible row has non-closed shape")
        if not isinstance(visible["files"], list):
            raise B2CorpusError("visible.files must be a list")
        files = tuple(B2FileRecord.from_dict(item) for item in visible["files"])
        if tuple(sorted(row.path for row in files)) != tuple(row.path for row in files):
            raise B2CorpusError("visible files must be path-sorted")
        if len({row.path for row in files}) != len(files):
            raise B2CorpusError("visible files contain duplicates")
        if visible["file_count"] != len(files) or visible["bytes"] != sum(
            row.bytes for row in files
        ):
            raise B2CorpusError("visible counts do not reconcile")
        if visible["manifest_digest"] != visible_manifest_digest(files):
            raise B2CorpusError("visible manifest digest mismatch")
        validate_visible_band(repo["language"], repo["size_band"], files)
        if require_sources:
            root = Path(source["clone_root"])
            if git_commit(root) != repo["commit"]:
                raise B2CorpusError("candidate checkout commit drift")
            require_git_worktree_clean(root)
            for row in files:
                full = _safe_file(root, row.path)
                if full.stat().st_size != row.bytes or file_sha256(full) != row.sha256:
                    raise B2CorpusError(f"frozen source drift for {row.path!r}")
    if seen_slots != expected_slots:
        raise B2CorpusError("repo lock slot coverage incomplete")
    expected_digest = compute_repo_lock_digest(lock)
    if lock["repo_lock_digest"] != expected_digest:
        raise B2CorpusError("repo lock aggregate digest mismatch")
    return lock


def load_repo_lock(path: Path, *, require_sources: bool = False) -> dict[str, Any]:
    return validate_repo_lock(load_json(path), require_sources=require_sources)


def repo_by_slot(lock: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["repo_slot"]): row for row in lock["repos"]}


def task_manifest_digest(manifest: Mapping[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("task_manifest_digest", None)
    return prefixed_digest("b2tasks_", payload)


def validate_task_manifest(
    manifest: Any, *, repo_lock_digest: str | None = None
) -> tuple[B2PublicTask, ...]:
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version", "corpus_version", "protocol_spec_digest",
        "task_slot_digest", "repo_lock_digest", "task_manifest_digest", "tasks",
    }:
        raise B2CorpusError("task manifest has non-closed shape")
    if manifest["schema_version"] != B2_TASK_MANIFEST_SCHEMA:
        raise B2CorpusError("task manifest schema mismatch")
    if manifest["corpus_version"] != B2_CORPUS_VERSION:
        raise B2CorpusError("task manifest corpus version mismatch")
    if manifest["protocol_spec_digest"] != b2_spec_digest():
        raise B2CorpusError("task manifest protocol digest drift")
    if manifest["task_slot_digest"] != task_slot_digest():
        raise B2CorpusError("task manifest slot digest drift")
    if repo_lock_digest is not None and manifest["repo_lock_digest"] != repo_lock_digest:
        raise B2CorpusError("task/repo lock digest mismatch")
    if not isinstance(manifest["repo_lock_digest"], str) or not _DIGEST_RE.fullmatch(
        manifest["repo_lock_digest"]
    ):
        raise B2CorpusError("task manifest repo digest malformed")
    if not isinstance(manifest["tasks"], list) or len(manifest["tasks"]) != B2_TASK_COUNT:
        raise B2CorpusError(f"task manifest must contain {B2_TASK_COUNT} tasks")
    tasks = tuple(B2PublicTask.from_dict(row) for row in manifest["tasks"])
    if len({task.slot_id for task in tasks}) != len(tasks):
        raise B2CorpusError("duplicate task slot")
    if len({task.task_slug for task in tasks}) != len(tasks):
        raise B2CorpusError("duplicate task slug")
    expected_slots = {slot.slot_id for slot in build_task_slots()}
    if {task.slot_id for task in tasks} != expected_slots:
        raise B2CorpusError("task manifest slot coverage incomplete")
    if manifest["task_manifest_digest"] != task_manifest_digest(manifest):
        raise B2CorpusError("task manifest digest mismatch")
    return tasks


def load_task_manifest(
    path: Path, *, repo_lock_digest: str | None = None
) -> tuple[dict[str, Any], tuple[B2PublicTask, ...]]:
    manifest = load_json(path)
    tasks = validate_task_manifest(manifest, repo_lock_digest=repo_lock_digest)
    return manifest, tasks


def copy_visible_snapshot(repo_row: Mapping[str, Any], destination: Path) -> tuple[str, ...]:
    """Copy every and only frozen visible file, verifying source bytes first."""
    root = Path(repo_row["source"]["clone_root"]).resolve(strict=True)
    if git_commit(root) != repo_row["commit"]:
        raise B2CorpusError("source checkout commit changed before mirror copy")
    require_git_worktree_clean(root)
    if destination.exists():
        raise B2CorpusError("mirror destination must not preexist")
    destination.mkdir(parents=True)
    visible: list[str] = []
    for raw in repo_row["visible"]["files"]:
        row = B2FileRecord.from_dict(raw)
        source = _safe_file(root, row.path)
        data = source.read_bytes()
        if len(data) != row.bytes or hashlib.sha256(data).hexdigest() != row.sha256:
            raise B2CorpusError(f"source bytes drifted for {row.path!r}")
        target = destination / row.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        if _is_reparse_or_link(target) or target.read_bytes() != data:
            raise B2CorpusError(f"mirror verification failed for {row.path!r}")
        visible.append(row.path)
    if tuple(visible) != tuple(sorted(visible)):
        raise B2CorpusError("mirror visible declaration order drift")
    return tuple(visible)


def build_external_visible_manifest(
    *, request_manifest_digest: str, source_visibility_digest: str,
    visible_tree_digest: str, visible_files: Iterable[str],
) -> dict[str, Any]:
    files = list(visible_files)
    for rel in files:
        validate_relative_path(rel)
    if files != sorted(files) or len(files) != len(set(files)):
        raise B2CorpusError("external visible manifest paths must be sorted and unique")
    payload = {
        "schema_version": B2_VISIBLE_MANIFEST_SCHEMA,
        "snapshot_manifest_digest": request_manifest_digest,
        "source_visibility_digest": source_visibility_digest,
        "visible_tree_digest": visible_tree_digest,
        "visible_files": files,
    }
    payload["manifest_digest"] = prefixed_digest("b2requestvis_", payload)
    return payload


def validate_external_visible_manifest(
    raw: Any, *, snapshot_manifest_digest: str, source_visibility_digest: str,
    visible_tree_digest: str,
) -> tuple[str, ...]:
    if not isinstance(raw, dict) or set(raw) != {
        "schema_version", "snapshot_manifest_digest", "source_visibility_digest",
        "visible_tree_digest", "visible_files", "manifest_digest",
    }:
        raise B2CorpusError("external visible manifest has non-closed shape")
    if raw["schema_version"] != B2_VISIBLE_MANIFEST_SCHEMA:
        raise B2CorpusError("external visible manifest schema mismatch")
    expected_bindings = {
        "snapshot_manifest_digest": snapshot_manifest_digest,
        "source_visibility_digest": source_visibility_digest,
        "visible_tree_digest": visible_tree_digest,
    }
    for key, expected in expected_bindings.items():
        if raw[key] != expected:
            raise B2CorpusError(f"external visible manifest binding mismatch: {key}")
    if not isinstance(raw["visible_files"], list) or not raw["visible_files"]:
        raise B2CorpusError("external visible manifest file list is empty")
    files = tuple(validate_relative_path(item) for item in raw["visible_files"])
    if files != tuple(sorted(files)) or len(files) != len(set(files)):
        raise B2CorpusError("external visible files must be sorted and unique")
    payload = dict(raw)
    observed = payload.pop("manifest_digest")
    if observed != prefixed_digest("b2requestvis_", payload):
        raise B2CorpusError("external visible manifest digest mismatch")
    return files


def build_freeze_receipt(
    *,
    repo_lock_digest: str,
    task_manifest_digest_value: str,
    oracle_manifest_digest: str,
    repo_lock_path: str | Path,
    task_manifest_path: str | Path,
    oracle_manifest_path: str | Path,
    cli_path: str | Path,
) -> dict[str, Any]:
    for name, value in (
        ("repo_lock_digest", repo_lock_digest),
        ("task_manifest_digest", task_manifest_digest_value),
        ("oracle_manifest_digest", oracle_manifest_digest),
    ):
        if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
            raise B2CorpusError(f"{name} is malformed")
    receipt = {
        "schema_version": B2_FREEZE_RECEIPT_SCHEMA,
        "protocol_spec_digest": b2_spec_digest(),
        "task_slot_digest": task_slot_digest(),
        "execution_schedule_digest": execution_schedule_digest(),
        "repo_lock_digest": repo_lock_digest,
        "task_manifest_digest": task_manifest_digest_value,
        "oracle_manifest_digest": oracle_manifest_digest,
        "repo_lock_file_sha256": file_sha256(Path(repo_lock_path)),
        "task_manifest_file_sha256": file_sha256(Path(task_manifest_path)),
        "oracle_manifest_file_sha256": file_sha256(Path(oracle_manifest_path)),
        "source_bundle_digest": b2_source_bundle_digest(),
        "runtime_bundle_digest": b2_runtime_bundle_digest(cli_path),
    }
    receipt["freeze_receipt_digest"] = prefixed_digest("b2freeze_", receipt)
    return receipt


def validate_freeze_receipt(
    raw: Any,
    *,
    repo_lock_digest: str,
    task_manifest_digest_value: str,
    oracle_manifest_digest: str,
    repo_lock_path: str | Path,
    task_manifest_path: str | Path,
    oracle_manifest_path: str | Path,
    cli_path: str | Path,
) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {
        "schema_version", "protocol_spec_digest", "task_slot_digest",
        "execution_schedule_digest", "repo_lock_digest", "task_manifest_digest",
        "oracle_manifest_digest", "repo_lock_file_sha256",
        "task_manifest_file_sha256", "oracle_manifest_file_sha256",
        "source_bundle_digest", "runtime_bundle_digest",
        "freeze_receipt_digest",
    }:
        raise B2CorpusError("freeze receipt has non-closed shape")
    expected = build_freeze_receipt(
        repo_lock_digest=repo_lock_digest,
        task_manifest_digest_value=task_manifest_digest_value,
        oracle_manifest_digest=oracle_manifest_digest,
        repo_lock_path=repo_lock_path,
        task_manifest_path=task_manifest_path,
        oracle_manifest_path=oracle_manifest_path,
        cli_path=cli_path,
    )
    if raw != expected:
        raise B2CorpusError("freeze receipt drifted from current locked inputs/runtime")
    return raw


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory(prefix="openlocus-b2-corpus-") as tmp:
        root = Path(tmp) / "repo"
        root.mkdir()
        (root / "src").mkdir()
        for index in range(40):
            (root / "src" / f"f{index:02d}.py").write_text(
                f"def stable_symbol_{index:02d}():\n    return {index}\n",
                encoding="utf-8",
            )
        (root / ".env.local").write_text("SECRET=never-index\n", encoding="utf-8")
        (root / "package-lock.json").write_text("{}\n", encoding="utf-8")
        records = scan_repository(root)
        checks.append(("safe_scan_count", len(records) == 40))
        checks.append(("secret_excluded", all(".env" not in row.path for row in records)))
        checks.append(("lockfile_excluded", all("lock" not in row.path for row in records)))
        checks.append(("manifest_deterministic", visible_manifest_digest(records) == visible_manifest_digest(records)))

        ext = build_external_visible_manifest(
            request_manifest_digest="snap_" + "a" * 24,
            source_visibility_digest="vis_" + "b" * 24,
            visible_tree_digest="tree_" + "c" * 24,
            visible_files=[row.path for row in records],
        )
        parsed = validate_external_visible_manifest(
            ext,
            snapshot_manifest_digest="snap_" + "a" * 24,
            source_visibility_digest="vis_" + "b" * 24,
            visible_tree_digest="tree_" + "c" * 24,
        )
        checks.append(("external_manifest_roundtrip", len(parsed) == 40))

    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    for bad in ("../x.py", "/x.py", "C:/x.py", "a\\b.py", "a//b.py"):
        try:
            validate_relative_path(bad)
            rejected = False
        except B2CorpusError:
            rejected = True
        checks.append((f"reject_path:{bad}", rejected))

    manifest = build_external_visible_manifest(
        request_manifest_digest="snap_" + "a" * 24,
        source_visibility_digest="vis_" + "b" * 24,
        visible_tree_digest="tree_" + "c" * 24,
        visible_files=["src/a.py"],
    )
    tampered = dict(manifest)
    tampered["visible_files"] = ["src/b.py"]
    try:
        validate_external_visible_manifest(
            tampered,
            snapshot_manifest_digest="snap_" + "a" * 24,
            source_visibility_digest="vis_" + "b" * 24,
            visible_tree_digest="tree_" + "c" * 24,
        )
        digest_rejected = False
    except B2CorpusError:
        digest_rejected = True
    checks.append(("reject_manifest_tamper", digest_rejected))

    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B2CorpusError", "B2FileRecord", "B2PublicTask",
    "B2_REPO_LOCK_SCHEMA", "B2_TASK_MANIFEST_SCHEMA",
    "B2_VISIBLE_MANIFEST_SCHEMA", "B2_FREEZE_RECEIPT_SCHEMA", "B2_CORPUS_VERSION",
    "VISIBLE_EXTENSIONS", "PRIMARY_EXTENSIONS",
    "prefixed_digest", "file_sha256", "b2_runtime_bundle_digest", "load_json", "write_json",
    "validate_relative_path", "scan_repository", "clone_public_repo",
    "git_commit", "require_git_worktree_clean", "visible_manifest_digest",
    "validate_visible_band", "compute_repo_lock_digest", "validate_repo_lock",
    "load_repo_lock", "repo_by_slot", "task_manifest_digest",
    "validate_task_manifest", "load_task_manifest", "copy_visible_snapshot",
    "build_external_visible_manifest", "validate_external_visible_manifest",
    "build_freeze_receipt", "validate_freeze_receipt",
    "run_self_test", "run_fault_test",
]
