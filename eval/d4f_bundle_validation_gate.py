#!/usr/bin/env python3
"""D4f D4b Bundle Validation / Gate-Check Harness (Public Harness / No-Validation Artifact).

This module implements the **D4b true-label bundle validation /
gate-check harness**. D4f is the last useful harness before real labels
exist: D4e proves filled packets can become a D4b bundle locally; D4f
proves a D4b bundle can be validated and gate-checked locally without
publishing labels, exact counts, or metrics. D4f must NOT claim real
label validation in the committed artifact, must NOT compute calibration
/ agreement / CI metrics, and must NOT unblock D5.

D4f **does not** read a private D4b bundle by default, **does not**
validate a private D4b bundle by default, **does not** persist any
private bundle by default, **does not** emit labels / raw label rows /
exact counts / bucket counts / cell counts / agreement metric values /
CI numeric values in any committed artifact, **does not** accept packet
refs / task IDs / repo IDs / paths / spans / snippets / content hashes /
query / candidate text / rater IDs / model outputs / provider payloads
in any committed artifact, **does not** compute calibration / inter-rater
agreement / confidence intervals, **does not** pass any public-release
gate, **does not** unblock D5, **does not** claim true E/S calibration,
**does not** perform model/LLM labeling, and **does not** change runtime
behavior, retriever, pack, model, backend, default policy, or
EvidenceCore semantics.

Claim boundary (binding):

* This is **eval/diagnostic only**. It is NOT a runtime change, NOT a
  retriever/pack/model/backend/default-policy change, and NOT an
  EvidenceCore semantic change.
* Claim level: ``d4b_bundle_validation_gate_harness_only``.
* Status: ``blocked_no_private_bundle_available_or_no_validation_run``;
  mode ``public_harness_no_private_bundle_no_validation``; phase
  ``D4f``.
* D4b bundle schema source: ``d4b_true_label_bundle_v1``.
* D4e converter source: ``d4e_filled_packet_converter_harness.v1``.
* D4d runbook protocol: ``d4d_human_annotation_runbook.v1``.
* The default committed artifact reads NO private D4b bundle, validates
  NO private bundle, persists NO private bundle, reads/validates NO
  labels, computes NO calibration / agreement / CI, performs NO
  model/LLM labeling, and passes NO public-release gate.

Two strictly separated modes:

* **D4f default (committed)**: public harness / no-validation artifact.
  No private input. All private read/validation/label/counts/metrics/D5
  flags false; the allowed harness/control flags true; diagnostic flags
  true.

* **D4f private validator (opt-in, NOT committed)**: explicit
  ``--allow-private-bundle --input-bundle <path> --out /tmp/...``.
  Reads a local/private D4b bundle (D4e D4b bundle output shape),
  validates the bundle schema, and runs the gate checks (schema,
  label_source, rater_count, agreement availability, CI availability,
  min-N band, k-min band). Writes a private ``/tmp`` report containing
  gate booleans and bands ONLY (no labels, no exact counts, no metrics).
  Never serializes input/output paths or basenames, label rows, packet
  refs, rater IDs, or provider payloads. ``--synthetic-harness-test``
  marks an in-memory/harness run: it sets
  ``synthetic_harness_test=true``,
  ``synthetic_bundle_validated_for_harness_only=true``,
  ``local_private_bundle_validation_run=false``, and
  ``real_human_bundle_validated=false`` even if the bundle is
  human-manual-shaped. A real local private run (no synthetic flag,
  bundle is not synthetic-marked, label_source is human manual, D4e
  real-conversion flags are true, schema passes, /tmp guard passes) may
  set ``local_private_bundle_validation_run=true`` and
  ``real_human_bundle_validated=true`` locally only (never committed).
  Docs mark the real-mode flag-path test over a synthetic fixture as a
  flag-path test, NOT evidence that real labels exist.

Run::

    python3 -m py_compile eval/d4f_bundle_validation_gate.py
    python3 eval/d4f_bundle_validation_gate.py --self-test
    python3 eval/d4f_bundle_validation_gate.py \
        --out artifacts/d4f_bundle_validation_gate/\
d4f_bundle_validation_gate_report.json
    # D4f private validator (NOT committed; /tmp only):
    python3 eval/d4f_bundle_validation_gate.py \
        --allow-private-bundle \
        --input-bundle /local/private/d4b_bundle.json \
        --out /tmp/d4f_bundle_validation_report.json
    # D4f synthetic harness self-test (NOT committed; /tmp only):
    python3 eval/d4f_bundle_validation_gate.py \
        --allow-private-bundle --synthetic-harness-test \
        --input-bundle /tmp/synthetic_d4b_bundle.json \
        --out /tmp/d4f_synthetic_validation.json
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

SCHEMA_VERSION = "d4f_bundle_validation_gate_harness.v1"
GENERATED_BY = "eval/d4f_bundle_validation_gate.py"
CLAIM_LEVEL = "d4b_bundle_validation_gate_harness_only"
TARGET_STATUS = (
    "blocked_no_private_bundle_available_or_no_validation_run"
)
MODE_PUBLIC = "public_harness_no_private_bundle_no_validation"
MODE_PRIVATE = "private_bundle_validation_gate_tmp_only"
PHASE = "D4f"
STATUS_PRIVATE_OK = "private_d4b_bundle_validated_locally"

DEFAULT_OUT = Path(
    "artifacts/d4f_bundle_validation_gate/"
    "d4f_bundle_validation_gate_report.json"
)

# Referenced schema/protocol versions (source/target contracts only; D4f
# default mode does not read D4b bundles, run any validator, or run any
# gate checks).
D4B_BUNDLE_SCHEMA_SOURCE = "d4b_true_label_bundle_v1"
D4E_CONVERTER_SOURCE = "d4e_filled_packet_converter_harness.v1"
D4D_RUNBOOK_PROTOCOL = "d4d_human_annotation_runbook.v1"

# Private D4f gate report schema (output of a private local-only run).
PRIVATE_REPORT_SCHEMA = (
    "d4f_bundle_validation_gate_private_report.v1"
)

# Private D4b bundle label source (input shape; same as D4e output).
HUMAN_MANUAL_LABEL_SOURCE = "human_manual_true_e_s"

# Fixed sanitized error for any private D4b bundle load/parse/schema/
# privacy failure. Never includes the input path, basename, raw JSON, or
# label text.
PRIVATE_LOAD_ERROR_MESSAGE = (
    "error: failed to load private bundle "
    "(schema/privacy/parse error; details suppressed)"
)

# Fixed label slots in each label object of a D4b bundle (input shape;
# same as D4e output).
LABEL_SLOTS: tuple[str, ...] = (
    "e_score",
    "s_score",
    "bucket",
    "citation_valid",
    "rater_pair_present",
    "adjudicated",
)

# D3 dual-rubric E-score / S-score levels (input label values; allowed
# inside the D4b bundle labels list and as contract values only).
E_SCORE_LEVELS: tuple[str, ...] = ("E0", "E1", "E2")
S_SCORE_LEVELS: tuple[str, ...] = ("S0", "S1", "S2")

# Bucket names referenced by the D3 rubric (input label values; allowed
# inside the D4b bundle labels list and as contract values only).
BUCKET_NAMES: tuple[str, ...] = (
    "primary_evidence",
    "dependency_support",
    "weak_candidates",
    "abstained",
)

# D4d runbook attestation field names (allowed as contract container
# values only; referenced by the gate-check contract).
ATTESTATION_FIELDS: tuple[str, ...] = (
    "protocol",
    "two_independent_human_raters",
    "independent_before_adjudication",
    "no_llm_or_model_labels",
    "no_proxy_labels_as_true_labels",
    "local_only_storage",
)

# Gate threshold values (referenced by the public gate-check contract;
# D4f computes the bands internally but never emits exact N or cell
# counts).
GATE_MIN_TOTAL_LABELS = 50
GATE_K_MIN_CELL = 5
GATE_MIN_RATER_COUNT = 2

# Gate band values (the only values allowed for min-N / k-min bands in
# the private report).
GATE_BAND_VALUES: tuple[str, ...] = ("met", "not_met", "not_evaluated")

# ---------------------------------------------------------------------------
# Default artifact false flags (all MUST be false in the committed public
# artifact). D4f reads no private D4b bundle, validates no bundle, reads
# no labels, emits no counts/metrics, computes no calibration, performs
# no model/LLM labeling, and passes no release gate.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "private_bundle_read": False,
    "private_bundle_validated": False,
    "private_bundle_persisted": False,
    "bundle_validation_run": False,
    "labels_read": False,
    "labels_persisted": False,
    "raw_label_rows_emitted": False,
    "exact_private_counts_emitted": False,
    "bucket_counts_emitted": False,
    "cell_counts_emitted": False,
    "calibration_metrics_computed": False,
    "inter_rater_agreement_computed": False,
    "inter_rater_agreement_measured": False,
    "agreement_metric_values_emitted": False,
    "confidence_intervals_computed": False,
    "confidence_interval_values_emitted": False,
    "public_release_gate_passed": False,
    "d5_unblocked": False,
    "true_e_s_calibration_claimed": False,
    "private_input_path_emitted": False,
    "private_output_path_emitted": False,
    "task_ids_emitted": False,
    "repo_ids_emitted": False,
    "paths_or_spans_emitted": False,
    "snippets_emitted": False,
    "content_sha_emitted": False,
    "query_or_candidate_text_emitted": False,
    "rater_ids_emitted": False,
    "model_or_llm_labeling_performed": False,
    "model_assisted_labels_allowed": False,
}

# Allowed positive harness/control flags (true only for the validated
# harness/controls; each is proven by a self-test). Exactly these; no
# read/validation/label/counts/metrics/D5 claim flags are true in the
# default committed artifact.
HARNESS_CONTROL_FLAGS: dict[str, bool] = {
    "bundle_validation_harness_available": True,
    "private_cli_guard_validated": True,
    "tmp_output_resolved_guard_validated": True,
    "sanitized_error_guard_validated": True,
    "d4b_bundle_schema_contract_defined": True,
    "gate_check_contract_defined": True,
    "min_n_gate_referenced": True,
    "k_min_gate_referenced": True,
    "agreement_availability_gate_referenced": True,
    "ci_availability_gate_referenced": True,
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
# string allowlist). Contract containers are exact string allowlists
# (no over-broad container exemption); sensitive field-name tokens are
# allowed as VALUES only inside contract containers and nowhere else.
# ---------------------------------------------------------------------------

# Top-level keys whose subtrees are explicit contract field-name /
# enum containers. String values inside these containers must be in
# APPROVED_CONTRACT_STRINGS (exact allowlist).
CONTRACT_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "d4b_bundle_schema_contract",
        "gate_check_contract",
        "d4d_runbook_contract",
        "d4e_converter_contract",
    }
)

# Sensitive field-name tokens that may appear as list-element VALUES
# inside contract containers (e.g. label_object_allowed_keys,
# required_attestation_fields) for the label-slot and attestation
# subsets only, but are forbidden as dict KEYS anywhere and forbidden
# as VALUES outside contract containers. Sensitive source fields
# (content_sha, query_text, packet_ref, etc.) are NOT approved contract
# strings, so they are rejected even inside contract containers.
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
        # sensitive source fields (never in public artifact)
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

# Allowed keys in a private D4b bundle input (D4e output shape).
ALLOWED_BUNDLE_KEYS: frozenset[str] = frozenset(
    {
        "schema",
        "label_source",
        "rater_count",
        "agreement_available",
        "confidence_intervals_available",
        "synthetic_harness_test",
        "local_private_conversion_executed",
        "real_human_labels_converted",
        "labels",
    }
)

# Allowed keys in each label object of a private D4b bundle input.
ALLOWED_LABEL_KEYS: frozenset[str] = frozenset(LABEL_SLOTS)

# Exact string values allowed inside explicit public contract containers.
# This intentionally does NOT allow arbitrary short strings inside a
# contract container; only approved schema/protocol identifiers, E/S
# levels, bucket names, label-slot field-name tokens, attestation
# field-name tokens, the human-manual label source, the D4e converter
# source identifier, the approved D4b bundle field-name tokens, the
# private report schema identifier, the gate band values, and the
# approved category strings (e.g. tmp-only-local-private location).
APPROVED_CONTRACT_STRINGS: frozenset[str] = frozenset(
    {
        D4B_BUNDLE_SCHEMA_SOURCE,
        D4E_CONVERTER_SOURCE,
        D4D_RUNBOOK_PROTOCOL,
        HUMAN_MANUAL_LABEL_SOURCE,
        PRIVATE_REPORT_SCHEMA,
        "tmp_only_local_private",
        *E_SCORE_LEVELS,
        *S_SCORE_LEVELS,
        *BUCKET_NAMES,
        *LABEL_SLOTS,
        *ATTESTATION_FIELDS,
        *ALLOWED_BUNDLE_KEYS,
        *GATE_BAND_VALUES,
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
        # D4c/D4d source-context / attestation keys (D4f public artifact
        # exposes only category-only contracts; the raw attestation dict
        # and packets list must never appear as keys).
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
        "d4b_bundle_schema_source",
        "d4e_converter_source",
        "d4d_runbook_protocol",
        "section",
        "check",
        "category",
        "output_location",
    }
)

# Value patterns that indicate leaked row-level / candidate / packet /
# annotation data. D4f rejects ALL URLs (no URL allowlist) per the
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


# Keys that must NEVER appear in a private D4b bundle INPUT (provider
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
        # packet-specific identifiers (NO packet refs in D4b bundle)
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
        # rows / records / packets (NO packets list in D4b bundle)
        "raw_rows", "rows", "records", "tasks", "row_values", "packets",
        # D4c/D4d source-context / attestation keys (NO source context or
        # attestation in D4b bundle)
        "source_packet_schema", "d4d_runbook_attestation",
        "source_records",
        # patches / tests
        "patch", "test_patch", "tests",
        # secrets
        "api_key", "api_token", "api_secret", "base_url", "provider_key",
        "authorization",
        # raw agreement / CI numeric values (D4b bundle must not carry
        # raw metric values; only availability flags)
        "agreement_metric", "agreement_value", "agreement_score",
        "kappa", "fleiss_kappa", "cohen_kappa", "agreement",
        "confidence_interval", "ci_value", "ci_lower", "ci_upper",
        "ci_low", "ci_high",
    }
)

# Allowed keys in a private D4f gate report output (exact allowlist).
ALLOWED_PRIVATE_REPORT_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "private_validation_report",
        "public_artifact",
        "do_not_commit",
        "synthetic_harness_test",
        "synthetic_bundle_validated_for_harness_only",
        "local_private_bundle_validation_run",
        "real_human_bundle_validated",
        "schema_gate_passed",
        "label_source_gate_passed",
        "rater_count_gate_passed",
        "agreement_availability_gate_passed",
        "ci_availability_gate_passed",
        "min_total_labels_gate_band",
        "k_min_gate_band",
        "small_cell_suppression_required",
        "exact_private_counts_emitted",
        "bucket_counts_emitted",
        "cell_counts_emitted",
        "agreement_metric_values_emitted",
        "confidence_interval_values_emitted",
        "public_release_gate_passed",
        "d5_unblocked",
    }
)

# Allowed band values for min-N / k-min gates.
ALLOWED_BAND_VALUES: frozenset[str] = frozenset(GATE_BAND_VALUES)

# Keys that must NEVER appear in a private D4f gate report (labels list,
# raw label rows, paths, snippets, content_sha, query/candidate text,
# rater IDs, provider payloads, API secrets, model outputs, raw
# agreement/CI numeric values, per-row hashes, task/repo IDs, packet
# refs, input/output paths/basenames).
PRIVATE_REPORT_FORBIDDEN_KEYS: frozenset[str] = frozenset(
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
        # labels / qrels / annotations / raters (NO labels list in the
        # private report; only gate booleans/bands)
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
        # source-context / attestation keys
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
        # exact counts (must NEVER appear in private report; only bands)
        "total_labels", "label_count", "labels_count",
        "bucket_count", "bucket_counts", "cell_count", "cell_counts",
        "n", "n_total", "count", "counts",
        # input/output paths / basenames
        "input_path", "output_path", "input_bundle", "output_bundle",
        "input_basename", "output_basename",
    }
)


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


def _is_str(value: Any) -> bool:
    return isinstance(value, str)


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _find_secret_like_values(obj: Any) -> list[str]:
    """Return any string values that look like provider secrets/API keys."""
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


# ---------------------------------------------------------------------------
# Public contracts (category-only; field-name tokens allowed only inside
# contract containers by the public scanner)
# ---------------------------------------------------------------------------


def _build_d4b_bundle_schema_contract() -> dict[str, Any]:
    """D4b bundle schema contract (input shape; validator not run by default)."""
    return {
        "schema": D4B_BUNDLE_SCHEMA_SOURCE,
        "required_label_source": HUMAN_MANUAL_LABEL_SOURCE,
        "bundle_allowed_keys": sorted(ALLOWED_BUNDLE_KEYS),
        "label_object_allowed_keys": sorted(ALLOWED_LABEL_KEYS),
        "e_score_levels": list(E_SCORE_LEVELS),
        "s_score_levels": list(S_SCORE_LEVELS),
        "bucket_names": list(BUCKET_NAMES),
        "rejects_unknown_keys": True,
        "rejects_packet_refs_paths_snippets_raters": True,
    }


def _build_gate_check_contract() -> dict[str, Any]:
    """Gate-check contract (referenced gates; thresholds shown, no counts)."""
    return {
        "min_total_labels_gate_referenced": True,
        "k_min_gate_referenced": True,
        "agreement_availability_gate_referenced": True,
        "ci_availability_gate_referenced": True,
        "min_rater_count_gate_referenced": True,
        "min_rater_count": GATE_MIN_RATER_COUNT,
        "min_total_labels_gate": GATE_MIN_TOTAL_LABELS,
        "k_min_cell_gate": GATE_K_MIN_CELL,
        "gate_band_values": list(GATE_BAND_VALUES),
        "small_cell_suppression_required": True,
        "exact_counts_never_emitted": True,
        "metrics_never_computed": True,
        "validator_not_run_by_default": True,
    }


def _build_d4d_runbook_contract() -> dict[str, Any]:
    """D4d runbook / attestation contract (referenced protocol)."""
    return {
        "protocol": D4D_RUNBOOK_PROTOCOL,
        "required_attestation_fields": list(ATTESTATION_FIELDS),
        "attestation_must_be_all_true": True,
        "no_llm_or_model_labels_required": True,
        "no_proxy_labels_as_true_labels_required": True,
        "local_only_storage_required": True,
    }


def _build_d4e_converter_contract() -> dict[str, Any]:
    """D4e converter source contract (referenced source)."""
    return {
        "converter_source": D4E_CONVERTER_SOURCE,
        "target_bundle_schema": D4B_BUNDLE_SCHEMA_SOURCE,
        "private_only": True,
        "output_location": "tmp_only_local_private",
        "committed": False,
    }


def _build_validation_harness_info() -> dict[str, Any]:
    """Private validator harness availability info."""
    return {
        "available": True,
        "opt_in_required": True,
        "output_location": "tmp_only_local_private",
        "committed": False,
        "validates_d4b_bundle_schema": True,
        "runs_gate_checks_only": True,
        "rejects_packet_refs_paths_snippets_raters": True,
        "rejects_model_proxy_llm_labels": True,
        "claims_calibration": False,
        "computes_agreement_or_ci": False,
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
# Private D4b bundle input contract (D4e D4b bundle output shape).
# Accepts the D4e D4b bundle output; rejects packet refs, source context,
# rater IDs, provider payloads, API secrets, model outputs, raw label
# rows, raw agreement/CI values, per-row hashes, and unknown keys.
# ---------------------------------------------------------------------------


class _PrivateBundleLoadError(Exception):
    """Raised when a private D4b bundle fails schema/privacy/parse checks.

    The CLI never surfaces this exception's message; it always emits the
    fixed sanitized ``PRIVATE_LOAD_ERROR_MESSAGE`` instead.
    """


def _validate_private_d4b_bundle(bundle: Any) -> list[dict[str, Any]]:
    """Private D4b bundle INPUT guard (fail-closed).

    Validates the D4e D4b bundle output shape:

    * bundle is a dict;
    * schema exactly ``d4b_true_label_bundle_v1``;
    * label_source exactly ``human_manual_true_e_s``;
    * bundle keys exactly the allowlist (no packet refs, paths, snippets,
      content_sha, query_text, candidate_text, rater IDs, provider
      payloads, API secrets, model outputs, raw label rows, packets list,
      source_packet_schema, d4d_runbook_attestation);
    * label object keys exactly the six label slots;
    * E/S values within the D3 enum; bucket within the D3 enum;
    * citation_valid / rater_pair_present / adjudicated as bools;
    * rater_count is int >= GATE_MIN_RATER_COUNT;
    * agreement_available / confidence_intervals_available as bools;
    * synthetic_harness_test / local_private_conversion_executed /
      real_human_labels_converted as bools with truthful combinations
      (synthetic => no real conversion; real => not synthetic-marked);
    * no forbidden source-context / packet / rater / secret / model keys
      anywhere in the bundle;
    * no provider secrets / API keys / sentinel in any string value;
    * no path-like or hex-digest values.

    Returns a list of violation dicts (never the leaked value). The
    loader rejects unknown keys rather than supporting and stripping
    them.
    """
    if not isinstance(bundle, dict):
        return [{"category": "bundle_not_dict"}]
    violations: list[dict[str, Any]] = []
    if bundle.get("schema") != D4B_BUNDLE_SCHEMA_SOURCE:
        violations.append({"category": "wrong_bundle_schema"})
    if bundle.get("label_source") != HUMAN_MANUAL_LABEL_SOURCE:
        violations.append({"category": "wrong_label_source"})
    for key in bundle.keys():
        if key not in ALLOWED_BUNDLE_KEYS:
            violations.append(
                {"category": "forbidden_bundle_key", "key": "suppressed"}
            )
    # Truthful synthetic / real flags (D4e output shape).
    sht = bundle.get("synthetic_harness_test")
    lpc = bundle.get("local_private_conversion_executed")
    rhc = bundle.get("real_human_labels_converted")
    if not isinstance(sht, bool):
        violations.append({"category": "synthetic_harness_test_not_bool"})
    if not isinstance(lpc, bool):
        violations.append(
            {"category": "local_private_conversion_not_bool"}
        )
    if not isinstance(rhc, bool):
        violations.append(
            {"category": "real_human_labels_converted_not_bool"}
        )
    if sht is True:
        if lpc is not False:
            violations.append(
                {"category": "synthetic_but_local_conversion_true"}
            )
        if rhc is not False:
            violations.append(
                {"category": "synthetic_but_real_conversion_true"}
            )
    else:
        # Real-mode: not synthetic-marked. If
        # local_private_conversion_executed=true then
        # real_human_labels_converted must also be true.
        if lpc is True and rhc is not True:
            violations.append(
                {"category": "local_conversion_but_real_false"}
            )
    # rater_count >= GATE_MIN_RATER_COUNT
    rater_count = bundle.get("rater_count")
    if (
        not isinstance(rater_count, int)
        or isinstance(rater_count, bool)
        or rater_count < GATE_MIN_RATER_COUNT
    ):
        violations.append({"category": "rater_count_below_min"})
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
                    {"category": "label_not_dict", "idx": "suppressed"}
                )
                continue
            if set(entry.keys()) != ALLOWED_LABEL_KEYS:
                violations.append(
                    {"category": "label_wrong_keys", "idx": "suppressed"}
                )
            else:
                if entry.get("e_score") not in E_SCORE_LEVELS:
                    violations.append(
                        {"category": "invalid_e_score", "idx": "suppressed"}
                    )
                if entry.get("s_score") not in S_SCORE_LEVELS:
                    violations.append(
                        {"category": "invalid_s_score", "idx": "suppressed"}
                    )
                if entry.get("bucket") not in BUCKET_NAMES:
                    violations.append(
                        {"category": "invalid_bucket", "idx": "suppressed"}
                    )
                for flag in (
                    "citation_valid",
                    "rater_pair_present",
                    "adjudicated",
                ):
                    if not isinstance(entry.get(flag), bool):
                        violations.append(
                            {"category": f"non_bool_{flag}", "idx": "suppressed"}
                        )
    # Forbidden source-context / packet / rater / secret / model keys
    # anywhere in the bundle.
    for bad in PRIVATE_BUNDLE_FORBIDDEN_KEYS:
        if _has_dict_key_anywhere(bundle, bad):
            violations.append(
                {"category": "private_bundle_forbidden_key", "key": "suppressed"}
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
    """Run the private D4b bundle INPUT guard and return a sanitized summary."""
    violations = _validate_private_d4b_bundle(bundle)
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
# Gate-check logic (compute internally; emit only bands, never exact
# counts or metric values)
# ---------------------------------------------------------------------------


def _evaluate_min_total_labels_gate(labels_count: int | None) -> str:
    """Compute the min-N gate band.

    Returns ``met`` / ``not_met`` (or ``not_evaluated`` when the count
    is unknown). Never emits the exact count; the band is the only
    output.
    """
    if labels_count is None:
        return "not_evaluated"
    if labels_count >= GATE_MIN_TOTAL_LABELS:
        return "met"
    return "not_met"


def _evaluate_k_min_gate(labels: list[dict[str, Any]] | None) -> str:
    """Compute the k-min gate band by counting per-bucket internally.

    Returns ``met`` (all per-bucket counts are 0 or >= k_min),
    ``not_met`` (at least one bucket has 1 <= count < k_min), or
    ``not_evaluated`` (labels not available). Never emits the exact
    per-bucket counts; the band is the only output.
    """
    if labels is None:
        return "not_evaluated"
    bucket_counts: dict[str, int] = {b: 0 for b in BUCKET_NAMES}
    for entry in labels:
        if not isinstance(entry, dict):
            continue
        bucket = entry.get("bucket")
        if bucket in bucket_counts:
            bucket_counts[bucket] += 1
    for count in bucket_counts.values():
        if 0 < count < GATE_K_MIN_CELL:
            return "not_met"
    return "met"


def _run_gate_checks(bundle: Any) -> dict[str, Any]:
    """Run all gate checks on a D4b bundle.

    Returns a dict with gate booleans and bands. The min-N and k-min
    gates are computed internally but only their bands (``met`` /
    ``not_met`` / ``not_evaluated``) are emitted; the exact N or cell
    counts are NEVER emitted.
    """
    schema_violations = _validate_private_d4b_bundle(bundle)
    schema_gate_passed = not schema_violations
    if not schema_gate_passed:
        return {
            "schema_gate_passed": False,
            "label_source_gate_passed": False,
            "rater_count_gate_passed": False,
            "agreement_availability_gate_passed": False,
            "ci_availability_gate_passed": False,
            "min_total_labels_gate_band": "not_evaluated",
            "k_min_gate_band": "not_evaluated",
        }
    bundle_dict = bundle  # type: dict[str, Any]
    label_source_gate_passed = (
        bundle_dict.get("label_source") == HUMAN_MANUAL_LABEL_SOURCE
    )
    rater_count = bundle_dict.get("rater_count")
    rater_count_gate_passed = (
        isinstance(rater_count, int)
        and not isinstance(rater_count, bool)
        and rater_count >= GATE_MIN_RATER_COUNT
    )
    agreement_availability_gate_passed = (
        bundle_dict.get("agreement_available") is True
    )
    ci_availability_gate_passed = (
        bundle_dict.get("confidence_intervals_available") is True
    )
    labels = bundle_dict.get("labels")
    labels_list = labels if isinstance(labels, list) else None
    labels_count = (
        len(labels_list) if labels_list is not None else None
    )
    min_total_labels_gate_band = _evaluate_min_total_labels_gate(
        labels_count
    )
    k_min_gate_band = _evaluate_k_min_gate(labels_list)
    return {
        "schema_gate_passed": True,
        "label_source_gate_passed": label_source_gate_passed,
        "rater_count_gate_passed": rater_count_gate_passed,
        "agreement_availability_gate_passed": agreement_availability_gate_passed,
        "ci_availability_gate_passed": ci_availability_gate_passed,
        "min_total_labels_gate_band": min_total_labels_gate_band,
        "k_min_gate_band": k_min_gate_band,
    }


# ---------------------------------------------------------------------------
# Private D4f gate report OUTPUT guard (DIFFERENT from the public
# scanner AND from the private bundle INPUT guard). Allows gate
# booleans/bands and schema/category names; rejects labels list/label
# rows, exact counts, agreement/CI numeric values, task/repo/path/
# snippet/hash/query/rater fields, input/output paths/basenames; verifies
# synthetic/real flags truthful.
# ---------------------------------------------------------------------------


def _validate_private_report(report: Any) -> list[dict[str, Any]]:
    """Private D4f gate report OUTPUT guard (fail-closed).

    Different from the public scanner AND from the private bundle INPUT
    guard: this guard allows gate booleans/bands and schema/category
    names; it rejects labels list/label rows, exact counts, agreement/
    CI numeric values, task/repo/path/snippet/hash/query/rater fields,
    and input/output paths/basenames. It verifies synthetic/real flags
    are truthful.
    """
    if not isinstance(report, dict):
        return [{"category": "report_not_dict"}]
    violations: list[dict[str, Any]] = []
    for key in report.keys():
        if key not in ALLOWED_PRIVATE_REPORT_KEYS:
            violations.append(
                {"category": "forbidden_report_key", "key": "suppressed"}
            )
    # Structural identity flags.
    if report.get("schema_version") != PRIVATE_REPORT_SCHEMA:
        violations.append({"category": "wrong_schema_version"})
    if report.get("private_validation_report") is not True:
        violations.append({"category": "private_validation_report_not_true"})
    if report.get("public_artifact") is not False:
        violations.append({"category": "public_artifact_not_false"})
    if report.get("do_not_commit") is not True:
        violations.append({"category": "do_not_commit_not_true"})
    if report.get("small_cell_suppression_required") is not True:
        violations.append(
            {"category": "small_cell_suppression_required_not_true"}
        )
    # No-release / no-D5 flags must be false.
    if report.get("public_release_gate_passed") is not False:
        violations.append(
            {"category": "public_release_gate_passed_not_false"}
        )
    if report.get("d5_unblocked") is not False:
        violations.append({"category": "d5_unblocked_not_false"})
    # No-emitted flags must be false.
    for flag in (
        "exact_private_counts_emitted",
        "bucket_counts_emitted",
        "cell_counts_emitted",
        "agreement_metric_values_emitted",
        "confidence_interval_values_emitted",
    ):
        if report.get(flag) is not False:
            violations.append({"category": f"{flag}_not_false"})
    # Synthetic / real flag truthfulness.
    sht = report.get("synthetic_harness_test")
    slc = report.get("synthetic_bundle_validated_for_harness_only")
    lpc = report.get("local_private_bundle_validation_run")
    rhc = report.get("real_human_bundle_validated")
    if not isinstance(sht, bool):
        violations.append({"category": "synthetic_harness_test_not_bool"})
    if not isinstance(slc, bool):
        violations.append(
            {"category": "synthetic_bundle_validated_not_bool"}
        )
    if not isinstance(lpc, bool):
        violations.append(
            {"category": "local_private_validation_not_bool"}
        )
    if not isinstance(rhc, bool):
        violations.append(
            {"category": "real_human_bundle_validated_not_bool"}
        )
    if sht is True:
        if slc is not True:
            violations.append(
                {"category": "synthetic_but_not_marked_harness_only"}
            )
        if lpc is not False:
            violations.append(
                {"category": "synthetic_but_local_validation_true"}
            )
        if rhc is not False:
            violations.append(
                {"category": "synthetic_but_real_validation_true"}
            )
    else:
        # Real-mode flag path: not synthetic-marked. If
        # local_private_bundle_validation_run=true then
        # real_human_bundle_validated must also be true and
        # synthetic_bundle_validated_for_harness_only must be false.
        if lpc is True:
            if rhc is not True:
                violations.append(
                    {"category": "local_validation_but_real_false"}
                )
            if slc is not False:
                violations.append(
                    {"category": "local_validation_but_synthetic_marked"}
                )
    # Gate booleans.
    for gate in (
        "schema_gate_passed",
        "label_source_gate_passed",
        "rater_count_gate_passed",
        "agreement_availability_gate_passed",
        "ci_availability_gate_passed",
    ):
        if not isinstance(report.get(gate), bool):
            violations.append({"category": f"{gate}_not_bool"})
    # Band values.
    for band in ("min_total_labels_gate_band", "k_min_gate_band"):
        val = report.get(band)
        if val not in ALLOWED_BAND_VALUES:
            violations.append({"category": f"{band}_invalid_value"})
    # Forbidden keys anywhere (labels, paths, snippets, etc.).
    for bad in PRIVATE_REPORT_FORBIDDEN_KEYS:
        if _has_dict_key_anywhere(report, bad):
            violations.append(
                {"category": "private_report_forbidden_key", "key": "suppressed"}
            )
    # No secret-like / path-like / hex-digest values.
    if _find_secret_like_values(report):
        violations.append(
            {"category": "secret_like_value", "count": "suppressed"}
        )
    if _find_path_like_values(report):
        violations.append(
            {"category": "path_or_digest_value", "count": "suppressed"}
        )
    return violations


def _private_report_guard_summary(
    report: Any,
    *,
    forbidden_path_fragments: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Run the private D4f gate report guard and return a sanitized summary."""
    violations = _validate_private_report(report)
    if forbidden_path_fragments:
        blob = json.dumps(report, sort_keys=True)
        for frag in forbidden_path_fragments:
            if frag and frag in blob:
                violations.append(
                    {
                        "category": "path_or_basename_in_report",
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
# Real-mode flag-path decision logic
# ---------------------------------------------------------------------------


def _decide_real_validation_claim(
    *,
    synthetic_harness_test_cli: bool,
    bundle_synthetic_flag: bool,
    label_source_human: bool,
    d4e_real_conversion: bool,
    schema_valid: bool,
    tmp_guard_passed: bool,
) -> bool:
    """Decide whether ``local_private_bundle_validation_run`` may be true.

    True only for a real local private run: no synthetic harness flag
    (CLI), the bundle is not synthetic-marked, the label_source is
    human manual, the D4e real-conversion flags are true (i.e. the
    input bundle claims real human labels were converted by D4e), the
    schema passes, and the resolved /tmp guard passes. Synthetic /
    in-memory harness runs are always false even if the bundle is
    human-manual-shaped. This function expresses the logic only; it
    does not itself claim execution in any committed artifact.
    """
    if synthetic_harness_test_cli:
        return False
    if bundle_synthetic_flag:
        return False
    if not label_source_human:
        return False
    if not d4e_real_conversion:
        return False
    if not schema_valid:
        return False
    if not tmp_guard_passed:
        return False
    return True


def build_private_report(
    *,
    bundle: dict[str, Any],
    synthetic_harness_test: bool,
    tmp_guard_passed: bool,
) -> dict[str, Any]:
    """Build a private D4f gate report from a validated D4b bundle.

    The report contains gate booleans and bands ONLY: no labels list,
    no exact counts, no agreement/CI numeric values, no input/output
    paths or basenames.

    For ``--synthetic-harness-test``:
    - ``synthetic_harness_test=true``
    - ``synthetic_bundle_validated_for_harness_only=true``
    - ``local_private_bundle_validation_run=false``
    - ``real_human_bundle_validated=false``

    For a real local private run (no synthetic CLI flag, bundle not
    synthetic-marked, label_source is human manual, D4e real-conversion
    flags are true, schema passes, /tmp guard passes):
    - ``synthetic_harness_test=false``
    - ``synthetic_bundle_validated_for_harness_only=false``
    - ``local_private_bundle_validation_run=true``
    - ``real_human_bundle_validated=true``

    Even if all gates pass locally, the report always keeps
    ``public_release_gate_passed=false`` and ``d5_unblocked=false``.
    """
    schema_violations = _validate_private_d4b_bundle(bundle)
    schema_valid = not schema_violations
    gates = _run_gate_checks(bundle)
    bundle_synthetic_flag = bool(bundle.get("synthetic_harness_test"))
    label_source_human = (
        bundle.get("label_source") == HUMAN_MANUAL_LABEL_SOURCE
    )
    d4e_real_conversion = (
        bundle.get("local_private_conversion_executed") is True
        and bundle.get("real_human_labels_converted") is True
    )
    real_validation = _decide_real_validation_claim(
        synthetic_harness_test_cli=synthetic_harness_test,
        bundle_synthetic_flag=bundle_synthetic_flag,
        label_source_human=label_source_human,
        d4e_real_conversion=d4e_real_conversion,
        schema_valid=schema_valid,
        tmp_guard_passed=tmp_guard_passed,
    )
    return {
        "schema_version": PRIVATE_REPORT_SCHEMA,
        "private_validation_report": True,
        "public_artifact": False,
        "do_not_commit": True,
        "synthetic_harness_test": bool(synthetic_harness_test),
        "synthetic_bundle_validated_for_harness_only": bool(
            synthetic_harness_test
        ),
        "local_private_bundle_validation_run": bool(real_validation),
        "real_human_bundle_validated": bool(real_validation),
        "schema_gate_passed": bool(gates["schema_gate_passed"]),
        "label_source_gate_passed": bool(
            gates["label_source_gate_passed"]
        ),
        "rater_count_gate_passed": bool(
            gates["rater_count_gate_passed"]
        ),
        "agreement_availability_gate_passed": bool(
            gates["agreement_availability_gate_passed"]
        ),
        "ci_availability_gate_passed": bool(
            gates["ci_availability_gate_passed"]
        ),
        "min_total_labels_gate_band": gates["min_total_labels_gate_band"],
        "k_min_gate_band": gates["k_min_gate_band"],
        "small_cell_suppression_required": True,
        "exact_private_counts_emitted": False,
        "bucket_counts_emitted": False,
        "cell_counts_emitted": False,
        "agreement_metric_values_emitted": False,
        "confidence_interval_values_emitted": False,
        "public_release_gate_passed": False,
        "d5_unblocked": False,
    }


# ---------------------------------------------------------------------------
# Default file-based loader / existence probe (injectable for self-test)
# ---------------------------------------------------------------------------


def _default_loader(input_path: Path) -> dict[str, Any]:
    """Read, parse, and validate a private D4b bundle file.

    Raises ``_PrivateBundleLoadError`` on any I/O, parse, or
    schema failure. The CLI converts this into the fixed sanitized
    error.
    """
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        raise _PrivateBundleLoadError()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        raise _PrivateBundleLoadError()
    if _validate_private_d4b_bundle(data):
        raise _PrivateBundleLoadError()
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
    """Validate CLI argument combinations for public vs private validator.

    Pure: performs NO filesystem I/O (only lexical path checks). Returns
    an error message string if invalid, or ``None`` if valid. The guards
    below are evaluated BEFORE the input is opened or stat'd, proving
    validate-before-read.

    * ``--input-bundle`` without ``--allow-private-bundle`` -> error.
    * ``--allow-private-bundle`` without ``--input-bundle`` -> error.
    * ``--allow-private-bundle`` without explicit ``--out`` -> error.
    * ``--allow-private-bundle`` with the committed artifact path as
      ``--out`` -> error (before read).
    * ``--allow-private-bundle`` with a non-``/tmp`` ``--out`` -> error
      (before read).
    * ``--synthetic-harness-test`` without ``--allow-private-bundle`` ->
      error.
    * ``--allow-private-bundle --input-bundle <path> --out /tmp/...`` ->
      valid.
    """
    if input_path is not None and not allow_private:
        return (
            "--input-bundle requires --allow-private-bundle; refusing "
            "to read private bundle without explicit opt-in"
        )
    if allow_private and input_path is None:
        return (
            "--allow-private-bundle requires --input-bundle; no private "
            "input path provided"
        )
    if synthetic_harness_test and not allow_private:
        return (
            "--synthetic-harness-test requires --allow-private-bundle; "
            "refusing to run a harness test without explicit opt-in"
        )
    if allow_private:
        if out_path is None:
            return (
                "--allow-private-bundle requires explicit --out under "
                "/tmp; refusing to use the committed artifact path"
            )
        if _is_committed_out(out_path):
            return (
                "--allow-private-bundle requires --out under /tmp; "
                "refusing to write to the committed artifact path"
            )
        if not _is_under_tmp(out_path):
            return (
                "--allow-private-bundle requires --out under /tmp; "
                "refusing to write private-mode output elsewhere"
            )
    return None


# ---------------------------------------------------------------------------
# Private validator runner (validate-before-read; resolved /tmp guard;
# sanitized errors)
# ---------------------------------------------------------------------------


def _run_private_validator_mode(
    *,
    allow_private: bool,
    input_path: Path | None,
    out_path: Path | None,
    synthetic_harness_test: bool,
    loader: Any,
    input_exists: Any,
    tmp_guard: Any = _validate_resolved_tmp_guard,
) -> tuple[dict[str, Any] | None, str | None]:
    """Run the private D4b bundle validator.

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
        return None, err
    assert input_path is not None and out_path is not None
    # Lexical validation passed: validate the resolved /tmp output guard
    # (filesystem on the OUTPUT path only) before touching the input.
    tmp_err = tmp_guard(out_path)
    tmp_guard_passed = tmp_err is None
    if not tmp_guard_passed:
        return None, tmp_err
    # Output guard passed: the input may now be touched.
    if not input_exists(input_path):
        return None, PRIVATE_LOAD_ERROR_MESSAGE
    try:
        bundle = loader(input_path)
    except Exception:
        return None, PRIVATE_LOAD_ERROR_MESSAGE
    # Re-validate the loaded bundle (the real loader validates internally
    # and raises; this also covers in-memory probes that return
    # unvalidated data). Fail-closed sanitized error.
    if _validate_private_d4b_bundle(bundle):
        return None, PRIVATE_LOAD_ERROR_MESSAGE
    report = build_private_report(
        bundle=bundle,
        synthetic_harness_test=synthetic_harness_test,
        tmp_guard_passed=tmp_guard_passed,
    )
    return report, None


# ---------------------------------------------------------------------------
# Report builders
# ---------------------------------------------------------------------------


def _build_public_report(
    checks: list[dict[str, Any]], all_passed: bool
) -> dict[str, Any]:
    """Assemble the public harness / no-validation report (fail-closed scan).

    The default committed artifact. No private D4b bundle read, no
    validation run, no labels read, no counts/metrics emitted, no claims.
    """
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": TARGET_STATUS if all_passed else "self_test_failed",
        "mode": MODE_PUBLIC,
        "phase": PHASE,
        "d4b_bundle_schema_source": D4B_BUNDLE_SCHEMA_SOURCE,
        "d4e_converter_source": D4E_CONVERTER_SOURCE,
        "d4d_runbook_protocol": D4D_RUNBOOK_PROTOCOL,
        "d4b_bundle_schema_contract": _build_d4b_bundle_schema_contract(),
        "gate_check_contract": _build_gate_check_contract(),
        "d4d_runbook_contract": _build_d4d_runbook_contract(),
        "d4e_converter_contract": _build_d4e_converter_contract(),
        "validation_harness_info": _build_validation_harness_info(),
        "self_test_summary": _self_test_category_summary(checks),
        "self_test_checks": checks,
        "self_test_passed": all_passed,
        # Default public mode reads/evaluates no D4b bundle input.
        "default_public_mode_input_validated": False,
        "private_validation_d4d_attestation_required": True,
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


def _private_success_message(report_with_guard: dict[str, Any]) -> str:
    """Build the private-mode success stdout message (no exact /tmp path)."""
    guard = report_with_guard.get("private_report_guard", {})
    return (
        "wrote D4f private gate report to /tmp output "
        f"(private_report_guard={guard.get('status')}, "
        f"bundle_validation_run=true, "
        f"synthetic_harness_test={report_with_guard['synthetic_harness_test']}, "
        f"synthetic_bundle_validated_for_harness_only="
        f"{report_with_guard['synthetic_bundle_validated_for_harness_only']}, "
        f"local_private_bundle_validation_run="
        f"{report_with_guard['local_private_bundle_validation_run']}, "
        f"real_human_bundle_validated="
        f"{report_with_guard['real_human_bundle_validated']}, "
        f"schema_gate_passed={report_with_guard['schema_gate_passed']}, "
        f"min_total_labels_gate_band="
        f"{report_with_guard['min_total_labels_gate_band']}, "
        f"k_min_gate_band={report_with_guard['k_min_gate_band']}, "
        f"exact_private_counts_emitted=false, "
        f"agreement_metric_values_emitted=false, "
        f"public_release_gate_passed=false, "
        f"d5_unblocked=false) "
        f"[NOT committed; /tmp only]"
    )


def build_report() -> dict[str, Any]:
    """Assemble the public harness / no-validation report (fail-closed scan).

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
            raise _PrivateBundleLoadError("probe: should not be called")
        return self._records

    def exists(self, path: Path) -> bool:
        self.calls.append(("exists", str(path)))
        return self._records is not None


# ---------------------------------------------------------------------------
# Self-test fixture builder
# ---------------------------------------------------------------------------


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return {"check": name, "passed": bool(ok)}


def _valid_synthetic_d4b_bundle(
    *,
    label_count: int = 3,
    synthetic: bool = True,
    real_conversion: bool = False,
    agreement_available: bool = True,
    confidence_intervals_available: bool = True,
) -> dict[str, Any]:
    """Build a synthetic D4b bundle for harness self-tests.

    Contains filled human-manual-shaped label slots (E/S values, bucket
    names, citation_valid/rater_pair_present/adjudicated booleans). This
    is a HARNESS self-test fixture only; it must be run with the
    ``--synthetic-harness-test`` flag (which sets
    ``synthetic_harness_test=true`` and
    ``local_private_bundle_validation_run=false``) OR with the real-mode
    flag path (``synthetic=False, real_conversion=True``).
    """
    labels: list[dict[str, Any]] = []
    e_levels = list(E_SCORE_LEVELS)
    s_levels = list(S_SCORE_LEVELS)
    buckets = list(BUCKET_NAMES)
    for i in range(label_count):
        labels.append(
            {
                "e_score": e_levels[i % len(e_levels)],
                "s_score": s_levels[i % len(s_levels)],
                "bucket": buckets[i % len(buckets)],
                "citation_valid": (i % 2 == 0),
                "rater_pair_present": True,
                "adjudicated": (i % 3 == 0),
            }
        )
    return {
        "schema": D4B_BUNDLE_SCHEMA_SOURCE,
        "label_source": HUMAN_MANUAL_LABEL_SOURCE,
        "rater_count": 2,
        "agreement_available": agreement_available,
        "confidence_intervals_available": confidence_intervals_available,
        "synthetic_harness_test": bool(synthetic),
        "local_private_conversion_executed": bool(real_conversion),
        "real_human_labels_converted": bool(real_conversion),
        "labels": labels,
    }


def _symlink_selftest_workspace() -> Path:
    """Create a unique /tmp workspace dir for symlink self-test fixtures."""
    pid = os.getpid()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    ws = Path("/tmp") / f"d4f_selftest_{pid}_{ts}"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


# ===========================================================================
# Self-test checks are appended below in run_self_test_checks().
# This file is intentionally structured so the self-test function is the
# last definition before the CLI; see the marker below.
# ===========================================================================

def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all D4f self-test groups. Returns (checks, all_passed)."""
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
            "default_public_mode_input_validated_false",
            skeleton["default_public_mode_input_validated"] is False,
        )
    )
    checks.append(
        _check(
            "private_validation_d4d_attestation_required_true",
            skeleton["private_validation_d4d_attestation_required"] is True,
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
            "mode_public_harness_no_private_bundle_no_validation",
            skeleton["mode"] == MODE_PUBLIC,
        )
    )
    checks.append(_check("phase_d4f", skeleton["phase"] == PHASE))
    checks.append(
        _check(
            "d4b_bundle_schema_source_correct",
            skeleton["d4b_bundle_schema_source"]
            == D4B_BUNDLE_SCHEMA_SOURCE,
        )
    )
    checks.append(
        _check(
            "d4e_converter_source_correct",
            skeleton["d4e_converter_source"] == D4E_CONVERTER_SOURCE,
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
            "d4b_bundle_schema_contract_defined_true",
            skeleton["d4b_bundle_schema_contract_defined"] is True,
        )
    )
    checks.append(
        _check(
            "gate_check_contract_defined_true",
            skeleton["gate_check_contract_defined"] is True,
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
            "agreement_availability_gate_referenced_true",
            skeleton["agreement_availability_gate_referenced"] is True,
        )
    )
    checks.append(
        _check(
            "ci_availability_gate_referenced_true",
            skeleton["ci_availability_gate_referenced"] is True,
        )
    )
    checks.append(
        _check(
            "d4b_bundle_schema_contract_has_schema_and_source",
            skeleton["d4b_bundle_schema_contract"]["schema"]
            == D4B_BUNDLE_SCHEMA_SOURCE
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
            "gate_check_contract_has_thresholds_and_bands",
            skeleton["gate_check_contract"][
                "min_total_labels_gate_referenced"
            ]
            is True
            and skeleton["gate_check_contract"]["k_min_gate_referenced"]
            is True
            and skeleton["gate_check_contract"][
                "agreement_availability_gate_referenced"
            ]
            is True
            and skeleton["gate_check_contract"][
                "ci_availability_gate_referenced"
            ]
            is True
            and skeleton["gate_check_contract"]["min_rater_count"]
            == GATE_MIN_RATER_COUNT
            and skeleton["gate_check_contract"]["min_total_labels_gate"]
            == GATE_MIN_TOTAL_LABELS
            and skeleton["gate_check_contract"]["k_min_cell_gate"]
            == GATE_K_MIN_CELL
            and skeleton["gate_check_contract"]["gate_band_values"]
            == list(GATE_BAND_VALUES)
            and skeleton["gate_check_contract"][
                "small_cell_suppression_required"
            ]
            is True
            and skeleton["gate_check_contract"][
                "exact_counts_never_emitted"
            ]
            is True
            and skeleton["gate_check_contract"][
                "metrics_never_computed"
            ]
            is True
            and skeleton["gate_check_contract"][
                "validator_not_run_by_default"
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
            "d4e_converter_contract_tmp_only_not_committed",
            skeleton["d4e_converter_contract"]["converter_source"]
            == D4E_CONVERTER_SOURCE
            and skeleton["d4e_converter_contract"]["target_bundle_schema"]
            == D4B_BUNDLE_SCHEMA_SOURCE
            and skeleton["d4e_converter_contract"]["private_only"] is True
            and skeleton["d4e_converter_contract"]["output_location"]
            == "tmp_only_local_private"
            and skeleton["d4e_converter_contract"]["committed"] is False,
        )
    )
    checks.append(
        _check(
            "validation_harness_info_tmp_only_not_committed",
            skeleton["validation_harness_info"]["available"] is True
            and skeleton["validation_harness_info"]["opt_in_required"]
            is True
            and skeleton["validation_harness_info"]["output_location"]
            == "tmp_only_local_private"
            and skeleton["validation_harness_info"]["committed"] is False
            and skeleton["validation_harness_info"][
                "validates_d4b_bundle_schema"
            ]
            is True
            and skeleton["validation_harness_info"][
                "runs_gate_checks_only"
            ]
            is True
            and skeleton["validation_harness_info"][
                "rejects_packet_refs_paths_snippets_raters"
            ]
            is True
            and skeleton["validation_harness_info"][
                "rejects_model_proxy_llm_labels"
            ]
            is True
            and skeleton["validation_harness_info"]["claims_calibration"]
            is False
            and skeleton["validation_harness_info"][
                "computes_agreement_or_ci"
            ]
            is False,
        )
    )

    # --- Group 3: No private read by default + public artifact clean. ---
    checks.append(
        _check(
            "default_mode_private_bundle_read_false",
            skeleton["private_bundle_read"] is False,
        )
    )
    checks.append(
        _check(
            "default_mode_bundle_validation_run_false",
            skeleton["bundle_validation_run"] is False,
        )
    )
    checks.append(
        _check(
            "default_mode_private_bundle_validated_false",
            skeleton["private_bundle_validated"] is False,
        )
    )
    checks.append(
        _check(
            "default_mode_labels_read_false",
            skeleton["labels_read"] is False,
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
    checks.append(
        _check(
            "default_mode_no_e_score_key",
            not _has_dict_key_anywhere(skeleton, "e_score"),
        )
    )
    checks.append(
        _check(
            "default_mode_no_bucket_key",
            not _has_dict_key_anywhere(skeleton, "bucket"),
        )
    )
    checks.append(
        _check(
            "default_mode_no_rater_id_key",
            not _has_dict_key_anywhere(skeleton, "rater_id"),
        )
    )
    checks.append(
        _check(
            "default_mode_no_task_id_key",
            not _has_dict_key_anywhere(skeleton, "task_id"),
        )
    )

    # --- Group 4: Public scanner fail-closes + contract allowlist. ---
    def _has_cat(obj: Any, cat: str) -> bool:
        return any(v["category"] == cat for v in _scan_forbidden(obj))

    checks.append(
        _check(
            "scanner_allows_label_slot_in_d4b_bundle_schema_contract",
            not _scan_forbidden(
                {
                    "d4b_bundle_schema_contract": {
                        "label_object_allowed_keys": ["e_score"]
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
                    "d4b_bundle_schema_contract": {
                        "label_object_allowed_keys": list(LABEL_SLOTS)
                    }
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
                    "d4b_bundle_schema_contract": {
                        "schema": D4B_BUNDLE_SCHEMA_SOURCE,
                        "required_label_source":
                            HUMAN_MANUAL_LABEL_SOURCE,
                    },
                    "d4e_converter_contract": {
                        "converter_source": D4E_CONVERTER_SOURCE,
                        "target_bundle_schema": D4B_BUNDLE_SCHEMA_SOURCE,
                    },
                    "d4d_runbook_contract": {
                        "protocol": D4D_RUNBOOK_PROTOCOL
                    },
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_band_values_in_gate_check_contract",
            not _scan_forbidden(
                {
                    "gate_check_contract": {
                        "gate_band_values": list(GATE_BAND_VALUES)
                    }
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_unapproved_string_in_contract",
            _has_cat(
                {
                    "d4b_bundle_schema_contract": {
                        "label_object_allowed_keys": ["compute_loss"]
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
                    "gate_check_contract": {
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
                    "d4b_bundle_schema_contract": {
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
                    "d4e_converter_contract": {
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
        ({"labels": []}, "labels"),
        ({"bucket": "x"}, "bucket"),
    ):
        checks.append(
            _check(
                f"scanner_rejects_{label}_key_outside_contract",
                _has_cat(bad_obj, "forbidden_key"),
            )
        )
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
        "agreement_metric", "kappa", "confidence_interval",
        "ci_value", "ci_lower", "ci_upper",
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
            "scanner_allows_safe_d4b_bundle_schema_source_string",
            not _scan_forbidden(
                {"d4b_bundle_schema_source": D4B_BUNDLE_SCHEMA_SOURCE}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_safe_d4e_converter_source_string",
            not _scan_forbidden(
                {"d4e_converter_source": D4E_CONVERTER_SOURCE}
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

    # --- Group 5: Private D4b bundle INPUT guard. ---
    valid_ok = not _validate_private_d4b_bundle(
        _valid_synthetic_d4b_bundle()
    )
    checks.append(
        _check("valid_synthetic_bundle_validates", valid_ok)
    )
    non_dict_rejected = bool(
        _validate_private_d4b_bundle([1, 2, 3])
    )
    checks.append(
        _check("non_dict_bundle_rejected", non_dict_rejected)
    )
    bad_schema_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(), "schema": "wrong"}
        )
    )
    checks.append(
        _check("unknown_bundle_schema_rejected", bad_schema_rejected)
    )
    bad_label_source_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(), "label_source": "proxy"}
        )
    )
    checks.append(
        _check(
            "wrong_label_source_rejected", bad_label_source_rejected
        )
    )
    extra_top_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(), "extra": 1}
        )
    )
    checks.append(
        _check("unknown_top_key_rejected", extra_top_rejected)
    )
    path_key_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(), "path": "src/x.rs"}
        )
    )
    checks.append(
        _check("bundle_with_path_key_rejected", path_key_rejected)
    )
    snippet_key_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(), "snippet": "code"}
        )
    )
    checks.append(
        _check("bundle_with_snippet_key_rejected", snippet_key_rejected)
    )
    content_sha_key_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(), "content_sha": "a" * 64}
        )
    )
    checks.append(
        _check(
            "bundle_with_content_sha_key_rejected",
            content_sha_key_rejected,
        )
    )
    query_key_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(), "query_text": "q"}
        )
    )
    checks.append(
        _check("bundle_with_query_text_key_rejected", query_key_rejected)
    )
    candidate_key_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(), "candidate_text": "c"}
        )
    )
    checks.append(
        _check(
            "bundle_with_candidate_text_key_rejected",
            candidate_key_rejected,
        )
    )
    rater_id_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(), "rater_id": "alice"}
        )
    )
    checks.append(
        _check("bundle_with_rater_id_key_rejected", rater_id_rejected)
    )
    task_id_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(), "task_id": "t1"}
        )
    )
    checks.append(
        _check("bundle_with_task_id_key_rejected", task_id_rejected)
    )
    packet_ref_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(), "packet_ref": "p1"}
        )
    )
    checks.append(
        _check("bundle_with_packet_ref_key_rejected", packet_ref_rejected)
    )
    provider_payload_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(), "provider_payload": {"x": 1}}
        )
    )
    checks.append(
        _check(
            "bundle_with_provider_payload_key_rejected",
            provider_payload_rejected,
        )
    )
    api_key_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(), "api_key": "sk-xxx"}
        )
    )
    checks.append(
        _check("bundle_with_api_key_key_rejected", api_key_rejected)
    )
    model_output_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(), "model_output": "x"}
        )
    )
    checks.append(
        _check("bundle_with_model_output_key_rejected", model_output_rejected)
    )
    agreement_metric_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(), "agreement_metric": 0.8}
        )
    )
    checks.append(
        _check(
            "bundle_with_agreement_metric_key_rejected",
            agreement_metric_rejected,
        )
    )
    ci_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(),
             "confidence_interval": [0.1, 0.2]}
        )
    )
    checks.append(
        _check("bundle_with_ci_key_rejected", ci_rejected)
    )
    per_row_hash_rejected = bool(
        _validate_private_d4b_bundle(
            {**_valid_synthetic_d4b_bundle(), "per_row_hash": "x"}
        )
    )
    checks.append(
        _check("bundle_with_per_row_hash_key_rejected", per_row_hash_rejected)
    )
    bad_label = _valid_synthetic_d4b_bundle()
    bad_label = {
        **bad_label,
        "labels": [{**bad_label["labels"][0], "extra_key": "x"}],
    }
    unknown_label_key_rejected = bool(
        _validate_private_d4b_bundle(bad_label)
    )
    checks.append(
        _check(
            "bundle_with_unknown_label_key_rejected",
            unknown_label_key_rejected,
        )
    )
    bad_e = _valid_synthetic_d4b_bundle()
    bad_e = {
        **bad_e,
        "labels": [{**bad_e["labels"][0], "e_score": "E9"}],
    }
    bad_e_rejected = bool(_validate_private_d4b_bundle(bad_e))
    checks.append(
        _check("bundle_with_invalid_e_score_rejected", bad_e_rejected)
    )
    bad_bucket = _valid_synthetic_d4b_bundle()
    bad_bucket = {
        **bad_bucket,
        "labels": [{**bad_bucket["labels"][0], "bucket": "unknown"}],
    }
    bad_bucket_rejected = bool(_validate_private_d4b_bundle(bad_bucket))
    checks.append(
        _check("bundle_with_invalid_bucket_rejected", bad_bucket_rejected)
    )
    bad_bool = _valid_synthetic_d4b_bundle()
    bad_bool = {
        **bad_bool,
        "labels": [{**bad_bool["labels"][0], "citation_valid": "yes"}],
    }
    bad_bool_rejected = bool(_validate_private_d4b_bundle(bad_bool))
    checks.append(
        _check(
            "bundle_with_non_bool_citation_valid_rejected",
            bad_bool_rejected,
        )
    )
    bad_rater = _valid_synthetic_d4b_bundle()
    bad_rater = {**bad_rater, "rater_count": 1}
    bad_rater_rejected = bool(_validate_private_d4b_bundle(bad_rater))
    checks.append(
        _check("bundle_with_rater_count_below_min_rejected", bad_rater_rejected)
    )
    bad_agr = _valid_synthetic_d4b_bundle()
    bad_agr = {**bad_agr, "agreement_available": "yes"}
    bad_agr_rejected = bool(_validate_private_d4b_bundle(bad_agr))
    checks.append(
        _check(
            "bundle_with_non_bool_agreement_available_rejected",
            bad_agr_rejected,
        )
    )
    bad_synth = _valid_synthetic_d4b_bundle(synthetic=True)
    bad_synth = {**bad_synth, "local_private_conversion_executed": True}
    bad_synth_rejected = bool(_validate_private_d4b_bundle(bad_synth))
    checks.append(
        _check(
            "bundle_synthetic_but_local_conversion_true_rejected",
            bad_synth_rejected,
        )
    )

    # --- Group 6: Gate-check logic. ---
    gates_valid = _run_gate_checks(_valid_synthetic_d4b_bundle())
    checks.append(
        _check(
            "gates_valid_bundle_schema_gate_passes",
            gates_valid["schema_gate_passed"] is True,
        )
    )
    checks.append(
        _check(
            "gates_valid_bundle_label_source_gate_passes",
            gates_valid["label_source_gate_passed"] is True,
        )
    )
    checks.append(
        _check(
            "gates_valid_bundle_rater_count_gate_passes",
            gates_valid["rater_count_gate_passed"] is True,
        )
    )
    checks.append(
        _check(
            "gates_valid_bundle_agreement_availability_gate_passes",
            gates_valid["agreement_availability_gate_passed"] is True,
        )
    )
    checks.append(
        _check(
            "gates_valid_bundle_ci_availability_gate_passes",
            gates_valid["ci_availability_gate_passed"] is True,
        )
    )
    checks.append(
        _check(
            "gates_valid_bundle_min_total_labels_band_emitted",
            gates_valid["min_total_labels_gate_band"]
            in ALLOWED_BAND_VALUES,
        )
    )
    checks.append(
        _check(
            "gates_valid_bundle_k_min_band_emitted",
            gates_valid["k_min_gate_band"] in ALLOWED_BAND_VALUES,
        )
    )
    small_bundle = _valid_synthetic_d4b_bundle(label_count=3)
    small_gates = _run_gate_checks(small_bundle)
    checks.append(
        _check(
            "min_n_gate_small_bundle_not_met",
            small_gates["min_total_labels_gate_band"] == "not_met",
        )
    )
    large_bundle = _valid_synthetic_d4b_bundle(
        label_count=GATE_MIN_TOTAL_LABELS
    )
    large_gates = _run_gate_checks(large_bundle)
    checks.append(
        _check(
            "min_n_gate_large_bundle_met",
            large_gates["min_total_labels_gate_band"] == "met",
        )
    )
    k_min_bundle_labels: list[dict[str, Any]] = []
    for bucket_name in BUCKET_NAMES:
        for _ in range(GATE_K_MIN_CELL):
            k_min_bundle_labels.append(
                {
                    "e_score": "E0",
                    "s_score": "S0",
                    "bucket": bucket_name,
                    "citation_valid": True,
                    "rater_pair_present": True,
                    "adjudicated": True,
                }
            )
    k_min_bundle = _valid_synthetic_d4b_bundle(label_count=1)
    k_min_bundle = {**k_min_bundle, "labels": k_min_bundle_labels}
    k_min_gates = _run_gate_checks(k_min_bundle)
    checks.append(
        _check(
            "k_min_gate_all_buckets_met_met",
            k_min_gates["k_min_gate_band"] == "met",
        )
    )
    k_min_bad_labels: list[dict[str, Any]] = []
    k_min_bad_labels.append(
        {
            "e_score": "E0",
            "s_score": "S0",
            "bucket": "primary_evidence",
            "citation_valid": True,
            "rater_pair_present": True,
            "adjudicated": True,
        }
    )
    for bucket_name in BUCKET_NAMES:
        if bucket_name == "primary_evidence":
            continue
        for _ in range(GATE_K_MIN_CELL):
            k_min_bad_labels.append(
                {
                    "e_score": "E0",
                    "s_score": "S0",
                    "bucket": bucket_name,
                    "citation_valid": True,
                    "rater_pair_present": True,
                    "adjudicated": True,
                }
            )
    k_min_bad_bundle = _valid_synthetic_d4b_bundle(label_count=1)
    k_min_bad_bundle = {**k_min_bad_bundle, "labels": k_min_bad_labels}
    k_min_bad_gates = _run_gate_checks(k_min_bad_bundle)
    checks.append(
        _check(
            "k_min_gate_small_cell_not_met",
            k_min_bad_gates["k_min_gate_band"] == "not_met",
        )
    )
    invalid_gates = _run_gate_checks({"schema": "wrong"})
    checks.append(
        _check(
            "invalid_bundle_all_gates_not_evaluated",
            invalid_gates["schema_gate_passed"] is False
            and invalid_gates["min_total_labels_gate_band"]
            == "not_evaluated"
            and invalid_gates["k_min_gate_band"] == "not_evaluated",
        )
    )
    no_agr = _valid_synthetic_d4b_bundle(agreement_available=False)
    no_agr_gates = _run_gate_checks(no_agr)
    checks.append(
        _check(
            "missing_agreement_availability_gate_fails",
            no_agr_gates["agreement_availability_gate_passed"] is False,
        )
    )
    no_ci = _valid_synthetic_d4b_bundle(
        confidence_intervals_available=False
    )
    no_ci_gates = _run_gate_checks(no_ci)
    checks.append(
        _check(
            "missing_ci_availability_gate_fails",
            no_ci_gates["ci_availability_gate_passed"] is False,
        )
    )
    gates_blob = json.dumps(gates_valid, sort_keys=True)
    gates_dict = json.loads(gates_blob) if gates_blob else {}
    checks.append(
        _check(
            "gates_output_no_exact_count_keys",
            "total_labels" not in gates_dict
            and "label_count" not in gates_dict
            and "bucket_count" not in gates_dict
            and "cell_count" not in gates_dict
            and "n" not in gates_dict
            and "count" not in gates_dict
            and "bucket_counts" not in gates_dict
            and "cell_counts" not in gates_dict,
        )
    )

    # --- Group 7: Real-mode flag-path decision logic. ---
    checks.append(
        _check(
            "real_validation_synthetic_cli_false",
            _decide_real_validation_claim(
                synthetic_harness_test_cli=True,
                bundle_synthetic_flag=False,
                label_source_human=True,
                d4e_real_conversion=True,
                schema_valid=True,
                tmp_guard_passed=True,
            )
            is False,
        )
    )
    checks.append(
        _check(
            "real_validation_bundle_synthetic_false",
            _decide_real_validation_claim(
                synthetic_harness_test_cli=False,
                bundle_synthetic_flag=True,
                label_source_human=True,
                d4e_real_conversion=True,
                schema_valid=True,
                tmp_guard_passed=True,
            )
            is False,
        )
    )
    checks.append(
        _check(
            "real_validation_real_passes_true",
            _decide_real_validation_claim(
                synthetic_harness_test_cli=False,
                bundle_synthetic_flag=False,
                label_source_human=True,
                d4e_real_conversion=True,
                schema_valid=True,
                tmp_guard_passed=True,
            )
            is True,
        )
    )
    checks.append(
        _check(
            "real_validation_label_source_not_human_false",
            _decide_real_validation_claim(
                synthetic_harness_test_cli=False,
                bundle_synthetic_flag=False,
                label_source_human=False,
                d4e_real_conversion=True,
                schema_valid=True,
                tmp_guard_passed=True,
            )
            is False,
        )
    )
    checks.append(
        _check(
            "real_validation_d4e_not_real_conversion_false",
            _decide_real_validation_claim(
                synthetic_harness_test_cli=False,
                bundle_synthetic_flag=False,
                label_source_human=True,
                d4e_real_conversion=False,
                schema_valid=True,
                tmp_guard_passed=True,
            )
            is False,
        )
    )
    checks.append(
        _check(
            "real_validation_invalid_schema_false",
            _decide_real_validation_claim(
                synthetic_harness_test_cli=False,
                bundle_synthetic_flag=False,
                label_source_human=True,
                d4e_real_conversion=True,
                schema_valid=False,
                tmp_guard_passed=True,
            )
            is False,
        )
    )
    checks.append(
        _check(
            "real_validation_tmp_guard_failed_false",
            _decide_real_validation_claim(
                synthetic_harness_test_cli=False,
                bundle_synthetic_flag=False,
                label_source_human=True,
                d4e_real_conversion=True,
                schema_valid=True,
                tmp_guard_passed=False,
            )
            is False,
        )
    )

    # === SELF_TEST_INSERTION_POINT ===

    # --- Group 8: CLI guard matrix (pure lexical). ---
    sensitive_input = Path(
        "/private/SECRET_VALIDATOR_SENTINEL_sensitive.json"
    )
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
    err_allow_no_input = _validate_cli_args(
        allow_private=True,
        input_path=None,
        out_path=Path("/tmp/d4f.json"),
        synthetic_harness_test=False,
    )
    checks.append(
        _check(
            "cli_allow_without_input_rejected",
            err_allow_no_input is not None,
        )
    )
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
    err_non_tmp = _validate_cli_args(
        allow_private=True,
        input_path=sensitive_input,
        out_path=Path("/not/tmp/d4f.json"),
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
    err_tmp_ok = _validate_cli_args(
        allow_private=True,
        input_path=sensitive_input,
        out_path=Path("/tmp/d4f_report.json"),
        synthetic_harness_test=False,
    )
    checks.append(
        _check(
            "cli_allow_tmp_out_allowed",
            err_tmp_ok is None,
        )
    )
    err_tmp_synth = _validate_cli_args(
        allow_private=True,
        input_path=sensitive_input,
        out_path=Path("/tmp/d4f_harness.json"),
        synthetic_harness_test=True,
    )
    checks.append(
        _check(
            "cli_allow_tmp_out_synthetic_allowed",
            err_tmp_synth is None,
        )
    )
    err_default = _validate_cli_args(
        allow_private=False,
        input_path=None,
        out_path=None,
        synthetic_harness_test=False,
    )
    checks.append(
        _check("cli_default_mode_allowed", err_default is None)
    )
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
    _report, err_probe = _run_private_validator_mode(
        allow_private=True,
        input_path=Path(
            "/private/SECRET_VALIDATOR_SENTINEL_nonexistent.json"
        ),
        out_path=Path("/not/tmp/d4f.json"),  # invalid out (lexical)
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
    probe_committed = _ReadProbe()
    _report2, err_pc = _run_private_validator_mode(
        allow_private=True,
        input_path=Path("/private/SECRET_VALIDATOR_SENTINEL.json"),
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
    probe_nontmp = _ReadProbe()
    _report3, err_pn = _run_private_validator_mode(
        allow_private=True,
        input_path=Path("/private/SECRET_VALIDATOR_SENTINEL.json"),
        out_path=Path("/home/user/d4f.json"),
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
    probe_synth = _ReadProbe()
    _report4, err_ps = _run_private_validator_mode(
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
    probe_input_only = _ReadProbe()
    _report5, err_pio = _run_private_validator_mode(
        allow_private=False,
        input_path=Path("/private/SECRET_VALIDATOR_SENTINEL.json"),
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
    probe_allow_only = _ReadProbe()
    _report6, err_ao = _run_private_validator_mode(
        allow_private=True,
        input_path=None,
        out_path=Path("/tmp/d4f.json"),
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
    malformed_bundle = {
        **_valid_synthetic_d4b_bundle(),
        "provider_payload": {"x": _SECRET_SENTINEL},
        "api_key": "sk-" + _SECRET_SENTINEL,
        "path": "/private/SECRET_VALIDATOR_SENTINEL_bundle.json",
    }
    probe_malformed = _ReadProbe(records=malformed_bundle)
    _report7, err_malformed = _run_private_validator_mode(
        allow_private=True,
        input_path=Path(
            "/private/SECRET_VALIDATOR_SENTINEL_bundle.json"
        ),
        out_path=Path("/tmp/d4f_malformed.json"),
        synthetic_harness_test=False,
        loader=probe_malformed.loader,
        input_exists=probe_malformed.exists,
    )
    checks.append(
        _check(
            "malformed_bundle_returns_sanitized_error",
            err_malformed == PRIVATE_LOAD_ERROR_MESSAGE
            and _report7 is None,
        )
    )
    checks.append(
        _check(
            "malformed_bundle_error_no_sentinel_or_basename",
            err_malformed is not None
            and _SECRET_SENTINEL not in err_malformed
            and "SECRET_VALIDATOR_SENTINEL_bundle.json"
            not in err_malformed
            and "sk-" not in err_malformed,
        )
    )
    probe_missing = _ReadProbe(records=None)
    probe_missing.exists = lambda p: False  # type: ignore[method-assign]
    _report8, err_missing = _run_private_validator_mode(
        allow_private=True,
        input_path=Path(
            "/private/SECRET_VALIDATOR_SENTINEL_missing.json"
        ),
        out_path=Path("/tmp/d4f_missing.json"),
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
            and "SECRET_VALIDATOR_SENTINEL_missing.json"
            not in err_missing,
        )
    )

    # --- Group 11: Private validator success path (synthetic harness
    # test) --- no path/basename/raw label/exact counts/output path in
    # the report. ---
    valid_bundle = _valid_synthetic_d4b_bundle()
    sensitive_in = Path(
        "/private/SECRET_VALIDATOR_SENTINEL_success.json"
    )
    sensitive_out = Path("/tmp/SECRET_VALIDATOR_SENTINEL_out.json")
    probe_ok = _ReadProbe(records=valid_bundle)
    report_ok, err_ok = _run_private_validator_mode(
        allow_private=True,
        input_path=sensitive_in,
        out_path=sensitive_out,
        synthetic_harness_test=True,
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
    checks.append(
        _check(
            "private_report_no_packet_ref_key",
            report_ok is not None
            and not _has_dict_key_anywhere(report_ok, "packet_ref"),
        )
    )
    checks.append(
        _check(
            "private_report_no_path_key",
            report_ok is not None
            and not _has_dict_key_anywhere(report_ok, "path"),
        )
    )
    checks.append(
        _check(
            "private_report_no_snippet_key",
            report_ok is not None
            and not _has_dict_key_anywhere(report_ok, "snippet"),
        )
    )
    checks.append(
        _check(
            "private_report_no_content_sha_key",
            report_ok is not None
            and not _has_dict_key_anywhere(report_ok, "content_sha"),
        )
    )
    checks.append(
        _check(
            "private_report_no_query_text_key",
            report_ok is not None
            and not _has_dict_key_anywhere(report_ok, "query_text"),
        )
    )
    checks.append(
        _check(
            "private_report_no_candidate_text_key",
            report_ok is not None
            and not _has_dict_key_anywhere(report_ok, "candidate_text"),
        )
    )
    checks.append(
        _check(
            "private_report_no_rater_id_key",
            report_ok is not None
            and not _has_dict_key_anywhere(report_ok, "rater_id"),
        )
    )
    checks.append(
        _check(
            "private_report_no_task_id_key",
            report_ok is not None
            and not _has_dict_key_anywhere(report_ok, "task_id"),
        )
    )
    checks.append(
        _check(
            "private_report_no_labels_key",
            report_ok is not None
            and not _has_dict_key_anywhere(report_ok, "labels"),
        )
    )
    checks.append(
        _check(
            "private_report_no_label_slots_key",
            report_ok is not None
            and not _has_dict_key_anywhere(report_ok, "label_slots"),
        )
    )
    checks.append(
        _check(
            "private_report_no_d4d_runbook_attestation_key",
            report_ok is not None
            and not _has_dict_key_anywhere(
                report_ok, "d4d_runbook_attestation"
            ),
        )
    )
    checks.append(
        _check(
            "private_report_no_source_packet_schema_key",
            report_ok is not None
            and not _has_dict_key_anywhere(
                report_ok, "source_packet_schema"
            ),
        )
    )
    checks.append(
        _check(
            "private_report_no_e_score_key",
            report_ok is not None
            and not _has_dict_key_anywhere(report_ok, "e_score"),
        )
    )
    checks.append(
        _check(
            "private_report_no_bucket_key",
            report_ok is not None
            and not _has_dict_key_anywhere(report_ok, "bucket"),
        )
    )
    checks.append(
        _check(
            "private_report_no_agreement_metric_key",
            report_ok is not None
            and not _has_dict_key_anywhere(report_ok, "agreement_metric"),
        )
    )
    checks.append(
        _check(
            "private_report_no_confidence_interval_key",
            report_ok is not None
            and not _has_dict_key_anywhere(
                report_ok, "confidence_interval"
            ),
        )
    )
    checks.append(
        _check(
            "private_report_no_count_keys",
            report_ok is not None
            and not _has_dict_key_anywhere(report_ok, "total_labels")
            and not _has_dict_key_anywhere(report_ok, "label_count")
            and not _has_dict_key_anywhere(report_ok, "bucket_count")
            and not _has_dict_key_anywhere(report_ok, "cell_count")
            and not _has_dict_key_anywhere(report_ok, "count"),
        )
    )
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
    checks.append(
        _check(
            "private_report_synthetic_harness_test_true",
            report_ok is not None
            and report_ok["synthetic_harness_test"] is True,
        )
    )
    checks.append(
        _check(
            "private_report_synthetic_bundle_validated_harness_only_true",
            report_ok is not None
            and report_ok[
                "synthetic_bundle_validated_for_harness_only"
            ]
            is True,
        )
    )
    checks.append(
        _check(
            "private_report_local_private_bundle_validation_run_false_synthetic",
            report_ok is not None
            and report_ok["local_private_bundle_validation_run"] is False,
        )
    )
    checks.append(
        _check(
            "private_report_real_human_bundle_validated_false_synthetic",
            report_ok is not None
            and report_ok["real_human_bundle_validated"] is False,
        )
    )
    checks.append(
        _check(
            "private_report_schema_version_correct",
            report_ok is not None
            and report_ok["schema_version"] == PRIVATE_REPORT_SCHEMA,
        )
    )
    checks.append(
        _check(
            "private_report_public_artifact_false",
            report_ok is not None
            and report_ok["public_artifact"] is False,
        )
    )
    checks.append(
        _check(
            "private_report_do_not_commit_true",
            report_ok is not None
            and report_ok["do_not_commit"] is True,
        )
    )
    checks.append(
        _check(
            "private_report_small_cell_suppression_required_true",
            report_ok is not None
            and report_ok["small_cell_suppression_required"] is True,
        )
    )
    checks.append(
        _check(
            "private_report_public_release_gate_passed_false",
            report_ok is not None
            and report_ok["public_release_gate_passed"] is False,
        )
    )
    checks.append(
        _check(
            "private_report_d5_unblocked_false",
            report_ok is not None
            and report_ok["d5_unblocked"] is False,
        )
    )
    checks.append(
        _check(
            "private_report_no_emitted_flags_false",
            report_ok is not None
            and report_ok["exact_private_counts_emitted"] is False
            and report_ok["bucket_counts_emitted"] is False
            and report_ok["cell_counts_emitted"] is False
            and report_ok["agreement_metric_values_emitted"] is False
            and report_ok["confidence_interval_values_emitted"] is False,
        )
    )
    checks.append(
        _check(
            "private_report_min_total_labels_band_emitted",
            report_ok is not None
            and report_ok["min_total_labels_gate_band"]
            in ALLOWED_BAND_VALUES,
        )
    )
    checks.append(
        _check(
            "private_report_k_min_band_emitted",
            report_ok is not None
            and report_ok["k_min_gate_band"] in ALLOWED_BAND_VALUES,
        )
    )
    guard = _private_report_guard_summary(
        report_ok,
        forbidden_path_fragments=(
            str(sensitive_in),
            sensitive_in.name,
            str(sensitive_out),
            sensitive_out.name,
        ),
    )
    checks.append(
        _check(
            "private_report_guard_passes_clean_report",
            guard["status"] == "pass" and guard["violations_count"] == 0,
        )
    )
    report_ok_with_guard = dict(report_ok) if report_ok else {}
    report_ok_with_guard["private_report_guard"] = guard
    msg = (
        _private_success_message(report_ok_with_guard)
        if report_ok else ""
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
    checks.append(
        _check(
            "private_success_message_no_counts_or_metrics",
            "exact_private_counts_emitted=false" in msg
            and "agreement_metric_values_emitted=false" in msg
            and "min_total_labels_gate_band=" in msg
            and "k_min_gate_band=" in msg
            and "public_release_gate_passed=false" in msg
            and "d5_unblocked=false" in msg,
        )
    )

    # --- Group 12: Real-mode flag-path test (in-memory, NOT committed).
    # A real-mode run (synthetic CLI flag false, bundle not
    # synthetic-marked, label_source is human manual, D4e real-conversion
    # flags are true, schema passes, /tmp guard passes) over a synthetic
    # fixture can set local_private_bundle_validation_run=true and
    # real_human_bundle_validated=true only locally. Docs mark this as a
    # flag-path test, NOT evidence that real labels exist.
    real_fixture = _valid_synthetic_d4b_bundle(
        synthetic=False, real_conversion=True
    )
    probe_real = _ReadProbe(records=real_fixture)
    report_real, err_real = _run_private_validator_mode(
        allow_private=True,
        input_path=Path(
            "/private/SECRET_VALIDATOR_SENTINEL_real.json"
        ),
        out_path=Path("/tmp/SECRET_VALIDATOR_SENTINEL_real_out.json"),
        synthetic_harness_test=False,
        loader=probe_real.loader,
        input_exists=probe_real.exists,
    )
    checks.append(
        _check(
            "real_mode_report_local_validation_true",
            err_real is None
            and report_real is not None
            and report_real["synthetic_harness_test"] is False
            and report_real["local_private_bundle_validation_run"] is True
            and report_real["real_human_bundle_validated"] is True,
        )
    )
    checks.append(
        _check(
            "real_mode_report_synthetic_bundle_validated_harness_only_false",
            report_real is not None
            and report_real[
                "synthetic_bundle_validated_for_harness_only"
            ]
            is False,
        )
    )
    checks.append(
        _check(
            "real_mode_report_no_sentinel_or_paths",
            report_real is not None
            and _SECRET_SENTINEL
            not in json.dumps(report_real, sort_keys=True),
        )
    )
    checks.append(
        _check(
            "real_mode_report_public_release_gate_passed_false",
            report_real is not None
            and report_real["public_release_gate_passed"] is False
            and report_real["d5_unblocked"] is False,
        )
    )
    checks.append(
        _check(
            "real_mode_report_guard_passes",
            report_real is not None
            and _private_report_guard_summary(
                report_real,
                forbidden_path_fragments=(
                    "/private/SECRET_VALIDATOR_SENTINEL_real.json",
                    "SECRET_VALIDATOR_SENTINEL_real.json",
                    "/tmp/SECRET_VALIDATOR_SENTINEL_real_out.json",
                    "SECRET_VALIDATOR_SENTINEL_real_out.json",
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
        tmp_in = ws / "d4b_bundle.json"
        tmp_out = ws / "d4f_report.json"
        _write_json(tmp_in, valid_bundle)
        report_file, err_file = _run_private_validator_mode(
            allow_private=True,
            input_path=tmp_in,
            out_path=tmp_out,
            synthetic_harness_test=True,
            loader=_default_loader,
            input_exists=_default_exists,
        )
        checks.append(
            _check(
                "tmp_smoke_success_returns_report",
                err_file is None and report_file is not None,
            )
        )
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
                    "tmp_smoke_readback_has_correct_schema",
                    read_back["schema_version"] == PRIVATE_REPORT_SCHEMA
                    and read_back["public_artifact"] is False
                    and read_back["do_not_commit"] is True,
                )
            )
            checks.append(
                _check(
                    "tmp_smoke_readback_has_gate_booleans",
                    isinstance(read_back.get("schema_gate_passed"), bool)
                    and isinstance(
                        read_back.get("label_source_gate_passed"), bool
                    )
                    and isinstance(
                        read_back.get("rater_count_gate_passed"), bool
                    )
                    and isinstance(
                        read_back.get(
                            "agreement_availability_gate_passed"
                        ),
                        bool,
                    )
                    and isinstance(
                        read_back.get("ci_availability_gate_passed"),
                        bool,
                    ),
                )
            )
            checks.append(
                _check(
                    "tmp_smoke_readback_has_bands",
                    read_back.get("min_total_labels_gate_band")
                    in ALLOWED_BAND_VALUES
                    and read_back.get("k_min_gate_band")
                    in ALLOWED_BAND_VALUES,
                )
            )
            checks.append(
                _check(
                    "tmp_smoke_readback_no_labels_key",
                    not _has_dict_key_anywhere(read_back, "labels"),
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
                    "tmp_smoke_readback_no_count_keys",
                    not _has_dict_key_anywhere(read_back, "total_labels")
                    and not _has_dict_key_anywhere(read_back, "label_count")
                    and not _has_dict_key_anywhere(read_back, "bucket_count")
                    and not _has_dict_key_anywhere(read_back, "cell_count"),
                )
            )
            checks.append(
                _check(
                    "tmp_smoke_readback_no_agreement_metric_keys",
                    not _has_dict_key_anywhere(
                        read_back, "agreement_metric"
                    )
                    and not _has_dict_key_anywhere(
                        read_back, "confidence_interval"
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
            checks.append(
                _check(
                    "tmp_smoke_readback_synthetic_harness_test_true",
                    read_back["synthetic_harness_test"] is True
                    and read_back[
                        "synthetic_bundle_validated_for_harness_only"
                    ]
                    is True
                    and read_back[
                        "local_private_bundle_validation_run"
                    ]
                    is False
                    and read_back["real_human_bundle_validated"] is False,
                )
            )
            checks.append(
                _check(
                    "tmp_smoke_readback_public_release_gate_passed_false",
                    read_back["public_release_gate_passed"] is False
                    and read_back["d5_unblocked"] is False,
                )
            )
        else:
            checks.append(_check("tmp_smoke_success_returns_report", False))
    finally:
        import shutil
        if ws is not None:
            shutil.rmtree(ws, ignore_errors=True)

    # --- Group 14: Resolved /tmp symlink-escape guards (filesystem). ---
    ws2 = None
    try:
        ws2 = _symlink_selftest_workspace()
        escape_link = ws2 / "link_to_repo"
        try:
            escape_link.symlink_to("/workspace")
        except OSError:
            escape_link.symlink_to("/")
        out_parent_escape = escape_link / "out.json"
        probe_esc = _ReadProbe(records=valid_bundle)
        _rep_esc, err_esc = _run_private_validator_mode(
            allow_private=True,
            input_path=Path(
                "/private/SECRET_VALIDATOR_SENTINEL_esc.json"
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
        out_file_symlink = ws2 / "outlink.json"
        try:
            out_file_symlink.symlink_to("/workspace/secret.json")
        except OSError:
            out_file_symlink.symlink_to("/secret.json")
        probe_fs = _ReadProbe(records=valid_bundle)
        _rep_fs, err_fs = _run_private_validator_mode(
            allow_private=True,
            input_path=Path(
                "/private/SECRET_VALIDATOR_SENTINEL_fs.json"
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
        out_valid = ws2 / "valid_out.json"
        probe_vo = _ReadProbe(records=valid_bundle)
        _rep_vo, err_vo = _run_private_validator_mode(
            allow_private=True,
            input_path=Path(
                "/private/SECRET_VALIDATOR_SENTINEL_vo.json"
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

    # --- Group 15: Private report OUTPUT guard rejects bad reports. ---
    # labels key -> guard fails.
    bad_report = dict(report_ok) if report_ok else {}
    bad_report["labels"] = [{"e_score": "E0"}]
    guard_bad = _private_report_guard_summary(bad_report)
    checks.append(
        _check(
            "private_guard_rejects_labels_key",
            guard_bad["status"] == "fail",
        )
    )
    # path key -> guard fails.
    bad_report2 = dict(report_ok) if report_ok else {}
    bad_report2["path"] = "src/x.rs"
    guard_bad2 = _private_report_guard_summary(bad_report2)
    checks.append(
        _check(
            "private_guard_rejects_path_key",
            guard_bad2["status"] == "fail",
        )
    )
    # snippet key -> guard fails.
    bad_report3 = dict(report_ok) if report_ok else {}
    bad_report3["snippet"] = "code"
    guard_bad3 = _private_report_guard_summary(bad_report3)
    checks.append(
        _check(
            "private_guard_rejects_snippet_key",
            guard_bad3["status"] == "fail",
        )
    )
    # rater_id key -> guard fails.
    bad_report4 = dict(report_ok) if report_ok else {}
    bad_report4["rater_id"] = "alice"
    guard_bad4 = _private_report_guard_summary(bad_report4)
    checks.append(
        _check(
            "private_guard_rejects_rater_id_key",
            guard_bad4["status"] == "fail",
        )
    )
    # wrong schema_version -> guard fails.
    bad_report5 = dict(report_ok) if report_ok else {}
    bad_report5["schema_version"] = "wrong_schema"
    guard_bad5 = _private_report_guard_summary(bad_report5)
    checks.append(
        _check(
            "private_guard_rejects_wrong_schema_version",
            guard_bad5["status"] == "fail",
        )
    )
    # public_release_gate_passed=true -> guard fails.
    bad_report6 = dict(report_ok) if report_ok else {}
    bad_report6["public_release_gate_passed"] = True
    guard_bad6 = _private_report_guard_summary(bad_report6)
    checks.append(
        _check(
            "private_guard_rejects_public_release_gate_passed_true",
            guard_bad6["status"] == "fail",
        )
    )
    # d5_unblocked=true -> guard fails.
    bad_report7 = dict(report_ok) if report_ok else {}
    bad_report7["d5_unblocked"] = True
    guard_bad7 = _private_report_guard_summary(bad_report7)
    checks.append(
        _check(
            "private_guard_rejects_d5_unblocked_true",
            guard_bad7["status"] == "fail",
        )
    )
    # synthetic but local_validation=true -> guard fails.
    bad_report8 = dict(report_ok) if report_ok else {}
    bad_report8["local_private_bundle_validation_run"] = True
    guard_bad8 = _private_report_guard_summary(bad_report8)
    checks.append(
        _check(
            "private_guard_rejects_synthetic_but_local_validation_true",
            guard_bad8["status"] == "fail",
        )
    )
    # agreement_metric key -> guard fails.
    bad_report9 = dict(report_ok) if report_ok else {}
    bad_report9["agreement_metric"] = 0.8
    guard_bad9 = _private_report_guard_summary(bad_report9)
    checks.append(
        _check(
            "private_guard_rejects_agreement_metric_key",
            guard_bad9["status"] == "fail",
        )
    )
    # confidence_interval key -> guard fails.
    bad_report10 = dict(report_ok) if report_ok else {}
    bad_report10["confidence_interval"] = [0.1, 0.2]
    guard_bad10 = _private_report_guard_summary(bad_report10)
    checks.append(
        _check(
            "private_guard_rejects_confidence_interval_key",
            guard_bad10["status"] == "fail",
        )
    )
    # total_labels key (exact count) -> guard fails.
    bad_report11 = dict(report_ok) if report_ok else {}
    bad_report11["total_labels"] = 50
    guard_bad11 = _private_report_guard_summary(bad_report11)
    checks.append(
        _check(
            "private_guard_rejects_total_labels_key",
            guard_bad11["status"] == "fail",
        )
    )
    # invalid band value -> guard fails.
    bad_report12 = dict(report_ok) if report_ok else {}
    bad_report12["min_total_labels_gate_band"] = "maybe"
    guard_bad12 = _private_report_guard_summary(bad_report12)
    checks.append(
        _check(
            "private_guard_rejects_invalid_band_value",
            guard_bad12["status"] == "fail",
        )
    )
    # Clean report passes.
    guard_clean = _private_report_guard_summary(report_ok)
    checks.append(
        _check(
            "private_guard_passes_clean_report_repeat",
            guard_clean["status"] == "pass",
        )
    )

    # --- Group 16: Sanitized unknown/private-looking argument errors
    # (SafeArgumentParser). ---
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
                    "/private/SECRET_VALIDATOR_SENTINEL_secret.json",
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
            "cli_has_allow_private_bundle_argument",
            "--allow-private-bundle" in cli_opts,
        )
    )
    checks.append(
        _check(
            "cli_has_input_bundle_argument",
            "--input-bundle" in cli_opts,
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
                "--allow-private-bundle",
                "--input-bundle",
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

    A caller may pass a private-looking ``--input-bundle /tmp/...`` by
    mistake; default argparse would echo the unknown argument and value
    into stderr. Keep the usage line but replace the raw error with a
    fixed generic message.
    """

    def error(self, message: str) -> NoReturn:  # noqa: D401 - argparse signature
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    """Build the D4f CLI parser."""
    ap = SafeArgumentParser(
        description=(
            "D4b bundle validation / gate-check harness "
            "(public harness/no-validation artifact; no private bundle "
            "read, no validation run by default)."
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
            "artifact; private validator requires an explicit /tmp path)"
        ),
    )
    ap.add_argument(
        "--allow-private-bundle",
        action="store_true",
        help=(
            "opt-in private D4b bundle validator; requires --input-bundle; "
            "output must go to /tmp only (NOT committed)"
        ),
    )
    ap.add_argument(
        "--input-bundle",
        type=Path,
        default=None,
        help=(
            "path to a private D4b bundle JSON (private validator only; "
            "requires --allow-private-bundle); never serialized into any "
            "committed artifact"
        ),
    )
    ap.add_argument(
        "--synthetic-harness-test",
        action="store_true",
        default=False,
        help=(
            "mark a private validator run as a synthetic/in-memory harness "
            "test (requires --allow-private-bundle); sets "
            "synthetic_harness_test=true, "
            "synthetic_bundle_validated_for_harness_only=true, "
            "local_private_bundle_validation_run=false, "
            "real_human_bundle_validated=false"
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

    # Private validator mode (any private arg present).
    if (
        args.allow_private_bundle
        or args.input_bundle is not None
        or args.synthetic_harness_test
    ):
        report, err = _run_private_validator_mode(
            allow_private=args.allow_private_bundle,
            input_path=args.input_bundle,
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
        # Compute the private report guard summary (fail-closed).
        # The output path itself is the only /tmp path; do NOT echo it
        # into the report. The guard checks for forbidden path
        # fragments (using lexical strings, not the resolved output
        # path itself, which is private).
        guard = _private_report_guard_summary(report)
        report_with_guard = dict(report)
        report_with_guard["private_report_guard"] = guard
        if guard.get("status") != "pass":
            print(
                "error: private D4f report guard failed; refusing to write",
                file=sys.stderr,
            )
            sys.exit(2)
        _write_json(args.out, report)
        # Do NOT print the exact /tmp output path.
        print(_private_success_message(report_with_guard))
        return

    # Public default mode (committed harness/no-validation artifact).
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
