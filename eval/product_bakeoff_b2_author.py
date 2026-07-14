#!/usr/bin/env python3
"""Offline B2 repository selection, task authoring, and oracle freeze.

This is an AUTHORING-phase module.  It reads only frozen current source; it
never invokes an S0-S5 adapter and never consumes adapter output.  The RUN
phase must not import it.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from ci_clone_and_lock_repo import check_license, detect_license
from product_bakeoff_b2_corpus import (
    B2_CORPUS_VERSION,
    B2_REPO_LOCK_SCHEMA,
    B2_TASK_MANIFEST_SCHEMA,
    B2CorpusError,
    B2FileRecord,
    B2PublicTask,
    PRIMARY_EXTENSIONS,
    build_freeze_receipt,
    clone_public_repo,
    compute_repo_lock_digest,
    file_sha256,
    git_commit,
    load_json,
    prefixed_digest,
    require_git_worktree_clean,
    scan_repository,
    task_manifest_digest,
    validate_repo_lock,
    validate_task_manifest,
    validate_visible_band,
    visible_manifest_digest,
    write_json,
)
from product_bakeoff_b2_oracle import (
    B2_ORACLE_SCHEMA,
    B2_ORACLE_VERSION,
    B2Span,
    B2SupportRelation,
    B2TaskOracle,
    oracle_manifest_digest,
    validate_oracle_manifest,
)
from product_bakeoff_b2_protocol import (
    B2_RANDOMIZATION_SEED,
    B2_SIZE_BAND_VISIBLE_BYTES,
    B2_TASK_COUNT,
    b2_spec_digest,
    build_task_slots,
    task_slot_digest,
)


B2_CANDIDATE_PLAN_SCHEMA = "product_bakeoff_b2_private_candidate_plan.v1"
B2_AUTHOR_VERSION = "product_bakeoff_b2_author.v1"

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{2,127}$")
_TEST_PATH_RE = re.compile(
    r"(?:^|/)(?:tests?|specs?|__tests__)(?:/|$)|(?:^|[._-])(?:test|spec)(?:[._-]|$)",
    re.IGNORECASE,
)
_GENERIC_SYMBOLS = frozenset(
    {
        "new", "main", "run", "test", "tests", "get", "set", "add", "remove",
        "update", "build", "create", "default", "config", "error", "result",
        "value", "data", "item", "handler", "client", "server", "request",
        "response", "init", "index", "parse", "load", "save", "read", "write",
    }
)
_ERROR_HINT_RE = re.compile(
    r"(?:error|raise|panic|throw|assert|fail|invalid|missing|cannot|failed|exception|unsupported)",
    re.IGNORECASE,
)
_QUOTED_RE = re.compile(r"(?P<q>['\"])(?P<text>[^'\"\r\n]{10,120})(?P=q)")
_CONFIG_BASENAMES = frozenset(
    {
        "cargo.toml", "pyproject.toml", "setup.cfg", "tox.ini", "pytest.ini",
        "package.json", "tsconfig.json", "vite.config.ts", "vite.config.js",
        "webpack.config.js", "ruff.toml", "mypy.ini",
    }
)
_CONFIG_KEY_RES = (
    re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_.-]{4,80})\s*="),
    re.compile(r'^\s*"([A-Za-z_][A-Za-z0-9_.-]{4,80})"\s*:'),
    re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_.-]{4,80})\s*:"),
)


class B2AuthorError(ValueError):
    """Fail-closed authoring/admission error."""


@dataclass(frozen=True)
class SymbolDef:
    name: str
    path: str
    line: int
    kind: str

    @property
    def span(self) -> B2Span:
        return B2Span(self.path, self.line, self.line)


@dataclass(frozen=True)
class ImportEdge:
    source_path: str
    source_line: int
    target_path: str

    @property
    def support_span(self) -> B2Span:
        return B2Span(self.source_path, self.source_line, self.source_line)


@dataclass(frozen=True)
class TextCandidate:
    query: str
    span: B2Span


@dataclass(frozen=True)
class TaskDraft:
    slot_id: str
    repo_slot: str
    language: str
    size_band: str
    role: str
    task_family: str
    interaction_mode: str
    oracle_kind: str
    query: str
    positives: tuple[B2Span, ...]
    negatives: tuple[B2Span, ...]
    support: tuple[B2SupportRelation, ...]


@dataclass(frozen=True)
class AuthoredRepo:
    repo_row: dict[str, Any]
    drafts: tuple[TaskDraft, ...]


def _stable_key(label: str, value: Any) -> str:
    material = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(
        f"{B2_RANDOMIZATION_SEED}|{label}|{material}".encode("utf-8")
    ).hexdigest()


def _seeded(values: Iterable[Any], label: str, key) -> list[Any]:
    return sorted(values, key=lambda value: (_stable_key(label, key(value)), key(value)))


def _read_verified(root: Path, row: B2FileRecord) -> str:
    full = (root / row.path).resolve(strict=True)
    try:
        full.relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise B2AuthorError(f"source path escaped checkout: {row.path!r}") from exc
    raw = full.read_bytes()
    if len(raw) != row.bytes or hashlib.sha256(raw).hexdigest() != row.sha256:
        raise B2AuthorError(f"source drift while authoring {row.path!r}")
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise B2AuthorError(f"visible source is not UTF-8: {row.path!r}") from exc


def _symbol_patterns(language: str) -> tuple[tuple[re.Pattern[str], str], ...]:
    if language == "rust":
        return (
            (re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:unsafe\s+)?(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)\b"), "function"),
            (re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:struct|enum|trait|type)\s+([A-Za-z_][A-Za-z0-9_]*)\b"), "type"),
        )
    if language == "python":
        return (
            (re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("), "function"),
            (re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b"), "type"),
        )
    if language == "typescript":
        return (
            (re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:declare\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)\b"), "function"),
            (re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:declare\s+)?(?:abstract\s+)?(?:class|interface|type|enum)\s+([A-Za-z_][A-Za-z0-9_]*)\b"), "type"),
            (re.compile(r"^\s*(?:export\s+)?(?:declare\s+)?(?:const|let)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]+)?=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_][A-Za-z0-9_]*)\s*=>"), "function"),
        )
    raise B2AuthorError(f"unsupported authoring language {language!r}")


def _extract_symbols(path: str, text: str, language: str) -> list[SymbolDef]:
    symbols: list[SymbolDef] = []
    patterns = _symbol_patterns(language)
    for line_no, line in enumerate(text.splitlines(), start=1):
        for pattern, kind in patterns:
            match = pattern.search(line)
            if match:
                name = match.group(1)
                if name.casefold() not in _GENERIC_SYMBOLS and _IDENTIFIER_RE.fullmatch(name):
                    symbols.append(SymbolDef(name, path, line_no, kind))
                break
    return symbols


def _normalize(path: str) -> str:
    parts: list[str] = []
    for part in PurePosixPath(path).parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
        else:
            parts.append(part)
    return "/".join(parts)


def _resolve_rust(path: str, line: str, paths: set[str], basenames: Mapping[str, list[str]]) -> list[str]:
    trimmed = line.strip()
    directory = str(PurePosixPath(path).parent)
    directory = "" if directory == "." else directory
    segment: str | None = None
    if trimmed.startswith("mod ") or trimmed.startswith("pub mod "):
        rest = trimmed.removeprefix("pub ").removeprefix("mod ").strip()
        match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)", rest)
        segment = match.group(1) if match else None
    elif trimmed.startswith("use "):
        rest = trimmed.removeprefix("use ").strip().rstrip(";")
        for item in rest.split("::"):
            if item and item not in {"crate", "self", "super"}:
                segment = re.match(r"[A-Za-z_][A-Za-z0-9_]*", item).group(0) if re.match(r"[A-Za-z_][A-Za-z0-9_]*", item) else None
                break
    if not segment:
        return []
    candidates = [
        _normalize(f"{directory}/{segment}.rs"),
        _normalize(f"{directory}/{segment}/mod.rs"),
    ]
    for candidate in candidates:
        if candidate in paths:
            return [candidate]
    matches = basenames.get(f"{segment}.rs", [])
    return [matches[0]] if len(matches) == 1 else []


def _resolve_ts(path: str, line: str, paths: set[str]) -> list[str]:
    trimmed = line.strip()
    from_part: str | None = None
    if " from " in trimmed:
        from_part = trimmed.split(" from ", 1)[1]
    elif trimmed.startswith(("import '", 'import "')):
        from_part = trimmed.removeprefix("import ")
    if from_part is None:
        return []
    target = from_part.strip().rstrip(";").strip("'\"")
    if not target.startswith("."):
        return []
    directory = str(PurePosixPath(path).parent)
    directory = "" if directory == "." else directory
    resolved = _normalize(f"{directory}/{target}")
    candidates = [
        resolved, f"{resolved}.ts", f"{resolved}.tsx", f"{resolved}.js",
        f"{resolved}.jsx", f"{resolved}/index.ts", f"{resolved}/index.tsx",
        f"{resolved}/index.js",
    ]
    return [candidate for candidate in candidates if candidate in paths][:1]


def _resolve_python(path: str, line: str, paths: set[str]) -> list[str]:
    trimmed = line.strip()
    module: str | None = None
    if trimmed.startswith("import "):
        rest = trimmed.removeprefix("import ").rstrip(";")
        module = rest.split(",", 1)[0].strip().split(".", 1)[0]
    elif trimmed.startswith("from "):
        rest = trimmed.removeprefix("from ").strip()
        module = rest.split(".", 1)[0].split(" ", 1)[0]
    if not module:
        return []
    directory = str(PurePosixPath(path).parent)
    directory = "" if directory == "." else directory
    candidates = [
        _normalize(f"{directory}/{module}.py"),
        _normalize(f"{directory}/__init__.py"),
        f"{module}.py", f"{module}/__init__.py",
    ]
    return [candidate for candidate in candidates if candidate in paths][:1]


def _extract_imports(
    path: str, text: str, language: str, paths: set[str], basenames: Mapping[str, list[str]]
) -> list[ImportEdge]:
    edges: list[ImportEdge] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if language == "rust":
            targets = _resolve_rust(path, line, paths, basenames)
        elif language == "python":
            targets = _resolve_python(path, line, paths)
        else:
            targets = _resolve_ts(path, line, paths)
        for target in targets:
            if target != path:
                edges.append(ImportEdge(path, line_no, target))
    return edges


def _query_safe(query: str, repo_slug: str) -> bool:
    if not isinstance(query, str) or not 3 <= len(query) <= 128:
        return False
    if any(ord(char) < 32 for char in query) or any(char in query for char in "/\\"):
        return False
    lowered = query.casefold()
    identity_tokens = {
        token.casefold()
        for token in re.split(r"[^A-Za-z0-9]+", repo_slug)
        if len(token) >= 4
    }
    return all(token not in lowered for token in identity_tokens)


def _extract_error_candidates(path: str, text: str, repo_slug: str) -> list[TextCandidate]:
    candidates: list[TextCandidate] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not _ERROR_HINT_RE.search(line):
            continue
        for match in _QUOTED_RE.finditer(line):
            query = " ".join(match.group("text").split())
            if _query_safe(query, repo_slug) and len(re.findall(r"[A-Za-z0-9]+", query)) >= 2:
                candidates.append(TextCandidate(query, B2Span(path, line_no, line_no)))
    return candidates


def _extract_config_candidates(path: str, text: str, repo_slug: str) -> list[TextCandidate]:
    basename = PurePosixPath(path).name.casefold()
    suffix = PurePosixPath(path).suffix.casefold()
    if basename not in _CONFIG_BASENAMES and suffix not in {".toml", ".json", ".jsonc", ".yaml", ".yml", ".ini", ".cfg"}:
        return []
    candidates: list[TextCandidate] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for pattern in _CONFIG_KEY_RES:
            match = pattern.search(line)
            if match:
                query = match.group(1)
                if query.casefold() not in _GENERIC_SYMBOLS and _query_safe(query, repo_slug):
                    candidates.append(TextCandidate(query, B2Span(path, line_no, line_no)))
                break
    return candidates


def _choose_unique_symbol(
    groups: Mapping[str, list[SymbolDef]], used: set[B2Span], label: str, repo_slug: str,
    *, test_only: bool = False,
) -> SymbolDef:
    candidates = [
        defs[0] for name, defs in groups.items()
        if len(defs) == 1 and defs[0].span not in used
        and (not test_only or _TEST_PATH_RE.search(defs[0].path))
        and _query_safe(name, repo_slug)
    ]
    ordered = _seeded(candidates, label, lambda item: (item.name, item.path, item.line))
    if not ordered:
        raise B2AuthorError(f"no source-only candidate for {label}")
    return ordered[0]


def _choose_ambiguous(
    groups: Mapping[str, list[SymbolDef]], label: str, repo_slug: str,
) -> tuple[str, tuple[SymbolDef, ...]]:
    candidates: list[tuple[str, tuple[SymbolDef, ...]]] = []
    for name, defs in groups.items():
        distinct: dict[str, SymbolDef] = {}
        for definition in defs:
            distinct.setdefault(definition.path, definition)
        rows = tuple(distinct[path] for path in sorted(distinct))
        if 2 <= len(rows) <= 4 and _query_safe(name, repo_slug):
            candidates.append((name, rows))
    ordered = _seeded(candidates, label, lambda item: (item[0], tuple(d.path for d in item[1])))
    if not ordered:
        raise B2AuthorError("no 2..4-path ambiguous symbol group")
    return ordered[0]


def _choose_text_candidate(
    candidates: Sequence[TextCandidate], used: set[B2Span], label: str
) -> TextCandidate:
    rows = [candidate for candidate in candidates if candidate.span not in used]
    ordered = _seeded(rows, label, lambda item: (item.query, item.span.path, item.span.start_line))
    if not ordered:
        raise B2AuthorError(f"no source-only text candidate for {label}")
    return ordered[0]


def _choose_relation(
    edges: Sequence[ImportEdge], groups: Mapping[str, list[SymbolDef]],
    used: set[B2Span], label: str, repo_slug: str,
) -> tuple[SymbolDef, ImportEdge]:
    by_target: dict[str, list[SymbolDef]] = defaultdict(list)
    for defs in groups.values():
        if len(defs) == 1:
            by_target[defs[0].path].append(defs[0])
    candidates: list[tuple[SymbolDef, ImportEdge]] = []
    for edge in edges:
        # Source-only convergence heuristic: the definition path sorts before
        # the importer, matching the production deterministic tie order.
        if edge.target_path >= edge.source_path:
            continue
        for definition in by_target.get(edge.target_path, []):
            if definition.span not in used and _query_safe(definition.name, repo_slug):
                candidates.append((definition, edge))
    ordered = _seeded(
        candidates, label,
        lambda item: (item[0].name, item[0].path, item[1].source_path, item[1].source_line),
    )
    if not ordered:
        raise B2AuthorError("no resolvable import relation with a unique target symbol")
    return ordered[0]


def _choose_negatives(
    symbols: Sequence[SymbolDef], positives: Sequence[B2Span], query: str, label: str,
) -> tuple[B2Span, B2Span]:
    positive_atoms = set().union(*(span.atoms() for span in positives)) if positives else set()
    rows = [
        symbol for symbol in symbols
        if symbol.name != query and not (symbol.span.atoms() & positive_atoms)
    ]
    ordered = _seeded(rows, label, lambda item: (item.path, item.line, item.name))
    selected: list[B2Span] = []
    selected_paths: set[str] = set()
    for symbol in ordered:
        if symbol.span in selected:
            continue
        if symbol.path in selected_paths and len({item.path for item in rows}) >= 2:
            continue
        selected.append(symbol.span)
        selected_paths.add(symbol.path)
        if len(selected) == 2:
            return (selected[0], selected[1])
    raise B2AuthorError("fewer than two distinct negative spans")


def _absent_query(repo_slot: str, all_text_digests: Sequence[str]) -> str:
    nonce = hashlib.sha256(
        (B2_RANDOMIZATION_SEED + "|" + repo_slot + "|" + "|".join(all_text_digests)).encode("utf-8")
    ).hexdigest()[:28]
    return "qzv" + nonce


def _build_drafts(
    *, repo_slot: str, language: str, size_band: str, repo_slug: str,
    records: Sequence[B2FileRecord], root: Path,
) -> tuple[tuple[TaskDraft, ...], dict[str, set[str]]]:
    paths = {row.path for row in records}
    basenames: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        basenames[PurePosixPath(path).name].append(path)
    row_by_path = {row.path: row for row in records}
    symbols: list[SymbolDef] = []
    edges: list[ImportEdge] = []
    error_candidates: list[TextCandidate] = []
    config_candidates: list[TextCandidate] = []
    text_digests: list[str] = []
    for row in records:
        text = _read_verified(root, row)
        text_digests.append(row.sha256)
        if row.extension in PRIMARY_EXTENSIONS[language]:
            symbols.extend(_extract_symbols(row.path, text, language))
            edges.extend(_extract_imports(row.path, text, language, paths, basenames))
        error_candidates.extend(_extract_error_candidates(row.path, text, repo_slug))
        config_candidates.extend(_extract_config_candidates(row.path, text, repo_slug))

    groups: dict[str, list[SymbolDef]] = defaultdict(list)
    for symbol in symbols:
        groups[symbol.name].append(symbol)
    if len(symbols) < 12:
        raise B2AuthorError("repository has too few authorable primary-language symbols")

    slot_rows = [slot for slot in build_task_slots() if slot.repo_slot == repo_slot]
    if len(slot_rows) != 4:
        raise B2AuthorError("repo slot does not map to four frozen task slots")
    drafts: list[TaskDraft] = []
    used: set[B2Span] = set()
    query_files_to_exclude: dict[str, set[str]] = defaultdict(set)

    # Relational first because it has the strictest source-only constraints.
    relational = next(slot for slot in slot_rows if slot.role == "relational")
    rel_symbol, rel_edge = _choose_relation(
        edges, groups, used, f"{repo_slot}:relational", repo_slug
    )
    used.add(rel_symbol.span)
    rel_positive = (rel_symbol.span,)
    rel_negative = _choose_negatives(
        symbols, rel_positive, rel_symbol.name, f"{repo_slot}:relational:negative"
    )
    drafts.append(TaskDraft(
        slot_id=relational.slot_id, repo_slot=repo_slot, language=language,
        size_band=size_band, role=relational.role, task_family=relational.task_family,
        interaction_mode=relational.interaction_mode, oracle_kind=relational.oracle_kind,
        query=rel_symbol.name, positives=rel_positive, negatives=rel_negative,
        support=(B2SupportRelation(
            support=rel_edge.support_span, relation_kind="import", target=rel_symbol.span,
        ),),
    ))

    for slot in slot_rows:
        if slot.role == "relational":
            continue
        positives: tuple[B2Span, ...]
        support: tuple[B2SupportRelation, ...] = ()
        if slot.task_family == "no_answer":
            query = _absent_query(repo_slot, sorted(text_digests))
            positives = ()
        elif slot.task_family == "ambiguous_target":
            query, ambiguous_defs = _choose_ambiguous(
                groups, f"{repo_slot}:ambiguous", repo_slug
            )
            positives = tuple(definition.span for definition in ambiguous_defs)
            used.update(positives)
            all_paths = {definition.path for definition in groups[query]}
            query_files_to_exclude[query].update(all_paths - {span.path for span in positives})
        elif slot.task_family == "error_text":
            candidate = _choose_text_candidate(
                error_candidates, used, f"{repo_slot}:error"
            )
            query, positives = candidate.query, (candidate.span,)
            used.add(candidate.span)
        elif slot.task_family == "configuration_discovery":
            candidate = _choose_text_candidate(
                config_candidates, used, f"{repo_slot}:config"
            )
            query, positives = candidate.query, (candidate.span,)
            used.add(candidate.span)
        elif slot.task_family == "test_discovery":
            definition = _choose_unique_symbol(
                groups, used, f"{repo_slot}:test", repo_slug, test_only=True
            )
            query, positives = definition.name, (definition.span,)
            used.add(definition.span)
        else:
            definition = _choose_unique_symbol(
                groups, used, f"{repo_slot}:{slot.task_family}", repo_slug
            )
            query, positives = definition.name, (definition.span,)
            used.add(definition.span)
        negatives = _choose_negatives(
            symbols, positives, query, f"{repo_slot}:{slot.role}:negative"
        )
        drafts.append(TaskDraft(
            slot_id=slot.slot_id, repo_slot=repo_slot, language=language,
            size_band=size_band, role=slot.role, task_family=slot.task_family,
            interaction_mode=slot.interaction_mode, oracle_kind=slot.oracle_kind,
            query=query, positives=positives, negatives=negatives, support=support,
        ))

    # For literal/config tasks keep non-target files containing the query out
    # of the bounded visible snapshot. This is decided from source only.
    for draft in drafts:
        if draft.task_family not in {"error_text", "configuration_discovery"}:
            continue
        target_paths = {span.path for span in draft.positives}
        for row in records:
            if row.path in target_paths:
                continue
            if draft.query in _read_verified(root, row):
                query_files_to_exclude[draft.query].add(row.path)

    drafts.sort(key=lambda draft: draft.slot_id)
    if len(drafts) != 4:
        raise B2AuthorError("authoring did not produce four tasks")
    return tuple(drafts), query_files_to_exclude


def _select_visible_files(
    *, records: Sequence[B2FileRecord], drafts: Sequence[TaskDraft],
    exclusions: Mapping[str, set[str]], language: str, size_band: str, repo_slot: str,
) -> tuple[B2FileRecord, ...]:
    row_by_path = {row.path: row for row in records}
    required_paths: set[str] = set()
    for draft in drafts:
        for span in (*draft.positives, *draft.negatives):
            required_paths.add(span.path)
        for relation in draft.support:
            required_paths.add(relation.support.path)
            required_paths.add(relation.target.path)
    if not required_paths <= set(row_by_path):
        raise B2AuthorError("task/oracle required path is absent from scanned corpus")
    forbidden_paths = set().union(*exclusions.values()) if exclusions else set()
    if required_paths & forbidden_paths:
        raise B2AuthorError("required task path conflicts with query-isolation exclusion")

    low, high = B2_SIZE_BAND_VISIBLE_BYTES[size_band]
    target = low + min((high - low) // 6, 16 * 1024 * 1024)
    selected: dict[str, B2FileRecord] = {
        path: row_by_path[path] for path in sorted(required_paths)
    }
    total = sum(row.bytes for row in selected.values())
    if total >= high:
        raise B2AuthorError("required task files alone exceed size-band upper bound")

    primary_ext = PRIMARY_EXTENSIONS[language]
    candidates = [
        row for row in records if row.path not in selected and row.path not in forbidden_paths
    ]
    primary = _seeded(
        [row for row in candidates if row.extension in primary_ext],
        f"{repo_slot}:visible-primary", lambda row: (row.path, row.sha256),
    )
    all_rows = _seeded(
        candidates, f"{repo_slot}:visible-all", lambda row: (row.path, row.sha256)
    )

    def add(row: B2FileRecord) -> None:
        nonlocal total
        if row.path in selected or total + row.bytes >= high:
            return
        selected[row.path] = row
        total += row.bytes

    primary_count = sum(row.extension in primary_ext for row in selected.values())
    primary_bytes = sum(
        row.bytes for row in selected.values() if row.extension in primary_ext
    )
    for row in primary:
        if primary_count >= 24 and primary_bytes >= min(target // 3, 16 * 1024 * 1024):
            break
        before = len(selected)
        add(row)
        if len(selected) != before:
            primary_count += 1
            primary_bytes += row.bytes
    for row in all_rows:
        if total >= target and len(selected) >= 32 and primary_count >= 16:
            break
        before = len(selected)
        add(row)
        if len(selected) != before and row.extension in primary_ext:
            primary_count += 1
            primary_bytes += row.bytes
    selected_rows = tuple(selected[path] for path in sorted(selected))
    validate_visible_band(language, size_band, selected_rows)
    return selected_rows


def _make_task_slug(slot_id: str, query: str, positives: Sequence[B2Span]) -> str:
    slot_number = int(slot_id.rsplit("_", 1)[1])
    material = {
        "slot_id": slot_id,
        "query": query,
        "positive_spans": [span.to_dict() for span in positives],
    }
    suffix = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:12]
    return f"b2_t{slot_number:02d}_{suffix}"


def _materialize_task_oracles(
    drafts: Sequence[TaskDraft],
) -> tuple[tuple[B2PublicTask, ...], tuple[B2TaskOracle, ...]]:
    tasks: list[B2PublicTask] = []
    oracles: list[B2TaskOracle] = []
    for draft in drafts:
        slug = _make_task_slug(draft.slot_id, draft.query, draft.positives)
        task = B2PublicTask(
            slot_id=draft.slot_id, task_slug=slug, repo_slot=draft.repo_slot,
            language=draft.language, size_band=draft.size_band, role=draft.role,
            task_family=draft.task_family, interaction_mode=draft.interaction_mode,
            query=draft.query,
        ).validate()
        oracle = B2TaskOracle(
            slot_id=draft.slot_id, task_slug=slug, oracle_kind=draft.oracle_kind,
            positive_spans=draft.positives, negative_spans=draft.negatives,
            support_relations=draft.support,
        ).validate(task=task)
        tasks.append(task)
        oracles.append(oracle)
    return tuple(tasks), tuple(oracles)


def _validate_candidate_plan(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "slots"}:
        raise B2AuthorError("candidate plan has non-closed shape")
    if raw["schema_version"] != B2_CANDIDATE_PLAN_SCHEMA:
        raise B2AuthorError("candidate plan schema mismatch")
    if not isinstance(raw["slots"], list) or len(raw["slots"]) != 12:
        raise B2AuthorError("candidate plan must contain 12 slot rows")
    expected_slots = {slot.repo_slot for slot in build_task_slots()}
    seen: set[str] = set()
    for slot in raw["slots"]:
        if not isinstance(slot, dict) or set(slot) != {"repo_slot", "candidates"}:
            raise B2AuthorError("candidate slot row has non-closed shape")
        if slot["repo_slot"] not in expected_slots or slot["repo_slot"] in seen:
            raise B2AuthorError("candidate plan has unknown/duplicate slot")
        seen.add(slot["repo_slot"])
        if not isinstance(slot["candidates"], list) or not slot["candidates"]:
            raise B2AuthorError("each slot needs at least one candidate")
        for candidate in slot["candidates"]:
            if not isinstance(candidate, dict) or set(candidate) != {"repo", "expected_license"}:
                raise B2AuthorError("candidate row has non-closed shape")
            if not isinstance(candidate["repo"], str) or not candidate["repo"]:
                raise B2AuthorError("candidate repo missing")
            if not isinstance(candidate["expected_license"], str) or not candidate["expected_license"]:
                raise B2AuthorError("candidate expected_license missing")
    return raw["slots"]


def _prepare_one_repo(
    *, repo_slot: str, candidates: Sequence[Mapping[str, str]], clone_root: Path,
) -> AuthoredRepo:
    slot = next(slot for slot in build_task_slots() if slot.repo_slot == repo_slot)
    failures: list[str] = []
    for index, candidate in enumerate(candidates, start=1):
        repo_slug = candidate["repo"]
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "__", repo_slug)
        destination = clone_root / f"{repo_slot}__{index:02d}__{safe_name}"
        try:
            root = clone_public_repo(repo_slug, destination)
            commit = git_commit(root)
            require_git_worktree_clean(root)
            detected = detect_license(str(root))
            mismatch = check_license(detected, candidate["expected_license"])
            if mismatch:
                raise B2AuthorError(mismatch)
            records = scan_repository(root)
            low, _ = B2_SIZE_BAND_VISIBLE_BYTES[slot.size_band]
            if sum(row.bytes for row in records) < low:
                raise B2AuthorError("eligible visible source is below size-band lower bound")
            drafts, exclusions = _build_drafts(
                repo_slot=repo_slot, language=slot.language, size_band=slot.size_band,
                repo_slug=repo_slug, records=records, root=root,
            )
            selected = _select_visible_files(
                records=records, drafts=drafts, exclusions=exclusions,
                language=slot.language, size_band=slot.size_band, repo_slot=repo_slot,
            )
            repo_row = {
                "repo_slot": repo_slot,
                "language": slot.language,
                "size_band": slot.size_band,
                "source": {
                    "type": "github_public",
                    "repo": repo_slug,
                    "clone_root": str(root.resolve()),
                },
                "commit": commit,
                "license": {
                    "detected": sorted(set(detected)),
                    "expected": candidate["expected_license"],
                },
                "visible": {
                    "file_count": len(selected),
                    "bytes": sum(row.bytes for row in selected),
                    "manifest_digest": visible_manifest_digest(selected),
                    "files": [row.to_dict() for row in selected],
                },
            }
            return AuthoredRepo(repo_row=repo_row, drafts=drafts)
        except (B2AuthorError, B2CorpusError, OSError, ValueError) as exc:
            failures.append(f"candidate_{index}:{type(exc).__name__}:{str(exc)[:180]}")
    raise B2AuthorError(
        f"no candidate admitted for {repo_slot}; " + " | ".join(failures)
    )


def prepare_private_manifests(
    *, candidate_plan: Path, private_root: Path,
) -> dict[str, Any]:
    """Clone/audit 12 repos and freeze repo/task/oracle manifests."""
    slots = _validate_candidate_plan(load_json(candidate_plan))
    private_root.mkdir(parents=True, exist_ok=True)
    clone_root = private_root / "clones"
    authored: list[AuthoredRepo] = []
    for slot_row in slots:
        authored.append(_prepare_one_repo(
            repo_slot=slot_row["repo_slot"],
            candidates=slot_row["candidates"],
            clone_root=clone_root,
        ))
    authored.sort(key=lambda item: item.repo_row["repo_slot"])

    repo_lock: dict[str, Any] = {
        "schema_version": B2_REPO_LOCK_SCHEMA,
        "corpus_version": B2_CORPUS_VERSION,
        "protocol_spec_digest": b2_spec_digest(),
        "task_slot_digest": task_slot_digest(),
        "repo_lock_digest": "",
        "repos": [item.repo_row for item in authored],
    }
    repo_lock["repo_lock_digest"] = compute_repo_lock_digest(repo_lock)
    validate_repo_lock(repo_lock, require_sources=True)

    all_drafts = tuple(
        draft for item in authored for draft in item.drafts
    )
    tasks, oracles = _materialize_task_oracles(all_drafts)
    tasks = tuple(sorted(tasks, key=lambda task: task.slot_id))
    oracles = tuple(sorted(oracles, key=lambda oracle: oracle.slot_id))
    if len(tasks) != B2_TASK_COUNT or len(oracles) != B2_TASK_COUNT:
        raise B2AuthorError("global task/oracle count drift")

    task_manifest: dict[str, Any] = {
        "schema_version": B2_TASK_MANIFEST_SCHEMA,
        "corpus_version": B2_CORPUS_VERSION,
        "protocol_spec_digest": b2_spec_digest(),
        "task_slot_digest": task_slot_digest(),
        "repo_lock_digest": repo_lock["repo_lock_digest"],
        "task_manifest_digest": "",
        "tasks": [task.to_dict() for task in tasks],
    }
    task_manifest["task_manifest_digest"] = task_manifest_digest(task_manifest)
    validate_task_manifest(task_manifest, repo_lock_digest=repo_lock["repo_lock_digest"])

    oracle_manifest: dict[str, Any] = {
        "schema_version": B2_ORACLE_SCHEMA,
        "oracle_version": B2_ORACLE_VERSION,
        "protocol_spec_digest": b2_spec_digest(),
        "repo_lock_digest": repo_lock["repo_lock_digest"],
        "task_manifest_digest": task_manifest["task_manifest_digest"],
        "oracle_manifest_digest": "",
        "tasks": [oracle.to_dict() for oracle in oracles],
    }
    oracle_manifest["oracle_manifest_digest"] = oracle_manifest_digest(oracle_manifest)
    validate_oracle_manifest(
        oracle_manifest, tasks=tasks, repo_lock=repo_lock,
        task_manifest_digest=task_manifest["task_manifest_digest"],
    )

    repo_path = private_root / "b2_private_repo_lock.json"
    task_path = private_root / "b2_private_task_manifest.json"
    oracle_path = private_root / "b2_private_oracle_manifest.json"
    write_json(repo_path, repo_lock)
    write_json(task_path, task_manifest)
    write_json(oracle_path, oracle_manifest)
    return {
        "author_version": B2_AUTHOR_VERSION,
        "repo_lock_path": str(repo_path.resolve()),
        "task_manifest_path": str(task_path.resolve()),
        "oracle_manifest_path": str(oracle_path.resolve()),
        "repo_lock_digest": repo_lock["repo_lock_digest"],
        "task_manifest_digest": task_manifest["task_manifest_digest"],
        "oracle_manifest_digest": oracle_manifest["oracle_manifest_digest"],
        "repo_count": len(repo_lock["repos"]),
        "task_count": len(tasks),
    }


def freeze_private_manifests(*, private_root: Path, cli_path: str | Path) -> dict[str, Any]:
    repo_path = private_root / "b2_private_repo_lock.json"
    task_path = private_root / "b2_private_task_manifest.json"
    oracle_path = private_root / "b2_private_oracle_manifest.json"
    repo_lock = load_json(repo_path)
    task_manifest = load_json(task_path)
    oracle_manifest = load_json(oracle_path)
    validate_repo_lock(repo_lock, require_sources=True)
    tasks = validate_task_manifest(
        task_manifest, repo_lock_digest=repo_lock["repo_lock_digest"]
    )
    validate_oracle_manifest(
        oracle_manifest,
        tasks=tasks,
        repo_lock=repo_lock,
        task_manifest_digest=task_manifest["task_manifest_digest"],
    )
    receipt = build_freeze_receipt(
        repo_lock_digest=repo_lock["repo_lock_digest"],
        task_manifest_digest_value=task_manifest["task_manifest_digest"],
        oracle_manifest_digest=oracle_manifest["oracle_manifest_digest"],
        repo_lock_path=repo_path,
        task_manifest_path=task_path,
        oracle_manifest_path=oracle_path,
        cli_path=cli_path,
    )
    path = private_root / "b2_private_freeze_receipt.json"
    write_json(path, receipt)
    return {**receipt, "freeze_receipt_path": str(path.resolve())}


def _synthetic_python_repo(root: Path) -> tuple[B2FileRecord, ...]:
    (root / "pkg").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "pkg" / "alpha.py").write_text(
        "class StableAlpha:\n    pass\n\ndef unique_alpha():\n    return 'alpha'\n",
        encoding="utf-8",
    )
    (root / "pkg" / "zeta.py").write_text(
        "from alpha import StableAlpha\n\ndef consume_alpha(value):\n    return value\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_alpha.py").write_text(
        "def test_alpha_contract():\n    assert True\n",
        encoding="utf-8",
    )
    for index in range(45):
        body = "x" * 7000
        (root / "pkg" / f"module_{index:02d}.py").write_text(
            f"def stable_helper_{index:02d}():\n    return '{body}'\n",
            encoding="utf-8",
        )
    return scan_repository(root)


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory(prefix="openlocus-b2-author-") as tmp:
        root = Path(tmp)
        records = _synthetic_python_repo(root)
        drafts, exclusions = _build_drafts(
            repo_slot="b2_repo_python_small", language="python", size_band="small",
            repo_slug="example/synthetic-python", records=records, root=root,
        )
        selected = _select_visible_files(
            records=records, drafts=drafts, exclusions=exclusions,
            language="python", size_band="small", repo_slot="b2_repo_python_small",
        )
        tasks, oracles = _materialize_task_oracles(drafts)
        checks.append(("four_tasks_authored", len(tasks) == 4 and len(oracles) == 4))
        checks.append(("small_band_selected", sum(row.bytes for row in selected) >= 256 * 1024))
        checks.append(("two_step_relation", sum(bool(row.support_relations) for row in oracles) == 1))
        checks.append(("negative_spans", all(len(row.negative_spans) >= 2 for row in oracles)))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    bad_plan = {"schema_version": B2_CANDIDATE_PLAN_SCHEMA, "slots": []}
    try:
        _validate_candidate_plan(bad_plan)
        plan_rejected = False
    except B2AuthorError:
        plan_rejected = True
    checks.append(("incomplete_plan_rejected", plan_rejected))
    checks.append(("repo_identity_query_rejected", not _query_safe("FlaskResolver", "pallets/flask")))
    try:
        _choose_negatives(
            [SymbolDef("Only", "a.py", 1, "type")],
            [B2Span("a.py", 1, 1)], "Only", "fault",
        )
        negatives_rejected = False
    except B2AuthorError:
        negatives_rejected = True
    checks.append(("insufficient_negatives_rejected", negatives_rejected))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B2AuthorError", "B2_CANDIDATE_PLAN_SCHEMA", "B2_AUTHOR_VERSION",
    "prepare_private_manifests", "freeze_private_manifests",
    "run_self_test", "run_fault_test",
]
