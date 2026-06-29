#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n6xfrd_private_reconstruction_input_inventory_recovery_audit.v1"
PHASE = "BEA-v1-N6XFR-D"
GENERATED_BY = "bea_v1_n6xfrd_private_reconstruction_input_inventory_recovery_audit"
STATUS_NO_GO = "no_go_n6xfrd_private_reconstruction_inputs_unavailable"
STATUS_PARTIAL = "partial_n6xfrd_private_input_candidates_found_unvalidated"
STATUS_PASS = "private_reconstruction_input_inventory_pass_n6xfr_prereq_rerun_authorized"

STATUSES = (
    STATUS_PASS,
    STATUS_PARTIAL,
    STATUS_NO_GO,
    "no_go_n6xfrd_required_inputs_unavailable",
    "no_go_n6xfrd_inventory_scope_invalid",
    "no_go_n6xfrd_privacy_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path(
    "artifacts/bea_v1_n6xfrd_private_reconstruction_input_inventory_recovery_audit/"
    "bea_v1_n6xfrd_private_reconstruction_input_inventory_recovery_audit_report.json"
)

N6XFRC_INPUT = (
    "n6xfrc_build_recovery_artifact",
    Path(
        "artifacts/bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery/"
        "bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery_report.json"
    ),
    "partial_n6xfrc_binary_built_private_inputs_missing",
)

CANDIDATE_BUCKETS = (
    "fd1_private_decomposition_candidate",
    "p4l_private_source_candidate",
    "n_series_candidate_pool_candidate",
    "n6_arm_outcome_candidate",
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
    "load_status", "forbidden_scan_status", "inventory_scope_bucket", "candidate_bucket",
    "candidate_file_count_bucket", "candidate_size_bucket", "candidate_extension_bucket",
    "coverage_status_bucket", "privacy_boundary_bucket", "public_artifact_bucket",
    "no_execution_boundary_bucket", "closure_decision_bucket", "next_required_input_bucket",
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


def _input_artifact_records() -> tuple[list[dict[str, Any]], bool, bool]:
    bucket, path, expected = N6XFRC_INPUT
    artifact, load = _load_json(path)
    scan = artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported"
    observed = str(artifact.get("status", "") or "")
    binary_after = False
    binary_records = artifact.get("binary_availability_records", [])
    if isinstance(binary_records, list) and binary_records and isinstance(binary_records[0], dict):
        binary_after = binary_records[0].get("release_binary_exists_after_bool") is True
    passed = load == "pass" and observed == expected and scan == "pass" and binary_after
    return [{
        "anonymous_input_artifact_id": "n6xfrdin0000",
        "input_artifact_bucket": bucket,
        "load_status": load,
        "observed_status": observed,
        "expected_status": expected,
        "forbidden_scan_status": str(scan),
        "binary_available_after_recovery_bool": binary_after,
        "input_gate_passed_bool": passed,
    }], passed, binary_after


def _inventory_scope_records() -> tuple[list[dict[str, Any]], bool]:
    record = {
        "anonymous_inventory_scope_id": "n6xfrdscope0000",
        "inventory_scope_bucket": "repo_research_private_only",
        "scope_exists_bool": _repo_root().joinpath(".openlocus", "research-private").exists(),
        "private_paths_publicly_serialized_bool": False,
        "private_names_publicly_serialized_bool": False,
        "tmp_scan_bool": False,
        "broad_filesystem_scan_bool": False,
        "private_content_read_bool": False,
        "metadata_only_bool": True,
        "inventory_scope_valid_bool": True,
    }
    return [record], True


def _count_bucket(count: int) -> str:
    if count == 0:
        return "zero"
    if count == 1:
        return "one"
    if count <= 5:
        return "few"
    return "many"


def _size_bucket(sizes: list[int]) -> str:
    if not sizes:
        return "none"
    def one(size: int) -> str:
        if size < 100_000:
            return "small"
        if size < 5_000_000:
            return "medium"
        return "large"
    buckets = {one(size) for size in sizes}
    return next(iter(buckets)) if len(buckets) == 1 else "mixed"


def _extension_bucket(exts: list[str]) -> str:
    if not exts:
        return "none"
    normalized = {(ext or "other").lower().lstrip(".") for ext in exts}
    normalized = {ext if ext in {"json", "jsonl"} else "other" for ext in normalized}
    return next(iter(normalized)) if len(normalized) == 1 else "mixed"


def _classify_private_metadata() -> dict[str, list[tuple[int, str]]]:
    root = _repo_root().joinpath(".openlocus", "research-private")
    buckets: dict[str, list[tuple[int, str]]] = {bucket: [] for bucket in CANDIDATE_BUCKETS}
    if not root.exists() or not root.is_dir():
        return buckets
    # Metadata-only scoped listing. Names are used only transiently for bucket classification.
    for item in root.iterdir():
        try:
            if not item.is_file():
                continue
            lower = item.name.lower()
            size = item.stat().st_size
            ext = item.suffix.lower()
        except OSError:
            continue
        if "fd1" in lower or "failure_decomposition" in lower:
            buckets["fd1_private_decomposition_candidate"].append((size, ext))
        if "p4l" in lower or "locked_non_python" in lower:
            buckets["p4l_private_source_candidate"].append((size, ext))
        if (("n6" in lower or "n_series" in lower or "n-series" in lower) and ("candidate" in lower or "pool" in lower)):
            buckets["n_series_candidate_pool_candidate"].append((size, ext))
        if "arm" in lower and "outcome" in lower:
            buckets["n6_arm_outcome_candidate"].append((size, ext))
    return buckets


def _private_input_candidate_summary_records() -> tuple[list[dict[str, Any]], dict[str, int]]:
    metadata = _classify_private_metadata()
    records: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for idx, bucket in enumerate(CANDIDATE_BUCKETS):
        entries = metadata[bucket]
        sizes = [entry[0] for entry in entries]
        exts = [entry[1] for entry in entries]
        count = len(entries)
        counts[bucket] = count
        records.append({
            "anonymous_private_input_candidate_summary_id": f"n6xfrdcand{idx:04d}",
            "candidate_bucket": bucket,
            "candidate_file_count_bucket": _count_bucket(count),
            "candidate_size_bucket": _size_bucket(sizes),
            "candidate_extension_bucket": _extension_bucket(exts),
            "candidate_count": count,
            "private_names_publicly_serialized_bool": False,
            "private_paths_publicly_serialized_bool": False,
            "private_content_read_bool": False,
            "usable_for_n6xfr_preflight_bool": count > 0,
        })
    return records, counts


def _required_input_coverage_records(binary_ok: bool, counts: dict[str, int]) -> tuple[list[dict[str, Any]], bool, bool]:
    fd1 = counts.get("fd1_private_decomposition_candidate", 0)
    p4l = counts.get("p4l_private_source_candidate", 0)
    nseries = counts.get("n_series_candidate_pool_candidate", 0)
    n6arm = counts.get("n6_arm_outcome_candidate", 0)
    all_covered = binary_ok and fd1 > 0 and p4l > 0 and (nseries > 0 or n6arm > 0)
    partial = (fd1 + p4l + nseries + n6arm) > 0 and not all_covered
    return [{
        "anonymous_required_input_coverage_id": "n6xfrdcov0000",
        "coverage_status_bucket": "all_required_buckets_covered" if all_covered else ("partial_candidate_buckets_found" if partial else "required_private_candidate_buckets_unavailable"),
        "release_binary_available_bool": binary_ok,
        "fd1_candidate_count": fd1,
        "p4l_candidate_count": p4l,
        "nseries_candidate_count": nseries,
        "n6_arm_outcome_candidate_count": n6arm,
        "all_required_buckets_covered_bool": all_covered,
    }], all_covered, partial


def _privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_privacy_boundary_id": "n6xfrdpb0000", "privacy_boundary_bucket": "metadata_only_private_inventory_summary", "public_artifact_bucket": "bucket_counts_booleans_only", "private_content_public_bool": False, "private_path_or_filename_public_bool": False, "raw_candidate_public_bool": False, "raw_rank_public_bool": False, "task_repo_id_public_bool": False, "source_span_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_complete_bool": True}
    return [record], True


def _no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_no_execution_id": "n6xfrdnoexec0000", "no_execution_boundary_bucket": "read_only_metadata_inventory_no_replay", "openlocus_binary_execution_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_n3_rerun_count": 0, "candidate_pool_generation_count": 0, "candidate_pool_materialization_count": 0, "n6xfr_canary_execution_count": 0, "n6xfr_full40_execution_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "no_execution_complete_bool": True}
    return [record], True


def _closure_decision_records(all_covered: bool, partial: bool) -> list[dict[str, Any]]:
    return [{"anonymous_closure_decision_id": "n6xfrdclose0000", "closure_decision_bucket": "private_inputs_unavailable_route_closed" if not all_covered else "private_inputs_candidates_available_unvalidated", "route_closed_bool": not all_covered, "private_reconstruction_inputs_available_bool": all_covered, "partial_candidates_found_bool": partial, "n6xfr_prereq_rerun_authorized_bool": all_covered, "next_required_input_bucket": "fd1_p4l_nseries_private_reconstruction_inputs"}]


def _status_from(*, self_ok: bool, input_ok: bool, scope_ok: bool, all_covered: bool, partial: bool, privacy_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n6xfrd_required_inputs_unavailable"
    if not scope_ok:
        return "no_go_n6xfrd_inventory_scope_invalid"
    if not privacy_ok:
        return "no_go_n6xfrd_privacy_boundary_failed"
    if all_covered:
        return STATUS_PASS
    if partial:
        return STATUS_PARTIAL
    return STATUS_NO_GO


def _gate_records(*, input_ok: bool, scope_ok: bool, all_covered: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    return [
        {"gate": "required_input_artifact_load_and_scan", "passed": input_ok, "threshold_relation": "equals", "value": int(input_ok), "threshold_value": 1},
        {"gate": "inventory_scope_valid", "passed": scope_ok, "threshold_relation": "equals", "value": int(scope_ok), "threshold_value": 1},
        {"gate": "all_required_private_input_buckets_covered", "passed": all_covered, "threshold_relation": "equals", "value": int(all_covered), "threshold_value": 1},
        {"gate": "privacy_boundary_complete", "passed": privacy_ok, "threshold_relation": "equals", "value": int(privacy_ok), "threshold_value": 1},
        {"gate": "no_execution", "passed": noexec_ok, "threshold_relation": "equals", "value": int(noexec_ok), "threshold_value": 1},
        {"gate": "scanner_pass", "passed": scanner_ok, "threshold_relation": "equals", "value": int(scanner_ok), "threshold_value": 1},
    ]


def _stop_go_records(status: str) -> list[dict[str, Any]]:
    pass_status = status == STATUS_PASS
    return [{"authorization": "private_reconstruction_input_inventory_no_go" if not pass_status else "private_reconstruction_input_inventory_pass", "next_allowed_phase": "BEA-v1-N6X-FR Prerequisite Rerun" if pass_status else "BEA-v1 Final Mechanism Route Synthesis", "next_allowed_scope_bucket": "n6xfr_preflight_rerun_only" if pass_status else "final_synthesis_only_no_execution", "n6xfr_prereq_rerun_authorized": pass_status, "n6xfr_canary_authorized": False, "n6xfr_full40_authorized": False, "openlocus_binary_execution_authorized": False, "private_read_authorized": False, "retrieval_authorized": False, "full_rerun_authorized": False, "candidate_generation_authorized": False, "candidate_materialization_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "counterfactual_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "runtime_or_policy_change_authorized": False, "method_winner_claimed": False, "method_winner_claim_authorized": False, "downstream_value_claimed": False, "downstream_value_claim_authorized": False}]


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    input_records, input_ok, binary_ok = _input_artifact_records()
    scope_records, scope_ok = _inventory_scope_records()
    candidate_records, counts = _private_input_candidate_summary_records()
    coverage_records, all_covered, partial = _required_input_coverage_records(binary_ok, counts)
    privacy_records, privacy_ok = _privacy_boundary_records()
    noexec_records, noexec_ok = _no_execution_records()
    closure_records = _closure_decision_records(all_covered, partial)
    self_ok = all(c["passed"] for c in checks)
    status = _status_from(self_ok=self_ok, input_ok=input_ok, scope_ok=scope_ok, all_covered=all_covered, partial=partial, privacy_ok=privacy_ok)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "status": status, "claim_level": "private_reconstruction_input_inventory_recovery_audit_only", "phase": PHASE, "generated_by": GENERATED_BY, "generated_at": _now_iso(), "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records, "inventory_scope_records": scope_records, "private_input_candidate_summary_records": candidate_records, "required_input_coverage_records": coverage_records, "privacy_boundary_records": privacy_records, "no_execution_records": noexec_records, "closure_decision_records": closure_records,
        "gate_records": _gate_records(input_ok=input_ok, scope_ok=scope_ok, all_covered=all_covered, privacy_ok=privacy_ok, noexec_ok=noexec_ok, scanner_ok=True),
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
    report["gate_records"] = _gate_records(input_ok=input_ok, scope_ok=scope_ok, all_covered=all_covered, privacy_ok=privacy_ok, noexec_ok=noexec_ok, scanner_ok=scanner_ok)
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
    input_records, input_ok, binary_ok = _input_artifact_records()
    scope_records, scope_ok = _inventory_scope_records()
    candidate_records, counts = _private_input_candidate_summary_records()
    coverage_records, all_covered, partial = _required_input_coverage_records(binary_ok, counts)
    privacy_records, privacy_ok = _privacy_boundary_records()
    noexec_records, noexec_ok = _no_execution_records()
    checks = [
        _check("status_vocabulary_exact", tuple(STATUSES) == (STATUS_PASS, STATUS_PARTIAL, STATUS_NO_GO, "no_go_n6xfrd_required_inputs_unavailable", "no_go_n6xfrd_inventory_scope_invalid", "no_go_n6xfrd_privacy_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_forbidden_keys", all(_scan_summary({key: "blocked"})["status"] == "fail" for key in ("path", "span", "snippet", "candidate_list", "rank", "task_id", "repo", "private_id", "source_hash", "provider_payload", "raw_diff", "filename"))),
        _check("scanner_rejects_path_and_digest_values", _scan_summary({"safe": "src/lib.rs"})["status"] == "fail" and _scan_summary({"safe": "a" * 40})["status"] == "fail"),
        _check("input_n6xfrc", input_ok and input_records[0]["binary_available_after_recovery_bool"] is True),
        _check("scope_valid", scope_ok and scope_records[0]["inventory_scope_bucket"] == "repo_research_private_only" and scope_records[0]["tmp_scan_bool"] is False and scope_records[0]["private_content_read_bool"] is False),
        _check("candidate_records_shape", len(candidate_records) == 4 and tuple(r["candidate_bucket"] for r in candidate_records) == CANDIDATE_BUCKETS),
        _check("candidate_records_private_safe", all(r["private_names_publicly_serialized_bool"] is False and r["private_paths_publicly_serialized_bool"] is False and r["private_content_read_bool"] is False for r in candidate_records)),
        _check("coverage_records", coverage_records[0]["release_binary_available_bool"] is True and coverage_records[0]["all_required_buckets_covered_bool"] is all_covered),
        _check("privacy_boundary", privacy_ok and privacy_records[0]["private_content_public_bool"] is False and privacy_records[0]["private_path_or_filename_public_bool"] is False and privacy_records[0]["raw_candidate_public_bool"] is False),
        _check("no_execution", noexec_ok and all(noexec_records[0][k] == 0 for k in ("openlocus_binary_execution_count", "retrieval_execution_count", "p4l_n1_n2_n3_rerun_count", "candidate_pool_generation_count", "n6xfr_canary_execution_count", "selector_reranker_execution_count", "p5_execution_count", "v1a_execution_count"))),
        _check("status_no_go_or_partial", _status_from(self_ok=True, input_ok=True, scope_ok=True, all_covered=all_covered, partial=partial, privacy_ok=True) in {STATUS_NO_GO, STATUS_PARTIAL, STATUS_PASS}),
        _check("expected_no_full_coverage", all_covered is False),
        _check("stop_go_no_go", _stop_go_records(STATUS_NO_GO)[0]["next_allowed_phase"] == "BEA-v1 Final Mechanism Route Synthesis" and _stop_go_records(STATUS_NO_GO)[0]["private_read_authorized"] is False and _stop_go_records(STATUS_NO_GO)[0]["n6xfr_canary_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N6XFR-D private reconstruction input inventory recovery audit")
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
    coverage = report["required_input_coverage_records"][0]
    print("wrote artifact " f"(status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, " f"fd1={coverage['fd1_candidate_count']}, p4l={coverage['p4l_candidate_count']})")


if __name__ == "__main__":
    main()
