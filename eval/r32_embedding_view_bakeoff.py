#!/usr/bin/env python3
"""R32 embedding view bakeoff harness.

R32 evaluates *view construction* for dense candidate channels.  The default
provider is a local token-hash mock so the harness is reproducible, offline, and
safe to commit.  Real OpenAI-compatible embeddings are supported only with
explicit `--provider openai-compatible --allow-remote` plus
`OPENLOCUS_ALLOW_REMOTE=1`.

This script preserves RUN/SCORE separation: public tasks are loaded and ranked
first, then private labels are loaded for metrics.  It never writes raw view
text, raw code, raw queries, provider URLs, or API keys to artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import score as score_mod  # type: ignore
except Exception:  # pragma: no cover - direct execution from non-eval cwd
    sys.path.append(str(Path(__file__).resolve().parent))
    import score as score_mod  # type: ignore


SCHEMA_VERSION = "r32-embedding-view-bakeoff-v1"
SOURCE_EXTENSIONS = {
    ".rs", ".py", ".go", ".js", ".mjs", ".jsx", ".ts", ".tsx",
    ".java", ".kt", ".kts", ".cs", ".c", ".h", ".cpp", ".hpp",
    ".cc", ".cxx", ".rb", ".toml", ".yaml", ".yml", ".json", ".ini",
}
REMOTE_SAFE_VIEWS = {"path_plus_symbol"}
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*[^\s]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
SKIP_DIRS = {
    ".git", ".openlocus", "target", "node_modules", "dist", "build",
    ".venv", "venv", "__pycache__", ".next", ".nuxt", "coverage",
}
DEFAULT_VIEWS = [
    "path_plus_symbol",
    "signature_only",
    "signature_plus_doc",
    "ast_header",
    "raw_code_trimmed",
    "comment_docstring",
    "test_name_plus_assert_terms",
    "config_key_plus_context",
    "route_plus_handler_signature",
    "mixed_all_views",
]
PUBLIC_TASK_FIELDS = {"test_id", "task_id", "repo_id", "query", "public_version", "source"}
PRIVATE_FIELD_DENYLIST = {
    "source_category", "risk_public", "intent_guess", "risk_tags",
    "oracle_type", "expected_behavior", "gold_spans", "hard_distractors",
    "must_not_primary", "why_this_is_hard", "which_strategy_it_targets",
}


class RemoteEmbeddingProviderError(RuntimeError):
    """Remote provider failure with sanitized fields safe for CI artifacts."""

    def __init__(
        self,
        reason: str,
        *,
        http_status: int | None = None,
        provider_code: str | None = None,
        provider_error_type: str | None = None,
        retriable: bool = False,
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.http_status = http_status
        self.provider_code = provider_code
        self.provider_error_type = provider_error_type
        self.retriable = retriable

    def as_public_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"reason_code": self.reason}
        if self.http_status is not None:
            data["http_status"] = self.http_status
        if self.provider_code:
            data["provider_code"] = self.provider_code
        if self.provider_error_type:
            data["provider_error_type"] = self.provider_error_type
        return data


def safe_reason_token(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    if re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", text):
        return text
    return "redacted"


def positive_env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


SYMBOL_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("rust", re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)", re.M), "fn"),
    ("rust", re.compile(r"^\s*(?:pub\s+)?(?:struct|enum|trait)\s+(\w+)", re.M), "type"),
    ("python", re.compile(r"^\s*(?:async\s+def|def)\s+(\w+)", re.M), "function"),
    ("python", re.compile(r"^\s*class\s+(\w+)", re.M), "class"),
    ("go", re.compile(r"^func\s+(?:\([^)]*\)\s+)?(\w+)", re.M), "function"),
    ("go", re.compile(r"^type\s+(\w+)\s+(?:struct|interface)", re.M), "type"),
    ("javascript", re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.M), "function"),
    ("javascript", re.compile(r"(?:export\s+)?(?:default\s+)?class\s+(\w+)", re.M), "class"),
    ("typescript", re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.M), "function"),
    ("typescript", re.compile(r"(?:export\s+)?(?:interface|type|class)\s+(\w+)", re.M), "type"),
    ("java", re.compile(r"^\s*(?:public\s+)?(?:class|interface|enum)\s+(\w+)", re.M), "type"),
    ("java", re.compile(r"^\s*(?:public|protected|private)\s+(?:static\s+)?[\w<>\[\], ?]+\s+(\w+)\s*\(", re.M), "method"),
    ("ruby", re.compile(r"^\s*(?:class|module)\s+([A-Z]\w*)", re.M), "type"),
    ("ruby", re.compile(r"^\s*def\s+(?:self\.)?(\w+[!?=]?)", re.M), "method"),
]
COMMENT_RE = re.compile(r"^\s*(#|//|/\*|\*|<!--|\"\"\"|''')")
ASSERT_RE = re.compile(r"\b(assert|expect|should|pytest|describe\(|it\(|test\()\b", re.I)
ROUTE_RE = re.compile(r"(@app\.route|router\.|\.get\(|\.post\(|\.put\(|\.delete\(|Route\(|http\.)", re.I)
CONFIG_RE = re.compile(r"^\s*([A-Za-z_][\w.-]*)\s*[:=]", re.M)
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[A-Z]?[a-z]+|\d+")


@dataclass
class ViewRecord:
    repo_id: str
    view_kind: str
    path: str
    start_line: int
    end_line: int
    content_sha: str
    language: str
    text: str
    data_level: int
    vector: list[float] | None = None

    @property
    def text_sha(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_public_tasks(tasks: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    for task in tasks:
        tid = task.get("test_id") or task.get("task_id") or "?"
        extra = set(task) - PUBLIC_TASK_FIELDS
        leaked = set(task) & PRIVATE_FIELD_DENYLIST
        if extra:
            issues.append(f"public task {tid} has extra fields {sorted(extra)}")
        if leaked:
            issues.append(f"public task {tid} leaks private fields {sorted(leaked)}")
    return issues


def load_repo_lock(path: Path) -> dict[str, Path]:
    repos: dict[str, Path] = {}
    rows = load_jsonl(path) if path.suffix == ".jsonl" else json.loads(path.read_text(encoding="utf-8"))
    if isinstance(rows, dict):
        if "repo_id" in rows and "source" in rows:
            rows = [rows]
        else:
            rows = rows.get("repos", rows.get("repositories", []))
    for row in rows:
        repo_id = row["repo_id"]
        source = row.get("source", {})
        repo_path = Path(source.get("path") or row.get("path") or "")
        if repo_path.exists():
            repos[repo_id] = repo_path.resolve()
    return repos


def ext_to_language(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".rs": "rust", ".py": "python", ".go": "go",
        ".js": "javascript", ".mjs": "javascript", ".jsx": "javascript",
        ".ts": "typescript", ".tsx": "typescript", ".java": "java",
        ".kt": "kotlin", ".kts": "kotlin", ".cs": "csharp",
        ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp",
        ".cc": "cpp", ".cxx": "cpp", ".rb": "ruby",
        ".toml": "config", ".yaml": "config", ".yml": "config",
        ".json": "config", ".ini": "config",
    }.get(ext, "unknown")


def run_scan(openlocus: Path | None, repo_root: Path) -> dict[str, dict[str, Any]]:
    if not openlocus or not openlocus.exists():
        return {}
    completed = subprocess.run(
        [str(openlocus), "scan", "--json"],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip().startswith("["):
        return {}
    return {row["path"]: row for row in json.loads(completed.stdout)}


def fallback_file_sha(path: Path) -> str:
    # Only used when the Rust scanner is unavailable.  R32 reports the hash mode.
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iter_source_files(repo_root: Path, max_files: int | None = None) -> Iterable[Path]:
    emitted = 0
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in sorted(filenames):
            path = Path(dirpath) / fname
            if path.suffix.lower() in SOURCE_EXTENSIONS and not path.is_symlink():
                yield path
                emitted += 1
                if max_files is not None and emitted >= max_files:
                    return


def line_no_from_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def safe_slice(lines: list[str], start: int, end: int) -> str:
    start = max(1, start)
    end = min(len(lines), end)
    return "\n".join(lines[start - 1:end])


def extract_symbols(path: Path, rel: str, language: str, text: str) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    for lang, pattern, kind in SYMBOL_PATTERNS:
        if lang not in {language, "javascript" if language == "typescript" else language}:
            continue
        for m in pattern.finditer(text):
            name = m.group(1)
            line = line_no_from_offset(text, m.start())
            symbols.append({"name": name, "kind": kind, "line": line, "path": rel})
    symbols.sort(key=lambda item: (item["path"], item["line"], item["name"]))
    return symbols


def previous_comment_block(lines: list[str], line: int, max_lines: int = 3) -> str:
    comments: list[str] = []
    idx = line - 2
    while idx >= 0 and len(comments) < max_lines:
        raw = lines[idx]
        if not raw.strip():
            if comments:
                break
            idx -= 1
            continue
        if COMMENT_RE.match(raw):
            comments.append(raw.strip())
            idx -= 1
            continue
        break
    return "\n".join(reversed(comments))


def build_views_for_file(repo_id: str, repo_root: Path, path: Path, scan_row: dict[str, Any] | None) -> dict[str, list[ViewRecord]]:
    rel = str(path.relative_to(repo_root)).replace(os.sep, "/")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {view: [] for view in DEFAULT_VIEWS}
    lines = text.splitlines()
    if not lines:
        return {view: [] for view in DEFAULT_VIEWS}
    language = (scan_row or {}).get("language") or ext_to_language(rel)
    content_sha = (scan_row or {}).get("content_sha") or fallback_file_sha(path)
    symbols = extract_symbols(path, rel, language, text)
    out: dict[str, list[ViewRecord]] = {view: [] for view in DEFAULT_VIEWS}

    if symbols:
        for sym in symbols[:80]:
            line = int(sym["line"])
            header = safe_slice(lines, line, line)
            comment = previous_comment_block(lines, line)
            out["path_plus_symbol"].append(ViewRecord(repo_id, "path_plus_symbol", rel, line, line, content_sha, language, f"path {rel} language {language} symbol {sym['name']} kind {sym['kind']}", 0))
            out["signature_only"].append(ViewRecord(repo_id, "signature_only", rel, line, line, content_sha, language, f"{sym['kind']} {sym['name']} {header.strip()}", 1))
            out["signature_plus_doc"].append(ViewRecord(repo_id, "signature_plus_doc", rel, max(1, line - 3), line, content_sha, language, f"{comment}\n{header}".strip(), 1))
            out["ast_header"].append(ViewRecord(repo_id, "ast_header", rel, line, min(len(lines), line + 2), content_sha, language, safe_slice(lines, line, line + 2), 1))
    else:
        stem = path.stem
        out["path_plus_symbol"].append(ViewRecord(repo_id, "path_plus_symbol", rel, 1, min(3, len(lines)), content_sha, language, f"path {rel} language {language} basename {stem}", 0))

    trimmed = "\n".join(line for line in lines[:60] if line.strip())[:3000]
    if trimmed:
        out["raw_code_trimmed"].append(ViewRecord(repo_id, "raw_code_trimmed", rel, 1, min(60, len(lines)), content_sha, language, trimmed, 1))

    comment_lines = [(i + 1, line.strip()) for i, line in enumerate(lines) if COMMENT_RE.match(line)]
    if comment_lines:
        start = comment_lines[0][0]
        end = comment_lines[min(len(comment_lines), 12) - 1][0]
        out["comment_docstring"].append(ViewRecord(repo_id, "comment_docstring", rel, start, end, content_sha, language, "\n".join(c for _, c in comment_lines[:24])[:2400], 1))

    if re.search(r"(test|spec|_test|\.test|\.spec)", rel, re.I):
        terms = [line.strip() for line in lines if ASSERT_RE.search(line)]
        if terms:
            out["test_name_plus_assert_terms"].append(ViewRecord(repo_id, "test_name_plus_assert_terms", rel, 1, len(lines), content_sha, language, f"test file {rel}\n" + "\n".join(terms[:30]), 1))

    if language == "config" or path.suffix.lower() in {".toml", ".yaml", ".yml", ".json", ".ini"}:
        keys = CONFIG_RE.findall(text)
        if keys:
            out["config_key_plus_context"].append(ViewRecord(repo_id, "config_key_plus_context", rel, 1, min(len(lines), 80), content_sha, language, f"config path {rel} keys {' '.join(keys[:80])}", 1))

    route_terms = [line.strip() for line in lines if ROUTE_RE.search(line)]
    if route_terms:
        first_line = next((i + 1 for i, line in enumerate(lines) if ROUTE_RE.search(line)), 1)
        out["route_plus_handler_signature"].append(ViewRecord(repo_id, "route_plus_handler_signature", rel, first_line, min(len(lines), first_line + 8), content_sha, language, f"route handler path {rel}\n" + "\n".join(route_terms[:24]), 1))

    mixed_inputs = []
    for view in ["path_plus_symbol", "signature_plus_doc", "comment_docstring", "config_key_plus_context", "route_plus_handler_signature"]:
        mixed_inputs.extend(out[view][:2])
    for rec in mixed_inputs[:5]:
        out["mixed_all_views"].append(ViewRecord(repo_id, "mixed_all_views", rec.path, rec.start_line, rec.end_line, rec.content_sha, rec.language, f"{rec.view_kind}\n{rec.text}", rec.data_level))
    return out


def token_hash_embedding(text: str, dims: int = 256) -> list[float]:
    vec = [0.0] * dims
    for token in TOKEN_RE.findall(text.lower()):
        h = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(h[:4], "little") % dims
        sign = 1.0 if h[4] % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm else vec


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def remote_embed_detailed(texts: list[str]) -> tuple[list[list[float]], dict[str, Any]]:
    if os.environ.get("OPENLOCUS_ALLOW_REMOTE") != "1":
        raise RuntimeError("OPENLOCUS_ALLOW_REMOTE must be 1 for remote R32 embedding")
    base_url = os.environ.get("OPENLOCUS_EMBEDDING_BASE_URL")
    api_key = os.environ.get("OPENLOCUS_EMBEDDING_API_KEY")
    model = os.environ.get("OPENLOCUS_EMBEDDING_MODEL")
    dimensions = os.environ.get("OPENLOCUS_EMBEDDING_DIMENSIONS")
    send_dimensions = os.environ.get("OPENLOCUS_EMBEDDING_SEND_DIMENSIONS", "1") != "0"
    if not base_url or not api_key or not model:
        raise RuntimeError("missing OPENLOCUS_EMBEDDING_* remote configuration")
    url = base_url.rstrip("/") + "/embeddings"
    batch_size = positive_env_int("OPENLOCUS_EMBEDDING_BATCH_SIZE", 16, minimum=1, maximum=64)
    retries = positive_env_int("OPENLOCUS_EMBEDDING_RETRIES", 2, minimum=0, maximum=5)
    vectors: list[list[float]] = []

    def post_payload(input_value: str | list[str]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "input": input_value,
            "encoding_format": "float",
        }
        if dimensions and send_dimensions:
            payload["dimensions"] = int(dimensions)
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "OpenLocus/0.1 (OpenAI-compatible research harness)",
            },
            method="POST",
        )
        last_error: RemoteEmbeddingProviderError | None = None
        for attempt in range(retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:  # noqa: S310 - explicit research opt-in
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                raw_body = exc.read().decode("utf-8", errors="ignore")
                provider_code = None
                provider_error_type = None
                try:
                    body = json.loads(raw_body)
                    error_obj = body.get("error") if isinstance(body, dict) else None
                    if isinstance(error_obj, dict):
                        provider_code = safe_reason_token(error_obj.get("code"))
                        provider_error_type = safe_reason_token(error_obj.get("type"))
                    elif isinstance(body, dict):
                        provider_code = safe_reason_token(body.get("code"))
                        provider_error_type = safe_reason_token(body.get("type"))
                except json.JSONDecodeError:
                    pass
                retriable = exc.code == 429 or 500 <= exc.code < 600
                last_error = RemoteEmbeddingProviderError(
                    f"provider_http_{exc.code}",
                    http_status=exc.code,
                    provider_code=provider_code,
                    provider_error_type=provider_error_type,
                    retriable=retriable,
                )
            except TimeoutError:
                last_error = RemoteEmbeddingProviderError("provider_timeout", retriable=True)
            except urllib.error.URLError as exc:
                reason_class = type(exc.reason).__name__ if getattr(exc, "reason", None) is not None else "unknown"
                last_error = RemoteEmbeddingProviderError(
                    "provider_url_error",
                    provider_error_type=safe_reason_token(reason_class),
                    retriable=True,
                )
            except json.JSONDecodeError:
                last_error = RemoteEmbeddingProviderError("provider_invalid_json", retriable=True)
            if last_error is None or not last_error.retriable or attempt >= retries:
                break
            time.sleep(min(8.0, 0.5 * (2**attempt)))
        assert last_error is not None
        raise last_error

    request_count = 0
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        request_count += 1
        body = post_payload(batch if len(batch) > 1 else batch[0])
        items = body.get("data")
        if not isinstance(items, list) or len(items) != len(batch):
            raise RemoteEmbeddingProviderError("provider_response_count_mismatch")
        if all(isinstance(item, dict) and "index" in item for item in items):
            items = sorted(items, key=lambda item: int(item.get("index", 0)))
        for item in items:
            if not isinstance(item, dict) or "embedding" not in item:
                raise RemoteEmbeddingProviderError("provider_response_missing_embedding")
            vectors.append([float(x) for x in item["embedding"]])
    return vectors, {"remote_requests": request_count, "remote_texts": len(texts), "batch_size": batch_size}


def remote_embed(texts: list[str]) -> list[list[float]]:
    vectors, _stats = remote_embed_detailed(texts)
    return vectors


def text_has_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def embed_records(records: list[ViewRecord], provider: str, allow_remote: bool) -> dict[str, Any]:
    started = time.time()
    if provider == "local_token_hash":
        for rec in records:
            rec.vector = token_hash_embedding(rec.text)
        return {"provider": provider, "remote_calls": 0, "latency_ms": int((time.time() - started) * 1000), "status": "ok"}
    if provider == "openai-compatible":
        if not allow_remote:
            return {"provider": provider, "remote_calls": 0, "status": "unavailable", "reason": "requires --allow-remote"}
        unsafe_views = sorted({rec.view_kind for rec in records if rec.view_kind not in REMOTE_SAFE_VIEWS})
        if unsafe_views:
            return {
                "provider": provider,
                "remote_calls": 0,
                "status": "unavailable",
                "reason": "remote R32 is restricted to data-level-0 path_plus_symbol views",
                "blocked_views": unsafe_views,
            }
        if any(rec.data_level > 0 or text_has_secret(rec.text) for rec in records):
            return {
                "provider": provider,
                "remote_calls": 0,
                "status": "unavailable",
                "reason": "remote R32 view blocked by data-level or secret scan",
            }
        try:
            vectors, remote_stats = remote_embed_detailed([rec.text for rec in records])
        except RemoteEmbeddingProviderError as exc:
            return {
                "provider": provider,
                "remote_calls": 0,
                "status": "unavailable",
                "reason": "remote embedding provider unavailable_or_failed",
                **exc.as_public_dict(),
            }
        except Exception as exc:
            return {
                "provider": provider,
                "remote_calls": 0,
                "status": "unavailable",
                "reason": "remote embedding provider unavailable_or_failed",
                "error_type": type(exc).__name__,
            }
        for rec, vector in zip(records, vectors):
            rec.vector = vector
        return {
            "provider": provider,
            "remote_calls": len(records),
            "latency_ms": int((time.time() - started) * 1000),
            "status": "ok",
            **remote_stats,
        }
    return {"provider": provider, "remote_calls": 0, "status": "unavailable", "reason": "unknown provider"}


def normalize_labels(labels: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    gold: dict[str, dict[str, Any]] = {}
    for row in labels:
        tid = row.get("test_id") or row.get("task_id")
        if not tid:
            continue
        spans = row.get("gold_spans", [])
        paths = []
        line_sets = []
        for span in spans:
            paths.append(span["path"])
            line_sets.append([int(span["start_line"]), int(span["end_line"])])
        gold[tid] = {
            **row,
            "task_id": tid,
            "gold_paths": paths,
            "gold_lines": line_sets,
        }
    return gold


def hard_negative_hit(evidence: list[dict[str, Any]], label: dict[str, Any]) -> bool:
    bad = label.get("must_not_primary") or label.get("hard_distractors") or []
    for ev in evidence[:1]:
        for span in bad:
            if ev.get("path") != span.get("path"):
                continue
            if int(ev.get("end_line", 0)) >= int(span.get("start_line", 0)) and int(ev.get("start_line", 0)) <= int(span.get("end_line", 0)):
                return True
    return False


def rank_tasks(tasks: list[dict[str, Any]], records_by_repo: dict[str, list[ViewRecord]], provider: str, top_k: int) -> tuple[list[dict[str, Any]], list[int]]:
    predictions: list[dict[str, Any]] = []
    latencies: list[int] = []
    for task in tasks:
        started = time.time()
        tid = task.get("test_id") or task.get("task_id")
        query = task["query"]
        repo_id = task["repo_id"]
        candidates = [rec for rec in records_by_repo.get(repo_id, []) if rec.vector]
        if provider == "local_token_hash":
            query_vec = token_hash_embedding(f"query {query}")
        else:
            if text_has_secret(query):
                query_vec = []
            else:
                try:
                    query_vec = remote_embed([f"query {query}"])[0]
                except Exception:
                    query_vec = []
        scored = sorted(((cosine(query_vec, rec.vector or []), rec) for rec in candidates), key=lambda x: x[0], reverse=True)
        evidence = []
        for score, rec in scored[:top_k]:
            if score <= 0 and provider == "local_token_hash":
                continue
            evidence.append({
                "path": rec.path,
                "start_line": rec.start_line,
                "end_line": rec.end_line,
                "content_sha": rec.content_sha,
                "score": round(float(score), 6),
                "why": [f"R32 {rec.view_kind} dense candidate", "candidate_not_fact"],
                "channels": ["dense"],
                "meta": {"view_kind": rec.view_kind, "provider": provider, "data_level": rec.data_level, "not_evidence_until_materialized": True},
            })
        latency_ms = int((time.time() - started) * 1000)
        latencies.append(latency_ms)
        predictions.append({
            "task_id": tid,
            "repo_id": repo_id,
            "strategy": f"dense_view_{provider}",
            "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            "evidence": evidence,
            "latency_ms": latency_ms,
            "returncode": 0,
        })
    return predictions, latencies


def percentile(values: list[int], pct: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(math.ceil((pct / 100.0) * len(ordered))) - 1))
    return ordered[idx]


def metrics_for(predictions: list[dict[str, Any]], labels: dict[str, dict[str, Any]], repo_roots: dict[str, Path], latencies: list[int]) -> dict[str, Any]:
    total = len(predictions)
    no_primary = 0
    no_primary_nonempty = 0
    no_gold_nonempty = 0
    hard_neg_hits = 0
    semantic_trap = 0
    semantic_trap_nonempty = 0
    citation_total = 0
    citation_valid = 0
    for pred in predictions:
        label = labels.get(pred["task_id"], {})
        evidence = pred.get("evidence", [])
        if label.get("expected_behavior") != "primary_evidence":
            no_primary += 1
            if evidence:
                no_primary_nonempty += 1
        if not label.get("gold_spans") and evidence:
            no_gold_nonempty += 1
        if evidence and hard_negative_hit(evidence, label):
            hard_neg_hits += 1
        if label.get("source_category") == "dense_quiver_trap":
            semantic_trap += 1
            if evidence:
                semantic_trap_nonempty += 1
        root = repo_roots.get(pred["repo_id"])
        for ev in evidence:
            citation_total += 1
            if root and (root / ev["path"]).exists():
                try:
                    lines = (root / ev["path"]).read_text(encoding="utf-8").splitlines()
                    if 1 <= int(ev["start_line"]) <= int(ev["end_line"]) <= len(lines):
                        citation_valid += 1
                except (OSError, UnicodeDecodeError):
                    pass

    return {
        "task_count": total,
        "FileRecall@1": score_mod.file_recall_at_k(predictions, labels, 1),
        "FileRecall@3": score_mod.file_recall_at_k(predictions, labels, 3),
        "FileRecall@5": score_mod.file_recall_at_k(predictions, labels, 5),
        "MRR": score_mod.mrr(predictions, labels),
        "SpanF0.5": score_mod.span_f_beta_at_k(predictions, labels, 10, 0.5),
        "SpanPrecision": score_mod.line_precision_at_k(predictions, labels, 10),
        "SpanRecall": score_mod.line_recall_at_k(predictions, labels, 10),
        "token_waste": score_mod.token_waste_ratio_at_k(predictions, labels, 10),
        "primary_false_positive_rate": no_primary_nonempty / no_primary if no_primary else 0.0,
        "no_gold_nonempty_rate": no_gold_nonempty / total if total else 0.0,
        "hard_negative_hit_rate": hard_neg_hits / total if total else 0.0,
        "semantic_trap_hit_rate": semantic_trap_nonempty / semantic_trap if semantic_trap else 0.0,
        "abstain_rate": sum(1 for p in predictions if not p.get("evidence")) / total if total else 0.0,
        "weak_candidate_rate": sum(1 for p in predictions if p.get("evidence")) / total if total else 0.0,
        "citation_validity": citation_valid / citation_total if citation_total else 1.0,
        "EvidenceCore_rejection_rate": 1.0 - (citation_valid / citation_total if citation_total else 1.0),
        "latency_p50_ms": percentile(latencies, 50),
        "latency_p95_ms": percentile(latencies, 95),
    }


def load_r30_baseline(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("r29_key_metrics", {})


def delta(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for anchor in ["rrf", "query_noise_plus_rrf_agree_min", "symbol"]:
        base = baseline.get(anchor, {})
        out[f"delta_vs_r29_{'query_noise_guard' if anchor == 'query_noise_plus_rrf_agree_min' else anchor}"] = {
            key: (current.get(key) - base.get(key)) if isinstance(current.get(key), (int, float)) and isinstance(base.get(key), (int, float)) else None
            for key in ["FileRecall@1", "SpanF0.5", "primary_false_positive_rate"]
        }
    return out


def make_self_test_inputs(tmp: Path) -> tuple[Path, Path, Path, dict[str, Path]]:
    repo = tmp / "r32-mini-repo"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "config").mkdir(parents=True)
    (repo / "src" / "lib.py").write_text(
        "# Alpha lookup resolves the primary account path\n"
        "def alpha_lookup(user_id):\n"
        "    return {'user_id': user_id}\n\n"
        "def beta_route_handler(request):\n"
        "    return alpha_lookup(request.user_id)\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_lib.py").write_text(
        "def test_alpha_lookup():\n"
        "    assert alpha_lookup('u1')['user_id'] == 'u1'\n",
        encoding="utf-8",
    )
    (repo / "config" / "service.yaml").write_text("service_name: alpha\ntimeout_ms: 100\n", encoding="utf-8")
    repo_lock = tmp / "repo-lock.jsonl"
    repo_lock.write_text(json.dumps({"repo_id": "r32-mini", "source": {"path": str(repo)}}) + "\n", encoding="utf-8")
    tasks = tmp / "tasks.jsonl"
    labels = tmp / "labels.jsonl"
    task_rows = [
        {"test_id": "r32-001", "repo_id": "r32-mini", "query": "alpha_lookup", "public_version": "0", "source": "r32_self_test"},
        {"test_id": "r32-002", "repo_id": "r32-mini", "query": "timeout_ms config", "public_version": "0", "source": "r32_self_test"},
        {"test_id": "r32-003", "repo_id": "r32-mini", "query": "quantum payment mesh", "public_version": "0", "source": "r32_self_test"},
    ]
    label_rows = [
        {"test_id": "r32-001", "repo_id": "r32-mini", "query": "alpha_lookup", "expected_behavior": "primary_evidence", "source_category": "positive", "gold_spans": [{"path": "src/lib.py", "start_line": 2, "end_line": 3}], "hard_distractors": [], "must_not_primary": []},
        {"test_id": "r32-002", "repo_id": "r32-mini", "query": "timeout_ms config", "expected_behavior": "primary_evidence", "source_category": "config_key", "gold_spans": [{"path": "config/service.yaml", "start_line": 2, "end_line": 2}], "hard_distractors": [], "must_not_primary": []},
        {"test_id": "r32-003", "repo_id": "r32-mini", "query": "quantum payment mesh", "expected_behavior": "no_primary", "source_category": "dense_quiver_trap", "gold_spans": [], "hard_distractors": [], "must_not_primary": []},
    ]
    tasks.write_text("".join(json.dumps(row) + "\n" for row in task_rows), encoding="utf-8")
    labels.write_text("".join(json.dumps(row) + "\n" for row in label_rows), encoding="utf-8")
    return repo_lock, tasks, labels, {"r32-mini": repo}


def run_bakeoff(args: argparse.Namespace) -> dict[str, Any]:
    provider = args.provider
    if provider != "local_token_hash" and not args.allow_remote:
        return {
            "schema_version": SCHEMA_VERSION,
            "provider": provider,
            "provider_status": "unavailable",
            "unavailable_reason": "requires --allow-remote and OPENLOCUS_ALLOW_REMOTE=1",
            "promotion_ready": False,
            "default_should_change": False,
            "not_promotion_evidence": True,
        }

    if args.self_test:
        tmp_ctx = tempfile.TemporaryDirectory(prefix="openlocus-r32-")
        tmp = Path(tmp_ctx.name)
        repo_lock, tasks_path, labels_path, self_repo_roots = make_self_test_inputs(tmp)
    else:
        tmp_ctx = None
        repo_lock, tasks_path, labels_path = args.repo_lock, args.tasks, args.labels
        self_repo_roots = {}

    try:
        tasks = load_jsonl(tasks_path)
        public_issues = validate_public_tasks(tasks)
        if public_issues:
            raise SystemExit("public task validation failed: " + "; ".join(public_issues[:5]))
        views = [v.strip() for v in args.views.split(",") if v.strip()]
        unknown = [v for v in views if v not in DEFAULT_VIEWS]
        if unknown:
            raise SystemExit(f"unknown R32 views: {unknown}")

        # RUN phase: no labels loaded above this line.
        repo_roots = self_repo_roots or load_repo_lock(repo_lock)
        repo_roots = {repo_id: root for repo_id, root in repo_roots.items() if root.exists()}
        tasks = [task for task in tasks if task["repo_id"] in repo_roots]
        all_view_records: dict[str, dict[str, list[ViewRecord]]] = {view: {} for view in views}
        build_summaries: dict[str, Any] = {}
        hash_mode = "openlocus_scan_blake3_if_available_else_sha256"
        for repo_id, root in repo_roots.items():
            scan_map = run_scan(args.openlocus, root)
            for file_path in iter_source_files(root, args.max_files_per_repo):
                rel = str(file_path.relative_to(root)).replace(os.sep, "/")
                built = build_views_for_file(repo_id, root, file_path, scan_map.get(rel))
                for view in views:
                    all_view_records[view].setdefault(repo_id, []).extend(built.get(view, []))

        reports: dict[str, Any] = {}
        baseline = load_r30_baseline(args.r30_baseline)
        labels_loaded_after_run = False
        run_outputs: dict[str, dict[str, Any]] = {}

        for view in views:
            records = [rec for repo_records in all_view_records[view].values() for rec in repo_records[: args.max_records_per_repo]]
            embed_status = embed_records(records, provider, args.allow_remote)
            if embed_status.get("status") != "ok":
                reports[view] = {"status": "unavailable", "reason": embed_status.get("reason"), "metrics": None}
                continue
            records_by_repo: dict[str, list[ViewRecord]] = {}
            for rec in records:
                records_by_repo.setdefault(rec.repo_id, []).append(rec)
            predictions, latencies = rank_tasks(tasks[: args.max_tasks], records_by_repo, provider, args.top_k)
            run_outputs[view] = {
                "records": records,
                "records_by_repo": records_by_repo,
                "predictions": predictions,
                "latencies": latencies,
                "embed_status": embed_status,
            }

        # SCORE phase starts here: labels are loaded only after all RUN outputs
        # (view records, embeddings, and per-task predictions) have been produced.
        label_rows = load_jsonl(labels_path)
        labels_loaded_after_run = True
        labels = normalize_labels(label_rows)

        for view, run_output in run_outputs.items():
            records = run_output["records"]
            records_by_repo = run_output["records_by_repo"]
            predictions = run_output["predictions"]
            latencies = run_output["latencies"]
            embed_status = run_output["embed_status"]
            current = metrics_for(predictions, labels, repo_roots, latencies)
            current["delta_vs_r29_baseline"] = delta(current, baseline)
            current["embedding_cost_estimate"] = 0.0 if provider == "local_token_hash" else None
            current["index_build_time_ms"] = embed_status.get("latency_ms", 0)
            current["vector_store_size"] = len(records)
            current["remote_calls"] = embed_status.get("remote_calls", 0)
            build_summaries[view] = {"records": len(records), "repos": len(records_by_repo), "remote_calls": embed_status.get("remote_calls", 0)}
            reports[view] = {"status": "ok", "metrics": current}

        ranked_views = [
            (view, data["metrics"].get("SpanF0.5", 0.0), data["metrics"].get("primary_false_positive_rate", 1.0))
            for view, data in reports.items() if data.get("status") == "ok" and data.get("metrics")
        ]
        ranked_views.sort(key=lambda item: (item[1], -item[2]), reverse=True)
        best_view = ranked_views[0][0] if ranked_views else None
        worst_view = ranked_views[-1][0] if ranked_views else None
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "provider_status": "ok" if ranked_views else "unavailable",
            "provider_role": "candidate/supporting-only",
            "data_level_max": 1,
            "remote_enabled": provider != "local_token_hash",
            "run_phase_public_only": True,
            "labels_loaded_after_run": labels_loaded_after_run,
            "score_phase_labels_only": True,
            "promotion_ready": False,
            "default_should_change": False,
            "not_promotion_evidence": True,
            "core_changes": False,
            "evidencecore_semantics_changed": False,
            "raw_text_stored": False,
            "raw_query_stored": False,
            "hash_mode": hash_mode,
            "tasks_scored": len(tasks[: args.max_tasks]),
            "repo_count": len(repo_roots),
            "views": views,
            "view_build_summaries": build_summaries,
            "view_results": reports,
            "conclusion": {
                "best_dense_view": best_view,
                "worst_dense_view": worst_view,
                "dense_has_positive_signal": provider != "local_token_hash" and bool(best_view),
                "dense_should_remain_supporting_only": True,
                "promotion_ready": False,
                "note": "local_token_hash is a deterministic view-harness smoke, not semantic embedding quality evidence" if provider == "local_token_hash" else "real embedding run remains candidate/supporting-only",
            },
        }
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


def write_doc(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# R32 Embedding View Bakeoff",
        "",
        "R32 introduces a reusable view bakeoff harness for dense candidate channels. The committed artifact uses the offline `local_token_hash` provider as a safety/reproducibility smoke; real providers require explicit manual opt-in and remain candidate/supporting-only.",
        "",
        "## Safety",
        "",
        f"- provider: `{report.get('provider')}`",
        f"- run_phase_public_only: `{report.get('run_phase_public_only')}`",
        f"- labels_loaded_after_run: `{report.get('labels_loaded_after_run')}`",
        f"- promotion_ready: `{report.get('promotion_ready')}`",
        f"- default_should_change: `{report.get('default_should_change')}`",
        f"- evidencecore_semantics_changed: `{report.get('evidencecore_semantics_changed')}`",
        f"- raw_text_stored: `{report.get('raw_text_stored')}`",
        f"- raw_query_stored: `{report.get('raw_query_stored')}`",
        "",
        "## View Results",
        "",
        "| View | Status | Records | FileRecall@1 | SpanF0.5 | primary_false_positive_rate | citation_validity |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    summaries = report.get("view_build_summaries", {})
    for view, data in report.get("view_results", {}).items():
        metrics = data.get("metrics") or {}
        lines.append(
            f"| {view} | {data.get('status')} | {summaries.get(view, {}).get('records', 0)} | "
            f"{metrics.get('FileRecall@1')} | {metrics.get('SpanF0.5')} | "
            f"{metrics.get('primary_false_positive_rate')} | {metrics.get('citation_validity')} |"
        )
    lines.extend([
        "",
        "## Conclusion",
        "",
        f"- best_dense_view: `{report.get('conclusion', {}).get('best_dense_view')}`",
        f"- worst_dense_view: `{report.get('conclusion', {}).get('worst_dense_view')}`",
        f"- dense_should_remain_supporting_only: `{report.get('conclusion', {}).get('dense_should_remain_supporting_only')}`",
        "- All R32 outputs must report `delta_vs_r29_rrf`, `delta_vs_r29_query_noise_guard`, and `delta_vs_r29_symbol` inside `delta_vs_r29_baseline`.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-lock", type=Path, default=Path("fixtures/r26_auto_stress/repos.lock.jsonl"))
    parser.add_argument("--tasks", type=Path, default=Path("fixtures/r26_auto_stress/tasks/auto_stress.jsonl"))
    parser.add_argument("--labels", type=Path, default=Path("fixtures/r26_auto_stress/labels/auto_stress.jsonl"))
    parser.add_argument("--r30-baseline", type=Path, default=Path("artifacts/r30/baseline_manifest.json"))
    parser.add_argument("--openlocus", type=Path, default=Path("target/debug/openlocus"))
    parser.add_argument("--views", default=",".join(DEFAULT_VIEWS))
    parser.add_argument("--provider", default="local_token_hash", choices=["local_token_hash", "openai-compatible"])
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--max-tasks", type=int, default=200)
    parser.add_argument("--max-files-per-repo", type=int, default=None)
    parser.add_argument("--max-records-per-repo", type=int, default=2000)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--self-test", action="store_true", help="Run a tiny generated repo smoke instead of external corpora")
    parser.add_argument("--out", type=Path, default=Path("artifacts/r32/view_bakeoff_report.json"))
    parser.add_argument("--doc", type=Path, default=Path("docs/r32-embedding-view-bakeoff.md"))
    args = parser.parse_args(argv)
    args.openlocus = args.openlocus.resolve()

    report = run_bakeoff(args)
    write_json(args.out, report)
    write_doc(report, args.doc)
    if report.get("provider_status") == "unavailable":
        print(json.dumps({"status": "unavailable", "reason": report.get("unavailable_reason")}, indent=2))
    else:
        print(f"Wrote {args.out}")
        print(f"Wrote {args.doc}")


if __name__ == "__main__":
    main()
