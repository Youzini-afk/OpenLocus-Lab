#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, Mapping, NoReturn


SCHEMA_VERSION = "bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture.v1"
PHASE = "BEA-v1-N6X-FR"
GENERATED_BY = "bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture"
STATUS_NO_GO_LOCAL = "no_go_n6xfr_local_prerequisites_unavailable"

STATUSES = (
    "full_frozen_candidate_pool_reconstruction_capture_pass_n7_authorized",
    "full_frozen_candidate_pool_reconstruction_complete_below_threshold",
    "canary_reconstruction_pass_full40_authorized",
    "no_go_n6xfr_required_inputs_unavailable",
    STATUS_NO_GO_LOCAL,
    "no_go_n6xfr_execution_not_explicitly_enabled",
    "no_go_n6xfr_canary_failed",
    "no_go_n6xfr_case_mapping_failed",
    "no_go_n6xfr_frozen_replay_not_reproducible",
    "no_go_n6xfr_private_output_or_privacy_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path(
    "artifacts/bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture/"
    "bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture_report.json"
)

INPUTS = (
    ("n4_denominator_artifact", Path("artifacts/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit_report.json"), "fixed_pool_rank_blocker_denominator_audit_pass_n5_authorized"),
    ("n5_preflight_artifact", Path("artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json"), "fixed_pool_rank_order_experiment_preflight_pass_n6_authorized"),
    ("n6_no_go_artifact", Path("artifacts/bea_v1_n6_fixed_pool_rank_order_experiment/bea_v1_n6_fixed_pool_rank_order_experiment_report.json"), "no_go_n6_public_fixed_pool_arm_fields_insufficient"),
    ("n6f_design_artifact", Path("artifacts/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design_report.json"), "fixed_pool_public_arm_field_materialization_design_pass"),
    ("n6g_source_discovery_artifact", Path("artifacts/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit_report.json"), "no_go_n6g_candidate_sources_inexact_or_aggregate_only"),
    ("n6xr_bounded_recapture_artifact", Path("artifacts/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke_report.json"), "no_go_n6xr_requires_full_rerun_or_unavailable_mapping"),
    ("p4l_locked_scheduler_artifact", Path("artifacts/bea_v1_p4l_locked_non_python_scheduler_validation/bea_v1_p4l_locked_non_python_scheduler_validation_report.json"), "bea_v1_p4l_locked_non_python_scheduler_validation_pass"),
    ("n2_rank_pack_artifact", Path("artifacts/bea_v1_n2_rank_pack_actionability_decomposition/bea_v1_n2_rank_pack_actionability_decomposition_report.json"), "n2_rank_pack_actionability_decomposition_pass"),
)

ARMS = (
    "baseline_n2_order",
    "extra_depth_promote_before_primary_prefix_4",
    "bounded_interleave_primary2_extra1",
    "late_extra_depth_demote_after_primary_prefix_8",
)

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "source_path", "exact_path", "private_path",
    "private_paths", "filename", "filenames", "file_name", "span", "spans",
    "exact_span", "line", "lines", "start_line", "end_line", "line_range",
    "snippet", "snippets", "content", "text", "raw_text", "candidate",
    "candidates", "candidate_list", "candidate_lists", "candidate_order",
    "candidate_paths", "rank", "ranks", "raw_rank", "rank_list", "rank_lists",
    "score", "scores", "task_id", "repo", "repo_id", "repo_name", "repo_slug",
    "repo_url", "private_id", "private_record_id", "private_ids", "source_hash",
    "source_hashes", "hash", "hashes", "content_sha", "provider", "provider_payload",
    "raw_payload", "payload", "prompt", "response", "raw", "raw_diff", "diff",
})

SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "claim_level", "phase", "generated_by", "generated_at",
    "status_vocabulary", "input_artifact_bucket", "observed_status", "expected_status",
    "load_status", "forbidden_scan_status", "prerequisite_status_bucket",
    "execution_request_bucket", "canary_status_bucket", "full40_status_bucket",
    "private_output_root_bucket", "public_schema_status_bucket", "threshold_decision_bucket",
    "privacy_boundary_bucket", "public_artifact_bucket", "no_execution_boundary_bucket",
    "gate", "threshold_relation", "authorization", "next_allowed_phase",
    "next_allowed_scope_bucket", "arm_bucket", "result_status_bucket",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = _repo_root() / path
    if not full.exists():
        return {}, "missing"
    try:
        data = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (data, "pass") if isinstance(data, dict) else ({}, "parse_failed")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    full = path if path.is_absolute() else _repo_root() / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)
    digest_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)

    def walk(value: Any, marker: str = "$") -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                key_s = str(key)
                if key_s in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, marker + "." + key_s)
        elif isinstance(value, list):
            for inner in value:
                walk(inner, marker + "[]")
        elif isinstance(value, str):
            last = marker.rsplit(".", 1)[-1].split("[")[0]
            if last in SAFE_VALUE_KEYS:
                return
            if path_re.search(value):
                violations.append({"category": "path_like_value", "location_bucket": "public_artifact"})
            if line_re.search(value):
                violations.append({"category": "line_range_value", "location_bucket": "public_artifact"})
            if digest_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})

    walk(obj)
    return violations


def _scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def _load_inputs() -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    artifacts: dict[str, dict[str, Any]] = {}
    loads: dict[str, str] = {}
    for bucket, path, _expected in INPUTS:
        artifact, load = _load_json(path)
        artifacts[bucket] = artifact
        loads[bucket] = load
    return artifacts, loads


def _input_artifact_records(artifacts: Mapping[str, Mapping[str, Any]], loads: Mapping[str, str]) -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, _path, expected) in enumerate(INPUTS):
        artifact = artifacts.get(bucket, {})
        scan = artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported"
        observed = str(artifact.get("status", "") or "")
        passed = loads.get(bucket) == "pass" and observed == expected and scan == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n6xfrin{idx:04d}", "input_artifact_bucket": bucket, "load_status": str(loads.get(bucket, "missing")), "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan), "input_gate_passed_bool": passed})
    return records, ok


def _count_private_globs(root: Path) -> tuple[int, int]:
    # Deliberately do not inspect .openlocus/private inventory or serialize paths.
    # The default public preflight records unavailable local private inputs unless
    # a future caller supplies explicit prereq paths.
    _ = root
    return 0, 0


def _prerequisite_preflight_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool]:
    root = _repo_root()
    openlocus_available = bool(args.openlocus and Path(args.openlocus).exists()) or (root / "target" / "release" / "openlocus").exists()
    fd1_count, p4l_count = _count_private_globs(root)
    fd1_available = bool(args.fd1_private_decomposition_jsonl and Path(args.fd1_private_decomposition_jsonl).exists()) or fd1_count > 0
    p4l_available = p4l_count > 0
    local_ok = openlocus_available and fd1_available and p4l_available
    record = {
        "anonymous_prerequisite_preflight_id": "n6xfrpre0000",
        "prerequisite_status_bucket": "local_prerequisites_unavailable" if not local_ok else "local_prerequisites_available",
        "openlocus_binary_available_bool": openlocus_available,
        "fd1_private_decomposition_available_bool": fd1_available,
        "p4l_private_source_available_bool": p4l_available,
        "n_series_private_candidate_pool_source_count": fd1_count,
        "p4l_or_fd1_private_source_count": p4l_count,
        "network_execution_explicitly_enabled_bool": False,
        "git_clone_explicitly_enabled_bool": False,
        "private_output_root_ignored_bool": True,
        "local_prerequisites_available_bool": local_ok,
    }
    return [record], local_ok


def _execution_request_records(args: argparse.Namespace, local_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    requested = bool(args.execute_canary or args.execute_full40)
    record = {
        "anonymous_execution_request_id": "n6xfrexec0000",
        "execution_request_bucket": "explicit_request_blocked_by_missing_prerequisites" if requested and not local_ok else "default_preflight_only",
        "execute_canary_requested_bool": bool(args.execute_canary),
        "execute_full40_requested_bool": bool(args.execute_full40),
        "default_preflight_only_bool": not requested,
        "execution_attempted_bool": False,
        "canary_required_before_full40_bool": True,
    }
    return [record], not requested


def _canary_reconstruction_records(args: argparse.Namespace, local_ok: bool) -> list[dict[str, Any]]:
    requested = bool(args.execute_canary)
    status = "not_executed_local_prerequisites_unavailable" if requested and not local_ok else "not_requested_preflight_only"
    return [{"anonymous_canary_reconstruction_id": "n6xfrcanary0000", "canary_status_bucket": status, "canary_case_limit": 2, "canary_executed_bool": False, "canary_passed_bool": False, "full40_authorized_bool": False}]


def _full40_capture_records() -> list[dict[str, Any]]:
    return [{"anonymous_full40_capture_id": "n6xfrfull0000", "full40_status_bucket": "not_executed_preflight_or_missing_prerequisites", "full40_executed_bool": False, "case_count": 40, "arm_count": 4, "public_arm_outcome_rows": 0, "private_candidate_diagnostics_written": 0}]


def _private_output_boundary_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_private_output_boundary_id": "n6xfrout0000", "private_output_root_bucket": "project_ignored_research_private", "private_output_root_ignored_bool": True, "private_paths_publicly_serialized_bool": False, "private_file_names_publicly_serialized_bool": False, "private_output_root_supplied_bool": bool(args.private_output_root)}
    return [record], True


def _public_schema_boundary_records() -> list[dict[str, Any]]:
    return [{"anonymous_public_schema_boundary_id": "n6xfrschema0000", "public_schema_status_bucket": "not_evaluated_no_materialization", "n6f_required_public_rows": 160, "public_rows_materialized": 0, "public_rows_match_n6f_schema_bool": False}]


def _no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_no_forbidden_execution_id": "n6xfrnoexec0000", "no_execution_boundary_bucket": "default_preflight_no_replay", "network_execution_count": 0, "git_clone_count": 0, "openlocus_binary_execution_count": 0, "p4l_rerun_count": 0, "n1_n2_n3_rerun_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "counterfactual_execution_count": 0, "no_forbidden_execution_complete_bool": True}
    return [record], True


def _per_arm_result_records() -> list[dict[str, Any]]:
    return [{"anonymous_per_arm_result_id": f"n6xfrarm{idx:04d}", "arm_bucket": arm, "result_status_bucket": "not_evaluated_no_full_frozen_capture", "evaluated_case_count": 0, "expected_case_count": 40, "candidate_pool_available_bool": False, "top10_recovery_count": None, "case_regression_count": None} for idx, arm in enumerate(ARMS)]


def _threshold_decision_records() -> list[dict[str, Any]]:
    return [{"anonymous_threshold_decision_id": "n6xfrtd0000", "threshold_decision_bucket": "not_evaluated_local_prerequisites_unavailable", "evaluated_arm_count": 0, "passing_arm_count": 0, "n7_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def _privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_privacy_boundary_id": "n6xfrpb0000", "privacy_boundary_bucket": "public_bucket_only_preflight", "public_artifact_bucket": "buckets_counts_booleans_only", "private_file_content_read_bool": False, "raw_candidate_public_bool": False, "raw_rank_public_bool": False, "path_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "private_identifier_public_bool": False, "privacy_boundary_complete_bool": True}
    return [record], True


def _gate_records(*, input_ok: bool, local_ok: bool, request_default: bool, output_ok: bool, noexec_ok: bool, privacy_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    return [
        {"gate": "required_inputs_load_and_scan", "passed": input_ok, "threshold_relation": "equals", "value": int(input_ok), "threshold_value": 1},
        {"gate": "local_prerequisites_available", "passed": local_ok, "threshold_relation": "equals", "value": int(local_ok), "threshold_value": 1},
        {"gate": "default_preflight_only_or_explicit_request_blocked", "passed": request_default or not local_ok, "threshold_relation": "equals", "value": int(request_default or not local_ok), "threshold_value": 1},
        {"gate": "private_output_boundary_safe", "passed": output_ok, "threshold_relation": "equals", "value": int(output_ok), "threshold_value": 1},
        {"gate": "no_forbidden_execution", "passed": noexec_ok, "threshold_relation": "equals", "value": int(noexec_ok), "threshold_value": 1},
        {"gate": "privacy_boundary_complete", "passed": privacy_ok, "threshold_relation": "equals", "value": int(privacy_ok), "threshold_value": 1},
        {"gate": "scanner_pass", "passed": scanner_ok, "threshold_relation": "equals", "value": int(scanner_ok), "threshold_value": 1},
    ]


def _stop_go_records(status: str) -> list[dict[str, Any]]:
    pass_status = status == "full_frozen_candidate_pool_reconstruction_capture_pass_n7_authorized"
    return [{"authorization": "full_frozen_candidate_pool_reconstruction_preflight_no_go" if not pass_status else "full_frozen_candidate_pool_reconstruction_capture_pass", "next_allowed_phase": "BEA-v1-N7 Fixed-Pool Rank-Order Result Audit" if pass_status else "none_until_full_frozen_reconstruction_prerequisites_are_available", "next_allowed_scope_bucket": "no_next_phase_local_prerequisites_missing" if not pass_status else "n7_result_audit_only", "n7_authorized": pass_status, "canary_authorized": False, "full40_authorized": False, "retrieval_authorized": False, "full_rerun_authorized": False, "network_authorized": False, "git_clone_authorized": False, "openlocus_binary_execution_authorized": False, "private_read_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "selector_or_reranker_authorized": False, "counterfactual_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "runtime_or_policy_change_authorized": False, "method_winner_claimed": False, "method_winner_claim_authorized": False, "downstream_value_claimed": False, "downstream_value_claim_authorized": False}]


def _status_from(*, self_ok: bool, input_ok: bool, local_ok: bool, output_ok: bool, noexec_ok: bool, privacy_ok: bool, request_default: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n6xfr_required_inputs_unavailable"
    if not output_ok or not privacy_ok or not noexec_ok:
        return "no_go_n6xfr_private_output_or_privacy_failed"
    if not local_ok:
        return STATUS_NO_GO_LOCAL
    if request_default:
        return "no_go_n6xfr_execution_not_explicitly_enabled"
    return "no_go_n6xfr_frozen_replay_not_reproducible"


def _build_report(checks: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    start = time.perf_counter()
    artifacts, loads = _load_inputs()
    input_records, input_ok = _input_artifact_records(artifacts, loads)
    prereq_records, local_ok = _prerequisite_preflight_records(args)
    request_records, request_default = _execution_request_records(args, local_ok)
    canary_records = _canary_reconstruction_records(args, local_ok)
    full40_records = _full40_capture_records()
    output_records, output_ok = _private_output_boundary_records(args)
    schema_records = _public_schema_boundary_records()
    noexec_records, noexec_ok = _no_forbidden_execution_records()
    threshold_records = _threshold_decision_records()
    privacy_records, privacy_ok = _privacy_boundary_records()
    self_ok = all(c["passed"] for c in checks)
    status = _status_from(self_ok=self_ok, input_ok=input_ok, local_ok=local_ok, output_ok=output_ok, noexec_ok=noexec_ok, privacy_ok=privacy_ok, request_default=request_default)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "status": status, "claim_level": "full_frozen_candidate_pool_reconstruction_capture_preflight_only", "phase": PHASE, "generated_by": GENERATED_BY, "generated_at": _now_iso(), "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records, "prerequisite_preflight_records": prereq_records, "execution_request_records": request_records, "canary_reconstruction_records": canary_records, "full40_capture_records": full40_records, "private_output_boundary_records": output_records, "public_schema_boundary_records": schema_records, "no_forbidden_execution_records": noexec_records, "per_arm_result_records": _per_arm_result_records(), "threshold_decision_records": threshold_records, "privacy_boundary_records": privacy_records,
        "gate_records": _gate_records(input_ok=input_ok, local_ok=local_ok, request_default=request_default, output_ok=output_ok, noexec_ok=noexec_ok, privacy_ok=privacy_ok, scanner_ok=True),
        "stop_go_records": _stop_go_records(status), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False,
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = _scan_summary(report)
    report["forbidden_scan"] = final_scan
    scanner_ok = final_scan["status"] == "pass"
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    report["gate_records"] = _gate_records(input_ok=input_ok, local_ok=local_ok, request_default=request_default, output_ok=output_ok, noexec_ok=noexec_ok, privacy_ok=privacy_ok, scanner_ok=scanner_ok)
    report["stop_go_records"] = _stop_go_records(report["status"])
    return report


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--unknown", "SECRET_VALUE"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET_VALUE" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    parser = build_parser()
    args = parser.parse_args([])
    artifacts, loads = _load_inputs()
    input_records, input_ok = _input_artifact_records(artifacts, loads)
    prereq_records, local_ok = _prerequisite_preflight_records(args)
    request_records, request_default = _execution_request_records(args, local_ok)
    output_records, output_ok = _private_output_boundary_records(args)
    noexec_records, noexec_ok = _no_forbidden_execution_records()
    privacy_records, privacy_ok = _privacy_boundary_records()
    checks = [
        _check("status_vocabulary_exact", tuple(STATUSES) == ("full_frozen_candidate_pool_reconstruction_capture_pass_n7_authorized", "full_frozen_candidate_pool_reconstruction_complete_below_threshold", "canary_reconstruction_pass_full40_authorized", "no_go_n6xfr_required_inputs_unavailable", STATUS_NO_GO_LOCAL, "no_go_n6xfr_execution_not_explicitly_enabled", "no_go_n6xfr_canary_failed", "no_go_n6xfr_case_mapping_failed", "no_go_n6xfr_frozen_replay_not_reproducible", "no_go_n6xfr_private_output_or_privacy_failed", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_forbidden_keys", all(_scan_summary({key: "blocked"})["status"] == "fail" for key in ("path", "span", "snippet", "candidate_list", "rank", "task_id", "repo", "private_id", "source_hash", "provider_payload", "raw_diff", "filename"))),
        _check("scanner_rejects_path_and_digest_values", _scan_summary({"safe": "src/lib.rs"})["status"] == "fail" and _scan_summary({"safe": "a" * 40})["status"] == "fail"),
        _check("inputs", input_ok and len(input_records) == 8 and all(r["input_gate_passed_bool"] for r in input_records)),
        _check("default_prerequisites_unavailable", local_ok is False and prereq_records[0]["local_prerequisites_available_bool"] is False),
        _check("prereq_fields_present", all(k in prereq_records[0] for k in ("openlocus_binary_available_bool", "fd1_private_decomposition_available_bool", "p4l_private_source_available_bool", "network_execution_explicitly_enabled_bool", "git_clone_explicitly_enabled_bool", "private_output_root_ignored_bool"))),
        _check("network_git_disabled", prereq_records[0]["network_execution_explicitly_enabled_bool"] is False and prereq_records[0]["git_clone_explicitly_enabled_bool"] is False),
        _check("execution_request_default", request_default and request_records[0]["default_preflight_only_bool"] is True and request_records[0]["execution_attempted_bool"] is False),
        _check("canary_not_executed", _canary_reconstruction_records(args, local_ok)[0]["canary_case_limit"] == 2 and _canary_reconstruction_records(args, local_ok)[0]["canary_executed_bool"] is False),
        _check("full40_not_executed", _full40_capture_records()[0]["full40_executed_bool"] is False and _full40_capture_records()[0]["case_count"] == 40 and _full40_capture_records()[0]["arm_count"] == 4 and _full40_capture_records()[0]["public_arm_outcome_rows"] == 0),
        _check("private_output_boundary", output_ok and output_records[0]["private_paths_publicly_serialized_bool"] is False and output_records[0]["private_file_names_publicly_serialized_bool"] is False),
        _check("public_schema_boundary", _public_schema_boundary_records()[0]["n6f_required_public_rows"] == 160 and _public_schema_boundary_records()[0]["public_rows_materialized"] == 0 and _public_schema_boundary_records()[0]["public_rows_match_n6f_schema_bool"] is False),
        _check("no_forbidden_execution", noexec_ok and all(noexec_records[0][k] == 0 for k in ("network_execution_count", "git_clone_count", "openlocus_binary_execution_count", "p4l_rerun_count", "n1_n2_n3_rerun_count", "selector_reranker_execution_count", "p5_execution_count", "v1a_execution_count", "runtime_change_count"))),
        _check("threshold_not_evaluated", _threshold_decision_records()[0]["threshold_decision_bucket"] == "not_evaluated_local_prerequisites_unavailable" and _threshold_decision_records()[0]["n7_authorized_bool"] is False),
        _check("privacy_boundary", privacy_ok and privacy_records[0]["raw_candidate_public_bool"] is False and privacy_records[0]["raw_rank_public_bool"] is False and privacy_records[0]["private_identifier_public_bool"] is False),
        _check("status_expected", _status_from(self_ok=True, input_ok=True, local_ok=False, output_ok=True, noexec_ok=True, privacy_ok=True, request_default=True) == STATUS_NO_GO_LOCAL),
        _check("stop_go_no_go", _stop_go_records(STATUS_NO_GO_LOCAL)[0]["next_allowed_phase"] == "none_until_full_frozen_reconstruction_prerequisites_are_available" and _stop_go_records(STATUS_NO_GO_LOCAL)[0]["n7_authorized"] is False and _stop_go_records(STATUS_NO_GO_LOCAL)[0]["canary_authorized"] is False and _stop_go_records(STATUS_NO_GO_LOCAL)[0]["full_rerun_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N6X-FR full-frozen reconstruction capture preflight")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--execute-canary", action="store_true")
    parser.add_argument("--execute-full-40", dest="execute_full40", action="store_true")
    parser.add_argument("--openlocus", type=Path)
    parser.add_argument("--fd1-private-decomposition-jsonl", type=Path)
    parser.add_argument("--private-output-root", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = _build_report(checks, args)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    prereq = report["prerequisite_preflight_records"][0]
    print("wrote artifact " f"(status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, " f"openlocus={prereq['openlocus_binary_available_bool']}, local_prereqs={prereq['local_prerequisites_available_bool']})")


if __name__ == "__main__":
    main()
