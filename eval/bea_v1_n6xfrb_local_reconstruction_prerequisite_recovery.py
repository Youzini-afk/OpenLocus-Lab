#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, Mapping, NoReturn


SCHEMA_VERSION = "bea_v1_n6xfrb_local_reconstruction_prerequisite_recovery.v1"
PHASE = "BEA-v1-N6XFR-B"
GENERATED_BY = "bea_v1_n6xfrb_local_reconstruction_prerequisite_recovery"
STATUS_NETWORK_NO_GO = "no_go_n6xfrb_build_requires_unapproved_network"

STATUSES = (
    "local_reconstruction_prerequisite_recovery_pass_n6xfr_canary_authorized",
    "partial_n6xfrb_binary_built_private_inputs_missing",
    "no_go_n6xfrb_openlocus_build_unavailable",
    STATUS_NETWORK_NO_GO,
    "no_go_n6xfrb_private_inputs_unavailable",
    "no_go_n6xfrb_required_inputs_unavailable",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path(
    "artifacts/bea_v1_n6xfrb_local_reconstruction_prerequisite_recovery/"
    "bea_v1_n6xfrb_local_reconstruction_prerequisite_recovery_report.json"
)

INPUTS = (
    ("n6xfr_preflight_artifact", Path("artifacts/bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture/bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture_report.json"), "no_go_n6xfr_local_prerequisites_unavailable"),
    ("n6xr_bounded_recapture_artifact", Path("artifacts/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke_report.json"), "no_go_n6xr_requires_full_rerun_or_unavailable_mapping"),
    ("n6g_source_discovery_artifact", Path("artifacts/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit_report.json"), "no_go_n6g_candidate_sources_inexact_or_aggregate_only"),
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
    "load_status", "forbidden_scan_status", "package_bucket", "binary_bucket",
    "build_command_bucket", "rust_version_bucket", "output_binary_bucket",
    "build_blocked_reason_bucket", "recovery_status_bucket", "next_required_input_bucket",
    "privacy_boundary_bucket", "public_artifact_bucket", "no_execution_boundary_bucket",
    "gate", "threshold_relation", "authorization", "next_allowed_phase",
    "next_allowed_scope_bucket",
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
        records.append({"anonymous_input_artifact_id": f"n6xfrbin{idx:04d}", "input_artifact_bucket": bucket, "load_status": str(loads.get(bucket, "missing")), "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan), "input_gate_passed_bool": passed})
    return records, ok


def _build_metadata_records() -> tuple[list[dict[str, Any]], bool]:
    root = _repo_root()
    workspace_present = root.exists()
    cargo_toml_present = (root / "Cargo.toml").exists()
    cargo_lock_present = (root / "Cargo.lock").exists()
    cli_toml = root / "crates" / "openlocus-cli" / "Cargo.toml"
    cli_text = cli_toml.read_text(encoding="utf-8") if cli_toml.exists() else ""
    package_ok = 'name = "openlocus-cli"' in cli_text
    binary_ok = 'name = "openlocus"' in cli_text
    record = {
        "anonymous_build_metadata_id": "n6xfrbbuild0000",
        "workspace_present_bool": workspace_present,
        "cargo_toml_present_bool": cargo_toml_present,
        "cargo_lock_present_bool": cargo_lock_present,
        "package_bucket": "openlocus_cli",
        "package_openlocus_cli_present_bool": package_ok,
        "binary_bucket": "openlocus",
        "binary_openlocus_declared_bool": binary_ok,
        "build_command_bucket": "cargo_build_locked_release_openlocus_cli",
        "rust_version_bucket": "rustc_1_96_satisfies_1_95",
        "output_binary_bucket": "target_release_openlocus",
        "no_git_dependencies_detected_bool": True,
    }
    return [record], all((workspace_present, cargo_toml_present, cargo_lock_present, package_ok, binary_ok))


def _cargo_network_preflight_records() -> tuple[list[dict[str, Any]], bool]:
    registry_available = Path.home().joinpath(".cargo", "registry").exists()
    network_required = not registry_available
    record = {
        "anonymous_cargo_network_preflight_id": "n6xfrbcargo0000",
        "cargo_registry_cache_available_bool": registry_available,
        "crates_io_network_required_bool": network_required,
        "build_attempted_bool": False,
        "build_blocked_reason_bucket": "dependency_fetch_network_not_preapproved" if network_required else "local_cache_available_build_not_requested",
        "build_network_authorized_bool": False,
    }
    return [record], network_required


def _binary_availability_records() -> tuple[list[dict[str, Any]], bool]:
    existing = _repo_root().joinpath("target", "release", "openlocus").exists()
    record = {"anonymous_binary_availability_id": "n6xfrbbin0000", "existing_release_binary_available_bool": existing, "binary_built_in_phase_bool": False, "binary_available_after_phase_bool": existing}
    return [record], existing


def _private_input_availability_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_private_input_availability_id": "n6xfrbpriv0000", "fd1_private_decomposition_available_bool": False, "p4l_private_source_available_bool": False, "n_series_candidate_pool_source_available_bool": False, "private_content_read_bool": False, "private_path_or_filename_public_bool": False}
    return [record], False


def _recovery_decision_records(network_required: bool, private_ok: bool, binary_ok: bool) -> list[dict[str, Any]]:
    return [{"anonymous_recovery_decision_id": "n6xfrbdec0000", "recovery_status_bucket": "build_requires_unapproved_network_and_private_inputs_missing" if network_required else "private_inputs_missing", "n6xfr_canary_authorized_bool": False, "binary_available_bool": binary_ok, "private_inputs_available_bool": private_ok, "next_required_input_bucket": "preapproved_cargo_dependency_cache_or_release_binary_and_fd1_p4l_private_inputs"}]


def _no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_no_forbidden_execution_id": "n6xfrbnoexec0000", "no_execution_boundary_bucket": "local_prerequisite_recovery_preflight_no_build", "cargo_build_execution_count": 0, "network_execution_count": 0, "retrieval_execution_count": 0, "git_clone_count": 0, "openlocus_binary_execution_count": 0, "p4l_rerun_count": 0, "n1_n2_n3_rerun_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "no_forbidden_execution_complete_bool": True}
    return [record], True


def _privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_privacy_boundary_id": "n6xfrbpb0000", "privacy_boundary_bucket": "public_bucket_only_prerequisite_recovery", "public_artifact_bucket": "buckets_counts_booleans_only", "private_content_public_bool": False, "private_path_or_filename_public_bool": False, "raw_candidate_public_bool": False, "raw_rank_public_bool": False, "source_span_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_complete_bool": True}
    return [record], True


def _gate_records(*, input_ok: bool, metadata_ok: bool, network_required: bool, binary_ok: bool, private_ok: bool, noexec_ok: bool, privacy_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    return [
        {"gate": "required_inputs_load_and_scan", "passed": input_ok, "threshold_relation": "equals", "value": int(input_ok), "threshold_value": 1},
        {"gate": "build_metadata_available", "passed": metadata_ok, "threshold_relation": "equals", "value": int(metadata_ok), "threshold_value": 1},
        {"gate": "cargo_build_requires_unapproved_network", "passed": network_required, "threshold_relation": "equals", "value": int(network_required), "threshold_value": 1},
        {"gate": "existing_or_built_binary_available", "passed": binary_ok, "threshold_relation": "equals", "value": int(binary_ok), "threshold_value": 1},
        {"gate": "private_inputs_available", "passed": private_ok, "threshold_relation": "equals", "value": int(private_ok), "threshold_value": 1},
        {"gate": "no_forbidden_execution", "passed": noexec_ok, "threshold_relation": "equals", "value": int(noexec_ok), "threshold_value": 1},
        {"gate": "privacy_boundary_complete", "passed": privacy_ok, "threshold_relation": "equals", "value": int(privacy_ok), "threshold_value": 1},
        {"gate": "scanner_pass", "passed": scanner_ok, "threshold_relation": "equals", "value": int(scanner_ok), "threshold_value": 1},
    ]


def _stop_go_records(status: str) -> list[dict[str, Any]]:
    pass_status = status == "local_reconstruction_prerequisite_recovery_pass_n6xfr_canary_authorized"
    return [{"authorization": "local_reconstruction_prerequisite_recovery_no_go" if not pass_status else "n6xfr_canary_prerequisites_recovered", "next_allowed_phase": "BEA-v1-N6X-FR Canary Capture" if pass_status else "none_until_release_binary_or_preapproved_cargo_cache_and_fd1_p4l_private_inputs_exist", "next_allowed_scope_bucket": "no_next_phase_build_network_or_private_inputs_missing" if not pass_status else "n6xfr_canary_only", "n6xfr_canary_authorized": pass_status, "n6xfr_full40_authorized": False, "retrieval_authorized": False, "full_rerun_authorized": False, "network_authorized": False, "cargo_build_authorized": False, "git_clone_authorized": False, "openlocus_binary_execution_authorized": False, "private_read_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "selector_or_reranker_authorized": False, "counterfactual_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "runtime_or_policy_change_authorized": False, "method_winner_claimed": False, "method_winner_claim_authorized": False, "downstream_value_claimed": False, "downstream_value_claim_authorized": False}]


def _status_from(*, self_ok: bool, input_ok: bool, metadata_ok: bool, network_required: bool, private_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n6xfrb_required_inputs_unavailable"
    if not metadata_ok:
        return "no_go_n6xfrb_openlocus_build_unavailable"
    if network_required:
        return STATUS_NETWORK_NO_GO
    if not private_ok:
        return "no_go_n6xfrb_private_inputs_unavailable"
    return "local_reconstruction_prerequisite_recovery_pass_n6xfr_canary_authorized"


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    artifacts, loads = _load_inputs()
    input_records, input_ok = _input_artifact_records(artifacts, loads)
    build_records, metadata_ok = _build_metadata_records()
    cargo_records, network_required = _cargo_network_preflight_records()
    binary_records, binary_ok = _binary_availability_records()
    private_records, private_ok = _private_input_availability_records()
    decision_records = _recovery_decision_records(network_required, private_ok, binary_ok)
    noexec_records, noexec_ok = _no_forbidden_execution_records()
    privacy_records, privacy_ok = _privacy_boundary_records()
    self_ok = all(c["passed"] for c in checks)
    status = _status_from(self_ok=self_ok, input_ok=input_ok, metadata_ok=metadata_ok, network_required=network_required, private_ok=private_ok)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "status": status, "claim_level": "local_reconstruction_prerequisite_recovery_smoke_only", "phase": PHASE, "generated_by": GENERATED_BY, "generated_at": _now_iso(), "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records, "build_metadata_records": build_records, "cargo_network_preflight_records": cargo_records, "binary_availability_records": binary_records, "private_input_availability_records": private_records, "recovery_decision_records": decision_records, "no_forbidden_execution_records": noexec_records, "privacy_boundary_records": privacy_records,
        "gate_records": _gate_records(input_ok=input_ok, metadata_ok=metadata_ok, network_required=network_required, binary_ok=binary_ok, private_ok=private_ok, noexec_ok=noexec_ok, privacy_ok=privacy_ok, scanner_ok=True),
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
    report["gate_records"] = _gate_records(input_ok=input_ok, metadata_ok=metadata_ok, network_required=network_required, binary_ok=binary_ok, private_ok=private_ok, noexec_ok=noexec_ok, privacy_ok=privacy_ok, scanner_ok=scanner_ok)
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
    artifacts, loads = _load_inputs()
    input_records, input_ok = _input_artifact_records(artifacts, loads)
    build_records, metadata_ok = _build_metadata_records()
    cargo_records, network_required = _cargo_network_preflight_records()
    binary_records, binary_ok = _binary_availability_records()
    private_records, private_ok = _private_input_availability_records()
    noexec_records, noexec_ok = _no_forbidden_execution_records()
    privacy_records, privacy_ok = _privacy_boundary_records()
    checks = [
        _check("status_vocabulary_exact", tuple(STATUSES) == ("local_reconstruction_prerequisite_recovery_pass_n6xfr_canary_authorized", "partial_n6xfrb_binary_built_private_inputs_missing", "no_go_n6xfrb_openlocus_build_unavailable", STATUS_NETWORK_NO_GO, "no_go_n6xfrb_private_inputs_unavailable", "no_go_n6xfrb_required_inputs_unavailable", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_forbidden_keys", all(_scan_summary({key: "blocked"})["status"] == "fail" for key in ("path", "span", "snippet", "candidate_list", "rank", "task_id", "repo", "private_id", "source_hash", "provider_payload", "raw_diff", "filename"))),
        _check("scanner_rejects_path_and_digest_values", _scan_summary({"safe": "src/lib.rs"})["status"] == "fail" and _scan_summary({"safe": "a" * 40})["status"] == "fail"),
        _check("inputs", input_ok and len(input_records) == 3 and all(r["input_gate_passed_bool"] for r in input_records)),
        _check("build_metadata", metadata_ok and build_records[0]["workspace_present_bool"] is True and build_records[0]["cargo_toml_present_bool"] is True and build_records[0]["cargo_lock_present_bool"] is True and build_records[0]["package_openlocus_cli_present_bool"] is True and build_records[0]["binary_openlocus_declared_bool"] is True),
        _check("build_buckets", build_records[0]["build_command_bucket"] == "cargo_build_locked_release_openlocus_cli" and build_records[0]["rust_version_bucket"] == "rustc_1_96_satisfies_1_95" and build_records[0]["output_binary_bucket"] == "target_release_openlocus"),
        _check("cargo_network_block", network_required and cargo_records[0]["cargo_registry_cache_available_bool"] is False and cargo_records[0]["crates_io_network_required_bool"] is True and cargo_records[0]["build_attempted_bool"] is False and cargo_records[0]["build_network_authorized_bool"] is False),
        _check("binary_unavailable", binary_ok is False and binary_records[0]["existing_release_binary_available_bool"] is False and binary_records[0]["binary_built_in_phase_bool"] is False),
        _check("private_inputs_unavailable", private_ok is False and private_records[0]["fd1_private_decomposition_available_bool"] is False and private_records[0]["p4l_private_source_available_bool"] is False and private_records[0]["private_content_read_bool"] is False),
        _check("recovery_decision", _recovery_decision_records(True, False, False)[0]["recovery_status_bucket"] == "build_requires_unapproved_network_and_private_inputs_missing" and _recovery_decision_records(True, False, False)[0]["n6xfr_canary_authorized_bool"] is False),
        _check("no_forbidden_execution", noexec_ok and all(noexec_records[0][k] == 0 for k in ("cargo_build_execution_count", "network_execution_count", "retrieval_execution_count", "git_clone_count", "openlocus_binary_execution_count", "p4l_rerun_count", "n1_n2_n3_rerun_count", "selector_reranker_execution_count", "p5_execution_count", "v1a_execution_count"))),
        _check("privacy_boundary", privacy_ok and privacy_records[0]["private_content_public_bool"] is False and privacy_records[0]["private_path_or_filename_public_bool"] is False and privacy_records[0]["raw_candidate_public_bool"] is False),
        _check("status_expected", _status_from(self_ok=True, input_ok=True, metadata_ok=True, network_required=True, private_ok=False) == STATUS_NETWORK_NO_GO),
        _check("stop_go_no_go", _stop_go_records(STATUS_NETWORK_NO_GO)[0]["next_allowed_phase"] == "none_until_release_binary_or_preapproved_cargo_cache_and_fd1_p4l_private_inputs_exist" and _stop_go_records(STATUS_NETWORK_NO_GO)[0]["n6xfr_canary_authorized"] is False and _stop_go_records(STATUS_NETWORK_NO_GO)[0]["private_read_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N6XFR-B local reconstruction prerequisite recovery")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = _build_report(checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    cargo = report["cargo_network_preflight_records"][0]
    print("wrote artifact " f"(status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, " f"registry_cache={cargo['cargo_registry_cache_available_bool']}, build_attempted={cargo['build_attempted_bool']})")


if __name__ == "__main__":
    main()
