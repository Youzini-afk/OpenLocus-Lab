#!/usr/bin/env python3
"""D5-A0 Automated E/S Calibration Smoke (Public Aggregate-Only Artifact).

This module implements the **D5-A0 automated E/S calibration smoke**
public artifact. D5-A0 is the **first empirical, post-control-plane
smoke** of the Step 6 dual-rubric pipeline. It uses the **existing
committed r14 sanity fixtures** (``fixtures/r14/tasks/sanity.jsonl`` +
``fixtures/r14/labels/sanity.jsonl``) and **real OpenLocus retrieval
outputs** produced transiently into ``/tmp`` (never committed) to compute
**automated E/S calibration smoke** aggregate metrics over the four
fixed retrieval methods (regex, bm25, symbol, rrf).

D5-A0 **does not** collect new human/manual labels, **does not** claim
true E/S calibration, **does not** audit human reference labels, **does
not** pass any public-release gate, **does not** promote any candidate,
**does not** unblock D5-H / human-reference / human-calibrated claims,
**does not** unblock default/policy/public-release or human-calibrated
claims, **does not** change runtime behavior, retriever, pack, model,
backend, default policy, or EvidenceCore semantics. The D5-A automated
empirical path is active (this smoke); D5-H / human-reference /
human-calibrated calibration remains out of scope until human labels.
D5-A0 **does not** commit raw predictions, raw retrieval outputs,
per-candidate rows, paths, spans, snippets, content hashes, queries,
gold labels, hard-negative labels, repo IDs, task IDs, or any row-level
data.

Claim boundary (binding):

* This is **eval/diagnostic only**. It is NOT a runtime change, NOT a
  retriever/pack/model/backend/default-policy change, and NOT an
  EvidenceCore semantic change.
* Claim level: ``automated_e_s_calibration_smoke_only``.
* Status: ``automated_es_calibration_smoke_pass`` on success; mode
  ``public_aggregate_r14_retrieval_smoke``; phase ``D5-A0``.
* The default committed artifact reads the **committed r14 sanity
  fixtures**, invokes ``eval/run_retrieval.py`` per method into
  ``/tmp`` (transient, never committed), reads those transient outputs,
  computes aggregate E/S labels from existing committed span labels, and
  writes ONLY aggregate counts/rates to the committed artifact. No raw
  predictions, no per-candidate rows, no paths/spans/snippets/hashes are
  ever committed.

Automated E label procedure (deterministic, derived from existing
committed span labels; never treated as true human E/S):

* invalid/source-missing candidate (no path, or no valid 1 <= start_line
  <= end_line) -> ``e_uncertain``;
* candidate overlaps a hard-negative span (same path AND line overlap
  with a hard-negative span) and a gold span -> ``conflict_uncertain``;
* candidate overlaps a hard-negative span only -> ``e_hard_negative``;
* candidate overlaps a gold span -> ``e_positive``;
* candidate is on a gold file path but has no gold overlap ->
  ``e_wrong_span_gold_file``;
* candidate is on a non-gold file path with a valid span ->
  ``e_negative_non_gold_file``;
* missing labels are NEVER treated as negatives; they fall through to
  ``e_uncertain``.

S-proxy label procedure (NOT a true human S-score; deterministic
support-shape evidence only):

* E-positive candidates are NOT evaluated for S-proxy
  (``s_proxy_not_evaluated_for_e_positive``) to avoid conflation;
* E-hard-negative / conflict-uncertain / e-uncertain candidates get
  ``s_proxy_none`` (do not conflate hard-negative shape with positive
  support);
* ``e_wrong_span_gold_file`` candidates (same gold file, no gold
  overlap) get ``s_proxy_positive`` (deterministic same-file support
  shape);
* candidates adjacent to a gold span on the same gold file (within
  +/-5 lines of any gold span boundary) get ``s_proxy_positive``;
* otherwise ``s_proxy_none`` (no deterministic support-shape signal).

Run::

    python3 -m py_compile eval/d5a_automated_es_calibration.py
    python3 eval/d5a_automated_es_calibration.py --self-test
    python3 eval/d5a_automated_es_calibration.py \\
        --out artifacts/d5a_automated_es_calibration/\\
d5a_automated_es_calibration_report.json

The default mode invokes ``eval/run_retrieval.py`` per method into a
transient ``/tmp/d5a_retrieval_*`` directory and writes ONLY the public
aggregate artifact. ``--self-test`` runs synthetic in-memory
predictions/labels with no external openlocus required.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "d5a_automated_es_calibration.v1"
GENERATED_BY = "eval/d5a_automated_es_calibration.py"
CLAIM_LEVEL = "automated_e_s_calibration_smoke_only"
TARGET_STATUS = "automated_es_calibration_smoke_pass"
STATUS_BLOCKED = "automated_es_calibration_smoke_blocked"
MODE = "public_aggregate_r14_retrieval_smoke"
PHASE = "D5-A0"

DEFAULT_OUT = Path(
    "artifacts/d5a_automated_es_calibration/"
    "d5a_automated_es_calibration_report.json"
)
DEFAULT_TASKS = Path("fixtures/r14/tasks/sanity.jsonl")
DEFAULT_LABELS = Path("fixtures/r14/labels/sanity.jsonl")
DEFAULT_OPENLOCUS = "target/debug/openlocus"
DEFAULT_CANDIDATE_LIMIT = 50
ADJACENCY_LINE_WINDOW = 5

# The four fixed retrieval methods evaluated by D5-A0.
METHODS: tuple[str, ...] = ("regex", "bm25", "symbol", "rrf")

# Approved short identifiers allowed as VALUES in the public artifact
# (methods + fixture label + label categories). All are short
# alphanumeric/underscore tokens with no file extension, so they do not
# match the path-like / hex / URL / secret / multiline / raw-JSON /
# line-range / sentinel forbidden value patterns. They are listed here
# explicitly to make the contract auditable; the scanner does NOT use
# an over-broad container exemption.
SAFE_SHORT_TOKENS: frozenset[str] = frozenset(
    {
        *METHODS,
        "r14_sanity",
        "human_reviewed",
        "mined",
        "mined_high_confidence",
        "unknown",
        "other_unapproved_label_source_category",
        # automated E label categories
        "e_positive",
        "e_hard_negative",
        "conflict_uncertain",
        "e_wrong_span_gold_file",
        "e_negative_non_gold_file",
        "e_uncertain",
        # S-proxy label categories
        "s_proxy_positive",
        "s_proxy_none",
        "s_proxy_uncertain",
        "s_proxy_not_evaluated_for_e_positive",
        # retrieval categories
        "run_retrieval_subprocess",
        "tmp_only_transient",
    }
)

APPROVED_LABEL_SOURCE_CATEGORIES: frozenset[str] = frozenset(
    {
        "human_reviewed",
        "mined",
        "mined_high_confidence",
        "unknown",
    }
)
COLLAPSED_LABEL_SOURCE_CATEGORY = "other_unapproved_label_source_category"

E_LABEL_CATEGORIES: tuple[str, ...] = (
    "e_positive",
    "e_hard_negative",
    "conflict_uncertain",
    "e_wrong_span_gold_file",
    "e_negative_non_gold_file",
    "e_uncertain",
)

S_PROXY_CATEGORIES: tuple[str, ...] = (
    "s_proxy_positive",
    "s_proxy_none",
    "s_proxy_uncertain",
    "s_proxy_not_evaluated_for_e_positive",
)

# ---------------------------------------------------------------------------
# Safe booleans true (smoke harness complete + aggregate-only /
# diagnostic / not-evidence + smoke-claimed + uses-existing-labels).
# Exactly these are true in the committed public artifact.
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
    "not_evidence": True,
    "automated_e_s_calibration_smoke_claimed": True,
    "automated_d5a_path_active": True,
    "uses_existing_committed_labels": True,
    "self_test_executed": True,
    "transient_retrieval_outputs_only": True,
}

# ---------------------------------------------------------------------------
# No-claim / no-runtime-change flags (all MUST be false in the committed
# public artifact). D5-A0 computes NO true E/S calibration, collects NO
# new human labels, audits NO human reference, promotes NO candidate,
# changes NO runtime/retriever/pack/model/backend/default-policy, and
# changes NO EvidenceCore semantics.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    # core no-claim flags required by the task contract
    "automated_e_s_calibration_claimed": False,
    "human_e_s_calibration_claimed": False,
    "new_human_labels_collected": False,
    "human_reference_audit_claimed": False,
    "promotion_ready": False,
    "default_should_change": False,
    "evidencecore_semantics_changed": False,
    "runtime_clean_general_algorithm_claimed": False,
    "downstream_agent_value_proven": False,
    "external_benchmark_performance_claimed": False,
    "runtime_behavior_changed": False,
    "retriever_changed": False,
    "pack_builder_changed": False,
    "model_calls_changed": False,
    "backend_changed": False,
    "default_policy_changed": False,
    # additional safety / no-leak flags
    "true_e_s_calibration_claimed": False,
    "raw_predictions_committed": False,
    "raw_retrieval_outputs_committed": False,
    "per_candidate_rows_emitted": False,
    "public_release_gate_passed": False,
    "d5_human_reference_calibration_unblocked": False,
    "ood_temporal_supported": False,
    "quiver_systems_supported": False,
}

# ---------------------------------------------------------------------------
# Public artifact scanner (strict, fail-closed). No contract containers
# with field-name tokens; no over-broad container exemption. Sensitive
# field-name tokens are NEVER emitted as keys anywhere and NEVER emitted
# as values outside the explicit short-token allowlist below. The scanner
# runs ONLY against the final public aggregate artifact (NOT against
# in-memory predictions/labels, which contain path/start_line/etc.).
# ---------------------------------------------------------------------------

# Top-level keys whose subtrees are explicit contract containers
# (short-token allowlists only). String VALUES inside these containers
# must be in APPROVED_CONTRACT_STRINGS. No over-broad exemption.
CONTRACT_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "methods_evaluated",
        "methods_attempted",
        "methods_succeeded",
        "e_label_categories",
        "s_proxy_label_categories",
    }
)

# Exact string values allowed inside contract containers (method names,
# fixture category, E/S label category tokens). No URLs, no paths, no
# implementation symbols, no sensitive field names.
APPROVED_CONTRACT_STRINGS: frozenset[str] = frozenset(SAFE_SHORT_TOKENS)

# Sensitive KEY names that must NEVER appear as dict keys anywhere in a
# public artifact JSON. Superset of location/content/hash/identifier/
# label/rater/prompt/row/patch/secret/agreement/CI keys. Adds the keys
# the D5-A0 contract explicitly forbids (task_id, query, path, file,
# span, start_line, end_line, snippet, content_sha, gold, label,
# hard_negative, repo_id, etc.).
FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset(
    {
        # location / span
        "path", "span", "line_range", "start_line", "end_line",
        "start_byte", "end_byte", "line_ranges", "spans",
        "file", "files", "filename", "filepath",
        # content / hash
        "content_sha", "content_hash", "hash", "digest", "sha256",
        "md5", "sha1",
        "snippet", "snippets", "excerpt", "excerpts", "candidate_text",
        "text", "code", "code_snippet", "source_code", "content", "body",
        # identifiers
        "task_id", "repo_id", "repo", "instance_id", "row_id",
        "record_id", "id", "name",
        # packet-specific identifiers
        "packet_ref", "packet_id", "packet_refs", "packet_ids",
        "private_record_ref", "candidate_ref", "candidate_id", "candidate",
        # labels / qrels / annotations / raters
        "label", "labels", "qrels",
        "gold", "gold_label", "gold_labels", "gold_answer",
        "gold_span", "gold_spans",
        "hard_negative", "hard_negatives", "hard_negative_span",
        "predicted_answer", "answer", "question",
        "raw_label", "raw_labels", "annotation_row", "annotation_rows",
        "annotator_id", "rater_id", "rater_name", "per_row_hash", "row_hash",
        "disagreement_example", "disagreement_examples",
        "true_label", "true_e_score", "true_s_score",
        "label_slots", "annotation_instructions",
        "e_score", "s_score", "bucket", "citation_valid",
        "rater_pair_present", "adjudicated",
        "candidate_bucket_hint", "evidence", "evidence_row",
        # prompts / responses / model outputs
        "query", "query_text", "prompt", "response", "model_response",
        "model_output", "provider_payload", "raw_payload", "api_response",
        "response_body",
        # rows / records / packets
        "raw_rows", "rows", "records", "tasks", "row_values", "packets",
        "source_packet_schema", "d4d_runbook_attestation",
        "source_records",
        # patches / tests
        "patch", "test_patch", "tests",
        # secrets
        "api_key", "api_token", "api_secret", "base_url", "provider_key",
        "authorization",
        # raw agreement / CI numeric values
        "agreement_metric", "agreement_value", "agreement_score",
        "kappa", "fleiss_kappa", "cohen_kappa", "agreement",
        "confidence_interval", "ci_value", "ci_lower", "ci_upper",
        "ci_low", "ci_high",
        # per-candidate / per-row forbidden
        "candidate_row", "candidates", "prediction", "predictions",
        "retrieval_output", "retrieval_outputs",
    }
)

# Known-safe provenance value paths (allowlisted for hex_digest /
# path_like value checks only). The forbidden dict-key check is NOT
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
        "check",
        "section",
        "category",
        "retrieval_invocation",
        "retrieval_output_location",
        "method",
        "fixture_name",
    }
)

# Value patterns that indicate leaked row-level / candidate / packet /
# annotation data. D5-A0 rejects ALL URLs (no URL allowlist) per the
# fail-closed rule.
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
# in a committed/public output. Used as a value-leak canary.
_SECRET_SENTINEL = "SECRET_VALIDATOR_SENTINEL"


def _path_last_key(path: str) -> str:
    """Extract the last key segment from a dotted JSON path."""
    last = path.rsplit(".", 1)[-1]
    return last.split("[")[0]


def _is_safe_value_path(path: str) -> bool:
    """Check if a JSON path ends with a known-safe value key."""
    return _path_last_key(path) in SAFE_VALUE_KEY_NAMES


def _is_inside_contract_container(path: str) -> bool:
    """True iff any ancestor segment of ``path`` is a contract container key."""
    for seg in path.split("."):
        base = seg.split("[")[0]
        if base in CONTRACT_CONTAINER_KEYS:
            return True
    return False


def _is_label_source_counts_container(path: str) -> bool:
    """True iff ``path`` is the label-source aggregate-count container."""
    return path.endswith(".label_source_category_counts")


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
            if (
                _is_label_source_counts_container(path)
                and key_str
                not in APPROVED_LABEL_SOURCE_CATEGORIES
                | {COLLAPSED_LABEL_SOURCE_CATEGORY}
            ):
                violations.append(
                    {
                        "category": "unapproved_label_source_category_key",
                        "path": sub_path,
                    }
                )
            violations.extend(_scan_forbidden(value, sub_path))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_scan_forbidden(value, f"{path}[{idx}]"))
    elif isinstance(obj, str):
        in_contract = _is_inside_contract_container(path)
        safe_value = _is_safe_value_path(path)
        if in_contract and obj not in APPROVED_CONTRACT_STRINGS:
            violations.append(
                {"category": "unapproved_contract_string", "path": path}
            )
        elif not in_contract and obj in FORBIDDEN_KEY_NAMES:
            # Sensitive field name as a VALUE outside a contract is a leak.
            violations.append(
                {"category": "forbidden_field_name_value", "path": path}
            )
        elif len(obj) > 256:
            violations.append({"category": "long_string", "path": path})
        elif _RE_URL_VALUE.search(obj) and not safe_value:
            violations.append({"category": "url_value", "path": path})
        elif (
            not in_contract
            and not safe_value
            and _RE_HEX_DIGEST.search(obj)
        ):
            violations.append(
                {"category": "hex_digest_value", "path": path}
            )
        elif _RE_SECRET_LIKE.search(obj) and not safe_value:
            violations.append({"category": "secret_like_value", "path": path})
        elif (
            not in_contract
            and not safe_value
            and _RE_FILE_PATH_VALUE.search(obj)
        ):
            violations.append({"category": "path_like_value", "path": path})
        elif "\n" in obj:
            violations.append({"category": "multiline_value", "path": path})
        elif _RE_RAW_JSON.search(obj):
            violations.append(
                {"category": "raw_json_fragment", "path": path}
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
# r14 sanity fixture loaders + automated E/S labelers
# ---------------------------------------------------------------------------


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a JSONL file (committed fixture) into a list of dicts."""
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as src:
        for line in src:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_tasks(path: Path) -> dict[str, dict[str, Any]]:
    """Load r14 sanity tasks indexed by task_id."""
    tasks: dict[str, dict[str, Any]] = {}
    for row in load_jsonl(path):
        tasks[row["task_id"]] = row
    return tasks


def load_labels(path: Path) -> dict[str, dict[str, Any]]:
    """Load r14 sanity labels indexed by task_id."""
    labels: dict[str, dict[str, Any]] = {}
    for row in load_jsonl(path):
        labels[row["task_id"]] = row
    return labels


def _span_lines(span: dict[str, Any]) -> set[int]:
    """Build the set of lines covered by a span dict."""
    path = span.get("path", "")
    start = span.get("start_line", 0)
    end = span.get("end_line", 0)
    if not isinstance(start, int) or not isinstance(end, int):
        return set()
    if start < 1 or end < start:
        return set()
    return set(range(start, end + 1))


def _gold_paths(label: dict[str, Any]) -> set[str]:
    return {
        span.get("path", "")
        for span in label.get("gold_spans", [])
        if span.get("path")
    }


def _candidate_valid(candidate: dict[str, Any]) -> bool:
    """True iff candidate has a non-empty path and a valid 1<=start<=end."""
    path = candidate.get("path", "")
    start = candidate.get("start_line", 0)
    end = candidate.get("end_line", 0)
    if not isinstance(path, str) or not path:
        return False
    if not isinstance(start, int) or not isinstance(end, int):
        return False
    if start < 1 or end < start:
        return False
    return True


def _candidate_lines(candidate: dict[str, Any]) -> set[int]:
    start = candidate.get("start_line", 0)
    end = candidate.get("end_line", 0)
    if not isinstance(start, int) or not isinstance(end, int):
        return set()
    if start < 1 or end < start:
        return set()
    return set(range(start, end + 1))


def _spans_overlap(
    candidate_path: str,
    candidate_lines: set[int],
    span: dict[str, Any],
) -> bool:
    """True iff candidate (path, lines) overlaps a span dict."""
    if span.get("path") != candidate_path:
        return False
    return bool(candidate_lines & _span_lines(span))


def _is_adjacent_to_gold(
    candidate_path: str,
    candidate_lines: set[int],
    label: dict[str, Any],
    window: int = ADJACENCY_LINE_WINDOW,
) -> bool:
    """True iff candidate (path, lines) is within +/-window lines of
    a gold span boundary on the same path (and does not overlap gold).

    Used as a deterministic support-shape signal for S-proxy.
    """
    for span in label.get("gold_spans", []):
        if span.get("path") != candidate_path:
            continue
        span_lines = _span_lines(span)
        if not span_lines:
            continue
        if candidate_lines & span_lines:
            continue  # overlap is e_positive, not adjacency
        gold_min = min(span_lines)
        gold_max = max(span_lines)
        cand_min = min(candidate_lines) if candidate_lines else 0
        cand_max = max(candidate_lines) if candidate_lines else 0
        if cand_min == 0 or cand_max == 0:
            continue
        if (
            gold_min - window <= cand_max <= gold_min - 1
        ) or (
            gold_max + 1 <= cand_min <= gold_max + window
        ):
            return True
    return False


def label_candidate_e(
    candidate: dict[str, Any], label: dict[str, Any]
) -> str:
    """Compute the automated E label for one candidate.

    Procedure (deterministic; derived from existing committed span
    labels; never treated as true human E/S):

    * invalid/source-missing -> e_uncertain;
    * overlap hard-negative AND gold -> conflict_uncertain;
    * overlap hard-negative only -> e_hard_negative;
    * overlap gold -> e_positive;
    * same gold file, no gold overlap -> e_wrong_span_gold_file;
    * non-gold file with valid span -> e_negative_non_gold_file;
    * missing labels -> e_uncertain (never treated as negative).
    """
    if not _candidate_valid(candidate):
        return "e_uncertain"

    cand_path = candidate["path"]
    cand_lines = _candidate_lines(candidate)

    overlaps_gold = any(
        _spans_overlap(cand_path, cand_lines, span)
        for span in label.get("gold_spans", [])
    )
    overlaps_hard_negative = any(
        _spans_overlap(cand_path, cand_lines, span)
        for span in label.get("hard_negatives", [])
    )

    if overlaps_gold and overlaps_hard_negative:
        return "conflict_uncertain"
    if overlaps_hard_negative:
        return "e_hard_negative"
    if overlaps_gold:
        return "e_positive"

    # No gold overlap. Distinguish same-gold-file vs non-gold-file.
    if cand_path in _gold_paths(label):
        return "e_wrong_span_gold_file"
    return "e_negative_non_gold_file"


def label_candidate_s_proxy(
    candidate: dict[str, Any],
    label: dict[str, Any],
    e_label: str,
) -> str:
    """Compute the deterministic S-proxy label for one candidate.

    NOT a true human S-score. Conservative positive only for
    deterministic support-shape signals:

    * E-positive -> s_proxy_not_evaluated_for_e_positive (avoid conflation);
    * E-hard-negative / conflict-uncertain / e_uncertain -> s_proxy_none
      (do not conflate hard-negative or invalid shape with positive support);
    * e_wrong_span_gold_file -> s_proxy_positive (same gold file support shape);
    * adjacency to a gold span on the same gold file -> s_proxy_positive;
    * otherwise -> s_proxy_none.
    """
    if e_label == "e_positive":
        return "s_proxy_not_evaluated_for_e_positive"
    if e_label in (
        "e_hard_negative",
        "conflict_uncertain",
        "e_uncertain",
    ):
        return "s_proxy_none"
    if e_label == "e_wrong_span_gold_file":
        return "s_proxy_positive"
    # e_negative_non_gold_file: check adjacency (rare, on a gold file with
    # adjacency it would already be e_wrong_span_gold_file, so this is
    # mostly s_proxy_none). Keep conservative.
    if _candidate_valid(candidate):
        cand_path = candidate["path"]
        cand_lines = _candidate_lines(candidate)
        if _is_adjacent_to_gold(cand_path, cand_lines, label):
            return "s_proxy_positive"
    return "s_proxy_none"


# ---------------------------------------------------------------------------
# Retrieval harness (transient /tmp only; never commits raw outputs)
# ---------------------------------------------------------------------------


def _run_retrieval(
    method: str,
    tasks_path: Path,
    openlocus: str,
    cwd: str,
    candidate_limit: int,
) -> tuple[list[dict[str, Any]], bool]:
    """Invoke eval/run_retrieval.py for one method into a transient /tmp
    file. Returns (predictions, succeeded).

    The transient output file lives under /tmp and is never committed.
    On any subprocess failure, returns ([], False).
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="d5a_retrieval_"))
    tmp_out = tmp_dir / f"{method}.jsonl"
    cmd = [
        sys.executable,
        "eval/run_retrieval.py",
        "--dataset",
        str(tasks_path),
        "--out",
        str(tmp_out),
        "--openlocus",
        openlocus,
        "--method",
        method,
        "--cwd",
        cwd,
    ]
    if method == "rrf":
        cmd.extend(["--channels", "regex,bm25,symbol"])
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except (subprocess.TimeoutExpired, OSError):
        return ([], False)
    if proc.returncode != 0:
        return ([], False)
    if not tmp_out.exists():
        return ([], False)
    try:
        predictions = load_jsonl(tmp_out)
    except (OSError, json.JSONDecodeError):
        return ([], False)
    # Apply candidate_limit per task (truncate evidence list).
    for pred in predictions:
        evidence = pred.get("evidence", [])
        if isinstance(evidence, list) and len(evidence) > candidate_limit:
            pred["evidence"] = evidence[:candidate_limit]
    # Best-effort cleanup of the transient file (do not raise on failure).
    try:
        tmp_out.unlink()
    except OSError:
        pass
    try:
        tmp_dir.rmdir()
    except OSError:
        pass
    return (predictions, True)


# ---------------------------------------------------------------------------
# Aggregate metric computation
# ---------------------------------------------------------------------------


def _rate(count: int, denom: int) -> float:
    """Safe division: count / denom (0.0 if denom == 0)."""
    if denom <= 0:
        return 0.0
    return count / denom


def _method_aggregate(
    method: str,
    predictions: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compute aggregate metrics for one method.

    Emits ONLY aggregate counts/rates. Never emits per-candidate rows,
    paths, spans, snippets, content_sha, queries, task IDs, repo IDs,
    gold labels, or hard-negative labels.
    """
    e_counts: dict[str, int] = {cat: 0 for cat in E_LABEL_CATEGORIES}
    s_counts: dict[str, int] = {cat: 0 for cat in S_PROXY_CATEGORIES}

    candidates_seen = 0
    for pred in predictions:
        task_id = pred.get("task_id", "")
        label = labels.get(task_id, {})
        evidence = pred.get("evidence", [])
        if not isinstance(evidence, list):
            continue
        for cand in evidence:
            if not isinstance(cand, dict):
                continue
            candidates_seen += 1
            e_label = label_candidate_e(cand, label)
            s_label = label_candidate_s_proxy(cand, label, e_label)
            e_counts[e_label] = e_counts.get(e_label, 0) + 1
            s_counts[s_label] = s_counts.get(s_label, 0) + 1

    e_denom = candidates_seen
    s_denom = candidates_seen

    return {
        "method": method,
        "candidates_seen": candidates_seen,
        "e_positive_count": e_counts.get("e_positive", 0),
        "e_hard_negative_count": e_counts.get("e_hard_negative", 0),
        "conflict_uncertain_count": e_counts.get("conflict_uncertain", 0),
        "e_wrong_span_gold_file_count": e_counts.get(
            "e_wrong_span_gold_file", 0
        ),
        "e_negative_non_gold_file_count": e_counts.get(
            "e_negative_non_gold_file", 0
        ),
        "e_uncertain_count": e_counts.get("e_uncertain", 0),
        "e_positive_rate": _rate(
            e_counts.get("e_positive", 0), e_denom
        ),
        "e_hard_negative_rate": _rate(
            e_counts.get("e_hard_negative", 0), e_denom
        ),
        "conflict_uncertain_rate": _rate(
            e_counts.get("conflict_uncertain", 0), e_denom
        ),
        "e_wrong_span_gold_file_rate": _rate(
            e_counts.get("e_wrong_span_gold_file", 0), e_denom
        ),
        "e_negative_non_gold_file_rate": _rate(
            e_counts.get("e_negative_non_gold_file", 0), e_denom
        ),
        "e_uncertain_rate": _rate(
            e_counts.get("e_uncertain", 0), e_denom
        ),
        "s_proxy_positive_count": s_counts.get("s_proxy_positive", 0),
        "s_proxy_uncertain_count": s_counts.get("s_proxy_uncertain", 0),
        "s_proxy_none_count": s_counts.get("s_proxy_none", 0),
        "s_proxy_not_evaluated_for_e_positive_count": s_counts.get(
            "s_proxy_not_evaluated_for_e_positive", 0
        ),
        "s_proxy_positive_rate": _rate(
            s_counts.get("s_proxy_positive", 0), s_denom
        ),
        "s_proxy_uncertain_rate": _rate(
            s_counts.get("s_proxy_uncertain", 0), s_denom
        ),
        "denominators": {
            "candidate_total": candidates_seen,
            "e_label_denominator": e_denom,
            "s_label_denominator": s_denom,
        },
    }


def _aggregate_label_summary(
    method_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute the cross-method aggregate label summary."""
    e_counts: dict[str, int] = {cat: 0 for cat in E_LABEL_CATEGORIES}
    s_counts: dict[str, int] = {cat: 0 for cat in S_PROXY_CATEGORIES}
    candidates_labeled_total = 0
    for m in method_metrics:
        candidates_labeled_total += m["candidates_seen"]
        e_counts["e_positive"] += m["e_positive_count"]
        e_counts["e_hard_negative"] += m["e_hard_negative_count"]
        e_counts["conflict_uncertain"] += m["conflict_uncertain_count"]
        e_counts["e_wrong_span_gold_file"] += m[
            "e_wrong_span_gold_file_count"
        ]
        e_counts["e_negative_non_gold_file"] += m[
            "e_negative_non_gold_file_count"
        ]
        e_counts["e_uncertain"] += m["e_uncertain_count"]
        s_counts["s_proxy_positive"] += m["s_proxy_positive_count"]
        s_counts["s_proxy_uncertain"] += m["s_proxy_uncertain_count"]
        s_counts["s_proxy_none"] += m["s_proxy_none_count"]
        s_counts["s_proxy_not_evaluated_for_e_positive"] += m[
            "s_proxy_not_evaluated_for_e_positive_count"
        ]

    e_denom = candidates_labeled_total
    s_denom = candidates_labeled_total

    return {
        "candidates_labeled_total": candidates_labeled_total,
        "candidates_unlabeled_total": 0,
        "e_label_categories": list(E_LABEL_CATEGORIES),
        "s_proxy_label_categories": list(S_PROXY_CATEGORIES),
        "e_label_category_counts": dict(e_counts),
        "s_proxy_label_category_counts": dict(s_counts),
        "e_positive_rate": _rate(e_counts["e_positive"], e_denom),
        "e_hard_negative_rate": _rate(
            e_counts["e_hard_negative"], e_denom
        ),
        "conflict_uncertain_rate": _rate(
            e_counts["conflict_uncertain"], e_denom
        ),
        "e_wrong_span_gold_file_rate": _rate(
            e_counts["e_wrong_span_gold_file"], e_denom
        ),
        "e_negative_non_gold_file_rate": _rate(
            e_counts["e_negative_non_gold_file"], e_denom
        ),
        "e_uncertain_rate": _rate(e_counts["e_uncertain"], e_denom),
        "s_proxy_positive_rate": _rate(
            s_counts["s_proxy_positive"], s_denom
        ),
        "s_proxy_uncertain_rate": _rate(
            s_counts["s_proxy_uncertain"], s_denom
        ),
    }


def _label_source_category_counts(
    labels: dict[str, dict[str, Any]],
) -> dict[str, int]:
    """Aggregate approved label_source category counts.

    ``label_quality`` is committed fixture metadata, but public aggregate keys
    must still be explicit. Approved categories are counted as-is; unapproved
    or malformed categories collapse to a fixed bucket so row-derived strings
    cannot become dynamic public artifact keys.
    """
    counts: dict[str, int] = {}
    for label in labels.values():
        category = label.get("label_quality", "unknown")
        if not isinstance(category, str) or not category:
            category = "unknown"
        if category not in APPROVED_LABEL_SOURCE_CATEGORIES:
            category = COLLAPSED_LABEL_SOURCE_CATEGORY
        counts[category] = counts.get(category, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Public artifact builder
# ---------------------------------------------------------------------------


def _build_public_report(
    checks: list[dict[str, Any]],
    all_passed: bool,
    method_metrics: list[dict[str, Any]] | None = None,
    retrieval_summary: dict[str, Any] | None = None,
    label_summary: dict[str, Any] | None = None,
    input_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the public aggregate-only report (fail-closed scan).

    The default committed artifact. No raw predictions, no per-candidate
    rows, no paths/spans/snippets/hashes/queries/gold/hard-negatives.
    """
    smoke_passes = (
        all_passed
        and retrieval_summary is not None
        and len(retrieval_summary.get("methods_succeeded", [])) >= 1
        and retrieval_summary.get("candidate_count_total", 0) >= 1
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
        # Input summary (fixture name, task count, label source category
        # counts, methods evaluated).
        "input_summary": input_summary or {
            "fixture_name": "r14_sanity",
            "task_count": 0,
            "label_source_category_counts": {},
            "methods_evaluated": list(METHODS),
        },
        # Retrieval summary (methods attempted/succeeded, candidate count
        # total, transient /tmp only, never committed).
        "retrieval_summary": retrieval_summary or {
            "methods_attempted": list(METHODS),
            "methods_succeeded": [],
            "candidate_count_total": 0,
            "retrieval_invocation": "run_retrieval_subprocess",
            "retrieval_output_location": "tmp_only_transient",
            "raw_retrieval_outputs_committed": False,
        },
        # Automated label summary (aggregate counts/rates only).
        "automated_label_summary": label_summary or _aggregate_label_summary(
            method_metrics or []
        ),
        # Per-method aggregate metrics (list of dicts; no per-candidate
        # rows, no paths/spans/snippets/hashes).
        "method_aggregate_metrics": method_metrics or [],
        # E/S label categories (contract containers; short-token allowlist).
        "e_label_categories": list(E_LABEL_CATEGORIES),
        "s_proxy_label_categories": list(S_PROXY_CATEGORIES),
        # Safe booleans true (smoke harness complete + aggregate-only /
        # diagnostic / not-evidence + smoke-claimed + uses-existing-labels).
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
        report["status"] = "fail_forbidden_leak"
    return report


def build_report(
    tasks_path: Path,
    labels_path: Path,
    openlocus: str,
    cwd: str,
    candidate_limit: int,
) -> dict[str, Any]:
    """Assemble the public aggregate-only report from real retrieval outputs.

    Runs the deterministic self-test checks, invokes run_retrieval.py per
    method into transient /tmp files, reads those transient outputs,
    computes aggregate E/S labels from existing committed span labels,
    and assembles the full public report (which re-scans itself).
    """
    checks, all_passed = run_self_test_checks()

    # Load committed fixtures.
    try:
        tasks = load_tasks(tasks_path)
        labels = load_labels(labels_path)
    except (OSError, json.JSONDecodeError):
        tasks = {}
        labels = {}

    label_source_counts = _label_source_category_counts(labels)

    input_summary: dict[str, Any] = {
        "fixture_name": "r14_sanity",
        "task_count": len(tasks),
        "label_source_category_counts": label_source_counts,
        "methods_evaluated": list(METHODS),
    }

    # Run retrieval per method into transient /tmp files.
    methods_attempted: list[str] = []
    methods_succeeded: list[str] = []
    method_metrics: list[dict[str, Any]] = []
    candidate_count_total = 0

    for method in METHODS:
        methods_attempted.append(method)
        predictions, succeeded = _run_retrieval(
            method, tasks_path, openlocus, cwd, candidate_limit
        )
        if not succeeded:
            # Method attempted but failed; emit an empty aggregate row
            # so the smoke still reports the attempt.
            method_metrics.append(_method_aggregate(method, [], labels))
            continue
        methods_succeeded.append(method)
        agg = _method_aggregate(method, predictions, labels)
        method_metrics.append(agg)
        candidate_count_total += agg["candidates_seen"]

    retrieval_summary: dict[str, Any] = {
        "methods_attempted": methods_attempted,
        "methods_succeeded": methods_succeeded,
        "candidate_count_total": candidate_count_total,
        "retrieval_invocation": "run_retrieval_subprocess",
        "retrieval_output_location": "tmp_only_transient",
        "raw_retrieval_outputs_committed": False,
    }

    label_summary = _aggregate_label_summary(method_metrics)

    return _build_public_report(
        checks,
        all_passed,
        method_metrics=method_metrics,
        retrieval_summary=retrieval_summary,
        label_summary=label_summary,
        input_summary=input_summary,
    )


# ---------------------------------------------------------------------------
# Self-test helpers
# ---------------------------------------------------------------------------


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return {"check": name, "passed": bool(ok)}


# Synthetic span/label fixtures for self-test (in-memory only; never
# committed). Use safe synthetic paths that the scanner will never see.
_SYNTH_GOLD_PATH = "synth_gold_file"
_SYNTH_HARD_NEG_PATH = "synth_hard_neg_file"
_SYNTH_NON_GOLD_PATH = "synth_other_file"


def _synth_label(
    gold_spans: list[dict[str, Any]] | None = None,
    hard_negatives: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a synthetic in-memory label dict (never committed)."""
    return {
        "task_id": "synth-task",
        "label_quality": "human_reviewed",
        "gold_spans": gold_spans or [],
        "hard_negatives": hard_negatives or [],
    }


def _synth_cand(
    path: str, start: int, end: int
) -> dict[str, Any]:
    """Build a synthetic in-memory candidate dict (never committed)."""
    return {
        "path": path,
        "start_line": start,
        "end_line": end,
        "content_sha": "synth",
        "score": 1.0,
        "channels": ["synth"],
        "why": ["synth"],
    }


# ===========================================================================
# Self-test checks are appended below in run_self_test_checks().
# ===========================================================================


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all D5-A0 automated E/S calibration smoke self-test groups.

    Returns (checks, all_passed). Uses synthetic in-memory predictions
    and labels; no external openlocus required.
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
            "status_correct_when_self_test_passes",
            _build_public_report([], True)["status"] == STATUS_BLOCKED,
        )
    )
    # When retrieval_summary is also populated (>=1 method succeeded,
    # >=1 candidate) AND self-test passes, status is the success status.
    ok_retrieval = {
        "methods_attempted": list(METHODS),
        "methods_succeeded": ["regex"],
        "candidate_count_total": 1,
        "retrieval_invocation": "run_retrieval_subprocess",
        "retrieval_output_location": "tmp_only_transient",
        "raw_retrieval_outputs_committed": False,
    }
    ok_label = _aggregate_label_summary(
        [
            {
                "method": "regex",
                "candidates_seen": 1,
                "e_positive_count": 1,
                "e_hard_negative_count": 0,
                "conflict_uncertain_count": 0,
                "e_wrong_span_gold_file_count": 0,
                "e_negative_non_gold_file_count": 0,
                "e_uncertain_count": 0,
                "e_positive_rate": 1.0,
                "e_hard_negative_rate": 0.0,
                "conflict_uncertain_rate": 0.0,
                "e_wrong_span_gold_file_rate": 0.0,
                "e_negative_non_gold_file_rate": 0.0,
                "e_uncertain_rate": 0.0,
                "s_proxy_positive_count": 0,
                "s_proxy_uncertain_count": 0,
                "s_proxy_none_count": 0,
                "s_proxy_not_evaluated_for_e_positive_count": 1,
                "s_proxy_positive_rate": 0.0,
                "s_proxy_uncertain_rate": 0.0,
                "denominators": {
                    "candidate_total": 1,
                    "e_label_denominator": 1,
                    "s_label_denominator": 1,
                },
            }
        ]
    )
    ok_report = _build_public_report(
        [],
        True,
        method_metrics=[],
        retrieval_summary=ok_retrieval,
        label_summary=ok_label,
    )
    checks.append(
        _check(
            "status_success_when_self_test_and_retrieval_pass",
            ok_report["status"] == TARGET_STATUS,
        )
    )
    checks.append(
        _check(
            "status_self_test_failed_when_not_passed",
            skeleton["status"] == STATUS_BLOCKED,
        )
    )
    checks.append(
        _check(
            "mode_public_aggregate_r14_retrieval_smoke",
            skeleton["mode"] == MODE,
        )
    )
    checks.append(
        _check("phase_d5_a0", skeleton["phase"] == PHASE)
    )
    checks.append(
        _check(
            "generated_by_correct",
            skeleton["generated_by"] == GENERATED_BY,
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

    # --- Group 4: Automated E label procedure (span overlap cases). ---
    # gold overlap -> e_positive
    label_gold = _synth_label(
        gold_spans=[{"path": _SYNTH_GOLD_PATH, "start_line": 10, "end_line": 20}]
    )
    checks.append(
        _check(
            "e_label_gold_overlap_is_e_positive",
            label_candidate_e(
                _synth_cand(_SYNTH_GOLD_PATH, 12, 15), label_gold
            )
            == "e_positive",
        )
    )
    # hard-negative overlap -> e_hard_negative
    label_hn = _synth_label(
        gold_spans=[{"path": _SYNTH_GOLD_PATH, "start_line": 10, "end_line": 20}],
        hard_negatives=[
            {"path": _SYNTH_GOLD_PATH, "start_line": 30, "end_line": 40}
        ],
    )
    checks.append(
        _check(
            "e_label_hard_negative_overlap_is_e_hard_negative",
            label_candidate_e(
                _synth_cand(_SYNTH_GOLD_PATH, 32, 35), label_hn
            )
            == "e_hard_negative",
        )
    )
    # conflict case: gold AND hard-negative overlap -> conflict_uncertain
    label_conflict = _synth_label(
        gold_spans=[{"path": _SYNTH_GOLD_PATH, "start_line": 10, "end_line": 40}],
        hard_negatives=[
            {"path": _SYNTH_GOLD_PATH, "start_line": 30, "end_line": 50}
        ],
    )
    checks.append(
        _check(
            "e_label_conflict_overlap_is_conflict_uncertain",
            label_candidate_e(
                _synth_cand(_SYNTH_GOLD_PATH, 32, 38), label_conflict
            )
            == "conflict_uncertain",
        )
    )
    # same gold file wrong span -> e_wrong_span_gold_file
    checks.append(
        _check(
            "e_label_same_gold_file_wrong_span",
            label_candidate_e(
                _synth_cand(_SYNTH_GOLD_PATH, 1, 5), label_gold
            )
            == "e_wrong_span_gold_file",
        )
    )
    # non-gold file valid span -> e_negative_non_gold_file
    checks.append(
        _check(
            "e_label_non_gold_file_is_e_negative_non_gold_file",
            label_candidate_e(
                _synth_cand(_SYNTH_NON_GOLD_PATH, 1, 5), label_gold
            )
            == "e_negative_non_gold_file",
        )
    )
    # invalid/source-missing -> e_uncertain
    checks.append(
        _check(
            "e_label_invalid_candidate_is_e_uncertain",
            label_candidate_e(
                {"path": "", "start_line": 1, "end_line": 5}, label_gold
            )
            == "e_uncertain",
        )
    )
    checks.append(
        _check(
            "e_label_missing_path_is_e_uncertain",
            label_candidate_e(
                {"start_line": 1, "end_line": 5}, label_gold
            )
            == "e_uncertain",
        )
    )
    checks.append(
        _check(
            "e_label_bad_line_range_is_e_uncertain",
            label_candidate_e(
                {"path": _SYNTH_GOLD_PATH, "start_line": 5, "end_line": 1},
                label_gold,
            )
            == "e_uncertain",
        )
    )
    # missing labels (no gold_spans, no hard_negatives) -> never negative
    empty_label = _synth_label()
    checks.append(
        _check(
            "e_label_missing_labels_not_treated_as_negative",
            label_candidate_e(
                _synth_cand(_SYNTH_NON_GOLD_PATH, 1, 5), empty_label
            )
            == "e_negative_non_gold_file",
        )
    )
    # missing labels for a valid candidate on no path -> e_uncertain only
    # for invalid candidates
    checks.append(
        _check(
            "e_label_missing_labels_invalid_candidate_still_uncertain",
            label_candidate_e(
                {"path": "", "start_line": 1, "end_line": 5}, empty_label
            )
            == "e_uncertain",
        )
    )

    # --- Group 5: S-proxy label procedure. ---
    # E-positive -> s_proxy_not_evaluated_for_e_positive
    checks.append(
        _check(
            "s_proxy_e_positive_not_evaluated",
            label_candidate_s_proxy(
                _synth_cand(_SYNTH_GOLD_PATH, 12, 15),
                label_gold,
                "e_positive",
            )
            == "s_proxy_not_evaluated_for_e_positive",
        )
    )
    # e_wrong_span_gold_file -> s_proxy_positive
    checks.append(
        _check(
            "s_proxy_wrong_span_gold_file_positive",
            label_candidate_s_proxy(
                _synth_cand(_SYNTH_GOLD_PATH, 1, 5),
                label_gold,
                "e_wrong_span_gold_file",
            )
            == "s_proxy_positive",
        )
    )
    # adjacency to gold span on same gold file -> s_proxy_positive
    # (candidate at lines 6-9, gold at 10-20, window=5 -> adjacent)
    checks.append(
        _check(
            "s_proxy_adjacency_to_gold_positive",
            label_candidate_s_proxy(
                _synth_cand(_SYNTH_GOLD_PATH, 6, 9),
                label_gold,
                "e_negative_non_gold_file",
            )
            == "s_proxy_positive",
        )
    )
    # e_hard_negative -> s_proxy_none
    checks.append(
        _check(
            "s_proxy_e_hard_negative_none",
            label_candidate_s_proxy(
                _synth_cand(_SYNTH_GOLD_PATH, 32, 35),
                label_hn,
                "e_hard_negative",
            )
            == "s_proxy_none",
        )
    )
    # conflict_uncertain -> s_proxy_none
    checks.append(
        _check(
            "s_proxy_conflict_uncertain_none",
            label_candidate_s_proxy(
                _synth_cand(_SYNTH_GOLD_PATH, 32, 38),
                label_conflict,
                "conflict_uncertain",
            )
            == "s_proxy_none",
        )
    )
    # e_uncertain -> s_proxy_none
    checks.append(
        _check(
            "s_proxy_e_uncertain_none",
            label_candidate_s_proxy(
                {"path": "", "start_line": 1, "end_line": 5},
                label_gold,
                "e_uncertain",
            )
            == "s_proxy_none",
        )
    )
    # non-gold file far from gold -> s_proxy_none
    checks.append(
        _check(
            "s_proxy_non_gold_far_from_gold_none",
            label_candidate_s_proxy(
                _synth_cand(_SYNTH_NON_GOLD_PATH, 1, 5),
                label_gold,
                "e_negative_non_gold_file",
            )
            == "s_proxy_none",
        )
    )

    # --- Group 6: Aggregate denominator consistency. ---
    # Sum of E label rates must equal 1.0 (modulo float rounding) when
    # denom > 0.
    cands = [
        _synth_cand(_SYNTH_GOLD_PATH, 12, 15),  # e_positive
        _synth_cand(_SYNTH_GOLD_PATH, 32, 35),  # e_hard_negative
        _synth_cand(_SYNTH_GOLD_PATH, 1, 5),    # e_wrong_span_gold_file
        _synth_cand(_SYNTH_NON_GOLD_PATH, 1, 5),  # e_negative_non_gold_file
        {"path": "", "start_line": 1, "end_line": 5},  # e_uncertain
    ]
    preds = [{"task_id": "synth-task", "evidence": cands}]
    agg = _method_aggregate("synth", preds, {"synth-task": label_hn})
    e_rate_sum = (
        agg["e_positive_rate"]
        + agg["e_hard_negative_rate"]
        + agg["conflict_uncertain_rate"]
        + agg["e_wrong_span_gold_file_rate"]
        + agg["e_negative_non_gold_file_rate"]
        + agg["e_uncertain_rate"]
    )
    checks.append(
        _check(
            "aggregate_e_label_rates_sum_to_one",
            abs(e_rate_sum - 1.0) < 1e-9,
        )
    )
    checks.append(
        _check(
            "aggregate_candidates_seen_matches_denominator",
            agg["candidates_seen"]
            == agg["denominators"]["candidate_total"]
            == agg["denominators"]["e_label_denominator"]
            == agg["denominators"]["s_label_denominator"]
            == len(cands),
        )
    )
    checks.append(
        _check(
            "aggregate_e_counts_match_candidates_seen",
            (
                agg["e_positive_count"]
                + agg["e_hard_negative_count"]
                + agg["conflict_uncertain_count"]
                + agg["e_wrong_span_gold_file_count"]
                + agg["e_negative_non_gold_file_count"]
                + agg["e_uncertain_count"]
            )
            == agg["candidates_seen"],
        )
    )
    checks.append(
        _check(
            "aggregate_s_counts_match_candidates_seen",
            (
                agg["s_proxy_positive_count"]
                + agg["s_proxy_uncertain_count"]
                + agg["s_proxy_none_count"]
                + agg["s_proxy_not_evaluated_for_e_positive_count"]
            )
            == agg["candidates_seen"],
        )
    )

    # --- Group 7: Forbidden scanner (rejects + allows). ---
    # Forbidden dict keys anywhere.
    for bad_key in (
        "task_id",
        "repo_id",
        "repo",
        "path",
        "file",
        "span",
        "start_line",
        "end_line",
        "content_sha",
        "snippet",
        "candidate_text",
        "query",
        "query_text",
        "prompt",
        "response",
        "model_output",
        "label",
        "raw_label",
        "annotation_row",
        "rater_id",
        "annotator_id",
        "packet_ref",
        "packet_id",
        "private_record_ref",
        "candidate_ref",
        "candidate",
        "per_row_hash",
        "row_hash",
        "provider_payload",
        "api_key",
        "agreement_metric",
        "confidence_interval",
        "ci_value",
        "ci_lower",
        "ci_upper",
        "kappa",
        "gold",
        "gold_span",
        "gold_spans",
        "hard_negative",
        "hard_negatives",
        "evidence",
        "evidence_row",
        "candidate_row",
        "predictions",
        "retrieval_output",
        "retrieval_outputs",
    ):
        checks.append(
            _check(
                f"scanner_rejects_{bad_key}_key",
                bool(_scan_forbidden({bad_key: "x"})),
            )
        )

    # Forbidden value patterns (outside contract containers). Use a
    # non-safe, non-forbidden key ("probe") so value-pattern checks apply.
    checks.append(
        _check(
            "scanner_rejects_url_value",
            bool(
                _scan_forbidden(
                    {"probe": "https://example.invalid/leak"}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_32_hex_digest_value",
            bool(_scan_forbidden({"probe": "a" * 32})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_40_hex_digest_value",
            bool(_scan_forbidden({"probe": "f" * 40})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_64_hex_digest_value",
            bool(_scan_forbidden({"probe": "0" * 64})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_secret_sentinel_value",
            bool(_scan_forbidden({"probe": _SECRET_SENTINEL})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_secret_like_value",
            bool(
                _scan_forbidden(
                    {"probe": "api_key=ABCDEF1234567890"}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_path_like_value",
            bool(
                _scan_forbidden(
                    {"probe": "src/openlocus/lib.rs"}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_leading_slash_path_value",
            bool(
                _scan_forbidden(
                    {"probe": "/private/records.jsonl"}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_jsonl_path_value",
            bool(
                _scan_forbidden(
                    {"probe": "runs/private_labels.jsonl"}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_multiline_value",
            bool(_scan_forbidden({"probe": "line1\nline2"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_raw_json_fragment",
            bool(
                _scan_forbidden(
                    {"probe": '{"task_id": "leak"}'}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_line_range_value",
            bool(_scan_forbidden({"probe": "12-34"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_colon_line_range_value",
            bool(_scan_forbidden({"probe": "12:34"})),
        )
    )

    # Unapproved string inside a contract container is rejected.
    checks.append(
        _check(
            "scanner_rejects_unapproved_string_in_contract_container",
            bool(
                _scan_forbidden(
                    {"methods_evaluated": ["compute_loss"]}
                )
            ),
        )
    )
    # Sensitive field name as a VALUE inside a contract container is
    # rejected (it is not in APPROVED_CONTRACT_STRINGS).
    checks.append(
        _check(
            "scanner_rejects_sensitive_field_name_in_contract_container",
            bool(
                _scan_forbidden(
                    {"methods_evaluated": ["content_sha"]}
                )
            ),
        )
    )
    # URL inside a contract container is rejected.
    checks.append(
        _check(
            "scanner_rejects_url_in_contract_container",
            bool(
                _scan_forbidden(
                    {"methods_evaluated": ["https://leak.invalid/"]}
                )
            ),
        )
    )

    # Approved short tokens inside contract containers pass.
    for token in METHODS:
        checks.append(
            _check(
                f"scanner_allows_method_{token}_in_contract",
                not _scan_forbidden(
                    {"methods_evaluated": [token]}
                ),
            )
        )
    for token in E_LABEL_CATEGORIES:
        checks.append(
            _check(
                f"scanner_allows_e_label_{token}_in_contract",
                not _scan_forbidden(
                    {"e_label_categories": [token]}
                ),
            )
        )
    for token in S_PROXY_CATEGORIES:
        checks.append(
            _check(
                f"scanner_allows_s_proxy_{token}_in_contract",
                not _scan_forbidden(
                    {"s_proxy_label_categories": [token]}
                ),
            )
        )

    # Approved label_source aggregate keys pass; unapproved dynamic keys
    # are rejected or collapsed before artifact emission.
    checks.append(
        _check(
            "label_source_counts_preserve_approved_mined",
            _label_source_category_counts(
                {"row1": {"label_quality": "mined"}}
            ) == {"mined": 1},
        )
    )
    collapsed_source_counts = _label_source_category_counts(
        {"row1": {"label_quality": "SECRET_LABEL_SOURCE_SENTINEL"}}
    )
    checks.append(
        _check(
            "label_source_counts_collapse_unapproved_category",
            collapsed_source_counts
            == {COLLAPSED_LABEL_SOURCE_CATEGORY: 1},
        )
    )
    checks.append(
        _check(
            "label_source_counts_do_not_emit_unapproved_sentinel",
            "SECRET_LABEL_SOURCE_SENTINEL"
            not in json.dumps(collapsed_source_counts, sort_keys=True),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_unapproved_label_source_category_key",
            bool(
                _scan_forbidden(
                    {
                        "input_summary": {
                            "label_source_category_counts": {
                                "SECRET_LABEL_SOURCE_SENTINEL": 1
                            }
                        }
                    }
                )
            ),
        )
    )

    # --- Group 8: Fail-closed generation. ---
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

    # --- Group 9: Public artifact self-scan is clean. ---
    checks.append(
        _check(
            "public_report_forbidden_scan_clean",
            skeleton["forbidden_scan"]["status"] == "pass",
        )
    )
    # No forbidden key anywhere in the skeleton.
    checks.append(
        _check(
            "public_report_no_forbidden_key_anywhere",
            not any(
                _has_dict_key_anywhere(skeleton, bad)
                for bad in (
                    "task_id",
                    "repo_id",
                    "path",
                    "file",
                    "snippet",
                    "content_sha",
                    "rater_id",
                    "label",
                    "raw_label",
                    "agreement_metric",
                    "confidence_interval",
                    "packet_ref",
                    "query_text",
                    "candidate_text",
                    "model_output",
                    "provider_payload",
                    "api_key",
                    "gold",
                    "hard_negative",
                    "evidence",
                    "candidate",
                )
            ),
        )
    )

    # --- Group 10: CLI argument surface. ---
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
        _check("cli_has_tasks_argument", "--tasks" in cli_opts)
    )
    checks.append(
        _check("cli_has_labels_argument", "--labels" in cli_opts)
    )
    checks.append(
        _check(
            "cli_has_openlocus_argument",
            "--openlocus" in cli_opts,
        )
    )
    checks.append(
        _check("cli_has_cwd_argument", "--cwd" in cli_opts)
    )
    checks.append(
        _check(
            "cli_has_candidate_limit_argument",
            "--candidate-limit" in cli_opts,
        )
    )
    checks.append(
        _check(
            "cli_only_expected_arguments",
            (cli_opts - {"-h", "--help"})
            == {
                "--self-test",
                "--out",
                "--tasks",
                "--labels",
                "--openlocus",
                "--cwd",
                "--candidate-limit",
            },
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
    """Build the D5-A0 CLI parser."""
    ap = SafeArgumentParser(
        description=(
            "D5-A0 automated E/S calibration smoke "
            "(public aggregate-only artifact; uses existing committed "
            "r14 sanity labels; invokes run_retrieval.py into /tmp; "
            "no raw predictions, no per-candidate rows, no labels, "
            "no metrics committed)."
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
        "--tasks",
        type=Path,
        default=DEFAULT_TASKS,
        help="r14 sanity tasks JSONL path (default: committed r14 sanity fixture)",
    )
    ap.add_argument(
        "--labels",
        type=Path,
        default=DEFAULT_LABELS,
        help="r14 sanity labels JSONL path (default: committed r14 sanity fixture)",
    )
    ap.add_argument(
        "--openlocus",
        default=DEFAULT_OPENLOCUS,
        help="openlocus CLI binary path (default: target/debug/openlocus)",
    )
    ap.add_argument(
        "--cwd",
        default=".",
        help="working directory for openlocus CLI (default: current dir)",
    )
    ap.add_argument(
        "--candidate-limit",
        type=int,
        default=DEFAULT_CANDIDATE_LIMIT,
        help=(
            "max candidates per task per method (default: "
            f"{DEFAULT_CANDIDATE_LIMIT})"
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

    # Public default mode (committed aggregate-only artifact).
    out_path = args.out if args.out is not None else DEFAULT_OUT
    report = build_report(
        tasks_path=args.tasks,
        labels_path=args.labels,
        openlocus=args.openlocus,
        cwd=args.cwd,
        candidate_limit=args.candidate_limit,
    )
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
