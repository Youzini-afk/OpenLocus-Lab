#!/usr/bin/env python3
"""D4-series Harness Rollup / D5 Blocked Status (Public Rollup-Only Artifact).

This module implements the **D4-series harness rollup / D5 blocked
status** public artifact. It is a **rollup-only** artifact, NOT a new
research phase. It aggregates ONLY the committed D4a-D4f public
statuses / claim levels and the D5 blockers. It performs NO private
reads, NO probes, NO `/tmp` outputs, NO label collection, NO metrics,
and NO D5 calibration.

The rollup **does not** read private records, packets, labels, or
bundles, **does not** emit labels / raw label rows / exact counts /
agreement / CI values, **does not** accept packet refs / task IDs /
repo IDs / paths / spans / snippets / content hashes / query /
candidate text / rater IDs / model outputs / provider payloads in any
committed artifact, **does not** compute calibration / inter-rater
agreement / confidence intervals, **does not** pass any public-release
gate, **does not** unblock D5, **does not** claim true E/S calibration,
**does not** perform model/LLM labeling, and **does not** change
runtime behavior, retriever, pack, model, backend, default policy, or
EvidenceCore semantics.

Claim boundary (binding):

* This is **eval/diagnostic only**. It is NOT a runtime change, NOT a
  retriever/pack/model/backend/default-policy change, and NOT an
  EvidenceCore semantic change.
* Claim level: ``d4_series_harness_rollup_only``.
* Status: ``d5_blocked_no_real_human_manual_labels``; mode
  ``public_rollup_no_private_reads``; phase ``D4-rollup``.
* The default committed artifact reads NO private records / packets /
  labels / bundles, collects NO labels, computes NO calibration /
  agreement / CI, performs NO model/LLM labeling, and passes NO
  public-release gate. D5 remains blocked.

The rollup lists EXACTLY the six D4 phases (D4a-D4f), each exactly
once, with their committed short-form commit ID, artifact_status, and
claim_level. The status / claim_level / commit strings inside the
``d4_phases`` contract container are an EXACT allowlist (no over-broad
container exemption; no URLs; no paths; no implementation symbols).

Run::

    python3 -m py_compile eval/d4_series_rollup.py
    python3 eval/d4_series_rollup.py --self-test
    python3 eval/d4_series_rollup.py \
        --out artifacts/d4_series_rollup/\
d4_series_rollup_report.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "d4_series_rollup.v1"
GENERATED_BY = "eval/d4_series_rollup.py"
CLAIM_LEVEL = "d4_series_harness_rollup_only"
TARGET_STATUS = "d5_blocked_no_real_human_manual_labels"
MODE = "public_rollup_no_private_reads"
PHASE = "D4-rollup"

DEFAULT_OUT = Path(
    "artifacts/d4_series_rollup/d4_series_rollup_report.json"
)

# ---------------------------------------------------------------------------
# D4a-D4f phase rollup entries (exactly these six, exactly once each).
# Each entry carries ONLY: phase, commit (short), artifact_status,
# claim_level. No private paths, no counts, no metrics, no packet/bundle
# contents, no task/repo IDs, no rater IDs.
# ---------------------------------------------------------------------------

D4_PHASES: list[dict[str, str]] = [
    {
        "phase": "D4a",
        "commit": "d62c13b",
        "artifact_status": (
            "execution_gate_ready_no_labels_collected"
        ),
        "claim_level": "dual_rubric_execution_gate_dry_run_only",
    },
    {
        "phase": "D4b",
        "commit": "6dd4024",
        "artifact_status": (
            "blocked_no_true_label_bundle_available"
        ),
        "claim_level": "true_label_bundle_execution_harness_only",
    },
    {
        "phase": "D4c",
        "commit": "3458716",
        "artifact_status": (
            "blocked_no_annotation_packets_created"
        ),
        "claim_level": "annotation_packet_builder_harness_only",
    },
    {
        "phase": "D4d",
        "commit": "55c9850",
        "artifact_status": (
            "protocol_ready_no_raters_no_labels_no_packets"
        ),
        "claim_level": "human_annotation_runbook_protocol_only",
    },
    {
        "phase": "D4e",
        "commit": "280d8bb",
        "artifact_status": (
            "blocked_no_filled_packets_available_or_no_conversion_run"
        ),
        "claim_level": (
            "filled_packet_to_d4b_bundle_converter_harness_only"
        ),
    },
    {
        "phase": "D4f",
        "commit": "fea76d3",
        "artifact_status": (
            "blocked_no_private_bundle_available_or_no_validation_run"
        ),
        "claim_level": "d4b_bundle_validation_gate_harness_only",
    },
]

# Short-form commit IDs of the six D4 phases (exact allowlist).
D4_COMMIT_IDS: tuple[str, ...] = (
    "d62c13b",
    "6dd4024",
    "3458716",
    "55c9850",
    "280d8bb",
    "fea76d3",
)

# D4 phase identifiers allowed inside the d4_phases contract container
# (the six phases plus the rollup's own phase identifier).
D4_PHASE_IDS: tuple[str, ...] = (
    "D4a",
    "D4b",
    "D4c",
    "D4d",
    "D4e",
    "D4f",
    "D4-rollup",
)

# Per-phase artifact_status strings allowed inside the d4_phases
# contract container (exact allowlist).
D4_PHASE_STATUS_STRINGS: tuple[str, ...] = (
    "execution_gate_ready_no_labels_collected",
    "blocked_no_true_label_bundle_available",
    "blocked_no_annotation_packets_created",
    "protocol_ready_no_raters_no_labels_no_packets",
    "blocked_no_filled_packets_available_or_no_conversion_run",
    "blocked_no_private_bundle_available_or_no_validation_run",
)

# Per-phase claim_level strings allowed inside the d4_phases contract
# container (exact allowlist).
D4_PHASE_CLAIM_LEVELS: tuple[str, ...] = (
    "dual_rubric_execution_gate_dry_run_only",
    "true_label_bundle_execution_harness_only",
    "annotation_packet_builder_harness_only",
    "human_annotation_runbook_protocol_only",
    "filled_packet_to_d4b_bundle_converter_harness_only",
    "d4b_bundle_validation_gate_harness_only",
)

# ---------------------------------------------------------------------------
# Safe booleans true (control-plane chain complete + each D4 harness
# complete + aggregate-only / diagnostic / not-evidence). Exactly these
# are true in the committed public artifact.
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "control_plane_chain_complete": True,
    "d4a_execution_gate_complete": True,
    "d4b_true_label_bundle_harness_complete": True,
    "d4c_annotation_packet_builder_harness_complete": True,
    "d4d_human_annotation_runbook_complete": True,
    "d4e_converter_harness_complete": True,
    "d4f_bundle_validation_gate_harness_complete": True,
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
    "not_evidence": True,
}

# ---------------------------------------------------------------------------
# D5 prerequisites (all false; real human manual labels are NOT yet
# available, so D5 remains blocked and NO D5 public-aggregate candidate
# is allowed).
# ---------------------------------------------------------------------------

D5_PREREQUISITE_FLAGS: dict[str, bool] = {
    "real_human_manual_labels_available": False,
    "d4e_real_local_conversion_over_real_labels_run": False,
    "d4f_real_local_validation_over_real_labels_run": False,
    "min_n_gate_passed_for_real_labels": False,
    "k_min_gate_passed_for_real_labels": False,
    "agreement_gate_passed_for_real_labels": False,
    "ci_gate_passed_for_real_labels": False,
    "d5_public_aggregate_candidate_allowed": False,
}

# ---------------------------------------------------------------------------
# No-read / no-claim / no-runtime-change flags (all MUST be false in the
# committed public artifact). The rollup reads no private records /
# packets / labels / bundles, collects no labels, computes no
# calibration / agreement / CI, claims no true E/S calibration, performs
# no model/LLM labeling, and changes no runtime / retriever / pack /
# model / backend / default policy / EvidenceCore semantics.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    # no private reads
    "private_records_read": False,
    "private_packets_read": False,
    "private_labels_read": False,
    "private_bundles_read": False,
    # no labels / metrics / agreement / CI
    "labels_collected": False,
    "calibration_metrics_computed": False,
    "agreement_metrics_computed": False,
    "confidence_intervals_computed": False,
    "true_e_s_calibration_claimed": False,
    # no claim / no runtime change
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
# Public artifact scanner (strict, fail-closed, with exact contract
# string allowlist). The ``d4_phases`` list is an EXACT contract
# container: string VALUES inside it must be in
# APPROVED_CONTRACT_STRINGS. No over-broad container exemption; no URLs.
# ---------------------------------------------------------------------------

# Top-level keys whose subtrees are explicit contract containers. String
# values inside these containers must be in APPROVED_CONTRACT_STRINGS.
CONTRACT_CONTAINER_KEYS: frozenset[str] = frozenset({"d4_phases"})

# Exact string values allowed inside the d4_phases contract container
# (phase IDs, short commit IDs, per-phase artifact_status, per-phase
# claim_level). No URLs, no paths, no implementation symbols.
APPROVED_CONTRACT_STRINGS: frozenset[str] = frozenset(
    {
        *D4_PHASE_IDS,
        *D4_COMMIT_IDS,
        *D4_PHASE_STATUS_STRINGS,
        *D4_PHASE_CLAIM_LEVELS,
    }
)

# Sensitive KEY names that must NEVER appear as dict keys anywhere in a
# public artifact JSON. Covers location / content / hash / identifiers /
# packet-specific identifiers / labels / raters / prompts / responses /
# rows / records / patches / secrets / agreement / CI numeric values.
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
        # packet-specific identifiers
        "packet_ref", "packet_id", "packet_refs", "packet_ids",
        "private_record_ref", "candidate_ref", "candidate_id",
        # labels / qrels / annotations / raters
        "label", "labels", "qrels", "gold", "gold_label", "gold_labels",
        "gold_answer", "predicted_answer", "answer", "question",
        "raw_label", "raw_labels", "annotation_row", "annotation_rows",
        "annotator_id", "rater_id", "rater_name", "per_row_hash", "row_hash",
        "disagreement_example", "disagreement_examples",
        "true_label", "true_e_score", "true_s_score",
        "label_slots", "annotation_instructions",
        "e_score", "s_score", "bucket", "citation_valid",
        "rater_pair_present", "adjudicated",
        "candidate_bucket_hint", "evidence",
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
        # exact counts (never emitted by the rollup)
        "total_labels", "label_count", "labels_count",
        "bucket_count", "bucket_counts", "cell_count", "cell_counts",
        "n", "n_total", "count", "counts",
    }
)

# Known-safe provenance value paths (allowlisted for hex_digest /
# path_like value checks only). The forbidden dict-key check is NOT
# relaxed by this.
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
    }
)

# Value patterns that indicate leaked row-level / candidate / packet /
# annotation data. The rollup rejects ALL URLs (no URL allowlist) per
# the fail-closed rule.
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
        in_contract = _is_inside_contract_container(path)
        safe_value = _is_safe_value_path(path)
        if in_contract and obj not in APPROVED_CONTRACT_STRINGS:
            violations.append(
                {"category": "unapproved_contract_string", "path": path}
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
# Report builder
# ---------------------------------------------------------------------------


def _build_public_report(
    checks: list[dict[str, Any]], all_passed: bool
) -> dict[str, Any]:
    """Assemble the public rollup-only report (fail-closed scan).

    The default committed artifact. No private reads, no labels, no
    counts/metrics, no claims, no D5 unblock.
    """
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": TARGET_STATUS if all_passed else "self_test_failed",
        "mode": MODE,
        "phase": PHASE,
        # Exact contract container: the six D4 phases, each exactly once.
        "d4_phases": [dict(entry) for entry in D4_PHASES],
        # Safe booleans true (control-plane chain + each harness complete
        # + aggregate-only / diagnostic / not-evidence).
        **SAFE_TRUE_FLAGS,
        # D5 prerequisites (all false; D5 remains blocked). Keep both a
        # structured object for readability and flat booleans for existing
        # scan / invariant conventions; they must remain identical.
        "d5_prerequisites": dict(D5_PREREQUISITE_FLAGS),
        **D5_PREREQUISITE_FLAGS,
        # No-read / no-claim / no-runtime-change flags (all false).
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


def build_report() -> dict[str, Any]:
    """Assemble the public rollup-only report (fail-closed scan).

    Runs the deterministic self-test checks and embeds their results,
    then assembles the full public report (which re-scans itself).
    """
    checks, all_passed = run_self_test_checks()
    return _build_public_report(checks, all_passed)


# ---------------------------------------------------------------------------
# Self-test helpers
# ---------------------------------------------------------------------------


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return {"check": name, "passed": bool(ok)}


def _phase_entry(phase_id: str) -> dict[str, str] | None:
    """Return the d4_phases entry for ``phase_id`` or ``None``."""
    for entry in D4_PHASES:
        if entry["phase"] == phase_id:
            return entry
    return None


def _phase_count_in_report(
    report: dict[str, Any], phase_id: str
) -> int:
    """Count occurrences of ``phase_id`` in the report's d4_phases list."""
    count = 0
    for entry in report.get("d4_phases", []):
        if entry.get("phase") == phase_id:
            count += 1
    return count


# ===========================================================================
# Self-test checks are appended below in run_self_test_checks().
# This file is intentionally structured so the self-test function is the
# last definition before the CLI; see the marker below.
# ===========================================================================

def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all D4-series rollup self-test groups.

    Returns (checks, all_passed).
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
            "mode_public_rollup_no_private_reads",
            skeleton["mode"] == MODE,
        )
    )
    checks.append(
        _check("phase_d4_rollup", skeleton["phase"] == PHASE)
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

    # --- Group 3: D5 prerequisite flags (all false). ---
    checks.append(
        _check(
            "d5_prerequisites_object_exact",
            skeleton.get("d5_prerequisites") == D5_PREREQUISITE_FLAGS,
        )
    )
    checks.append(
        _check(
            "d5_prerequisites_object_all_false",
            isinstance(skeleton.get("d5_prerequisites"), dict)
            and all(
                value is False
                for value in skeleton["d5_prerequisites"].values()
            ),
        )
    )
    for flag in D5_PREREQUISITE_FLAGS:
        checks.append(
            _check(
                f"d5_prereq_{flag}_false",
                skeleton.get(flag) is False,
            )
        )

    # --- Group 4: No-read / no-claim / no-runtime-change false flags. ---
    for flag in DEFAULT_FALSE_FLAGS:
        checks.append(
            _check(
                f"default_false_{flag}",
                skeleton.get(flag) is False,
            )
        )

    # --- Group 5: D4 phases present exactly once with exact strings. ---
    checks.append(
        _check(
            "d4_phases_count_is_six",
            len(skeleton["d4_phases"]) == 6,
        )
    )
    expected_phase_ids = ("D4a", "D4b", "D4c", "D4d", "D4e", "D4f")
    for phase_id in expected_phase_ids:
        checks.append(
            _check(
                f"d4_phases_{phase_id}_present_exactly_once",
                _phase_count_in_report(skeleton, phase_id) == 1,
            )
        )
    # No duplicate phase IDs, no extra phase IDs.
    seen_ids = [e["phase"] for e in skeleton["d4_phases"]]
    checks.append(
        _check(
            "d4_phases_no_duplicates",
            len(seen_ids) == len(set(seen_ids)),
        )
    )
    checks.append(
        _check(
            "d4_phases_no_extra_or_missing",
            set(seen_ids) == set(expected_phase_ids),
        )
    )
    # Each phase entry has exactly the four allowed keys.
    allowed_entry_keys = frozenset(
        {"phase", "commit", "artifact_status", "claim_level"}
    )
    all_entries_have_exact_keys = all(
        set(e.keys()) == allowed_entry_keys for e in skeleton["d4_phases"]
    )
    checks.append(
        _check(
            "d4_phases_entries_have_exact_keys",
            all_entries_have_exact_keys,
        )
    )

    # Per-phase commit / artifact_status / claim_level exact strings.
    expected_per_phase = {
        "D4a": (
            "d62c13b",
            "execution_gate_ready_no_labels_collected",
            "dual_rubric_execution_gate_dry_run_only",
        ),
        "D4b": (
            "6dd4024",
            "blocked_no_true_label_bundle_available",
            "true_label_bundle_execution_harness_only",
        ),
        "D4c": (
            "3458716",
            "blocked_no_annotation_packets_created",
            "annotation_packet_builder_harness_only",
        ),
        "D4d": (
            "55c9850",
            "protocol_ready_no_raters_no_labels_no_packets",
            "human_annotation_runbook_protocol_only",
        ),
        "D4e": (
            "280d8bb",
            "blocked_no_filled_packets_available_or_no_conversion_run",
            "filled_packet_to_d4b_bundle_converter_harness_only",
        ),
        "D4f": (
            "fea76d3",
            "blocked_no_private_bundle_available_or_no_validation_run",
            "d4b_bundle_validation_gate_harness_only",
        ),
    }
    for phase_id, (
        commit,
        artifact_status,
        claim_level,
    ) in expected_per_phase.items():
        entry = _phase_entry(phase_id)
        checks.append(
            _check(
                f"{phase_id.lower()}_commit_correct",
                entry is not None and entry["commit"] == commit,
            )
        )
        checks.append(
            _check(
                f"{phase_id.lower()}_artifact_status_correct",
                entry is not None
                and entry["artifact_status"] == artifact_status,
            )
        )
        checks.append(
            _check(
                f"{phase_id.lower()}_claim_level_correct",
                entry is not None and entry["claim_level"] == claim_level,
            )
        )

    # control_plane_chain_complete must be true.
    checks.append(
        _check(
            "control_plane_chain_complete_true",
            skeleton["control_plane_chain_complete"] is True,
        )
    )

    # --- Group 6: Public artifact forbidden scanner (rejects + allows). ---
    # Forbidden dict keys anywhere.
    for bad_key in (
        "task_id",
        "repo_id",
        "repo",
        "path",
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
        "total_labels",
        "label_count",
        "bucket_count",
        "cell_count",
    ):
        checks.append(
            _check(
                f"scanner_rejects_{bad_key}_key",
                bool(_scan_forbidden({bad_key: "x"})),
            )
        )

    # Forbidden value patterns (outside contract containers). Use a
    # non-safe, non-forbidden key ("probe") so the value-pattern checks
    # actually apply (safe-value keys bypass them).
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
            "scanner_rejects_hex_digest_value",
            bool(
                _scan_forbidden(
                    {
                        "probe": (
                            "a" * 32
                            + "b" * 8
                        )
                    }
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_40_hex_digest_value",
            bool(
                _scan_forbidden({"probe": "f" * 40}),
            )
        )
    )
    checks.append(
        _check(
            "scanner_rejects_64_hex_digest_value",
            bool(
                _scan_forbidden({"probe": "0" * 64}),
            )
        )
    )
    checks.append(
        _check(
            "scanner_rejects_secret_sentinel_value",
            bool(
                _scan_forbidden(
                    {"probe": _SECRET_SENTINEL}
                )
            ),
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
            bool(
                _scan_forbidden(
                    {"probe": "line1\nline2"}
                )
            ),
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
            bool(
                _scan_forbidden({"probe": "12-34"}),
            )
        )
    )
    checks.append(
        _check(
            "scanner_rejects_colon_line_range_value",
            bool(
                _scan_forbidden({"probe": "12:34"}),
            )
        )
    )

    # Unapproved string inside the d4_phases contract container is
    # rejected (no over-broad container exemption).
    checks.append(
        _check(
            "scanner_rejects_unapproved_string_in_contract_container",
            bool(
                _scan_forbidden(
                    {
                        "d4_phases": [
                            {
                                "phase": "D4a",
                                "commit": "d62c13b",
                                "artifact_status": (
                                    "compute_loss_or_private_text"
                                ),
                                "claim_level": (
                                    "dual_rubric_execution_gate_"
                                    "dry_run_only"
                                ),
                            }
                        ]
                    }
                )
            ),
        )
    )
    # Sensitive field name as a VALUE inside the contract container is
    # rejected (it is not in APPROVED_CONTRACT_STRINGS).
    checks.append(
        _check(
            "scanner_rejects_sensitive_field_name_in_contract_container",
            bool(
                _scan_forbidden(
                    {
                        "d4_phases": [
                            {
                                "phase": "D4a",
                                "commit": "d62c13b",
                                "artifact_status": "content_sha",
                                "claim_level": (
                                    "dual_rubric_execution_gate_"
                                    "dry_run_only"
                                ),
                            }
                        ]
                    }
                )
            ),
        )
    )
    # URL inside the contract container is rejected (no URL allowlist;
    # URLs are not in APPROVED_CONTRACT_STRINGS).
    checks.append(
        _check(
            "scanner_rejects_url_in_contract_container",
            bool(
                _scan_forbidden(
                    {
                        "d4_phases": [
                            {
                                "phase": "D4a",
                                "commit": "https://leak.invalid/",
                                "artifact_status": (
                                    "execution_gate_ready_no_labels_"
                                    "collected"
                                ),
                                "claim_level": (
                                    "dual_rubric_execution_gate_"
                                    "dry_run_only"
                                ),
                            }
                        ]
                    }
                )
            ),
        )
    )

    # Approved contract strings inside the d4_phases container pass.
    checks.append(
        _check(
            "scanner_allows_approved_phase_in_contract",
            not _scan_forbidden(
                {"d4_phases": [{"phase": "D4a"}]}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_approved_commit_in_contract",
            not _scan_forbidden(
                {"d4_phases": [{"commit": "d62c13b"}]}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_approved_status_in_contract",
            not _scan_forbidden(
                {
                    "d4_phases": [
                        {
                            "artifact_status": (
                                "execution_gate_ready_no_labels_"
                                "collected"
                            )
                        }
                    ]
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_approved_claim_level_in_contract",
            not _scan_forbidden(
                {
                    "d4_phases": [
                        {
                            "claim_level": (
                                "dual_rubric_execution_gate_dry_run_only"
                            )
                        }
                    ]
                }
            ),
        )
    )

    # --- Group 7: Fail-closed generation. ---
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
    # Passed self-test carries success status.
    checks.append(
        _check(
            "passed_self_test_carries_success_status",
            _build_public_report([], True)["status"] == TARGET_STATUS,
        )
    )

    # --- Group 8: Public artifact self-scan is clean. ---
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
                )
            ),
        )
    )

    # --- Group 9: CLI argument surface. ---
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
            "cli_only_required_arguments",
            (cli_opts - {"-h", "--help"})
            == {"--self-test", "--out"},
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
    """Build the D4-series rollup CLI parser."""
    ap = SafeArgumentParser(
        description=(
            "D4-series harness rollup / D5 blocked status "
            "(public rollup-only artifact; no private reads, no labels, "
            "no metrics, no D5 calibration by default)."
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
            "rollup artifact)"
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

    # Public default mode (committed rollup-only artifact).
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
