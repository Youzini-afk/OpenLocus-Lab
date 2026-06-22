#!/usr/bin/env python3
"""B16-F BEA-Derived Context Pack Live-Provider Paired Smoke (Public Aggregate-Only).

This module implements the **B16-F BEA-derived context pack live-provider
downstream paired smoke**. It is the first downstream live-provider paired
smoke that compares a **BEA v0.3-derived context pack** against a
**same-budget BM25 context-pack control** (and a sparse control) on
bounded synthetic coding tasks.

B16-F has THREE arms:

1. ``control_sparse`` — task issue only, minimal context.
2. ``bm25_same_budget_context_pack`` — same-budget BM25 prefix pack.
3. ``bea_v03_context_pack`` — frozen BEA v0.3 anchor/span/latency selected
   pack.

Primary public paired delta: BEA minus same-budget BM25. Secondary
deltas: BEA minus sparse and BM25 minus sparse.

For each synthetic workspace, B16-F constructs runtime-clean candidate
features (method source, rank, score/normalized score, agreement count,
span extent, path). BM25 selects the same-budget BM25 prefix; BEA applies
a frozen v0.3-style policy using ONLY runtime-available features. The
BEA selector NEVER reads gold paths/lines/labels, task answers,
``correct_value``, or per-task outcomes.

Candidate paths, snippets, BEA/BM25 action traces, budget traces, pack
composition, prompts, responses, patches, and test output are private
under ``/tmp`` only. The public artifact includes ONLY aggregate
counts/rates/means, booleans, and manifests.

B16-F is explicitly **not** a downstream agent value proof, **not** a
live-agent generalization proof, **not** an external benchmark result,
**not** a production coding-agent benchmark, **not** a real user task
evaluation, **not** a method winner/default/promotion claim, **not** a
calibration claim, and **not** a runtime/retriever/pack/backend/default-
policy/EvidenceCore semantic change. It does NOT publish prompts,
responses, provider payloads, base URLs, API keys, raw model routing
prefixes, workspace paths, file paths, source snippets, patches/diffs,
test output, raw event logs, or per-run rows.

Claim boundary (binding):

* Claim level: ``bea_derived_context_pack_downstream_paired_smoke_only``.
* Status enum: ``bea_derived_context_pack_paired_smoke_pass`` on live
  success; ``blocked_remote_not_enabled`` /
  ``unavailable_no_local_provider_env`` when remote opt-in not
  satisfied; ``provider_call_failed`` / ``structured_action_parse_failed``
  / ``paired_run_failed`` / ``fail_forbidden_scan`` on failures.
* Mode: ``public_aggregate_synthetic_task_family_matrix``; phase ``B16-F``.

Modes:

* ``--self-test``: no provider/network; uses fake provider responses.
* default without ``--allow-remote`` or without provider env: writes a
  truthful ``blocked_remote_not_enabled`` /
  ``unavailable_no_local_provider_env`` aggregate report if ``--out``
  is supplied; no provider calls; live-run flags false except
  ``aggregate_only_public_artifact`` / ``diagnostic_only``.
* live opt-in: requires ``--allow-remote``, the remote opt-in gate, and (when
  ``--require-workflow-dispatch``) the workflow-dispatch provider gate;
  runs a tiny task count (default 8; hard cap 12; default 24 live
  calls = 8 tasks x 3 arms; max 36 live calls).

Run::

    python3 -m py_compile eval/b16f_bea_derived_context_pack_paired_smoke.py
    python3 eval/b16f_bea_derived_context_pack_paired_smoke.py --self-test
    python3 eval/b16f_bea_derived_context_pack_paired_smoke.py \
        --out artifacts/b16f_bea_derived_context_pack_paired_smoke/\
b16f_bea_derived_context_pack_paired_smoke_report.json
    # Live opt-in only if provider credential/model environment is available and safe:
    python3 eval/b16f_bea_derived_context_pack_paired_smoke.py \
        --allow-remote --task-count 8 \
        --out artifacts/b16f_bea_derived_context_pack_paired_smoke/\
b16f_bea_derived_context_pack_paired_smoke_report.json
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

# Reuse the provider client helper from B16-C/D/E (unchanged).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import provider_client  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "b16f_bea_derived_context_pack_paired_smoke.v1"
GENERATED_BY = "eval/b16f_bea_derived_context_pack_paired_smoke.py"
CLAIM_LEVEL = "bea_derived_context_pack_downstream_paired_smoke_only"
MODE = "public_aggregate_synthetic_task_family_matrix"
PHASE = "B16-F"

STATUS_PASS = "bea_derived_context_pack_paired_smoke_pass"
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
    "artifacts/b16f_bea_derived_context_pack_paired_smoke/"
    "b16f_bea_derived_context_pack_paired_smoke_report.json"
)
DEFAULT_TASK_COUNT = 8
MIN_TASK_COUNT = 4
MAX_TASK_COUNT = 12
# Max live calls = MAX_TASK_COUNT * len(ARMS) = 12 * 3 = 36.
MAX_LIVE_CALLS = MAX_TASK_COUNT * 3

ARMS: tuple[str, ...] = (
    "control_sparse",
    "bm25_same_budget_context_pack",
    "bea_v03_context_pack",
)
ARM_CONTROL = "control_sparse"
ARM_BM25 = "bm25_same_budget_context_pack"
ARM_BEA = "bea_v03_context_pack"
PRIMARY_CONTRAST = "bea_v03_context_pack_vs_bm25_same_budget_context_pack"

# Eight fixed allowlisted task families (public; never dynamic).
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

# Per-arm aggregate metric names emitted in the public artifact.
METRIC_NAMES: tuple[str, ...] = (
    "run_count",
    "solve_rate",
    "tests_pass_rate",
    "patch_apply_rate",
    "invalid_json_rate",
    "no_op_rate",
    "provider_failure_rate",
    "context_tokens_mean",
    "prompt_tokens_total",
    "completion_tokens_total",
    "latency_seconds_mean",
    "cost_proxy_total",
    "correct_file_before_first_edit_rate",
    "wrong_file_edit_rate",
)

# Delta metric names (treatment minus baseline). Excludes run_count.
DELTA_METRIC_NAMES: tuple[str, ...] = tuple(
    name for name in METRIC_NAMES if name != "run_count"
)

# Allowlisted synthetic filenames for the structured edit action schema.
ALLOWED_EDIT_FILES: frozenset[str] = frozenset({"target.py"})
ALLOWED_EDIT_ACTIONS: frozenset[str] = frozenset(
    {"replace_return_value", "choose_helper_constant", "no_op"}
)

# Private SCORE / event schema versions (under /tmp only; never committed).
PRIVATE_SCORE_SCHEMA_VERSION = "b16f_private_score.v1"
PRIVATE_EVENT_SCHEMA_VERSION = "b16f_private_event.v1"

# ---------------------------------------------------------------------------
# Frozen BEA v0.3-style policy constants (NOT tuned from outcomes)
# ---------------------------------------------------------------------------

BEA_V03_ANCHOR_COUNT = 2
BEA_V03_WEIGHT_ANCHOR = 0.35
BEA_V03_WEIGHT_SPAN_TIGHT = 0.15
BEA_V03_WEIGHT_ANCHOR_FILE_SUPPORT = 0.10
BEA_V03_WEIGHT_WEAK_SUPPORT_PENALTY = -0.20
BEA_V03_WEIGHT_EARLY_STOP_MARGIN = 0.05
BEA_V03_WEIGHT_AGREEMENT = 0.30
BEA_V03_WEIGHT_BM25_NORM = 0.20
BEA_V03_WEIGHT_DIVERSITY = 0.20
BEA_V03_WEIGHT_QUERY_PATH_OVERLAP = 0.15
BEA_V03_WEIGHT_RISK_PENALTY = -0.25
BEA_V03_WEIGHT_DUPLICATION_PENALTY = -0.30

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
    "bea_v03_context_pack_executed",
    "bm25_same_budget_context_pack_executed",
    "private_score_records_written",
    "private_event_records_written",
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
    "method_winner_claimed": False,
    "calibration_claimed": False,
}

# ---------------------------------------------------------------------------
# Public artifact scanner (strict, fail-closed). Extends B16-E scanner with
# BEA-private-key forbid rules. Same shape as B16-C/D/E + BEA-3.
# ---------------------------------------------------------------------------

FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset(
    {
        # prompt / response / message / request / provider payload
        "prompt", "prompts", "message", "messages", "response",
        "responses", "raw_response", "request", "request_body",
        "provider_payload", "raw_payload", "api_response",
        "response_body", "model_response", "model_output",
        "parsed_action", "parsed_response",
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
        "config_module", "cross_file_module", "test_module",
        "source_path", "module_path", "module",
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
        # BEA-private keys (action trace / budget / priority / score outcome)
        "action_order", "priority_components", "priority_score",
        "selected_decisions", "budget_trace", "stop_reason",
        "candidate_features", "anchor_eligibility",
        "anchor_slots", "early_stop_reason",
        "private_score_path", "score_path", "private_score_file",
        "private_event_path", "event_path", "private_event_file",
        "private_record_id", "private_record_hash",
        "action_trace", "action_steps_trace",
        "budget_state", "budget_states",
        "bea_action_trace", "bea_budget_trace", "bea_stop_reason",
        "selected_candidates", "candidates_selected",
        "accepted_candidates", "final_candidates",
        "candidate_list", "score_outcome",
        "per_record_metrics", "runtime_query_features",
        "query_feature_summary", "query_features",
        "benchmark_row_id", "benchmark_record_id", "benchmark_label",
        "phase_run_id", "provider_metadata",
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
        "primary_contrast",
        "model_display_category",
        "storage_class",
        "manifest_hash",
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
# Private SCORE / event writers (under /tmp only; never committed)
# ---------------------------------------------------------------------------


def _resolve_private_dir(explicit: str | None, prefix: str) -> tuple[Path, str]:
    """Resolve a private JSONL directory under /tmp (or gitignored runs/).

    Returns ``(absolute_path, storage_class)``. The path itself is NEVER
    serialized in the public artifact.
    """
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
    """Stable sha256 of the private SCORE manifest schema (NOT row values)."""
    manifest_schema = {
        "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
        "fields": [
            "phase_run_id", "arm", "task_family",
            "candidate_features", "bea_action_trace",
            "bea_budget_trace", "bea_stop_reason",
            "selected_candidates", "score_outcome",
            "latency_ms", "cost_usd", "tokens",
            "provider_calls", "failure_reason",
        ],
    }
    canonical = json.dumps(manifest_schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _private_event_manifest_hash() -> str:
    """Stable sha256 of the private event manifest schema (NOT row values)."""
    manifest_schema = {
        "schema_version": PRIVATE_EVENT_SCHEMA_VERSION,
        "fields": [
            "phase_run_id", "arm", "task_family",
            "prompt", "response", "parsed_action",
            "patch", "test_stdout", "test_stderr",
            "test_returncode", "provider_metadata",
            "failure_reason",
        ],
    }
    canonical = json.dumps(manifest_schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_private_row(score_path: Path, row: dict[str, Any]) -> None:
    """Append a single private JSONL row (transient /tmp only)."""
    score_path.parent.mkdir(parents=True, exist_ok=True)
    with score_path.open("a", encoding="utf-8") as dst:
        dst.write(json.dumps(row, sort_keys=True) + "\n")

# ---------------------------------------------------------------------------
# Eight fixed allowlisted task families. Each has a different decisive
# cue that the BEA pack supplies (via the support/config/cross_file
# module being included as an anchor). Family names are public and
# fixed (allowlisted); never dynamic.
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
    """Generate deterministic heterogeneous synthetic public micro bug tasks.

    Tasks cycle through the eight fixed families so the matrix is
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

    target_path.write_text(
        f"def {task['symbol']}():\n"
        f"    return {task['buggy_value']}\n",
        encoding="utf-8",
    )

    distractor_path.write_text(
        f"def {task['symbol']}():\n"
        f"    return {task['buggy_value']}\n",
        encoding="utf-8",
    )

    if family == "same_symbol_support_relation":
        test_body = (
            f"    expected = {task['helper_constant_name']} * 2 + {task['index']}\n"
        )
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
# Deterministic candidate-feature generator (runtime-clean only).
#
# For each synthetic task, generates 6 candidates with deterministic
# runtime-clean features. The BEA selector uses ONLY these features
# (method source, rank, score, normalized score, agreement count, span
# extent, path). It NEVER reads gold paths, correct_value, task_family
# decisive cue, or any private answer.
#
# Design: target.py has agreement=3 (all methods return it), medium BM25
# score, tight span. distractor.py has agreement=1 (bm25 only), HIGH BM25
# score, tight span. support/config/cross_file.py has agreement=2
# (bm25+symbol), medium BM25, tight span. This makes BEA v0.3 pick
# target.py + support.py (agreement anchor + anchor-file support), while
# BM25 prefix picks distractor.py + support.py (top-2 by BM25 score, NO
# target.py). The BEA pack thus supplies the target file cue + decisive
# cue; the BM25 pack supplies distractor + support (no target file cue).
# ---------------------------------------------------------------------------


def _generate_candidates(task: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate deterministic runtime-clean candidate features per task.

    Each candidate: {path, method, rank, score, normalized_score,
    methods (set), agreement, start_line, end_line, span_extent,
    extension, first_method, first_rank, content_sha}.

    The BEA selector consumes ONLY these features. No gold/correct_value.
    """
    i = task["index"]
    target = task["target_module"]
    distractor = task["distractor_module"]
    support = task["support_module"]

    distractor_bm25 = 0.90 - (i % 5) * 0.01
    # target_bm25 is intentionally LOWER than support_bm25 so that the
    # BM25 same-budget prefix (top-K by score) excludes target.py while
    # BEA v0.3 (agreement anchor) still selects target.py. This creates
    # the causal BEA-vs-BM25 pack-composition difference.
    support_bm25 = 0.60 - (i % 5) * 0.01
    target_bm25 = 0.40 - (i % 5) * 0.01
    other_bm25 = 0.30 - (i % 5) * 0.01

    candidates: list[dict[str, Any]] = [
        {
            "path": target,
            "method": "bm25",
            "rank": 2,
            "score": target_bm25,
            "normalized_score": target_bm25,
            "methods": {"bm25", "regex", "symbol"},
            "agreement": 3,
            "start_line": 1,
            "end_line": 2,
            "span_extent": 2,
            "extension": "py",
            "first_method": "bm25",
            "first_rank": 2,
            "content_sha": "",
        },
        {
            "path": distractor,
            "method": "bm25",
            "rank": 1,
            "score": distractor_bm25,
            "normalized_score": distractor_bm25,
            "methods": {"bm25"},
            "agreement": 1,
            "start_line": 1,
            "end_line": 2,
            "span_extent": 2,
            "extension": "py",
            "first_method": "bm25",
            "first_rank": 1,
            "content_sha": "",
        },
        {
            "path": support,
            "method": "bm25",
            "rank": 3,
            "score": support_bm25,
            "normalized_score": support_bm25,
            "methods": {"bm25", "symbol"},
            "agreement": 2,
            "start_line": 1,
            "end_line": 1,
            "span_extent": 1,
            "extension": "py",
            "first_method": "bm25",
            "first_rank": 3,
            "content_sha": "",
        },
        {
            "path": "other.py",
            "method": "regex",
            "rank": 4,
            "score": other_bm25,
            "normalized_score": other_bm25,
            "methods": {"regex"},
            "agreement": 1,
            "start_line": 1,
            "end_line": 30,
            "span_extent": 30,
            "extension": "py",
            "first_method": "regex",
            "first_rank": 4,
            "content_sha": "",
        },
        {
            "path": "aux.py",
            "method": "regex",
            "rank": 5,
            "score": other_bm25 * 0.8,
            "normalized_score": other_bm25 * 0.8,
            "methods": {"regex"},
            "agreement": 1,
            "start_line": 1,
            "end_line": 10,
            "span_extent": 10,
            "extension": "py",
            "first_method": "regex",
            "first_rank": 5,
            "content_sha": "",
        },
        {
            "path": "util.py",
            "method": "symbol",
            "rank": 6,
            "score": other_bm25 * 0.6,
            "normalized_score": other_bm25 * 0.6,
            "methods": {"symbol"},
            "agreement": 1,
            "start_line": 1,
            "end_line": 3,
            "span_extent": 3,
            "extension": "py",
            "first_method": "symbol",
            "first_rank": 6,
            "content_sha": "",
        },
    ]
    return candidates

# ---------------------------------------------------------------------------
# Frozen BEA v0.3-style anchor/span/latency policy (deterministic,
# runtime-clean). Simplified inline version (does NOT import bea3 to keep
# B16-F self-contained and avoid pulling c5/bea network deps).
#
# Consumes ONLY runtime-clean candidate features. NEVER reads gold paths,
# correct_value, task_family decisive cue, or any private answer.
# ---------------------------------------------------------------------------


def _span_tightness(entry: dict[str, Any]) -> float:
    """Tighter line-span bonus in [0, 1]. Runtime-clean (span extent only)."""
    extent = int(entry.get("span_extent", 0) or 0)
    if extent <= 0:
        return 0.0
    if extent <= 10:
        return 1.0
    if extent <= 20:
        return 0.5
    if extent <= 50:
        return 0.25
    return 0.0


def _span_proxy_bucket(extent: int) -> str:
    if extent <= 0:
        return "empty"
    if extent <= 10:
        return "tight"
    if extent <= 20:
        return "medium"
    if extent <= 50:
        return "wide"
    return "very_wide"


def _is_anchor_eligible(entry: dict[str, Any]) -> bool:
    """Anchor eligibility: bm25 method OR agreement >= 2. Runtime-clean."""
    methods = entry.get("methods", set())
    if not isinstance(methods, set):
        methods = set(methods)
    if "bm25" in methods:
        return True
    if len(methods) >= 2:
        return True
    return False


def _compute_v03_priority(
    entry: dict[str, Any],
    accepted_paths: set[str],
    anchor_paths: set[str],
    query_tokens: set[str],
    is_anchor_slot: bool,
) -> dict[str, Any]:
    """Compute v0.3 priority score with span/latency proxies.

    Runtime-clean: uses only agreement, bm25_norm, span tightness,
    path overlap (query token match in path), diversity (new file),
    anchor eligibility, anchor-file support. NEVER uses gold/correct_value.
    """
    agreement = int(entry.get("agreement", 1))
    bm25_norm = float(entry.get("normalized_score", 0.0))
    span_tight = _span_tightness(entry)
    path_str = str(entry.get("path", ""))
    is_new_file = path_str not in accepted_paths
    same_file_as_anchor = path_str in anchor_paths
    anchor_eligible = _is_anchor_eligible(entry)

    query_overlap = 1.0 if "target" in path_str else 0.0

    agreement_component = BEA_V03_WEIGHT_AGREEMENT * (agreement / 3.0)
    bm25_component = BEA_V03_WEIGHT_BM25_NORM * bm25_norm
    diversity_component = (
        BEA_V03_WEIGHT_DIVERSITY if is_new_file else 0.0
    )
    query_path_component = (
        BEA_V03_WEIGHT_QUERY_PATH_OVERLAP * query_overlap
    )
    span_bonus = BEA_V03_WEIGHT_SPAN_TIGHT * span_tight
    anchor_file_support = (
        BEA_V03_WEIGHT_ANCHOR_FILE_SUPPORT if same_file_as_anchor else 0.0
    )
    anchor_boost = (
        BEA_V03_WEIGHT_ANCHOR if (is_anchor_slot and anchor_eligible) else 0.0
    )
    risk = 0.0
    if span_tight < 0.5 and agreement <= 1 and bm25_norm < 0.1:
        risk = BEA_V03_WEIGHT_RISK_PENALTY
    weak_penalty = (
        BEA_V03_WEIGHT_WEAK_SUPPORT_PENALTY
        if (agreement <= 1 and bm25_norm < 0.01)
        else 0.0
    )
    dup_penalty = (
        BEA_V03_WEIGHT_DUPLICATION_PENALTY if not is_new_file else 0.0
    )

    priority = (
        agreement_component
        + bm25_component
        + diversity_component
        + query_path_component
        + span_bonus
        + anchor_file_support
        + anchor_boost
        + risk
        + weak_penalty
        + dup_penalty
    )

    return {
        "priority_score": round(priority, 6),
        "priority_components": {
            "agreement_component": round(agreement_component, 6),
            "bm25_component": round(bm25_component, 6),
            "diversity_component": round(diversity_component, 6),
            "query_path_component": round(query_path_component, 6),
            "span_bonus": round(span_bonus, 6),
            "anchor_file_support": round(anchor_file_support, 6),
            "anchor_boost": round(anchor_boost, 6),
            "risk_penalty": round(risk, 6),
            "weak_support_penalty": round(weak_penalty, 6),
            "duplication_penalty": round(dup_penalty, 6),
        },
        "is_new_file": is_new_file,
        "anchor_eligible": anchor_eligible,
        "same_file_as_anchor": same_file_as_anchor,
        "span_tightness": round(span_tight, 6),
    }


def _bea_v03_policy(
    candidates: list[dict[str, Any]],
    query: str,
    budget: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str, dict[str, Any]]:
    """Deterministic BEA v0.3 anchor/span/latency policy.

    Consumes ONLY runtime-clean candidate features. NEVER reads gold/
    correct_value/task_family decisive cue/private answer.

    Returns ``(accepted, action_order, budget_trace, stop_reason,
    mechanism_summary)``.
    """
    anchor_count = min(BEA_V03_ANCHOR_COUNT, budget)

    mechanism_summary = {
        "anchor_used": True,
        "early_stop_used": True,
        "anchor_count_reserved": int(anchor_count),
        "anchor_count_filled": 0,
        "early_stop_reason": "",
        "mean_span_extent": 0.0,
        "span_proxy_bucket_counts": {},
    }

    if not candidates or budget <= 0:
        return [], [], [
            {"step": 0, "budget_remaining": 0, "accepted_so_far": 0}
        ], "no_candidates_or_zero_budget", mechanism_summary

    seen: set[tuple[str, int, int]] = set()
    deduped: list[dict[str, Any]] = []
    for c in candidates:
        key = (str(c["path"]), int(c["start_line"]), int(c["end_line"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(dict(c))

    if not deduped:
        return [], [], [
            {"step": 0, "budget_remaining": budget, "accepted_so_far": 0}
        ], "no_deduped_candidates", mechanism_summary

    query_tokens = set(re.findall(r"[A-Za-z0-9_]+", query.lower()))

    accepted: list[dict[str, Any]] = []
    accepted_paths: set[str] = set()
    anchor_paths: set[str] = set()
    action_order: list[dict[str, Any]] = []
    budget_trace: list[dict[str, Any]] = []
    stop_reason = "candidates_exhausted"
    early_stop_reason = ""
    span_extents: list[int] = []
    span_bucket_counts: dict[str, int] = {}
    remaining = list(deduped)
    anchors_filled = 0

    for step in range(budget):
        if not remaining:
            stop_reason = "candidates_exhausted"
            break

        is_anchor_slot = anchors_filled < anchor_count

        scored: list[tuple[float, int, dict[str, Any], dict[str, Any]]] = []
        for idx, entry in enumerate(remaining):
            prio = _compute_v03_priority(
                entry, accepted_paths, anchor_paths, query_tokens,
                is_anchor_slot,
            )
            scored.append((prio["priority_score"], idx, entry, prio))
        scored.sort(key=lambda t: (-t[0], t[1]))
        best_prio, _best_idx, best_entry, best_components = scored[0]

        budget_remaining = budget - len(accepted)
        budget_trace.append({
            "step": step,
            "budget_remaining": budget_remaining,
            "accepted_so_far": len(accepted),
            "candidate_count_remaining": len(remaining),
            "is_anchor_slot": is_anchor_slot,
        })

        if (
            anchors_filled >= anchor_count
            and best_prio < BEA_V03_WEIGHT_EARLY_STOP_MARGIN
        ):
            stop_reason = "early_stop_marginal_priority"
            early_stop_reason = "marginal_priority_below_threshold"
            action_order.append({
                "step": step,
                "action": "stop_early_stop",
                "priority_score": best_prio,
                "priority_components": best_components["priority_components"],
                "anchor_slots_filled": anchors_filled,
            })
            break

        if len(accepted) >= budget:
            stop_reason = "budget_exhausted"
            action_order.append({
                "step": step,
                "action": "stop_budget_exhausted",
                "priority_score": best_prio,
                "priority_components": best_components["priority_components"],
            })
            break

        path = str(best_entry["path"])
        accepted.append({
            "path": path,
            "start_line": int(best_entry["start_line"]),
            "end_line": int(best_entry["end_line"]),
            "content_sha": best_entry.get("content_sha", ""),
        })
        accepted_paths.add(path)
        if is_anchor_slot:
            anchors_filled += 1
            anchor_paths.add(path)

        extent = int(best_entry.get("span_extent", 0) or 0)
        span_extents.append(extent)
        bucket = _span_proxy_bucket(extent)
        span_bucket_counts[bucket] = span_bucket_counts.get(bucket, 0) + 1

        action_order.append({
            "step": step,
            "action": "accept_candidate",
            "priority_score": best_prio,
            "priority_components": best_components["priority_components"],
            "candidate_method": best_entry.get("first_method", ""),
            "candidate_rank": best_entry.get("first_rank", 0),
            "agreement": int(best_entry.get("agreement", 1)),
            "is_new_file": best_components["is_new_file"],
            "is_anchor_slot": is_anchor_slot,
            "anchor_eligible": best_components["anchor_eligible"],
            "span_extent": extent,
            "span_proxy_bucket": bucket,
        })
        remaining = [
            e for e in remaining
            if (
                str(e["path"]),
                int(e["start_line"]),
                int(e["end_line"]),
            )
            != (
                path,
                int(best_entry["start_line"]),
                int(best_entry["end_line"]),
            )
        ]

    if len(accepted) >= budget and stop_reason != "early_stop_marginal_priority":
        stop_reason = "budget_exhausted"
    elif not remaining and stop_reason != "early_stop_marginal_priority":
        stop_reason = "candidates_exhausted"

    mechanism_summary["anchor_count_filled"] = anchors_filled
    mechanism_summary["early_stop_reason"] = early_stop_reason
    mechanism_summary["mean_span_extent"] = (
        round(sum(span_extents) / len(span_extents), 6) if span_extents else 0.0
    )
    mechanism_summary["span_proxy_bucket_counts"] = span_bucket_counts

    return accepted, action_order, budget_trace, stop_reason, mechanism_summary


# ---------------------------------------------------------------------------
# BM25 same-budget prefix selector (runtime-clean).
# ---------------------------------------------------------------------------


def _bm25_prefix_same_budget(
    candidates: list[dict[str, Any]], k: int
) -> list[dict[str, Any]]:
    """Select top-K candidates by BM25 score (deterministic, runtime-clean).

    Tie-break: rank asc, then path asc. NEVER uses gold/correct_value.
    """
    if k <= 0 or not candidates:
        return []
    seen: dict[tuple[str, int, int], dict[str, Any]] = {}
    for c in candidates:
        key = (str(c["path"]), int(c["start_line"]), int(c["end_line"]))
        if key not in seen:
            seen[key] = c
        else:
            if float(c.get("normalized_score", 0.0)) > float(
                seen[key].get("normalized_score", 0.0)
            ):
                seen[key] = c
    deduped = list(seen.values())
    deduped.sort(
        key=lambda c: (
            -float(c.get("normalized_score", 0.0)),
            int(c.get("rank", 99)),
            str(c.get("path", "")),
        )
    )
    selected = deduped[:k]
    return [
        {
            "path": str(s["path"]),
            "start_line": int(s["start_line"]),
            "end_line": int(s["end_line"]),
            "content_sha": s.get("content_sha", ""),
        }
        for s in selected
    ]


# ---------------------------------------------------------------------------
# Pack builder (control_sparse vs bm25_same_budget vs bea_v03).
# Public descriptor is safe: booleans/counts/token estimates only.
# ---------------------------------------------------------------------------


def _build_pack(
    arm: str,
    task: dict[str, Any],
    bea_accepted: list[dict[str, Any]],
    bm25_accepted: list[dict[str, Any]],
    same_budget_k: int,
) -> dict[str, Any]:
    """Build the public-safe pack descriptor for an arm.

    * control_sparse: minimal description; NO target file cue; NO
      decisive cue; candidate_count=0; small token budget.
    * bm25_same_budget_context_pack: same-budget BM25 prefix; includes
      target file cue + symbol cue + decisive cue ONLY IF the BM25
      prefix happens to include target.py and support.py.
    * bea_v03_context_pack: BEA v0.3 selected; includes target file cue
      + symbol cue + decisive cue (BEA picks target.py + support.py
      as anchors).
    """
    if arm == ARM_CONTROL:
        return {
            "arm": arm,
            "candidate_count": 0,
            "context_tokens": 20,
            "has_target_file_cue": False,
            "has_symbol_cue": False,
            "has_decisive_cue": False,
            "has_exact_edit_constraint": False,
            "same_budget_k": 0,
        }

    if arm == ARM_BEA:
        selected = bea_accepted
    elif arm == ARM_BM25:
        selected = bm25_accepted
    else:
        selected = []

    selected_paths = {str(c["path"]) for c in selected}
    target_module = task["target_module"]
    support_module = task["support_module"]
    has_target = target_module in selected_paths
    has_support = support_module in selected_paths
    has_decisive = has_support
    has_symbol = has_target

    return {
        "arm": arm,
        "candidate_count": len(selected),
        "context_tokens": 64,
        "has_target_file_cue": has_target,
        "has_symbol_cue": has_symbol,
        "has_decisive_cue": has_decisive,
        "has_exact_edit_constraint": True,
        "same_budget_k": int(same_budget_k),
    }

# ---------------------------------------------------------------------------
# Live LLM prompt builder (in-memory only; never persisted).
# ---------------------------------------------------------------------------


def _decisive_cue_text(task: dict[str, Any]) -> str:
    """Return the family-specific decisive cue text (treatment only)."""
    family = task["task_family"]
    if family == "same_symbol_support_relation":
        return (
            f"Support relation: correct_value = {task['helper_constant_name']} "
            f"* 2 + {task['index']}. "
            f"Helper constant {task['helper_constant_name']} = "
            f"{task['helper_constant_value']} (defined in {task['support_module']}). "
            f"Correct value: {task['correct_value']}."
        )
    if family == "operation_ambiguity":
        return (
            f"Operation hint: multiply the base value by 2 (do not "
            f"increment). "
            f"Base value {task['helper_constant_name']} = "
            f"{task['helper_constant_value']} (defined in {task['support_module']}). "
            f"Correct value: {task['correct_value']}."
        )
    if family == "boundary_condition":
        return (
            f"Boundary hint: the limit is an exclusive upper bound "
            f"(correct value = limit - 1). "
            f"Limit {task['helper_constant_name']} = "
            f"{task['helper_constant_value']} (defined in {task['support_module']}). "
            f"Correct value: {task['correct_value']}."
        )
    if family == "helper_dependency_choice":
        return (
            f"Helper choice hint: use {task['helper_constant_name']} "
            f"(not {task['helper_constant_name_alt']}). "
            f"Correct value = {task['helper_constant_name']} * 3 = "
            f"{task['correct_value']}."
        )
    if family == "config_or_test_mismatch":
        return (
            f"Config source hint: the correct value comes from "
            f"{task['support_module']} ({task['helper_constant_name']} = "
            f"{task['helper_constant_value']}). "
            f"Correct value: {task['correct_value']}."
        )
    if family == "distractor_file":
        return (
            f"Target file hint: edit {task['target_module']} (not "
            f"{task['distractor_module']}). "
            f"Correct value = {task['helper_constant_name']} + 5 = "
            f"{task['correct_value']}."
        )
    if family == "nearby_wrong_function":
        return (
            f"Symbol cue hint: fix the function {task['symbol']} "
            f"(not a similarly-named nearby function). "
            f"Correct value = {task['helper_constant_name']} * 2 = "
            f"{task['correct_value']}."
        )
    if family == "cross_file_symbol":
        return (
            f"Cross-file source hint: the helper lives in "
            f"{task['support_module']} ({task['helper_constant_name']} = "
            f"{task['helper_constant_value']}). "
            f"Correct value = {task['helper_constant_name']} + 1 = "
            f"{task['correct_value']}."
        )
    return ""


def _build_messages(
    workspace_dir: Path,
    task: dict[str, Any],
    pack: dict[str, Any],
    selected_candidates: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Build the live LLM chat messages (in-memory; never persisted).

    The prompt may include tiny synthetic/public source snippets (the
    buggy target module + the support module) and a family-specific
    decisive cue only when the treatment pack carries it. Prompts are
    NEVER persisted.
    """
    target_path = workspace_dir / task["target_module"]
    support_path = workspace_dir / task["support_module"]
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
        user_lines.append(
            f"Target file: {task['target_module']} (not {task['distractor_module']})."
        )
    if pack.get("has_symbol_cue"):
        user_lines.append(
            f"Target symbol: {task['symbol']} in {task['target_module']}."
        )
    if pack.get("has_decisive_cue"):
        user_lines.append(_decisive_cue_text(task))
    if pack.get("has_exact_edit_constraint"):
        user_lines.append(
            f"Edit constraint: only edit {task['target_module']}; do not edit "
            f"{task['distractor_module']} or {task['support_module']}."
        )
    user_lines.append(f"Target source:\n{target_snippet}")
    if pack.get("has_decisive_cue"):
        user_lines.append(f"Support source:\n{support_snippet}")
    if selected_candidates:
        cand_lines = []
        for c in selected_candidates:
            cand_lines.append(
                f"- {c['path']} (lines {c['start_line']}-{c['end_line']})"
            )
        user_lines.append("Pack candidates:\n" + "\n".join(cand_lines))
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
# Live LLM agent run (one task + arm) with private SCORE/event writers
# ---------------------------------------------------------------------------


def _run_live_agent(
    workspace_dir: Path,
    task: dict[str, Any],
    pack: dict[str, Any],
    selected_candidates: list[dict[str, Any]],
    bea_action_trace: list[dict[str, Any]],
    bea_budget_trace: list[dict[str, Any]],
    bea_stop_reason: str,
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
    """Run the live LLM agent for one task+arm.

    When ``fake_response`` is supplied (self-test mode), no network call
    is made. Otherwise a real provider call is made via
    ``provider_client.chat_completion``.

    Always writes one private SCORE row and one private event row under
    /tmp. The public return value contains ONLY aggregate metrics.
    """
    event_log: list[dict[str, Any]] = []
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
        messages = _build_messages(workspace_dir, task, pack, selected_candidates)
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

    if parsed_action is None:
        event_log.append({"event": "no_action", "kind": "no_parse"})
    else:
        valid, reason = _validate_edit_action(parsed_action, task)
        if not valid:
            event_log.append({"event": "invalid_action", "kind": reason})
        else:
            tool_calls_before_first_edit = 1
            edited_correct, kind = _apply_edit_action(
                workspace_dir, task, parsed_action
            )
            if kind == "correct_file":
                correct_file_before_first_edit = True
                patch_applied = True
            elif kind == "wrong_file":
                wrong_file_edits += 1
                patch_applied = True
            elif kind == "no_op":
                no_op = True
            event_log.append({"event": "edit", "kind": kind})

    test_cmd = [sys.executable, str(workspace_dir / task["test_module"])]
    test_start = time.perf_counter()
    test_stdout = ""
    test_stderr = ""
    test_returncode: int | None = None
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
        test_returncode = proc.returncode
    except (subprocess.TimeoutExpired, OSError):
        tests_pass = False
        test_returncode = -1
    test_latency_ms = max(1, int((time.perf_counter() - test_start) * 1000))

    event_log.append({"event": "test", "passed": tests_pass})

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
        "context_tokens": pack.get("context_tokens", 0),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "latency_ms": latency_ms + test_latency_ms,
        "cost_proxy": 0,
    }

    private_score_row = {
        "phase_run_id": phase_run_id,
        "arm": arm,
        "task_family": task["task_family"],
        "candidate_features": [
            {
                "path": str(c.get("path", "")),
                "method": str(c.get("method", "")),
                "rank": int(c.get("rank", 0)),
                "score": float(c.get("score", 0.0)),
                "normalized_score": float(c.get("normalized_score", 0.0)),
                "agreement": int(c.get("agreement", 1)),
                "start_line": int(c.get("start_line", 0)),
                "end_line": int(c.get("end_line", 0)),
                "span_extent": int(c.get("span_extent", 0)),
            }
            for c in selected_candidates
        ],
        "bea_action_trace": bea_action_trace if arm == ARM_BEA else [],
        "bea_budget_trace": bea_budget_trace if arm == ARM_BEA else [],
        "bea_stop_reason": bea_stop_reason if arm == ARM_BEA else "",
        "selected_candidates": [
            {
                "path": str(c.get("path", "")),
                "start_line": int(c.get("start_line", 0)),
                "end_line": int(c.get("end_line", 0)),
            }
            for c in selected_candidates
        ],
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
        "prompt": _build_messages(
            workspace_dir, task, pack, selected_candidates
        )[-1]["content"],
        "response": raw_response_text or "",
        "parsed_action": parsed_action,
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
        "patch_apply_rate": _round_metric(
            _rate(sum(1 for r in runs if r["patch_applied"]), n)
        ),
        "invalid_json_rate": _round_metric(
            _rate(sum(1 for r in runs if r["invalid_json"]), n)
        ),
        "no_op_rate": _round_metric(
            _rate(sum(1 for r in runs if r["no_op"]), n)
        ),
        "provider_failure_rate": _round_metric(
            _rate(sum(1 for r in runs if r["provider_failure"]), n)
        ),
        "context_tokens_mean": _round_metric(
            _mean([r["context_tokens"] for r in runs])
        ),
        "prompt_tokens_total": int(sum(r["prompt_tokens"] for r in runs)),
        "completion_tokens_total": int(
            sum(r["completion_tokens"] for r in runs)
        ),
        "latency_seconds_mean": _round_metric(
            _mean([r["latency_ms"] for r in runs]) / 1000.0
        ),
        "cost_proxy_total": _round_metric(
            sum(r["cost_proxy"] for r in runs)
        ),
        "correct_file_before_first_edit_rate": _round_metric(
            _rate(
                sum(1 for r in runs if r["correct_file_before_first_edit"]),
                n,
            )
        ),
        "wrong_file_edit_rate": _round_metric(
            _rate(sum(1 for r in runs if r["wrong_file_edits"] > 0), n)
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
    """Compute per-family per-arm aggregate records (counts only)."""
    family_results: list[dict[str, Any]] = []
    for family in TASK_FAMILIES:
        for arm in ARMS:
            runs = [
                r for r in arm_runs[arm] if r.get("task_family") == family
            ]
            n = len(runs)
            family_results.append(
                {
                    "task_family": family,
                    "arm": arm,
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
                    "wrong_file_edit_rate": _round_metric(
                        _rate(
                            sum(1 for r in runs if r["wrong_file_edits"] > 0),
                            n,
                        )
                    ),
                }
            )
    return family_results


def _compute_paired_deltas(
    arm_metrics_by_arm: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute all three paired deltas (treatment minus baseline).

    Primary: BEA vs BM25. Secondary: BEA vs sparse, BM25 vs sparse.
    """
    contrasts = [
        (ARM_BM25, ARM_BEA),
        (ARM_CONTROL, ARM_BEA),
        (ARM_CONTROL, ARM_BM25),
    ]
    records: list[dict[str, Any]] = []
    for baseline_arm, treatment_arm in contrasts:
        baseline = arm_metrics_by_arm[baseline_arm]
        treatment = arm_metrics_by_arm[treatment_arm]
        for name in DELTA_METRIC_NAMES:
            records.append(
                {
                    "baseline_arm": baseline_arm,
                    "treatment_arm": treatment_arm,
                    "metric": name,
                    "delta": _round_metric(
                        treatment[name] - baseline[name]
                    ),
                }
            )
    return records


def _compute_family_signal_summary(
    family_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute aggregate family signal summary for the PRIMARY contrast
    (BEA vs BM25). Counts families by solve-rate delta sign."""
    families_evaluated = 0
    positive = 0
    zero = 0
    negative = 0
    for family in TASK_FAMILIES:
        bm25 = next(
            (
                r
                for r in family_results
                if r["task_family"] == family and r["arm"] == ARM_BM25
            ),
            None,
        )
        bea = next(
            (
                r
                for r in family_results
                if r["task_family"] == family and r["arm"] == ARM_BEA
            ),
            None,
        )
        if bm25 is None or bea is None:
            continue
        if bm25["run_count"] == 0 or bea["run_count"] == 0:
            continue
        families_evaluated += 1
        delta = bea["solve_rate"] - bm25["solve_rate"]
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
    arm_metrics_by_arm: dict[str, dict[str, Any]],
    paired_deltas: list[dict[str, Any]],
    family_signal_summary: dict[str, Any],
) -> dict[str, Any]:
    """Compute honest diagnostic signal fields for the PRIMARY contrast."""
    primary_delta_solve = next(
        (
            d["delta"]
            for d in paired_deltas
            if d["baseline_arm"] == ARM_BM25
            and d["treatment_arm"] == ARM_BEA
            and d["metric"] == "solve_rate"
        ),
        0.0,
    )
    primary_delta_tests = next(
        (
            d["delta"]
            for d in paired_deltas
            if d["baseline_arm"] == ARM_BM25
            and d["treatment_arm"] == ARM_BEA
            and d["metric"] == "tests_pass_rate"
        ),
        0.0,
    )
    primary_delta_wrong_file = next(
        (
            d["delta"]
            for d in paired_deltas
            if d["baseline_arm"] == ARM_BM25
            and d["treatment_arm"] == ARM_BEA
            and d["metric"] == "wrong_file_edit_rate"
        ),
        0.0,
    )
    bea_metrics = arm_metrics_by_arm[ARM_BEA]
    bm25_metrics = arm_metrics_by_arm[ARM_BM25]
    context_signal = (
        bea_metrics.get("solve_rate", 0.0) > bm25_metrics.get("solve_rate", 0.0)
        or bea_metrics.get("wrong_file_edit_rate", 0.0)
        < bm25_metrics.get("wrong_file_edit_rate", 0.0)
        or family_signal_summary.get(
            "families_with_positive_solve_delta", 0
        )
        > 0
    )
    return {
        "context_pack_signal_observed": bool(context_signal),
        "primary_solve_rate_delta": _round_metric(primary_delta_solve),
        "primary_tests_pass_rate_delta": _round_metric(primary_delta_tests),
        "primary_wrong_file_edit_rate_delta": _round_metric(
            primary_delta_wrong_file
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


def _determine_live_status(
    arm_results: list[dict[str, Any]],
    paired_run_completed: bool,
    any_provider_call_failed: bool,
    any_parse_failed: bool,
) -> str:
    """Determine the live run status.

    CI pass means: live run completed + privacy scan passed + artifact
    is honest. CI pass does NOT require BEA improvement.
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
    private_score_manifest: dict[str, Any] | None = None,
    private_event_manifest: dict[str, Any] | None = None,
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
        "primary_solve_rate_delta": 0.0,
        "primary_tests_pass_rate_delta": 0.0,
        "primary_wrong_file_edit_rate_delta": 0.0,
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
        "primary_contrast": PRIMARY_CONTRAST,
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
        "family_signal_summary": family_signal_summary,
        "honest_signals": honest_signals_out,
        "private_score_manifest": private_score_manifest,
        "private_event_manifest": private_event_manifest,
        **DEFAULT_FALSE_FLAGS,
        "aggregate_only_public_artifact": True,
        "diagnostic_only": True,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for check in checks if check.get("passed")),
        "self_test_passed": all_passed,
    }

    if live_run_executed:
        for flag in LIVE_TRUE_FLAGS:
            report[flag] = True
    else:
        for flag in LIVE_TRUE_FLAGS:
            if flag not in (
                "aggregate_only_public_artifact", "diagnostic_only"
            ):
                report[flag] = False

    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_LEAK
    return report


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


def build_report(
    task_count: int,
    *,
    allow_remote: bool,
    require_workflow_dispatch: bool,
    private_score_dir: str | None = None,
    private_event_dir: str | None = None,
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
            "primary_contrast": PRIMARY_CONTRAST,
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
                "primary_solve_rate_delta": 0.0,
                "primary_tests_pass_rate_delta": 0.0,
                "primary_wrong_file_edit_rate_delta": 0.0,
                "families_evaluated": 0,
                "families_with_positive_solve_delta": 0,
                "families_with_zero_solve_delta": 0,
                "families_with_negative_solve_delta": 0,
            },
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

    score_dir, score_storage = _resolve_private_dir(
        private_score_dir, "b16f_private_score"
    )
    event_dir, event_storage = _resolve_private_dir(
        private_event_dir, "b16f_private_event"
    )
    score_path = score_dir / "b16f_private_score.jsonl"
    event_path = event_dir / "b16f_private_event.jsonl"
    score_path.write_text("", encoding="utf-8")
    event_path.write_text("", encoding="utf-8")
    phase_run_id = f"b16f_{int(time.time())}_{os.getpid()}"

    tasks = _generate_synthetic_tasks(task_count)
    arm_runs: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    any_provider_call_failed = False
    any_parse_failed = False
    score_rows_written = 0
    event_rows_written = 0

    for task in tasks:
        candidates = _generate_candidates(task)
        bea_budget = 2
        bea_accepted, bea_action_trace, bea_budget_trace, bea_stop_reason, _mech = (
            _bea_v03_policy(candidates, task["symbol"], bea_budget)
        )
        same_budget_k = len(bea_accepted)
        bm25_accepted = _bm25_prefix_same_budget(candidates, same_budget_k)

        for arm in ARMS:
            pack = _build_pack(
                arm, task, bea_accepted, bm25_accepted,
                same_budget_k,
            )
            if arm == ARM_BEA:
                selected = bea_accepted
                arm_bea_action_trace = bea_action_trace
                arm_bea_budget_trace = bea_budget_trace
                arm_bea_stop_reason = bea_stop_reason
            elif arm == ARM_BM25:
                selected = bm25_accepted
                arm_bea_action_trace = []
                arm_bea_budget_trace = []
                arm_bea_stop_reason = "same_budget_bm25_prefix"
            else:
                selected = []
                arm_bea_action_trace = []
                arm_bea_budget_trace = []
                arm_bea_stop_reason = "control_sparse"

            workspace_dir = Path(
                tempfile.mkdtemp(prefix="b16f_workspace_")
            )
            try:
                _build_workspace(workspace_dir, task)
                run = _run_live_agent(
                    workspace_dir,
                    task,
                    pack,
                    selected,
                    arm_bea_action_trace,
                    arm_bea_budget_trace,
                    arm_bea_stop_reason,
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
                "failure_category_counts": provider_summary.get(
                    "failure_category_counts", {}
                ),
            }
        )

    paired_deltas = _compute_paired_deltas(arm_metrics_by_arm)
    task_family_results = _aggregate_family_results(arm_runs)
    family_signal_summary = _compute_family_signal_summary(
        task_family_results
    )
    honest_signals = _compute_honest_signals(
        arm_metrics_by_arm, paired_deltas, family_signal_summary
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
        "primary_contrast": PRIMARY_CONTRAST,
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
        checks,
        all_passed,
        status=status,
        arm_results=arm_results,
        paired_deltas=paired_deltas,
        task_family_results=task_family_results,
        family_signal_summary=family_signal_summary,
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
    """Run all B16-F self-test groups (no network)."""
    checks: list[dict[str, Any]] = []

    # --- Group 1: Artifact identity fields. ---
    skeleton = _build_public_report([], False, status=STATUS_UNAVAILABLE)
    checks.append(_check("schema_version_correct", skeleton["schema_version"] == SCHEMA_VERSION))
    checks.append(_check("claim_level_correct", skeleton["claim_level"] == CLAIM_LEVEL))
    checks.append(_check("mode_correct", skeleton["mode"] == MODE))
    checks.append(_check("phase_correct", skeleton["phase"] == PHASE))
    checks.append(_check("generated_by_correct", skeleton["generated_by"] == GENERATED_BY))
    checks.append(_check("primary_contrast_correct", skeleton["input_summary"]["primary_contrast"] == PRIMARY_CONTRAST))
    checks.append(_check("arms_count_is_3", len(ARMS) == 3))
    checks.append(_check("task_families_count_is_8", len(TASK_FAMILIES) == 8))
    checks.append(_check("default_task_count_is_8", DEFAULT_TASK_COUNT == 8))
    checks.append(_check("max_live_calls_is_36", MAX_LIVE_CALLS == 36))
    for status in ALL_STATUSES:
        rep = _build_public_report([], False, status=status)
        checks.append(_check(f"status_{status}_preserved", rep["status"] == status))

    # --- Group 2: Always-false no-claim flags. ---
    for flag in DEFAULT_FALSE_FLAGS:
        checks.append(_check(f"default_false_{flag}", skeleton.get(flag) is False))

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
    f1 = next(t for t in tasks_8 if t["task_family"] == "same_symbol_support_relation")
    checks.append(_check("family1_correct_value_uses_support_relation", f1["correct_value"] == f1["helper_constant_value"] * 2 + f1["index"]))
    f2 = next(t for t in tasks_8 if t["task_family"] == "operation_ambiguity")
    checks.append(_check("family2_correct_value_uses_multiply", f2["correct_value"] == f2["helper_constant_value"] * 2))
    f3 = next(t for t in tasks_8 if t["task_family"] == "boundary_condition")
    checks.append(_check("family3_correct_value_uses_exclusive_bound", f3["correct_value"] == f3["helper_constant_value"] - 1))
    f4 = next(t for t in tasks_8 if t["task_family"] == "helper_dependency_choice")
    checks.append(_check("family4_correct_value_uses_helper_b", f4["correct_value"] == f4["helper_constant_value"] * 3))
    f5 = next(t for t in tasks_8 if t["task_family"] == "config_or_test_mismatch")
    checks.append(_check("family5_correct_value_uses_config_source", f5["correct_value"] == f5["helper_constant_value"]))
    f6 = next(t for t in tasks_8 if t["task_family"] == "distractor_file")
    checks.append(_check("family6_correct_value_uses_helper_plus_5", f6["correct_value"] == f6["helper_constant_value"] + 5))
    f7 = next(t for t in tasks_8 if t["task_family"] == "nearby_wrong_function")
    checks.append(_check("family7_correct_value_uses_helper_times_2", f7["correct_value"] == f7["helper_constant_value"] * 2))
    f8 = next(t for t in tasks_8 if t["task_family"] == "cross_file_symbol")
    checks.append(_check("family8_correct_value_uses_helper_plus_1", f8["correct_value"] == f8["helper_constant_value"] + 1))

    # --- Group 5: Multi-file workspace per family. ---
    workspace_dir = Path(tempfile.mkdtemp(prefix="b16f_selftest_"))
    try:
        for family_task in (f1, f2, f3, f4, f5, f6, f7, f8):
            _build_workspace(workspace_dir, family_task)
            target_path = workspace_dir / family_task["target_module"]
            distractor_path = workspace_dir / family_task["distractor_module"]
            support_path = workspace_dir / family_task["support_module"]
            test_path = workspace_dir / family_task["test_module"]
            checks.append(_check(f"workspace_{family_task['task_family']}_creates_target", target_path.is_file()))
            checks.append(_check(f"workspace_{family_task['task_family']}_creates_distractor", distractor_path.is_file()))
            checks.append(_check(f"workspace_{family_task['task_family']}_creates_support", support_path.is_file()))
            checks.append(_check(f"workspace_{family_task['task_family']}_creates_test", test_path.is_file()))
            target_src = target_path.read_text(encoding="utf-8")
            distractor_src = distractor_path.read_text(encoding="utf-8")
            checks.append(_check(f"workspace_{family_task['task_family']}_same_symbol", f"def {family_task['symbol']}()" in target_src and f"def {family_task['symbol']}()" in distractor_src))
            proc_before = subprocess.run([sys.executable, str(test_path)], check=False, capture_output=True, text=True, timeout=30)
            checks.append(_check(f"workspace_{family_task['task_family']}_test_fails_before_fix", proc_before.returncode != 0))

        # --- Group 6: Candidate generator. ---
        cands = _generate_candidates(f1)
        checks.append(_check("candidate_count_is_6", len(cands) == 6))
        target_cand = next(c for c in cands if c["path"] == f1["target_module"])
        distractor_cand = next(c for c in cands if c["path"] == f1["distractor_module"])
        support_cand = next(c for c in cands if c["path"] == f1["support_module"])
        checks.append(_check("target_candidate_has_agreement_3", target_cand["agreement"] == 3))
        checks.append(_check("distractor_candidate_has_agreement_1", distractor_cand["agreement"] == 1))
        checks.append(_check("support_candidate_has_agreement_2", support_cand["agreement"] == 2))
        checks.append(_check("distractor_bm25_higher_than_target", distractor_cand["normalized_score"] > target_cand["normalized_score"]))
        for c in cands:
            checks.append(_check(f"candidate_{c['path']}_no_gold_fields", "correct_value" not in c and "gold" not in c and "label" not in c))

        # --- Group 7: BEA v0.3 policy (runtime-clean; ignores gold). ---
        bea_accepted, bea_action, bea_trace, bea_stop, bea_mech = _bea_v03_policy(cands, f1["symbol"], 2)
        checks.append(_check("bea_accepts_2_candidates", len(bea_accepted) == 2))
        bea_paths = {c["path"] for c in bea_accepted}
        checks.append(_check("bea_accepts_target_as_anchor", f1["target_module"] in bea_paths))
        checks.append(_check("bea_accepts_support_as_anchor_or_diversity", f1["support_module"] in bea_paths))
        checks.append(_check("bea_does_not_accept_distractor_first", f1["distractor_module"] not in bea_paths or len(bea_accepted) > 2))
        checks.append(_check("bea_action_trace_nonempty", len(bea_action) >= 1))
        checks.append(_check("bea_budget_trace_nonempty", len(bea_trace) >= 1))
        checks.append(_check("bea_stop_reason_set", bea_stop != ""))
        checks.append(_check("bea_mech_summary_has_anchor_count_filled", "anchor_count_filled" in bea_mech))

        # BEA runtime-clean invariant: tainting gold must NOT change BEA selection.
        tainted_task = dict(f1)
        tainted_task["correct_value"] = 999999
        tainted_cands = _generate_candidates(tainted_task)
        bea_accepted_tainted, _, _, _, _ = _bea_v03_policy(tainted_cands, tainted_task["symbol"], 2)
        checks.append(_check("bea_selection_invariant_under_gold_tainting", {c["path"] for c in bea_accepted_tainted} == bea_paths))

        # --- Group 8: BM25 same-budget prefix. ---
        same_budget_k = len(bea_accepted)
        bm25_accepted = _bm25_prefix_same_budget(cands, same_budget_k)
        checks.append(_check("bm25_prefix_count_matches_same_budget_k", len(bm25_accepted) == same_budget_k))
        bm25_paths = {c["path"] for c in bm25_accepted}
        checks.append(_check("bm25_prefix_includes_distractor_high_score", f1["distractor_module"] in bm25_paths))
        checks.append(_check("bm25_prefix_excludes_target_low_score", f1["target_module"] not in bm25_paths))

        # --- Group 9: Pack builder. ---
        control_pack = _build_pack(ARM_CONTROL, f1, bea_accepted, bm25_accepted, same_budget_k)
        bm25_pack = _build_pack(ARM_BM25, f1, bea_accepted, bm25_accepted, same_budget_k)
        bea_pack = _build_pack(ARM_BEA, f1, bea_accepted, bm25_accepted, same_budget_k)
        checks.append(_check("control_pack_lacks_target_file_cue", control_pack["has_target_file_cue"] is False))
        checks.append(_check("control_pack_lacks_decisive_cue", control_pack["has_decisive_cue"] is False))
        checks.append(_check("control_pack_candidate_count_zero", control_pack["candidate_count"] == 0))
        checks.append(_check("bea_pack_has_target_file_cue", bea_pack["has_target_file_cue"] is True))
        checks.append(_check("bea_pack_has_symbol_cue", bea_pack["has_symbol_cue"] is True))
        checks.append(_check("bea_pack_has_decisive_cue", bea_pack["has_decisive_cue"] is True))
        checks.append(_check("bea_pack_same_budget_k_matches_bea_accepted", bea_pack["same_budget_k"] == same_budget_k))
        checks.append(_check("bm25_pack_same_budget_k_matches_bea_accepted", bm25_pack["same_budget_k"] == same_budget_k))
        checks.append(_check("bm25_pack_lacks_target_file_cue", bm25_pack["has_target_file_cue"] is False))
        checks.append(_check("bea_pack_richer_than_control", bea_pack["context_tokens"] > control_pack["context_tokens"]))

        # --- Group 10: Decisive cue text per family. ---
        for family_task in (f1, f2, f3, f4, f5, f6, f7, f8):
            cue_text = _decisive_cue_text(family_task)
            checks.append(_check(f"decisive_cue_text_nonempty_{family_task['task_family']}", len(cue_text) > 0))
            checks.append(_check(f"decisive_cue_text_no_raw_routing_prefix_{family_task['task_family']}", _ROUTING_PREFIX_SENTINEL not in cue_text))

        # --- Group 11: Private SCORE/event writers + fake valid BEA per family. ---
        score_dir, score_storage = _resolve_private_dir(None, "b16f_selftest_score")
        event_dir, event_storage = _resolve_private_dir(None, "b16f_selftest_event")
        score_path = score_dir / "b16f_selftest_score.jsonl"
        event_path = event_dir / "b16f_selftest_event.jsonl"
        score_path.write_text("", encoding="utf-8")
        event_path.write_text("", encoding="utf-8")

        for family_task in (f1, f2, f3, f4, f5, f6, f7, f8):
            _build_workspace(workspace_dir, family_task)
            cands_fam = _generate_candidates(family_task)
            bea_acc_fam, bea_act_fam, bea_tr_fam, bea_stop_fam, _ = _bea_v03_policy(cands_fam, family_task["symbol"], 2)
            k_fam = len(bea_acc_fam)
            bm25_acc_fam = _bm25_prefix_same_budget(cands_fam, k_fam)
            bea_pack_fam = _build_pack(ARM_BEA, family_task, bea_acc_fam, bm25_acc_fam, k_fam)
            fake_valid = {"action": "replace_return_value", "file": "target.py", "symbol": family_task["symbol"], "new_return_value": family_task["correct_value"]}
            run = _run_live_agent(workspace_dir, family_task, bea_pack_fam, bea_acc_fam, bea_act_fam, bea_tr_fam, bea_stop_fam, arm=ARM_BEA, allow_remote=False, require_workflow_dispatch=False, phase_run_id="b16f_selftest", score_path=score_path, event_path=event_path, fake_response=fake_valid)
            checks.append(_check(f"fake_valid_bea_{family_task['task_family']}_correct_file", run["correct_file_before_first_edit"] is True))
            checks.append(_check(f"fake_valid_bea_{family_task['task_family']}_no_wrong_file", run["wrong_file_edits"] == 0))
            checks.append(_check(f"fake_valid_bea_{family_task['task_family']}_tests_pass", run["tests_pass"] is True))
            checks.append(_check(f"fake_valid_bea_{family_task['task_family']}_solve", run["solve"] is True))
            checks.append(_check(f"fake_valid_bea_{family_task['task_family']}_provider_succeeded", run["provider_summary"]["calls_succeeded"] == 1))
            checks.append(_check(f"fake_valid_bea_{family_task['task_family']}_family_recorded", run["task_family"] == family_task["task_family"]))
            checks.append(_check(f"fake_valid_bea_{family_task['task_family']}_arm_recorded", run["arm"] == ARM_BEA))

        # --- Group 12: Fake invalid JSON. ---
        _build_workspace(workspace_dir, f1)
        run_invalid = _run_live_agent(workspace_dir, f1, control_pack, [], [], [], "", arm=ARM_CONTROL, allow_remote=False, require_workflow_dispatch=False, phase_run_id="b16f_selftest", score_path=score_path, event_path=event_path, fake_invalid=True)
        checks.append(_check("invalid_json_no_edit", run_invalid["tool_calls_before_first_edit"] == 0))
        checks.append(_check("invalid_json_tests_fail", run_invalid["tests_pass"] is False))
        checks.append(_check("invalid_json_count_incremented", run_invalid["invalid_json"] is True))
        checks.append(_check("no_raw_response_in_run_result", not any(k in run_invalid for k in ("raw_response", "response", "messages", "prompt"))))

        # --- Group 13: Private SCORE/event rows written. ---
        score_lines = score_path.read_text(encoding="utf-8").splitlines()
        event_lines = event_path.read_text(encoding="utf-8").splitlines()
        checks.append(_check("private_score_rows_written", len(score_lines) == 9))
        checks.append(_check("private_event_rows_written", len(event_lines) == 9))
        for i, line in enumerate(score_lines):
            try:
                json.loads(line)
                checks.append(_check(f"score_row_{i}_valid_json", True))
            except (json.JSONDecodeError, ValueError):
                checks.append(_check(f"score_row_{i}_valid_json", False))
        for i, line in enumerate(event_lines):
            try:
                json.loads(line)
                checks.append(_check(f"event_row_{i}_valid_json", True))
            except (json.JSONDecodeError, ValueError):
                checks.append(_check(f"event_row_{i}_valid_json", False))
        first_score_row = json.loads(score_lines[0])
        checks.append(_check("score_row_has_candidate_features", "candidate_features" in first_score_row))
        checks.append(_check("score_row_has_selected_candidates", "selected_candidates" in first_score_row))
        checks.append(_check("score_row_has_score_outcome", "score_outcome" in first_score_row))
        first_event_row = json.loads(event_lines[0])
        checks.append(_check("event_row_has_prompt", "prompt" in first_event_row))
        checks.append(_check("event_row_has_response", "response" in first_event_row))
        checks.append(_check("event_row_has_test_stdout", "test_stdout" in first_event_row))

        # --- Group 14: Edit action restrictions. ---
        valid, reason = _validate_edit_action({"action": "replace_return_value", "file": "evil.py", "symbol": "x", "new_return_value": 1}, f1)
        checks.append(_check("disallowed_file_rejected", not valid))
        valid, reason = _validate_edit_action({"action": "shell_exec", "file": "target.py", "symbol": "x", "new_return_value": 1}, f1)
        checks.append(_check("disallowed_action_rejected", not valid))
        valid, reason = _validate_edit_action({"action": "replace_return_value", "file": "distractor.py", "symbol": "x", "new_return_value": 1}, f1)
        checks.append(_check("distractor_file_rejected", not valid))
        valid, reason = _validate_edit_action({"action": "replace_return_value", "file": "support.py", "symbol": "x", "new_return_value": 1}, f1)
        checks.append(_check("support_file_rejected", not valid))
        valid, reason = _validate_edit_action({"action": "replace_return_value", "file": "target.py", "new_return_value": 1}, f1)
        checks.append(_check("missing_symbol_rejected", not valid))
        valid, reason = _validate_edit_action({"action": "replace_return_value", "file": "target.py", "symbol": "x", "new_return_value": "not_int"}, f1)
        checks.append(_check("non_int_return_rejected", not valid))
        valid, reason = _validate_edit_action([], f1)
        checks.append(_check("non_object_rejected", not valid))
        valid, reason = _validate_edit_action({"action": "replace_return_value", "file": "target.py", "symbol": "x", "new_return_value": 1}, f1)
        checks.append(_check("valid_action_accepted", valid))
        valid, reason = _validate_edit_action({"action": "choose_helper_constant", "file": "target.py", "symbol": "x", "new_return_value": 1}, f1)
        checks.append(_check("choose_helper_constant_accepted", valid))
        valid, reason = _validate_edit_action({"action": "no_op", "file": "target.py", "symbol": "x"}, f1)
        checks.append(_check("no_op_action_accepted", valid))

        # --- Group 15: Aggregate metrics + paired deltas + family + honest. ---
        _build_workspace(workspace_dir, f1)
        run_bea_solve = _run_live_agent(workspace_dir, f1, bea_pack, bea_accepted, bea_action, bea_trace, bea_stop, arm=ARM_BEA, allow_remote=False, require_workflow_dispatch=False, phase_run_id="b16f_selftest", score_path=score_path, event_path=event_path, fake_response={"action": "replace_return_value", "file": "target.py", "symbol": f1["symbol"], "new_return_value": f1["correct_value"]})
        _build_workspace(workspace_dir, f1)
        run_bm25_wrong = _run_live_agent(workspace_dir, f1, bm25_pack, bm25_accepted, [], [], "same_budget_bm25_prefix", arm=ARM_BM25, allow_remote=False, require_workflow_dispatch=False, phase_run_id="b16f_selftest", score_path=score_path, event_path=event_path, fake_response={"action": "replace_return_value", "file": "target.py", "symbol": f1["symbol"], "new_return_value": f1["buggy_value"]})
        _build_workspace(workspace_dir, f1)
        run_control_noop = _run_live_agent(workspace_dir, f1, control_pack, [], [], [], "control_sparse", arm=ARM_CONTROL, allow_remote=False, require_workflow_dispatch=False, phase_run_id="b16f_selftest", score_path=score_path, event_path=event_path, fake_response={"action": "no_op", "file": "target.py", "symbol": f1["symbol"]})
        arm_runs_test: dict[str, list[dict[str, Any]]] = {ARM_CONTROL: [run_control_noop], ARM_BM25: [run_bm25_wrong], ARM_BEA: [run_bea_solve]}
        arm_metrics_map: dict[str, dict[str, Any]] = {}
        for arm in ARMS:
            m, _ = _aggregate_arm_metrics(arm_runs_test[arm])
            arm_metrics_map[arm] = m
        checks.append(_check("aggregate_bea_solve_rate_1", arm_metrics_map[ARM_BEA]["solve_rate"] == 1.0))
        checks.append(_check("aggregate_bm25_solve_rate_0", arm_metrics_map[ARM_BM25]["solve_rate"] == 0.0))
        checks.append(_check("aggregate_control_solve_rate_0", arm_metrics_map[ARM_CONTROL]["solve_rate"] == 0.0))
        checks.append(_check("aggregate_control_no_op_rate_1", arm_metrics_map[ARM_CONTROL]["no_op_rate"] == 1.0))

        deltas = _compute_paired_deltas(arm_metrics_map)
        checks.append(_check("paired_deltas_count_correct", len(deltas) == 3 * len(DELTA_METRIC_NAMES)))
        primary_deltas = [d for d in deltas if d["baseline_arm"] == ARM_BM25 and d["treatment_arm"] == ARM_BEA]
        checks.append(_check("primary_contrast_deltas_present", len(primary_deltas) == len(DELTA_METRIC_NAMES)))
        primary_solve_delta = next(d for d in primary_deltas if d["metric"] == "solve_rate")
        checks.append(_check("primary_solve_rate_delta_positive", primary_solve_delta["delta"] == 1.0))
        sec_bea_sparse = [d for d in deltas if d["baseline_arm"] == ARM_CONTROL and d["treatment_arm"] == ARM_BEA]
        sec_bm25_sparse = [d for d in deltas if d["baseline_arm"] == ARM_CONTROL and d["treatment_arm"] == ARM_BM25]
        checks.append(_check("secondary_bea_vs_sparse_deltas_present", len(sec_bea_sparse) == len(DELTA_METRIC_NAMES)))
        checks.append(_check("secondary_bm25_vs_sparse_deltas_present", len(sec_bm25_sparse) == len(DELTA_METRIC_NAMES)))

        family_results = _aggregate_family_results(arm_runs_test)
        checks.append(_check("family_results_all_eight_families", set(r["task_family"] for r in family_results) == set(TASK_FAMILIES)))
        checks.append(_check("family_results_three_arms_per_family", all(sum(1 for r in family_results if r["task_family"] == fam) == 3 for fam in TASK_FAMILIES)))

        fss = _compute_family_signal_summary(family_results)
        checks.append(_check("family_signal_summary_has_counts", set(fss.keys()) == {"families_evaluated", "families_with_positive_solve_delta", "families_with_zero_solve_delta", "families_with_negative_solve_delta"}))

        honest = _compute_honest_signals(arm_metrics_map, deltas, fss)
        checks.append(_check("honest_signal_context_pack_observed_true", honest["context_pack_signal_observed"] is True))
        checks.append(_check("honest_signal_primary_solve_delta_positive", honest["primary_solve_rate_delta"] == 1.0))
        equal_metrics = dict(arm_metrics_map)
        equal_metrics[ARM_BEA] = dict(arm_metrics_map[ARM_BM25])
        zero_deltas = _compute_paired_deltas(equal_metrics)
        zero_fss = {"families_evaluated": 0, "families_with_positive_solve_delta": 0, "families_with_zero_solve_delta": 0, "families_with_negative_solve_delta": 0}
        honest_zero = _compute_honest_signals(equal_metrics, zero_deltas, zero_fss)
        checks.append(_check("honest_signal_zero_delta_not_observed", honest_zero["context_pack_signal_observed"] is False))

        # --- Group 16: Model display normalization. ---
        checks.append(_check("normalize_strips_routing_prefix", _normalize_model_display(_ROUTING_PREFIX_SENTINEL + "Kimi-K2.7-Code") == "Kimi-K2.7-Code"))
        checks.append(_check("normalize_empty_returns_unavailable", _normalize_model_display("") == "unavailable"))
        checks.append(_check("normalize_strips_unsafe_chars", _normalize_model_display(_ROUTING_PREFIX_SENTINEL + "Test;Model!@#") == "TestModel"))

        # --- Group 17: Env preservation. ---
        checks.append(_check("env_preservation_probe_restores_env", _self_test_probe_preserves_synthetic_provider_env()))
        enabled, failure_category, restored = _probe_missing_env_without_mutating_remote_env()
        checks.append(_check("probe_missing_env_returns_missing_env", not enabled and failure_category == provider_client.FAILURE_CATEGORY_MISSING_ENV))
        checks.append(_check("probe_missing_env_restores_env", restored))

        # --- Group 18: Private manifest hashes. ---
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

    # --- Group 19: Scanner rejections. ---
    checks.append(_check("scanner_rejects_tmp_workspace_path", bool(_scan_forbidden({"leaked_workspace": "/tmp/b16f_workspace_0"}))))
    checks.append(_check("scanner_rejects_file_path_value", bool(_scan_forbidden({"leaked_file": "target.py"}))))
    checks.append(_check("scanner_rejects_source_snippet", bool(_scan_forbidden({"leaked_snippet": "def resolve():\n    return 0\n"}))))
    checks.append(_check("scanner_rejects_patch_marker", bool(_scan_forbidden({"leaked_patch": "--- a/target.py\n+++ b/target.py\n"}))))
    checks.append(_check("scanner_rejects_test_output", bool(_scan_forbidden({"leaked_stdout": "test passed\nok\n"}))))
    checks.append(_check("scanner_rejects_task_id_key", bool(_scan_forbidden({"task_id": "abc"}))))
    checks.append(_check("scanner_rejects_raw_event_log", bool(_scan_forbidden({"leaked_log": '{"event": "edit", "file": "target.py"}'}))))
    checks.append(_check("scanner_rejects_stack_trace", bool(_scan_forbidden({"leaked_trace": "Traceback (most recent call last):\n"}))))
    checks.append(_check("scanner_rejects_content_sha_key", bool(_scan_forbidden({"content_sha": "abc"}))))
    checks.append(_check("scanner_rejects_hex_digest_value", bool(_scan_forbidden({"leaked_hash": "a" * 32}))))
    checks.append(_check("scanner_rejects_provider_auth_field_string", bool(_scan_forbidden({"leaked": "api_key=" + "sk-" + "abc"}))))
    checks.append(_check("scanner_rejects_endpoint_url_field_string", bool(_scan_forbidden({"leaked": "base_url=" + "https" + "://x.example"}))))
    checks.append(_check("scanner_rejects_raw_routing_prefix", bool(_scan_forbidden({"leaked": _ROUTING_PREFIX_SENTINEL + "Kimi-K2.7-Code"}))))
    checks.append(_check("scanner_rejects_url_value", bool(_scan_forbidden({"leaked": "https" + "://example.com"}))))
    checks.append(_check("scanner_rejects_prompt_key", bool(_scan_forbidden({"prompt": "abc"}))))
    checks.append(_check("scanner_rejects_response_key", bool(_scan_forbidden({"response": "abc"}))))
    checks.append(_check("scanner_rejects_messages_key", bool(_scan_forbidden({"messages": []}))))
    checks.append(_check("scanner_rejects_provider_payload_key", bool(_scan_forbidden({"provider_payload": {}}))))
    checks.append(_check("scanner_rejects_candidate_features_key", bool(_scan_forbidden({"candidate_features": []}))))
    checks.append(_check("scanner_rejects_selected_candidates_key", bool(_scan_forbidden({"selected_candidates": []}))))
    checks.append(_check("scanner_rejects_score_outcome_key", bool(_scan_forbidden({"score_outcome": {}}))))
    checks.append(_check("scanner_rejects_bea_action_trace_key", bool(_scan_forbidden({"bea_action_trace": []}))))
    checks.append(_check("scanner_rejects_bea_budget_trace_key", bool(_scan_forbidden({"bea_budget_trace": []}))))
    checks.append(_check("scanner_rejects_sentinel_canary", bool(_scan_forbidden({"leaked": _SECRET_SENTINEL}))))

    # --- Group 20: Scanner allows legitimate aggregate values. ---
    checks.append(_check("scanner_allows_arm_name_control", not _scan_forbidden({"arm": "control_sparse"})))
    checks.append(_check("scanner_allows_arm_name_bm25", not _scan_forbidden({"arm": "bm25_same_budget_context_pack"})))
    checks.append(_check("scanner_allows_arm_name_bea", not _scan_forbidden({"arm": "bea_v03_context_pack"})))
    checks.append(_check("scanner_allows_task_family_names", not _scan_forbidden({"task_family": "operation_ambiguity"})))
    checks.append(_check("scanner_allows_paired_deltas_records", not _scan_forbidden({"paired_deltas": [{"baseline_arm": "bm25_same_budget_context_pack", "treatment_arm": "bea_v03_context_pack", "metric": "solve_rate", "delta": 1.0}]})))
    checks.append(_check("scanner_allows_family_results_records", not _scan_forbidden({"task_family_results": [{"task_family": "boundary_condition", "arm": "bea_v03_context_pack", "run_count": 1, "solve_rate": 1.0, "tests_pass_rate": 1.0, "correct_file_before_first_edit_rate": 1.0, "wrong_file_edit_rate": 0.0}]})))
    checks.append(_check("scanner_allows_model_display_category", not _scan_forbidden({"model_display_category": "Kimi-K2.7-Code"})))
    checks.append(_check("scanner_allows_honest_signal_fields", not _scan_forbidden({"honest_signals": {"context_pack_signal_observed": True, "primary_solve_rate_delta": 1.0, "primary_tests_pass_rate_delta": 1.0, "primary_wrong_file_edit_rate_delta": 0.0, "families_evaluated": 8, "families_with_positive_solve_delta": 8, "families_with_zero_solve_delta": 0, "families_with_negative_solve_delta": 0}})))
    checks.append(_check("scanner_allows_private_score_manifest", not _scan_forbidden({"private_score_manifest": {"records_written": True, "record_count": 24, "schema_version": "b16f_private_score.v1", "manifest_hash": "abc123", "storage_class": "tmp_private", "path_publicly_serialized": False}})))
    checks.append(_check("scanner_allows_private_event_manifest", not _scan_forbidden({"private_event_manifest": {"records_written": True, "record_count": 24, "schema_version": "b16f_private_event.v1", "manifest_hash": "def456", "storage_class": "tmp_private", "path_publicly_serialized": False}})))
    checks.append(_check("scanner_allows_failure_category_token", not _scan_forbidden({"failure_category": "ok"})))
    checks.append(_check("scanner_allows_primary_contrast", not _scan_forbidden({"primary_contrast": "bea_v03_context_pack_vs_bm25_same_budget_context_pack"})))

    # --- Group 21: Fail-closed generation. ---
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

    # --- Group 22: Public artifact self-scan is clean. ---
    checks.append(_check("public_report_forbidden_scan_clean", skeleton["forbidden_scan"]["status"] == "pass"))
    checks.append(_check("public_report_no_forbidden_key_anywhere", not any(_has_dict_key_anywhere(skeleton, bad) for bad in ("task_id", "workspace_path", "file_path", "target_file", "path", "file", "snippet", "code", "patch", "diff", "test_output", "event_log", "stack_trace", "content_sha", "content_hash", "api_key", "base_url", "provider_key", "secret", "token", "stdout", "stderr", "rows", "per_run", "predictions", "prompt", "messages", "response", "provider_payload", "request", "request_body", "model_id_raw", "support_module", "candidate_features", "selected_candidates", "bea_action_trace", "bea_budget_trace", "score_outcome"))))

    # --- Group 23: CLI argument surface. ---
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

    # --- Group 24: Remote gating. ---
    enabled, failure_category = provider_client._check_remote_enabled(allow_remote=False, require_workflow_dispatch=False)
    checks.append(_check("blocked_when_allow_remote_false", not enabled and failure_category == provider_client.FAILURE_CATEGORY_REMOTE_NOT_ENABLED))
    blocked_rep = _build_public_report([], True, status=STATUS_BLOCKED_REMOTE, live_run_executed=False)
    checks.append(_check("blocked_report_live_flags_false", all(blocked_rep.get(flag) is False for flag in LIVE_TRUE_FLAGS if flag not in ("aggregate_only_public_artifact", "diagnostic_only"))))
    checks.append(_check("blocked_report_forbidden_scan_pass", blocked_rep["forbidden_scan"]["status"] == "pass"))

    # --- Group 25: Three-arm structure. ---
    checks.append(_check("arms_tuple_has_control_first", ARMS[0] == ARM_CONTROL))
    checks.append(_check("arms_tuple_has_bm25_second", ARMS[1] == ARM_BM25))
    checks.append(_check("arms_tuple_has_bea_third", ARMS[2] == ARM_BEA))
    checks.append(_check("default_total_runs_24", DEFAULT_TASK_COUNT * len(ARMS) == 24))

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
            "B16-F BEA-derived context pack live-provider downstream "
            "paired smoke (public aggregate-only artifact; synthetic "
            "public task-family matrix; three arms: control_sparse, "
            "bm25_same_budget_context_pack, bea_v03_context_pack; "
            "fresh /tmp workspace per task+arm; real file edits + "
            "real subprocess tests; live LLM provider only when "
            "--allow-remote + remote opt-in gate + provider env; primary "
            "contrast BEA vs same-budget BM25; no raw prompt/response/"
            "payload committed; CI pass does NOT require BEA "
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
        help="allow live provider calls (requires remote opt-in provider gate)",
    )
    ap.add_argument(
        "--require-workflow-dispatch",
        action="store_true",
        help="require the workflow-dispatch provider gate for live calls",
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
    ap.add_argument(
        "--private-score-dir",
        type=str,
        default=None,
        help="explicit private SCORE JSONL directory (must be under /tmp or runs/)",
    )
    ap.add_argument(
        "--private-event-dir",
        type=str,
        default=None,
        help="explicit private event JSONL directory (must be under /tmp or runs/)",
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
