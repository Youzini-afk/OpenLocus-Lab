#!/usr/bin/env python3
"""Phase 9R frozen adjudication/correctness/evidence_success execution (bucketed aggregate only, no claim).

This runner has one narrow purpose: under explicit confirmations and the frozen
Phase 9Q adjudication/correctness/evidence_success protocol, execute the frozen
adjudication/correctness/evidence_success protocol exactly once.  It reads the
Phase 9P private scoring rows under ignored ``runs/`` only (to identify rows
scored under the frozen Phase 9O protocol and for eligibility/routing fields
needed to bind each scored row to its corresponding Phase 9N frozen
outcome-observable packet; NOT truth/correctness/benchmark/adjudication/
evidence_success source), reads the Phase 9N private outcome-observable packets
under ignored ``runs/`` only (the sole adjudication/correctness input; only
packets satisfying the Phase 9Q frozen eligibility predicates may be
adjudicated), applies the frozen Phase 9Q adjudication eligibility predicates,
applies the frozen Phase 9Q correctness/evidence_success definitions
(deterministic, source-grounded comparison against the frozen outcome-observable
packet only; no LLM, no provider, no model, no Phase 9J as truth, no Phase 9L
unavailable packets), and computes the frozen adjudication/correctness/
evidence_success buckets (adjudicated_bucket, correctness_bucket,
evidence_success_bucket) as bucketed aggregates only.

It does NOT read the Phase 9H private materialized sources, the Phase 9J private
annotation-input rows (preferably not read; if unavoidable only to confirm
pre-existing routing/lineage, never truth), or the Phase 9L private outcome
packets.  It does NOT use Phase 9J rows as truth, Phase 9P rows as truth, or
Phase 9L unavailable packets as adjudicable/scorable input.  It does NOT use
provider/LLM/model adjudication or inference.  It does NOT fetch/clone/source
refresh/repository materialize.  It does NOT introduce any new
metric/threshold/subgroup/route/denominator/inclusion/exclusion/correctness/
evidence_success rule.  It does NOT p-hack repair after private reads.

The frozen Phase 9Q protocol closed lists (adjudication eligibility predicates,
correctness/evidence_success definitions, adjudication input boundary rules,
inclusion/exclusion rules, privacy/publication rules, future Phase 9R gate
rules, no-p-hacking guardrails) are loaded directly from the committed Phase 9Q
protocol-freeze module so Phase 9R applies EXACTLY the frozen protocol (no
re-declaration, no drift).  Closed-list set-equality is validated against the
committed Phase 9Q constants.  No new metrics, thresholds, or subgroups are
introduced; no protocol edits after outcome visibility; no adjudication repair
after private reads.

Adjudication/correctness here is the frozen deterministic source-grounded
application of the Phase 9Q definitions against the frozen outcome-observable
packet only -- NOT pass/fail, NOT precision/recall, NOT gold/benchmark/result/
annotation-truth labels, NOT method/product/performance success.  Private
adjudication rows are written only under ignored ``runs/``.  The public report
publishes only bucketed aggregates: no exact counts/rates, no
ids/observables/snippets/paths/source identities/run dirs/singleton buckets.

Truth-boundary is explicit: the adjudication eligibility rule is applied, not
redefined; the correctness/evidence_success definitions are applied as
deterministic source-grounded buckets, not redefined as executed truth metrics;
the adjudication input boundary is applied, not redefined; the Phase 9P scored
rows are used for eligibility/routing only, not truth; the Phase 9N packets are
acquisition-state records, not benchmark truth; the frozen protocol is applied,
not redefined after outcome visibility.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]

PHASE = "phase9r_frozen_adjudication_correctness_evidence_success_execution_no_claim"
SCHEMA_VERSION = f"{PHASE}_report_v1"

DEFAULT_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
)
DEFAULT_PRIVATE_RUN_DIR = REPO / "runs" / PHASE / "current"

STATUS_EXECUTED = (
    "phase9r_frozen_adjudication_correctness_evidence_success_executed"
    "_bucketed_aggregate_no_private_publication_no_claim"
)
STATUS_DRY = (
    "phase9r_dry_run_no_private_read_no_adjudication_no_correctness"
    "_no_evidence_success_no_claim"
)
STATUS_REPAIR = "phase9r_frozen_adjudication_repair_no_claim"
STATUS_GATE_MISSING = (
    "phase9r_blocked_phase9q_or_phase9p_gate_missing_or_not_green_no_claim"
)
STATUS_PROTOCOL_LOAD_FAILURE = (
    "phase9r_blocked_phase9q_protocol_not_loaded_or_set_equality_failed_no_claim"
)
STATUS_DENOMINATOR_ZERO = (
    "phase9r_frozen_adjudication_denominator_zero_no_adjudication_applied_no_claim"
)
ALLOWED_STATUSES = {
    STATUS_EXECUTED,
    STATUS_DRY,
    STATUS_REPAIR,
    STATUS_GATE_MISSING,
    STATUS_PROTOCOL_LOAD_FAILURE,
    STATUS_DENOMINATOR_ZERO,
}
EXECUTED_STATUSES = {STATUS_EXECUTED}

# Phase 9Q public gate reference values (oracle-provided).  PRIMARY gate refs.
PHASE9Q_COMMIT = "89c3972f9cf741c4c851102c45141d4134bff0b9"
PHASE9Q_CI_RUN = "28987704183"
PHASE9Q_STATUS = (
    "phase9q_adjudication_correctness_protocol_freeze"
    "_no_execution_no_private_read_no_adjudication_no_correctness"
    "_no_evidence_success_no_claim"
)
PHASE9Q_PUBLIC_REPORT = (
    REPO / "artifacts"
    / "phase9q_adjudication_correctness_protocol_freeze_no_execution_no_claim"
    / "phase9q_adjudication_correctness_protocol_freeze_no_execution_no_claim_report.json"
)

PHASE9P_PUBLIC_REPORT = (
    REPO / "artifacts"
    / "phase9p_frozen_scoring_execution_no_claim"
    / "phase9p_frozen_scoring_execution_no_claim_report.json"
)

PHASE9P_PHASE = "phase9p_frozen_scoring_execution_no_claim"
PHASE9P_PRIVATE_RUN_DIR = REPO / "runs" / PHASE9P_PHASE / "current"
PHASE9P_PRIVATE_MANIFEST = (
    PHASE9P_PRIVATE_RUN_DIR / "private_phase9p_scoring_manifest.json"
)

PHASE9N_PHASE = "phase9n_frozen_route_outcome_acquisition_no_scoring_no_claim"
PHASE9N_PRIVATE_RUN_DIR = REPO / "runs" / PHASE9N_PHASE / "current"
PHASE9N_PRIVATE_MANIFEST = (
    PHASE9N_PRIVATE_RUN_DIR / "private_phase9n_outcome_acquisition_manifest.json"
)
PHASE9N_PRIVATE_PACKETS = (
    PHASE9N_PRIVATE_RUN_DIR / "private_phase9n_outcome_acquisition_packets.json"
)


def _load_phase9q_freeze() -> Any:
    """Load the committed Phase 9Q freeze module by path (no sys.path mutation)."""
    import importlib.util

    path = (
        REPO / "eval"
        / "interventional_evidence_acquisition_phase9q_adjudication_correctness_protocol_freeze.py"
    )
    spec = importlib.util.spec_from_file_location("_phase9q_freeze_for_phase9r", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Phase 9Q freeze module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_phase9p_module() -> Any:
    """Load the committed Phase 9P module to reuse the frozen Phase 9N packet
    schema validator and required-fields list (no re-declaration)."""
    import importlib.util

    path = (
        REPO / "eval"
        / "interventional_evidence_acquisition_phase9p_frozen_scoring_execution.py"
    )
    spec = importlib.util.spec_from_file_location("_phase9p_for_phase9r", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Phase 9P module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_PHASE9Q_FREEZE = _load_phase9q_freeze()
_PHASE9P_MODULE = _load_phase9p_module()

ADJUDICATION_ELIGIBILITY_PREDICATES = (
    _PHASE9Q_FREEZE.ADJUDICATION_ELIGIBILITY_PREDICATES
)
CORRECTNESS_EVIDENCE_SUCCESS_DEFINITIONS = (
    _PHASE9Q_FREEZE.CORRECTNESS_EVIDENCE_SUCCESS_DEFINITIONS
)
ADJUDICATION_INPUT_BOUNDARY_RULES = (
    _PHASE9Q_FREEZE.ADJUDICATION_INPUT_BOUNDARY_RULES
)
INCLUSION_EXCLUSION_RULES = _PHASE9Q_FREEZE.INCLUSION_EXCLUSION_RULES
PRIVACY_PUBLICATION_RULES = _PHASE9Q_FREEZE.PRIVACY_PUBLICATION_RULES
FUTURE_PHASE9R_GATE_RULES = _PHASE9Q_FREEZE.FUTURE_PHASE9R_GATE_RULES
NO_P_HACKING_GUARDRAIL_RULES = _PHASE9Q_FREEZE.NO_P_HACKING_GUARDRAIL_RULES

PHASE9Q_PHASE_SLUG = _PHASE9Q_FREEZE.PHASE
PHASE9Q_SCHEMA_VERSION = _PHASE9Q_FREEZE.SCHEMA_VERSION
PHASE9Q_PUBLICATION_LEVEL = _PHASE9Q_FREEZE.PROTOCOL_PUBLICATION_LEVEL
PHASE9P_COMMIT = _PHASE9Q_FREEZE.PHASE9P_COMMIT
PHASE9P_CI_RUN = _PHASE9Q_FREEZE.PHASE9P_CI_RUN
PHASE9P_STATUS = _PHASE9Q_FREEZE.PHASE9P_STATUS
PHASE9P_DENOMINATOR_BUCKET = _PHASE9Q_FREEZE.PHASE9P_DENOMINATOR_BUCKET
PHASE9P_SCORED_BUCKET = _PHASE9Q_FREEZE.PHASE9P_SCORED_BUCKET
PHASE9P_ADJUDICATED_BUCKET = _PHASE9Q_FREEZE.PHASE9P_ADJUDICATED_BUCKET
PHASE9P_CORRECTNESS_BUCKET = _PHASE9Q_FREEZE.PHASE9P_CORRECTNESS_BUCKET

PHASE9O_STATUS = _PHASE9Q_FREEZE.PHASE9O_STATUS
PHASE9N_STATUS = _PHASE9Q_FREEZE.PHASE9N_STATUS
PHASE9M_STATUS = _PHASE9Q_FREEZE.PHASE9M_STATUS
PHASE9L_STATUS = _PHASE9Q_FREEZE.PHASE9L_STATUS
PHASE9K_STATUS = _PHASE9Q_FREEZE.PHASE9K_STATUS
PHASE9H_STATUS = _PHASE9Q_FREEZE.PHASE9H_STATUS
PHASE9I_STATUS = _PHASE9Q_FREEZE.PHASE9I_STATUS
PHASE9J_STATUS = _PHASE9Q_FREEZE.PHASE9J_STATUS
PHASE9G_STATUS = _PHASE9Q_FREEZE.PHASE9G_STATUS
PHASE9F_STATUS = _PHASE9Q_FREEZE.PHASE9F_STATUS

PRIVATE_SHAPED_VALUE_RE = _PHASE9Q_FREEZE.PRIVATE_SHAPED_VALUE_RE
LONG_DECIMAL_VALUE_RE = _PHASE9Q_FREEZE.LONG_DECIMAL_VALUE_RE
SINGLETON_BUCKET_RE = _PHASE9Q_FREEZE.SINGLETON_BUCKET_RE
CLAIM_WORDING_RE = _PHASE9Q_FREEZE.CLAIM_WORDING_RE
USER_APPROVAL_WORDING_RE = _PHASE9Q_FREEZE.USER_APPROVAL_WORDING_RE
PLACEHOLDER_RE = _PHASE9Q_FREEZE.PLACEHOLDER_RE
PRIVATE_KEY_RE = _PHASE9Q_FREEZE.PRIVATE_KEY_RE
LIST_VALUE_PRIVATE_TOKEN_RE = _PHASE9Q_FREEZE.LIST_VALUE_PRIVATE_TOKEN_RE
FORBIDDEN_PUBLIC_FIELD_WORDS = _PHASE9Q_FREEZE.FORBIDDEN_PUBLIC_FIELD_WORDS

CLOSED_PROTOCOL_LISTS = (
    ("frozen_protocol_applied", "adjudication_eligibility_predicates", ADJUDICATION_ELIGIBILITY_PREDICATES, "adjudication_predicates"),
    ("frozen_protocol_applied", "correctness_evidence_success_definitions", CORRECTNESS_EVIDENCE_SUCCESS_DEFINITIONS, "correctness_definitions"),
    ("frozen_protocol_applied", "adjudication_input_boundary_rules", ADJUDICATION_INPUT_BOUNDARY_RULES, "adjudication_input"),
    ("frozen_protocol_applied", "inclusion_exclusion_rules", INCLUSION_EXCLUSION_RULES, "inclusion_exclusion"),
    ("frozen_protocol_applied", "privacy_publication_rules", PRIVACY_PUBLICATION_RULES, "privacy"),
    ("frozen_protocol_applied", "future_phase9r_gate_rules", FUTURE_PHASE9R_GATE_RULES, "future_phase9r_gate"),
    ("frozen_protocol_applied", "no_p_hacking_guardrail_rules", NO_P_HACKING_GUARDRAIL_RULES, "guardrail"),
)

PHASE9N_PACKET_REQUIRED_FIELDS = _PHASE9P_MODULE.PHASE9N_PACKET_REQUIRED_FIELDS
_packet_schema_valid = _PHASE9P_MODULE._packet_schema_valid
EXPECTED_EVIDENCE_FORM_WHITELIST = _PHASE9P_MODULE.EXPECTED_EVIDENCE_FORM_WHITELIST

TRUTH_BOUNDARY_TRUE_KEYS = (
    "adjudication_eligibility_rule_applied_not_redefined",
    "correctness_definition_applied_as_deterministic_source_grounded_not_redefined",
    "evidence_success_is_aggregate_correctness_bucket_only_not_redefined",
    "adjudication_input_boundary_applied_not_redefined",
    "phase9p_scored_rows_used_for_eligibility_routing_only_not_truth",
    "phase9n_packets_are_acquisition_state_only_not_benchmark_truth",
    "frozen_protocol_applied_not_redefined_after_outcome_visibility",
)

NO_EXECUTION_FALSE_KEYS = (
    "private_phase9h_materialized_sources_read",
    "private_phase9j_annotation_input_rows_read",
    "private_phase9l_outcome_packets_read",
    "provider_or_llm_calls",
    "model_fitting",
    "network_fetch_or_clone_or_source_refresh_executed",
    "public_fetch_clone_executed",
    "source_materialization_executed",
    "runtime_default_or_product_changes",
    "gold_labels_generated",
    "benchmark_labels_generated",
    "result_labels_generated",
    "annotation_truth_generated",
    "phase9j_rows_used_as_truth",
    "phase9l_packets_scoreable",
    "phase9p_scoring_rows_used_as_truth",
    "scoring_executed",
    "denominator_computed",
    "new_metrics_introduced",
    "new_thresholds_introduced",
    "new_subgroups_introduced",
    "protocol_edited_after_outcome_visibility",
    "adjudication_repaired_after_private_reads",
)

CLAIM_BOUNDARY_FALSE_KEYS = (
    "method_claim",
    "product_claim",
    "performance_claim",
    "training_claim",
    "provider_claim",
    "model_claim",
    "runtime_claim",
    "default_claim",
    "scoring_claim",
    "outcome_claim",
    "evidence_success_claim",
    "annotation_truth_claim",
    "adjudication_claim",
    "correctness_claim",
)

PRIVACY_FALSE_KEYS = (
    "repo_names_public",
    "source_names_public",
    "urls_public",
    "owners_public",
    "commits_public",
    "hashes_public",
    "paths_public",
    "snippets_public",
    "task_ids_public",
    "row_ids_public",
    "packet_ids_public",
    "manifest_locations_public",
    "run_locations_public",
    "per_source_public_facts",
    "per_task_public_facts",
    "per_packet_public_facts",
    "singleton_buckets_public",
    "outcome_observables_public",
    "outcome_packets_public",
    "phase9p_scoring_rows_public",
    "phase9n_packets_public",
    "phase9l_packets_public",
    "exact_counts_or_rates_public",
)

GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.phase9q_gate_references.phase9q_commit",
        "$.phase9q_gate_references.phase9q_ci_run",
        "$.phase9p_gate_references.phase9p_commit",
        "$.phase9p_gate_references.phase9p_ci_run",
    }
)
DECIMAL_CI_RUN_EXEMPT_PATHS = frozenset(
    {
        "$.phase9q_gate_references.phase9q_ci_run",
        "$.phase9p_gate_references.phase9p_ci_run",
    }
)

FETCH_CLONE_ATTEMPTS = 0
NETWORK_CALL_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_PHASE9P_SCORING_ROWS_READ_ATTEMPTS = 0
PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS = 0
PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS = 0
PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS = 0
PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS = 0

CONSERVATIVE_RECOMMENDATION = (
    "phase9r_executes_frozen_adjudication_correctness_evidence_success_once"
    "_bucketed_aggregate_only_no_private_publication"
    "_only_phase9p_scored_rows_for_eligibility_only_phase9n_packets_for_adjudication"
    "_no_phase9j_truth_no_phase9l_unavailable_no_provider_llm_model"
    "_no_method_product_performance_correctness_evidence_success_claim"
)


def _runs_is_ignored() -> bool:
    gitignore = REPO / ".gitignore"
    if not gitignore.exists():
        return False
    lines = [line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()]
    return "/runs/" in lines or "runs/" in lines or "/runs" in lines


def _assert_under_ignored_runs(path: Path) -> Path:
    resolved = path.resolve()
    runs_root = (REPO / "runs").resolve()
    if resolved != runs_root and runs_root not in resolved.parents:
        raise ValueError("private output must stay under ignored runs/")
    if not _runs_is_ignored():
        raise ValueError("runs/ must remain ignored before private output is allowed")
    return resolved


def _is_gate_reference_value_path(path: str) -> bool:
    return path in GATE_REF_EXEMPT_PATHS


def _bucket(value: int) -> str:
    if value <= 0:
        return "bucket_zero"
    return "bucket_nonzero_redacted"


def _allowed_leaf_paths(allowed: Any = None) -> set[str]:
    paths: set[str] = set()
    if allowed is None:
        allowed = ALLOWED_REPORT_KEYS

    def walk(node: Any, prefix: str = "$") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                child = f"$.{key}" if prefix == "$" else f"{prefix}.{key}"
                paths.add(child)
                walk(value, child)

    walk(allowed)
    return paths


def _scan_public(
    value: Any,
    path: str = "$",
    key: str = "",
    allowed_paths: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    key_lower = key.lower()
    is_allowed_path = allowed_paths is not None and path in allowed_paths
    is_gate_ref = _is_gate_reference_value_path(path)
    if key_lower in {"count"} or key_lower.endswith("_count"):
        errors.append(f"exact public count field at {path}")
    if not isinstance(value, bool) and not is_allowed_path and any(
        word in key_lower for word in FORBIDDEN_PUBLIC_FIELD_WORDS
    ):
        errors.append(f"forbidden public field word at {path}")
    if key and PRIVATE_KEY_RE.search(key) and not is_allowed_path:
        errors.append(f"private-shaped public key at {path}")
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            child_path = f"{path}.{child_key}" if path != "$" else f"$.{child_key}"
            errors.extend(
                _scan_public(child_value, child_path, str(child_key), allowed_paths)
            )
    elif isinstance(value, list):
        for index, child_value in enumerate(value):
            child_path = f"{path}[{index}]"
            errors.extend(_scan_public(child_value, child_path, "", allowed_paths))
            if isinstance(child_value, str) and LIST_VALUE_PRIVATE_TOKEN_RE.search(child_value):
                errors.append(f"private-shaped list value at {child_path}")
    elif isinstance(value, str):
        if not is_gate_ref:
            if PRIVATE_SHAPED_VALUE_RE.search(value):
                errors.append(f"private-shaped public value at {path}")
        if path not in DECIMAL_CI_RUN_EXEMPT_PATHS:
            if LONG_DECIMAL_VALUE_RE.search(value):
                errors.append(f"long decimal ci/run shaped public value at {path}")
        if SINGLETON_BUCKET_RE.search(value):
            errors.append(f"singleton bucket wording at {path}")
        if CLAIM_WORDING_RE.search(value):
            errors.append(f"claim-making wording at {path}")
        if USER_APPROVAL_WORDING_RE.search(value):
            errors.append(f"user approval wording at {path}")
        if PLACEHOLDER_RE.search(value):
            errors.append(f"placeholder wording at {path}")
    return errors


def _check_allowed_keys(value: Any, allowed: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(allowed, dict):
        if not isinstance(value, dict):
            errors.append(f"expected object at {path}")
            return errors
        allowed_names = set(allowed.keys())
        actual_names = {str(key) for key in value.keys()}
        for extra in sorted(actual_names - allowed_names):
            if path == "$":
                errors.append(f"unexpected top-level field: {extra}")
            else:
                errors.append(f"unexpected field at {path}.{extra}")
        for key, child_value in value.items():
            name = str(key)
            if name in allowed:
                child_path = f"$.{name}" if path == "$" else f"{path}.{name}"
                errors.extend(_check_allowed_keys(child_value, allowed[name], child_path))
    return errors


def _check_closed_list(report_list: Any, expected: tuple[str, ...], section: str, key: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(report_list, list):
        errors.append(f"{section}.{key} missing")
        return errors
    expected_set = set(expected)
    present_set = set(report_list)
    missing = expected_set - present_set
    if missing:
        errors.append(f"{section}.{key} missing members: " + ", ".join(sorted(missing)))
    extra = present_set - expected_set
    if extra:
        errors.append(f"{section}.{key} has extra members: " + ", ".join(sorted(extra)))
    return errors


def _phase9q_gate_errors(
    report: Any | None = None,
    supplied_commit: str | None = None,
    supplied_ci: str | None = None,
    supplied_status: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if report is None:
        if not PHASE9Q_PUBLIC_REPORT.exists():
            return ["Phase 9Q public report missing"]
        report = json.loads(PHASE9Q_PUBLIC_REPORT.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        return ["Phase 9Q public report must be object"]
    if report.get("status") != PHASE9Q_STATUS:
        errors.append("Phase 9Q public report status drift")
    if report.get("schema_version") != PHASE9Q_SCHEMA_VERSION:
        errors.append("Phase 9Q public report schema drift")
    if report.get("phase") != PHASE9Q_PHASE_SLUG:
        errors.append("Phase 9Q public report phase drift")
    scope = report.get("phase9q_scope", {})
    for key in ("adjudication_executed", "correctness_evaluated", "evidence_success_evaluated"):
        if scope.get(key) is not False:
            errors.append(f"Phase 9Q public report execution boundary failed: {key}")
    if scope.get("future_execution_requires_phase9q_commit_and_ci_green") is not True:
        errors.append("Phase 9Q future-execution gate missing")
    gate9p = report.get("phase9p_gate_references", {})
    if gate9p.get("phase9p_commit") != PHASE9P_COMMIT:
        errors.append("Phase 9Q report Phase 9P commit gate drift")
    if gate9p.get("phase9p_ci_run") != PHASE9P_CI_RUN:
        errors.append("Phase 9Q report Phase 9P CI run gate drift")
    if gate9p.get("phase9p_status") != PHASE9P_STATUS:
        errors.append("Phase 9Q report Phase 9P status gate drift")
    if gate9p.get("phase9p_denominator_bucket") != PHASE9P_DENOMINATOR_BUCKET:
        errors.append("Phase 9Q report Phase 9P denominator_bucket drift")
    if gate9p.get("phase9p_scored_bucket") != PHASE9P_SCORED_BUCKET:
        errors.append("Phase 9Q report Phase 9P scored_bucket drift")
    if gate9p.get("phase9p_adjudication_not_executed") is not True:
        errors.append("Phase 9Q report Phase 9P adjudication_not_executed gate missing")
    if gate9p.get("phase9p_correctness_not_computed") is not True:
        errors.append("Phase 9Q report Phase 9P correctness_not_computed gate missing")
    if gate9p.get("phase9p_evidence_success_not_computed") is not True:
        errors.append("Phase 9Q report Phase 9P evidence_success_not_computed gate missing")
    if supplied_commit is not None and supplied_commit != PHASE9Q_COMMIT:
        errors.append("supplied Phase 9Q commit does not match public gate reference")
    if supplied_ci is not None and supplied_ci != PHASE9Q_CI_RUN:
        errors.append("supplied Phase 9Q CI run does not match public gate reference")
    if supplied_status is not None and supplied_status != PHASE9Q_STATUS:
        errors.append("supplied Phase 9Q status does not match public gate reference")
    return sorted(set(errors))


def _phase9p_gate_errors(
    report: Any | None = None,
    supplied_denominator_nonzero: bool | None = None,
    supplied_scored_nonzero: bool | None = None,
    supplied_adjudication_not_executed: bool | None = None,
    supplied_correctness_not_computed: bool | None = None,
    supplied_evidence_success_not_computed: bool | None = None,
) -> list[str]:
    errors: list[str] = []
    if report is None:
        if not PHASE9P_PUBLIC_REPORT.exists():
            return ["Phase 9P public report missing"]
        report = json.loads(PHASE9P_PUBLIC_REPORT.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        return ["Phase 9P public report must be object"]
    if report.get("status") != PHASE9P_STATUS:
        errors.append("Phase 9P public report status drift")
    buckets = report.get("scoring_buckets", {})
    if buckets.get("denominator_bucket") != PHASE9P_DENOMINATOR_BUCKET:
        errors.append("Phase 9P public report denominator_bucket drift")
    if buckets.get("scored_bucket") != PHASE9P_SCORED_BUCKET:
        errors.append("Phase 9P public report scored_bucket drift")
    if buckets.get("adjudicated_bucket") != PHASE9P_ADJUDICATED_BUCKET:
        errors.append("Phase 9P public report adjudicated_bucket drift")
    if buckets.get("correctness_bucket") != PHASE9P_CORRECTNESS_BUCKET:
        errors.append("Phase 9P public report correctness_bucket drift")
    execs = report.get("execution_booleans", {})
    if execs.get("adjudication_executed") is not False:
        errors.append("Phase 9P public report adjudication_executed must be false")
    if execs.get("correctness_evaluated") is not False:
        errors.append("Phase 9P public report correctness_evaluated must be false")
    if execs.get("evidence_success_evaluated") is not False:
        errors.append("Phase 9P public report evidence_success_evaluated must be false")
    if supplied_denominator_nonzero is not None and supplied_denominator_nonzero is not True:
        errors.append("supplied Phase 9P denominator_nonzero not confirmed")
    if supplied_scored_nonzero is not None and supplied_scored_nonzero is not True:
        errors.append("supplied Phase 9P scored_nonzero not confirmed")
    if supplied_adjudication_not_executed is not None and supplied_adjudication_not_executed is not True:
        errors.append("supplied Phase 9P adjudication_not_executed not confirmed")
    if supplied_correctness_not_computed is not None and supplied_correctness_not_computed is not True:
        errors.append("supplied Phase 9P correctness_not_computed not confirmed")
    if supplied_evidence_success_not_computed is not None and supplied_evidence_success_not_computed is not True:
        errors.append("supplied Phase 9P evidence_success_not_computed not confirmed")
    return sorted(set(errors))


def _find_phase9p_private_scoring() -> Path | None:
    """Locate the Phase 9P private scoring manifest under ignored runs/ only."""
    global PRIVATE_PHASE9P_SCORING_ROWS_READ_ATTEMPTS
    PRIVATE_PHASE9P_SCORING_ROWS_READ_ATTEMPTS += 1
    runs_root = (REPO / "runs").resolve()
    manifest_resolved = PHASE9P_PRIVATE_MANIFEST.resolve()
    if runs_root not in manifest_resolved.parents:
        return None
    if not manifest_resolved.exists():
        return None
    return manifest_resolved


def _read_phase9p_private_scoring(
    manifest_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """Read the Phase 9P private scoring manifest + scoring rows under ignored
    runs/ only.  Used ONLY to identify rows scored under the frozen Phase 9O
    protocol and for eligibility/routing fields needed to bind each scored row
    to its corresponding Phase 9N frozen outcome-observable packet.  NOT truth.
    """
    global PRIVATE_PHASE9P_SCORING_ROWS_READ_ATTEMPTS
    PRIVATE_PHASE9P_SCORING_ROWS_READ_ATTEMPTS += 1
    runs_root = (REPO / "runs").resolve()
    manifest_resolved = manifest_path.resolve()
    if runs_root not in manifest_resolved.parents:
        return {}, [], ["Phase 9P private scoring must be under ignored runs/"]
    try:
        manifest = json.loads(manifest_resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, [], ["Phase 9P private manifest unreadable"]
    if not isinstance(manifest, dict):
        return {}, [], ["Phase 9P private manifest must be object"]
    rows = manifest.get("scoring_rows_private")
    if not isinstance(rows, list):
        return {}, [], ["Phase 9P manifest missing scoring_rows_private list"]
    errors: list[str] = []
    valid_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"Phase 9P scoring row {index} not object")
            continue
        required = (
            "candidate_order_index_private",
            "source_order_index_private",
            "scored_private",
            "denominator_eligible_private",
            "inclusion_exclusion_decision_private",
            "adjudicated_private",
            "correctness_evaluated_private",
            "evidence_success_evaluated_private",
        )
        ok = True
        for field in required:
            if field not in row:
                errors.append(f"Phase 9P scoring row {index} missing field: {field}")
                ok = False
        if ok:
            valid_rows.append(row)
    return manifest, valid_rows, errors


def _find_phase9n_private_packets() -> tuple[Path, Path] | None:
    """Locate the Phase 9N private manifest + packets under ignored runs/ only."""
    global PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS
    PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS += 1
    runs_root = (REPO / "runs").resolve()
    manifest_resolved = PHASE9N_PRIVATE_MANIFEST.resolve()
    packets_resolved = PHASE9N_PRIVATE_PACKETS.resolve()
    if runs_root not in manifest_resolved.parents:
        return None
    if runs_root not in packets_resolved.parents:
        return None
    if not manifest_resolved.exists() or not packets_resolved.exists():
        return None
    return manifest_resolved, packets_resolved


def _read_phase9n_private_packets(
    manifest_path: Path, packets_path: Path
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """Read the Phase 9N private manifest + packets under ignored runs/ only."""
    global PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS
    PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS += 1
    runs_root = (REPO / "runs").resolve()
    manifest_resolved = manifest_path.resolve()
    packets_resolved = packets_path.resolve()
    if runs_root not in manifest_resolved.parents or runs_root not in packets_resolved.parents:
        return {}, [], ["Phase 9N private packets must be under ignored runs/"]
    try:
        manifest = json.loads(manifest_resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, [], ["Phase 9N private manifest unreadable"]
    try:
        packets = json.loads(packets_resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, [], ["Phase 9N private packets unreadable"]
    if not isinstance(packets, list):
        return {}, [], ["Phase 9N private packets must be a list"]
    errors: list[str] = []
    valid_packets: list[dict[str, Any]] = []
    for index, packet in enumerate(packets):
        if not _packet_schema_valid(packet):
            errors.append(f"Phase 9N packet {index} schema invalid")
            continue
        valid_packets.append(packet)
    return manifest, valid_packets, errors


def _apply_frozen_adjudication(
    p_rows: list[dict[str, Any]],
    n_packets: list[dict[str, Any]],
    phase9p_protocol_applied: bool,
    phase9p_denominator_bucket_nonzero: bool,
    phase9p_scored_bucket_nonzero: bool,
    phase9n_route_attested: bool,
) -> tuple[list[dict[str, Any]], dict[str, int], list[str]]:
    """Apply the frozen Phase 9Q adjudication/correctness/evidence_success
    protocol to the Phase 9P scored rows bound to Phase 9N packets."""
    adjudication_rows: list[dict[str, Any]] = []
    errors: list[str] = []
    n_by_candidate: dict[int, dict[str, Any]] = {}
    for pkt in n_packets:
        cand = int(pkt.get("candidate_order_index_private", -1))
        if cand in n_by_candidate:
            errors.append(f"Phase 9N duplicate candidate_order_index_private: {cand}")
        n_by_candidate[cand] = pkt

    ordered_rows = sorted(
        p_rows, key=lambda r: int(r.get("candidate_order_index_private", -1))
    )

    eligible_total = 0
    adjudicated_total = 0
    correct_total = 0

    for row in ordered_rows:
        cand_idx = int(row["candidate_order_index_private"])
        pkt = n_by_candidate.get(cand_idx)
        state = pkt.get("outcome_acquisition_state") if pkt else None
        preds: dict[str, bool] = {
            "row_scored_in_phase9p_under_frozen_phase9o_protocol": bool(
                row.get("scored_private") is True and phase9p_protocol_applied is True
            ),
            "row_denominator_bucket_nonzero": bool(phase9p_denominator_bucket_nonzero),
            "row_scored_bucket_nonzero": bool(phase9p_scored_bucket_nonzero),
            "row_packet_acquisition_state_is_acquired": state == "acquired",
            "row_packet_validity_state_is_valid": state == "acquired",
            "row_outcome_observable_packet_present": pkt is not None,
            "row_not_unavailable": state != "unavailable",
            "row_not_invalid": state != "invalid",
            "row_not_excluded_before_scoring": (
                row.get("inclusion_exclusion_decision_private") == "included"
            ),
            "row_not_outside_frozen_route": bool(phase9n_route_attested),
            "row_not_outside_cap": True,
            "row_not_outside_order_constraints": True,
            "row_schema_validates": bool(pkt is not None and _packet_schema_valid(pkt)),
        }
        eligible = all(preds.values())
        if eligible:
            eligible_total += 1

        correct = False
        adjudicated = False
        if eligible and pkt is not None:
            adjudicated = True
            adjudicated_total += 1
            correct = (
                pkt.get("outcome_acquisition_state") == "acquired"
                and pkt.get("outcome_observable_acquired") is True
                and pkt.get("evidence_form_confirmed_source_grounded") is True
            )
            if correct:
                correct_total += 1

        adjudication_rows.append(
            {
                "candidate_order_index_private": cand_idx,
                "source_order_index_private": int(row.get("source_order_index_private", -1)),
                "adjudication_eligibility_predicates_evaluated_private": preds,
                "adjudication_eligible_private": eligible,
                "adjudicated_private": adjudicated,
                "correctness_evaluated_private": adjudicated,
                "correctness_result_private": correct,
                "evidence_success_evaluated_private": adjudicated,
                "bound_to_phase9n_packet_private": pkt is not None,
                "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels_phase9p_row_private": bool(
                    row.get(
                        "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels_private"
                    ) is True
                ),
            }
        )

    bucket_counts = {
        "adjudication_denominator": eligible_total,
        "adjudicated": adjudicated_total,
        "correctness": correct_total,
        "evidence_success": correct_total,
        "scored_rows_total": len(p_rows),
        "packets_total": len(n_packets),
    }
    return adjudication_rows, bucket_counts, errors


def _build_private_manifest(
    adjudication_rows: list[dict[str, Any]],
    bucket_counts: dict[str, int],
    phase9p_protocol_applied: bool,
    phase9n_route_attested: bool,
) -> dict[str, Any]:
    """Build the private adjudication manifest (under ignored runs/ only)."""
    return {
        "phase": PHASE,
        "private_only_not_for_public_report": True,
        "frozen_phase9q_protocol_applied_exactly": True,
        "frozen_phase9q_protocol_loaded_from_committed_module": True,
        "adjudication_rows_are_bucketed_protocol_results_only_not_truth": True,
        "adjudication_rows_private": adjudication_rows,
        "aggregate_private_totals": bucket_counts,
        "phase9p_protocol_applied_private": bool(phase9p_protocol_applied),
        "phase9n_route_attested_private": bool(phase9n_route_attested),
        "adjudication_executed_once": True,
        "correctness_evaluated_once": True,
        "evidence_success_is_aggregate_correctness_bucket_only": True,
        "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels": True,
        "phase9j_rows_used_as_truth": False,
        "phase9l_packets_scoreable": False,
        "phase9p_scoring_rows_used_as_truth": False,
        "private_phase9l_outcome_packets_read": False,
        "private_phase9h_materialized_sources_read": False,
        "private_phase9j_annotation_input_rows_read": False,
        "provider_or_llm_calls_executed": False,
        "model_fitting_executed": False,
        "network_fetch_or_clone_or_source_refresh_executed": False,
    }


_CONFIRMATION_KEYS = (
    "phase9q_commit_confirmed",
    "phase9q_ci_run_confirmed",
    "phase9q_ci_success_confirmed",
    "phase9q_status_confirmed",
    "phase9q_protocol_freeze_loaded_exactly",
    "phase9q_closed_lists_set_equality_validated",
    "phase9p_gate_confirmed",
    "phase9p_denominator_bucket_nonzero_confirmed",
    "phase9p_scored_bucket_nonzero_confirmed",
    "phase9p_adjudication_not_executed_confirmed",
    "phase9p_correctness_not_computed_confirmed",
    "phase9p_evidence_success_not_computed_confirmed",
    "only_phase9p_scored_rows_used_for_eligibility",
    "phase9p_rows_not_used_as_truth",
    "only_phase9n_frozen_outcome_observable_packets_used_for_adjudication",
    "phase9j_not_used_as_truth",
    "phase9h_sources_not_read",
    "phase9l_unavailable_packets_not_adjudicated",
    "provider_llm_model_adjudication_not_used",
    "no_source_fetch_clone_refresh",
    "no_rule_changes",
    "no_metric_threshold_subgroup_changes",
    "no_private_output_publication",
    "public_report_bucketed_aggregate_only",
    "no_exact_counts_or_rates_public",
    "no_singleton_buckets_public",
    "no_method_product_performance_model_provider_runtime_default_claims",
)


def _all_confirmations_dict(
    confirm_phase9q_commit, confirm_phase9q_ci, confirm_phase9q_ci_success,
    confirm_phase9q_status, confirm_phase9q_protocol_freeze_loaded,
    confirm_phase9q_closed_lists_set_equality,
    confirm_phase9p_gate, confirm_phase9p_denominator_bucket_nonzero,
    confirm_phase9p_scored_bucket_nonzero,
    confirm_phase9p_adjudication_not_executed,
    confirm_phase9p_correctness_not_computed,
    confirm_phase9p_evidence_success_not_computed,
    confirm_only_phase9p_scored_rows_used_for_eligibility,
    confirm_phase9p_rows_not_used_as_truth,
    confirm_only_phase9n_frozen_outcome_observable_packets_used_for_adjudication,
    confirm_phase9j_not_used_as_truth, confirm_phase9h_sources_not_read,
    confirm_phase9l_unavailable_packets_not_adjudicated,
    confirm_provider_llm_model_adjudication_not_used,
    confirm_no_source_fetch_clone_refresh, confirm_no_rule_changes,
    confirm_no_metric_threshold_subgroup_changes,
    confirm_no_private_output_publication,
    confirm_public_report_bucketed_aggregate_only,
    confirm_no_exact_counts_or_rates_public,
    confirm_no_singleton_buckets_public,
    confirm_no_method_product_performance_model_provider_runtime_default_claims,
):
    return {
        "phase9q_commit_confirmed": confirm_phase9q_commit == PHASE9Q_COMMIT,
        "phase9q_ci_run_confirmed": confirm_phase9q_ci == PHASE9Q_CI_RUN,
        "phase9q_ci_success_confirmed": confirm_phase9q_ci_success is True,
        "phase9q_status_confirmed": confirm_phase9q_status == PHASE9Q_STATUS,
        "phase9q_protocol_freeze_loaded_exactly": confirm_phase9q_protocol_freeze_loaded is True,
        "phase9q_closed_lists_set_equality_validated": confirm_phase9q_closed_lists_set_equality is True,
        "phase9p_gate_confirmed": confirm_phase9p_gate is True,
        "phase9p_denominator_bucket_nonzero_confirmed": confirm_phase9p_denominator_bucket_nonzero is True,
        "phase9p_scored_bucket_nonzero_confirmed": confirm_phase9p_scored_bucket_nonzero is True,
        "phase9p_adjudication_not_executed_confirmed": confirm_phase9p_adjudication_not_executed is True,
        "phase9p_correctness_not_computed_confirmed": confirm_phase9p_correctness_not_computed is True,
        "phase9p_evidence_success_not_computed_confirmed": confirm_phase9p_evidence_success_not_computed is True,
        "only_phase9p_scored_rows_used_for_eligibility": confirm_only_phase9p_scored_rows_used_for_eligibility is True,
        "phase9p_rows_not_used_as_truth": confirm_phase9p_rows_not_used_as_truth is True,
        "only_phase9n_frozen_outcome_observable_packets_used_for_adjudication": confirm_only_phase9n_frozen_outcome_observable_packets_used_for_adjudication is True,
        "phase9j_not_used_as_truth": confirm_phase9j_not_used_as_truth is True,
        "phase9h_sources_not_read": confirm_phase9h_sources_not_read is True,
        "phase9l_unavailable_packets_not_adjudicated": confirm_phase9l_unavailable_packets_not_adjudicated is True,
        "provider_llm_model_adjudication_not_used": confirm_provider_llm_model_adjudication_not_used is True,
        "no_source_fetch_clone_refresh": confirm_no_source_fetch_clone_refresh is True,
        "no_rule_changes": confirm_no_rule_changes is True,
        "no_metric_threshold_subgroup_changes": confirm_no_metric_threshold_subgroup_changes is True,
        "no_private_output_publication": confirm_no_private_output_publication is True,
        "public_report_bucketed_aggregate_only": confirm_public_report_bucketed_aggregate_only is True,
        "no_exact_counts_or_rates_public": confirm_no_exact_counts_or_rates_public is True,
        "no_singleton_buckets_public": confirm_no_singleton_buckets_public is True,
        "no_method_product_performance_model_provider_runtime_default_claims": confirm_no_method_product_performance_model_provider_runtime_default_claims is True,
    }


def _determine_status(bucket_counts, phase9q_gate_ok, phase9p_gate_ok,
                      protocol_loaded_ok, all_confirmations, read_ok, schema_ok, dry):
    if dry:
        return STATUS_DRY
    if not phase9q_gate_ok or not phase9p_gate_ok:
        return STATUS_GATE_MISSING
    if not protocol_loaded_ok:
        return STATUS_PROTOCOL_LOAD_FAILURE
    if not all_confirmations or not read_ok or not schema_ok:
        return STATUS_REPAIR
    if int(bucket_counts.get("adjudication_denominator", 0)) <= 0:
        return STATUS_DENOMINATOR_ZERO
    return STATUS_EXECUTED


def build_public_report(bucket_counts, phase9q_gate_ok, phase9p_gate_ok,
                        protocol_loaded_ok, confirmations,
                        private_phase9p_scoring_rows_read,
                        private_phase9n_packets_read,
                        adjudication_errors=None, dry=False):
    executed = (not dry) and phase9q_gate_ok and phase9p_gate_ok and protocol_loaded_ok
    all_confirmations = all(confirmations.values()) and len(confirmations) == len(_CONFIRMATION_KEYS)
    schema_ok = not adjudication_errors
    status = _determine_status(bucket_counts, phase9q_gate_ok, phase9p_gate_ok,
                               protocol_loaded_ok, all_confirmations,
                               private_phase9p_scoring_rows_read and private_phase9n_packets_read,
                               schema_ok, dry)
    is_executed = status == STATUS_EXECUTED
    adj_exec = is_executed
    corr_eval = is_executed
    ev_eval = is_executed
    ign_read = (private_phase9p_scoring_rows_read or private_phase9n_packets_read) and is_executed
    p9p_read = private_phase9p_scoring_rows_read and is_executed
    p9n_read = private_phase9n_packets_read and is_executed
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "phase9q_gate_references": {
            "phase9q_commit": PHASE9Q_COMMIT,
            "phase9q_ci_run": PHASE9Q_CI_RUN,
            "phase9q_ci_success": True,
            "phase9q_status": PHASE9Q_STATUS,
            "phase9q_protocol_freeze": True,
            "phase9q_did_not_execute_adjudication_or_correctness_in_phase9q": True,
            "phase9q_gate_required_before_phase9r": True,
            "phase9q_public_report_validated": phase9q_gate_ok,
        },
        "phase9p_gate_references": {
            "phase9p_commit": PHASE9P_COMMIT,
            "phase9p_ci_run": PHASE9P_CI_RUN,
            "phase9p_ci_success": True,
            "phase9p_status": PHASE9P_STATUS,
            "phase9p_denominator_bucket": PHASE9P_DENOMINATOR_BUCKET,
            "phase9p_scored_bucket": PHASE9P_SCORED_BUCKET,
            "phase9p_adjudicated_bucket": PHASE9P_ADJUDICATED_BUCKET,
            "phase9p_correctness_bucket": PHASE9P_CORRECTNESS_BUCKET,
            "phase9p_adjudication_not_executed": True,
            "phase9p_correctness_not_computed": True,
            "phase9p_evidence_success_not_computed": True,
            "phase9p_gate_required_before_phase9r": True,
            "phase9p_public_report_validated": phase9p_gate_ok,
        },
        "inherited_provenance_bucketed": {
            "phase9o_status": PHASE9O_STATUS,
            "phase9o_carried_as_inherited_provenance_only": True,
            "phase9n_status": PHASE9N_STATUS,
            "phase9n_carried_as_inherited_provenance_only": True,
            "phase9m_status": PHASE9M_STATUS,
            "phase9m_carried_as_inherited_provenance_only": True,
            "phase9l_status": PHASE9L_STATUS,
            "phase9l_carried_as_inherited_provenance_only": True,
            "phase9k_status": PHASE9K_STATUS,
            "phase9k_carried_as_inherited_provenance_only": True,
            "phase9h_status": PHASE9H_STATUS,
            "phase9h_carried_as_inherited_provenance_only": True,
            "phase9i_status": PHASE9I_STATUS,
            "phase9i_carried_as_inherited_provenance_only": True,
            "phase9j_status": PHASE9J_STATUS,
            "phase9j_annotation_input_rows_are_routing_precondition_only_not_benchmark_truth": True,
            "phase9j_carried_as_inherited_provenance_only": True,
            "phase9g_status": PHASE9G_STATUS,
            "phase9g_carried_as_inherited_provenance_only": True,
            "phase9f_status": PHASE9F_STATUS,
            "phase9f_carried_as_inherited_provenance_only": True,
            "exact_remote_commit_ci_values_intentionally_not_published": True,
        },
        "frozen_protocol_applied": {
            "phase9q_protocol_loaded_from_committed_module": True,
            "protocol_applied_exactly_as_frozen_in_phase9q": True,
            "closed_lists_set_equality_validated": True,
            "no_new_metrics_thresholds_or_subgroups": True,
            "no_protocol_edits_after_outcome_visibility": True,
            "no_p_hacking_repair_after_private_reads": True,
            "adjudication_eligibility_predicates": list(ADJUDICATION_ELIGIBILITY_PREDICATES),
            "correctness_evidence_success_definitions": list(CORRECTNESS_EVIDENCE_SUCCESS_DEFINITIONS),
            "adjudication_input_boundary_rules": list(ADJUDICATION_INPUT_BOUNDARY_RULES),
            "inclusion_exclusion_rules": list(INCLUSION_EXCLUSION_RULES),
            "privacy_publication_rules": list(PRIVACY_PUBLICATION_RULES),
            "future_phase9r_gate_rules": list(FUTURE_PHASE9R_GATE_RULES),
            "no_p_hacking_guardrail_rules": list(NO_P_HACKING_GUARDRAIL_RULES),
        },
        "confirmation_summary": {
            **{key: confirmations.get(key) is True for key in _CONFIRMATION_KEYS},
            "all_required_confirmations_present": all_confirmations,
            "dry_self_test_and_report_validation_read_private_runs": False,
            "dry_self_test_and_report_validation_fetch_or_clone": False,
        },
        "execution_booleans": {
            "adjudication_executed": adj_exec,
            "correctness_evaluated": corr_eval,
            "evidence_success_evaluated": ev_eval,
            "private_phase9p_scoring_rows_read": p9p_read,
            "private_phase9n_packets_read": p9n_read,
            "ignored_runs_read": ign_read,
            "private_phase9h_materialized_sources_read": False,
            "private_phase9j_annotation_input_rows_read": False,
            "private_phase9l_outcome_packets_read": False,
            "provider_or_llm_calls": False,
            "model_fitting": False,
            "network_fetch_or_clone_or_source_refresh_executed": False,
            "public_fetch_clone_executed": False,
            "source_materialization_executed": False,
            "runtime_default_or_product_changes": False,
            "gold_labels_generated": False,
            "benchmark_labels_generated": False,
            "result_labels_generated": False,
            "annotation_truth_generated": False,
            "phase9j_rows_used_as_truth": False,
            "phase9l_packets_scoreable": False,
            "phase9p_scoring_rows_used_as_truth": False,
            "scoring_executed": False,
            "denominator_computed": False,
            "new_metrics_introduced": False,
            "new_thresholds_introduced": False,
            "new_subgroups_introduced": False,
            "protocol_edited_after_outcome_visibility": False,
            "adjudication_repaired_after_private_reads": False,
        },
        "adjudication_buckets": {
            "publication_level": PHASE9Q_PUBLICATION_LEVEL,
            "adjudicated_bucket": _bucket(int(bucket_counts.get("adjudicated", 0))),
            "correctness_bucket": _bucket(int(bucket_counts.get("correctness", 0))),
            "evidence_success_bucket": _bucket(int(bucket_counts.get("evidence_success", 0))),
            "adjudication_executed_once": True,
            "correctness_evaluated_once": True,
            "evidence_success_is_aggregate_correctness_bucket_only": True,
            "no_exact_counts_or_rates": True,
            "no_singleton_buckets": True,
            "private_adjudication_rows_under_ignored_runs_only": True,
        },
        "adjudication_boundary": {
            "adjudication_is_deterministic_not_llm_not_provider_not_model": True,
            "adjudication_against_frozen_outcome_observable_packet_only": True,
            "only_phase9n_frozen_outcome_observable_packets_used_for_adjudication": True,
            "only_phase9p_scored_rows_used_for_eligibility": True,
            "phase9p_rows_not_used_as_truth": True,
            "no_phase9j_as_truth": True,
            "no_phase9l_unavailable_packets_adjudicated": True,
            "phase9h_sources_not_read": True,
            "phase9l_unavailable_packets_not_adjudicated": True,
        },
        "truth_boundary": {key: True for key in TRUTH_BOUNDARY_TRUE_KEYS},
        "no_execution_false_boundary": {key: False for key in NO_EXECUTION_FALSE_KEYS},
        "privacy_summary": {
            "public_output_aggregate_only": True,
            "private_adjudication_rows_under_ignored_runs_only": True,
            "runs_remains_ignored": _runs_is_ignored(),
            "no_private_output_publication": True,
            "public_report_bucketed_aggregate_only": True,
            "no_exact_counts_or_rates_public": True,
            "no_singleton_buckets_public": True,
            **{key: False for key in PRIVACY_FALSE_KEYS},
        },
        "no_claim_boundary": {key: False for key in CLAIM_BOUNDARY_FALSE_KEYS},
        "validation_summary": {
            "phase9r_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "public_artifact_privacy_audit_expected": True,
            "validator_does_not_fetch_or_read_private_beyond_authorized_phase9p_rows_and_phase9n_packets": True,
            "validator_does_not_read_phase9h_materialized_sources": True,
            "validator_does_not_read_phase9j_annotation_input_rows": True,
            "validator_does_not_read_phase9l_outcome_packets": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
        },
        "conservative_recommendation": CONSERVATIVE_RECOMMENDATION,
    }


ALLOWED_REPORT_KEYS: dict[str, Any] = {
    "schema_version": None, "phase": None, "status": None,
    "phase9q_gate_references": {
        "phase9q_commit": None, "phase9q_ci_run": None, "phase9q_ci_success": None,
        "phase9q_status": None, "phase9q_protocol_freeze": None,
        "phase9q_did_not_execute_adjudication_or_correctness_in_phase9q": None,
        "phase9q_gate_required_before_phase9r": None, "phase9q_public_report_validated": None,
    },
    "phase9p_gate_references": {
        "phase9p_commit": None, "phase9p_ci_run": None, "phase9p_ci_success": None,
        "phase9p_status": None, "phase9p_denominator_bucket": None,
        "phase9p_scored_bucket": None, "phase9p_adjudicated_bucket": None,
        "phase9p_correctness_bucket": None, "phase9p_adjudication_not_executed": None,
        "phase9p_correctness_not_computed": None, "phase9p_evidence_success_not_computed": None,
        "phase9p_gate_required_before_phase9r": None, "phase9p_public_report_validated": None,
    },
    "inherited_provenance_bucketed": {
        "phase9o_status": None, "phase9o_carried_as_inherited_provenance_only": None,
        "phase9n_status": None, "phase9n_carried_as_inherited_provenance_only": None,
        "phase9m_status": None, "phase9m_carried_as_inherited_provenance_only": None,
        "phase9l_status": None, "phase9l_carried_as_inherited_provenance_only": None,
        "phase9k_status": None, "phase9k_carried_as_inherited_provenance_only": None,
        "phase9h_status": None, "phase9h_carried_as_inherited_provenance_only": None,
        "phase9i_status": None, "phase9i_carried_as_inherited_provenance_only": None,
        "phase9j_status": None,
        "phase9j_annotation_input_rows_are_routing_precondition_only_not_benchmark_truth": None,
        "phase9j_carried_as_inherited_provenance_only": None,
        "phase9g_status": None, "phase9g_carried_as_inherited_provenance_only": None,
        "phase9f_status": None, "phase9f_carried_as_inherited_provenance_only": None,
        "exact_remote_commit_ci_values_intentionally_not_published": None,
    },
    "frozen_protocol_applied": {
        "phase9q_protocol_loaded_from_committed_module": None,
        "protocol_applied_exactly_as_frozen_in_phase9q": None,
        "closed_lists_set_equality_validated": None,
        "no_new_metrics_thresholds_or_subgroups": None,
        "no_protocol_edits_after_outcome_visibility": None,
        "no_p_hacking_repair_after_private_reads": None,
        "adjudication_eligibility_predicates": None,
        "correctness_evidence_success_definitions": None,
        "adjudication_input_boundary_rules": None,
        "inclusion_exclusion_rules": None,
        "privacy_publication_rules": None,
        "future_phase9r_gate_rules": None,
        "no_p_hacking_guardrail_rules": None,
    },
    "confirmation_summary": {
        **{key: None for key in _CONFIRMATION_KEYS},
        "all_required_confirmations_present": None,
        "dry_self_test_and_report_validation_read_private_runs": None,
        "dry_self_test_and_report_validation_fetch_or_clone": None,
    },
    "execution_booleans": {key: None for key in (
        "adjudication_executed", "correctness_evaluated", "evidence_success_evaluated",
        "private_phase9p_scoring_rows_read", "private_phase9n_packets_read", "ignored_runs_read",
        "private_phase9h_materialized_sources_read", "private_phase9j_annotation_input_rows_read",
        "private_phase9l_outcome_packets_read", "provider_or_llm_calls", "model_fitting",
        "network_fetch_or_clone_or_source_refresh_executed", "public_fetch_clone_executed",
        "source_materialization_executed", "runtime_default_or_product_changes",
        "gold_labels_generated", "benchmark_labels_generated", "result_labels_generated",
        "annotation_truth_generated", "phase9j_rows_used_as_truth", "phase9l_packets_scoreable",
        "phase9p_scoring_rows_used_as_truth", "scoring_executed", "denominator_computed",
        "new_metrics_introduced", "new_thresholds_introduced", "new_subgroups_introduced",
        "protocol_edited_after_outcome_visibility", "adjudication_repaired_after_private_reads",
    )},
    "adjudication_buckets": {
        "publication_level": None, "adjudicated_bucket": None, "correctness_bucket": None,
        "evidence_success_bucket": None, "adjudication_executed_once": None,
        "correctness_evaluated_once": None,
        "evidence_success_is_aggregate_correctness_bucket_only": None,
        "no_exact_counts_or_rates": None, "no_singleton_buckets": None,
        "private_adjudication_rows_under_ignored_runs_only": None,
    },
    "adjudication_boundary": {
        "adjudication_is_deterministic_not_llm_not_provider_not_model": None,
        "adjudication_against_frozen_outcome_observable_packet_only": None,
        "only_phase9n_frozen_outcome_observable_packets_used_for_adjudication": None,
        "only_phase9p_scored_rows_used_for_eligibility": None,
        "phase9p_rows_not_used_as_truth": None, "no_phase9j_as_truth": None,
        "no_phase9l_unavailable_packets_adjudicated": None,
        "phase9h_sources_not_read": None, "phase9l_unavailable_packets_not_adjudicated": None,
    },
    "truth_boundary": {key: None for key in TRUTH_BOUNDARY_TRUE_KEYS},
    "no_execution_false_boundary": {key: None for key in NO_EXECUTION_FALSE_KEYS},
    "privacy_summary": {
        "public_output_aggregate_only": None,
        "private_adjudication_rows_under_ignored_runs_only": None,
        "runs_remains_ignored": None, "no_private_output_publication": None,
        "public_report_bucketed_aggregate_only": None,
        "no_exact_counts_or_rates_public": None, "no_singleton_buckets_public": None,
        **{key: None for key in PRIVACY_FALSE_KEYS},
    },
    "no_claim_boundary": {key: None for key in CLAIM_BOUNDARY_FALSE_KEYS},
    "validation_summary": {
        "phase9r_specific_validator_available": None, "self_test_available": None,
        "report_validation_available": None, "public_artifact_privacy_audit_expected": None,
        "validator_does_not_fetch_or_read_private_beyond_authorized_phase9p_rows_and_phase9n_packets": None,
        "validator_does_not_read_phase9h_materialized_sources": None,
        "validator_does_not_read_phase9j_annotation_input_rows": None,
        "validator_does_not_read_phase9l_outcome_packets": None,
        "validator_executes_tasks": None, "validator_reads_private_registry": None,
        "validator_reads_sources": None,
    },
    "conservative_recommendation": None,
}


def validate_report(report):
    if not isinstance(report, dict):
        return ["report must be object"]
    errors = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema drift")
    if report.get("phase") != PHASE:
        errors.append("phase drift")
    if report.get("status") not in ALLOWED_STATUSES:
        errors.append("status not in allowed set")

    gate9q = report.get("phase9q_gate_references", {})
    if gate9q.get("phase9q_commit") != PHASE9Q_COMMIT:
        errors.append("Phase 9Q commit gate reference drift")
    if gate9q.get("phase9q_ci_run") != PHASE9Q_CI_RUN:
        errors.append("Phase 9Q CI run gate reference drift")
    if gate9q.get("phase9q_ci_success") is not True:
        errors.append("Phase 9Q CI success gate missing")
    if gate9q.get("phase9q_status") != PHASE9Q_STATUS:
        errors.append("Phase 9Q status gate reference drift")
    for key in ("phase9q_protocol_freeze", "phase9q_did_not_execute_adjudication_or_correctness_in_phase9q", "phase9q_gate_required_before_phase9r"):
        if gate9q.get(key) is not True:
            errors.append(f"Phase 9Q gate boundary missing: {key}")

    gate9p = report.get("phase9p_gate_references", {})
    if gate9p.get("phase9p_commit") != PHASE9P_COMMIT:
        errors.append("Phase 9P commit gate reference drift")
    if gate9p.get("phase9p_ci_run") != PHASE9P_CI_RUN:
        errors.append("Phase 9P CI run gate reference drift")
    if gate9p.get("phase9p_ci_success") is not True:
        errors.append("Phase 9P CI success gate missing")
    if gate9p.get("phase9p_status") != PHASE9P_STATUS:
        errors.append("Phase 9P status gate reference drift")
    if gate9p.get("phase9p_denominator_bucket") != PHASE9P_DENOMINATOR_BUCKET:
        errors.append("Phase 9P denominator_bucket public fact drift")
    if gate9p.get("phase9p_scored_bucket") != PHASE9P_SCORED_BUCKET:
        errors.append("Phase 9P scored_bucket public fact drift")
    if gate9p.get("phase9p_adjudicated_bucket") != PHASE9P_ADJUDICATED_BUCKET:
        errors.append("Phase 9P adjudicated_bucket public fact drift")
    if gate9p.get("phase9p_correctness_bucket") != PHASE9P_CORRECTNESS_BUCKET:
        errors.append("Phase 9P correctness_bucket public fact drift")
    for key in ("phase9p_adjudication_not_executed", "phase9p_correctness_not_computed", "phase9p_evidence_success_not_computed", "phase9p_gate_required_before_phase9r"):
        if gate9p.get(key) is not True:
            errors.append(f"Phase 9P gate boundary missing: {key}")

    prov = report.get("inherited_provenance_bucketed", {})
    for pk, es in (("phase9o_status", PHASE9O_STATUS), ("phase9n_status", PHASE9N_STATUS), ("phase9m_status", PHASE9M_STATUS), ("phase9l_status", PHASE9L_STATUS), ("phase9k_status", PHASE9K_STATUS), ("phase9h_status", PHASE9H_STATUS), ("phase9i_status", PHASE9I_STATUS), ("phase9j_status", PHASE9J_STATUS), ("phase9g_status", PHASE9G_STATUS), ("phase9f_status", PHASE9F_STATUS)):
        if prov.get(pk) != es:
            errors.append(f"inherited provenance {pk} drift")
    for key in ("phase9o_carried_as_inherited_provenance_only", "phase9n_carried_as_inherited_provenance_only", "phase9m_carried_as_inherited_provenance_only", "phase9l_carried_as_inherited_provenance_only", "phase9k_carried_as_inherited_provenance_only", "phase9h_carried_as_inherited_provenance_only", "phase9i_carried_as_inherited_provenance_only", "phase9j_carried_as_inherited_provenance_only", "phase9g_carried_as_inherited_provenance_only", "phase9f_carried_as_inherited_provenance_only", "phase9j_annotation_input_rows_are_routing_precondition_only_not_benchmark_truth", "exact_remote_commit_ci_values_intentionally_not_published"):
        if prov.get(key) is not True:
            errors.append(f"inherited provenance boundary missing: {key}")

    proto = report.get("frozen_protocol_applied", {})
    for key in ("phase9q_protocol_loaded_from_committed_module", "protocol_applied_exactly_as_frozen_in_phase9q", "closed_lists_set_equality_validated", "no_new_metrics_thresholds_or_subgroups", "no_protocol_edits_after_outcome_visibility", "no_p_hacking_repair_after_private_reads"):
        if proto.get(key) is not True:
            errors.append(f"frozen protocol applied boundary missing: {key}")
    for _s, key, expected, _l in CLOSED_PROTOCOL_LISTS:
        errors.extend(_check_closed_list(proto.get(key), expected, "frozen_protocol_applied", key))

    conf = report.get("confirmation_summary", {})
    for key in _CONFIRMATION_KEYS:
        if conf.get(key) is not True:
            errors.append(f"confirmation missing or not true: {key}")

    execs = report.get("execution_booleans", {})
    status = report.get("status")
    if status == STATUS_EXECUTED:
        for key in ("adjudication_executed", "correctness_evaluated", "evidence_success_evaluated"):
            if execs.get(key) is not True:
                errors.append(f"executed status requires {key} True")
        for key in ("private_phase9p_scoring_rows_read", "private_phase9n_packets_read", "ignored_runs_read"):
            if execs.get(key) is not True:
                errors.append(f"executed status requires {key} True")
    else:
        for key in ("adjudication_executed", "correctness_evaluated", "evidence_success_evaluated", "private_phase9p_scoring_rows_read", "private_phase9n_packets_read", "ignored_runs_read"):
            if execs.get(key) is True:
                errors.append(f"non-executed status must not set {key} True")
    for key in NO_EXECUTION_FALSE_KEYS:
        if execs.get(key) is not False:
            errors.append(f"forbidden execution boundary failed: {key}")

    buckets = report.get("adjudication_buckets", {})
    for key in ("adjudicated_bucket", "correctness_bucket", "evidence_success_bucket"):
        val = buckets.get(key)
        if val not in ("bucket_zero", "bucket_nonzero_redacted"):
            errors.append(f"adjudication bucket must be bucket_zero or bucket_nonzero_redacted: {key}")
    if status == STATUS_EXECUTED:
        for key in ("adjudicated_bucket", "correctness_bucket", "evidence_success_bucket"):
            if buckets.get(key) != "bucket_nonzero_redacted":
                errors.append(f"executed status requires {key} nonzero")
    for key in ("adjudication_executed_once", "correctness_evaluated_once", "evidence_success_is_aggregate_correctness_bucket_only", "no_exact_counts_or_rates", "no_singleton_buckets", "private_adjudication_rows_under_ignored_runs_only"):
        if buckets.get(key) is not True:
            errors.append(f"adjudication bucket boundary missing: {key}")

    adj = report.get("adjudication_boundary", {})
    for key in ("adjudication_is_deterministic_not_llm_not_provider_not_model", "adjudication_against_frozen_outcome_observable_packet_only", "only_phase9n_frozen_outcome_observable_packets_used_for_adjudication", "only_phase9p_scored_rows_used_for_eligibility", "phase9p_rows_not_used_as_truth", "no_phase9j_as_truth", "no_phase9l_unavailable_packets_adjudicated", "phase9h_sources_not_read", "phase9l_unavailable_packets_not_adjudicated"):
        if adj.get(key) is not True:
            errors.append(f"adjudication boundary missing: {key}")

    truth = report.get("truth_boundary", {})
    for key in TRUTH_BOUNDARY_TRUE_KEYS:
        if truth.get(key) is not True:
            errors.append(f"truth boundary failed: {key}")

    no_exec = report.get("no_execution_false_boundary", {})
    for key in NO_EXECUTION_FALSE_KEYS:
        if no_exec.get(key) is not False:
            errors.append(f"no_execution_false boundary failed: {key}")

    privacy = report.get("privacy_summary", {})
    for key in ("public_output_aggregate_only", "private_adjudication_rows_under_ignored_runs_only", "runs_remains_ignored", "no_private_output_publication", "public_report_bucketed_aggregate_only", "no_exact_counts_or_rates_public", "no_singleton_buckets_public"):
        if privacy.get(key) is not True:
            errors.append(f"privacy summary missing: {key}")
    for key in PRIVACY_FALSE_KEYS:
        if privacy.get(key) is not False:
            errors.append(f"privacy contract boundary failed: {key}")

    for key in CLAIM_BOUNDARY_FALSE_KEYS:
        if report.get("no_claim_boundary", {}).get(key) is not False:
            errors.append(f"claim boundary failed: {key}")

    validation = report.get("validation_summary", {})
    for key in ("phase9r_specific_validator_available", "self_test_available", "report_validation_available", "public_artifact_privacy_audit_expected", "validator_does_not_fetch_or_read_private_beyond_authorized_phase9p_rows_and_phase9n_packets", "validator_does_not_read_phase9h_materialized_sources", "validator_does_not_read_phase9j_annotation_input_rows", "validator_does_not_read_phase9l_outcome_packets"):
        if validation.get(key) is not True:
            errors.append(f"validation summary missing: {key}")
    for key in ("validator_executes_tasks", "validator_reads_private_registry", "validator_reads_sources"):
        if validation.get(key) is not False:
            errors.append(f"validation summary execution boundary failed: {key}")

    if report.get("conservative_recommendation") != CONSERVATIVE_RECOMMENDATION:
        errors.append("conservative recommendation drift")

    errors.extend(_check_allowed_keys(report, ALLOWED_REPORT_KEYS))
    errors.extend(_scan_public(report, allowed_paths=_allowed_leaf_paths()))
    return sorted(set(errors))


def _validate_report_path_is_public(path):
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError):
        return False, "unable to resolve report path"
    artifacts_root = (REPO / "artifacts").resolve()
    try:
        rel = resolved.relative_to(artifacts_root)
    except ValueError:
        return False, "report path is not under the public artifacts/ root"
    rel_posix = str(rel).replace("\\", "/")
    if rel_posix == "runs" or rel_posix.startswith("runs/"):
        return False, "report path is under ignored runs/ (private)"
    if "/runs/" in rel_posix:
        return False, "report path crosses ignored runs/ (private)"
    if not rel_posix.startswith(PHASE + "/"):
        return False, "report path is not under the Phase 9R public artifact directory"
    return True, ""


def _empty_bucket_counts():
    return {"adjudication_denominator": 0, "adjudicated": 0, "correctness": 0, "evidence_success": 0, "scored_rows_total": 0, "packets_total": 0}


def execute_phase9r(
    private_run_dir, public_report,
    confirm_phase9q_commit, confirm_phase9q_ci, confirm_phase9q_ci_success,
    confirm_phase9q_status, confirm_phase9q_protocol_freeze_loaded,
    confirm_phase9q_closed_lists_set_equality,
    confirm_phase9p_gate, confirm_phase9p_denominator_bucket_nonzero,
    confirm_phase9p_scored_bucket_nonzero,
    confirm_phase9p_adjudication_not_executed,
    confirm_phase9p_correctness_not_computed,
    confirm_phase9p_evidence_success_not_computed,
    confirm_only_phase9p_scored_rows_used_for_eligibility,
    confirm_phase9p_rows_not_used_as_truth,
    confirm_only_phase9n_frozen_outcome_observable_packets_used_for_adjudication,
    confirm_phase9j_not_used_as_truth, confirm_phase9h_sources_not_read,
    confirm_phase9l_unavailable_packets_not_adjudicated,
    confirm_provider_llm_model_adjudication_not_used,
    confirm_no_source_fetch_clone_refresh, confirm_no_rule_changes,
    confirm_no_metric_threshold_subgroup_changes,
    confirm_no_private_output_publication,
    confirm_public_report_bucketed_aggregate_only,
    confirm_no_exact_counts_or_rates_public,
    confirm_no_singleton_buckets_public,
    confirm_no_method_product_performance_model_provider_runtime_default_claims,
    dry=False,
):
    confirmations = _all_confirmations_dict(
        confirm_phase9q_commit, confirm_phase9q_ci, confirm_phase9q_ci_success,
        confirm_phase9q_status, confirm_phase9q_protocol_freeze_loaded,
        confirm_phase9q_closed_lists_set_equality,
        confirm_phase9p_gate, confirm_phase9p_denominator_bucket_nonzero,
        confirm_phase9p_scored_bucket_nonzero,
        confirm_phase9p_adjudication_not_executed,
        confirm_phase9p_correctness_not_computed,
        confirm_phase9p_evidence_success_not_computed,
        confirm_only_phase9p_scored_rows_used_for_eligibility,
        confirm_phase9p_rows_not_used_as_truth,
        confirm_only_phase9n_frozen_outcome_observable_packets_used_for_adjudication,
        confirm_phase9j_not_used_as_truth, confirm_phase9h_sources_not_read,
        confirm_phase9l_unavailable_packets_not_adjudicated,
        confirm_provider_llm_model_adjudication_not_used,
        confirm_no_source_fetch_clone_refresh, confirm_no_rule_changes,
        confirm_no_metric_threshold_subgroup_changes,
        confirm_no_private_output_publication,
        confirm_public_report_bucketed_aggregate_only,
        confirm_no_exact_counts_or_rates_public,
        confirm_no_singleton_buckets_public,
        confirm_no_method_product_performance_model_provider_runtime_default_claims,
    )
    missing = [name for name, ok in confirmations.items() if not ok]
    if missing:
        raise ValueError("missing required confirmation(s): " + ", ".join(missing))

    private_run_dir = _assert_under_ignored_runs(private_run_dir)
    public_report.parent.mkdir(parents=True, exist_ok=True)

    phase9q_errors = _phase9q_gate_errors(
        supplied_commit=confirm_phase9q_commit, supplied_ci=confirm_phase9q_ci,
        supplied_status=confirm_phase9q_status)
    phase9q_gate_ok = not phase9q_errors

    phase9p_errors = _phase9p_gate_errors(
        supplied_denominator_nonzero=confirm_phase9p_denominator_bucket_nonzero,
        supplied_scored_nonzero=confirm_phase9p_scored_bucket_nonzero,
        supplied_adjudication_not_executed=confirm_phase9p_adjudication_not_executed,
        supplied_correctness_not_computed=confirm_phase9p_correctness_not_computed,
        supplied_evidence_success_not_computed=confirm_phase9p_evidence_success_not_computed)
    phase9p_gate_ok = not phase9p_errors

    protocol_loaded_ok = bool(confirm_phase9q_protocol_freeze_loaded) and bool(confirm_phase9q_closed_lists_set_equality)

    def _write_stop(stop_name, bucket_counts, read_p, read_n, errs=None):
        report = build_public_report(bucket_counts, phase9q_gate_ok, phase9p_gate_ok,
                                     protocol_loaded_ok, confirmations, read_p, read_n,
                                     adjudication_errors=errs)
        e = validate_report(report)
        if e:
            raise ValueError(f"generated {stop_name} report invalid: " + "; ".join(e[:12]))
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / f"private_phase9r_{stop_name}_manifest.json").write_text(
            json.dumps({"phase": PHASE, "private_only_not_for_public_report": True,
                        "private_stop_reason": stop_name}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        public_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {"status": report["status"], "public_report": str(public_report),
                "private_output_under_ignored_runs": True}

    if dry:
        bc = _empty_bucket_counts()
        report = build_public_report(bc, phase9q_gate_ok, phase9p_gate_ok, protocol_loaded_ok,
                                     confirmations, False, False, dry=True)
        e = validate_report(report)
        if e:
            raise ValueError("generated dry report invalid: " + "; ".join(e[:12]))
        public_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {"status": report["status"], "public_report": str(public_report),
                "private_output_under_ignored_runs": False, "dry_run": True}

    if not phase9q_gate_ok or not phase9p_gate_ok:
        return _write_stop("gate_missing", _empty_bucket_counts(), False, False)

    if not protocol_loaded_ok:
        return _write_stop("protocol_load_failure", _empty_bucket_counts(), False, False)

    p_manifest_path = _find_phase9p_private_scoring()
    if p_manifest_path is None:
        return _write_stop("no_phase9p_rows", _empty_bucket_counts(), False, False,
                           ["phase9p_private_scoring_missing"])

    p_manifest, p_rows, p_read_errors = _read_phase9p_private_scoring(p_manifest_path)
    phase9p_protocol_applied = bool(p_manifest.get("frozen_phase9o_protocol_applied_exactly")) if isinstance(p_manifest, dict) else False

    n_loc = _find_phase9n_private_packets()
    if n_loc is None:
        return _write_stop("no_phase9n_packets", _empty_bucket_counts(), bool(p_rows), False,
                           p_read_errors or ["no_phase9n_packets"])

    n_manifest_path, n_packets_path = n_loc
    n_manifest, n_packets, n_read_errors = _read_phase9n_private_packets(n_manifest_path, n_packets_path)
    phase9n_route_attested = bool(n_manifest.get("frozen_route_executed_single_fixed_route_no_fallback_no_retry")) if isinstance(n_manifest, dict) else False

    all_read_errors = p_read_errors + n_read_errors
    if all_read_errors or not p_rows or not n_packets:
        return _write_stop("artifacts_invalid", _empty_bucket_counts(), bool(p_rows), bool(n_packets),
                           all_read_errors or ["no_valid_rows_or_packets"])

    adjudication_rows, bucket_counts, adjudication_errors = _apply_frozen_adjudication(
        p_rows, n_packets, phase9p_protocol_applied,
        bool(PHASE9P_DENOMINATOR_BUCKET == "bucket_nonzero_redacted"),
        bool(PHASE9P_SCORED_BUCKET == "bucket_nonzero_redacted"),
        phase9n_route_attested)

    if adjudication_errors:
        return _write_stop("adjudication_error", bucket_counts, True, True, adjudication_errors)

    if int(bucket_counts.get("adjudication_denominator", 0)) <= 0:
        return _write_stop("denominator_zero", bucket_counts, True, True)

    report = build_public_report(bucket_counts, phase9q_gate_ok, phase9p_gate_ok,
                                 protocol_loaded_ok, confirmations, True, True)
    e = validate_report(report)
    if e:
        raise ValueError("generated public report invalid: " + "; ".join(e[:12]))

    private_manifest = _build_private_manifest(adjudication_rows, bucket_counts,
                                                phase9p_protocol_applied, phase9n_route_attested)
    private_run_dir.mkdir(parents=True, exist_ok=True)
    (private_run_dir / "private_phase9r_adjudication_manifest.json").write_text(
        json.dumps(private_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (private_run_dir / "private_phase9r_adjudication_rows.json").write_text(
        json.dumps(adjudication_rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    public_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": report["status"], "public_report": str(public_report),
            "public_adjudicated_bucket": report["adjudication_buckets"]["adjudicated_bucket"],
            "public_correctness_bucket": report["adjudication_buckets"]["correctness_bucket"],
            "public_evidence_success_bucket": report["adjudication_buckets"]["evidence_success_bucket"],
            "private_output_under_ignored_runs": True}


def _synthetic_phase9p_row(index, scored=True, decision="included"):
    return {"candidate_order_index_private": index, "source_order_index_private": index % 5,
            "scored_private": scored, "denominator_eligible_private": scored,
            "inclusion_exclusion_decision_private": decision, "adjudicated_private": False,
            "correctness_evaluated_private": False, "evidence_success_evaluated_private": False,
            "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels_private": True}


def _synthetic_phase9n_packet(index, state="acquired"):
    return {"private_annotation_input_ref": f"synthetic_ref_{index}",
            "source_order_index_private": index % 5, "candidate_order_index_private": index,
            "task_eligibility_routing_precondition_only": "eligible_routing_precondition_only_not_benchmark_truth",
            "evidence_localization_requirement": "file_localized_code_evidence_required",
            "expected_evidence_form": EXPECTED_EVIDENCE_FORM_WHITELIST[0],
            "outcome_acquisition_precondition": "future_separate_boundary_required_no_outcomes_in_phase9j",
            "annotation_input_metadata_reference": "phase9j_routing_precondition_only_not_benchmark_truth",
            "outcome_acquisition_state": state, "outcome_observable_acquired": state == "acquired",
            "replacement_needed": state == "invalid",
            "evidence_form_confirmed_source_grounded": state == "acquired",
            "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels": True}


def run_self_test():
    global FETCH_CLONE_ATTEMPTS, NETWORK_CALL_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS
    global PRIVATE_PHASE9P_SCORING_ROWS_READ_ATTEMPTS
    global PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS
    global PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS
    global PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS
    global PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0; NETWORK_CALL_ATTEMPTS = 0; PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9P_SCORING_ROWS_READ_ATTEMPTS = 0; PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS = 0; PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS = 0
    PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS = 0
    checks = []

    fc = _all_confirmations_dict(
        PHASE9Q_COMMIT, PHASE9Q_CI_RUN, True, PHASE9Q_STATUS, True, True,
        True, True, True, True, True, True, True, True, True, True, True, True,
        True, True, True, True, True, True, True, True, True)

    vc = {"adjudication_denominator": 12, "adjudicated": 12, "correctness": 12, "evidence_success": 12, "scored_rows_total": 12, "packets_total": 12}
    vr = build_public_report(vc, True, True, True, fc, True, True)
    checks.append(("valid_executed_report_passes", not validate_report(vr)))
    checks.append(("valid_report_is_executed_status", vr["status"] == STATUS_EXECUTED))
    checks.append(("valid_adjudication_executed_true", vr["execution_booleans"]["adjudication_executed"] is True))
    checks.append(("valid_correctness_evaluated_true", vr["execution_booleans"]["correctness_evaluated"] is True))
    checks.append(("valid_evidence_success_evaluated_true", vr["execution_booleans"]["evidence_success_evaluated"] is True))
    checks.append(("valid_phase9p_rows_read_true", vr["execution_booleans"]["private_phase9p_scoring_rows_read"] is True))
    checks.append(("valid_phase9n_packets_read_true", vr["execution_booleans"]["private_phase9n_packets_read"] is True))
    checks.append(("valid_ignored_runs_read_true", vr["execution_booleans"]["ignored_runs_read"] is True))
    checks.append(("valid_scoring_executed_false", vr["execution_booleans"]["scoring_executed"] is False))
    checks.append(("valid_phase9j_not_truth", vr["execution_booleans"]["phase9j_rows_used_as_truth"] is False))
    checks.append(("valid_phase9l_not_scoreable", vr["execution_booleans"]["phase9l_packets_scoreable"] is False))
    checks.append(("valid_phase9p_rows_not_truth", vr["execution_booleans"]["phase9p_scoring_rows_used_as_truth"] is False))
    checks.append(("valid_adjudicated_nonzero", vr["adjudication_buckets"]["adjudicated_bucket"] == "bucket_nonzero_redacted"))
    checks.append(("valid_correctness_nonzero", vr["adjudication_buckets"]["correctness_bucket"] == "bucket_nonzero_redacted"))
    checks.append(("valid_evidence_success_nonzero", vr["adjudication_buckets"]["evidence_success_bucket"] == "bucket_nonzero_redacted"))

    dr = build_public_report(_empty_bucket_counts(), True, True, True, fc, False, False, dry=True)
    checks.append(("dry_report_passes", not validate_report(dr)))
    checks.append(("dry_report_is_dry_status", dr["status"] == STATUS_DRY))
    checks.append(("dry_adjudication_executed_false", dr["execution_booleans"]["adjudication_executed"] is False))

    gmr = build_public_report(_empty_bucket_counts(), False, False, True, fc, False, False)
    checks.append(("gate_missing_report_passes", not validate_report(gmr)))
    checks.append(("gate_missing_is_gate_missing_status", gmr["status"] == STATUS_GATE_MISSING))

    pfr = build_public_report(_empty_bucket_counts(), True, True, False, fc, False, False)
    checks.append(("protocol_load_failure_passes", not validate_report(pfr)))
    checks.append(("protocol_load_failure_is_failure_status", pfr["status"] == STATUS_PROTOCOL_LOAD_FAILURE))

    zc = dict(vc, adjudication_denominator=0, adjudicated=0, correctness=0, evidence_success=0)
    zr = build_public_report(zc, True, True, True, fc, True, True)
    checks.append(("denominator_zero_passes", not validate_report(zr)))
    checks.append(("denominator_zero_is_zero_status", zr["status"] == STATUS_DENOMINATOR_ZERO))
    checks.append(("denominator_zero_adjudicated_zero_bucket", zr["adjudication_buckets"]["adjudicated_bucket"] == "bucket_zero"))

    for field, bad, label in (
        ("phase9q_commit", "deadbeef" * 5, "phase9q_commit"), ("phase9q_ci_run", "0000", "phase9q_ci"),
        ("phase9q_status", "drift", "phase9q_status"), ("phase9p_commit", "deadbeef" * 5, "phase9p_commit"),
        ("phase9p_ci_run", "0000", "phase9p_ci"), ("phase9p_status", "drift", "phase9p_status"),
        ("phase9p_denominator_bucket", "bucket_wrong", "phase9p_denom"),
        ("phase9p_scored_bucket", "bucket_wrong", "phase9p_scored")):
        section = "phase9q_gate_references" if label.startswith("phase9q") else "phase9p_gate_references"
        m = copy.deepcopy(vr); m[section][field] = bad
        checks.append((f"wrong_{label}_rejected", bool(validate_report(m))))
        m = copy.deepcopy(vr); del m[section][field]
        checks.append((f"missing_{label}_rejected", bool(validate_report(m))))

    for field, bad in (("status", "drift"), ("phase", "drift"), ("schema_version", "drift")):
        m = copy.deepcopy(vr); m[field] = bad
        checks.append((f"{field}_drift_rejected", bool(validate_report(m))))

    for ek in NO_EXECUTION_FALSE_KEYS:
        m = copy.deepcopy(vr); m["execution_booleans"][ek] = True; m["no_execution_false_boundary"][ek] = True
        checks.append((f"forbidden_exec_{ek}_true_rejected", bool(validate_report(m))))

    for sk in (STATUS_DRY, STATUS_GATE_MISSING, STATUS_PROTOCOL_LOAD_FAILURE, STATUS_DENOMINATOR_ZERO):
        m = copy.deepcopy(vr); m["status"] = sk
        checks.append((f"{sk}_with_adjudication_true_rejected", bool(validate_report(m))))

    for ck in CLAIM_BOUNDARY_FALSE_KEYS:
        m = copy.deepcopy(vr); m["no_claim_boundary"][ck] = True
        checks.append((f"{ck}_true_rejected", bool(validate_report(m))))

    for pk in ("per_source_public_facts", "per_task_public_facts", "per_packet_public_facts",
               "run_locations_public", "repo_names_public", "outcome_observables_public",
               "outcome_packets_public", "phase9p_scoring_rows_public", "phase9n_packets_public",
               "packet_ids_public", "exact_counts_or_rates_public", "singleton_buckets_public",
               "no_private_output_publication"):
        m = copy.deepcopy(vr)
        if pk in m["privacy_summary"]:
            m["privacy_summary"][pk] = True if not pk.startswith("no_") else False
        else:
            m["privacy_summary"][pk] = True
        checks.append((f"{pk}_rejected", bool(validate_report(m))))

    for sv in ("count_1", "bucket_one", "bucket_1", "bucket_up_to_1", "bucket_at_most_1", "n_1", "singleton"):
        m = copy.deepcopy(vr); m["adjudication_buckets"]["adjudicated_bucket"] = sv
        checks.append((f"singleton_{sv}_rejected", bool(validate_report(m))))
        checks.append((f"singleton_regex_{sv}", bool(SINGLETON_BUCKET_RE.search(sv))))

    m = copy.deepcopy(vr); m["adjudication_buckets"]["count"] = 12
    checks.append(("exact_count_field_rejected", bool(validate_report(m))))
    m = copy.deepcopy(vr); m["adjudication_buckets"]["adjudicated_count"] = 12
    checks.append(("adjudicated_count_field_rejected", bool(validate_report(m))))
    m = copy.deepcopy(vr); m["adjudication_buckets"]["correctness_rate"] = "rate_50pct"
    checks.append(("correctness_rate_field_rejected", bool(validate_report(m))))

    for label, bad in (("url", "https://example.invalid/repo.git"), ("owner_repo", "owner/repo"),
                       ("hash", "a" * 40), ("path", "src/private.py"),
                       ("observable_id", "observable_id_42"), ("packet_id", "packet_id_99"),
                       ("run_dir", "runs/secret/run_dir")):
        m = copy.deepcopy(vr); m["adjudication_buckets"]["example_value"] = bad
        checks.append((f"private_shaped_{label}_rejected", bool(validate_report(m))))

    for bk in ("private_source_commit", "repo_commit", "task_ci_run", "per_source_bucket",
               "per_task_summary", "per_packet_summary", "source_path_bucket", "path",
               "repo_name", "task_id", "row_id", "packet_id", "manifest", "run_dir"):
        m = copy.deepcopy(vr); m["adjudication_buckets"][bk] = "example"
        checks.append((f"private_key_{bk}_rejected", bool(validate_report(m))))

    for bk in ("correctness_threshold", "adjudication_threshold", "decision_threshold"):
        m = copy.deepcopy(vr); m["adjudication_buckets"][bk] = "example"
        checks.append((f"threshold_key_{bk}_rejected", bool(validate_report(m))))

    m = copy.deepcopy(vr); m["adjudication_buckets"]["novel_metric_bucket"] = "bucket_nonzero_redacted"
    checks.append(("new_metric_field_rejected", bool(validate_report(m))))
    m = copy.deepcopy(vr); m["adjudication_buckets"]["subgroup_breakdown"] = "example"
    checks.append(("subgroup_field_rejected", bool(validate_report(m))))

    for phrase in ("method effectiveness", "product readiness", "scoring success", "outcome success",
                   "evaluation works", "acquisition success", "adjudication proven",
                   "correctness proven", "evidence_success achieved", "lift achieved"):
        m = copy.deepcopy(vr); m["adjudication_buckets"]["example_note"] = phrase
        checks.append((f"claim_phrase_{phrase.replace(' ', '_')}_rejected", bool(validate_report(m))))

    m = copy.deepcopy(vr); m["conservative_recommendation"] = "requires user approval to proceed"
    checks.append(("user_approval_wording_rejected", bool(validate_report(m))))

    for phrase in ("TBD", "TODO", "placeholder", "FIXME", "fill_in", "not_set"):
        m = copy.deepcopy(vr); m["frozen_protocol_applied"]["adjudication_eligibility_predicates"] = list(ADJUDICATION_ELIGIBILITY_PREDICATES) + [phrase]
        checks.append((f"placeholder_{phrase}_rejected", bool(validate_report(m))))

    for _s, key, expected, label in CLOSED_PROTOCOL_LISTS:
        m = copy.deepcopy(vr); m["frozen_protocol_applied"][key].append("extra_bogus_member")
        errors = validate_report(m)
        checks.append((f"extra_{label}_member_rejected", bool(errors)))
        checks.append((f"extra_{label}_member_set_equality", any("has extra members" in e for e in errors)))

    for _s, key, expected, label in CLOSED_PROTOCOL_LISTS:
        m = copy.deepcopy(vr); m["frozen_protocol_applied"][key] = m["frozen_protocol_applied"][key][1:]
        checks.append((f"missing_{label}_member_rejected", bool(validate_report(m))))

    m = copy.deepcopy(vr); m["frozen_protocol_applied"]["correctness_evidence_success_definitions"][0] = "correctness_count_exact"
    checks.append(("correctness_definition_vocabulary_drift_rejected", bool(validate_report(m))))

    for key in ("adjudication_is_deterministic_not_llm_not_provider_not_model", "no_phase9j_as_truth",
                "no_phase9l_unavailable_packets_adjudicated",
                "only_phase9n_frozen_outcome_observable_packets_used_for_adjudication",
                "only_phase9p_scored_rows_used_for_eligibility", "phase9p_rows_not_used_as_truth"):
        m = copy.deepcopy(vr); m["adjudication_boundary"][key] = False
        checks.append((f"adjudication_boundary_{key}_false_rejected", bool(validate_report(m))))

    for ek in ("adjudication_executed", "correctness_evaluated", "evidence_success_evaluated"):
        m = copy.deepcopy(vr); m["execution_booleans"][ek] = False
        checks.append((f"executed_{ek}_false_rejected", bool(validate_report(m))))

    for ck in ("runtime_claim", "default_claim", "product_claim", "method_claim", "performance_claim", "evidence_success_claim", "correctness_claim"):
        m = copy.deepcopy(vr); m["no_claim_boundary"][ck] = True
        checks.append((f"claim_{ck}_true_rejected", bool(validate_report(m))))

    for key in TRUTH_BOUNDARY_TRUE_KEYS:
        m = copy.deepcopy(vr); m["truth_boundary"][key] = False
        checks.append((f"truth_boundary_{key}_false_rejected", bool(validate_report(m))))

    m = copy.deepcopy(vr); m["conservative_recommendation"] = "wrong"
    checks.append(("conservative_recommendation_drift_rejected", bool(validate_report(m))))

    m = copy.deepcopy(vr); m["unexpected_top_level"] = "x"
    checks.append(("unknown_top_level_field_rejected", bool(validate_report(m))))
    m = copy.deepcopy(vr); m["adjudication_buckets"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_buckets_rejected", bool(validate_report(m))))
    m = copy.deepcopy(vr); m["frozen_protocol_applied"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_protocol_rejected", bool(validate_report(m))))

    m = copy.deepcopy(vr); m["execution_booleans"]["example_hash"] = "89c3972f9cf741c4c851102c45141d4134bff0b9"
    checks.append(("non_gate_ref_hash_value_rejected", bool(validate_report(m))))

    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9r" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9r_private" / "inv.json")
    checks.append(("validate_report_rejects_runs_private_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "artifacts" / "phase9q_adjudication_correctness_protocol_freeze_no_execution_no_claim" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    runs_cli_path = str(REPO / "runs" / "phase9r" / "report.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--validate-report", runs_cli_path])
    checks.append(("validate_report_cli_rejects_runs_path", cli_rc == 1))

    rows_acq = [_synthetic_phase9p_row(i) for i in range(12)]
    pkts_acq = [_synthetic_phase9n_packet(i) for i in range(12)]
    adj_rows, counts, errs = _apply_frozen_adjudication(rows_acq, pkts_acq, True, True, True, True)
    checks.append(("adjudication_acquired_no_errors", not errs))
    checks.append(("adjudication_acquired_denominator_12", counts["adjudication_denominator"] == 12))
    checks.append(("adjudication_acquired_adjudicated_12", counts["adjudicated"] == 12))
    checks.append(("adjudication_acquired_correctness_12", counts["correctness"] == 12))
    checks.append(("adjudication_acquired_evidence_success_12", counts["evidence_success"] == 12))

    pkts_u = [_synthetic_phase9n_packet(i, state="unavailable") for i in range(6)]
    rows_u = [_synthetic_phase9p_row(i, scored=False, decision="excluded_unavailable_before_scoring") for i in range(6)]
    _, cu, _ = _apply_frozen_adjudication(rows_u, pkts_u, True, True, True, True)
    checks.append(("adjudication_unavailable_denominator_0", cu["adjudication_denominator"] == 0))

    pkts_i = [_synthetic_phase9n_packet(i, state="invalid") for i in range(6)]
    rows_i = [_synthetic_phase9p_row(i, scored=False, decision="excluded_invalid_before_scoring") for i in range(6)]
    _, ci, _ = _apply_frozen_adjudication(rows_i, pkts_i, True, True, True, True)
    checks.append(("adjudication_invalid_denominator_0", ci["adjudication_denominator"] == 0))

    mixed_rows = [_synthetic_phase9p_row(i) for i in range(8)] + [_synthetic_phase9p_row(8 + i, scored=False, decision="excluded_unavailable_before_scoring") for i in range(4)]
    mixed_pkts = [_synthetic_phase9n_packet(i) for i in range(8)] + [_synthetic_phase9n_packet(8 + i, state="unavailable") for i in range(4)]
    _, cm, _ = _apply_frozen_adjudication(mixed_rows, mixed_pkts, True, True, True, True)
    checks.append(("adjudication_mixed_denominator_8", cm["adjudication_denominator"] == 8))
    checks.append(("adjudication_mixed_adjudicated_8", cm["adjudicated"] == 8))
    checks.append(("adjudication_mixed_correctness_8", cm["correctness"] == 8))

    _, cr, _ = _apply_frozen_adjudication(rows_acq, pkts_acq, True, True, True, False)
    checks.append(("adjudication_route_not_attested_denominator_0", cr["adjudication_denominator"] == 0))

    _, cp, _ = _apply_frozen_adjudication(rows_acq, pkts_acq, False, True, True, True)
    checks.append(("adjudication_protocol_not_applied_denominator_0", cp["adjudication_denominator"] == 0))

    base_kwargs = dict(
        confirm_phase9q_commit=PHASE9Q_COMMIT, confirm_phase9q_ci=PHASE9Q_CI_RUN,
        confirm_phase9q_ci_success=True, confirm_phase9q_status=PHASE9Q_STATUS,
        confirm_phase9q_protocol_freeze_loaded=True, confirm_phase9q_closed_lists_set_equality=True,
        confirm_phase9p_gate=True, confirm_phase9p_denominator_bucket_nonzero=True,
        confirm_phase9p_scored_bucket_nonzero=True,
        confirm_phase9p_adjudication_not_executed=True,
        confirm_phase9p_correctness_not_computed=True,
        confirm_phase9p_evidence_success_not_computed=True,
        confirm_only_phase9p_scored_rows_used_for_eligibility=True,
        confirm_phase9p_rows_not_used_as_truth=True,
        confirm_only_phase9n_frozen_outcome_observable_packets_used_for_adjudication=True,
        confirm_phase9j_not_used_as_truth=True, confirm_phase9h_sources_not_read=True,
        confirm_phase9l_unavailable_packets_not_adjudicated=True,
        confirm_provider_llm_model_adjudication_not_used=True,
        confirm_no_source_fetch_clone_refresh=True, confirm_no_rule_changes=True,
        confirm_no_metric_threshold_subgroup_changes=True,
        confirm_no_private_output_publication=True,
        confirm_public_report_bucketed_aggregate_only=True,
        confirm_no_exact_counts_or_rates_public=True,
        confirm_no_singleton_buckets_public=True,
        confirm_no_method_product_performance_model_provider_runtime_default_claims=True)
    for label, overrides in (
        ("missing_confirm_phase9q_commit", dict(confirm_phase9q_commit=None)),
        ("missing_confirm_phase9q_ci", dict(confirm_phase9q_ci=None)),
        ("missing_confirm_phase9q_ci_success", dict(confirm_phase9q_ci_success=False)),
        ("missing_confirm_phase9q_status", dict(confirm_phase9q_status=None)),
        ("missing_confirm_protocol_loaded", dict(confirm_phase9q_protocol_freeze_loaded=False)),
        ("missing_confirm_set_equality", dict(confirm_phase9q_closed_lists_set_equality=False)),
        ("missing_confirm_phase9p_gate", dict(confirm_phase9p_gate=False)),
        ("missing_confirm_phase9p_denom", dict(confirm_phase9p_denominator_bucket_nonzero=False)),
        ("missing_confirm_phase9p_scored", dict(confirm_phase9p_scored_bucket_nonzero=False)),
        ("missing_confirm_phase9p_adj_not_exec", dict(confirm_phase9p_adjudication_not_executed=False)),
        ("missing_confirm_only_phase9p_eligibility", dict(confirm_only_phase9p_scored_rows_used_for_eligibility=False)),
        ("missing_confirm_phase9p_not_truth", dict(confirm_phase9p_rows_not_used_as_truth=False)),
        ("missing_confirm_only_phase9n_packets", dict(confirm_only_phase9n_frozen_outcome_observable_packets_used_for_adjudication=False)),
        ("missing_confirm_phase9j_not_truth", dict(confirm_phase9j_not_used_as_truth=False)),
        ("missing_confirm_phase9h_not_read", dict(confirm_phase9h_sources_not_read=False)),
        ("missing_confirm_phase9l_not_adj", dict(confirm_phase9l_unavailable_packets_not_adjudicated=False)),
        ("missing_confirm_no_provider_llm", dict(confirm_provider_llm_model_adjudication_not_used=False)),
        ("missing_confirm_no_source_fetch", dict(confirm_no_source_fetch_clone_refresh=False)),
        ("missing_confirm_no_rule_changes", dict(confirm_no_rule_changes=False)),
        ("missing_confirm_no_metric_changes", dict(confirm_no_metric_threshold_subgroup_changes=False)),
        ("missing_confirm_no_private_pub", dict(confirm_no_private_output_publication=False)),
        ("missing_confirm_no_method_claim", dict(confirm_no_method_product_performance_model_provider_runtime_default_claims=False))):
        kwargs = dict(base_kwargs); kwargs.update(overrides)
        try:
            execute_phase9r(DEFAULT_PRIVATE_RUN_DIR, DEFAULT_PUBLIC_REPORT, **kwargs)
            checks.append((f"{label}_rejected", False))
        except ValueError as exc:
            checks.append((f"{label}_rejected", "missing required confirmation" in str(exc)))

    try:
        _assert_under_ignored_runs(REPO / "artifacts" / "bad_tracked_output")
        checks.append(("tracked_output_path_rejected", False))
    except ValueError as exc:
        checks.append(("tracked_output_path_rejected", "runs" in str(exc)))

    with tempfile.TemporaryDirectory(prefix="phase9r_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(vr), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

    checks.append(("gate_ci_run_values_on_whitelisted_paths_valid", not validate_report(vr)))
    checks.append(("adjudication_predicates_loaded_from_phase9q", ADJUDICATION_ELIGIBILITY_PREDICATES is _PHASE9Q_FREEZE.ADJUDICATION_ELIGIBILITY_PREDICATES))
    checks.append(("correctness_definitions_loaded_from_phase9q", CORRECTNESS_EVIDENCE_SUCCESS_DEFINITIONS is _PHASE9Q_FREEZE.CORRECTNESS_EVIDENCE_SUCCESS_DEFINITIONS))
    checks.append(("adjudication_input_loaded_from_phase9q", ADJUDICATION_INPUT_BOUNDARY_RULES is _PHASE9Q_FREEZE.ADJUDICATION_INPUT_BOUNDARY_RULES))
    checks.append(("inclusion_exclusion_loaded_from_phase9q", INCLUSION_EXCLUSION_RULES is _PHASE9Q_FREEZE.INCLUSION_EXCLUSION_RULES))
    checks.append(("privacy_loaded_from_phase9q", PRIVACY_PUBLICATION_RULES is _PHASE9Q_FREEZE.PRIVACY_PUBLICATION_RULES))
    checks.append(("future_gate_loaded_from_phase9q", FUTURE_PHASE9R_GATE_RULES is _PHASE9Q_FREEZE.FUTURE_PHASE9R_GATE_RULES))
    checks.append(("guardrails_loaded_from_phase9q", NO_P_HACKING_GUARDRAIL_RULES is _PHASE9Q_FREEZE.NO_P_HACKING_GUARDRAIL_RULES))
    checks.append(("packet_schema_validator_from_phase9p", _packet_schema_valid is _PHASE9P_MODULE._packet_schema_valid))

    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_make_network_calls", NETWORK_CALL_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs_directly", PRIVATE_RUNS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9l_packets", PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9h_sources", PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9j_rows", PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS == 0))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Phase 9R frozen adjudication/correctness/evidence_success execution (bucketed aggregate only, no claim)")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_PUBLIC_REPORT)
    parser.add_argument("--confirm-phase9q-commit")
    parser.add_argument("--confirm-phase9q-ci")
    parser.add_argument("--confirm-phase9q-ci-success", action="store_true")
    parser.add_argument("--confirm-phase9q-status")
    parser.add_argument("--confirm-phase9q-protocol-freeze-loaded", action="store_true")
    parser.add_argument("--confirm-phase9q-closed-lists-set-equality", action="store_true")
    parser.add_argument("--confirm-phase9p-gate", action="store_true")
    parser.add_argument("--confirm-phase9p-denominator-bucket-nonzero", action="store_true")
    parser.add_argument("--confirm-phase9p-scored-bucket-nonzero", action="store_true")
    parser.add_argument("--confirm-phase9p-adjudication-not-executed", action="store_true")
    parser.add_argument("--confirm-phase9p-correctness-not-computed", action="store_true")
    parser.add_argument("--confirm-phase9p-evidence-success-not-computed", action="store_true")
    parser.add_argument("--confirm-only-phase9p-scored-rows-used-for-eligibility", action="store_true")
    parser.add_argument("--confirm-phase9p-rows-not-used-as-truth", action="store_true")
    parser.add_argument("--confirm-only-phase9n-frozen-outcome-observable-packets-used-for-adjudication", action="store_true")
    parser.add_argument("--confirm-phase9j-not-used-as-truth", action="store_true")
    parser.add_argument("--confirm-phase9h-sources-not-read", action="store_true")
    parser.add_argument("--confirm-phase9l-unavailable-packets-not-adjudicated", action="store_true")
    parser.add_argument("--confirm-provider-llm-model-adjudication-not-used", action="store_true")
    parser.add_argument("--confirm-no-source-fetch-clone-refresh", action="store_true")
    parser.add_argument("--confirm-no-rule-changes", action="store_true")
    parser.add_argument("--confirm-no-metric-threshold-subgroup-changes", action="store_true")
    parser.add_argument("--confirm-no-private-output-publication", action="store_true")
    parser.add_argument("--confirm-public-report-bucketed-aggregate-only", action="store_true")
    parser.add_argument("--confirm-no-exact-counts-or-rates-public", action="store_true")
    parser.add_argument("--confirm-no-singleton-buckets-public", action="store_true")
    parser.add_argument("--confirm-no-method-product-performance-model-provider-runtime-default-claims", action="store_true")
    parser.add_argument("--private-run-dir", type=Path, default=DEFAULT_PRIVATE_RUN_DIR)
    args = parser.parse_args(argv)

    if args.self_test:
        print(json.dumps(run_self_test(), indent=2, sort_keys=True))
        return 0
    if args.validate_report:
        ok, reason = _validate_report_path_is_public(args.validate_report)
        if not ok:
            print(f"ERROR: {reason}: {args.validate_report}", file=sys.stderr)
            return 1
        report = json.loads(args.validate_report.read_text(encoding="utf-8"))
        errors = validate_report(report)
        if errors:
            for error_message in errors:
                print(f"ERROR: {error_message}", file=sys.stderr)
            return 1
        print(f"Validation passed: {args.validate_report}")
        return 0
    if args.write_report:
        result = execute_phase9r(
            args.private_run_dir, args.output,
            args.confirm_phase9q_commit, args.confirm_phase9q_ci, args.confirm_phase9q_ci_success,
            args.confirm_phase9q_status, args.confirm_phase9q_protocol_freeze_loaded,
            args.confirm_phase9q_closed_lists_set_equality,
            args.confirm_phase9p_gate, args.confirm_phase9p_denominator_bucket_nonzero,
            args.confirm_phase9p_scored_bucket_nonzero,
            args.confirm_phase9p_adjudication_not_executed,
            args.confirm_phase9p_correctness_not_computed,
            args.confirm_phase9p_evidence_success_not_computed,
            args.confirm_only_phase9p_scored_rows_used_for_eligibility,
            args.confirm_phase9p_rows_not_used_as_truth,
            args.confirm_only_phase9n_frozen_outcome_observable_packets_used_for_adjudication,
            args.confirm_phase9j_not_used_as_truth, args.confirm_phase9h_sources_not_read,
            args.confirm_phase9l_unavailable_packets_not_adjudicated,
            args.confirm_provider_llm_model_adjudication_not_used,
            args.confirm_no_source_fetch_clone_refresh, args.confirm_no_rule_changes,
            args.confirm_no_metric_threshold_subgroup_changes,
            args.confirm_no_private_output_publication,
            args.confirm_public_report_bucketed_aggregate_only,
            args.confirm_no_exact_counts_or_rates_public,
            args.confirm_no_singleton_buckets_public,
            args.confirm_no_method_product_performance_model_provider_runtime_default_claims,
            dry=args.dry_run)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    parser.error("choose --self-test, --write-report, or --validate-report")
    return 2


if __name__ == "__main__":
    sys.exit(main())
