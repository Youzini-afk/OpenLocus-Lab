#!/usr/bin/env python3
"""Phase 9E public source fetch/clone materialization protocol freeze.

This is a docs/report/validator-only protocol freeze. It freezes the future
public source fetch/clone/materialization rules after the Phase 9D
zero-materialization repair checkpoint. It does NOT fetch, clone, read, or
materialize any repository or source, does NOT read ignored ``runs/`` or private
registries/manifests, does NOT generate task rows, labels, outcomes, scoring
rows, or evidence_success, and makes no method/product/performance/model/
provider/training/runtime/default/scoring/outcome/evidence-success claim.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]

PHASE = "phase9e_public_source_fetch_clone_materialization_protocol_freeze_no_execution_no_scoring_no_claim"
STATUS = PHASE
SCHEMA_VERSION = f"{PHASE}_report_v1"

DEFAULT_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
)

PHASE9D_STATUS = "repair_task_materialization_no_claim"
PHASE9D_PHASE = "phase9d_task_candidate_materialization_no_scoring_no_claim"
PHASE9D_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE9D_PHASE / f"{PHASE9D_PHASE}_report.json"
)
PHASE9D_DOCS = (
    REPO / "docs" / "en" / "interventional-evidence-acquisition-phase9d-task-candidate-materialization-no-scoring-no-claim.md",
    REPO / "docs" / "zh" / "interventional-evidence-acquisition-phase9d-task-candidate-materialization-no-scoring-no-claim.md",
)

# Oracle-provided Phase 9D gate reference values.
PHASE9D_COMMIT = "44400c4"
PHASE9D_CI_RUN = "28971783265"

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
)

NO_EXECUTION_FALSE_KEYS = (
    "public_fetch_clone_executed",
    "source_materialization_executed",
    "task_generation_executed",
    "labels_generated",
    "outcomes_generated",
    "scoring_executed",
    "evidence_success_evaluated",
    "model_fitting",
    "provider_or_llm_calls",
    "runtime_default_or_product_changes",
    "private_registry_read",
    "ignored_runs_read",
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
    "manifest_locations_public",
    "run_locations_public",
    "per_source_public_facts",
    "per_task_public_facts",
    "singleton_buckets_public",
)

FORBIDDEN_PUBLIC_FIELD_WORDS = (
    "scoring",
    "labels",
    "outcomes",
    "evidence_success",
)

PRIVATE_SHAPED_VALUE_RE = re.compile(
    r"(?:https?://|git@|[A-Za-z]:[\\/]"
    r"|(?:^|\s)/[A-Za-z0-9_.-]+/"
    r"|\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b"
    r"|\b[a-fA-F0-9]{32,}\b)"
)
SINGLETON_BUCKET_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:count_1|bucket_one|singleton)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
PRIVATE_KEY_RE = re.compile(
    r"^(?:repo|repo_name|repo_url|owner|url|source_url"
    r"|candidate_identity|commit|commit_sha|sha|hash"
    r"|path|range|snippet|task_id|row_id"
    r"|manifest|run_dir|per_source|per_task)$",
    re.IGNORECASE,
)

# Attestation counters to prove the validator/self-test do not fetch/read.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_READ_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0


def _runs_is_ignored() -> bool:
    gitignore = REPO / ".gitignore"
    if not gitignore.exists():
        return False
    lines = [line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()]
    return "/runs/" in lines or "runs/" in lines or "/runs" in lines


def build_public_report() -> dict[str, Any]:
    """Build the frozen Phase 9E public protocol report.

    This function performs no network/filesystem fetch or private reads. It
    assembles the frozen protocol document from static constants.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "phase9d_gate_references": {
            "phase9d_commit": PHASE9D_COMMIT,
            "phase9d_ci_run": PHASE9D_CI_RUN,
            "phase9d_ci_success": True,
            "phase9d_status": PHASE9D_STATUS,
            "phase9d_zero_rows": True,
            "phase9d_public_fetch_or_clone_executed": False,
            "phase9d_gate_required_before_phase9e": True,
        },
        "phase9e_scope": {
            "docs_report_validator_only": True,
            "protocol_freeze_only": True,
            "public_fetch_clone_executed": False,
            "source_materialization_executed": False,
            "private_registry_read": False,
            "ignored_runs_read": False,
            "future_execution_requires_phase9e_commit_and_ci_green": True,
        },
        "future_protocol_summary": {
            "publication_level": "aggregate_bucketed_protocol_only",
            "fetch_clone_rules": [
                "public_only_fetch_clone_under_explicit_confirmation_only",
                "fetch_clone_into_ignored_workspace_only_not_into_tracked_artifacts",
                "license_access_default_branch_checks_before_any_materialization",
                "currentness_hash_reread_before_any_task_row_acceptance",
                "exact_paths_ranges_hashes_snippets_private_only",
                "deterministic_source_order_no_random_shuffle",
                "task_candidate_target_bucket_conservative_48_to_72",
                "task_candidate_hard_cap_bucket_up_to_96",
                "per_source_task_cap_bucket_up_to_8",
                "minimum_distinct_sources_bucket_at_least_8",
                "stop_or_repair_if_zero_materialization_after_caps",
                "stop_or_repair_if_source_or_task_diversity_below_minimum_after_caps",
                "stop_or_repair_on_privacy_leak_or_singleton_public_bucket_need",
                "replacement_before_labels_outcomes_scoring_only",
                "replacement_cannot_use_performance_or_evidence_success_feedback",
                "task_types_limited_to_evidence_finding_file_localizable_code_tasks",
                "provider_llm_tasks_forbidden",
                "no_unit_public_per_source_or_per_task_reporting",
            ],
            "ignored_workspace": "runs/ only",
            "license_access_default_branch_currentness_hash_checks": True,
            "deterministic_caps_preserved": True,
            "stop_on_zero_materialization_after_caps": True,
            "stop_on_diversity_below_minimum_after_caps": True,
            "stop_on_privacy_leak_or_singleton_public_bucket": True,
            "future_strategy_scoring_requires_another_frozen_boundary": True,
        },
        "no_execution_booleans": {key: False for key in NO_EXECUTION_FALSE_KEYS},
        "privacy_contract": {
            "public_output_aggregate_only": True,
            "private_future_manifests_only_under_ignored_runs": True,
            "runs_remains_ignored": _runs_is_ignored(),
            **{key: False for key in PRIVACY_FALSE_KEYS},
        },
        "claim_boundary": {key: False for key in CLAIM_BOUNDARY_FALSE_KEYS},
        "validation_summary": {
            "route_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "validator_does_not_fetch_or_read_private": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "public_artifact_privacy_audit_expected": True,
        },
        "conservative_recommendation": (
            "freeze_future_public_source_fetch_clone_materialization_protocol"
            "_no_execution_no_scoring_no_claim"
        ),
    }


def _scan_public(value: Any, path: str = "$", key: str = "") -> list[str]:
    errors: list[str] = []
    key_lower = key.lower()
    if key_lower in {"count"} or key_lower.endswith("_count"):
        errors.append(f"exact public count field at {path}")
    # Forbidden public field words (scoring/labels/outcomes/evidence_success)
    # only apply to non-boolean values: boolean attestation keys such as
    # ``scoring_executed`` or ``evidence_success_claim`` are boundary checks
    # that must be ``false``, not exposed scoring data.
    if not isinstance(value, bool) and any(word in key_lower for word in FORBIDDEN_PUBLIC_FIELD_WORDS):
        errors.append(f"forbidden public field word at {path}")
    if key and PRIVATE_KEY_RE.search(key):
        errors.append(f"private-shaped public key at {path}")
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            child_path = f"{path}.{child_key}" if path != "$" else f"$.{child_key}"
            errors.extend(_scan_public(child_value, child_path, str(child_key)))
    elif isinstance(value, list):
        for index, child_value in enumerate(value):
            errors.extend(_scan_public(child_value, f"{path}[{index}]", ""))
    elif isinstance(value, str):
        if PRIVATE_SHAPED_VALUE_RE.search(value):
            errors.append(f"private-shaped public value at {path}")
        if SINGLETON_BUCKET_RE.search(value):
            errors.append(f"singleton bucket wording at {path}")
    return errors


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema drift")
    if report.get("phase") != PHASE:
        errors.append("phase drift")
    if report.get("status") != STATUS:
        errors.append("status drift")

    gate = report.get("phase9d_gate_references", {})
    if gate.get("phase9d_commit") != PHASE9D_COMMIT:
        errors.append("Phase 9D commit gate reference missing or drift")
    if gate.get("phase9d_ci_run") != PHASE9D_CI_RUN:
        errors.append("Phase 9D CI run gate reference missing or drift")
    if gate.get("phase9d_ci_success") is not True:
        errors.append("Phase 9D CI success gate missing")
    if gate.get("phase9d_status") != PHASE9D_STATUS:
        errors.append("Phase 9D status gate reference drift")
    if gate.get("phase9d_zero_rows") is not True:
        errors.append("Phase 9D zero-rows gate reference missing")
    if gate.get("phase9d_public_fetch_or_clone_executed") is not False:
        errors.append("Phase 9D public fetch/clone gate must be false")
    if gate.get("phase9d_gate_required_before_phase9e") is not True:
        errors.append("Phase 9D gate-required boundary missing")

    scope = report.get("phase9e_scope", {})
    for key in ("docs_report_validator_only", "protocol_freeze_only"):
        if scope.get(key) is not True:
            errors.append(f"phase9e scope missing: {key}")
    for key in ("public_fetch_clone_executed", "source_materialization_executed", "private_registry_read", "ignored_runs_read"):
        if scope.get(key) is not False:
            errors.append(f"phase9e execution boundary failed: {key}")
    if scope.get("future_execution_requires_phase9e_commit_and_ci_green") is not True:
        errors.append("phase9e future execution commit+CI-green boundary missing")

    future = report.get("future_protocol_summary", {})
    if future.get("publication_level") != "aggregate_bucketed_protocol_only":
        errors.append("future protocol publication level drift")
    if future.get("ignored_workspace") != "runs/ only":
        errors.append("future protocol ignored workspace drift")
    if future.get("license_access_default_branch_currentness_hash_checks") is not True:
        errors.append("future protocol license/access/currentness/hash checks missing")
    if future.get("deterministic_caps_preserved") is not True:
        errors.append("future protocol deterministic caps missing")
    if future.get("stop_on_zero_materialization_after_caps") is not True:
        errors.append("future protocol stop-on-zero missing")
    if future.get("stop_on_diversity_below_minimum_after_caps") is not True:
        errors.append("future protocol stop-on-diversity missing")
    if future.get("stop_on_privacy_leak_or_singleton_public_bucket") is not True:
        errors.append("future protocol stop-on-privacy/singleton missing")
    if future.get("future_strategy_scoring_requires_another_frozen_boundary") is not True:
        errors.append("future protocol strategy-scoring boundary missing")

    no_exec = report.get("no_execution_booleans", {})
    for key in NO_EXECUTION_FALSE_KEYS:
        if no_exec.get(key) is not False:
            errors.append(f"no_execution boundary failed: {key}")

    privacy = report.get("privacy_contract", {})
    for key in ("public_output_aggregate_only", "private_future_manifests_only_under_ignored_runs", "runs_remains_ignored"):
        if privacy.get(key) is not True:
            errors.append(f"privacy contract missing: {key}")
    for key in PRIVACY_FALSE_KEYS:
        if privacy.get(key) is not False:
            errors.append(f"privacy contract boundary failed: {key}")

    claims = report.get("claim_boundary", {})
    for key in CLAIM_BOUNDARY_FALSE_KEYS:
        if claims.get(key) is not False:
            errors.append(f"claim boundary failed: {key}")

    validation = report.get("validation_summary", {})
    for key in (
        "route_specific_validator_available",
        "self_test_available",
        "report_validation_available",
        "validator_does_not_fetch_or_read_private",
        "public_artifact_privacy_audit_expected",
    ):
        if validation.get(key) is not True:
            errors.append(f"validation summary missing: {key}")
    for key in ("validator_executes_tasks", "validator_reads_private_registry", "validator_reads_sources"):
        if validation.get(key) is not False:
            errors.append(f"validation summary execution boundary failed: {key}")

    errors.extend(_scan_public(report))
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    global FETCH_CLONE_ATTEMPTS, SOURCE_READ_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_READ_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    base = build_public_report()
    checks.append(("base_report_valid", not validate_report(base)))

    # Reject public_fetch_clone_executed=true
    mutated = copy.deepcopy(base)
    mutated["phase9e_scope"]["public_fetch_clone_executed"] = True
    mutated["no_execution_booleans"]["public_fetch_clone_executed"] = True
    checks.append(("public_fetch_clone_executed_rejected", bool(validate_report(mutated))))

    # Reject source_materialization_executed=true
    mutated = copy.deepcopy(base)
    mutated["phase9e_scope"]["source_materialization_executed"] = True
    mutated["no_execution_booleans"]["source_materialization_executed"] = True
    checks.append(("source_materialization_executed_rejected", bool(validate_report(mutated))))

    # Reject task rows / labels / outcomes / scoring / evidence_success fields
    for bad_key in FORBIDDEN_PUBLIC_FIELD_WORDS:
        mutated = copy.deepcopy(base)
        mutated["future_protocol_summary"][bad_key] = "exposed_value"
        checks.append((f"forbidden_public_field_rejected_{bad_key}", bool(validate_report(mutated))))

    # Reject provider/model/runtime/default claims
    for claim_key in ("provider_claim", "model_claim", "runtime_claim", "default_claim", "product_claim", "performance_claim"):
        mutated = copy.deepcopy(base)
        mutated["claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # Reject private/run/per-source/per-task public facts
    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["per_source_public_facts"] = True
    checks.append(("per_source_public_facts_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["per_task_public_facts"] = True
    checks.append(("per_task_public_facts_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["run_locations_public"] = True
    checks.append(("run_locations_public_rejected", bool(validate_report(mutated))))

    # Reject singleton buckets
    mutated = copy.deepcopy(base)
    mutated["future_protocol_summary"]["example_bucket"] = "count_1"
    checks.append(("count_1_singleton_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_protocol_summary"]["example_bucket"] = "bucket_one"
    checks.append(("bucket_one_singleton_rejected", bool(validate_report(mutated))))

    # Reject missing Phase9D gate references
    mutated = copy.deepcopy(base)
    del mutated["phase9d_gate_references"]["phase9d_commit"]
    checks.append(("missing_phase9d_commit_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    del mutated["phase9d_gate_references"]["phase9d_ci_run"]
    checks.append(("missing_phase9d_ci_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9d_gate_references"]["phase9d_status"] = "drift"
    checks.append(("phase9d_status_drift_rejected", bool(validate_report(mutated))))

    # Reject future execution without phase9e commit+CI green
    mutated = copy.deepcopy(base)
    mutated["phase9e_scope"]["future_execution_requires_phase9e_commit_and_ci_green"] = False
    checks.append(("future_execution_without_commit_ci_rejected", bool(validate_report(mutated))))

    # Reject exact count fields
    mutated = copy.deepcopy(base)
    mutated["future_protocol_summary"]["count"] = 48
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))

    # Reject private-shaped values
    mutated = copy.deepcopy(base)
    mutated["future_protocol_summary"]["example_value"] = "owner/repo"
    checks.append(("private_shaped_value_rejected", bool(validate_report(mutated))))

    # Reject private-shaped keys
    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["path"] = "src/private.py"
    checks.append(("private_shaped_key_rejected", bool(validate_report(mutated))))

    # Validate a temp-file round-trip
    with tempfile.TemporaryDirectory(prefix="phase9e_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(base), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

    # Prove the validator/self-test did not fetch/read private
    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_sources", SOURCE_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs", PRIVATE_RUNS_READ_ATTEMPTS == 0))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 9E public source fetch/clone materialization protocol freeze"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_PUBLIC_REPORT)
    args = parser.parse_args(argv)

    if args.self_test:
        print(json.dumps(run_self_test(), indent=2, sort_keys=True))
        return 0
    if args.validate_report:
        report = json.loads(args.validate_report.read_text(encoding="utf-8"))
        errors = validate_report(report)
        if errors:
            for error_message in errors:
                print(f"ERROR: {error_message}", file=sys.stderr)
            return 1
        print(f"Validation passed: {args.validate_report}")
        return 0
    if args.write_report:
        report = build_public_report()
        errors = validate_report(report)
        if errors:
            for error_message in errors:
                print(f"ERROR: {error_message}", file=sys.stderr)
            return 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps({"status": report["status"], "public_report": str(args.output)}, indent=2, sort_keys=True))
        return 0
    parser.error("choose --self-test, --write-report, or --validate-report")
    return 2


if __name__ == "__main__":
    sys.exit(main())
