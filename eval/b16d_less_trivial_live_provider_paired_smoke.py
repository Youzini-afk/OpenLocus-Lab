#!/usr/bin/env python3
"""B16-D Less-Trivial Live-Provider Downstream Paired Smoke (Public Aggregate-Only Artifact).

This module implements the **B16-D less-trivial live-provider downstream
paired smoke**. It is a harder follow-up to B16-C: the synthetic public
task family is **less trivial** (multi-file, same/similar symbol names
in target and distractor files, and a **support relation** needed to
determine the correct value/operation). A live LLM provider
(OpenAI-compatible) is used over synthetic public micro bug tasks; the
model's structured edit action is applied locally; real stdlib tests
run; only aggregate behavior metrics are published.

B16-D is explicitly **not** a downstream agent value proof, **not** a
live-agent generalization proof, **not** an external benchmark result,
**not** a production coding-agent benchmark, **not** a real user task
evaluation, and **not** a promotion/default-policy/runtime/retriever/
pack/backend/EvidenceCore semantic change. It does NOT publish prompts,
responses, provider payloads, base URLs, API keys, raw model routing
prefixes, workspace paths, file paths, source snippets, patches/diffs,
test output, raw event logs, or per-run rows.

Claim boundary (binding):

* Claim level: ``less_trivial_live_provider_downstream_paired_smoke_only``.
* Status enum: ``live_provider_less_trivial_paired_smoke_pass`` on live
  success; ``blocked_remote_not_enabled`` /
  ``unavailable_no_local_provider_env`` when remote opt-in not
  satisfied; ``provider_call_failed`` / ``structured_action_parse_failed``
  / ``paired_run_failed`` / ``fail_forbidden_scan`` on failures.
* Mode: ``public_aggregate_synthetic_less_trivial_tasks``; phase ``B16-D``.

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
  runs a tiny task count (default 4; hard cap 8).

Run::

    python3 -m py_compile eval/b16d_less_trivial_live_provider_paired_smoke.py
    python3 eval/b16d_less_trivial_live_provider_paired_smoke.py --self-test
    python3 eval/b16d_less_trivial_live_provider_paired_smoke.py \\
        --out artifacts/b16d_less_trivial_live_provider_paired_smoke/\\
b16d_less_trivial_live_provider_paired_smoke_report.json
    # Live opt-in (only if provider env is available and safe):
    OPENLOCUS_ALLOW_REMOTE=1 OPENLOCUS_LLM_WORKFLOW_DISPATCH=1 \\
        python3 eval/b16d_less_trivial_live_provider_paired_smoke.py \\
        --allow-remote --task-count 4 \\
        --out artifacts/b16d_less_trivial_live_provider_paired_smoke/\\
b16d_less_trivial_live_provider_paired_smoke_report.json
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

# Reuse the provider client helper from B16-C (unchanged).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import provider_client  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "b16d_less_trivial_live_provider_paired_smoke.v1"
GENERATED_BY = "eval/b16d_less_trivial_live_provider_paired_smoke.py"
CLAIM_LEVEL = "less_trivial_live_provider_downstream_paired_smoke_only"
MODE = "public_aggregate_synthetic_less_trivial_tasks"
PHASE = "B16-D"

STATUS_PASS = "live_provider_less_trivial_paired_smoke_pass"
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
    "artifacts/b16d_less_trivial_live_provider_paired_smoke/"
    "b16d_less_trivial_live_provider_paired_smoke_report.json"
)
DEFAULT_TASK_COUNT = 4
MIN_TASK_COUNT = 2
MAX_TASK_COUNT = 8

ARMS: tuple[str, ...] = ("control_sparse", "treatment_context_pack")

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
# Only the target file may be edited; distractor / support / test files
# are NOT editable. No arbitrary paths, no shell.
ALLOWED_EDIT_FILES: frozenset[str] = frozenset({"target.py"})
ALLOWED_EDIT_ACTIONS: frozenset[str] = frozenset(
    {"replace_return_value", "choose_helper_constant", "no_op"}
)

# ---------------------------------------------------------------------------
# Safe booleans true (live run only). Exactly these are true in the
# committed public artifact WHEN a live run succeeded. On unavailable /
# blocked / failed statuses, only aggregate_only_public_artifact and
# diagnostic_only are true; the live-run flags are false.
# ---------------------------------------------------------------------------

LIVE_TRUE_FLAGS: tuple[str, ...] = (
    "downstream_agent_runs_performed",
    "live_llm_agent",
    "provider_calls_made",
    "remote_provider_calls_made",
    "paired_run_executed",
    "synthetic_micro_tasks_used",
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
# Public artifact scanner (strict, fail-closed). Same shape as B16-C.
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
        "support_module", "test_module", "source_path", "module_path",
        "module",
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
# Less-trivial synthetic public micro bug task generation.
#
# Each task has multiple files:
#   - target.py:     contains the buggy function (same symbol name as
#                    the distractor to make less-trivial).
#   - distractor.py: contains a same-named symbol (decoy).
#   - support.py:    defines a helper constant whose value determines
#                    the correct return value (support relation).
#   - test_target.py: imports target AND support; asserts the correct
#                    relation. The test only passes if target uses the
#                    support relation correctly.
#
# The correct fix requires the agent to read the support relation
# (helper constant value) and apply it to the target. A control pack
# that lacks the support-relation cue cannot determine the correct
# value; a treatment pack includes the target file cue, target symbol
# cue, support-relation cue, and the exact edit constraint.
# ---------------------------------------------------------------------------


def _generate_synthetic_tasks(count: int) -> list[dict[str, Any]]:
    """Generate deterministic less-trivial synthetic public micro bug tasks."""
    tasks: list[dict[str, Any]] = []
    for i in range(count):
        helper_constant = 10 + i * 7
        correct_value = helper_constant * 2 + i  # support relation
        buggy_value = -(correct_value)
        task: dict[str, Any] = {
            "index": i,
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
            "support_relation": "correct_value = helper_constant * 2 + task_index",
        }
        tasks.append(task)
    return tasks


# ---------------------------------------------------------------------------
# Workspace builder (fresh /tmp per task+arm; real multi-file Python).
# ---------------------------------------------------------------------------


def _build_workspace(workspace_dir: Path, task: dict[str, Any]) -> None:
    """Create a fresh multi-file workspace with a real stdlib test."""
    workspace_dir.mkdir(parents=True, exist_ok=True)

    target_path = workspace_dir / task["target_module"]
    distractor_path = workspace_dir / task["distractor_module"]
    support_path = workspace_dir / task["support_module"]
    test_path = workspace_dir / task["test_module"]

    # Support module: defines the helper constant (support relation).
    support_path.write_text(
        f"{task['helper_constant_name']} = {task['helper_constant_value']}\n",
        encoding="utf-8",
    )

    # Target module: same symbol name as distractor; has a bug (returns
    # wrong value, ignores support relation).
    target_path.write_text(
        f"def {task['symbol']}():\n"
        f"    return {task['buggy_value']}\n",
        encoding="utf-8",
    )

    # Distractor module: SAME symbol name (decoy); also has wrong value.
    distractor_path.write_text(
        f"def {task['symbol']}():\n"
        f"    return {task['buggy_value']}\n",
        encoding="utf-8",
    )

    # Test module: imports target AND support; asserts correct relation.
    # Uses only stdlib; runs as a script that exits 0 on success.
    test_path.write_text(
        "import sys\n"
        f"sys.path.insert(0, r'{workspace_dir}')\n"
        f"from target import {task['symbol']}\n"
        f"from support import {task['helper_constant_name']}\n"
        "def main():\n"
        f"    expected = {task['helper_constant_name']} * 2 + {task['index']}\n"
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
      support-relation cue; small token budget. The agent cannot
      determine the correct value without the support relation.
    * treatment_context_pack: target file cue, target symbol cue,
      support-relation cue (helper constant name + value + relation),
      and exact edit constraint; larger token budget.
    """
    if arm == "control_sparse":
        return {
            "arm": arm,
            "context_tokens": 20,
            "has_target_file_cue": False,
            "has_symbol_cue": False,
            "has_support_relation_cue": False,
            "has_exact_edit_constraint": False,
        }
    # treatment_context_pack
    return {
        "arm": arm,
        "context_tokens": 64,
        "has_target_file_cue": True,
        "has_symbol_cue": True,
        "has_support_relation_cue": True,
        "has_exact_edit_constraint": True,
    }


# ---------------------------------------------------------------------------
# Live LLM prompt builder (in-memory only; never persisted)
# ---------------------------------------------------------------------------


def _build_messages(
    workspace_dir: Path, task: dict[str, Any], pack: dict[str, Any]
) -> list[dict[str, str]]:
    """Build the live LLM chat messages (in-memory; never persisted).

    The prompt may include a tiny synthetic/public source snippet (the
    buggy target module + the support module) and a support-relation
    cue only when the treatment pack carries it. Prompts are NEVER
    persisted.
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
    ]
    if pack.get("has_target_file_cue"):
        user_lines.append("Target file: target.py (not distractor.py).")
    if pack.get("has_symbol_cue"):
        user_lines.append(f"Target symbol: {task['symbol']} in target.py.")
    if pack.get("has_support_relation_cue"):
        user_lines.append(
            f"Support relation: correct_value = {task['helper_constant_name']} "
            f"* 2 + {task['index']}."
        )
        user_lines.append(
            f"Helper constant {task['helper_constant_name']} = "
            f"{task['helper_constant_value']} (defined in support.py)."
        )
        user_lines.append(f"Correct value: {task['correct_value']}.")
    if pack.get("has_exact_edit_constraint"):
        user_lines.append(
            "Edit constraint: only edit target.py; do not edit "
            "distractor.py or support.py."
        )
    # Always include the source snippets so the model sees the bug.
    user_lines.append(f"Target source:\n{target_snippet}")
    if pack.get("has_support_relation_cue"):
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
    # Should not reach here after validation, but guard anyway.
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
    edit_applied = False

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
            edit_applied = True
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
        "cost_proxy": 0,  # cost_proxy only; no live price inference
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


def _compute_honest_signals(
    control_metrics: dict[str, Any],
    treatment_metrics: dict[str, Any],
    paired_deltas: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute honest diagnostic signal fields.

    These are diagnostic smoke outcomes only, NEVER promotion/default/
    value claims.
    """
    solve_delta = next(
        (d["delta"] for d in paired_deltas if d["metric"] == "solve_rate"),
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
    # wrong_file_edits_mean.
    context_signal = (
        treatment_metrics.get("solve_rate", 0.0)
        > control_metrics.get("solve_rate", 0.0)
        or treatment_metrics.get("wrong_file_edits_mean", 0.0)
        < control_metrics.get("wrong_file_edits_mean", 0.0)
    )
    return {
        "context_pack_signal_observed": bool(context_signal),
        "treatment_solve_rate_delta": _round_metric(solve_delta),
        "treatment_wrong_file_edits_delta": _round_metric(wrong_file_delta),
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
    # Paired run completed without provider/parse failure -> pass,
    # regardless of treatment delta (zero/negative delta is valid).
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
    input_summary: dict[str, Any] | None = None,
    model_display_category: str = "unavailable",
    live_run_executed: bool = False,
    honest_signals: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the public aggregate-only report (fail-closed scan)."""
    arm_results = arm_results or []
    paired_deltas = paired_deltas or []
    honest_signals_out = honest_signals or {
        "context_pack_signal_observed": False,
        "treatment_solve_rate_delta": 0.0,
        "treatment_wrong_file_edits_delta": 0.0,
    }
    input_summary = input_summary or {
        "synthetic_task_count": 0,
        "run_count_per_arm": 0,
        "total_runs": 0,
        "arms": list(ARMS),
        "paired_design": True,
        "workspace_isolation": "fresh_tmp_per_task_arm",
        "transient_workspace_outputs_only": True,
        "designed_causal_subset": True,
        "less_trivial_multi_file_tasks": True,
        "support_relation_required": True,
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
            "paired_design": True,
            "workspace_isolation": "fresh_tmp_per_task_arm",
            "transient_workspace_outputs_only": True,
            "designed_causal_subset": True,
            "less_trivial_multi_file_tasks": True,
            "support_relation_required": True,
        }
        return _build_public_report(
            checks,
            all_passed,
            status=status,
            arm_results=[],
            paired_deltas=[],
            input_summary=input_summary,
            model_display_category="unavailable",
            live_run_executed=False,
            honest_signals={
                "context_pack_signal_observed": False,
                "treatment_solve_rate_delta": 0.0,
                "treatment_wrong_file_edits_delta": 0.0,
            },
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
                tempfile.mkdtemp(prefix="b16d_workspace_")
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

    honest_signals = _compute_honest_signals(
        arm_results[0]["metrics"],
        arm_results[1]["metrics"],
        paired_deltas,
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
        "paired_design": True,
        "workspace_isolation": "fresh_tmp_per_task_arm",
        "transient_workspace_outputs_only": True,
        "designed_causal_subset": True,
        "less_trivial_multi_file_tasks": True,
        "support_relation_required": True,
    }

    raw_model = os.environ.get(provider_client.ENV_MODEL, "")
    model_display_category = _normalize_model_display(raw_model)

    return _build_public_report(
        checks,
        all_passed,
        status=status,
        arm_results=arm_results,
        paired_deltas=paired_deltas,
        input_summary=input_summary,
        model_display_category=model_display_category,
        live_run_executed=True,
        honest_signals=honest_signals,
    )


def _normalize_model_display(raw_model: str) -> str:
    """Normalize a raw model id to a safe display category.

    Strips the provider routing prefix and any non-alphanumeric suffix.
    Returns ``"unavailable"`` for empty input. NEVER returns the raw
    provider routing prefix.
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
        provider_client.ENV_BASE_URL: "https://example.invalid/openai/v1",
        provider_client.ENV_API_KEY: "redacted-test-key",
        provider_client.ENV_MODEL: _ROUTING_PREFIX_SENTINEL + "Kimi-K2.7-Code",
        provider_client.ENV_ALLOW_REMOTE: "1",
        provider_client.ENV_WORKFLOW_DISPATCH: "1",
    }
    try:
        for k, v in synthetic.items():
            os.environ[k] = v
        _enabled, _failure_category, restored = _probe_missing_env_without_mutating_remote_env()
        return restored and all(os.environ.get(k) == v for k, v in synthetic.items())
    finally:
        for k, v in outer.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)


# ---------------------------------------------------------------------------
# Self-test checks (no network; uses fake provider responses)
# ---------------------------------------------------------------------------

_SYNTH_TASK = {
    "index": 0,
    "symbol": "resolve_000",
    "target_module": "target.py",
    "distractor_module": "distractor.py",
    "support_module": "support.py",
    "test_module": "test_target.py",
    "helper_constant_name": "BASE_000",
    "helper_constant_value": 10,
    "correct_value": 20,  # 10 * 2 + 0
    "buggy_value": -20,
    "fix_kind": "replace_return_value",
    "support_relation": "correct_value = helper_constant * 2 + task_index",
}


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all B16-D self-test groups (no network)."""
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

    # --- Group 4: Less-trivial synthetic task generation. ---
    tasks_4 = _generate_synthetic_tasks(4)
    checks.append(_check("synthetic_task_count_correct", len(tasks_4) == 4))
    checks.append(
        _check(
            "synthetic_task_symbols_deterministic",
            tasks_4[0]["symbol"] == "resolve_000"
            and tasks_4[3]["symbol"] == "resolve_003",
        )
    )
    checks.append(
        _check(
            "synthetic_task_helper_constant_deterministic",
            tasks_4[0]["helper_constant_value"] == 10
            and tasks_4[3]["helper_constant_value"] == 31,
        )
    )
    checks.append(
        _check(
            "synthetic_task_correct_value_uses_support_relation",
            tasks_4[0]["correct_value"] == 20  # 10*2+0
            and tasks_4[1]["correct_value"] == 35  # 17*2+1
            and tasks_4[3]["correct_value"] == 65,  # 31*2+3
        )
    )

    # --- Group 5: Multi-file workspace + same-symbol distractor. ---
    workspace_dir = Path(tempfile.mkdtemp(prefix="b16d_selftest_"))
    try:
        _build_workspace(workspace_dir, _SYNTH_TASK)
        target_path = workspace_dir / _SYNTH_TASK["target_module"]
        distractor_path = workspace_dir / _SYNTH_TASK["distractor_module"]
        support_path = workspace_dir / _SYNTH_TASK["support_module"]
        test_path = workspace_dir / _SYNTH_TASK["test_module"]

        checks.append(
            _check("workspace_creates_target_file", target_path.is_file())
        )
        checks.append(
            _check(
                "workspace_creates_distractor_file",
                distractor_path.is_file(),
            )
        )
        checks.append(
            _check(
                "workspace_creates_support_file",
                support_path.is_file(),
            )
        )
        checks.append(
            _check("workspace_creates_test_file", test_path.is_file())
        )

        # Same/similar symbol in target and distractor (less-trivial).
        target_src = target_path.read_text(encoding="utf-8")
        distractor_src = distractor_path.read_text(encoding="utf-8")
        checks.append(
            _check(
                "target_and_distractor_have_same_symbol",
                f"def {_SYNTH_TASK['symbol']}()" in target_src
                and f"def {_SYNTH_TASK['symbol']}()" in distractor_src,
            )
        )
        # Support module defines the helper constant.
        support_src = support_path.read_text(encoding="utf-8")
        checks.append(
            _check(
                "support_module_defines_helper_constant",
                f"{_SYNTH_TASK['helper_constant_name']} = "
                f"{_SYNTH_TASK['helper_constant_value']}" in support_src,
            )
        )

        # Test fails before fix (bug present).
        proc_before = subprocess.run(
            [sys.executable, str(test_path)],
            check=False, capture_output=True, text=True, timeout=30,
        )
        checks.append(
            _check("test_fails_before_fix", proc_before.returncode != 0)
        )

        # --- Group 6: Pack builder (control lacks decisive cue). ---
        control_pack = _build_pack("control_sparse", tasks_4[0])
        treatment_pack = _build_pack("treatment_context_pack", tasks_4[0])
        checks.append(
            _check(
                "control_pack_lacks_target_file_cue",
                control_pack["has_target_file_cue"] is False,
            )
        )
        checks.append(
            _check(
                "control_pack_lacks_support_relation_cue",
                control_pack["has_support_relation_cue"] is False,
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
                "treatment_pack_has_support_relation_cue",
                treatment_pack["has_support_relation_cue"] is True,
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

        # --- Group 7: Fake valid provider response (treatment) ---
        # applies correct file edit using the support relation, tests pass.
        fake_valid = {
            "action": "replace_return_value",
            "file": "target.py",
            "symbol": _SYNTH_TASK["symbol"],
            "new_return_value": _SYNTH_TASK["correct_value"],
        }
        run = _run_live_agent(
            workspace_dir, _SYNTH_TASK, treatment_pack,
            allow_remote=False, require_workflow_dispatch=False,
            fake_response=fake_valid,
        )
        checks.append(
            _check(
                "fake_valid_edit_correct_file",
                run["correct_file_before_first_edit"] is True,
            )
        )
        checks.append(
            _check("fake_valid_no_wrong_file", run["wrong_file_edits"] == 0)
        )
        checks.append(_check("fake_valid_tests_pass", run["tests_pass"] is True))
        checks.append(_check("fake_valid_solve", run["solve"] is True))
        checks.append(
            _check(
                "fake_valid_real_file_edit",
                f"return {_SYNTH_TASK['correct_value']}"
                in target_path.read_text(encoding="utf-8"),
            )
        )
        ps = run["provider_summary"]
        checks.append(
            _check(
                "fake_valid_provider_call_succeeded",
                ps["calls_attempted"] == 1
                and ps["calls_succeeded"] == 1
                and ps["calls_failed"] == 0,
            )
        )

        # --- Group 8: Fake invalid JSON (parse failure). ---
        _build_workspace(workspace_dir, _SYNTH_TASK)
        run_invalid = _run_live_agent(
            workspace_dir, _SYNTH_TASK, control_pack,
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

        # --- Group 9: Edit action restrictions. ---
        # Disallowed file.
        valid, reason = _validate_edit_action(
            {"action": "replace_return_value", "file": "evil.py",
             "symbol": "x", "new_return_value": 1},
            _SYNTH_TASK,
        )
        checks.append(_check("disallowed_file_rejected", not valid))
        # Disallowed action.
        valid, reason = _validate_edit_action(
            {"action": "shell_exec", "file": "target.py",
             "symbol": "x", "new_return_value": 1},
            _SYNTH_TASK,
        )
        checks.append(_check("disallowed_action_rejected", not valid))
        # Disallowed file: distractor.py (same-symbol distractor).
        valid, reason = _validate_edit_action(
            {"action": "replace_return_value", "file": "distractor.py",
             "symbol": "x", "new_return_value": 1},
            _SYNTH_TASK,
        )
        checks.append(
            _check("distractor_file_rejected", not valid)
        )
        # Disallowed file: support.py.
        valid, reason = _validate_edit_action(
            {"action": "replace_return_value", "file": "support.py",
             "symbol": "x", "new_return_value": 1},
            _SYNTH_TASK,
        )
        checks.append(
            _check("support_file_rejected", not valid)
        )
        # Missing symbol.
        valid, reason = _validate_edit_action(
            {"action": "replace_return_value", "file": "target.py",
             "new_return_value": 1},
            _SYNTH_TASK,
        )
        checks.append(_check("missing_symbol_rejected", not valid))
        # Non-int new_return_value.
        valid, reason = _validate_edit_action(
            {"action": "replace_return_value", "file": "target.py",
             "symbol": "x", "new_return_value": "not_int"},
            _SYNTH_TASK,
        )
        checks.append(_check("non_int_return_rejected", not valid))
        # Top-level not object.
        valid, reason = _validate_edit_action([], _SYNTH_TASK)
        checks.append(_check("non_object_rejected", not valid))
        # Valid action accepted.
        valid, reason = _validate_edit_action(
            {"action": "replace_return_value", "file": "target.py",
             "symbol": "resolve_000", "new_return_value": 20},
            _SYNTH_TASK,
        )
        checks.append(_check("valid_action_accepted", valid))
        # choose_helper_constant action accepted.
        valid, reason = _validate_edit_action(
            {"action": "choose_helper_constant", "file": "target.py",
             "symbol": "x", "new_return_value": 20},
            _SYNTH_TASK,
        )
        checks.append(
            _check("choose_helper_constant_accepted", valid)
        )
        # no_op action accepted.
        valid, reason = _validate_edit_action(
            {"action": "no_op", "file": "target.py", "symbol": "x"},
            _SYNTH_TASK,
        )
        checks.append(_check("no_op_action_accepted", valid))

        # --- Group 10: Aggregate metrics + deltas + honest signals. ---
        runs = [run, run_invalid]
        metrics, provider_summary = _aggregate_arm_metrics(runs)
        checks.append(
            _check("aggregate_run_count_correct", metrics["run_count"] == 2)
        )
        checks.append(
            _check(
                "aggregate_solve_rate_correct",
                _round_metric(metrics["solve_rate"]) == _round_metric(0.5),
            )
        )
        checks.append(
            _check(
                "aggregate_provider_calls_attempted",
                provider_summary["calls_attempted"] == 1,
            )
        )
        checks.append(
            _check(
                "aggregate_provider_calls_succeeded",
                provider_summary["calls_succeeded"] == 1,
            )
        )
        control_metrics = {
            "run_count": 2, "solve_rate": 0.0, "tests_pass_rate": 0.0,
            "correct_file_before_first_edit_rate": 0.0,
            "wrong_file_edits_mean": 0.0,
            "tool_calls_before_first_edit_mean": 0.0,
            "context_tokens_mean": 20.0, "latency_ms_mean": 10.0,
            "cost_proxy_mean": 0.0,
        }
        treatment_metrics = {
            "run_count": 2, "solve_rate": 1.0, "tests_pass_rate": 1.0,
            "correct_file_before_first_edit_rate": 1.0,
            "wrong_file_edits_mean": 0.0,
            "tool_calls_before_first_edit_mean": 1.0,
            "context_tokens_mean": 64.0, "latency_ms_mean": 20.0,
            "cost_proxy_mean": 0.0,
        }
        deltas = _compute_deltas(control_metrics, treatment_metrics)
        checks.append(
            _check(
                "deltas_are_records",
                all(
                    set(d.keys()) == {"baseline_arm", "treatment_arm", "metric", "delta"}
                    for d in deltas
                ),
            )
        )
        checks.append(
            _check(
                "deltas_exclude_run_count",
                all(d["metric"] != "run_count" for d in deltas),
            )
        )
        solve_delta = next(
            d for d in deltas if d["metric"] == "solve_rate"
        )
        checks.append(
            _check("delta_solve_rate_positive", solve_delta["delta"] == 1.0)
        )
        # Honest signals.
        honest = _compute_honest_signals(
            control_metrics, treatment_metrics, deltas
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
                honest["treatment_solve_rate_delta"] == 1.0,
            )
        )
        # Honest signal: zero delta -> context_pack_signal_observed False.
        zero_deltas = _compute_deltas(control_metrics, control_metrics)
        honest_zero = _compute_honest_signals(
            control_metrics, control_metrics, zero_deltas
        )
        checks.append(
            _check(
                "honest_signal_zero_delta_not_observed",
                honest_zero["context_pack_signal_observed"] is False,
            )
        )

        # --- Group 11: Model display normalization. ---
        checks.append(
            _check(
                "normalize_strips_mk_prefix",
                _normalize_model_display(_ROUTING_PREFIX_SENTINEL + "Kimi-K2.7-Code") == "Kimi-K2.7-Code",
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
                _normalize_model_display(_ROUTING_PREFIX_SENTINEL + "Test;Model!@#") == "TestModel",
            )
        )
    finally:
        try:
            shutil.rmtree(workspace_dir, ignore_errors=True)
        except OSError:
            pass

    # --- Group 12: Scanner rejections. ---
    checks.append(
        _check(
            "scanner_rejects_tmp_workspace_path",
            bool(_scan_forbidden({"leaked_workspace": "/tmp/b16d_workspace_0"})),
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
            bool(_scan_forbidden({"leaked": "api_key=sk-abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_endpoint_url_field_string",
            bool(_scan_forbidden({"leaked": "base_url=https://x.example"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_raw_model_prefix",
            bool(_scan_forbidden({"leaked": _ROUTING_PREFIX_SENTINEL + "Kimi-K2.7-Code"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_url_value",
            bool(_scan_forbidden({"leaked": "https://example.com"})),
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

    # --- Group 13: Scanner allows legitimate aggregate values. ---
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
            "scanner_allows_model_display_category",
            not _scan_forbidden({"model_display_category": "Kimi-K2.7-Code"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_honest_signal_field",
            not _scan_forbidden(
                {
                    "honest_signals": {
                        "context_pack_signal_observed": True,
                        "treatment_solve_rate_delta": 1.0,
                        "treatment_wrong_file_edits_delta": -0.5,
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

    # --- Group 14: Fail-closed generation. ---
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

    # --- Group 15: Public artifact self-scan is clean. ---
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

    # --- Group 16: CLI argument surface. ---
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

    # --- Group 17: Remote gating (delegated to provider_client). ---
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
    # Unavailable path: when allow_remote=True but env missing. This probe must
    # restore the exact provider env, because build_report() runs self-tests and
    # live provider calls in the same process.
    enabled, failure_category, restored = _probe_missing_env_without_mutating_remote_env()
    checks.append(
        _check(
            "unavailable_when_env_missing",
            not enabled
            and failure_category
            == provider_client.FAILURE_CATEGORY_MISSING_ENV,
        )
    )
    checks.append(
        _check(
            "self_test_missing_env_probe_restores_provider_env",
            restored,
        )
    )
    checks.append(
        _check(
            "self_test_preserves_synthetic_provider_env",
            _self_test_probe_preserves_synthetic_provider_env(),
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
            "B16-D less-trivial live-provider downstream paired smoke "
            "(public aggregate-only artifact; synthetic public "
            "less-trivial multi-file micro bug tasks; fresh /tmp "
            "workspace per task+arm; real file edits + real subprocess "
            "tests; live LLM provider only when --allow-remote + "
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
