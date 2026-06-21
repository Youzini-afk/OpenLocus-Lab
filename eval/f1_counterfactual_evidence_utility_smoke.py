#!/usr/bin/env python3
"""F1 Counterfactual Evidence Utility Smoke (Public Aggregate-Only Artifact).

This module implements the **F1 counterfactual evidence utility smoke**. It
is a deterministic/mock causal smoke over public synthetic micro tasks that
measures marginal context-utility deltas for a coding-agent trajectory.

F1 is **not** a live LLM downstream agent run. The agent is a
**deterministic mock agent** whose behavior depends on the provided
context pack. There are **no provider calls**, **no remote calls**, and
**no live LLM**. For each synthetic task and each counterfactual context
variant, F1 creates a fresh ``/tmp`` workspace, runs the deterministic
mock agent (real file edits + real subprocess tests), and computes
aggregate per-variant behavior metrics. From those aggregate metrics it
computes marginal utility deltas that are causal-shaped (variant vs
variant), but it is still a deterministic/mock smoke, not live-agent
value.

F1 uses **six counterfactual context variants**:

1. ``base_no_context``: no cue -> no-op -> tests fail.
2. ``primary_only``: primary cue -> edit target correctly -> tests pass.
3. ``support_only``: support cue -> edit support (wrong file) -> tests fail.
4. ``primary_plus_support``: primary + support -> inspect support, edit
   target correctly -> tests pass; higher tool/context tokens than primary.
5. ``distractor_only``: wrong cue -> edit distractor -> tests fail;
   ``wrong_file_edits`` increases.
6. ``primary_plus_distractor``: primary + distractor -> inspect
   distractor, edit target correctly, then edit distractor (after the
   correct first edit) -> tests pass; ``wrong_file_edits``,
   ``tool_calls_before_first_edit``, and ``context_tokens`` are worse
   than primary_only.

Five marginal utility effects are computed from aggregate variant
metrics (effect names are deliberately utility-specific and do NOT use
``E_primary`` / ``S_support`` field names that would resemble real E/S
calibration):

* ``primary_context_vs_base`` = ``primary_only`` - ``base_no_context``
* ``support_context_vs_base`` = ``support_only`` - ``base_no_context``
* ``distractor_context_vs_base`` = ``distractor_only`` - ``base_no_context``
* ``support_added_to_primary`` = ``primary_plus_support`` - ``primary_only``
* ``distractor_added_to_primary`` = ``primary_plus_distractor`` - ``primary_only``

A ``theory_mapping`` block records that ``primary_context_vs_base``
corresponds to an E-utility smoke proxy and that
``support_added_to_primary`` / ``distractor_added_to_primary``
correspond to S-conditional utility smoke proxies. However F1 is
explicitly NOT true E/S calibration: ``true_e_s_calibration_claimed=false``,
``automated_e_s_full_calibration_claimed=false``,
``human_e_s_calibration_claimed=false``.

F1 **does not** claim downstream agent value, **does not** promote any
candidate, **does not** change runtime/retriever/pack/backend/
default-policy/EvidenceCore semantics, **does not** claim live agent
generalization, **does not** claim external benchmark performance, and
**does not** claim a real user task. The committed artifact is
aggregate-only: no task IDs, workspace paths, file paths, source
snippets, patches/diffs, test output, raw event logs, per-run rows,
private IDs, or provider/model info beyond the deterministic mock
identity.

Claim boundary (binding):

* Claim level: ``counterfactual_evidence_utility_smoke_only``.
* Status: ``counterfactual_evidence_utility_smoke_pass`` on success; mode
  ``public_aggregate_synthetic_micro_tasks``; phase ``F1``.
* This is **eval/diagnostic only**. It is NOT a runtime change, NOT a
  retriever/pack/backend/default-policy change, NOT an EvidenceCore
  semantic change, NOT a live agent value claim, NOT a promotion, NOT
  an external benchmark performance claim, NOT a true E/S calibration
  claim, and NOT a real user task claim.

Run::

    python3 -m py_compile eval/f1_counterfactual_evidence_utility_smoke.py
    python3 eval/f1_counterfactual_evidence_utility_smoke.py --self-test
    python3 eval/f1_counterfactual_evidence_utility_smoke.py \\
        --out artifacts/f1_counterfactual_evidence_utility/\\
f1_counterfactual_evidence_utility_report.json

The default mode generates deterministic synthetic public micro bug
tasks, creates a fresh ``/tmp`` workspace per task+variant, runs the
deterministic mock agent (real file edits + real subprocess tests),
computes aggregate behavior metrics and marginal utility deltas, and
writes ONLY the public aggregate artifact. Raw event logs/patches/test
output stay under ``/tmp`` and are never committed or uploaded.
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

SCHEMA_VERSION = "f1_counterfactual_evidence_utility_smoke.v1"
GENERATED_BY = "eval/f1_counterfactual_evidence_utility_smoke.py"
CLAIM_LEVEL = "counterfactual_evidence_utility_smoke_only"
TARGET_STATUS = "counterfactual_evidence_utility_smoke_pass"
STATUS_BLOCKED = "counterfactual_evidence_utility_smoke_blocked"
STATUS_FAIL_LEAK = "fail_forbidden_leak"
MODE = "public_aggregate_synthetic_micro_tasks"
PHASE = "F1"

DEFAULT_OUT = Path(
    "artifacts/f1_counterfactual_evidence_utility/"
    "f1_counterfactual_evidence_utility_report.json"
)
DEFAULT_TASK_COUNT = 24
MIN_TASK_COUNT = 4
MAX_TASK_COUNT = 100

# Six counterfactual context variants (fixed allowlist; never per-run rows).
VARIANTS: tuple[str, ...] = (
    "base_no_context",
    "primary_only",
    "support_only",
    "primary_plus_support",
    "distractor_only",
    "primary_plus_distractor",
)

# Five marginal utility effects (fixed allowlist; utility-specific names
# that deliberately avoid E_primary / S_support field-name shape).
EFFECTS: tuple[str, ...] = (
    "primary_context_vs_base",
    "support_context_vs_base",
    "distractor_context_vs_base",
    "support_added_to_primary",
    "distractor_added_to_primary",
)

# Each effect is computed as (treatment_variant - control_variant).
EFFECT_VARIANT_PAIRS: dict[str, tuple[str, str]] = {
    "primary_context_vs_base": ("primary_only", "base_no_context"),
    "support_context_vs_base": ("support_only", "base_no_context"),
    "distractor_context_vs_base": ("distractor_only", "base_no_context"),
    "support_added_to_primary": (
        "primary_plus_support",
        "primary_only",
    ),
    "distractor_added_to_primary": (
        "primary_plus_distractor",
        "primary_only",
    ),
}

# Per-variant aggregate metric names emitted in the public artifact.
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
# because it is identical across variants by paired design.
DELTA_METRIC_NAMES: tuple[str, ...] = tuple(
    name for name in METRIC_NAMES if name != "run_count"
)

# ---------------------------------------------------------------------------
# Safe booleans true (deterministic mock run only). Exactly these are true
# in the committed public artifact.
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "counterfactual_context_variants_executed": True,
    "deterministic_mock_agent": True,
    "real_file_edits_performed": True,
    "subprocess_tests_executed": True,
    "marginal_utility_metrics_computed": True,
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
}

# ---------------------------------------------------------------------------
# No-claim / no-runtime-change flags (all MUST be false in the committed
# public artifact). F1 runs NO live LLM, makes NO provider/remote calls,
# proves NO downstream agent value, promotes NO candidate, changes NO
# runtime/retriever/pack/backend/default-policy/EvidenceCore semantics,
# claims NO external benchmark performance, NO live agent generalization,
# NO real user task, and NO true E/S calibration.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "live_llm_agent": False,
    "provider_calls_made": False,
    "remote_provider_calls_made": False,
    "downstream_agent_value_proven": False,
    "live_agent_generalization_claimed": False,
    "real_user_task_claimed": False,
    "true_e_s_calibration_claimed": False,
    "automated_e_s_full_calibration_claimed": False,
    "human_e_s_calibration_claimed": False,
    "external_benchmark_performance_claimed": False,
    "promotion_ready": False,
    "default_should_change": False,
    "runtime_behavior_changed": False,
    "retriever_changed": False,
    "pack_builder_changed": False,
    "backend_changed": False,
    "default_policy_changed": False,
    "evidencecore_semantics_changed": False,
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
        "target_module", "support_module", "distractor_module",
        "test_module", "source_path", "module_path", "module",
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
# event-log / secret / identifier data. F1 rejects ALL URLs (no URL
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
# F1-specific leak patterns: /tmp workspace paths, task identifiers,
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
            "support_module": "support.py",
            "distractor_module": "distractor.py",
            "test_module": "test_target.py",
            "correct_value": correct_value,
            "buggy_value": buggy_value,
            "fix_kind": "replace_return_value",
        }
        tasks.append(task)
    return tasks


# ---------------------------------------------------------------------------
# Workspace builder (fresh /tmp per task+variant; real tiny Python files).
# ---------------------------------------------------------------------------


def _build_workspace(workspace_dir: Path, task: dict[str, Any]) -> None:
    """Create a fresh workspace with tiny Python modules + stdlib test.

    The workspace contains:

    * ``target.py``: a tiny module with a one-line bug (returns wrong
      value). The mock agent edits this file when a primary cue is
      present.
    * ``support.py``: a helper module containing a supporting symbol that
      is NOT the target symbol. Editing this file does not affect the
      test outcome.
    * ``distractor.py``: a wrong-file distractor with a similar-looking
      symbol (the mock agent may edit this if given a wrong cue).
    * ``test_target.py``: a stdlib test that imports ``target`` and
      asserts the correct value; exits 0 on success, 1 on failure.

    All files are real Python files written to disk under ``/tmp``.
    """
    workspace_dir.mkdir(parents=True, exist_ok=True)

    target_path = workspace_dir / task["target_module"]
    support_path = workspace_dir / task["support_module"]
    distractor_path = workspace_dir / task["distractor_module"]
    test_path = workspace_dir / task["test_module"]

    # Target module: has a bug (returns wrong value).
    target_path.write_text(
        f"def {task['symbol']}():\n"
        f"    return {task['buggy_value']}\n",
        encoding="utf-8",
    )

    # Support module: helper symbol, not the target. Editing this does
    # not affect the test (test only imports target).
    support_path.write_text(
        f"def {task['symbol']}_helper():\n"
        f"    return {task['correct_value']}\n",
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
# Pack builder (six counterfactual context variants; deterministic cues).
# ---------------------------------------------------------------------------


def _build_pack(variant: str, task: dict[str, Any]) -> dict[str, Any]:
    """Build the context pack for a variant.

    Packs are NEVER emitted to the public artifact; only their
    deterministic ``context_tokens`` count is aggregated.

    Six counterfactual context variants:

    * ``base_no_context``: no file cue at all -> agent no-op -> tests fail.
    * ``primary_only``: primary target/symbol/operation cue -> agent
      edits the correct target file -> tests pass.
    * ``support_only``: support cue only -> agent edits support (wrong
      file) -> tests fail.
    * ``primary_plus_support``: primary + support cue -> agent inspects
      support, then edits target correctly -> tests pass; richer
      context (higher tool calls / context tokens) than primary_only.
    * ``distractor_only``: wrong cue only -> agent edits distractor
      (wrong file) -> tests fail; ``wrong_file_edits`` increases.
    * ``primary_plus_distractor``: primary + distractor cue -> agent
      inspects distractor, edits target correctly, then also edits
      distractor (after the correct first edit) -> tests pass; worse
      ``wrong_file_edits`` / ``tool_calls`` / ``context_tokens`` than
      primary_only.
    """
    if variant == "base_no_context":
        return {"context_tokens": 8}
    if variant == "primary_only":
        return {
            "target_file": task["target_module"],
            "target_symbol": task["symbol"],
            "operation_hint": "replace_return_value",
            "context_tokens": 24,
        }
    if variant == "support_only":
        return {
            "support_file": task["support_module"],
            "context_tokens": 20,
        }
    if variant == "primary_plus_support":
        return {
            "target_file": task["target_module"],
            "target_symbol": task["symbol"],
            "operation_hint": "replace_return_value",
            "support_file": task["support_module"],
            "context_tokens": 40,
        }
    if variant == "distractor_only":
        return {
            "wrong_cue_file": task["distractor_module"],
            "context_tokens": 16,
        }
    if variant == "primary_plus_distractor":
        return {
            "target_file": task["target_module"],
            "target_symbol": task["symbol"],
            "operation_hint": "replace_return_value",
            "wrong_cue_file": task["distractor_module"],
            "context_tokens": 32,
        }
    raise ValueError(f"unknown variant: {variant}")


# ---------------------------------------------------------------------------
# Deterministic mock agent (pack-dependent; real file edits).
# ---------------------------------------------------------------------------


def _run_mock_agent(
    workspace_dir: Path, task: dict[str, Any], pack: dict[str, Any]
) -> dict[str, Any]:
    """Run the deterministic mock agent for one task+variant.

    The agent is fully deterministic and pack-dependent:

    * if the pack has a ``target_file`` cue (primary cue present):
        * if ``support_file`` is also present: inspect support
          (1 tool call, no edit), then edit target correctly.
        * if ``wrong_cue_file`` is also present: inspect distractor
          (1 tool call, no edit), then edit target correctly, then
          edit distractor (wrong file edit AFTER the correct first
          edit; tests still pass because target is fixed).
        * else: edit target correctly.
    * elif the pack has a ``support_file`` cue (no primary): edit
      support (wrong file); tests still fail.
    * elif the pack has a ``wrong_cue_file`` cue (no primary): edit
      distractor (wrong file); tests fail.
    * else -> do nothing (tests fail; no edit).

    After the edit (or no-op), the agent runs the real subprocess test
    command and records the pass/fail result. The per-run **event log**
    (with file paths, edit content, test stdout/stderr) is kept in-memory
    only and NEVER written to the public artifact. Only aggregate
    metrics are returned.
    """
    # Transient event log; NEVER committed.
    event_log: list[dict[str, Any]] = []

    target_file = pack.get("target_file")
    wrong_cue_file = pack.get("wrong_cue_file")
    support_file = pack.get("support_file")

    wrong_file_edits = 0
    tool_calls_before_first_edit = 0
    correct_file_before_first_edit = False

    if target_file:
        # Primary cue present: agent will eventually edit target correctly.
        if support_file:
            # Inspect support first (tool call, no edit).
            tool_calls_before_first_edit += 1
            event_log.append(
                {"event": "inspect", "kind": "support", "file": support_file}
            )
        if wrong_cue_file:
            # Inspect distractor first (tool call, no edit).
            tool_calls_before_first_edit += 1
            event_log.append(
                {"event": "inspect", "kind": "distractor",
                 "file": wrong_cue_file}
            )
        # Edit target correctly (this is the FIRST edit).
        edit_path = workspace_dir / target_file
        correct_file_before_first_edit = True
        tool_calls_before_first_edit += 1
        new_content = (
            f"def {task['symbol']}():\n"
            f"    return {task['correct_value']}\n"
        )
        edit_path.write_text(new_content, encoding="utf-8")
        event_log.append(
            {"event": "edit", "kind": "correct_file",
             "file": str(edit_path)}
        )
        # If distractor also present, agent also edits distractor
        # (after correct first edit; does not break correctness because
        # tests already pass on the target fix).
        if wrong_cue_file:
            distractor_edit_path = workspace_dir / wrong_cue_file
            wrong_file_edits += 1
            new_distractor_content = (
                f"def {task['symbol']}_aux():\n"
                f"    return {task['correct_value']}\n"
            )
            distractor_edit_path.write_text(
                new_distractor_content, encoding="utf-8"
            )
            event_log.append(
                {"event": "edit", "kind": "wrong_file_after_correct",
                 "file": str(distractor_edit_path)}
            )
    elif support_file:
        # Support cue only: edit support (wrong file); tests still fail.
        edit_path = workspace_dir / support_file
        wrong_file_edits += 1
        tool_calls_before_first_edit += 1
        new_content = (
            f"def {task['symbol']}_helper():\n"
            f"    return {task['correct_value']}\n"
        )
        edit_path.write_text(new_content, encoding="utf-8")
        event_log.append(
            {"event": "edit", "kind": "wrong_file",
             "file": str(edit_path)}
        )
    elif wrong_cue_file:
        # Distractor cue only: edit distractor (wrong file); tests fail.
        edit_path = workspace_dir / wrong_cue_file
        wrong_file_edits += 1
        tool_calls_before_first_edit += 1
        new_content = (
            f"def {task['symbol']}_aux():\n"
            f"    return {task['correct_value']}\n"
        )
        edit_path.write_text(new_content, encoding="utf-8")
        event_log.append(
            {"event": "edit", "kind": "wrong_file",
             "file": str(edit_path)}
        )
    else:
        # No cue: do nothing.
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


def _aggregate_variant_metrics(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute per-variant aggregate metrics from per-run results.

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


def _compute_effect(
    control: dict[str, Any], treatment: dict[str, Any]
) -> dict[str, float]:
    """Compute treatment-minus-control deltas for rate/mean metrics."""
    return {
        f"{name}_delta": _round_metric(treatment[name] - control[name])
        for name in DELTA_METRIC_NAMES
    }


def _build_theory_mapping() -> dict[str, Any]:
    """Build the theory-mapping block.

    The mapping records that the marginal effects correspond to
    E-utility smoke proxies and S-conditional utility smoke proxies,
    but explicitly states that F1 is NOT true E/S calibration.
    """
    return {
        "primary_context_vs_base_corresponds_to": "e_utility_smoke_proxy",
        "support_context_vs_base_corresponds_to": (
            "e_utility_smoke_proxy_support_variant"
        ),
        "distractor_context_vs_base_corresponds_to": (
            "e_utility_smoke_proxy_distractor_variant"
        ),
        "support_added_to_primary_corresponds_to": (
            "s_conditional_utility_smoke_proxy"
        ),
        "distractor_added_to_primary_corresponds_to": (
            "s_conditional_distractor_utility_smoke_proxy"
        ),
        "interpretation": (
            "marginal utility deltas computed from aggregate variant "
            "metrics; deterministic mock causal smoke; not true E/S "
            "calibration"
        ),
        "true_e_s_calibration_claimed": False,
        "automated_e_s_full_calibration_claimed": False,
        "human_e_s_calibration_claimed": False,
    }


# ---------------------------------------------------------------------------
# Public artifact builder
# ---------------------------------------------------------------------------


def _build_public_report(
    checks: list[dict[str, Any]],
    all_passed: bool,
    variant_metrics: dict[str, dict[str, Any]] | None = None,
    marginal_effects: dict[str, dict[str, float]] | None = None,
    input_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the public aggregate-only report (fail-closed scan).

    The default committed artifact. No per-run rows, no paths, no
    patches, no test output, no event logs, no task IDs, no file paths,
    no source snippets, no content hashes, no secrets.
    """
    variant_metrics = variant_metrics or {
        v: _aggregate_variant_metrics([]) for v in VARIANTS
    }
    marginal_effects = marginal_effects or {
        effect: _compute_effect(
            variant_metrics[EFFECT_VARIANT_PAIRS[effect][1]],
            variant_metrics[EFFECT_VARIANT_PAIRS[effect][0]],
        )
        for effect in EFFECTS
    }
    input_summary = input_summary or {
        "synthetic_task_count": 0,
        "run_count_per_variant": 0,
        "total_runs": 0,
        "variants": list(VARIANTS),
        "variant_count": len(VARIANTS),
        "effects": list(EFFECTS),
        "effect_count": len(EFFECTS),
        "counterfactual_design": True,
        "workspace_isolation": "fresh_tmp_per_task_variant",
        "transient_workspace_outputs_only": True,
    }

    # Smoke passes iff self-test passed AND every variant has run_count
    # >= 1 AND primary_only solves (solve_rate=1.0) AND base_no_context
    # does NOT solve AND support_only does NOT solve AND distractor_only
    # does NOT solve AND distractor_only wrong_file_edits >
    # base_no_context wrong_file_edits AND marginal effects are computed.
    primary_solves = (
        variant_metrics["primary_only"]["solve_rate"] == 1.0
    )
    base_not_solve = (
        variant_metrics["base_no_context"]["solve_rate"] == 0.0
    )
    support_not_solve = (
        variant_metrics["support_only"]["solve_rate"] == 0.0
    )
    distractor_not_solve = (
        variant_metrics["distractor_only"]["solve_rate"] == 0.0
    )
    distractor_wrong_gt_base = (
        variant_metrics["distractor_only"]["wrong_file_edits_mean"]
        > variant_metrics["base_no_context"]["wrong_file_edits_mean"]
    )
    all_variants_ran = all(
        variant_metrics[v]["run_count"] >= 1 for v in VARIANTS
    )
    smoke_passes = (
        all_passed
        and all_variants_ran
        and primary_solves
        and base_not_solve
        and support_not_solve
        and distractor_not_solve
        and distractor_wrong_gt_base
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
        "variant_metrics": variant_metrics,
        "marginal_effects": marginal_effects,
        "theory_mapping": _build_theory_mapping(),
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
    """Assemble the public aggregate-only report from a real run.

    Runs the deterministic self-test checks, generates deterministic
    synthetic public micro bug tasks, creates a fresh ``/tmp`` workspace
    per task+variant, runs the deterministic mock agent (real file
    edits + real subprocess tests), computes aggregate behavior metrics
    and marginal utility deltas, and assembles the full public report
    (which re-scans itself).
    """
    checks, all_passed = run_self_test_checks()

    tasks = _generate_synthetic_tasks(task_count)

    variant_runs: dict[str, list[dict[str, Any]]] = {
        v: [] for v in VARIANTS
    }

    for task in tasks:
        for variant in VARIANTS:
            pack = _build_pack(variant, task)
            # Fresh /tmp workspace per task+variant.
            workspace_dir = Path(
                tempfile.mkdtemp(prefix="f1_workspace_")
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
            variant_runs[variant].append(run)

    variant_metrics = {
        v: _aggregate_variant_metrics(variant_runs[v]) for v in VARIANTS
    }
    marginal_effects = {
        effect: _compute_effect(
            variant_metrics[EFFECT_VARIANT_PAIRS[effect][1]],
            variant_metrics[EFFECT_VARIANT_PAIRS[effect][0]],
        )
        for effect in EFFECTS
    }

    input_summary: dict[str, Any] = {
        "synthetic_task_count": task_count,
        "run_count_per_variant": task_count,
        "total_runs": task_count * len(VARIANTS),
        "variants": list(VARIANTS),
        "variant_count": len(VARIANTS),
        "effects": list(EFFECTS),
        "effect_count": len(EFFECTS),
        "counterfactual_design": True,
        "workspace_isolation": "fresh_tmp_per_task_variant",
        "transient_workspace_outputs_only": True,
    }

    return _build_public_report(
        checks,
        all_passed,
        variant_metrics=variant_metrics,
        marginal_effects=marginal_effects,
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
    "support_module": "support.py",
    "distractor_module": "distractor.py",
    "test_module": "test_target.py",
    "correct_value": 100,
    "buggy_value": -100,
    "fix_kind": "replace_return_value",
}


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all F1 self-test groups.

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

    # --- Group 5: Pack builder (six variants + designed cues). ---
    base_pack = _build_pack("base_no_context", tasks_4[0])
    primary_pack = _build_pack("primary_only", tasks_4[0])
    support_pack = _build_pack("support_only", tasks_4[0])
    primary_plus_support_pack = _build_pack(
        "primary_plus_support", tasks_4[0]
    )
    distractor_pack = _build_pack("distractor_only", tasks_4[0])
    primary_plus_distractor_pack = _build_pack(
        "primary_plus_distractor", tasks_4[0]
    )
    checks.append(
        _check(
            "base_pack_has_no_file_cue",
            "target_file" not in base_pack
            and "support_file" not in base_pack
            and "wrong_cue_file" not in base_pack,
        )
    )
    checks.append(
        _check(
            "primary_pack_has_target_file_cue",
            "target_file" in primary_pack,
        )
    )
    checks.append(
        _check(
            "primary_pack_has_target_symbol_cue",
            "target_symbol" in primary_pack,
        )
    )
    checks.append(
        _check(
            "primary_pack_has_operation_hint_cue",
            "operation_hint" in primary_pack,
        )
    )
    checks.append(
        _check(
            "support_pack_has_support_file_cue_only",
            "support_file" in support_pack
            and "target_file" not in support_pack
            and "wrong_cue_file" not in support_pack,
        )
    )
    checks.append(
        _check(
            "primary_plus_support_pack_has_both_target_and_support",
            "target_file" in primary_plus_support_pack
            and "support_file" in primary_plus_support_pack,
        )
    )
    checks.append(
        _check(
            "distractor_pack_has_wrong_cue_file_cue_only",
            "wrong_cue_file" in distractor_pack
            and "target_file" not in distractor_pack
            and "support_file" not in distractor_pack,
        )
    )
    checks.append(
        _check(
            "primary_plus_distractor_pack_has_both_target_and_wrong_cue",
            "target_file" in primary_plus_distractor_pack
            and "wrong_cue_file" in primary_plus_distractor_pack,
        )
    )
    checks.append(
        _check(
            "primary_plus_support_pack_richer_than_primary_pack",
            primary_plus_support_pack["context_tokens"]
            > primary_pack["context_tokens"],
        )
    )
    checks.append(
        _check(
            "primary_plus_distractor_pack_richer_than_primary_pack",
            primary_plus_distractor_pack["context_tokens"]
            > primary_pack["context_tokens"],
        )
    )
    checks.append(
        _check(
            "variant_count_is_six",
            len(VARIANTS) == 6,
        )
    )
    checks.append(
        _check(
            "effect_count_is_five",
            len(EFFECTS) == 5,
        )
    )

    # --- Group 6: Real workspace creation + real file edits + real tests.
    # Use a real /tmp workspace for the edit/test loop.
    workspace_dir = Path(tempfile.mkdtemp(prefix="f1_selftest_"))
    try:
        _build_workspace(workspace_dir, _SYNTH_TASK)
        target_path = workspace_dir / _SYNTH_TASK["target_module"]
        support_path = workspace_dir / _SYNTH_TASK["support_module"]
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
                "workspace_creates_support_file",
                support_path.is_file(),
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

        # --- Group 7: Mock agent behavior per variant. ---
        # base_no_context: agent no-op -> tests fail.
        _build_workspace(workspace_dir, _SYNTH_TASK)
        base_run = _run_mock_agent(
            workspace_dir, _SYNTH_TASK, base_pack
        )
        checks.append(
            _check(
                "base_agent_no_edit",
                base_run["wrong_file_edits"] == 0
                and base_run["correct_file_before_first_edit"] is False
                and base_run["tool_calls_before_first_edit"] == 0,
            )
        )
        checks.append(
            _check(
                "base_agent_tests_fail",
                base_run["tests_pass"] is False,
            )
        )
        checks.append(
            _check(
                "base_agent_no_solve",
                base_run["solve"] is False,
            )
        )

        # primary_only: agent edits correct target file -> tests pass.
        _build_workspace(workspace_dir, _SYNTH_TASK)
        primary_run = _run_mock_agent(
            workspace_dir, _SYNTH_TASK, primary_pack
        )
        checks.append(
            _check(
                "primary_agent_edits_correct_file",
                primary_run["correct_file_before_first_edit"] is True,
            )
        )
        checks.append(
            _check(
                "primary_agent_no_wrong_file_edits",
                primary_run["wrong_file_edits"] == 0,
            )
        )
        checks.append(
            _check(
                "primary_agent_one_tool_call_before_first_edit",
                primary_run["tool_calls_before_first_edit"] == 1,
            )
        )
        checks.append(
            _check(
                "primary_agent_tests_pass",
                primary_run["tests_pass"] is True,
            )
        )
        checks.append(
            _check(
                "primary_agent_solve",
                primary_run["solve"] is True,
            )
        )
        checks.append(
            _check(
                "primary_agent_real_file_edit",
                "return 100" in target_path.read_text(encoding="utf-8"),
            )
        )

        # support_only: agent edits support (wrong file) -> tests fail.
        _build_workspace(workspace_dir, _SYNTH_TASK)
        support_run = _run_mock_agent(
            workspace_dir, _SYNTH_TASK, support_pack
        )
        checks.append(
            _check(
                "support_agent_edits_wrong_file",
                support_run["wrong_file_edits"] == 1,
            )
        )
        checks.append(
            _check(
                "support_agent_not_correct_file",
                support_run["correct_file_before_first_edit"] is False,
            )
        )
        checks.append(
            _check(
                "support_agent_tests_fail",
                support_run["tests_pass"] is False,
            )
        )
        checks.append(
            _check(
                "support_agent_no_solve",
                support_run["solve"] is False,
            )
        )
        checks.append(
            _check(
                "support_agent_edited_support_file",
                "return 100"
                in support_path.read_text(encoding="utf-8"),
            )
        )

        # primary_plus_support: agent inspects support, edits target
        # correctly -> tests pass; more tool calls/context than primary.
        _build_workspace(workspace_dir, _SYNTH_TASK)
        primary_plus_support_run = _run_mock_agent(
            workspace_dir, _SYNTH_TASK, primary_plus_support_pack
        )
        checks.append(
            _check(
                "primary_plus_support_agent_edits_correct_file",
                primary_plus_support_run[
                    "correct_file_before_first_edit"
                ]
                is True,
            )
        )
        checks.append(
            _check(
                "primary_plus_support_agent_no_wrong_file_edits",
                primary_plus_support_run["wrong_file_edits"] == 0,
            )
        )
        checks.append(
            _check(
                "primary_plus_support_agent_two_tool_calls_before_edit",
                primary_plus_support_run[
                    "tool_calls_before_first_edit"
                ]
                == 2,
            )
        )
        checks.append(
            _check(
                "primary_plus_support_agent_tests_pass",
                primary_plus_support_run["tests_pass"] is True,
            )
        )
        checks.append(
            _check(
                "primary_plus_support_agent_solve",
                primary_plus_support_run["solve"] is True,
            )
        )
        checks.append(
            _check(
                "primary_plus_support_richer_context_than_primary",
                primary_plus_support_run["context_tokens"]
                > primary_run["context_tokens"],
            )
        )

        # distractor_only: agent edits distractor (wrong file) -> tests
        # fail; wrong_file_edits > base.
        _build_workspace(workspace_dir, _SYNTH_TASK)
        distractor_run = _run_mock_agent(
            workspace_dir, _SYNTH_TASK, distractor_pack
        )
        checks.append(
            _check(
                "distractor_agent_edits_wrong_file",
                distractor_run["wrong_file_edits"] == 1,
            )
        )
        checks.append(
            _check(
                "distractor_agent_not_correct_file",
                distractor_run["correct_file_before_first_edit"] is False,
            )
        )
        checks.append(
            _check(
                "distractor_agent_tests_fail",
                distractor_run["tests_pass"] is False,
            )
        )
        checks.append(
            _check(
                "distractor_agent_no_solve",
                distractor_run["solve"] is False,
            )
        )
        checks.append(
            _check(
                "distractor_agent_wrong_edits_greater_than_base",
                distractor_run["wrong_file_edits"]
                > base_run["wrong_file_edits"],
            )
        )
        checks.append(
            _check(
                "distractor_agent_edited_distractor_file",
                "return 100"
                in distractor_path.read_text(encoding="utf-8"),
            )
        )

        # primary_plus_distractor: agent inspects distractor, edits
        # target correctly, then edits distractor (after correct first
        # edit) -> tests pass; wrong_file_edits > primary_only.
        _build_workspace(workspace_dir, _SYNTH_TASK)
        primary_plus_distractor_run = _run_mock_agent(
            workspace_dir, _SYNTH_TASK, primary_plus_distractor_pack
        )
        checks.append(
            _check(
                "primary_plus_distractor_agent_edits_correct_file",
                primary_plus_distractor_run[
                    "correct_file_before_first_edit"
                ]
                is True,
            )
        )
        checks.append(
            _check(
                "primary_plus_distractor_agent_wrong_file_edits_one",
                primary_plus_distractor_run["wrong_file_edits"] == 1,
            )
        )
        checks.append(
            _check(
                "primary_plus_distractor_agent_two_tool_calls_before_edit",
                primary_plus_distractor_run[
                    "tool_calls_before_first_edit"
                ]
                == 2,
            )
        )
        checks.append(
            _check(
                "primary_plus_distractor_agent_tests_pass",
                primary_plus_distractor_run["tests_pass"] is True,
            )
        )
        checks.append(
            _check(
                "primary_plus_distractor_agent_solve",
                primary_plus_distractor_run["solve"] is True,
            )
        )
        checks.append(
            _check(
                "primary_plus_distractor_wrong_edits_greater_than_primary",
                primary_plus_distractor_run["wrong_file_edits"]
                > primary_run["wrong_file_edits"],
            )
        )
        checks.append(
            _check(
                "primary_plus_distractor_richer_context_than_primary",
                primary_plus_distractor_run["context_tokens"]
                > primary_run["context_tokens"],
            )
        )

        # --- Group 8: Mock action dependence on pack cues. ---
        checks.append(
            _check(
                "mock_action_depends_on_primary_target_file",
                primary_run["correct_file_before_first_edit"]
                and not base_run["correct_file_before_first_edit"]
                and not support_run["correct_file_before_first_edit"]
                and not distractor_run["correct_file_before_first_edit"],
            )
        )
        checks.append(
            _check(
                "mock_action_depends_on_wrong_cue_file",
                distractor_run["wrong_file_edits"] == 1
                and base_run["wrong_file_edits"] == 0
                and primary_run["wrong_file_edits"] == 0,
            )
        )
        checks.append(
            _check(
                "primary_solve_rate_higher_than_base",
                primary_run["solve"] and not base_run["solve"],
            )
        )
        checks.append(
            _check(
                "support_only_does_not_solve_but_edits_wrong_file",
                not support_run["solve"]
                and support_run["wrong_file_edits"] == 1,
            )
        )
        checks.append(
            _check(
                "distractor_only_does_not_solve_but_edits_wrong_file",
                not distractor_run["solve"]
                and distractor_run["wrong_file_edits"] == 1,
            )
        )
        checks.append(
            _check(
                "primary_plus_distractor_still_solves",
                primary_plus_distractor_run["solve"] is True,
            )
        )

        # --- Group 9: Aggregate metrics math. ---
        runs = [
            base_run,
            primary_run,
            support_run,
            primary_plus_support_run,
            distractor_run,
            primary_plus_distractor_run,
        ]
        agg = _aggregate_variant_metrics(runs)
        checks.append(
            _check(
                "aggregate_run_count_correct",
                agg["run_count"] == 6,
            )
        )
        # Of the 6 runs: base/support/distractor fail; primary,
        # primary_plus_support, primary_plus_distractor solve.
        checks.append(
            _check(
                "aggregate_solve_rate_correct",
                _round_metric(agg["solve_rate"]) == _round_metric(3 / 6),
            )
        )
        checks.append(
            _check(
                "aggregate_tests_pass_rate_correct",
                _round_metric(agg["tests_pass_rate"])
                == _round_metric(3 / 6),
            )
        )
        checks.append(
            _check(
                "aggregate_correct_file_rate_correct",
                _round_metric(
                    agg["correct_file_before_first_edit_rate"]
                )
                == _round_metric(3 / 6),
            )
        )
        # wrong_file_edits: support(1) + distractor(1) +
        # primary_plus_distractor(1) = 3 over 6 runs.
        checks.append(
            _check(
                "aggregate_wrong_file_edits_mean_correct",
                _round_metric(agg["wrong_file_edits_mean"])
                == _round_metric(3 / 6),
            )
        )
        # tool_calls: base(0) + primary(1) + support(1) +
        # primary_plus_support(2) + distractor(1) +
        # primary_plus_distractor(2) = 7 over 6 runs.
        checks.append(
            _check(
                "aggregate_tool_calls_mean_correct",
                _round_metric(agg["tool_calls_before_first_edit_mean"])
                == _round_metric(7 / 6),
            )
        )
        checks.append(
            _check(
                "aggregate_cost_proxy_mean_zero",
                agg["cost_proxy_mean"] == 0.0,
            )
        )

        # --- Group 10: Marginal effects computation. ---
        base_agg = _aggregate_variant_metrics([base_run])
        primary_agg = _aggregate_variant_metrics([primary_run])
        support_agg = _aggregate_variant_metrics([support_run])
        primary_plus_support_agg = _aggregate_variant_metrics(
            [primary_plus_support_run]
        )
        distractor_agg = _aggregate_variant_metrics([distractor_run])
        primary_plus_distractor_agg = _aggregate_variant_metrics(
            [primary_plus_distractor_run]
        )

        primary_vs_base = _compute_effect(base_agg, primary_agg)
        support_vs_base = _compute_effect(base_agg, support_agg)
        distractor_vs_base = _compute_effect(base_agg, distractor_agg)
        support_added = _compute_effect(
            primary_agg, primary_plus_support_agg
        )
        distractor_added = _compute_effect(
            primary_agg, primary_plus_distractor_agg
        )

        checks.append(
            _check(
                "primary_context_vs_base_solve_rate_delta_positive",
                primary_vs_base["solve_rate_delta"] > 0,
            )
        )
        checks.append(
            _check(
                "primary_context_vs_base_tool_calls_delta_positive",
                primary_vs_base[
                    "tool_calls_before_first_edit_mean_delta"
                ]
                > 0,
            )
        )
        checks.append(
            _check(
                "primary_context_vs_base_context_tokens_delta_positive",
                primary_vs_base["context_tokens_mean_delta"] > 0,
            )
        )
        checks.append(
            _check(
                "support_context_vs_base_solve_rate_delta_zero",
                support_vs_base["solve_rate_delta"] == 0.0,
            )
        )
        checks.append(
            _check(
                "support_context_vs_base_wrong_file_edits_delta_positive",
                support_vs_base["wrong_file_edits_mean_delta"] > 0,
            )
        )
        checks.append(
            _check(
                "distractor_context_vs_base_solve_rate_delta_zero",
                distractor_vs_base["solve_rate_delta"] == 0.0,
            )
        )
        checks.append(
            _check(
                "distractor_context_vs_base_wrong_file_edits_delta_positive",
                distractor_vs_base["wrong_file_edits_mean_delta"] > 0,
            )
        )
        checks.append(
            _check(
                "support_added_to_primary_solve_rate_delta_zero",
                support_added["solve_rate_delta"] == 0.0,
            )
        )
        checks.append(
            _check(
                "support_added_to_primary_tool_calls_delta_positive",
                support_added[
                    "tool_calls_before_first_edit_mean_delta"
                ]
                > 0,
            )
        )
        checks.append(
            _check(
                "support_added_to_primary_context_tokens_delta_positive",
                support_added["context_tokens_mean_delta"] > 0,
            )
        )
        checks.append(
            _check(
                "distractor_added_to_primary_solve_rate_delta_zero",
                distractor_added["solve_rate_delta"] == 0.0,
            )
        )
        checks.append(
            _check(
                "distractor_added_to_primary_wrong_file_edits_delta_positive",
                distractor_added["wrong_file_edits_mean_delta"] > 0,
            )
        )
        checks.append(
            _check(
                "distractor_added_to_primary_context_tokens_delta_positive",
                distractor_added["context_tokens_mean_delta"] > 0,
            )
        )
        checks.append(
            _check(
                "delta_run_count_not_present_in_effects",
                "run_count_delta" not in primary_vs_base
                and "run_count_delta" not in support_added
                and "run_count_delta" not in distractor_added,
            )
        )

        # --- Group 11: Theory mapping. ---
        tm = _build_theory_mapping()
        checks.append(
            _check(
                "theory_mapping_marks_e_utility_proxy",
                tm["primary_context_vs_base_corresponds_to"]
                == "e_utility_smoke_proxy",
            )
        )
        checks.append(
            _check(
                "theory_mapping_marks_s_conditional_proxy",
                tm["support_added_to_primary_corresponds_to"]
                == "s_conditional_utility_smoke_proxy",
            )
        )
        checks.append(
            _check(
                "theory_mapping_marks_s_conditional_distractor_proxy",
                tm["distractor_added_to_primary_corresponds_to"]
                == "s_conditional_distractor_utility_smoke_proxy",
            )
        )
        checks.append(
            _check(
                "theory_mapping_true_e_s_calibration_claimed_false",
                tm["true_e_s_calibration_claimed"] is False,
            )
        )
        checks.append(
            _check(
                "theory_mapping_automated_e_s_full_calibration_claimed_false",
                tm["automated_e_s_full_calibration_claimed"] is False,
            )
        )
        checks.append(
            _check(
                "theory_mapping_human_e_s_calibration_claimed_false",
                tm["human_e_s_calibration_claimed"] is False,
            )
        )
    finally:
        try:
            shutil.rmtree(workspace_dir, ignore_errors=True)
        except OSError:
            pass

    # --- Group 12: Scanner rejections (fail-closed). ---
    # Workspace path value.
    checks.append(
        _check(
            "scanner_rejects_tmp_workspace_path",
            bool(
                _scan_forbidden(
                    {"leaked_workspace": "/tmp/f1_workspace_0"}
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
    checks.append(
        _check(
            "scanner_rejects_support_file_path_value",
            bool(_scan_forbidden({"leaked_file": "support.py"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_distractor_file_path_value",
            bool(_scan_forbidden({"leaked_file": "distractor.py"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_test_file_path_value",
            bool(_scan_forbidden({"leaked_file": "test_target.py"})),
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
    # Context text value (multiline).
    checks.append(
        _check(
            "scanner_rejects_context_text",
            bool(
                _scan_forbidden(
                    {"leaked_context": "primary cue:\nedit target\n"}
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
    # Multiline string value.
    checks.append(
        _check(
            "scanner_rejects_multiline_value",
            bool(_scan_forbidden({"leaked": "line1\nline2"})),
        )
    )
    # Raw JSON fragment value.
    checks.append(
        _check(
            "scanner_rejects_raw_json_fragment",
            bool(
                _scan_forbidden(
                    {"leaked": '{"key": "value"}'}
                )
            ),
        )
    )

    # --- Group 13: Scanner allows legitimate aggregate values. ---
    checks.append(
        _check(
            "scanner_allows_variant_name_base_no_context",
            not _scan_forbidden({"variants": ["base_no_context"]}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_variant_name_primary_only",
            not _scan_forbidden({"variants": ["primary_only"]}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_variant_name_primary_plus_distractor",
            not _scan_forbidden(
                {"variants": ["primary_plus_distractor"]}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_effect_name_primary_context_vs_base",
            not _scan_forbidden(
                {"effects": ["primary_context_vs_base"]}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_effect_name_distractor_added_to_primary",
            not _scan_forbidden(
                {"effects": ["distractor_added_to_primary"]}
            ),
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
                    "context_tokens_mean": 24.0,
                    "tool_calls_before_first_edit_mean": 1.0,
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_delta_metric_values",
            not _scan_forbidden(
                {
                    "solve_rate_delta": 1.0,
                    "wrong_file_edits_mean_delta": 1.0,
                    "context_tokens_mean_delta": 16.0,
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_workspace_isolation_token",
            not _scan_forbidden(
                {"workspace_isolation": "fresh_tmp_per_task_variant"}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_theory_mapping_proxy_token",
            not _scan_forbidden(
                {"corresponds_to": "e_utility_smoke_proxy"}
            ),
        )
    )

    # --- Group 14: Fail-closed generation. ---
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
                    "task_id",
                    "workspace_path",
                    "file_path",
                    "target_file",
                    "wrong_cue_file",
                    "support_file",
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
                    "context",
                    "source",
                )
            ),
        )
    )

    # --- Group 16: CLI argument surface. ---
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
    """Build the F1 CLI parser."""
    ap = SafeArgumentParser(
        description=(
            "F1 counterfactual evidence utility smoke (public "
            "aggregate-only artifact; synthetic public micro bug "
            "tasks; six counterfactual context variants; fresh /tmp "
            "workspace per task+variant; real file edits + real "
            "subprocess tests; five marginal utility deltas; no live "
            "LLM, no provider calls; no raw event logs/patches/test "
            "output/per-run rows committed; not true E/S calibration)."
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
