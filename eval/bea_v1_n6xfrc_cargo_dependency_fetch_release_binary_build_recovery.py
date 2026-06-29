#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Mapping, NoReturn


SCHEMA_VERSION = "bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery.v1"
PHASE = "BEA-v1-N6XFR-C"
GENERATED_BY = "bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery"
STATUS_PARTIAL = "partial_n6xfrc_binary_built_private_inputs_missing"
STATUS_PASS = "n6xfrc_release_binary_build_pass_n6xfr_prereq_rerun_authorized"

STATUSES = (
    STATUS_PASS,
    STATUS_PARTIAL,
    "no_go_n6xfrc_required_inputs_unavailable",
    "no_go_n6xfrc_cargo_build_failed",
    "no_go_n6xfrc_build_network_out_of_scope",
    "no_go_n6xfrc_binary_missing_after_build",
    "no_go_n6xfrc_private_inputs_missing",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path(
    "artifacts/bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery/"
    "bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery_report.json"
)

N6XFRB_INPUT = (
    "n6xfrb_prerequisite_recovery_artifact",
    Path(
        "artifacts/bea_v1_n6xfrb_local_reconstruction_prerequisite_recovery/"
        "bea_v1_n6xfrb_local_reconstruction_prerequisite_recovery_report.json"
    ),
    "no_go_n6xfrb_build_requires_unapproved_network",
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
    "log", "logs",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "claim_level", "phase", "generated_by", "generated_at",
    "status_vocabulary", "input_artifact_bucket", "observed_status", "expected_status",
    "load_status", "forbidden_scan_status", "command_bucket", "cargo_exit_code_bucket",
    "duration_bucket", "network_scope_bucket", "private_input_count_bucket",
    "privacy_boundary_bucket", "public_artifact_bucket", "no_execution_boundary_bucket",
    "gate", "threshold_relation", "authorization", "next_allowed_phase",
    "next_allowed_scope_bucket", "build_status_bucket", "binary_bucket",
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


def _input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    bucket, path, expected = N6XFRB_INPUT
    artifact, load = _load_json(path)
    scan = artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported"
    observed = str(artifact.get("status", "") or "")
    passed = load == "pass" and observed == expected and scan == "pass"
    return [{"anonymous_input_artifact_id": "n6xfrcin0000", "input_artifact_bucket": bucket, "load_status": load, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan), "input_gate_passed_bool": passed}], passed


def _release_binary_exists() -> bool:
    return _repo_root().joinpath("target", "release", "openlocus").exists()


def _duration_bucket(seconds: float) -> str:
    if seconds < 30:
        return "duration_lt_30s"
    if seconds < 120:
        return "duration_30s_to_120s"
    if seconds < 600:
        return "duration_120s_to_600s"
    return "duration_ge_600s"


def _run_cargo_build() -> dict[str, Any]:
    before = _release_binary_exists()
    start = time.perf_counter()
    exit_code = 124
    timed_out = False
    try:
        proc = subprocess.run(
            ["cargo", "build", "--locked", "--release", "-p", "openlocus-cli"],
            cwd=_repo_root(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=1800,
        )
        exit_code = int(proc.returncode)
    except subprocess.TimeoutExpired:
        timed_out = True
    duration = time.perf_counter() - start
    after = _release_binary_exists()
    success = exit_code == 0 and not timed_out
    return {
        "before": before,
        "after": after,
        "exit_code": exit_code,
        "success": success,
        "timed_out": timed_out,
        "duration_bucket": _duration_bucket(duration),
        "built_in_phase": (not before) and after and success,
    }


def _cargo_build_execution_records(build: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{
        "anonymous_cargo_build_execution_id": "n6xfrcbuild0000",
        "command_bucket": "cargo_build_locked_release_openlocus_cli",
        "build_status_bucket": "cargo_build_success" if build["success"] else "cargo_build_failed",
        "build_attempted_bool": True,
        "cargo_exit_code_bucket": "zero" if build["exit_code"] == 0 else "nonzero",
        "cargo_success_bool": bool(build["success"]),
        "raw_log_public_bool": False,
        "openlocus_binary_executed_bool": False,
        "duration_bucket": str(build["duration_bucket"]),
        "build_timed_out_bool": bool(build["timed_out"]),
    }]


def _binary_availability_records(build: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{
        "anonymous_binary_availability_id": "n6xfrcbin0000",
        "binary_bucket": "target_release_openlocus",
        "release_binary_exists_before_bool": bool(build["before"]),
        "release_binary_exists_after_bool": bool(build["after"]),
        "binary_built_in_phase_bool": bool(build["built_in_phase"]),
        "binary_available_after_recovery_bool": bool(build["success"] and build["after"]),
        "binary_created_during_this_invocation_bool": bool(build["built_in_phase"]),
    }]


def _network_scope_records() -> list[dict[str, Any]]:
    return [{"anonymous_network_scope_id": "n6xfrcnet0000", "network_scope_bucket": "crates_io_dependency_fetch_only", "crates_io_dependency_fetch_scope_bool": True, "benchmark_repo_network_bool": False, "git_clone_bool": False}]


def _private_input_bucket_records() -> tuple[list[dict[str, Any]], bool]:
    # Do not read private content or serialize paths/names. Current checkpoint records unavailable.
    record = {
        "anonymous_private_input_bucket_id": "n6xfrcpriv0000",
        "fd1_private_decomposition_available_bool": False,
        "p4l_private_source_available_bool": False,
        "n_series_candidate_pool_source_available_bool": False,
        "fd1_private_input_count_bucket": "zero",
        "p4l_private_input_count_bucket": "zero",
        "n_series_private_input_count_bucket": "zero",
        "private_content_read_bool": False,
        "private_path_or_filename_public_bool": False,
    }
    return [record], False


def _no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_no_forbidden_execution_id": "n6xfrcnoexec0000", "no_execution_boundary_bucket": "cargo_build_only_no_replay", "retrieval_execution_count": 0, "openlocus_binary_execution_count": 0, "p4l_n1_n2_n3_rerun_count": 0, "candidate_pool_generation_count": 0, "candidate_pool_materialization_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "benchmark_repo_clone_count": 0, "no_forbidden_execution_complete_bool": True}
    return [record], True


def _privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_privacy_boundary_id": "n6xfrcpb0000", "privacy_boundary_bucket": "scanner_safe_build_summary_only", "public_artifact_bucket": "buckets_counts_booleans_only", "raw_cargo_log_public_bool": False, "private_content_public_bool": False, "private_path_or_filename_public_bool": False, "raw_candidate_public_bool": False, "raw_rank_public_bool": False, "source_span_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_complete_bool": True}
    return [record], True


def _status_from(*, self_ok: bool, input_ok: bool, build_success: bool, binary_after: bool, private_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n6xfrc_required_inputs_unavailable"
    if not build_success:
        return "no_go_n6xfrc_cargo_build_failed"
    if not binary_after:
        return "no_go_n6xfrc_binary_missing_after_build"
    if not private_ok:
        return STATUS_PARTIAL
    return STATUS_PASS


def _gate_records(*, input_ok: bool, build_success: bool, binary_after: bool, private_ok: bool, noexec_ok: bool, privacy_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    return [
        {"gate": "required_inputs_load_and_scan", "passed": input_ok, "threshold_relation": "equals", "value": int(input_ok), "threshold_value": 1},
        {"gate": "cargo_build_success", "passed": build_success, "threshold_relation": "equals", "value": int(build_success), "threshold_value": 1},
        {"gate": "release_binary_exists_after_build", "passed": binary_after, "threshold_relation": "equals", "value": int(binary_after), "threshold_value": 1},
        {"gate": "private_inputs_available", "passed": private_ok, "threshold_relation": "equals", "value": int(private_ok), "threshold_value": 1},
        {"gate": "no_forbidden_execution", "passed": noexec_ok, "threshold_relation": "equals", "value": int(noexec_ok), "threshold_value": 1},
        {"gate": "privacy_boundary_complete", "passed": privacy_ok, "threshold_relation": "equals", "value": int(privacy_ok), "threshold_value": 1},
        {"gate": "scanner_pass", "passed": scanner_ok, "threshold_relation": "equals", "value": int(scanner_ok), "threshold_value": 1},
    ]


def _stop_go_records(status: str) -> list[dict[str, Any]]:
    pass_status = status == STATUS_PASS
    partial_status = status == STATUS_PARTIAL
    return [{
        "authorization": "release_binary_build_recovery_partial" if partial_status else ("release_binary_build_recovery_pass" if pass_status else "release_binary_build_recovery_no_go"),
        "next_allowed_phase": "BEA-v1-N6X-FR Prerequisite Rerun" if pass_status else ("none_until_fd1_p4l_private_inputs_are_supplied" if partial_status else "none_until_release_binary_build_succeeds"),
        "next_allowed_scope_bucket": "n6xfr_preflight_rerun_only" if pass_status else ("private_inputs_required_before_n6xfr" if partial_status else "build_failed_no_next_phase"),
        "n6xfr_prereq_rerun_authorized": pass_status,
        "n6xfr_canary_authorized": False,
        "n6xfr_full40_authorized": False,
        "retrieval_authorized": False,
        "full_rerun_authorized": False,
        "network_authorized": False,
        "git_clone_authorized": False,
        "openlocus_binary_execution_authorized": False,
        "private_read_authorized": False,
        "p5_authorized": False,
        "v1_a_authorized": False,
        "selector_or_reranker_authorized": False,
        "counterfactual_authorized": False,
        "runtime_promotion_authorized": False,
        "default_promotion_authorized": False,
        "runtime_or_policy_change_authorized": False,
        "method_winner_claimed": False,
        "method_winner_claim_authorized": False,
        "downstream_value_claimed": False,
        "downstream_value_claim_authorized": False,
    }]


def _build_report(checks: list[dict[str, Any]], build: Mapping[str, Any]) -> dict[str, Any]:
    start = time.perf_counter()
    input_records, input_ok = _input_artifact_records()
    private_records, private_ok = _private_input_bucket_records()
    noexec_records, noexec_ok = _no_forbidden_execution_records()
    privacy_records, privacy_ok = _privacy_boundary_records()
    self_ok = all(c["passed"] for c in checks)
    status = _status_from(self_ok=self_ok, input_ok=input_ok, build_success=bool(build["success"]), binary_after=bool(build["after"]), private_ok=private_ok)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "status": status, "claim_level": "cargo_dependency_fetch_release_binary_build_recovery_only", "phase": PHASE, "generated_by": GENERATED_BY, "generated_at": _now_iso(), "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records, "cargo_build_execution_records": _cargo_build_execution_records(build), "binary_availability_records": _binary_availability_records(build), "network_scope_records": _network_scope_records(), "private_input_bucket_records": private_records, "no_forbidden_execution_records": noexec_records, "privacy_boundary_records": privacy_records,
        "gate_records": _gate_records(input_ok=input_ok, build_success=bool(build["success"]), binary_after=bool(build["after"]), private_ok=private_ok, noexec_ok=noexec_ok, privacy_ok=privacy_ok, scanner_ok=True),
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
    report["gate_records"] = _gate_records(input_ok=input_ok, build_success=bool(build["success"]), binary_after=bool(build["after"]), private_ok=private_ok, noexec_ok=noexec_ok, privacy_ok=privacy_ok, scanner_ok=scanner_ok)
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
    input_records, input_ok = _input_artifact_records()
    private_records, private_ok = _private_input_bucket_records()
    noexec_records, noexec_ok = _no_forbidden_execution_records()
    privacy_records, privacy_ok = _privacy_boundary_records()
    fake_success_build = {"before": False, "after": True, "exit_code": 0, "success": True, "timed_out": False, "duration_bucket": "duration_lt_30s", "built_in_phase": True}
    checks = [
        _check("status_vocabulary_exact", tuple(STATUSES) == (STATUS_PASS, STATUS_PARTIAL, "no_go_n6xfrc_required_inputs_unavailable", "no_go_n6xfrc_cargo_build_failed", "no_go_n6xfrc_build_network_out_of_scope", "no_go_n6xfrc_binary_missing_after_build", "no_go_n6xfrc_private_inputs_missing", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_forbidden_keys", all(_scan_summary({key: "blocked"})["status"] == "fail" for key in ("path", "span", "snippet", "candidate_list", "rank", "task_id", "repo", "private_id", "source_hash", "provider_payload", "raw_diff", "filename", "log"))),
        _check("scanner_rejects_path_and_digest_values", _scan_summary({"safe": "src/lib.rs"})["status"] == "fail" and _scan_summary({"safe": "a" * 40})["status"] == "fail"),
        _check("input_artifact", input_ok and len(input_records) == 1 and input_records[0]["input_gate_passed_bool"] is True),
        _check("cargo_record_shape", _cargo_build_execution_records(fake_success_build)[0]["command_bucket"] == "cargo_build_locked_release_openlocus_cli" and _cargo_build_execution_records(fake_success_build)[0]["build_attempted_bool"] is True and _cargo_build_execution_records(fake_success_build)[0]["raw_log_public_bool"] is False and _cargo_build_execution_records(fake_success_build)[0]["openlocus_binary_executed_bool"] is False),
        _check("binary_record_shape", _binary_availability_records(fake_success_build)[0]["release_binary_exists_after_bool"] is True and _binary_availability_records(fake_success_build)[0]["binary_built_in_phase_bool"] is True and _binary_availability_records(fake_success_build)[0]["binary_available_after_recovery_bool"] is True and _binary_availability_records(fake_success_build)[0]["binary_created_during_this_invocation_bool"] is True),
        _check("binary_record_idempotent_shape", _binary_availability_records({"before": True, "after": True, "exit_code": 0, "success": True, "timed_out": False, "duration_bucket": "duration_lt_30s", "built_in_phase": False})[0]["binary_available_after_recovery_bool"] is True and _binary_availability_records({"before": True, "after": True, "exit_code": 0, "success": True, "timed_out": False, "duration_bucket": "duration_lt_30s", "built_in_phase": False})[0]["binary_created_during_this_invocation_bool"] is False),
        _check("network_scope", _network_scope_records()[0]["crates_io_dependency_fetch_scope_bool"] is True and _network_scope_records()[0]["benchmark_repo_network_bool"] is False and _network_scope_records()[0]["git_clone_bool"] is False),
        _check("private_inputs_missing", private_ok is False and private_records[0]["fd1_private_decomposition_available_bool"] is False and private_records[0]["p4l_private_source_available_bool"] is False and private_records[0]["private_content_read_bool"] is False),
        _check("no_forbidden_execution", noexec_ok and all(noexec_records[0][k] == 0 for k in ("retrieval_execution_count", "openlocus_binary_execution_count", "p4l_n1_n2_n3_rerun_count", "candidate_pool_generation_count", "selector_reranker_execution_count", "p5_execution_count", "v1a_execution_count"))),
        _check("privacy_boundary", privacy_ok and privacy_records[0]["raw_cargo_log_public_bool"] is False and privacy_records[0]["private_path_or_filename_public_bool"] is False and privacy_records[0]["raw_candidate_public_bool"] is False),
        _check("status_partial_expected", _status_from(self_ok=True, input_ok=True, build_success=True, binary_after=True, private_ok=False) == STATUS_PARTIAL),
        _check("status_failed_expected", _status_from(self_ok=True, input_ok=True, build_success=False, binary_after=False, private_ok=False) == "no_go_n6xfrc_cargo_build_failed"),
        _check("stop_go_partial", _stop_go_records(STATUS_PARTIAL)[0]["next_allowed_phase"] == "none_until_fd1_p4l_private_inputs_are_supplied" and _stop_go_records(STATUS_PARTIAL)[0]["n6xfr_canary_authorized"] is False and _stop_go_records(STATUS_PARTIAL)[0]["private_read_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N6XFR-C cargo dependency fetch release binary build recovery")
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
    build = _run_cargo_build()
    report = _build_report(checks, build)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    binary = report["binary_availability_records"][0]
    print("wrote artifact " f"(status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, " f"binary_before={binary['release_binary_exists_before_bool']}, binary_after={binary['release_binary_exists_after_bool']})")


if __name__ == "__main__":
    main()
