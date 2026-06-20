#!/usr/bin/env python3
"""D4e Filled-Packet to D4b Bundle Converter Harness / Blocked Public Artifact.

This module implements the **D4e filled-packet -> D4b true-label bundle
converter harness**. D4e hardens the conversion control plane between
D4d human annotation and D4b bundle validation, before any real human
labels exist. The **default committed artifact is a public harness /
no-conversion artifact**, NOT a real filled-packet -> D4b bundle
conversion run. D4e must NOT claim real label conversion in the
committed artifact, must NOT compute calibration / agreement / CI
metrics, and must NOT unblock D5.

D4e **does not** read private filled packets by default, **does not**
convert filled packets to a D4b bundle by default, **does not** write
or commit a D4b bundle by default, **does not** accept D4c source
context fields, **does not** accept model/proxy/LLM labels as
human/manual labels, **does not** emit packet refs / task IDs / repo
IDs / paths / spans / snippets / content hashes / query / candidate
text / rater IDs in any committed artifact, **does not** compute
calibration / inter-rater agreement / confidence intervals, **does
not** pass any public-release gate, **does not** unblock D5, **does
not** claim true E/S calibration, **does not** perform model/LLM
labeling, and **does not** change runtime behavior, retriever, pack,
model, backend, default policy, or EvidenceCore semantics.

Claim boundary (binding):

* This is **eval/diagnostic only**. It is NOT a runtime change, NOT a
  retriever/pack/model/backend/default-policy change, and NOT an
  EvidenceCore semantic change.
* Claim level: ``filled_packet_to_d4b_bundle_converter_harness_only``.
* Status: ``blocked_no_filled_packets_available_or_no_conversion_run``;
  mode ``public_harness_no_filled_packets_no_conversion``; phase
  ``D4e``.
* D4c packet schema source: ``d4c_annotation_packet_v1``.
* D4d runbook protocol: ``d4d_human_annotation_runbook.v1``.
* D4b bundle schema target: ``d4b_true_label_bundle_v1``.
* The default committed artifact reads NO private filled packets,
  converts NO filled packets to a D4b bundle, writes/commits NO D4b
  bundle, validates NO D4b bundle, collects/converts NO labels, emits
  NO packet refs / paths / snippets / IDs / rater IDs, computes NO
  calibration, performs NO model/LLM labeling, and passes NO
  public-release gate.

Two strictly separated modes:

* **D4e default (committed)**: public harness / no-conversion artifact.
  No private input. All private read/conversion/bundle/label/metrics/
  D5 flags false; the allowed harness/control flags true; diagnostic
  flags true.

* **D4e private converter (opt-in, NOT committed)**: explicit
  ``--allow-private-filled-packets --input-filled-packets <path>
  --out /tmp/...``. Reads a local/private minimal label-only filled
  packet batch with a D4d attestation, converts the filled label slots
  to a ``d4b_true_label_bundle_v1``-shaped bundle, and writes ``/tmp``
  output only. Never serializes input/output paths or basenames, label
  text, packet refs, rater IDs, or provider payloads. Rejects D4c
  source context fields. ``--synthetic-harness-test`` marks an
  in-memory/harness run: it sets ``synthetic_harness_test=true``,
  ``synthetic_labels_converted_for_harness_only=true``,
  ``local_private_conversion_executed=false``, and
  ``real_human_labels_converted=false`` even if the bundle is
  human-manual-shaped. A real local private run (no synthetic flag,
  D4d attestation passes, no model/proxy labels, schema passes, and
  /tmp guard passes) may set
  ``local_private_conversion_executed=true`` and
  ``real_human_labels_converted=true`` locally only (never committed).
  Docs mark the real-mode flag-path test over a synthetic fixture as a
  flag-path test, NOT evidence that real labels exist.

Run::

    python3 -m py_compile eval/d4e_filled_packet_converter.py
    python3 eval/d4e_filled_packet_converter.py --self-test
    python3 eval/d4e_filled_packet_converter.py \
        --out artifacts/d4e_filled_packet_converter/\
d4e_filled_packet_converter_report.json
    # D4e private converter (NOT committed; /tmp only):
    python3 eval/d4e_filled_packet_converter.py \
        --allow-private-filled-packets \
        --input-filled-packets /local/private/filled_packets.json \
        --out /tmp/d4b_true_label_bundle.json
    # D4e synthetic harness self-test (NOT committed; /tmp only):
    python3 eval/d4e_filled_packet_converter.py \
        --allow-private-filled-packets --synthetic-harness-test \
        --input-filled-packets /tmp/synthetic_filled_packets.json \
        --out /tmp/d4e_synthetic_bundle.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "d4e_filled_packet_converter_harness.v1"
GENERATED_BY = "eval/d4e_filled_packet_converter.py"
CLAIM_LEVEL = "filled_packet_to_d4b_bundle_converter_harness_only"
TARGET_STATUS = (
    "blocked_no_filled_packets_available_or_no_conversion_run"
)
MODE_PUBLIC = "public_harness_no_filled_packets_no_conversion"
MODE_PRIVATE = "private_filled_packet_converter_tmp_only"
PHASE = "D4e"
STATUS_PRIVATE_OK = "private_d4b_bundle_built_locally"

DEFAULT_OUT = Path(
    "artifacts/d4e_filled_packet_converter/"
    "d4e_filled_packet_converter_report.json"
)

# Referenced schema/protocol versions (source/target contracts only; D4e
# default mode does not read filled packets, build bundles, or run any
# converter).
D4C_PACKET_SCHEMA_SOURCE = "d4c_annotation_packet_v1"
D4D_RUNBOOK_PROTOCOL = "d4d_human_annotation_runbook.v1"
D4B_BUNDLE_SCHEMA_TARGET = "d4b_true_label_bundle_v1"

# Private filled-packet batch schema (label-only, with D4d attestation).
FILLED_PACKETS_SCHEMA = "d4e_filled_annotation_packets_v1"

# Private D4b bundle output schema + label source.
HUMAN_MANUAL_LABEL_SOURCE = "human_manual_true_e_s"

# Fixed sanitized error for any private filled-packet load/parse/schema/
# privacy failure. Never includes the input path, basename, raw JSON, or
# label text.
PRIVATE_LOAD_ERROR_MESSAGE = (
    "error: failed to load private filled packets "
    "(schema/privacy/parse error; details suppressed)"
)

# Fixed label slots a human rater fills (D3 protocol; D4e consumes them
# as filled values, never as blank slots).
LABEL_SLOTS: tuple[str, ...] = (
    "e_score",
    "s_score",
    "bucket",
    "citation_valid",
    "rater_pair_present",
    "adjudicated",
)

# D3 dual-rubric E-score / S-score levels (filled-label values; allowed
# inside the D4b bundle labels list and as contract values only).
E_SCORE_LEVELS: tuple[str, ...] = ("E0", "E1", "E2")
S_SCORE_LEVELS: tuple[str, ...] = ("S0", "S1", "S2")

# Bucket names referenced by the D3 rubric (filled-label values; allowed
# inside the D4b bundle labels list and as contract values only).
BUCKET_NAMES: tuple[str, ...] = (
    "primary_evidence",
    "dependency_support",
    "weak_candidates",
    "abstained",
)

# D4d runbook attestation field names (allowed as contract container
# values only).
ATTESTATION_FIELDS: tuple[str, ...] = (
    "protocol",
    "two_independent_human_raters",
    "independent_before_adjudication",
    "no_llm_or_model_labels",
    "no_proxy_labels_as_true_labels",
    "local_only_storage",
)

# ---------------------------------------------------------------------------
# Default artifact false flags (all MUST be false in the committed public
# artifact). D4e reads no filled packets, converts no labels, writes no
# D4b bundle, computes no calibration, performs no model/LLM labeling,
# and passes no release gate.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "private_filled_packets_read": False,
    "filled_packets_validated": False,
    "filled_packets_persisted": False,
    "conversion_run": False,
    "d4b_true_label_bundle_created": False,
    "d4b_true_label_bundle_written": False,
    "d4b_true_label_bundle_validated": False,
    "labels_collected": False,
    "labels_converted": False,
    "raw_label_rows_emitted": False,
    "packet_ids_emitted": False,
    "task_ids_emitted": False,
    "repo_ids_emitted": False,
    "paths_or_spans_emitted": False,
    "snippets_emitted": False,
    "content_sha_emitted": False,
    "query_or_candidate_text_emitted": False,
    "rater_ids_emitted": False,
    "private_input_path_emitted": False,
    "private_output_path_emitted": False,
    "exact_private_counts_emitted": False,
    "calibration_metrics_computed": False,
    "inter_rater_agreement_measured": False,
    "confidence_intervals_computed": False,
    "public_release_gate_passed": False,
    "d5_unblocked": False,
    "true_e_s_calibration_claimed": False,
    "model_or_llm_labeling_performed": False,
    "model_assisted_labels_allowed": False,
}

# Allowed positive harness/control flags (true only for the validated
# harness/controls; each is proven by a self-test). Exactly these; no
# read/conversion/bundle/label/calibration/D5 claim flags are true in
# the default committed artifact.
HARNESS_CONTROL_FLAGS: dict[str, bool] = {
    "converter_harness_available": True,
    "private_cli_guard_validated": True,
    "tmp_output_resolved_guard_validated": True,
    "sanitized_error_guard_validated": True,
    "filled_packet_schema_contract_defined": True,
    "d4d_attestation_required": True,
    "d4b_bundle_schema_contract_defined": True,
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
# Public artifact scanner (strict, fail-closed, with exact contract
# string allowlist). Same shape as D4d: contract containers are exact
# string allowlists (no over-broad container exemption); sensitive
# field-name tokens are allowed as VALUES only inside contract containers
# and nowhere else.
# ---------------------------------------------------------------------------

# Top-level keys whose subtrees are explicit contract field-name /
# enum containers. String values inside these containers must be in
# APPROVED_CONTRACT_STRINGS (exact allowlist). Field-name token strings
# are allowed as VALUES only inside these containers and nowhere else.
CONTRACT_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "filled_packet_schema_contract",
        "d4d_runbook_contract",
        "d4b_bundle_schema_contract",
        "d4b_mapping_contract",
    }
)

# Sensitive field-name tokens that may appear as list-element VALUES
# inside contract containers (e.g. required_label_slots,
# required_attestation_fields, packet_label_slots) for the label-slot
# and attestation subsets only, but are forbidden as dict KEYS anywhere
# and forbidden as VALUES outside contract containers. Sensitive
# packet/source fields (content_sha, query_text, packet_ref, etc.) are
# NOT approved contract strings, so they are rejected even inside
# contract containers.
FIELD_NAME_TOKENS: frozenset[str] = frozenset(
    {
        # label slots
        "e_score",
        "s_score",
        "bucket",
        "citation_valid",
        "rater_pair_present",
        "adjudicated",
        # attestation fields
        "protocol",
        "two_independent_human_raters",
        "independent_before_adjudication",
        "no_llm_or_model_labels",
        "no_proxy_labels_as_true_labels",
        "local_only_storage",
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
        "source_packet_schema",
        "d4d_runbook_attestation",
        "packets",
    }
)

# Exact string values allowed inside explicit public contract containers.
# This intentionally does NOT allow arbitrary short strings inside a
# contract container; only approved schema/protocol identifiers, E/S
# levels, bucket names, label-slot field-name tokens, attestation
# field-name tokens, the human-manual label source identifier, and the
# approved D4b bundle field-name tokens. Sensitive source fields such as
# content_sha / query_text / packet_ref are not exposed in the public
# artifact contracts.
ALLOWED_BUNDLE_KEY_TOKENS: frozenset[str] = frozenset(
    {
        "schema",
        "label_source",
        "rater_count",
        "agreement_available",
        "confidence_intervals_available",
        "synthetic_harness_test",
        "synthetic_labels_converted_for_harness_only",
        "local_private_conversion_executed",
        "real_human_labels_converted",
        "labels",
    }
)
APPROVED_CONTRACT_STRINGS: frozenset[str] = frozenset(
    {
        D4C_PACKET_SCHEMA_SOURCE,
        D4D_RUNBOOK_PROTOCOL,
        D4B_BUNDLE_SCHEMA_TARGET,
        FILLED_PACKETS_SCHEMA,
        HUMAN_MANUAL_LABEL_SOURCE,
        *E_SCORE_LEVELS,
        *S_SCORE_LEVELS,
        *BUCKET_NAMES,
        *LABEL_SLOTS,
        *ATTESTATION_FIELDS,
        *ALLOWED_BUNDLE_KEY_TOKENS,
    }
)

# Sensitive KEY names that must NEVER appear as dict keys anywhere in a
# public artifact JSON. Superset of the generic
# location/content/identifier/label/rater/model/secret keys.
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
        # D4c/D4d source-context / attestation keys (D4e public artifact
        # exposes only category-only contracts; the raw attestation dict
        # and packets list must never appear as keys).
        "source_packet_schema", "d4d_runbook_attestation",
        "source_records",
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
        "d4c_packet_schema_source",
        "d4d_runbook_protocol",
        "d4b_bundle_schema_target",
        "section",
        "check",
        "category",
        "output_location",
    }
)

# Value patterns that indicate leaked row-level / candidate / packet /
# annotation data. D4e rejects ALL URLs (no URL allowlist) per the
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
_SECRET_SENTINEL = "SECRET_CONVERTER_SENTINEL"


def _path_last_key(path: str) -> str:
    """Extract the last key segment from a dotted JSON path."""
    last = path.rsplit(".", 1)[-1]
    return last.split("[")[0]


def _is_safe_value_path(path: str) -> bool:
    """Check if a JSON path ends with a known-safe value key."""
    return _path_last_key(path) in SAFE_VALUE_KEY_NAMES


def _is_inside_contract_container(path: str) -> bool:
    """True iff any ancestor segment of ``path`` is a contract container key.

    Approved strings (schema/protocol identifiers, E/S levels, bucket
    names, label-slot field names, attestation field names, and the
    human-manual label source) are allowed as VALUES only inside
    explicit contract containers and nowhere else.
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
    annotation_row/rater_id/model_output/provider_payload/
    source_packet_schema/d4d_runbook_attestation/packets/etc.) anywhere,
    and rejects value patterns: ANY URL, 32/40/64-char hex digests,
    secret-like strings, path-like strings (``src/foo.py``,
    ``/private/foo.jsonl``), multiline strings, raw JSON fragments,
    raw line-range strings (``12-34``), and the self-test sentinel.

    Contract containers are exact allowlists: only approved schema/
    protocol identifiers, E/S levels, bucket names, label-slot field
    names, attestation field names, and the human-manual label source
    may appear there. Arbitrary short strings such as implementation
    symbols or private text are rejected even inside contract
    containers. Field names remain rejected as keys anywhere and as
    values outside contracts.
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
        # Contract containers are exact allowlists: only approved
        # schema/protocol identifiers, E/S levels, bucket names,
        # label-slot field names, attestation field names, and the
        # human-manual label source. Reject arbitrary short strings
        # such as "compute_loss" or private text even if nested under
        # a contract container.
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


def _build_filled_packet_schema_contract() -> dict[str, Any]:
    """Filled-packet schema contract (label-only, with D4d attestation)."""
    return {
        "schema": FILLED_PACKETS_SCHEMA,
        "source_packet_schema_ref": D4C_PACKET_SCHEMA_SOURCE,
        "private_only": True,
        "may_contain_filled_label_slots": True,
        "required_label_slots": list(LABEL_SLOTS),
        "required_attestation_fields": list(ATTESTATION_FIELDS),
        "rejects_source_context_fields": True,
    }


def _build_d4d_runbook_contract() -> dict[str, Any]:
    """D4d runbook / attestation contract (required, all-true)."""
    return {
        "protocol": D4D_RUNBOOK_PROTOCOL,
        "required_attestation_fields": list(ATTESTATION_FIELDS),
        "attestation_must_be_all_true": True,
        "no_llm_or_model_labels_required": True,
        "no_proxy_labels_as_true_labels_required": True,
        "local_only_storage_required": True,
    }


def _build_d4b_bundle_schema_contract() -> dict[str, Any]:
    """D4b bundle schema contract (output target; converter not run by default)."""
    return {
        "schema": D4B_BUNDLE_SCHEMA_TARGET,
        "required_label_source": HUMAN_MANUAL_LABEL_SOURCE,
        "bundle_allowed_keys": sorted(ALLOWED_BUNDLE_KEYS),
        "label_object_allowed_keys": sorted(ALLOWED_LABEL_KEYS),
        "e_score_levels": list(E_SCORE_LEVELS),
        "s_score_levels": list(S_SCORE_LEVELS),
        "bucket_names": list(BUCKET_NAMES),
        "rejects_unknown_keys": True,
        "rejects_packet_refs_paths_snippets_raters": True,
    }


def _build_d4b_mapping_contract() -> dict[str, Any]:
    """D4e -> D4b mapping contract (converter not run by default)."""
    return {
        "target_bundle_schema": D4B_BUNDLE_SCHEMA_TARGET,
        "packet_label_slots": list(LABEL_SLOTS),
        "source_packet_schema_ref": D4C_PACKET_SCHEMA_SOURCE,
        "runbook_protocol": D4D_RUNBOOK_PROTOCOL,
        "packet_to_bundle_requires_human_or_local_converter": True,
        "converter_not_run_by_default": True,
        "d4b_true_label_bundle_created": False,
    }


def _build_converter_harness_info() -> dict[str, Any]:
    """Private converter harness availability info."""
    return {
        "available": True,
        "opt_in_required": True,
        "output_location": "tmp_only_local_private",
        "committed": False,
        "converts_filled_packets_to_d4b_bundle": True,
        "rejects_source_context_fields": True,
        "rejects_model_proxy_llm_labels": True,
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
# Private filled-packet input contract (label-only, with D4d attestation;
# rejects D4c source context fields)
# ---------------------------------------------------------------------------


ALLOWED_BATCH_KEYS: frozenset[str] = frozenset(
    {
        "schema",
        "source_packet_schema",
        "d4d_runbook_attestation",
        "packets",
    }
)
ALLOWED_ATTESTATION_KEYS: frozenset[str] = frozenset(ATTESTATION_FIELDS)
ALLOWED_PACKET_KEYS: frozenset[str] = frozenset({"packet_ref", "label_slots"})
ALLOWED_LABEL_SLOT_KEYS: frozenset[str] = frozenset(LABEL_SLOTS)


class _PrivateFilledPacketsLoadError(Exception):
    """Raised when private filled packets fail schema/privacy/parse checks.

    The CLI never surfaces this exception's message; it always emits the
    fixed sanitized ``PRIVATE_LOAD_ERROR_MESSAGE`` instead.
    """


def _is_str(value: Any) -> bool:
    return isinstance(value, str)


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _validate_d4d_attestation(attestation: Any) -> None:
    """Validate a D4d runbook attestation (fail-closed, sanitized).

    Raises ``_PrivateFilledPacketsLoadError`` if missing, malformed, has
    unknown keys, has wrong-typed values, has any required flag set to
    false, or has a wrong protocol. The attestation must be exactly
    ``d4d_human_annotation_runbook.v1`` with all six required flags true:
    two independent human raters, independence before adjudication, no
    LLM/model labels, no proxy labels as true labels, local-only storage.
    """
    if not isinstance(attestation, dict):
        raise _PrivateFilledPacketsLoadError()
    if set(attestation.keys()) != ALLOWED_ATTESTATION_KEYS:
        raise _PrivateFilledPacketsLoadError()
    if attestation.get("protocol") != D4D_RUNBOOK_PROTOCOL:
        raise _PrivateFilledPacketsLoadError()
    for flag in (
        "two_independent_human_raters",
        "independent_before_adjudication",
        "no_llm_or_model_labels",
        "no_proxy_labels_as_true_labels",
        "local_only_storage",
    ):
        if attestation.get(flag) is not True:
            raise _PrivateFilledPacketsLoadError()


def _validate_filled_packet_batch(data: Any) -> None:
    """Validate a private filled-packet batch (fail-closed, sanitized).

    Raises ``_PrivateFilledPacketsLoadError`` if malformed, has an
    unknown schema, contains keys outside the allowlist (e.g. paths,
    snippets, content_sha, query_text, candidate_text, packet_ref
    source context, rater IDs, provider payloads, API keys, model
    outputs, prompts/responses, raw label rows), or has wrong-typed /
    out-of-range values. The loader rejects unknown keys rather than
    supporting and stripping them.

    D4e consumes filled labels and the D4d attestation only; it rejects
    D4c source context fields.
    """
    if not isinstance(data, dict):
        raise _PrivateFilledPacketsLoadError()
    if set(data.keys()) != ALLOWED_BATCH_KEYS:
        raise _PrivateFilledPacketsLoadError()
    if data.get("schema") != FILLED_PACKETS_SCHEMA:
        raise _PrivateFilledPacketsLoadError()
    if data.get("source_packet_schema") != D4C_PACKET_SCHEMA_SOURCE:
        raise _PrivateFilledPacketsLoadError()
    _validate_d4d_attestation(data.get("d4d_runbook_attestation"))
    packets = data.get("packets")
    if not isinstance(packets, list) or len(packets) == 0:
        raise _PrivateFilledPacketsLoadError()
    for packet in packets:
        if not isinstance(packet, dict):
            raise _PrivateFilledPacketsLoadError()
        if set(packet.keys()) != ALLOWED_PACKET_KEYS:
            raise _PrivateFilledPacketsLoadError()
        packet_ref = packet.get("packet_ref")
        if not _is_str(packet_ref) or not packet_ref:
            raise _PrivateFilledPacketsLoadError()
        slots = packet.get("label_slots")
        if not isinstance(slots, dict):
            raise _PrivateFilledPacketsLoadError()
        if set(slots.keys()) != ALLOWED_LABEL_SLOT_KEYS:
            raise _PrivateFilledPacketsLoadError()
        if slots.get("e_score") not in E_SCORE_LEVELS:
            raise _PrivateFilledPacketsLoadError()
        if slots.get("s_score") not in S_SCORE_LEVELS:
            raise _PrivateFilledPacketsLoadError()
        if slots.get("bucket") not in BUCKET_NAMES:
            raise _PrivateFilledPacketsLoadError()
        for flag in (
            "citation_valid",
            "rater_pair_present",
            "adjudicated",
        ):
            if not _is_bool(slots.get(flag)):
                raise _PrivateFilledPacketsLoadError()


def _attestation_allows_real_conversion(attestation: Any) -> bool:
    """True iff the attestation permits a real (non-synthetic) conversion.

    Requires the attestation to be valid (all flags true) AND
    ``no_llm_or_model_labels=true`` AND
    ``no_proxy_labels_as_true_labels=true``. Used by the real-mode
    flag-path decision; does not itself claim execution in any committed
    artifact.
    """
    if not isinstance(attestation, dict):
        return False
    try:
        _validate_d4d_attestation(attestation)
    except _PrivateFilledPacketsLoadError:
        return False
    return (
        attestation.get("no_llm_or_model_labels") is True
        and attestation.get("no_proxy_labels_as_true_labels") is True
    )


# ---------------------------------------------------------------------------
# Private D4b bundle output guard (DIFFERENT from the public scanner).
# Allows label fields and E/S values (the bundle is a real D4b bundle);
# rejects paths/snippets/content_sha/query/candidate text, packet refs,
# rater IDs, provider payload/API secrets/model outputs; verifies schema,
# label_source, truthful synthetic/real flags, and no path/basename
# metadata.
# ---------------------------------------------------------------------------


# Keys that must NEVER appear in a private D4b bundle output (provider
# secrets / API keys / provider payloads / model outputs / source
# context / packet refs / rater IDs / row metadata). The private bundle
# guard ALLOWS labels, E/S values, bucket names, and the truthful
# synthetic/real flag set.
PRIVATE_BUNDLE_FORBIDDEN_KEYS: frozenset[str] = frozenset(
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
        # packet-specific identifiers (NO packet refs in final D4b bundle)
        "packet_ref", "packet_id", "packet_refs", "packet_ids",
        "private_record_ref", "candidate_ref", "candidate_id",
        # labels / qrels / annotations / raters (the labels LIST is
        # allowed, but raw_label/annotation_row/rater_id/etc. are not)
        "label", "qrels", "gold", "gold_label", "gold_labels",
        "gold_answer", "predicted_answer", "answer", "question",
        "raw_label", "raw_labels", "annotation_row", "annotation_rows",
        "annotator_id", "rater_id", "rater_name", "per_row_hash", "row_hash",
        "disagreement_example", "disagreement_examples",
        "true_label", "true_e_score", "true_s_score",
        "label_slots", "annotation_instructions",
        "candidate_bucket_hint", "evidence",
        # prompts / responses / model outputs
        "query", "query_text", "prompt", "response", "model_response",
        "model_output", "provider_payload", "raw_payload", "api_response",
        "response_body",
        # rows / records / packets (NO packets list in final D4b bundle)
        "raw_rows", "rows", "records", "tasks", "row_values", "packets",
        # D4c/D4d source-context / attestation keys (NO source context or
        # attestation in final D4b bundle)
        "source_packet_schema", "d4d_runbook_attestation",
        "source_records",
        # patches / tests
        "patch", "test_patch", "tests",
        # secrets
        "api_key", "api_token", "api_secret", "base_url", "provider_key",
        "authorization",
    }
)

# Allowed keys in a private D4b bundle output (exact allowlist).
ALLOWED_BUNDLE_KEYS: frozenset[str] = frozenset(
    {
        "schema",
        "label_source",
        "rater_count",
        "agreement_available",
        "confidence_intervals_available",
        "synthetic_harness_test",
        "synthetic_labels_converted_for_harness_only",
        "local_private_conversion_executed",
        "real_human_labels_converted",
        "labels",
    }
)

# Allowed keys in each label object of a private D4b bundle output.
ALLOWED_LABEL_KEYS: frozenset[str] = frozenset(LABEL_SLOTS)


def _find_secret_like_values(obj: Any) -> list[str]:
    """Return any string values that look like provider secrets/API keys.

    The private bundle allows label fields and E/S values but must reject
    provider secrets, API keys, provider payloads, and the self-test
    sentinel.
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


def _find_path_like_values(obj: Any) -> list[str]:
    """Return any string values that look like file paths (path-like)."""
    found: list[str] = []
    if isinstance(obj, dict):
        for value in obj.values():
            found.extend(_find_path_like_values(value))
    elif isinstance(obj, list):
        for value in obj:
            found.extend(_find_path_like_values(value))
    elif isinstance(obj, str):
        if (
            _RE_FILE_PATH_VALUE.search(obj)
            or _RE_HEX_DIGEST.fullmatch(obj)
        ):
            found.append(obj)
    return found


def _validate_private_d4b_bundle(bundle: Any) -> list[dict[str, Any]]:
    """Private D4b bundle output guard (fail-closed).

    Different from the public scanner: this guard allows label fields
    and E/S values (the bundle is a real D4b bundle that may contain
    labels locally), but enforces:

    * schema exactly ``d4b_true_label_bundle_v1``;
    * label_source exactly ``human_manual_true_e_s``;
    * bundle keys exactly the allowlist (no packet refs, paths,
      snippets, content_sha, query_text, candidate_text, rater IDs,
      provider payloads, API secrets, model outputs, raw label rows,
      packets list, source_packet_schema, d4d_runbook_attestation);
    * label object keys exactly the six label slots;
    * E/S values within the D3 enum; bucket within the D3 enum;
    * citation_valid / rater_pair_present / adjudicated as bools;
    * truthful synthetic/real flags (synthetic => harness-only and no
      real conversion; real => not synthetic-marked);
    * no provider secrets/API keys/sentinel in any string value;
    * no path-like or hex-digest values;
    * no input/output path or basename in any string value (caller
      passes them in via ``forbidden_path_fragments``).

    Returns a list of violation dicts (never the leaked value).
    """
    if not isinstance(bundle, dict):
        return [{"category": "bundle_not_dict"}]
    violations: list[dict[str, Any]] = []
    if bundle.get("schema") != D4B_BUNDLE_SCHEMA_TARGET:
        violations.append({"category": "wrong_bundle_schema"})
    if bundle.get("label_source") != HUMAN_MANUAL_LABEL_SOURCE:
        violations.append({"category": "wrong_label_source"})
    for key in bundle.keys():
        if key not in ALLOWED_BUNDLE_KEYS:
            violations.append(
                {"category": "forbidden_bundle_key", "key": key}
            )
    # Truthful synthetic/real flags.
    sht = bundle.get("synthetic_harness_test")
    slc = bundle.get("synthetic_labels_converted_for_harness_only")
    lpc = bundle.get("local_private_conversion_executed")
    rhc = bundle.get("real_human_labels_converted")
    if not isinstance(sht, bool):
        violations.append({"category": "synthetic_harness_test_not_bool"})
    if not isinstance(slc, bool):
        violations.append(
            {"category": "synthetic_labels_converted_not_bool"}
        )
    if not isinstance(lpc, bool):
        violations.append(
            {"category": "local_private_conversion_not_bool"}
        )
    if not isinstance(rhc, bool):
        violations.append(
            {"category": "real_human_labels_converted_not_bool"}
        )
    if sht is True:
        if slc is not True:
            violations.append(
                {"category": "synthetic_but_not_marked_harness_only"}
            )
        if lpc is not False:
            violations.append(
                {"category": "synthetic_but_local_conversion_true"}
            )
        if rhc is not False:
            violations.append(
                {"category": "synthetic_but_real_conversion_true"}
            )
    else:
        # Real-mode flag path: not synthetic-marked. If
        # local_private_conversion_executed=true then
        # real_human_labels_converted must also be true and
        # synthetic_labels_converted_for_harness_only must be false.
        if lpc is True:
            if rhc is not True:
                violations.append(
                    {"category": "local_conversion_but_real_false"}
                )
            if slc is not False:
                violations.append(
                    {"category": "local_conversion_but_synthetic_marked"}
                )
    # rater_count >= 2
    rater_count = bundle.get("rater_count")
    if (
        not isinstance(rater_count, int)
        or isinstance(rater_count, bool)
        or rater_count < 2
    ):
        violations.append({"category": "rater_count_below_2"})
    for flag in ("agreement_available", "confidence_intervals_available"):
        if not isinstance(bundle.get(flag), bool):
            violations.append({"category": f"{flag}_not_bool"})
    # Labels list.
    labels = bundle.get("labels")
    if not isinstance(labels, list) or len(labels) == 0:
        violations.append({"category": "missing_or_empty_labels"})
    else:
        for idx, entry in enumerate(labels):
            if not isinstance(entry, dict):
                violations.append(
                    {"category": "label_not_dict", "idx": idx}
                )
                continue
            if set(entry.keys()) != ALLOWED_LABEL_KEYS:
                violations.append(
                    {"category": "label_wrong_keys", "idx": idx}
                )
            else:
                if entry.get("e_score") not in E_SCORE_LEVELS:
                    violations.append(
                        {"category": "invalid_e_score", "idx": idx}
                    )
                if entry.get("s_score") not in S_SCORE_LEVELS:
                    violations.append(
                        {"category": "invalid_s_score", "idx": idx}
                    )
                if entry.get("bucket") not in BUCKET_NAMES:
                    violations.append(
                        {"category": "invalid_bucket", "idx": idx}
                    )
                for flag in (
                    "citation_valid",
                    "rater_pair_present",
                    "adjudicated",
                ):
                    if not isinstance(entry.get(flag), bool):
                        violations.append(
                            {"category": f"non_bool_{flag}", "idx": idx}
                        )
    # Forbidden source-context / packet / rater / secret / model keys
    # anywhere in the bundle.
    for bad in PRIVATE_BUNDLE_FORBIDDEN_KEYS:
        if _has_dict_key_anywhere(bundle, bad):
            violations.append(
                {"category": "private_bundle_forbidden_key", "key": bad}
            )
    # No provider secrets / API keys / sentinel in any string value.
    if _find_secret_like_values(bundle):
        violations.append(
            {"category": "secret_like_value", "count": "suppressed"}
        )
    # No path-like or hex-digest values anywhere in the bundle.
    if _find_path_like_values(bundle):
        violations.append(
            {"category": "path_or_digest_value", "count": "suppressed"}
        )
    return violations


def _private_bundle_guard_summary(
    bundle: Any,
    *,
    forbidden_path_fragments: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Run the private D4b bundle guard and return a sanitized summary.

    ``forbidden_path_fragments`` is a tuple of exact input/output path
    strings and basenames that must NOT appear in any bundle string
    value. The summary never echoes the fragments themselves.
    """
    violations = _validate_private_d4b_bundle(bundle)
    # Check forbidden path/basename fragments in string values.
    if forbidden_path_fragments:
        blob = json.dumps(bundle, sort_keys=True)
        for frag in forbidden_path_fragments:
            if frag and frag in blob:
                violations.append(
                    {
                        "category": "path_or_basename_in_bundle",
                        "fragment": "suppressed",
                    }
                )
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
# Conversion logic (filled packet batch -> D4b bundle, local-only)
# ---------------------------------------------------------------------------


def _decide_real_conversion_claim(
    *,
    synthetic_harness_test: bool,
    attestation_allows_real: bool,
    schema_valid: bool,
    tmp_guard_passed: bool,
) -> bool:
    """Decide whether ``local_private_conversion_executed`` may be true.

    True only for a real local private run: no synthetic harness flag,
    the D4d attestation passes (no model/proxy labels), the schema
    passes, and the resolved /tmp guard passes. Synthetic / in-memory
    harness runs are always false even if the bundle is human-manual-
    shaped. This function expresses the logic only; it does not itself
    claim execution in any committed artifact.
    """
    if synthetic_harness_test:
        return False
    if not attestation_allows_real:
        return False
    if not schema_valid:
        return False
    if not tmp_guard_passed:
        return False
    return True


def convert_filled_packets_to_d4b_bundle(
    *,
    filled_packets: dict[str, Any],
    synthetic_harness_test: bool,
    tmp_guard_passed: bool,
) -> dict[str, Any]:
    """Convert validated filled packets to a D4b bundle (local-only).

    Extracts ``label_slots`` from each packet into the bundle's
    ``labels`` list. No packet refs, source context, or rater IDs are
    carried over. The bundle is the recommended D4b bundle output shape
    (``schema=d4b_true_label_bundle_v1``,
    ``label_source=human_manual_true_e_s``, ``rater_count=2``,
    ``agreement_available=true``, ``confidence_intervals_available=false``)
    with synthetic/real flags set truthfully.

    For ``--synthetic-harness-test``:
    - ``synthetic_harness_test=true``
    - ``synthetic_labels_converted_for_harness_only=true``
    - ``local_private_conversion_executed=false``
    - ``real_human_labels_converted=false``

    For a real local private run (no synthetic flag, D4d attestation
    passes, no model/proxy labels, schema passes, /tmp guard passes):
    - ``synthetic_harness_test=false``
    - ``synthetic_labels_converted_for_harness_only=false``
    - ``local_private_conversion_executed=true``
    - ``real_human_labels_converted=true``

    The bundle never echoes input/output paths, basenames, packet refs,
    rater IDs, provider payloads, API secrets, model outputs, snippets,
    content_sha, query text, or candidate text.
    """
    attestation = filled_packets.get("d4d_runbook_attestation", {})
    attestation_allows_real = _attestation_allows_real_conversion(attestation)
    real_conversion = _decide_real_conversion_claim(
        synthetic_harness_test=synthetic_harness_test,
        attestation_allows_real=attestation_allows_real,
        schema_valid=True,  # already validated by the loader
        tmp_guard_passed=tmp_guard_passed,
    )
    labels: list[dict[str, Any]] = []
    for packet in filled_packets["packets"]:
        slots = packet["label_slots"]
        labels.append(
            {
                "e_score": slots["e_score"],
                "s_score": slots["s_score"],
                "bucket": slots["bucket"],
                "citation_valid": slots["citation_valid"],
                "rater_pair_present": slots["rater_pair_present"],
                "adjudicated": slots["adjudicated"],
            }
        )
    return {
        "schema": D4B_BUNDLE_SCHEMA_TARGET,
        "label_source": HUMAN_MANUAL_LABEL_SOURCE,
        "rater_count": 2,
        "agreement_available": True,
        "confidence_intervals_available": False,
        "synthetic_harness_test": bool(synthetic_harness_test),
        "synthetic_labels_converted_for_harness_only": bool(
            synthetic_harness_test
        ),
        "local_private_conversion_executed": bool(real_conversion),
        "real_human_labels_converted": bool(real_conversion),
        "labels": labels,
    }


# ---------------------------------------------------------------------------
# Default file-based loader / existence probe (injectable for self-test)
# ---------------------------------------------------------------------------


def _default_loader(input_path: Path) -> dict[str, Any]:
    """Read, parse, and validate a private filled-packet batch file.

    Raises ``_PrivateFilledPacketsLoadError`` on any I/O, parse, or
    schema failure. The CLI converts this into the fixed sanitized
    error.
    """
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        raise _PrivateFilledPacketsLoadError()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        raise _PrivateFilledPacketsLoadError()
    _validate_filled_packet_batch(data)
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
    synthetic_harness_test: bool,
) -> str | None:
    """Validate CLI argument combinations for public vs private converter.

    Pure: performs NO filesystem I/O (only lexical path checks). Returns
    an error message string if invalid, or ``None`` if valid. The guards
    below are evaluated BEFORE the input is opened or stat'd, proving
    validate-before-read.

    * ``--input-filled-packets`` without
      ``--allow-private-filled-packets`` -> error.
    * ``--allow-private-filled-packets`` without
      ``--input-filled-packets`` -> error.
    * ``--allow-private-filled-packets`` without explicit ``--out`` ->
      error.
    * ``--allow-private-filled-packets`` with the committed artifact
      path as ``--out`` -> error (before read).
    * ``--allow-private-filled-packets`` with a non-``/tmp`` ``--out`` ->
      error (before read).
    * ``--synthetic-harness-test`` without
      ``--allow-private-filled-packets`` -> error.
    * ``--allow-private-filled-packets --input-filled-packets <path>
      --out /tmp/...`` -> valid.
    """
    if input_path is not None and not allow_private:
        return (
            "--input-filled-packets requires "
            "--allow-private-filled-packets; refusing to read private "
            "filled packets without explicit opt-in"
        )
    if allow_private and input_path is None:
        return (
            "--allow-private-filled-packets requires "
            "--input-filled-packets; no private input path provided"
        )
    if synthetic_harness_test and not allow_private:
        return (
            "--synthetic-harness-test requires "
            "--allow-private-filled-packets; refusing to run a harness "
            "test without explicit opt-in"
        )
    if allow_private:
        if out_path is None:
            return (
                "--allow-private-filled-packets requires explicit --out "
                "under /tmp; refusing to use the committed artifact path"
            )
        if _is_committed_out(out_path):
            return (
                "--allow-private-filled-packets requires --out under "
                "/tmp; refusing to write to the committed artifact path"
            )
        if not _is_under_tmp(out_path):
            return (
                "--allow-private-filled-packets requires --out under "
                "/tmp; refusing to write private-mode output elsewhere"
            )
    return None


# ---------------------------------------------------------------------------
# Private converter runner (validate-before-read; resolved /tmp guard;
# sanitized errors)
# ---------------------------------------------------------------------------


def _run_private_converter_mode(
    *,
    allow_private: bool,
    input_path: Path | None,
    out_path: Path | None,
    synthetic_harness_test: bool,
    loader: Any,
    input_exists: Any,
    tmp_guard: Any = _validate_resolved_tmp_guard,
) -> tuple[dict[str, Any] | None, str | None]:
    """Run the private filled-packet -> D4b bundle converter.

    Returns ``(report, error)``: exactly one is non-``None``.

    The CLI/output guards are validated BEFORE the input is opened or
    stat'd (validate-before-read): lexical CLI args first (no
    filesystem), then the resolved ``/tmp`` guard (filesystem on the
    OUTPUT path only). Any load/parse/schema failure returns the fixed
    sanitized error; the input path, basename, raw JSON, and label text
    are never surfaced.
    """
    err = _validate_cli_args(
        allow_private=allow_private,
        input_path=input_path,
        out_path=out_path,
        synthetic_harness_test=synthetic_harness_test,
    )
    if err is not None:
        # Lexical validation failed: NO input or output filesystem access
        # performed.
        return None, err
    assert input_path is not None and out_path is not None
    # Lexical validation passed: validate the resolved /tmp output guard
    # (filesystem on the OUTPUT path only) before touching the input.
    tmp_err = tmp_guard(out_path)
    tmp_guard_passed = tmp_err is None
    if not tmp_guard_passed:
        # Output guard failed: NO input access performed.
        return None, tmp_err
    # Output guard passed: the input may now be touched.
    if not input_exists(input_path):
        return None, PRIVATE_LOAD_ERROR_MESSAGE
    try:
        filled_packets = loader(input_path)
    except Exception:
        return None, PRIVATE_LOAD_ERROR_MESSAGE
    # Re-validate the loaded filled packets (the real loader validates
    # internally and raises; this also covers in-memory probes that
    # return unvalidated data). Fail-closed sanitized error.
    try:
        _validate_filled_packet_batch(filled_packets)
    except _PrivateFilledPacketsLoadError:
        return None, PRIVATE_LOAD_ERROR_MESSAGE
    bundle = convert_filled_packets_to_d4b_bundle(
        filled_packets=filled_packets,
        synthetic_harness_test=synthetic_harness_test,
        tmp_guard_passed=tmp_guard_passed,
    )
    return bundle, None


# ---------------------------------------------------------------------------
# Report builders
# ---------------------------------------------------------------------------


def _build_public_report(
    checks: list[dict[str, Any]], all_passed: bool
) -> dict[str, Any]:
    """Assemble the public harness / no-conversion report (fail-closed scan).

    The default committed artifact. No private filled packets read, no
    conversion run, no D4b bundle created/written/validated, no labels
    collected/converted, no claims.
    """
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": TARGET_STATUS if all_passed else "self_test_failed",
        "mode": MODE_PUBLIC,
        "phase": PHASE,
        "d4c_packet_schema_source": D4C_PACKET_SCHEMA_SOURCE,
        "d4d_runbook_protocol": D4D_RUNBOOK_PROTOCOL,
        "d4b_bundle_schema_target": D4B_BUNDLE_SCHEMA_TARGET,
        "filled_packet_schema_contract":
            _build_filled_packet_schema_contract(),
        "d4d_runbook_contract": _build_d4d_runbook_contract(),
        "d4b_bundle_schema_contract": _build_d4b_bundle_schema_contract(),
        "d4b_mapping_contract": _build_d4b_mapping_contract(),
        "converter_harness_info": _build_converter_harness_info(),
        "self_test_summary": _self_test_category_summary(checks),
        "self_test_checks": checks,
        "self_test_passed": all_passed,
        # Default public mode reads/evaluates no filled-packet input, but
        # private conversion mode requires D4d attestation. Keep these scoped
        # fields separate so the public artifact cannot be misread as saying
        # private filled-packet input has no attestation requirement.
        "default_public_mode_input_attestation_evaluated": False,
        "private_conversion_d4d_attestation_required": True,
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


def _private_success_message(bundle_with_guard: dict[str, Any]) -> str:
    """Build the private-mode success stdout message (no exact /tmp path)."""
    guard = bundle_with_guard.get("private_bundle_guard", {})
    return (
        "wrote D4e private D4b bundle to /tmp output "
        f"(private_bundle_guard={guard.get('status')}, "
        f"conversion_run=true, "
        f"synthetic_harness_test={bundle_with_guard['synthetic_harness_test']}, "
        f"synthetic_labels_converted_for_harness_only="
        f"{bundle_with_guard['synthetic_labels_converted_for_harness_only']}, "
        f"local_private_conversion_executed="
        f"{bundle_with_guard['local_private_conversion_executed']}, "
        f"real_human_labels_converted="
        f"{bundle_with_guard['real_human_labels_converted']}, "
        f"d4b_true_label_bundle_created=true, "
        f"calibration_metrics_computed=false, "
        f"model_or_llm_labeling_performed=false) "
        f"[NOT committed; /tmp only]"
    )


def build_report() -> dict[str, Any]:
    """Assemble the public harness / no-conversion report (fail-closed scan).

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

    def __init__(
        self, records: dict[str, Any] | None = None
    ) -> None:
        self.calls: list[tuple[str, str]] = []
        self._records = records

    def loader(self, path: Path) -> dict[str, Any]:
        self.calls.append(("load", str(path)))
        if self._records is None:
            raise _PrivateFilledPacketsLoadError("probe: should not be called")
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


def _valid_synthetic_filled_packets(
    *,
    packet_count: int = 3,
) -> dict[str, Any]:
    """Build synthetic private filled packets for harness self-tests.

    Contains filled human-manual-shaped label slots (E/S values, bucket
    names, citation_valid/rater_pair_present/adjudicated booleans) and a
    passing D4d attestation. This is a HARNESS self-test fixture only;
    it must be run with the ``--synthetic-harness-test`` flag, which
    sets ``synthetic_harness_test=true`` and
    ``local_private_conversion_executed=false``.
    """
    packets: list[dict[str, Any]] = []
    e_levels = list(E_SCORE_LEVELS)
    s_levels = list(S_SCORE_LEVELS)
    buckets = list(BUCKET_NAMES)
    for i in range(packet_count):
        packets.append(
            {
                "packet_ref": f"local-packet-{i:04d}",
                "label_slots": {
                    "e_score": e_levels[i % len(e_levels)],
                    "s_score": s_levels[i % len(s_levels)],
                    "bucket": buckets[i % len(buckets)],
                    "citation_valid": (i % 2 == 0),
                    "rater_pair_present": True,
                    "adjudicated": (i % 3 == 0),
                },
            }
        )
    return {
        "schema": FILLED_PACKETS_SCHEMA,
        "source_packet_schema": D4C_PACKET_SCHEMA_SOURCE,
        "d4d_runbook_attestation": {
            "protocol": D4D_RUNBOOK_PROTOCOL,
            "two_independent_human_raters": True,
            "independent_before_adjudication": True,
            "no_llm_or_model_labels": True,
            "no_proxy_labels_as_true_labels": True,
            "local_only_storage": True,
        },
        "packets": packets,
    }


def _symlink_selftest_workspace() -> Path:
    """Create a unique /tmp workspace dir for symlink self-test fixtures."""
    pid = os.getpid()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    ws = Path("/tmp") / f"d4e_selftest_{pid}_{ts}"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all D4e self-test groups. Returns (checks, all_passed)."""
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
            "default_public_mode_input_attestation_evaluated_false",
            skeleton["default_public_mode_input_attestation_evaluated"]
            is False,
        )
    )
    checks.append(
        _check(
            "private_conversion_d4d_attestation_required_true",
            skeleton["private_conversion_d4d_attestation_required"] is True,
        )
    )
    checks.append(
        _check(
            "public_artifact_has_no_contradictory_attestation_flags",
            "input_attestation_required" not in skeleton
            and skeleton["d4d_attestation_required"] is True
            and skeleton["private_conversion_d4d_attestation_required"]
            is True
            and skeleton["private_filled_packets_read"] is False
            and skeleton["default_public_mode_input_attestation_evaluated"]
            is False,
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
            "mode_public_harness_no_filled_packets_no_conversion",
            skeleton["mode"] == MODE_PUBLIC,
        )
    )
    checks.append(
        _check("phase_d4e", skeleton["phase"] == PHASE)
    )
    checks.append(
        _check(
            "d4c_packet_schema_source_correct",
            skeleton["d4c_packet_schema_source"]
            == D4C_PACKET_SCHEMA_SOURCE,
        )
    )
    checks.append(
        _check(
            "d4d_runbook_protocol_correct",
            skeleton["d4d_runbook_protocol"] == D4D_RUNBOOK_PROTOCOL,
        )
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
            "filled_packet_schema_contract_defined_true",
            skeleton["filled_packet_schema_contract_defined"] is True,
        )
    )
    checks.append(
        _check(
            "d4d_attestation_required_true",
            skeleton["d4d_attestation_required"] is True,
        )
    )
    checks.append(
        _check(
            "d4b_bundle_schema_contract_defined_true",
            skeleton["d4b_bundle_schema_contract_defined"] is True,
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
            "filled_packet_schema_contract_has_schema_and_source",
            skeleton["filled_packet_schema_contract"]["schema"]
            == FILLED_PACKETS_SCHEMA
            and skeleton["filled_packet_schema_contract"][
                "source_packet_schema_ref"
            ]
            == D4C_PACKET_SCHEMA_SOURCE
            and skeleton["filled_packet_schema_contract"]["private_only"]
            is True
            and skeleton["filled_packet_schema_contract"][
                "may_contain_filled_label_slots"
            ]
            is True
            and skeleton["filled_packet_schema_contract"][
                "required_label_slots"
            ]
            == list(LABEL_SLOTS)
            and skeleton["filled_packet_schema_contract"][
                "required_attestation_fields"
            ]
            == list(ATTESTATION_FIELDS)
            and skeleton["filled_packet_schema_contract"][
                "rejects_source_context_fields"
            ]
            is True,
        )
    )
    checks.append(
        _check(
            "d4d_runbook_contract_protocol_correct",
            skeleton["d4d_runbook_contract"]["protocol"]
            == D4D_RUNBOOK_PROTOCOL
            and skeleton["d4d_runbook_contract"][
                "required_attestation_fields"
            ]
            == list(ATTESTATION_FIELDS)
            and skeleton["d4d_runbook_contract"][
                "attestation_must_be_all_true"
            ]
            is True
            and skeleton["d4d_runbook_contract"][
                "no_llm_or_model_labels_required"
            ]
            is True
            and skeleton["d4d_runbook_contract"][
                "no_proxy_labels_as_true_labels_required"
            ]
            is True
            and skeleton["d4d_runbook_contract"][
                "local_only_storage_required"
            ]
            is True,
        )
    )
    checks.append(
        _check(
            "d4b_bundle_schema_contract_has_schema_and_source",
            skeleton["d4b_bundle_schema_contract"]["schema"]
            == D4B_BUNDLE_SCHEMA_TARGET
            and skeleton["d4b_bundle_schema_contract"][
                "required_label_source"
            ]
            == HUMAN_MANUAL_LABEL_SOURCE
            and skeleton["d4b_bundle_schema_contract"][
                "bundle_allowed_keys"
            ]
            == sorted(ALLOWED_BUNDLE_KEYS)
            and skeleton["d4b_bundle_schema_contract"][
                "label_object_allowed_keys"
            ]
            == sorted(ALLOWED_LABEL_KEYS)
            and skeleton["d4b_bundle_schema_contract"]["e_score_levels"]
            == list(E_SCORE_LEVELS)
            and skeleton["d4b_bundle_schema_contract"]["s_score_levels"]
            == list(S_SCORE_LEVELS)
            and skeleton["d4b_bundle_schema_contract"]["bucket_names"]
            == list(BUCKET_NAMES)
            and skeleton["d4b_bundle_schema_contract"][
                "rejects_unknown_keys"
            ]
            is True
            and skeleton["d4b_bundle_schema_contract"][
                "rejects_packet_refs_paths_snippets_raters"
            ]
            is True,
        )
    )
    checks.append(
        _check(
            "d4b_mapping_contract_converter_not_run_by_default",
            skeleton["d4b_mapping_contract"]["target_bundle_schema"]
            == D4B_BUNDLE_SCHEMA_TARGET
            and skeleton["d4b_mapping_contract"]["packet_label_slots"]
            == list(LABEL_SLOTS)
            and skeleton["d4b_mapping_contract"]["source_packet_schema_ref"]
            == D4C_PACKET_SCHEMA_SOURCE
            and skeleton["d4b_mapping_contract"]["runbook_protocol"]
            == D4D_RUNBOOK_PROTOCOL
            and skeleton["d4b_mapping_contract"][
                "packet_to_bundle_requires_human_or_local_converter"
            ]
            is True
            and skeleton["d4b_mapping_contract"][
                "converter_not_run_by_default"
            ]
            is True
            and skeleton["d4b_mapping_contract"][
                "d4b_true_label_bundle_created"
            ]
            is False,
        )
    )
    checks.append(
        _check(
            "converter_harness_info_tmp_only_not_committed",
            skeleton["converter_harness_info"]["available"] is True
            and skeleton["converter_harness_info"]["opt_in_required"]
            is True
            and skeleton["converter_harness_info"]["output_location"]
            == "tmp_only_local_private"
            and skeleton["converter_harness_info"]["committed"] is False
            and skeleton["converter_harness_info"][
                "converts_filled_packets_to_d4b_bundle"
            ]
            is True
            and skeleton["converter_harness_info"][
                "rejects_source_context_fields"
            ]
            is True
            and skeleton["converter_harness_info"][
                "rejects_model_proxy_llm_labels"
            ]
            is True
            and skeleton["converter_harness_info"]["claims_calibration"]
            is False,
        )
    )

    # --- Group 3: No private read by default + public artifact clean. ---
    checks.append(
        _check(
            "default_mode_private_filled_packets_read_false",
            skeleton["private_filled_packets_read"] is False,
        )
    )
    checks.append(
        _check(
            "default_mode_conversion_run_false",
            skeleton["conversion_run"] is False,
        )
    )
    checks.append(
        _check(
            "default_mode_d4b_true_label_bundle_created_false",
            skeleton["d4b_true_label_bundle_created"] is False,
        )
    )
    checks.append(
        _check(
            "default_mode_d4b_true_label_bundle_written_false",
            skeleton["d4b_true_label_bundle_written"] is False,
        )
    )
    checks.append(
        _check(
            "default_mode_d4b_true_label_bundle_validated_false",
            skeleton["d4b_true_label_bundle_validated"] is False,
        )
    )
    checks.append(
        _check(
            "default_mode_labels_converted_false",
            skeleton["labels_converted"] is False,
        )
    )
    checks.append(
        _check(
            "default_mode_d5_unblocked_false",
            skeleton["d5_unblocked"] is False,
        )
    )
    checks.append(
        _check(
            "default_mode_no_packet_ref_key",
            not _has_dict_key_anywhere(skeleton, "packet_ref"),
        )
    )
    checks.append(
        _check(
            "default_mode_no_labels_key",
            not _has_dict_key_anywhere(skeleton, "labels"),
        )
    )
    checks.append(
        _check(
            "default_mode_no_packets_key",
            not _has_dict_key_anywhere(skeleton, "packets"),
        )
    )
    checks.append(
        _check(
            "default_mode_no_label_slots_key",
            not _has_dict_key_anywhere(skeleton, "label_slots"),
        )
    )
    checks.append(
        _check(
            "default_mode_no_d4d_runbook_attestation_key",
            not _has_dict_key_anywhere(skeleton, "d4d_runbook_attestation"),
        )
    )
    checks.append(
        _check(
            "default_mode_no_path_key",
            not _has_dict_key_anywhere(skeleton, "path"),
        )
    )
    checks.append(
        _check(
            "default_mode_no_snippet_key",
            not _has_dict_key_anywhere(skeleton, "snippet"),
        )
    )
    checks.append(
        _check(
            "default_mode_no_content_sha_key",
            not _has_dict_key_anywhere(skeleton, "content_sha"),
        )
    )
    checks.append(
        _check(
            "default_mode_no_query_text_key",
            not _has_dict_key_anywhere(skeleton, "query_text"),
        )
    )
    checks.append(
        _check(
            "default_mode_no_candidate_text_key",
            not _has_dict_key_anywhere(skeleton, "candidate_text"),
        )
    )

    # --- Group 4: Public scanner fail-closes + contract allowlist. ---
    def _has_cat(obj: Any, cat: str) -> bool:
        return any(v["category"] == cat for v in _scan_forbidden(obj))

    # Contract allowlist: field-name tokens ALLOWED as values inside
    # explicit contract field-name containers.
    checks.append(
        _check(
            "scanner_allows_label_slot_in_filled_packet_schema_contract",
            not _scan_forbidden(
                {
                    "filled_packet_schema_contract": {
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
                    "filled_packet_schema_contract": {
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
            "scanner_allows_attestation_fields_in_contract",
            not _scan_forbidden(
                {
                    "d4d_runbook_contract": {
                        "required_attestation_fields": list(ATTESTATION_FIELDS)
                    }
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_e_score_levels_in_contract",
            not _scan_forbidden(
                {
                    "d4b_bundle_schema_contract": {
                        "e_score_levels": list(E_SCORE_LEVELS)
                    }
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_bucket_names_in_contract",
            not _scan_forbidden(
                {
                    "d4b_bundle_schema_contract": {
                        "bucket_names": list(BUCKET_NAMES)
                    }
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_schema_refs_in_contract",
            not _scan_forbidden(
                {
                    "filled_packet_schema_contract": {
                        "schema": FILLED_PACKETS_SCHEMA,
                        "source_packet_schema_ref": D4C_PACKET_SCHEMA_SOURCE,
                    },
                    "d4d_runbook_contract": {
                        "protocol": D4D_RUNBOOK_PROTOCOL
                    },
                    "d4b_bundle_schema_contract": {
                        "schema": D4B_BUNDLE_SCHEMA_TARGET,
                        "required_label_source":
                            HUMAN_MANUAL_LABEL_SOURCE,
                    },
                }
            ),
        )
    )
    # Contract reject: unapproved string in contract container.
    checks.append(
        _check(
            "scanner_rejects_unapproved_string_in_contract",
            _has_cat(
                {
                    "filled_packet_schema_contract": {
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
            "scanner_rejects_content_sha_string_in_contract",
            _has_cat(
                {
                    "filled_packet_schema_contract": {
                        "field_names": ["content_sha"]
                    }
                },
                "unapproved_contract_string",
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_packet_ref_string_in_contract",
            _has_cat(
                {
                    "d4b_mapping_contract": {
                        "field_names": ["packet_ref"]
                    }
                },
                "unapproved_contract_string",
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_query_text_string_in_contract",
            _has_cat(
                {
                    "d4b_bundle_schema_contract": {
                        "field_names": ["query_text"]
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
        ({"packets": []}, "packets"),
        ({"source_packet_schema": "..."}, "source_packet_schema"),
        ({"d4d_runbook_attestation": {}}, "d4d_runbook_attestation"),
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
        "source_packet_schema", "d4d_runbook_attestation", "packets",
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
            "scanner_allows_safe_d4c_packet_schema_source_string",
            not _scan_forbidden(
                {"d4c_packet_schema_source": D4C_PACKET_SCHEMA_SOURCE}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_safe_d4d_runbook_protocol_string",
            not _scan_forbidden(
                {"d4d_runbook_protocol": D4D_RUNBOOK_PROTOCOL}
            ),
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

    # --- Group 4b: Fail-closed generation on scanner leak. ---
    raised = False
    try:
        _enforce_no_forbidden(
            {"path": "src/foo.rs", "content_sha": "a" * 64,
             "packet_ref": "p1", "query_text": _SECRET_SENTINEL,
             "labels": [{"e_score": "E0"}],
             "source_packet_schema": "leaked",
             "d4d_runbook_attestation": {}}
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

    # --- Group 5: D4d attestation validation. ---
    # Valid attestation validates.
    valid_att_ok = True
    try:
        _validate_d4d_attestation(
            _valid_synthetic_filled_packets()["d4d_runbook_attestation"]
        )
    except _PrivateFilledPacketsLoadError:
        valid_att_ok = False
    checks.append(
        _check("valid_d4d_attestation_validates", valid_att_ok)
    )
    # Missing attestation rejected (batch-level).
    missing_att_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        del recs["d4d_runbook_attestation"]
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        missing_att_rejected = True
    checks.append(
        _check("missing_d4d_attestation_rejected", missing_att_rejected)
    )
    # Missing attestation field rejected.
    missing_field_rejected = False
    try:
        att = dict(
            _valid_synthetic_filled_packets()["d4d_runbook_attestation"]
        )
        del att["no_llm_or_model_labels"]
        _validate_d4d_attestation(att)
    except _PrivateFilledPacketsLoadError:
        missing_field_rejected = True
    checks.append(
        _check("missing_attestation_field_rejected", missing_field_rejected)
    )
    # Extra attestation field rejected.
    extra_att_rejected = False
    try:
        att = dict(
            _valid_synthetic_filled_packets()["d4d_runbook_attestation"]
        )
        att["rater_id"] = "alice"
        _validate_d4d_attestation(att)
    except _PrivateFilledPacketsLoadError:
        extra_att_rejected = True
    checks.append(
        _check("extra_attestation_field_rejected", extra_att_rejected)
    )
    # Wrong protocol rejected.
    wrong_protocol_rejected = False
    try:
        att = dict(
            _valid_synthetic_filled_packets()["d4d_runbook_attestation"]
        )
        att["protocol"] = "wrong_protocol"
        _validate_d4d_attestation(att)
    except _PrivateFilledPacketsLoadError:
        wrong_protocol_rejected = True
    checks.append(
        _check("wrong_attestation_protocol_rejected", wrong_protocol_rejected)
    )
    # no_llm_or_model_labels=false rejected (model/LLM attestation).
    llm_att_rejected = False
    try:
        att = dict(
            _valid_synthetic_filled_packets()["d4d_runbook_attestation"]
        )
        att["no_llm_or_model_labels"] = False
        _validate_d4d_attestation(att)
    except _PrivateFilledPacketsLoadError:
        llm_att_rejected = True
    checks.append(
        _check("model_llm_attestation_rejected", llm_att_rejected)
    )
    # no_proxy_labels_as_true_labels=false rejected (proxy attestation).
    proxy_att_rejected = False
    try:
        att = dict(
            _valid_synthetic_filled_packets()["d4d_runbook_attestation"]
        )
        att["no_proxy_labels_as_true_labels"] = False
        _validate_d4d_attestation(att)
    except _PrivateFilledPacketsLoadError:
        proxy_att_rejected = True
    checks.append(
        _check("proxy_attestation_rejected", proxy_att_rejected)
    )
    # local_only_storage=false rejected.
    no_local_rejected = False
    try:
        att = dict(
            _valid_synthetic_filled_packets()["d4d_runbook_attestation"]
        )
        att["local_only_storage"] = False
        _validate_d4d_attestation(att)
    except _PrivateFilledPacketsLoadError:
        no_local_rejected = True
    checks.append(
        _check("no_local_storage_attestation_rejected", no_local_rejected)
    )
    # two_independent_human_raters=false rejected.
    one_rater_rejected = False
    try:
        att = dict(
            _valid_synthetic_filled_packets()["d4d_runbook_attestation"]
        )
        att["two_independent_human_raters"] = False
        _validate_d4d_attestation(att)
    except _PrivateFilledPacketsLoadError:
        one_rater_rejected = True
    checks.append(
        _check("one_rater_attestation_rejected", one_rater_rejected)
    )
    # independent_before_adjudication=false rejected.
    no_indep_rejected = False
    try:
        att = dict(
            _valid_synthetic_filled_packets()["d4d_runbook_attestation"]
        )
        att["independent_before_adjudication"] = False
        _validate_d4d_attestation(att)
    except _PrivateFilledPacketsLoadError:
        no_indep_rejected = True
    checks.append(
        _check("no_independence_attestation_rejected", no_indep_rejected)
    )

    # --- Group 6: Filled-packet batch validation (rejects source
    # context fields, rater IDs, paths, snippets, content_sha, query/
    # candidate text). ---
    # Valid filled packets validate.
    valid_ok = True
    try:
        _validate_filled_packet_batch(_valid_synthetic_filled_packets())
    except _PrivateFilledPacketsLoadError:
        valid_ok = False
    checks.append(
        _check("valid_filled_packets_validate", valid_ok)
    )
    # Unknown schema rejected.
    bad_schema_rejected = False
    try:
        _validate_filled_packet_batch(
            {**_valid_synthetic_filled_packets(), "schema": "wrong"}
        )
    except _PrivateFilledPacketsLoadError:
        bad_schema_rejected = True
    checks.append(
        _check("unknown_filled_packets_schema_rejected", bad_schema_rejected)
    )
    # Wrong source_packet_schema rejected.
    bad_source_rejected = False
    try:
        _validate_filled_packet_batch(
            {
                **_valid_synthetic_filled_packets(),
                "source_packet_schema": "wrong",
            }
        )
    except _PrivateFilledPacketsLoadError:
        bad_source_rejected = True
    checks.append(
        _check("wrong_source_packet_schema_rejected", bad_source_rejected)
    )
    # Extra top-level key rejected.
    extra_top_rejected = False
    try:
        _validate_filled_packet_batch(
            {**_valid_synthetic_filled_packets(), "extra": 1}
        )
    except _PrivateFilledPacketsLoadError:
        extra_top_rejected = True
    checks.append(
        _check("unknown_top_key_rejected", extra_top_rejected)
    )
    # Empty packets list rejected.
    empty_packets_rejected = False
    try:
        _validate_filled_packet_batch(
            {**_valid_synthetic_filled_packets(), "packets": []}
        )
    except _PrivateFilledPacketsLoadError:
        empty_packets_rejected = True
    checks.append(
        _check("empty_packets_rejected", empty_packets_rejected)
    )
    # Non-dict batch rejected.
    non_dict_rejected = False
    try:
        _validate_filled_packet_batch([1, 2, 3])  # type: ignore[arg-type]
    except _PrivateFilledPacketsLoadError:
        non_dict_rejected = True
    checks.append(
        _check("non_dict_batch_rejected", non_dict_rejected)
    )
    # Packet with extra key (path) rejected.
    path_packet_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        recs = {
            **recs,
            "packets": [{**recs["packets"][0], "path": "src/x.rs"}],
        }
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        path_packet_rejected = True
    checks.append(
        _check("packet_with_path_rejected", path_packet_rejected)
    )
    # Packet with snippet rejected.
    snippet_packet_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        recs = {
            **recs,
            "packets": [
                {**recs["packets"][0], "snippet": _SECRET_SENTINEL}
            ],
        }
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        snippet_packet_rejected = True
    checks.append(
        _check("packet_with_snippet_rejected", snippet_packet_rejected)
    )
    # Packet with content_sha rejected.
    sha_packet_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        recs = {
            **recs,
            "packets": [
                {**recs["packets"][0], "content_sha": "a" * 64}
            ],
        }
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        sha_packet_rejected = True
    checks.append(
        _check("packet_with_content_sha_rejected", sha_packet_rejected)
    )
    # Packet with query_text rejected.
    query_packet_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        recs = {
            **recs,
            "packets": [
                {**recs["packets"][0], "query_text": "private query"}
            ],
        }
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        query_packet_rejected = True
    checks.append(
        _check("packet_with_query_text_rejected", query_packet_rejected)
    )
    # Packet with candidate_text rejected.
    candidate_packet_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        recs = {
            **recs,
            "packets": [
                {**recs["packets"][0], "candidate_text": "private text"}
            ],
        }
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        candidate_packet_rejected = True
    checks.append(
        _check(
            "packet_with_candidate_text_rejected",
            candidate_packet_rejected,
        )
    )
    # Packet with rater_id rejected.
    rater_packet_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        recs = {
            **recs,
            "packets": [
                {**recs["packets"][0], "rater_id": "alice"}
            ],
        }
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        rater_packet_rejected = True
    checks.append(
        _check("packet_with_rater_id_rejected", rater_packet_rejected)
    )
    # Packet with task_id rejected.
    task_packet_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        recs = {
            **recs,
            "packets": [
                {**recs["packets"][0], "task_id": "task-001"}
            ],
        }
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        task_packet_rejected = True
    checks.append(
        _check("packet_with_task_id_rejected", task_packet_rejected)
    )
    # Packet with provider_payload rejected.
    provider_packet_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        recs = {
            **recs,
            "packets": [
                {**recs["packets"][0], "provider_payload": {"x": 1}}
            ],
        }
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        provider_packet_rejected = True
    checks.append(
        _check(
            "packet_with_provider_payload_rejected",
            provider_packet_rejected,
        )
    )
    # Packet with api_key rejected.
    api_packet_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        recs = {
            **recs,
            "packets": [
                {**recs["packets"][0], "api_key": "sk-" + _SECRET_SENTINEL}
            ],
        }
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        api_packet_rejected = True
    checks.append(
        _check("packet_with_api_key_rejected", api_packet_rejected)
    )
    # Packet with model_output rejected.
    model_packet_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        recs = {
            **recs,
            "packets": [
                {**recs["packets"][0], "model_output": "x"}
            ],
        }
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        model_packet_rejected = True
    checks.append(
        _check("packet_with_model_output_rejected", model_packet_rejected)
    )
    # Packet with extra source-context field rejected.
    extra_packet_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        recs = {
            **recs,
            "packets": [
                {**recs["packets"][0], "annotation_instructions": "x"}
            ],
        }
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        extra_packet_rejected = True
    checks.append(
        _check(
            "packet_with_annotation_instructions_rejected",
            extra_packet_rejected,
        )
    )
    # Packet missing packet_ref rejected.
    missing_ref_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        bad_packet = dict(recs["packets"][0])
        del bad_packet["packet_ref"]
        recs = {**recs, "packets": [bad_packet]}
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        missing_ref_rejected = True
    checks.append(
        _check("packet_missing_packet_ref_rejected", missing_ref_rejected)
    )
    # Packet missing label_slots rejected.
    missing_slots_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        bad_packet = dict(recs["packets"][0])
        del bad_packet["label_slots"]
        recs = {**recs, "packets": [bad_packet]}
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        missing_slots_rejected = True
    checks.append(
        _check("packet_missing_label_slots_rejected", missing_slots_rejected)
    )
    # Label slots with extra key rejected.
    extra_slot_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        bad_packet = dict(recs["packets"][0])
        bad_packet = {
            **bad_packet,
            "label_slots": {
                **bad_packet["label_slots"],
                "rater_id": "alice",
            },
        }
        recs = {**recs, "packets": [bad_packet]}
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        extra_slot_rejected = True
    checks.append(
        _check("label_slot_with_extra_key_rejected", extra_slot_rejected)
    )
    # Invalid e_score rejected.
    bad_e_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        bad_packet = dict(recs["packets"][0])
        bad_packet = {
            **bad_packet,
            "label_slots": {**bad_packet["label_slots"], "e_score": "E9"},
        }
        recs = {**recs, "packets": [bad_packet]}
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        bad_e_rejected = True
    checks.append(
        _check("invalid_e_score_rejected", bad_e_rejected)
    )
    # Invalid bucket rejected.
    bad_bucket_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        bad_packet = dict(recs["packets"][0])
        bad_packet = {
            **bad_packet,
            "label_slots": {
                **bad_packet["label_slots"],
                "bucket": "unknown_bucket",
            },
        }
        recs = {**recs, "packets": [bad_packet]}
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        bad_bucket_rejected = True
    checks.append(
        _check("invalid_bucket_rejected", bad_bucket_rejected)
    )
    # Non-bool citation_valid rejected.
    non_bool_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        bad_packet = dict(recs["packets"][0])
        bad_packet = {
            **bad_packet,
            "label_slots": {
                **bad_packet["label_slots"],
                "citation_valid": "yes",
            },
        }
        recs = {**recs, "packets": [bad_packet]}
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        non_bool_rejected = True
    checks.append(
        _check("non_bool_citation_valid_rejected", non_bool_rejected)
    )
    # Empty packet_ref rejected.
    empty_ref_rejected = False
    try:
        recs = _valid_synthetic_filled_packets()
        bad_packet = dict(recs["packets"][0])
        bad_packet = {**bad_packet, "packet_ref": ""}
        recs = {**recs, "packets": [bad_packet]}
        _validate_filled_packet_batch(recs)
    except _PrivateFilledPacketsLoadError:
        empty_ref_rejected = True
    checks.append(
        _check("empty_packet_ref_rejected", empty_ref_rejected)
    )

    # --- Group 7: Real-mode flag-path decision logic. ---
    checks.append(
        _check(
            "real_conversion_synthetic_harness_test_false",
            _decide_real_conversion_claim(
                synthetic_harness_test=True,
                attestation_allows_real=True,
                schema_valid=True,
                tmp_guard_passed=True,
            )
            is False,
        )
    )
    checks.append(
        _check(
            "real_conversion_real_passes_true",
            _decide_real_conversion_claim(
                synthetic_harness_test=False,
                attestation_allows_real=True,
                schema_valid=True,
                tmp_guard_passed=True,
            )
            is True,
        )
    )
    checks.append(
        _check(
            "real_conversion_model_proxy_attestation_false",
            _decide_real_conversion_claim(
                synthetic_harness_test=False,
                attestation_allows_real=False,
                schema_valid=True,
                tmp_guard_passed=True,
            )
            is False,
        )
    )
    checks.append(
        _check(
            "real_conversion_invalid_schema_false",
            _decide_real_conversion_claim(
                synthetic_harness_test=False,
                attestation_allows_real=True,
                schema_valid=False,
                tmp_guard_passed=True,
            )
            is False,
        )
    )
    checks.append(
        _check(
            "real_conversion_tmp_guard_failed_false",
            _decide_real_conversion_claim(
                synthetic_harness_test=False,
                attestation_allows_real=True,
                schema_valid=True,
                tmp_guard_passed=False,
            )
            is False,
        )
    )

    # --- Group 8: CLI guard matrix (pure lexical). ---
    sensitive_input = Path(
        "/private/SECRET_CONVERTER_SENTINEL_sensitive.json"
    )
    # --input-filled-packets without --allow-private-filled-packets => error.
    err_input_no_allow = _validate_cli_args(
        allow_private=False,
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
            and _SECRET_SENTINEL not in err_input_no_allow,
        )
    )
    # --allow-private-filled-packets without --input-filled-packets => error.
    err_allow_no_input = _validate_cli_args(
        allow_private=True,
        input_path=None,
        out_path=Path("/tmp/d4e.json"),
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
        allow_private=True,
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
            and _SECRET_SENTINEL not in err_no_out,
        )
    )
    # allow + committed artifact out => error.
    err_committed = _validate_cli_args(
        allow_private=True,
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
            and _SECRET_SENTINEL not in err_committed,
        )
    )
    # allow + non-/tmp out => error.
    err_non_tmp = _validate_cli_args(
        allow_private=True,
        input_path=sensitive_input,
        out_path=Path("/not/tmp/d4e.json"),
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
            and _SECRET_SENTINEL not in err_non_tmp,
        )
    )
    # --synthetic-harness-test without --allow-private-filled-packets => error.
    err_synth_no_allow = _validate_cli_args(
        allow_private=False,
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
        allow_private=True,
        input_path=sensitive_input,
        out_path=Path("/tmp/d4e_bundle.json"),
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
        allow_private=True,
        input_path=sensitive_input,
        out_path=Path("/tmp/d4e_harness.json"),
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
        allow_private=False,
        input_path=None,
        out_path=None,
        synthetic_harness_test=False,
    )
    checks.append(
        _check("cli_default_mode_allowed", err_default is None)
    )
    # path traversal /tmp/../etc is NOT under /tmp.
    err_traversal = _validate_cli_args(
        allow_private=True,
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

    # --- Group 9: Validate-before-read (probe records no input access). ---
    probe_invalid = _ReadProbe()
    _report, err_probe = _run_private_converter_mode(
        allow_private=True,
        input_path=Path(
            "/private/SECRET_CONVERTER_SENTINEL_nonexistent.json"
        ),
        out_path=Path("/not/tmp/d4e.json"),  # invalid out (lexical)
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
            and _SECRET_SENTINEL not in err_probe
            and "nonexistent.json" not in err_probe,
        )
    )
    # Committed-out rejected before read.
    probe_committed = _ReadProbe()
    _report2, err_pc = _run_private_converter_mode(
        allow_private=True,
        input_path=Path("/private/SECRET_CONVERTER_SENTINEL.json"),
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
    _report3, err_pn = _run_private_converter_mode(
        allow_private=True,
        input_path=Path("/private/SECRET_CONVERTER_SENTINEL.json"),
        out_path=Path("/home/user/d4e.json"),
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
    _report4, err_ps = _run_private_converter_mode(
        allow_private=False,
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
    # Input without allow rejected before read.
    probe_input_only = _ReadProbe()
    _report5, err_pio = _run_private_converter_mode(
        allow_private=False,
        input_path=Path("/private/SECRET_CONVERTER_SENTINEL.json"),
        out_path=None,
        synthetic_harness_test=False,
        loader=probe_input_only.loader,
        input_exists=probe_input_only.exists,
    )
    checks.append(
        _check(
            "input_without_allow_rejected_before_read",
            err_pio is not None and probe_input_only.calls == [],
        )
    )
    # Allow without input rejected before read.
    probe_allow_only = _ReadProbe()
    _report6, err_ao = _run_private_converter_mode(
        allow_private=True,
        input_path=None,
        out_path=Path("/tmp/d4e.json"),
        synthetic_harness_test=False,
        loader=probe_allow_only.loader,
        input_exists=probe_allow_only.exists,
    )
    checks.append(
        _check(
            "allow_without_input_rejected_before_read",
            err_ao is not None and probe_allow_only.calls == [],
        )
    )

    # --- Group 10: Sanitized error with sensitive basename + sentinel. ---
    # Malformed filled packets (extra keys + sentinel) returned by a
    # loader: the schema validator must reject it and only the fixed
    # sanitized error is surfaced; nothing reaches the bundle.
    malformed_packets = {
        "schema": FILLED_PACKETS_SCHEMA,
        "source_packet_schema": D4C_PACKET_SCHEMA_SOURCE,
        "d4d_runbook_attestation": _valid_synthetic_filled_packets()[
            "d4d_runbook_attestation"
        ],
        "packets": [
            {
                "packet_ref": "p1",
                "label_slots": {
                    "e_score": "E0", "s_score": "S0",
                    "bucket": "primary_evidence",
                    "citation_valid": True,
                    "rater_pair_present": True,
                    "adjudicated": True,
                },
                "provider_payload": {"x": _SECRET_SENTINEL},
                "api_key": "sk-" + _SECRET_SENTINEL,
            }
        ],
    }
    probe_malformed = _ReadProbe(records=malformed_packets)
    _report7, err_malformed = _run_private_converter_mode(
        allow_private=True,
        input_path=Path(
            "/private/SECRET_CONVERTER_SENTINEL_bundle.json"
        ),
        out_path=Path("/tmp/d4e_malformed.json"),
        synthetic_harness_test=False,
        loader=probe_malformed.loader,
        input_exists=probe_malformed.exists,
    )
    checks.append(
        _check(
            "malformed_packets_returns_sanitized_error",
            err_malformed == PRIVATE_LOAD_ERROR_MESSAGE
            and _report7 is None,
        )
    )
    checks.append(
        _check(
            "malformed_packets_error_no_sentinel_or_basename",
            err_malformed is not None
            and _SECRET_SENTINEL not in err_malformed
            and "SECRET_CONVERTER_SENTINEL_bundle.json"
            not in err_malformed
            and "sk-" not in err_malformed,
        )
    )
    # Nonexistent input returns the sanitized error (no path leak).
    probe_missing = _ReadProbe(records=None)
    probe_missing.exists = lambda p: False  # type: ignore[method-assign]
    _report8, err_missing = _run_private_converter_mode(
        allow_private=True,
        input_path=Path(
            "/private/SECRET_CONVERTER_SENTINEL_missing.json"
        ),
        out_path=Path("/tmp/d4e_missing.json"),
        synthetic_harness_test=False,
        loader=probe_missing.loader,
        input_exists=probe_missing.exists,
    )
    checks.append(
        _check(
            "missing_input_returns_sanitized_error",
            err_missing == PRIVATE_LOAD_ERROR_MESSAGE
            and _report8 is None,
        )
    )
    checks.append(
        _check(
            "missing_input_error_no_path_basename_leak",
            err_missing is not None
            and _SECRET_SENTINEL not in err_missing
            and "SECRET_CONVERTER_SENTINEL_missing.json"
            not in err_missing,
        )
    )

    # --- Group 11: Private converter success path (synthetic harness
    # test) — no path/basename/raw label/exact counts/output path in
    # bundle. ---
    valid_records = _valid_synthetic_filled_packets()
    sensitive_in = Path(
        "/private/SECRET_CONVERTER_SENTINEL_success.json"
    )
    sensitive_out = Path("/tmp/SECRET_CONVERTER_SENTINEL_out.json")
    probe_ok = _ReadProbe(records=valid_records)
    bundle_ok, err_ok = _run_private_converter_mode(
        allow_private=True,
        input_path=sensitive_in,
        out_path=sensitive_out,
        synthetic_harness_test=True,
        loader=probe_ok.loader,
        input_exists=probe_ok.exists,
    )
    checks.append(
        _check(
            "private_success_returns_bundle",
            err_ok is None and bundle_ok is not None,
        )
    )
    ok_blob = json.dumps(bundle_ok, sort_keys=True) if bundle_ok else ""
    # No packet refs / paths / snippets / content_sha / query /
    # candidate text in the bundle.
    checks.append(
        _check(
            "private_bundle_no_packet_ref_key",
            bundle_ok is not None
            and not _has_dict_key_anywhere(bundle_ok, "packet_ref"),
        )
    )
    checks.append(
        _check(
            "private_bundle_no_path_key",
            bundle_ok is not None
            and not _has_dict_key_anywhere(bundle_ok, "path"),
        )
    )
    checks.append(
        _check(
            "private_bundle_no_snippet_key",
            bundle_ok is not None
            and not _has_dict_key_anywhere(bundle_ok, "snippet"),
        )
    )
    checks.append(
        _check(
            "private_bundle_no_content_sha_key",
            bundle_ok is not None
            and not _has_dict_key_anywhere(bundle_ok, "content_sha"),
        )
    )
    checks.append(
        _check(
            "private_bundle_no_query_text_key",
            bundle_ok is not None
            and not _has_dict_key_anywhere(bundle_ok, "query_text"),
        )
    )
    checks.append(
        _check(
            "private_bundle_no_candidate_text_key",
            bundle_ok is not None
            and not _has_dict_key_anywhere(bundle_ok, "candidate_text"),
        )
    )
    checks.append(
        _check(
            "private_bundle_no_rater_id_key",
            bundle_ok is not None
            and not _has_dict_key_anywhere(bundle_ok, "rater_id"),
        )
    )
    checks.append(
        _check(
            "private_bundle_no_task_id_key",
            bundle_ok is not None
            and not _has_dict_key_anywhere(bundle_ok, "task_id"),
        )
    )
    checks.append(
        _check(
            "private_bundle_no_packets_key",
            bundle_ok is not None
            and not _has_dict_key_anywhere(bundle_ok, "packets"),
        )
    )
    checks.append(
        _check(
            "private_bundle_no_d4d_runbook_attestation_key",
            bundle_ok is not None
            and not _has_dict_key_anywhere(
                bundle_ok, "d4d_runbook_attestation"
            ),
        )
    )
    checks.append(
        _check(
            "private_bundle_no_source_packet_schema_key",
            bundle_ok is not None
            and not _has_dict_key_anywhere(
                bundle_ok, "source_packet_schema"
            ),
        )
    )
    # No sentinel / input path / output path / basename in bundle.
    checks.append(
        _check(
            "private_bundle_no_sentinel",
            _SECRET_SENTINEL not in ok_blob,
        )
    )
    checks.append(
        _check(
            "private_bundle_no_input_path_or_basename",
            str(sensitive_in) not in ok_blob
            and sensitive_in.name not in ok_blob
            and "/private" not in ok_blob,
        )
    )
    checks.append(
        _check(
            "private_bundle_no_output_path_or_basename",
            str(sensitive_out) not in ok_blob
            and sensitive_out.name not in ok_blob,
        )
    )
    # Synthetic harness metadata truthfully marked.
    checks.append(
        _check(
            "private_bundle_synthetic_harness_test_true",
            bundle_ok is not None
            and bundle_ok["synthetic_harness_test"] is True,
        )
    )
    checks.append(
        _check(
            "private_bundle_synthetic_labels_converted_harness_only_true",
            bundle_ok is not None
            and bundle_ok[
                "synthetic_labels_converted_for_harness_only"
            ]
            is True,
        )
    )
    checks.append(
        _check(
            "private_bundle_local_private_conversion_executed_false_synthetic",
            bundle_ok is not None
            and bundle_ok["local_private_conversion_executed"] is False,
        )
    )
    checks.append(
        _check(
            "private_bundle_real_human_labels_converted_false_synthetic",
            bundle_ok is not None
            and bundle_ok["real_human_labels_converted"] is False,
        )
    )
    # Bundle has correct schema, label_source, and labels list.
    checks.append(
        _check(
            "private_bundle_schema_correct",
            bundle_ok is not None
            and bundle_ok["schema"] == D4B_BUNDLE_SCHEMA_TARGET,
        )
    )
    checks.append(
        _check(
            "private_bundle_label_source_correct",
            bundle_ok is not None
            and bundle_ok["label_source"] == HUMAN_MANUAL_LABEL_SOURCE,
        )
    )
    checks.append(
        _check(
            "private_bundle_labels_present_and_correct_shape",
            bundle_ok is not None
            and isinstance(bundle_ok.get("labels"), list)
            and len(bundle_ok["labels"]) == len(valid_records["packets"])
            and all(
                isinstance(entry, dict)
                and set(entry.keys()) == ALLOWED_LABEL_KEYS
                and entry["e_score"] in E_SCORE_LEVELS
                and entry["s_score"] in S_SCORE_LEVELS
                and entry["bucket"] in BUCKET_NAMES
                and isinstance(entry["citation_valid"], bool)
                and isinstance(entry["rater_pair_present"], bool)
                and isinstance(entry["adjudicated"], bool)
                for entry in bundle_ok["labels"]
            ),
        )
    )
    # No calibration / agreement / CI / model labeling / release gate.
    checks.append(
        _check(
            "private_bundle_no_claim_flags",
            bundle_ok is not None
            and "calibration_metrics_computed" not in bundle_ok
            and "inter_rater_agreement_measured" not in bundle_ok
            and "confidence_intervals_computed" not in bundle_ok
            and "model_or_llm_labeling_performed" not in bundle_ok
            and "public_release_gate_passed" not in bundle_ok,
        )
    )
    # Private bundle guard passes (with path fragments blocked).
    guard = _private_bundle_guard_summary(
        bundle_ok,
        forbidden_path_fragments=(
            str(sensitive_in),
            sensitive_in.name,
            str(sensitive_out),
            sensitive_out.name,
        ),
    )
    checks.append(
        _check(
            "private_bundle_guard_passes_clean_bundle",
            guard["status"] == "pass" and guard["violations_count"] == 0,
        )
    )
    # Success stdout message has no exact path.
    bundle_ok_with_guard = dict(bundle_ok) if bundle_ok else {}
    bundle_ok_with_guard["private_bundle_guard"] = guard
    msg = (
        _private_success_message(bundle_ok_with_guard)
        if bundle_ok else ""
    )
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

    # --- Group 12: Real-mode flag-path test (in-memory, NOT committed).
    # A real-mode run (synthetic flag false, D4d attestation passes, no
    # model/proxy labels, schema passes, /tmp guard passes) over a
    # synthetic fixture can set local_private_conversion_executed=true
    # and real_human_labels_converted=true only locally. Docs mark this
    # as a flag-path test, NOT evidence that real labels exist.
    probe_real = _ReadProbe(records=valid_records)
    bundle_real, err_real = _run_private_converter_mode(
        allow_private=True,
        input_path=Path(
            "/private/SECRET_CONVERTER_SENTINEL_real.json"
        ),
        out_path=Path("/tmp/SECRET_CONVERTER_SENTINEL_real_out.json"),
        synthetic_harness_test=False,
        loader=probe_real.loader,
        input_exists=probe_real.exists,
    )
    checks.append(
        _check(
            "real_mode_bundle_local_conversion_true",
            err_real is None
            and bundle_real is not None
            and bundle_real["synthetic_harness_test"] is False
            and bundle_real["local_private_conversion_executed"] is True
            and bundle_real["real_human_labels_converted"] is True,
        )
    )
    checks.append(
        _check(
            "real_mode_bundle_synthetic_labels_converted_false",
            bundle_real is not None
            and bundle_real[
                "synthetic_labels_converted_for_harness_only"
            ]
            is False,
        )
    )
    checks.append(
        _check(
            "real_mode_bundle_no_sentinel_or_paths",
            bundle_real is not None
            and _SECRET_SENTINEL
            not in json.dumps(bundle_real, sort_keys=True),
        )
    )
    checks.append(
        _check(
            "real_mode_bundle_guard_passes",
            bundle_real is not None
            and _private_bundle_guard_summary(
                bundle_real,
                forbidden_path_fragments=(
                    "/private/SECRET_CONVERTER_SENTINEL_real.json",
                    "SECRET_CONVERTER_SENTINEL_real.json",
                    "/tmp/SECRET_CONVERTER_SENTINEL_real_out.json",
                    "SECRET_CONVERTER_SENTINEL_real_out.json",
                ),
            )["status"]
            == "pass",
        )
    )

    # --- Group 13: /tmp synthetic write smoke (NOT committed). ---
    ws = None
    tmp_in = None
    tmp_out = None
    try:
        ws = _symlink_selftest_workspace()
        tmp_in = ws / "filled_packets.json"
        tmp_out = ws / "d4b_bundle.json"
        _write_json(tmp_in, valid_records)
        bundle_file, err_file = _run_private_converter_mode(
            allow_private=True,
            input_path=tmp_in,
            out_path=tmp_out,
            synthetic_harness_test=True,
            loader=_default_loader,
            input_exists=_default_exists,
        )
        checks.append(
            _check(
                "tmp_smoke_success_returns_bundle",
                err_file is None and bundle_file is not None,
            )
        )
        # Write the bundle and read it back to prove /tmp write works.
        if bundle_file is not None:
            _write_json(tmp_out, bundle_file)
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
                    "tmp_smoke_readback_has_correct_schema",
                    read_back["schema"] == D4B_BUNDLE_SCHEMA_TARGET
                    and read_back["label_source"]
                    == HUMAN_MANUAL_LABEL_SOURCE,
                )
            )
            checks.append(
                _check(
                    "tmp_smoke_readback_has_labels",
                    isinstance(read_back.get("labels"), list)
                    and len(read_back["labels"])
                    == len(valid_records["packets"]),
                )
            )
            checks.append(
                _check(
                    "tmp_smoke_readback_no_packet_refs",
                    not _has_dict_key_anywhere(read_back, "packet_ref"),
                )
            )
            checks.append(
                _check(
                    "tmp_smoke_readback_no_paths_snippets_query",
                    not _has_dict_key_anywhere(read_back, "path")
                    and not _has_dict_key_anywhere(read_back, "snippet")
                    and not _has_dict_key_anywhere(read_back, "content_sha")
                    and not _has_dict_key_anywhere(read_back, "query_text")
                    and not _has_dict_key_anywhere(
                        read_back, "candidate_text"
                    ),
                )
            )
            checks.append(
                _check(
                    "tmp_smoke_readback_no_input_output_path",
                    str(tmp_in) not in json.dumps(read_back, sort_keys=True)
                    and str(tmp_out)
                    not in json.dumps(read_back, sort_keys=True)
                    and tmp_in.name
                    not in json.dumps(read_back, sort_keys=True)
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
            # Synthetic mode truthfully marked.
            checks.append(
                _check(
                    "tmp_smoke_readback_synthetic_harness_test_true",
                    read_back["synthetic_harness_test"] is True
                    and read_back[
                        "synthetic_labels_converted_for_harness_only"
                    ]
                    is True
                    and read_back["local_private_conversion_executed"]
                    is False
                    and read_back["real_human_labels_converted"] is False,
                )
            )
        else:
            checks.append(_check("tmp_smoke_success_returns_bundle", False))
    finally:
        import shutil
        if ws is not None:
            shutil.rmtree(ws, ignore_errors=True)

    # --- Group 14: Resolved /tmp symlink-escape guards (filesystem). ---
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
        _rep_esc, err_esc = _run_private_converter_mode(
            allow_private=True,
            input_path=Path(
                "/private/SECRET_CONVERTER_SENTINEL_esc.json"
            ),
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
        _rep_fs, err_fs = _run_private_converter_mode(
            allow_private=True,
            input_path=Path(
                "/private/SECRET_CONVERTER_SENTINEL_fs.json"
            ),
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
        out_valid = ws2 / "valid_out.json"
        probe_vo = _ReadProbe(records=valid_records)
        _rep_vo, err_vo = _run_private_converter_mode(
            allow_private=True,
            input_path=Path(
                "/private/SECRET_CONVERTER_SENTINEL_vo.json"
            ),
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
        import shutil
        if ws2 is not None:
            shutil.rmtree(ws2, ignore_errors=True)

    # --- Group 15: Private bundle output guard rejects bad bundles. ---
    # Packet ref key -> guard fails.
    bad_bundle = dict(bundle_ok) if bundle_ok else {}
    bad_bundle["packet_ref"] = "p1"
    guard_bad = _private_bundle_guard_summary(bad_bundle)
    checks.append(
        _check(
            "private_guard_rejects_packet_ref_key",
            guard_bad["status"] == "fail",
        )
    )
    # path key -> guard fails.
    bad_bundle2 = dict(bundle_ok) if bundle_ok else {}
    bad_bundle2["path"] = "src/x.rs"
    guard_bad2 = _private_bundle_guard_summary(bad_bundle2)
    checks.append(
        _check(
            "private_guard_rejects_path_key",
            guard_bad2["status"] == "fail",
        )
    )
    # snippet key -> guard fails.
    bad_bundle3 = dict(bundle_ok) if bundle_ok else {}
    bad_bundle3["snippet"] = "code"
    guard_bad3 = _private_bundle_guard_summary(bad_bundle3)
    checks.append(
        _check(
            "private_guard_rejects_snippet_key",
            guard_bad3["status"] == "fail",
        )
    )
    # rater_id key -> guard fails.
    bad_bundle4 = dict(bundle_ok) if bundle_ok else {}
    bad_bundle4["rater_id"] = "alice"
    guard_bad4 = _private_bundle_guard_summary(bad_bundle4)
    checks.append(
        _check(
            "private_guard_rejects_rater_id_key",
            guard_bad4["status"] == "fail",
        )
    )
    # wrong schema -> guard fails.
    bad_bundle5 = dict(bundle_ok) if bundle_ok else {}
    bad_bundle5["schema"] = "wrong_schema"
    guard_bad5 = _private_bundle_guard_summary(bad_bundle5)
    checks.append(
        _check(
            "private_guard_rejects_wrong_schema",
            guard_bad5["status"] == "fail",
        )
    )
    # wrong label_source -> guard fails.
    bad_bundle6 = dict(bundle_ok) if bundle_ok else {}
    bad_bundle6["label_source"] = "proxy"
    guard_bad6 = _private_bundle_guard_summary(bad_bundle6)
    checks.append(
        _check(
            "private_guard_rejects_wrong_label_source",
            guard_bad6["status"] == "fail",
        )
    )
    # synthetic but local_conversion=true -> guard fails.
    bad_bundle7 = dict(bundle_ok) if bundle_ok else {}
    bad_bundle7["local_private_conversion_executed"] = True
    guard_bad7 = _private_bundle_guard_summary(bad_bundle7)
    checks.append(
        _check(
            "private_guard_rejects_synthetic_but_local_conversion_true",
            guard_bad7["status"] == "fail",
        )
    )
    # Clean bundle passes.
    guard_clean = _private_bundle_guard_summary(bundle_ok)
    checks.append(
        _check(
            "private_guard_passes_clean_bundle_repeat",
            guard_clean["status"] == "pass",
        )
    )

    # --- Group 16: Sanitized unknown/private-looking argument errors
    # (SafeArgumentParser). ---
    # Unknown argument with a private-looking value: error message must
    # NOT echo the value (the SafeArgumentParser uses a fixed generic
    # message). We probe by capturing stderr.
    import io
    import contextlib
    parser = build_parser()
    captured_stderr = io.StringIO()
    exit_code: int | None = None
    with contextlib.redirect_stderr(captured_stderr):
        try:
            parser.parse_args(
                [
                    "--unknown-private",
                    "/private/SECRET_CONVERTER_SENTINEL_secret.json",
                ]
            )
        except SystemExit as e:
            exit_code = e.code if isinstance(e.code, int) else 1
    err_text = captured_stderr.getvalue()
    checks.append(
        _check(
            "cli_unknown_argument_rejected_exit_2",
            exit_code == 2,
        )
    )
    checks.append(
        _check(
            "cli_unknown_argument_no_private_value_leak",
            _SECRET_SENTINEL not in err_text
            and "/private" not in err_text
            and ".json" not in err_text,
        )
    )

    # --- Group 17: Artifact generation refuses success if self-test
    # fails. ---
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
            and _build_public_report([], False)["self_test_passed"]
            is False,
        )
    )
    checks.append(
        _check(
            "passed_self_test_carries_success_status",
            _build_public_report([], True)["status"] == TARGET_STATUS
            and _build_public_report([], True)["self_test_passed"]
            is True,
        )
    )

    # --- Group 18: CLI option surface (exactly the required options). ---
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
            "cli_has_allow_private_filled_packets_argument",
            "--allow-private-filled-packets" in cli_opts,
        )
    )
    checks.append(
        _check(
            "cli_has_input_filled_packets_argument",
            "--input-filled-packets" in cli_opts,
        )
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
                "--allow-private-filled-packets",
                "--input-filled-packets",
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


class SafeArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that never echoes unknown/private-looking args.

    A caller may pass a private-looking ``--input-filled-packets
    /tmp/...`` by mistake; default argparse would echo the unknown
    argument and value into stderr. Keep the usage line but replace the
    raw error with a fixed generic message.
    """

    def error(self, message: str) -> NoReturn:  # noqa: D401 - argparse signature
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    """Build the D4e CLI parser."""
    ap = SafeArgumentParser(
        description=(
            "D4e filled-packet -> D4b bundle converter harness "
            "(public harness/no-conversion artifact; no filled packets "
            "read, no conversion run by default)."
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
            "artifact; private converter requires an explicit /tmp path)"
        ),
    )
    ap.add_argument(
        "--allow-private-filled-packets",
        action="store_true",
        help=(
            "opt-in private filled-packet -> D4b bundle converter; "
            "requires --input-filled-packets; output must go to /tmp only "
            "(NOT committed)"
        ),
    )
    ap.add_argument(
        "--input-filled-packets",
        type=Path,
        default=None,
        help=(
            "path to a private filled-packet batch JSON (private converter "
            "only; requires --allow-private-filled-packets); never "
            "serialized into any committed artifact"
        ),
    )
    ap.add_argument(
        "--synthetic-harness-test",
        action="store_true",
        default=False,
        help=(
            "mark a private converter run as a synthetic/in-memory harness "
            "test (requires --allow-private-filled-packets); sets "
            "synthetic_harness_test=true, "
            "synthetic_labels_converted_for_harness_only=true, "
            "local_private_conversion_executed=false, "
            "real_human_labels_converted=false"
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

    # Private converter mode (any private arg present).
    if (
        args.allow_private_filled_packets
        or args.input_filled_packets is not None
        or args.synthetic_harness_test
    ):
        bundle, err = _run_private_converter_mode(
            allow_private=args.allow_private_filled_packets,
            input_path=args.input_filled_packets,
            out_path=args.out,
            synthetic_harness_test=args.synthetic_harness_test,
            loader=_default_loader,
            input_exists=_default_exists,
        )
        if err is not None:
            msg = err if err.startswith("error:") else f"error: {err}"
            print(msg, file=sys.stderr)
            sys.exit(2)
        assert bundle is not None and args.out is not None
        # Compute the private bundle guard summary (fail-closed).
        # The output path itself is the only /tmp path; do NOT echo it
        # into the bundle. The guard checks for forbidden path
        # fragments (using lexical strings, not the resolved output
        # path itself, which is private).
        guard = _private_bundle_guard_summary(bundle)
        bundle_with_guard = dict(bundle)
        bundle_with_guard["private_bundle_guard"] = guard
        if guard.get("status") != "pass":
            print(
                "error: private D4b bundle guard failed; refusing to write",
                file=sys.stderr,
            )
            sys.exit(2)
        _write_json(args.out, bundle)
        # Do NOT print the exact /tmp output path.
        print(_private_success_message(bundle_with_guard))
        return

    # Public default mode (committed harness/no-conversion artifact).
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
