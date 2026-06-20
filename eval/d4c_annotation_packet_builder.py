#!/usr/bin/env python3
"""D4c Annotation Packet Builder Harness / Blocked Public Artifact.

This module implements the **D4c annotation packet builder harness**.
D4c bridges private source records to future human annotations by
building local/private annotation packets with blank label slots. The
**default committed artifact is a public harness / no-packets artifact**,
NOT a real packet build. D4c must NOT claim annotation packets were
built unless private source records are explicitly supplied and run
locally under ``/tmp``.

D4c **does not** collect labels, **does not** fill label slots, **does
not** create a D4b true-label bundle, **does not** run the packet->bundle
converter, **does not** compute calibration metrics, **does not** perform
model/LLM labeling, **does not** read private source records by default,
**does not** emit provider payloads/API keys/secrets/model outputs, and
**does not** change runtime behavior, retriever, pack, model, backend,
default policy, or EvidenceCore semantics.

Claim boundary (binding):

* This is **eval/diagnostic only**. It is NOT a runtime change, NOT a
  retriever/pack/model/backend/default-policy change, and NOT an
  EvidenceCore semantic change.
* Claim level: ``annotation_packet_builder_harness_only``.
* Status: ``blocked_no_private_source_records_available_or_no_packets_built``;
  mode ``public_harness_no_packets``; phase ``D4c``.
* D4b bundle schema target: ``d4b_true_label_bundle_v1``.
* The default committed artifact reads NO private source records, builds
  NO packets, persists NO packets, fills NO labels, creates NO D4b
  bundle, runs NO converter, computes NO calibration, performs NO
  model/LLM labeling, and passes NO public-release gate.

Two strictly separated modes:

* **D4c default (committed)**: public harness / no-packets artifact. No
  private input. All packet/private/label/bundle/calibration/claim
  flags false; the allowed harness/control flags true; diagnostic flags
  true.

* **D4c private packet builder (opt-in, NOT committed)**: explicit
  ``--allow-private-source-records --input <path> --out /tmp/...``.
  Reads a local/private source-records JSON, builds annotation packets
  with sensitive context preserved (local packet refs, query/candidate
  text, evidence path/spans/snippet/content_sha, annotation
  instructions, blank label slots). Writes ``/tmp`` output only. Never
  serializes input/output paths or basenames. Does NOT fill labels, does
  NOT create a D4b bundle, does NOT run the converter, does NOT compute
  calibration, does NOT perform model/LLM labeling.

Unlike D4b, the D4c private packet output MAY intentionally contain
sensitive context required for human labeling, but ONLY under ``/tmp``
and NEVER committed. The public artifact stays packet-free.

Run::

    python3 -m py_compile eval/d4c_annotation_packet_builder.py
    python3 eval/d4c_annotation_packet_builder.py --self-test
    python3 eval/d4c_annotation_packet_builder.py \
        --out artifacts/d4c_annotation_packet_builder/\
d4c_annotation_packet_builder_report.json
    # D4c private packet builder (NOT committed; /tmp only):
    python3 eval/d4c_annotation_packet_builder.py \
        --allow-private-source-records \
        --input /tmp/private_source_records.json \
        --out /tmp/d4c_annotation_packets.json
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

SCHEMA_VERSION = "d4c_annotation_packet_builder_harness.v1"
GENERATED_BY = "eval/d4c_annotation_packet_builder.py"
CLAIM_LEVEL = "annotation_packet_builder_harness_only"
TARGET_STATUS = (
    "blocked_no_private_source_records_available_or_no_packets_built"
)
MODE_PUBLIC = "public_harness_no_packets"
MODE_PRIVATE = "private_packet_builder_tmp_only"
PHASE = "D4c"
STATUS_PRIVATE_OK = "private_annotation_packets_built_locally"

DEFAULT_OUT = Path(
    "artifacts/d4c_annotation_packet_builder/"
    "d4c_annotation_packet_builder_report.json"
)

# D4c bridges to the D4b true-label bundle schema (target only; the
# converter is NOT run by D4c).
D4B_BUNDLE_SCHEMA_TARGET = "d4b_true_label_bundle_v1"

# Private source-records / packet schemas.
PRIVATE_SOURCE_RECORDS_SCHEMA = "d4c_private_source_records_v1"
PACKET_SCHEMA = "d4c_annotation_packet_v1"

# Fixed sanitized error for any private source-records load/parse/schema/
# privacy failure. Never includes the input path, basename, raw JSON, or
# private text.
PRIVATE_LOAD_ERROR_MESSAGE = (
    "error: failed to load private source records "
    "(schema/privacy/parse error; details suppressed)"
)

# Fixed label slots a human rater must fill (blank/null in packets).
LABEL_SLOTS: tuple[str, ...] = (
    "e_score",
    "s_score",
    "bucket",
    "citation_valid",
    "rater_pair_present",
    "adjudicated",
)

# Fixed E-score / S-score levels (filled-label canary values; must never
# appear as filled values in a packet's annotation slots).
E_SCORE_LEVELS: tuple[str, ...] = ("E0", "E1", "E2")
S_SCORE_LEVELS: tuple[str, ...] = ("S0", "S1", "S2")

# candidate_bucket_hint enum (primary_evidence/dependency_support/
# weak_candidates/abstained/unknown). These are HINTS only, never filled
# label values.
BUCKET_HINTS: tuple[str, ...] = (
    "primary_evidence",
    "dependency_support",
    "weak_candidates",
    "abstained",
    "unknown",
)

# Annotation instructions emitted in private packets only (guidance for
# human raters). Phrased to avoid standalone filled-label canary tokens.
_ANNOTATION_INSTRUCTIONS = (
    "Assign the dual-rubric E-score, S-score, bucket, citation validity, "
    "rater-pair presence, and adjudication per the D3 protocol. Leave "
    "any uncertain slot blank/null. Do not infer from the candidate text."
)

# ---------------------------------------------------------------------------
# Default artifact false flags (all MUST be false in the committed public
# artifact). D4c reads no private source records, builds no packets, fills
# no labels, creates no D4b bundle, runs no converter, computes no
# calibration, performs no model/LLM labeling, and passes no release gate.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "private_source_records_read": False,
    "private_source_records_persisted": False,
    "annotation_packets_built": False,
    "annotation_packets_persisted": False,
    "private_packet_output_written": False,
    "packet_output_path_emitted": False,
    "private_input_path_emitted": False,
    "packet_ids_emitted": False,
    "task_ids_emitted": False,
    "repo_ids_emitted": False,
    "paths_or_spans_emitted": False,
    "snippets_emitted": False,
    "content_sha_emitted": False,
    "query_text_emitted": False,
    "candidate_text_emitted": False,
    "private_packet_output_contains_sensitive_context": False,
    "private_packet_schema_validated": False,
    "private_packet_labels_filled": False,
    "labels_collected": False,
    "true_label_bundle_created": False,
    "d4b_true_label_bundle_validated": False,
    "d4b_bundle_converter_run": False,
    "calibration_metrics_computed": False,
    "model_or_llm_labeling_performed": False,
    "provider_payloads_emitted": False,
    "annotation_instructions_emitted": False,
    "true_e_s_calibration_claimed": False,
    "public_release_gate_passed": False,
}

# Allowed positive harness/control flags (true only for the validated
# harness/controls; each is proven by a self-test). Exactly these; no
# packet-build / label / bundle / calibration claim flags are true in the
# default committed artifact.
HARNESS_CONTROL_FLAGS: dict[str, bool] = {
    "private_packet_builder_harness_available": True,
    "private_cli_guard_validated": True,
    "tmp_output_resolved_guard_validated": True,
    "sanitized_error_guard_validated": True,
    "packet_schema_contract_defined": True,
    "d4b_mapping_contract_defined": True,
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
# Public artifact scanner (strict, fail-closed, with contract allowlist)
# ---------------------------------------------------------------------------

# Top-level keys whose subtrees are explicit contract field-name
# containers. Field-name token strings (e.g. "e_score", "content_sha")
# are allowed as VALUES only inside these containers and nowhere else.
CONTRACT_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "private_source_record_schema_contract",
        "packet_schema_contract",
        "d4b_mapping_contract",
    }
)

# Sensitive field-name tokens that may appear as list-element VALUES
# inside contract containers (e.g. packet_schema_contract.
# required_label_slots), but are forbidden as dict KEYS anywhere and
# forbidden as VALUES outside contract containers.
FIELD_NAME_TOKENS: frozenset[str] = frozenset(
    {
        # label slots
        "e_score",
        "s_score",
        "bucket",
        "citation_valid",
        "rater_pair_present",
        "adjudicated",
        # sensitive packet / source fields
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
# contract container; contract subtrees may expose only approved schema
# identifiers and approved label-slot field-name tokens. Sensitive source
# fields such as content_sha/query_text remain private-input/packet-only and
# are not exposed in the public artifact contracts unless deliberately added
# here in a future reviewed phase.
APPROVED_CONTRACT_STRINGS: frozenset[str] = frozenset(
    {
        PRIVATE_SOURCE_RECORDS_SCHEMA,
        PACKET_SCHEMA,
        D4B_BUNDLE_SCHEMA_TARGET,
        *LABEL_SLOTS,
    }
)

# Sensitive KEY names that must NEVER appear as dict keys anywhere in a
# public artifact JSON. Packet/source-specific superset of the generic
# location/content/identifier/label keys.
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
        "annotator_id", "rater_id", "per_row_hash", "row_hash",
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
        "d4b_bundle_schema_target",
        "schema",
        "target_bundle_schema",
        "output_location",
        "check",
    }
)

# Value patterns that indicate leaked row-level / candidate / packet /
# annotation data. D4c rejects ALL URLs (no URL allowlist) per the
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
_SECRET_SENTINEL = "SECRET_PACKET_SENTINEL"

# content_sha accepted in PRIVATE source input only (32/40/64 hex).
_RE_HEX_SHA = re.compile(
    r"^(?:[A-Fa-f0-9]{32}|[A-Fa-f0-9]{40}|[A-Fa-f0-9]{64})$"
)


def _path_last_key(path: str) -> str:
    """Extract the last key segment from a dotted JSON path."""
    last = path.rsplit(".", 1)[-1]
    return last.split("[")[0]


def _is_safe_value_path(path: str) -> bool:
    """Check if a JSON path ends with a known-safe value key."""
    return _path_last_key(path) in SAFE_VALUE_KEY_NAMES


def _is_inside_contract_container(path: str) -> bool:
    """True iff any ancestor segment of ``path`` is a contract container key.

    Field-name token strings are allowed as VALUES only inside explicit
    contract field-name containers (e.g. packet_schema_contract.
    required_label_slots) and nowhere else.
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
    secret-like strings, path-like strings (``src/foo.py``,
    ``/private/foo.jsonl``), multiline strings, raw JSON fragments, raw
    line-range strings (``12-34``), and the self-test sentinel.

    Field-name tokens (e.g. ``e_score``, ``content_sha``) are allowed as
    VALUES only inside explicit contract field-name containers and
    nowhere else. Allows safe protocol / identity / band strings only.
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
        # Contract containers are exact allowlists: schema identifiers and
        # label-slot field names only. Reject arbitrary short strings such
        # as "compute_loss" or "private candidate text" even if they are
        # nested under a contract container.
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
# Private packet guard (DIFFERENT from the public scanner)
# ---------------------------------------------------------------------------

# Keys that must NEVER appear in a private annotation packet output
# (provider secrets / API keys / provider payloads / model outputs /
# filled-label material). The private packet guard ALLOWS paths/snippets/
# content_sha/query_text/candidate_text/annotation_instructions/blank
# label slots (sensitive context required for human labeling), but
# rejects these provider/model/secret payloads.
PRIVATE_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "api_key", "api_token", "api_secret", "base_url", "provider_key",
        "authorization", "secret",
        "provider_payload", "raw_payload", "api_response", "response_body",
        "model_output", "model_response", "prompt_response",
        "model_assisted_label", "model_assisted_labels",
    }
)

# Filled-label canary values that must never appear as filled annotation
# slot values in a packet (exact match only; substring text is fine).
_FILLED_LABEL_VALUES: frozenset[str] = frozenset(
    set(E_SCORE_LEVELS) | set(S_SCORE_LEVELS)
)


def _find_filled_label_values(obj: Any) -> list[str]:
    """Return any filled E/S level values appearing as exact string values.

    Exact match only (a long instruction string containing "E0" as a
    substring is NOT flagged). Used to prove no annotation slot carries
    a filled E0/E1/E2 / S0/S1/S2 value.
    """
    found: list[str] = []
    if isinstance(obj, dict):
        for value in obj.values():
            found.extend(_find_filled_label_values(value))
    elif isinstance(obj, list):
        for value in obj:
            found.extend(_find_filled_label_values(value))
    elif isinstance(obj, str) and obj in _FILLED_LABEL_VALUES:
        found.append(obj)
    return found


def _find_secret_like_values(obj: Any) -> list[str]:
    """Return any string values that look like provider secrets/API keys.

    The private packet allows sensitive labeling context (paths/snippets/
    content_sha/query/candidate text) but must reject provider secrets,
    API keys, provider payloads, and the self-test sentinel.
    """
    found: list[str] = []
    if isinstance(obj, dict):
        for value in obj.values():
            found.extend(_find_secret_like_values(value))
    elif isinstance(obj, list):
        for value in obj:
            found.extend(_find_secret_like_values(value))
    elif isinstance(obj, str):
        if _RE_SECRET_LIKE.search(obj) or _SECRET_SENTINEL in obj:
            found.append(obj)
    return found


def _validate_one_packet_entry(entry: Any, idx: int) -> list[dict[str, Any]]:
    """Validate a single packet entry: label slots must be blank/null."""
    violations: list[dict[str, Any]] = []
    if not isinstance(entry, dict):
        return [{"category": "packet_entry_not_dict", "idx": idx}]
    slots = entry.get("label_slots")
    if not isinstance(slots, dict):
        violations.append({"category": "missing_label_slots", "idx": idx})
    else:
        for slot in LABEL_SLOTS:
            if slots.get(slot) is not None:
                violations.append(
                    {
                        "category": "label_slot_not_blank",
                        "slot": slot,
                        "idx": idx,
                    }
                )
    return violations


def _validate_private_packet(packet_report: Any) -> list[dict[str, Any]]:
    """Private packet guard (fail-closed).

    Allows sensitive context required for human labeling (local packet
    refs, query/candidate text, evidence path/spans/snippet/content_sha,
    annotation instructions, blank label slots) but enforces:

    * packet schema = d4c_annotation_packet_v1;
    * no provider secrets/API keys/provider payloads/model outputs;
    * no filled E/S label values (E0/E1/E2, S0/S1/S2) anywhere;
    * label slots all blank/null;
    * no D4b bundle created, converter not run, no calibration, no
      model/LLM labeling, labels not filled by builder.

    Returns a list of violation dicts (never the leaked value).
    """
    if not isinstance(packet_report, dict):
        return [{"category": "packet_report_not_dict"}]
    violations: list[dict[str, Any]] = []
    if packet_report.get("schema") != PACKET_SCHEMA:
        violations.append({"category": "wrong_packet_schema"})
    # Forbidden provider/model/secret keys anywhere.
    for bad in PRIVATE_FORBIDDEN_KEYS:
        if _has_dict_key_anywhere(packet_report, bad):
            violations.append(
                {"category": "private_forbidden_key", "key": bad}
            )
    # No filled E/S label values anywhere.
    filled = _find_filled_label_values(packet_report)
    if filled:
        violations.append(
            {"category": "filled_label_value", "count": len(filled)}
        )
    # No provider secrets / API keys / sentinel in any string value.
    secrets = _find_secret_like_values(packet_report)
    if secrets:
        violations.append(
            {"category": "secret_like_value", "count": len(secrets)}
        )
    # Safe flags must be present and false.
    for flag in (
        "d4b_bundle_created",
        "true_label_bundle_created",
        "d4b_bundle_converter_run",
        "calibration_metrics_computed",
        "model_or_llm_labeling_performed",
        "labels_filled_by_builder",
        "provider_payloads_emitted",
    ):
        if packet_report.get(flag) is not False:
            violations.append({"category": f"{flag}_not_false"})
    # Packets list with blank label slots.
    packets = packet_report.get("packets")
    if not isinstance(packets, list):
        violations.append({"category": "missing_packets_list"})
    else:
        for idx, entry in enumerate(packets):
            violations.extend(_validate_one_packet_entry(entry, idx))
    return violations


def _private_packet_guard_summary(
    packet_report: Any,
) -> dict[str, Any]:
    """Run the private packet guard and return a sanitized summary."""
    violations = _validate_private_packet(packet_report)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }

# ---------------------------------------------------------------------------
# Public contracts (category-only; field-name tokens allowed only inside
# contract field-name containers by the public scanner)
# ---------------------------------------------------------------------------


def _build_private_source_record_schema_contract() -> dict[str, Any]:
    """Category-only private source-records schema contract."""
    return {
        "schema": PRIVATE_SOURCE_RECORDS_SCHEMA,
        "private_only": True,
        "may_contain_sensitive_context": True,
    }


def _build_packet_schema_contract() -> dict[str, Any]:
    """Annotation packet schema contract (lists label-slot field names)."""
    return {
        "schema": PACKET_SCHEMA,
        "private_only": True,
        "may_contain_sensitive_context": True,
        "required_label_slots": list(LABEL_SLOTS),
        "target_bundle_schema": D4B_BUNDLE_SCHEMA_TARGET,
    }


def _build_d4b_mapping_contract() -> dict[str, Any]:
    """D4c -> D4b mapping contract (converter not run by D4c)."""
    return {
        "target_bundle_schema": D4B_BUNDLE_SCHEMA_TARGET,
        "packet_label_slots": list(LABEL_SLOTS),
        "packet_to_bundle_requires_manual_transcription_or_local_converter": True,
        "converter_not_run": True,
        "true_label_bundle_created": False,
    }


def _build_private_packet_builder_harness_info() -> dict[str, Any]:
    """Private packet builder harness availability info."""
    return {
        "available": True,
        "opt_in_required": True,
        "output_location": "tmp_only_local_private",
        "committed": False,
        "builds_annotation_packets": True,
        "fills_labels": False,
        "creates_d4b_bundle": False,
        "runs_converter": False,
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


# ---------------------------------------------------------------------------
# Report builders
# ---------------------------------------------------------------------------


def _build_public_report(
    checks: list[dict[str, Any]], all_passed: bool
) -> dict[str, Any]:
    """Assemble the public harness / no-packets report (fail-closed scan).

    The default committed artifact. No private source records read, no
    packets built, no labels filled, no D4b bundle, no calibration, no
    claims.
    """
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": TARGET_STATUS if all_passed else "self_test_failed",
        "mode": MODE_PUBLIC,
        "phase": PHASE,
        "d4b_bundle_schema_target": D4B_BUNDLE_SCHEMA_TARGET,
        "private_source_record_schema_contract":
            _build_private_source_record_schema_contract(),
        "packet_schema_contract": _build_packet_schema_contract(),
        "d4b_mapping_contract": _build_d4b_mapping_contract(),
        "private_packet_builder_harness":
            _build_private_packet_builder_harness_info(),
        "self_test_summary": _self_test_category_summary(checks),
        "self_test_checks": checks,
        "self_test_passed": all_passed,
        "input_attestation_required": False,
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


def _build_private_packet_report(
    *, packets: list[dict[str, Any]]
) -> dict[str, Any]:
    """Assemble the private annotation packet report (NOT committed; /tmp only).

    Contains sensitive context required for human labeling: local packet
    refs, query/candidate text, evidence path/spans/snippet/content_sha,
    annotation instructions, and blank label slots. Does NOT fill labels,
    does NOT create a D4b bundle, does NOT run the converter, does NOT
    compute calibration, does NOT perform model/LLM labeling. Does NOT
    echo input/output paths or basenames.
    """
    report: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": STATUS_PRIVATE_OK,
        "mode": MODE_PRIVATE,
        "phase": PHASE,
        "d4b_bundle_schema_target": D4B_BUNDLE_SCHEMA_TARGET,
        "packets": packets,
        "input_attestation_required": True,
        # Safe flags (required by the private packet contract).
        "private_packet_output": True,
        "public_artifact": False,
        "do_not_commit": True,
        "labels_filled_by_builder": False,
        "d4b_bundle_created": False,
        "d4b_bundle_converter_run": False,
        "true_label_bundle_created": False,
        "calibration_metrics_computed": False,
        "model_or_llm_labeling_performed": False,
        "provider_payloads_emitted": False,
        # Truthful sensitive-context flags (packets contain context).
        "private_source_records_read": True,
        "private_source_records_persisted": False,
        "annotation_packets_built": True,
        "annotation_packets_persisted": True,
        "private_packet_output_written": True,
        "private_packet_output_contains_sensitive_context": True,
        "private_packet_schema_validated": True,
        "private_packet_labels_filled": False,
        "paths_or_spans_emitted": True,
        "snippets_emitted": True,
        "content_sha_emitted": True,
        "query_text_emitted": True,
        "candidate_text_emitted": True,
        "annotation_instructions_emitted": True,
        "packet_ids_emitted": True,
        "task_ids_emitted": False,
        "repo_ids_emitted": False,
        "private_input_path_emitted": False,
        "packet_output_path_emitted": False,
        # No-labels / no-bundle / no-calibration / no-claim flags.
        "labels_collected": False,
        "d4b_true_label_bundle_validated": False,
        "true_e_s_calibration_claimed": False,
        "public_release_gate_passed": False,
        # Harness/control + no-claim + diagnostic flags.
        **HARNESS_CONTROL_FLAGS,
        **NO_CLAIM_FLAGS,
        **DIAGNOSTIC_FLAGS,
    }

    # Private packet guard (fail-closed). Computed on the report before
    # the guard summary field is embedded (no recursion).
    guard = _private_packet_guard_summary(report)
    report["private_packet_guard"] = guard
    if guard["status"] != "pass":
        report["status"] = "fail_private_packet_guard"
    return report


def _private_success_message(report: dict[str, Any]) -> str:
    """Build the private-mode success stdout message (no exact /tmp path)."""
    guard = report.get("private_packet_guard", {})
    return (
        "wrote D4c private annotation packets to /tmp output "
        f"(private_packet_guard={guard.get('status')}, "
        f"annotation_packets_built={report['annotation_packets_built']}, "
        f"private_packet_output_contains_sensitive_context="
        f"{report['private_packet_output_contains_sensitive_context']}, "
        f"labels_filled_by_builder={report['labels_filled_by_builder']}, "
        f"d4b_bundle_created={report['d4b_bundle_created']}, "
        f"calibration_metrics_computed={report['calibration_metrics_computed']}, "
        f"model_or_llm_labeling_performed="
        f"{report['model_or_llm_labeling_performed']}) "
        f"[NOT committed; /tmp only]"
    )


def build_report() -> dict[str, Any]:
    """Assemble the public harness / no-packets report (fail-closed scan).

    Runs the deterministic self-test checks and embeds their results,
    then assembles the full public report (which re-scans itself).
    """
    checks, all_passed = run_self_test_checks()
    return _build_public_report(checks, all_passed)

# ---------------------------------------------------------------------------
# Private source-records schema validation (fail-closed, sanitized)
# ---------------------------------------------------------------------------


class _PrivateSourceLoadError(Exception):
    """Raised when private source records fail schema/privacy/parse checks.

    The CLI never surfaces this exception's message; it always emits the
    fixed sanitized ``PRIVATE_LOAD_ERROR_MESSAGE`` instead.
    """


ALLOWED_SOURCE_TOP_KEYS: frozenset[str] = frozenset({"schema", "records"})
ALLOWED_RECORD_KEYS: frozenset[str] = frozenset(
    {
        "private_record_ref",
        "candidate_ref",
        "query_text",
        "candidate_text",
        "candidate_bucket_hint",
        "evidence",
    }
)
ALLOWED_EVIDENCE_KEYS: frozenset[str] = frozenset(
    {
        "path",
        "start_line",
        "end_line",
        "content_sha",
        "snippet",
    }
)

_REQUIRED_RECORD_STR_FIELDS = (
    "private_record_ref",
    "candidate_ref",
    "query_text",
    "candidate_text",
)


def _is_str(value: Any) -> bool:
    return isinstance(value, str)


def _is_nonneg_int(value: Any) -> bool:
    """True iff ``value`` is a non-bool positive int (>=1)."""
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 1
    )


def _validate_source_records(data: Any) -> None:
    """Validate private source records (fail-closed, sanitized).

    Raises ``_PrivateSourceLoadError`` if malformed, has an unknown
    schema, contains keys outside the allowlist (e.g. provider_payload,
    api_key, secret, model_output, prompt_response, labels/label rows),
    or has wrong-typed / out-of-range values. The loader rejects unknown
    keys rather than supporting and stripping them.
    """
    if not isinstance(data, dict):
        raise _PrivateSourceLoadError()
    for key in data.keys():
        if key not in ALLOWED_SOURCE_TOP_KEYS:
            raise _PrivateSourceLoadError()
    if data.get("schema") != PRIVATE_SOURCE_RECORDS_SCHEMA:
        raise _PrivateSourceLoadError()
    records = data.get("records")
    if not isinstance(records, list) or len(records) == 0:
        raise _PrivateSourceLoadError()
    for rec in records:
        if not isinstance(rec, dict):
            raise _PrivateSourceLoadError()
        if set(rec.keys()) != ALLOWED_RECORD_KEYS:
            raise _PrivateSourceLoadError()
        for str_field in _REQUIRED_RECORD_STR_FIELDS:
            val = rec.get(str_field)
            if not _is_str(val) or not val:
                raise _PrivateSourceLoadError()
        if rec.get("candidate_bucket_hint") not in BUCKET_HINTS:
            raise _PrivateSourceLoadError()
        evidence = rec.get("evidence")
        if not isinstance(evidence, list) or len(evidence) == 0:
            raise _PrivateSourceLoadError()
        for ev in evidence:
            if not isinstance(ev, dict):
                raise _PrivateSourceLoadError()
            if set(ev.keys()) != ALLOWED_EVIDENCE_KEYS:
                raise _PrivateSourceLoadError()
            if not _is_str(ev.get("path")) or not ev.get("path"):
                raise _PrivateSourceLoadError()
            sl = ev.get("start_line")
            el = ev.get("end_line")
            if (
                not isinstance(sl, int)
                or isinstance(sl, bool)
                or sl < 1
                or not isinstance(el, int)
                or isinstance(el, bool)
                or el < 1
            ):
                raise _PrivateSourceLoadError()
            start_line = sl
            end_line = el
            if start_line > end_line:
                raise _PrivateSourceLoadError()
            sha = ev.get("content_sha")
            if not _is_str(sha):
                raise _PrivateSourceLoadError()
            sha_str = str(sha)
            if not _RE_HEX_SHA.fullmatch(sha_str):
                raise _PrivateSourceLoadError()
            if not _is_str(ev.get("snippet")):
                raise _PrivateSourceLoadError()


def build_annotation_packets(
    source_records: dict[str, Any]
) -> list[dict[str, Any]]:
    """Build private annotation packets from validated source records.

    Sensitive context is preserved (local packet refs, query/candidate
    text, evidence path/spans/snippet/content_sha, annotation
    instructions). Label slots are blank/null. No D4b bundle, no
    converter, no labels filled, no calibration, no model/LLM labeling.
    The builder never echoes input/output file paths or basenames into
    the packet metadata.
    """
    packets: list[dict[str, Any]] = []
    for idx, rec in enumerate(source_records["records"]):
        packet_ref = f"local-packet-{idx:04d}"
        packet: dict[str, Any] = {
            "packet_ref": packet_ref,
            "private_record_ref": rec["private_record_ref"],
            "candidate_ref": rec["candidate_ref"],
            "candidate_bucket_hint": rec["candidate_bucket_hint"],
            "query_text": rec["query_text"],
            "candidate_text": rec["candidate_text"],
            "evidence": [
                {
                    "path": ev["path"],
                    "start_line": ev["start_line"],
                    "end_line": ev["end_line"],
                    "content_sha": ev["content_sha"],
                    "snippet": ev["snippet"],
                }
                for ev in rec["evidence"]
            ],
            "annotation_instructions": _ANNOTATION_INSTRUCTIONS,
            "label_slots": {slot: None for slot in LABEL_SLOTS},
        }
        packets.append(packet)
    return packets


# ---------------------------------------------------------------------------
# Default file-based loader / existence probe (injectable for self-test)
# ---------------------------------------------------------------------------


def _default_loader(input_path: Path) -> dict[str, Any]:
    """Read, parse, and validate a private source-records file.

    Raises ``_PrivateSourceLoadError`` on any I/O, parse, or schema
    failure. The CLI converts this into the fixed sanitized error.
    """
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        raise _PrivateSourceLoadError()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        raise _PrivateSourceLoadError()
    _validate_source_records(data)
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
    parent = out_path.parent
    parent_resolved = _resolve(parent)
    if not _is_under_resolved(parent_resolved, tmp_resolved):
        return (
            "private output resolves outside /tmp; refusing to write "
            "private-mode output"
        )
    try:
        is_link = out_path.is_symlink()
    except OSError:
        is_link = False
    if is_link:
        return (
            "private output path is a symlink; refusing to write "
            "private-mode output"
        )
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
    allow_private: bool,
    input_path: Path | None,
    out_path: Path | None,
) -> str | None:
    """Validate CLI argument combinations for public vs private builder.

    Pure: performs NO filesystem I/O (only lexical path checks). Returns
    an error message string if invalid, or ``None`` if valid. The guards
    below are evaluated BEFORE the input is opened or stat'd, proving
    validate-before-read.

    * ``--input`` without ``--allow-private-source-records`` -> error.
    * ``--allow-private-source-records`` without ``--input`` -> error.
    * ``--allow-private-source-records`` without explicit ``--out`` ->
      error.
    * ``--allow-private-source-records`` with the committed artifact path
      as ``--out`` -> error (before read).
    * ``--allow-private-source-records`` with a non-``/tmp`` ``--out`` ->
      error (before read).
    * ``--allow-private-source-records --input <path> --out /tmp/...`` ->
      valid.
    """
    if input_path is not None and not allow_private:
        return (
            "--input requires --allow-private-source-records; refusing to "
            "read private source records without explicit opt-in"
        )
    if allow_private and input_path is None:
        return (
            "--allow-private-source-records requires --input; no private "
            "input path provided"
        )
    if allow_private:
        if out_path is None:
            return (
                "--allow-private-source-records requires explicit --out "
                "under /tmp; refusing to use the committed artifact path"
            )
        if _is_committed_out(out_path):
            return (
                "--allow-private-source-records requires --out under /tmp; "
                "refusing to write to the committed artifact path"
            )
        if not _is_under_tmp(out_path):
            return (
                "--allow-private-source-records requires --out under /tmp; "
                "refusing to write private-mode output elsewhere"
            )
    return None


# ---------------------------------------------------------------------------
# Private packet builder runner (validate-before-read; resolved /tmp guard;
# sanitized errors)
# ---------------------------------------------------------------------------


def _run_private_packet_mode(
    *,
    allow_private: bool,
    input_path: Path | None,
    out_path: Path | None,
    loader: Any,
    input_exists: Any,
    tmp_guard: Any = _validate_resolved_tmp_guard,
) -> tuple[dict[str, Any] | None, str | None]:
    """Run the private annotation packet builder.

    Returns ``(report, error)``: exactly one is non-``None``.

    The CLI/output guards are validated BEFORE the input is opened or
    stat'd (validate-before-read): lexical CLI args first (no filesystem),
    then the resolved ``/tmp`` guard (filesystem on the OUTPUT path only).
    Any load/parse/schema failure returns the fixed sanitized error; the
    input path, basename, raw JSON, and private text are never surfaced.
    """
    err = _validate_cli_args(
        allow_private=allow_private,
        input_path=input_path,
        out_path=out_path,
    )
    if err is not None:
        # Lexical validation failed: NO input or output filesystem access
        # performed.
        return None, err
    assert input_path is not None and out_path is not None
    err = tmp_guard(out_path)
    if err is not None:
        # Output guard failed: NO input access performed.
        return None, err
    # Output guard passed: the input may now be touched.
    if not input_exists(input_path):
        return None, PRIVATE_LOAD_ERROR_MESSAGE
    try:
        source_records = loader(input_path)
    except Exception:
        return None, PRIVATE_LOAD_ERROR_MESSAGE
    # Re-validate the loaded source records (the real loader validates
    # internally and raises; this also covers in-memory probes that
    # return unvalidated data). Fail-closed sanitized error.
    try:
        _validate_source_records(source_records)
    except _PrivateSourceLoadError:
        return None, PRIVATE_LOAD_ERROR_MESSAGE
    packets = build_annotation_packets(source_records)
    report = _build_private_packet_report(packets=packets)
    return report, None

# ---------------------------------------------------------------------------
# Self-test probe (records every input access for validate-before-read)
# ---------------------------------------------------------------------------


class _ReadProbe:
    """Records every loader/exists call to prove validate-before-read."""

    def __init__(self, records: dict[str, Any] | None = None) -> None:
        self.calls: list[tuple[str, str]] = []
        self._records = records

    def loader(self, path: Path) -> dict[str, Any]:
        self.calls.append(("load", str(path)))
        if self._records is None:
            raise _PrivateSourceLoadError("probe: should not be called")
        return self._records

    def exists(self, path: Path) -> bool:
        self.calls.append(("exists", str(path)))
        return self._records is not None


# ---------------------------------------------------------------------------
# Self-test checks (pure, no I/O except in-memory probes and explicit
# /tmp symlink fixtures with cleanup)
# ---------------------------------------------------------------------------


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return {"check": name, "passed": bool(ok)}


def _valid_synthetic_source_records(
    *,
    record_count: int = 3,
) -> dict[str, Any]:
    """Build synthetic private source records for harness self-tests.

    Contains sensitive context (paths/snippets/content_sha/query/
    candidate text) on purpose, to prove the private packet preserves it
    while the public artifact stays packet-free.
    """
    records: list[dict[str, Any]] = []
    hints = list(BUCKET_HINTS)
    for i in range(record_count):
        records.append(
            {
                "private_record_ref": f"local-record-{i:04d}",
                "candidate_ref": f"local-candidate-{i:04d}",
                "query_text": f"private query text for record {i}",
                "candidate_text": f"private candidate text for record {i}",
                "candidate_bucket_hint": hints[i % len(hints)],
                "evidence": [
                    {
                        "path": f"src/lib/module_{i}.rs",
                        "start_line": 10 + i,
                        "end_line": 20 + i,
                        "content_sha": ("a" * 64),
                        "snippet": (
                            f"// record {i} line one\n"
                            f"// record {i} line two\n"
                            f"// record {i} line three"
                        ),
                    }
                ],
            }
        )
    return {
        "schema": PRIVATE_SOURCE_RECORDS_SCHEMA,
        "records": records,
    }


def _symlink_selftest_workspace() -> Path:
    """Create a unique /tmp workspace dir for symlink self-test fixtures."""
    pid = os.getpid()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    ws = Path("/tmp") / f"d4c_selftest_{pid}_{ts}"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all D4c self-test groups. Returns (checks, all_passed)."""
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
    for flag in HARNESS_CONTROL_FLAGS:
        checks.append(
            _check(
                f"harness_control_{flag}_true",
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
    checks.append(
        _check(
            "default_input_attestation_required_false",
            skeleton["input_attestation_required"] is False,
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
            "mode_public_harness_no_packets",
            skeleton["mode"] == MODE_PUBLIC,
        )
    )
    checks.append(
        _check("phase_d4c", skeleton["phase"] == PHASE)
    )
    checks.append(
        _check(
            "d4b_bundle_schema_target_correct",
            skeleton["d4b_bundle_schema_target"]
            == D4B_BUNDLE_SCHEMA_TARGET,
        )
    )
    checks.append(
        _check(
            "packet_schema_contract_defined_true",
            skeleton["packet_schema_contract_defined"] is True,
        )
    )
    checks.append(
        _check(
            "d4b_mapping_contract_defined_true",
            skeleton["d4b_mapping_contract_defined"] is True,
        )
    )
    checks.append(
        _check(
            "private_source_record_schema_contract_category_only",
            skeleton["private_source_record_schema_contract"]["schema"]
            == PRIVATE_SOURCE_RECORDS_SCHEMA
            and skeleton["private_source_record_schema_contract"][
                "private_only"
            ]
            is True
            and skeleton["private_source_record_schema_contract"][
                "may_contain_sensitive_context"
            ]
            is True,
        )
    )
    checks.append(
        _check(
            "packet_schema_contract_has_schema_and_label_slots",
            skeleton["packet_schema_contract"]["schema"] == PACKET_SCHEMA
            and skeleton["packet_schema_contract"]["private_only"] is True
            and skeleton["packet_schema_contract"][
                "may_contain_sensitive_context"
            ]
            is True
            and skeleton["packet_schema_contract"]["required_label_slots"]
            == list(LABEL_SLOTS)
            and skeleton["packet_schema_contract"]["target_bundle_schema"]
            == D4B_BUNDLE_SCHEMA_TARGET,
        )
    )
    checks.append(
        _check(
            "d4b_mapping_contract_converter_not_run",
            skeleton["d4b_mapping_contract"]["target_bundle_schema"]
            == D4B_BUNDLE_SCHEMA_TARGET
            and skeleton["d4b_mapping_contract"]["packet_label_slots"]
            == list(LABEL_SLOTS)
            and skeleton["d4b_mapping_contract"][
                "packet_to_bundle_requires_manual_transcription_or_local_converter"
            ]
            is True
            and skeleton["d4b_mapping_contract"]["converter_not_run"] is True
            and skeleton["d4b_mapping_contract"][
                "true_label_bundle_created"
            ]
            is False,
        )
    )
    checks.append(
        _check(
            "private_packet_builder_harness_tmp_only_not_committed",
            skeleton["private_packet_builder_harness"]["available"] is True
            and skeleton["private_packet_builder_harness"]["opt_in_required"]
            is True
            and skeleton["private_packet_builder_harness"]["output_location"]
            == "tmp_only_local_private"
            and skeleton["private_packet_builder_harness"]["committed"]
            is False
            and skeleton["private_packet_builder_harness"][
                "fills_labels"
            ]
            is False
            and skeleton["private_packet_builder_harness"][
                "creates_d4b_bundle"
            ]
            is False,
        )
    )

    # --- Group 3: Public scanner fail-closes + contract allowlist. ---
    def _has_cat(obj: Any, cat: str) -> bool:
        return any(v["category"] == cat for v in _scan_forbidden(obj))

    # Contract allowlist: field-name tokens ALLOWED as values inside
    # explicit contract field-name containers.
    checks.append(
        _check(
            "scanner_allows_label_slot_in_packet_schema_contract",
            not _scan_forbidden(
                {
                    "packet_schema_contract": {
                        "required_label_slots": ["e_score"]
                    }
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_all_label_slots_in_contract",
            not _scan_forbidden(
                {
                    "packet_schema_contract": {
                        "required_label_slots": list(LABEL_SLOTS)
                    },
                    "d4b_mapping_contract": {
                        "packet_label_slots": list(LABEL_SLOTS)
                    },
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_private_source_schema_in_contract_container",
            not _scan_forbidden(
                {
                    "private_source_record_schema_contract": {
                        "schema": PRIVATE_SOURCE_RECORDS_SCHEMA,
                        "private_only": True,
                        "may_contain_sensitive_context": True,
                    }
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_unapproved_label_slot_in_contract",
            _has_cat(
                {
                    "packet_schema_contract": {
                        "required_label_slots": ["compute_loss"]
                    }
                },
                "unapproved_contract_string",
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_debug_string_in_contract",
            _has_cat(
                {
                    "d4b_mapping_contract": {
                        "debug": "private candidate text"
                    }
                },
                "unapproved_contract_string",
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_content_sha_string_in_contract_until_approved",
            _has_cat(
                {
                    "private_source_record_schema_contract": {
                        "field_names": ["content_sha"]
                    }
                },
                "unapproved_contract_string",
            ),
        )
    )
    # Contract reject: field names forbidden as KEYS outside contracts.
    for bad_obj, label in (
        ({"e_score": "E2"}, "e_score"),
        ({"content_sha": "abc"}, "content_sha"),
        ({"query_text": "..."}, "query_text"),
        ({"packet_ref": "..."}, "packet_ref"),
        ({"candidate_text": "..."}, "candidate_text"),
        ({"snippet": "..."}, "snippet"),
        ({"path": "src/foo.rs"}, "path"),
        ({"label_slots": {}}, "label_slots"),
        ({"annotation_instructions": "..."}, "annotation_instructions"),
        ({"private_record_ref": "..."}, "private_record_ref"),
    ):
        checks.append(
            _check(
                f"scanner_rejects_{label}_key_outside_contract",
                _has_cat(bad_obj, "forbidden_key"),
            )
        )
    # Field-name tokens forbidden as VALUES outside contracts.
    checks.append(
        _check(
            "scanner_rejects_e_score_value_outside_contract",
            _has_cat({"some_key": "e_score"}, "forbidden_field_name_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_content_sha_value_outside_contract",
            _has_cat({"x": ["content_sha"]}, "forbidden_field_name_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_query_text_value_outside_contract",
            _has_cat({"x": "query_text"}, "forbidden_field_name_value"),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_packet_ref_value_outside_contract",
            _has_cat({"x": "packet_ref"}, "forbidden_field_name_value"),
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
            "scanner_allows_safe_d4b_bundle_schema_target_string",
            not _scan_forbidden(
                {"d4b_bundle_schema_target": D4B_BUNDLE_SCHEMA_TARGET}
            ),
        )
    )

    # --- Group 3b: Fail-closed generation on scanner leak. ---
    raised = False
    try:
        _enforce_no_forbidden(
            {"path": "src/foo.rs", "content_sha": "a" * 64,
             "packet_ref": "p1", "query_text": "SECRET_PACKET_SENTINEL",
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

    # --- Group 4: Private source-records schema validation. ---
    # Valid source records validate.
    valid_ok = True
    try:
        _validate_source_records(_valid_synthetic_source_records())
    except _PrivateSourceLoadError:
        valid_ok = False
    checks.append(
        _check("valid_source_records_validate", valid_ok)
    )
    # Unknown schema rejected.
    bad_schema_rejected = False
    try:
        _validate_source_records(
            {**_valid_synthetic_source_records(), "schema": "wrong_schema"}
        )
    except _PrivateSourceLoadError:
        bad_schema_rejected = True
    checks.append(
        _check("unknown_source_schema_rejected", bad_schema_rejected)
    )
    # Non-dict rejected.
    non_dict_rejected = False
    try:
        _validate_source_records([1, 2, 3])  # type: ignore[arg-type]
    except _PrivateSourceLoadError:
        non_dict_rejected = True
    checks.append(
        _check("non_dict_source_rejected", non_dict_rejected)
    )
    # Empty records list rejected.
    empty_rejected = False
    try:
        _validate_source_records(
            {**_valid_synthetic_source_records(), "records": []}
        )
    except _PrivateSourceLoadError:
        empty_rejected = True
    checks.append(
        _check("empty_records_rejected", empty_rejected)
    )
    # Unknown top-level key rejected.
    extra_top_rejected = False
    try:
        _validate_source_records(
            {**_valid_synthetic_source_records(), "extra": 1}
        )
    except _PrivateSourceLoadError:
        extra_top_rejected = True
    checks.append(
        _check("unknown_top_key_rejected", extra_top_rejected)
    )
    # Record with extra key (provider_payload) rejected.
    extra_rec_rejected = False
    try:
        recs = _valid_synthetic_source_records()
        recs = {
            **recs,
            "records": [
                {**recs["records"][0], "provider_payload": {"x": 1}}
            ],
        }
        _validate_source_records(recs)
    except _PrivateSourceLoadError:
        extra_rec_rejected = True
    checks.append(
        _check("record_with_provider_payload_rejected", extra_rec_rejected)
    )
    # Record with api_key rejected.
    api_key_rejected = False
    try:
        recs = _valid_synthetic_source_records()
        recs = {
            **recs,
            "records": [
                {**recs["records"][0], "api_key": "sk-SECRET_PACKET_SENTINEL"}
            ],
        }
        _validate_source_records(recs)
    except _PrivateSourceLoadError:
        api_key_rejected = True
    checks.append(
        _check("record_with_api_key_rejected", api_key_rejected)
    )
    # Record with secret rejected.
    secret_rejected = False
    try:
        recs = _valid_synthetic_source_records()
        recs = {
            **recs,
            "records": [{**recs["records"][0], "secret": "x"}],
        }
        _validate_source_records(recs)
    except _PrivateSourceLoadError:
        secret_rejected = True
    checks.append(
        _check("record_with_secret_rejected", secret_rejected)
    )
    # Record with model_output rejected.
    model_out_rejected = False
    try:
        recs = _valid_synthetic_source_records()
        recs = {
            **recs,
            "records": [{**recs["records"][0], "model_output": "x"}],
        }
        _validate_source_records(recs)
    except _PrivateSourceLoadError:
        model_out_rejected = True
    checks.append(
        _check("record_with_model_output_rejected", model_out_rejected)
    )
    # Record with prompt_response rejected.
    prompt_resp_rejected = False
    try:
        recs = _valid_synthetic_source_records()
        recs = {
            **recs,
            "records": [{**recs["records"][0], "prompt_response": "x"}],
        }
        _validate_source_records(recs)
    except _PrivateSourceLoadError:
        prompt_resp_rejected = True
    checks.append(
        _check("record_with_prompt_response_rejected", prompt_resp_rejected)
    )
    # Record with labels rejected.
    labels_rejected = False
    try:
        recs = _valid_synthetic_source_records()
        recs = {
            **recs,
            "records": [{**recs["records"][0], "labels": [{"e_score": "E0"}]}],
        }
        _validate_source_records(recs)
    except _PrivateSourceLoadError:
        labels_rejected = True
    checks.append(
        _check("record_with_labels_rejected", labels_rejected)
    )
    # Missing record field rejected.
    missing_field_rejected = False
    try:
        recs = _valid_synthetic_source_records()
        bad_rec = dict(recs["records"][0])
        del bad_rec["query_text"]
        recs = {**recs, "records": [bad_rec]}
        _validate_source_records(recs)
    except _PrivateSourceLoadError:
        missing_field_rejected = True
    checks.append(
        _check("record_missing_field_rejected", missing_field_rejected)
    )
    # Invalid candidate_bucket_hint rejected.
    bad_hint_rejected = False
    try:
        recs = _valid_synthetic_source_records()
        recs = {
            **recs,
            "records": [
                {**recs["records"][0], "candidate_bucket_hint": "nope"}
            ],
        }
        _validate_source_records(recs)
    except _PrivateSourceLoadError:
        bad_hint_rejected = True
    checks.append(
        _check("invalid_bucket_hint_rejected", bad_hint_rejected)
    )
    # Empty query_text rejected.
    empty_q_rejected = False
    try:
        recs = _valid_synthetic_source_records()
        recs = {
            **recs,
            "records": [{**recs["records"][0], "query_text": ""}],
        }
        _validate_source_records(recs)
    except _PrivateSourceLoadError:
        empty_q_rejected = True
    checks.append(
        _check("empty_query_text_rejected", empty_q_rejected)
    )
    # start_line > end_line rejected.
    line_order_rejected = False
    try:
        recs = _valid_synthetic_source_records()
        ev = dict(recs["records"][0]["evidence"][0])
        ev["start_line"] = 50
        ev["end_line"] = 10
        recs = {
            **recs,
            "records": [
                {**recs["records"][0], "evidence": [ev]}
            ],
        }
        _validate_source_records(recs)
    except _PrivateSourceLoadError:
        line_order_rejected = True
    checks.append(
        _check("start_line_greater_than_end_line_rejected", line_order_rejected)
    )
    # Non-integer start_line rejected.
    bad_line_rejected = False
    try:
        recs = _valid_synthetic_source_records()
        ev = dict(recs["records"][0]["evidence"][0])
        ev["start_line"] = 0
        recs = {
            **recs,
            "records": [
                {**recs["records"][0], "evidence": [ev]}
            ],
        }
        _validate_source_records(recs)
    except _PrivateSourceLoadError:
        bad_line_rejected = True
    checks.append(
        _check("non_positive_start_line_rejected", bad_line_rejected)
    )
    # Invalid content_sha (not 32/40/64 hex) rejected.
    bad_sha_rejected = False
    try:
        recs = _valid_synthetic_source_records()
        ev = dict(recs["records"][0]["evidence"][0])
        ev["content_sha"] = "not-a-hex"
        recs = {
            **recs,
            "records": [
                {**recs["records"][0], "evidence": [ev]}
            ],
        }
        _validate_source_records(recs)
    except _PrivateSourceLoadError:
        bad_sha_rejected = True
    checks.append(
        _check("invalid_content_sha_rejected", bad_sha_rejected)
    )
    # 40-hex content_sha accepted.
    sha40_ok = True
    try:
        recs = _valid_synthetic_source_records()
        ev = dict(recs["records"][0]["evidence"][0])
        ev["content_sha"] = "f" * 40
        recs = {
            **recs,
            "records": [
                {**recs["records"][0], "evidence": [ev]}
            ],
        }
        _validate_source_records(recs)
    except _PrivateSourceLoadError:
        sha40_ok = False
    checks.append(
        _check("content_sha_40_hex_accepted", sha40_ok)
    )
    # Evidence with extra key rejected.
    extra_ev_rejected = False
    try:
        recs = _valid_synthetic_source_records()
        ev = {**recs["records"][0]["evidence"][0], "extra": 1}
        recs = {
            **recs,
            "records": [
                {**recs["records"][0], "evidence": [ev]}
            ],
        }
        _validate_source_records(recs)
    except _PrivateSourceLoadError:
        extra_ev_rejected = True
    checks.append(
        _check("evidence_with_extra_key_rejected", extra_ev_rejected)
    )
    # Empty evidence list rejected.
    empty_ev_rejected = False
    try:
        recs = _valid_synthetic_source_records()
        recs = {
            **recs,
            "records": [{**recs["records"][0], "evidence": []}],
        }
        _validate_source_records(recs)
    except _PrivateSourceLoadError:
        empty_ev_rejected = True
    checks.append(
        _check("empty_evidence_rejected", empty_ev_rejected)
    )

    # --- Group 5: CLI guard matrix (pure lexical). ---
    sensitive_input = Path("/private/SECRET_PACKET_SENTINEL_sensitive.json")
    # --input without --allow-private-source-records => error.
    err_input_no_allow = _validate_cli_args(
        allow_private=False,
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
            and _SECRET_SENTINEL not in err_input_no_allow,
        )
    )
    # --allow-private-source-records without --input => error.
    err_allow_no_input = _validate_cli_args(
        allow_private=True,
        input_path=None,
        out_path=Path("/tmp/d4c.json"),
    )
    checks.append(
        _check(
            "cli_allow_without_input_rejected",
            err_allow_no_input is not None,
        )
    )
    # allow + input but no explicit out => error.
    err_no_out = _validate_cli_args(
        allow_private=True,
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
            and _SECRET_SENTINEL not in err_no_out,
        )
    )
    # allow + committed artifact out => error.
    err_committed = _validate_cli_args(
        allow_private=True,
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
            and _SECRET_SENTINEL not in err_committed,
        )
    )
    # allow + non-/tmp out => error.
    err_non_tmp = _validate_cli_args(
        allow_private=True,
        input_path=sensitive_input,
        out_path=Path("/not/tmp/d4c.json"),
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
            and _SECRET_SENTINEL not in err_non_tmp,
        )
    )
    # allow + /tmp out => valid.
    err_tmp_ok = _validate_cli_args(
        allow_private=True,
        input_path=sensitive_input,
        out_path=Path("/tmp/d4c_packets.json"),
    )
    checks.append(
        _check(
            "cli_allow_tmp_out_allowed",
            err_tmp_ok is None,
        )
    )
    # default mode (no private args) => valid.
    err_default = _validate_cli_args(
        allow_private=False,
        input_path=None,
        out_path=None,
    )
    checks.append(
        _check("cli_default_mode_allowed", err_default is None)
    )
    # path traversal /tmp/../etc is NOT under /tmp.
    err_traversal = _validate_cli_args(
        allow_private=True,
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
    _report, err_probe = _run_private_packet_mode(
        allow_private=True,
        input_path=Path("/private/SECRET_PACKET_SENTINEL_nonexistent.json"),
        out_path=Path("/not/tmp/d4c.json"),  # invalid out (lexical)
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
            and _SECRET_SENTINEL not in err_probe
            and "nonexistent.json" not in err_probe,
        )
    )
    # Committed-out rejected before read.
    probe_committed = _ReadProbe()
    _report2, err_pc = _run_private_packet_mode(
        allow_private=True,
        input_path=Path("/private/SECRET_PACKET_SENTINEL.json"),
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
    _report3, err_pn = _run_private_packet_mode(
        allow_private=True,
        input_path=Path("/private/SECRET_PACKET_SENTINEL.json"),
        out_path=Path("/home/user/d4c.json"),
        loader=probe_nontmp.loader,
        input_exists=probe_nontmp.exists,
    )
    checks.append(
        _check(
            "non_tmp_out_rejected_before_read",
            err_pn is not None and probe_nontmp.calls == [],
        )
    )
    # Input without allow rejected before read.
    probe_input_only = _ReadProbe()
    _report4, err_pio = _run_private_packet_mode(
        allow_private=False,
        input_path=Path("/private/SECRET_PACKET_SENTINEL.json"),
        out_path=None,
        loader=probe_input_only.loader,
        input_exists=probe_input_only.exists,
    )
    checks.append(
        _check(
            "input_without_allow_rejected_before_read",
            err_pio is not None and probe_input_only.calls == [],
        )
    )

    # --- Group 7: Sanitized error with sensitive basename + sentinel. ---
    # Malformed source records (extra keys + sentinel) returned by a
    # loader: the schema validator must reject it and only the fixed
    # sanitized error is surfaced; nothing reaches the report.
    malformed_records = {
        "schema": PRIVATE_SOURCE_RECORDS_SCHEMA,
        "records": [
            {
                "private_record_ref": "r1",
                "candidate_ref": "c1",
                "query_text": "q",
                "candidate_text": "ct",
                "candidate_bucket_hint": "primary_evidence",
                "evidence": [],
                "provider_payload": {"x": _SECRET_SENTINEL},
                "api_key": "sk-SECRET_PACKET_SENTINEL",
            }
        ],
    }
    probe_malformed = _ReadProbe(records=malformed_records)
    _report5, err_malformed = _run_private_packet_mode(
        allow_private=True,
        input_path=Path("/private/SECRET_PACKET_SENTINEL_bundle.json"),
        out_path=Path("/tmp/d4c_malformed.json"),
        loader=probe_malformed.loader,
        input_exists=probe_malformed.exists,
    )
    checks.append(
        _check(
            "malformed_records_returns_sanitized_error",
            err_malformed == PRIVATE_LOAD_ERROR_MESSAGE
            and _report5 is None,
        )
    )
    checks.append(
        _check(
            "malformed_records_error_no_sentinel_or_basename",
            err_malformed is not None
            and _SECRET_SENTINEL not in err_malformed
            and "SECRET_PACKET_SENTINEL_bundle.json" not in err_malformed
            and "sk-" not in err_malformed,
        )
    )
    # Nonexistent input returns the sanitized error (no path leak).
    probe_missing = _ReadProbe(records=None)
    probe_missing.exists = lambda p: False  # type: ignore[method-assign]
    _report6, err_missing = _run_private_packet_mode(
        allow_private=True,
        input_path=Path("/private/SECRET_PACKET_SENTINEL_missing.json"),
        out_path=Path("/tmp/d4c_missing.json"),
        loader=probe_missing.loader,
        input_exists=probe_missing.exists,
    )
    checks.append(
        _check(
            "missing_input_returns_sanitized_error",
            err_missing == PRIVATE_LOAD_ERROR_MESSAGE
            and _report6 is None,
        )
    )
    checks.append(
        _check(
            "missing_input_error_no_path_basename_leak",
            err_missing is not None
            and _SECRET_SENTINEL not in err_missing
            and "SECRET_PACKET_SENTINEL_missing.json" not in err_missing,
        )
    )

    # --- Group 8: Private packet success path (synthetic source records) ---
    # sensitive context present in /tmp private output but NOT in public
    # artifact; label slots blank; no filled labels; no D4b bundle; no
    # calibration/model labeling; no exact input/output path/basename in
    # metadata/stdout. ---
    valid_records = _valid_synthetic_source_records()
    sensitive_in = Path("/private/SECRET_PACKET_SENTINEL_success.json")
    sensitive_out = Path("/tmp/SECRET_PACKET_SENTINEL_out.json")
    probe_ok = _ReadProbe(records=valid_records)
    report_ok, err_ok = _run_private_packet_mode(
        allow_private=True,
        input_path=sensitive_in,
        out_path=sensitive_out,
        loader=probe_ok.loader,
        input_exists=probe_ok.exists,
    )
    checks.append(
        _check(
            "private_success_returns_report",
            err_ok is None and report_ok is not None,
        )
    )
    ok_blob = json.dumps(report_ok, sort_keys=True) if report_ok else ""
    # Sensitive context PRESENT in private packet output.
    checks.append(
        _check(
            "private_report_contains_sensitive_paths",
            report_ok is not None
            and _has_dict_key_anywhere(report_ok, "path"),
        )
    )
    checks.append(
        _check(
            "private_report_contains_snippets",
            report_ok is not None
            and _has_dict_key_anywhere(report_ok, "snippet"),
        )
    )
    checks.append(
        _check(
            "private_report_contains_content_sha",
            report_ok is not None
            and _has_dict_key_anywhere(report_ok, "content_sha"),
        )
    )
    checks.append(
        _check(
            "private_report_contains_query_text",
            report_ok is not None
            and _has_dict_key_anywhere(report_ok, "query_text"),
        )
    )
    checks.append(
        _check(
            "private_report_contains_candidate_text",
            report_ok is not None
            and _has_dict_key_anywhere(report_ok, "candidate_text"),
        )
    )
    checks.append(
        _check(
            "private_report_contains_annotation_instructions",
            report_ok is not None
            and _has_dict_key_anywhere(report_ok, "annotation_instructions"),
        )
    )
    checks.append(
        _check(
            "private_report_contains_local_packet_refs",
            report_ok is not None
            and _has_dict_key_anywhere(report_ok, "packet_ref"),
        )
    )
    # Sensitive context NOT in public artifact.
    public_skeleton = _build_public_report([], True)
    pub_blob = json.dumps(public_skeleton, sort_keys=True)
    checks.append(
        _check(
            "public_report_has_no_path_key",
            not _has_dict_key_anywhere(public_skeleton, "path"),
        )
    )
    checks.append(
        _check(
            "public_report_has_no_snippet_key",
            not _has_dict_key_anywhere(public_skeleton, "snippet"),
        )
    )
    checks.append(
        _check(
            "public_report_has_no_content_sha_key",
            not _has_dict_key_anywhere(public_skeleton, "content_sha"),
        )
    )
    checks.append(
        _check(
            "public_report_has_no_query_text_key",
            not _has_dict_key_anywhere(public_skeleton, "query_text"),
        )
    )
    checks.append(
        _check(
            "public_report_has_no_candidate_text_key",
            not _has_dict_key_anywhere(public_skeleton, "candidate_text"),
        )
    )
    checks.append(
        _check(
            "public_report_has_no_packet_ref_key",
            not _has_dict_key_anywhere(public_skeleton, "packet_ref"),
        )
    )
    checks.append(
        _check(
            "public_report_has_no_packets_list",
            not _has_dict_key_anywhere(public_skeleton, "packets"),
        )
    )
    checks.append(
        _check(
            "public_report_has_no_label_slots",
            not _has_dict_key_anywhere(public_skeleton, "label_slots"),
        )
    )
    # No input/output path or basename in private metadata.
    checks.append(
        _check(
            "private_report_no_sentinel",
            _SECRET_SENTINEL not in ok_blob,
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
    # Success stdout message has no exact path.
    msg = _private_success_message(report_ok) if report_ok else ""
    checks.append(
        _check(
            "private_success_message_no_input_path",
            str(sensitive_in) not in msg
            and sensitive_in.name not in msg
            and _SECRET_SENTINEL not in msg,
        )
    )
    checks.append(
        _check(
            "private_success_message_no_output_path",
            str(sensitive_out) not in msg
            and sensitive_out.name not in msg,
        )
    )
    # Label slots blank/null; no filled E/S values.
    checks.append(
        _check(
            "private_report_label_slots_all_null",
            report_ok is not None
            and all(
                isinstance(p, dict)
                and isinstance(p.get("label_slots"), dict)
                and all(p["label_slots"].get(s) is None for s in LABEL_SLOTS)
                for p in report_ok["packets"]
            ),
        )
    )
    checks.append(
        _check(
            "private_report_no_filled_label_values",
            not _find_filled_label_values(report_ok),
        )
    )
    # No D4b bundle / converter / calibration / model labeling / labels.
    checks.append(
        _check(
            "private_report_no_d4b_bundle_or_labels",
            report_ok is not None
            and report_ok["d4b_bundle_created"] is False
            and report_ok["true_label_bundle_created"] is False
            and report_ok["d4b_bundle_converter_run"] is False
            and report_ok["calibration_metrics_computed"] is False
            and report_ok["model_or_llm_labeling_performed"] is False
            and report_ok["labels_filled_by_builder"] is False
            and report_ok["labels_collected"] is False
            and report_ok["provider_payloads_emitted"] is False
            and report_ok["true_e_s_calibration_claimed"] is False
            and report_ok["public_release_gate_passed"] is False,
        )
    )
    # Safe flags present and correct.
    checks.append(
        _check(
            "private_report_safe_flags",
            report_ok is not None
            and report_ok["private_packet_output"] is True
            and report_ok["public_artifact"] is False
            and report_ok["do_not_commit"] is True
            and report_ok["labels_filled_by_builder"] is False
            and report_ok["d4b_bundle_created"] is False
            and report_ok["calibration_metrics_computed"] is False
            and report_ok["model_or_llm_labeling_performed"] is False,
        )
    )
    # Truthful sensitive-context flags true.
    checks.append(
        _check(
            "private_report_truthful_sensitive_flags",
            report_ok is not None
            and report_ok["annotation_packets_built"] is True
            and report_ok["private_source_records_read"] is True
            and report_ok["private_packet_output_written"] is True
            and report_ok["private_packet_output_contains_sensitive_context"]
            is True
            and report_ok["private_packet_schema_validated"] is True
            and report_ok["paths_or_spans_emitted"] is True
            and report_ok["snippets_emitted"] is True
            and report_ok["content_sha_emitted"] is True
            and report_ok["query_text_emitted"] is True
            and report_ok["candidate_text_emitted"] is True
            and report_ok["annotation_instructions_emitted"] is True,
        )
    )
    # No task/repo IDs emitted; no input/output path emitted.
    checks.append(
        _check(
            "private_report_no_task_repo_or_path_emitted_flags",
            report_ok is not None
            and report_ok["task_ids_emitted"] is False
            and report_ok["repo_ids_emitted"] is False
            and report_ok["private_input_path_emitted"] is False
            and report_ok["packet_output_path_emitted"] is False
            and report_ok["private_source_records_persisted"] is False,
        )
    )
    # Harness flags true; no-claim flags false.
    checks.append(
        _check(
            "private_report_harness_flags_true",
            report_ok is not None
            and report_ok["private_packet_builder_harness_available"] is True
            and report_ok["private_cli_guard_validated"] is True
            and report_ok["tmp_output_resolved_guard_validated"] is True
            and report_ok["sanitized_error_guard_validated"] is True
            and report_ok["packet_schema_contract_defined"] is True
            and report_ok["d4b_mapping_contract_defined"] is True,
        )
    )
    # Private packet guard passes.
    checks.append(
        _check(
            "private_report_packet_guard_passes",
            report_ok is not None
            and report_ok["private_packet_guard"]["status"] == "pass"
            and report_ok["private_packet_guard"]["violations_count"] == 0,
        )
    )

    # --- Group 9: /tmp synthetic packet write smoke (NOT committed). ---
    ws = None
    tmp_in = None
    tmp_out = None
    try:
        ws = _symlink_selftest_workspace()
        tmp_in = ws / "source_records.json"
        tmp_out = ws / "annotation_packets.json"
        _write_json(tmp_in, valid_records)
        report_file, err_file = _run_private_packet_mode(
            allow_private=True,
            input_path=tmp_in,
            out_path=tmp_out,
            loader=_default_loader,
            input_exists=_default_exists,
        )
        checks.append(
            _check(
                "tmp_smoke_success_returns_report",
                err_file is None and report_file is not None,
            )
        )
        # Write the report and read it back to prove /tmp write works.
        if report_file is not None:
            _write_json(tmp_out, report_file)
            checks.append(
                _check(
                    "tmp_smoke_output_file_written_under_tmp",
                    tmp_out.is_file()
                    and _is_under_tmp(tmp_out)
                    and not _is_committed_out(tmp_out),
                )
            )
            read_back = json.loads(tmp_out.read_text(encoding="utf-8"))
            checks.append(
                _check(
                    "tmp_smoke_readback_has_blank_label_slots",
                    all(
                        isinstance(p, dict)
                        and isinstance(p.get("label_slots"), dict)
                        and all(
                            p["label_slots"].get(s) is None
                            for s in LABEL_SLOTS
                        )
                        for p in read_back["packets"]
                    ),
                )
            )
            checks.append(
                _check(
                    "tmp_smoke_readback_has_sensitive_context",
                    _has_dict_key_anywhere(read_back, "content_sha")
                    and _has_dict_key_anywhere(read_back, "snippet")
                    and _has_dict_key_anywhere(read_back, "query_text"),
                )
            )
            checks.append(
                _check(
                    "tmp_smoke_readback_no_input_output_path",
                    str(tmp_in) not in json.dumps(read_back, sort_keys=True)
                    and str(tmp_out) not in json.dumps(read_back, sort_keys=True)
                    and tmp_in.name not in json.dumps(read_back, sort_keys=True)
                    and tmp_out.name
                    not in json.dumps(read_back, sort_keys=True),
                )
            )
            # Output is NOT committed (under /tmp, not the artifacts dir).
            checks.append(
                _check(
                    "tmp_smoke_output_not_committed",
                    _is_under_tmp(tmp_out)
                    and _resolve(tmp_out).startswith(
                        _resolve(Path("/tmp")) + os.sep
                    )
                    and not str(tmp_out).startswith("artifacts/"),
                )
            )
        else:
            checks.append(_check("tmp_smoke_success_returns_report", False))
    finally:
        import shutil
        if ws is not None:
            shutil.rmtree(ws, ignore_errors=True)

    # --- Group 10: Resolved /tmp symlink-escape guards (filesystem). ---
    ws2 = None
    try:
        ws2 = _symlink_selftest_workspace()
        # Parent-symlink escape: /tmp/<ws>/link_to_repo/out.json.
        escape_link = ws2 / "link_to_repo"
        try:
            escape_link.symlink_to("/workspace")
        except OSError:
            escape_link.symlink_to("/")
        out_parent_escape = escape_link / "out.json"
        probe_esc = _ReadProbe(records=valid_records)
        _rep_esc, err_esc = _run_private_packet_mode(
            allow_private=True,
            input_path=Path("/private/SECRET_PACKET_SENTINEL_esc.json"),
            out_path=out_parent_escape,
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
                err_esc is not None and _SECRET_SENTINEL not in err_esc,
            )
        )
        # Existing output file symlink pointing outside /tmp rejected.
        out_file_symlink = ws2 / "outlink.json"
        try:
            out_file_symlink.symlink_to("/workspace/secret.json")
        except OSError:
            out_file_symlink.symlink_to("/secret.json")
        probe_fs = _ReadProbe(records=valid_records)
        _rep_fs, err_fs = _run_private_packet_mode(
            allow_private=True,
            input_path=Path("/private/SECRET_PACKET_SENTINEL_fs.json"),
            out_path=out_file_symlink,
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
        out_valid = ws2 / "valid_out.json"
        probe_vo = _ReadProbe(records=valid_records)
        _rep_vo, err_vo = _run_private_packet_mode(
            allow_private=True,
            input_path=Path("/private/SECRET_PACKET_SENTINEL_vo.json"),
            out_path=out_valid,
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
        import shutil
        if ws2 is not None:
            shutil.rmtree(ws2, ignore_errors=True)

    # --- Group 11: Private packet guard rejects bad packets. ---
    # Filled label slot -> guard fails.
    bad_packet = _build_private_packet_report(
        packets=[
            {
                "packet_ref": "local-packet-0001",
                "private_record_ref": "r1",
                "candidate_ref": "c1",
                "candidate_bucket_hint": "primary_evidence",
                "query_text": "q",
                "candidate_text": "ct",
                "evidence": [
                    {"path": "src/x.rs", "start_line": 1, "end_line": 2,
                     "content_sha": "a" * 64, "snippet": "s"}
                ],
                "annotation_instructions": _ANNOTATION_INSTRUCTIONS,
                "label_slots": {s: None for s in LABEL_SLOTS},
            }
        ]
    )
    # Tamper: fill an e_score slot.
    bad_packet["packets"][0]["label_slots"]["e_score"] = "E2"
    guard_bad = _private_packet_guard_summary(bad_packet)
    checks.append(
        _check(
            "private_guard_rejects_filled_label_slot",
            guard_bad["status"] == "fail",
        )
    )
    # Provider payload key -> guard fails.
    bad_packet2 = _build_private_packet_report(
        packets=[
            {
                "packet_ref": "local-packet-0001",
                "private_record_ref": "r1",
                "candidate_ref": "c1",
                "candidate_bucket_hint": "primary_evidence",
                "query_text": "q",
                "candidate_text": "ct",
                "evidence": [
                    {"path": "src/x.rs", "start_line": 1, "end_line": 2,
                     "content_sha": "a" * 64, "snippet": "s"}
                ],
                "annotation_instructions": _ANNOTATION_INSTRUCTIONS,
                "label_slots": {s: None for s in LABEL_SLOTS},
            }
        ]
    )
    bad_packet2["packets"][0]["provider_payload"] = {"x": 1}
    guard_bad2 = _private_packet_guard_summary(bad_packet2)
    checks.append(
        _check(
            "private_guard_rejects_provider_payload_key",
            guard_bad2["status"] == "fail",
        )
    )
    # api_key value -> guard fails (secret-like).
    bad_packet3 = _build_private_packet_report(
        packets=[
            {
                "packet_ref": "local-packet-0001",
                "private_record_ref": "r1",
                "candidate_ref": "c1",
                "candidate_bucket_hint": "primary_evidence",
                "query_text": "q",
                "candidate_text": "ct",
                "evidence": [
                    {"path": "src/x.rs", "start_line": 1, "end_line": 2,
                     "content_sha": "a" * 64, "snippet": "s"}
                ],
                "annotation_instructions": _ANNOTATION_INSTRUCTIONS,
                "label_slots": {s: None for s in LABEL_SLOTS},
            }
        ]
    )
    bad_packet3["packets"][0]["annotation_instructions"] = (
        "api_key=sk-SECRET_PACKET_SENTINEL"
    )
    guard_bad3 = _private_packet_guard_summary(bad_packet3)
    checks.append(
        _check(
            "private_guard_rejects_secret_like_value",
            guard_bad3["status"] == "fail",
        )
    )
    # A clean valid packet passes the guard.
    guard_ok = _private_packet_guard_summary(report_ok)
    checks.append(
        _check(
            "private_guard_passes_clean_packet",
            guard_ok["status"] == "pass",
        )
    )

    # --- Group 12: Artifact generation refuses success if self-test fails. ---
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

    # --- Group 13: CLI option surface (exactly the required options). ---
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
            "cli_has_allow_private_source_records_argument",
            "--allow-private-source-records" in cli_opts,
        )
    )
    checks.append(
        _check("cli_has_input_argument", "--input" in cli_opts)
    )
    checks.append(
        _check(
            "cli_only_required_arguments",
            (cli_opts - {"-h", "--help"})
            == {
                "--self-test",
                "--out",
                "--allow-private-source-records",
                "--input",
            },
        )
    )

    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the D4c CLI parser."""
    ap = argparse.ArgumentParser(
        description=(
            "D4c annotation packet builder harness "
            "(public harness/no-packets artifact; no packets built by "
            "default; no labels collected)."
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
            "artifact; private packet builder requires an explicit /tmp path)"
        ),
    )
    ap.add_argument(
        "--allow-private-source-records",
        action="store_true",
        help=(
            "opt-in private annotation packet builder; requires --input; "
            "output must go to /tmp only (NOT committed)"
        ),
    )
    ap.add_argument(
        "--input",
        type=Path,
        default=None,
        help=(
            "path to a private source-records JSON (private packet builder "
            "only; requires --allow-private-source-records); never "
            "serialized into any committed artifact"
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

    # Private packet builder mode (any private arg present).
    if args.allow_private_source_records or args.input is not None:
        report, err = _run_private_packet_mode(
            allow_private=args.allow_private_source_records,
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
        # Strict private packet guard immediately before writing.
        guard = report.get("private_packet_guard", {})
        if guard.get("status") != "pass":
            print(
                "error: private packet guard failed; refusing to write",
                file=sys.stderr,
            )
            sys.exit(2)
        _write_json(args.out, report)
        # Do NOT print the exact /tmp output path.
        print(_private_success_message(report))
        return

    # Public default mode (committed harness/no-packets artifact).
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
