#!/usr/bin/env python3
"""D4d Human Annotation Runbook / Checklist Protocol (Public Protocol-Only Artifact).

This module implements the **D4d human annotation runbook / checklist
protocol** public artifact. D4d freezes how future human raters should
label D4c annotation packets (filling the dual-rubric E/S slots) before
any D4e converter or D5 aggregate release candidate. The default
committed artifact is a **public protocol-only runbook**, NOT a label
collection, NOT a packet build, NOT a filled packet, NOT a D4b bundle,
NOT a converter run, and NOT a calibration.

D4d **does not** read private packets, **does not** read private packet
output, **does not** read private source records, **does not** generate
or persist annotation packets, **does not** recruit or identify raters,
**does not** emit rater IDs, **does not** collect labels, **does not**
create filled packets, **does not** create a D4b true-label bundle,
**does not** run the packet->bundle converter, **does not** validate a
D4b bundle, **does not** compute calibration metrics, **does not**
measure inter-rater agreement, **does not** compute confidence
intervals, **does not** pass any public-release gate, **does not**
unblock D5, **does not** claim true E/S calibration, **does not**
perform model/LLM labeling, **does not** allow model-assisted labels,
**does not** emit private paths/snippets, **does not** emit packet/task/
repo IDs or content hashes, **does not** emit query/candidate text, and
**does not** change runtime behavior, retriever, pack, model, backend,
default policy, or EvidenceCore semantics.

Claim boundary (binding):

* This is **eval/diagnostic only**. It is NOT a runtime change, NOT a
  retriever/pack/model/backend/default-policy change, and NOT an
  EvidenceCore semantic change.
* Claim level: ``human_annotation_runbook_protocol_only``.
* Status: ``protocol_ready_no_raters_no_labels_no_packets``; mode
  ``public_runbook_protocol_only``; phase ``D4d``.
* D3 rubric version: ``d3_true_dual_rubric_label_protocol_v1``.
* D4c packet schema target: ``d4c_annotation_packet_v1``.
* D4b bundle schema target: ``d4b_true_label_bundle_v1``.

D4d is **protocol-only**: there is NO private mode, NO ``--input``, NO
private packet/source reads, NO packet generation, NO filled packets,
NO D4b bundle creation, NO converter, NO calibration, NO agreement
measurement, and NO D5 unblocking. The runbook/checklist content is
category-only and abstract: no packet examples, snippets, paths, task
IDs, repo names, rater IDs/names, URLs, or private examples.

Run::

    python3 -m py_compile eval/d4d_human_annotation_runbook.py
    python3 eval/d4d_human_annotation_runbook.py --self-test
    python3 eval/d4d_human_annotation_runbook.py \
        --out artifacts/d4d_human_annotation_runbook/\
d4d_human_annotation_runbook_report.json
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "d4d_human_annotation_runbook.v1"
GENERATED_BY = "eval/d4d_human_annotation_runbook.py"
CLAIM_LEVEL = "human_annotation_runbook_protocol_only"
TARGET_STATUS = "protocol_ready_no_raters_no_labels_no_packets"
MODE = "public_runbook_protocol_only"
PHASE = "D4d"

DEFAULT_OUT = Path(
    "artifacts/d4d_human_annotation_runbook/"
    "d4d_human_annotation_runbook_report.json"
)

# Referenced schema versions (target/source contracts only; D4d does not
# read packets, build bundles, or run any converter).
D3_RUBRIC_VERSION = "d3_true_dual_rubric_label_protocol_v1"
D4C_PACKET_SCHEMA_TARGET = "d4c_annotation_packet_v1"
D4B_BUNDLE_SCHEMA_TARGET = "d4b_true_label_bundle_v1"

# Fixed label slots a human rater must fill (referenced by the runbook
# checklist; D4d collects NO labels and creates NO filled packets).
LABEL_SLOTS: tuple[str, ...] = (
    "e_score",
    "s_score",
    "bucket",
    "citation_valid",
    "rater_pair_present",
    "adjudicated",
)

# D3 dual-rubric E-score / S-score levels (definitions referenced by the
# runbook; D4d emits no filled label values).
E_SCORE_LEVELS: tuple[str, ...] = ("E0", "E1", "E2")
S_SCORE_LEVELS: tuple[str, ...] = ("S0", "S1", "S2")

# Bucket names referenced by the D3 rubric (category-only).
BUCKET_NAMES: tuple[str, ...] = (
    "primary_evidence",
    "dependency_support",
    "weak_candidates",
    "abstained",
)

# Release gate names / categories used by the protocol.
GATE_NAMES: tuple[str, ...] = (
    "min_total_labels",
    "k_min",
    "agreement_metric",
    "confidence_intervals",
    "small_cell_suppression",
)

# Release gate numeric thresholds (referenced; D4d passes NO gate).
MIN_TOTAL_LABELS = 50
K_MIN_PER_PUBLIC_CELL = 5
MIN_RATER_COUNT = 2

# ---------------------------------------------------------------------------
# Runbook / checklist category tokens (abstract, category-only). These
# are the only approved abstract strings that may appear as values inside
# runbook checklist / prohibited-source contract containers. No packet
# examples, snippets, paths, IDs, rater names, URLs, or private examples.
# ---------------------------------------------------------------------------

# Section 1: Preconditions
_PRECONDITIONS: tuple[str, ...] = (
    "d3_rubric_only",
    "d4c_packet_schema_source",
    "d4b_bundle_schema_target_ref",
    "packets_local_private",
    "no_public_packet_contents",
    "d4d_collects_no_labels",
)

# Section 2: Rater setup
_RATER_SETUP: tuple[str, ...] = (
    "two_independent_human_raters",
    "independent_work_before_adjudication",
    "no_rater_ids_in_public_artifacts",
    "local_rater_identity_mapping_private",
    "abstract_training_examples_only",
)

# Section 3: Labeling rules
_LABELING_RULES: tuple[str, ...] = (
    "fill_label_slots_only",
    "d3_e_score_levels_e0_e1_e2",
    "d3_s_score_levels_s0_s1_s2",
    "primary_evidence_requires_citation_valid",
    "dependency_support_structural_not_direct_answer",
    "abstain_on_invalid_stale_insufficient_evidence",
)

# Section 4: Prohibited labeling sources
_PROHIBITED_SOURCES: tuple[str, ...] = (
    "no_llm_or_model_labels",
    "no_proxy_labels_as_true_labels",
    "no_model_name_rules",
    "no_benchmark_private_buckets_as_runtime_policy",
    "no_downstream_value_claims",
)

# Section 5: Local storage / privacy
_LOCAL_STORAGE_PRIVACY: tuple[str, ...] = (
    "packets_and_filled_packets_local_only",
    "no_packet_task_repo_ids_in_public",
    "no_paths_snippets_hashes_query_candidate_text_in_public",
    "local_outputs_under_tmp_or_approved_private",
    "no_committed_packets_or_labels",
)

# Section 6: Adjudication
_ADJUDICATION: tuple[str, ...] = (
    "disagreement_categories_local_only",
    "adjudication_after_independent_labels",
    "aggregate_disagreement_counts_only_if_d5_gates_pass",
    "no_disagreement_examples_in_public",
)

# Section 7: Release gates
_RELEASE_GATES: tuple[str, ...] = (
    "min_total_labels_n_ge_50",
    "k_min_per_public_cell_k_ge_5",
    "agreement_metric_required",
    "confidence_intervals_required",
    "small_cells_suppressed_or_merged",
    "aggregate_only_public_release_candidate",
    "d5_remains_blocked_until_all_gates_pass",
)

# Section identifiers (safe abstract strings; not contract-container
# values, so they only need to avoid forbidden patterns).
RUNBOOK_SECTION_IDS: tuple[str, ...] = (
    "preconditions",
    "rater_setup",
    "labeling_rules",
    "prohibited_labeling_sources",
    "local_storage_privacy",
    "adjudication",
    "release_gates",
)

# All approved abstract category tokens that may appear as values inside
# runbook checklist / prohibited-source contract containers.
RUNBOOK_CATEGORY_TOKENS: frozenset[str] = frozenset(
    set(_PRECONDITIONS)
    | set(_RATER_SETUP)
    | set(_LABELING_RULES)
    | set(_PROHIBITED_SOURCES)
    | set(_LOCAL_STORAGE_PRIVACY)
    | set(_ADJUDICATION)
    | set(_RELEASE_GATES)
)

# ---------------------------------------------------------------------------
# Default false flags (all MUST be false in the committed public artifact).
# D4d reads no private packets/source records, generates no packets,
# recruits/identifies no raters, collects no labels, creates no filled
# packets, creates no D4b bundle, runs no converter, computes no calibration,
# measures no agreement/CI, passes no release gate, and unblocks no D5.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "private_packets_read": False,
    "private_packet_output_read": False,
    "private_source_records_read": False,
    "annotation_packets_generated": False,
    "annotation_packets_persisted": False,
    "raters_recruited": False,
    "raters_identified": False,
    "rater_ids_emitted": False,
    "labels_collected": False,
    "filled_packets_created": False,
    "d4b_true_label_bundle_created": False,
    "d4b_bundle_converter_run": False,
    "d4b_true_label_bundle_validated": False,
    "calibration_metrics_computed": False,
    "inter_rater_agreement_measured": False,
    "confidence_intervals_computed": False,
    "public_release_gate_passed": False,
    "d5_unblocked": False,
    "true_e_s_calibration_claimed": False,
    "model_or_llm_labeling_performed": False,
    "model_assisted_labels_allowed": False,
    "private_paths_or_snippets_emitted": False,
    "packet_ids_emitted": False,
    "task_ids_emitted": False,
    "repo_ids_emitted": False,
    "content_sha_emitted": False,
    "query_or_candidate_text_emitted": False,
}

# Allowed true protocol flags (true only for the defined protocol controls;
# each is proven by a self-test). Exactly these; no packet-build / label /
# bundle / calibration / agreement / CI / release / D5-unblock claim flags
# are true in the default committed artifact.
PROTOCOL_TRUE_FLAGS: dict[str, bool] = {
    "runbook_protocol_defined": True,
    "checklist_schema_defined": True,
    "rater_independence_required": True,
    "d3_rubric_required": True,
    "d4c_packet_schema_referenced": True,
    "d4b_bundle_schema_referenced": True,
    "local_only_storage_required": True,
    "no_llm_labeling_required": True,
    "adjudication_policy_defined": True,
    "disagreement_handling_defined": True,
    "min_n_gate_referenced": True,
    "k_min_gate_referenced": True,
    "agreement_gate_referenced": True,
    "ci_gate_referenced": True,
    "aggregate_only_public_release_required": True,
}

# No-claim / no-runtime-change flags (all MUST be false).
NO_CLAIM_FLAGS: dict[str, bool] = {
    "runtime_behavior_changed": False,
    "retriever_changed": False,
    "pack_builder_changed": False,
    "model_calls_changed": False,
    "backend_changed": False,
    "default_policy_changed": False,
    "evidencecore_semantics_changed": False,
    "promotion_ready": False,
    "default_should_change": False,
    "downstream_agent_value_proven": False,
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
# Public artifact scanner (strict, fail-closed, with exact contract
# string allowlist). Unlike a broad container exemption, contract
# containers allow ONLY approved schema/label/bucket/gate/category
# strings; arbitrary strings inside containers are rejected.
# ---------------------------------------------------------------------------

# Top-level keys whose subtrees are explicit contract field-name / enum
# containers. String values inside these containers must be in
# APPROVED_CONTRACT_STRINGS (exact allowlist). Field-name token strings
# are allowed as VALUES only inside these containers and nowhere else.
CONTRACT_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "checklist",
        "e_score_levels",
        "s_score_levels",
        "bucket_names",
        "required_label_slots",
        "gate_names",
        "prohibited_sources",
        "rater_independence_rules",
    }
)

# Sensitive field-name tokens that may appear as list-element VALUES
# inside contract containers (e.g. required_label_slots) for the LABEL
# SLOT subset only, but are forbidden as dict KEYS anywhere and forbidden
# as VALUES outside contract containers. Sensitive packet/source fields
# (content_sha, query_text, etc.) are NOT approved contract strings, so
# they are rejected even inside contract containers.
FIELD_NAME_TOKENS: frozenset[str] = frozenset(
    {
        # label slots
        "e_score",
        "s_score",
        "bucket",
        "citation_valid",
        "rater_pair_present",
        "adjudicated",
        # sensitive packet / source fields (never in public artifact)
        "content_sha",
        "query_text",
        "candidate_text",
        "packet_ref",
        "packet_id",
        "private_record_ref",
        "candidate_ref",
        "candidate_bucket_hint",
        "start_line",
        "end_line",
        "snippet",
        "label_slots",
        "annotation_instructions",
    }
)

# Exact string values allowed inside explicit public contract containers.
# This intentionally does NOT allow arbitrary short strings inside a
# contract container; only approved schema identifiers, E/S levels, bucket
# names, label-slot field-name tokens, gate names, and approved abstract
# runbook category tokens. Sensitive source fields such as content_sha /
# query_text are not exposed in the public artifact.
APPROVED_CONTRACT_STRINGS: frozenset[str] = frozenset(
    {
        D3_RUBRIC_VERSION,
        D4C_PACKET_SCHEMA_TARGET,
        D4B_BUNDLE_SCHEMA_TARGET,
        *E_SCORE_LEVELS,
        *S_SCORE_LEVELS,
        *BUCKET_NAMES,
        *LABEL_SLOTS,
        *GATE_NAMES,
        *RUNBOOK_CATEGORY_TOKENS,
    }
)

# Sensitive KEY names that must NEVER appear as dict keys anywhere in a
# public artifact JSON.
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
        # patches / tests
        "patch", "test_patch", "tests",
        # secrets
        "api_key", "api_token", "api_secret", "base_url", "provider_key",
        "authorization",
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
        "d3_rubric_version",
        "d4c_packet_schema_target",
        "d4b_bundle_schema_target",
        "section",
        "check",
        "category",
    }
)

# Value patterns that indicate leaked row-level / candidate / packet /
# annotation data. D4d rejects ALL URLs (no URL allowlist) per the
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
_SECRET_SENTINEL = "SECRET_RUNBOOK_SENTINEL"


def _path_last_key(path: str) -> str:
    """Extract the last key segment from a dotted JSON path."""
    last = path.rsplit(".", 1)[-1]
    return last.split("[")[0]


def _is_safe_value_path(path: str) -> bool:
    """Check if a JSON path ends with a known-safe value key."""
    return _path_last_key(path) in SAFE_VALUE_KEY_NAMES


def _is_inside_contract_container(path: str) -> bool:
    """True iff any ancestor segment of ``path`` is a contract container key.

    Approved strings (schema identifiers, E/S levels, bucket names,
    label-slot field names, gate names, and approved abstract runbook
    category tokens) are allowed as VALUES only inside explicit contract
    containers and nowhere else.
    """
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

    Rejects forbidden dict keys (path/span/content_sha/snippet/
    query_text/packet_ref/task_id/repo_id/label/labels/raw_label/
    annotation_row/rater_id/model_output/provider_payload/etc.) anywhere,
    and rejects value patterns: ANY URL, 32/40/64-char hex digests,
    secret-like strings, path-like strings, multiline strings, raw JSON
    fragments, raw line-range strings, and the self-test sentinel.

    Contract containers are exact allowlists: only approved schema
    identifiers, E/S levels, bucket names, label-slot field names, gate
    names, and approved abstract runbook category tokens may appear
    there. Arbitrary short strings such as implementation symbols or
    private text are rejected even inside contract containers.
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
        # Contract containers are exact allowlists: only approved schema
        # identifiers, E/S levels, bucket names, label-slot field names,
        # gate names, and approved runbook category tokens. Reject
        # arbitrary short strings such as "compute_loss" or private text
        # even if nested under a contract container.
        if in_contract and obj not in APPROVED_CONTRACT_STRINGS:
            violations.append(
                {"category": "unapproved_contract_string", "path": path}
            )
        # Field-name tokens are allowed as values ONLY inside contract
        # containers; reject them as values anywhere else.
        elif not in_contract and obj in FIELD_NAME_TOKENS:
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


# ---------------------------------------------------------------------------
# Public contracts (category-only; field-name tokens allowed only inside
# contract containers by the public scanner)
# ---------------------------------------------------------------------------


def _build_rubric_contract() -> dict[str, Any]:
    """D3 dual-rubric contract (E/S levels, bucket names, label slots)."""
    return {
        "d3_rubric_version": D3_RUBRIC_VERSION,
        "e_score_levels": list(E_SCORE_LEVELS),
        "s_score_levels": list(S_SCORE_LEVELS),
        "bucket_names": list(BUCKET_NAMES),
        "required_label_slots": list(LABEL_SLOTS),
    }


def _build_label_slot_contract() -> dict[str, Any]:
    """Label slot contract (the six slots a human rater fills)."""
    return {
        "required_label_slots": list(LABEL_SLOTS),
        "target_packet_schema": D4C_PACKET_SCHEMA_TARGET,
        "target_bundle_schema": D4B_BUNDLE_SCHEMA_TARGET,
        "no_filled_packets_created": True,
    }


def _build_release_gate_contract() -> dict[str, Any]:
    """Release gate contract (referenced; D4d passes NO gate)."""
    return {
        "gate_names": list(GATE_NAMES),
        "min_total_labels": MIN_TOTAL_LABELS,
        "k_min": K_MIN_PER_PUBLIC_CELL,
        "min_rater_count": MIN_RATER_COUNT,
        "agreement_required": True,
        "confidence_intervals_required": True,
        "small_cell_suppression_required": True,
        "aggregate_only_public_release_required": True,
        "d5_blocked_until_all_gates_pass": True,
        "public_release_gate_passed": False,
    }


def _build_prohibited_labeling_sources_contract() -> dict[str, Any]:
    """Prohibited labeling sources contract (no LLM/proxy/model labels)."""
    return {
        "prohibited_sources": list(_PROHIBITED_SOURCES),
        "model_or_llm_labeling_performed": False,
        "model_assisted_labels_allowed": False,
    }


def _build_rater_setup_contract() -> dict[str, Any]:
    """Rater setup contract (independence, privacy, abstract training)."""
    return {
        "min_rater_count": MIN_RATER_COUNT,
        "rater_independence_required": True,
        "rater_independence_rules": list(_RATER_SETUP),
        "local_rater_mapping_private_only": True,
        "rater_ids_emitted": False,
        "raters_recruited": False,
        "raters_identified": False,
    }


def _build_runbook_protocol_contract() -> dict[str, Any]:
    """Human annotation runbook / checklist protocol contract.

    Category-only and abstract. Seven required sections, each with a
    checklist of approved abstract category tokens. No packet examples,
    snippets, paths, task IDs, repo names, rater IDs/names, URLs, or
    private examples.
    """
    sections = (
        ("preconditions", _PRECONDITIONS),
        ("rater_setup", _RATER_SETUP),
        ("labeling_rules", _LABELING_RULES),
        ("prohibited_labeling_sources", _PROHIBITED_SOURCES),
        ("local_storage_privacy", _LOCAL_STORAGE_PRIVACY),
        ("adjudication", _ADJUDICATION),
        ("release_gates", _RELEASE_GATES),
    )
    return {
        "d3_rubric_version": D3_RUBRIC_VERSION,
        "d4c_packet_schema_target": D4C_PACKET_SCHEMA_TARGET,
        "d4b_bundle_schema_target": D4B_BUNDLE_SCHEMA_TARGET,
        "sections": [
            {"section": sid, "checklist": list(checklist)}
            for sid, checklist in sections
        ],
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


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def _build_public_report(
    checks: list[dict[str, Any]], all_passed: bool
) -> dict[str, Any]:
    """Assemble the public protocol-only runbook report (fail-closed scan).

    The default committed artifact. No private packets read, no packets
    generated, no raters recruited/identified, no labels collected, no
    filled packets, no D4b bundle, no converter, no calibration, no
    agreement/CI, no release gate passed, no D5 unblocked, no claims.
    """
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": TARGET_STATUS if all_passed else "self_test_failed",
        "mode": MODE,
        "phase": PHASE,
        "d3_rubric_version": D3_RUBRIC_VERSION,
        "d4c_packet_schema_target": D4C_PACKET_SCHEMA_TARGET,
        "d4b_bundle_schema_target": D4B_BUNDLE_SCHEMA_TARGET,
        "runbook_protocol_contract": _build_runbook_protocol_contract(),
        "rubric_contract": _build_rubric_contract(),
        "label_slot_contract": _build_label_slot_contract(),
        "release_gate_contract": _build_release_gate_contract(),
        "prohibited_labeling_sources_contract":
            _build_prohibited_labeling_sources_contract(),
        "rater_setup_contract": _build_rater_setup_contract(),
        "self_test_summary": _self_test_category_summary(checks),
        "self_test_checks": checks,
        "self_test_passed": all_passed,
        # Default false flags (flat).
        **DEFAULT_FALSE_FLAGS,
        # Protocol true flags (flat; true only for defined controls).
        **PROTOCOL_TRUE_FLAGS,
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


def build_report() -> dict[str, Any]:
    """Assemble the public protocol-only runbook report (fail-closed scan).

    Runs the deterministic self-test checks and embeds their results,
    then assembles the full public report (which re-scans itself).
    """
    checks, all_passed = run_self_test_checks()
    return _build_public_report(checks, all_passed)


# ---------------------------------------------------------------------------
# Self-test checks (pure, no I/O)
# ---------------------------------------------------------------------------


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return {"check": name, "passed": bool(ok)}


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all D4d self-test groups. Returns (checks, all_passed)."""
    checks: list[dict[str, Any]] = []

    # --- Group 1: Default false / true flags. ---
    skeleton = _build_public_report([], False)
    for flag in DEFAULT_FALSE_FLAGS:
        checks.append(
            _check(
                f"default_flag_{flag}_false",
                skeleton.get(flag) is False,
            )
        )
    for flag in PROTOCOL_TRUE_FLAGS:
        checks.append(
            _check(
                f"protocol_flag_{flag}_true",
                skeleton.get(flag) is True,
            )
        )
    for flag in NO_CLAIM_FLAGS:
        checks.append(
            _check(
                f"no_claim_{flag}_false",
                skeleton.get(flag) is False,
            )
        )
    for flag in DIAGNOSTIC_FLAGS:
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
            "mode_public_runbook_protocol_only",
            skeleton["mode"] == MODE,
        )
    )
    checks.append(
        _check("phase_d4d", skeleton["phase"] == PHASE)
    )
    checks.append(
        _check(
            "d3_rubric_version_correct",
            skeleton["d3_rubric_version"] == D3_RUBRIC_VERSION,
        )
    )
    checks.append(
        _check(
            "d4c_packet_schema_target_correct",
            skeleton["d4c_packet_schema_target"] == D4C_PACKET_SCHEMA_TARGET,
        )
    )
    checks.append(
        _check(
            "d4b_bundle_schema_target_correct",
            skeleton["d4b_bundle_schema_target"] == D4B_BUNDLE_SCHEMA_TARGET,
        )
    )
    checks.append(
        _check(
            "runbook_protocol_defined_true",
            skeleton["runbook_protocol_defined"] is True,
        )
    )
    checks.append(
        _check(
            "checklist_schema_defined_true",
            skeleton["checklist_schema_defined"] is True,
        )
    )
    checks.append(
        _check(
            "rater_independence_required_true",
            skeleton["rater_independence_required"] is True,
        )
    )
    checks.append(
        _check(
            "d3_rubric_required_true",
            skeleton["d3_rubric_required"] is True,
        )
    )
    checks.append(
        _check(
            "d4c_packet_schema_referenced_true",
            skeleton["d4c_packet_schema_referenced"] is True,
        )
    )
    checks.append(
        _check(
            "d4b_bundle_schema_referenced_true",
            skeleton["d4b_bundle_schema_referenced"] is True,
        )
    )
    checks.append(
        _check(
            "local_only_storage_required_true",
            skeleton["local_only_storage_required"] is True,
        )
    )
    checks.append(
        _check(
            "no_llm_labeling_required_true",
            skeleton["no_llm_labeling_required"] is True,
        )
    )
    checks.append(
        _check(
            "adjudication_policy_defined_true",
            skeleton["adjudication_policy_defined"] is True,
        )
    )
    checks.append(
        _check(
            "disagreement_handling_defined_true",
            skeleton["disagreement_handling_defined"] is True,
        )
    )
    checks.append(
        _check(
            "min_n_gate_referenced_true",
            skeleton["min_n_gate_referenced"] is True,
        )
    )
    checks.append(
        _check(
            "k_min_gate_referenced_true",
            skeleton["k_min_gate_referenced"] is True,
        )
    )
    checks.append(
        _check(
            "agreement_gate_referenced_true",
            skeleton["agreement_gate_referenced"] is True,
        )
    )
    checks.append(
        _check(
            "ci_gate_referenced_true",
            skeleton["ci_gate_referenced"] is True,
        )
    )
    checks.append(
        _check(
            "aggregate_only_public_release_required_true",
            skeleton["aggregate_only_public_release_required"] is True,
        )
    )

    # --- Group 3: Required runbook sections present. ---
    sections = skeleton["runbook_protocol_contract"]["sections"]
    section_ids = [s["section"] for s in sections]
    checks.append(
        _check(
            "runbook_has_seven_sections",
            len(sections) == 7,
        )
    )
    checks.append(
        _check(
            "runbook_section_ids_exact",
            tuple(section_ids) == RUNBOOK_SECTION_IDS,
        )
    )
    for sid in RUNBOOK_SECTION_IDS:
        checks.append(
            _check(
                f"runbook_section_{sid}_nonempty",
                any(
                    s["section"] == sid and len(s["checklist"]) > 0
                    for s in sections
                ),
            )
        )
    # Each section checklist only contains approved category tokens.
    for s in sections:
        checks.append(
            _check(
                f"runbook_section_{s['section']}_approved_tokens_only",
                all(tok in RUNBOOK_CATEGORY_TOKENS for tok in s["checklist"]),
            )
        )

    # --- Group 4: Rubric / label-slot / gate contracts exact. ---
    rc = skeleton["rubric_contract"]
    checks.append(
        _check(
            "rubric_contract_d3_version",
            rc["d3_rubric_version"] == D3_RUBRIC_VERSION,
        )
    )
    checks.append(
        _check(
            "rubric_contract_e_score_levels",
            rc["e_score_levels"] == list(E_SCORE_LEVELS),
        )
    )
    checks.append(
        _check(
            "rubric_contract_s_score_levels",
            rc["s_score_levels"] == list(S_SCORE_LEVELS),
        )
    )
    checks.append(
        _check(
            "rubric_contract_bucket_names",
            rc["bucket_names"] == list(BUCKET_NAMES),
        )
    )
    checks.append(
        _check(
            "rubric_contract_required_label_slots",
            rc["required_label_slots"] == list(LABEL_SLOTS),
        )
    )
    checks.append(
        _check(
            "label_slot_contract_target_packet_schema",
            skeleton["label_slot_contract"]["target_packet_schema"]
            == D4C_PACKET_SCHEMA_TARGET,
        )
    )
    checks.append(
        _check(
            "label_slot_contract_target_bundle_schema",
            skeleton["label_slot_contract"]["target_bundle_schema"]
            == D4B_BUNDLE_SCHEMA_TARGET,
        )
    )
    checks.append(
        _check(
            "label_slot_contract_no_filled_packets_created",
            skeleton["label_slot_contract"]["no_filled_packets_created"]
            is True,
        )
    )

    # --- Group 5: Release gate constants and references. ---
    gc = skeleton["release_gate_contract"]
    checks.append(
        _check(
            "gate_min_total_labels_ge_50",
            gc["min_total_labels"] >= 50,
        )
    )
    checks.append(
        _check(
            "gate_k_min_ge_5",
            gc["k_min"] >= 5,
        )
    )
    checks.append(
        _check(
            "gate_min_rater_count_ge_2",
            gc["min_rater_count"] >= 2,
        )
    )
    checks.append(
        _check(
            "gate_agreement_required",
            gc["agreement_required"] is True,
        )
    )
    checks.append(
        _check(
            "gate_confidence_intervals_required",
            gc["confidence_intervals_required"] is True,
        )
    )
    checks.append(
        _check(
            "gate_small_cell_suppression_required",
            gc["small_cell_suppression_required"] is True,
        )
    )
    checks.append(
        _check(
            "gate_aggregate_only_release_required",
            gc["aggregate_only_public_release_required"] is True,
        )
    )
    checks.append(
        _check(
            "gate_d5_blocked_until_all_gates_pass",
            gc["d5_blocked_until_all_gates_pass"] is True
            and gc["public_release_gate_passed"] is False,
        )
    )
    checks.append(
        _check(
            "gate_names_exact",
            gc["gate_names"] == list(GATE_NAMES),
        )
    )
    checks.append(
        _check(
            "d5_unblocked_false",
            skeleton["d5_unblocked"] is False,
        )
    )
    checks.append(
        _check(
            "public_release_gate_passed_false",
            skeleton["public_release_gate_passed"] is False,
        )
    )

    # --- Group 6: Prohibited labeling sources (no LLM/proxy/model). ---
    pc = skeleton["prohibited_labeling_sources_contract"]
    checks.append(
        _check(
            "prohibited_sources_contains_no_llm",
            "no_llm_or_model_labels" in pc["prohibited_sources"],
        )
    )
    checks.append(
        _check(
            "prohibited_sources_contains_no_proxy",
            "no_proxy_labels_as_true_labels" in pc["prohibited_sources"],
        )
    )
    checks.append(
        _check(
            "prohibited_sources_contains_no_model_name_rules",
            "no_model_name_rules" in pc["prohibited_sources"],
        )
    )
    checks.append(
        _check(
            "prohibited_sources_contains_no_benchmark_buckets_policy",
            "no_benchmark_private_buckets_as_runtime_policy"
            in pc["prohibited_sources"],
        )
    )
    checks.append(
        _check(
            "prohibited_sources_contains_no_downstream_claims",
            "no_downstream_value_claims" in pc["prohibited_sources"],
        )
    )
    checks.append(
        _check(
            "model_or_llm_labeling_performed_false",
            skeleton["model_or_llm_labeling_performed"] is False
            and pc["model_or_llm_labeling_performed"] is False,
        )
    )
    checks.append(
        _check(
            "model_assisted_labels_allowed_false",
            skeleton["model_assisted_labels_allowed"] is False
            and pc["model_assisted_labels_allowed"] is False,
        )
    )
    checks.append(
        _check(
            "no_llm_labeling_required_true_flag",
            skeleton["no_llm_labeling_required"] is True,
        )
    )

    # --- Group 7: No private reads / no packets / no labels / no raters. ---
    checks.append(
        _check(
            "private_packets_read_false",
            skeleton["private_packets_read"] is False,
        )
    )
    checks.append(
        _check(
            "private_packet_output_read_false",
            skeleton["private_packet_output_read"] is False,
        )
    )
    checks.append(
        _check(
            "private_source_records_read_false",
            skeleton["private_source_records_read"] is False,
        )
    )
    checks.append(
        _check(
            "annotation_packets_generated_false",
            skeleton["annotation_packets_generated"] is False,
        )
    )
    checks.append(
        _check(
            "annotation_packets_persisted_false",
            skeleton["annotation_packets_persisted"] is False,
        )
    )
    checks.append(
        _check(
            "raters_recruited_false",
            skeleton["raters_recruited"] is False,
        )
    )
    checks.append(
        _check(
            "raters_identified_false",
            skeleton["raters_identified"] is False,
        )
    )
    checks.append(
        _check(
            "rater_ids_emitted_false",
            skeleton["rater_ids_emitted"] is False,
        )
    )
    checks.append(
        _check(
            "labels_collected_false",
            skeleton["labels_collected"] is False,
        )
    )
    checks.append(
        _check(
            "filled_packets_created_false",
            skeleton["filled_packets_created"] is False,
        )
    )
    checks.append(
        _check(
            "d4b_true_label_bundle_created_false",
            skeleton["d4b_true_label_bundle_created"] is False,
        )
    )
    checks.append(
        _check(
            "d4b_bundle_converter_run_false",
            skeleton["d4b_bundle_converter_run"] is False,
        )
    )
    checks.append(
        _check(
            "d4b_true_label_bundle_validated_false",
            skeleton["d4b_true_label_bundle_validated"] is False,
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
            "confidence_intervals_computed_false",
            skeleton["confidence_intervals_computed"] is False,
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
            "private_paths_or_snippets_emitted_false",
            skeleton["private_paths_or_snippets_emitted"] is False,
        )
    )
    checks.append(
        _check(
            "packet_ids_emitted_false",
            skeleton["packet_ids_emitted"] is False,
        )
    )
    checks.append(
        _check(
            "task_ids_emitted_false",
            skeleton["task_ids_emitted"] is False,
        )
    )
    checks.append(
        _check(
            "repo_ids_emitted_false",
            skeleton["repo_ids_emitted"] is False,
        )
    )
    checks.append(
        _check(
            "content_sha_emitted_false",
            skeleton["content_sha_emitted"] is False,
        )
    )
    checks.append(
        _check(
            "query_or_candidate_text_emitted_false",
            skeleton["query_or_candidate_text_emitted"] is False,
        )
    )

    # --- Group 8: Public report has no sensitive keys anywhere. ---
    for bad_key in (
        "path", "snippet", "content_sha", "query_text", "candidate_text",
        "packet_ref", "packet_id", "label_slots", "annotation_instructions",
        "packets", "labels", "rater_id", "annotator_id", "raw_label",
        "disagreement_example", "model_output", "provider_payload",
        "api_key", "evidence", "task_id", "repo_id",
    ):
        checks.append(
            _check(
                f"public_report_has_no_{bad_key}_key",
                not _has_dict_key_anywhere(skeleton, bad_key),
            )
        )

    # --- Group 9: Public scanner fail-closes + exact contract allowlist. ---
    def _has_cat(obj: Any, cat: str) -> bool:
        return any(v["category"] == cat for v in _scan_forbidden(obj))

    # Approved abstract category tokens pass inside contract containers.
    checks.append(
        _check(
            "scanner_allows_approved_category_in_checklist",
            not _scan_forbidden(
                {"checklist": ["d3_rubric_only", "two_independent_human_raters"]}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_e_levels_in_contract",
            not _scan_forbidden(
                {"e_score_levels": ["E0", "E1", "E2"]}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_s_levels_in_contract",
            not _scan_forbidden(
                {"s_score_levels": ["S0", "S1", "S2"]}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_bucket_names_in_contract",
            not _scan_forbidden(
                {"bucket_names": list(BUCKET_NAMES)}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_label_slots_in_contract",
            not _scan_forbidden(
                {"required_label_slots": list(LABEL_SLOTS)}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_gate_names_in_contract",
            not _scan_forbidden(
                {"gate_names": list(GATE_NAMES)}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_schema_refs_in_contract",
            not _scan_forbidden(
                {
                    "checklist": [
                        D3_RUBRIC_VERSION,
                        D4C_PACKET_SCHEMA_TARGET,
                        D4B_BUNDLE_SCHEMA_TARGET,
                    ]
                }
            ),
        )
    )
    # Unapproved strings inside contract containers MUST be rejected
    # (avoid over-broad container allowlist).
    checks.append(
        _check(
            "scanner_rejects_unapproved_string_in_checklist",
            _has_cat(
                {"checklist": ["compute_loss"]},
                "unapproved_contract_string",
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_debug_string_in_checklist",
            _has_cat(
                {"checklist": ["private candidate text"]},
                "unapproved_contract_string",
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_unapproved_string_in_gate_names",
            _has_cat(
                {"gate_names": ["arbitrary_gate"]},
                "unapproved_contract_string",
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_unapproved_string_in_bucket_names",
            _has_cat(
                {"bucket_names": ["secret_bucket"]},
                "unapproved_contract_string",
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_unapproved_string_in_label_slots",
            _has_cat(
                {"required_label_slots": ["extra_slot"]},
                "unapproved_contract_string",
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_content_sha_in_contract_container",
            _has_cat(
                {"checklist": ["content_sha"]},
                "unapproved_contract_string",
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_query_text_in_contract_container",
            _has_cat(
                {"checklist": ["query_text"]},
                "unapproved_contract_string",
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_packet_ref_in_contract_container",
            _has_cat(
                {"checklist": ["packet_ref"]},
                "unapproved_contract_string",
            ),
        )
    )
    # Field names forbidden as KEYS outside contracts.
    for bad_obj, label in (
        ({"e_score": "E2"}, "e_score"),
        ({"content_sha": "abc"}, "content_sha"),
        ({"query_text": "x"}, "query_text"),
        ({"packet_ref": "x"}, "packet_ref"),
        ({"candidate_text": "x"}, "candidate_text"),
        ({"snippet": "x"}, "snippet"),
        ({"path": "src/foo.rs"}, "path"),
        ({"label_slots": {}}, "label_slots"),
        ({"annotation_instructions": "x"}, "annotation_instructions"),
        ({"rater_id": "x"}, "rater_id"),
        ({"raw_label": "x"}, "raw_label"),
        ({"model_output": "x"}, "model_output"),
        ({"provider_payload": "x"}, "provider_payload"),
    ):
        checks.append(
            _check(
                f"scanner_rejects_{label}_key",
                _has_cat(bad_obj, "forbidden_key"),
            )
        )
    # Field-name tokens forbidden as VALUES outside contracts.
    for tok in (
        "e_score", "s_score", "bucket", "citation_valid",
        "content_sha", "query_text", "candidate_text", "packet_ref",
    ):
        checks.append(
            _check(
                f"scanner_rejects_{tok}_value_outside_contract",
                _has_cat({"x": tok}, "forbidden_field_name_value"),
            )
        )
    # Value-pattern rejections.
    for bad_key in (
        "task_id", "repo_id", "repo", "path", "span", "line_range",
        "start_line", "end_line", "content_sha", "snippet",
        "candidate_text", "query", "query_text", "prompt", "response",
        "model_output", "label", "labels", "raw_label", "annotation_row",
        "rater_id", "annotator_id", "disagreement_example", "per_row_hash",
        "packet_ref", "packet_id", "private_record_ref", "candidate_ref",
        "candidate_bucket_hint", "evidence", "e_score", "s_score",
        "bucket", "label_slots", "annotation_instructions",
        "provider_payload", "api_key",
    ):
        checks.append(
            _check(
                f"scanner_rejects_{bad_key}_key_value_pattern",
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
            _has_cat({"x": _SECRET_SENTINEL}, "sentinel_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_path_like_value",
            _has_cat({"x": "src/foo.rs"}, "path_like_value"),
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
    checks.append(
        _check(
            "scanner_rejects_secret_like_value",
            _has_cat({"x": "api_key=sk-xxx"}, "secret_like_value"),
        )
    )
    # Safe values must NOT be flagged.
    checks.append(
        _check(
            "scanner_allows_pure_digit_count_string",
            not _scan_forbidden({"x": "50"}),
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
            "scanner_allows_safe_schema_version_string",
            not _scan_forbidden({"schema_version": SCHEMA_VERSION}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_safe_status_string",
            not _scan_forbidden({"status": TARGET_STATUS}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_safe_section_id_string",
            not _scan_forbidden({"section": "preconditions"}),
        )
    )

    # --- Group 10: Fail-closed generation on scanner leak. ---
    raised = False
    try:
        _enforce_no_forbidden(
            {"path": "src/foo.rs", "content_sha": "a" * 64,
             "packet_ref": "p1", "query_text": _SECRET_SENTINEL,
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
            "cli_has_no_input_argument",
            "--input" not in cli_opts,
        )
    )
    checks.append(
        _check(
            "cli_has_no_allow_private_argument",
            "--allow-private-source-records" not in cli_opts,
        )
    )
    checks.append(
        _check(
            "cli_only_required_arguments",
            (cli_opts - {"-h", "--help"})
            == {"--self-test", "--out"},
        )
    )
    private_arg = "/tmp/SECRET_RUNBOOK_SENTINEL_private_packets.json"
    private_arg_basename = "SECRET_RUNBOOK_SENTINEL_private_packets.json"
    parser = build_parser()
    stderr = io.StringIO()
    unknown_rejected = False
    unknown_code = None
    with contextlib.redirect_stderr(stderr):
        try:
            parser.parse_args(["--input", private_arg])
        except SystemExit as exc:
            unknown_rejected = True
            unknown_code = exc.code
    unknown_err = stderr.getvalue()
    checks.append(
        _check(
            "cli_unknown_input_argument_rejected",
            unknown_rejected and unknown_code == 2,
        )
    )
    checks.append(
        _check(
            "cli_unknown_input_argument_no_private_path_leak",
            private_arg not in unknown_err
            and private_arg_basename not in unknown_err
            and "SECRET_RUNBOOK_SENTINEL" not in unknown_err
            and "invalid arguments" in unknown_err,
        )
    )

    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class SafeArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that never echoes unknown/private-looking args.

    D4d intentionally has no private input mode. A caller may still pass a
    private-looking ``--input /tmp/...`` by mistake; default argparse would
    echo the unknown argument and value into stderr. Keep the usage line but
    replace the raw error with a fixed generic message.
    """

    def error(self, message: str) -> NoReturn:  # noqa: D401 - argparse signature
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    """Build the D4d CLI parser (protocol-only; no private mode, no --input)."""
    ap = SafeArgumentParser(
        description=(
            "D4d human annotation runbook / checklist protocol "
            "(public protocol-only artifact; no packets read, no raters "
            "recruited, no labels collected)."
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
            "protocol-only runbook artifact)"
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

    # Public protocol-only mode (the only mode; no private mode exists).
    out_path = args.out if args.out is not None else DEFAULT_OUT
    checks, all_passed = run_self_test_checks()
    report = _build_public_report(checks, all_passed)
    # Strict fail-closed guards immediately before writing the JSON artifact.
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
