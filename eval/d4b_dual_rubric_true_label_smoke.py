#!/usr/bin/env python3
"""D4b Dual-Rubric True-Label Smoke Harness / Blocked Public Artifact.

This module implements the **D4b dual-rubric true-label smoke harness**.
D4b freezes the local/private true E-score / S-score label-bundle input
contract and hardens the execution controls. The **default committed
artifact is a public harness / no-labels artifact**, NOT a real true-label
smoke result. D4b must NOT claim a true-label smoke was executed unless a
real human/manual true E/S label bundle is explicitly supplied and run
locally under ``/tmp``.

D4b **does not** fabricate labels, **does not** accept proxy/synthetic/LLM
labels as true labels, **does not** read private label bundles by default,
**does not** compute true calibration metrics, **does not** measure
inter-rater agreement, **does not** claim true/proxy calibration, and
**does not** change runtime behavior, retriever, pack, model, backend,
default policy, or EvidenceCore semantics.

Claim boundary (binding):

* This is **eval/diagnostic only**. It is NOT a runtime change, NOT a
  retriever/pack/model/backend/default-policy change, and NOT an
  EvidenceCore semantic change.
* Claim level: ``true_label_bundle_execution_harness_only``.
* Rubric version: ``d3_true_dual_rubric_label_protocol_v1`` (D3 protocol
  checked; D4b does not redefine the rubric).
* Status: ``blocked_no_true_label_bundle_available``; mode
  ``public_harness_no_labels``; phase ``D4b``.
* The default committed artifact collects NO labels, reads NO true label
  bundles, validates NO bundle as true labels, computes NO calibration
  metrics, measures NO inter-rater agreement, claims NO true/proxy
  calibration, and passes NO public-release / real-bundle gate.

Two strictly separated modes:

* **D4b default (committed)**: public harness / no-labels artifact. No
  private input. All label/private/calibration/claim flags false; the
  five allowed harness/control flags true; diagnostic flags true.

* **D4b private smoke (opt-in, NOT committed)**: explicit
  ``--allow-private-labels --input <path> --out /tmp/...``. Validates a
  local/private true-label-bundle-shaped JSON only to validate
  shape/gates. Writes ``/tmp`` output only. Never serializes input/output
  paths, basenames, raw label rows, rater IDs, annotation rows, row
  hashes, or exact real private counts (bands only). Does NOT compute or
  claim true calibration metrics. ``--synthetic-harness-test`` marks an
  in-memory/harness run: it sets ``synthetic_harness_test=true`` and
  ``local_private_true_label_smoke_executed=false`` even if the bundle is
  human-manual-shaped. A real local private run (no synthetic flag,
  ``label_source=human_manual_true_e_s``, valid schema) may set
  ``local_private_true_label_smoke_executed=true`` locally only (never
  committed).

Run::

    python3 -m py_compile eval/d4b_dual_rubric_true_label_smoke.py
    python3 eval/d4b_dual_rubric_true_label_smoke.py --self-test
    python3 eval/d4b_dual_rubric_true_label_smoke.py \
        --out artifacts/d4b_dual_rubric_true_label_smoke/\\
d4b_dual_rubric_true_label_smoke_report.json
    # D4b private smoke (NOT committed; /tmp only):
    python3 eval/d4b_dual_rubric_true_label_smoke.py \
        --allow-private-labels --input /tmp/private_bundle.json \
        --out /tmp/d4b_smoke.json
    # D4b synthetic harness self-test (NOT committed; /tmp only):
    python3 eval/d4b_dual_rubric_true_label_smoke.py \
        --allow-private-labels --synthetic-harness-test \
        --input /tmp/harness_bundle.json --out /tmp/d4b_harness.json
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

SCHEMA_VERSION = "d4b_dual_rubric_true_label_smoke.v1"
GENERATED_BY = "eval/d4b_dual_rubric_true_label_smoke.py"
CLAIM_LEVEL = "true_label_bundle_execution_harness_only"
RUBRIC_VERSION = "d3_true_dual_rubric_label_protocol_v1"
TARGET_STATUS = "blocked_no_true_label_bundle_available"
MODE_PUBLIC = "public_harness_no_labels"
MODE_PRIVATE = "private_true_label_smoke_harness"
PHASE = "D4b"
STATUS_PRIVATE_OK = "private_true_label_smoke_harness_completed"

DEFAULT_OUT = Path(
    "artifacts/d4b_dual_rubric_true_label_smoke/"
    "d4b_dual_rubric_true_label_smoke_report.json"
)

# Fixed sanitized error for any private true-label bundle load/parse/
# schema/privacy failure. Never includes the input path, basename, raw
# JSON, or label text.
PRIVATE_LOAD_ERROR_MESSAGE = (
    "error: failed to load private true labels "
    "(schema/privacy/parse error; details suppressed)"
)

# ---------------------------------------------------------------------------
# D3 protocol constants (D4b checks these; it does not redefine the
# rubric). Mirrors D3 future_execution_gates / public_release_thresholds.
# ---------------------------------------------------------------------------

D3_PROTOCOL_VERSION = "d3_true_dual_rubric_label_protocol_v1"
K_MIN = 5
MIN_TOTAL_LABELS = 50
MIN_RATER_COUNT = 2
AGREEMENT_REQUIRED = True
CONFIDENCE_INTERVALS_REQUIRED = True

# Fixed gate category names (approved enum for the bucket dimension of a
# true E/S label). These are category labels only; no concrete
# repo/path/snippet content.
GATE_CATEGORY_NAMES: tuple[str, ...] = (
    "primary_evidence",
    "dependency_support",
    "weak_candidates",
    "abstained",
)

# Fixed E-score / S-score levels (D3 protocol enum).
E_SCORE_LEVELS: tuple[str, ...] = ("E0", "E1", "E2")
S_SCORE_LEVELS: tuple[str, ...] = ("S0", "S1", "S2")

# ---------------------------------------------------------------------------
# Private true-label bundle contract (local-only, sanitized)
# ---------------------------------------------------------------------------

# A real local private true-label bundle is a JSON object whose labels are
# human/manual true E/S annotations. The loader rejects IDs/paths/
# snippets/rater IDs/raw row metadata/unknown keys rather than supporting
# and stripping them. label_source must be exactly human_manual_true_e_s
# for a real local run; proxy/synthetic/llm/etc are rejected as true
# labels.
PRIVATE_BUNDLE_SCHEMA = "d4b_true_label_bundle_v1"
HUMAN_MANUAL_LABEL_SOURCE = "human_manual_true_e_s"
ALLOWED_BUNDLE_KEYS: frozenset[str] = frozenset(
    {
        "schema",
        "label_source",
        "rater_count",
        "agreement_available",
        "confidence_intervals_available",
        "labels",
    }
)
ALLOWED_LABEL_KEYS: frozenset[str] = frozenset(
    {
        "e_score",
        "s_score",
        "bucket",
        "citation_valid",
        "rater_pair_present",
        "adjudicated",
    }
)

# ---------------------------------------------------------------------------
# Default artifact false flags (all MUST be false in the committed public
# artifact). D4b collects no labels, reads no true label bundles, computes
# no calibration metrics, and passes no release gate.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "labels_collected": False,
    "true_label_bundle_read": False,
    "true_label_bundle_validated": False,
    "true_label_bundle_persisted": False,
    "local_private_true_label_smoke_executed": False,
    "calibration_metrics_computed": False,
    "inter_rater_agreement_measured": False,
    "confidence_intervals_computed": False,
    "true_e_s_calibration_claimed": False,
    "public_release_gate_passed": False,
    "real_label_bundle_gate_passed": False,
    "raw_label_rows_emitted": False,
    "private_input_path_emitted": False,
    "private_output_path_emitted": False,
    "private_output_committed": False,
    "exact_private_counts_emitted": False,
    "synthetic_labels_accepted_as_true": False,
    "proxy_labels_accepted_as_true": False,
    "llm_labels_accepted_as_true": False,
    "model_assisted_labels_allowed": False,
}

# Allowed positive harness/control flags (true only for the validated
# harness/controls; each is proven by a self-test). Exactly these five;
# no gate-validated / calibration claim flags are true in the default
# committed artifact.
HARNESS_CONTROL_FLAGS: dict[str, bool] = {
    "private_execution_harness_available": True,
    "private_cli_guard_validated": True,
    "tmp_output_resolved_guard_validated": True,
    "sanitized_error_guard_validated": True,
    "bundle_schema_contract_defined": True,
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
# Forbidden-output scanner (D4b-specific, fail-closed)
# ---------------------------------------------------------------------------

# Sensitive KEY names that must NEVER appear as dict keys anywhere in a
# public or private output JSON. Because the private bundle INPUT contract
# uses a ``labels`` key, no OUTPUT may emit a ``labels`` key (the scanner
# rejects it). Superset of D3's set, extended with rater/annotator/
# disagreement keys for the label-bundle domain.
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
        "d3_protocol_version",
        "bundle_schema",
        "required_label_source",
        "label_count_band",
    }
)

# Value patterns that indicate leaked row-level / candidate / annotation
# data. D4b rejects ALL URLs (no URL allowlist) per the fail-closed rule.
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
    task_id/repo_id/repo/label/labels/raw_label/annotation_row/rater_id/
    annotator_id/disagreement_example/per_row_hash/model_output/etc.)
    anywhere, and rejects value patterns: ANY URL, 32/40/64-char hex
    digests, secret-like strings, path-like strings (``src/foo.py``,
    ``/private/foo.jsonl``), multiline strings, raw JSON fragments,
    raw line-range strings (``12-34``), and the self-test sentinel.

    Allows safe protocol / gate / level / category / band strings only if
    they are not row-like (e.g. ``primary_evidence``, ``k_min``, ``D4b``,
    ``min_n_met``).
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


def _has_dict_key_anywhere(obj: Any, key: str) -> bool:
    """True iff any dict within ``obj`` has ``key`` as a dict key.

    Used by self-tests to prove no forbidden key (e.g. ``labels``) is
    emitted as a dict key anywhere in an output, complementing the
    forbidden scanner (which also rejects such keys).
    """
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


# ---------------------------------------------------------------------------
# Gate logic (over a validated human-manual bundle; no calibration
# metrics computed; bands only, never exact private counts)
# ---------------------------------------------------------------------------


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _is_nonneg_int(value: Any) -> bool:
    """True iff ``value`` is a non-bool non-negative int."""
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0
    )


def _bucket_counts(labels: list[dict[str, Any]]) -> dict[str, int]:
    """Count labels per fixed gate category (never emits rows)."""
    counts: dict[str, int] = {name: 0 for name in GATE_CATEGORY_NAMES}
    for entry in labels:
        bucket = entry.get("bucket")
        if bucket in counts:
            counts[bucket] += 1
    return counts


def _bucket_count_band(count: int, k_min: int) -> str:
    """Map a bucket count to a safe band (never an exact count).

    - ``k_met``: count >= k_min (threshold met).
    - ``below_k``: 0 < count < k_min (small cell; exact count suppressed).
    - ``suppressed``: count == 0 (empty cell; suppressed).
    """
    if count >= k_min:
        return "k_met"
    if count > 0:
        return "below_k"
    return "suppressed"


def evaluate_gate_logic(bundle: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the D4b gate logic over a validated true-label bundle.

    This ONLY checks gate thresholds and emits bands. It does NOT compute
    calibration metrics, inter-rater agreement, or confidence intervals.
    It returns per-gate pass/fail booleans, count bands, and an overall
    gate verdict. No exact private counts are returned; no label rows are
    returned.

    Gates (constants from D3):
      * min_total_n: ``len(labels) >= 50``.
      * bucket_cell: every fixed bucket cell ``n >= k_min`` (5); any cell
        below 5 fails/suppresses (small-cell suppression).
      * second_rater: ``rater_count >= 2``.
      * agreement: ``agreement_available`` is true.
      * confidence_interval: ``confidence_intervals_available`` is true.
    """
    labels = bundle.get("labels", [])
    total = len(labels) if isinstance(labels, list) else 0
    rater_count = bundle.get("rater_count", 0)
    agreement = bool(bundle.get("agreement_available", False))
    ci = bool(bundle.get("confidence_intervals_available", False))

    counts = _bucket_counts(labels if isinstance(labels, list) else [])
    bucket_bands = {
        name: _bucket_count_band(counts[name], K_MIN)
        for name in GATE_CATEGORY_NAMES
    }

    min_total_n_passed = total >= MIN_TOTAL_LABELS
    bucket_cell_passed = all(
        band == "k_met" for band in bucket_bands.values()
    )
    second_rater_passed = (
        _is_nonneg_int(rater_count) and rater_count >= MIN_RATER_COUNT
    )
    agreement_passed = agreement
    ci_passed = ci

    overall = (
        min_total_n_passed
        and bucket_cell_passed
        and second_rater_passed
        and agreement_passed
        and ci_passed
    )
    return {
        "min_total_n_gate_passed": min_total_n_passed,
        "bucket_cell_gate_passed": bucket_cell_passed,
        "second_rater_gate_passed": second_rater_passed,
        "agreement_gate_passed": agreement_passed,
        "confidence_interval_gate_passed": ci_passed,
        "overall_gate_passed": overall,
        "label_count_band": "min_n_met" if min_total_n_passed else "below_min_n",
        "bucket_count_bands": bucket_bands,
    }


# ---------------------------------------------------------------------------
# Private true-label bundle schema validation (fail-closed, sanitized)
# ---------------------------------------------------------------------------


class _PrivateLabelLoadError(Exception):
    """Raised when a private true-label bundle fails schema/privacy/parse
    checks.

    The CLI never surfaces this exception's message; it always emits the
    fixed sanitized ``PRIVATE_LOAD_ERROR_MESSAGE`` instead.
    """


def _validate_bundle_schema(bundle: Any) -> None:
    """Validate a private true-label bundle (fail-closed, sanitized).

    Raises ``_PrivateLabelLoadError`` if the bundle is malformed, has an
    unknown schema, contains keys outside the allowlist (e.g. raw labels,
    rater IDs, annotation rows, paths), has a non-human-manual
    label_source, or has wrong-typed values. The loader rejects IDs/
    paths/snippets/rater IDs/raw row metadata/unknown keys rather than
    supporting and stripping them.

    A real local true-label bundle must have label_source exactly
    ``human_manual_true_e_s``; proxy/synthetic/llm/etc are rejected as
    true labels.
    """
    if not isinstance(bundle, dict):
        raise _PrivateLabelLoadError()
    # Fail-closed: reject any key outside the allowlist (catches raw_label,
    # rater_id, annotation_row, path, task_id, snippet, etc.).
    for key in bundle.keys():
        if key not in ALLOWED_BUNDLE_KEYS:
            raise _PrivateLabelLoadError()
    if bundle.get("schema") != PRIVATE_BUNDLE_SCHEMA:
        raise _PrivateLabelLoadError()
    # label_source must be exactly human_manual_true_e_s for a real run;
    # proxy/synthetic/llm/etc are rejected as true labels.
    if bundle.get("label_source") != HUMAN_MANUAL_LABEL_SOURCE:
        raise _PrivateLabelLoadError()
    rater_count = bundle.get("rater_count")
    if (
        not isinstance(rater_count, int)
        or isinstance(rater_count, bool)
        or rater_count < MIN_RATER_COUNT
    ):
        raise _PrivateLabelLoadError()
    for flag in ("agreement_available", "confidence_intervals_available"):
        if not isinstance(bundle.get(flag), bool):
            raise _PrivateLabelLoadError()
    labels = bundle.get("labels")
    if not isinstance(labels, list) or len(labels) == 0:
        raise _PrivateLabelLoadError()
    for entry in labels:
        if not isinstance(entry, dict):
            raise _PrivateLabelLoadError()
        # Each label object must have ONLY the six allowed keys; any
        # unknown key (IDs/paths/snippets/rater IDs/raw row metadata) is
        # rejected.
        if set(entry.keys()) != ALLOWED_LABEL_KEYS:
            raise _PrivateLabelLoadError()
        if entry.get("e_score") not in E_SCORE_LEVELS:
            raise _PrivateLabelLoadError()
        if entry.get("s_score") not in S_SCORE_LEVELS:
            raise _PrivateLabelLoadError()
        if entry.get("bucket") not in GATE_CATEGORY_NAMES:
            raise _PrivateLabelLoadError()
        for flag in (
            "citation_valid",
            "rater_pair_present",
            "adjudicated",
        ):
            if not isinstance(entry.get(flag), bool):
                raise _PrivateLabelLoadError()


def _decide_execution_claim(
    *,
    synthetic_harness_test: bool,
    label_source: Any,
    schema_valid: bool,
) -> bool:
    """Decide whether ``local_private_true_label_smoke_executed`` may be
    true.

    True only for a real local private run: no synthetic harness flag, a
    human-manual label_source, and a valid schema. Synthetic / in-memory
    harness runs are always false even if the bundle is human-manual-
    shaped. This function expresses the logic only; it does not itself
    claim execution in any committed artifact.
    """
    if synthetic_harness_test:
        return False
    if label_source != HUMAN_MANUAL_LABEL_SOURCE:
        return False
    if not schema_valid:
        return False
    return True


# ---------------------------------------------------------------------------
# Default file-based loader / existence probe (injectable for self-test)
# ---------------------------------------------------------------------------


def _default_loader(input_path: Path) -> dict[str, Any]:
    """Read, parse, and validate a private true-label bundle file.

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
# Resolved /tmp output guard (strong; filesystem on OUTPUT only)
# ---------------------------------------------------------------------------


def _resolve(path: Path) -> str:
    """Resolve a path following symlinks (filesystem access)."""
    return os.path.realpath(str(path))


def _is_under_resolved(resolved_path: str, resolved_root: str) -> bool:
    """True iff ``resolved_path`` is ``resolved_root`` or under it."""
    if resolved_path == resolved_root:
        return True
    return resolved_path.startswith(resolved_root + os.sep)


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


def _validate_resolved_tmp_guard(out_path: Path) -> str | None:
    """Strong resolved /tmp output guard.

    Validates (with filesystem access on the OUTPUT path ONLY, before any
    private input is opened/stat'd):
      * resolve ``/tmp``;
      * resolve the output parent; reject if it escapes ``/tmp`` (parent
        symlink escape, e.g. ``/tmp/link_to_repo/out.json``);
      * reject if the existing output file is a symlink;
      * resolve the output target; reject if it escapes ``/tmp``.

    Returns an error message string if invalid, or ``None`` if valid. The
    message never echoes the output path/basename.
    """
    tmp_resolved = _resolve(Path("/tmp"))
    # Parent symlink escape: resolve the output parent directory.
    parent = out_path.parent
    parent_resolved = _resolve(parent)
    if not _is_under_resolved(parent_resolved, tmp_resolved):
        return (
            "private output resolves outside /tmp; refusing to write "
            "private-mode output"
        )
    # Existing output file symlink: a symlink at the output path itself
    # is rejected (it could point outside /tmp).
    try:
        is_link = out_path.is_symlink()
    except OSError:
        is_link = False
    if is_link:
        return (
            "private output path is a symlink; refusing to write "
            "private-mode output"
        )
    # Resolved target escape: resolve the full output path; reject if it
    # is not under resolved /tmp.
    target_resolved = _resolve(out_path)
    if not _is_under_resolved(target_resolved, tmp_resolved):
        return (
            "private output resolves outside /tmp; refusing to write "
            "private-mode output"
        )
    return None


# ---------------------------------------------------------------------------
# CLI argument validation (pure: no I/O before the input is opened)
# ---------------------------------------------------------------------------


def _validate_cli_args(
    *,
    allow_private_labels: bool,
    input_path: Path | None,
    out_path: Path | None,
    synthetic_harness_test: bool,
) -> str | None:
    """Validate CLI argument combinations for public vs private smoke.

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
    * ``--synthetic-harness-test`` without ``--allow-private-labels`` ->
      error.
    * ``--allow-private-labels --input <path> --out /tmp/...`` -> valid.
    """
    if input_path is not None and not allow_private_labels:
        return (
            "--input requires --allow-private-labels; refusing to read "
            "private true labels without explicit opt-in"
        )
    if allow_private_labels and input_path is None:
        return (
            "--allow-private-labels requires --input; no private input "
            "path provided"
        )
    if synthetic_harness_test and not allow_private_labels:
        return (
            "--synthetic-harness-test requires --allow-private-labels; "
            "refusing to run a harness test without explicit opt-in"
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
# Private smoke runner (validate-before-read; resolved /tmp guard;
# sanitized errors)
# ---------------------------------------------------------------------------


def _run_private_smoke(
    *,
    allow_private_labels: bool,
    input_path: Path | None,
    out_path: Path | None,
    synthetic_harness_test: bool,
    loader: Any,
    input_exists: Any,
    tmp_guard: Any = _validate_resolved_tmp_guard,
) -> tuple[dict[str, Any] | None, str | None]:
    """Run the private true-label smoke harness.

    Returns ``(report, error)``: exactly one is non-``None``.

    The CLI/output guards are validated BEFORE the input is opened or
    stat'd (validate-before-read): lexical CLI args first (no filesystem),
    then the resolved ``/tmp`` guard (filesystem on the OUTPUT path only).
    Any load/parse/schema failure returns the fixed sanitized error; the
    input path, basename, raw JSON, and label text are never surfaced.
    """
    err = _validate_cli_args(
        allow_private_labels=allow_private_labels,
        input_path=input_path,
        out_path=out_path,
        synthetic_harness_test=synthetic_harness_test,
    )
    if err is not None:
        # Lexical validation failed: NO input or output filesystem access
        # performed.
        return None, err
    # Lexical validation passed: validate the resolved /tmp output guard
    # (filesystem on the OUTPUT path only) before touching the input.
    assert input_path is not None and out_path is not None
    err = tmp_guard(out_path)
    if err is not None:
        # Output guard failed: NO input access performed.
        return None, err
    # Output guard passed: the input may now be touched.
    if not input_exists(input_path):
        return None, PRIVATE_LOAD_ERROR_MESSAGE
    try:
        bundle = loader(input_path)
    except Exception:
        return None, PRIVATE_LOAD_ERROR_MESSAGE
    schema_valid = True
    try:
        _validate_bundle_schema(bundle)
    except _PrivateLabelLoadError:
        schema_valid = False
        return None, PRIVATE_LOAD_ERROR_MESSAGE
    gate = evaluate_gate_logic(bundle)
    local_executed = _decide_execution_claim(
        synthetic_harness_test=synthetic_harness_test,
        label_source=bundle.get("label_source"),
        schema_valid=schema_valid,
    )
    report = _build_private_smoke_report(
        gate=gate,
        synthetic_harness_test=synthetic_harness_test,
        local_private_true_label_smoke_executed=local_executed,
    )
    return report, None


# ---------------------------------------------------------------------------
# Report builders
# ---------------------------------------------------------------------------


def _build_gate_thresholds() -> dict[str, Any]:
    return {
        "k_min": K_MIN,
        "min_total_labels": MIN_TOTAL_LABELS,
        "min_rater_count": MIN_RATER_COUNT,
        "agreement_required": AGREEMENT_REQUIRED,
        "confidence_intervals_required": CONFIDENCE_INTERVALS_REQUIRED,
    }


def _build_bundle_schema_contract() -> dict[str, Any]:
    return {
        "bundle_schema": PRIVATE_BUNDLE_SCHEMA,
        "required_label_source": HUMAN_MANUAL_LABEL_SOURCE,
        "rejected_label_sources": (
            "proxy",
            "synthetic",
            "llm",
            "model_assisted",
        ),
        "bundle_allowed_keys": sorted(ALLOWED_BUNDLE_KEYS),
        "label_object_allowed_keys": sorted(ALLOWED_LABEL_KEYS),
        "e_score_levels": list(E_SCORE_LEVELS),
        "s_score_levels": list(S_SCORE_LEVELS),
        "bucket_names": list(GATE_CATEGORY_NAMES),
        "rejects_unknown_keys": True,
        "rejects_ids_paths_snippets_raters": True,
    }


def _build_private_execution_harness_info() -> dict[str, Any]:
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
    """Assemble the public harness / no-labels report (fail-closed scan).

    The default committed artifact. No labels collected, no true label
    bundles read, no calibration metrics computed, no claims.
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
        "gate_thresholds": _build_gate_thresholds(),
        "gate_category_names": list(GATE_CATEGORY_NAMES),
        "bundle_schema_contract": _build_bundle_schema_contract(),
        "private_execution_harness": _build_private_execution_harness_info(),
        "self_test_summary": _self_test_category_summary(checks),
        "self_test_checks": checks,
        "self_test_passed": all_passed,
        "input_attestation_required": False,
        # D3 protocol check (flat).
        **D3_PROTOCOL_FLAGS,
        # Default false flags (flat).
        **DEFAULT_FALSE_FLAGS,
        # Harness/control flags (flat; true only for validated controls).
        **HARNESS_CONTROL_FLAGS,
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


def _build_private_smoke_report(
    *,
    gate: dict[str, Any],
    synthetic_harness_test: bool,
    local_private_true_label_smoke_executed: bool,
) -> dict[str, Any]:
    """Assemble the private smoke harness report (NOT committed; /tmp only).

    Contains ONLY: identity fields, fixed gate thresholds/category names,
    bundle schema contract, gate pass/fail booleans, count bands, and
    sanitized flags. Does NOT echo any label rows, IDs, paths, basenames,
    raw E/S rows, rater IDs, annotation rows, row hashes, prompts/
    responses/model outputs, or exact real private counts.
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
        "gate_thresholds": _build_gate_thresholds(),
        "gate_category_names": list(GATE_CATEGORY_NAMES),
        "bundle_schema_contract": _build_bundle_schema_contract(),
        "gate_results": {
            "min_total_n_gate_passed": bool(
                gate["min_total_n_gate_passed"]
            ),
            "bucket_cell_gate_passed": bool(
                gate["bucket_cell_gate_passed"]
            ),
            "second_rater_gate_passed": bool(
                gate["second_rater_gate_passed"]
            ),
            "agreement_gate_passed": bool(gate["agreement_gate_passed"]),
            "confidence_interval_gate_passed": bool(
                gate["confidence_interval_gate_passed"]
            ),
            "overall_gate_passed": bool(gate["overall_gate_passed"]),
        },
        "label_count_band": gate["label_count_band"],
        "bucket_count_bands": dict(gate["bucket_count_bands"]),
        "synthetic_harness_test": bool(synthetic_harness_test),
        "local_private_true_label_smoke_executed": bool(
            local_private_true_label_smoke_executed
        ),
        "input_attestation_required": True,
        # D3 protocol check (flat).
        **D3_PROTOCOL_FLAGS,
        # Private smoke transiently reads a local bundle in memory only to
        # validate shape/gates; it did NOT collect labels, persist the
        # bundle, emit rows, compute calibration, or commit output. In a
        # real local run that is not marked as a synthetic harness test,
        # truthfully mark the bundle as read/validated when the smoke
        # execution flag is true. Synthetic harness runs keep these false.
        "labels_collected": False,
        "true_label_bundle_read": bool(
            local_private_true_label_smoke_executed
        ),
        "true_label_bundle_validated": bool(
            local_private_true_label_smoke_executed
        ),
        "true_label_bundle_persisted": False,
        "calibration_metrics_computed": False,
        "inter_rater_agreement_measured": False,
        "confidence_intervals_computed": False,
        "true_e_s_calibration_claimed": False,
        "raw_label_rows_emitted": False,
        "private_input_path_emitted": False,
        "private_output_path_emitted": False,
        "private_output_committed": False,
        "exact_private_counts_emitted": False,
        "synthetic_labels_accepted_as_true": False,
        "proxy_labels_accepted_as_true": False,
        "llm_labels_accepted_as_true": False,
        "model_assisted_labels_allowed": False,
        # NOT a public-release gate pass and NOT a real bundle gate.
        "public_release_gate_passed": False,
        "real_label_bundle_gate_passed": False,
        # Harness/control flags (flat).
        **HARNESS_CONTROL_FLAGS,
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
    """Assemble the public harness / no-labels report (fail-closed scan).

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
# Self-test checks (pure, no I/O except in-memory probes and explicit
# /tmp symlink fixtures with cleanup)
# ---------------------------------------------------------------------------


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return {"check": name, "passed": bool(ok)}


def _valid_synthetic_bundle(
    *,
    total_labels: int = MIN_TOTAL_LABELS + 10,
    small_bucket: bool = False,
    empty_bucket: bool = False,
    rater_count: int = MIN_RATER_COUNT,
    agreement: bool = True,
    ci: bool = True,
) -> dict[str, Any]:
    """Build a synthetic human-manual-shaped bundle for gate-logic tests.

    This is a HARNESS self-test bundle only. It is human-manual-shaped
    (label_source=human_manual_true_e_s) but must be run with the
    --synthetic-harness-test flag, which sets synthetic_harness_test=true
    and local_private_true_label_smoke_executed=false.
    """
    # Build labels across the four buckets. By default every bucket meets
    # k_min AND the total meets min_total_labels (>= 50); small_bucket
    # forces one bucket below k_min; empty_bucket forces one bucket to
    # zero. per_bucket=13 => 4*13=52 >= 50 by default.
    per_bucket = 13
    counts = {
        "primary_evidence": per_bucket,
        "dependency_support": per_bucket,
        "weak_candidates": per_bucket,
        "abstained": per_bucket,
    }
    if small_bucket:
        counts["weak_candidates"] = K_MIN - 1
    if empty_bucket:
        counts["abstained"] = 0
    # Distribute total_labels proportionally but keep bucket counts fixed
    # above; ensure total >= MIN_TOTAL_LABELS unless caller overrides.
    labels: list[dict[str, Any]] = []
    e_levels = list(E_SCORE_LEVELS)
    s_levels = list(S_SCORE_LEVELS)
    for idx, bucket in enumerate(GATE_CATEGORY_NAMES):
        for j in range(counts[bucket]):
            labels.append(
                {
                    "e_score": e_levels[(idx + j) % len(e_levels)],
                    "s_score": s_levels[(idx + j) % len(s_levels)],
                    "bucket": bucket,
                    "citation_valid": (j % 2 == 0),
                    "rater_pair_present": True,
                    "adjudicated": (j % 3 == 0),
                }
            )
    # If the caller requested a specific total below the default bucket
    # sum, truncate (only used for the below-min-N failure case).
    if total_labels < len(labels):
        labels = labels[:total_labels]
    return {
        "schema": PRIVATE_BUNDLE_SCHEMA,
        "label_source": HUMAN_MANUAL_LABEL_SOURCE,
        "rater_count": rater_count,
        "agreement_available": agreement,
        "confidence_intervals_available": ci,
        "labels": labels,
    }


def _symlink_selftest_workspace() -> Path:
    """Create a unique /tmp workspace dir for symlink self-test fixtures."""
    pid = os.getpid()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    ws = Path("/tmp") / f"d4b_selftest_{pid}_{ts}"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all D4b self-test groups. Returns (checks, all_passed)."""
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
    for flag, value in HARNESS_CONTROL_FLAGS.items():
        checks.append(
            _check(
                f"harness_control_{flag}_true",
                skeleton.get(flag) is True,
            )
        )
    checks.append(
        _check(
            "default_input_attestation_required_false",
            skeleton["input_attestation_required"] is False,
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
            "mode_public_harness_no_labels",
            skeleton["mode"] == MODE_PUBLIC,
        )
    )
    checks.append(
        _check("phase_d4b", skeleton["phase"] == PHASE)
    )
    checks.append(
        _check(
            "bundle_schema_contract_defined_true",
            skeleton["bundle_schema_contract_defined"] is True,
        )
    )
    checks.append(
        _check(
            "bundle_schema_contract_has_schema_and_source",
            skeleton["bundle_schema_contract"]["bundle_schema"]
            == PRIVATE_BUNDLE_SCHEMA
            and skeleton["bundle_schema_contract"]["required_label_source"]
            == HUMAN_MANUAL_LABEL_SOURCE,
        )
    )
    checks.append(
        _check(
            "bundle_schema_contract_rejects_proxy_synthetic_llm",
            "proxy" in skeleton["bundle_schema_contract"]["rejected_label_sources"]
            and "synthetic"
            in skeleton["bundle_schema_contract"]["rejected_label_sources"]
            and "llm"
            in skeleton["bundle_schema_contract"]["rejected_label_sources"],
        )
    )

    # --- Group 3: D3 protocol constants / gates checked. ---
    checks.append(_check("k_min_is_5", K_MIN == 5))
    checks.append(
        _check("min_total_labels_is_50", MIN_TOTAL_LABELS == 50)
    )
    checks.append(
        _check("min_rater_count_is_2", MIN_RATER_COUNT == 2)
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
        _check("gate_thresholds_min_rater_count_2", gt["min_rater_count"] == 2)
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
            "e_score_levels_correct",
            tuple(skeleton["bundle_schema_contract"]["e_score_levels"])
            == E_SCORE_LEVELS,
        )
    )
    checks.append(
        _check(
            "s_score_levels_correct",
            tuple(skeleton["bundle_schema_contract"]["s_score_levels"])
            == S_SCORE_LEVELS,
        )
    )
    checks.append(
        _check(
            "private_execution_harness_tmp_only_not_committed",
            skeleton["private_execution_harness"]["opt_in_required"] is True
            and skeleton["private_execution_harness"]["output_location"]
            == "tmp_only_local_private"
            and skeleton["private_execution_harness"]["committed"] is False
            and skeleton["private_execution_harness"]["claims_calibration"]
            is False,
        )
    )

    # --- Group 4: Gate logic tests (synthetic human-manual-shaped). ---
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
            "gate_logic_pass_bucket_cell",
            g_pass["bucket_cell_gate_passed"] is True,
        )
    )
    checks.append(
        _check(
            "gate_logic_pass_second_rater",
            g_pass["second_rater_gate_passed"] is True,
        )
    )
    checks.append(
        _check(
            "gate_logic_pass_agreement",
            g_pass["agreement_gate_passed"] is True,
        )
    )
    checks.append(
        _check(
            "gate_logic_pass_ci",
            g_pass["confidence_interval_gate_passed"] is True,
        )
    )
    checks.append(
        _check(
            "gate_logic_pass_label_count_band_min_n_met",
            g_pass["label_count_band"] == "min_n_met",
        )
    )
    checks.append(
        _check(
            "gate_logic_pass_bucket_bands_all_k_met",
            all(
                band == "k_met"
                for band in g_pass["bucket_count_bands"].values()
            ),
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
            and g_low_n["overall_gate_passed"] is False
            and g_low_n["label_count_band"] == "below_min_n",
        )
    )
    # small bucket cell below 5 fails/suppresses.
    g_small = evaluate_gate_logic(
        _valid_synthetic_bundle(small_bucket=True)
    )
    checks.append(
        _check(
            "gate_logic_small_bucket_below_5_fails",
            g_small["bucket_cell_gate_passed"] is False
            and g_small["overall_gate_passed"] is False
            and g_small["bucket_count_bands"]["weak_candidates"]
            == "below_k",
        )
    )
    # empty bucket cell (0) is suppressed and fails the bucket gate.
    g_empty = evaluate_gate_logic(
        _valid_synthetic_bundle(empty_bucket=True)
    )
    checks.append(
        _check(
            "gate_logic_empty_bucket_suppressed_fails",
            g_empty["bucket_cell_gate_passed"] is False
            and g_empty["overall_gate_passed"] is False
            and g_empty["bucket_count_bands"]["abstained"]
            == "suppressed",
        )
    )
    # missing second rater fails.
    g_no_rater = evaluate_gate_logic(
        _valid_synthetic_bundle(rater_count=MIN_RATER_COUNT - 1)
    )
    checks.append(
        _check(
            "gate_logic_missing_second_rater_fails",
            g_no_rater["second_rater_gate_passed"] is False
            and g_no_rater["overall_gate_passed"] is False,
        )
    )
    # agreement unavailable fails.
    g_no_agree = evaluate_gate_logic(
        _valid_synthetic_bundle(agreement=False)
    )
    checks.append(
        _check(
            "gate_logic_agreement_unavailable_fails",
            g_no_agree["agreement_gate_passed"] is False
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

    # --- Group 5: Execution-claim logic (real vs synthetic). ---
    checks.append(
        _check(
            "execution_claim_synthetic_harness_test_false",
            _decide_execution_claim(
                synthetic_harness_test=True,
                label_source=HUMAN_MANUAL_LABEL_SOURCE,
                schema_valid=True,
            )
            is False,
        )
    )
    checks.append(
        _check(
            "execution_claim_real_human_manual_valid_true",
            _decide_execution_claim(
                synthetic_harness_test=False,
                label_source=HUMAN_MANUAL_LABEL_SOURCE,
                schema_valid=True,
            )
            is True,
        )
    )
    checks.append(
        _check(
            "execution_claim_proxy_source_false",
            _decide_execution_claim(
                synthetic_harness_test=False,
                label_source="proxy",
                schema_valid=True,
            )
            is False,
        )
    )
    checks.append(
        _check(
            "execution_claim_invalid_schema_false",
            _decide_execution_claim(
                synthetic_harness_test=False,
                label_source=HUMAN_MANUAL_LABEL_SOURCE,
                schema_valid=False,
            )
            is False,
        )
    )

    # --- Group 6: Bundle schema validation (reject proxy/synthetic/llm
    # and unknown keys). ---
    # Valid human-manual bundle validates.
    valid_ok = True
    try:
        _validate_bundle_schema(_valid_synthetic_bundle())
    except _PrivateLabelLoadError:
        valid_ok = False
    checks.append(
        _check(
            "valid_human_manual_bundle_validates",
            valid_ok,
        )
    )
    # Proxy source rejected as true labels.
    proxy_rejected = False
    try:
        _validate_bundle_schema(
            {**_valid_synthetic_bundle(), "label_source": "proxy"}
        )
    except _PrivateLabelLoadError:
        proxy_rejected = True
    checks.append(
        _check(
            "proxy_label_source_rejected",
            proxy_rejected,
        )
    )
    # Synthetic source rejected as true labels.
    synth_rejected = False
    try:
        _validate_bundle_schema(
            {**_valid_synthetic_bundle(), "label_source": "synthetic"}
        )
    except _PrivateLabelLoadError:
        synth_rejected = True
    checks.append(
        _check(
            "synthetic_label_source_rejected",
            synth_rejected,
        )
    )
    # LLM source rejected as true labels.
    llm_rejected = False
    try:
        _validate_bundle_schema(
            {**_valid_synthetic_bundle(), "label_source": "llm"}
        )
    except _PrivateLabelLoadError:
        llm_rejected = True
    checks.append(
        _check(
            "llm_label_source_rejected",
            llm_rejected,
        )
    )
    # Unknown schema rejected.
    bad_schema_rejected = False
    try:
        _validate_bundle_schema(
            {**_valid_synthetic_bundle(), "schema": "wrong_schema"}
        )
    except _PrivateLabelLoadError:
        bad_schema_rejected = True
    checks.append(
        _check("unknown_bundle_schema_rejected", bad_schema_rejected)
    )
    # rater_count < 2 rejected.
    low_rater_rejected = False
    try:
        _validate_bundle_schema(
            _valid_synthetic_bundle(rater_count=1)
        )
    except _PrivateLabelLoadError:
        low_rater_rejected = True
    checks.append(
        _check("rater_count_below_2_rejected", low_rater_rejected)
    )
    # Unknown label key (task_id) rejected.
    bad_label_key_rejected = False
    bundle_extra = _valid_synthetic_bundle()
    bundle_extra = {
        **bundle_extra,
        "labels": [
            {**bundle_extra["labels"][0], "task_id": "SECRET_LABEL_SENTINEL"}
        ],
    }
    try:
        _validate_bundle_schema(bundle_extra)
    except _PrivateLabelLoadError:
        bad_label_key_rejected = True
    checks.append(
        _check(
            "label_with_task_id_rejected",
            bad_label_key_rejected,
        )
    )
    # Unknown bundle key (rater_id) rejected.
    bad_bundle_key_rejected = False
    try:
        _validate_bundle_schema(
            {**_valid_synthetic_bundle(), "rater_id": "alice"}
        )
    except _PrivateLabelLoadError:
        bad_bundle_key_rejected = True
    checks.append(
        _check(
            "bundle_with_rater_id_rejected",
            bad_bundle_key_rejected,
        )
    )
    # Unknown bundle key (path) rejected.
    path_key_rejected = False
    try:
        _validate_bundle_schema(
            {**_valid_synthetic_bundle(), "path": "src/foo.py"}
        )
    except _PrivateLabelLoadError:
        path_key_rejected = True
    checks.append(
        _check("bundle_with_path_key_rejected", path_key_rejected)
    )
    # Unknown bundle key (snippet) rejected.
    snippet_key_rejected = False
    try:
        _validate_bundle_schema(
            {**_valid_synthetic_bundle(), "snippet": "SECRET_LABEL_SENTINEL"}
        )
    except _PrivateLabelLoadError:
        snippet_key_rejected = True
    checks.append(
        _check("bundle_with_snippet_key_rejected", snippet_key_rejected)
    )
    # Unknown bundle key (raw_label) rejected.
    raw_label_key_rejected = False
    try:
        _validate_bundle_schema(
            {**_valid_synthetic_bundle(), "raw_label": "SECRET_LABEL_SENTINEL"}
        )
    except _PrivateLabelLoadError:
        raw_label_key_rejected = True
    checks.append(
        _check(
            "bundle_with_raw_label_key_rejected",
            raw_label_key_rejected,
        )
    )
    # Invalid e_score rejected.
    bad_e_rejected = False
    bundle_bad_e = _valid_synthetic_bundle()
    bundle_bad_e = {
        **bundle_bad_e,
        "labels": [{**bundle_bad_e["labels"][0], "e_score": "E9"}],
    }
    try:
        _validate_bundle_schema(bundle_bad_e)
    except _PrivateLabelLoadError:
        bad_e_rejected = True
    checks.append(
        _check("invalid_e_score_rejected", bad_e_rejected)
    )
    # Invalid bucket rejected.
    bad_bucket_rejected = False
    bundle_bad_b = _valid_synthetic_bundle()
    bundle_bad_b = {
        **bundle_bad_b,
        "labels": [
            {**bundle_bad_b["labels"][0], "bucket": "unknown_bucket"}
        ],
    }
    try:
        _validate_bundle_schema(bundle_bad_b)
    except _PrivateLabelLoadError:
        bad_bucket_rejected = True
    checks.append(
        _check("invalid_bucket_rejected", bad_bucket_rejected)
    )
    # Non-bool citation_valid rejected.
    bad_bool_rejected = False
    bundle_bad_bool = _valid_synthetic_bundle()
    bundle_bad_bool = {
        **bundle_bad_bool,
        "labels": [
            {**bundle_bad_bool["labels"][0], "citation_valid": "yes"}
        ],
    }
    try:
        _validate_bundle_schema(bundle_bad_bool)
    except _PrivateLabelLoadError:
        bad_bool_rejected = True
    checks.append(
        _check("non_bool_citation_valid_rejected", bad_bool_rejected)
    )
    # Empty labels list rejected.
    empty_labels_rejected = False
    try:
        _validate_bundle_schema(
            {**_valid_synthetic_bundle(), "labels": []}
        )
    except _PrivateLabelLoadError:
        empty_labels_rejected = True
    checks.append(
        _check("empty_labels_rejected", empty_labels_rejected)
    )
    # Non-dict bundle rejected.
    non_dict_rejected = False
    try:
        _validate_bundle_schema([1, 2, 3])  # type: ignore[arg-type]
    except _PrivateLabelLoadError:
        non_dict_rejected = True
    checks.append(
        _check("non_dict_bundle_rejected", non_dict_rejected)
    )

    # --- Group 7: CLI guard matrix (pure lexical). ---
    sensitive_input = Path("/private/SECRET_LABEL_SENTINEL_sensitive.jsonl")
    # --input without --allow-private-labels => error.
    err_input_no_allow = _validate_cli_args(
        allow_private_labels=False,
        input_path=sensitive_input,
        out_path=None,
        synthetic_harness_test=False,
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
        out_path=Path("/tmp/d4b.json"),
        synthetic_harness_test=False,
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
        synthetic_harness_test=False,
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
        synthetic_harness_test=False,
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
        out_path=Path("/not/tmp/d4b.json"),
        synthetic_harness_test=False,
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
    # --synthetic-harness-test without --allow-private-labels => error.
    err_synth_no_allow = _validate_cli_args(
        allow_private_labels=False,
        input_path=None,
        out_path=None,
        synthetic_harness_test=True,
    )
    checks.append(
        _check(
            "cli_synthetic_without_allow_rejected",
            err_synth_no_allow is not None,
        )
    )
    # allow + /tmp out => valid (real mode).
    err_tmp_ok = _validate_cli_args(
        allow_private_labels=True,
        input_path=sensitive_input,
        out_path=Path("/tmp/d4b_smoke.json"),
        synthetic_harness_test=False,
    )
    checks.append(
        _check(
            "cli_allow_tmp_out_allowed",
            err_tmp_ok is None,
        )
    )
    # allow + /tmp out + synthetic => valid.
    err_tmp_synth = _validate_cli_args(
        allow_private_labels=True,
        input_path=sensitive_input,
        out_path=Path("/tmp/d4b_harness.json"),
        synthetic_harness_test=True,
    )
    checks.append(
        _check(
            "cli_allow_tmp_out_synthetic_allowed",
            err_tmp_synth is None,
        )
    )
    # default mode (no private args) => valid.
    err_default = _validate_cli_args(
        allow_private_labels=False,
        input_path=None,
        out_path=None,
        synthetic_harness_test=False,
    )
    checks.append(
        _check("cli_default_mode_allowed", err_default is None)
    )
    # path traversal /tmp/../etc is NOT under /tmp.
    err_traversal = _validate_cli_args(
        allow_private_labels=True,
        input_path=sensitive_input,
        out_path=Path("/tmp/../etc/passwd"),
        synthetic_harness_test=False,
    )
    checks.append(
        _check(
            "cli_traversal_out_rejected",
            err_traversal is not None,
        )
    )

    # --- Group 8: Validate-before-read (probe records no input access). ---
    probe_invalid = _ReadProbe()
    _report, err_probe = _run_private_smoke(
        allow_private_labels=True,
        input_path=Path("/private/SECRET_LABEL_SENTINEL_nonexistent.jsonl"),
        out_path=Path("/not/tmp/d4b.json"),  # invalid out (lexical)
        synthetic_harness_test=False,
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
    _report2, err_pc = _run_private_smoke(
        allow_private_labels=True,
        input_path=Path("/private/SECRET_LABEL_SENTINEL.jsonl"),
        out_path=DEFAULT_OUT,
        synthetic_harness_test=False,
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
    _report3, err_pn = _run_private_smoke(
        allow_private_labels=True,
        input_path=Path("/private/SECRET_LABEL_SENTINEL.jsonl"),
        out_path=Path("/home/user/d4b.json"),
        synthetic_harness_test=False,
        loader=probe_nontmp.loader,
        input_exists=probe_nontmp.exists,
    )
    checks.append(
        _check(
            "non_tmp_out_rejected_before_read",
            err_pn is not None and probe_nontmp.calls == [],
        )
    )
    # Synthetic flag without allow rejected before read.
    probe_synth = _ReadProbe()
    _report4, err_ps = _run_private_smoke(
        allow_private_labels=False,
        input_path=None,
        out_path=None,
        synthetic_harness_test=True,
        loader=probe_synth.loader,
        input_exists=probe_synth.exists,
    )
    checks.append(
        _check(
            "synthetic_without_allow_rejected_before_read",
            err_ps is not None and probe_synth.calls == [],
        )
    )

    # --- Group 9: Sanitized error with sensitive basename + sentinel. ---
    # Malformed bundle (forbidden keys + sentinel) returned by a loader:
    # the schema validator must reject it and only the fixed sanitized
    # error is surfaced; nothing reaches the report.
    malformed_bundle = {
        "schema": PRIVATE_BUNDLE_SCHEMA,
        "label_source": HUMAN_MANUAL_LABEL_SOURCE,
        "rater_count": 2,
        "agreement_available": True,
        "confidence_intervals_available": True,
        "rater_id": "alice",
        "raw_label": "SECRET_LABEL_SENTINEL_raw_text",
        "annotation_row": {"row": 1, "text": "SECRET_LABEL_SENTINEL"},
        "labels": [],
    }
    probe_malformed = _ReadProbe(bundle=malformed_bundle)
    _report5, err_malformed = _run_private_smoke(
        allow_private_labels=True,
        input_path=Path("/private/SECRET_LABEL_SENTINEL_bundle.jsonl"),
        out_path=Path("/tmp/d4b_malformed.json"),
        synthetic_harness_test=False,
        loader=probe_malformed.loader,
        input_exists=probe_malformed.exists,
    )
    checks.append(
        _check(
            "malformed_bundle_returns_sanitized_error",
            err_malformed == PRIVATE_LOAD_ERROR_MESSAGE
            and _report5 is None,
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
    # Proxy-source bundle returns sanitized error (rejected as true labels).
    proxy_bundle = {
        **_valid_synthetic_bundle(),
        "label_source": "proxy",
    }
    probe_proxy = _ReadProbe(bundle=proxy_bundle)
    _report6, err_proxy = _run_private_smoke(
        allow_private_labels=True,
        input_path=Path("/private/SECRET_LABEL_SENTINEL_proxy.jsonl"),
        out_path=Path("/tmp/d4b_proxy.json"),
        synthetic_harness_test=False,
        loader=probe_proxy.loader,
        input_exists=probe_proxy.exists,
    )
    checks.append(
        _check(
            "proxy_bundle_returns_sanitized_error",
            err_proxy == PRIVATE_LOAD_ERROR_MESSAGE and _report6 is None,
        )
    )
    # Nonexistent input returns the sanitized error (no path leak).
    probe_missing = _ReadProbe(bundle=None)
    probe_missing.exists = lambda p: False  # type: ignore[method-assign]
    _report7, err_missing = _run_private_smoke(
        allow_private_labels=True,
        input_path=Path("/private/SECRET_LABEL_SENTINEL_missing.jsonl"),
        out_path=Path("/tmp/d4b_missing.json"),
        synthetic_harness_test=False,
        loader=probe_missing.loader,
        input_exists=probe_missing.exists,
    )
    checks.append(
        _check(
            "missing_input_returns_sanitized_error",
            err_missing == PRIVATE_LOAD_ERROR_MESSAGE
            and _report7 is None,
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

    # --- Group 10: Private smoke success path (synthetic harness test) —
    # no path/basename/raw label/exact counts/output path in report. ---
    valid_bundle = _valid_synthetic_bundle()
    sensitive_in = Path("/private/SECRET_LABEL_SENTINEL_success.jsonl")
    sensitive_out = Path("/tmp/SECRET_LABEL_SENTINEL_out.json")
    probe_ok = _ReadProbe(bundle=valid_bundle)
    report_ok, err_ok = _run_private_smoke(
        allow_private_labels=True,
        input_path=sensitive_in,
        out_path=sensitive_out,
        synthetic_harness_test=True,
        loader=probe_ok.loader,
        input_exists=probe_ok.exists,
    )
    checks.append(
        _check(
            "private_smoke_success_returns_report",
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
            "private_report_no_labels_key_or_rows",
            report_ok is not None
            and not _has_dict_key_anywhere(report_ok, "labels")
            and not _has_dict_key_anywhere(report_ok, "rater_id")
            and not _has_dict_key_anywhere(report_ok, "raw_label")
            and not _has_dict_key_anywhere(report_ok, "annotation_row")
            and not _has_dict_key_anywhere(report_ok, "per_row_hash")
            and '"rater_id"' not in ok_blob
            and '"raw_label"' not in ok_blob
            and '"annotation_row"' not in ok_blob
            and '"per_row_hash"' not in ok_blob,
        )
    )
    # No exact private counts: the bundle's total (60) and per-bucket n
    # (10) must NOT be echoed as exact counts (only bands + constants).
    checks.append(
        _check(
            "private_report_no_exact_private_sample_sizes",
            # total_labels/bucket counts are not echoed as values; only
            # the constant thresholds (50, 5) and bands appear.
            ok_blob.count('"total_labels"') == 0
            and ok_blob.count('"min_cell_n"') == 0,
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
            "private_report_label_count_band_min_n_met",
            report_ok is not None
            and report_ok["label_count_band"] == "min_n_met",
        )
    )
    checks.append(
        _check(
            "private_report_bucket_count_bands_all_k_met",
            report_ok is not None
            and all(
                band == "k_met"
                for band in report_ok["bucket_count_bands"].values()
            ),
        )
    )
    checks.append(
        _check(
            "private_report_synthetic_harness_test_true",
            report_ok is not None
            and report_ok["synthetic_harness_test"] is True,
        )
    )
    checks.append(
        _check(
            "private_report_local_executed_false_for_synthetic",
            report_ok is not None
            and report_ok["local_private_true_label_smoke_executed"]
            is False,
        )
    )
    checks.append(
        _check(
            "private_report_input_attestation_required_true",
            report_ok is not None
            and report_ok["input_attestation_required"] is True,
        )
    )
    checks.append(
        _check(
            "private_report_no_claim_flags_remain_false",
            report_ok is not None
            and report_ok["labels_collected"] is False
            and report_ok["true_label_bundle_read"] is False
            and report_ok["true_label_bundle_validated"] is False
            and report_ok["true_label_bundle_persisted"] is False
            and report_ok["calibration_metrics_computed"] is False
            and report_ok["inter_rater_agreement_measured"] is False
            and report_ok["confidence_intervals_computed"] is False
            and report_ok["true_e_s_calibration_claimed"] is False
            and report_ok["proxy_labels_accepted_as_true"] is False
            and report_ok["synthetic_labels_accepted_as_true"] is False
            and report_ok["llm_labels_accepted_as_true"] is False
            and report_ok["model_assisted_labels_allowed"] is False
            and report_ok["raw_label_rows_emitted"] is False
            and report_ok["private_output_committed"] is False
            and report_ok["exact_private_counts_emitted"] is False
            and report_ok["public_release_gate_passed"] is False
            and report_ok["real_label_bundle_gate_passed"] is False,
        )
    )
    checks.append(
        _check(
            "private_report_harness_flags_true",
            report_ok is not None
            and report_ok["private_execution_harness_available"] is True
            and report_ok["private_cli_guard_validated"] is True
            and report_ok["tmp_output_resolved_guard_validated"] is True
            and report_ok["sanitized_error_guard_validated"] is True
            and report_ok["bundle_schema_contract_defined"] is True,
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

    # --- Group 11: Real-mode flag logic (in-memory, not committed). ---
    # A real-mode run (synthetic flag false, human_manual source, valid
    # schema) sets local_private_true_label_smoke_executed=true in the
    # in-memory report. This report is NOT written or committed by the
    # self-test; it only verifies the flag logic.
    probe_real = _ReadProbe(bundle=valid_bundle)
    report_real, err_real = _run_private_smoke(
        allow_private_labels=True,
        input_path=Path("/private/SECRET_LABEL_SENTINEL_real.jsonl"),
        out_path=Path("/tmp/SECRET_LABEL_SENTINEL_real_out.json"),
        synthetic_harness_test=False,
        loader=probe_real.loader,
        input_exists=probe_real.exists,
    )
    checks.append(
        _check(
            "real_mode_report_local_executed_true",
            err_real is None
            and report_real is not None
            and report_real["synthetic_harness_test"] is False
            and report_real["local_private_true_label_smoke_executed"]
            is True,
        )
    )
    checks.append(
        _check(
            "real_mode_report_true_label_bundle_read_true",
            report_real is not None
            and report_real["true_label_bundle_read"] is True,
        )
    )
    checks.append(
        _check(
            "real_mode_report_true_label_bundle_validated_true",
            report_real is not None
            and report_real["true_label_bundle_validated"] is True,
        )
    )
    checks.append(
        _check(
            "real_mode_report_no_raw_or_persisted_private_output",
            report_real is not None
            and report_real["true_label_bundle_persisted"] is False
            and report_real["raw_label_rows_emitted"] is False
            and report_real["exact_private_counts_emitted"] is False
            and report_real["private_output_committed"] is False,
        )
    )
    checks.append(
        _check(
            "real_mode_report_no_sentinel_or_paths",
            report_real is not None
            and "SECRET_LABEL_SENTINEL"
            not in json.dumps(report_real, sort_keys=True),
        )
    )

    # --- Group 12: Resolved /tmp symlink-escape guards (filesystem). ---
    # Parent-symlink escape: /tmp/<ws>/link_to_repo/out.json where the
    # parent symlink escapes /tmp.
    ws = None
    try:
        ws = _symlink_selftest_workspace()
        escape_link = ws / "link_to_repo"
        try:
            escape_link.symlink_to("/workspace")
        except OSError:
            escape_link.symlink_to("/")
        out_parent_escape = escape_link / "out.json"
        # Use a probe so we can assert no input access occurs on rejection.
        probe_esc = _ReadProbe(bundle=valid_bundle)
        _rep_esc, err_esc = _run_private_smoke(
            allow_private_labels=True,
            input_path=Path("/private/SECRET_LABEL_SENTINEL_esc.jsonl"),
            out_path=out_parent_escape,
            synthetic_harness_test=True,
            loader=probe_esc.loader,
            input_exists=probe_esc.exists,
        )
        checks.append(
            _check(
                "parent_symlink_escape_rejected",
                err_esc is not None and probe_esc.calls == [],
            )
        )
        checks.append(
            _check(
                "parent_symlink_escape_error_no_leak",
                err_esc is not None
                and "SECRET_LABEL_SENTINEL" not in err_esc,
            )
        )
        # Existing output file symlink pointing outside /tmp rejected.
        out_file_symlink = ws / "outlink.json"
        try:
            out_file_symlink.symlink_to("/workspace/secret.json")
        except OSError:
            out_file_symlink.symlink_to("/secret.json")
        probe_fs = _ReadProbe(bundle=valid_bundle)
        _rep_fs, err_fs = _run_private_smoke(
            allow_private_labels=True,
            input_path=Path("/private/SECRET_LABEL_SENTINEL_fs.jsonl"),
            out_path=out_file_symlink,
            synthetic_harness_test=True,
            loader=probe_fs.loader,
            input_exists=probe_fs.exists,
        )
        checks.append(
            _check(
                "existing_output_symlink_rejected",
                err_fs is not None and probe_fs.calls == [],
            )
        )
        # Valid /tmp output (no symlinks) passes the guard.
        out_valid = ws / "valid_out.json"
        probe_vo = _ReadProbe(bundle=valid_bundle)
        _rep_vo, err_vo = _run_private_smoke(
            allow_private_labels=True,
            input_path=Path("/private/SECRET_LABEL_SENTINEL_vo.jsonl"),
            out_path=out_valid,
            synthetic_harness_test=True,
            loader=probe_vo.loader,
            input_exists=probe_vo.exists,
        )
        checks.append(
            _check(
                "valid_tmp_output_guard_passes",
                err_vo is None and _rep_vo is not None,
            )
        )
    finally:
        if ws is not None:
            import shutil

            shutil.rmtree(ws, ignore_errors=True)

    # --- Group 13: Forbidden scanner rejects sensitive keys/values. ---
    def _has_cat(obj: Any, cat: str) -> bool:
        return any(v["category"] == cat for v in _scan_forbidden(obj))

    for bad_key in (
        "task_id", "repo_id", "repo", "path", "span", "line_range",
        "start_line", "end_line", "content_sha", "snippet",
        "candidate_text", "query", "prompt", "response", "model_output",
        "label", "labels", "raw_label", "annotation_row", "rater_id",
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
    # Safe gate/protocol/band strings must NOT be flagged.
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
            not _scan_forbidden({"phase": PHASE}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_safe_band_string",
            not _scan_forbidden(
                {
                    "label_count_band": "min_n_met",
                    "bucket_count_bands": {
                        "primary_evidence": "k_met",
                        "weak_candidates": "below_k",
                        "abstained": "suppressed",
                    },
                }
            ),
        )
    )

    # --- Group 14: Fail-closed generation on scanner leak. ---
    raised = False
    try:
        _enforce_no_forbidden(
            {"path": "src/foo.py", "content_sha": "a" * 64,
             "rater_id": "alice", "raw_label": "SECRET_LABEL_SENTINEL",
             "labels": [{"e_score": "E0"}]}
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
    # Private report forbidden scan clean.
    checks.append(
        _check(
            "private_report_forbidden_scan_clean_on_success",
            report_ok is not None
            and report_ok["forbidden_scan"]["status"] == "pass",
        )
    )

    # --- Group 15: Artifact generation refuses success if self-test fails. ---
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

    # --- Group 16: CLI option surface (exactly the required options). ---
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
            "cli_has_synthetic_harness_test_argument",
            "--synthetic-harness-test" in cli_opts,
        )
    )
    checks.append(
        _check(
            "cli_only_required_arguments",
            (cli_opts - {"-h", "--help"})
            == {
                "--self-test",
                "--out",
                "--allow-private-labels",
                "--input",
                "--synthetic-harness-test",
            },
        )
    )
    checks.append(
        _check(
            "cli_synthetic_harness_test_defaults_false",
            build_parser().get_default("synthetic_harness_test") is False,
        )
    )

    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the D4b CLI parser."""
    ap = argparse.ArgumentParser(
        description=(
            "D4b dual-rubric true-label smoke harness "
            "(public harness/no-labels artifact; no labels collected)."
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
            "output artifact JSON path (default: committed public harness "
            "artifact; private smoke requires an explicit /tmp path)"
        ),
    )
    ap.add_argument(
        "--allow-private-labels",
        action="store_true",
        help=(
            "opt-in private true-label smoke harness; requires --input; "
            "output must go to /tmp only (NOT committed)"
        ),
    )
    ap.add_argument(
        "--input",
        type=Path,
        default=None,
        help=(
            "path to a private true-label-bundle JSON (private smoke only; "
            "requires --allow-private-labels); never serialized into any "
            "artifact"
        ),
    )
    ap.add_argument(
        "--synthetic-harness-test",
        action="store_true",
        default=False,
        help=(
            "mark a private smoke run as a synthetic/in-memory harness "
            "test (requires --allow-private-labels); sets "
            "synthetic_harness_test=true and "
            "local_private_true_label_smoke_executed=false"
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

    # Private smoke mode (any private arg present).
    if (
        args.allow_private_labels
        or args.input is not None
        or args.synthetic_harness_test
    ):
        report, err = _run_private_smoke(
            allow_private_labels=args.allow_private_labels,
            input_path=args.input,
            out_path=args.out,
            synthetic_harness_test=args.synthetic_harness_test,
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
            "wrote D4b private true-label smoke harness to /tmp output "
            f"(forbidden_scan={report['forbidden_scan']['status']}, "
            f"overall_gate_passed="
            f"{report['gate_results']['overall_gate_passed']}, "
            f"synthetic_harness_test={report['synthetic_harness_test']}, "
            f"local_private_true_label_smoke_executed="
            f"{report['local_private_true_label_smoke_executed']}) "
            f"[NOT committed; /tmp only]"
        )
        return

    # Public default mode (committed harness/no-labels artifact).
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
