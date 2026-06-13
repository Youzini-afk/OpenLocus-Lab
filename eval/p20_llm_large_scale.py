#!/usr/bin/env python3
"""P20-LS bounded LLM large-scale eval harness.

P20-LS is an eval-only Python script. It does not change Rust core or
EvidenceCore. Default mode is offline deterministic; remote LLM access is
opt-in only with explicit flags, environment variables, and policy checks.

Phases:
- ls0: safety-gate validation
- ls1: LLM-derived query-alias generation + alias-expanded retrieval matrix
- ls3: public/private stress-label split generation
- all: runs all phases

Safety:
- Never stores raw prompt or raw LLM response on disk.
- LS1 remote prompts contain only public task fields (repo_id, test_id, query).
- LS3 stress uses fixed public failure-cluster names; generated labels are
  private and explicitly tagged not_promotion_evidence / not_human_verified.
- Drops remote records where JSON schema is invalid or not_evidence != true.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Existing helper imports where sensible ─────────────────────────────

try:
    import score as score_mod  # type: ignore
except Exception:  # pragma: no cover -
    sys.path.append(str(Path(__file__).resolve().parent))
    import score as score_mod  # type: ignore

_EVAL_DIR = Path(__file__).resolve().parent

try:
    from r32_embedding_view_bakeoff import (
        load_jsonl,
        validate_public_tasks,
        write_json,
        load_repo_lock,
        make_self_test_inputs,
        positive_env_int,
        safe_reason_token,
        PUBLIC_TASK_FIELDS,
        PRIVATE_FIELD_DENYLIST,
    )
except Exception as exc:  # pragma: no cover - fallback for standalone use
    sys.path.insert(0, str(_EVAL_DIR))
    try:
        from r32_embedding_view_bakeoff import (
            load_jsonl,
            validate_public_tasks,
            write_json,
            load_repo_lock,
            make_self_test_inputs,
            positive_env_int,
            safe_reason_token,
            PUBLIC_TASK_FIELDS,
            PRIVATE_FIELD_DENYLIST,
        )
    except Exception as exc2:
        raise RuntimeError(f"Failed to import r32 helpers: {exc}; {exc2}") from exc2

try:
    from r29_r26_stress_matrix import (
        validate_repo_lock as r29_validate_repo_lock,
        compute_normalized_manifest_sha,
        rrf_fuse_predictions,
        rrf_fuse_three_predictions,
        NEGATIVE_NOISE_MARKERS,
        COMMON_WORDS,
        is_negative_noise_query,
        is_vague_multi_word_query,
        is_compound_snake_case_noise,
        file_sha256,
        SOURCE_EXTENSIONS as R29_SOURCE_EXTENSIONS,
        SKIP_DIR_NAMES as R29_SKIP_DIR_NAMES,
    )
except Exception as exc:  # pragma: no cover
    sys.path.insert(0, str(_EVAL_DIR))
    try:
        from r29_r26_stress_matrix import (
            validate_repo_lock as r29_validate_repo_lock,
            compute_normalized_manifest_sha,
            rrf_fuse_predictions,
            rrf_fuse_three_predictions,
            is_negative_noise_query,
            is_vague_multi_word_query,
            is_compound_snake_case_noise,
            file_sha256,
            SOURCE_EXTENSIONS as R29_SOURCE_EXTENSIONS,
            SKIP_DIR_NAMES as R29_SKIP_DIR_NAMES,
        )
    except Exception as exc2:
        raise RuntimeError(f"Failed to import r29 helpers: {exc}; {exc2}") from exc2

# ── Constants ──────────────────────────────────────────────────────────

SCHEMA_VERSION = "p20-llm-large-report-v1"
ALIAS_SCHEMA_VERSION = "llm-derived-v1"
ALIAS_KIND = "query_aliases"
ALIAS_PROMPT_VERSION = "p20-ls1-query-alias-v1"
STRESS_LABEL_SCHEMA_VERSION = "p20-ls3-stress-v1"

PUBLIC_STRESS_FIELDS = {"test_id", "repo_id", "query", "public_version", "source"}

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),
    re.compile(r"AKIA[A-Z0-9]{16}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*[A-Za-z0-9_/+=@-]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]

ALIAS_TOP_LEVEL_FIELDS = {
    "schema_version",
    "kind",
    "derived_id",
    "model_id",
    "prompt_version",
    "temperature",
    "source_ref",
    "input_data_level",
    "not_evidence",
    "test_id",
    "repo_id",
    "query_sha",
    "items",
}

# Alias scan is narrower: aliases are short query expansion strings, so we only
# flag values that look like real credential literals rather than ordinary words.
ALIAS_SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{36,}"),
    re.compile(r"\bAKIA[A-Z0-9]{16}"),
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*[A-Za-z0-9_/+=@-]{8,}"),
]

LS3_FAILURE_CLUSTERS = [
    "DENSE_FILE_RIGHT_SPAN_WRONG",
    "DENSE_MODULE_RIGHT_FUNCTION_WRONG",
    "DENSE_TEST_SOURCE_CONFUSION",
    "DENSE_DOC_SOURCE_CONFUSION",
    "DENSE_FRONTEND_BACKEND_CONFUSION",
    "DENSE_SAME_NAME_SYMBOL_CONFUSION",
    "RRF_INHERITED_BM25_FALSE_POSITIVE",
    "GUARD_RECALL_KILL",
    "SYMBOL_EXTRACTION_MISS",
    "REGEX_NORMALIZATION_BUG",
    "GRAPH_ADDS_NO_GOLD",
]

LS1_STRATEGIES = [
    "regex_original",
    "regex_llm_aliases",
    "bm25_original",
    "bm25_llm_aliases",
    "rrf_original",
    "rrf_llm_aliases",
    "query_noise_guard",
    "query_noise_guard_plus_llm_aliases_supporting",
]

DEFAULT_MODEL_ID = "offline_deterministic"
MAX_NATURAL_ALIASES = 5
MAX_IDENTIFIER_ALIASES = 5
MAX_PATH_HINTS = 3
MAX_NEGATIVE_HINTS = 3
MAX_ALIAS_QUERIES = 5
MAX_ALIAS_TEXT_CHARS = 120

EMPTY_ALIAS_ITEMS = {
    "natural_aliases": [],
    "identifier_aliases": [],
    "path_hints": [],
    "negative_clarification_hints": [],
}

REMOTE_ALIAS_FIELDS = {
    "not_evidence",
    "natural_aliases",
    "identifier_aliases",
    "path_hints",
    "negative_clarification_hints",
}
FORBIDDEN_REMOTE_ALIAS_FIELDS = {
    "evidence",
    "gold",
    "gold_spans",
    "citation_validity",
    "promotion_ready",
    "default_should_change",
    "router",
    "route",
    "judge",
    "verdict",
    "confidence",
}

# ── Provider config ────────────────────────────────────────────────────


def remote_llm_enabled(args: argparse.Namespace) -> tuple[bool, str | None]:
    """Return (enabled, reason_if_disabled) for remote LLM mode."""
    if args.provider != "openai-compatible":
        return False, "provider not openai-compatible"
    if not args.allow_remote:
        return False, "--allow-remote not set"
    if os.environ.get("OPENLOCUS_LLM_WORKFLOW_DISPATCH") != "1":
        return False, "OPENLOCUS_LLM_WORKFLOW_DISPATCH != 1"
    if os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        return False, "remote LLM allowed only from workflow_dispatch in GitHub Actions"
    if os.environ.get("OPENLOCUS_ALLOW_REMOTE") != "1":
        return False, "OPENLOCUS_ALLOW_REMOTE != 1"
    base_url = os.environ.get("OPENLOCUS_LLM_BASE_URL")
    api_key = os.environ.get("OPENLOCUS_LLM_API_KEY")
    model = os.environ.get("OPENLOCUS_LLM_MODEL")
    if not base_url or not api_key or not model:
        return False, "missing OPENLOCUS_LLM_BASE_URL/API_KEY/MODEL"
    return True, None


class RemoteLLMProviderError(RuntimeError):
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


def _post_chat_completion(
    messages: list[dict[str, str]],
    temperature: float,
) -> dict[str, Any]:
    base_url = os.environ.get("OPENLOCUS_LLM_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("OPENLOCUS_LLM_API_KEY", "")
    model = os.environ.get("OPENLOCUS_LLM_MODEL", "")
    url = base_url + "/chat/completions"
    retries = positive_env_int("OPENLOCUS_LLM_RETRIES", 2, minimum=0, maximum=5)
    timeout = positive_env_int("OPENLOCUS_LLM_TIMEOUT_SEC", 90, minimum=5, maximum=300)

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "OpenLocus/0.1 (research harness)",
        },
        method="POST",
    )

    last_error: RemoteLLMProviderError | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - explicit opt-in
                body = json.loads(resp.read().decode("utf-8"))
            choice = body.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "{}")
            parsed = json.loads(content)
            return parsed
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
            except json.JSONDecodeError:
                pass
            retriable = exc.code == 429 or 500 <= exc.code < 600
            last_error = RemoteLLMProviderError(
                f"provider_http_{exc.code}",
                http_status=exc.code,
                provider_code=provider_code,
                provider_error_type=provider_error_type,
                retriable=retriable,
            )
        except TimeoutError:
            last_error = RemoteLLMProviderError("provider_timeout", retriable=True)
        except urllib.error.URLError as exc:
            reason_class = type(exc.reason).__name__ if getattr(exc, "reason", None) is not None else "unknown"
            last_error = RemoteLLMProviderError(
                "provider_url_error",
                provider_error_type=safe_reason_token(reason_class),
                retriable=True,
            )
        except json.JSONDecodeError:
            last_error = RemoteLLMProviderError("provider_invalid_json", retriable=True)

        if last_error is None or not last_error.retriable or attempt >= retries:
            break
        time.sleep(min(8.0, 0.5 * (2**attempt)))

    assert last_error is not None
    raise last_error


def _validated_remote_alias_record(
    task: dict[str, Any],
    model_id: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Call remote LLM for alias record. Returns (record, usage_diag)."""
    public = {
        k: v for k, v in task.items()
        if k in PUBLIC_TASK_FIELDS
    }
    query = public.get("query", "")
    test_id = public.get("test_id") or public.get("task_id") or "?"
    repo_id = public.get("repo_id", "")

    messages = [
        {
            "role": "system",
            "content": (
                "You generate a JSON object with query aliases for a code retrieval task. "
                "The output must conform exactly to the requested schema and set not_evidence to true. "
                "Do not include raw source code, secret values, or confidence scores. "
                "Do not treat this output as evidence or a label; it is only query expansion material."
            ),
        },
        {
            "role": "user",
            "content": (
                f"task public fields: repo_id={repo_id}, test_id={test_id}, query={query!r}\n"
                "Generate these arrays of short strings:\n"
                "- natural_aliases: 3-5 natural-language paraphrases of the query\n"
                "- identifier_aliases: 0-5 identifier variants (camelCase, snake_case, kebab-case, plural, acronym)\n"
                "- path_hints: 0-3 likely file-path fragments or directory hints\n"
                "- negative_clarification_hints: 0-3 phrases that clarify what the query is NOT asking for\n"
                "Respond with a JSON object: "
                '{"not_evidence": true, "natural_aliases": [...], "identifier_aliases": [...], '
                '"path_hints": [...], "negative_clarification_hints": [...]}'
            ),
        },
    ]

    t0 = time.time()
    try:
        parsed = _post_chat_completion(messages, temperature=0.0)
    except RemoteLLMProviderError as exc:
        return None, {
            "call_succeeded": False,
            **exc.as_public_dict(),
            "latency_ms": int((time.time() - t0) * 1000),
            "tokens_sent_chars": len(messages[1]["content"]),
            "tokens_received_chars": 0,
        }

    diag = {
        "call_succeeded": True,
        "latency_ms": int((time.time() - t0) * 1000),
        "tokens_sent_chars": len(messages[1]["content"]),
        "tokens_received_chars": len(json.dumps(parsed)),
    }

    if not isinstance(parsed, dict):
        diag["schema_error"] = "top_level_not_object"
        return None, diag

    extra = set(parsed) - REMOTE_ALIAS_FIELDS
    if extra:
        diag["schema_error"] = f"unexpected_fields:{','.join(sorted(extra))}"
        return None, diag

    forbidden = set(parsed) & FORBIDDEN_REMOTE_ALIAS_FIELDS
    if forbidden:
        diag["schema_error"] = f"forbidden_fields:{','.join(sorted(forbidden))}"
        return None, diag

    if parsed.get("not_evidence") is not True:
        diag["schema_error"] = "not_evidence_missing_or_false"
        return None, diag

    required = ["natural_aliases", "identifier_aliases", "path_hints", "negative_clarification_hints"]
    for key in required:
        value = parsed.get(key)
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            diag["schema_error"] = f"invalid_array_field:{key}"
            return None, diag
        if any(not _safe_alias_text(x) for x in value):
            diag["schema_error"] = f"unsafe_alias_text:{key}"
            return None, diag

    return parsed, diag


# ── Alias generation (offline deterministic + remote) ──────────────────


def _input_sha(task: dict[str, Any], prompt_version: str, model_id: str) -> str:
    normalizer = {
        "test_id": task.get("test_id") or task.get("task_id") or "",
        "repo_id": task.get("repo_id", ""),
        "query": task.get("query", ""),
        "prompt_version": prompt_version,
        "model_id": model_id,
    }
    return hashlib.sha256(
        json.dumps(normalizer, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _normalize_id(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    # camelCase / PascalCase
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", raw)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
    return s2


def _safe_alias_text(value: str) -> bool:
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    if not stripped or len(stripped) > MAX_ALIAS_TEXT_CHARS:
        return False
    if "\n" in stripped or "\r" in stripped:
        return False
    if any(p.search(stripped) for p in ALIAS_SECRET_PATTERNS):
        return False
    if re.search(r"\b(def|fn|class|function|struct|impl)\s+[A-Za-z_][A-Za-z0-9_]{2,}", stripped):
        return False
    return True


def _clip_unique_aliases(values: Any, limit: int) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        text = value.strip()
        key = text.lower()
        if key in seen or not _safe_alias_text(text):
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def _normalize_alias_items(items: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "natural_aliases": _clip_unique_aliases(items.get("natural_aliases", []), MAX_NATURAL_ALIASES),
        "identifier_aliases": _clip_unique_aliases(items.get("identifier_aliases", []), MAX_IDENTIFIER_ALIASES),
        "path_hints": _clip_unique_aliases(items.get("path_hints", []), MAX_PATH_HINTS),
        "negative_clarification_hints": _clip_unique_aliases(
            items.get("negative_clarification_hints", []), MAX_NEGATIVE_HINTS
        ),
    }


def scan_public_task_values(tasks: list[dict[str, Any]]) -> list[str]:
    """Find secret-like values in fields that may be sent to remote/public artifacts."""
    issues: list[str] = []
    for task in tasks:
        tid = task.get("test_id") or task.get("task_id") or "?"
        for key in ["repo_id", "test_id", "task_id", "query"]:
            value = str(task.get(key, ""))
            if any(p.search(value) for p in SECRET_PATTERNS):
                issues.append(f"task {tid}: secret-like value in {key}")
        extra_private = sorted(set(task) & set(PRIVATE_FIELD_DENYLIST))
        if extra_private:
            issues.append(f"task {tid}: private fields present {extra_private}")
    return issues


def load_repo_lock_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    if path.suffix == ".jsonl":
        return load_jsonl(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        if "repo_id" in raw and "source" in raw:
            return [raw]
        rows = raw.get("repos", raw.get("repositories", []))
        return rows if isinstance(rows, list) else []
    return []


def repo_lock_validation_report(path: Path, self_repo_roots: dict[str, Path]) -> dict[str, Any]:
    rows = load_repo_lock_rows(path)
    repo_ids = [str(row.get("repo_id", "")) for row in rows if isinstance(row, dict)]
    rows_by_id = {str(row.get("repo_id", "")): row for row in rows if isinstance(row, dict)}
    locked = [row for row in rows_by_id.values() if row.get("content_manifest_sha")]
    if self_repo_roots and not locked:
        return {
            "repo_lock_path": str(path),
            "repo_count": len(repo_ids),
            "manifest_validation": "self_test_no_manifest_lock",
            "issues": [],
            "info": [],
        }
    if not locked:
        return {
            "repo_lock_path": str(path),
            "repo_count": len(repo_ids),
            "manifest_validation": "not_available_missing_content_manifest_sha",
            "issues": ["repo lock lacks content_manifest_sha; manifest validation skipped"],
            "info": [],
        }
    issues, info = r29_validate_repo_lock(rows_by_id)
    return {
        "repo_lock_path": str(path),
        "repo_count": len(repo_ids),
        "manifest_validation": "r29_content_manifest_sha",
        "issues": issues,
        "info": info[:10],
    }


def _make_offline_aliases(query: str) -> dict[str, list[str]]:
    """Deterministic alias generator; no LLM, no source code access."""
    q = query.strip()
    lower = q.lower()

    # Natural aliases
    natural = []
    tokens = [t for t in re.split(r"[^a-zA-Z0-9]+", q) if t]
    if "config" in lower:
        natural.append(f"configuration setting for {q}")
        natural.append(f"{q} setup value")
    if "handler" in lower:
        natural.append(f"request handler implementing {q}")
    if "lookup" in lower:
        natural.append(f"lookup function for {q.replace('lookup', '').strip()}")
    if "route" in lower:
        natural.append(f"router endpoint for {q}")
    if "test" in lower:
        natural.append(f"unit test covering {q}")
    if not natural:
        natural.append(f"implementation of {q}")
        natural.append(f"{q} function or method")

    # Identifier aliases
    identifiers = set()
    base = "".join(tokens)
    if base:
        identifiers.add(base)
        identifiers.add("_".join(tokens).lower())
        identifiers.add("-".join(tokens).lower())
        if tokens:
            camel = tokens[0].lower() + "".join(t.capitalize() for t in tokens[1:])
            pascal = "".join(t.capitalize() for t in tokens)
            identifiers.add(camel)
            identifiers.add(pascal)

    # Path hints
    path_hints = []
    if "test" in lower or "spec" in lower:
        path_hints.append("tests/")
    if "config" in lower or "yaml" in lower or "json" in lower:
        path_hints.append("config/")
        path_hints.append("*.yaml")
        path_hints.append("*.json")
    if "handler" in lower or "route" in lower:
        path_hints.append("src/")
        path_hints.append("routes/")
    if not path_hints:
        path_hints.append("src/")

    # Negative clarification hints
    negative = []
    if "config" in lower:
        negative.append("not runtime implementation logic")
    if "test" in lower:
        negative.append("not production source implementation")
    else:
        negative.append("not test-only fixtures")
    negative.append("not unrelated module with similar name")
    negative.append("not a renamed or deleted symbol")

    return _normalize_alias_items({
        "natural_aliases": list(dict.fromkeys(natural)),
        "identifier_aliases": list(dict.fromkeys(identifiers)),
        "path_hints": list(dict.fromkeys(path_hints)),
        "negative_clarification_hints": list(dict.fromkeys(negative)),
    })


def build_alias_record(
    task: dict[str, Any],
    *,
    model_id: str = DEFAULT_MODEL_ID,
    allow_remote: bool = False,
    remote_stats: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (alias_record, diagnostics). Diagnostics do not include raw prompt/response."""
    if remote_stats is None:
        remote_stats = {"calls": 0, "failures": 0, "cost_estimate": 0.0}

    test_id = task.get("test_id") or task.get("task_id") or "?"
    repo_id = task.get("repo_id", "")
    query = task.get("query", "")

    if allow_remote and model_id != DEFAULT_MODEL_ID:
        parsed, diag = _validated_remote_alias_record(task, model_id)
        remote_stats["calls"] += 1
        if diag.get("call_succeeded"):
            remote_stats["cost_estimate"] += 0.0001  # nominal placeholder
        else:
            remote_stats["failures"] += 1
        if parsed is None:
            # Fail/drop invalid or unavailable remote records closed: keep a
            # valid not_evidence wrapper with no aliases rather than silently
            # replacing rejected LLM output with synthetic expansion.
            parsed = dict(EMPTY_ALIAS_ITEMS)
            diag["dropped_remote_aliases"] = True
        else:
            parsed = _normalize_alias_items(parsed)
    else:
        parsed = _normalize_alias_items(_make_offline_aliases(query))
        diag: dict[str, Any] = {"call_succeeded": False, "offline_mode": True}

    derived_id = _input_sha(task, ALIAS_PROMPT_VERSION, model_id)
    record = {
        "schema_version": ALIAS_SCHEMA_VERSION,
        "kind": ALIAS_KIND,
        "derived_id": derived_id,
        "model_id": model_id,
        "prompt_version": ALIAS_PROMPT_VERSION,
        "temperature": 0,
        "source_ref": None,
        "input_data_level": 0,
        "not_evidence": True,
        "test_id": test_id,
        "repo_id": repo_id,
        "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "items": parsed,
    }
    return record, diag


# ── Cache helpers ──────────────────────────────────────────────────────


def cache_path_for(cache_dir: Path, derived_id: str) -> Path:
    return cache_dir / f"{derived_id[:2]}" / f"{derived_id[2:]}.json"


def _task_test_id(task: dict[str, Any]) -> str:
    return str(task.get("test_id") or task.get("task_id") or "?")


def _task_query_sha(task: dict[str, Any]) -> str:
    return hashlib.sha256(str(task.get("query", "")).encode("utf-8")).hexdigest()


def _alias_schema_issues_for_record(
    rec: dict[str, Any],
    *,
    task: dict[str, Any] | None = None,
    model_id: str | None = None,
) -> list[str]:
    tid = str(rec.get("test_id") or rec.get("task_id") or (task and _task_test_id(task)) or "?")
    issues: list[str] = []
    extra = set(rec) - ALIAS_TOP_LEVEL_FIELDS
    if extra:
        issues.append(f"alias {tid}: unexpected top-level fields {sorted(extra)}")
    forbidden = set(rec) & (FORBIDDEN_REMOTE_ALIAS_FIELDS | set(PRIVATE_FIELD_DENYLIST))
    if forbidden:
        issues.append(f"alias {tid}: forbidden top-level fields {sorted(forbidden)}")
    if rec.get("schema_version") != ALIAS_SCHEMA_VERSION:
        issues.append(f"alias {tid}: schema_version mismatch")
    if rec.get("kind") != ALIAS_KIND:
        issues.append(f"alias {tid}: kind mismatch")
    if rec.get("not_evidence") is not True:
        issues.append(f"alias {tid}: not_evidence != true")
    if rec.get("input_data_level", -1) != 0:
        issues.append(f"alias {tid}: input_data_level != 0")
    if rec.get("source_ref") is not None:
        issues.append(f"alias {tid}: source_ref must be null for LS1 query aliases")
    if rec.get("temperature") != 0:
        issues.append(f"alias {tid}: temperature must be 0")
    if rec.get("prompt_version") != ALIAS_PROMPT_VERSION:
        issues.append(f"alias {tid}: prompt_version mismatch")
    if model_id is not None and rec.get("model_id") != model_id:
        issues.append(f"alias {tid}: model_id mismatch")
    if task is not None:
        expected_tid = _task_test_id(task)
        if rec.get("test_id") != expected_tid:
            issues.append(f"alias {tid}: test_id mismatch")
        if rec.get("repo_id") != task.get("repo_id", ""):
            issues.append(f"alias {tid}: repo_id mismatch")
        if rec.get("query_sha") != _task_query_sha(task):
            issues.append(f"alias {tid}: query_sha mismatch")
        expected_id = _input_sha(task, ALIAS_PROMPT_VERSION, str(model_id or rec.get("model_id", "")))
        if rec.get("derived_id") != expected_id:
            issues.append(f"alias {tid}: derived_id mismatch")
    items = rec.get("items", {})
    if not isinstance(items, dict):
        issues.append(f"alias {tid}: items not object")
        return issues
    item_extra = set(items) - set(EMPTY_ALIAS_ITEMS)
    if item_extra:
        issues.append(f"alias {tid}: unexpected item fields {sorted(item_extra)}")
    for key in ["natural_aliases", "identifier_aliases", "path_hints", "negative_clarification_hints"]:
        value = items.get(key)
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            issues.append(f"alias {tid}: invalid items.{key}")
            continue
        for alias in value:
            if not _safe_alias_text(alias):
                issues.append(f"alias {tid}: unsafe alias text in items.{key}")
                break
    return issues


def load_cached_alias(
    cache_dir: Path, derived_id: str, task: dict[str, Any], model_id: str
) -> dict[str, Any] | None:
    path = cache_path_for(cache_dir, derived_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and not _alias_schema_issues_for_record(data, task=task, model_id=model_id):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return None


def write_cached_alias(cache_dir: Path, record: dict[str, Any]) -> None:
    path = cache_path_for(cache_dir, record["derived_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, record)


# ── Local CLI helpers ──────────────────────────────────────────────────


def _run_openlocus_query(
    openlocus: Path | None,
    method: str,
    query: str,
    cwd: Path,
) -> dict[str, Any]:
    """Best-effort openlocus CLI call. Returns evidence list + latency."""
    if not openlocus or not openlocus.exists():
        return {"evidence": [], "latency_ms": 0, "returncode": -1, "stderr": "openlocus not found"}
    if method == "regex":
        cmd = [str(openlocus), "search", "regex", query, "--json"]
    elif method == "bm25":
        cmd = [str(openlocus), "search", "bm25", query, "--json"]
    elif method == "symbol":
        cmd = [str(openlocus), "search", "symbol", query, "--json"]
    elif method == "rrf":
        cmd = [str(openlocus), "retrieve", query, "--json"]
    else:
        return {"evidence": [], "latency_ms": 0, "returncode": -1, "stderr": f"unknown method {method}"}

    t0 = time.perf_counter()
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True, cwd=str(cwd))
    latency_ms = int((time.perf_counter() - t0) * 1000)

    evidence: list[dict[str, Any]] = []
    try:
        raw = json.loads(proc.stdout) if proc.stdout.strip() else []
        if method == "rrf" and isinstance(raw, dict) and "evidence" in raw:
            evidence = raw["evidence"]
        elif isinstance(raw, list):
            evidence = raw
    except json.JSONDecodeError:
        pass

    return {
        "evidence": evidence,
        "latency_ms": latency_ms,
        "returncode": proc.returncode,
        "stderr": proc.stderr[:500] if proc.stderr else "",
    }


def _local_deterministic_search(
    query: str,
    repo_root: Path,
    method: str,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Fallback deterministic text search over repo files (no CLI)."""
    evidence: list[dict[str, Any]] = []
    terms = [t.lower() for t in re.split(r"[^a-zA-Z0-9]+", query) if t and len(t) > 1]
    if not terms:
        terms = [query.lower()]

    ext_filter = R29_SOURCE_EXTENSIONS
    file_sha_cache: dict[str, str] = {}
    matches: list[tuple[float, str, int, int]] = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in R29_SKIP_DIR_NAMES and not d.startswith(".")]
        for fname in sorted(filenames):
            ext = os.path.splitext(fname)[1]
            if ext not in ext_filter:
                continue
            path = Path(dirpath) / fname
            if path.is_symlink():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            lines = text.splitlines()
            rel = str(path.relative_to(repo_root)).replace(os.sep, "/")
            for i, line in enumerate(lines, start=1):
                lower = line.lower()
                score = sum(1 for t in terms if t in lower)
                if score == 0:
                    continue
                if method == "symbol":
                    # Only definition-like lines
                    if not re.search(r"(def\s|fn\s|class\s|function\s|type\s|struct\s|impl\s)", line):
                        continue
                matches.append((score, rel, i, i))

    matches.sort(key=lambda x: (-x[0], x[1], x[2]))
    seen = set()
    for score, rel, start, end in matches[:top_k]:
        key = (rel, start, end)
        if key in seen:
            continue
        seen.add(key)
        rel_path = repo_root / rel
        if rel not in file_sha_cache:
            try:
                file_sha_cache[rel] = file_sha256(rel_path)
            except OSError:
                file_sha_cache[rel] = hashlib.sha256(str(rel_path).encode("utf-8")).hexdigest()
        evidence.append({
            "path": rel,
            "start_line": start,
            "end_line": end,
            "content_sha": file_sha_cache[rel],
            "score": float(score),
            "why": [f"P20 fallback {method}"],
            "channels": [method],
        })
    return evidence


def _materialize_evidence(repo_root: Path, evidence: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    """Ensure candidate evidence has the local evidence contract fields."""
    out: list[dict[str, Any]] = []
    sha_cache: dict[str, str] = {}
    for ev in evidence[:top_k]:
        if not isinstance(ev, dict):
            continue
        path = str(ev.get("path") or "")
        start = int(ev.get("start_line") or 0)
        end = int(ev.get("end_line") or start)
        if not path or start < 1 or end < start:
            continue
        if ".." in Path(path).parts or Path(path).is_absolute():
            continue
        full = repo_root / path
        if not full.exists() or not full.is_file():
            continue
        if path not in sha_cache:
            try:
                sha_cache[path] = file_sha256(full)
            except OSError:
                continue
        mat = dict(ev)
        mat["path"] = path.replace(os.sep, "/")
        mat["start_line"] = start
        mat["end_line"] = end
        mat["content_sha"] = sha_cache[path]
        mat["why"] = list(mat.get("why") or ["P20 candidate_not_fact"])
        mat["channels"] = list(mat.get("channels") or [])
        out.append(mat)
    return out


def run_strategy_query(
    method: str,
    query: str,
    repo_root: Path,
    openlocus: Path | None,
    top_k: int = 10,
) -> dict[str, Any]:
    if openlocus and openlocus.exists():
        result = _run_openlocus_query(openlocus, method, query, repo_root)
        if result["returncode"] == 0:
            result["evidence"] = _materialize_evidence(repo_root, result["evidence"], top_k)
            return result
    if method == "rrf":
        regex = {"evidence": _local_deterministic_search(query, repo_root, "regex", top_k)}
        bm25 = {"evidence": _local_deterministic_search(query, repo_root, "bm25", top_k)}
        symbol = {"evidence": _local_deterministic_search(query, repo_root, "symbol", top_k)}
        return {
            "evidence": _materialize_evidence(
                repo_root, rrf_fuse_three_predictions(regex, bm25, symbol), top_k
            ),
            "latency_ms": 0,
            "returncode": 0,
            "stderr": "",
            "fallback": "local_deterministic_rrf",
        }
    return {
        "evidence": _materialize_evidence(
            repo_root, _local_deterministic_search(query, repo_root, method, top_k), top_k
        ),
        "latency_ms": 0,
        "returncode": 0,
        "stderr": "",
        "fallback": "local_deterministic",
    }


# ── Composite strategy builders ────────────────────────────────────────


def _alias_queries(alias_record: dict[str, Any]) -> list[str]:
    items = alias_record.get("items", {})
    aliases = []
    aliases.extend(items.get("natural_aliases", []))
    aliases.extend(items.get("identifier_aliases", []))
    aliases.extend(items.get("path_hints", []))
    out: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        if not isinstance(alias, str):
            continue
        text = alias.strip()
        key = text.lower()
        if key in seen or not _safe_alias_text(text):
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= MAX_ALIAS_QUERIES:
            break
    return out


def _run_alias_pool(
    methods: list[str],
    queries: list[str],
    repo_root: Path,
    openlocus: Path | None,
    top_k: int,
) -> list[list[dict[str, Any]]]:
    all_evidence: list[list[dict[str, Any]]] = []
    for method in methods:
        for q in queries:
            ev = run_strategy_query(method, q, repo_root, openlocus, top_k)["evidence"]
            all_evidence.append(ev)
    return all_evidence


def _dedupe_evidence(evidence_lists: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for ev_list in evidence_lists:
        for ev in ev_list:
            key = f"{ev.get('path')}:{ev.get('start_line')}:{ev.get('end_line')}"
            if key in seen:
                continue
            seen.add(key)
            out.append(ev)
    return out


def _mark_p20_candidate(ev: dict[str, Any], source: str) -> dict[str, Any]:
    marked = dict(ev)
    marked["candidate_layer"] = "p20_llm_alias_candidate_not_fact"
    marked["candidate_source"] = source
    marked["not_promotion_evidence"] = True
    return marked


def build_original_predictions(
    tasks: list[dict[str, Any]],
    repo_roots: dict[str, Path],
    openlocus: Path | None,
    strategy: str,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    method = strategy.replace("_original", "").replace("_llm_aliases", "")
    predictions: list[dict[str, Any]] = []
    for task in tasks:
        tid = task.get("test_id") or task.get("task_id") or "?"
        repo_id = task.get("repo_id", "")
        query = task.get("query", "")
        root = repo_roots.get(repo_id)
        if root is None:
            predictions.append({
                "task_id": tid,
                "repo_id": repo_id,
                "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                "strategy": strategy,
                "evidence": [],
                "latency_ms": 0,
                "returncode": -1,
            })
            continue
        result = run_strategy_query(method, query, root, openlocus, top_k)
        predictions.append({
            "task_id": tid,
            "repo_id": repo_id,
            "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            "strategy": strategy,
            "evidence": result["evidence"],
            "latency_ms": result["latency_ms"],
            "returncode": result["returncode"],
        })
    return predictions


def build_alias_predictions(
    tasks: list[dict[str, Any]],
    aliases_by_task: dict[str, dict[str, Any]],
    repo_roots: dict[str, Path],
    openlocus: Path | None,
    strategy: str,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    base_method = strategy.replace("_original", "").replace("_llm_aliases", "")
    predictions: list[dict[str, Any]] = []
    for task in tasks:
        tid = task.get("test_id") or task.get("task_id") or "?"
        repo_id = task.get("repo_id", "")
        query = task.get("query", "")
        root = repo_roots.get(repo_id)
        alias_record = aliases_by_task.get(tid, {})
        alias_queries = _alias_queries(alias_record)

        if root is None:
            predictions.append({
                "task_id": tid,
                "repo_id": repo_id,
                "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                "strategy": strategy,
                "evidence": [],
                "latency_ms": 0,
                "returncode": -1,
            })
            continue

        if base_method == "rrf":
            # RRF fuse regex + bm25 + symbol from alias-expanded query pool
            query_pool = [query] + alias_queries
            method_evidence: dict[str, list[dict[str, Any]]] = {}
            for method in ["regex", "bm25", "symbol"]:
                lists = []
                for q in query_pool:
                    source = "original_query" if q == query else "llm_alias_query"
                    lists.append([
                        _mark_p20_candidate(ev, source)
                        for ev in run_strategy_query(method, q, root, openlocus, top_k)["evidence"]
                    ])
                method_evidence[method] = _dedupe_evidence(lists)
            evidence = rrf_fuse_three_predictions(
                {"evidence": method_evidence["regex"]},
                {"evidence": method_evidence["bm25"]},
                {"evidence": method_evidence["symbol"]},
            )
            evidence = [_mark_p20_candidate(ev, ev.get("candidate_source", "original_or_alias_query_pool")) for ev in evidence]
        else:
            # run original + each alias for this single method, dedupe
            lists = [[
                _mark_p20_candidate(ev, "original_query")
                for ev in run_strategy_query(base_method, query, root, openlocus, top_k)["evidence"]
            ]]
            for aq in alias_queries:
                lists.append([
                    _mark_p20_candidate(ev, "llm_alias_query")
                    for ev in run_strategy_query(base_method, aq, root, openlocus, top_k)["evidence"]
                ])
            evidence = _dedupe_evidence(lists)

        predictions.append({
            "task_id": tid,
            "repo_id": repo_id,
            "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            "strategy": strategy,
            "evidence": evidence[:top_k],
            "latency_ms": 0,
            "returncode": 0,
        })
    return predictions


def build_guard_predictions(
    tasks: list[dict[str, Any]],
    aliases_by_task: dict[str, dict[str, Any]] | None,
    repo_roots: dict[str, Path],
    openlocus: Path | None,
    strategy: str,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    include_aliases = aliases_by_task is not None and "plus_llm_aliases" in strategy
    predictions: list[dict[str, Any]] = []
    for task in tasks:
        tid = task.get("test_id") or task.get("task_id") or "?"
        repo_id = task.get("repo_id", "")
        query = task.get("query", "")
        root = repo_roots.get(repo_id)

        if root is None:
            predictions.append({
                "task_id": tid,
                "repo_id": repo_id,
                "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                "strategy": strategy,
                "evidence": [],
                "latency_ms": 0,
                "returncode": -1,
            })
            continue

        # Query noise guard on original query
        noise = (
            is_negative_noise_query(query)
            or is_vague_multi_word_query(query)
            or is_compound_snake_case_noise(query)
        )
        if noise:
            predictions.append({
                "task_id": tid,
                "repo_id": repo_id,
                "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                "strategy": strategy,
                "evidence": [],
                "latency_ms": 0,
                "returncode": 0,
                "route_decision": "query_noise_guard",
            })
            continue

        rrf_evidence = run_strategy_query("rrf", query, root, openlocus, top_k)["evidence"]
        symbol_evidence = run_strategy_query("symbol", query, root, openlocus, top_k)["evidence"]
        regex_evidence = run_strategy_query("regex", query, root, openlocus, top_k)["evidence"]

        top_score = rrf_evidence[0].get("score", 0.0) if rrf_evidence else 0.0
        threshold = 0.0
        if top_score >= threshold and (symbol_evidence or regex_evidence) and rrf_evidence:
            primary = rrf_evidence
            route = "query_noise_plus_rrf_agree_min_0.0"
        else:
            primary = []
            route = "query_noise_plus_rrf_agree_min_0.0_empty"

        # Alias additions as supporting only: cannot create evidence where guard abstained
        supporting: list[dict[str, Any]] = []
        if include_aliases and primary and aliases_by_task:
            alias_record = aliases_by_task.get(tid, {})
            alias_queries = _alias_queries(alias_record)
            alias_pool = _run_alias_pool(["regex", "bm25"], alias_queries, root, openlocus, top_k)
            supporting = _dedupe_evidence([
                [_mark_p20_candidate(ev, "llm_alias_supporting_query") for ev in evs]
                for evs in alias_pool
            ])

        # Supporting items are appended after primary; they never replace empty primary
        evidence = primary + [e for e in supporting if e not in primary][:top_k]
        predictions.append({
            "task_id": tid,
            "repo_id": repo_id,
            "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            "strategy": strategy,
            "evidence": evidence[:top_k],
            "latency_ms": 0,
            "returncode": 0,
            "route_decision": route,
        })
    return predictions


# ── Normalized labels ──────────────────────────────────────────────────


def normalize_labels(labels: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    gold: dict[str, dict[str, Any]] = {}
    for row in labels:
        tid = row.get("test_id") or row.get("task_id")
        if not tid:
            continue
        paths = [span["path"] for span in row.get("gold_spans", [])]
        line_sets = [[int(span["start_line"]), int(span["end_line"])] for span in row.get("gold_spans", [])]
        gold[tid] = {
            **row,
            "task_id": tid,
            "gold_paths": paths,
            "gold_lines": line_sets,
        }
    return gold


# ── Scoring ────────────────────────────────────────────────────────────


def _gold_path_set(label: dict[str, Any]) -> set[str]:
    return set(label.get("gold_paths", []))


def _line_range_set(label: dict[str, Any]) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for span in label.get("gold_spans", []):
        path = span.get("path", "")
        start = span.get("start_line", 0)
        end = span.get("end_line", 0)
        for ln in range(start, end + 1):
            result.add((path, ln))
    return result


def _primary_hit(pred: dict[str, Any], label: dict[str, Any]) -> bool:
    gold_lines = _line_range_set(label)
    if not gold_lines:
        return False
    repo_id = pred.get("repo_id", "")
    for ev in pred.get("evidence", [])[:1]:
        path = ev.get("path", "")
        for ln in range(ev.get("start_line", 0), ev.get("end_line", 0) + 1):
            for gp, gln in gold_lines:
                if (path == gp or path == f"{repo_id}/{gp}") and ln == gln:
                    return True
    return False


def _any_hit(pred: dict[str, Any], label: dict[str, Any]) -> bool:
    gold_lines = _line_range_set(label)
    if not gold_lines:
        return False
    repo_id = pred.get("repo_id", "")
    for ev in pred.get("evidence", []):
        path = ev.get("path", "")
        for ln in range(ev.get("start_line", 0), ev.get("end_line", 0) + 1):
            for gp, gln in gold_lines:
                if (path == gp or path == f"{repo_id}/{gp}") and ln == gln:
                    return True
    return False


def _file_hit(pred: dict[str, Any], label: dict[str, Any]) -> bool:
    gold_paths = _gold_path_set(label)
    repo_id = pred.get("repo_id", "")
    for ev in pred.get("evidence", [])[:1]:
        path = ev.get("path", "")
        for gp in gold_paths:
            if path == gp or path == f"{repo_id}/{gp}":
                return True
    return False


def score_predictions(
    predictions: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    positive_predictions = [p for p in predictions if labels.get(p.get("task_id", ""), {}).get("gold_spans")]
    metrics: dict[str, Any] = {
        "task_count": len(predictions),
        "FileRecall@1": score_mod.file_recall_at_k(predictions, labels, 1),
        "FileRecall@3": score_mod.file_recall_at_k(predictions, labels, 3),
        "FileRecall@5": score_mod.file_recall_at_k(predictions, labels, 5),
        "MRR": score_mod.mrr(predictions, labels),
        "SpanF0.5": score_mod.span_f_beta_at_k(predictions, labels, 10, 0.5),
        "SpanPrecision": score_mod.line_precision_at_k(predictions, labels, 10),
        "SpanRecall": score_mod.line_recall_at_k(predictions, labels, 10),
        "token_waste": score_mod.token_waste_ratio_at_k(predictions, labels, 10),
    }
    metrics["positive_task_count"] = len(positive_predictions)
    metrics["SpanRecall_positive_only"] = (
        score_mod.line_recall_at_k(positive_predictions, labels, 10)
        if positive_predictions
        else None
    )
    if not positive_predictions:
        metrics["SpanRecall"] = None
    return metrics


def compute_delta(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    keys: list[str],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in keys:
        b = baseline.get(key)
        c = candidate.get(key)
        if isinstance(b, (int, float)) and isinstance(c, (int, float)):
            out[key] = round(c - b, 6)
        else:
            out[key] = None
    return out


def compute_metric_delta_by_pair(
    original_metrics: dict[str, dict[str, Any]],
    alias_metrics: dict[str, dict[str, Any]],
    metric: str,
) -> dict[str, Any]:
    pairs = [
        ("regex_original", "regex_llm_aliases"),
        ("bm25_original", "bm25_llm_aliases"),
        ("rrf_original", "rrf_llm_aliases"),
        ("query_noise_guard", "query_noise_guard_plus_llm_aliases_supporting"),
    ]
    out: dict[str, Any] = {}
    for base, alias in pairs:
        b = original_metrics.get(base, {}).get(metric)
        c = alias_metrics.get(alias, {}).get(metric)
        if isinstance(b, (int, float)) and isinstance(c, (int, float)):
            out[f"{alias}_vs_{base}"] = round(c - b, 6)
        else:
            out[f"{alias}_vs_{base}"] = None
    return out


def false_primary_rate(
    predictions: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
) -> float:
    total = 0
    false_primary = 0
    for pred in predictions:
        tid = pred["task_id"]
        label = labels.get(tid)
        if not label:
            continue
        eb = label.get("expected_behavior", "")
        if eb not in ("abstain", "no_primary"):
            continue
        total += 1
        if pred.get("evidence"):
            false_primary += 1
    return false_primary / total if total else 0.0


def no_gold_nonempty_rate(
    predictions: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
) -> float:
    total = 0
    nonempty = 0
    for pred in predictions:
        tid = pred["task_id"]
        label = labels.get(tid)
        if not label:
            continue
        if label.get("gold_spans"):
            continue
        total += 1
        if pred.get("evidence"):
            nonempty += 1
    return nonempty / total if total else 0.0


def hard_negative_hit_rate(
    predictions: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
) -> float:
    total = 0
    hits = 0
    for pred in predictions:
        tid = pred["task_id"]
        label = labels.get(tid)
        if not label:
            continue
        hard = label.get("hard_distractors", [])
        if not hard:
            continue
        total += 1
        hit = False
        for ev in pred.get("evidence", [])[:1]:
            path = ev.get("path", "")
            for ln in range(ev.get("start_line", 0), ev.get("end_line", 0) + 1):
                for hd in hard:
                    if path == hd.get("path", "") and hd.get("start_line", 0) <= ln <= hd.get("end_line", 0):
                        hit = True
                        break
                if hit:
                    break
            if hit:
                break
        if hit:
            hits += 1
    return hits / total if total else 0.0


def false_primary_rate_for_category(
    predictions: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    category: str,
) -> float:
    total = 0
    false_primary = 0
    for pred in predictions:
        label = labels.get(pred["task_id"])
        if not label or label.get("source_category") != category:
            continue
        total += 1
        if pred.get("evidence") and not _primary_hit(pred, label):
            false_primary += 1
    return false_primary / total if total else 0.0


def source_category_rate(
    predictions: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    category: str,
) -> float:
    total = 0
    nonempty = 0
    for pred in predictions:
        tid = pred["task_id"]
        label = labels.get(tid)
        if not label:
            continue
        if label.get("source_category") != category:
            continue
        total += 1
        if pred.get("evidence"):
            nonempty += 1
    return nonempty / total if total else 0.0


def semantic_trap_nonempty_rate(
    predictions: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
) -> float:
    return source_category_rate(predictions, labels, "dense_quiver_trap")


def guard_recall_kill_rate(
    guard_preds: list[dict[str, Any]],
    rrf_preds: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
) -> float | None:
    guard_by_task = {p["task_id"]: p for p in guard_preds}
    rrf_by_task = {p["task_id"]: p for p in rrf_preds}
    denom = 0
    numer = 0
    for tid, label in labels.items():
        if label.get("expected_behavior") != "primary_evidence" or not label.get("gold_spans"):
            continue
        rrf_pred = rrf_by_task.get(tid)
        if not rrf_pred or not _file_hit(rrf_pred, label):
            continue
        denom += 1
        guard_pred = guard_by_task.get(tid)
        if not guard_pred or not _file_hit(guard_pred, label):
            numer += 1
    return numer / denom if denom > 0 else None


def _pred_line_set(pred: dict[str, Any]) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for ev in pred.get("evidence", []):
        path = ev.get("path", "")
        for ln in range(ev.get("start_line", 0), ev.get("end_line", 0) + 1):
            result.add((path, ln))
    return result


def _pred_path_set(pred: dict[str, Any]) -> set[str]:
    return {ev.get("path", "") for ev in pred.get("evidence", [])}


def compute_alias_contribution(
    alias_preds: list[dict[str, Any]],
    baseline_preds: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compute alias-added gold/false files and spans vs baseline."""
    baseline_by_task = {p["task_id"]: p for p in baseline_preds}
    added_gold_file = 0
    added_false_file = 0
    added_gold_span = 0
    added_false_span = 0
    tasks_with_alias_additions = 0

    for pred in alias_preds:
        tid = pred["task_id"]
        label = labels.get(tid)
        if not label:
            continue

        base = baseline_by_task.get(tid, {"evidence": []})
        base_paths = _pred_path_set(base)
        base_lines = _pred_line_set(base)

        alias_paths = _pred_path_set(pred) - base_paths
        alias_lines = _pred_line_set(pred) - base_lines

        if not alias_paths and not alias_lines:
            continue

        tasks_with_alias_additions += 1
        gold_paths = _gold_path_set(label)
        gold_lines = _line_range_set(label)

        for path in alias_paths:
            if gold_paths and any(path == gp or path == f"{label.get('repo_id', '')}/{gp}" for gp in gold_paths):
                added_gold_file += 1
            else:
                added_false_file += 1

        for path, ln in alias_lines:
            if gold_lines and any((path == gp or path == f"{label.get('repo_id', '')}/{gp}") and ln == gln for gp, gln in gold_lines):
                added_gold_span += 1
            else:
                added_false_span += 1

    return {
        "alias_added_gold_file": added_gold_file,
        "alias_added_false_file": added_false_file,
        "alias_added_gold_span": added_gold_span,
        "alias_added_false_span": added_false_span,
        "tasks_with_alias_additions": tasks_with_alias_additions,
    }


def build_repo_identifier_index(repo_roots: dict[str, Path]) -> dict[str, set[str]]:
    indexes: dict[str, set[str]] = {}
    ident_re = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}")
    for repo_id, root in repo_roots.items():
        identifiers: set[str] = set()
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in R29_SKIP_DIR_NAMES and not d.startswith(".")]
            for fname in filenames:
                ext = os.path.splitext(fname)[1]
                if ext not in R29_SOURCE_EXTENSIONS:
                    continue
                path = Path(dirpath) / fname
                rel = str(path.relative_to(root)).replace(os.sep, "/")
                for part in re.split(r"[^A-Za-z0-9_]+", rel):
                    if len(part) > 1:
                        identifiers.add(part.lower())
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for match in ident_re.finditer(text[:200_000]):
                    identifiers.add(match.group(0).lower())
        indexes[repo_id] = identifiers
    return indexes


def compute_fabricated_identifier_rate(
    alias_records: list[dict[str, Any]], repo_identifier_index: dict[str, set[str]]
) -> float:
    total = 0
    fabricated = 0
    for rec in alias_records:
        identifiers = repo_identifier_index.get(rec.get("repo_id", ""), set())
        for alias in rec.get("items", {}).get("identifier_aliases", []):
            total += 1
            norm = _normalize_id(alias).replace("-", "_").lower()
            variants = {alias.lower(), norm, norm.replace("_", ""), norm.replace("_", "-")}
            if not identifiers or not any(v in identifiers for v in variants if v):
                fabricated += 1
    return fabricated / total if total else 0.0


# ── Alias record schema validation ─────────────────────────────────────


def validate_alias_records(records: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    for rec in records:
        issues.extend(_alias_schema_issues_for_record(rec))
    return issues


# ── LS0 safety gate validation ─────────────────────────────────────────


def ls0_validate_safety(
    tasks: list[dict[str, Any]],
    aliases: list[dict[str, Any]],
    report: dict[str, Any],
    remote_enabled: bool,
) -> dict[str, Any]:
    task_value_issues = scan_public_task_values(tasks)
    public_issues = validate_public_tasks(tasks) + task_value_issues
    alias_issues = validate_alias_records(aliases)

    # Scan aliases for raw source or secrets
    secret_hits = 0
    raw_source_hits = 0
    for rec in aliases:
        items = rec.get("items", {})
        for key, values in items.items():
            for value in values:
                text = str(value)
                if any(p.search(text) for p in ALIAS_SECRET_PATTERNS):
                    secret_hits += 1
                if len(text) > 200 or "\n" in text or "def " in text or "fn " in text:
                    raw_source_hits += 1

    forbidden_kinds = {"evidence", "label", "judge", "router", "default", "promotion"}
    bad_alias_kind = any(r.get("kind") in forbidden_kinds for r in aliases)

    result = {
        "remote_explicit_gate_enabled": remote_enabled,
        "public_task_schema_clean": len(public_issues) == 0,
        "public_task_schema_issues": public_issues[:10],
        "run_phase_public_only": len(task_value_issues) == 0,
        "private_labels_not_uploaded": True,
        "raw_source_sent": False,
        "raw_prompt_response_stored": False,
        "llm_outputs_not_evidence_labels_judge_router_default_promotion": not bad_alias_kind,
        "alias_schema_version_coverage": all(r.get("schema_version") == ALIAS_SCHEMA_VERSION for r in aliases),
        "alias_not_evidence_coverage": all(r.get("not_evidence") is True for r in aliases),
        "artifact_secret_scan_clean": secret_hits == 0 and not task_value_issues,
        "artifact_secret_scan_hits": secret_hits,
        "artifact_raw_source_hits": raw_source_hits,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "alias_schema_issues": alias_issues[:10],
    }
    result["ls0_passed"] = (
        result["public_task_schema_clean"]
        and result["run_phase_public_only"]
        and result["private_labels_not_uploaded"]
        and not result["raw_source_sent"]
        and not result["raw_prompt_response_stored"]
        and result["llm_outputs_not_evidence_labels_judge_router_default_promotion"]
        and not result["promotion_ready"]
        and not result["default_should_change"]
        and not result["evidencecore_semantics_changed"]
        and result["artifact_secret_scan_clean"]
        and result["alias_schema_version_coverage"]
        and result["alias_not_evidence_coverage"]
    )
    return result


# ── LS1 run/score ──────────────────────────────────────────────────────


def run_ls1(
    tasks: list[dict[str, Any]],
    repo_roots: dict[str, Path],
    labels_path: Path,
    openlocus: Path | None,
    model_id: str,
    allow_remote: bool,
    remote_enabled: bool,
    cache_dir: Path,
    alias_out: Path,
    top_k: int,
    max_tasks: int | None,
    disable_cache: bool = False,
) -> dict[str, Any]:
    tasks = tasks[:max_tasks] if max_tasks else tasks
    public_task_value_issues = scan_public_task_values(tasks)
    if remote_enabled and public_task_value_issues:
        raise SystemExit("public task secret/private scan failed before remote call")

    alias_records: list[dict[str, Any]] = []
    aliases_by_task: dict[str, dict[str, Any]] = {}
    remote_stats = {"calls": 0, "failures": 0, "cost_estimate": 0.0, "invalid_json": 0, "schema_violation": 0, "not_evidence_missing": 0}

    for task in tasks:
        tid = task.get("test_id") or task.get("task_id") or "?"
        derived_id = _input_sha(task, ALIAS_PROMPT_VERSION, model_id)
        if not disable_cache:
            cached = load_cached_alias(cache_dir, derived_id, task, model_id)
        else:
            cached = None
        if cached:
            record = cached
            diag: dict[str, Any] = {"cached": True}
        else:
            record, diag = build_alias_record(
                task,
                model_id=model_id,
                allow_remote=remote_enabled,
                remote_stats=remote_stats,
            )
            if not disable_cache:
                write_cached_alias(cache_dir, record)
        if diag.get("schema_error"):
            if "invalid_json" in diag["schema_error"]:
                remote_stats["invalid_json"] += 1
            elif "not_evidence" in diag["schema_error"]:
                remote_stats["not_evidence_missing"] += 1
            else:
                remote_stats["schema_violation"] += 1
        alias_records.append(record)
        aliases_by_task[tid] = record

    alias_issues = validate_alias_records(alias_records)
    if alias_issues:
        print(f"WARNING: {len(alias_issues)} alias schema issues; see report", file=sys.stderr)

    # Write alias artifact (no raw prompt/response)
    alias_out.parent.mkdir(parents=True, exist_ok=True)
    with alias_out.open("w", encoding="utf-8") as f:
        for rec in alias_records:
            f.write(json.dumps(rec, sort_keys=True) + "\n")

    # Build predictions
    all_predictions: dict[str, list[dict[str, Any]]] = {}
    for strategy in LS1_STRATEGIES:
        if strategy.startswith("query_noise_guard"):
            aliases = aliases_by_task if "plus_llm_aliases" in strategy else None
            all_predictions[strategy] = build_guard_predictions(
                tasks, aliases, repo_roots, openlocus, strategy, top_k
            )
        elif "_llm_aliases" in strategy:
            all_predictions[strategy] = build_alias_predictions(
                tasks, aliases_by_task, repo_roots, openlocus, strategy, top_k
            )
        else:
            all_predictions[strategy] = build_original_predictions(
                tasks, repo_roots, openlocus, strategy, top_k
            )

    # SCORE phase begins only after alias generation and all retrieval
    # predictions are complete. The RUN phase above never reads labels.
    label_rows = load_jsonl(labels_path)
    labels = normalize_labels(label_rows)

    # Score phase.
    original_metrics: dict[str, dict[str, Any]] = {}
    alias_metrics: dict[str, dict[str, Any]] = {}
    baselines: dict[str, list[dict[str, Any]]] = {}
    for strategy in LS1_STRATEGIES:
        preds = all_predictions[strategy]
        baselines[strategy] = preds
        metrics = score_predictions(preds, labels)
        metrics["primary_false_positive_rate"] = false_primary_rate(preds, labels)
        metrics["no_gold_nonempty_rate"] = no_gold_nonempty_rate(preds, labels)
        metrics["hard_negative_hit_rate"] = hard_negative_hit_rate(preds, labels)
        metrics["semantic_trap_nonempty_rate"] = semantic_trap_nonempty_rate(preds, labels)
        metrics["negative_nonexistent_false_primary_rate"] = false_primary_rate_for_category(
            preds, labels, "negative_nonexistent"
        )

        if strategy == "query_noise_guard":
            metrics["guard_recall_kill_rate"] = guard_recall_kill_rate(
                preds, all_predictions.get("rrf_original", []), labels
            )
        elif strategy == "query_noise_guard_plus_llm_aliases_supporting":
            metrics["guard_recall_kill_rate"] = guard_recall_kill_rate(
                preds, all_predictions.get("rrf_llm_aliases", []), labels
            )
        else:
            metrics["guard_recall_kill_rate"] = None

        if "_llm_aliases" in strategy:
            alias_metrics[strategy] = metrics
        else:
            original_metrics[strategy] = metrics

    # Compute alias-added deltas vs original baselines
    deltas: dict[str, dict[str, Any]] = {}
    contributions: dict[str, dict[str, Any]] = {}
    keys = [
        "FileRecall@1",
        "SpanF0.5",
        "primary_false_positive_rate",
        "no_gold_nonempty_rate",
        "negative_nonexistent_false_primary_rate",
        "token_waste",
    ]
    for base, alias in [
        ("regex_original", "regex_llm_aliases"),
        ("bm25_original", "bm25_llm_aliases"),
        ("rrf_original", "rrf_llm_aliases"),
        ("query_noise_guard", "query_noise_guard_plus_llm_aliases_supporting"),
    ]:
        if base in original_metrics and alias in alias_metrics:
            key = f"{alias}_vs_{base}"
            deltas[key] = compute_delta(original_metrics[base], alias_metrics[alias], keys)
            contributions[key] = compute_alias_contribution(
                all_predictions[alias], all_predictions[base], labels
            )

    # Aggregate help/harm rates over tasks, not just strategy-level deltas.
    task_help = 0
    task_harm = 0
    task_compared = 0
    for base, alias in [
        ("regex_original", "regex_llm_aliases"),
        ("bm25_original", "bm25_llm_aliases"),
        ("rrf_original", "rrf_llm_aliases"),
        ("query_noise_guard", "query_noise_guard_plus_llm_aliases_supporting"),
    ]:
        base_by_task = {p["task_id"]: p for p in all_predictions.get(base, [])}
        for alias_pred in all_predictions.get(alias, []):
            label = labels.get(alias_pred["task_id"])
            base_pred = base_by_task.get(alias_pred["task_id"], {"evidence": []})
            if not label:
                continue
            task_compared += 1
            if _any_hit(alias_pred, label) and not _any_hit(base_pred, label):
                task_help += 1
            if not _primary_hit(alias_pred, label) and _primary_hit(base_pred, label):
                task_harm += 1
            if not label.get("gold_spans") and alias_pred.get("evidence") and not base_pred.get("evidence"):
                task_harm += 1
    alias_help_rate = task_help / task_compared if task_compared else 0.0
    alias_harm_rate = task_harm / task_compared if task_compared else 0.0

    invalid_json_rate = remote_stats["invalid_json"] / remote_stats["calls"] if remote_stats["calls"] else 0.0
    schema_violation_rate = remote_stats["schema_violation"] / remote_stats["calls"] if remote_stats["calls"] else 0.0
    not_evidence_missing_rate = remote_stats["not_evidence_missing"] / remote_stats["calls"] if remote_stats["calls"] else 0.0
    fabricated_identifier_rate = compute_fabricated_identifier_rate(
        alias_records, build_repo_identifier_index(repo_roots)
    )
    pfp_increased = any(
        isinstance(v.get("primary_false_positive_rate"), (int, float))
        and v["primary_false_positive_rate"] > 0
        for v in deltas.values()
    )
    quality_passed = (
        not pfp_increased
        and fabricated_identifier_rate <= 0.5
        and alias_harm_rate <= alias_help_rate
        and sum(c.get("alias_added_gold_span", 0) for c in contributions.values())
        >= sum(c.get("alias_added_false_span", 0) for c in contributions.values())
    )

    return {
        "ls1_completed": True,
        "ls1_safety_passed": not alias_issues and not public_task_value_issues,
        "ls1_quality_passed": quality_passed,
        "model_id": model_id,
        "remote_enabled": remote_enabled and allow_remote,
        "run_phase_read_labels": False,
        "score_phase_read_labels": True,
        "labels_loaded_after_run": True,
        "alias_count": len(alias_records),
        "alias_out": str(alias_out),
        "alias_schema_issues": alias_issues[:10],
        "original_metrics": original_metrics,
        "alias_metrics": alias_metrics,
        "alias_deltas": deltas,
        "alias_contributions": contributions,
        "alias_added_gold_file": sum(c.get("alias_added_gold_file", 0) for c in contributions.values()),
        "alias_added_false_file": sum(c.get("alias_added_false_file", 0) for c in contributions.values()),
        "alias_added_gold_span": sum(c.get("alias_added_gold_span", 0) for c in contributions.values()),
        "alias_added_false_span": sum(c.get("alias_added_false_span", 0) for c in contributions.values()),
        "alias_help_rate": round(alias_help_rate, 6),
        "alias_harm_rate": round(alias_harm_rate, 6),
        "primary_false_positive_delta": {k: v.get("primary_false_positive_rate") for k, v in deltas.items()},
        "guard_recall_kill_delta": compute_metric_delta_by_pair(
            original_metrics, alias_metrics, "guard_recall_kill_rate"
        ),
        "semantic_trap_nonempty_delta": compute_metric_delta_by_pair(
            original_metrics, alias_metrics, "semantic_trap_nonempty_rate"
        ),
        "negative_nonexistent_false_primary_delta": {
            k: v.get("negative_nonexistent_false_primary_rate") for k, v in deltas.items()
        },
        "token_waste_delta": {k: v.get("token_waste") for k, v in deltas.items()},
        "fabricated_identifier_rate": fabricated_identifier_rate,
        "quality_blocking_reasons": [
            reason for reason, blocked in [
                ("primary_false_positive_delta_increased", pfp_increased),
                ("fabricated_identifier_rate_gt_0.5", fabricated_identifier_rate > 0.5),
                ("alias_harm_rate_gt_help_rate", alias_harm_rate > alias_help_rate),
                (
                    "alias_added_false_span_gt_gold_span",
                    sum(c.get("alias_added_false_span", 0) for c in contributions.values())
                    > sum(c.get("alias_added_gold_span", 0) for c in contributions.values()),
                ),
            ]
            if blocked
        ],
        "invalid_json_rate": invalid_json_rate,
        "schema_violation_rate": schema_violation_rate,
        "not_evidence_missing_rate": not_evidence_missing_rate,
        "provider_calls": remote_stats["calls"],
        "provider_cost_estimate": round(remote_stats["cost_estimate"], 8),
        "remote_stats": remote_stats,
        "prediction_counts": {k: len(v) for k, v in all_predictions.items()},
    }


# ── LS3 stress generation ──────────────────────────────────────────────


def generate_ls3_stress_tasks(
    base_tasks: list[dict[str, Any]],
    cluster_names: list[str],
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate public stress tasks and private labels from base public tasks only."""
    stress_types = [
        "semantic_trap",
        "hard_distractor",
        "ambiguous_vague",
        "negative_nonexistent",
        "same_name_symbol",
        "frontend_backend_confusion",
        "test_source_confusion",
        "docs_source_confusion",
        "route_config_trap",
        "api_config_regression",
        "dense_quiver_specific_trap",
    ]
    public_tasks: list[dict[str, Any]] = []
    private_labels: list[dict[str, Any]] = []
    seed_prefix = hashlib.sha256(f"p20-ls3-seed-{seed}".encode("utf-8")).hexdigest()[:8]

    for i, task in enumerate(base_tasks):
        base_test_id = task.get("test_id") or task.get("task_id") or f"base-{i}"
        test_id = f"p20ls3-{seed_prefix}-{i:05d}"
        cluster = cluster_names[i % len(cluster_names)]
        stress_type = stress_types[i % len(stress_types)]
        why_hard = {
            "DENSE_FILE_RIGHT_SPAN_WRONG": "Dense retrieval returns the correct file but wrong line span.",
            "DENSE_MODULE_RIGHT_FUNCTION_WRONG": "Correct module but wrong function within the module.",
            "DENSE_TEST_SOURCE_CONFUSION": "Test code is semantically close to the query; source implementation is required.",
            "DENSE_DOC_SOURCE_CONFUSION": "Doc comments match the query; implementation source is required.",
            "DENSE_FRONTEND_BACKEND_CONFUSION": "Frontend and backend share terms; the backend target is required.",
            "DENSE_SAME_NAME_SYMBOL_CONFUSION": "Multiple symbols share the same name in different scopes.",
            "RRF_INHERITED_BM25_FALSE_POSITIVE": "RRF inherits a false positive from the BM25 channel.",
            "GUARD_RECALL_KILL": "A guard strategy rejects a valid primary-evidence query.",
            "SYMBOL_EXTRACTION_MISS": "The relevant symbol is missed by heuristic symbol extraction.",
            "REGEX_NORMALIZATION_BUG": "Regex normalization matches the wrong token boundary.",
            "GRAPH_ADDS_NO_GOLD": "Graph neighbor expansion adds no gold spans.",
        }[cluster]

        public = {
            "test_id": test_id,
            "repo_id": task.get("repo_id", ""),
            "query": task.get("query", ""),
            "public_version": "p20-ls3-v1",
            "source": "p20-ls3-stress",
        }
        private = {
            "test_id": test_id,
            "base_test_id_sha": hashlib.sha256(str(base_test_id).encode("utf-8")).hexdigest(),
            "repo_id": task.get("repo_id", ""),
            "query": task.get("query", ""),
            "schema_version": STRESS_LABEL_SCHEMA_VERSION,
            "target_failure_cluster": cluster,
            "risk_tag": stress_type,
            "why_this_is_hard": why_hard,
            "expected_behavior_hint": "needs_human_label",
            "label_quality": "synthetic_unverified",
            "not_promotion_evidence": True,
            "not_human_verified": True,
            "gold_spans": [],
            "hard_distractors": [],
            "must_not_primary": [],
        }
        public_tasks.append(public)
        private_labels.append(private)

    return public_tasks, private_labels


def run_ls3(
    tasks: list[dict[str, Any]],
    stress_tasks_out: Path,
    stress_labels_out: Path | None,
    seed: int,
    write_private_labels: bool,
) -> dict[str, Any]:
    public_task_value_issues = scan_public_task_values(tasks)
    if public_task_value_issues:
        raise SystemExit("public task secret/private scan failed before LS3 public stress write")
    public_tasks, private_labels = generate_ls3_stress_tasks(tasks, LS3_FAILURE_CLUSTERS, seed)

    stress_tasks_out.parent.mkdir(parents=True, exist_ok=True)
    with stress_tasks_out.open("w", encoding="utf-8") as f:
        for t in public_tasks:
            f.write(json.dumps(t, sort_keys=True) + "\n")
    if write_private_labels and stress_labels_out is not None:
        stress_labels_out.parent.mkdir(parents=True, exist_ok=True)
        with stress_labels_out.open("w", encoding="utf-8") as f:
            for lab in private_labels:
                f.write(json.dumps(lab, sort_keys=True) + "\n")

    cluster_counts: dict[str, int] = defaultdict(int)
    for lab in private_labels:
        cluster_counts[lab["target_failure_cluster"]] += 1

    # Verify public tasks contain only public fields
    leak_issues: list[str] = []
    for t in public_tasks:
        extra = set(t) - PUBLIC_STRESS_FIELDS
        if extra:
            leak_issues.append(f"public stress task {t['test_id']} has extra fields {sorted(extra)}")

    return {
        "ls3_passed": len(leak_issues) == 0 and not public_task_value_issues,
        "stress_task_count": len(public_tasks),
        "stress_label_count": len(private_labels),
        "stress_tasks_out": str(stress_tasks_out),
        "stress_labels_out": str(stress_labels_out) if write_private_labels and stress_labels_out else None,
        "private_labels_written": write_private_labels and stress_labels_out is not None,
        "private_labels_not_uploaded": not write_private_labels,
        "cluster_counts": dict(sorted(cluster_counts.items())),
        "public_field_leak_issues": leak_issues[:10],
        "private_label_fields_all_present": all(
            lab.get("not_promotion_evidence") is True and lab.get("not_human_verified") is True
            for lab in private_labels
        ),
        "promotion_ready": False,
    }


# ── Docs ───────────────────────────────────────────────────────────────


def write_doc(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# P20-LLM Large-Scale Eval Harness",
        "",
        "P20-LS is an eval-only harness for LLM-derived query aliases and stress-label generation. "
        "It does not modify EvidenceCore or the Rust core. "
        "Default mode is offline deterministic; remote LLM access is opt-in only.",
        "",
        "## Safety summary",
        "",
        f"- schema_version: `{report.get('schema_version')}`",
        f"- promotion_ready: `{report.get('promotion_ready')}`",
        f"- llm_default_allowed: `{report.get('llm_default_allowed')}`",
        f"- llm_direct_evidence_allowed: `{report.get('llm_direct_evidence_allowed')}`",
        f"- remote_enabled: `{report.get('remote_enabled')}`",
        f"- run_phase_public_only: `{report.get('run_phase_public_only')}`",
        f"- raw_prompt_response_stored: `{report.get('raw_prompt_response_stored')}`",
        "",
        "## LS0 safety gates",
        "",
    ]
    ls0 = report.get("ls0", {})
    for key, value in sorted(ls0.items()):
        if isinstance(value, list):
            lines.append(f"- {key}: {value[:3]}{' ...' if len(value) > 3 else ''}")
        else:
            lines.append(f"- {key}: `{value}`")

    lines.extend([
        "",
        "## LS1 alias retrieval matrix",
        "",
        "LLM aliases are candidate/supporting-only and not promotion evidence. "
        "A quality failure does not change defaults.",
        "",
        f"- alias_count: `{report.get('ls1', {}).get('alias_count')}`",
        f"- ls1_safety_passed: `{report.get('ls1', {}).get('ls1_safety_passed')}`",
        f"- ls1_quality_passed: `{report.get('ls1', {}).get('ls1_quality_passed')}`",
        f"- alias_help_rate: `{report.get('ls1', {}).get('alias_help_rate')}`",
        f"- alias_harm_rate: `{report.get('ls1', {}).get('alias_harm_rate')}`",
        f"- fabricated_identifier_rate: `{report.get('ls1', {}).get('fabricated_identifier_rate')}`",
        f"- quality_blocking_reasons: `{report.get('ls1', {}).get('quality_blocking_reasons')}`",
        f"- provider_calls: `{report.get('ls1', {}).get('provider_calls')}`",
        f"- provider_cost_estimate: `{report.get('ls1', {}).get('provider_cost_estimate')}`",
        "",
        "| strategy | FileRecall@1 | SpanF0.5 | PFP | no_gold_nonempty |",
        "|---|---:|---:|---:|---:|",
    ])
    for side in ["original_metrics", "alias_metrics"]:
        for strategy, metrics in (report.get("ls1", {}).get(side, {}) or {}).items():
            lines.append(
                f"| {strategy} | {metrics.get('FileRecall@1')} | {metrics.get('SpanF0.5')} | "
                f"{metrics.get('primary_false_positive_rate')} | {metrics.get('no_gold_nonempty_rate')} |"
            )

    lines.extend([
        "",
        "## LS3 stress split",
        "",
        f"- stress_task_count: `{report.get('ls3', {}).get('stress_task_count')}`",
        f"- stress_label_count: `{report.get('ls3', {}).get('stress_label_count')}`",
        f"- private_labels_written: `{report.get('ls3', {}).get('private_labels_written')}`",
        f"- private_labels_not_uploaded: `{report.get('ls3', {}).get('private_labels_not_uploaded')}`",
        "",
        "| failure cluster | count |",
        "|---|---:|",
    ])
    for cluster, count in sorted((report.get("ls3", {}).get("cluster_counts") or {}).items()):
        lines.append(f"| {cluster} | {count} |")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


# ── Main ───────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=["ls0", "ls1", "ls3", "all"],
        default="all",
        help="Phase to run (default: all)",
    )
    parser.add_argument("--self-test", action="store_true", help="Run on r32 generated self-test inputs")
    parser.add_argument("--repo-lock", type=Path, default=Path("fixtures/r26_auto_stress/repos.lock.jsonl"))
    parser.add_argument("--tasks", type=Path, default=Path("fixtures/r26_auto_stress/tasks/auto_stress.jsonl"))
    parser.add_argument("--labels", type=Path, default=Path("fixtures/r26_auto_stress/labels/auto_stress.jsonl"))
    parser.add_argument("--openlocus", type=Path, default=Path("target/debug/openlocus"))
    parser.add_argument("--provider", default="offline_deterministic", choices=["offline_deterministic", "openai-compatible"])
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--model-id", default=None, help="Override model_id in alias records")
    parser.add_argument("--cache-dir", type=Path, default=Path("artifacts/p20_llm_large/cache/aliases"))
    parser.add_argument("--disable-cache", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("artifacts/p20_llm_large/p20_llm_large_report.json"))
    parser.add_argument("--alias-out", type=Path, default=Path("artifacts/p20_llm_large/ls1_aliases.jsonl"))
    parser.add_argument("--stress-tasks-out", type=Path, default=Path("datasets/p20-llm-stress/tasks/stress_public.jsonl"))
    parser.add_argument("--stress-labels-out", type=Path, default=Path("artifacts/p20_llm_large/private/stress_labels.private.jsonl"))
    parser.add_argument(
        "--write-private-labels",
        action="store_true",
        help="Write LS3 private labels to --stress-labels-out. Default is false to avoid uploading private labels.",
    )
    parser.add_argument("--doc", type=Path, default=Path("docs/p20-llm-large-scale.md"))
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--ls3-seed", type=int, default=42)
    args = parser.parse_args(argv)

    args.openlocus = args.openlocus.resolve()
    out_path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    remote_enabled, remote_disabled_reason = remote_llm_enabled(args)
    model_id = args.model_id or (os.environ.get("OPENLOCUS_LLM_MODEL", "") if remote_enabled else DEFAULT_MODEL_ID)
    if not model_id:
        model_id = DEFAULT_MODEL_ID

    # Resolve input paths / self-test
    if args.self_test:
        tmp_ctx = tempfile.TemporaryDirectory(prefix="openlocus-p20-")
        tmp = Path(tmp_ctx.name)
        repo_lock, tasks_path, labels_path, self_repo_roots = make_self_test_inputs(tmp)
        cache_dir: Path | None = tmp / "aliases_cache" if not args.disable_cache else None
    else:
        tmp_ctx = None
        repo_lock = args.repo_lock
        tasks_path = args.tasks
        labels_path = args.labels
        self_repo_roots = {}
        cache_dir = None if args.disable_cache else args.cache_dir

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": args.phase,
        "provider": args.provider,
        "allow_remote": args.allow_remote,
        "remote_enabled": remote_enabled,
        "remote_disabled_reason": remote_disabled_reason,
        "model_id": model_id,
        "promotion_ready": False,
        "llm_default_allowed": False,
        "llm_direct_evidence_allowed": False,
        "run_phase_public_only": True,
        "labels_loaded_after_run": True,
        "raw_prompt_response_stored": False,
        "raw_source_sent": False,
        "evidencecore_semantics_changed": False,
        "default_should_change": False,
    }

    try:
        tasks = load_jsonl(tasks_path)
        repo_roots = self_repo_roots or load_repo_lock(repo_lock)
        # Validate a subset of repos is present
        repo_roots = {rid: root for rid, root in repo_roots.items() if root.exists()}
        tasks = [t for t in tasks if t.get("repo_id", "") in repo_roots]

        report["input_artifacts"] = {
            "tasks": {"path": str(tasks_path), "sha256": file_sha256(tasks_path) if tasks_path.exists() else None},
            "labels": {"path": str(labels_path), "sha256": file_sha256(labels_path) if labels_path.exists() else None},
            "repo_lock": {"path": str(repo_lock), "sha256": file_sha256(repo_lock) if repo_lock.exists() else None},
        }
        report["repo_lock_validation"] = repo_lock_validation_report(repo_lock, self_repo_roots)

        if args.phase in ("ls0", "all"):
            # Generate minimal deterministic aliases for safety validation
            alias_records = []
            for task in tasks[: args.max_tasks]:
                rec, _ = build_alias_record(task, model_id=model_id, allow_remote=False)
                alias_records.append(rec)
            report["ls0"] = ls0_validate_safety(tasks, alias_records, report, remote_enabled)

        if args.phase in ("ls1", "all"):
            if args.self_test:
                openlocus_path = None  # self-test relies on deterministic fallback
            else:
                openlocus_path = args.openlocus if args.openlocus.exists() else None
            report["ls1"] = run_ls1(
                tasks,
                repo_roots,
                labels_path,
                openlocus_path,
                model_id,
                args.allow_remote,
                remote_enabled,
                cache_dir if cache_dir else Path("/tmp/p20-uncached"),
                args.alias_out,
                args.top_k,
                args.max_tasks,
                disable_cache=args.disable_cache,
            )
            if args.phase == "all" and args.alias_out.exists():
                actual_alias_records = load_jsonl(args.alias_out)
                report["ls0"] = ls0_validate_safety(tasks, actual_alias_records, report, remote_enabled)
                report["ls0"]["actual_alias_artifact_validated"] = True

        if args.phase in ("ls3", "all"):
            report["ls3"] = run_ls3(
                tasks[: args.max_tasks] if args.max_tasks else tasks,
                args.stress_tasks_out,
                args.stress_labels_out,
                args.ls3_seed,
                args.write_private_labels,
            )

        write_json(out_path, report)
        write_doc(report, args.doc)
        print(f"Wrote {out_path}")
        print(f"Wrote {args.doc}")
        if args.phase in ("ls0", "all") and not report.get("ls0", {}).get("ls0_passed"):
            return 1
        return 0
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


if __name__ == "__main__":
    sys.exit(main())
