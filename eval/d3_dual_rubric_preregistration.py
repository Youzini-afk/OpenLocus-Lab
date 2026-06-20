#!/usr/bin/env python3
"""D3 Dual-Rubric Label Protocol Preregistration — protocol only, no labels.

This module implements the **D3 dual-rubric label protocol preregistration**.
D3 is the protocol-only bridge between D1 (deterministic rubric scaffold) and
D2 (proxy mappability), and a later D4 local/private true E/S calibration run.

D3 **preregisters** the future true E-score/S-score label collection and
calibration protocol. It does NOT collect labels, NOT read private records,
NOT compute calibration metrics, NOT measure inter-rater agreement, and NOT
change runtime behavior. It is a *preregistration* of the protocol only.

Claim boundary (binding):

* This is **eval/diagnostic protocol only**. It is NOT a runtime change, NOT
  a retriever/pack/model/backend/default-policy change, and NOT an
  EvidenceCore semantic change.
* Claim level emitted: ``dual_rubric_label_protocol_preregistration_only``.
* Rubric version: ``d3_true_dual_rubric_label_protocol_v1``.
* Status: ``protocol_ready_no_labels_collected``; mode ``protocol_only``.
* D3 collects NO labels, reads NO private records, computes NO calibration
  metrics, measures NO inter-rater agreement, claims NO true E/S calibration,
  claims NO proxy calibration, and collects NO model-assisted labels.

Public-artifact contract (binding):

* aggregate-only / protocol-only public output;
* NEVER emit task IDs, repo IDs/names, paths/spans/snippets, line/byte
  ranges, content hashes, raw candidate text, prompts/responses, model
  outputs, private labels, raw annotation rows, per-row hashes, exact
  private sample sizes, or local filesystem paths;
* a strict forbidden-output scanner runs fail-closed before the JSON
  artifact is written;
* no-claim / no-runtime-change flags all false;
  ``aggregate_only_public_artifact=true``, ``not_evidence=true``,
  ``diagnostic_only=true``.
* any examples are approved abstract category strings only (no concrete
  repo/path/snippet content).

Run::

    python3 -m py_compile eval/d3_dual_rubric_preregistration.py
    python3 eval/d3_dual_rubric_preregistration.py --self-test
    python3 eval/d3_dual_rubric_preregistration.py \
        --out artifacts/d3_dual_rubric_preregistration/\\
d3_dual_rubric_preregistration_report.json
    python3 scripts/validate_docs_i18n.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "d3_dual_rubric_preregistration.v1"
GENERATED_BY = "eval/d3_dual_rubric_preregistration.py"
CLAIM_LEVEL = "dual_rubric_label_protocol_preregistration_only"
RUBRIC_VERSION = "d3_true_dual_rubric_label_protocol_v1"
TARGET_STATUS = "protocol_ready_no_labels_collected"
MODE = "protocol_only"

DEFAULT_OUT = Path(
    "artifacts/d3_dual_rubric_preregistration/"
    "d3_dual_rubric_preregistration_report.json"
)

# ---------------------------------------------------------------------------
# Label-protocol false flags (all MUST be false in D3).
# ---------------------------------------------------------------------------

LABEL_PROTOCOL_FLAGS: dict[str, bool] = {
    "labels_collected": False,
    "private_records_read": False,
    "raw_private_records_read": False,
    "private_records_persisted": False,
    "true_e_s_calibration_claimed": False,
    "proxy_calibration_claimed": False,
    "model_assisted_labels_collected": False,
    "inter_rater_agreement_measured": False,
    "calibration_metrics_computed": False,
}

# ---------------------------------------------------------------------------
# No-claim / no-runtime-change flags (all MUST be false).
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Diagnostic flags (all MUST be true).
# ---------------------------------------------------------------------------

DIAGNOSTIC_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
    "not_evidence": True,
}

# ---------------------------------------------------------------------------
# Annotation rubric semantics (protocol definitions only; no row data).
# ---------------------------------------------------------------------------

# True E-score levels (semantic / direct-answer evidence). Ordinal scale.
E_SCORE_LEVELS: tuple[dict[str, str], ...] = (
    {"level": "E0", "definition": "no semantic or direct-answer evidence"},
    {
        "level": "E1",
        "definition": (
            "weak or partial semantic or direct-answer evidence"
        ),
    },
    {
        "level": "E2",
        "definition": (
            "strong semantic or direct-answer evidence with valid citation"
        ),
    },
)
E_LEVEL_NAMES: tuple[str, ...] = ("E0", "E1", "E2")

# True S-score levels (dependency / support-structure evidence).
S_SCORE_LEVELS: tuple[dict[str, str], ...] = (
    {
        "level": "S0",
        "definition": "no dependency or support-structure evidence",
    },
    {
        "level": "S1",
        "definition": (
            "weak or partial dependency or support-structure evidence"
        ),
    },
    {
        "level": "S2",
        "definition": "strong dependency or support-structure evidence",
    },
)
S_LEVEL_NAMES: tuple[str, ...] = ("S0", "S1", "S2")

# Bucket mapping (categories only; mirrors D1 bucket names).
BUCKET_PRIMARY_EVIDENCE = "primary_evidence"
BUCKET_DEPENDENCY_SUPPORT = "dependency_support"
BUCKET_WEAK_CANDIDATES = "weak_candidates"
BUCKET_ABSTAINED = "abstained"

BUCKET_MAPPING: tuple[dict[str, str], ...] = (
    {
        "bucket": BUCKET_PRIMARY_EVIDENCE,
        "mapping": "E2 with valid citation",
    },
    {
        "bucket": BUCKET_DEPENDENCY_SUPPORT,
        "mapping": "S2 with E below E2",
    },
    {
        "bucket": BUCKET_WEAK_CANDIDATES,
        "mapping": "nonzero E or S below high thresholds",
    },
    {
        "bucket": BUCKET_ABSTAINED,
        "mapping": "no evidence or abstention gate fired",
    },
)
BUCKET_NAMES: tuple[str, ...] = (
    BUCKET_PRIMARY_EVIDENCE,
    BUCKET_DEPENDENCY_SUPPORT,
    BUCKET_WEAK_CANDIDATES,
    BUCKET_ABSTAINED,
)

# Approved abstract example category strings ONLY. No concrete repo/path/
# snippet content. The self-test enforces that annotation_rubric
# abstract_examples EXACTLY matches this approved enum.
APPROVED_ABSTRACT_EXAMPLES: tuple[str, ...] = (
    "direct_definition_of_requested_symbol",
    "caller_import_relation_without_answer_bearing_text",
    "same_module_but_insufficient_evidence",
)

# Rubric-level definitions (protocol metadata, not row data).
RUBRIC_DEFINITIONS: dict[str, str] = {
    "abstention_gate": (
        "citation validity, staleness, uncited, or explicit no-evidence "
        "gate fires before E or S bucket assignment"
    ),
    "e_score_level_scale": (
        "E0, E1, E2 ordinal scale for semantic or direct-answer evidence"
    ),
    "s_score_level_scale": (
        "S0, S1, S2 ordinal scale for dependency or support-structure "
        "evidence"
    ),
}

# ---------------------------------------------------------------------------
# Sampling-frame protocol (category-only).
# ---------------------------------------------------------------------------

ELIGIBLE_RECORD_SOURCES: tuple[str, ...] = (
    "local_private_p21_records",
    "local_private_d2b_proxy_smoke_candidates",
)

SAMPLING_AXES: tuple[str, ...] = (
    "proxy_bucket",
    "proxy_e_band",
    "proxy_s_band",
    "abstain_or_unmappable_status",
)

STRATIFICATION_REQUIRED = True
MAX_RECORDS_PER_BATCH_LOCAL_ONLY = 50
RAW_RECORD_MATERIAL_PRIVATE_ONLY = True

# ---------------------------------------------------------------------------
# Future D4 execution gates (protocol only; D4 is a separate gated phase).
# ---------------------------------------------------------------------------

FUTURE_EXECUTION_GATES: dict[str, Any] = {
    "explicit_private_opt_in_required": True,
    "local_output_path_required": True,
    "output_location_category": "tmp_only_local_private",
    "no_committed_raw_labels": True,
    "k_min": 5,
    "min_total_labels": 50,
    "inter_rater_agreement_required": True,
    "agreement_metrics_aggregate_only": ("cohens_kappa", "krippendorff_alpha"),
    "confidence_intervals_required": True,
}

# ---------------------------------------------------------------------------
# Public release thresholds.
# ---------------------------------------------------------------------------

PUBLIC_RELEASE_THRESHOLDS: dict[str, Any] = {
    "min_total_n": 50,
    "k_min_per_cell": 5,
    "small_cell_policy": "suppress_or_merge_to_other",
    "confidence_intervals_required": True,
    "per_row_raw_label_outputs": False,
}

# ---------------------------------------------------------------------------
# Privacy contract.
# ---------------------------------------------------------------------------

PRIVACY_CONTRACT: dict[str, Any] = {
    "no_task_ids": True,
    "no_repo_ids_or_names": True,
    "no_file_paths": True,
    "no_spans_or_line_ranges": True,
    "no_snippets_or_excerpts": True,
    "no_content_hashes": True,
    "no_prompts_or_responses": True,
    "no_model_outputs": True,
    "no_private_labels": True,
    "no_raw_annotation_rows": True,
    "no_per_row_hashes": True,
    "no_local_filesystem_paths": True,
    "forbidden_field_categories": (
        "task_id",
        "repo_id",
        "repo",
        "path",
        "span",
        "line_range",
        "start_line",
        "end_line",
        "content_sha",
        "snippet",
        "excerpt",
        "candidate_text",
        "query",
        "prompt",
        "response",
        "model_output",
        "label",
        "raw_label",
        "annotation_row",
        "per_row_hash",
        "local_filesystem_path",
    ),
}

# ---------------------------------------------------------------------------
# Phase graph (D1..D6 as category strings only; no execution data).
# ---------------------------------------------------------------------------

PHASE_GRAPH: tuple[dict[str, str], ...] = (
    {"phase": "D1", "category": "dual_rubric_relevance_scaffold"},
    {
        "phase": "D2",
        "category": "dual_rubric_proxy_aggregate_calibration",
    },
    {
        "phase": "D3",
        "category": "dual_rubric_label_protocol_preregistration",
    },
    {
        "phase": "D4",
        "category": "local_private_true_e_s_calibration_execution_gated",
    },
    {
        "phase": "D5",
        "category": "aggregate_calibration_release_candidate_gated",
    },
    {
        "phase": "D6",
        "category": "runtime_integration_decision_gated",
    },
)
PHASE_IDS: tuple[str, ...] = ("D1", "D2", "D3", "D4", "D5", "D6")

# ---------------------------------------------------------------------------
# Forbidden-output scanner (D3-specific, fail-closed)
# ---------------------------------------------------------------------------

# Sensitive KEY names that must NEVER appear as dict keys anywhere in a
# public JSON output. Extended beyond D1/D2 with D3-specific label/
# annotation-row keys.
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
        # labels / qrels / annotations
        "label", "labels", "qrels", "gold", "gold_label", "gold_labels",
        "gold_answer", "predicted_answer", "answer", "question",
        "raw_label", "raw_labels", "annotation_row", "annotation_rows",
        "annotator_id", "rater_id", "per_row_hash", "row_hash",
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
        # private-record fields (C1/P21 private payload)
        "private_record_hash", "private_records", "private_rows",
        "p31_score_gold", "p31_candidate_pools", "p33b_anchor_subtypes",
        "candidate_id", "gold_spans", "raw_query", "raw_snippet",
        "raw_prompt", "raw_response",
        # model-assisted label fields
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
    }
)

# Value patterns that indicate leaked row-level / candidate / annotation data.
# D3 rejects ALL URLs (no URL allowlist) per the simpler-fail-closed rule.
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
# Path-like strings, with OR without a leading slash (e.g. "src/foo.py",
# "foo.py", "/a/b.py", "/private/foo.jsonl").
_RE_FILE_PATH_VALUE = re.compile(
    rf"\b[A-Za-z0-9._/\-]+\.(?:{_FILE_EXT})\b"
)
# Raw line-range value: "12-34" or "12:34" (3-16 chars, digits + separator).
_RE_LINE_RANGE_VALUE = re.compile(r"\b\d+\s*[:\-]\s*\d+\b")
# Raw JSON fragment: starts with {/[, then a quoted key, then :.
_RE_RAW_JSON = re.compile(r'^\s*[\{\[]\s*"[^"]+"\s*:')


def _path_last_key(path: str) -> str:
    """Extract the last key segment from a dotted JSON path."""
    last = path.rsplit(".", 1)[-1]
    return last.split("[")[0]


def _is_safe_value_path(path: str) -> bool:
    """Check if a JSON path ends with a known-safe value key."""
    return _path_last_key(path) in SAFE_VALUE_KEY_NAMES


def _scan_forbidden(obj: Any, path: str = "$") -> list[dict[str, Any]]:
    """Strict recursive scanner for public JSON outputs.

    Returns a list of violation dicts with ``category`` and ``path``
    (JSON path), NEVER the leaked value itself. Fail-closed: any
    violation means the public output would leak.

    Rejects forbidden dict keys (path/span/content_sha/snippet/query/
    task_id/repo_id/repo/label/raw_label/annotation_row/per_row_hash/
    model_output/etc.) anywhere, and rejects value patterns: ANY URL,
    32/40/64-char hex digests, secret-like strings, path-like strings
    (``src/foo.py``, ``/private/foo.jsonl``), multiline strings, raw JSON
    fragments, and raw line-range strings (``12-34``).

    Allows generic protocol / category / level / bucket strings only if
    they are not row-like (e.g. ``local_private_p21_records``,
    ``proxy_bucket``, ``E0``).
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
        else:
            # A raw line-range value: "12-34" or "12:34" (3-16 chars,
            # only digits + separator). Pure-digit strings like "1234"
            # are NOT flagged (they could be counts).
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
# Abstract-example validator
# ---------------------------------------------------------------------------


def validate_abstract_examples(examples: Any) -> bool:
    """Return True iff ``examples`` exactly matches the approved enum.

    Order-sensitive: the approved enum is the canonical order. Any
    unapproved, concrete, or path-like example fails this check. The
    forbidden scanner independently rejects path-like concrete examples.
    """
    if not isinstance(examples, (list, tuple)):
        return False
    return tuple(examples) == APPROVED_ABSTRACT_EXAMPLES


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
# Protocol sections
# ---------------------------------------------------------------------------


def _build_sampling_frame_protocol() -> dict[str, Any]:
    return {
        "eligible_record_sources": list(ELIGIBLE_RECORD_SOURCES),
        "sampling_axes": list(SAMPLING_AXES),
        "stratification_required": STRATIFICATION_REQUIRED,
        "max_records_per_batch_local_only": MAX_RECORDS_PER_BATCH_LOCAL_ONLY,
        "raw_record_material_private_only": RAW_RECORD_MATERIAL_PRIVATE_ONLY,
    }


def _build_annotation_rubric() -> dict[str, Any]:
    return {
        "e_score_levels": [dict(d) for d in E_SCORE_LEVELS],
        "s_score_levels": [dict(d) for d in S_SCORE_LEVELS],
        "definitions": dict(RUBRIC_DEFINITIONS),
        "bucket_mapping": [dict(d) for d in BUCKET_MAPPING],
        "abstract_examples": list(APPROVED_ABSTRACT_EXAMPLES),
    }


def _build_future_execution_gates() -> dict[str, Any]:
    gates = dict(FUTURE_EXECUTION_GATES)
    # Convert tuple to list for JSON serialization.
    gates["agreement_metrics_aggregate_only"] = list(
        FUTURE_EXECUTION_GATES["agreement_metrics_aggregate_only"]
    )
    return gates


def _build_public_release_thresholds() -> dict[str, Any]:
    return dict(PUBLIC_RELEASE_THRESHOLDS)


def _build_privacy_contract() -> dict[str, Any]:
    contract = dict(PRIVACY_CONTRACT)
    contract["forbidden_field_categories"] = list(
        PRIVACY_CONTRACT["forbidden_field_categories"]
    )
    return contract


def _build_phase_graph() -> list[dict[str, str]]:
    return [dict(d) for d in PHASE_GRAPH]


# ---------------------------------------------------------------------------
# Self-test checks (pure, no I/O)
# ---------------------------------------------------------------------------


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return {"check": name, "passed": bool(ok)}


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all D3 self-test groups. Returns (checks, all_passed)."""
    checks: list[dict[str, Any]] = []

    # --- Group 1: No private read / no input CLI. ---
    skeleton = _build_report_core([], False)
    checks.append(
        _check(
            "artifact_private_records_read_false",
            skeleton["private_records_read"] is False,
        )
    )
    checks.append(
        _check(
            "artifact_raw_private_records_read_false",
            skeleton["raw_private_records_read"] is False,
        )
    )
    checks.append(
        _check(
            "artifact_private_records_persisted_false",
            skeleton["private_records_persisted"] is False,
        )
    )
    cli_opts = _cli_argument_option_strings()
    checks.append(
        _check(
            "cli_has_no_input_argument",
            "--input" not in cli_opts,
        )
    )
    checks.append(
        _check(
            "cli_has_no_allow_private_records_argument",
            "--allow-private-records" not in cli_opts,
        )
    )
    checks.append(
        _check(
            "cli_only_self_test_and_out_arguments",
            (cli_opts - {"-h", "--help"}) == {"--self-test", "--out"},
        )
    )

    # --- Group 2: No label collection / no calibration metrics. ---
    checks.append(
        _check(
            "labels_collected_false",
            skeleton["labels_collected"] is False,
        )
    )
    checks.append(
        _check(
            "calibration_metrics_computed_false",
            skeleton["calibration_metrics_computed"] is False,
        )
    )
    checks.append(
        _check(
            "inter_rater_agreement_measured_false",
            skeleton["inter_rater_agreement_measured"] is False,
        )
    )
    checks.append(
        _check(
            "true_e_s_calibration_claimed_false",
            skeleton["true_e_s_calibration_claimed"] is False,
        )
    )
    checks.append(
        _check(
            "proxy_calibration_claimed_false",
            skeleton["proxy_calibration_claimed"] is False,
        )
    )
    checks.append(
        _check(
            "model_assisted_labels_collected_false",
            skeleton["model_assisted_labels_collected"] is False,
        )
    )

    # --- Group 3: No-claim / no-runtime-change flags false. ---
    checks.append(
        _check(
            "no_claim_flags_all_false",
            all(v is False for v in NO_CLAIM_FLAGS.values()),
        )
    )
    checks.append(
        _check(
            "label_protocol_flags_all_false",
            all(v is False for v in LABEL_PROTOCOL_FLAGS.values()),
        )
    )
    checks.append(
        _check(
            "diagnostic_flags_all_true",
            all(v is True for v in DIAGNOSTIC_FLAGS.values()),
        )
    )

    # --- Group 4: Protocol completeness (required sections/fields). ---
    required_top = (
        "schema_version", "generated_by", "generated_at", "claim_level",
        "rubric_version", "status", "mode",
        "sampling_frame_protocol", "annotation_rubric",
        "future_execution_gates", "public_release_thresholds",
        "privacy_contract", "phase_graph", "forbidden_scan",
        "self_test_checks", "self_test_passed",
    )
    checks.append(
        _check(
            "required_top_level_keys_present",
            all(k in skeleton for k in required_top),
        )
    )
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
            "rubric_version_correct",
            skeleton["rubric_version"] == RUBRIC_VERSION,
        )
    )
    checks.append(
        _check(
            "status_correct_when_self_test_passes",
            _build_report_core([], True)["status"] == TARGET_STATUS,
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
            "mode_correct",
            skeleton["mode"] == MODE,
        )
    )

    sfp = skeleton["sampling_frame_protocol"]
    checks.append(
        _check(
            "eligible_record_sources_correct",
            tuple(sfp["eligible_record_sources"])
            == ELIGIBLE_RECORD_SOURCES,
        )
    )
    checks.append(
        _check(
            "sampling_axes_correct",
            tuple(sfp["sampling_axes"]) == SAMPLING_AXES,
        )
    )
    checks.append(
        _check(
            "stratification_required_true",
            sfp["stratification_required"] is True,
        )
    )
    checks.append(
        _check(
            "max_records_per_batch_local_only_50",
            sfp["max_records_per_batch_local_only"] == 50,
        )
    )
    checks.append(
        _check(
            "raw_record_material_private_only_true",
            sfp["raw_record_material_private_only"] is True,
        )
    )

    rubric = skeleton["annotation_rubric"]
    checks.append(
        _check(
            "e_score_levels_correct",
            tuple(d["level"] for d in rubric["e_score_levels"])
            == E_LEVEL_NAMES,
        )
    )
    checks.append(
        _check(
            "s_score_levels_correct",
            tuple(d["level"] for d in rubric["s_score_levels"])
            == S_LEVEL_NAMES,
        )
    )
    checks.append(
        _check(
            "bucket_mapping_correct",
            tuple(d["bucket"] for d in rubric["bucket_mapping"])
            == BUCKET_NAMES,
        )
    )
    checks.append(
        _check(
            "rubric_definitions_present",
            isinstance(rubric["definitions"], dict)
            and len(rubric["definitions"]) > 0,
        )
    )

    gates = skeleton["future_execution_gates"]
    checks.append(
        _check(
            "explicit_private_opt_in_required_true",
            gates["explicit_private_opt_in_required"] is True,
        )
    )
    checks.append(
        _check(
            "local_output_path_required_true",
            gates["local_output_path_required"] is True,
        )
    )
    checks.append(
        _check(
            "no_committed_raw_labels_true",
            gates["no_committed_raw_labels"] is True,
        )
    )
    checks.append(
        _check(
            "future_k_min_is_5",
            gates["k_min"] == 5,
        )
    )
    checks.append(
        _check(
            "future_min_total_labels_is_50",
            gates["min_total_labels"] == 50,
        )
    )
    checks.append(
        _check(
            "inter_rater_agreement_required_true",
            gates["inter_rater_agreement_required"] is True,
        )
    )
    checks.append(
        _check(
            "agreement_metrics_aggregate_only_correct",
            tuple(gates["agreement_metrics_aggregate_only"])
            == ("cohens_kappa", "krippendorff_alpha"),
        )
    )
    checks.append(
        _check(
            "future_confidence_intervals_required_true",
            gates["confidence_intervals_required"] is True,
        )
    )

    prt = skeleton["public_release_thresholds"]
    checks.append(
        _check(
            "public_min_total_n_50",
            prt["min_total_n"] == 50,
        )
    )
    checks.append(
        _check(
            "public_k_min_per_cell_5",
            prt["k_min_per_cell"] == 5,
        )
    )
    checks.append(
        _check(
            "small_cell_policy_correct",
            prt["small_cell_policy"] == "suppress_or_merge_to_other",
        )
    )
    checks.append(
        _check(
            "public_confidence_intervals_required_true",
            prt["confidence_intervals_required"] is True,
        )
    )
    checks.append(
        _check(
            "per_row_raw_label_outputs_false",
            prt["per_row_raw_label_outputs"] is False,
        )
    )

    pc = skeleton["privacy_contract"]
    checks.append(
        _check(
            "privacy_contract_all_no_flags_true",
            all(
                v is True
                for k, v in pc.items()
                if k.startswith("no_") and k != "forbidden_field_categories"
            ),
        )
    )
    checks.append(
        _check(
            "privacy_contract_forbidden_field_categories_present",
            isinstance(pc.get("forbidden_field_categories"), list)
            and len(pc["forbidden_field_categories"]) > 0,
        )
    )

    pg = skeleton["phase_graph"]
    checks.append(
        _check(
            "phase_graph_has_six_phases",
            [d["phase"] for d in pg] == list(PHASE_IDS),
        )
    )
    checks.append(
        _check(
            "phase_graph_categories_present",
            all(isinstance(d.get("category"), str) for d in pg),
        )
    )

    # --- Group 5: Forbidden scanner rejects sensitive keys/values. ---
    def _has_cat(obj: Any, cat: str) -> bool:
        return any(v["category"] == cat for v in _scan_forbidden(obj))

    # Forbidden dict keys.
    for bad_key in (
        "task_id", "repo_id", "repo", "path", "span", "line_range",
        "start_line", "end_line", "content_sha", "snippet", "excerpt",
        "candidate_text", "query", "prompt", "response", "model_output",
        "label", "raw_label", "annotation_row",
    ):
        checks.append(
            _check(
                f"scanner_rejects_{bad_key}_key",
                _has_cat({bad_key: "abc"}, "forbidden_key"),
            )
        )
    # Forbidden value patterns.
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
    # Safe protocol strings must NOT be flagged.
    checks.append(
        _check(
            "scanner_allows_safe_protocol_string_local_private_p21_records",
            not _scan_forbidden(
                {"eligible_record_sources": ["local_private_p21_records"]}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_safe_protocol_string_proxy_bucket",
            not _scan_forbidden(
                {"sampling_axes": ["proxy_bucket"]}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_safe_protocol_string_e0_level",
            not _scan_forbidden({"level": "E0"}),
        )
    )

    # --- Group 6: Abstract examples only (approved enum). ---
    checks.append(
        _check(
            "abstract_examples_match_approved_enum",
            validate_abstract_examples(APPROVED_ABSTRACT_EXAMPLES),
        )
    )
    checks.append(
        _check(
            "rubric_abstract_examples_match_approved_enum",
            validate_abstract_examples(
                skeleton["annotation_rubric"]["abstract_examples"]
            ),
        )
    )
    # Unapproved abstract string fails validation.
    checks.append(
        _check(
            "unapproved_abstract_example_rejected",
            not validate_abstract_examples(
                ("direct_definition_of_requested_symbol",
                 "unapproved_concrete_example")
            ),
        )
    )
    # Unapproved concrete/path-like example fails BOTH validation and
    # the forbidden scanner (path-like value).
    unapproved_concrete = "src/foo.py defines the requested symbol"
    checks.append(
        _check(
            "concrete_path_like_example_fails_validation",
            not validate_abstract_examples((unapproved_concrete,)),
        )
    )
    checks.append(
        _check(
            "concrete_path_like_example_rejected_by_scanner",
            bool(_scan_forbidden({"abstract_examples": [unapproved_concrete]})),
        )
    )
    # Empty / wrong-type examples fail validation.
    checks.append(
        _check(
            "empty_abstract_examples_rejected",
            not validate_abstract_examples([]),
        )
    )
    checks.append(
        _check(
            "non_list_abstract_examples_rejected",
            not validate_abstract_examples("not_a_list"),
        )
    )

    # --- Group 7: Fail-closed generation on scanner leak. ---
    raised = False
    try:
        _enforce_no_forbidden(
            {"path": "src/foo.py", "content_sha": "a" * 64}
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
        _check("fail_closed_clean_report_does_not_raise", no_raise)
    )
    checks.append(
        _check(
            "skeleton_forbidden_scan_clean",
            skeleton["forbidden_scan"]["status"] == "pass"
            and skeleton["forbidden_scan"]["violations_count"] == 0,
        )
    )

    # --- Group 8: Artifact generation refuses success if self-test fails. ---
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
    # A report built with all_passed=False must NOT carry the success
    # status, and a report built with all_passed=True must.
    checks.append(
        _check(
            "failed_self_test_does_not_carry_success_status",
            _build_report_core([], False)["status"] != TARGET_STATUS
            and _build_report_core([], False)["self_test_passed"] is False,
        )
    )
    checks.append(
        _check(
            "passed_self_test_carries_success_status",
            _build_report_core([], True)["status"] == TARGET_STATUS
            and _build_report_core([], True)["self_test_passed"] is True,
        )
    )

    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def _build_report_core(
    checks: list[dict[str, Any]], all_passed: bool
) -> dict[str, Any]:
    """Assemble the protocol-only report payload from explicit checks.

    Embeds the supplied ``checks`` list and runs the fail-closed
    forbidden scan. Split out so ``run_self_test_checks`` can scan a
    skeleton payload (empty checks) without recursing through
    ``build_report``.
    """
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "rubric_version": RUBRIC_VERSION,
        "status": TARGET_STATUS if all_passed else "self_test_failed",
        "mode": MODE,
        "sampling_frame_protocol": _build_sampling_frame_protocol(),
        "annotation_rubric": _build_annotation_rubric(),
        "future_execution_gates": _build_future_execution_gates(),
        "public_release_thresholds": _build_public_release_thresholds(),
        "privacy_contract": _build_privacy_contract(),
        "phase_graph": _build_phase_graph(),
        "self_test_checks": checks,
        "self_test_passed": all_passed,
        # Label-protocol false flags (flat).
        **LABEL_PROTOCOL_FLAGS,
        # No-claim / no-runtime-change flags (flat).
        **NO_CLAIM_FLAGS,
        # Diagnostic flags (flat).
        **DIAGNOSTIC_FLAGS,
    }

    # Fail-closed forbidden scan before returning. The CLI runs
    # _enforce_no_forbidden again immediately before writing to disk.
    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_leak"
    return report


def build_report() -> dict[str, Any]:
    """Assemble the protocol-only public report (fail-closed scan).

    Runs the deterministic self-test checks and embeds their results,
    then assembles the full report payload (which re-scans itself).
    """
    checks, all_passed = run_self_test_checks()
    return _build_report_core(checks, all_passed)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the D3 CLI parser (no ``--input``; protocol-only)."""
    ap = argparse.ArgumentParser(
        description=(
            "D3 dual-rubric label protocol preregistration "
            "(protocol only; no labels collected)."
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
        default=DEFAULT_OUT,
        help="output artifact JSON path",
    )
    return ap


def _cli_argument_option_strings() -> set[str]:
    """Return the set of CLI option strings (for the no-input self-test)."""
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

    report = build_report()
    # Strict fail-closed guard immediately before writing the JSON artifact.
    _enforce_no_forbidden(report)
    # Refuse successful artifact generation if self-test failed.
    _refuse_on_self_test_failure(report)
    _write_json(args.out, report)
    print(
        f"wrote {args.out} "
        f"(forbidden_scan={report['forbidden_scan']['status']}, "
        f"self_test_passed={report['self_test_passed']}, "
        f"status={report['status']})"
    )


if __name__ == "__main__":
    main()
