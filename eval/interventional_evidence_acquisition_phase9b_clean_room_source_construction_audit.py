#!/usr/bin/env python3
"""Phase 9B clean-room candidate-source construction/audit helper.

This runner is intentionally narrow.  It constructs and audits a private
candidate-source registry under ignored ``runs/`` using only the frozen Phase 9A
public rules, then publishes one aggregate-only public JSON report.  It does not
score sources, generate labels, generate tasks/outcomes, fit models, call
providers/LLMs, change runtime defaults, or read Phase 8B/private prior runs.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any
from urllib import error, parse, request


REPO = Path(__file__).resolve().parents[1]

PHASE = "phase9b_clean_room_source_construction_audit_no_scoring_no_claim"
STATUS_PASS = "phase9b_clean_room_source_construction_audit_no_scoring_no_claim"
STATUS_REPAIR = "repair_clean_room_source_construction_audit_no_claim"
STATUS_STOP = "stop_clean_room_source_construction_no_claim"
ALLOWED_STATUSES = {STATUS_PASS, STATUS_REPAIR, STATUS_STOP}
SCHEMA_VERSION = f"{PHASE}_report_v1"

DEFAULT_PUBLIC_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
DEFAULT_PRIVATE_RUN_DIR = REPO / "runs" / "phase9b_clean_room_source_construction_audit" / "current"
PHASE9A_REPORT = REPO / "artifacts" / "phase9a_protocol_freeze_no_execution_no_claim" / "phase9a_protocol_freeze_no_execution_no_claim_report.json"

PHASE9A_COMMIT = "a479e48"
PHASE9A_CI_RUN = "28964719920"
PHASE9A_STATUS = "phase9a_protocol_freeze_no_execution_no_claim"

SEED_LABEL = "phase9a_clean_room_public_seed_v1"

PUBLIC_METADATA_MODE_LIVE = "live_public_metadata_api_fetch"
PUBLIC_METADATA_MODE_FIXTURE = "private_validator_fixture_no_network_not_pass_capable"
PUBLIC_METADATA_MODE_FAILED = "public_metadata_fetch_failed_no_private_or_synthetic_substitution"

PUBLIC_METADATA_CHANNEL_QUERIES = {
    "public_language_registry_top_projects_index": {
        "kind": "github_repository_search",
        "query": "language:Python archived:false mirror:false fork:false stars:>=1000",
        "sort": "stars",
        "order": "desc",
    },
    "public_ecosystem_topic_index": {
        "kind": "github_repository_search",
        "query": "topic:developer-tools archived:false mirror:false fork:false stars:>=500",
        "sort": "stars",
        "order": "desc",
    },
    "public_package_metadata_dependents_index": {
        "kind": "npm_package_search",
        "query": "not:deprecated",
        "sort": "popularity",
    },
}

CHANNEL_ORDER = (
    "public_language_registry_top_projects_index",
    "public_ecosystem_topic_index",
    "public_package_metadata_dependents_index",
)

DETERMINISTIC_SORT_KEYS = (
    "normalized_public_project_identity_ascending",
    "public_metadata_stable_rank_ascending",
    "default_branch_name_ascending",
    "channel_local_index_ascending",
)

ELIGIBILITY_CRITERIA = (
    "publicly_accessible_without_authentication",
    "source_archive_materializable_before_scoring",
    "declared_or_publicly_auditable_license_present",
    "default_branch_or_equivalent_revision_resolvable",
    "in_scope_language_or_file_mix_detectable_from_public_metadata",
    "not_private_prior_phase_or_manual_named_seed_material",
)

EXCLUSION_CRITERIA = (
    "requires_authentication_or_private_access",
    "cannot_materialize_source_archive_before_scoring",
    "license_absent_or_not_publicly_auditable",
    "identity_collides_with_earlier_clean_room_candidate",
    "fork_or_mirror_duplicate_of_already_accepted_identity",
    "would_require_public_reporting_of_exact_identifiers",
)

REPLACEMENT_ALGORITHM = (
    "replace_unavailable_or_ineligible_source_with_next_uninspected_item_from_same_frozen_channel_stream",
    "if_channel_stream_exhausted_continue_round_robin_to_next_channel_in_frozen_channel_order",
    "replacement_must_happen_before_any_scoring_labels_or_outcomes",
    "replacement_must_not_use_performance_outcome_evidence_success_or_phase8b_private_feedback",
)

FROZEN_QUOTAS = {
    "accepted_source_target": 12,
    "accepted_source_minimum_for_audit_pass": 8,
    "candidate_inspection_cap_total": 48,
    "candidate_inspection_cap_per_channel": 16,
    "initial_channel_quota_each": 16,
}

REQUIRED_TRUE_BOOLEANS = (
    "clean_room_source_construction_executed",
    "source_audit_executed",
    "public_output_aggregate_only",
)

REQUIRED_FALSE_BOOLEANS = (
    "scoring_executed",
    "labels_generated",
    "outcomes_generated",
    "evidence_success_evaluated",
    "model_fitting",
    "provider_or_llm_calls",
    "runtime_default_or_product_changes",
    "phase8b_private_pool_read",
    "phase8b_manifests_read",
    "phase8b_provenance_read",
    "phase8b_accepted_or_rejected_identities_read",
    "phase8b_private_material_reuse_allowed",
    "candidate_details_public",
)

CLAIM_BOUNDARY_FALSE = (
    "method_claim",
    "product_claim",
    "performance_claim",
    "training_claim",
    "provider_claim",
    "model_claim",
    "scoring_claim",
    "outcome_claim",
    "evidence_success_claim",
    "runtime_claim",
    "default_claim",
)

PRIVATE_SHAPED_VALUE_RE = re.compile(
    r"(?:https?://|git@|[A-Za-z]:[\\/]|(?:^|\s)/[A-Za-z0-9_.-]+/|\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b|\b[a-fA-F0-9]{32,}\b)"
)
SINGLETON_BUCKET_RE = re.compile(r"(?<![A-Za-z0-9])(?:count_1|bucket_one|singleton)(?![A-Za-z0-9])", re.IGNORECASE)
FORBIDDEN_PUBLIC_KEY_RE = re.compile(
    r"^(?:repo_name|repo_url|owner|source_url|source_name|candidate_identity|commit_sha|sha|hash|path|snippet|task_id|row_id|manifest|run_dir|per_source_fact)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Candidate:
    channel: str
    channel_local_index: int
    normalized_public_project_identity: str
    stable_public_metadata_rank: int
    default_branch_name: str
    publicly_accessible_without_authentication: bool
    source_archive_materializable_before_scoring: bool
    declared_or_publicly_auditable_license_present: bool
    default_branch_or_equivalent_revision_resolvable: bool
    in_scope_language_file_mix_detectable_from_public_metadata: bool
    not_private_prior_phase_or_manual_named_seed_material: bool
    fork_mirror_duplicate_of_already_accepted_identity: bool
    public_metadata_channel_kind: str
    public_metadata_mode: str
    public_metadata_license_key_present: bool
    public_metadata_source_archive_hint_present: bool


def _bucket_count(value: int) -> str:
    if value == 0:
        return "bucket_zero"
    if value <= 3:
        return "bucket_nonzero_to_three"
    if value <= 7:
        return "bucket_four_to_seven"
    if value <= 12:
        return "bucket_eight_to_twelve"
    if value <= 16:
        return "bucket_thirteen_to_sixteen"
    if value <= 24:
        return "bucket_seventeen_to_twenty_four"
    return "bucket_more_than_twenty_four"


def _assert_under_ignored_runs(path: Path) -> Path:
    resolved = path.resolve()
    runs_root = (REPO / "runs").resolve()
    if resolved != runs_root and runs_root not in resolved.parents:
        raise ValueError("private output must stay under ignored runs/")
    return resolved


def _load_phase9a_gate() -> dict[str, Any]:
    if not PHASE9A_REPORT.exists():
        raise ValueError("Phase 9A public report is missing")
    report = json.loads(PHASE9A_REPORT.read_text(encoding="utf-8"))
    if report.get("phase") != PHASE9A_STATUS or report.get("status") != PHASE9A_STATUS:
        raise ValueError("Phase 9A public report status drift")
    errors = _phase9a_rule_drift_errors(report)
    if errors:
        raise ValueError("Phase 9A frozen rule drift: " + "; ".join(errors))
    return {
        "phase9a_public_report_validated": True,
        "phase9a_commit": PHASE9A_COMMIT,
        "phase9a_ci_run": PHASE9A_CI_RUN,
        "phase9a_status": PHASE9A_STATUS,
    }


def _phase9a_rule_drift_errors(report: dict[str, Any] | None = None) -> list[str]:
    if report is None:
        if not PHASE9A_REPORT.exists():
            return ["Phase 9A public report is missing"]
        report = json.loads(PHASE9A_REPORT.read_text(encoding="utf-8"))
    protocol = report.get("clean_room_protocol", {}) if isinstance(report, dict) else {}
    identity = protocol.get("identity_normalization_before_inspection", {})
    eligibility = protocol.get("eligibility_filter_before_inspection", {})
    ordering = protocol.get("ordering_quota_replacement_rules", {})
    expected = {
        "channel_order": list(CHANNEL_ORDER),
        "sort_keys": list(DETERMINISTIC_SORT_KEYS),
        "quotas": dict(FROZEN_QUOTAS),
        "eligibility_criteria": list(ELIGIBILITY_CRITERIA),
        "exclusion_criteria": list(EXCLUSION_CRITERIA),
        "replacement_algorithm": list(REPLACEMENT_ALGORITHM),
    }
    actual = {
        "channel_order": protocol.get("neutral_acquisition_channels", {}).get("channel_order"),
        "sort_keys": ordering.get("deterministic_sort_keys") or identity.get("public_metadata_fields_used_for_ordering"),
        "quotas": ordering.get("quota_numbers"),
        "eligibility_criteria": eligibility.get("eligibility_criteria"),
        "exclusion_criteria": eligibility.get("exclusion_criteria"),
        "replacement_algorithm": ordering.get("replacement_algorithm"),
    }
    return [f"{key} does not match Phase 9A public report" for key, value in expected.items() if actual.get(key) != value]


def _generate_private_fixture_candidates() -> list[Candidate]:
    candidates: list[Candidate] = []
    for channel in CHANNEL_ORDER:
        for index in range(FROZEN_QUOTAS["candidate_inspection_cap_per_channel"]):
            accepted_slot = index < 4
            license_ok = accepted_slot or index >= 8
            materializable = accepted_slot or index < 8 or index >= 12
            duplicate = index >= 12
            identity_index = index - 8 if duplicate else index
            candidates.append(
                Candidate(
                    channel=channel,
                    channel_local_index=index,
                    normalized_public_project_identity=f"validator_fixture_candidate_{channel}_{identity_index:02d}",
                    stable_public_metadata_rank=index + 1,
                    default_branch_name="main",
                    publicly_accessible_without_authentication=True,
                    source_archive_materializable_before_scoring=materializable,
                    declared_or_publicly_auditable_license_present=license_ok,
                    default_branch_or_equivalent_revision_resolvable=True,
                    in_scope_language_file_mix_detectable_from_public_metadata=True,
                    not_private_prior_phase_or_manual_named_seed_material=True,
                    fork_mirror_duplicate_of_already_accepted_identity=duplicate,
                    public_metadata_channel_kind=PUBLIC_METADATA_CHANNEL_QUERIES[channel]["kind"],
                    public_metadata_mode=PUBLIC_METADATA_MODE_FIXTURE,
                    public_metadata_license_key_present=license_ok,
                    public_metadata_source_archive_hint_present=materializable,
                )
            )
    return candidates


def _http_json(url: str, timeout_seconds: int = 20) -> Any:
    headers = {
        "Accept": "application/json",
        "User-Agent": "OpenLocus-Phase9B-clean-room-public-metadata-audit",
    }
    req = request.Request(url, headers=headers)
    with request.urlopen(req, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _normalize_public_identity(raw: Any) -> str:
    text = str(raw or "").strip().lower()
    text = re.sub(r"^https?://", "", text)
    text = re.sub(r"^(?:www\.)?github\.com/", "", text)
    text = re.sub(r"[^a-z0-9._/-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-./")
    return text


def _license_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, dict):
        return any(bool(value.get(key)) for key in ("key", "spdx_id", "name", "type", "url"))
    return bool(str(value).strip())


def _branch_name(value: Any) -> str:
    text = str(value or "").strip()
    return text or "main"


def _github_candidates(channel: str, query_spec: dict[str, Any]) -> list[Candidate]:
    params = {
        "q": query_spec["query"],
        "sort": query_spec.get("sort", "stars"),
        "order": query_spec.get("order", "desc"),
        "per_page": str(FROZEN_QUOTAS["candidate_inspection_cap_per_channel"]),
    }
    url = "https://api.github.com/search/repositories?" + parse.urlencode(params)
    payload = _http_json(url)
    items = payload.get("items", []) if isinstance(payload, dict) else []
    candidates: list[Candidate] = []
    for index, item in enumerate(items[: FROZEN_QUOTAS["candidate_inspection_cap_per_channel"]]):
        if not isinstance(item, dict):
            continue
        identity = _normalize_public_identity(item.get("full_name"))
        if not identity:
            continue
        archived = bool(item.get("archived"))
        disabled = bool(item.get("disabled"))
        default_branch = _branch_name(item.get("default_branch"))
        license_ok = _license_present(item.get("license"))
        materializable = bool(default_branch) and not archived and not disabled
        language_ok = bool(item.get("language") or item.get("topics"))
        candidates.append(
            Candidate(
                channel=channel,
                channel_local_index=index,
                normalized_public_project_identity=identity,
                stable_public_metadata_rank=index + 1,
                default_branch_name=default_branch,
                publicly_accessible_without_authentication=not bool(item.get("private")),
                source_archive_materializable_before_scoring=materializable,
                declared_or_publicly_auditable_license_present=license_ok,
                default_branch_or_equivalent_revision_resolvable=bool(default_branch),
                in_scope_language_file_mix_detectable_from_public_metadata=language_ok,
                not_private_prior_phase_or_manual_named_seed_material=True,
                fork_mirror_duplicate_of_already_accepted_identity=bool(item.get("fork") or item.get("mirror_url")),
                public_metadata_channel_kind=query_spec["kind"],
                public_metadata_mode=PUBLIC_METADATA_MODE_LIVE,
                public_metadata_license_key_present=license_ok,
                public_metadata_source_archive_hint_present=materializable,
            )
        )
    return candidates


def _npm_candidates(channel: str, query_spec: dict[str, Any]) -> list[Candidate]:
    params = {
        "text": query_spec["query"],
        "size": str(FROZEN_QUOTAS["candidate_inspection_cap_per_channel"]),
    }
    url = "https://registry.npmjs.org/-/v1/search?" + parse.urlencode(params)
    payload = _http_json(url)
    objects = payload.get("objects", []) if isinstance(payload, dict) else []
    candidates: list[Candidate] = []
    for index, item in enumerate(objects[: FROZEN_QUOTAS["candidate_inspection_cap_per_channel"]]):
        if not isinstance(item, dict):
            continue
        package = item.get("package")
        if not isinstance(package, dict):
            continue
        name = str(package.get("name") or "").strip()
        identity = _normalize_public_identity("npm/" + name)
        if not identity:
            continue
        links = package.get("links") if isinstance(package.get("links"), dict) else {}
        license_ok = _license_present(package.get("license"))
        materializable = bool(links.get("npm") or links.get("repository"))
        candidates.append(
            Candidate(
                channel=channel,
                channel_local_index=index,
                normalized_public_project_identity=identity,
                stable_public_metadata_rank=index + 1,
                default_branch_name="registry",
                publicly_accessible_without_authentication=True,
                source_archive_materializable_before_scoring=materializable,
                declared_or_publicly_auditable_license_present=license_ok,
                default_branch_or_equivalent_revision_resolvable=True,
                in_scope_language_file_mix_detectable_from_public_metadata=True,
                not_private_prior_phase_or_manual_named_seed_material=True,
                fork_mirror_duplicate_of_already_accepted_identity=False,
                public_metadata_channel_kind=query_spec["kind"],
                public_metadata_mode=PUBLIC_METADATA_MODE_LIVE,
                public_metadata_license_key_present=license_ok,
                public_metadata_source_archive_hint_present=materializable,
            )
        )
    return candidates


def fetch_public_metadata_candidates() -> tuple[list[Candidate], dict[str, Any]]:
    candidates: list[Candidate] = []
    channel_fetch_buckets: dict[str, str] = {}
    fetch_errors: dict[str, str] = {}
    for channel in CHANNEL_ORDER:
        spec = PUBLIC_METADATA_CHANNEL_QUERIES[channel]
        try:
            if spec["kind"] == "github_repository_search":
                channel_candidates = _github_candidates(channel, spec)
            elif spec["kind"] == "npm_package_search":
                channel_candidates = _npm_candidates(channel, spec)
            else:
                raise ValueError("unsupported public metadata channel kind")
            candidates.extend(channel_candidates)
            channel_fetch_buckets[channel] = _bucket_count(len(channel_candidates))
        except (OSError, TimeoutError, ValueError, error.URLError, error.HTTPError, json.JSONDecodeError) as exc:
            channel_fetch_buckets[channel] = "bucket_zero"
            fetch_errors[channel] = type(exc).__name__
    fetch_summary = {
        "mode": PUBLIC_METADATA_MODE_LIVE if candidates else PUBLIC_METADATA_MODE_FAILED,
        "public_metadata_fetch_attempted": True,
        "public_metadata_fetch_succeeded": not fetch_errors and bool(candidates),
        "channel_fetch_buckets": channel_fetch_buckets,
        "fetch_error_type_buckets": {error_type: _bucket_count(list(fetch_errors.values()).count(error_type)) for error_type in sorted(set(fetch_errors.values()))},
    }
    return candidates, fetch_summary


def _is_eligible(candidate: Candidate, seen: set[str]) -> tuple[bool, str | None]:
    if not candidate.publicly_accessible_without_authentication:
        return False, "requires_authentication_or_private_access"
    if not candidate.source_archive_materializable_before_scoring:
        return False, "cannot_materialize_source_archive_before_scoring"
    if not candidate.declared_or_publicly_auditable_license_present:
        return False, "license_absent_or_not_publicly_auditable"
    if candidate.normalized_public_project_identity in seen:
        return False, "identity_collides_with_earlier_clean_room_candidate"
    if candidate.fork_mirror_duplicate_of_already_accepted_identity:
        return False, "fork_or_mirror_duplicate_of_already_accepted_identity"
    if not candidate.default_branch_or_equivalent_revision_resolvable:
        return False, "cannot_materialize_source_archive_before_scoring"
    if not candidate.in_scope_language_file_mix_detectable_from_public_metadata:
        return False, "cannot_materialize_source_archive_before_scoring"
    if not candidate.not_private_prior_phase_or_manual_named_seed_material:
        return False, "would_require_public_reporting_of_exact_identifiers"
    return True, None


def _stable_sort_candidates(candidates: list[Candidate]) -> list[Candidate]:
    return sorted(
        candidates,
        key=lambda item: (
            item.normalized_public_project_identity,
            item.stable_public_metadata_rank,
            item.default_branch_name,
            item.channel_local_index,
        ),
    )


def _normalize_and_deduplicate_before_inspection(candidates: list[Candidate]) -> tuple[dict[str, list[Candidate]], dict[str, int], bool]:
    seen_identities: set[str] = set()
    unique_by_channel = {channel: [] for channel in CHANNEL_ORDER}
    duplicate_counts = {channel: 0 for channel in CHANNEL_ORDER}
    for candidate in _stable_sort_candidates(candidates):
        normalized_identity = _normalize_public_identity(candidate.normalized_public_project_identity)
        if not normalized_identity:
            duplicate_counts[candidate.channel] = duplicate_counts.get(candidate.channel, 0) + 1
            continue
        normalized_candidate = replace(candidate, normalized_public_project_identity=normalized_identity)
        if normalized_identity in seen_identities:
            duplicate_counts[normalized_candidate.channel] = duplicate_counts.get(normalized_candidate.channel, 0) + 1
            continue
        seen_identities.add(normalized_identity)
        unique_by_channel.setdefault(normalized_candidate.channel, []).append(normalized_candidate)
    for channel in CHANNEL_ORDER:
        unique_by_channel[channel] = _stable_sort_candidates(unique_by_channel.get(channel, []))
    return unique_by_channel, duplicate_counts, True


def _balanced_inspection_order(unique_by_channel: dict[str, list[Candidate]]) -> list[Candidate]:
    ordered: list[Candidate] = []
    cap_per_channel = FROZEN_QUOTAS["candidate_inspection_cap_per_channel"]
    total_cap = FROZEN_QUOTAS["candidate_inspection_cap_total"]
    cursors = {channel: 0 for channel in CHANNEL_ORDER}
    while len(ordered) < total_cap:
        advanced = False
        for channel in CHANNEL_ORDER:
            if cursors[channel] >= cap_per_channel:
                continue
            channel_candidates = unique_by_channel.get(channel, [])
            if cursors[channel] >= len(channel_candidates):
                continue
            ordered.append(channel_candidates[cursors[channel]])
            cursors[channel] += 1
            advanced = True
            if len(ordered) >= total_cap:
                break
        if not advanced:
            break
    return ordered


def construct_private_audit(candidates: list[Candidate], metadata_summary: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    unique_by_channel, duplicate_counts, identity_normalization_completed = _normalize_and_deduplicate_before_inspection(candidates)
    inspected = _balanced_inspection_order(unique_by_channel)

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    not_selected_after_target: list[dict[str, Any]] = []
    seen: set[str] = set()
    channel_counts = {channel: 0 for channel in CHANNEL_ORDER}
    reason_counts: dict[str, int] = {}

    for candidate in inspected:
        if sum(channel_counts.values()) >= FROZEN_QUOTAS["candidate_inspection_cap_total"]:
            break
        if channel_counts[candidate.channel] >= FROZEN_QUOTAS["candidate_inspection_cap_per_channel"]:
            continue
        channel_counts[candidate.channel] += 1
        eligible, reason = _is_eligible(candidate, seen)
        record = asdict(candidate)
        record["identity_normalized_before_inspection"] = identity_normalization_completed
        record["availability_gate_completed_before_scoring"] = True
        if eligible:
            seen.add(candidate.normalized_public_project_identity)
            if len(accepted) < FROZEN_QUOTAS["accepted_source_target"]:
                record["clean_room_audit_decision"] = "accepted"
                accepted.append(record)
            else:
                record["clean_room_audit_decision"] = "eligible_not_accepted_after_frozen_target_reached"
                not_selected_after_target.append(record)
        else:
            record["clean_room_audit_decision"] = "rejected"
            record["exclusion_reason"] = reason
            rejected.append(record)
            if reason is not None:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

    totals = {
        "inspected_total": sum(channel_counts.values()),
        "accepted_total": len(accepted),
        "rejected_total": len(rejected),
        "not_accepted_after_target_total": len(not_selected_after_target),
        "unavailable_total": reason_counts.get("cannot_materialize_source_archive_before_scoring", 0),
        "ineligible_total": len(rejected) - reason_counts.get("cannot_materialize_source_archive_before_scoring", 0),
        "replacement_total": len(rejected),
        "channel_counts": channel_counts,
        "exclusion_reason_counts": reason_counts,
        "duplicate_collision_buckets": {channel: _bucket_count(count) for channel, count in duplicate_counts.items()},
        "identity_normalization_completed_before_inspection": identity_normalization_completed,
        "quota_balance_before_inspection": True,
        "public_metadata_fetch_attempted": metadata_summary.get("public_metadata_fetch_attempted") is True,
        "public_metadata_fetch_succeeded": metadata_summary.get("public_metadata_fetch_succeeded") is True,
        "public_metadata_mode": metadata_summary.get("mode", PUBLIC_METADATA_MODE_FAILED),
        "public_metadata_channel_fetch_buckets": metadata_summary.get("channel_fetch_buckets", {}),
        "public_metadata_fetch_error_type_buckets": metadata_summary.get("fetch_error_type_buckets", {}),
    }
    private_registry = {
        "phase": PHASE,
        "private_candidate_details_not_for_public_report": True,
        "metadata_materialization": metadata_summary.get("mode", PUBLIC_METADATA_MODE_FAILED),
        "public_metadata_fetch_attempted": metadata_summary.get("public_metadata_fetch_attempted") is True,
        "public_metadata_fetch_succeeded": metadata_summary.get("public_metadata_fetch_succeeded") is True,
        "seed_label": SEED_LABEL,
        "phase8b_private_pool_read": False,
        "phase8b_manifests_read": False,
        "phase8b_provenance_read": False,
        "phase8b_accepted_or_rejected_identities_read": False,
        "scoring_executed": False,
        "labels_generated": False,
        "outcomes_generated": False,
        "evidence_success_evaluated": False,
        "model_fitting": False,
        "provider_or_llm_calls": False,
        "accepted_private_registry": accepted,
        "rejected_private_registry": rejected,
        "eligible_not_accepted_after_target_private_registry": not_selected_after_target,
        "aggregate_counts": totals,
    }
    return private_registry, totals


def _bucket_obj(value: int) -> dict[str, str]:
    return {"bucket": _bucket_count(value)}


def _aggregate_public_report(totals: dict[str, Any], phase9a_gate: dict[str, Any]) -> dict[str, Any]:
    channel_counts: dict[str, int] = totals["channel_counts"]
    reason_counts: dict[str, int] = totals["exclusion_reason_counts"]
    caps_respected = (
        totals["inspected_total"] <= FROZEN_QUOTAS["candidate_inspection_cap_total"]
        and all(count <= FROZEN_QUOTAS["candidate_inspection_cap_per_channel"] for count in channel_counts.values())
    )
    accepted_total = totals["accepted_total"]
    live_public_metadata = totals.get("public_metadata_mode") == PUBLIC_METADATA_MODE_LIVE and totals.get("public_metadata_fetch_succeeded") is True
    status = STATUS_PASS if live_public_metadata and accepted_total >= FROZEN_QUOTAS["accepted_source_minimum_for_audit_pass"] and caps_respected else STATUS_REPAIR
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "phase9a_gate": dict(phase9a_gate),
        "frozen_phase9a_rules": {
            "channel_order": list(CHANNEL_ORDER),
            "sort_keys": list(DETERMINISTIC_SORT_KEYS),
            "seed_label": SEED_LABEL,
            "randomness_forbidden": True,
            "quotas": dict(FROZEN_QUOTAS),
            "eligibility_criteria": list(ELIGIBILITY_CRITERIA),
            "exclusion_criteria": list(EXCLUSION_CRITERIA),
            "replacement_algorithm": list(REPLACEMENT_ALGORITHM),
        },
        "public_aggregate_audit": {
            "channel_inspected_buckets": {
                channel: _bucket_obj(count) for channel, count in channel_counts.items()
            },
            "accepted_bucket": _bucket_obj(totals["accepted_total"]),
            "rejected_bucket": _bucket_obj(totals["rejected_total"]),
            "unavailable_bucket": _bucket_obj(totals["unavailable_total"]),
            "ineligible_bucket": _bucket_obj(totals["ineligible_total"]),
            "replacement_bucket": _bucket_obj(totals["replacement_total"]),
            "pre_inspection_duplicate_collision_buckets": dict(totals.get("duplicate_collision_buckets", {})),
            "exclusion_reason_buckets": {
                reason: _bucket_obj(count) for reason, count in sorted(reason_counts.items())
            },
            "minimum_acceptance_threshold_bucket": _bucket_obj(FROZEN_QUOTAS["accepted_source_minimum_for_audit_pass"]),
            "identity_normalization_completed_before_inspection": totals.get("identity_normalization_completed_before_inspection") is True,
            "quota_balance_before_inspection": totals.get("quota_balance_before_inspection") is True,
            "availability_gate_completed_before_scoring": True,
            "caps_respected": caps_respected,
            "hard_stops_occurred": not bool(totals.get("public_metadata_fetch_succeeded")),
        },
        "required_public_booleans": {
            **{key: True for key in REQUIRED_TRUE_BOOLEANS},
            **{key: False for key in REQUIRED_FALSE_BOOLEANS},
        },
        "claim_boundary": {key: False for key in CLAIM_BOUNDARY_FALSE},
        "privacy_confirmation": {
            "private_output_confirmed": True,
            "public_metadata_fetch_attempted": totals.get("public_metadata_fetch_attempted") is True,
            "public_metadata_fetch_succeeded": totals.get("public_metadata_fetch_succeeded") is True,
            "public_metadata_mode": totals.get("public_metadata_mode", PUBLIC_METADATA_MODE_FAILED),
            "public_metadata_channel_fetch_buckets": dict(totals.get("public_metadata_channel_fetch_buckets", {})),
            "public_metadata_fetch_error_type_buckets": dict(totals.get("public_metadata_fetch_error_type_buckets", {})),
            "candidate_details_public": False,
            "public_output_aggregate_only": True,
        },
        "validation_summary": {
            "self_test_available": True,
            "route_specific_validator_available": True,
            "public_artifact_privacy_scan_expected": True,
        },
    }


def _scan_public_value(value: Any, path: str = "$", key: str = "") -> list[str]:
    errors: list[str] = []
    if key and FORBIDDEN_PUBLIC_KEY_RE.search(key) and key != "phase9a_commit":
        errors.append(f"private-shaped public key at {path}")
    if key == "count":
        errors.append(f"exact public count field at {path}")
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            child_path = f"{path}.{child_key}" if path != "$" else f"$.{child_key}"
            errors.extend(_scan_public_value(child_value, child_path, str(child_key)))
    elif isinstance(value, list):
        for index, child_value in enumerate(value):
            errors.extend(_scan_public_value(child_value, f"{path}[{index}]", ""))
    elif isinstance(value, str):
        if PRIVATE_SHAPED_VALUE_RE.search(value) and not (path.endswith(".phase9a_commit") or path.endswith(".phase9a_ci_run")):
            errors.append(f"private-shaped public value at {path}")
        if SINGLETON_BUCKET_RE.search(value):
            errors.append(f"singleton public bucket at {path}")
    return errors


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be a JSON object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION or report.get("phase") != PHASE:
        errors.append("schema or phase drift")
    if report.get("status") not in ALLOWED_STATUSES:
        errors.append("unknown status")

    gate = report.get("phase9a_gate", {})
    if gate.get("phase9a_commit") != PHASE9A_COMMIT or gate.get("phase9a_ci_run") != PHASE9A_CI_RUN or gate.get("phase9a_status") != PHASE9A_STATUS:
        errors.append("Phase 9A gate drift")
    if gate.get("phase9a_public_report_validated") is not True:
        errors.append("Phase 9A public report gate missing")

    rules = report.get("frozen_phase9a_rules", {})
    if rules.get("channel_order") != list(CHANNEL_ORDER):
        errors.append("channel order drift")
    if rules.get("sort_keys") != list(DETERMINISTIC_SORT_KEYS):
        errors.append("sort-key drift")
    if rules.get("seed_label") != SEED_LABEL or rules.get("randomness_forbidden") is not True:
        errors.append("randomness policy drift")
    if rules.get("quotas") != dict(FROZEN_QUOTAS):
        errors.append("quota drift")
    if rules.get("eligibility_criteria") != list(ELIGIBILITY_CRITERIA):
        errors.append("eligibility drift")
    if rules.get("exclusion_criteria") != list(EXCLUSION_CRITERIA):
        errors.append("exclusion drift")
    if rules.get("replacement_algorithm") != list(REPLACEMENT_ALGORITHM):
        errors.append("replacement drift")

    booleans = report.get("required_public_booleans", {})
    for key in REQUIRED_TRUE_BOOLEANS:
        if booleans.get(key) is not True:
            errors.append(f"required true boolean missing: {key}")
    for key in REQUIRED_FALSE_BOOLEANS:
        if booleans.get(key) is not False:
            errors.append(f"required false boolean failed: {key}")
    for key in CLAIM_BOUNDARY_FALSE:
        if report.get("claim_boundary", {}).get(key) is not False:
            errors.append(f"claim boundary failed: {key}")

    audit = report.get("public_aggregate_audit", {})
    accepted_bucket = audit.get("accepted_bucket", {}).get("bucket")
    inspected_by_channel = audit.get("channel_inspected_buckets", {})
    if isinstance(inspected_by_channel, dict):
        for channel in CHANNEL_ORDER:
            bucket = inspected_by_channel.get(channel, {}).get("bucket")
            if not isinstance(bucket, str):
                errors.append(f"missing channel inspected bucket: {channel}")
                continue
    else:
        errors.append("channel inspected buckets missing")
    for required_bucket_key in (
        "accepted_bucket",
        "rejected_bucket",
        "unavailable_bucket",
        "ineligible_bucket",
        "replacement_bucket",
        "minimum_acceptance_threshold_bucket",
    ):
        if not isinstance(audit.get(required_bucket_key, {}).get("bucket"), str):
            errors.append(f"missing public aggregate bucket: {required_bucket_key}")
    if "replacement_count_bucket" in audit:
        errors.append("public aggregate uses exact-count key name")
    if audit.get("caps_respected") is not True:
        errors.append("caps respected flag not true")
    if audit.get("identity_normalization_completed_before_inspection") is not True:
        errors.append("identity normalization not completed before inspection")
    if audit.get("quota_balance_before_inspection") is not True:
        errors.append("quota balance before inspection missing")
    if audit.get("availability_gate_completed_before_scoring") is not True:
        errors.append("availability gate not completed before scoring")
    privacy = report.get("privacy_confirmation", {})
    live_public_metadata = privacy.get("public_metadata_mode") == PUBLIC_METADATA_MODE_LIVE and privacy.get("public_metadata_fetch_succeeded") is True
    if report.get("status") == STATUS_PASS:
        if not live_public_metadata:
            errors.append("pass status without live public metadata fetch")
        if accepted_bucket not in {"bucket_eight_to_twelve", "bucket_thirteen_to_sixteen", "bucket_seventeen_to_twenty_four", "bucket_more_than_twenty_four"}:
            errors.append("pass status with accepted below minimum bucket")

    if privacy.get("private_output_confirmed") is not True:
        errors.append("private output confirmation missing")
    if "public_metadata_fetch_confirmed" in privacy or "public_metadata_source" in privacy:
        errors.append("misleading public metadata fetch/source field present")
    if privacy.get("public_metadata_mode") in {PUBLIC_METADATA_MODE_FIXTURE, PUBLIC_METADATA_MODE_FAILED} and report.get("status") == STATUS_PASS:
        errors.append("fixture or failed metadata mode cannot pass")
    if privacy.get("candidate_details_public") is not False or privacy.get("public_output_aggregate_only") is not True:
        errors.append("privacy aggregate-only contract failed")

    errors.extend(_scan_public_value(report))
    return sorted(set(errors))


def execute_phase9b(private_run_dir: Path, public_report: Path, confirm_private_output: bool, confirm_public_metadata_fetch: bool) -> dict[str, Any]:
    if not confirm_private_output:
        raise ValueError("missing --confirm-private-output")
    if not confirm_public_metadata_fetch:
        raise ValueError("missing --confirm-public-metadata-fetch for live public metadata acquisition")
    private_run_dir = _assert_under_ignored_runs(private_run_dir)
    phase9a_gate = _load_phase9a_gate()
    candidates, metadata_summary = fetch_public_metadata_candidates()
    private_registry, totals = construct_private_audit(candidates, metadata_summary)
    report = _aggregate_public_report(totals, phase9a_gate)
    errors = validate_report(report)
    if errors:
        raise ValueError("generated public report invalid: " + "; ".join(errors[:12]))

    private_run_dir.mkdir(parents=True, exist_ok=True)
    public_report.parent.mkdir(parents=True, exist_ok=True)
    (private_run_dir / "private_candidate_registry.json").write_text(json.dumps(private_registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (private_run_dir / "private_aggregate_audit.json").write_text(json.dumps(totals, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    public_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": report["status"],
        "accepted_bucket": report["public_aggregate_audit"]["accepted_bucket"]["bucket"],
        "public_metadata_fetch_attempted": totals["public_metadata_fetch_attempted"],
        "public_metadata_fetch_succeeded": totals["public_metadata_fetch_succeeded"],
        "public_metadata_mode": totals["public_metadata_mode"],
        "public_report": str(public_report),
    }


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    fixture_summary = {
        "mode": PUBLIC_METADATA_MODE_FIXTURE,
        "public_metadata_fetch_attempted": False,
        "public_metadata_fetch_succeeded": False,
        "channel_fetch_buckets": {channel: _bucket_count(FROZEN_QUOTAS["candidate_inspection_cap_per_channel"]) for channel in CHANNEL_ORDER},
        "fetch_error_type_buckets": {},
    }
    private_registry, totals = construct_private_audit(_generate_private_fixture_candidates(), fixture_summary)
    checks.append(("private_registry_has_no_phase8b_reads", private_registry["phase8b_private_pool_read"] is False and private_registry["phase8b_manifests_read"] is False))
    fixture_report = _aggregate_public_report(totals, {
        "phase9a_public_report_validated": True,
        "phase9a_commit": PHASE9A_COMMIT,
        "phase9a_ci_run": PHASE9A_CI_RUN,
        "phase9a_status": PHASE9A_STATUS,
    })
    checks.append(("fixture_report_valid_repair_not_pass", not validate_report(fixture_report) and fixture_report["status"] == STATUS_REPAIR))
    checks.append(("phase9a_public_rule_constants_exact", not _phase9a_rule_drift_errors()))
    checks.append(("fixture_duplicate_prepass_reduces_inspections", totals["inspected_total"] < len(_generate_private_fixture_candidates())))
    checks.append(("fixture_duplicates_not_inspected_twice", totals["exclusion_reason_counts"].get("identity_collides_with_earlier_clean_room_candidate", 0) == 0))
    checks.append(("fixture_quota_balance_inspects_all_channels", all(count > 0 for count in totals["channel_counts"].values())))
    checks.append(("fixture_not_first_channel_only", len({count for count in totals["channel_counts"].values()}) == 1))

    live_totals = copy.deepcopy(totals)
    live_totals["public_metadata_mode"] = PUBLIC_METADATA_MODE_LIVE
    live_totals["public_metadata_fetch_attempted"] = True
    live_totals["public_metadata_fetch_succeeded"] = True
    base = _aggregate_public_report(live_totals, {
        "phase9a_public_report_validated": True,
        "phase9a_commit": PHASE9A_COMMIT,
        "phase9a_ci_run": PHASE9A_CI_RUN,
        "phase9a_status": PHASE9A_STATUS,
    })
    checks.append(("base_report_valid", not validate_report(base)))

    for name, mutator in (
        ("phase9a_gate_drift_rejected", lambda r: r["phase9a_gate"].update({"phase9a_commit": "drift"})),
        ("channel_order_drift_rejected", lambda r: r["frozen_phase9a_rules"].update({"channel_order": list(reversed(CHANNEL_ORDER))})),
        ("sort_key_drift_rejected", lambda r: r["frozen_phase9a_rules"].update({"sort_keys": ["posthoc_rank_descending"]})),
        ("quota_drift_rejected", lambda r: r["frozen_phase9a_rules"]["quotas"].update({"candidate_inspection_cap_total": 96})),
        ("eligibility_drift_rejected", lambda r: r["frozen_phase9a_rules"].update({"eligibility_criteria": ["manual_review"]})),
        ("replacement_drift_rejected", lambda r: r["frozen_phase9a_rules"].update({"replacement_algorithm": ["choose_after_outcomes"]})),
        ("randomness_allowed_rejected", lambda r: r["frozen_phase9a_rules"].update({"randomness_forbidden": False})),
        ("private_read_flag_rejected", lambda r: r["required_public_booleans"].update({"phase8b_private_pool_read": True})),
        ("scoring_flag_rejected", lambda r: r["required_public_booleans"].update({"scoring_executed": True})),
        ("labels_flag_rejected", lambda r: r["required_public_booleans"].update({"labels_generated": True})),
        ("outcomes_flag_rejected", lambda r: r["required_public_booleans"].update({"outcomes_generated": True})),
        ("evidence_success_flag_rejected", lambda r: r["required_public_booleans"].update({"evidence_success_evaluated": True})),
        ("public_private_shaped_value_rejected", lambda r: r.update({"public_example": "https://example.invalid/owner/repo"})),
        ("singleton_bucket_rejected", lambda r: r["public_aggregate_audit"].update({"bad_bucket": "bucket_one"})),
        ("public_exact_count_rejected", lambda r: r["public_aggregate_audit"]["accepted_bucket"].update({"count": 12})),
        ("pass_with_accepted_under_minimum_rejected", lambda r: r["public_aggregate_audit"]["accepted_bucket"].update({"bucket": "bucket_four_to_seven"})),
        ("pass_without_live_fetch_rejected", lambda r: r["privacy_confirmation"].update({"public_metadata_mode": PUBLIC_METADATA_MODE_FIXTURE, "public_metadata_fetch_succeeded": False})),
        ("misleading_fetch_confirmed_field_rejected", lambda r: r["privacy_confirmation"].update({"public_metadata_fetch_confirmed": True})),
        ("missing_identity_prepass_rejected", lambda r: r["public_aggregate_audit"].update({"identity_normalization_completed_before_inspection": False})),
        ("missing_quota_balance_rejected", lambda r: r["public_aggregate_audit"].update({"quota_balance_before_inspection": False})),
    ):
        mutated = copy.deepcopy(base)
        mutator(mutated)
        checks.append((name, bool(validate_report(mutated))))

    try:
        execute_phase9b(DEFAULT_PRIVATE_RUN_DIR, DEFAULT_PUBLIC_REPORT, False, True)
        checks.append(("missing_confirm_private_rejected", False))
    except ValueError as exc:
        checks.append(("missing_confirm_private_rejected", "confirm-private-output" in str(exc)))
    try:
        execute_phase9b(DEFAULT_PRIVATE_RUN_DIR, DEFAULT_PUBLIC_REPORT, True, False)
        checks.append(("missing_confirm_public_metadata_rejected", False))
    except ValueError as exc:
        checks.append(("missing_confirm_public_metadata_rejected", "confirm-public-metadata-fetch" in str(exc)))
    try:
        _assert_under_ignored_runs(REPO / "artifacts" / "bad_private_output")
        checks.append(("private_output_outside_runs_rejected", False))
    except ValueError as exc:
        checks.append(("private_output_outside_runs_rejected", "runs" in str(exc)))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 9B clean-room source construction/audit runner")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-private-output", action="store_true")
    parser.add_argument("--confirm-public-metadata-fetch", action="store_true")
    parser.add_argument("--private-run-dir", type=Path, default=DEFAULT_PRIVATE_RUN_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_PUBLIC_REPORT)
    parser.add_argument("--validate-report", type=Path)
    args = parser.parse_args(argv)

    if args.self_test:
        print(json.dumps(run_self_test(), indent=2, sort_keys=True))
        return 0
    if args.execute:
        result = execute_phase9b(args.private_run_dir, args.output, args.confirm_private_output, args.confirm_public_metadata_fetch)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.validate_report:
        report = json.loads(args.validate_report.read_text(encoding="utf-8"))
        errors = validate_report(report)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(f"Validation passed: {args.validate_report}")
        return 0
    parser.error("choose --self-test, --execute, or --validate-report")
    return 2


if __name__ == "__main__":
    sys.exit(main())
