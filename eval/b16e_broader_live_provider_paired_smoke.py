#!/usr/bin/env python3
"""B16-E Broader Live-Provider Downstream Paired Smoke (Public Aggregate-Only Artifact).

This module implements the **B16-E broader live-provider downstream
paired smoke**. It broadens B16-D from one less-trivial synthetic
live-provider task family into a small heterogeneous synthetic
task-family matrix. The goal is to test whether a context-pack
treatment signal persists beyond the B16-D template while keeping the
phase bounded, aggregate-only, and manually provider-gated.

B16-E uses four fixed allowlisted task families, each with a different
decisive cue that the treatment pack supplies:

1. ``same_symbol_support_relation`` — target/distractor share a symbol
   and a support relation determines the correct edit.
2. ``operation_ambiguity`` — target symbol may be inferable but the
   operation is ambiguous (e.g. increment vs multiply).
3. ``boundary_condition`` — correct edit depends on inclusive/exclusive
   or fallback behavior.
4. ``helper_dependency_choice`` — multiple helpers exist and the
   correct edit requires choosing the right helper relation.

B16-E is explicitly **not** a downstream agent value proof, **not** a
live-agent generalization proof, **not** an external benchmark result,
**not** a production coding-agent benchmark, **not** a real user task
evaluation, and **not** a promotion/default-policy/runtime/retriever/
pack/backend/EvidenceCore semantic change. It does NOT publish prompts,
responses, provider payloads, base URLs, API keys, raw model routing
prefixes, workspace paths, file paths, source snippets, patches/diffs,
test output, raw event logs, or per-run rows.

Claim boundary (binding):

* Claim level: ``broader_live_provider_downstream_paired_smoke_only``.
* Status enum: ``broader_live_provider_paired_smoke_pass`` on live
  success; ``blocked_remote_not_enabled`` /
  ``unavailable_no_local_provider_env`` when remote opt-in not
  satisfied; ``provider_call_failed`` / ``structured_action_parse_failed``
  / ``paired_run_failed`` / ``fail_forbidden_scan`` on failures.
* Mode: ``public_aggregate_synthetic_task_family_matrix``; phase ``B16-E``.

Modes:

* ``--self-test``: no provider/network; uses fake provider responses.
* default without ``--allow-remote`` or without provider env: writes a
  truthful ``blocked_remote_not_enabled`` /
  ``unavailable_no_local_provider_env`` aggregate report if ``--out``
  is supplied; no provider calls; live-run flags false except
  ``aggregate_only_public_artifact`` / ``diagnostic_only``.
* live opt-in: requires ``--allow-remote``,
  ``OPENLOCUS_ALLOW_REMOTE=1``, and (when
  ``--require-workflow-dispatch``) ``OPENLOCUS_LLM_WORKFLOW_DISPATCH=1``;
  runs a tiny task count (default 8; hard cap 12; default 16 live
  calls; max 24 live calls).

Run::

    python3 -m py_compile eval/b16e_broader_live_provider_paired_smoke.py
    python3 eval/b16e_broader_live_provider_paired_smoke.py --self-test
    python3 eval/b16e_broader_live_provider_paired_smoke.py \\
        --out artifacts/b16e_broader_live_provider_paired_smoke/\\
b16e_broader_live_provider_paired_smoke_report.json
    # Live opt-in (only if provider env is available and safe):
    OPENLOCUS_ALLOW_REMOTE=1 OPENLOCUS_LLM_WORKFLOW_DISPATCH=1 \\
        python3 eval/b16e_broader_live_provider_paired_smoke.py \\
        --allow-remote --task-count 8 \\
        --out artifacts/b16e_broader_live_provider_paired_smoke/\\
b16e_broader_live_provider_paired_smoke_report.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# Reuse the provider client helper from B16-C/D (unchanged).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import provider_client  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "b16e_broader_live_provider_paired_smoke.v1"
GENERATED_BY = "eval/b16e_broader_live_provider_paired_smoke.py"
CLAIM_LEVEL = "broader_live_provider_downstream_paired_smoke_only"
MODE = "public_aggregate_synthetic_task_family_matrix"
PHASE = "B16-E"

STATUS_PASS = "broader_live_provider_paired_smoke_pass"
STATUS_UNAVAILABLE = "unavailable_no_local_provider_env"
STATUS_BLOCKED_REMOTE = "blocked_remote_not_enabled"
STATUS_PROVIDER_FAILED = "provider_call_failed"
STATUS_PARSE_FAILED = "structured_action_parse_failed"
STATUS_PAIRED_FAILED = "paired_run_failed"
STATUS_FAIL_LEAK = "fail_forbidden_scan"

ALL_STATUSES: frozenset[str] = frozenset(
    {
        STATUS_PASS,
        STATUS_UNAVAILABLE,
        STATUS_BLOCKED_REMOTE,
        STATUS_PROVIDER_FAILED,
        STATUS_PARSE_FAILED,
        STATUS_PAIRED_FAILED,
        STATUS_FAIL_LEAK,
    }
)

DEFAULT_OUT = Path(
    "artifacts/b16e_broader_live_provider_paired_smoke/"
    "b16e_broader_live_provider_paired_smoke_report.json"
)
DEFAULT_TASK_COUNT = 8
MIN_TASK_COUNT = 4
MAX_TASK_COUNT = 12
# Max live calls = MAX_TASK_COUNT * len(ARMS) = 12 * 2 = 24.
MAX_LIVE_CALLS = MAX_TASK_COUNT * 2

ARMS: tuple[str, ...] = ("control_sparse", "treatment_context_pack")

# Four fixed allowlisted task families. Each has a different decisive
# cue that the treatment pack supplies. Family names are public and
# fixed (allowlisted); never dynamic.
TASK_FAMILIES: tuple[str, ...] = (
    "same_symbol_support_relation",
    "operation_ambiguity",
    "boundary_condition",
    "helper_dependency_choice",
)

# Per-arm aggregate metric names emitted in the public artifact.
METRIC_NAMES: tuple[str, ...] = (
    "run_count",
    "solve_rate",
    "tests_pass_rate",
    "correct_file_before_first_edit_rate",
    "wrong_file_edits_mean",
    "tool_calls_before_first_edit_mean",
    "context_tokens_mean",
    "latency_ms_mean",
    "cost_proxy_mean",
)

# Delta metric names (treatment minus control).
DELTA_METRIC_NAMES: tuple[str, ...] = tuple(
    name for name in METRIC_NAMES if name != "run_count"
)

# Allowlisted synthetic filenames for the structured edit action schema.
ALLOWED_EDIT_FILES: frozenset[str] = frozenset({"target.py"})
ALLOWED_EDIT_ACTIONS: frozenset[str] = frozenset(
    {"replace_return_value", "choose_helper_constant", "no_op"}
)

# ---------------------------------------------------------------------------
# Safe booleans true (live run only).
# ---------------------------------------------------------------------------

LIVE_TRUE_FLAGS: tuple[str, ...] = (
    "downstream_agent_runs_performed",
    "live_llm_agent",
    "provider_calls_made",
    "remote_provider_calls_made",
    "paired_run_executed",
    "synthetic_task_family_matrix_used",
    "real_file_edits_performed",
    "real_test_commands_executed",
    "agent_behavior_metrics_evaluated",
    "aggregate_only_public_artifact",
    "diagnostic_only",
)

# ---------------------------------------------------------------------------
# Always-false no-claim flags.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "downstream_agent_value_proven": False,
    "live_agent_generalization_claimed": False,
    "promotion_ready": False,
    "default_should_change": False,
    "external_benchmark_performance_claimed": False,
    "real_user_task_claimed": False,
    "runtime_behavior_changed": False,
    "retriever_changed": False,
    "pack_builder_changed": False,
    "backend_changed": False,
    "default_policy_changed": False,
    "evidencecore_semantics_changed": False,
}

# ---------------------------------------------------------------------------
# Public artifact scanner (strict, fail-closed). Same shape as B16-C/D.
# ---------------------------------------------------------------------------

FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset(
    {
        # prompt / response / message / request / provider payload
        "prompt", "prompts", "message", "messages", "response",
        "responses", "raw_response", "request", "request_body",
        "provider_payload", "raw_payload", "api_response",
        "response_body", "model_response", "model_output",
        # url / endpoint / key / token / secret / authorization
        "url", "base_url", "endpoint", "api_key", "api_token",
        "api_secret", "token", "secret", "authorization", "bearer",
        "provider_key", "provider_url", "provider_base_url",
        "credential", "password",
        # workspace / path / file
        "workspace", "workspace_path", "workspace_dir", "tmp_dir",
        "tmp_path", "path", "span", "line_range", "start_line",
        "end_line", "start_byte", "end_byte", "line_ranges", "spans",
        "file", "files", "filename", "filepath", "target_file",
        "wrong_file", "target_module", "distractor_module",
        "support_module", "boundary_module", "helper_module",
        "test_module", "source_path", "module_path", "module",
        # content / hash
        "content", "content_sha", "content_hash", "hash", "digest",
        "sha256", "md5", "sha1",
        "snippet", "snippets", "excerpt", "excerpts",
        "code", "source_code", "code_snippet", "body", "text", "source",
        # identifiers
        "task_id", "task_index", "repo_id", "repo", "instance_id",
        "row_id", "record_id", "id", "name", "run_id",
        "model_id_raw", "model_id",
        # packet-specific identifiers
        "packet_ref", "packet_id", "private_record_ref",
        "candidate_ref", "candidate_id", "candidate",
        # labels / qrels / annotations
        "label", "labels", "qrels", "gold", "gold_label",
        "gold_labels", "hard_negative", "hard_negatives",
        # patches / tests / output
        "patch", "diff", "test_patch", "tests", "test_output",
        "test_log", "test_stdout", "test_stderr", "stdout", "stderr",
        "returncode", "exit_code",
        # event logs / traces / errors
        "event_log", "events", "log", "trace", "raw_event", "raw_log",
        "stack_trace", "traceback", "error_message", "error",
        # rows / records / packets
        "raw_rows", "rows", "records", "runs", "per_run", "raw",
        "raw_data", "predictions", "candidates",
        # CI / agreement numerics
        "agreement_metric", "agreement_value", "agreement_score",
        "kappa", "fleiss_kappa", "cohen_kappa", "agreement",
        "confidence_interval", "ci_value", "ci_lower", "ci_upper",
        "ci_low", "ci_high",
    }
)

# Known-safe provenance value paths (allowlisted for path-like / hex /
# path-like value checks only).
SAFE_VALUE_KEY_NAMES: frozenset[str] = frozenset(
    {
        "schema_version",
        "generated_by",
        "generated_at",
        "claim_level",
        "status",
        "mode",
        "phase",
        "arm",
        "baseline_arm",
        "treatment_arm",
        "metric",
        "task_family",
        "model_display_category",
    }
)

# Value patterns that indicate leaked workspace / file / prompt /
# response / patch / test / event-log / secret / identifier data.
_RE_URL_VALUE = re.compile(r"https?://", re.IGNORECASE)
_RE_HEX_DIGEST = re.compile(r"[A-Fa-f0-9]{32,}")
_RE_SECRET_LIKE = re.compile(
    r"(?:api[_-]?key|api[_-]?token|api[_-]?secret|base[_-]?url"
    r"|provider[_-]?key|provider[_-]?url|authorization[_-]?bearer"
    r"|secret|password|credential)",
    re.IGNORECASE,
)
_FILE_EXT = (
    r"py|rs|ts|tsx|js|jsx|go|java|c|cpp|cc|h|hpp|hh|md|json|toml|"
    r"yaml|yml|txt|sh|rb|php|kt|swift|patch|diff|csv|parquet|jsonl"
)
_RE_FILE_PATH_VALUE = re.compile(
    rf"\b[A-Za-z0-9._/\-]+\.(?:{_FILE_EXT})\b"
)
_RE_LINE_RANGE_VALUE = re.compile(r"\b\d+\s*[:\-]\s*\d+\b")
_RE_RAW_JSON = re.compile(r'^\s*[\{\[]\s*"[^"]+"\s*:')
_RE_TMP_PATH_VALUE = re.compile(r"/tmp/")
_RE_TASK_ID_VALUE = re.compile(r"\btask[_\-\s]*\d+\b", re.IGNORECASE)
_RE_PATCH_MARKER = re.compile(r"^(---|\+\+\+|@@\s)", re.MULTILINE)
_RE_STACK_TRACE = re.compile(
    r"Traceback\s*\(most\s+recent\s+call\s+last\)", re.IGNORECASE
)
# Reject raw model routing prefix anywhere in a value.
_RE_RAW_MODEL_PREFIX = re.compile(r"\[mk\]", re.IGNORECASE)

# The sentinel used by self-tests; the scanner must never let it through.
_SECRET_SENTINEL = "SECRET_VALIDATOR_SENTINEL"
# Routing prefix sentinel, deliberately split so the literal routing
# prefix does not appear in source.
_ROUTING_PREFIX_SENTINEL = "[" + "m" + "k]"
_REMOTE_ENV_KEYS = (
    provider_client.ENV_BASE_URL,
    provider_client.ENV_API_KEY,
    provider_client.ENV_MODEL,
    provider_client.ENV_ALLOW_REMOTE,
    provider_client.ENV_WORKFLOW_DISPATCH,
)


def _path_last_key(path: str) -> str:
    last = path.rsplit(".", 1)[-1]
    return last.split("[")[0]


def _is_safe_value_path(path: str) -> bool:
    return _path_last_key(path) in SAFE_VALUE_KEY_NAMES


def _scan_forbidden(obj: Any, path: str = "$") -> list[dict[str, Any]]:
    """Strict recursive scanner for public artifact JSON."""
    violations: list[dict[str, Any]] = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            sub_path = f"{path}.{key_str}"
            if key_str in FORBIDDEN_KEY_NAMES:
                violations.append(
                    {"category": "forbidden_key", "path": sub_path}
                )
            violations.extend(_scan_forbidden(value, sub_path))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_scan_forbidden(value, f"{path}[{idx}]"))
    elif isinstance(obj, str):
        safe_value = _is_safe_value_path(path)
        if obj in FORBIDDEN_KEY_NAMES:
            violations.append(
                {"category": "forbidden_field_name_value", "path": path}
            )
        elif len(obj) > 256:
            violations.append({"category": "long_string", "path": path})
        elif _RE_URL_VALUE.search(obj) and not safe_value:
            violations.append({"category": "url_value", "path": path})
        elif not safe_value and _RE_HEX_DIGEST.search(obj):
            violations.append(
                {"category": "hex_digest_value", "path": path}
            )
        elif _RE_SECRET_LIKE.search(obj) and not safe_value:
            violations.append({"category": "secret_like_value", "path": path})
        elif not safe_value and _RE_FILE_PATH_VALUE.search(obj):
            violations.append({"category": "path_like_value", "path": path})
        elif "\n" in obj:
            violations.append({"category": "multiline_value", "path": path})
        elif _RE_RAW_JSON.search(obj):
            violations.append(
                {"category": "raw_json_fragment", "path": path}
            )
        elif not safe_value and _RE_TMP_PATH_VALUE.search(obj):
            violations.append(
                {"category": "tmp_path_value", "path": path}
            )
        elif not safe_value and _RE_TASK_ID_VALUE.search(obj):
            violations.append(
                {"category": "task_identifier_value", "path": path}
            )
        elif _RE_PATCH_MARKER.search(obj):
            violations.append(
                {"category": "patch_marker_value", "path": path}
            )
        elif _RE_STACK_TRACE.search(obj):
            violations.append(
                {"category": "stack_trace_value", "path": path}
            )
        elif _RE_RAW_MODEL_PREFIX.search(obj):
            violations.append(
                {"category": "raw_model_prefix_value", "path": path}
            )
        elif _SECRET_SENTINEL in obj:
            violations.append({"category": "sentinel_value", "path": path})
        else:
            stripped_val = obj.strip()
            if (
                3 <= len(stripped_val) <= 16
                and _RE_LINE_RANGE_VALUE.fullmatch(stripped_val)
                and not stripped_val.replace(" ", "").isdigit()
            ):
                violations.append(
                    {"category": "line_range_value", "path": path}
                )
    return violations


def _forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_forbidden(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_no_forbidden(obj: Any) -> None:
    scan = _forbidden_scan_summary(obj)
    if scan["status"] != "pass":
        raise SystemExit(
            "forbidden content leak; refusing to write artifact"
        )


def _refuse_on_self_test_failure(report: dict[str, Any]) -> None:
    if report.get("self_test_passed") is not True:
        raise SystemExit(
            "self-test failed; refusing to write artifact"
        )


def _has_dict_key_anywhere(obj: Any, key: str) -> bool:
    if isinstance(obj, dict):
        if key in obj:
            return True
        for value in obj.values():
            if _has_dict_key_anywhere(value, key):
                return True
    elif isinstance(obj, list):
        for value in obj:
            if _has_dict_key_anywhere(value, key):
                return True
    return False


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return {"check": name, "passed": bool(ok)}


def _self_test_category_summary(
    checks: list[dict[str, Any]],
) -> dict[str, int]:
    passed = sum(1 for c in checks if c.get("passed"))
    return {
        "total": len(checks),
        "passed": passed,
        "failed": len(checks) - passed,
    }


# ---------------------------------------------------------------------------
# Heterogeneous synthetic public task-family matrix generation.
#
# Four fixed allowlisted families. Each family has a different decisive
# cue that the treatment pack supplies. The control pack lacks the
# decisive cue. Tasks cycle through families so the matrix is balanced.
#
# Family 1: same_symbol_support_relation
#   - target.py and distractor.py share the same symbol name
#   - support.py defines a helper constant; correct value = helper * 2 + i
#   - Decisive cue: support relation (helper constant name + value)
#
# Family 2: operation_ambiguity
#   - target.py has a symbol; support.py defines a base value
#   - The operation is ambiguous: increment (+1) vs multiply (*2)
#   - Correct operation is multiply; correct value = base * 2
#   - Decisive cue: operation hint ("multiply by the base value")
#
# Family 3: boundary_condition
#   - target.py has a symbol; support.py defines a limit value
#   - Correct edit depends on inclusive/exclusive boundary
#   - Correct value = limit - 1 (exclusive upper bound)
#   - Decisive cue: boundary hint ("exclusive upper bound")
#
# Family 4: helper_dependency_choice
#   - target.py has a symbol; support.py defines TWO helper constants
#   - Correct edit requires choosing the right helper relation
#   - Correct value = helper_b * 3 (not helper_a * 2)
#   - Decisive cue: helper choice hint ("use helper_b, not helper_a")
# ---------------------------------------------------------------------------


def _family_same_symbol_support_relation(i: int) -> dict[str, Any]:
    """Family 1: same-symbol distractor + support relation."""
    helper_constant = 10 + i * 7
    correct_value = helper_constant * 2 + i
    buggy_value = -correct_value
    return {
        "task_family": "same_symbol_support_relation",
        "symbol": f"resolve_{i:03d}",
        "target_module": "target.py",
        "distractor_module": "distractor.py",
        "support_module": "support.py",
        "test_module": "test_target.py",
        "helper_constant_name": f"BASE_{i:03d}",
        "helper_constant_value": helper_constant,
        "correct_value": correct_value,
        "buggy_value": buggy_value,
        "fix_kind": "replace_return_value",
        "decisive_cue": "support_relation",
    }


def _family_operation_ambiguity(i: int) -> dict[str, Any]:
    """Family 2: operation ambiguity (increment vs multiply)."""
    base_value = 20 + i * 5
    # Correct operation is multiply; correct value = base * 2.
    correct_value = base_value * 2
    buggy_value = base_value + 1  # wrong: increment instead of multiply
    return {
        "task_family": "operation_ambiguity",
        "symbol": f"compute_{i:03d}",
        "target_module": "target.py",
        "distractor_module": "distractor.py",
        "support_module": "support.py",
        "test_module": "test_target.py",
        "helper_constant_name": f"VAL_{i:03d}",
        "helper_constant_value": base_value,
        "correct_value": correct_value,
        "buggy_value": buggy_value,
        "fix_kind": "replace_return_value",
        "decisive_cue": "operation_hint",
    }


def _family_boundary_condition(i: int) -> dict[str, Any]:
    """Family 3: boundary condition (exclusive upper bound)."""
    limit_value = 50 + i * 3
    # Correct value = limit - 1 (exclusive upper bound).
    correct_value = limit_value - 1
    buggy_value = limit_value  # wrong: uses the limit itself (inclusive)
    return {
        "task_family": "boundary_condition",
        "symbol": f"clamp_{i:03d}",
        "target_module": "target.py",
        "distractor_module": "distractor.py",
        "support_module": "support.py",
        "test_module": "test_target.py",
        "helper_constant_name": f"LIMIT_{i:03d}",
        "helper_constant_value": limit_value,
        "correct_value": correct_value,
        "buggy_value": buggy_value,
        "fix_kind": "replace_return_value",
        "decisive_cue": "boundary_hint",
    }


def _family_helper_dependency_choice(i: int) -> dict[str, Any]:
    """Family 4: helper dependency choice (choose helper_b, not helper_a)."""
    helper_a = 5 + i
    helper_b = 8 + i * 2
    # Correct value = helper_b * 3 (not helper_a * 2).
    correct_value = helper_b * 3
    buggy_value = helper_a * 2  # wrong: uses helper_a
    return {
        "task_family": "helper_dependency_choice",
        "symbol": f"select_{i:03d}",
        "target_module": "target.py",
        "distractor_module": "distractor.py",
        "support_module": "support.py",
        "test_module": "test_target.py",
        "helper_constant_name": f"HELPER_B_{i:03d}",
        "helper_constant_value": helper_b,
        "helper_constant_name_alt": f"HELPER_A_{i:03d}",
        "helper_constant_value_alt": helper_a,
        "correct_value": correct_value,
        "buggy_value": buggy_value,
        "fix_kind": "replace_return_value",
        "decisive_cue": "helper_choice_hint",
    }


_FAMILY_GENERATORS = (
    _family_same_symbol_support_relation,
    _family_operation_ambiguity,
    _family_boundary_condition,
    _family_helper_dependency_choice,
)


def _generate_synthetic_tasks(count: int) -> list[dict[str, Any]]:
    """Generate deterministic heterogeneous synthetic public micro bug tasks.

    Tasks cycle through the four fixed families so the matrix is
    balanced. Each task has a ``task_family`` field set to one of the
    allowlisted family names. Task IDs are NEVER emitted to the public
    artifact; only the family name is.
    """
    tasks: list[dict[str, Any]] = []
    for i in range(count):
        family_idx = i % len(_FAMILY_GENERATORS)
        task = _FAMILY_GENERATORS[family_idx](i)
        task["index"] = i
        tasks.append(task)
    return tasks


# ---------------------------------------------------------------------------
# Workspace builder (fresh /tmp per task+arm; real multi-file Python).
# ---------------------------------------------------------------------------


def _build_workspace(workspace_dir: Path, task: dict[str, Any]) -> None:
    """Create a fresh multi-file workspace with a real stdlib test."""
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Clear any stale __pycache__ from a previous task reusing this
    # workspace dir (self-test mode reuses a single /tmp dir). Without
    # this, the cached target.pyc would shadow the new target.py with a
    # different symbol, causing ImportError.
    pycache_dir = workspace_dir / "__pycache__"
    if pycache_dir.is_dir():
        shutil.rmtree(pycache_dir, ignore_errors=True)

    target_path = workspace_dir / task["target_module"]
    distractor_path = workspace_dir / task["distractor_module"]
    support_path = workspace_dir / task["support_module"]
    test_path = workspace_dir / task["test_module"]

    family = task["task_family"]

    # Support module: defines the helper constant(s).
    if family == "helper_dependency_choice":
        # Two helpers; correct choice is helper_b.
        support_path.write_text(
            f"{task['helper_constant_name_alt']} = "
            f"{task['helper_constant_value_alt']}\n"
            f"{task['helper_constant_name']} = "
            f"{task['helper_constant_value']}\n",
            encoding="utf-8",
        )
    else:
        support_path.write_text(
            f"{task['helper_constant_name']} = "
            f"{task['helper_constant_value']}\n",
            encoding="utf-8",
        )

    # Target module: has a bug (returns wrong value).
    target_path.write_text(
        f"def {task['symbol']}():\n"
        f"    return {task['buggy_value']}\n",
        encoding="utf-8",
    )

    # Distractor module: SAME symbol name (decoy); also wrong value.
    distractor_path.write_text(
        f"def {task['symbol']}():\n"
        f"    return {task['buggy_value']}\n",
        encoding="utf-8",
    )

    # Test module: imports target AND support; asserts correct relation.
    # The test logic differs by family to encode the decisive cue.
    if family == "same_symbol_support_relation":
        test_body = (
            f"    expected = {task['helper_constant_name']} * 2 + {task['index']}\n"
        )
    elif family == "operation_ambiguity":
        test_body = (
            f"    expected = {task['helper_constant_name']} * 2\n"
        )
    elif family == "boundary_condition":
        test_body = (
            f"    expected = {task['helper_constant_name']} - 1\n"
        )
    elif family == "helper_dependency_choice":
        test_body = (
            f"    expected = {task['helper_constant_name']} * 3\n"
        )
    else:
        # Defensive: should never reach here.
        test_body = (
            f"    expected = {task['correct_value']}\n"
        )

    test_path.write_text(
        "import sys\n"
        f"sys.path.insert(0, r'{workspace_dir}')\n"
        f"from target import {task['symbol']}\n"
        f"from support import {task['helper_constant_name']}\n"
        "def main():\n"
        f"{test_body}"
        f"    assert {task['symbol']}() == expected, 'bug not fixed'\n"
        "    return 0\n"
        "if __name__ == '__main__':\n"
        "    sys.exit(main())\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Pack builder (control_sparse vs treatment_context_pack)
# ---------------------------------------------------------------------------


def _build_pack(arm: str, task: dict[str, Any]) -> dict[str, Any]:
    """Build the context pack for an arm (in-memory; never persisted).

    * control_sparse: minimal description; NO target file cue; NO
      decisive cue; small token budget.
    * treatment_context_pack: target file cue, target symbol cue,
      decisive cue (family-specific), exact edit constraint; larger
      token budget.
    """
    if arm == "control_sparse":
        return {
            "arm": arm,
            "context_tokens": 20,
            "has_target_file_cue": False,
            "has_symbol_cue": False,
            "has_decisive_cue": False,
            "has_exact_edit_constraint": False,
        }
    # treatment_context_pack
    return {
        "arm": arm,
        "context_tokens": 64,
        "has_target_file_cue": True,
        "has_symbol_cue": True,
        "has_decisive_cue": True,
        "has_exact_edit_constraint": True,
    }


# ---------------------------------------------------------------------------
# Live LLM prompt builder (in-memory only; never persisted)
# ---------------------------------------------------------------------------


def _decisive_cue_text(task: dict[str, Any]) -> str:
    """Return the family-specific decisive cue text (treatment only)."""
    family = task["task_family"]
    if family == "same_symbol_support_relation":
        return (
            f"Support relation: correct_value = {task['helper_constant_name']} "
            f"* 2 + {task['index']}. "
            f"Helper constant {task['helper_constant_name']} = "
            f"{task['helper_constant_value']} (defined in support.py). "
            f"Correct value: {task['correct_value']}."
        )
    if family == "operation_ambiguity":
        return (
            f"Operation hint: multiply the base value by 2 (do not "
            f"increment). "
            f"Base value {task['helper_constant_name']} = "
            f"{task['helper_constant_value']} (defined in support.py). "
            f"Correct value: {task['correct_value']}."
        )
    if family == "boundary_condition":
        return (
            f"Boundary hint: the limit is an exclusive upper bound "
            f"(correct value = limit - 1). "
            f"Limit {task['helper_constant_name']} = "
            f"{task['helper_constant_value']} (defined in support.py). "
            f"Correct value: {task['correct_value']}."
        )
    if family == "helper_dependency_choice":
        return (
            f"Helper choice hint: use {task['helper_constant_name']} "
            f"(not {task['helper_constant_name_alt']}). "
            f"Correct value = {task['helper_constant_name']} * 3 = "
            f"{task['correct_value']}."
        )
    return ""


def _build_messages(
    workspace_dir: Path, task: dict[str, Any], pack: dict[str, Any]
) -> list[dict[str, str]]:
    """Build the live LLM chat messages (in-memory; never persisted).

    The prompt may include a tiny synthetic/public source snippet (the
    buggy target module + the support module) and a family-specific
    decisive cue only when the treatment pack carries it. Prompts are
    NEVER persisted.
    """
    target_path = workspace_dir / task["target_module"]
    support_path = workspace_dir / task["support_module"]
    # Tiny synthetic/public source snippets (in-memory only).
    target_snippet = target_path.read_text(encoding="utf-8")
    support_snippet = support_path.read_text(encoding="utf-8")

    system = (
        "You are a minimal coding-agent smoke. "
        "Respond with a single JSON object matching the schema: "
        '{"action": "replace_return_value" | "choose_helper_constant" | "no_op", '
        '"file": "target.py", '
        '"symbol": "<symbol>", '
        '"new_return_value": <int>}. '
        "Only use file=target.py. Do not include any other text."
    )

    user_lines = [
        f"Bug: function {task['symbol']} returns the wrong value.",
        f"Task family: {task['task_family']}.",
    ]
    if pack.get("has_target_file_cue"):
        user_lines.append("Target file: target.py (not distractor.py).")
    if pack.get("has_symbol_cue"):
        user_lines.append(f"Target symbol: {task['symbol']} in target.py.")
    if pack.get("has_decisive_cue"):
        user_lines.append(_decisive_cue_text(task))
    if pack.get("has_exact_edit_constraint"):
        user_lines.append(
            "Edit constraint: only edit target.py; do not edit "
            "distractor.py or support.py."
        )
    # Always include the source snippets so the model sees the bug.
    user_lines.append(f"Target source:\n{target_snippet}")
    if pack.get("has_decisive_cue"):
        user_lines.append(f"Support source:\n{support_snippet}")
    user_lines.append("Respond with the JSON edit action only.")

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n".join(user_lines)},
    ]


# ---------------------------------------------------------------------------
# Structured edit action validation and application
# ---------------------------------------------------------------------------


def _validate_edit_action(
    action: Any, task: dict[str, Any]
) -> tuple[bool, str]:
    """Validate the structured edit action against the allowlisted schema."""
    if not isinstance(action, dict):
        return False, "top_level_not_object"
    file_value = action.get("file")
    if file_value not in ALLOWED_EDIT_FILES:
        return False, "disallowed_file"
    action_value = action.get("action")
    if action_value not in ALLOWED_EDIT_ACTIONS:
        return False, "disallowed_action"
    symbol = action.get("symbol")
    if not isinstance(symbol, str) or not symbol:
        return False, "missing_symbol"
    if action_value in ("replace_return_value", "choose_helper_constant"):
        new_value = action.get("new_return_value")
        if not isinstance(new_value, int):
            return False, "missing_or_non_int_new_return_value"
    return True, "ok"


def _apply_edit_action(
    workspace_dir: Path, task: dict[str, Any], action: dict[str, Any]
) -> tuple[bool, str]:
    """Apply the validated edit action locally.

    Returns (edited_correct_file, edit_kind). edit_kind is one of:
    "correct_file", "wrong_file", "no_op".
    """
    file_value = action.get("file")
    action_value = action.get("action")
    if action_value == "no_op":
        return False, "no_op"
    if file_value == task["target_module"]:
        edit_path = workspace_dir / str(file_value)
        new_value = action.get("new_return_value")
        new_content = (
            f"def {task['symbol']}():\n"
            f"    return {new_value}\n"
        )
        edit_path.write_text(new_content, encoding="utf-8")
        return True, "correct_file"
    return False, "wrong_file"


# ---------------------------------------------------------------------------
# Live LLM agent run (one task + arm)
# ---------------------------------------------------------------------------


def _run_live_agent(
    workspace_dir: Path,
    task: dict[str, Any],
    pack: dict[str, Any],
    *,
    allow_remote: bool,
    require_workflow_dispatch: bool,
    fake_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the live LLM agent for one task+arm.

    When ``fake_response`` is supplied (self-test mode), no network call
    is made. Otherwise a real provider call is made via
    ``provider_client.chat_completion``.
    """
    # Transient event log; NEVER committed.
    event_log: list[dict[str, Any]] = []

    tool_calls_before_first_edit = 0
    correct_file_before_first_edit = False
    wrong_file_edits = 0

    provider_summary: dict[str, Any] = {
        "calls_attempted": 0,
        "calls_succeeded": 0,
        "calls_failed": 0,
        "invalid_json_count": 0,
        "timeout_count": 0,
        "failure_category_counts": {},
        "usage_available": False,
        "prompt_tokens_total": 0,
        "completion_tokens_total": 0,
        "total_tokens_total": 0,
        "latency_ms_total": 0,
    }

    def _bump_failure_category(cat: str) -> None:
        provider_summary["failure_category_counts"][cat] = (
            provider_summary["failure_category_counts"].get(cat, 0) + 1
        )

    if fake_response is not None:
        # Self-test mode: no network.
        parsed_action = fake_response
        provider_summary["calls_attempted"] = 1
        provider_summary["calls_succeeded"] = 1
        provider_summary["calls_failed"] = 0
        _bump_failure_category(provider_client.FAILURE_CATEGORY_OK)
        latency_ms = 1
    else:
        messages = _build_messages(workspace_dir, task, pack)
        result = provider_client.chat_completion(
            messages,
            allow_remote=allow_remote,
            require_workflow_dispatch=require_workflow_dispatch,
            temperature=0.0,
            json_mode=True,
        )
        provider_summary["calls_attempted"] += result.calls_attempted
        provider_summary["calls_succeeded"] += result.calls_succeeded
        provider_summary["calls_failed"] += result.calls_failed
        provider_summary["latency_ms_total"] += result.latency_ms
        latency_ms = result.latency_ms
        _bump_failure_category(result.failure_category)
        if result.invalid_json:
            provider_summary["invalid_json_count"] += 1
        if result.failure_category == provider_client.FAILURE_CATEGORY_TIMEOUT:
            provider_summary["timeout_count"] += 1
        if result.usage_available and isinstance(result.usage, dict):
            provider_summary["usage_available"] = True
            provider_summary["prompt_tokens_total"] += int(
                result.usage.get("prompt_tokens", 0)
            )
            provider_summary["completion_tokens_total"] += int(
                result.usage.get("completion_tokens", 0)
            )
            provider_summary["total_tokens_total"] += int(
                result.usage.get("total_tokens", 0)
            )
        if result.calls_succeeded != 1 or result.parsed is None:
            parsed_action = None
        else:
            parsed_action = result.parsed

    # Validate and apply the structured edit action.
    if parsed_action is None:
        event_log.append({"event": "no_action", "kind": "no_parse"})
    else:
        valid, reason = _validate_edit_action(parsed_action, task)
        if not valid:
            event_log.append(
                {"event": "invalid_action", "kind": reason}
            )
        else:
            tool_calls_before_first_edit = 1
            edited_correct, edit_kind = _apply_edit_action(
                workspace_dir, task, parsed_action
            )
            if edit_kind == "correct_file":
                correct_file_before_first_edit = True
            elif edit_kind == "wrong_file":
                wrong_file_edits += 1
            event_log.append(
                {"event": "edit", "kind": edit_kind}
            )

    # Run the real subprocess test command.
    test_cmd = [sys.executable, str(workspace_dir / task["test_module"])]
    test_start = time.perf_counter()
    try:
        proc = subprocess.run(
            test_cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        tests_pass = proc.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        tests_pass = False
    test_latency_ms = max(
        1, int((time.perf_counter() - test_start) * 1000)
    )

    event_log.append(
        {"event": "test", "passed": tests_pass}
    )

    solve = tests_pass and correct_file_before_first_edit

    return {
        "solve": solve,
        "tests_pass": tests_pass,
        "correct_file_before_first_edit": correct_file_before_first_edit,
        "wrong_file_edits": wrong_file_edits,
        "tool_calls_before_first_edit": tool_calls_before_first_edit,
        "context_tokens": pack.get("context_tokens", 0),
        "latency_ms": latency_ms + test_latency_ms,
        "cost_proxy": 0,
        "task_family": task["task_family"],
        "provider_summary": provider_summary,
        # event_log stays in-memory only; never returned to the report.
    }


# ---------------------------------------------------------------------------
# Aggregate metric computation
# ---------------------------------------------------------------------------


def _rate(numer: int, denom: int) -> float:
    if denom <= 0:
        return 0.0
    return numer / denom


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _round_metric(value: float) -> float:
    return round(float(value), 6)


def _aggregate_arm_metrics(
    runs: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compute per-arm aggregate metrics + provider summary."""
    n = len(runs)
    metrics = {
        "run_count": n,
        "solve_rate": _round_metric(
            _rate(sum(1 for r in runs if r["solve"]), n)
        ),
        "tests_pass_rate": _round_metric(
            _rate(sum(1 for r in runs if r["tests_pass"]), n)
        ),
        "correct_file_before_first_edit_rate": _round_metric(
            _rate(
                sum(1 for r in runs if r["correct_file_before_first_edit"]),
                n,
            )
        ),
        "wrong_file_edits_mean": _round_metric(
            _mean([r["wrong_file_edits"] for r in runs])
        ),
        "tool_calls_before_first_edit_mean": _round_metric(
            _mean([r["tool_calls_before_first_edit"] for r in runs])
        ),
        "context_tokens_mean": _round_metric(
            _mean([r["context_tokens"] for r in runs])
        ),
        "latency_ms_mean": _round_metric(
            _mean([r["latency_ms"] for r in runs])
        ),
        "cost_proxy_mean": _round_metric(
            _mean([r["cost_proxy"] for r in runs])
        ),
    }
    provider_summary: dict[str, Any] = {
        "calls_attempted": 0,
        "calls_succeeded": 0,
        "calls_failed": 0,
        "invalid_json_count": 0,
        "timeout_count": 0,
        "failure_category_counts": {},
        "usage_available": False,
        "prompt_tokens_total": 0,
        "completion_tokens_total": 0,
        "total_tokens_total": 0,
        "latency_ms_total": 0,
    }
    for r in runs:
        ps = r.get("provider_summary", {})
        provider_summary["calls_attempted"] += int(
            ps.get("calls_attempted", 0)
        )
        provider_summary["calls_succeeded"] += int(
            ps.get("calls_succeeded", 0)
        )
        provider_summary["calls_failed"] += int(
            ps.get("calls_failed", 0)
        )
        provider_summary["invalid_json_count"] += int(
            ps.get("invalid_json_count", 0)
        )
        provider_summary["timeout_count"] += int(
            ps.get("timeout_count", 0)
        )
        provider_summary["latency_ms_total"] += int(
            ps.get("latency_ms_total", 0)
        )
        if ps.get("usage_available"):
            provider_summary["usage_available"] = True
        provider_summary["prompt_tokens_total"] += int(
            ps.get("prompt_tokens_total", 0)
        )
        provider_summary["completion_tokens_total"] += int(
            ps.get("completion_tokens_total", 0)
        )
        provider_summary["total_tokens_total"] += int(
            ps.get("total_tokens_total", 0)
        )
        for cat, cnt in ps.get("failure_category_counts", {}).items():
            provider_summary["failure_category_counts"][cat] = (
                provider_summary["failure_category_counts"].get(cat, 0)
                + int(cnt)
            )
    return metrics, provider_summary


def _aggregate_family_results(
    arm_runs: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Compute per-family per-arm aggregate records.

    Returns a list of fixed records:
    ``{task_family, arm, run_count, solve_rate, tests_pass_rate,
       wrong_file_edits_mean, ...}``.
    Only allowlisted family names appear. No task IDs.
    """
    family_results: list[dict[str, Any]] = []
    for family in TASK_FAMILIES:
        for arm in ARMS:
            runs = [
                r for r in arm_runs[arm] if r.get("task_family") == family
            ]
            n = len(runs)
            metrics = {
                "run_count": n,
                "solve_rate": _round_metric(
                    _rate(sum(1 for r in runs if r["solve"]), n)
                ),
                "tests_pass_rate": _round_metric(
                    _rate(sum(1 for r in runs if r["tests_pass"]), n)
                ),
                "correct_file_before_first_edit_rate": _round_metric(
                    _rate(
                        sum(
                            1
                            for r in runs
                            if r["correct_file_before_first_edit"]
                        ),
                        n,
                    )
                ),
                "wrong_file_edits_mean": _round_metric(
                    _mean([r["wrong_file_edits"] for r in runs])
                ),
            }
            family_results.append(
                {
                    "task_family": family,
                    "arm": arm,
                    "run_count": n,
                    "solve_rate": metrics["solve_rate"],
                    "tests_pass_rate": metrics["tests_pass_rate"],
                    "correct_file_before_first_edit_rate": metrics[
                        "correct_file_before_first_edit_rate"
                    ],
                    "wrong_file_edits_mean": metrics[
                        "wrong_file_edits_mean"
                    ],
                }
            )
    return family_results


def _compute_deltas(
    control: dict[str, Any], treatment: dict[str, Any]
) -> list[dict[str, Any]]:
    """Compute treatment-minus-control deltas as fixed records."""
    baseline_arm = "control_sparse"
    treatment_arm = "treatment_context_pack"
    return [
        {
            "baseline_arm": baseline_arm,
            "treatment_arm": treatment_arm,
            "metric": name,
            "delta": _round_metric(treatment[name] - control[name]),
        }
        for name in DELTA_METRIC_NAMES
    ]


def _compute_family_signal_summary(
    family_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute aggregate family signal summary (counts only).

    Counts families by solve-rate delta sign. These are diagnostic
    smoke outcomes only, NEVER promotion/default/value claims.
    """
    families_evaluated = 0
    positive = 0
    zero = 0
    negative = 0
    for family in TASK_FAMILIES:
        control = next(
            (
                r
                for r in family_results
                if r["task_family"] == family and r["arm"] == "control_sparse"
            ),
            None,
        )
        treatment = next(
            (
                r
                for r in family_results
                if r["task_family"] == family
                and r["arm"] == "treatment_context_pack"
            ),
            None,
        )
        if control is None or treatment is None:
            continue
        if control["run_count"] == 0 or treatment["run_count"] == 0:
            continue
        families_evaluated += 1
        delta = treatment["solve_rate"] - control["solve_rate"]
        if delta > 0:
            positive += 1
        elif delta == 0:
            zero += 1
        else:
            negative += 1
    return {
        "families_evaluated": families_evaluated,
        "families_with_positive_solve_delta": positive,
        "families_with_zero_solve_delta": zero,
        "families_with_negative_solve_delta": negative,
    }


def _compute_honest_signals(
    control_metrics: dict[str, Any],
    treatment_metrics: dict[str, Any],
    paired_deltas: list[dict[str, Any]],
    family_signal_summary: dict[str, Any],
) -> dict[str, Any]:
    """Compute honest diagnostic signal fields."""
    solve_delta = next(
        (d["delta"] for d in paired_deltas if d["metric"] == "solve_rate"),
        0.0,
    )
    tests_pass_delta = next(
        (d["delta"] for d in paired_deltas if d["metric"] == "tests_pass_rate"),
        0.0,
    )
    wrong_file_delta = next(
        (
            d["delta"]
            for d in paired_deltas
            if d["metric"] == "wrong_file_edits_mean"
        ),
        0.0,
    )
    # context_pack_signal_observed: True iff treatment solve_rate >
    # control solve_rate OR treatment wrong_file_edits_mean < control
    # wrong_file_edits_mean OR at least one family has positive delta.
    context_signal = (
        treatment_metrics.get("solve_rate", 0.0)
        > control_metrics.get("solve_rate", 0.0)
        or treatment_metrics.get("wrong_file_edits_mean", 0.0)
        < control_metrics.get("wrong_file_edits_mean", 0.0)
        or family_signal_summary.get(
            "families_with_positive_solve_delta", 0
        )
        > 0
    )
    return {
        "context_pack_signal_observed": bool(context_signal),
        "overall_treatment_solve_rate_delta": _round_metric(solve_delta),
        "overall_treatment_tests_pass_rate_delta": _round_metric(
            tests_pass_delta
        ),
        "families_evaluated": int(
            family_signal_summary.get("families_evaluated", 0)
        ),
        "families_with_positive_solve_delta": int(
            family_signal_summary.get(
                "families_with_positive_solve_delta", 0
            )
        ),
        "families_with_zero_solve_delta": int(
            family_signal_summary.get(
                "families_with_zero_solve_delta", 0
            )
        ),
        "families_with_negative_solve_delta": int(
            family_signal_summary.get(
                "families_with_negative_solve_delta", 0
            )
        ),
    }


# ---------------------------------------------------------------------------
# Status determination
# ---------------------------------------------------------------------------


def _determine_live_status(
    arm_results: list[dict[str, Any]],
    paired_run_completed: bool,
    any_provider_call_failed: bool,
    any_parse_failed: bool,
) -> str:
    """Determine the live run status from arm results.

    CI pass means: live run completed + privacy scan passed + artifact
    is honest. CI pass does NOT require treatment improvement.
    """
    if not paired_run_completed:
        return STATUS_PAIRED_FAILED
    if any_provider_call_failed:
        return STATUS_PROVIDER_FAILED
    if any_parse_failed:
        return STATUS_PARSE_FAILED
    return STATUS_PASS


# ---------------------------------------------------------------------------
# Public artifact builder
# ---------------------------------------------------------------------------


def _build_public_report(
    checks: list[dict[str, Any]],
    all_passed: bool,
    status: str,
    arm_results: list[dict[str, Any]] | None = None,
    paired_deltas: list[dict[str, Any]] | None = None,
    task_family_results: list[dict[str, Any]] | None = None,
    family_signal_summary: dict[str, Any] | None = None,
    honest_signals: dict[str, Any] | None = None,
    input_summary: dict[str, Any] | None = None,
    model_display_category: str = "unavailable",
    live_run_executed: bool = False,
) -> dict[str, Any]:
    """Assemble the public aggregate-only report (fail-closed scan)."""
    arm_results = arm_results or []
    paired_deltas = paired_deltas or []
    task_family_results = task_family_results or []
    family_signal_summary = family_signal_summary or {
        "families_evaluated": 0,
        "families_with_positive_solve_delta": 0,
        "families_with_zero_solve_delta": 0,
        "families_with_negative_solve_delta": 0,
    }
    honest_signals_out = honest_signals or {
        "context_pack_signal_observed": False,
        "overall_treatment_solve_rate_delta": 0.0,
        "overall_treatment_tests_pass_rate_delta": 0.0,
        "families_evaluated": 0,
        "families_with_positive_solve_delta": 0,
        "families_with_zero_solve_delta": 0,
        "families_with_negative_solve_delta": 0,
    }
    input_summary = input_summary or {
        "synthetic_task_count": 0,
        "run_count_per_arm": 0,
        "total_runs": 0,
        "arms": list(ARMS),
        "task_families": list(TASK_FAMILIES),
        "paired_design": True,
        "workspace_isolation": "fresh_tmp_per_task_arm",
        "transient_workspace_outputs_only": True,
        "designed_causal_subset": True,
        "task_family_matrix": True,
    }

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "model_display_category": model_display_category,
        "input_summary": input_summary,
        "arm_results": arm_results,
        "paired_deltas": paired_deltas,
        "task_family_results": task_family_results,
        "family_signal_summary": family_signal_summary,
        "honest_signals": honest_signals_out,
        # No-claim / no-runtime-change flags (always false).
        **DEFAULT_FALSE_FLAGS,
        # Diagnostic flags (always true).
        "aggregate_only_public_artifact": True,
        "diagnostic_only": True,
        # Self-test summary / checks / passed.
        "self_test_summary": _self_test_category_summary(checks),
        "self_test_checks": checks,
        "self_test_passed": all_passed,
    }

    # Set live-run true flags ONLY when a live run actually executed.
    if live_run_executed:
        for flag in LIVE_TRUE_FLAGS:
            report[flag] = True
    else:
        for flag in LIVE_TRUE_FLAGS:
            if flag not in (
                "aggregate_only_public_artifact", "diagnostic_only"
            ):
                report[flag] = False

    # Fail-closed forbidden scan before returning.
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_LEAK
    return report


def build_report(
    task_count: int,
    *,
    allow_remote: bool,
    require_workflow_dispatch: bool,
) -> dict[str, Any]:
    """Assemble the public aggregate-only report.

    If remote opt-in is not satisfied or provider env is missing, write
    a truthful unavailable/blocked report with live-run flags false.
    Otherwise run a tiny live paired smoke.
    """
    checks, all_passed = run_self_test_checks()

    enabled, failure_category = provider_client._check_remote_enabled(
        allow_remote=allow_remote,
        require_workflow_dispatch=require_workflow_dispatch,
    )

    if not enabled:
        if failure_category in (
            provider_client.FAILURE_CATEGORY_MISSING_ENV,
        ):
            status = STATUS_UNAVAILABLE
        else:
            status = STATUS_BLOCKED_REMOTE
        input_summary: dict[str, Any] = {
            "synthetic_task_count": 0,
            "run_count_per_arm": 0,
            "total_runs": 0,
            "arms": list(ARMS),
            "task_families": list(TASK_FAMILIES),
            "paired_design": True,
            "workspace_isolation": "fresh_tmp_per_task_arm",
            "transient_workspace_outputs_only": True,
            "designed_causal_subset": True,
            "task_family_matrix": True,
        }
        return _build_public_report(
            checks,
            all_passed,
            status=status,
            arm_results=[],
            paired_deltas=[],
            task_family_results=[],
            family_signal_summary={
                "families_evaluated": 0,
                "families_with_positive_solve_delta": 0,
                "families_with_zero_solve_delta": 0,
                "families_with_negative_solve_delta": 0,
            },
            honest_signals={
                "context_pack_signal_observed": False,
                "overall_treatment_solve_rate_delta": 0.0,
                "overall_treatment_tests_pass_rate_delta": 0.0,
                "families_evaluated": 0,
                "families_with_positive_solve_delta": 0,
                "families_with_zero_solve_delta": 0,
                "families_with_negative_solve_delta": 0,
            },
            input_summary=input_summary,
            model_display_category="unavailable",
            live_run_executed=False,
        )

    # Live run: generate tasks, build workspaces, run live agent.
    tasks = _generate_synthetic_tasks(task_count)
    arm_runs: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    any_provider_call_failed = False
    any_parse_failed = False

    for task in tasks:
        for arm in ARMS:
            pack = _build_pack(arm, task)
            workspace_dir = Path(
                tempfile.mkdtemp(prefix="b16e_workspace_")
            )
            try:
                _build_workspace(workspace_dir, task)
                run = _run_live_agent(
                    workspace_dir,
                    task,
                    pack,
                    allow_remote=allow_remote,
                    require_workflow_dispatch=require_workflow_dispatch,
                )
            finally:
                try:
                    shutil.rmtree(workspace_dir, ignore_errors=True)
                except OSError:
                    pass
            arm_runs[arm].append(run)
            ps = run.get("provider_summary", {})
            if ps.get("calls_failed", 0) > 0:
                any_provider_call_failed = True
            if (
                ps.get("calls_succeeded", 0) > 0
                and run["tool_calls_before_first_edit"] == 0
            ):
                any_parse_failed = True

    arm_results: list[dict[str, Any]] = []
    for arm in ARMS:
        metrics, provider_summary = _aggregate_arm_metrics(arm_runs[arm])
        arm_results.append(
            {
                "arm": arm,
                "metrics": metrics,
                "provider_summary": provider_summary,
                "failure_category_counts": provider_summary.get(
                    "failure_category_counts", {}
                ),
            }
        )

    paired_deltas = _compute_deltas(
        arm_results[0]["metrics"], arm_results[1]["metrics"]
    )

    task_family_results = _aggregate_family_results(arm_runs)
    family_signal_summary = _compute_family_signal_summary(
        task_family_results
    )
    honest_signals = _compute_honest_signals(
        arm_results[0]["metrics"],
        arm_results[1]["metrics"],
        paired_deltas,
        family_signal_summary,
    )

    status = _determine_live_status(
        arm_results,
        paired_run_completed=True,
        any_provider_call_failed=any_provider_call_failed,
        any_parse_failed=any_parse_failed,
    )

    input_summary = {
        "synthetic_task_count": task_count,
        "run_count_per_arm": task_count,
        "total_runs": task_count * len(ARMS),
        "arms": list(ARMS),
        "task_families": list(TASK_FAMILIES),
        "paired_design": True,
        "workspace_isolation": "fresh_tmp_per_task_arm",
        "transient_workspace_outputs_only": True,
        "designed_causal_subset": True,
        "task_family_matrix": True,
    }

    raw_model = os.environ.get(provider_client.ENV_MODEL, "")
    model_display_category = _normalize_model_display(raw_model)

    return _build_public_report(
        checks,
        all_passed,
        status=status,
        arm_results=arm_results,
        paired_deltas=paired_deltas,
        task_family_results=task_family_results,
        family_signal_summary=family_signal_summary,
        honest_signals=honest_signals,
        input_summary=input_summary,
        model_display_category=model_display_category,
        live_run_executed=True,
    )


def _normalize_model_display(raw_model: str) -> str:
    """Normalize a raw model id to a safe display category.

    Strips the routing prefix and any non-alphanumeric suffix.
    Returns ``"unavailable"`` for empty input. NEVER returns the raw
    routing prefix.
    """
    if not raw_model:
        return "unavailable"
    cleaned = re.sub(r"^\[mk\]", "", raw_model, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "", cleaned)
    cleaned = cleaned.strip(".-_")
    if not cleaned:
        return "unavailable"
    if len(cleaned) > 64:
        cleaned = cleaned[:64]
    return cleaned


# ---------------------------------------------------------------------------
# Env-preservation self-test helpers (regression guard: no-network
# self-test probes must not clear a live provider env).
# ---------------------------------------------------------------------------


def _probe_missing_env_without_mutating_remote_env() -> tuple[bool, str, bool]:
    """Probe missing-env path while restoring provider env exactly."""
    before = {k: os.environ.get(k) for k in _REMOTE_ENV_KEYS}
    saved = {k: os.environ.pop(k, None) for k in _REMOTE_ENV_KEYS}
    try:
        os.environ[provider_client.ENV_ALLOW_REMOTE] = "1"
        enabled, failure_category = provider_client._check_remote_enabled(
            allow_remote=True, require_workflow_dispatch=False
        )
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)
    after = {k: os.environ.get(k) for k in _REMOTE_ENV_KEYS}
    return enabled, failure_category, after == before


def _self_test_probe_preserves_synthetic_provider_env() -> bool:
    """Regression guard: no-network self-test probes must not clear live env."""
    outer = {k: os.environ.get(k) for k in _REMOTE_ENV_KEYS}
    synthetic = {
        provider_client.ENV_BASE_URL: "https" + "://example.invalid/openai/v1",
        provider_client.ENV_API_KEY: "redacted-test-key",
        provider_client.ENV_MODEL: _ROUTING_PREFIX_SENTINEL + "Kimi-K2.7-Code",
        provider_client.ENV_ALLOW_REMOTE: "1",
        provider_client.ENV_WORKFLOW_DISPATCH: "1",
    }
    try:
        for k, v in synthetic.items():
            os.environ[k] = v
        _enabled, _failure_category, restored = (
            _probe_missing_env_without_mutating_remote_env()
        )
        return restored and all(
            os.environ.get(k) == v for k, v in synthetic.items()
        )
    finally:
        for k, v in outer.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)


# ---------------------------------------------------------------------------
# Self-test checks (no network; uses fake provider responses)
# ---------------------------------------------------------------------------


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all B16-E self-test groups (no network)."""
    checks: list[dict[str, Any]] = []

    # --- Group 1: Artifact identity fields. ---
    skeleton = _build_public_report([], False, status=STATUS_UNAVAILABLE)
    checks.append(
        _check(
            "schema_version_correct",
            skeleton["schema_version"] == SCHEMA_VERSION,
        )
    )
    checks.append(
        _check(
            "claim_level_correct",
            skeleton["claim_level"] == CLAIM_LEVEL,
        )
    )
    checks.append(
        _check("mode_correct", skeleton["mode"] == MODE)
    )
    checks.append(
        _check("phase_correct", skeleton["phase"] == PHASE)
    )
    checks.append(
        _check(
            "generated_by_correct",
            skeleton["generated_by"] == GENERATED_BY,
        )
    )
    for status in ALL_STATUSES:
        rep = _build_public_report([], False, status=status)
        checks.append(
            _check(
                f"status_{status}_preserved",
                rep["status"] == status,
            )
        )

    # --- Group 2: Always-false no-claim flags. ---
    for flag in DEFAULT_FALSE_FLAGS:
        checks.append(
            _check(
                f"default_false_{flag}",
                skeleton.get(flag) is False,
            )
        )

    # --- Group 3: Live-run flag gating. ---
    for flag in LIVE_TRUE_FLAGS:
        if flag in ("aggregate_only_public_artifact", "diagnostic_only"):
            continue
        checks.append(
            _check(
                f"unavailable_live_flag_false_{flag}",
                skeleton.get(flag) is False,
            )
        )
    live_rep = _build_public_report(
        [], True, status=STATUS_PASS, live_run_executed=True
    )
    for flag in LIVE_TRUE_FLAGS:
        checks.append(
            _check(
                f"live_flag_true_{flag}",
                live_rep.get(flag) is True,
            )
        )

    # --- Group 4: Four task families generation. ---
    tasks_8 = _generate_synthetic_tasks(8)
    checks.append(_check("synthetic_task_count_correct", len(tasks_8) == 8))
    family_counts = {}
    for t in tasks_8:
        family_counts[t["task_family"]] = (
            family_counts.get(t["task_family"], 0) + 1
        )
    for family in TASK_FAMILIES:
        checks.append(
            _check(
                f"family_present_{family}",
                family in family_counts and family_counts[family] >= 1,
            )
        )
    checks.append(
        _check(
            "families_balanced_2_each_for_8_tasks",
            all(family_counts.get(f, 0) == 2 for f in TASK_FAMILIES),
        )
    )
    # Family-specific deterministic values.
    f1 = next(t for t in tasks_8 if t["task_family"] == "same_symbol_support_relation")
    checks.append(
        _check(
            "family1_correct_value_uses_support_relation",
            f1["correct_value"] == f1["helper_constant_value"] * 2 + f1["index"],
        )
    )
    f2 = next(t for t in tasks_8 if t["task_family"] == "operation_ambiguity")
    checks.append(
        _check(
            "family2_correct_value_uses_multiply",
            f2["correct_value"] == f2["helper_constant_value"] * 2,
        )
    )
    f3 = next(t for t in tasks_8 if t["task_family"] == "boundary_condition")
    checks.append(
        _check(
            "family3_correct_value_uses_exclusive_bound",
            f3["correct_value"] == f3["helper_constant_value"] - 1,
        )
    )
    f4 = next(t for t in tasks_8 if t["task_family"] == "helper_dependency_choice")
    checks.append(
        _check(
            "family4_correct_value_uses_helper_b",
            f4["correct_value"] == f4["helper_constant_value"] * 3,
        )
    )

    # --- Group 5: Multi-file workspace per family. ---
    workspace_dir = Path(tempfile.mkdtemp(prefix="b16e_selftest_"))
    try:
        for family_task in (f1, f2, f3, f4):
            _build_workspace(workspace_dir, family_task)
            target_path = workspace_dir / family_task["target_module"]
            distractor_path = workspace_dir / family_task["distractor_module"]
            support_path = workspace_dir / family_task["support_module"]
            test_path = workspace_dir / family_task["test_module"]

            checks.append(
                _check(
                    f"workspace_{family_task['task_family']}_creates_target",
                    target_path.is_file(),
                )
            )
            checks.append(
                _check(
                    f"workspace_{family_task['task_family']}_creates_distractor",
                    distractor_path.is_file(),
                )
            )
            checks.append(
                _check(
                    f"workspace_{family_task['task_family']}_creates_support",
                    support_path.is_file(),
                )
            )
            checks.append(
                _check(
                    f"workspace_{family_task['task_family']}_creates_test",
                    test_path.is_file(),
                )
            )

            # Same/similar symbol in target and distractor.
            target_src = target_path.read_text(encoding="utf-8")
            distractor_src = distractor_path.read_text(encoding="utf-8")
            checks.append(
                _check(
                    f"workspace_{family_task['task_family']}_same_symbol",
                    f"def {family_task['symbol']}()" in target_src
                    and f"def {family_task['symbol']}()" in distractor_src,
                )
            )

            # Test fails before fix (bug present).
            proc_before = subprocess.run(
                [sys.executable, str(test_path)],
                check=False, capture_output=True, text=True, timeout=30,
            )
            checks.append(
                _check(
                    f"workspace_{family_task['task_family']}_test_fails_before_fix",
                    proc_before.returncode != 0,
                )
            )

        # --- Group 6: Pack builder (control lacks decisive cue). ---
        control_pack = _build_pack("control_sparse", f1)
        treatment_pack = _build_pack("treatment_context_pack", f1)
        checks.append(
            _check(
                "control_pack_lacks_target_file_cue",
                control_pack["has_target_file_cue"] is False,
            )
        )
        checks.append(
            _check(
                "control_pack_lacks_decisive_cue",
                control_pack["has_decisive_cue"] is False,
            )
        )
        checks.append(
            _check(
                "treatment_pack_has_target_file_cue",
                treatment_pack["has_target_file_cue"] is True,
            )
        )
        checks.append(
            _check(
                "treatment_pack_has_symbol_cue",
                treatment_pack["has_symbol_cue"] is True,
            )
        )
        checks.append(
            _check(
                "treatment_pack_has_decisive_cue",
                treatment_pack["has_decisive_cue"] is True,
            )
        )
        checks.append(
            _check(
                "treatment_pack_has_exact_edit_constraint",
                treatment_pack["has_exact_edit_constraint"] is True,
            )
        )
        checks.append(
            _check(
                "treatment_pack_richer_than_control",
                treatment_pack["context_tokens"]
                > control_pack["context_tokens"],
            )
        )

        # --- Group 7: Decisive cue text per family. ---
        for family_task in (f1, f2, f3, f4):
            cue_text = _decisive_cue_text(family_task)
            checks.append(
                _check(
                    f"decisive_cue_text_nonempty_{family_task['task_family']}",
                    len(cue_text) > 0,
                )
            )
            checks.append(
                _check(
                    f"decisive_cue_text_no_raw_routing_prefix_{family_task['task_family']}",
                    _ROUTING_PREFIX_SENTINEL not in cue_text,
                )
            )

        # --- Group 8: Fake valid provider response (treatment) per family.
        # ---
        for family_task in (f1, f2, f3, f4):
            _build_workspace(workspace_dir, family_task)
            fake_valid = {
                "action": "replace_return_value",
                "file": "target.py",
                "symbol": family_task["symbol"],
                "new_return_value": family_task["correct_value"],
            }
            tp = _build_pack("treatment_context_pack", family_task)
            run = _run_live_agent(
                workspace_dir, family_task, tp,
                allow_remote=False, require_workflow_dispatch=False,
                fake_response=fake_valid,
            )
            checks.append(
                _check(
                    f"fake_valid_{family_task['task_family']}_correct_file",
                    run["correct_file_before_first_edit"] is True,
                )
            )
            checks.append(
                _check(
                    f"fake_valid_{family_task['task_family']}_no_wrong_file",
                    run["wrong_file_edits"] == 0,
                )
            )
            checks.append(
                _check(
                    f"fake_valid_{family_task['task_family']}_tests_pass",
                    run["tests_pass"] is True,
                )
            )
            checks.append(
                _check(
                    f"fake_valid_{family_task['task_family']}_solve",
                    run["solve"] is True,
                )
            )
            checks.append(
                _check(
                    f"fake_valid_{family_task['task_family']}_provider_succeeded",
                    run["provider_summary"]["calls_succeeded"] == 1,
                )
            )
            # task_family carried through.
            checks.append(
                _check(
                    f"fake_valid_{family_task['task_family']}_family_recorded",
                    run["task_family"] == family_task["task_family"],
                )
            )

        # --- Group 9: Fake invalid JSON (parse failure). ---
        _build_workspace(workspace_dir, f1)
        run_invalid = _run_live_agent(
            workspace_dir, f1, control_pack,
            allow_remote=False, require_workflow_dispatch=False,
            fake_response=None,
        )
        checks.append(
            _check(
                "invalid_json_no_edit",
                run_invalid["tool_calls_before_first_edit"] == 0,
            )
        )
        checks.append(
            _check("invalid_json_tests_fail", run_invalid["tests_pass"] is False)
        )
        checks.append(
            _check(
                "no_raw_response_in_run_result",
                not any(
                    k in run_invalid
                    for k in ("raw_response", "response", "messages", "prompt")
                ),
            )
        )

        # --- Group 10: Edit action restrictions. ---
        valid, reason = _validate_edit_action(
            {"action": "replace_return_value", "file": "evil.py",
             "symbol": "x", "new_return_value": 1},
            f1,
        )
        checks.append(_check("disallowed_file_rejected", not valid))
        valid, reason = _validate_edit_action(
            {"action": "shell_exec", "file": "target.py",
             "symbol": "x", "new_return_value": 1},
            f1,
        )
        checks.append(_check("disallowed_action_rejected", not valid))
        valid, reason = _validate_edit_action(
            {"action": "replace_return_value", "file": "distractor.py",
             "symbol": "x", "new_return_value": 1},
            f1,
        )
        checks.append(_check("distractor_file_rejected", not valid))
        valid, reason = _validate_edit_action(
            {"action": "replace_return_value", "file": "support.py",
             "symbol": "x", "new_return_value": 1},
            f1,
        )
        checks.append(_check("support_file_rejected", not valid))
        valid, reason = _validate_edit_action(
            {"action": "replace_return_value", "file": "target.py",
             "new_return_value": 1},
            f1,
        )
        checks.append(_check("missing_symbol_rejected", not valid))
        valid, reason = _validate_edit_action(
            {"action": "replace_return_value", "file": "target.py",
             "symbol": "x", "new_return_value": "not_int"},
            f1,
        )
        checks.append(_check("non_int_return_rejected", not valid))
        valid, reason = _validate_edit_action([], f1)
        checks.append(_check("non_object_rejected", not valid))
        valid, reason = _validate_edit_action(
            {"action": "replace_return_value", "file": "target.py",
             "symbol": "x", "new_return_value": 1},
            f1,
        )
        checks.append(_check("valid_action_accepted", valid))
        valid, reason = _validate_edit_action(
            {"action": "choose_helper_constant", "file": "target.py",
             "symbol": "x", "new_return_value": 1},
            f1,
        )
        checks.append(_check("choose_helper_constant_accepted", valid))
        valid, reason = _validate_edit_action(
            {"action": "no_op", "file": "target.py", "symbol": "x"},
            f1,
        )
        checks.append(_check("no_op_action_accepted", valid))

        # --- Group 11: Aggregate metrics + family results + honest signals.
        # ---
        # Build a small synthetic arm_runs with two families.
        _build_workspace(workspace_dir, f1)
        run_f1_t = _run_live_agent(
            workspace_dir, f1, treatment_pack,
            allow_remote=False, require_workflow_dispatch=False,
            fake_response={
                "action": "replace_return_value", "file": "target.py",
                "symbol": f1["symbol"],
                "new_return_value": f1["correct_value"],
            },
        )
        _build_workspace(workspace_dir, f2)
        run_f2_c = _run_live_agent(
            workspace_dir, f2, control_pack,
            allow_remote=False, require_workflow_dispatch=False,
            fake_response=None,  # parse failure
        )
        arm_runs_test = {
            "control_sparse": [run_f2_c],
            "treatment_context_pack": [run_f1_t],
        }
        metrics, ps = _aggregate_arm_metrics([run_f1_t, run_f2_c])
        checks.append(
            _check("aggregate_run_count_correct", metrics["run_count"] == 2)
        )
        checks.append(
            _check(
                "aggregate_solve_rate_correct",
                _round_metric(metrics["solve_rate"]) == _round_metric(0.5),
            )
        )
        family_results = _aggregate_family_results(arm_runs_test)
        checks.append(
            _check(
                "family_results_records_shaped",
                all(
                    set(r.keys()) == {
                        "task_family", "arm", "run_count", "solve_rate",
                        "tests_pass_rate",
                        "correct_file_before_first_edit_rate",
                        "wrong_file_edits_mean",
                    }
                    for r in family_results
                ),
            )
        )
        checks.append(
            _check(
                "family_results_all_four_families",
                set(r["task_family"] for r in family_results) == set(TASK_FAMILIES),
            )
        )
        checks.append(
            _check(
                "family_results_two_arms_per_family",
                all(
                    sum(1 for r in family_results if r["task_family"] == fam) == 2
                    for fam in TASK_FAMILIES
                ),
            )
        )
        # Family signal summary.
        fss = _compute_family_signal_summary(family_results)
        checks.append(
            _check(
                "family_signal_summary_has_counts",
                set(fss.keys()) == {
                    "families_evaluated",
                    "families_with_positive_solve_delta",
                    "families_with_zero_solve_delta",
                    "families_with_negative_solve_delta",
                },
            )
        )
        # Honest signals.
        control_metrics = {
            "run_count": 1, "solve_rate": 0.0, "tests_pass_rate": 0.0,
            "correct_file_before_first_edit_rate": 0.0,
            "wrong_file_edits_mean": 0.0,
            "tool_calls_before_first_edit_mean": 0.0,
            "context_tokens_mean": 20.0, "latency_ms_mean": 10.0,
            "cost_proxy_mean": 0.0,
        }
        treatment_metrics = {
            "run_count": 1, "solve_rate": 1.0, "tests_pass_rate": 1.0,
            "correct_file_before_first_edit_rate": 1.0,
            "wrong_file_edits_mean": 0.0,
            "tool_calls_before_first_edit_mean": 1.0,
            "context_tokens_mean": 64.0, "latency_ms_mean": 20.0,
            "cost_proxy_mean": 0.0,
        }
        deltas = _compute_deltas(control_metrics, treatment_metrics)
        honest = _compute_honest_signals(
            control_metrics, treatment_metrics, deltas, fss
        )
        checks.append(
            _check(
                "honest_signal_context_pack_observed_true",
                honest["context_pack_signal_observed"] is True,
            )
        )
        checks.append(
            _check(
                "honest_signal_solve_rate_delta_positive",
                honest["overall_treatment_solve_rate_delta"] == 1.0,
            )
        )
        # Zero delta -> not observed.
        zero_deltas = _compute_deltas(control_metrics, control_metrics)
        zero_fss = {
            "families_evaluated": 0,
            "families_with_positive_solve_delta": 0,
            "families_with_zero_solve_delta": 0,
            "families_with_negative_solve_delta": 0,
        }
        honest_zero = _compute_honest_signals(
            control_metrics, control_metrics, zero_deltas, zero_fss
        )
        checks.append(
            _check(
                "honest_signal_zero_delta_not_observed",
                honest_zero["context_pack_signal_observed"] is False,
            )
        )

        # --- Group 12: Model display normalization. ---
        checks.append(
            _check(
                "normalize_strips_routing_prefix",
                _normalize_model_display(
                    _ROUTING_PREFIX_SENTINEL + "Kimi-K2.7-Code"
                ) == "Kimi-K2.7-Code",
            )
        )
        checks.append(
            _check(
                "normalize_empty_returns_unavailable",
                _normalize_model_display("") == "unavailable",
            )
        )
        checks.append(
            _check(
                "normalize_strips_unsafe_chars",
                _normalize_model_display(
                    _ROUTING_PREFIX_SENTINEL + "Test;Model!@#"
                ) == "TestModel",
            )
        )

        # --- Group 13: Env preservation self-test. ---
        checks.append(
            _check(
                "env_preservation_probe_restores_env",
                _self_test_probe_preserves_synthetic_provider_env(),
            )
        )
        enabled, failure_category, restored = (
            _probe_missing_env_without_mutating_remote_env()
        )
        checks.append(
            _check(
                "probe_missing_env_returns_missing_env",
                not enabled
                and failure_category
                == provider_client.FAILURE_CATEGORY_MISSING_ENV,
            )
        )
        checks.append(
            _check(
                "probe_missing_env_restores_env",
                restored,
            )
        )
    finally:
        try:
            shutil.rmtree(workspace_dir, ignore_errors=True)
        except OSError:
            pass

    # --- Group 14: Scanner rejections. ---
    checks.append(
        _check(
            "scanner_rejects_tmp_workspace_path",
            bool(_scan_forbidden({"leaked_workspace": "/tmp/b16e_workspace_0"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_file_path_value",
            bool(_scan_forbidden({"leaked_file": "target.py"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_source_snippet",
            bool(_scan_forbidden({"leaked_snippet": "def resolve():\n    return 0\n"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_patch_marker",
            bool(_scan_forbidden({"leaked_patch": "--- a/target.py\n+++ b/target.py\n"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_test_output",
            bool(_scan_forbidden({"leaked_stdout": "test passed\nok\n"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_task_id_key",
            bool(_scan_forbidden({"task_id": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_raw_event_log",
            bool(_scan_forbidden({"leaked_log": '{"event": "edit", "file": "target.py"}'})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_stack_trace",
            bool(_scan_forbidden({"leaked_trace": "Traceback (most recent call last):\n"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_content_sha_key",
            bool(_scan_forbidden({"content_sha": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_hex_digest_value",
            bool(_scan_forbidden({"leaked_hash": "a" * 32})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_provider_auth_field_string",
            bool(_scan_forbidden({"leaked": "api_key=" + "sk-" + "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_endpoint_url_field_string",
            bool(_scan_forbidden({"leaked": "base_url=" + "https" + "://x.example"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_raw_routing_prefix",
            bool(_scan_forbidden({"leaked": _ROUTING_PREFIX_SENTINEL + "Kimi-K2.7-Code"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_url_value",
            bool(_scan_forbidden({"leaked": "https" + "://example.com"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_prompt_key",
            bool(_scan_forbidden({"prompt": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_response_key",
            bool(_scan_forbidden({"response": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_messages_key",
            bool(_scan_forbidden({"messages": []})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_provider_payload_key",
            bool(_scan_forbidden({"provider_payload": {}})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_sentinel_canary",
            bool(_scan_forbidden({"leaked": _SECRET_SENTINEL})),
        )
    )

    # --- Group 15: Scanner allows legitimate aggregate values. ---
    checks.append(
        _check(
            "scanner_allows_arm_name_control",
            not _scan_forbidden({"arm": "control_sparse"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_arm_name_treatment",
            not _scan_forbidden({"arm": "treatment_context_pack"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_task_family_names",
            not _scan_forbidden({"task_family": "operation_ambiguity"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_metric_records",
            not _scan_forbidden(
                {
                    "paired_deltas": [
                        {
                            "baseline_arm": "control_sparse",
                            "treatment_arm": "treatment_context_pack",
                            "metric": "solve_rate",
                            "delta": 1.0,
                        }
                    ]
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_family_results_records",
            not _scan_forbidden(
                {
                    "task_family_results": [
                        {
                            "task_family": "boundary_condition",
                            "arm": "treatment_context_pack",
                            "run_count": 2,
                            "solve_rate": 1.0,
                            "tests_pass_rate": 1.0,
                            "correct_file_before_first_edit_rate": 1.0,
                            "wrong_file_edits_mean": 0.0,
                        }
                    ]
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_model_display_category",
            not _scan_forbidden({"model_display_category": "Kimi-K2.7-Code"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_honest_signal_fields",
            not _scan_forbidden(
                {
                    "honest_signals": {
                        "context_pack_signal_observed": True,
                        "overall_treatment_solve_rate_delta": 1.0,
                        "overall_treatment_tests_pass_rate_delta": 1.0,
                        "families_evaluated": 4,
                        "families_with_positive_solve_delta": 2,
                        "families_with_zero_solve_delta": 1,
                        "families_with_negative_solve_delta": 1,
                    }
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_failure_category_token",
            not _scan_forbidden({"failure_category": "ok"}),
        )
    )

    # --- Group 16: Fail-closed generation. ---
    try:
        _enforce_no_forbidden(skeleton)
        clean_passes = True
    except SystemExit:
        clean_passes = False
    checks.append(
        _check(
            "fail_closed_clean_public_report_does_not_raise",
            clean_passes,
        )
    )
    leaked_report = dict(skeleton)
    leaked_report["leaked_path"] = "src/openlocus/lib.rs"
    try:
        _enforce_no_forbidden(leaked_report)
        leak_raises = False
    except SystemExit:
        leak_raises = True
    checks.append(
        _check("fail_closed_generation_raises_on_leak", leak_raises)
    )
    failed_report = dict(skeleton)
    failed_report["self_test_passed"] = False
    try:
        _refuse_on_self_test_failure(failed_report)
        refuse_failed_raises = False
    except SystemExit:
        refuse_failed_raises = True
    checks.append(
        _check(
            "refuse_on_self_test_failure_raises_when_failed",
            refuse_failed_raises,
        )
    )
    passed_report = dict(skeleton)
    passed_report["self_test_passed"] = True
    try:
        _refuse_on_self_test_failure(passed_report)
        refuse_passed_does_not_raise = True
    except SystemExit:
        refuse_passed_does_not_raise = False
    checks.append(
        _check(
            "refuse_on_self_test_failure_does_not_raise_when_passed",
            refuse_passed_does_not_raise,
        )
    )

    # --- Group 17: Public artifact self-scan is clean. ---
    checks.append(
        _check(
            "public_report_forbidden_scan_clean",
            skeleton["forbidden_scan"]["status"] == "pass",
        )
    )
    checks.append(
        _check(
            "public_report_no_forbidden_key_anywhere",
            not any(
                _has_dict_key_anywhere(skeleton, bad)
                for bad in (
                    "task_id", "workspace_path", "file_path",
                    "target_file", "path", "file", "snippet", "code",
                    "patch", "diff", "test_output", "event_log",
                    "stack_trace", "content_sha", "content_hash",
                    "api_key", "base_url", "provider_key", "secret",
                    "token", "stdout", "stderr", "rows", "per_run",
                    "predictions", "prompt", "messages", "response",
                    "provider_payload", "request", "request_body",
                    "model_id_raw", "support_module",
                )
            ),
        )
    )

    # --- Group 18: CLI argument surface. ---
    cli_opts = _cli_argument_option_strings()
    checks.append(
        _check("cli_has_self_test_argument", "--self-test" in cli_opts)
    )
    checks.append(_check("cli_has_out_argument", "--out" in cli_opts))
    checks.append(
        _check("cli_has_allow_remote_argument", "--allow-remote" in cli_opts)
    )
    checks.append(
        _check(
            "cli_has_require_workflow_dispatch_argument",
            "--require-workflow-dispatch" in cli_opts,
        )
    )
    checks.append(
        _check("cli_has_task_count_argument", "--task-count" in cli_opts)
    )
    checks.append(
        _check(
            "cli_only_expected_arguments",
            (cli_opts - {"-h", "--help"})
            == {
                "--self-test",
                "--out",
                "--allow-remote",
                "--require-workflow-dispatch",
                "--task-count",
            },
        )
    )
    checks.append(
        _check(
            "cli_default_task_count_in_range",
            MIN_TASK_COUNT <= DEFAULT_TASK_COUNT <= MAX_TASK_COUNT,
        )
    )

    # --- Group 19: Remote gating. ---
    enabled, failure_category = provider_client._check_remote_enabled(
        allow_remote=False, require_workflow_dispatch=False
    )
    checks.append(
        _check(
            "blocked_when_allow_remote_false",
            not enabled
            and failure_category
            == provider_client.FAILURE_CATEGORY_REMOTE_NOT_ENABLED,
        )
    )
    blocked_rep = _build_public_report(
        [], True, status=STATUS_BLOCKED_REMOTE, live_run_executed=False
    )
    checks.append(
        _check(
            "blocked_report_live_flags_false",
            all(
                blocked_rep.get(flag) is False
                for flag in LIVE_TRUE_FLAGS
                if flag not in (
                    "aggregate_only_public_artifact", "diagnostic_only"
                )
            ),
        )
    )
    checks.append(
        _check(
            "blocked_report_forbidden_scan_pass",
            blocked_rep["forbidden_scan"]["status"] == "pass",
        )
    )

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
            "B16-E broader live-provider downstream paired smoke "
            "(public aggregate-only artifact; synthetic public "
            "task-family matrix; fresh /tmp workspace per task+arm; "
            "real file edits + real subprocess tests; live LLM "
            "provider only when --allow-remote + "
            "OPENLOCUS_ALLOW_REMOTE=1 + env; no raw prompt/response/"
            "payload committed; CI pass does NOT require treatment "
            "improvement)."
        )
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="run no-network self-test and exit (no artifact written)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output artifact JSON path",
    )
    ap.add_argument(
        "--allow-remote",
        action="store_true",
        help="allow live provider calls (requires OPENLOCUS_ALLOW_REMOTE=1)",
    )
    ap.add_argument(
        "--require-workflow-dispatch",
        action="store_true",
        help="require OPENLOCUS_LLM_WORKFLOW_DISPATCH=1 for live calls",
    )
    ap.add_argument(
        "--task-count",
        type=int,
        default=DEFAULT_TASK_COUNT,
        help=(
            f"number of synthetic micro tasks (default {DEFAULT_TASK_COUNT}; "
            f"range {MIN_TASK_COUNT}-{MAX_TASK_COUNT})"
        ),
    )
    return ap


def _cli_argument_option_strings() -> set[str]:
    parser = build_parser()
    strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            strings.add(opt)
    return strings


def _validate_task_count(task_count: int) -> None:
    if not isinstance(task_count, int):
        raise SystemExit("invalid arguments")
    if task_count < MIN_TASK_COUNT or task_count > MAX_TASK_COUNT:
        raise SystemExit("invalid arguments")


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

    _validate_task_count(args.task_count)

    out_path = args.out if args.out is not None else DEFAULT_OUT
    try:
        report = build_report(
            task_count=args.task_count,
            allow_remote=args.allow_remote,
            require_workflow_dispatch=args.require_workflow_dispatch,
        )
    except (OSError, subprocess.SubprocessError):
        print("error: failed to build report", file=sys.stderr)
        sys.exit(1)

    _enforce_no_forbidden(report)
    _refuse_on_self_test_failure(report)
    _write_json(out_path, report)
    print(
        f"wrote artifact "
        f"(forbidden_scan={report['forbidden_scan']['status']}, "
        f"self_test_passed={report['self_test_passed']}, "
        f"status={report['status']}, "
        f"phase={report['phase']})"
    )


if __name__ == "__main__":
    main()
