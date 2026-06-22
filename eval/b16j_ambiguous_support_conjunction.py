#!/usr/bin/env python3
"""B16-J Ambiguous-Support Conjunction Live-Provider Smoke (Public Aggregate-Only).

This module implements the **B16-J ambiguous-support conjunction
live-provider downstream smoke**. It is the LAST B16 atom-redesign
attempt. B16-J constructs ambiguous-support tasks where support-only
cannot identify the target binding by construction: each task has
multiple safe plausible target files/symbols, and the same abstract
support rule applies plausibly to multiple candidates.

B16-J has FIVE fixed arms:

1. ``control_sparse`` — task issue only, minimal context; no atoms.
2. ``ambiguous_target_only`` — target file cue + target symbol cue;
   no support module, no support rule. Gives binding but omits rule/value.
3. ``ambiguous_support_only`` — support module cue + ambiguous support
   rule (same abstract rule applies to multiple candidates); no target
   file cue, no symbol cue. The support text must NOT contain target
   filename, target symbol, unique target noun, exact final answer,
   exact edit instruction, or test path/name.
4. ``ambiguous_distractor_plus_support`` — distractor file cue +
   support module cue + ambiguous support rule; no target file;
   plausible wrong binding plus rule.
5. ``ambiguous_target_plus_support`` — target file cue + target
   symbol cue + support module cue + ambiguous support rule. Gives
   both binding and rule.

Primary contrasts:

* ``ambiguous_target_plus_support`` vs ``ambiguous_support_only``
* ``ambiguous_target_plus_support`` vs ``ambiguous_target_only``
* ``ambiguous_target_plus_support`` vs
  ``ambiguous_distractor_plus_support``

File choice remains open across the per-task safe file set (target
module + distractor module + support module). The chosen file is
recorded ONLY in private SCORE/event JSONL under ``/tmp``. Only
aggregate file-choice rates are exposed publicly.

B16-J is explicitly **not** a downstream agent value proof, **not** a
live-agent generalization proof, **not** an external benchmark result,
**not** a production coding-agent benchmark, **not** a real user task
evaluation, **not** a method winner/default/promotion claim, **not** a
calibration claim, **not** a BEA superiority claim, and **not** a
runtime/retriever/pack/backend/default-policy/EvidenceCore semantic
change.

Claim boundary (binding):

* Claim level: ``ambiguous_support_conjunction_downstream_smoke_only``.
* Status enum: ``ambiguous_support_conjunction_smoke_pass`` on live
  success; ``blocked_remote_not_enabled`` /
  ``unavailable_no_local_provider_env`` when remote opt-in not
  satisfied; ``provider_call_failed`` / ``structured_action_parse_failed``
  / ``paired_run_failed`` / ``fail_forbidden_scan`` on failures.
* Mode: ``public_aggregate_synthetic_task_family_matrix``; phase ``B16-J``.

Run::

    python3 -m py_compile eval/b16j_ambiguous_support_conjunction.py
    python3 eval/b16j_ambiguous_support_conjunction.py --self-test
    python3 eval/b16j_ambiguous_support_conjunction.py \\
        --out artifacts/b16j_ambiguous_support_conjunction/\\
b16j_ambiguous_support_conjunction_report.json
"""

from __future__ import annotations

import argparse
import hashlib
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import provider_client  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "b16j_ambiguous_support_conjunction.v1"
GENERATED_BY = "eval/b16j_ambiguous_support_conjunction.py"
CLAIM_LEVEL = "ambiguous_support_conjunction_downstream_smoke_only"
MODE = "public_aggregate_synthetic_task_family_matrix"
PHASE = "B16-J"

STATUS_PASS = "ambiguous_support_conjunction_smoke_pass"
STATUS_UNAVAILABLE = "unavailable_no_local_provider_env"
STATUS_BLOCKED_REMOTE = "blocked_remote_not_enabled"
STATUS_PROVIDER_FAILED = "provider_call_failed"
STATUS_PARSE_FAILED = "structured_action_parse_failed"
STATUS_PAIRED_FAILED = "paired_run_failed"
STATUS_FAIL_LEAK = "fail_forbidden_scan"

ALL_STATUSES: frozenset[str] = frozenset(
    {STATUS_PASS, STATUS_UNAVAILABLE, STATUS_BLOCKED_REMOTE,
     STATUS_PROVIDER_FAILED, STATUS_PARSE_FAILED, STATUS_PAIRED_FAILED,
     STATUS_FAIL_LEAK}
)

DEFAULT_OUT = Path(
    "artifacts/b16j_ambiguous_support_conjunction/"
    "b16j_ambiguous_support_conjunction_report.json"
)
DEFAULT_TASK_COUNT = 8
MIN_TASK_COUNT = 4
MAX_TASK_COUNT = 12
MAX_LIVE_CALLS = MAX_TASK_COUNT * 5

ARMS: tuple[str, ...] = (
    "control_sparse",
    "ambiguous_target_only",
    "ambiguous_support_only",
    "ambiguous_distractor_plus_support",
    "ambiguous_target_plus_support",
)
ARM_CONTROL = "control_sparse"
ARM_TARGET_ONLY = "ambiguous_target_only"
ARM_SUPPORT_ONLY = "ambiguous_support_only"
ARM_DISTRACTOR_PLUS_SUPPORT = "ambiguous_distractor_plus_support"
ARM_TARGET_PLUS_SUPPORT = "ambiguous_target_plus_support"

PRIMARY_CONTRASTS: tuple[tuple[str, str], ...] = (
    (ARM_SUPPORT_ONLY, ARM_TARGET_PLUS_SUPPORT),
    (ARM_TARGET_ONLY, ARM_TARGET_PLUS_SUPPORT),
    (ARM_DISTRACTOR_PLUS_SUPPORT, ARM_TARGET_PLUS_SUPPORT),
)
SECONDARY_CONTRASTS: tuple[tuple[str, str], ...] = (
    (ARM_SUPPORT_ONLY, ARM_TARGET_ONLY),
) + tuple(
    (ARM_CONTROL, arm)
    for arm in (ARM_TARGET_ONLY, ARM_SUPPORT_ONLY, ARM_DISTRACTOR_PLUS_SUPPORT, ARM_TARGET_PLUS_SUPPORT)
)
ALL_CONTRASTS: tuple[tuple[str, str], ...] = PRIMARY_CONTRASTS + SECONDARY_CONTRASTS

TASK_FAMILIES: tuple[str, ...] = (
    "same_symbol_support_relation",
    "operation_ambiguity",
    "boundary_condition",
    "helper_dependency_choice",
    "config_or_test_mismatch",
    "distractor_file",
    "nearby_wrong_function",
    "cross_file_symbol",
)

METRIC_NAMES: tuple[str, ...] = (
    "run_count", "solve_rate", "tests_pass_rate", "patch_apply_rate",
    "correct_file_before_first_edit_rate", "wrong_file_edit_rate",
    "selected_target_file_rate", "selected_distractor_file_rate",
    "selected_support_file_rate", "no_op_rate", "invalid_json_rate",
    "provider_failure_rate", "context_tokens_mean",
    "prompt_tokens_total", "completion_tokens_total",
    "latency_seconds_mean", "cost_proxy_total",
)
DELTA_METRIC_NAMES: tuple[str, ...] = tuple(
    n for n in METRIC_NAMES if n != "run_count"
)

ALLOWED_EDIT_ACTIONS: frozenset[str] = frozenset(
    {"replace_return_value", "choose_helper_constant", "no_op"}
)

PRIVATE_SCORE_SCHEMA_VERSION = "b16j_private_score.v1"
PRIVATE_EVENT_SCHEMA_VERSION = "b16j_private_event.v1"

LIVE_TRUE_FLAGS: tuple[str, ...] = (
    "downstream_agent_runs_performed", "live_llm_agent",
    "provider_calls_made", "remote_provider_calls_made",
    "paired_run_executed", "synthetic_task_family_matrix_used",
    "real_file_edits_performed", "real_test_commands_executed",
    "agent_behavior_metrics_evaluated",
    "ambiguous_support_conjunction_executed",
    "private_score_records_written", "private_event_records_written",
    "aggregate_only_public_artifact", "diagnostic_only",
)

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
    "method_winner_claimed": False,
    "calibration_claimed": False,
    "bea_superiority_claimed": False,
}

# ---------------------------------------------------------------------------
# Scanner (strict, fail-closed). Adds ambiguous-support-private keys.
# ---------------------------------------------------------------------------

FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset(
    {
        "prompt", "prompts", "message", "messages", "response",
        "responses", "raw_response", "request", "request_body",
        "provider_payload", "raw_payload", "api_response",
        "response_body", "model_response", "model_output",
        "parsed_action", "parsed_response",
        "url", "base_url", "endpoint", "api_key", "api_token",
        "api_secret", "token", "secret", "authorization", "bearer",
        "provider_key", "provider_url", "provider_base_url",
        "credential", "password",
        "workspace", "workspace_path", "workspace_dir", "tmp_dir",
        "tmp_path", "path", "span", "line_range", "start_line",
        "end_line", "start_byte", "end_byte", "line_ranges", "spans",
        "file", "files", "filename", "filepath", "target_file",
        "wrong_file", "target_module", "distractor_module",
        "support_module", "boundary_module", "helper_module",
        "config_module", "cross_file_module", "test_module",
        "source_path", "module_path", "module",
        "chosen_file", "selected_file", "file_choice",
        "chosen_symbol", "selected_symbol",
        "support_rule_text", "exact_answer", "support_rule",
        "ambiguous_support_rule", "ambiguous_rule_text",
        "content", "content_sha", "content_hash", "hash", "digest",
        "sha256", "md5", "sha1",
        "snippet", "snippets", "excerpt", "excerpts",
        "code", "source_code", "code_snippet", "body", "text", "source",
        "task_id", "task_index", "repo_id", "repo", "instance_id",
        "row_id", "record_id", "id", "name", "run_id",
        "model_id_raw", "model_id",
        "packet_ref", "packet_id", "private_record_ref",
        "candidate_ref", "candidate_id", "candidate",
        "label", "labels", "qrels", "gold", "gold_label",
        "gold_labels", "hard_negative", "hard_negatives",
        "patch", "diff", "test_patch", "tests", "test_output",
        "test_log", "test_stdout", "test_stderr", "stdout", "stderr",
        "returncode", "exit_code",
        "event_log", "events", "log", "trace", "raw_event", "raw_log",
        "stack_trace", "traceback", "error_message", "error",
        "raw_rows", "rows", "records", "runs", "per_run", "raw",
        "raw_data", "predictions", "candidates",
        "atom_composition", "atoms", "atom_set", "selected_atoms",
        "atom_trace", "action_trace", "action_order",
        "priority_components", "priority_score",
        "selected_decisions", "budget_trace", "stop_reason",
        "candidate_features", "anchor_eligibility",
        "anchor_slots", "early_stop_reason",
        "private_score_path", "score_path", "private_score_file",
        "private_event_path", "event_path", "private_event_file",
        "private_record_id", "private_record_hash",
        "action_steps_trace", "budget_state", "budget_states",
        "selected_candidates", "candidates_selected",
        "accepted_candidates", "final_candidates",
        "candidate_list", "score_outcome",
        "per_record_metrics", "runtime_query_features",
        "query_feature_summary", "query_features",
        "benchmark_row_id", "benchmark_record_id", "benchmark_label",
        "phase_run_id", "provider_metadata",
        "agreement_metric", "agreement_value", "agreement_score",
        "kappa", "fleiss_kappa", "cohen_kappa", "agreement",
        "confidence_interval", "ci_value", "ci_lower", "ci_upper",
        "ci_low", "ci_high",
    }
)

SAFE_VALUE_KEY_NAMES: frozenset[str] = frozenset(
    {"schema_version", "generated_by", "generated_at", "claim_level",
     "status", "mode", "phase", "arm", "baseline_arm", "treatment_arm",
     "metric", "task_family", "model_display_category",
     "storage_class", "manifest_hash", "mechanism_field"}
)

_RE_URL_VALUE = re.compile(r"https?://", re.IGNORECASE)
_RE_HEX_DIGEST = re.compile(r"[A-Fa-f0-9]{32,}")
_RE_SECRET_LIKE = re.compile(
    r"(?:api[_-]?key|api[_-]?token|api[_-]?secret|base[_-]?url"
    r"|provider[_-]?key|provider[_-]?url|authorization[_-]?bearer"
    r"|secret|password|credential)", re.IGNORECASE)
_FILE_EXT = (r"py|rs|ts|tsx|js|jsx|go|java|c|cpp|cc|h|hpp|hh|md|json|"
    r"toml|yaml|yml|txt|sh|rb|php|kt|swift|patch|diff|csv|parquet|jsonl")
_RE_FILE_PATH_VALUE = re.compile(rf"\b[A-Za-z0-9._/\-]+\.(?:{_FILE_EXT})\b")
_RE_LINE_RANGE_VALUE = re.compile(r"\b\d+\s*[:\-]\s*\d+\b")
_RE_RAW_JSON = re.compile(r'^\s*[\{\[]\s*"[^"]+"\s*:')
_RE_TMP_PATH_VALUE = re.compile(r"/tmp/")
_RE_TASK_ID_VALUE = re.compile(r"\btask[_\-\s]*\d+\b", re.IGNORECASE)
_RE_PATCH_MARKER = re.compile(r"^(---|\+\+\+|@@\s)", re.MULTILINE)
_RE_STACK_TRACE = re.compile(r"Traceback\s*\(most\s+recent\s+call\s+last\)", re.IGNORECASE)
_RE_RAW_MODEL_PREFIX = re.compile(r"\[mk\]", re.IGNORECASE)

_SECRET_SENTINEL = "SECRET_VALIDATOR_SENTINEL"
_ROUTING_PREFIX_SENTINEL = "[" + "m" + "k]"
_REMOTE_ENV_KEYS = (provider_client.ENV_BASE_URL, provider_client.ENV_API_KEY,
    provider_client.ENV_MODEL, provider_client.ENV_ALLOW_REMOTE,
    provider_client.ENV_WORKFLOW_DISPATCH)


def _path_last_key(path: str) -> str:
    return path.rsplit(".", 1)[-1].split("[")[0]

def _is_safe_value_path(path: str) -> bool:
    return _path_last_key(path) in SAFE_VALUE_KEY_NAMES

def _scan_forbidden(obj: Any, path: str = "$") -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            sub = f"{path}.{key}"
            if str(key) in FORBIDDEN_KEY_NAMES:
                violations.append({"category": "forbidden_key", "path": sub})
            violations.extend(_scan_forbidden(value, sub))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_scan_forbidden(value, f"{path}[{idx}]"))
    elif isinstance(obj, str):
        sv = _is_safe_value_path(path)
        if obj in FORBIDDEN_KEY_NAMES:
            violations.append({"category": "forbidden_field_name_value", "path": path})
        elif len(obj) > 256:
            violations.append({"category": "long_string", "path": path})
        elif _RE_URL_VALUE.search(obj) and not sv:
            violations.append({"category": "url_value", "path": path})
        elif not sv and _RE_HEX_DIGEST.search(obj):
            violations.append({"category": "hex_digest_value", "path": path})
        elif _RE_SECRET_LIKE.search(obj) and not sv:
            violations.append({"category": "secret_like_value", "path": path})
        elif not sv and _RE_FILE_PATH_VALUE.search(obj):
            violations.append({"category": "path_like_value", "path": path})
        elif "\n" in obj:
            violations.append({"category": "multiline_value", "path": path})
        elif _RE_RAW_JSON.search(obj):
            violations.append({"category": "raw_json_fragment", "path": path})
        elif not sv and _RE_TMP_PATH_VALUE.search(obj):
            violations.append({"category": "tmp_path_value", "path": path})
        elif not sv and _RE_TASK_ID_VALUE.search(obj):
            violations.append({"category": "task_identifier_value", "path": path})
        elif _RE_PATCH_MARKER.search(obj):
            violations.append({"category": "patch_marker_value", "path": path})
        elif _RE_STACK_TRACE.search(obj):
            violations.append({"category": "stack_trace_value", "path": path})
        elif _RE_RAW_MODEL_PREFIX.search(obj):
            violations.append({"category": "raw_model_prefix_value", "path": path})
        elif _SECRET_SENTINEL in obj:
            violations.append({"category": "sentinel_value", "path": path})
        else:
            s = obj.strip()
            if 3 <= len(s) <= 16 and _RE_LINE_RANGE_VALUE.fullmatch(s) and not s.replace(" ", "").isdigit():
                violations.append({"category": "line_range_value", "path": path})
    return violations

def _forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    v = _scan_forbidden(obj)
    c: dict[str, int] = {}
    for x in v:
        c[x["category"]] = c.get(x["category"], 0) + 1
    return {"status": "pass" if not v else "fail", "violations_count": len(v), "categories": c}

def _enforce_no_forbidden(obj: Any) -> None:
    if _forbidden_scan_summary(obj)["status"] != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")

def _refuse_on_self_test_failure(report: dict[str, Any]) -> None:
    if report.get("self_test_passed") is not True:
        raise SystemExit("self-test failed; refusing to write artifact")

def _has_dict_key_anywhere(obj: Any, key: str) -> bool:
    if isinstance(obj, dict):
        if key in obj: return True
        for v in obj.values():
            if _has_dict_key_anywhere(v, key): return True
    elif isinstance(obj, list):
        for v in obj:
            if _has_dict_key_anywhere(v, key): return True
    return False

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return {"check": name, "passed": bool(ok)}

def _resolve_private_dir(explicit: str | None, prefix: str) -> tuple[Path, str]:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        try:
            p.relative_to("/tmp"); sc = "tmp_private"
        except ValueError:
            rr = Path(__file__).resolve().parent.parent
            try:
                p.relative_to(rr / "runs"); sc = "ignored_private"
            except ValueError:
                raise SystemExit("invalid arguments")
        p.mkdir(parents=True, exist_ok=True)
        return p, sc
    p = Path("/tmp") / f"{prefix}_{os.getpid()}_{int(time.time())}"
    p.mkdir(parents=True, exist_ok=True)
    return p, "tmp_private"

def _private_score_manifest_hash() -> str:
    ms = {"schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
          "fields": ["phase_run_id", "arm", "task_family",
                      "atom_composition", "chosen_file", "chosen_symbol",
                      "score_outcome", "latency_ms", "cost_usd", "tokens",
                      "provider_calls", "failure_reason"]}
    return hashlib.sha256(json.dumps(ms, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

def _private_event_manifest_hash() -> str:
    ms = {"schema_version": PRIVATE_EVENT_SCHEMA_VERSION,
          "fields": ["phase_run_id", "arm", "task_family",
                      "prompt", "response", "parsed_action",
                      "chosen_file", "chosen_symbol", "patch",
                      "test_stdout", "test_stderr", "test_returncode",
                      "provider_metadata", "failure_reason"]}
    return hashlib.sha256(json.dumps(ms, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

def _write_private_row(p: Path, row: dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")

# ---------------------------------------------------------------------------
# Ambiguous-support task families. KEY DIFFERENCE from B16-I:
# Each task has MULTIPLE plausible target files/symbols. The same abstract
# support rule applies plausibly to multiple candidates. The support-only
# text gives the rule but NOT the target-role filename, target symbol, unique
# target noun, exact final answer, exact edit instruction, or test path/name.
# Support-only is intended to withhold target binding at the full-prompt level.
#
# Design: each task has two role-neutral candidate files, BOTH containing the
# same symbol name. The support module defines a constant. The support rule says
# "the correct value is derived from the helper constant" but does NOT say which
# file/symbol to edit. The agent must receive the target binding (from
# target_only or target_plus_support) to know WHICH file to edit. Support-only
# gives the rule but both role-neutral candidate files are plausible edit sites.
#
# Additionally, the support rule uses GENERIC wording (no target-role filename,
# no target symbol, no unique noun). E.g. "the return value of the function
# should be derived as helper * 2 + offset" — this applies to both candidate
# files equally.
# ---------------------------------------------------------------------------


def _opaque_candidate_modules(index: int) -> tuple[str, str]:
    """Return (target_role_file, distractor_role_file) with role-neutral names."""
    if index % 2 == 0:
        return "candidate_a.py", "candidate_b.py"
    return "candidate_b.py", "candidate_a.py"


def _family_same_symbol_support_relation(i: int) -> dict[str, Any]:
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
    base_value = 20 + i * 5
    correct_value = base_value * 2
    buggy_value = base_value + 1
    return {
        "task_family": "operation_ambiguity", "symbol": f"compute_{i:03d}",
        "target_module": "target.py", "distractor_module": "distractor.py",
        "support_module": "support.py", "test_module": "test_target.py",
        "helper_constant_name": f"VAL_{i:03d}",
        "helper_constant_value": base_value,
        "correct_value": correct_value, "buggy_value": buggy_value,
        "fix_kind": "replace_return_value", "decisive_cue": "operation_hint",
    }


def _family_boundary_condition(i: int) -> dict[str, Any]:
    limit_value = 50 + i * 3
    correct_value = limit_value - 1
    buggy_value = limit_value
    return {
        "task_family": "boundary_condition", "symbol": f"clamp_{i:03d}",
        "target_module": "target.py", "distractor_module": "distractor.py",
        "support_module": "support.py", "test_module": "test_target.py",
        "helper_constant_name": f"LIMIT_{i:03d}",
        "helper_constant_value": limit_value,
        "correct_value": correct_value, "buggy_value": buggy_value,
        "fix_kind": "replace_return_value", "decisive_cue": "boundary_hint",
    }


def _family_helper_dependency_choice(i: int) -> dict[str, Any]:
    helper_a = 5 + i
    helper_b = 8 + i * 2
    correct_value = helper_b * 3
    buggy_value = helper_a * 2
    return {
        "task_family": "helper_dependency_choice", "symbol": f"select_{i:03d}",
        "target_module": "target.py", "distractor_module": "distractor.py",
        "support_module": "support.py", "test_module": "test_target.py",
        "helper_constant_name": f"HELPER_B_{i:03d}",
        "helper_constant_value": helper_b,
        "helper_constant_name_alt": f"HELPER_A_{i:03d}",
        "helper_constant_value_alt": helper_a,
        "correct_value": correct_value, "buggy_value": buggy_value,
        "fix_kind": "replace_return_value", "decisive_cue": "helper_choice_hint",
    }


def _family_config_or_test_mismatch(i: int) -> dict[str, Any]:
    config_value = 100 + i * 4
    correct_value = config_value
    buggy_value = config_value + 10
    return {
        "task_family": "config_or_test_mismatch", "symbol": f"load_config_{i:03d}",
        "target_module": "target.py", "distractor_module": "distractor.py",
        "support_module": "config.py", "test_module": "test_target.py",
        "helper_constant_name": f"CONFIG_{i:03d}",
        "helper_constant_value": config_value,
        "correct_value": correct_value, "buggy_value": buggy_value,
        "fix_kind": "replace_return_value", "decisive_cue": "config_source_hint",
    }


def _family_distractor_file(i: int) -> dict[str, Any]:
    base_value = 30 + i * 6
    correct_value = base_value + 5
    buggy_value = -base_value
    return {
        "task_family": "distractor_file", "symbol": f"fetch_{i:03d}",
        "target_module": "target.py", "distractor_module": "distractor.py",
        "support_module": "support.py", "test_module": "test_target.py",
        "helper_constant_name": f"SRC_{i:03d}",
        "helper_constant_value": base_value,
        "correct_value": correct_value, "buggy_value": buggy_value,
        "fix_kind": "replace_return_value", "decisive_cue": "target_file_hint",
    }


def _family_nearby_wrong_function(i: int) -> dict[str, Any]:
    base_value = 40 + i * 3
    correct_value = base_value * 2
    buggy_value = base_value
    return {
        "task_family": "nearby_wrong_function", "symbol": f"process_{i:03d}",
        "target_module": "target.py", "distractor_module": "distractor.py",
        "support_module": "support.py", "test_module": "test_target.py",
        "helper_constant_name": f"PROC_{i:03d}",
        "helper_constant_value": base_value,
        "correct_value": correct_value, "buggy_value": buggy_value,
        "fix_kind": "replace_return_value", "decisive_cue": "symbol_cue_hint",
    }


def _family_cross_file_symbol(i: int) -> dict[str, Any]:
    cross_value = 70 + i * 5
    correct_value = cross_value + 1
    buggy_value = cross_value - 1
    return {
        "task_family": "cross_file_symbol", "symbol": f"lookup_{i:03d}",
        "target_module": "target.py", "distractor_module": "distractor.py",
        "support_module": "cross_file.py", "test_module": "test_target.py",
        "helper_constant_name": f"CROSS_{i:03d}",
        "helper_constant_value": cross_value,
        "correct_value": correct_value, "buggy_value": buggy_value,
        "fix_kind": "replace_return_value", "decisive_cue": "cross_file_source_hint",
    }


_FAMILY_GENERATORS = (
    _family_same_symbol_support_relation, _family_operation_ambiguity,
    _family_boundary_condition, _family_helper_dependency_choice,
    _family_config_or_test_mismatch, _family_distractor_file,
    _family_nearby_wrong_function, _family_cross_file_symbol,
)


def _generate_synthetic_tasks(count: int) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for i in range(count):
        t = _FAMILY_GENERATORS[i % len(_FAMILY_GENERATORS)](i)
        t["index"] = i
        target_module, distractor_module = _opaque_candidate_modules(i)
        t["target_module"] = target_module
        t["distractor_module"] = distractor_module
        tasks.append(t)
    return tasks


def _build_workspace(workspace_dir: Path, task: dict[str, Any]) -> None:
    workspace_dir.mkdir(parents=True, exist_ok=True)
    pyc = workspace_dir / "__pycache__"
    if pyc.is_dir():
        shutil.rmtree(pyc, ignore_errors=True)
    tp = workspace_dir / task["target_module"]
    dp = workspace_dir / task["distractor_module"]
    sp = workspace_dir / task["support_module"]
    testp = workspace_dir / task["test_module"]
    fam = task["task_family"]
    if fam == "helper_dependency_choice":
        sp.write_text(f"{task['helper_constant_name_alt']} = {task['helper_constant_value_alt']}\n{task['helper_constant_name']} = {task['helper_constant_value']}\n", encoding="utf-8")
    else:
        sp.write_text(f"{task['helper_constant_name']} = {task['helper_constant_value']}\n", encoding="utf-8")
    # BOTH target and distractor have the SAME symbol (ambiguous binding).
    tp.write_text(f"def {task['symbol']}():\n    return {task['buggy_value']}\n", encoding="utf-8")
    dp.write_text(f"def {task['symbol']}():\n    return {task['buggy_value']}\n", encoding="utf-8")
    if fam == "same_symbol_support_relation":
        tb = f"    expected = {task['helper_constant_name']} * 2 + {task['index']}\n"
    elif fam == "operation_ambiguity":
        tb = f"    expected = {task['helper_constant_name']} * 2\n"
    elif fam == "boundary_condition":
        tb = f"    expected = {task['helper_constant_name']} - 1\n"
    elif fam == "helper_dependency_choice":
        tb = f"    expected = {task['helper_constant_name']} * 3\n"
    elif fam == "config_or_test_mismatch":
        tb = f"    expected = {task['helper_constant_name']}\n"
    elif fam == "distractor_file":
        tb = f"    expected = {task['helper_constant_name']} + 5\n"
    elif fam == "nearby_wrong_function":
        tb = f"    expected = {task['helper_constant_name']} * 2\n"
    elif fam == "cross_file_symbol":
        tb = f"    expected = {task['helper_constant_name']} + 1\n"
    else:
        tb = f"    expected = {task['correct_value']}\n"
    tmn = task["target_module"].removesuffix(".py")
    smn = task["support_module"].removesuffix(".py")
    testp.write_text(
        "import sys\n"
        f"sys.path.insert(0, r'{workspace_dir}')\n"
        f"from {tmn} import {task['symbol']}\n"
        f"from {smn} import {task['helper_constant_name']}\n"
        "def main():\n"
        f"{tb}"
        f"    assert {task['symbol']}() == expected, 'bug not fixed'\n"
        "    return 0\n"
        "if __name__ == '__main__':\n"
        "    sys.exit(main())\n", encoding="utf-8")

# ---------------------------------------------------------------------------
# File-choice-safe edit file set (per-task, no global ALLOWED_EDIT_FILES).
# ---------------------------------------------------------------------------

def _safe_edit_files(task: dict[str, Any]) -> frozenset[str]:
    return frozenset({task["target_module"], task["distractor_module"], task["support_module"]})

# ---------------------------------------------------------------------------
# Pack builder. Five arms with ambiguous-support atoms.
# ---------------------------------------------------------------------------

def _build_pack(arm: str) -> dict[str, Any]:
    if arm == ARM_CONTROL:
        return {"arm": arm, "candidate_count": 0, "context_tokens": 20,
                "has_target_file_cue": False, "has_target_symbol_cue": False,
                "has_support_module_cue": False, "has_ambiguous_support_rule": False,
                "has_distractor_file_cue": False, "has_edit_constraint": False}
    if arm == ARM_TARGET_ONLY:
        return {"arm": arm, "candidate_count": 1, "context_tokens": 48,
                "has_target_file_cue": True, "has_target_symbol_cue": True,
                "has_support_module_cue": False, "has_ambiguous_support_rule": False,
                "has_distractor_file_cue": False, "has_edit_constraint": True}
    if arm == ARM_SUPPORT_ONLY:
        return {"arm": arm, "candidate_count": 1, "context_tokens": 48,
                "has_target_file_cue": False, "has_target_symbol_cue": False,
                "has_support_module_cue": True, "has_ambiguous_support_rule": True,
                "has_distractor_file_cue": False, "has_edit_constraint": True}
    if arm == ARM_DISTRACTOR_PLUS_SUPPORT:
        return {"arm": arm, "candidate_count": 2, "context_tokens": 64,
                "has_target_file_cue": False, "has_target_symbol_cue": False,
                "has_support_module_cue": True, "has_ambiguous_support_rule": True,
                "has_distractor_file_cue": True, "has_edit_constraint": True}
    if arm == ARM_TARGET_PLUS_SUPPORT:
        return {"arm": arm, "candidate_count": 2, "context_tokens": 64,
                "has_target_file_cue": True, "has_target_symbol_cue": True,
                "has_support_module_cue": True, "has_ambiguous_support_rule": True,
                "has_distractor_file_cue": False, "has_edit_constraint": True}
    return {"arm": arm, "candidate_count": 0, "context_tokens": 20,
            "has_target_file_cue": False, "has_target_symbol_cue": False,
            "has_support_module_cue": False, "has_ambiguous_support_rule": False,
            "has_distractor_file_cue": False, "has_edit_constraint": False}

def _build_atom_composition(arm: str) -> list[str]:
    if arm == ARM_CONTROL: return []
    if arm == ARM_TARGET_ONLY: return ["target_file_cue", "target_symbol_cue"]
    if arm == ARM_SUPPORT_ONLY: return ["support_module_cue", "ambiguous_support_rule"]
    if arm == ARM_DISTRACTOR_PLUS_SUPPORT: return ["distractor_file_cue", "support_module_cue", "ambiguous_support_rule"]
    if arm == ARM_TARGET_PLUS_SUPPORT: return ["target_file_cue", "target_symbol_cue", "support_module_cue", "ambiguous_support_rule"]
    return []

# ---------------------------------------------------------------------------
# Ambiguous support rule text (private, in-memory only).
#
# KEY DESIGN: the support rule uses GENERIC wording. It does NOT contain:
# - target-role filename
# - target symbol (e.g. "resolve_001")
# - unique target noun
# - exact final answer (e.g. "Correct value: 42")
# - exact edit instruction
# - test path/name
#
# The rule applies plausibly to both role-neutral candidate files because both
# contain the same symbol. Support-only is designed to withhold target binding.
# ---------------------------------------------------------------------------

def _ambiguous_support_cue_text(task: dict[str, Any]) -> str:
    """Ambiguous support rule text (private, in-memory only).

    The rule does NOT contain target filename, target symbol, unique noun,
    exact answer, exact edit instruction, or test path/name. It applies
    plausibly to multiple candidate files.
    """
    fam = task["task_family"]
    if fam == "same_symbol_support_relation":
        return (
            "Support invariant: the correct return value of the function "
            "should be helper_constant * 2 + task_index. The helper constant "
            f"is {task['helper_constant_name']} = {task['helper_constant_value']}. "
            "Multiple candidate files contain a function with this name; "
            "you must determine which file is the correct edit site."
        )
    if fam == "operation_ambiguity":
        return (
            "Support rule: the correct operation is multiplication by 2 "
            "(not increment by 1). The base value is "
            f"{task['helper_constant_name']} = {task['helper_constant_value']}. "
            "Multiple candidate files contain a function with this name; "
            "you must determine which file is the correct edit site."
        )
    if fam == "boundary_condition":
        return (
            "Support rule: the limit is an exclusive upper bound; the correct "
            "value is limit - 1. The limit is "
            f"{task['helper_constant_name']} = {task['helper_constant_value']}. "
            "Multiple candidate files contain a function with this name; "
            "you must determine which file is the correct edit site."
        )
    if fam == "helper_dependency_choice":
        return (
            "Support relation: the correct helper is "
            f"{task['helper_constant_name']} (value {task['helper_constant_value']}) "
            f"not {task['helper_constant_name_alt']} (value "
            f"{task['helper_constant_value_alt']}). The correct value is "
            f"{task['helper_constant_name']} * 3. Multiple candidate files "
            "contain a function with this name; you must determine which "
            "file is the correct edit site."
        )
    if fam == "config_or_test_mismatch":
        return (
            "Support rule: the correct value comes from the config source "
            f"where {task['helper_constant_name']} = {task['helper_constant_value']}. "
            "Multiple candidate files contain a function with this name; "
            "you must determine which file should return this value."
        )
    if fam == "distractor_file":
        return (
            "Support relation: the correct return value is "
            f"{task['helper_constant_name']} + 5, where "
            f"{task['helper_constant_name']} = {task['helper_constant_value']}. "
            "Multiple candidate files contain a function with the same name; "
            "you must determine which file is the correct "
            "edit site."
        )
    if fam == "nearby_wrong_function":
        return (
            "Support rule: the correct return value is "
            f"{task['helper_constant_name']} * 2, where "
            f"{task['helper_constant_name']} = {task['helper_constant_value']}. "
            "Multiple candidate files contain a function with this name; "
            "you must determine which file is the correct edit site."
        )
    if fam == "cross_file_symbol":
        return (
            "Support relation: the correct return value is "
            f"{task['helper_constant_name']} + 1, where the helper lives in "
            f"a cross-file module ({task['helper_constant_name']} = "
            f"{task['helper_constant_value']}). Multiple candidate files "
            "contain a function with this name; you must determine which "
            "file is the correct edit site."
        )
    return ""


def _decisive_cue_text(task: dict[str, Any]) -> str:
    """Full decisive cue text (private, in-memory only).

    Used ONLY for the target_plus_support arm. Gives the target binding
    plus the support rule.
    """
    fam = task["task_family"]
    if fam == "same_symbol_support_relation":
        return (f"Target binding: edit {task['target_module']}, function {task['symbol']}. "
                f"Support invariant: correct_value = {task['helper_constant_name']} * 2 + {task['index']}. "
                f"Helper {task['helper_constant_name']} = {task['helper_constant_value']}. "
                f"Correct value: {task['correct_value']}.")
    if fam == "operation_ambiguity":
        return (f"Target binding: edit {task['target_module']}, function {task['symbol']}. "
                f"Support rule: multiply base by 2. Base {task['helper_constant_name']} = {task['helper_constant_value']}. "
                f"Correct value: {task['correct_value']}.")
    if fam == "boundary_condition":
        return (f"Target binding: edit {task['target_module']}, function {task['symbol']}. "
                f"Support rule: exclusive upper bound; correct = limit - 1. "
                f"Limit {task['helper_constant_name']} = {task['helper_constant_value']}. "
                f"Correct value: {task['correct_value']}.")
    if fam == "helper_dependency_choice":
        return (f"Target binding: edit {task['target_module']}, function {task['symbol']}. "
                f"Support relation: use {task['helper_constant_name']} (value {task['helper_constant_value']}) "
                f"not {task['helper_constant_name_alt']}. Correct value = "
                f"{task['helper_constant_name']} * 3 = {task['correct_value']}.")
    if fam == "config_or_test_mismatch":
        return (f"Target binding: edit {task['target_module']}, function {task['symbol']}. "
                f"Support rule: correct value from config source {task['support_module']} "
                f"({task['helper_constant_name']} = {task['helper_constant_value']}). "
                f"Correct value: {task['correct_value']}.")
    if fam == "distractor_file":
        return (f"Target binding: edit {task['target_module']} (not {task['distractor_module']}), "
                f"function {task['symbol']}. Support relation: correct = "
                f"{task['helper_constant_name']} + 5 = {task['correct_value']}.")
    if fam == "nearby_wrong_function":
        return (f"Target binding: edit {task['target_module']}, function {task['symbol']}. "
                f"Support rule: correct = {task['helper_constant_name']} * 2 = {task['correct_value']}.")
    if fam == "cross_file_symbol":
        return (f"Target binding: edit {task['target_module']}, function {task['symbol']}. "
                f"Support relation: helper in cross-file module {task['support_module']} "
                f"({task['helper_constant_name']} = {task['helper_constant_value']}). "
                f"Correct = {task['helper_constant_name']} + 1 = {task['correct_value']}.")
    return ""


def _build_messages(workspace_dir: Path, task: dict[str, Any], pack: dict[str, Any]) -> list[dict[str, str]]:
    tp = workspace_dir / task["target_module"]
    dp = workspace_dir / task["distractor_module"]
    sp = workspace_dir / task["support_module"]
    ts = tp.read_text(encoding="utf-8")
    ss = sp.read_text(encoding="utf-8")
    ds = dp.read_text(encoding="utf-8")
    sf = sorted(_safe_edit_files(task))
    sfs = ", ".join(sf)
    system = ("You are a minimal coding-agent smoke. "
              "Respond with a single JSON object matching the schema: "
              '{"action": "replace_return_value" | "choose_helper_constant" | "no_op", '
              '"file": "<one of the allowed files>", '
              '"symbol": "<symbol>", '
              '"new_return_value": <int>}. '
              f"The allowed files for this task are: {sfs}. "
              "You must choose which file to edit. Do not include any other text.")
    ul = [f"Bug: function {task['symbol']} returns the wrong value.",
          f"Allowed files you may edit: {sfs}."]
    if pack.get("has_target_file_cue"):
        ul.append(f"Target file: {task['target_module']} (not {task['distractor_module']}).")
    if pack.get("has_target_symbol_cue"):
        ul.append(f"Target symbol: {task['symbol']} in {task['target_module']}.")
    if pack.get("has_ambiguous_support_rule"):
        if pack.get("has_target_file_cue"):
            ul.append(_decisive_cue_text(task))
        else:
            ul.append(_ambiguous_support_cue_text(task))
    if pack.get("has_edit_constraint"):
        ul.append(f"Edit constraint: choose exactly one of {sfs} to edit; no other files are allowed.")
    if pack.get("has_distractor_file_cue"):
        ul.append(f"Candidate source (may be wrong file):\n{ds}")
    if pack.get("has_target_file_cue"):
        ul.append(f"Target source:\n{ts}")
    if pack.get("has_support_module_cue"):
        ul.append(f"Support source:\n{ss}")
    ul.append("Respond with the JSON edit action only.")
    return [{"role": "system", "content": system}, {"role": "user", "content": "\n".join(ul)}]

# ---------------------------------------------------------------------------
# Edit action validation + application (same as B16-I).
# ---------------------------------------------------------------------------

def _validate_edit_action(action: Any, task: dict[str, Any]) -> tuple[bool, str]:
    if not isinstance(action, dict): return False, "top_level_not_object"
    fv = action.get("file")
    if fv not in _safe_edit_files(task): return False, "disallowed_file"
    av = action.get("action")
    if av not in ALLOWED_EDIT_ACTIONS: return False, "disallowed_action"
    sym = action.get("symbol")
    if not isinstance(sym, str) or not sym: return False, "missing_symbol"
    if av in ("replace_return_value", "choose_helper_constant"):
        nv = action.get("new_return_value")
        if not isinstance(nv, int): return False, "missing_or_non_int_new_return_value"
    return True, "ok"

def _categorize_chosen_file(fv: str, task: dict[str, Any]) -> str:
    if fv == task["target_module"]: return "target"
    if fv == task["distractor_module"]: return "distractor"
    if fv == task["support_module"]: return "support"
    return "none"

def _apply_edit_action(wd: Path, task: dict[str, Any], action: dict[str, Any]) -> tuple[bool, str, str | None]:
    fv = action.get("file")
    av = action.get("action")
    if av == "no_op": return False, "no_op", fv
    if fv in _safe_edit_files(task):
        ep = wd / str(fv)
        nv = action.get("new_return_value")
        ep.write_text(f"def {task['symbol']}():\n    return {nv}\n", encoding="utf-8")
        if fv == task["target_module"]: return True, "correct_file", fv
        return False, "wrong_file", fv
    return False, "wrong_file", fv

# ---------------------------------------------------------------------------
# Live LLM agent run (one task + arm) with private SCORE/event writers.
# ---------------------------------------------------------------------------

def _run_live_agent(wd: Path, task: dict[str, Any], pack: dict[str, Any], *, arm: str,
                    allow_remote: bool, require_workflow_dispatch: bool,
                    phase_run_id: str, score_path: Path, event_path: Path,
                    fake_response: dict[str, Any] | None = None,
                    fake_invalid: bool = False) -> dict[str, Any]:
    ps: dict[str, Any] = {"calls_attempted": 0, "calls_succeeded": 0, "calls_failed": 0,
                          "invalid_json_count": 0, "timeout_count": 0,
                          "failure_category_counts": {}, "usage_available": False,
                          "prompt_tokens_total": 0, "completion_tokens_total": 0,
                          "total_tokens_total": 0, "latency_ms_total": 0}
    def _bfc(c: str) -> None:
        ps["failure_category_counts"][c] = ps["failure_category_counts"].get(c, 0) + 1
    pa: dict[str, Any] | None = None
    rrt: str | None = None
    ij = False
    pfr: str | None = None
    pt = 0
    ct = 0
    if fake_invalid:
        ps["calls_attempted"] = 1; ps["calls_succeeded"] = 0; ps["calls_failed"] = 1
        ps["invalid_json_count"] = 1; _bfc(provider_client.FAILURE_CATEGORY_INVALID_JSON)
        ij = True; rrt = "not-valid-json"; lm = 1
    elif fake_response is not None:
        pa = fake_response; ps["calls_attempted"] = 1; ps["calls_succeeded"] = 1
        ps["calls_failed"] = 0; _bfc(provider_client.FAILURE_CATEGORY_OK); lm = 1
    else:
        msgs = _build_messages(wd, task, pack)
        r = provider_client.chat_completion(msgs, allow_remote=allow_remote,
                                            require_workflow_dispatch=require_workflow_dispatch,
                                            temperature=0.0, json_mode=True)
        ps["calls_attempted"] += r.calls_attempted; ps["calls_succeeded"] += r.calls_succeeded
        ps["calls_failed"] += r.calls_failed; ps["latency_ms_total"] += r.latency_ms; lm = r.latency_ms
        _bfc(r.failure_category)
        if r.invalid_json: ps["invalid_json_count"] += 1; ij = True
        if r.failure_category == provider_client.FAILURE_CATEGORY_TIMEOUT: ps["timeout_count"] += 1
        if r.usage_available and isinstance(r.usage, dict):
            ps["usage_available"] = True; pt = int(r.usage.get("prompt_tokens", 0))
            ct = int(r.usage.get("completion_tokens", 0))
            ps["prompt_tokens_total"] += pt; ps["completion_tokens_total"] += ct
            ps["total_tokens_total"] += int(r.usage.get("total_tokens", 0))
        rrt = r.raw_content
        if r.calls_succeeded != 1 or r.parsed is None:
            pa = None
            if r.failure_category != provider_client.FAILURE_CATEGORY_OK: pfr = r.failure_category
        else:
            pa = r.parsed
    tcbfe = 0; cfbfe = False; wfe = 0; pa_flag = False; no_op = False
    cfc = "none"; cfa: str | None = None
    if pa is not None:
        v, _ = _validate_edit_action(pa, task)
        if v:
            tcbfe = 1
            ec, kind, cf = _apply_edit_action(wd, task, pa)
            cfa = cf; cfc = _categorize_chosen_file(cf if cf else "", task)
            if kind == "correct_file": cfbfe = True; pa_flag = True
            elif kind == "wrong_file": wfe += 1; pa_flag = True
            elif kind == "no_op": no_op = True
    tc = [sys.executable, str(wd / task["test_module"])]
    ts = time.perf_counter()
    tso = ""; tse = ""; trc: int | None = None
    try:
        p = subprocess.run(tc, check=False, capture_output=True, text=True, timeout=30)
        tp_flag = p.returncode == 0; tso = p.stdout; tse = p.stderr; trc = p.returncode
    except (subprocess.TimeoutExpired, OSError):
        tp_flag = False; trc = -1
    tlm = max(1, int((time.perf_counter() - ts) * 1000))
    solve = tp_flag and cfbfe
    pf = ps["calls_failed"] > 0
    so = {"solve": solve, "tests_pass": tp_flag, "patch_applied": pa_flag,
          "invalid_json": ij, "no_op": no_op, "provider_failure": pf,
          "correct_file_before_first_edit": cfbfe, "wrong_file_edits": wfe,
          "chosen_file_category": cfc, "context_tokens": pack.get("context_tokens", 0),
          "prompt_tokens": pt, "completion_tokens": ct,
          "latency_ms": lm + tlm, "cost_proxy": 0}
    ac = _build_atom_composition(arm)
    psr = {"phase_run_id": phase_run_id, "arm": arm, "task_family": task["task_family"],
           "atom_composition": ac, "chosen_file": cfa, "chosen_symbol": pa.get("symbol") if pa else None,
           "score_outcome": so, "latency_ms": lm + tlm, "cost_usd": 0.0,
           "tokens": pt + ct, "provider_calls": ps["calls_attempted"], "failure_reason": pfr}
    try: _write_private_row(score_path, psr)
    except OSError: pass
    per = {"phase_run_id": phase_run_id, "arm": arm, "task_family": task["task_family"],
           "prompt": _build_messages(wd, task, pack)[-1]["content"], "response": rrt or "",
           "parsed_action": pa, "chosen_file": cfa, "chosen_symbol": pa.get("symbol") if pa else None,
           "patch": "", "test_stdout": tso, "test_stderr": tse, "test_returncode": trc,
           "provider_metadata": {"calls_attempted": ps["calls_attempted"],
                                 "calls_succeeded": ps["calls_succeeded"],
                                 "calls_failed": ps["calls_failed"],
                                 "invalid_json_count": ps["invalid_json_count"],
                                 "latency_ms": lm, "prompt_tokens": pt,
                                 "completion_tokens": ct,
                                 "failure_category": (list(ps["failure_category_counts"].keys())[-1]
                                                       if ps["failure_category_counts"] else "ok")},
           "failure_reason": pfr}
    try: _write_private_row(event_path, per)
    except OSError: pass
    return {"solve": solve, "tests_pass": tp_flag, "patch_applied": pa_flag,
            "invalid_json": ij, "no_op": no_op, "provider_failure": pf,
            "correct_file_before_first_edit": cfbfe, "wrong_file_edits": wfe,
            "chosen_file_category": cfc, "tool_calls_before_first_edit": tcbfe,
            "context_tokens": pack.get("context_tokens", 0), "prompt_tokens": pt,
            "completion_tokens": ct, "latency_ms": lm + tlm, "cost_proxy": 0,
            "task_family": task["task_family"], "arm": arm, "provider_summary": ps}

# ---------------------------------------------------------------------------
# Aggregate metrics
# ---------------------------------------------------------------------------

def _rate(n: int, d: int) -> float:
    return n / d if d > 0 else 0.0

def _mean(v: list[float]) -> float:
    return sum(v) / len(v) if v else 0.0

def _rm(v: float) -> float:
    return round(float(v), 6)

def _aggregate_arm_metrics(runs: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    n = len(runs)
    m = {"run_count": n,
         "solve_rate": _rm(_rate(sum(1 for r in runs if r["solve"]), n)),
         "tests_pass_rate": _rm(_rate(sum(1 for r in runs if r["tests_pass"]), n)),
         "patch_apply_rate": _rm(_rate(sum(1 for r in runs if r["patch_applied"]), n)),
         "correct_file_before_first_edit_rate": _rm(_rate(sum(1 for r in runs if r["correct_file_before_first_edit"]), n)),
         "wrong_file_edit_rate": _rm(_rate(sum(1 for r in runs if r["wrong_file_edits"] > 0), n)),
         "selected_target_file_rate": _rm(_rate(sum(1 for r in runs if r.get("chosen_file_category") == "target"), n)),
         "selected_distractor_file_rate": _rm(_rate(sum(1 for r in runs if r.get("chosen_file_category") == "distractor"), n)),
         "selected_support_file_rate": _rm(_rate(sum(1 for r in runs if r.get("chosen_file_category") == "support"), n)),
         "no_op_rate": _rm(_rate(sum(1 for r in runs if r["no_op"]), n)),
         "invalid_json_rate": _rm(_rate(sum(1 for r in runs if r["invalid_json"]), n)),
         "provider_failure_rate": _rm(_rate(sum(1 for r in runs if r["provider_failure"]), n)),
         "context_tokens_mean": _rm(_mean([r["context_tokens"] for r in runs])),
         "prompt_tokens_total": int(sum(r["prompt_tokens"] for r in runs)),
         "completion_tokens_total": int(sum(r["completion_tokens"] for r in runs)),
         "latency_seconds_mean": _rm(_mean([r["latency_ms"] for r in runs]) / 1000.0),
         "cost_proxy_total": _rm(sum(r["cost_proxy"] for r in runs))}
    psm: dict[str, Any] = {"calls_attempted": 0, "calls_succeeded": 0, "calls_failed": 0,
                           "invalid_json_count": 0, "timeout_count": 0,
                           "failure_category_counts": {}, "usage_available": False,
                           "prompt_tokens_total": 0, "completion_tokens_total": 0,
                           "total_tokens_total": 0, "latency_ms_total": 0}
    for r in runs:
        ps = r.get("provider_summary", {})
        for k in ("calls_attempted", "calls_succeeded", "calls_failed", "invalid_json_count", "timeout_count", "latency_ms_total", "prompt_tokens_total", "completion_tokens_total", "total_tokens_total"):
            psm[k] += int(ps.get(k, 0))
        if ps.get("usage_available"): psm["usage_available"] = True
        for c, cn in ps.get("failure_category_counts", {}).items():
            psm["failure_category_counts"][c] = psm["failure_category_counts"].get(c, 0) + int(cn)
    return m, psm

def _aggregate_family_results(arm_runs: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    fr: list[dict[str, Any]] = []
    for fam in TASK_FAMILIES:
        for arm in ARMS:
            runs = [r for r in arm_runs[arm] if r.get("task_family") == fam]
            n = len(runs)
            fr.append({"task_family": fam, "arm": arm, "run_count": n,
                       "solve_rate": _rm(_rate(sum(1 for r in runs if r["solve"]), n)),
                       "tests_pass_rate": _rm(_rate(sum(1 for r in runs if r["tests_pass"]), n))})
    return fr

def _compute_paired_deltas(am: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    for ba, ta in ALL_CONTRASTS:
        b, t = am[ba], am[ta]
        for nm in DELTA_METRIC_NAMES:
            recs.append({"baseline_arm": ba, "treatment_arm": ta, "metric": nm,
                         "delta": _rm(t[nm] - b[nm])})
    return recs

def _compute_mechanism_summary_records(arm_runs: dict[str, list[dict[str, Any]]], tc: int) -> list[dict[str, Any]]:
    if tc <= 0: return []
    cr = 0; ss = 0; ts = 0; dh = 0; awb = 0; aas = 0; sc = 0; wfs = 0
    for i in range(tc):
        pas: dict[str, bool] = {}
        paw: dict[str, bool] = {}
        for arm in ARMS:
            runs = arm_runs[arm]
            if i < len(runs):
                pas[arm] = bool(runs[i].get("solve"))
                paw[arm] = bool(runs[i].get("wrong_file_edits", 0) > 0) or runs[i].get("chosen_file_category") in ("distractor", "support")
            else:
                pas[arm] = False; paw[arm] = False
        if pas[ARM_TARGET_PLUS_SUPPORT] and not pas[ARM_TARGET_ONLY] and not pas[ARM_SUPPORT_ONLY]: cr += 1
        if pas[ARM_SUPPORT_ONLY]: ss += 1
        if pas[ARM_TARGET_ONLY]: ts += 1
        if not pas[ARM_DISTRACTOR_PLUS_SUPPORT] and pas[ARM_TARGET_PLUS_SUPPORT]: dh += 1
        # ambiguous_support_wrong_binding: support_only chose wrong file.
        if not pas[ARM_SUPPORT_ONLY] and paw.get(ARM_SUPPORT_ONLY): awb += 1
        for arm in (ARM_TARGET_ONLY, ARM_SUPPORT_ONLY, ARM_DISTRACTOR_PLUS_SUPPORT, ARM_TARGET_PLUS_SUPPORT):
            if paw.get(arm): wfs += 1; break
        if all(pas[arm] for arm in ARMS): aas += 1
        if pas[ARM_CONTROL]: sc += 1
    return [
        {"mechanism_field": "target_support_conjunction_required_count", "value": cr, "record_count": tc},
        {"mechanism_field": "support_only_sufficient_count", "value": ss, "record_count": tc},
        {"mechanism_field": "target_only_sufficient_count", "value": ts, "record_count": tc},
        {"mechanism_field": "distractor_hurts_count", "value": dh, "record_count": tc},
        {"mechanism_field": "ambiguous_support_wrong_binding_count", "value": awb, "record_count": tc},
        {"mechanism_field": "wrong_file_selection_count", "value": wfs, "record_count": tc},
        {"mechanism_field": "all_arms_solved_count", "value": aas, "record_count": tc},
        {"mechanism_field": "sparse_solved_count", "value": sc, "record_count": tc},
    ]

def _compute_honest_signals(am: dict[str, dict[str, Any]], mech: list[dict[str, Any]]) -> dict[str, Any]:
    mm = {r["mechanism_field"]: r["value"] for r in mech}
    tps = am[ARM_TARGET_PLUS_SUPPORT]; dps = am[ARM_DISTRACTOR_PLUS_SUPPORT]
    so = am[ARM_SUPPORT_ONLY]; to = am[ARM_TARGET_ONLY]; ctrl = am[ARM_CONTROL]
    cs = tps.get("solve_rate", 0.0) > so.get("solve_rate", 0.0) and tps.get("solve_rate", 0.0) > to.get("solve_rate", 0.0)
    ds = tps.get("solve_rate", 0.0) > dps.get("solve_rate", 0.0) or tps.get("selected_target_file_rate", 0.0) > dps.get("selected_target_file_rate", 0.0)
    return {
        "target_support_conjunction_signal_observed": bool(cs),
        "distractor_hurts_signal_observed": bool(ds),
        "target_support_conjunction_required_count": int(mm.get("target_support_conjunction_required_count", 0)),
        "support_only_sufficient_count": int(mm.get("support_only_sufficient_count", 0)),
        "target_only_sufficient_count": int(mm.get("target_only_sufficient_count", 0)),
        "distractor_hurts_count": int(mm.get("distractor_hurts_count", 0)),
        "ambiguous_support_wrong_binding_count": int(mm.get("ambiguous_support_wrong_binding_count", 0)),
        "wrong_file_selection_count": int(mm.get("wrong_file_selection_count", 0)),
        "all_arms_solved_count": int(mm.get("all_arms_solved_count", 0)),
        "sparse_solved_count": int(mm.get("sparse_solved_count", 0)),
        "target_plus_support_solve_rate": _rm(tps.get("solve_rate", 0.0)),
        "distractor_plus_support_solve_rate": _rm(dps.get("solve_rate", 0.0)),
        "support_only_solve_rate": _rm(so.get("solve_rate", 0.0)),
        "target_only_solve_rate": _rm(to.get("solve_rate", 0.0)),
        "control_sparse_solve_rate": _rm(ctrl.get("solve_rate", 0.0)),
        "target_plus_support_selected_target_file_rate": _rm(tps.get("selected_target_file_rate", 0.0)),
        "distractor_plus_support_selected_target_file_rate": _rm(dps.get("selected_target_file_rate", 0.0)),
    }

def _determine_live_status(prc: bool, apcf: bool, apf: bool) -> str:
    if not prc: return STATUS_PAIRED_FAILED
    if apcf: return STATUS_PROVIDER_FAILED
    if apf: return STATUS_PARSE_FAILED
    return STATUS_PASS

# ---------------------------------------------------------------------------
# Public artifact builder + build_report
# ---------------------------------------------------------------------------

def _build_public_report(checks: list[dict[str, Any]], all_passed: bool, status: str,
                         arm_results: list[dict[str, Any]] | None = None,
                         paired_deltas: list[dict[str, Any]] | None = None,
                         task_family_results: list[dict[str, Any]] | None = None,
                         mechanism_summary_records: list[dict[str, Any]] | None = None,
                         honest_signals: dict[str, Any] | None = None,
                         input_summary: dict[str, Any] | None = None,
                         private_score_manifest: dict[str, Any] | None = None,
                         private_event_manifest: dict[str, Any] | None = None,
                         model_display_category: str = "unavailable",
                         live_run_executed: bool = False) -> dict[str, Any]:
    arm_results = arm_results or []
    pd = paired_deltas or []
    tfr = task_family_results or []
    msr = mechanism_summary_records or []
    hs = honest_signals or {}
    ism = input_summary or {
        "synthetic_task_count": 0, "run_count_per_arm": 0, "total_runs": 0,
        "arms": list(ARMS), "task_families": list(TASK_FAMILIES),
        "paired_design": True, "workspace_isolation": "fresh_tmp_per_task_arm",
        "transient_workspace_outputs_only": True, "designed_causal_subset": True,
        "task_family_matrix": True,
        "primary_contrasts": [f"{t}_vs_{b}" for b, t in PRIMARY_CONTRASTS],
        "secondary_contrasts": [f"{t}_vs_{b}" for b, t in SECONDARY_CONTRASTS],
        "file_choice_confound_removed": True, "support_cue_ambiguous": True,
    }
    psm = private_score_manifest or {
        "records_written": False, "record_count": 0,
        "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
        "manifest_hash": _private_score_manifest_hash(),
        "storage_class": "tmp_private", "path_publicly_serialized": False}
    pem = private_event_manifest or {
        "records_written": False, "record_count": 0,
        "schema_version": PRIVATE_EVENT_SCHEMA_VERSION,
        "manifest_hash": _private_event_manifest_hash(),
        "storage_class": "tmp_private", "path_publicly_serialized": False}
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "generated_by": GENERATED_BY,
        "generated_at": _now_iso(), "claim_level": CLAIM_LEVEL,
        "status": status, "mode": MODE, "phase": PHASE,
        "model_display_category": model_display_category,
        "input_summary": ism, "arm_results": arm_results,
        "paired_deltas": pd, "task_family_results": tfr,
        "mechanism_summary_records": msr, "honest_signals": hs,
        "private_score_manifest": psm, "private_event_manifest": pem,
        **DEFAULT_FALSE_FLAGS,
        "aggregate_only_public_artifact": True, "diagnostic_only": True,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c.get("passed")),
        "self_test_passed": all_passed,
    }
    if live_run_executed:
        for f in LIVE_TRUE_FLAGS: report[f] = True
    else:
        for f in LIVE_TRUE_FLAGS:
            if f not in ("aggregate_only_public_artifact", "diagnostic_only"):
                report[f] = False
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report

def _normalize_model_display(raw: str) -> str:
    if not raw: return "unavailable"
    c = re.sub(r"^\[mk\]", "", raw, flags=re.IGNORECASE)
    c = re.sub(r"[^A-Za-z0-9._-]", "", c).strip(".-_")
    if not c: return "unavailable"
    return c[:64] if len(c) > 64 else c

def build_report(task_count: int, *, allow_remote: bool, require_workflow_dispatch: bool,
                 private_score_dir: str | None = None, private_event_dir: str | None = None) -> dict[str, Any]:
    checks, all_passed = run_self_test_checks()
    enabled, fc = provider_client._check_remote_enabled(allow_remote=allow_remote,
                                                         require_workflow_dispatch=require_workflow_dispatch)
    if not enabled:
        status = STATUS_UNAVAILABLE if fc in (provider_client.FAILURE_CATEGORY_MISSING_ENV,) else STATUS_BLOCKED_REMOTE
        ism = {"synthetic_task_count": 0, "run_count_per_arm": 0, "total_runs": 0,
               "arms": list(ARMS), "task_families": list(TASK_FAMILIES),
               "paired_design": True, "workspace_isolation": "fresh_tmp_per_task_arm",
               "transient_workspace_outputs_only": True, "designed_causal_subset": True,
               "task_family_matrix": True,
               "primary_contrasts": [f"{t}_vs_{b}" for b, t in PRIMARY_CONTRASTS],
               "secondary_contrasts": [f"{t}_vs_{b}" for b, t in SECONDARY_CONTRASTS],
               "file_choice_confound_removed": True, "support_cue_ambiguous": True}
        return _build_public_report(checks, all_passed, status=status, input_summary=ism,
                                    model_display_category="unavailable", live_run_executed=False)
    sd, ss = _resolve_private_dir(private_score_dir, "b16j_private_score")
    ed, es = _resolve_private_dir(private_event_dir, "b16j_private_event")
    sp = sd / "b16j_private_score.jsonl"; ep = ed / "b16j_private_event.jsonl"
    sp.write_text("", encoding="utf-8"); ep.write_text("", encoding="utf-8")
    prid = f"b16j_{int(time.time())}_{os.getpid()}"
    tasks = _generate_synthetic_tasks(task_count)
    ar: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    apcf = False; apf = False; srw = 0; erw = 0
    for task in tasks:
        for arm in ARMS:
            pack = _build_pack(arm)
            wd = Path(tempfile.mkdtemp(prefix="b16j_workspace_"))
            try:
                _build_workspace(wd, task)
                run = _run_live_agent(wd, task, pack, arm=arm, allow_remote=allow_remote,
                                       require_workflow_dispatch=require_workflow_dispatch,
                                       phase_run_id=prid, score_path=sp, event_path=ep)
            finally:
                try: shutil.rmtree(wd, ignore_errors=True)
                except OSError: pass
            ar[arm].append(run)
            ps = run.get("provider_summary", {})
            if ps.get("calls_failed", 0) > 0: apcf = True
            if run["invalid_json"]: apf = True
            srw += 1; erw += 1
    amb: dict[str, dict[str, Any]] = {}
    ares: list[dict[str, Any]] = []
    for arm in ARMS:
        m, psm = _aggregate_arm_metrics(ar[arm]); amb[arm] = m
        ares.append({"arm": arm, "metrics": m, "provider_summary": psm,
                      "failure_category_counts": psm.get("failure_category_counts", {})})
    pd = _compute_paired_deltas(amb)
    tfr = _aggregate_family_results(ar)
    msr = _compute_mechanism_summary_records(ar, task_count)
    hs = _compute_honest_signals(amb, msr)
    status = _determine_live_status(True, apcf, apf)
    ism = {"synthetic_task_count": task_count, "run_count_per_arm": task_count,
           "total_runs": task_count * len(ARMS), "arms": list(ARMS),
           "task_families": list(TASK_FAMILIES), "paired_design": True,
           "workspace_isolation": "fresh_tmp_per_task_arm",
           "transient_workspace_outputs_only": True, "designed_causal_subset": True,
           "task_family_matrix": True,
           "primary_contrasts": [f"{t}_vs_{b}" for b, t in PRIMARY_CONTRASTS],
           "secondary_contrasts": [f"{t}_vs_{b}" for b, t in SECONDARY_CONTRASTS],
           "file_choice_confound_removed": True, "support_cue_ambiguous": True}
    rm = os.environ.get(provider_client.ENV_MODEL, "")
    mdc = _normalize_model_display(rm)
    psmm = {"records_written": srw > 0, "record_count": int(srw),
            "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
            "manifest_hash": _private_score_manifest_hash(),
            "storage_class": ss, "path_publicly_serialized": False}
    pemm = {"records_written": erw > 0, "record_count": int(erw),
            "schema_version": PRIVATE_EVENT_SCHEMA_VERSION,
            "manifest_hash": _private_event_manifest_hash(),
            "storage_class": es, "path_publicly_serialized": False}
    return _build_public_report(checks, all_passed, status=status, arm_results=ares,
                               paired_deltas=pd, task_family_results=tfr,
                               mechanism_summary_records=msr, honest_signals=hs,
                               input_summary=ism, private_score_manifest=psmm,
                               private_event_manifest=pemm, model_display_category=mdc,
                               live_run_executed=True)

# ---------------------------------------------------------------------------
# Env-preservation self-test helpers
# ---------------------------------------------------------------------------

def _probe_missing_env() -> tuple[bool, str, bool]:
    before = {k: os.environ.get(k) for k in _REMOTE_ENV_KEYS}
    saved = {k: os.environ.pop(k, None) for k in _REMOTE_ENV_KEYS}
    try:
        os.environ[provider_client.ENV_ALLOW_REMOTE] = "1"
        e, fc = provider_client._check_remote_enabled(allow_remote=True, require_workflow_dispatch=False)
    finally:
        for k, v in saved.items():
            if v is not None: os.environ[k] = v
            else: os.environ.pop(k, None)
    after = {k: os.environ.get(k) for k in _REMOTE_ENV_KEYS}
    return e, fc, after == before

def _self_test_probe_preserves_env() -> bool:
    outer = {k: os.environ.get(k) for k in _REMOTE_ENV_KEYS}
    synth = {provider_client.ENV_BASE_URL: "https" + "://example.invalid/openai/v1",
             provider_client.ENV_API_KEY: "redacted-test-key",
             provider_client.ENV_MODEL: _ROUTING_PREFIX_SENTINEL + "Kimi-K2.7-Code",
             provider_client.ENV_ALLOW_REMOTE: "1",
             provider_client.ENV_WORKFLOW_DISPATCH: "1"}
    try:
        for k, v in synth.items(): os.environ[k] = v
        _, _, restored = _probe_missing_env()
        return restored and all(os.environ.get(k) == v for k, v in synth.items())
    finally:
        for k, v in outer.items():
            if v is not None: os.environ[k] = v
            else: os.environ.pop(k, None)

# ---------------------------------------------------------------------------
# Self-test checks
# ---------------------------------------------------------------------------

def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []
    sk = _build_public_report([], False, status=STATUS_UNAVAILABLE)
    # Group 1: Identity.
    checks.append(_check("schema_version_correct", sk["schema_version"] == SCHEMA_VERSION))
    checks.append(_check("claim_level_correct", sk["claim_level"] == CLAIM_LEVEL))
    checks.append(_check("mode_correct", sk["mode"] == MODE))
    checks.append(_check("phase_correct", sk["phase"] == PHASE))
    checks.append(_check("generated_by_correct", sk["generated_by"] == GENERATED_BY))
    checks.append(_check("arms_count_is_5", len(ARMS) == 5))
    checks.append(_check("task_families_count_is_8", len(TASK_FAMILIES) == 8))
    checks.append(_check("default_task_count_is_8", DEFAULT_TASK_COUNT == 8))
    checks.append(_check("max_live_calls_is_60", MAX_LIVE_CALLS == 60))
    checks.append(_check("primary_contrasts_count_is_3", len(PRIMARY_CONTRASTS) == 3))
    checks.append(_check("secondary_contrasts_count_is_5", len(SECONDARY_CONTRASTS) == 5))
    checks.append(_check("all_contrasts_count_is_8", len(ALL_CONTRASTS) == 8))
    checks.append(_check("support_cue_ambiguous_flag", sk["input_summary"].get("support_cue_ambiguous") is True))
    checks.append(_check("file_choice_confound_removed_flag", sk["input_summary"].get("file_choice_confound_removed") is True))
    checks.append(_check("no_global_allowed_edit_files_set", "ALLOWED_EDIT_FILES" not in dir()))
    checks.append(_check("no_self_test_summary_key", "self_test_summary" not in sk))
    checks.append(_check("no_self_test_checks_list_key", "self_test_checks" not in sk))
    checks.append(_check("self_test_checks_total_is_int", isinstance(sk.get("self_test_checks_total"), int)))
    checks.append(_check("self_test_checks_passed_is_int", isinstance(sk.get("self_test_checks_passed"), int)))
    for st in ALL_STATUSES:
        checks.append(_check(f"status_{st}_preserved", _build_public_report([], False, status=st)["status"] == st))
    # Group 2: No-claim flags.
    for f in DEFAULT_FALSE_FLAGS:
        checks.append(_check(f"default_false_{f}", sk.get(f) is False))
    # Group 3: Live-run flag gating.
    for f in LIVE_TRUE_FLAGS:
        if f in ("aggregate_only_public_artifact", "diagnostic_only"): continue
        checks.append(_check(f"unavailable_live_flag_false_{f}", sk.get(f) is False))
    lr = _build_public_report([], True, status=STATUS_PASS, live_run_executed=True)
    for f in LIVE_TRUE_FLAGS:
        checks.append(_check(f"live_flag_true_{f}", lr.get(f) is True))
    # Group 4: Task families.
    t8 = _generate_synthetic_tasks(8)
    checks.append(_check("synthetic_task_count_correct", len(t8) == 8))
    fc: dict[str, int] = {}
    for t in t8: fc[t["task_family"]] = fc.get(t["task_family"], 0) + 1
    for fam in TASK_FAMILIES:
        checks.append(_check(f"family_present_{fam}", fam in fc and fc[fam] >= 1))
    checks.append(_check("families_balanced_1_each", all(fc.get(f, 0) == 1 for f in TASK_FAMILIES)))
    # Group 5: Workspace + safe files.
    wd = Path(tempfile.mkdtemp(prefix="b16j_selftest_"))
    try:
        for ft in t8:
            _build_workspace(wd, ft)
            tp = wd / ft["target_module"]; dp = wd / ft["distractor_module"]
            sp = wd / ft["support_module"]; tp_test = wd / ft["test_module"]
            checks.append(_check(f"ws_{ft['task_family']}_target", tp.is_file()))
            checks.append(_check(f"ws_{ft['task_family']}_distractor", dp.is_file()))
            checks.append(_check(f"ws_{ft['task_family']}_support", sp.is_file()))
            checks.append(_check(f"ws_{ft['task_family']}_test", tp_test.is_file()))
            pb = subprocess.run([sys.executable, str(tp_test)], check=False, capture_output=True, text=True, timeout=30)
            checks.append(_check(f"ws_{ft['task_family']}_test_fails", pb.returncode != 0))
            sf = _safe_edit_files(ft)
            checks.append(_check(f"safe_files_{ft['task_family']}_target", ft["target_module"] in sf))
            checks.append(_check(f"safe_files_{ft['task_family']}_distractor", ft["distractor_module"] in sf))
            checks.append(_check(f"safe_files_{ft['task_family']}_support", ft["support_module"] in sf))
            checks.append(_check(f"opaque_target_filename_{ft['task_family']}", "target" not in ft["target_module"] and "distractor" not in ft["target_module"] and "decoy" not in ft["target_module"] and ft["target_module"].startswith("candidate_")))
            checks.append(_check(f"opaque_distractor_filename_{ft['task_family']}", "target" not in ft["distractor_module"] and "distractor" not in ft["distractor_module"] and "decoy" not in ft["distractor_module"] and ft["distractor_module"].startswith("candidate_")))
        # Group 6: Pack builder.
        cp = _build_pack(ARM_CONTROL); top = _build_pack(ARM_TARGET_ONLY)
        sop = _build_pack(ARM_SUPPORT_ONLY); dpsp = _build_pack(ARM_DISTRACTOR_PLUS_SUPPORT)
        tpsp = _build_pack(ARM_TARGET_PLUS_SUPPORT)
        checks.append(_check("control_no_atoms", not cp["has_target_file_cue"] and not cp["has_support_module_cue"] and not cp["has_ambiguous_support_rule"]))
        checks.append(_check("target_only_has_target", top["has_target_file_cue"] and top["has_target_symbol_cue"]))
        checks.append(_check("target_only_lacks_support", not top["has_support_module_cue"] and not top["has_ambiguous_support_rule"]))
        checks.append(_check("support_only_has_support_and_ambiguous_rule", sop["has_support_module_cue"] and sop["has_ambiguous_support_rule"]))
        checks.append(_check("support_only_lacks_target", not sop["has_target_file_cue"] and not sop["has_target_symbol_cue"]))
        checks.append(_check("dps_has_distractor", dpsp["has_distractor_file_cue"]))
        checks.append(_check("dps_has_support_and_ambiguous_rule", dpsp["has_support_module_cue"] and dpsp["has_ambiguous_support_rule"]))
        checks.append(_check("tps_has_all_atoms", tpsp["has_target_file_cue"] and tpsp["has_target_symbol_cue"] and tpsp["has_support_module_cue"] and tpsp["has_ambiguous_support_rule"]))
        checks.append(_check("tps_no_distractor", not tpsp["has_distractor_file_cue"]))
        # Group 7: Atom composition.
        checks.append(_check("control_atoms_empty", _build_atom_composition(ARM_CONTROL) == []))
        checks.append(_check("target_only_atoms_2", len(_build_atom_composition(ARM_TARGET_ONLY)) == 2))
        checks.append(_check("support_only_atoms_2", len(_build_atom_composition(ARM_SUPPORT_ONLY)) == 2))
        checks.append(_check("dps_atoms_3", len(_build_atom_composition(ARM_DISTRACTOR_PLUS_SUPPORT)) == 3))
        checks.append(_check("tps_atoms_4", len(_build_atom_composition(ARM_TARGET_PLUS_SUPPORT)) == 4))
        # Group 8: Ambiguous support cue text (NO target filename/symbol/answer).
        f1 = t8[0]
        for ft in t8:
            ac = _ambiguous_support_cue_text(ft)
            checks.append(_check(f"ambiguous_cue_nonempty_{ft['task_family']}", len(ac) > 0))
            checks.append(_check(f"ambiguous_cue_no_target_filename_{ft['task_family']}", ft["target_module"] not in ac))
            checks.append(_check(f"ambiguous_cue_no_exact_answer_{ft['task_family']}", f"Correct value: {ft['correct_value']}" not in ac and f"correct value is {ft['correct_value']}" not in ac.lower()))
            checks.append(_check(f"ambiguous_cue_no_edit_instruction_{ft['task_family']}", f"edit {ft['target_module']}" not in ac.lower()))
            support_prompt = "\n".join(part["content"] for part in _build_messages(wd, ft, sop))
            role_tokens = ("target.py", "distractor.py", "target file", "distractor file", "decoy", "correct file", "wrong file", "target source")
            checks.append(_check(f"support_prompt_no_role_lexical_cue_{ft['task_family']}", not any(tok in support_prompt.lower() for tok in role_tokens)))
            checks.append(_check(f"support_prompt_no_target_module_{ft['task_family']}", ft["target_module"] not in support_prompt or ft["distractor_module"] in support_prompt))
            checks.append(_check(f"support_prompt_no_target_symbol_{ft['task_family']}", f"Target symbol: {ft['symbol']}" not in support_prompt))
            dc = _decisive_cue_text(ft)
            checks.append(_check(f"decisive_cue_has_answer_{ft['task_family']}", str(ft["correct_value"]) in dc))
            checks.append(_check(f"decisive_cue_has_target_filename_{ft['task_family']}", ft["target_module"] in dc))
        # Group 9: Validator.
        v, _ = _validate_edit_action({"action": "replace_return_value", "file": "evil.py", "symbol": "x", "new_return_value": 1}, f1)
        checks.append(_check("validator_rejects_evil_py", not v))
        v, _ = _validate_edit_action({"action": "replace_return_value", "file": f1["target_module"], "symbol": "x", "new_return_value": 1}, f1)
        checks.append(_check("validator_accepts_private_target_role_file", v))
        v, _ = _validate_edit_action({"action": "replace_return_value", "file": f1["distractor_module"], "symbol": "x", "new_return_value": 1}, f1)
        checks.append(_check("validator_accepts_private_distractor_role_file", v))
        v, _ = _validate_edit_action({"action": "no_op", "file": f1["target_module"], "symbol": "x"}, f1)
        checks.append(_check("validator_accepts_no_op", v))
        # Group 10: Categorization.
        checks.append(_check("categorize_target", _categorize_chosen_file(f1["target_module"], f1) == "target"))
        checks.append(_check("categorize_distractor", _categorize_chosen_file(f1["distractor_module"], f1) == "distractor"))
        checks.append(_check("categorize_support", _categorize_chosen_file(f1["support_module"], f1) == "support"))
        # Group 11: Private writers + fake responses.
        sd, _ = _resolve_private_dir(None, "b16j_st_score")
        ed, _ = _resolve_private_dir(None, "b16j_st_event")
        sp = sd / "b16j_st_score.jsonl"; ep = ed / "b16j_st_event.jsonl"
        sp.write_text("", encoding="utf-8"); ep.write_text("", encoding="utf-8")
        _build_workspace(wd, f1)
        rts = _run_live_agent(wd, f1, tpsp, arm=ARM_TARGET_PLUS_SUPPORT, allow_remote=False, require_workflow_dispatch=False, phase_run_id="b16j_st", score_path=sp, event_path=ep, fake_response={"action": "replace_return_value", "file": f1["target_module"], "symbol": f1["symbol"], "new_return_value": f1["correct_value"]})
        checks.append(_check("tps_solve", rts["solve"] is True))
        checks.append(_check("tps_chose_target", rts["chosen_file_category"] == "target"))
        _build_workspace(wd, f1)
        rsw = _run_live_agent(wd, f1, sop, arm=ARM_SUPPORT_ONLY, allow_remote=False, require_workflow_dispatch=False, phase_run_id="b16j_st", score_path=sp, event_path=ep, fake_response={"action": "replace_return_value", "file": f1["distractor_module"], "symbol": f1["symbol"], "new_return_value": f1["buggy_value"]})
        checks.append(_check("so_wrong_file_no_solve", rsw["solve"] is False))
        checks.append(_check("so_chose_distractor", rsw["chosen_file_category"] == "distractor"))
        _build_workspace(wd, f1)
        rcn = _run_live_agent(wd, f1, cp, arm=ARM_CONTROL, allow_remote=False, require_workflow_dispatch=False, phase_run_id="b16j_st", score_path=sp, event_path=ep, fake_response={"action": "no_op", "file": f1["target_module"], "symbol": f1["symbol"]})
        checks.append(_check("control_no_op", rcn["no_op"] is True))
        _build_workspace(wd, f1)
        ri = _run_live_agent(wd, f1, cp, arm=ARM_CONTROL, allow_remote=False, require_workflow_dispatch=False, phase_run_id="b16j_st", score_path=sp, event_path=ep, fake_invalid=True)
        checks.append(_check("invalid_json_flag", ri["invalid_json"] is True))
        checks.append(_check("no_raw_in_result", not any(k in ri for k in ("raw_response", "response", "prompt", "chosen_file"))))
        sl = sp.read_text(encoding="utf-8").splitlines()
        el = ep.read_text(encoding="utf-8").splitlines()
        checks.append(_check("private_rows_4", len(sl) == 4 and len(el) == 4))
        for i, line in enumerate(sl):
            try:
                row = json.loads(line)
                checks.append(_check(f"score_row_{i}_has_atoms_chosen_file", "atom_composition" in row and "chosen_file" in row and "score_outcome" in row))
            except (json.JSONDecodeError, ValueError):
                checks.append(_check(f"score_row_{i}_has_atoms_chosen_file", False))
        # Group 12: Aggregate + deltas + mechanism.
        art: dict[str, list[dict[str, Any]]] = {ARM_CONTROL: [rcn], ARM_TARGET_ONLY: [rcn], ARM_SUPPORT_ONLY: [rsw], ARM_DISTRACTOR_PLUS_SUPPORT: [rsw], ARM_TARGET_PLUS_SUPPORT: [rts]}
        amm: dict[str, dict[str, Any]] = {}
        for arm in ARMS:
            m, _ = _aggregate_arm_metrics(art[arm]); amm[arm] = m
        checks.append(_check("tps_solve_rate_1", amm[ARM_TARGET_PLUS_SUPPORT]["solve_rate"] == 1.0))
        checks.append(_check("control_solve_rate_0", amm[ARM_CONTROL]["solve_rate"] == 0.0))
        for mn in ("selected_target_file_rate", "selected_distractor_file_rate", "selected_support_file_rate"):
            checks.append(_check(f"metric_{mn}_present", mn in amm[ARM_TARGET_PLUS_SUPPORT]))
        deltas = _compute_paired_deltas(amm)
        checks.append(_check("paired_deltas_count", len(deltas) == len(ALL_CONTRASTS) * len(DELTA_METRIC_NAMES)))
        for ba, ta in PRIMARY_CONTRASTS:
            checks.append(_check(f"primary_{ta}_vs_{ba}_present", any(d.get("baseline_arm") == ba and d.get("treatment_arm") == ta for d in deltas)))
        mech = _compute_mechanism_summary_records(art, 1)
        checks.append(_check("mechanism_count_8", len(mech) == 8))
        mf = {r["mechanism_field"] for r in mech}
        checks.append(_check("mechanism_has_required_fields", mf == {
            "target_support_conjunction_required_count", "support_only_sufficient_count",
            "target_only_sufficient_count", "distractor_hurts_count",
            "ambiguous_support_wrong_binding_count", "wrong_file_selection_count",
            "all_arms_solved_count", "sparse_solved_count"}))
        mm = {r["mechanism_field"]: r["value"] for r in mech}
        checks.append(_check("mechanism_conjunction_required_1", mm["target_support_conjunction_required_count"] == 1))
        checks.append(_check("mechanism_ambiguous_wrong_binding_1", mm["ambiguous_support_wrong_binding_count"] == 1))
        hs = _compute_honest_signals(amm, mech)
        checks.append(_check("honest_conjunction_signal_true", hs["target_support_conjunction_signal_observed"] is True))
        fr = _aggregate_family_results(art)
        checks.append(_check("family_results_all_8", set(r["task_family"] for r in fr) == set(TASK_FAMILIES)))
        checks.append(_check("family_results_5_per_family", all(sum(1 for r in fr if r["task_family"] == f) == 5 for f in TASK_FAMILIES)))
        # Group 13: Model display.
        checks.append(_check("normalize_strips_prefix", _normalize_model_display(_ROUTING_PREFIX_SENTINEL + "Kimi-K2.7-Code") == "Kimi-K2.7-Code"))
        checks.append(_check("normalize_empty", _normalize_model_display("") == "unavailable"))
        # Group 14: Env preservation.
        checks.append(_check("env_preserves", _self_test_probe_preserves_env()))
        e, fc, r = _probe_missing_env()
        checks.append(_check("probe_missing_env", not e and fc == provider_client.FAILURE_CATEGORY_MISSING_ENV))
        checks.append(_check("probe_restores", r))
        # Group 15: Manifest hashes.
        h1 = _private_score_manifest_hash(); h2 = _private_score_manifest_hash()
        checks.append(_check("score_hash_stable", h1 == h2 and len(h1) == 64))
        e1 = _private_event_manifest_hash(); e2 = _private_event_manifest_hash()
        checks.append(_check("event_hash_stable", e1 == e2 and len(e1) == 64))
        checks.append(_check("hashes_distinct", h1 != e1))
    finally:
        try: shutil.rmtree(wd, ignore_errors=True)
        except OSError: pass
    # Group 16: Scanner rejections.
    checks.append(_check("scanner_rejects_tmp_path", bool(_scan_forbidden({"leaked": "/tmp/b16j_workspace_0"}))))
    checks.append(_check("scanner_rejects_file_path", bool(_scan_forbidden({"leaked": "target.py"}))))
    checks.append(_check("scanner_rejects_prompt_key", bool(_scan_forbidden({"prompt": "abc"}))))
    checks.append(_check("scanner_rejects_response_key", bool(_scan_forbidden({"response": "abc"}))))
    checks.append(_check("scanner_rejects_chosen_file", bool(_scan_forbidden({"chosen_file": "target.py"}))))
    checks.append(_check("scanner_rejects_chosen_symbol", bool(_scan_forbidden({"chosen_symbol": "resolve_001"}))))
    checks.append(_check("scanner_rejects_file_choice", bool(_scan_forbidden({"file_choice": "target"}))))
    checks.append(_check("scanner_rejects_support_rule_text", bool(_scan_forbidden({"support_rule_text": "abc"}))))
    checks.append(_check("scanner_rejects_exact_answer", bool(_scan_forbidden({"exact_answer": 42}))))
    checks.append(_check("scanner_rejects_ambiguous_support_rule", bool(_scan_forbidden({"ambiguous_support_rule": "abc"}))))
    checks.append(_check("scanner_rejects_atom_composition", bool(_scan_forbidden({"atom_composition": []}))))
    checks.append(_check("scanner_rejects_score_outcome", bool(_scan_forbidden({"score_outcome": {}}))))
    checks.append(_check("scanner_rejects_phase_run_id", bool(_scan_forbidden({"phase_run_id": "abc"}))))
    checks.append(_check("scanner_rejects_provider_metadata", bool(_scan_forbidden({"provider_metadata": {}}))))
    checks.append(_check("scanner_rejects_raw_prefix", bool(_scan_forbidden({"leaked": _ROUTING_PREFIX_SENTINEL + "Kimi-K2.7-Code"}))))
    checks.append(_check("scanner_rejects_url", bool(_scan_forbidden({"leaked": "https" + "://example.com"}))))
    checks.append(_check("scanner_rejects_sentinel", bool(_scan_forbidden({"leaked": _SECRET_SENTINEL}))))
    # Group 17: Scanner allows.
    checks.append(_check("scanner_allows_arm", not _scan_forbidden({"arm": "ambiguous_target_plus_support"})))
    checks.append(_check("scanner_allows_family", not _scan_forbidden({"task_family": "operation_ambiguity"})))
    checks.append(_check("scanner_allows_deltas", not _scan_forbidden({"paired_deltas": [{"baseline_arm": "ambiguous_support_only", "treatment_arm": "ambiguous_target_plus_support", "metric": "solve_rate", "delta": 1.0}]})))
    checks.append(_check("scanner_allows_mechanism", not _scan_forbidden({"mechanism_summary_records": [{"mechanism_field": "ambiguous_support_wrong_binding_count", "value": 3, "record_count": 8}]})))
    checks.append(_check("scanner_allows_manifest", not _scan_forbidden({"private_score_manifest": {"records_written": True, "record_count": 40, "schema_version": "b16j_private_score.v1", "manifest_hash": "abc", "storage_class": "tmp_private", "path_publicly_serialized": False}})))
    checks.append(_check("scanner_allows_file_rates", not _scan_forbidden({"selected_target_file_rate": 1.0, "selected_distractor_file_rate": 0.0, "selected_support_file_rate": 0.0})))
    # Group 18: Fail-closed.
    try: _enforce_no_forbidden(sk); cp2 = True
    except SystemExit: cp2 = False
    checks.append(_check("fail_closed_clean_ok", cp2))
    lr2 = dict(sk); lr2["leaked_path"] = "src/openlocus/lib.rs"
    try: _enforce_no_forbidden(lr2); lr2_raises = False
    except SystemExit: lr2_raises = True
    checks.append(_check("fail_closed_leak_raises", lr2_raises))
    fr2 = dict(sk); fr2["self_test_passed"] = False
    try: _refuse_on_self_test_failure(fr2); rfr = False
    except SystemExit: rfr = True
    checks.append(_check("refuse_failed_raises", rfr))
    # Group 19: Public self-scan clean.
    checks.append(_check("public_scan_clean", sk["forbidden_scan"]["status"] == "pass"))
    checks.append(_check("public_no_forbidden_key", not any(_has_dict_key_anywhere(sk, b) for b in ("task_id", "path", "file", "prompt", "response", "chosen_file", "chosen_symbol", "file_choice", "support_rule_text", "exact_answer", "atom_composition", "score_outcome", "phase_run_id", "provider_metadata"))))
    # Group 20: CLI.
    co = _cli_argument_option_strings()
    checks.append(_check("cli_has_self_test", "--self-test" in co))
    checks.append(_check("cli_has_out", "--out" in co))
    checks.append(_check("cli_has_allow_remote", "--allow-remote" in co))
    checks.append(_check("cli_has_require_workflow_dispatch", "--require-workflow-dispatch" in co))
    checks.append(_check("cli_has_task_count", "--task-count" in co))
    checks.append(_check("cli_only_expected", (co - {"-h", "--help"}) == {"--self-test", "--out", "--allow-remote", "--require-workflow-dispatch", "--task-count", "--private-score-dir", "--private-event-dir"}))
    # Group 21: Remote gating.
    e, fc = provider_client._check_remote_enabled(allow_remote=False, require_workflow_dispatch=False)
    checks.append(_check("blocked_when_no_remote", not e and fc == provider_client.FAILURE_CATEGORY_REMOTE_NOT_ENABLED))
    br = _build_public_report([], True, status=STATUS_BLOCKED_REMOTE, live_run_executed=False)
    checks.append(_check("blocked_live_flags_false", all(br.get(f) is False for f in LIVE_TRUE_FLAGS if f not in ("aggregate_only_public_artifact", "diagnostic_only"))))
    checks.append(_check("blocked_scan_pass", br["forbidden_scan"]["status"] == "pass"))
    # Group 22: Five-arm structure.
    checks.append(_check("arms_control_first", ARMS[0] == ARM_CONTROL))
    checks.append(_check("arms_target_only_second", ARMS[1] == ARM_TARGET_ONLY))
    checks.append(_check("arms_support_only_third", ARMS[2] == ARM_SUPPORT_ONLY))
    checks.append(_check("arms_dps_fourth", ARMS[3] == ARM_DISTRACTOR_PLUS_SUPPORT))
    checks.append(_check("arms_tps_fifth", ARMS[4] == ARM_TARGET_PLUS_SUPPORT))
    checks.append(_check("default_total_40", DEFAULT_TASK_COUNT * len(ARMS) == 40))
    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")

def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(description=(
        "B16-J ambiguous-support conjunction live-provider downstream smoke "
        "(public aggregate-only; 5 arms: control_sparse, ambiguous_target_only, "
        "ambiguous_support_only, ambiguous_distractor_plus_support, "
        "ambiguous_target_plus_support; support cue ambiguous (applies to multiple "
        "candidates); file choice open; no raw prompt/response/payload/chosen-file/"
        "support-rule/answer committed; CI pass does NOT require conjunction to hold)."))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--allow-remote", action="store_true")
    ap.add_argument("--require-workflow-dispatch", action="store_true")
    ap.add_argument("--task-count", type=int, default=DEFAULT_TASK_COUNT)
    ap.add_argument("--private-score-dir", type=str, default=None)
    ap.add_argument("--private-event-dir", type=str, default=None)
    return ap

def _cli_argument_option_strings() -> set[str]:
    p = build_parser()
    s: set[str] = set()
    for a in p._actions:
        for o in a.option_strings: s.add(o)
    return s

def _validate_task_count(tc: int) -> None:
    if not isinstance(tc, int) or tc < MIN_TASK_COUNT or tc > MAX_TASK_COUNT:
        raise SystemExit("invalid arguments")

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.self_test:
        checks, passed = run_self_test_checks()
        for c in checks:
            print(f"[{'PASS' if c['passed'] else 'FAIL'}] {c['check']}")
        pc = sum(1 for c in checks if c["passed"])
        print(f"self_test_passed={passed} ({pc}/{len(checks)} checks)")
        sys.exit(0 if passed else 1)
    _validate_task_count(args.task_count)
    op = args.out if args.out is not None else DEFAULT_OUT
    try:
        report = build_report(task_count=args.task_count, allow_remote=args.allow_remote,
                              require_workflow_dispatch=args.require_workflow_dispatch,
                              private_score_dir=args.private_score_dir,
                              private_event_dir=args.private_event_dir)
    except (OSError, subprocess.SubprocessError):
        print("error: failed to build report", file=sys.stderr); sys.exit(1)
    _enforce_no_forbidden(report)
    _refuse_on_self_test_failure(report)
    _write_json(op, report)
    print(f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, "
          f"self_test_passed={report['self_test_passed']}, status={report['status']}, phase={report['phase']})")

if __name__ == "__main__":
    main()
