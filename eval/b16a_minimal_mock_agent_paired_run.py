#!/usr/bin/env python3
"""B16-A Minimal Mock Downstream Paired Run (Public Aggregate-Only Artifact).

This module implements the **B16-A minimal deterministic/mock downstream
paired-agent empirical run**. It is the first B16-style downstream-agent
empirical run that is **not** control-plane-only: it actually executes
an edit/test loop on real tiny Python workspaces under transient
``/tmp`` directories and produces behavior metrics.

B16-A is explicitly **not** a live LLM downstream agent run. The agent
is a **deterministic mock agent** whose behavior depends on the
provided context pack. There are **no provider calls**, **no remote
calls**, and **no live LLM**. The paired design is:

* **control arm**: bare/wrong-cue pack (lacks the target file cue for a
  designed subset, or carries a wrong-cue file) -> the deterministic
  mock agent edits the wrong file or does nothing -> tests fail.
* **treatment arm**: richer/evidence pack with the target file/symbol/
  operation cue -> the deterministic mock agent edits the correct
  target file -> tests pass.

The treatment pack **causally alters** the mock agent's behavior for a
designed subset of tasks. The same budget/tool constraints apply to
both arms; only the pack differs.

B16-A **does not** claim downstream agent value, **does not** promote
any candidate, **does not** change runtime/retriever/pack/backend/
default-policy/EvidenceCore semantics, **does not** claim live agent
generalization, **does not** claim external benchmark performance, and
**does not** claim a real user task. The committed artifact is
aggregate-only: no task IDs, workspace paths, file paths, source
snippets, patches/diffs, test output, raw event logs, per-run rows,
private IDs, or provider/model info beyond the deterministic mock
identity.

Claim boundary (binding):

* Claim level: ``deterministic_mock_downstream_paired_smoke_only``.
* Status: ``mock_downstream_paired_smoke_pass`` on success; mode
  ``public_aggregate_synthetic_micro_tasks``; phase ``B16-A``.
* This is **eval/diagnostic only**. It is NOT a runtime change, NOT a
  retriever/pack/backend/default-policy change, NOT an EvidenceCore
  semantic change, NOT a live agent value claim, NOT a promotion, NOT
  an external benchmark performance claim, and NOT a real user task
  claim.

Run::

    python3 -m py_compile eval/b16a_minimal_mock_agent_paired_run.py
    python3 eval/b16a_minimal_mock_agent_paired_run.py --self-test
    python3 eval/b16a_minimal_mock_agent_paired_run.py \\
        --out artifacts/b16a_minimal_mock_agent_paired_run/\\
b16a_minimal_mock_agent_paired_run_report.json

The default mode generates deterministic synthetic public micro bug
tasks, creates a fresh ``/tmp`` workspace per task+arm, runs the
deterministic mock agent (real file edits + real subprocess tests),
computes aggregate behavior metrics, and writes ONLY the public
aggregate artifact. Raw event logs/patches/test output stay under
``/tmp`` and are never committed or uploaded.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "b16a_minimal_mock_agent_paired_run.v1"
GENERATED_BY = "eval/b16a_minimal_mock_agent_paired_run.py"
CLAIM_LEVEL = "deterministic_mock_downstream_paired_smoke_only"
TARGET_STATUS = "mock_downstream_paired_smoke_pass"
STATUS_BLOCKED = "mock_downstream_paired_smoke_blocked"
STATUS_FAIL_LEAK = "fail_forbidden_leak"
MODE = "public_aggregate_synthetic_micro_tasks"
PHASE = "B16-A"

DEFAULT_OUT = Path(
    "artifacts/b16a_minimal_mock_agent_paired_run/"
    "b16a_minimal_mock_agent_paired_run_report.json"
)
DEFAULT_TASK_COUNT = 24
MIN_TASK_COUNT = 4
MAX_TASK_COUNT = 32

ARMS: tuple[str, ...] = ("control", "treatment")

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

# Delta metric names (treatment minus control). ``run_count`` is excluded
# because it is identical across arms by paired design.
DELTA_METRIC_NAMES: tuple[str, ...] = tuple(
    name for name in METRIC_NAMES if name != "run_count"
)

# ---------------------------------------------------------------------------
# Safe booleans true (deterministic mock run only). Exactly these are true
# in the committed public artifact.
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "downstream_agent_runs_performed": True,
    "deterministic_mock_agent": True,
    "synthetic_micro_tasks_used": True,
    "paired_arms_evaluated": True,
    "real_file_edits_performed": True,
    "real_test_commands_executed": True,
    "agent_behavior_metrics_evaluated": True,
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
}

# ---------------------------------------------------------------------------
# No-claim / no-runtime-change flags (all MUST be false in the committed
# public artifact). B16-A runs NO live LLM, makes NO provider/remote calls,
# proves NO downstream agent value, promotes NO candidate, changes NO
# runtime/retriever/pack/backend/default-policy/EvidenceCore semantics,
# claims NO external benchmark performance, NO live agent generalization,
# and NO real user task.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "live_llm_agent": False,
    "provider_calls_made": False,
    "remote_calls_made": False,
    "downstream_agent_value_proven": False,
    "promotion_ready": False,
    "default_should_change": False,
    "runtime_behavior_changed": False,
    "retriever_changed": False,
    "pack_builder_changed": False,
    "backend_changed": False,
    "default_policy_changed": False,
    "evidencecore_semantics_changed": False,
    "external_benchmark_performance_claimed": False,
    "live_agent_generalization_claimed": False,
    "real_user_task_claimed": False,
}

# ---------------------------------------------------------------------------
# Public artifact scanner (strict, fail-closed). No contract containers
# with field-name tokens; no over-broad container exemption. Sensitive
# field-name tokens are NEVER emitted as keys anywhere and NEVER emitted
# as values outside the explicit safe-value key allowlist. The scanner
# runs ONLY against the final public aggregate artifact (NOT against
# in-memory per-run event logs, which contain paths/patches/test output).
# ---------------------------------------------------------------------------

# Sensitive KEY names that must NEVER appear as dict keys anywhere in a
# public artifact JSON. Superset of workspace/path/file/span/content/
# hash/identifier/patch/test/event-log/secret/raw-row keys.
FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset(
    {
        # location / path / workspace
        "path", "span", "line_range", "start_line", "end_line",
        "start_byte", "end_byte", "line_ranges", "spans",
        "file", "files", "filename", "filepath",
        "workspace_path", "workspace", "workspace_dir", "tmp_dir",
        "tmp_path", "target_file", "wrong_file", "wrong_cue_file",
        "target_module", "distractor_module", "test_module",
        "source_path", "module_path", "module",
        # content / hash
        "content", "content_sha", "content_hash", "hash", "digest",
        "sha256", "md5", "sha1",
        "snippet", "snippets", "excerpt", "excerpts",
        "code", "source_code", "code_snippet", "body", "text", "source",
        # identifiers
        "task_id", "task_index", "repo_id", "repo", "instance_id",
        "row_id", "record_id", "id", "name", "run_id",
        # packet-specific identifiers
        "packet_ref", "packet_id", "private_record_ref",
        "candidate_ref", "candidate_id", "candidate",
        # labels / qrels / annotations
        "label", "labels", "qrels", "gold", "gold_label", "gold_labels",
        "hard_negative", "hard_negatives",
        # prompts / responses / model outputs
        "query", "query_text", "prompt", "response", "model_response",
        "model_output", "provider_payload", "raw_payload", "api_response",
        "response_body",
        # rows / records / packets
        "raw_rows", "rows", "records", "runs", "per_run", "raw",
        "raw_data", "predictions", "candidates",
        # patches / tests / output
        "patch", "diff", "test_patch", "tests", "test_output",
        "test_log", "test_stdout", "test_stderr", "stdout", "stderr",
        "returncode", "exit_code",
        # event logs / traces / errors
        "event_log", "events", "log", "trace", "raw_event", "raw_log",
        "stack_trace", "traceback", "error_message", "error",
        # secrets / provider
        "api_key", "api_token", "api_secret", "base_url", "provider_key",
        "authorization", "secret", "token", "credential", "password",
        "provider_url", "provider_base_url",
        # CI / agreement numerics
        "agreement_metric", "agreement_value", "agreement_score",
        "kappa", "fleiss_kappa", "cohen_kappa", "agreement",
        "confidence_interval", "ci_value", "ci_lower", "ci_upper",
        "ci_low", "ci_high",
    }
)

# Known-safe provenance value paths (allowlisted for path-like / hex /
# path-like value checks only). The forbidden dict-key check is NOT
# relaxed by this. These keys MAY hold path-like values (e.g. the
# generator script path) without triggering the path-like value leak.
SAFE_VALUE_KEY_NAMES: frozenset[str] = frozenset(
    {
        "schema_version",
        "generated_by",
        "generated_at",
        "claim_level",
        "status",
        "mode",
        "phase",
    }
)

# Value patterns that indicate leaked workspace / file / patch / test /
# event-log / secret / identifier data. B16-A rejects ALL URLs (no URL
# allowlist) per the fail-closed rule.
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
# B16-A-specific leak patterns: /tmp workspace paths, task identifiers,
# patch/diff markers, stack traces.
_RE_TMP_PATH_VALUE = re.compile(r"/tmp/")
_RE_TASK_ID_VALUE = re.compile(r"\btask[_\-\s]*\d+\b", re.IGNORECASE)
_RE_PATCH_MARKER = re.compile(r"^(---|\+\+\+|@@\s)", re.MULTILINE)
_RE_STACK_TRACE = re.compile(
    r"Traceback\s*\(most\s+recent\s+call\s+last\)", re.IGNORECASE
)

# The sentinel used by self-tests; the scanner must never let it through
# in a committed/public output. Used as a value-leak canary.
_SECRET_SENTINEL = "SECRET_VALIDATOR_SENTINEL"


def _path_last_key(path: str) -> str:
    """Extract the last key segment from a dotted JSON path."""
    last = path.rsplit(".", 1)[-1]
    return last.split("[")[0]


def _is_safe_value_path(path: str) -> bool:
    """Check if a JSON path ends with a known-safe value key."""
    return _path_last_key(path) in SAFE_VALUE_KEY_NAMES


def _scan_forbidden(obj: Any, path: str = "$") -> list[dict[str, Any]]:
    """Strict recursive scanner for public artifact JSON.

    Returns a list of violation dicts with ``category`` and ``path``
    (JSON path), NEVER the leaked value itself. Fail-closed: any
    violation means the output would leak.
    """
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
            # Sensitive field name as a VALUE is a leak.
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
    """Run the public forbidden scanner and return a sanitized summary."""
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
    """Fail-closed guard: raise SystemExit if any forbidden content leaks."""
    scan = _forbidden_scan_summary(obj)
    if scan["status"] != "pass":
        raise SystemExit(
            "forbidden content leak; refusing to write artifact"
        )


def _refuse_on_self_test_failure(report: dict[str, Any]) -> None:
    """Refuse successful artifact generation if self-test failed."""
    if report.get("self_test_passed") is not True:
        raise SystemExit(
            "self-test failed; refusing to write artifact"
        )


def _has_dict_key_anywhere(obj: Any, key: str) -> bool:
    """True iff any dict within ``obj`` has ``key`` as a dict key."""
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
# Synthetic public micro bug task generation (deterministic, in-code).
# ---------------------------------------------------------------------------


def _generate_synthetic_tasks(count: int) -> list[dict[str, Any]]:
    """Generate deterministic synthetic public micro bug task specs.

    Each task spec describes a tiny Python module with a one-line bug
    (returns the wrong value) and a stdlib test that asserts the correct
    value. The fix is a deterministic one-line return-value replacement.

    Task specs are NEVER emitted to the public artifact; they live only
    in transient memory and under ``/tmp`` workspaces.
    """
    tasks: list[dict[str, Any]] = []
    for i in range(count):
        correct_value = 100 + i
        buggy_value = -(100 + i)
        task: dict[str, Any] = {
            "index": i,
            "symbol": f"compute_{i:03d}",
            "target_module": "target.py",
            "distractor_module": "distractor.py",
            "test_module": "test_target.py",
            "correct_value": correct_value,
            "buggy_value": buggy_value,
            "fix_kind": "replace_return_value",
        }
        tasks.append(task)
    return tasks


# ---------------------------------------------------------------------------
# Workspace builder (fresh /tmp per task+arm; real tiny Python files).
# ---------------------------------------------------------------------------


def _build_workspace(workspace_dir: Path, task: dict[str, Any]) -> None:
    """Create a fresh workspace with a tiny Python module + stdlib test.

    The workspace contains:
    * ``target.py``: a tiny module with a one-line bug (returns wrong value).
    * ``distractor.py``: a wrong-file distractor with a similar-looking
      symbol (the mock agent may edit this if given a wrong cue).
    * ``test_target.py``: a stdlib test that imports ``target`` and
      asserts the correct value; exits 0 on success, 1 on failure.

    All files are real Python files written to disk under ``/tmp``.
    """
    workspace_dir.mkdir(parents=True, exist_ok=True)

    target_path = workspace_dir / task["target_module"]
    distractor_path = workspace_dir / task["distractor_module"]
    test_path = workspace_dir / task["test_module"]

    # Target module: has a bug (returns wrong value).
    target_path.write_text(
        f"def {task['symbol']}():\n"
        f"    return {task['buggy_value']}\n",
        encoding="utf-8",
    )

    # Distractor module: looks similar but is the wrong file.
    distractor_path.write_text(
        f"def {task['symbol']}_aux():\n"
        f"    return {task['buggy_value']}\n",
        encoding="utf-8",
    )

    # Test module: imports target, asserts the correct value.
    # Uses only stdlib; runs as a script that exits 0 on success.
    test_path.write_text(
        "import sys\n"
        f"sys.path.insert(0, r'{workspace_dir}')\n"
        f"from target import {task['symbol']}\n"
        "def main():\n"
        f"    assert {task['symbol']}() == {task['correct_value']}, "
        "'bug not fixed'\n"
        "    return 0\n"
        "if __name__ == '__main__':\n"
        "    sys.exit(main())\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Pack builder (control vs treatment; treatment causally adds cues).
# ---------------------------------------------------------------------------


def _build_pack(arm: str, task: dict[str, Any]) -> dict[str, Any]:
    """Build the context pack for an arm.

    * **control**: bare description. For a designed subset (even-index
      tasks) the control pack carries a **wrong-cue file** pointing at
      the distractor; for the rest it carries **no file cue** at all.
      The deterministic mock agent therefore edits the wrong file (or
      does nothing) and tests fail.
    * **treatment**: richer/evidence pack with the **target file**,
      **target symbol**, and **operation hint** cues. The deterministic
      mock agent edits the correct target file and tests pass.

    Packs are NEVER emitted to the public artifact; only their
    deterministic ``context_tokens`` count is aggregated.
    """
    if arm == "control":
        if task["index"] % 2 == 0:
            # Designed subset: wrong-cue file pointing at the distractor.
            return {
                "wrong_cue_file": task["distractor_module"],
                "context_tokens": 12,
            }
        # No file cue: bare description only.
        return {
            "context_tokens": 8,
        }
    # treatment: richer/evidence pack with target file/symbol/operation cue.
    return {
        "target_file": task["target_module"],
        "target_symbol": task["symbol"],
        "operation_hint": "replace_return_value",
        "context_tokens": 24,
    }


# ---------------------------------------------------------------------------
# Deterministic mock agent (pack-dependent; real file edits).
# ---------------------------------------------------------------------------


def _run_mock_agent(
    workspace_dir: Path, task: dict[str, Any], pack: dict[str, Any]
) -> dict[str, Any]:
    """Run the deterministic mock agent for one task+arm.

    The agent is fully deterministic and pack-dependent:
    * if the pack has a ``target_file`` cue -> edit that file with the
      correct fix (tests will pass);
    * elif the pack has a ``wrong_cue_file`` cue -> edit the wrong file
      (tests will still fail; wrong_file_edits=1);
    * else -> do nothing (tests fail; no edit).

    After the edit (or no-op), the agent runs the real subprocess test
    command and records the pass/fail result.

    The per-run **event log** (with file paths, edit content, test
    stdout/stderr) is kept in-memory only and NEVER written to the
    public artifact. Only aggregate metrics are returned.
    """
    # Transient event log; NEVER committed.
    event_log: list[dict[str, Any]] = []

    target_file = pack.get("target_file")
    wrong_cue_file = pack.get("wrong_cue_file")

    wrong_file_edits = 0
    tool_calls_before_first_edit = 0
    correct_file_before_first_edit = False
    edit_applied = False

    # Decide which file to edit based on pack cues (pack-dependent).
    if target_file:
        # Treatment arm: edit the correct target file.
        edit_path = workspace_dir / target_file
        correct_file_before_first_edit = True
        tool_calls_before_first_edit = 1
        # Apply the deterministic correct fix.
        new_content = (
            f"def {task['symbol']}():\n"
            f"    return {task['correct_value']}\n"
        )
        edit_path.write_text(new_content, encoding="utf-8")
        edit_applied = True
        event_log.append(
            {"event": "edit", "kind": "correct_file", "file": str(edit_path)}
        )
    elif wrong_cue_file:
        # Control arm with wrong cue: edit the wrong file.
        edit_path = workspace_dir / wrong_cue_file
        wrong_file_edits += 1
        tool_calls_before_first_edit = 1
        # Apply a fix attempt that does not make the test pass.
        new_content = (
            f"def {task['symbol']}_aux():\n"
            f"    return {task['correct_value']}\n"
        )
        edit_path.write_text(new_content, encoding="utf-8")
        edit_applied = True
        event_log.append(
            {"event": "edit", "kind": "wrong_file", "file": str(edit_path)}
        )
    else:
        # Control arm with no cue: do nothing.
        event_log.append({"event": "no_edit", "kind": "no_cue"})

    # Run the real subprocess test command.
    test_cmd = [sys.executable, str(workspace_dir / task["test_module"])]
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            test_cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        tests_pass = proc.returncode == 0
        test_stdout = proc.stdout
        test_stderr = proc.stderr
    except (subprocess.TimeoutExpired, OSError):
        tests_pass = False
        test_stdout = ""
        test_stderr = ""
    latency_ms = max(1, int((time.perf_counter() - start) * 1000))

    event_log.append(
        {
            "event": "test",
            "passed": tests_pass,
            "stdout": test_stdout,
            "stderr": test_stderr,
        }
    )

    # Solve = tests pass AND correct file was edited before/at first edit.
    solve = tests_pass and correct_file_before_first_edit

    # Per-run metrics (aggregate only; event_log stays transient).
    return {
        "solve": solve,
        "tests_pass": tests_pass,
        "correct_file_before_first_edit": correct_file_before_first_edit,
        "wrong_file_edits": wrong_file_edits,
        "tool_calls_before_first_edit": tool_calls_before_first_edit,
        "context_tokens": pack.get("context_tokens", 0),
        "latency_ms": latency_ms,
        "cost_proxy": 0,  # deterministic mock: no provider calls, no cost
        # event_log is kept in-memory only; never returned to the report.
    }


# ---------------------------------------------------------------------------
# Aggregate metric computation
# ---------------------------------------------------------------------------


def _rate(numer: int, denom: int) -> float:
    """Safe division: numer / denom (0.0 if denom == 0)."""
    if denom <= 0:
        return 0.0
    return numer / denom


def _mean(values: list[float]) -> float:
    """Arithmetic mean (0.0 if empty)."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _round_metric(value: float) -> float:
    """Round a metric to 6 decimal places for stable serialization."""
    return round(float(value), 6)


def _aggregate_arm_metrics(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute per-arm aggregate metrics from per-run results.

    Emits ONLY aggregate counts/rates/means. Never emits per-run rows,
    paths, patches, test output, event logs, task IDs, or file paths.
    """
    n = len(runs)
    return {
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


def _compute_deltas(
    control: dict[str, Any], treatment: dict[str, Any]
) -> dict[str, float]:
    """Compute treatment-minus-control deltas for rate/mean metrics."""
    return {
        name: _round_metric(treatment[name] - control[name])
        for name in DELTA_METRIC_NAMES
    }


# ---------------------------------------------------------------------------
# Public artifact builder
# ---------------------------------------------------------------------------


def _build_public_report(
    checks: list[dict[str, Any]],
    all_passed: bool,
    arm_metrics: dict[str, dict[str, Any]] | None = None,
    deltas: dict[str, float] | None = None,
    input_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the public aggregate-only report (fail-closed scan).

    The default committed artifact. No per-run rows, no paths, no
    patches, no test output, no event logs, no task IDs, no file paths,
    no source snippets, no content hashes, no secrets.
    """
    arm_metrics = arm_metrics or {arm: _aggregate_arm_metrics([]) for arm in ARMS}
    deltas = deltas or _compute_deltas(arm_metrics["control"], arm_metrics["treatment"])
    input_summary = input_summary or {
        "synthetic_task_count": 0,
        "run_count_per_arm": 0,
        "total_runs": 0,
        "arms": list(ARMS),
        "paired_design": True,
        "workspace_isolation": "fresh_tmp_per_task_arm",
        "transient_workspace_outputs_only": True,
        "designed_causal_subset": True,
    }

    # Smoke passes iff self-test passed AND at least one run per arm
    # AND treatment solve_rate > control solve_rate (causal pack effect).
    smoke_passes = (
        all_passed
        and arm_metrics["control"]["run_count"] >= 1
        and arm_metrics["treatment"]["run_count"] >= 1
        and arm_metrics["treatment"]["solve_rate"]
        > arm_metrics["control"]["solve_rate"]
    )
    status = TARGET_STATUS if smoke_passes else STATUS_BLOCKED

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "input_summary": input_summary,
        "arm_metrics": arm_metrics,
        "deltas_treatment_minus_control": deltas,
        # Safe booleans true (deterministic mock run only).
        **SAFE_TRUE_FLAGS,
        # No-claim / no-runtime-change flags (all false).
        **DEFAULT_FALSE_FLAGS,
        # Self-test summary / checks / passed.
        "self_test_summary": _self_test_category_summary(checks),
        "self_test_checks": checks,
        "self_test_passed": all_passed,
    }

    # Fail-closed forbidden scan before returning.
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_LEAK
    return report


def build_report(task_count: int) -> dict[str, Any]:
    """Assemble the public aggregate-only report from a real paired run.

    Runs the deterministic self-test checks, generates deterministic
    synthetic public micro bug tasks, creates a fresh ``/tmp`` workspace
    per task+arm, runs the deterministic mock agent (real file edits +
    real subprocess tests), computes aggregate behavior metrics, and
    assembles the full public report (which re-scans itself).
    """
    checks, all_passed = run_self_test_checks()

    tasks = _generate_synthetic_tasks(task_count)

    arm_runs: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}

    for task in tasks:
        for arm in ARMS:
            pack = _build_pack(arm, task)
            # Fresh /tmp workspace per task+arm.
            workspace_dir = Path(
                tempfile.mkdtemp(prefix="b16a_workspace_")
            )
            try:
                _build_workspace(workspace_dir, task)
                run = _run_mock_agent(workspace_dir, task, pack)
            finally:
                # Best-effort cleanup of the transient workspace.
                # Never raise on cleanup failure.
                try:
                    shutil.rmtree(workspace_dir, ignore_errors=True)
                except OSError:
                    pass
            arm_runs[arm].append(run)

    arm_metrics = {
        arm: _aggregate_arm_metrics(arm_runs[arm]) for arm in ARMS
    }
    deltas = _compute_deltas(
        arm_metrics["control"], arm_metrics["treatment"]
    )

    input_summary: dict[str, Any] = {
        "synthetic_task_count": task_count,
        "run_count_per_arm": task_count,
        "total_runs": task_count * len(ARMS),
        "arms": list(ARMS),
        "paired_design": True,
        "workspace_isolation": "fresh_tmp_per_task_arm",
        "transient_workspace_outputs_only": True,
        "designed_causal_subset": True,
    }

    return _build_public_report(
        checks,
        all_passed,
        arm_metrics=arm_metrics,
        deltas=deltas,
        input_summary=input_summary,
    )


# ---------------------------------------------------------------------------
# Self-test checks
# ---------------------------------------------------------------------------

# Synthetic test workspace for self-test (in-memory; cleaned up after).
_SYNTH_TASK = {
    "index": 0,
    "symbol": "compute_000",
    "target_module": "target.py",
    "distractor_module": "distractor.py",
    "test_module": "test_target.py",
    "correct_value": 100,
    "buggy_value": -100,
    "fix_kind": "replace_return_value",
}


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all B16-A self-test groups.

    Returns (checks, all_passed). Uses a small real ``/tmp`` workspace
    for the edit/test loop tests; no external provider required.
    """
    checks: list[dict[str, Any]] = []

    # --- Group 1: Artifact identity fields. ---
    skeleton = _build_public_report([], False)
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
        _check(
            "mode_correct",
            skeleton["mode"] == MODE,
        )
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
    checks.append(
        _check(
            "status_blocked_when_self_test_not_passed",
            skeleton["status"] == STATUS_BLOCKED,
        )
    )

    # --- Group 2: Safe true flags. ---
    for flag in SAFE_TRUE_FLAGS:
        checks.append(
            _check(
                f"safe_true_{flag}",
                skeleton.get(flag) is True,
            )
        )

    # --- Group 3: No-claim / no-runtime-change false flags. ---
    for flag in DEFAULT_FALSE_FLAGS:
        checks.append(
            _check(
                f"default_false_{flag}",
                skeleton.get(flag) is False,
            )
        )

    # --- Group 4: Synthetic task generation (deterministic). ---
    tasks_4 = _generate_synthetic_tasks(4)
    checks.append(
        _check(
            "synthetic_task_count_correct",
            len(tasks_4) == 4,
        )
    )
    checks.append(
        _check(
            "synthetic_task_symbols_deterministic",
            tasks_4[0]["symbol"] == "compute_000"
            and tasks_4[3]["symbol"] == "compute_003",
        )
    )
    checks.append(
        _check(
            "synthetic_task_correct_value_deterministic",
            tasks_4[0]["correct_value"] == 100
            and tasks_4[3]["correct_value"] == 103,
        )
    )
    checks.append(
        _check(
            "synthetic_task_buggy_value_deterministic",
            tasks_4[0]["buggy_value"] == -100
            and tasks_4[3]["buggy_value"] == -103,
        )
    )

    # --- Group 5: Pack builder (arm difference + causal cues). ---
    control_pack_even = _build_pack("control", tasks_4[0])
    control_pack_odd = _build_pack("control", tasks_4[1])
    treatment_pack = _build_pack("treatment", tasks_4[0])
    checks.append(
        _check(
            "control_pack_even_has_wrong_cue_file",
            "wrong_cue_file" in control_pack_even,
        )
    )
    checks.append(
        _check(
            "control_pack_odd_has_no_file_cue",
            "target_file" not in control_pack_odd
            and "wrong_cue_file" not in control_pack_odd,
        )
    )
    checks.append(
        _check(
            "treatment_pack_has_target_file_cue",
            "target_file" in treatment_pack,
        )
    )
    checks.append(
        _check(
            "treatment_pack_has_target_symbol_cue",
            "target_symbol" in treatment_pack,
        )
    )
    checks.append(
        _check(
            "treatment_pack_has_operation_hint_cue",
            "operation_hint" in treatment_pack,
        )
    )
    checks.append(
        _check(
            "treatment_pack_richer_than_control",
            treatment_pack["context_tokens"]
            > control_pack_even["context_tokens"],
        )
    )
    checks.append(
        _check(
            "control_pack_lacks_target_file_cue",
            "target_file" not in control_pack_even
            and "target_file" not in control_pack_odd,
        )
    )

    # --- Group 6: Real workspace creation + real file edits + real tests.
    # Use a real /tmp workspace for the edit/test loop.
    workspace_dir = Path(tempfile.mkdtemp(prefix="b16a_selftest_"))
    try:
        _build_workspace(workspace_dir, _SYNTH_TASK)
        target_path = workspace_dir / _SYNTH_TASK["target_module"]
        distractor_path = workspace_dir / _SYNTH_TASK["distractor_module"]
        test_path = workspace_dir / _SYNTH_TASK["test_module"]

        checks.append(
            _check(
                "workspace_creates_target_file",
                target_path.is_file(),
            )
        )
        checks.append(
            _check(
                "workspace_creates_distractor_file",
                distractor_path.is_file(),
            )
        )
        checks.append(
            _check(
                "workspace_creates_test_file",
                test_path.is_file(),
            )
        )

        # Real test subprocess: should FAIL before the fix (bug present).
        proc_before = subprocess.run(
            [sys.executable, str(test_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        checks.append(
            _check(
                "test_fails_before_fix",
                proc_before.returncode != 0,
            )
        )

        # --- Group 7: Mock agent behavior (pack-dependent). ---
        # Treatment pack: agent edits the correct target file -> tests pass.
        treatment_run = _run_mock_agent(
            workspace_dir, _SYNTH_TASK, treatment_pack
        )
        checks.append(
            _check(
                "treatment_agent_edits_correct_file",
                treatment_run["correct_file_before_first_edit"] is True,
            )
        )
        checks.append(
            _check(
                "treatment_agent_no_wrong_file_edits",
                treatment_run["wrong_file_edits"] == 0,
            )
        )
        checks.append(
            _check(
                "treatment_agent_tests_pass",
                treatment_run["tests_pass"] is True,
            )
        )
        checks.append(
            _check(
                "treatment_agent_solve",
                treatment_run["solve"] is True,
            )
        )
        checks.append(
            _check(
                "treatment_agent_real_file_edit",
                "return 100" in target_path.read_text(encoding="utf-8"),
            )
        )

        # Control pack with wrong cue: agent edits wrong file -> tests fail.
        # Rebuild workspace first so the bug is present again.
        _build_workspace(workspace_dir, _SYNTH_TASK)
        control_run_wrong = _run_mock_agent(
            workspace_dir, _SYNTH_TASK, control_pack_even
        )
        checks.append(
            _check(
                "control_wrong_cue_agent_edits_wrong_file",
                control_run_wrong["wrong_file_edits"] == 1,
            )
        )
        checks.append(
            _check(
                "control_wrong_cue_agent_not_correct_file",
                control_run_wrong["correct_file_before_first_edit"] is False,
            )
        )
        checks.append(
            _check(
                "control_wrong_cue_agent_tests_fail",
                control_run_wrong["tests_pass"] is False,
            )
        )
        checks.append(
            _check(
                "control_wrong_cue_agent_no_solve",
                control_run_wrong["solve"] is False,
            )
        )
        # Distractor file was actually edited (real file edit).
        checks.append(
            _check(
                "control_wrong_cue_agent_edited_distractor_file",
                "return 100"
                in distractor_path.read_text(encoding="utf-8"),
            )
        )

        # Control pack with no cue: agent does nothing -> tests fail.
        _build_workspace(workspace_dir, _SYNTH_TASK)
        control_run_none = _run_mock_agent(
            workspace_dir, _SYNTH_TASK, control_pack_odd
        )
        checks.append(
            _check(
                "control_no_cue_agent_no_edit",
                control_run_none["wrong_file_edits"] == 0
                and control_run_none["correct_file_before_first_edit"] is False,
            )
        )
        checks.append(
            _check(
                "control_no_cue_agent_tests_fail",
                control_run_none["tests_pass"] is False,
            )
        )
        checks.append(
            _check(
                "control_no_cue_agent_no_solve",
                control_run_none["solve"] is False,
            )
        )

        # --- Group 8: Mock action dependence on pack cues. ---
        checks.append(
            _check(
                "mock_action_depends_on_pack_target_file",
                treatment_run["correct_file_before_first_edit"]
                and not control_run_wrong["correct_file_before_first_edit"],
            )
        )
        checks.append(
            _check(
                "mock_action_depends_on_pack_wrong_cue",
                control_run_wrong["wrong_file_edits"] == 1
                and control_run_none["wrong_file_edits"] == 0,
            )
        )
        checks.append(
            _check(
                "treatment_solve_rate_higher_than_control",
                treatment_run["solve"] and not control_run_wrong["solve"],
            )
        )

        # --- Group 9: Aggregate metrics math. ---
        runs = [treatment_run, control_run_wrong, control_run_none]
        agg = _aggregate_arm_metrics(runs)
        checks.append(
            _check(
                "aggregate_run_count_correct",
                agg["run_count"] == 3,
            )
        )
        checks.append(
            _check(
                "aggregate_solve_rate_correct",
                _round_metric(agg["solve_rate"]) == _round_metric(1 / 3),
            )
        )
        checks.append(
            _check(
                "aggregate_tests_pass_rate_correct",
                _round_metric(agg["tests_pass_rate"]) == _round_metric(1 / 3),
            )
        )
        checks.append(
            _check(
                "aggregate_correct_file_rate_correct",
                _round_metric(agg["correct_file_before_first_edit_rate"])
                == _round_metric(1 / 3),
            )
        )
        checks.append(
            _check(
                "aggregate_wrong_file_edits_mean_correct",
                _round_metric(agg["wrong_file_edits_mean"])
                == _round_metric(1 / 3),
            )
        )
        checks.append(
            _check(
                "aggregate_tool_calls_mean_correct",
                _round_metric(agg["tool_calls_before_first_edit_mean"])
                == _round_metric(2 / 3),
            )
        )
        checks.append(
            _check(
                "aggregate_cost_proxy_mean_zero",
                agg["cost_proxy_mean"] == 0.0,
            )
        )

        # --- Group 10: Deltas computation. ---
        control_agg = _aggregate_arm_metrics(
            [control_run_wrong, control_run_none]
        )
        treatment_agg = _aggregate_arm_metrics([treatment_run])
        deltas = _compute_deltas(control_agg, treatment_agg)
        checks.append(
            _check(
                "delta_solve_rate_positive",
                deltas["solve_rate"] > 0,
            )
        )
        checks.append(
            _check(
                "delta_wrong_file_edits_negative",
                deltas["wrong_file_edits_mean"] < 0,
            )
        )
        checks.append(
            _check(
                "delta_run_count_not_present",
                "run_count" not in deltas,
            )
        )
    finally:
        try:
            shutil.rmtree(workspace_dir, ignore_errors=True)
        except OSError:
            pass

    # --- Group 11: Scanner rejections (fail-closed). ---
    # Workspace path value.
    checks.append(
        _check(
            "scanner_rejects_tmp_workspace_path",
            bool(
                _scan_forbidden(
                    {"leaked_workspace": "/tmp/b16a_workspace_0"}
                )
            ),
        )
    )
    # File path value.
    checks.append(
        _check(
            "scanner_rejects_file_path_value",
            bool(_scan_forbidden({"leaked_file": "target.py"})),
        )
    )
    # Source snippet value (multiline).
    checks.append(
        _check(
            "scanner_rejects_source_snippet",
            bool(
                _scan_forbidden(
                    {"leaked_snippet": "def compute():\n    return 0\n"}
                )
            ),
        )
    )
    # Patch/diff marker value.
    checks.append(
        _check(
            "scanner_rejects_patch_marker",
            bool(
                _scan_forbidden(
                    {"leaked_patch": "--- a/target.py\n+++ b/target.py\n"}
                )
            ),
        )
    )
    # Test output value (multiline stdout).
    checks.append(
        _check(
            "scanner_rejects_test_output",
            bool(
                _scan_forbidden(
                    {"leaked_stdout": "test passed\nok\n"}
                )
            ),
        )
    )
    # task_id key.
    checks.append(
        _check(
            "scanner_rejects_task_id_key",
            bool(_scan_forbidden({"task_id": "abc"})),
        )
    )
    # task_id value.
    checks.append(
        _check(
            "scanner_rejects_task_id_value",
            bool(_scan_forbidden({"leaked": "task_001"})),
        )
    )
    # Raw event log value (JSON fragment).
    checks.append(
        _check(
            "scanner_rejects_raw_event_log",
            bool(
                _scan_forbidden(
                    {"leaked_log": '{"event": "edit", "file": "target.py"}'}
                )
            ),
        )
    )
    # Stack trace value.
    checks.append(
        _check(
            "scanner_rejects_stack_trace",
            bool(
                _scan_forbidden(
                    {
                        "leaked_trace": (
                            "Traceback (most recent call last):\n"
                            '  File "test.py", line 1\n'
                        )
                    }
                )
            ),
        )
    )
    # content_sha key.
    checks.append(
        _check(
            "scanner_rejects_content_sha_key",
            bool(_scan_forbidden({"content_sha": "abc"})),
        )
    )
    # Hex digest value (32+ hex chars).
    checks.append(
        _check(
            "scanner_rejects_hex_digest_value",
            bool(
                _scan_forbidden(
                    {"leaked_hash": "a" * 32}
                )
            ),
        )
    )
    # Provider auth/endpoint credential value.
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
    # Sentinel canary value.
    checks.append(
        _check(
            "scanner_rejects_sentinel_canary",
            bool(
                _scan_forbidden({"leaked": _SECRET_SENTINEL})
            ),
        )
    )
    # URL value.
    checks.append(
        _check(
            "scanner_rejects_url_value",
            bool(_scan_forbidden({"leaked": "https://example.com"})),
        )
    )
    # Forbidden field name as value.
    checks.append(
        _check(
            "scanner_rejects_forbidden_field_name_as_value",
            bool(_scan_forbidden({"leaked": "content_sha"})),
        )
    )
    # Line range value.
    checks.append(
        _check(
            "scanner_rejects_line_range_value",
            bool(_scan_forbidden({"leaked": "12-34"})),
        )
    )

    # --- Group 12: Scanner allows legitimate aggregate values. ---
    checks.append(
        _check(
            "scanner_allows_arm_name_control",
            not _scan_forbidden({"arms": ["control"]}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_arm_name_treatment",
            not _scan_forbidden({"arms": ["treatment"]}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_metric_values",
            not _scan_forbidden(
                {
                    "solve_rate": 0.5,
                    "tests_pass_rate": 0.5,
                    "wrong_file_edits_mean": 1.0,
                    "latency_ms_mean": 5.0,
                    "cost_proxy_mean": 0.0,
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_workspace_isolation_token",
            not _scan_forbidden(
                {"workspace_isolation": "fresh_tmp_per_task_arm"}
            ),
        )
    )

    # --- Group 13: Fail-closed generation. ---
    # Clean public report does not raise.
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
    # Leak in a public report raises.
    leaked_report = dict(skeleton)
    leaked_report["leaked_path"] = "src/openlocus/lib.rs"
    try:
        _enforce_no_forbidden(leaked_report)
        leak_raises = False
    except SystemExit:
        leak_raises = True
    checks.append(
        _check(
            "fail_closed_generation_raises_on_leak",
            leak_raises,
        )
    )
    # Refuse on self-test failure: raises when failed.
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
    # Refuse on self-test failure: does not raise when passed.
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
    # Failed self-test does not carry success status.
    checks.append(
        _check(
            "failed_self_test_does_not_carry_success_status",
            skeleton["status"] != TARGET_STATUS,
        )
    )

    # --- Group 14: Public artifact self-scan is clean. ---
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
                    "task_id",
                    "workspace_path",
                    "file_path",
                    "target_file",
                    "wrong_cue_file",
                    "path",
                    "file",
                    "snippet",
                    "code",
                    "patch",
                    "diff",
                    "test_output",
                    "event_log",
                    "stack_trace",
                    "content_sha",
                    "content_hash",
                    "api_key",
                    "base_url",
                    "provider_key",
                    "secret",
                    "token",
                    "stdout",
                    "stderr",
                    "rows",
                    "per_run",
                    "predictions",
                )
            ),
        )
    )

    # --- Group 15: CLI argument surface. ---
    cli_opts = _cli_argument_option_strings()
    checks.append(
        _check(
            "cli_has_self_test_argument",
            "--self-test" in cli_opts,
        )
    )
    checks.append(
        _check("cli_has_out_argument", "--out" in cli_opts)
    )
    checks.append(
        _check(
            "cli_has_task_count_argument",
            "--task-count" in cli_opts,
        )
    )
    checks.append(
        _check(
            "cli_only_expected_arguments",
            (cli_opts - {"-h", "--help"})
            == {
                "--self-test",
                "--out",
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

    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class SafeArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that never echoes unknown/private-looking args.

    A caller may pass a private-looking argument by mistake; default
    argparse would echo the unknown argument and value into stderr.
    Keep the usage line but replace the raw error with a fixed generic
    message.
    """

    def error(self, message: str) -> NoReturn:  # noqa: D401 - argparse signature
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    """Build the B16-A CLI parser."""
    ap = SafeArgumentParser(
        description=(
            "B16-A minimal deterministic/mock downstream paired-agent "
            "empirical run (public aggregate-only artifact; synthetic "
            "public micro bug tasks; fresh /tmp workspace per task+arm; "
            "real file edits + real subprocess tests; no live LLM, no "
            "provider calls; no raw event logs/patches/test output/"
            "per-run rows committed)."
        )
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="run deterministic self-test groups and exit (no artifact written)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "output artifact JSON path (default: committed public "
            "aggregate-only artifact)"
        ),
    )
    ap.add_argument(
        "--task-count",
        type=int,
        default=DEFAULT_TASK_COUNT,
        help=(
            "number of deterministic synthetic micro tasks (default: "
            f"{DEFAULT_TASK_COUNT}; range {MIN_TASK_COUNT}-{MAX_TASK_COUNT})"
        ),
    )
    return ap


def _cli_argument_option_strings() -> set[str]:
    """Return the set of CLI option strings (for the option-surface test)."""
    parser = build_parser()
    strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            strings.add(opt)
    return strings


def _validate_task_count(task_count: int) -> None:
    """Validate --task-count is a positive integer in the safe range."""
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

    # Validate task count before running.
    _validate_task_count(args.task_count)

    # Public default mode (committed aggregate-only artifact).
    out_path = args.out if args.out is not None else DEFAULT_OUT
    try:
        report = build_report(task_count=args.task_count)
    except (OSError, subprocess.SubprocessError):
        # Sanitize errors: do not print raw paths or subprocess output.
        print("error: failed to build report", file=sys.stderr)
        sys.exit(1)

    # Strict fail-closed guard immediately before writing the JSON artifact.
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
