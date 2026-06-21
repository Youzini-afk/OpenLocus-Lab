#!/usr/bin/env python3
"""Minimal OpenAI-compatible chat helper for B16-C live-provider runs.

This module provides a minimal, shared, **redacted** OpenAI-compatible
chat-completions helper used by `eval/b16c_live_provider_paired_smoke.py`.

Design constraints (binding):

* Remote calls are allowed **only** when the caller passes
  ``allow_remote=True`` AND env ``OPENLOCUS_ALLOW_REMOTE=1``. For CI /
  manual workflow runs the caller may additionally require
  ``OPENLOCUS_LLM_WORKFLOW_DISPATCH=1`` via ``require_workflow_dispatch``.
* Raw prompts, messages, responses, base URLs, API keys, and provider
  payloads are NEVER returned in public diagnostics. The public result
  object exposes ONLY safe aggregate counts (calls attempted /
  succeeded / failed, invalid_json, timeout, latency, numeric provider
  ``usage`` if present, a fixed failure-category enum token).
* Safe failure categories are a fixed enum; raw exception text is
  suppressed.
* No raw model routing prefix is leaked. Callers normalize the model
  display name themselves; this helper never returns the raw model id.

Env vars:

* ``OPENLOCUS_LLM_BASE_URL`` — provider base URL.
* ``OPENLOCUS_LLM_API_KEY`` — provider API key.
* ``OPENLOCUS_LLM_MODEL`` — model id.
* ``OPENLOCUS_ALLOW_REMOTE`` — must be ``1`` for any remote call.
* ``OPENLOCUS_LLM_WORKFLOW_DISPATCH`` — must be ``1`` for CI / manual
  workflow runs when the caller sets ``require_workflow_dispatch=True``.
* ``OPENLOCUS_LLM_RETRIES`` — optional retry count (0-5, default 2).
* ``OPENLOCUS_LLM_TIMEOUT_SEC`` — optional per-call timeout (5-300s,
  default 90).

Run self-test (no network)::

    python3 eval/provider_client.py --self-test
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any, NoReturn

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "provider_client.v1"
GENERATED_BY = "eval/provider_client.py"

# Fixed failure-category enum. Public diagnostics may ONLY use these
# tokens. Raw exception text is NEVER exposed.
FAILURE_CATEGORY_OK = "ok"
FAILURE_CATEGORY_MISSING_ENV = "missing_env"
FAILURE_CATEGORY_REMOTE_NOT_ENABLED = "remote_not_enabled"
FAILURE_CATEGORY_WORKFLOW_DISPATCH_REQUIRED = "workflow_dispatch_required"
FAILURE_CATEGORY_HTTP_4XX = "provider_http_4xx"
FAILURE_CATEGORY_HTTP_5XX = "provider_http_5xx"
FAILURE_CATEGORY_TIMEOUT = "provider_timeout"
FAILURE_CATEGORY_URL_ERROR = "provider_url_error"
FAILURE_CATEGORY_INVALID_JSON = "provider_invalid_json"
FAILURE_CATEGORY_SCHEMA_ERROR = "provider_schema_error"
FAILURE_CATEGORY_UNKNOWN = "provider_unknown_error"

FAILURE_CATEGORIES: frozenset[str] = frozenset(
    {
        FAILURE_CATEGORY_OK,
        FAILURE_CATEGORY_MISSING_ENV,
        FAILURE_CATEGORY_REMOTE_NOT_ENABLED,
        FAILURE_CATEGORY_WORKFLOW_DISPATCH_REQUIRED,
        FAILURE_CATEGORY_HTTP_4XX,
        FAILURE_CATEGORY_HTTP_5XX,
        FAILURE_CATEGORY_TIMEOUT,
        FAILURE_CATEGORY_URL_ERROR,
        FAILURE_CATEGORY_INVALID_JSON,
        FAILURE_CATEGORY_SCHEMA_ERROR,
        FAILURE_CATEGORY_UNKNOWN,
    }
)

# Env var names (never echoed as values; only the names are public).
ENV_BASE_URL = "OPENLOCUS_LLM_BASE_URL"
ENV_API_KEY = "OPENLOCUS_LLM_API_KEY"
ENV_MODEL = "OPENLOCUS_LLM_MODEL"
ENV_ALLOW_REMOTE = "OPENLOCUS_ALLOW_REMOTE"
ENV_WORKFLOW_DISPATCH = "OPENLOCUS_LLM_WORKFLOW_DISPATCH"
ENV_RETRIES = "OPENLOCUS_LLM_RETRIES"
ENV_TIMEOUT = "OPENLOCUS_LLM_TIMEOUT_SEC"

DEFAULT_RETRIES = 2
MIN_RETRIES = 0
MAX_RETRIES = 5
DEFAULT_TIMEOUT_SEC = 90
MIN_TIMEOUT_SEC = 5
MAX_TIMEOUT_SEC = 300


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _positive_env_int(
    name: str, default: int, *, minimum: int, maximum: int
) -> int:
    """Read a positive integer env var clamped to [minimum, maximum]."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def _safe_reason_token(value: Any) -> str | None:
    """Sanitize a provider error reason token (alphanumeric, 1-80 chars)."""
    if value is None:
        return None
    text = str(value)
    if re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", text):
        return text
    return "redacted"


class ProviderCallResult:
    """Safe, redacted result object for one chat-completions call.

    NEVER exposes raw prompt/messages/response/base_url/api_key/provider
    payload. Exposes only:
    * ``parsed``: parsed JSON dict or ``None`` (caller handles in-memory).
    * ``raw_content``: raw response content string (caller may keep in
      memory transiently; never serialized to public artifact by this
      helper).
    * ``latency_ms``: wall-clock latency in milliseconds.
    * ``usage_available``: bool; whether numeric provider ``usage`` was
      returned.
    * ``usage``: ``None`` or ``{prompt, completion, total}`` (ints only)
      when ``usage_available`` is True.
    * ``calls_attempted``: 1 if a network attempt was made else 0.
    * ``calls_succeeded``: 1 if a successful HTTP 200 + JSON parse
      occurred else 0.
    * ``calls_failed``: 1 if attempted but failed else 0.
    * ``invalid_json``: bool; True if the response body or content was
      not valid JSON.
    * ``failure_category``: fixed enum token (never raw exception text).
    * ``http_status``: HTTP status code or ``None``.
    """

    __slots__ = (
        "parsed",
        "raw_content",
        "latency_ms",
        "usage_available",
        "usage",
        "calls_attempted",
        "calls_succeeded",
        "calls_failed",
        "invalid_json",
        "failure_category",
        "http_status",
    )

    def __init__(
        self,
        *,
        parsed: dict[str, Any] | None,
        raw_content: str | None,
        latency_ms: int,
        usage_available: bool,
        usage: dict[str, int] | None,
        calls_attempted: int,
        calls_succeeded: int,
        calls_failed: int,
        invalid_json: bool,
        failure_category: str,
        http_status: int | None,
    ) -> None:
        self.parsed = parsed
        self.raw_content = raw_content
        self.latency_ms = latency_ms
        self.usage_available = usage_available
        self.usage = usage
        self.calls_attempted = calls_attempted
        self.calls_succeeded = calls_succeeded
        self.calls_failed = calls_failed
        self.invalid_json = invalid_json
        self.failure_category = failure_category
        self.http_status = http_status

    def public_summary(self) -> dict[str, Any]:
        """Return a safe, redacted summary dict for public artifacts.

        Excludes raw_content / parsed / any prompt / response / base_url
        / api_key. Returns only aggregate counts and the fixed failure
        category enum token.
        """
        usage_block: dict[str, int] | None = None
        if self.usage_available and isinstance(self.usage, dict):
            usage_block = {
                "prompt_tokens": int(self.usage.get("prompt_tokens", 0)),
                "completion_tokens": int(
                    self.usage.get("completion_tokens", 0)
                ),
                "total_tokens": int(self.usage.get("total_tokens", 0)),
            }
        return {
            "calls_attempted": int(self.calls_attempted),
            "calls_succeeded": int(self.calls_succeeded),
            "calls_failed": int(self.calls_failed),
            "invalid_json": bool(self.invalid_json),
            "latency_ms": int(self.latency_ms),
            "usage_available": bool(self.usage_available),
            "usage": usage_block,
            "failure_category": self.failure_category,
            "http_status": self.http_status,
        }


def _check_remote_enabled(
    *,
    allow_remote: bool,
    require_workflow_dispatch: bool,
) -> tuple[bool, str]:
    """Return (enabled, failure_category_if_disabled).

    failure_category is one of the fixed enum tokens (never raw text).
    """
    if not allow_remote:
        return False, FAILURE_CATEGORY_REMOTE_NOT_ENABLED
    if os.environ.get(ENV_ALLOW_REMOTE) != "1":
        return False, FAILURE_CATEGORY_REMOTE_NOT_ENABLED
    if require_workflow_dispatch and os.environ.get(
        ENV_WORKFLOW_DISPATCH
    ) != "1":
        return False, FAILURE_CATEGORY_WORKFLOW_DISPATCH_REQUIRED
    base_url = os.environ.get(ENV_BASE_URL)
    api_key = os.environ.get(ENV_API_KEY)
    model = os.environ.get(ENV_MODEL)
    if not base_url or not api_key or not model:
        return False, FAILURE_CATEGORY_MISSING_ENV
    return True, FAILURE_CATEGORY_OK


def _parse_usage(body: Any) -> tuple[bool, dict[str, int] | None]:
    """Parse a numeric provider ``usage`` block if present.

    Returns (usage_available, usage_dict_or_None). Only integer-valued
    prompt/completion/total tokens are accepted; otherwise marked not
    available.
    """
    if not isinstance(body, dict):
        return False, None
    usage = body.get("usage")
    if not isinstance(usage, dict):
        return False, None
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    total = usage.get("total_tokens")
    if not (
        isinstance(prompt, int) and isinstance(completion, int)
    ):
        return False, None
    if not isinstance(total, int):
        total = prompt + completion
    return True, {
        "prompt_tokens": int(prompt),
        "completion_tokens": int(completion),
        "total_tokens": int(total),
    }


def chat_completion(
    messages: list[dict[str, str]],
    *,
    allow_remote: bool,
    require_workflow_dispatch: bool = False,
    temperature: float = 0.0,
    json_mode: bool = True,
) -> ProviderCallResult:
    """Call an OpenAI-compatible chat-completions endpoint.

    Remote calls are made ONLY when ``allow_remote=True`` AND env
    ``OPENLOCUS_ALLOW_REMOTE=1`` (and, when
    ``require_workflow_dispatch=True``, env
    ``OPENLOCUS_LLM_WORKFLOW_DISPATCH=1``) AND all of
    ``OPENLOCUS_LLM_BASE_URL`` / ``OPENLOCUS_LLM_API_KEY`` /
    ``OPENLOCUS_LLM_MODEL`` are set.

    Returns a redacted ``ProviderCallResult``. Raw prompt/messages /
    response / base_url / api_key are NEVER in the public summary.

    The ``messages`` argument is read in-memory only; never persisted.

    The ``raw_content`` attribute holds the raw response content string
    in memory only; the caller must NEVER serialize it to a public
    artifact.
    """
    enabled, failure_category = _check_remote_enabled(
        allow_remote=allow_remote,
        require_workflow_dispatch=require_workflow_dispatch,
    )
    if not enabled:
        return ProviderCallResult(
            parsed=None,
            raw_content=None,
            latency_ms=0,
            usage_available=False,
            usage=None,
            calls_attempted=0,
            calls_succeeded=0,
            calls_failed=0,
            invalid_json=False,
            failure_category=failure_category,
            http_status=None,
        )

    base_url = os.environ.get(ENV_BASE_URL, "").rstrip("/")
    api_key = os.environ.get(ENV_API_KEY, "")
    model = os.environ.get(ENV_MODEL, "")
    url = base_url + "/chat/completions"
    retries = _positive_env_int(
        ENV_RETRIES, DEFAULT_RETRIES, minimum=MIN_RETRIES, maximum=MAX_RETRIES
    )
    timeout = _positive_env_int(
        ENV_TIMEOUT,
        DEFAULT_TIMEOUT_SEC,
        minimum=MIN_TIMEOUT_SEC,
        maximum=MAX_TIMEOUT_SEC,
    )

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": float(temperature),
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "OpenLocus/0.1 (research harness)",
        },
        method="POST",
    )

    last_failure = FAILURE_CATEGORY_UNKNOWN
    last_http_status: int | None = None
    last_parsed: dict[str, Any] | None = None
    last_raw_content: str | None = None
    last_usage_available = False
    last_usage: dict[str, int] | None = None
    last_invalid_json = False

    t0 = time.time()
    for attempt in range(retries + 1):
        # Re-build request per attempt (urllib Request is single-use
        # after the body has been sent in some edge cases).
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "OpenLocus/0.1 (research harness)",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - explicit opt-in
                body_bytes = resp.read()
                last_http_status = int(getattr(resp, "status", 200) or 200)
            try:
                body = json.loads(body_bytes.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                last_failure = FAILURE_CATEGORY_INVALID_JSON
                last_invalid_json = True
                continue
            last_invalid_json = False
            last_usage_available, last_usage = _parse_usage(body)
            choice = (
                body.get("choices", [{}])[0]
                if isinstance(body, dict)
                else {}
            )
            content = (
                choice.get("message", {}).get("content", "")
                if isinstance(choice, dict)
                else ""
            )
            last_raw_content = content if isinstance(content, str) else ""
            try:
                parsed = json.loads(last_raw_content)
            except (json.JSONDecodeError, TypeError):
                last_failure = FAILURE_CATEGORY_INVALID_JSON
                last_invalid_json = True
                continue
            if not isinstance(parsed, dict):
                last_failure = FAILURE_CATEGORY_SCHEMA_ERROR
                last_parsed = None
                continue
            last_parsed = parsed
            last_failure = FAILURE_CATEGORY_OK
            break
        except urllib.error.HTTPError as exc:
            last_http_status = exc.code
            # Drain the body but never expose it.
            try:
                exc.read()
            except Exception:
                pass
            if 400 <= exc.code < 500:
                last_failure = FAILURE_CATEGORY_HTTP_4XX
            elif 500 <= exc.code < 600:
                last_failure = FAILURE_CATEGORY_HTTP_5XX
            else:
                last_failure = FAILURE_CATEGORY_UNKNOWN
        except TimeoutError:
            last_failure = FAILURE_CATEGORY_TIMEOUT
        except urllib.error.URLError:
            last_failure = FAILURE_CATEGORY_URL_ERROR
        except Exception:
            # Suppress raw exception text; use fixed category.
            last_failure = FAILURE_CATEGORY_UNKNOWN

        # Retry logic: retry only on retriable categories.
        retriable = last_failure in {
            FAILURE_CATEGORY_HTTP_5XX,
            FAILURE_CATEGORY_TIMEOUT,
            FAILURE_CATEGORY_URL_ERROR,
            FAILURE_CATEGORY_INVALID_JSON,
            FAILURE_CATEGORY_UNKNOWN,
        }
        if not retriable or attempt >= retries:
            break
        time.sleep(min(8.0, 0.5 * (2**attempt)))

    latency_ms = max(0, int((time.time() - t0) * 1000))
    calls_attempted = 1
    calls_succeeded = 1 if last_failure == FAILURE_CATEGORY_OK else 0
    calls_failed = 0 if calls_succeeded else 1

    return ProviderCallResult(
        parsed=last_parsed,
        raw_content=last_raw_content,
        latency_ms=latency_ms,
        usage_available=last_usage_available,
        usage=last_usage,
        calls_attempted=calls_attempted,
        calls_succeeded=calls_succeeded,
        calls_failed=calls_failed,
        invalid_json=last_invalid_json,
        failure_category=last_failure,
        http_status=last_http_status,
    )


# ---------------------------------------------------------------------------
# Self-test (no network)
# ---------------------------------------------------------------------------


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return {"check": name, "passed": bool(ok)}


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run no-network self-test checks for the provider client.

    Covers: failure-category enum fixed; remote gating; missing env
    unavailable; provider diagnostics redaction; usage parsing; safe
    reason token; result object slots; public summary has no raw
    fields.
    """
    checks: list[dict[str, Any]] = []

    # --- Group 1: Failure category enum. ---
    checks.append(
        _check(
            "failure_categories_fixed_enum",
            FAILURE_CATEGORIES
            == {
                "ok",
                "missing_env",
                "remote_not_enabled",
                "workflow_dispatch_required",
                "provider_http_4xx",
                "provider_http_5xx",
                "provider_timeout",
                "provider_url_error",
                "provider_invalid_json",
                "provider_schema_error",
                "provider_unknown_error",
            },
        )
    )
    for cat in FAILURE_CATEGORIES:
        checks.append(
            _check(
                f"failure_category_in_enum_{cat}",
                cat in FAILURE_CATEGORIES,
            )
        )

    # --- Group 2: Remote gating (no network). ---
    # allow_remote=False -> remote_not_enabled.
    r = chat_completion(
        [], allow_remote=False, require_workflow_dispatch=False
    )
    checks.append(
        _check(
            "allow_remote_false_returns_remote_not_enabled",
            r.failure_category == FAILURE_CATEGORY_REMOTE_NOT_ENABLED
            and r.calls_attempted == 0
            and r.calls_succeeded == 0
            and r.calls_failed == 0,
        )
    )
    # allow_remote=True but env not set -> remote_not_enabled.
    old_env = {
        k: os.environ.pop(k, None)
        for k in (ENV_BASE_URL, ENV_API_KEY, ENV_MODEL, ENV_ALLOW_REMOTE, ENV_WORKFLOW_DISPATCH)
    }
    try:
        r = chat_completion(
            [], allow_remote=True, require_workflow_dispatch=False
        )
        checks.append(
            _check(
                "allow_remote_true_no_env_returns_remote_not_enabled",
                r.failure_category == FAILURE_CATEGORY_REMOTE_NOT_ENABLED
                and r.calls_attempted == 0,
            )
        )
        # allow_remote=True, OPENLOCUS_ALLOW_REMOTE=1, but missing
        # base_url/api_key/model -> missing_env.
        os.environ[ENV_ALLOW_REMOTE] = "1"
        r = chat_completion(
            [], allow_remote=True, require_workflow_dispatch=False
        )
        checks.append(
            _check(
                "allow_remote_true_partial_env_returns_missing_env",
                r.failure_category == FAILURE_CATEGORY_MISSING_ENV
                and r.calls_attempted == 0,
            )
        )
        # allow_remote=True, env fully set, but require_workflow_dispatch
        # and OPENLOCUS_LLM_WORKFLOW_DISPATCH != 1 ->
        # workflow_dispatch_required.
        os.environ[ENV_BASE_URL] = "https://example.test"
        os.environ[ENV_API_KEY] = "sk-test"
        os.environ[ENV_MODEL] = "test-model"
        r = chat_completion(
            [], allow_remote=True, require_workflow_dispatch=True
        )
        checks.append(
            _check(
                "require_workflow_dispatch_missing_returns_required",
                r.failure_category
                == FAILURE_CATEGORY_WORKFLOW_DISPATCH_REQUIRED
                and r.calls_attempted == 0,
            )
        )
    finally:
        # Restore / clean env.
        for k, v in old_env.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)
        os.environ.pop(ENV_ALLOW_REMOTE, None)
        os.environ.pop(ENV_BASE_URL, None)
        os.environ.pop(ENV_API_KEY, None)
        os.environ.pop(ENV_MODEL, None)
        os.environ.pop(ENV_WORKFLOW_DISPATCH, None)

    # --- Group 3: Result object redaction / public summary. ---
    r = chat_completion(
        [], allow_remote=False, require_workflow_dispatch=False
    )
    summary = r.public_summary()
    forbidden_keys = {
        "prompt", "prompts", "message", "messages", "response",
        "responses", "raw_response", "request", "request_body",
        "provider_payload", "url", "base_url", "endpoint", "api_key",
        "token", "secret", "authorization", "bearer", "raw_content",
        "parsed",
    }
    checks.append(
        _check(
            "public_summary_no_forbidden_keys",
            not (set(summary.keys()) & forbidden_keys),
        )
    )
    expected_keys = {
        "calls_attempted", "calls_succeeded", "calls_failed",
        "invalid_json", "latency_ms", "usage_available", "usage",
        "failure_category", "http_status",
    }
    checks.append(
        _check(
            "public_summary_has_expected_keys",
            set(summary.keys()) == expected_keys,
        )
    )
    checks.append(
        _check(
            "public_summary_failure_category_in_enum",
            summary["failure_category"] in FAILURE_CATEGORIES,
        )
    )

    # --- Group 4: Usage parsing. ---
    ok, usage = _parse_usage(
        {"usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}
    )
    checks.append(
        _check(
            "parse_usage_valid",
            ok and usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )
    )
    ok, usage = _parse_usage(
        {"usage": {"prompt_tokens": 10, "completion_tokens": 5}}
    )
    checks.append(
        _check(
            "parse_usage_total_inferred",
            ok and usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )
    )
    ok, usage = _parse_usage({"usage": "not_a_dict"})
    checks.append(_check("parse_usage_invalid_returns_false", ok is False and usage is None))
    ok, usage = _parse_usage({"usage": {"prompt_tokens": "x", "completion_tokens": 5}})
    checks.append(_check("parse_usage_non_int_returns_false", ok is False and usage is None))
    ok, usage = _parse_usage({})
    checks.append(_check("parse_usage_missing_returns_false", ok is False and usage is None))

    # --- Group 5: Safe reason token. ---
    checks.append(
        _check(
            "safe_reason_token_alphanumeric",
            _safe_reason_token("provider_rate_limited") == "provider_rate_limited",
        )
    )
    checks.append(
        _check(
            "safe_reason_token_redacts_unsafe",
            _safe_reason_token("not a safe token!@#") == "redacted",
        )
    )
    checks.append(
        _check(
            "safe_reason_token_none",
            _safe_reason_token(None) is None,
        )
    )
    checks.append(
        _check(
            "safe_reason_token_too_long",
            _safe_reason_token("a" * 81) == "redacted",
        )
    )

    # --- Group 6: Result object slots. ---
    expected_slots = {
        "parsed", "raw_content", "latency_ms", "usage_available",
        "usage", "calls_attempted", "calls_succeeded", "calls_failed",
        "invalid_json", "failure_category", "http_status",
    }
    checks.append(
        _check(
            "result_object_slots_complete",
            set(ProviderCallResult.__slots__) == expected_slots,
        )
    )

    # --- Group 7: positive_env_int clamping. ---
    old_val = os.environ.pop(ENV_RETRIES, None)
    try:
        checks.append(
            _check(
                "positive_env_int_default_when_missing",
                _positive_env_int(
                    ENV_RETRIES, 2, minimum=0, maximum=5
                ) == 2,
            )
        )
        os.environ[ENV_RETRIES] = "3"
        checks.append(
            _check(
                "positive_env_int_valid",
                _positive_env_int(
                    ENV_RETRIES, 2, minimum=0, maximum=5
                ) == 3,
            )
        )
        os.environ[ENV_RETRIES] = "99"
        checks.append(
            _check(
                "positive_env_int_clamped_to_max",
                _positive_env_int(
                    ENV_RETRIES, 2, minimum=0, maximum=5
                ) == 5,
            )
        )
        os.environ[ENV_RETRIES] = "not_a_number"
        checks.append(
            _check(
                "positive_env_int_invalid_returns_default",
                _positive_env_int(
                    ENV_RETRIES, 2, minimum=0, maximum=5
                ) == 2,
            )
        )
    finally:
        if old_val is not None:
            os.environ[ENV_RETRIES] = old_val
        else:
            os.environ.pop(ENV_RETRIES, None)

    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class SafeArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that never echoes unknown/private-looking args."""

    def error(self, message: str) -> NoReturn:  # noqa: D401 - argparse signature
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(
        description=(
            "Minimal OpenAI-compatible chat helper self-test "
            "(no network; covers remote gating, redaction, usage parsing)."
        )
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="run no-network self-test and exit",
    )
    return ap


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.self_test:
        checks, passed = run_self_test_checks()
        for c in checks:
            tag = "PASS" if c["passed"] else "FAIL"
            print(f"[{tag}] {c['check']}")
        passed_count = sum(1 for c in checks if c["passed"])
        print(
            f"self_test_passed={passed} "
            f"({passed_count}/{len(checks)} checks)"
        )
        sys.exit(0 if passed else 1)
    parser.print_help()


if __name__ == "__main__":
    main()
