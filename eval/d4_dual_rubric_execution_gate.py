#!/usr/bin/env python3
"""D4a Dual-Rubric Execution Gate / Dry-Run — public gate artifact only.

This module implements the **D4a dual-rubric execution gate / dry-run**.
D4a is the *execution gate* that validates the control plane required
before any future local/private true E-score / S-score label calibration
(D4b) can run. It is the dry-run public artifact follow-on to D3 (which
preregistered the label protocol only).

D4a **does not** collect real labels, **does not** read private records
by default, **does not** compute true calibration metrics, **does not**
measure inter-rater agreement, **does not** claim true/proxy calibration,
and **does not** change runtime behavior. It validates:

* CLI/privacy guards (private dry-run opt-in, `/tmp`-only output,
  validate-before-read);
* D3 protocol constants and required gates (k_min=5, min_total_labels=50,
  agreement required, confidence intervals required);
* synthetic in-memory gate logic (min-N, small-cell suppression,
  agreement availability, confidence-interval availability);
* fail-closed forbidden-output scanning;
* documentation boundaries.

Claim boundary (binding):

* This is **eval/diagnostic only**. It is NOT a runtime change, NOT a
  retriever/pack/model/backend/default-policy change, and NOT an
  EvidenceCore semantic change.
* Claim level: ``dual_rubric_execution_gate_dry_run_only``.
* Rubric version: ``d3_true_dual_rubric_label_protocol_v1`` (D3 protocol
  checked; D4a does not redefine the rubric).
* Status: ``execution_gate_ready_no_labels_collected``; mode
  ``public_gate_dry_run``; phase ``D4a``; next phase
  ``D4b_local_private_label_collection_smoke``.
* The default committed artifact collects NO labels, reads NO private
  label bundles, computes NO calibration metrics, measures NO
  inter-rater agreement, claims NO true/proxy calibration, and passes NO
  public-release gate.

Two strictly separated modes:

* **D4a default (committed)**: public gate dry-run artifact. No private
  input. All label/private/calibration flags false; execution-control
  flags true only for the validated dry-run controls; diagnostic flags
  true.

* **D4a private dry-run (opt-in, NOT committed)**: explicit
  ``--allow-private-labels --input <path> --out /tmp/...``. Validates a
  local/private label-bundle-shaped JSON only to validate shape/gates.
  Writes `/tmp` output only. Never serializes input/output paths,
  basenames, raw labels, rater IDs, annotation rows, row hashes, or
  exact real private sample sizes. Does NOT compute or claim true
  calibration metrics.

Run::

    python3 -m py_compile eval/d4_dual_rubric_execution_gate.py
    python3 eval/d4_dual_rubric_execution_gate.py --self-test
    python3 eval/d4_dual_rubric_execution_gate.py \
        --out artifacts/d4_dual_rubric_execution_gate/\\
d4_dual_rubric_execution_gate_report.json
    # D4a private dry-run (NOT committed; /tmp only):
    python3 eval/d4_dual_rubric_execution_gate.py \
        --allow-private-labels --input /tmp/private_bundle.json \
        --out /tmp/d4a_gate_smoke.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "d4_dual_rubric_execution_gate.v1"
GENERATED_BY = "eval/d4_dual_rubric_execution_gate.py"
CLAIM_LEVEL = "dual_rubric_execution_gate_dry_run_only"
RUBRIC_VERSION = "d3_true_dual_rubric_label_protocol_v1"
TARGET_STATUS = "execution_gate_ready_no_labels_collected"
MODE_PUBLIC = "public_gate_dry_run"
MODE_PRIVATE = "private_dry_run_gate_smoke"
PHASE = "D4a"
NEXT_PHASE = "D4b_local_private_label_collection_smoke"
STATUS_PRIVATE_OK = "private_dry_run_gate_smoke_completed"

DEFAULT_OUT = Path(
    "artifacts/d4_dual_rubric_execution_gate/"
    "d4_dual_rubric_execution_gate_report.json"
)

# Fixed sanitized error for any private-bundle load/parse/schema/privacy
# failure. Never includes the input path, basename, raw JSON, or label
# text.
PRIVATE_LOAD_ERROR_MESSAGE = (
    "error: failed to load private labels "
    "(schema/privacy/parse error; details suppressed)"
)

# ---------------------------------------------------------------------------
# D3 protocol constants (D4a checks these; it does not redefine the
# rubric). Mirrors D3 future_execution_gates / public_release_thresholds.
# ---------------------------------------------------------------------------

D3_PROTOCOL_VERSION = "d3_true_dual_rubric_label_protocol_v1"
K_MIN = 5
MIN_TOTAL_LABELS = 50
AGREEMENT_REQUIRED = True
CONFIDENCE_INTERVALS_REQUIRED = True

# Fixed gate category names (approved enum for the private dry-run
# bundle cells). These are category labels only; no concrete
# repo/path/snippet content.
GATE_CATEGORY_NAMES: tuple[str, ...] = (
    "primary_evidence",
    "dependency_support",
    "weak_candidates",
    "abstained",
)

# ---------------------------------------------------------------------------
# Private dry-run bundle schema (local-only, sanitized, aggregate-only)
# ---------------------------------------------------------------------------

# The private dry-run bundle accepts a synthetic/private-shaped AGGREGATE
# summary (counts and booleans), NOT raw rows. It must NOT contain raw
# labels, rater IDs, annotation rows, paths, or per-row hashes. The
# schema validator rejects any key outside this allowlist (fail-closed).
PRIVATE_BUNDLE_SCHEMA = "d4_private_label_bundle_dry_run_v1"
ALLOWED_BUNDLE_KEYS: frozenset[str] = frozenset(
    {
        "schema",
        "total_labels",
        "cells",
        "second_rater_present",
        "agreement_available",
        "confidence_intervals_available",
        "min_cell_n",
    }
)

# ---------------------------------------------------------------------------
# Default artifact false flags (all MUST be false in the committed public
# artifact). D4a collects no labels, reads no private bundles, computes no
# calibration metrics, and passes no release gate.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "labels_collected": False,
    "private_label_bundle_read": False,
    "private_label_bundle_persisted": False,
    "private_records_read": False,
    "raw_private_records_read": False,
    "raw_labels_persisted": False,
    "raw_label_rows_emitted": False,
    "private_output_path_emitted": False,
    "private_input_path_emitted": False,
    "private_output_committed": False,
    "calibration_metrics_computed": False,
    "inter_rater_agreement_measured": False,
    "agreement_metrics_computed": False,
    "confidence_intervals_computed": False,
    "true_e_s_calibration_claimed": False,
    "proxy_calibration_claimed": False,
    "public_release_gate_passed": False,
    "real_label_bundle_gate_passed": False,
}

# Execution-control flags true only for the validated dry-run controls
# (each is proven by a self-test).
EXECUTION_CONTROL_FLAGS: dict[str, bool] = {
    "execution_controls_validated": True,
    "private_cli_guard_validated": True,
    "tmp_output_guard_validated": True,
    "validate_before_read_guard_validated": True,
    "sanitized_error_guard_validated": True,
    "small_cell_suppression_gate_validated": True,
    "min_total_n_gate_validated": True,
    "agreement_required_gate_validated": True,
    "confidence_interval_gate_validated": True,
}

# D3 protocol check fields.
D3_PROTOCOL_FLAGS: dict[str, Any] = {
    "d3_protocol_checked": True,
    "d3_protocol_version": D3_PROTOCOL_VERSION,
    "d3_required_gates_present": True,
}

# No-claim / no-runtime-change flags (all MUST be false).
NO_CLAIM_FLAGS: dict[str, bool] = {
    "promotion_ready": False,
    "default_should_change": False,
    "downstream_agent_value_proven": False,
    "runtime_behavior_changed": False,
    "retriever_changed": False,
    "pack_builder_changed": False,
    "model_calls_changed": False,
    "backend_changed": False,
    "default_policy_changed": False,
    "evidencecore_semantics_changed": False,
    "runtime_clean_general_algorithm_claimed": False,
    "ood_temporal_supported": False,
    "quiver_systems_supported": False,
}

# Diagnostic flags (all MUST be true).
DIAGNOSTIC_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
    "not_evidence": True,
}

# ---------------------------------------------------------------------------
# Forbidden-output scanner (D4a-specific, fail-closed)
# ---------------------------------------------------------------------------

# Sensitive KEY names that must NEVER appear as dict keys anywhere in a
# public or private dry-run JSON output. Superset of D3's set, extended
# with rater/annotator/disagreement keys for the label-bundle domain.
FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset(
    {
        # location / span
        "path", "span", "line_range", "start_line", "end_line",
        "start_byte", "end_byte", "line_ranges", "spans",
        # content / hash
        "content_sha", "content_hash", "hash", "digest", "sha256",
        "md5", "sha1",
        "snippet", "snippets", "excerpt", "excerpts", "candidate_text",
        "text", "code", "code_snippet", "source_code", "content", "body",
        # identifiers
        "task_id", "repo_id", "repo", "instance_id", "row_id",
        "record_id", "id", "name", "filename", "filepath",
        # labels / qrels / annotations / raters
        "label", "labels", "qrels", "gold", "gold_label", "gold_labels",
        "gold_answer", "predicted_answer", "answer", "question",
        "raw_label", "raw_labels", "annotation_row", "annotation_rows",
        "annotator_id", "rater_id", "per_row_hash", "row_hash",
        "disagreement_example", "disagreement_examples",
        "true_label", "true_e_score", "true_s_score",
        # prompts / responses / model outputs
        "query", "prompt", "response", "model_response", "model_output",
        "provider_payload", "raw_payload", "api_response", "response_body",
        # rows / records
        "raw_rows", "rows", "records", "tasks", "row_values",
        # patches / tests
        "patch", "test_patch", "tests",
        # secrets
        "api_key", "api_token", "api_secret", "base_url", "provider_key",
        "authorization",
        # private-record / model-assisted fields
        "private_record_hash", "private_records", "private_rows",
        "candidate_id", "gold_spans", "raw_query", "raw_snippet",
        "raw_prompt", "raw_response",
        "model_assisted_label", "model_assisted_labels",
    }
)

# Known-safe provenance value paths (allowlisted for hex_digest / path_like
# value checks only). The forbidden dict-key check is NOT relaxed by this.
SAFE_VALUE_KEY_NAMES: frozenset[str] = frozenset(
    {
        "schema_version",
        "generated_by",
        "generated_at",
        "claim_level",
        "rubric_version",
        "status",
        "mode",
        "phase",
        "next_phase",
        "d3_protocol_version",
    }
)

# Value patterns that indicate leaked row-level / candidate / annotation
# data. D4a rejects ALL URLs (no URL allowlist) per the fail-closed rule.
_RE_URL_VALUE = re.compile(r"https?://", re.IGNORECASE)
_RE_HEX_DIGEST = re.compile(r"[A-Fa-f0-9]{32,}")
_RE_SECRET_LIKE = re.compile(
    r"(?:api[_-]?key|api[_-]?token|api[_-]?secret|base[_-]?url"
    r"|provider[_-]?key|authorization[_-]?bearer)",
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
# The sentinel used by self-tests; the scanner must never let it through
# in a committed/private output. Used as a value-leak canary.
_SECRET_SENTINEL = "SECRET_LABEL_SENTINEL"


def _path_last_key(path: str) -> str:
    """Extract the last key segment from a dotted JSON path."""
    last = path.rsplit(".", 1)[-1]
    return last.split("[")[0]


def _is_safe_value_path(path: str) -> bool:
    """Check if a JSON path ends with a known-safe value key."""
    return _path_last_key(path) in SAFE_VALUE_KEY_NAMES


def _scan_forbidden(obj: Any, path: str = "$") -> list[dict[str, Any]]:
    """Strict recursive scanner for public/private JSON outputs.

    Returns a list of violation dicts with ``category`` and ``path``
    (JSON path), NEVER the leaked value itself. Fail-closed: any
    violation means the output would leak.

    Rejects forbidden dict keys (path/span/content_sha/snippet/query/
    task_id/repo_id/repo/label/raw_label/annotation_row/rater_id/
    annotator_id/disagreement_example/per_row_hash/model_output/etc.)
    anywhere, and rejects value patterns: ANY URL, 32/40/64-char hex
    digests, secret-like strings, path-like strings (``src/foo.py``,
    ``/private/foo.jsonl``), multiline strings, raw JSON fragments,
    raw line-range strings (``12-34``), and the self-test sentinel.

    Allows safe protocol / gate / level / category strings only if they
    are not row-like (e.g. ``primary_evidence``, ``k_min``, ``D4a``).
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
        if len(obj) > 256:
            violations.append({"category": "long_string", "path": path})
        elif _RE_URL_VALUE.search(obj) and not safe_value:
            violations.append({"category": "url_value", "path": path})
        elif not safe_value and _RE_HEX_DIGEST.search(obj):
            violations.append({"category": "hex_digest_value", "path": path})
        elif _RE_SECRET_LIKE.search(obj):
            violations.append({"category": "secret_like_value", "path": path})
        elif _RE_FILE_PATH_VALUE.search(obj) and not safe_value:
            violations.append({"category": "path_like_value", "path": path})
        elif "\n" in obj:
            violations.append({"category": "multiline_value", "path": path})
        elif _RE_RAW_JSON.search(obj):
            violations.append({"category": "raw_json_fragment", "path": path})
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
    """Run the forbidden scanner and return a sanitized summary."""
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
            f"forbidden content leak; refusing to write artifact: "
            f"{scan['categories']}"
        )


def _refuse_on_self_test_failure(report: dict[str, Any]) -> None:
    """Refuse successful artifact generation if self-test failed."""
    if report.get("self_test_passed") is not True:
        raise SystemExit(
            "self-test failed; refusing to write artifact"
        )


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


# ---------------------------------------------------------------------------
# Gate logic (synthetic, in-memory; no calibration metrics computed)
# ---------------------------------------------------------------------------


def _is_nonneg_int(value: Any) -> bool:
    """True iff ``value`` is a non-bool non-negative int."""
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0
    )


def _all_cells_pass_k_min(cells: Any, k_min: int) -> bool:
    """True iff ``cells`` is a non-empty list of {category,n} dicts with
    every ``n >= k_min`` (small-cell suppression gate)."""
    if not isinstance(cells, list) or len(cells) == 0:
        return False
    for c in cells:
        if not isinstance(c, dict):
            return False
        n = c.get("n")
        if not isinstance(n, int) or isinstance(n, bool):
            return False
        if n < k_min:
            return False
    return True


def evaluate_gate_logic(bundle: dict[str, Any]) -> dict[str, bool]:
    """Evaluate the D4a execution gate logic over a sanitized aggregate bundle.

    This ONLY checks gate thresholds. It does NOT compute calibration
    metrics, inter-rater agreement, or confidence intervals. It returns
    per-gate pass/fail booleans and an overall gate verdict.

    Gates (constants from D3):
      * min_total_n: ``total_labels >= 50``.
      * small_cell_suppression: every cell ``n >= k_min`` (5); any cell
        below 5 fails the gate (cells would be suppressed).
      * agreement_required: a second rater is present AND agreement is
        available (unavailable => fail).
      * confidence_interval: confidence intervals are available.
    """
    total = bundle.get("total_labels", 0)
    cells = bundle.get("cells", [])
    second_rater = bool(bundle.get("second_rater_present", False))
    agreement = bool(bundle.get("agreement_available", False))
    ci = bool(bundle.get("confidence_intervals_available", False))

    min_total_n_passed = _is_nonneg_int(total) and total >= MIN_TOTAL_LABELS
    small_cell_passed = _all_cells_pass_k_min(cells, K_MIN)
    agreement_passed = second_rater and agreement
    ci_passed = ci

    overall = (
        min_total_n_passed
        and small_cell_passed
        and agreement_passed
        and ci_passed
    )
    return {
        "min_total_n_gate_passed": min_total_n_passed,
        "small_cell_suppression_gate_passed": small_cell_passed,
        "agreement_required_gate_passed": agreement_passed,
        "confidence_interval_gate_passed": ci_passed,
        "overall_gate_passed": overall,
    }


# ---------------------------------------------------------------------------
# Private dry-run bundle schema validation (fail-closed, sanitized)
# ---------------------------------------------------------------------------


class _PrivateLabelLoadError(Exception):
    """Raised when a private label bundle fails schema/privacy/parse checks.

    The CLI never surfaces this exception's message; it always emits the
    fixed sanitized ``PRIVATE_LOAD_ERROR_MESSAGE`` instead.
    """


def _validate_bundle_schema(bundle: Any) -> None:
    """Validate a private dry-run bundle is sanitized (aggregate-only).

    Raises ``_PrivateLabelLoadError`` if the bundle is malformed, has an
    unknown schema, contains keys outside the allowlist (e.g. raw labels,
    rater IDs, annotation rows, paths), or has wrong-typed values. The
    bundle must be a synthetic aggregate summary only: counts and
    booleans, NOT raw rows.
    """
    if not isinstance(bundle, dict):
        raise _PrivateLabelLoadError()
    # Fail-closed: reject any key outside the allowlist (catches raw_label,
    # rater_id, annotation_row, path, etc.).
    for key in bundle.keys():
        if key not in ALLOWED_BUNDLE_KEYS:
            raise _PrivateLabelLoadError()
    if bundle.get("schema") != PRIVATE_BUNDLE_SCHEMA:
        raise _PrivateLabelLoadError()
    total = bundle.get("total_labels")
    if (
        not isinstance(total, int)
        or isinstance(total, bool)
        or total < 0
    ):
        raise _PrivateLabelLoadError()
    cells = bundle.get("cells")
    if not isinstance(cells, list) or len(cells) == 0:
        raise _PrivateLabelLoadError()
    for c in cells:
        if not isinstance(c, dict):
            raise _PrivateLabelLoadError()
        if set(c.keys()) != {"category", "n"}:
            raise _PrivateLabelLoadError()
        if c.get("category") not in GATE_CATEGORY_NAMES:
            raise _PrivateLabelLoadError()
        n = c.get("n")
        if not isinstance(n, int) or isinstance(n, bool) or n < 0:
            raise _PrivateLabelLoadError()
    for flag in (
        "second_rater_present",
        "agreement_available",
        "confidence_intervals_available",
    ):
        if not isinstance(bundle.get(flag), bool):
            raise _PrivateLabelLoadError()
    mn = bundle.get("min_cell_n")
    if mn is not None and (
        not isinstance(mn, int)
        or isinstance(mn, bool)
        or mn < 0
    ):
        raise _PrivateLabelLoadError()


# ---------------------------------------------------------------------------
# Default file-based loader / existence probe (injectable for self-test)
# ---------------------------------------------------------------------------


def _default_loader(input_path: Path) -> dict[str, Any]:
    """Read, parse, and validate a private label bundle file.

    Raises ``_PrivateLabelLoadError`` on any I/O, parse, or schema
    failure. The CLI converts this into the fixed sanitized error.
    """
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        raise _PrivateLabelLoadError()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        raise _PrivateLabelLoadError()
    _validate_bundle_schema(data)
    return data


def _default_exists(input_path: Path) -> bool:
    """Default input existence probe (stat only; never reads content)."""
    try:
        return input_path.is_file()
    except OSError:
        return False


# ---------------------------------------------------------------------------
# CLI argument validation (pure: no I/O before the input is opened)
# ---------------------------------------------------------------------------


def _is_under_tmp(path: Path) -> bool:
    """Lexical check that ``path`` is under ``/tmp`` (no filesystem access)."""
    s = os.path.normpath(str(path))
    tmp = os.path.normpath("/tmp")
    return s == tmp or s.startswith(tmp + os.sep)


def _is_committed_out(path: Path) -> bool:
    """Lexical check that ``path`` is the committed artifact path."""
    return (
        os.path.normpath(str(path))
        == os.path.normpath(str(DEFAULT_OUT))
    )


def _validate_cli_args(
    *,
    allow_private_labels: bool,
    input_path: Path | None,
    out_path: Path | None,
) -> str | None:
    """Validate CLI argument combinations for public vs private dry-run.

    Pure: performs NO filesystem I/O (only lexical path checks). Returns
    an error message string if invalid, or ``None`` if valid. The guards
    below are evaluated BEFORE the input is opened or stat'd, proving
    validate-before-read.

    * ``--input`` without ``--allow-private-labels`` -> error.
    * ``--allow-private-labels`` without ``--input`` -> error.
    * ``--allow-private-labels`` without explicit ``--out`` -> error.
    * ``--allow-private-labels`` with the committed artifact path as
      ``--out`` -> error (before read).
    * ``--allow-private-labels`` with a non-``/tmp`` ``--out`` -> error
      (before read).
    * ``--allow-private-labels --input <path> --out /tmp/...`` -> valid.
    """
    if input_path is not None and not allow_private_labels:
        return (
            "--input requires --allow-private-labels; refusing to read "
            "private labels without explicit opt-in"
        )
    if allow_private_labels and input_path is None:
        return (
            "--allow-private-labels requires --input; no private input "
            "path provided"
        )
    if allow_private_labels:
        if out_path is None:
            return (
                "--allow-private-labels requires explicit --out under "
                "/tmp; refusing to use the committed artifact path"
            )
        if _is_committed_out(out_path):
            return (
                "--allow-private-labels requires --out under /tmp; "
                "refusing to write to the committed artifact path"
            )
        if not _is_under_tmp(out_path):
            return (
                "--allow-private-labels requires --out under /tmp; "
                "refusing to write private-mode output elsewhere"
            )
    return None


# ---------------------------------------------------------------------------
# Private dry-run runner (validate-before-read; sanitized errors)
# ---------------------------------------------------------------------------


def _run_private_dry_run(
    *,
    allow_private_labels: bool,
    input_path: Path | None,
    out_path: Path | None,
    loader: Any,
    input_exists: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    """Run the private dry-run gate smoke.

    Returns ``(report, error)``: exactly one is non-``None``.

    The CLI/output guards are validated BEFORE the input is opened or
    stat'd (validate-before-read). Any load/parse/schema failure returns
    the fixed sanitized error; the input path, basename, raw JSON, and
    label text are never surfaced.
    """
    err = _validate_cli_args(
        allow_private_labels=allow_private_labels,
        input_path=input_path,
        out_path=out_path,
    )
    if err is not None:
        # Validation failed: NO input access performed.
        return None, err
    # Validation passed: the input may now be touched.
    assert input_path is not None and out_path is not None
    if not input_exists(input_path):
        return None, PRIVATE_LOAD_ERROR_MESSAGE
    try:
        bundle = loader(input_path)
    except Exception:
        return None, PRIVATE_LOAD_ERROR_MESSAGE
    try:
        _validate_bundle_schema(bundle)
    except _PrivateLabelLoadError:
        return None, PRIVATE_LOAD_ERROR_MESSAGE
    gate = evaluate_gate_logic(bundle)
    report = _build_private_dry_run_report(gate)
    return report, None


# ---------------------------------------------------------------------------
# Report builders
# ---------------------------------------------------------------------------


def _build_gate_thresholds() -> dict[str, Any]:
    return {
        "k_min": K_MIN,
        "min_total_labels": MIN_TOTAL_LABELS,
        "agreement_required": AGREEMENT_REQUIRED,
        "confidence_intervals_required": CONFIDENCE_INTERVALS_REQUIRED,
    }


def _build_private_dry_run_harness_info() -> dict[str, Any]:
    return {
        "available": True,
        "opt_in_required": True,
        "output_location": "tmp_only_local_private",
        "committed": False,
        "claims_calibration": False,
    }


def _self_test_category_summary(
    checks: list[dict[str, Any]],
) -> dict[str, int]:
    passed = sum(1 for c in checks if c.get("passed"))
    return {
        "total": len(checks),
        "passed": passed,
        "failed": len(checks) - passed,
    }


def _build_public_report(
    checks: list[dict[str, Any]], all_passed: bool
) -> dict[str, Any]:
    """Assemble the public gate dry-run report (fail-closed scan).

    The default committed artifact. No labels collected, no private
    bundles read, no calibration metrics computed.
    """
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "rubric_version": RUBRIC_VERSION,
        "status": TARGET_STATUS if all_passed else "self_test_failed",
        "mode": MODE_PUBLIC,
        "phase": PHASE,
        "next_phase": NEXT_PHASE,
        "gate_thresholds": _build_gate_thresholds(),
        "gate_category_names": list(GATE_CATEGORY_NAMES),
        "private_dry_run_harness": _build_private_dry_run_harness_info(),
        "self_test_summary": _self_test_category_summary(checks),
        "self_test_checks": checks,
        "self_test_passed": all_passed,
        # D3 protocol check (flat).
        **D3_PROTOCOL_FLAGS,
        # Default false flags (flat).
        **DEFAULT_FALSE_FLAGS,
        # Execution-control flags (flat; true only for validated controls).
        **EXECUTION_CONTROL_FLAGS,
        # No-claim / no-runtime-change flags (flat).
        **NO_CLAIM_FLAGS,
        # Diagnostic flags (flat).
        **DIAGNOSTIC_FLAGS,
    }

    # Fail-closed forbidden scan before returning.
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_leak"
    return report


def _build_private_dry_run_report(gate: dict[str, bool]) -> dict[str, Any]:
    """Assemble the private dry-run gate smoke report (NOT committed; /tmp only).

    Contains ONLY: identity fields, fixed gate thresholds/category names,
    gate pass/fail booleans, and sanitized flags. Does NOT echo any
    bundle counts, bundle categories, input/output paths, basenames, raw
    labels, rater IDs, annotation rows, row hashes, or exact real private
    sample sizes.
    """
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "rubric_version": RUBRIC_VERSION,
        "status": STATUS_PRIVATE_OK,
        "mode": MODE_PRIVATE,
        "phase": PHASE,
        "next_phase": NEXT_PHASE,
        "gate_thresholds": _build_gate_thresholds(),
        "gate_category_names": list(GATE_CATEGORY_NAMES),
        "gate_results": dict(gate),
        # D3 protocol check (flat).
        **D3_PROTOCOL_FLAGS,
        # Private dry-run did transiently read a private label bundle (in
        # memory only); it did NOT read raw private records, persist the
        # bundle, emit rows, or commit output.
        "labels_collected": False,
        "private_label_bundle_read": True,
        "private_label_bundle_persisted": False,
        "private_records_read": False,
        "raw_private_records_read": False,
        "raw_labels_persisted": False,
        "raw_label_rows_emitted": False,
        "private_output_path_emitted": False,
        "private_input_path_emitted": False,
        "private_output_committed": False,
        "calibration_metrics_computed": False,
        "inter_rater_agreement_measured": False,
        "agreement_metrics_computed": False,
        "confidence_intervals_computed": False,
        "true_e_s_calibration_claimed": False,
        "proxy_calibration_claimed": False,
        # Dry-run: NOT a public-release gate pass and NOT a real bundle gate.
        "public_release_gate_passed": False,
        "real_label_bundle_gate_passed": False,
        # Execution-control flags (flat).
        **EXECUTION_CONTROL_FLAGS,
        # No-claim / no-runtime-change flags (flat).
        **NO_CLAIM_FLAGS,
        # Diagnostic flags (flat).
        **DIAGNOSTIC_FLAGS,
    }

    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_leak"
    return report


def build_report() -> dict[str, Any]:
    """Assemble the public gate dry-run report (fail-closed scan).

    Runs the deterministic self-test checks and embeds their results,
    then assembles the full public report (which re-scans itself).
    """
    checks, all_passed = run_self_test_checks()
    return _build_public_report(checks, all_passed)


# ---------------------------------------------------------------------------
# Self-test probe (records every input access for validate-before-read)
# ---------------------------------------------------------------------------


class _ReadProbe:
    """Records every loader/exists call to prove validate-before-read."""

    def __init__(self, bundle: dict[str, Any] | None = None) -> None:
        self.calls: list[tuple[str, str]] = []
        self._bundle = bundle

    def loader(self, path: Path) -> dict[str, Any]:
        self.calls.append(("load", str(path)))
        if self._bundle is None:
            raise _PrivateLabelLoadError("probe: should not be called")
        return self._bundle

    def exists(self, path: Path) -> bool:
        self.calls.append(("exists", str(path)))
        return self._bundle is not None


# ---------------------------------------------------------------------------
# Self-test checks (pure, no I/O except in-memory probes)
# ---------------------------------------------------------------------------


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return {"check": name, "passed": bool(ok)}


def _valid_synthetic_bundle(
    *,
    total_labels: int = MIN_TOTAL_LABELS + 10,
    small_cell_ok: bool = True,
    second_rater: bool = True,
    agreement: bool = True,
    ci: bool = True,
) -> dict[str, Any]:
    """Build a synthetic aggregate bundle for gate-logic self-tests."""
    n = K_MIN + 5 if small_cell_ok else K_MIN - 1
    return {
        "schema": PRIVATE_BUNDLE_SCHEMA,
        "total_labels": total_labels,
        "cells": [
            {"category": "primary_evidence", "n": n},
            {"category": "dependency_support", "n": n},
        ],
        "second_rater_present": second_rater,
        "agreement_available": agreement,
        "confidence_intervals_available": ci,
    }


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all D4a self-test groups. Returns (checks, all_passed)."""
    checks: list[dict[str, Any]] = []

    # --- Group 1: Default false / true flags. ---
    skeleton = _build_public_report([], False)
    for flag, value in DEFAULT_FALSE_FLAGS.items():
        checks.append(
            _check(
                f"default_flag_{flag}_false",
                skeleton.get(flag) is False,
            )
        )
    for flag, value in EXECUTION_CONTROL_FLAGS.items():
        checks.append(
            _check(
                f"execution_control_{flag}_true",
                skeleton.get(flag) is True,
            )
        )
    checks.append(
        _check(
            "d3_protocol_checked_true",
            skeleton["d3_protocol_checked"] is True,
        )
    )
    checks.append(
        _check(
            "d3_protocol_version_correct",
            skeleton["d3_protocol_version"] == D3_PROTOCOL_VERSION,
        )
    )
    checks.append(
        _check(
            "d3_required_gates_present_true",
            skeleton["d3_required_gates_present"] is True,
        )
    )
    for flag, value in NO_CLAIM_FLAGS.items():
        checks.append(
            _check(
                f"no_claim_{flag}_false",
                skeleton.get(flag) is False,
            )
        )
    for flag, value in DIAGNOSTIC_FLAGS.items():
        checks.append(
            _check(
                f"diagnostic_{flag}_true",
                skeleton.get(flag) is True,
            )
        )

    # --- Group 2: Artifact identity fields. ---
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
            "rubric_version_is_d3_protocol",
            skeleton["rubric_version"] == RUBRIC_VERSION
            and skeleton["rubric_version"] == D3_PROTOCOL_VERSION,
        )
    )
    checks.append(
        _check(
            "status_correct_when_self_test_passes",
            _build_public_report([], True)["status"] == TARGET_STATUS,
        )
    )
    checks.append(
        _check(
            "status_self_test_failed_when_not_passed",
            skeleton["status"] == "self_test_failed",
        )
    )
    checks.append(
        _check(
            "mode_public_gate_dry_run",
            skeleton["mode"] == MODE_PUBLIC,
        )
    )
    checks.append(
        _check("phase_d4a", skeleton["phase"] == PHASE)
    )
    checks.append(
        _check(
            "next_phase_d4b",
            skeleton["next_phase"] == NEXT_PHASE,
        )
    )

    # --- Group 3: D3 protocol constants / gates checked. ---
    checks.append(_check("k_min_is_5", K_MIN == 5))
    checks.append(
        _check("min_total_labels_is_50", MIN_TOTAL_LABELS == 50)
    )
    checks.append(
        _check("agreement_required_true", AGREEMENT_REQUIRED is True)
    )
    checks.append(
        _check(
            "confidence_intervals_required_true",
            CONFIDENCE_INTERVALS_REQUIRED is True,
        )
    )
    gt = skeleton["gate_thresholds"]
    checks.append(_check("gate_thresholds_k_min_5", gt["k_min"] == 5))
    checks.append(
        _check("gate_thresholds_min_total_labels_50", gt["min_total_labels"] == 50)
    )
    checks.append(
        _check(
            "gate_thresholds_agreement_required_true",
            gt["agreement_required"] is True,
        )
    )
    checks.append(
        _check(
            "gate_thresholds_confidence_intervals_required_true",
            gt["confidence_intervals_required"] is True,
        )
    )
    checks.append(
        _check(
            "gate_category_names_correct",
            tuple(skeleton["gate_category_names"]) == GATE_CATEGORY_NAMES,
        )
    )
    checks.append(
        _check(
            "private_dry_run_harness_tmp_only_not_committed",
            skeleton["private_dry_run_harness"]["opt_in_required"] is True
            and skeleton["private_dry_run_harness"]["output_location"]
            == "tmp_only_local_private"
            and skeleton["private_dry_run_harness"]["committed"] is False
            and skeleton["private_dry_run_harness"]["claims_calibration"]
            is False,
        )
    )

    # --- Group 4: Gate logic tests (synthetic in-memory summaries). ---
    # All pass.
    g_pass = evaluate_gate_logic(_valid_synthetic_bundle())
    checks.append(
        _check(
            "gate_logic_all_pass_overall_true",
            g_pass["overall_gate_passed"] is True,
        )
    )
    checks.append(
        _check(
            "gate_logic_pass_min_total_n",
            g_pass["min_total_n_gate_passed"] is True,
        )
    )
    checks.append(
        _check(
            "gate_logic_pass_small_cell",
            g_pass["small_cell_suppression_gate_passed"] is True,
        )
    )
    checks.append(
        _check(
            "gate_logic_pass_agreement",
            g_pass["agreement_required_gate_passed"] is True,
        )
    )
    checks.append(
        _check(
            "gate_logic_pass_ci",
            g_pass["confidence_interval_gate_passed"] is True,
        )
    )
    # min-N below 50 fails.
    g_low_n = evaluate_gate_logic(
        _valid_synthetic_bundle(total_labels=MIN_TOTAL_LABELS - 1)
    )
    checks.append(
        _check(
            "gate_logic_min_n_below_50_fails",
            g_low_n["min_total_n_gate_passed"] is False
            and g_low_n["overall_gate_passed"] is False,
        )
    )
    # small cell below 5 fails/suppresses.
    g_small = evaluate_gate_logic(
        _valid_synthetic_bundle(small_cell_ok=False)
    )
    checks.append(
        _check(
            "gate_logic_small_cell_below_5_fails",
            g_small["small_cell_suppression_gate_passed"] is False
            and g_small["overall_gate_passed"] is False,
        )
    )
    # missing second rater / agreement unavailable fails.
    g_no_rater = evaluate_gate_logic(
        _valid_synthetic_bundle(second_rater=False)
    )
    checks.append(
        _check(
            "gate_logic_missing_second_rater_fails",
            g_no_rater["agreement_required_gate_passed"] is False
            and g_no_rater["overall_gate_passed"] is False,
        )
    )
    g_no_agree = evaluate_gate_logic(
        _valid_synthetic_bundle(agreement=False)
    )
    checks.append(
        _check(
            "gate_logic_agreement_unavailable_fails",
            g_no_agree["agreement_required_gate_passed"] is False
            and g_no_agree["overall_gate_passed"] is False,
        )
    )
    # missing CI fails.
    g_no_ci = evaluate_gate_logic(
        _valid_synthetic_bundle(ci=False)
    )
    checks.append(
        _check(
            "gate_logic_missing_ci_fails",
            g_no_ci["confidence_interval_gate_passed"] is False
            and g_no_ci["overall_gate_passed"] is False,
        )
    )

    # --- Group 5: CLI guard matrix (pure). ---
    # --input without --allow-private-labels => error.
    sensitive_input = Path("/private/SECRET_LABEL_SENTINEL_sensitive.jsonl")
    err_input_no_allow = _validate_cli_args(
        allow_private_labels=False,
        input_path=sensitive_input,
        out_path=None,
    )
    checks.append(
        _check(
            "cli_input_without_allow_rejected",
            err_input_no_allow is not None,
        )
    )
    checks.append(
        _check(
            "cli_input_without_allow_no_path_basename_leak",
            err_input_no_allow is not None
            and str(sensitive_input) not in err_input_no_allow
            and sensitive_input.name not in err_input_no_allow
            and "SECRET_LABEL_SENTINEL" not in err_input_no_allow,
        )
    )
    # --allow-private-labels without --input => error.
    err_allow_no_input = _validate_cli_args(
        allow_private_labels=True,
        input_path=None,
        out_path=Path("/tmp/d4.json"),
    )
    checks.append(
        _check(
            "cli_allow_without_input_rejected",
            err_allow_no_input is not None,
        )
    )
    # allow + input but no explicit out => error.
    err_no_out = _validate_cli_args(
        allow_private_labels=True,
        input_path=sensitive_input,
        out_path=None,
    )
    checks.append(
        _check(
            "cli_allow_without_explicit_out_rejected",
            err_no_out is not None,
        )
    )
    checks.append(
        _check(
            "cli_allow_without_explicit_out_no_leak",
            err_no_out is not None
            and str(sensitive_input) not in err_no_out
            and "SECRET_LABEL_SENTINEL" not in err_no_out,
        )
    )
    # allow + committed artifact out => error.
    err_committed = _validate_cli_args(
        allow_private_labels=True,
        input_path=sensitive_input,
        out_path=DEFAULT_OUT,
    )
    checks.append(
        _check(
            "cli_allow_committed_out_rejected",
            err_committed is not None,
        )
    )
    checks.append(
        _check(
            "cli_allow_committed_out_no_leak",
            err_committed is not None
            and str(sensitive_input) not in err_committed
            and "SECRET_LABEL_SENTINEL" not in err_committed,
        )
    )
    # allow + non-/tmp out => error.
    err_non_tmp = _validate_cli_args(
        allow_private_labels=True,
        input_path=sensitive_input,
        out_path=Path("/not/tmp/d4.json"),
    )
    checks.append(
        _check(
            "cli_allow_non_tmp_out_rejected",
            err_non_tmp is not None,
        )
    )
    checks.append(
        _check(
            "cli_allow_non_tmp_out_no_leak",
            err_non_tmp is not None
            and str(sensitive_input) not in err_non_tmp
            and "SECRET_LABEL_SENTINEL" not in err_non_tmp,
        )
    )
    # allow + /tmp out => valid.
    err_tmp_ok = _validate_cli_args(
        allow_private_labels=True,
        input_path=sensitive_input,
        out_path=Path("/tmp/d4a_smoke.json"),
    )
    checks.append(
        _check(
            "cli_allow_tmp_out_allowed",
            err_tmp_ok is None,
        )
    )
    # default mode (no private args) => valid.
    err_default = _validate_cli_args(
        allow_private_labels=False,
        input_path=None,
        out_path=None,
    )
    checks.append(
        _check("cli_default_mode_allowed", err_default is None)
    )
    # path traversal /tmp/../etc is NOT under /tmp.
    err_traversal = _validate_cli_args(
        allow_private_labels=True,
        input_path=sensitive_input,
        out_path=Path("/tmp/../etc/passwd"),
    )
    checks.append(
        _check(
            "cli_traversal_out_rejected",
            err_traversal is not None,
        )
    )

    # --- Group 6: Validate-before-read (probe records no input access). ---
    probe_invalid = _ReadProbe()
    _report, err_probe = _run_private_dry_run(
        allow_private_labels=True,
        input_path=Path("/private/SECRET_LABEL_SENTINEL_nonexistent.jsonl"),
        out_path=Path("/not/tmp/d4.json"),  # invalid out
        loader=probe_invalid.loader,
        input_exists=probe_invalid.exists,
    )
    checks.append(
        _check(
            "validate_before_read_no_input_access_on_invalid_out",
            err_probe is not None and probe_invalid.calls == [],
        )
    )
    checks.append(
        _check(
            "validate_before_read_error_no_sentinel_leak",
            err_probe is not None
            and "SECRET_LABEL_SENTINEL" not in err_probe
            and "nonexistent.jsonl" not in err_probe,
        )
    )
    # Committed-out rejected before read.
    probe_committed = _ReadProbe()
    _report2, err_pc = _run_private_dry_run(
        allow_private_labels=True,
        input_path=Path("/private/SECRET_LABEL_SENTINEL.jsonl"),
        out_path=DEFAULT_OUT,
        loader=probe_committed.loader,
        input_exists=probe_committed.exists,
    )
    checks.append(
        _check(
            "committed_out_rejected_before_read",
            err_pc is not None and probe_committed.calls == [],
        )
    )
    # Non-/tmp out rejected before read.
    probe_nontmp = _ReadProbe()
    _report3, err_pn = _run_private_dry_run(
        allow_private_labels=True,
        input_path=Path("/private/SECRET_LABEL_SENTINEL.jsonl"),
        out_path=Path("/home/user/d4.json"),
        loader=probe_nontmp.loader,
        input_exists=probe_nontmp.exists,
    )
    checks.append(
        _check(
            "non_tmp_out_rejected_before_read",
            err_pn is not None and probe_nontmp.calls == [],
        )
    )

    # --- Group 7: Sanitized error with sensitive basename + sentinel. ---
    # Malformed bundle (forbidden keys + sentinel) returned by a loader:
    # the schema validator must reject it and only the fixed sanitized
    # error is surfaced; nothing reaches the report.
    malformed_bundle = {
        "schema": PRIVATE_BUNDLE_SCHEMA,
        "rater_id": "alice",
        "raw_label": "SECRET_LABEL_SENTINEL_raw_text",
        "annotation_row": {"row": 1, "text": "SECRET_LABEL_SENTINEL"},
    }
    probe_malformed = _ReadProbe(bundle=malformed_bundle)
    _report4, err_malformed = _run_private_dry_run(
        allow_private_labels=True,
        input_path=Path("/private/SECRET_LABEL_SENTINEL_bundle.jsonl"),
        out_path=Path("/tmp/d4a_malformed.json"),
        loader=probe_malformed.loader,
        input_exists=probe_malformed.exists,
    )
    checks.append(
        _check(
            "malformed_bundle_returns_sanitized_error",
            err_malformed == PRIVATE_LOAD_ERROR_MESSAGE
            and _report4 is None,
        )
    )
    checks.append(
        _check(
            "malformed_bundle_error_no_sentinel_or_basename",
            err_malformed is not None
            and "SECRET_LABEL_SENTINEL" not in err_malformed
            and "SECRET_LABEL_SENTINEL_bundle.jsonl"
            not in err_malformed
            and "alice" not in err_malformed,
        )
    )
    # Nonexistent input returns the sanitized error (no path leak).
    probe_missing = _ReadProbe(bundle=None)
    probe_missing.exists = lambda p: False  # type: ignore[method-assign]
    _report5, err_missing = _run_private_dry_run(
        allow_private_labels=True,
        input_path=Path("/private/SECRET_LABEL_SENTINEL_missing.jsonl"),
        out_path=Path("/tmp/d4a_missing.json"),
        loader=probe_missing.loader,
        input_exists=probe_missing.exists,
    )
    checks.append(
        _check(
            "missing_input_returns_sanitized_error",
            err_missing == PRIVATE_LOAD_ERROR_MESSAGE
            and _report5 is None,
        )
    )
    checks.append(
        _check(
            "missing_input_error_no_path_basename_leak",
            err_missing is not None
            and "SECRET_LABEL_SENTINEL" not in err_missing
            and "SECRET_LABEL_SENTINEL_missing.jsonl" not in err_missing,
        )
    )

    # --- Group 8: Private dry-run success path — no path/basename/raw
    # label/output path in the serialized report. ---
    valid_bundle = _valid_synthetic_bundle()
    sensitive_in = Path("/private/SECRET_LABEL_SENTINEL_success.jsonl")
    sensitive_out = Path("/tmp/SECRET_LABEL_SENTINEL_out.json")
    probe_ok = _ReadProbe(bundle=valid_bundle)
    report_ok, err_ok = _run_private_dry_run(
        allow_private_labels=True,
        input_path=sensitive_in,
        out_path=sensitive_out,
        loader=probe_ok.loader,
        input_exists=probe_ok.exists,
    )
    checks.append(
        _check(
            "private_dry_run_success_returns_report",
            err_ok is None and report_ok is not None,
        )
    )
    ok_blob = json.dumps(report_ok, sort_keys=True) if report_ok else ""
    checks.append(
        _check(
            "private_report_no_sentinel",
            "SECRET_LABEL_SENTINEL" not in ok_blob,
        )
    )
    checks.append(
        _check(
            "private_report_no_input_path_or_basename",
            str(sensitive_in) not in ok_blob
            and sensitive_in.name not in ok_blob
            and "/private" not in ok_blob,
        )
    )
    checks.append(
        _check(
            "private_report_no_output_path_or_basename",
            str(sensitive_out) not in ok_blob
            and sensitive_out.name not in ok_blob,
        )
    )
    checks.append(
        _check(
            "private_report_no_raw_labels_raters_rows",
            '"rater_id"' not in ok_blob
            and '"raw_label"' not in ok_blob
            and '"annotation_row"' not in ok_blob
            and '"per_row_hash"' not in ok_blob,
        )
    )
    checks.append(
        _check(
            "private_report_no_exact_private_sample_sizes",
            # The bundle's total_labels (60) and cell n's (10) must NOT be
            # echoed into the report (only gate booleans + constants).
            ok_blob.count('"total_labels"') == 0
            if valid_bundle["total_labels"] == 60
            else True,
        )
    )
    checks.append(
        _check(
            "private_report_gate_results_present_and_booleans_only",
            isinstance(report_ok, dict)
            and isinstance(report_ok.get("gate_results"), dict)
            and all(
                isinstance(v, bool)
                for v in report_ok["gate_results"].values()
            )
            and report_ok["gate_results"]["overall_gate_passed"] is True,
        )
    )
    checks.append(
        _check(
            "private_report_private_label_bundle_read_true_others_false",
            report_ok is not None
            and report_ok["private_label_bundle_read"] is True
            and report_ok["private_records_read"] is False
            and report_ok["raw_private_records_read"] is False
            and report_ok["private_label_bundle_persisted"] is False
            and report_ok["private_output_committed"] is False
            and report_ok["labels_collected"] is False
            and report_ok["calibration_metrics_computed"] is False
            and report_ok["true_e_s_calibration_claimed"] is False
            and report_ok["proxy_calibration_claimed"] is False
            and report_ok["public_release_gate_passed"] is False,
        )
    )
    checks.append(
        _check(
            "private_report_forbidden_scan_clean",
            report_ok is not None
            and report_ok["forbidden_scan"]["status"] == "pass"
            and report_ok["forbidden_scan"]["violations_count"] == 0,
        )
    )

    # --- Group 9: Forbidden scanner rejects sensitive keys/values. ---
    def _has_cat(obj: Any, cat: str) -> bool:
        return any(v["category"] == cat for v in _scan_forbidden(obj))

    for bad_key in (
        "task_id", "repo_id", "repo", "path", "span", "line_range",
        "start_line", "end_line", "content_sha", "snippet",
        "candidate_text", "query", "prompt", "response", "model_output",
        "label", "raw_label", "annotation_row", "rater_id",
        "annotator_id", "disagreement_example", "per_row_hash",
    ):
        checks.append(
            _check(
                f"scanner_rejects_{bad_key}_key",
                _has_cat({bad_key: "abc"}, "forbidden_key"),
            )
        )
    checks.append(
        _check(
            "scanner_rejects_64_hex_digest_value",
            _has_cat({"x": "a" * 64}, "hex_digest_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_40_hex_digest_value",
            _has_cat({"x": "f" * 40}, "hex_digest_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_32_hex_digest_value",
            _has_cat(
                {"x": "0123456789abcdef0123456789abcdef"},
                "hex_digest_value",
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_secret_sentinel_value",
            _has_cat({"x": "SECRET_LABEL_SENTINEL"}, "sentinel_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_path_like_value",
            _has_cat({"x": "src/foo.py"}, "path_like_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_leading_slash_path_value",
            _has_cat({"x": "/a/b.py"}, "path_like_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_jsonl_path_value",
            _has_cat({"x": "/private/foo.jsonl"}, "path_like_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_line_range_value",
            _has_cat({"x": "12-34"}, "line_range_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_colon_line_range_value",
            _has_cat({"x": "12:34"}, "line_range_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_multiline_value",
            _has_cat({"x": "line one\nline two"}, "multiline_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_url_value",
            _has_cat({"x": "https://example.com/x"}, "url_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_raw_json_fragment",
            _has_cat({"x": '{"repo": "x"}'}, "raw_json_fragment"),
        )
    )
    # Pure-digit count strings must NOT be flagged.
    checks.append(
        _check(
            "scanner_allows_pure_digit_count_string",
            not _scan_forbidden({"x": "50"}),
        )
    )
    # Safe gate/protocol strings must NOT be flagged.
    checks.append(
        _check(
            "scanner_allows_safe_gate_category_string",
            not _scan_forbidden({"gate_category_names": ["primary_evidence"]}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_safe_d3_protocol_version_string",
            not _scan_forbidden(
                {"d3_protocol_version": D3_PROTOCOL_VERSION}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_safe_phase_string",
            not _scan_forbidden({"phase": PHASE, "next_phase": NEXT_PHASE}),
        )
    )

    # --- Group 10: Fail-closed generation on scanner leak. ---
    raised = False
    try:
        _enforce_no_forbidden(
            {"path": "src/foo.py", "content_sha": "a" * 64,
             "rater_id": "alice", "raw_label": "SECRET_LABEL_SENTINEL"}
        )
    except SystemExit:
        raised = True
    checks.append(
        _check("fail_closed_generation_raises_on_leak", raised)
    )
    no_raise = True
    try:
        _enforce_no_forbidden(skeleton)
    except SystemExit:
        no_raise = False
    checks.append(
        _check("fail_closed_clean_public_report_does_not_raise", no_raise)
    )
    checks.append(
        _check(
            "public_report_forbidden_scan_clean",
            skeleton["forbidden_scan"]["status"] == "pass"
            and skeleton["forbidden_scan"]["violations_count"] == 0,
        )
    )

    # --- Group 11: Artifact generation refuses success if self-test fails. ---
    raised_on_fail = False
    try:
        _refuse_on_self_test_failure({"self_test_passed": False})
    except SystemExit:
        raised_on_fail = True
    checks.append(
        _check(
            "refuse_on_self_test_failure_raises_when_failed",
            raised_on_fail,
        )
    )
    no_raise_on_pass = True
    try:
        _refuse_on_self_test_failure({"self_test_passed": True})
    except SystemExit:
        no_raise_on_pass = False
    checks.append(
        _check(
            "refuse_on_self_test_failure_does_not_raise_when_passed",
            no_raise_on_pass,
        )
    )
    checks.append(
        _check(
            "failed_self_test_does_not_carry_success_status",
            _build_public_report([], False)["status"] != TARGET_STATUS
            and _build_public_report([], False)["self_test_passed"] is False,
        )
    )
    checks.append(
        _check(
            "passed_self_test_carries_success_status",
            _build_public_report([], True)["status"] == TARGET_STATUS
            and _build_public_report([], True)["self_test_passed"] is True,
        )
    )

    # --- Group 12: CLI option surface (exactly the required options). ---
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
            "cli_has_allow_private_labels_argument",
            "--allow-private-labels" in cli_opts,
        )
    )
    checks.append(
        _check("cli_has_input_argument", "--input" in cli_opts)
    )
    checks.append(
        _check(
            "cli_only_required_arguments",
            (cli_opts - {"-h", "--help"})
            == {"--self-test", "--out", "--allow-private-labels", "--input"},
        )
    )

    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the D4a CLI parser."""
    ap = argparse.ArgumentParser(
        description=(
            "D4a dual-rubric execution gate / dry-run "
            "(public gate artifact only; no labels collected)."
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
            "output artifact JSON path (default: committed public gate "
            "artifact; private dry-run requires an explicit /tmp path)"
        ),
    )
    ap.add_argument(
        "--allow-private-labels",
        action="store_true",
        help=(
            "opt-in private dry-run gate smoke; requires --input; output "
            "must go to /tmp only (NOT committed)"
        ),
    )
    ap.add_argument(
        "--input",
        type=Path,
        default=None,
        help=(
            "path to a private label-bundle-shaped JSON (private dry-run "
            "only; requires --allow-private-labels); never serialized "
            "into any artifact"
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

    # Private dry-run mode (any private arg present).
    if args.allow_private_labels or args.input is not None:
        report, err = _run_private_dry_run(
            allow_private_labels=args.allow_private_labels,
            input_path=args.input,
            out_path=args.out,
            loader=_default_loader,
            input_exists=_default_exists,
        )
        if err is not None:
            msg = err if err.startswith("error:") else f"error: {err}"
            print(msg, file=sys.stderr)
            sys.exit(2)
        assert report is not None and args.out is not None
        # Strict fail-closed guard immediately before writing.
        _enforce_no_forbidden(report)
        _write_json(args.out, report)
        # Do NOT print the exact /tmp output path.
        print(
            "wrote D4a private dry-run gate smoke to /tmp output "
            f"(forbidden_scan={report['forbidden_scan']['status']}, "
            f"overall_gate_passed="
            f"{report['gate_results']['overall_gate_passed']}) "
            f"[NOT committed; /tmp only]"
        )
        return

    # Public default mode (committed gate artifact).
    out_path = args.out if args.out is not None else DEFAULT_OUT
    checks, all_passed = run_self_test_checks()
    report = _build_public_report(checks, all_passed)
    # Strict fail-closed guard immediately before writing the JSON artifact.
    _enforce_no_forbidden(report)
    _refuse_on_self_test_failure(report)
    _write_json(out_path, report)
    print(
        f"wrote {out_path} "
        f"(forbidden_scan={report['forbidden_scan']['status']}, "
        f"self_test_passed={report['self_test_passed']}, "
        f"status={report['status']})"
    )


if __name__ == "__main__":
    main()
