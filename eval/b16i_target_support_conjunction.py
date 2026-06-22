#!/usr/bin/env python3
"""B16-I Non-Decisive Support / Target-Support Conjunction Live-Provider Smoke.

This module implements the **B16-I non-decisive support / target-support
conjunction live-provider downstream smoke**. B16-H removed the file-choice
confound, but support-only still solved every task because the support cue
was too decisive. B16-I redesigns the live-provider synthetic tasks so
support alone is non-decisive: target binding and support rule should both
be needed.

B16-I has FIVE fixed arms over the same eight synthetic task families
reused from B16-F/B16-G/B16-H for comparability:

1. ``control_sparse`` — task issue only, minimal context; no atoms.
2. ``file_choice_target_only`` — target file cue + target symbol cue;
   no support module, no support rule.
3. ``file_choice_nondecisive_support_only`` — support module cue +
   non-decisive support rule (formula/invariant/dependency/config relation
   that still requires target binding); no target file cue, no symbol
   cue. The support atom must NOT contain the exact final answer, exact
   target-file instruction, or target-symbol edit instruction.
4. ``file_choice_distractor_plus_nondecisive_support`` — distractor file
   cue + support module cue + non-decisive support rule; no target file;
   wrong-file binding.
5. ``file_choice_target_plus_support`` — target file cue + target
   symbol cue + support module cue + non-decisive support rule. This is
   the conjunction arm and should be the only reliably solving context
   arm.

Primary contrasts:

* ``file_choice_target_plus_support`` vs ``file_choice_target_only``
* ``file_choice_target_plus_support`` vs
  ``file_choice_nondecisive_support_only``
* ``file_choice_target_plus_support`` vs
  ``file_choice_distractor_plus_nondecisive_support``

Secondary contrasts:

* ``file_choice_target_only`` vs
  ``file_choice_nondecisive_support_only``
* each context arm vs ``control_sparse``

File choice remains enabled across the per-task safe file set (target
module + distractor module + support/config/cross-file module). The
chosen file is recorded ONLY in private SCORE/event JSONL under ``/tmp``.
Only aggregate file-choice rates are exposed publicly. No actual
filenames, support rule text, prompts, responses, patches, or per-run
rows are published.

B16-I is explicitly **not** a downstream agent value proof, **not** a
live-agent generalization proof, **not** an external benchmark result,
**not** a production coding-agent benchmark, **not** a real user task
evaluation, **not** a method winner/default/promotion claim, **not** a
calibration claim, **not** a BEA superiority claim, and **not** a
runtime/retriever/pack/backend/default-policy/EvidenceCore semantic
change.

Claim boundary (binding):

* Claim level: ``target_support_conjunction_downstream_smoke_only``.
* Status enum: ``target_support_conjunction_smoke_pass`` on live
  success; ``blocked_remote_not_enabled`` /
  ``unavailable_no_local_provider_env`` when remote opt-in not
  satisfied; ``provider_call_failed`` / ``structured_action_parse_failed``
  / ``paired_run_failed`` / ``fail_forbidden_scan`` on failures.
* Mode: ``public_aggregate_synthetic_task_family_matrix``; phase ``B16-I``.

Modes:

* ``--self-test``: no provider/network; uses fake provider responses.
* default without ``--allow-remote`` or without provider credential/model env: writes a
  truthful ``blocked_remote_not_enabled`` /
  ``unavailable_no_local_provider_env`` aggregate report if ``--out``
  is supplied; no provider calls; live-run flags false except
  ``aggregate_only_public_artifact`` / ``diagnostic_only``.
* live opt-in: requires ``--allow-remote``, the remote opt-in gate, and
  (when ``--require-workflow-dispatch``) the workflow-dispatch gate;
  runs a tiny task count (default 8; hard cap 12; default 40 live
  calls = 8 tasks x 5 arms; max 60 live calls).

Run::

    python3 -m py_compile eval/b16i_target_support_conjunction.py
    python3 eval/b16i_target_support_conjunction.py --self-test
    python3 eval/b16i_target_support_conjunction.py \\
        --out artifacts/b16i_target_support_conjunction/\\
b16i_target_support_conjunction_report.json
    # Live opt-in only when provider credential/model environment is available and safe:
    python3 eval/b16i_target_support_conjunction.py \\
        --allow-remote --task-count 8 \\
        --out artifacts/b16i_target_support_conjunction/\\
b16i_target_support_conjunction_report.json
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

# Reuse the provider client helper (unchanged).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import provider_client  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "b16i_target_support_conjunction.v1"
GENERATED_BY = "eval/b16i_target_support_conjunction.py"
CLAIM_LEVEL = "target_support_conjunction_downstream_smoke_only"
MODE = "public_aggregate_synthetic_task_family_matrix"
PHASE = "B16-I"

STATUS_PASS = "target_support_conjunction_smoke_pass"
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
    "artifacts/b16i_target_support_conjunction/"
    "b16i_target_support_conjunction_report.json"
)
DEFAULT_TASK_COUNT = 8
MIN_TASK_COUNT = 4
MAX_TASK_COUNT = 12
MAX_LIVE_CALLS = MAX_TASK_COUNT * 5

ARMS: tuple[str, ...] = (
    "control_sparse",
    "file_choice_target_only",
    "file_choice_nondecisive_support_only",
    "file_choice_distractor_plus_nondecisive_support",
    "file_choice_target_plus_support",
)
ARM_CONTROL = "control_sparse"
ARM_TARGET_ONLY = "file_choice_target_only"
ARM_SUPPORT_ONLY = "file_choice_nondecisive_support_only"
ARM_DISTRACTOR_PLUS_SUPPORT = "file_choice_distractor_plus_nondecisive_support"
ARM_TARGET_PLUS_SUPPORT = "file_choice_target_plus_support"

PRIMARY_CONTRASTS: tuple[tuple[str, str], ...] = (
    (ARM_TARGET_ONLY, ARM_TARGET_PLUS_SUPPORT),
    (ARM_SUPPORT_ONLY, ARM_TARGET_PLUS_SUPPORT),
    (ARM_DISTRACTOR_PLUS_SUPPORT, ARM_TARGET_PLUS_SUPPORT),
)
SECONDARY_CONTRASTS: tuple[tuple[str, str], ...] = (
    (ARM_SUPPORT_ONLY, ARM_TARGET_ONLY),
) + tuple(
    (ARM_CONTROL, arm)
    for arm in (
        ARM_TARGET_ONLY,
        ARM_SUPPORT_ONLY,
        ARM_DISTRACTOR_PLUS_SUPPORT,
        ARM_TARGET_PLUS_SUPPORT,
    )
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
    "run_count",
    "solve_rate",
    "tests_pass_rate",
    "patch_apply_rate",
    "correct_file_before_first_edit_rate",
    "wrong_file_edit_rate",
    "selected_target_file_rate",
    "selected_distractor_file_rate",
    "selected_support_file_rate",
    "no_op_rate",
    "invalid_json_rate",
    "provider_failure_rate",
    "context_tokens_mean",
    "prompt_tokens_total",
    "completion_tokens_total",
    "latency_seconds_mean",
    "cost_proxy_total",
)
DELTA_METRIC_NAMES: tuple[str, ...] = tuple(
    name for name in METRIC_NAMES if name != "run_count"
)

ALLOWED_EDIT_ACTIONS: frozenset[str] = frozenset(
    {"replace_return_value", "choose_helper_constant", "no_op"}
)

PRIVATE_SCORE_SCHEMA_VERSION = "b16i_private_score.v1"
PRIVATE_EVENT_SCHEMA_VERSION = "b16i_private_event.v1"

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
    "target_support_conjunction_executed",
    "private_score_records_written",
    "private_event_records_written",
    "aggregate_only_public_artifact",
    "diagnostic_only",
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
# Public artifact scanner (strict, fail-closed). Reuses B16-H shape plus
# support-rule-text forbid rules (support_rule_text, exact_answer).
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
        "support_rule_text", "exact_answer", "support_rule",
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
        "bea_action_trace", "bea_budget_trace", "bea_stop_reason",
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
    {
        "schema_version", "generated_by", "generated_at",
        "claim_level", "status", "mode", "phase",
        "arm", "baseline_arm", "treatment_arm", "metric",
        "task_family", "model_display_category",
        "storage_class", "manifest_hash", "mechanism_field",
    }
)

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
_RE_FILE_PATH_VALUE = re.compile(rf"\b[A-Za-z0-9._/\-]+\.(?:{_FILE_EXT})\b")
_RE_LINE_RANGE_VALUE = re.compile(r"\b\d+\s*[:\-]\s*\d+\b")
_RE_RAW_JSON = re.compile(r'^\s*[\{\[]\s*"[^"]+"\s*:')
_RE_TMP_PATH_VALUE = re.compile(r"/tmp/")
_RE_TASK_ID_VALUE = re.compile(r"\btask[_\-\s]*\d+\b", re.IGNORECASE)
_RE_PATCH_MARKER = re.compile(r"^(---|\+\+\+|@@\s)", re.MULTILINE)
_RE_STACK_TRACE = re.compile(
    r"Traceback\s*\(most\s+recent\s+call\s+last\)", re.IGNORECASE
)
_RE_RAW_MODEL_PREFIX = re.compile(r"\[mk\]", re.IGNORECASE)

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
    violations: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            sub_path = f"{path}.{key_str}"
            if key_str in FORBIDDEN_KEY_NAMES:
                violations.append({"category": "forbidden_key", "path": sub_path})
            violations.extend(_scan_forbidden(value, sub_path))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_scan_forbidden(value, f"{path}[{idx}]"))
    elif isinstance(obj, str):
        safe_value = _is_safe_value_path(path)
        if obj in FORBIDDEN_KEY_NAMES:
            violations.append({"category": "forbidden_field_name_value", "path": path})
        elif len(obj) > 256:
            violations.append({"category": "long_string", "path": path})
        elif _RE_URL_VALUE.search(obj) and not safe_value:
            violations.append({"category": "url_value", "path": path})
        elif not safe_value and _RE_HEX_DIGEST.search(obj):
            violations.append({"category": "hex_digest_value", "path": path})
        elif _RE_SECRET_LIKE.search(obj) and not safe_value:
            violations.append({"category": "secret_like_value", "path": path})
        elif not safe_value and _RE_FILE_PATH_VALUE.search(obj):
            violations.append({"category": "path_like_value", "path": path})
        elif "\n" in obj:
            violations.append({"category": "multiline_value", "path": path})
        elif _RE_RAW_JSON.search(obj):
            violations.append({"category": "raw_json_fragment", "path": path})
        elif not safe_value and _RE_TMP_PATH_VALUE.search(obj):
            violations.append({"category": "tmp_path_value", "path": path})
        elif not safe_value and _RE_TASK_ID_VALUE.search(obj):
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
            stripped_val = obj.strip()
            if (
                3 <= len(stripped_val) <= 16
                and _RE_LINE_RANGE_VALUE.fullmatch(stripped_val)
                and not stripped_val.replace(" ", "").isdigit()
            ):
                violations.append({"category": "line_range_value", "path": path})
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
        raise SystemExit("forbidden content leak; refusing to write artifact")


def _refuse_on_self_test_failure(report: dict[str, Any]) -> None:
    if report.get("self_test_passed") is not True:
        raise SystemExit("self-test failed; refusing to write artifact")


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
            p.relative_to("/tmp")
            storage_class = "tmp_private"
        except ValueError:
            repo_root = Path(__file__).resolve().parent.parent
            try:
                p.relative_to(repo_root / "runs")
                storage_class = "ignored_private"
            except ValueError:
                raise SystemExit("invalid arguments")
        p.mkdir(parents=True, exist_ok=True)
        return p, storage_class
    ts = int(time.time())
    pid = os.getpid()
    p = Path("/tmp") / f"{prefix}_{pid}_{ts}"
    p.mkdir(parents=True, exist_ok=True)
    return p, "tmp_private"


def _private_score_manifest_hash() -> str:
    manifest_schema = {
        "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
        "fields": [
            "phase_run_id", "arm", "task_family",
            "atom_composition", "chosen_file",
            "score_outcome",
            "latency_ms", "cost_usd", "tokens",
            "provider_calls", "failure_reason",
        ],
    }
    canonical = json.dumps(manifest_schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _private_event_manifest_hash() -> str:
    manifest_schema = {
        "schema_version": PRIVATE_EVENT_SCHEMA_VERSION,
        "fields": [
            "phase_run_id", "arm", "task_family",
            "prompt", "response", "parsed_action",
            "chosen_file", "patch",
            "test_stdout", "test_stderr",
            "test_returncode", "provider_metadata",
            "failure_reason",
        ],
    }
    canonical = json.dumps(manifest_schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_private_row(score_path: Path, row: dict[str, Any]) -> None:
    score_path.parent.mkdir(parents=True, exist_ok=True)
    with score_path.open("a", encoding="utf-8") as dst:
        dst.write(json.dumps(row, sort_keys=True) + "\n")

# ---------------------------------------------------------------------------
# Eight fixed allowlisted task families. Reused from B16-F/B16-G/B16-H for
# comparability. The support cue text (``_nondecisive_support_cue_text``)
# is NON-decisive: it gives a formula/invariant/rule that still requires
# target binding to apply. It never contains the exact final answer, the
# exact target-file instruction, or the target-symbol edit instruction.
#
# The ``_decisive_cue_text`` function (used ONLY for the target_plus_support
# arm's full cue) gives the target binding plus the support rule. It is
# private in-memory only (never serialized to the public artifact).
# ---------------------------------------------------------------------------


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
    limit_value = 50 + i * 3
    correct_value = limit_value - 1
    buggy_value = limit_value
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
    helper_a = 5 + i
    helper_b = 8 + i * 2
    correct_value = helper_b * 3
    buggy_value = helper_a * 2
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


def _family_config_or_test_mismatch(i: int) -> dict[str, Any]:
    config_value = 100 + i * 4
    correct_value = config_value
    buggy_value = config_value + 10
    return {
        "task_family": "config_or_test_mismatch",
        "symbol": f"load_config_{i:03d}",
        "target_module": "target.py",
        "distractor_module": "distractor.py",
        "support_module": "config.py",
        "test_module": "test_target.py",
        "helper_constant_name": f"CONFIG_{i:03d}",
        "helper_constant_value": config_value,
        "correct_value": correct_value,
        "buggy_value": buggy_value,
        "fix_kind": "replace_return_value",
        "decisive_cue": "config_source_hint",
    }


def _family_distractor_file(i: int) -> dict[str, Any]:
    base_value = 30 + i * 6
    correct_value = base_value + 5
    buggy_value = -base_value
    return {
        "task_family": "distractor_file",
        "symbol": f"fetch_{i:03d}",
        "target_module": "target.py",
        "distractor_module": "distractor.py",
        "support_module": "support.py",
        "test_module": "test_target.py",
        "helper_constant_name": f"SRC_{i:03d}",
        "helper_constant_value": base_value,
        "correct_value": correct_value,
        "buggy_value": buggy_value,
        "fix_kind": "replace_return_value",
        "decisive_cue": "target_file_hint",
    }


def _family_nearby_wrong_function(i: int) -> dict[str, Any]:
    base_value = 40 + i * 3
    correct_value = base_value * 2
    buggy_value = base_value
    return {
        "task_family": "nearby_wrong_function",
        "symbol": f"process_{i:03d}",
        "target_module": "target.py",
        "distractor_module": "distractor.py",
        "support_module": "support.py",
        "test_module": "test_target.py",
        "helper_constant_name": f"PROC_{i:03d}",
        "helper_constant_value": base_value,
        "correct_value": correct_value,
        "buggy_value": buggy_value,
        "fix_kind": "replace_return_value",
        "decisive_cue": "symbol_cue_hint",
    }


def _family_cross_file_symbol(i: int) -> dict[str, Any]:
    cross_value = 70 + i * 5
    correct_value = cross_value + 1
    buggy_value = cross_value - 1
    return {
        "task_family": "cross_file_symbol",
        "symbol": f"lookup_{i:03d}",
        "target_module": "target.py",
        "distractor_module": "distractor.py",
        "support_module": "cross_file.py",
        "test_module": "test_target.py",
        "helper_constant_name": f"CROSS_{i:03d}",
        "helper_constant_value": cross_value,
        "correct_value": correct_value,
        "buggy_value": buggy_value,
        "fix_kind": "replace_return_value",
        "decisive_cue": "cross_file_source_hint",
    }


_FAMILY_GENERATORS = (
    _family_same_symbol_support_relation,
    _family_operation_ambiguity,
    _family_boundary_condition,
    _family_helper_dependency_choice,
    _family_config_or_test_mismatch,
    _family_distractor_file,
    _family_nearby_wrong_function,
    _family_cross_file_symbol,
)


def _generate_synthetic_tasks(count: int) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for i in range(count):
        family_idx = i % len(_FAMILY_GENERATORS)
        task = _FAMILY_GENERATORS[family_idx](i)
        task["index"] = i
        tasks.append(task)
    return tasks


def _build_workspace(workspace_dir: Path, task: dict[str, Any]) -> None:
    workspace_dir.mkdir(parents=True, exist_ok=True)
    pycache_dir = workspace_dir / "__pycache__"
    if pycache_dir.is_dir():
        shutil.rmtree(pycache_dir, ignore_errors=True)
    target_path = workspace_dir / task["target_module"]
    distractor_path = workspace_dir / task["distractor_module"]
    support_path = workspace_dir / task["support_module"]
    test_path = workspace_dir / task["test_module"]
    family = task["task_family"]
    if family == "helper_dependency_choice":
        support_path.write_text(
            f"{task['helper_constant_name_alt']} = {task['helper_constant_value_alt']}\n"
            f"{task['helper_constant_name']} = {task['helper_constant_value']}\n",
            encoding="utf-8",
        )
    else:
        support_path.write_text(
            f"{task['helper_constant_name']} = {task['helper_constant_value']}\n",
            encoding="utf-8",
        )
    target_path.write_text(
        f"def {task['symbol']}():\n    return {task['buggy_value']}\n",
        encoding="utf-8",
    )
    distractor_path.write_text(
        f"def {task['symbol']}():\n    return {task['buggy_value']}\n",
        encoding="utf-8",
    )
    if family == "same_symbol_support_relation":
        test_body = f"    expected = {task['helper_constant_name']} * 2 + {task['index']}\n"
    elif family == "operation_ambiguity":
        test_body = f"    expected = {task['helper_constant_name']} * 2\n"
    elif family == "boundary_condition":
        test_body = f"    expected = {task['helper_constant_name']} - 1\n"
    elif family == "helper_dependency_choice":
        test_body = f"    expected = {task['helper_constant_name']} * 3\n"
    elif family == "config_or_test_mismatch":
        test_body = f"    expected = {task['helper_constant_name']}\n"
    elif family == "distractor_file":
        test_body = f"    expected = {task['helper_constant_name']} + 5\n"
    elif family == "nearby_wrong_function":
        test_body = f"    expected = {task['helper_constant_name']} * 2\n"
    elif family == "cross_file_symbol":
        test_body = f"    expected = {task['helper_constant_name']} + 1\n"
    else:
        test_body = f"    expected = {task['correct_value']}\n"
    support_module_name = task["support_module"].removesuffix(".py")
    test_path.write_text(
        "import sys\n"
        f"sys.path.insert(0, r'{workspace_dir}')\n"
        f"from target import {task['symbol']}\n"
        f"from {support_module_name} import {task['helper_constant_name']}\n"
        "def main():\n"
        f"{test_body}"
        f"    assert {task['symbol']}() == expected, 'bug not fixed'\n"
        "    return 0\n"
        "if __name__ == '__main__':\n"
        "    sys.exit(main())\n",
        encoding="utf-8",
    )

# ---------------------------------------------------------------------------
# File-choice-safe edit file set (same as B16-H: per-task safe set, no
# global ALLOWED_EDIT_FILES).
# ---------------------------------------------------------------------------


def _safe_edit_files(task: dict[str, Any]) -> frozenset[str]:
    return frozenset(
        {task["target_module"], task["distractor_module"], task["support_module"]}
    )


# ---------------------------------------------------------------------------
# Atom pack builder. Same five-arm structure as B16-H but with
# non-decisive support atoms.
# ---------------------------------------------------------------------------


def _build_pack(arm: str) -> dict[str, Any]:
    if arm == ARM_CONTROL:
        return {
            "arm": arm, "candidate_count": 0, "context_tokens": 20,
            "has_target_file_cue": False, "has_target_symbol_cue": False,
            "has_support_module_cue": False, "has_nondecisive_support_rule": False,
            "has_distractor_file_cue": False, "has_edit_constraint": False,
        }
    if arm == ARM_TARGET_ONLY:
        return {
            "arm": arm, "candidate_count": 1, "context_tokens": 48,
            "has_target_file_cue": True, "has_target_symbol_cue": True,
            "has_support_module_cue": False, "has_nondecisive_support_rule": False,
            "has_distractor_file_cue": False, "has_edit_constraint": True,
        }
    if arm == ARM_SUPPORT_ONLY:
        return {
            "arm": arm, "candidate_count": 1, "context_tokens": 48,
            "has_target_file_cue": False, "has_target_symbol_cue": False,
            "has_support_module_cue": True, "has_nondecisive_support_rule": True,
            "has_distractor_file_cue": False, "has_edit_constraint": True,
        }
    if arm == ARM_DISTRACTOR_PLUS_SUPPORT:
        return {
            "arm": arm, "candidate_count": 2, "context_tokens": 64,
            "has_target_file_cue": False, "has_target_symbol_cue": False,
            "has_support_module_cue": True, "has_nondecisive_support_rule": True,
            "has_distractor_file_cue": True, "has_edit_constraint": True,
        }
    if arm == ARM_TARGET_PLUS_SUPPORT:
        return {
            "arm": arm, "candidate_count": 2, "context_tokens": 64,
            "has_target_file_cue": True, "has_target_symbol_cue": True,
            "has_support_module_cue": True, "has_nondecisive_support_rule": True,
            "has_distractor_file_cue": False, "has_edit_constraint": True,
        }
    return {
        "arm": arm, "candidate_count": 0, "context_tokens": 20,
        "has_target_file_cue": False, "has_target_symbol_cue": False,
        "has_support_module_cue": False, "has_nondecisive_support_rule": False,
        "has_distractor_file_cue": False, "has_edit_constraint": False,
    }


def _build_atom_composition(arm: str) -> list[str]:
    if arm == ARM_CONTROL:
        return []
    if arm == ARM_TARGET_ONLY:
        return ["target_file_cue", "target_symbol_cue"]
    if arm == ARM_SUPPORT_ONLY:
        return ["support_module_cue", "nondecisive_support_rule"]
    if arm == ARM_DISTRACTOR_PLUS_SUPPORT:
        return ["distractor_file_cue", "support_module_cue", "nondecisive_support_rule"]
    if arm == ARM_TARGET_PLUS_SUPPORT:
        return [
            "target_file_cue", "target_symbol_cue",
            "support_module_cue", "nondecisive_support_rule",
        ]
    return []


# ---------------------------------------------------------------------------
# Non-decisive support rule text (private, in-memory only).
#
# KEY DESIGN: the support rule gives a formula/invariant/dependency/config
# relation that STILL REQUIRES TARGET BINDING to apply. It does NOT contain
# the exact final answer, the exact target-file instruction, or the
# target-symbol edit instruction.
#
# The ``_decisive_cue_text`` function (used ONLY for the target_plus_support
# arm) gives the target binding plus the support rule, producing the full
# decisive cue. Both are private in-memory only.
# ---------------------------------------------------------------------------


def _nondecisive_support_cue_text(task: dict[str, Any]) -> str:
    """Non-decisive support rule text (private, in-memory only).

    Gives a formula/invariant/dependency/config relation that still
    requires target binding. NEVER contains the exact final answer,
    the exact target-file instruction, or the target-symbol edit
    instruction.
    """
    family = task["task_family"]
    if family == "same_symbol_support_relation":
        return (
            f"Support invariant: the correct return value is derived as "
            f"helper_constant * 2 + task_index, where helper_constant is "
            f"{task['helper_constant_name']} defined in {task['support_module']}. "
            f"The helper value is {task['helper_constant_value']}. "
            f"You must determine which file applies this relation."
        )
    if family == "operation_ambiguity":
        return (
            f"Support rule: the correct operation is multiplication by 2 "
            f"(not increment by 1). The base value is "
            f"{task['helper_constant_name']} = {task['helper_constant_value']} "
            f"defined in {task['support_module']}. You must determine which "
            f"file applies this operation."
        )
    if family == "boundary_condition":
        return (
            f"Support rule: the limit is an exclusive upper bound; the correct "
            f"value is limit - 1. The limit is {task['helper_constant_name']} = "
            f"{task['helper_constant_value']} defined in {task['support_module']}. "
            f"You must determine which file applies this boundary."
        )
    if family == "helper_dependency_choice":
        return (
            f"Support relation: the correct helper is "
            f"{task['helper_constant_name']} (value {task['helper_constant_value']}) "
            f"not {task['helper_constant_name_alt']} (value "
            f"{task['helper_constant_value_alt']}), both defined in "
            f"{task['support_module']}. The correct value is "
            f"{task['helper_constant_name']} * 3. You must determine which "
            f"file applies this relation."
        )
    if family == "config_or_test_mismatch":
        return (
            f"Support rule: the correct value comes from the config source "
            f"{task['support_module']} where "
            f"{task['helper_constant_name']} = {task['helper_constant_value']}. "
            f"You must determine which file should return this config value."
        )
    if family == "distractor_file":
        return (
            f"Support relation: the correct return value is "
            f"{task['helper_constant_name']} + 5, where "
            f"{task['helper_constant_name']} = {task['helper_constant_value']} "
            f"defined in {task['support_module']}. You must determine which "
            f"file is the correct target (not a same-named decoy)."
        )
    if family == "nearby_wrong_function":
        return (
            f"Support rule: the correct return value is "
            f"{task['helper_constant_name']} * 2, where "
            f"{task['helper_constant_name']} = {task['helper_constant_value']} "
            f"defined in {task['support_module']}. You must determine which "
            f"function (of similarly-named candidates) should return this."
        )
    if family == "cross_file_symbol":
        return (
            f"Support relation: the correct return value is "
            f"{task['helper_constant_name']} + 1, where the helper lives in "
            f"a cross-file module {task['support_module']} "
            f"({task['helper_constant_name']} = {task['helper_constant_value']}). "
            f"You must determine which file should return this value."
        )
    return ""


def _decisive_cue_text(task: dict[str, Any]) -> str:
    """Full decisive cue text (private, in-memory only).

    Used ONLY for the target_plus_support arm. Gives the target binding
    plus the support rule, producing the full decisive cue that should
    allow the agent to solve.
    """
    family = task["task_family"]
    if family == "same_symbol_support_relation":
        return (
            f"Target binding: edit {task['target_module']}, function "
            f"{task['symbol']}. Support invariant: correct_value = "
            f"{task['helper_constant_name']} * 2 + {task['index']}. "
            f"Helper {task['helper_constant_name']} = "
            f"{task['helper_constant_value']} (in {task['support_module']}). "
            f"Correct value: {task['correct_value']}."
        )
    if family == "operation_ambiguity":
        return (
            f"Target binding: edit {task['target_module']}, function "
            f"{task['symbol']}. Support rule: multiply base by 2. "
            f"Base {task['helper_constant_name']} = "
            f"{task['helper_constant_value']} (in {task['support_module']}). "
            f"Correct value: {task['correct_value']}."
        )
    if family == "boundary_condition":
        return (
            f"Target binding: edit {task['target_module']}, function "
            f"{task['symbol']}. Support rule: exclusive upper bound; "
            f"correct = limit - 1. Limit {task['helper_constant_name']} = "
            f"{task['helper_constant_value']} (in {task['support_module']}). "
            f"Correct value: {task['correct_value']}."
        )
    if family == "helper_dependency_choice":
        return (
            f"Target binding: edit {task['target_module']}, function "
            f"{task['symbol']}. Support relation: use "
            f"{task['helper_constant_name']} (value "
            f"{task['helper_constant_value']}) not "
            f"{task['helper_constant_name_alt']}. Correct value = "
            f"{task['helper_constant_name']} * 3 = {task['correct_value']}."
        )
    if family == "config_or_test_mismatch":
        return (
            f"Target binding: edit {task['target_module']}, function "
            f"{task['symbol']}. Support rule: correct value from config "
            f"source {task['support_module']} ({task['helper_constant_name']} "
            f"= {task['helper_constant_value']}). "
            f"Correct value: {task['correct_value']}."
        )
    if family == "distractor_file":
        return (
            f"Target binding: edit {task['target_module']} (not "
            f"{task['distractor_module']}), function {task['symbol']}. "
            f"Support relation: correct = {task['helper_constant_name']} + 5 = "
            f"{task['correct_value']}."
        )
    if family == "nearby_wrong_function":
        return (
            f"Target binding: edit {task['target_module']}, function "
            f"{task['symbol']} (not a similarly-named nearby function). "
            f"Support rule: correct = {task['helper_constant_name']} * 2 = "
            f"{task['correct_value']}."
        )
    if family == "cross_file_symbol":
        return (
            f"Target binding: edit {task['target_module']}, function "
            f"{task['symbol']}. Support relation: helper in cross-file "
            f"module {task['support_module']} ({task['helper_constant_name']} "
            f"= {task['helper_constant_value']}). Correct = "
            f"{task['helper_constant_name']} + 1 = {task['correct_value']}."
        )
    return ""


def _build_messages(
    workspace_dir: Path,
    task: dict[str, Any],
    pack: dict[str, Any],
) -> list[dict[str, str]]:
    """Build the live LLM chat messages (in-memory; never persisted).

    File choice remains enabled: the prompt lists the per-task safe
    file set and lets the agent CHOOSE which file to edit.
    """
    target_path = workspace_dir / task["target_module"]
    distractor_path = workspace_dir / task["distractor_module"]
    support_path = workspace_dir / task["support_module"]
    target_snippet = target_path.read_text(encoding="utf-8")
    support_snippet = support_path.read_text(encoding="utf-8")
    distractor_snippet = distractor_path.read_text(encoding="utf-8")

    safe_files = sorted(_safe_edit_files(task))
    safe_files_str = ", ".join(safe_files)

    system = (
        "You are a minimal coding-agent smoke. "
        "Respond with a single JSON object matching the schema: "
        '{"action": "replace_return_value" | "choose_helper_constant" | "no_op", '
        '"file": "<one of the allowed files>", '
        '"symbol": "<symbol>", '
        '"new_return_value": <int>}. '
        f"The allowed files for this task are: {safe_files_str}. "
        "You must choose which file to edit. Do not include any other text."
    )

    user_lines = [
        f"Bug: function {task['symbol']} returns the wrong value.",
        f"Task family: {task['task_family']}.",
        f"Allowed files you may edit: {safe_files_str}.",
    ]
    if pack.get("has_target_file_cue"):
        user_lines.append(
            f"Target file: {task['target_module']} (not {task['distractor_module']})."
        )
    if pack.get("has_target_symbol_cue"):
        user_lines.append(
            f"Target symbol: {task['symbol']} in {task['target_module']}."
        )
    # Non-decisive support rule (private, in-memory only).
    if pack.get("has_nondecisive_support_rule"):
        if pack.get("has_target_file_cue"):
            # target_plus_support arm: full decisive cue.
            user_lines.append(_decisive_cue_text(task))
        else:
            # support_only or distractor_plus_support arm: non-decisive cue.
            user_lines.append(_nondecisive_support_cue_text(task))
    if pack.get("has_edit_constraint"):
        user_lines.append(
            f"Edit constraint: choose exactly one of {safe_files_str} to edit; "
            "no other files are allowed."
        )
    if pack.get("has_distractor_file_cue"):
        user_lines.append(f"Candidate source (may be wrong file):\n{distractor_snippet}")
    if pack.get("has_target_file_cue"):
        user_lines.append(f"Target source:\n{target_snippet}")
    if pack.get("has_support_module_cue"):
        user_lines.append(f"Support source:\n{support_snippet}")
    user_lines.append("Respond with the JSON edit action only.")

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n".join(user_lines)},
    ]

# ---------------------------------------------------------------------------
# Structured edit action validation and application (same as B16-H).
# ---------------------------------------------------------------------------


def _validate_edit_action(
    action: Any, task: dict[str, Any]
) -> tuple[bool, str]:
    if not isinstance(action, dict):
        return False, "top_level_not_object"
    file_value = action.get("file")
    if file_value not in _safe_edit_files(task):
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


def _categorize_chosen_file(file_value: str, task: dict[str, Any]) -> str:
    if file_value == task["target_module"]:
        return "target"
    if file_value == task["distractor_module"]:
        return "distractor"
    if file_value == task["support_module"]:
        return "support"
    return "none"


def _apply_edit_action(
    workspace_dir: Path, task: dict[str, Any], action: dict[str, Any]
) -> tuple[bool, str, str | None]:
    file_value = action.get("file")
    action_value = action.get("action")
    if action_value == "no_op":
        return False, "no_op", file_value
    if file_value in _safe_edit_files(task):
        edit_path = workspace_dir / str(file_value)
        new_value = action.get("new_return_value")
        new_content = f"def {task['symbol']}():\n    return {new_value}\n"
        edit_path.write_text(new_content, encoding="utf-8")
        if file_value == task["target_module"]:
            return True, "correct_file", file_value
        return False, "wrong_file", file_value
    return False, "wrong_file", file_value


# ---------------------------------------------------------------------------
# Live LLM agent run (one task + arm) with private SCORE/event writers.
# ---------------------------------------------------------------------------


def _run_live_agent(
    workspace_dir: Path,
    task: dict[str, Any],
    pack: dict[str, Any],
    *,
    arm: str,
    allow_remote: bool,
    require_workflow_dispatch: bool,
    phase_run_id: str,
    score_path: Path,
    event_path: Path,
    fake_response: dict[str, Any] | None = None,
    fake_invalid: bool = False,
) -> dict[str, Any]:
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

    parsed_action: dict[str, Any] | None = None
    raw_response_text: str | None = None
    invalid_json = False
    provider_failure_reason: str | None = None
    prompt_tokens = 0
    completion_tokens = 0

    if fake_invalid:
        provider_summary["calls_attempted"] = 1
        provider_summary["calls_succeeded"] = 0
        provider_summary["calls_failed"] = 1
        provider_summary["invalid_json_count"] = 1
        _bump_failure_category(provider_client.FAILURE_CATEGORY_INVALID_JSON)
        invalid_json = True
        raw_response_text = "not-valid-json"
        latency_ms = 1
    elif fake_response is not None:
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
            invalid_json = True
        if result.failure_category == provider_client.FAILURE_CATEGORY_TIMEOUT:
            provider_summary["timeout_count"] += 1
        if result.usage_available and isinstance(result.usage, dict):
            provider_summary["usage_available"] = True
            prompt_tokens = int(result.usage.get("prompt_tokens", 0))
            completion_tokens = int(result.usage.get("completion_tokens", 0))
            provider_summary["prompt_tokens_total"] += prompt_tokens
            provider_summary["completion_tokens_total"] += completion_tokens
            provider_summary["total_tokens_total"] += int(
                result.usage.get("total_tokens", 0)
            )
        raw_response_text = result.raw_content
        if result.calls_succeeded != 1 or result.parsed is None:
            parsed_action = None
            if result.failure_category != provider_client.FAILURE_CATEGORY_OK:
                provider_failure_reason = result.failure_category
        else:
            parsed_action = result.parsed

    tool_calls_before_first_edit = 0
    correct_file_before_first_edit = False
    wrong_file_edits = 0
    patch_applied = False
    no_op = False
    chosen_file_category = "none"
    chosen_file_actual: str | None = None

    if parsed_action is not None:
        valid, reason = _validate_edit_action(parsed_action, task)
        if valid:
            tool_calls_before_first_edit = 1
            edited_correct, kind, cfile = _apply_edit_action(
                workspace_dir, task, parsed_action
            )
            chosen_file_actual = cfile
            chosen_file_category = _categorize_chosen_file(
                cfile if cfile is not None else "", task
            )
            if kind == "correct_file":
                correct_file_before_first_edit = True
                patch_applied = True
            elif kind == "wrong_file":
                wrong_file_edits += 1
                patch_applied = True
            elif kind == "no_op":
                no_op = True

    test_cmd = [sys.executable, str(workspace_dir / task["test_module"])]
    test_start = time.perf_counter()
    test_stdout = ""
    test_stderr = ""
    test_returncode: int | None = None
    try:
        proc = subprocess.run(
            test_cmd, check=False, capture_output=True, text=True, timeout=30,
        )
        tests_pass = proc.returncode == 0
        test_stdout = proc.stdout
        test_stderr = proc.stderr
        test_returncode = proc.returncode
    except (subprocess.TimeoutExpired, OSError):
        tests_pass = False
        test_returncode = -1
    test_latency_ms = max(1, int((time.perf_counter() - test_start) * 1000))

    solve = tests_pass and correct_file_before_first_edit
    provider_failure = provider_summary["calls_failed"] > 0

    score_outcome = {
        "solve": solve,
        "tests_pass": tests_pass,
        "patch_applied": patch_applied,
        "invalid_json": invalid_json,
        "no_op": no_op,
        "provider_failure": provider_failure,
        "correct_file_before_first_edit": correct_file_before_first_edit,
        "wrong_file_edits": wrong_file_edits,
        "chosen_file_category": chosen_file_category,
        "context_tokens": pack.get("context_tokens", 0),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "latency_ms": latency_ms + test_latency_ms,
        "cost_proxy": 0,
    }

    atom_composition = _build_atom_composition(arm)

    private_score_row = {
        "phase_run_id": phase_run_id,
        "arm": arm,
        "task_family": task["task_family"],
        "atom_composition": atom_composition,
        "chosen_file": chosen_file_actual,
        "score_outcome": score_outcome,
        "latency_ms": latency_ms + test_latency_ms,
        "cost_usd": 0.0,
        "tokens": prompt_tokens + completion_tokens,
        "provider_calls": provider_summary["calls_attempted"],
        "failure_reason": provider_failure_reason,
    }
    try:
        _write_private_row(score_path, private_score_row)
    except OSError:
        pass

    private_event_row = {
        "phase_run_id": phase_run_id,
        "arm": arm,
        "task_family": task["task_family"],
        "prompt": _build_messages(workspace_dir, task, pack)[-1]["content"],
        "response": raw_response_text or "",
        "parsed_action": parsed_action,
        "chosen_file": chosen_file_actual,
        "patch": "",
        "test_stdout": test_stdout,
        "test_stderr": test_stderr,
        "test_returncode": test_returncode,
        "provider_metadata": {
            "calls_attempted": provider_summary["calls_attempted"],
            "calls_succeeded": provider_summary["calls_succeeded"],
            "calls_failed": provider_summary["calls_failed"],
            "invalid_json_count": provider_summary["invalid_json_count"],
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "failure_category": (
                list(provider_summary["failure_category_counts"].keys())[-1]
                if provider_summary["failure_category_counts"]
                else "ok"
            ),
        },
        "failure_reason": provider_failure_reason,
    }
    try:
        _write_private_row(event_path, private_event_row)
    except OSError:
        pass

    return {
        "solve": solve,
        "tests_pass": tests_pass,
        "patch_applied": patch_applied,
        "invalid_json": invalid_json,
        "no_op": no_op,
        "provider_failure": provider_failure,
        "correct_file_before_first_edit": correct_file_before_first_edit,
        "wrong_file_edits": wrong_file_edits,
        "chosen_file_category": chosen_file_category,
        "tool_calls_before_first_edit": tool_calls_before_first_edit,
        "context_tokens": pack.get("context_tokens", 0),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "latency_ms": latency_ms + test_latency_ms,
        "cost_proxy": 0,
        "task_family": task["task_family"],
        "arm": arm,
        "provider_summary": provider_summary,
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
    n = len(runs)
    metrics = {
        "run_count": n,
        "solve_rate": _round_metric(_rate(sum(1 for r in runs if r["solve"]), n)),
        "tests_pass_rate": _round_metric(_rate(sum(1 for r in runs if r["tests_pass"]), n)),
        "patch_apply_rate": _round_metric(_rate(sum(1 for r in runs if r["patch_applied"]), n)),
        "correct_file_before_first_edit_rate": _round_metric(
            _rate(sum(1 for r in runs if r["correct_file_before_first_edit"]), n)
        ),
        "wrong_file_edit_rate": _round_metric(
            _rate(sum(1 for r in runs if r["wrong_file_edits"] > 0), n)
        ),
        "selected_target_file_rate": _round_metric(
            _rate(sum(1 for r in runs if r.get("chosen_file_category") == "target"), n)
        ),
        "selected_distractor_file_rate": _round_metric(
            _rate(sum(1 for r in runs if r.get("chosen_file_category") == "distractor"), n)
        ),
        "selected_support_file_rate": _round_metric(
            _rate(sum(1 for r in runs if r.get("chosen_file_category") == "support"), n)
        ),
        "no_op_rate": _round_metric(_rate(sum(1 for r in runs if r["no_op"]), n)),
        "invalid_json_rate": _round_metric(_rate(sum(1 for r in runs if r["invalid_json"]), n)),
        "provider_failure_rate": _round_metric(_rate(sum(1 for r in runs if r["provider_failure"]), n)),
        "context_tokens_mean": _round_metric(_mean([r["context_tokens"] for r in runs])),
        "prompt_tokens_total": int(sum(r["prompt_tokens"] for r in runs)),
        "completion_tokens_total": int(sum(r["completion_tokens"] for r in runs)),
        "latency_seconds_mean": _round_metric(_mean([r["latency_ms"] for r in runs]) / 1000.0),
        "cost_proxy_total": _round_metric(sum(r["cost_proxy"] for r in runs)),
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
        provider_summary["calls_attempted"] += int(ps.get("calls_attempted", 0))
        provider_summary["calls_succeeded"] += int(ps.get("calls_succeeded", 0))
        provider_summary["calls_failed"] += int(ps.get("calls_failed", 0))
        provider_summary["invalid_json_count"] += int(ps.get("invalid_json_count", 0))
        provider_summary["timeout_count"] += int(ps.get("timeout_count", 0))
        provider_summary["latency_ms_total"] += int(ps.get("latency_ms_total", 0))
        if ps.get("usage_available"):
            provider_summary["usage_available"] = True
        provider_summary["prompt_tokens_total"] += int(ps.get("prompt_tokens_total", 0))
        provider_summary["completion_tokens_total"] += int(ps.get("completion_tokens_total", 0))
        provider_summary["total_tokens_total"] += int(ps.get("total_tokens_total", 0))
        for cat, cnt in ps.get("failure_category_counts", {}).items():
            provider_summary["failure_category_counts"][cat] = (
                provider_summary["failure_category_counts"].get(cat, 0) + int(cnt)
            )
    return metrics, provider_summary


def _aggregate_family_results(
    arm_runs: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    family_results: list[dict[str, Any]] = []
    for family in TASK_FAMILIES:
        for arm in ARMS:
            runs = [r for r in arm_runs[arm] if r.get("task_family") == family]
            n = len(runs)
            family_results.append(
                {
                    "task_family": family,
                    "arm": arm,
                    "run_count": n,
                    "solve_rate": _round_metric(_rate(sum(1 for r in runs if r["solve"]), n)),
                    "tests_pass_rate": _round_metric(_rate(sum(1 for r in runs if r["tests_pass"]), n)),
                }
            )
    return family_results


def _compute_paired_deltas(
    arm_metrics_by_arm: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for baseline_arm, treatment_arm in ALL_CONTRASTS:
        baseline = arm_metrics_by_arm[baseline_arm]
        treatment = arm_metrics_by_arm[treatment_arm]
        for name in DELTA_METRIC_NAMES:
            records.append(
                {
                    "baseline_arm": baseline_arm,
                    "treatment_arm": treatment_arm,
                    "metric": name,
                    "delta": _round_metric(treatment[name] - baseline[name]),
                }
            )
    return records


def _compute_mechanism_summary_records(
    arm_runs: dict[str, list[dict[str, Any]]],
    task_count: int,
) -> list[dict[str, Any]]:
    """B16-I mechanism summary records (counts only).

    - target_support_conjunction_required_count: tasks where
      target_plus_support solved but NEITHER target_only NOR
      support_only solved (conjunction was required).
    - support_only_sufficient_count: tasks where support_only solved.
    - target_only_sufficient_count: tasks where target_only solved.
    - distractor_hurts_count: tasks where distractor_plus_support did
      NOT solve but target_plus_support DID.
    - wrong_file_selection_count: tasks where any context arm selected
      a non-target file.
    - all_arms_solved_count: tasks where all 5 arms solved.
    - sparse_solved_count: tasks where control_sparse solved.
    """
    if task_count <= 0:
        return []
    conjunction_required = 0
    support_sufficient = 0
    target_sufficient = 0
    distractor_hurts = 0
    wrong_file_selection = 0
    all_arms_solved = 0
    sparse_solved = 0
    for i in range(task_count):
        per_arm_solve: dict[str, bool] = {}
        per_arm_wrong: dict[str, bool] = {}
        for arm in ARMS:
            runs = arm_runs[arm]
            if i < len(runs):
                per_arm_solve[arm] = bool(runs[i].get("solve"))
                per_arm_wrong[arm] = bool(runs[i].get("wrong_file_edits", 0) > 0) or (
                    runs[i].get("chosen_file_category") in ("distractor", "support")
                )
            else:
                per_arm_solve[arm] = False
                per_arm_wrong[arm] = False
        if (
            per_arm_solve[ARM_TARGET_PLUS_SUPPORT]
            and not per_arm_solve[ARM_TARGET_ONLY]
            and not per_arm_solve[ARM_SUPPORT_ONLY]
        ):
            conjunction_required += 1
        if per_arm_solve[ARM_SUPPORT_ONLY]:
            support_sufficient += 1
        if per_arm_solve[ARM_TARGET_ONLY]:
            target_sufficient += 1
        if (
            not per_arm_solve[ARM_DISTRACTOR_PLUS_SUPPORT]
            and per_arm_solve[ARM_TARGET_PLUS_SUPPORT]
        ):
            distractor_hurts += 1
        for arm in (ARM_TARGET_ONLY, ARM_SUPPORT_ONLY, ARM_DISTRACTOR_PLUS_SUPPORT, ARM_TARGET_PLUS_SUPPORT):
            if per_arm_wrong.get(arm):
                wrong_file_selection += 1
                break
        if all(per_arm_solve[arm] for arm in ARMS):
            all_arms_solved += 1
        if per_arm_solve[ARM_CONTROL]:
            sparse_solved += 1
    return [
        {"mechanism_field": "target_support_conjunction_required_count", "value": conjunction_required, "record_count": task_count},
        {"mechanism_field": "support_only_sufficient_count", "value": support_sufficient, "record_count": task_count},
        {"mechanism_field": "target_only_sufficient_count", "value": target_sufficient, "record_count": task_count},
        {"mechanism_field": "distractor_hurts_count", "value": distractor_hurts, "record_count": task_count},
        {"mechanism_field": "wrong_file_selection_count", "value": wrong_file_selection, "record_count": task_count},
        {"mechanism_field": "all_arms_solved_count", "value": all_arms_solved, "record_count": task_count},
        {"mechanism_field": "sparse_solved_count", "value": sparse_solved, "record_count": task_count},
    ]


def _compute_honest_signals(
    arm_metrics_by_arm: dict[str, dict[str, Any]],
    mechanism_summary_records: list[dict[str, Any]],
) -> dict[str, Any]:
    mech = {r["mechanism_field"]: r["value"] for r in mechanism_summary_records}
    tps = arm_metrics_by_arm[ARM_TARGET_PLUS_SUPPORT]
    dps = arm_metrics_by_arm[ARM_DISTRACTOR_PLUS_SUPPORT]
    so = arm_metrics_by_arm[ARM_SUPPORT_ONLY]
    to = arm_metrics_by_arm[ARM_TARGET_ONLY]
    ctrl = arm_metrics_by_arm[ARM_CONTROL]
    conjunction_signal = (
        tps.get("solve_rate", 0.0) > so.get("solve_rate", 0.0)
        and tps.get("solve_rate", 0.0) > to.get("solve_rate", 0.0)
    )
    distractor_signal = (
        tps.get("solve_rate", 0.0) > dps.get("solve_rate", 0.0)
        or tps.get("selected_target_file_rate", 0.0) > dps.get("selected_target_file_rate", 0.0)
    )
    return {
        "target_support_conjunction_signal_observed": bool(conjunction_signal),
        "distractor_hurts_signal_observed": bool(distractor_signal),
        "target_support_conjunction_required_count": int(mech.get("target_support_conjunction_required_count", 0)),
        "support_only_sufficient_count": int(mech.get("support_only_sufficient_count", 0)),
        "target_only_sufficient_count": int(mech.get("target_only_sufficient_count", 0)),
        "distractor_hurts_count": int(mech.get("distractor_hurts_count", 0)),
        "wrong_file_selection_count": int(mech.get("wrong_file_selection_count", 0)),
        "all_arms_solved_count": int(mech.get("all_arms_solved_count", 0)),
        "sparse_solved_count": int(mech.get("sparse_solved_count", 0)),
        "target_plus_support_solve_rate": _round_metric(tps.get("solve_rate", 0.0)),
        "distractor_plus_support_solve_rate": _round_metric(dps.get("solve_rate", 0.0)),
        "support_only_solve_rate": _round_metric(so.get("solve_rate", 0.0)),
        "target_only_solve_rate": _round_metric(to.get("solve_rate", 0.0)),
        "control_sparse_solve_rate": _round_metric(ctrl.get("solve_rate", 0.0)),
        "target_plus_support_selected_target_file_rate": _round_metric(tps.get("selected_target_file_rate", 0.0)),
        "distractor_plus_support_selected_target_file_rate": _round_metric(dps.get("selected_target_file_rate", 0.0)),
    }


def _determine_live_status(
    paired_run_completed: bool,
    any_provider_call_failed: bool,
    any_parse_failed: bool,
) -> str:
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
    mechanism_summary_records: list[dict[str, Any]] | None = None,
    honest_signals: dict[str, Any] | None = None,
    input_summary: dict[str, Any] | None = None,
    private_score_manifest: dict[str, Any] | None = None,
    private_event_manifest: dict[str, Any] | None = None,
    model_display_category: str = "unavailable",
    live_run_executed: bool = False,
) -> dict[str, Any]:
    """Assemble the public aggregate-only report (fail-closed scan).

    NOTE: B16-I uses counts-only self-test fields:
    ``self_test_checks_total`` and ``self_test_checks_passed``. It does
    NOT publish ``self_test_summary`` or ``self_test_checks`` list.
    """
    arm_results = arm_results or []
    paired_deltas = paired_deltas or []
    task_family_results = task_family_results or []
    mechanism_summary_records = mechanism_summary_records or []
    honest_signals_out = honest_signals or {}
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
        "primary_contrasts": [f"{t}_vs_{b}" for b, t in PRIMARY_CONTRASTS],
        "secondary_contrasts": [f"{t}_vs_{b}" for b, t in SECONDARY_CONTRASTS],
        "file_choice_confound_removed": True,
        "support_cue_nondecisive": True,
    }
    private_score_manifest = private_score_manifest or {
        "records_written": False,
        "record_count": 0,
        "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
        "manifest_hash": _private_score_manifest_hash(),
        "storage_class": "tmp_private",
        "path_publicly_serialized": False,
    }
    private_event_manifest = private_event_manifest or {
        "records_written": False,
        "record_count": 0,
        "schema_version": PRIVATE_EVENT_SCHEMA_VERSION,
        "manifest_hash": _private_event_manifest_hash(),
        "storage_class": "tmp_private",
        "path_publicly_serialized": False,
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
        "mechanism_summary_records": mechanism_summary_records,
        "honest_signals": honest_signals_out,
        "private_score_manifest": private_score_manifest,
        "private_event_manifest": private_event_manifest,
        **DEFAULT_FALSE_FLAGS,
        "aggregate_only_public_artifact": True,
        "diagnostic_only": True,
        # Counts-only self-test fields (NO self_test_summary, NO
        # self_test_checks list).
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c.get("passed")),
        "self_test_passed": all_passed,
    }

    if live_run_executed:
        for flag in LIVE_TRUE_FLAGS:
            report[flag] = True
    else:
        for flag in LIVE_TRUE_FLAGS:
            if flag not in ("aggregate_only_public_artifact", "diagnostic_only"):
                report[flag] = False

    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_LEAK
    return report


def _normalize_model_display(raw_model: str) -> str:
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


def build_report(
    task_count: int,
    *,
    allow_remote: bool,
    require_workflow_dispatch: bool,
    private_score_dir: str | None = None,
    private_event_dir: str | None = None,
) -> dict[str, Any]:
    checks, all_passed = run_self_test_checks()

    enabled, failure_category = provider_client._check_remote_enabled(
        allow_remote=allow_remote,
        require_workflow_dispatch=require_workflow_dispatch,
    )

    if not enabled:
        if failure_category in (provider_client.FAILURE_CATEGORY_MISSING_ENV,):
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
            "primary_contrasts": [f"{t}_vs_{b}" for b, t in PRIMARY_CONTRASTS],
            "secondary_contrasts": [f"{t}_vs_{b}" for b, t in SECONDARY_CONTRASTS],
            "file_choice_confound_removed": True,
            "support_cue_nondecisive": True,
        }
        return _build_public_report(
            checks,
            all_passed,
            status=status,
            arm_results=[],
            paired_deltas=[],
            task_family_results=[],
            mechanism_summary_records=[],
            honest_signals={},
            input_summary=input_summary,
            private_score_manifest={
                "records_written": False,
                "record_count": 0,
                "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
                "manifest_hash": _private_score_manifest_hash(),
                "storage_class": "tmp_private",
                "path_publicly_serialized": False,
            },
            private_event_manifest={
                "records_written": False,
                "record_count": 0,
                "schema_version": PRIVATE_EVENT_SCHEMA_VERSION,
                "manifest_hash": _private_event_manifest_hash(),
                "storage_class": "tmp_private",
                "path_publicly_serialized": False,
            },
            model_display_category="unavailable",
            live_run_executed=False,
        )

    score_dir, score_storage = _resolve_private_dir(private_score_dir, "b16i_private_score")
    event_dir, event_storage = _resolve_private_dir(private_event_dir, "b16i_private_event")
    score_path = score_dir / "b16i_private_score.jsonl"
    event_path = event_dir / "b16i_private_event.jsonl"
    score_path.write_text("", encoding="utf-8")
    event_path.write_text("", encoding="utf-8")
    phase_run_id = f"b16i_{int(time.time())}_{os.getpid()}"

    tasks = _generate_synthetic_tasks(task_count)
    arm_runs: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    any_provider_call_failed = False
    any_parse_failed = False
    score_rows_written = 0
    event_rows_written = 0

    for task in tasks:
        for arm in ARMS:
            pack = _build_pack(arm)
            workspace_dir = Path(tempfile.mkdtemp(prefix="b16i_workspace_"))
            try:
                _build_workspace(workspace_dir, task)
                run = _run_live_agent(
                    workspace_dir, task, pack,
                    arm=arm,
                    allow_remote=allow_remote,
                    require_workflow_dispatch=require_workflow_dispatch,
                    phase_run_id=phase_run_id,
                    score_path=score_path,
                    event_path=event_path,
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
            if run["invalid_json"]:
                any_parse_failed = True
            score_rows_written += 1
            event_rows_written += 1

    arm_metrics_by_arm: dict[str, dict[str, Any]] = {}
    arm_results: list[dict[str, Any]] = []
    for arm in ARMS:
        metrics, provider_summary = _aggregate_arm_metrics(arm_runs[arm])
        arm_metrics_by_arm[arm] = metrics
        arm_results.append(
            {
                "arm": arm,
                "metrics": metrics,
                "provider_summary": provider_summary,
                "failure_category_counts": provider_summary.get("failure_category_counts", {}),
            }
        )

    paired_deltas = _compute_paired_deltas(arm_metrics_by_arm)
    task_family_results = _aggregate_family_results(arm_runs)
    mechanism_summary_records = _compute_mechanism_summary_records(arm_runs, task_count)
    honest_signals = _compute_honest_signals(arm_metrics_by_arm, mechanism_summary_records)

    status = _determine_live_status(
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
        "primary_contrasts": [f"{t}_vs_{b}" for b, t in PRIMARY_CONTRASTS],
        "secondary_contrasts": [f"{t}_vs_{b}" for b, t in SECONDARY_CONTRASTS],
        "file_choice_confound_removed": True,
        "support_cue_nondecisive": True,
    }

    raw_model = os.environ.get(provider_client.ENV_MODEL, "")
    model_display_category = _normalize_model_display(raw_model)

    private_score_manifest = {
        "records_written": score_rows_written > 0,
        "record_count": int(score_rows_written),
        "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
        "manifest_hash": _private_score_manifest_hash(),
        "storage_class": score_storage,
        "path_publicly_serialized": False,
    }
    private_event_manifest = {
        "records_written": event_rows_written > 0,
        "record_count": int(event_rows_written),
        "schema_version": PRIVATE_EVENT_SCHEMA_VERSION,
        "manifest_hash": _private_event_manifest_hash(),
        "storage_class": event_storage,
        "path_publicly_serialized": False,
    }

    return _build_public_report(
        checks, all_passed,
        status=status,
        arm_results=arm_results,
        paired_deltas=paired_deltas,
        task_family_results=task_family_results,
        mechanism_summary_records=mechanism_summary_records,
        honest_signals=honest_signals,
        input_summary=input_summary,
        private_score_manifest=private_score_manifest,
        private_event_manifest=private_event_manifest,
        model_display_category=model_display_category,
        live_run_executed=True,
    )

# ---------------------------------------------------------------------------
# Env-preservation self-test helpers
# ---------------------------------------------------------------------------


def _probe_missing_env_without_mutating_remote_env() -> tuple[bool, str, bool]:
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
    """Run all B16-I self-test groups (no network)."""
    checks: list[dict[str, Any]] = []

    # --- Group 1: Artifact identity fields. ---
    skeleton = _build_public_report([], False, status=STATUS_UNAVAILABLE)
    checks.append(_check("schema_version_correct", skeleton["schema_version"] == SCHEMA_VERSION))
    checks.append(_check("claim_level_correct", skeleton["claim_level"] == CLAIM_LEVEL))
    checks.append(_check("mode_correct", skeleton["mode"] == MODE))
    checks.append(_check("phase_correct", skeleton["phase"] == PHASE))
    checks.append(_check("generated_by_correct", skeleton["generated_by"] == GENERATED_BY))
    checks.append(_check("arms_count_is_5", len(ARMS) == 5))
    checks.append(_check("task_families_count_is_8", len(TASK_FAMILIES) == 8))
    checks.append(_check("default_task_count_is_8", DEFAULT_TASK_COUNT == 8))
    checks.append(_check("max_live_calls_is_60", MAX_LIVE_CALLS == 60))
    checks.append(_check("primary_contrasts_count_is_3", len(PRIMARY_CONTRASTS) == 3))
    checks.append(_check("secondary_contrasts_count_is_5", len(SECONDARY_CONTRASTS) == 5))
    checks.append(_check("all_contrasts_count_is_8", len(ALL_CONTRASTS) == 8))
    checks.append(_check("file_choice_confound_removed_flag", skeleton["input_summary"].get("file_choice_confound_removed") is True))
    checks.append(_check("support_cue_nondecisive_flag", skeleton["input_summary"].get("support_cue_nondecisive") is True))
    checks.append(_check("no_global_allowed_edit_files_set", "ALLOWED_EDIT_FILES" not in dir()))
    # Counts-only self-test fields (NO self_test_summary, NO self_test_checks list).
    checks.append(_check("no_self_test_summary_key", "self_test_summary" not in skeleton))
    checks.append(_check("no_self_test_checks_list_key", "self_test_checks" not in skeleton))
    checks.append(_check("self_test_checks_total_is_int", isinstance(skeleton.get("self_test_checks_total"), int)))
    checks.append(_check("self_test_checks_passed_is_int", isinstance(skeleton.get("self_test_checks_passed"), int)))
    for status in ALL_STATUSES:
        rep = _build_public_report([], False, status=status)
        checks.append(_check(f"status_{status}_preserved", rep["status"] == status))

    # --- Group 2: Always-false no-claim flags. ---
    for flag in DEFAULT_FALSE_FLAGS:
        checks.append(_check(f"default_false_{flag}", skeleton.get(flag) is False))
    checks.append(_check("bea_superiority_flag_false", skeleton.get("bea_superiority_claimed") is False))

    # --- Group 3: Live-run flag gating. ---
    for flag in LIVE_TRUE_FLAGS:
        if flag in ("aggregate_only_public_artifact", "diagnostic_only"):
            continue
        checks.append(_check(f"unavailable_live_flag_false_{flag}", skeleton.get(flag) is False))
    live_rep = _build_public_report([], True, status=STATUS_PASS, live_run_executed=True)
    for flag in LIVE_TRUE_FLAGS:
        checks.append(_check(f"live_flag_true_{flag}", live_rep.get(flag) is True))

    # --- Group 4: Eight task families generation. ---
    tasks_8 = _generate_synthetic_tasks(8)
    checks.append(_check("synthetic_task_count_correct", len(tasks_8) == 8))
    family_counts: dict[str, int] = {}
    for t in tasks_8:
        family_counts[t["task_family"]] = family_counts.get(t["task_family"], 0) + 1
    for family in TASK_FAMILIES:
        checks.append(_check(f"family_present_{family}", family in family_counts and family_counts[family] >= 1))
    checks.append(_check("families_balanced_1_each_for_8_tasks", all(family_counts.get(f, 0) == 1 for f in TASK_FAMILIES)))

    # --- Group 5: Workspace builder per family + safe file set. ---
    workspace_dir = Path(tempfile.mkdtemp(prefix="b16i_selftest_"))
    try:
        for family_task in tasks_8:
            _build_workspace(workspace_dir, family_task)
            target_path = workspace_dir / family_task["target_module"]
            distractor_path = workspace_dir / family_task["distractor_module"]
            support_path = workspace_dir / family_task["support_module"]
            test_path = workspace_dir / family_task["test_module"]
            checks.append(_check(f"workspace_{family_task['task_family']}_creates_target", target_path.is_file()))
            checks.append(_check(f"workspace_{family_task['task_family']}_creates_distractor", distractor_path.is_file()))
            checks.append(_check(f"workspace_{family_task['task_family']}_creates_support", support_path.is_file()))
            checks.append(_check(f"workspace_{family_task['task_family']}_creates_test", test_path.is_file()))
            proc_before = subprocess.run([sys.executable, str(test_path)], check=False, capture_output=True, text=True, timeout=30)
            checks.append(_check(f"workspace_{family_task['task_family']}_test_fails_before_fix", proc_before.returncode != 0))
            safe = _safe_edit_files(family_task)
            checks.append(_check(f"safe_files_{family_task['task_family']}_includes_target", family_task["target_module"] in safe))
            checks.append(_check(f"safe_files_{family_task['task_family']}_includes_distractor", family_task["distractor_module"] in safe))
            checks.append(_check(f"safe_files_{family_task['task_family']}_includes_support", family_task["support_module"] in safe))

        # --- Group 6: Pack builder atoms per arm. ---
        ctrl_pack = _build_pack(ARM_CONTROL)
        to_pack = _build_pack(ARM_TARGET_ONLY)
        so_pack = _build_pack(ARM_SUPPORT_ONLY)
        dps_pack = _build_pack(ARM_DISTRACTOR_PLUS_SUPPORT)
        tps_pack = _build_pack(ARM_TARGET_PLUS_SUPPORT)
        checks.append(_check("control_pack_has_no_atoms", not ctrl_pack["has_target_file_cue"] and not ctrl_pack["has_support_module_cue"] and not ctrl_pack["has_nondecisive_support_rule"]))
        checks.append(_check("target_only_has_target_cue", to_pack["has_target_file_cue"] is True and to_pack["has_target_symbol_cue"] is True))
        checks.append(_check("target_only_lacks_support", to_pack["has_support_module_cue"] is False and to_pack["has_nondecisive_support_rule"] is False))
        checks.append(_check("support_only_has_support_and_nondecisive_rule", so_pack["has_support_module_cue"] is True and so_pack["has_nondecisive_support_rule"] is True))
        checks.append(_check("support_only_lacks_target", so_pack["has_target_file_cue"] is False and so_pack["has_target_symbol_cue"] is False))
        checks.append(_check("distractor_plus_support_has_distractor", dps_pack["has_distractor_file_cue"] is True))
        checks.append(_check("distractor_plus_support_has_support_and_nondecisive_rule", dps_pack["has_support_module_cue"] is True and dps_pack["has_nondecisive_support_rule"] is True))
        checks.append(_check("distractor_plus_support_lacks_target", dps_pack["has_target_file_cue"] is False and dps_pack["has_target_symbol_cue"] is False))
        checks.append(_check("target_plus_support_has_all_atoms", tps_pack["has_target_file_cue"] is True and tps_pack["has_target_symbol_cue"] is True and tps_pack["has_support_module_cue"] is True and tps_pack["has_nondecisive_support_rule"] is True))
        checks.append(_check("target_plus_support_no_distractor", tps_pack["has_distractor_file_cue"] is False))

        # --- Group 7: Atom composition private list. ---
        ctrl_atoms = _build_atom_composition(ARM_CONTROL)
        to_atoms = _build_atom_composition(ARM_TARGET_ONLY)
        so_atoms = _build_atom_composition(ARM_SUPPORT_ONLY)
        dps_atoms = _build_atom_composition(ARM_DISTRACTOR_PLUS_SUPPORT)
        tps_atoms = _build_atom_composition(ARM_TARGET_PLUS_SUPPORT)
        checks.append(_check("control_atoms_empty", ctrl_atoms == []))
        checks.append(_check("target_only_atoms_2", len(to_atoms) == 2 and "target_file_cue" in to_atoms and "target_symbol_cue" in to_atoms))
        checks.append(_check("support_only_atoms_2", len(so_atoms) == 2 and "support_module_cue" in so_atoms and "nondecisive_support_rule" in so_atoms))
        checks.append(_check("distractor_plus_support_atoms_3", len(dps_atoms) == 3 and "distractor_file_cue" in dps_atoms and "support_module_cue" in dps_atoms and "nondecisive_support_rule" in dps_atoms))
        checks.append(_check("target_plus_support_atoms_4", len(tps_atoms) == 4 and "target_file_cue" in tps_atoms and "target_symbol_cue" in tps_atoms and "support_module_cue" in tps_atoms and "nondecisive_support_rule" in tps_atoms))

        # --- Group 8: Non-decisive support cue text (no exact answer/target-file instruction). ---
        f1 = tasks_8[0]
        for family_task in tasks_8:
            nd_cue = _nondecisive_support_cue_text(family_task)
            checks.append(_check(f"nondecisive_cue_nonempty_{family_task['task_family']}", len(nd_cue) > 0))
            # Non-decisive cue must NOT contain the exact final answer string.
            checks.append(_check(f"nondecisive_cue_no_exact_answer_{family_task['task_family']}", f"Correct value: {family_task['correct_value']}" not in nd_cue))
            # Non-decisive cue must NOT contain the exact target-file instruction.
            checks.append(_check(f"nondecisive_cue_no_target_file_instruction_{family_task['task_family']}", f"edit {family_task['target_module']}" not in nd_cue.lower() or "you must determine" in nd_cue.lower()))
            # Decisive cue (target_plus_support) DOES contain the exact answer value.
            d_cue = _decisive_cue_text(family_task)
            checks.append(_check(f"decisive_cue_has_exact_answer_{family_task['task_family']}", str(family_task['correct_value']) in d_cue))

        # --- Group 9: File-choice validator (accepts safe files; rejects evil.py). ---
        valid, reason = _validate_edit_action({"action": "replace_return_value", "file": "evil.py", "symbol": "x", "new_return_value": 1}, f1)
        checks.append(_check("validator_rejects_evil_py", not valid and reason == "disallowed_file"))
        valid, reason = _validate_edit_action({"action": "replace_return_value", "file": "target.py", "symbol": "x", "new_return_value": 1}, f1)
        checks.append(_check("validator_accepts_target_py", valid))
        valid, reason = _validate_edit_action({"action": "replace_return_value", "file": "distractor.py", "symbol": "x", "new_return_value": 1}, f1)
        checks.append(_check("validator_accepts_distractor_py", valid))
        valid, reason = _validate_edit_action({"action": "replace_return_value", "file": "support.py", "symbol": "x", "new_return_value": 1}, f1)
        checks.append(_check("validator_accepts_support_py", valid))
        f5 = next(t for t in tasks_8 if t["task_family"] == "config_or_test_mismatch")
        valid, reason = _validate_edit_action({"action": "replace_return_value", "file": "config.py", "symbol": "x", "new_return_value": 1}, f5)
        checks.append(_check("validator_accepts_config_py_for_config_family", valid))
        f8 = next(t for t in tasks_8 if t["task_family"] == "cross_file_symbol")
        valid, reason = _validate_edit_action({"action": "replace_return_value", "file": "cross_file.py", "symbol": "x", "new_return_value": 1}, f8)
        checks.append(_check("validator_accepts_cross_file_py_for_cross_file_family", valid))
        valid, reason = _validate_edit_action({"action": "shell_exec", "file": "target.py", "symbol": "x", "new_return_value": 1}, f1)
        checks.append(_check("validator_rejects_disallowed_action", not valid))
        valid, reason = _validate_edit_action({"action": "no_op", "file": "target.py", "symbol": "x"}, f1)
        checks.append(_check("validator_accepts_no_op", valid))

        # --- Group 10: Chosen-file categorization. ---
        checks.append(_check("categorize_target", _categorize_chosen_file("target.py", f1) == "target"))
        checks.append(_check("categorize_distractor", _categorize_chosen_file("distractor.py", f1) == "distractor"))
        checks.append(_check("categorize_support", _categorize_chosen_file("support.py", f1) == "support"))
        checks.append(_check("categorize_none", _categorize_chosen_file("evil.py", f1) == "none"))

        # --- Group 11: Private SCORE/event writers + fake responses. ---
        score_dir, score_storage = _resolve_private_dir(None, "b16i_selftest_score")
        event_dir, event_storage = _resolve_private_dir(None, "b16i_selftest_event")
        score_path = score_dir / "b16i_selftest_score.jsonl"
        event_path = event_dir / "b16i_selftest_event.jsonl"
        score_path.write_text("", encoding="utf-8")
        event_path.write_text("", encoding="utf-8")

        # Fake valid target_plus_support: solves, chose target.py.
        _build_workspace(workspace_dir, f1)
        run_tps_solve = _run_live_agent(workspace_dir, f1, tps_pack, arm=ARM_TARGET_PLUS_SUPPORT, allow_remote=False, require_workflow_dispatch=False, phase_run_id="b16i_selftest", score_path=score_path, event_path=event_path, fake_response={"action": "replace_return_value", "file": "target.py", "symbol": f1["symbol"], "new_return_value": f1["correct_value"]})
        checks.append(_check("tps_solve_correct_file", run_tps_solve["correct_file_before_first_edit"] is True))
        checks.append(_check("tps_solve_tests_pass", run_tps_solve["tests_pass"] is True))
        checks.append(_check("tps_solve_solve", run_tps_solve["solve"] is True))
        checks.append(_check("tps_chose_target_category", run_tps_solve["chosen_file_category"] == "target"))

        # Fake support_only chose distractor.py (wrong file, no solve).
        _build_workspace(workspace_dir, f1)
        run_so_wrong = _run_live_agent(workspace_dir, f1, so_pack, arm=ARM_SUPPORT_ONLY, allow_remote=False, require_workflow_dispatch=False, phase_run_id="b16i_selftest", score_path=score_path, event_path=event_path, fake_response={"action": "replace_return_value", "file": "distractor.py", "symbol": f1["symbol"], "new_return_value": f1["buggy_value"]})
        checks.append(_check("so_wrong_file_no_solve", run_so_wrong["solve"] is False))
        checks.append(_check("so_wrong_file_wrong_edits", run_so_wrong["wrong_file_edits"] == 1))
        checks.append(_check("so_chose_distractor_category", run_so_wrong["chosen_file_category"] == "distractor"))

        # Fake control no_op.
        _build_workspace(workspace_dir, f1)
        run_ctrl_noop = _run_live_agent(workspace_dir, f1, ctrl_pack, arm=ARM_CONTROL, allow_remote=False, require_workflow_dispatch=False, phase_run_id="b16i_selftest", score_path=score_path, event_path=event_path, fake_response={"action": "no_op", "file": "target.py", "symbol": f1["symbol"]})
        checks.append(_check("control_no_op_executed", run_ctrl_noop["tool_calls_before_first_edit"] == 1))
        checks.append(_check("control_no_op_tests_fail", run_ctrl_noop["tests_pass"] is False))
        checks.append(_check("control_no_op_no_op_flag", run_ctrl_noop["no_op"] is True))

        # Fake invalid JSON.
        _build_workspace(workspace_dir, f1)
        run_invalid = _run_live_agent(workspace_dir, f1, ctrl_pack, arm=ARM_CONTROL, allow_remote=False, require_workflow_dispatch=False, phase_run_id="b16i_selftest", score_path=score_path, event_path=event_path, fake_invalid=True)
        checks.append(_check("invalid_json_no_edit", run_invalid["tool_calls_before_first_edit"] == 0))
        checks.append(_check("invalid_json_flag_set", run_invalid["invalid_json"] is True))
        checks.append(_check("no_raw_response_in_run_result", not any(k in run_invalid for k in ("raw_response", "response", "messages", "prompt", "chosen_file"))))

        # Private rows written (4 runs = 4 rows each).
        score_lines = score_path.read_text(encoding="utf-8").splitlines()
        event_lines = event_path.read_text(encoding="utf-8").splitlines()
        checks.append(_check("private_score_rows_4", len(score_lines) == 4))
        checks.append(_check("private_event_rows_4", len(event_lines) == 4))
        for i, line in enumerate(score_lines):
            try:
                row = json.loads(line)
                checks.append(_check(f"score_row_{i}_has_atoms_and_chosen_file", "atom_composition" in row and "chosen_file" in row and "score_outcome" in row))
            except (json.JSONDecodeError, ValueError):
                checks.append(_check(f"score_row_{i}_has_atoms_and_chosen_file", False))
        for i, line in enumerate(event_lines):
            try:
                row = json.loads(line)
                checks.append(_check(f"event_row_{i}_has_prompt_response_chosen_file", "prompt" in row and "response" in row and "chosen_file" in row))
            except (json.JSONDecodeError, ValueError):
                checks.append(_check(f"event_row_{i}_has_prompt_response_chosen_file", False))

        # --- Group 12: Aggregate metrics + file-choice rates + paired deltas + mechanism. ---
        arm_runs_test: dict[str, list[dict[str, Any]]] = {
            ARM_CONTROL: [run_ctrl_noop],
            ARM_TARGET_ONLY: [run_ctrl_noop],
            ARM_SUPPORT_ONLY: [run_so_wrong],
            ARM_DISTRACTOR_PLUS_SUPPORT: [run_so_wrong],
            ARM_TARGET_PLUS_SUPPORT: [run_tps_solve],
        }
        arm_metrics_map: dict[str, dict[str, Any]] = {}
        for arm in ARMS:
            m, _ = _aggregate_arm_metrics(arm_runs_test[arm])
            arm_metrics_map[arm] = m
        checks.append(_check("tps_solve_rate_1", arm_metrics_map[ARM_TARGET_PLUS_SUPPORT]["solve_rate"] == 1.0))
        checks.append(_check("control_solve_rate_0", arm_metrics_map[ARM_CONTROL]["solve_rate"] == 0.0))
        checks.append(_check("so_wrong_file_rate_1", arm_metrics_map[ARM_SUPPORT_ONLY]["wrong_file_edit_rate"] == 1.0))
        checks.append(_check("tps_selected_target_rate_1", arm_metrics_map[ARM_TARGET_PLUS_SUPPORT]["selected_target_file_rate"] == 1.0))
        checks.append(_check("so_selected_distractor_rate_1", arm_metrics_map[ARM_SUPPORT_ONLY]["selected_distractor_file_rate"] == 1.0))
        for mname in ("selected_target_file_rate", "selected_distractor_file_rate", "selected_support_file_rate"):
            checks.append(_check(f"metric_{mname}_present", mname in arm_metrics_map[ARM_TARGET_PLUS_SUPPORT]))

        deltas = _compute_paired_deltas(arm_metrics_map)
        expected_delta_count = len(ALL_CONTRASTS) * len(DELTA_METRIC_NAMES)
        checks.append(_check("paired_deltas_count_correct", len(deltas) == expected_delta_count))
        # All 3 primary contrasts present.
        for baseline, treatment in PRIMARY_CONTRASTS:
            present = any(d.get("baseline_arm") == baseline and d.get("treatment_arm") == treatment for d in deltas)
            checks.append(_check(f"primary_contrast_{treatment}_vs_{baseline}_present", present))

        # Mechanism summary (7 records).
        mech = _compute_mechanism_summary_records(arm_runs_test, 1)
        checks.append(_check("mechanism_records_count_7", len(mech) == 7))
        mech_fields = {r["mechanism_field"] for r in mech}
        checks.append(_check("mechanism_has_required_fields", mech_fields == {
            "target_support_conjunction_required_count",
            "support_only_sufficient_count",
            "target_only_sufficient_count",
            "distractor_hurts_count",
            "wrong_file_selection_count",
            "all_arms_solved_count",
            "sparse_solved_count",
        }))
        mech_map = {r["mechanism_field"]: r["value"] for r in mech}
        checks.append(_check("mechanism_conjunction_required_count_1", mech_map["target_support_conjunction_required_count"] == 1))
        checks.append(_check("mechanism_wrong_file_selection_count_1", mech_map["wrong_file_selection_count"] == 1))
        checks.append(_check("mechanism_sparse_solved_count_0", mech_map["sparse_solved_count"] == 0))

        # Honest signals.
        honest = _compute_honest_signals(arm_metrics_map, mech)
        checks.append(_check("honest_conjunction_signal_true", honest["target_support_conjunction_signal_observed"] is True))
        checks.append(_check("honest_wrong_file_selection_count_1", honest["wrong_file_selection_count"] == 1))

        # Family results.
        family_results = _aggregate_family_results(arm_runs_test)
        checks.append(_check("family_results_all_eight_families", set(r["task_family"] for r in family_results) == set(TASK_FAMILIES)))
        checks.append(_check("family_results_five_arms_per_family", all(sum(1 for r in family_results if r["task_family"] == fam) == 5 for fam in TASK_FAMILIES)))

        # --- Group 13: Model display normalization. ---
        checks.append(_check("normalize_strips_routing_prefix", _normalize_model_display(_ROUTING_PREFIX_SENTINEL + "Kimi-K2.7-Code") == "Kimi-K2.7-Code"))
        checks.append(_check("normalize_empty_returns_unavailable", _normalize_model_display("") == "unavailable"))
        checks.append(_check("normalize_strips_unsafe_chars", _normalize_model_display(_ROUTING_PREFIX_SENTINEL + "Test;Model!@#") == "TestModel"))

        # --- Group 14: Env preservation. ---
        checks.append(_check("env_preservation_probe_restores_env", _self_test_probe_preserves_synthetic_provider_env()))
        enabled, failure_category, restored = _probe_missing_env_without_mutating_remote_env()
        checks.append(_check("probe_missing_env_returns_missing_env", not enabled and failure_category == provider_client.FAILURE_CATEGORY_MISSING_ENV))
        checks.append(_check("probe_missing_env_restores_env", restored))

        # --- Group 15: Private manifest hashes. ---
        h1 = _private_score_manifest_hash()
        h2 = _private_score_manifest_hash()
        checks.append(_check("private_score_manifest_hash_stable", h1 == h2 and len(h1) == 64))
        e1 = _private_event_manifest_hash()
        e2 = _private_event_manifest_hash()
        checks.append(_check("private_event_manifest_hash_stable", e1 == e2 and len(e1) == 64))
        checks.append(_check("private_score_and_event_manifests_distinct", h1 != e1))

    finally:
        try:
            shutil.rmtree(workspace_dir, ignore_errors=True)
        except OSError:
            pass

    # --- Group 16: Scanner rejections. ---
    checks.append(_check("scanner_rejects_tmp_workspace_path", bool(_scan_forbidden({"leaked_workspace": "/tmp/b16i_workspace_0"}))))
    checks.append(_check("scanner_rejects_file_path_value", bool(_scan_forbidden({"leaked_file": "target.py"}))))
    checks.append(_check("scanner_rejects_source_snippet", bool(_scan_forbidden({"leaked_snippet": "def resolve():\n    return 0\n"}))))
    checks.append(_check("scanner_rejects_patch_marker", bool(_scan_forbidden({"leaked_patch": "--- a/target.py\n+++ b/target.py\n"}))))
    checks.append(_check("scanner_rejects_prompt_key", bool(_scan_forbidden({"prompt": "abc"}))))
    checks.append(_check("scanner_rejects_response_key", bool(_scan_forbidden({"response": "abc"}))))
    checks.append(_check("scanner_rejects_chosen_file_key", bool(_scan_forbidden({"chosen_file": "target.py"}))))
    checks.append(_check("scanner_rejects_file_choice_key", bool(_scan_forbidden({"file_choice": "target"}))))
    checks.append(_check("scanner_rejects_support_rule_text_key", bool(_scan_forbidden({"support_rule_text": "abc"}))))
    checks.append(_check("scanner_rejects_exact_answer_key", bool(_scan_forbidden({"exact_answer": 42}))))
    checks.append(_check("scanner_rejects_atom_composition_key", bool(_scan_forbidden({"atom_composition": []}))))
    checks.append(_check("scanner_rejects_score_outcome_key", bool(_scan_forbidden({"score_outcome": {}}))))
    checks.append(_check("scanner_rejects_phase_run_id_key", bool(_scan_forbidden({"phase_run_id": "abc"}))))
    checks.append(_check("scanner_rejects_provider_metadata_key", bool(_scan_forbidden({"provider_metadata": {}}))))
    checks.append(_check("scanner_rejects_raw_routing_prefix", bool(_scan_forbidden({"leaked": _ROUTING_PREFIX_SENTINEL + "Kimi-K2.7-Code"}))))
    checks.append(_check("scanner_rejects_url_value", bool(_scan_forbidden({"leaked": "https" + "://example.com"}))))
    checks.append(_check("scanner_rejects_target_py_value", bool(_scan_forbidden({"leaked": "target.py"}))))
    checks.append(_check("scanner_rejects_distractor_py_value", bool(_scan_forbidden({"leaked": "distractor.py"}))))
    checks.append(_check("scanner_rejects_sentinel_canary", bool(_scan_forbidden({"leaked": _SECRET_SENTINEL}))))

    # --- Group 17: Scanner allows legitimate aggregate values. ---
    checks.append(_check("scanner_allows_arm_name_control", not _scan_forbidden({"arm": "control_sparse"})))
    checks.append(_check("scanner_allows_arm_name_target_plus_support", not _scan_forbidden({"arm": "file_choice_target_plus_support"})))
    checks.append(_check("scanner_allows_task_family_names", not _scan_forbidden({"task_family": "operation_ambiguity"})))
    checks.append(_check("scanner_allows_paired_deltas", not _scan_forbidden({"paired_deltas": [{"baseline_arm": "file_choice_nondecisive_support_only", "treatment_arm": "file_choice_target_plus_support", "metric": "solve_rate", "delta": 1.0}]})))
    checks.append(_check("scanner_allows_mechanism_records", not _scan_forbidden({"mechanism_summary_records": [{"mechanism_field": "target_support_conjunction_required_count", "value": 5, "record_count": 8}]})))
    checks.append(_check("scanner_allows_model_display_category", not _scan_forbidden({"model_display_category": "Kimi-K2.7-Code"})))
    checks.append(_check("scanner_allows_private_score_manifest", not _scan_forbidden({"private_score_manifest": {"records_written": True, "record_count": 40, "schema_version": "b16i_private_score.v1", "manifest_hash": "abc123", "storage_class": "tmp_private", "path_publicly_serialized": False}})))
    checks.append(_check("scanner_allows_file_choice_rates", not _scan_forbidden({"selected_target_file_rate": 1.0, "selected_distractor_file_rate": 0.0, "selected_support_file_rate": 0.0})))
    checks.append(_check("scanner_allows_honest_signals", not _scan_forbidden({"honest_signals": {"target_support_conjunction_signal_observed": True, "distractor_hurts_signal_observed": True, "target_support_conjunction_required_count": 5, "support_only_sufficient_count": 0, "target_only_sufficient_count": 0, "distractor_hurts_count": 2, "wrong_file_selection_count": 1, "all_arms_solved_count": 0, "sparse_solved_count": 0, "target_plus_support_solve_rate": 1.0, "distractor_plus_support_solve_rate": 0.5, "support_only_solve_rate": 0.0, "target_only_solve_rate": 0.0, "control_sparse_solve_rate": 0.0, "target_plus_support_selected_target_file_rate": 1.0, "distractor_plus_support_selected_target_file_rate": 0.5}})))

    # --- Group 18: Fail-closed generation. ---
    try:
        _enforce_no_forbidden(skeleton)
        clean_passes = True
    except SystemExit:
        clean_passes = False
    checks.append(_check("fail_closed_clean_public_report_does_not_raise", clean_passes))
    leaked_report = dict(skeleton)
    leaked_report["leaked_path"] = "src/openlocus/lib.rs"
    try:
        _enforce_no_forbidden(leaked_report)
        leak_raises = False
    except SystemExit:
        leak_raises = True
    checks.append(_check("fail_closed_generation_raises_on_leak", leak_raises))
    failed_report = dict(skeleton)
    failed_report["self_test_passed"] = False
    try:
        _refuse_on_self_test_failure(failed_report)
        refuse_failed_raises = False
    except SystemExit:
        refuse_failed_raises = True
    checks.append(_check("refuse_on_self_test_failure_raises_when_failed", refuse_failed_raises))
    passed_report = dict(skeleton)
    passed_report["self_test_passed"] = True
    try:
        _refuse_on_self_test_failure(passed_report)
        refuse_passed_does_not_raise = True
    except SystemExit:
        refuse_passed_does_not_raise = False
    checks.append(_check("refuse_on_self_test_failure_does_not_raise_when_passed", refuse_passed_does_not_raise))

    # --- Group 19: Public artifact self-scan is clean. ---
    checks.append(_check("public_report_forbidden_scan_clean", skeleton["forbidden_scan"]["status"] == "pass"))
    checks.append(_check("public_report_no_forbidden_key_anywhere", not any(_has_dict_key_anywhere(skeleton, bad) for bad in ("task_id", "workspace_path", "file_path", "target_file", "path", "file", "snippet", "code", "patch", "diff", "test_output", "event_log", "stack_trace", "content_sha", "content_hash", "api_key", "base_url", "provider_key", "secret", "token", "stdout", "stderr", "rows", "per_run", "predictions", "prompt", "messages", "response", "provider_payload", "request", "request_body", "model_id_raw", "support_module", "atom_composition", "score_outcome", "phase_run_id", "provider_metadata", "chosen_file", "file_choice", "support_rule_text", "exact_answer"))))

    # --- Group 20: CLI argument surface. ---
    cli_opts = _cli_argument_option_strings()
    checks.append(_check("cli_has_self_test_argument", "--self-test" in cli_opts))
    checks.append(_check("cli_has_out_argument", "--out" in cli_opts))
    checks.append(_check("cli_has_allow_remote_argument", "--allow-remote" in cli_opts))
    checks.append(_check("cli_has_require_workflow_dispatch_argument", "--require-workflow-dispatch" in cli_opts))
    checks.append(_check("cli_has_task_count_argument", "--task-count" in cli_opts))
    checks.append(_check("cli_has_private_score_dir_argument", "--private-score-dir" in cli_opts))
    checks.append(_check("cli_has_private_event_dir_argument", "--private-event-dir" in cli_opts))
    checks.append(_check("cli_only_expected_arguments", (cli_opts - {"-h", "--help"}) == {"--self-test", "--out", "--allow-remote", "--require-workflow-dispatch", "--task-count", "--private-score-dir", "--private-event-dir"}))
    checks.append(_check("cli_default_task_count_in_range", MIN_TASK_COUNT <= DEFAULT_TASK_COUNT <= MAX_TASK_COUNT))

    # --- Group 21: Remote gating. ---
    enabled, failure_category = provider_client._check_remote_enabled(allow_remote=False, require_workflow_dispatch=False)
    checks.append(_check("blocked_when_allow_remote_false", not enabled and failure_category == provider_client.FAILURE_CATEGORY_REMOTE_NOT_ENABLED))
    blocked_rep = _build_public_report([], True, status=STATUS_BLOCKED_REMOTE, live_run_executed=False)
    checks.append(_check("blocked_report_live_flags_false", all(blocked_rep.get(flag) is False for flag in LIVE_TRUE_FLAGS if flag not in ("aggregate_only_public_artifact", "diagnostic_only"))))
    checks.append(_check("blocked_report_forbidden_scan_pass", blocked_rep["forbidden_scan"]["status"] == "pass"))

    # --- Group 22: Five-arm structure. ---
    checks.append(_check("arms_tuple_has_control_first", ARMS[0] == ARM_CONTROL))
    checks.append(_check("arms_tuple_has_target_only_second", ARMS[1] == ARM_TARGET_ONLY))
    checks.append(_check("arms_tuple_has_support_only_third", ARMS[2] == ARM_SUPPORT_ONLY))
    checks.append(_check("arms_tuple_has_distractor_plus_support_fourth", ARMS[3] == ARM_DISTRACTOR_PLUS_SUPPORT))
    checks.append(_check("arms_tuple_has_target_plus_support_fifth", ARMS[4] == ARM_TARGET_PLUS_SUPPORT))
    checks.append(_check("default_total_runs_40", DEFAULT_TASK_COUNT * len(ARMS) == 40))

    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class SafeArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that never echoes unknown/private-looking args."""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(
        description=(
            "B16-I non-decisive support / target-support conjunction "
            "live-provider downstream smoke (public aggregate-only "
            "artifact; synthetic public task-family matrix; five arms: "
            "control_sparse, file_choice_target_only, "
            "file_choice_nondecisive_support_only, "
            "file_choice_distractor_plus_nondecisive_support, "
            "file_choice_target_plus_support; fresh /tmp workspace per "
            "task+arm; real file edits + real subprocess tests; live "
            "LLM provider only when --allow-remote + remote opt-in "
            "gate + provider credential/model env; file-choice confound "
            "removed; support cue non-decisive (requires target binding); "
            "primary contrasts file_choice_target_plus_support vs "
            "file_choice_target_only, vs "
            "file_choice_nondecisive_support_only, vs "
            "file_choice_distractor_plus_nondecisive_support; no raw "
            "prompt/response/payload/chosen-file/support-rule-text "
            "committed; CI pass does NOT require any atom to win)."
        )
    )
    ap.add_argument("--self-test", action="store_true", help="run no-network self-test and exit (no artifact written)")
    ap.add_argument("--out", type=Path, default=None, help="output artifact JSON path")
    ap.add_argument("--allow-remote", action="store_true", help="allow live provider calls (requires remote opt-in gate)")
    ap.add_argument("--require-workflow-dispatch", action="store_true", help="require the workflow-dispatch provider gate for live calls")
    ap.add_argument("--task-count", type=int, default=DEFAULT_TASK_COUNT, help=f"number of synthetic micro tasks (default {DEFAULT_TASK_COUNT}; range {MIN_TASK_COUNT}-{MAX_TASK_COUNT})")
    ap.add_argument("--private-score-dir", type=str, default=None, help="explicit private SCORE JSONL directory (must be under /tmp or runs/)")
    ap.add_argument("--private-event-dir", type=str, default=None, help="explicit private event JSONL directory (must be under /tmp or runs/)")
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
        print(f"self_test_passed={passed} ({passed_count}/{len(checks)} checks)")
        sys.exit(0 if passed else 1)

    _validate_task_count(args.task_count)

    out_path = args.out if args.out is not None else DEFAULT_OUT
    try:
        report = build_report(
            task_count=args.task_count,
            allow_remote=args.allow_remote,
            require_workflow_dispatch=args.require_workflow_dispatch,
            private_score_dir=args.private_score_dir,
            private_event_dir=args.private_event_dir,
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
