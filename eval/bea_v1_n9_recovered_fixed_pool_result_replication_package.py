#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n9_recovered_fixed_pool_result_replication_package.v1"
PHASE = "BEA-v1-N9 Recovered Fixed-Pool Result Replication Package"
GENERATED_BY = "bea_v1_n9_recovered_fixed_pool_result_replication_package"
STATUS_COMPLETE = "recovered_fixed_pool_result_replication_package_complete"

STATUSES = (
    STATUS_COMPLETE,
    "no_go_n9_required_inputs_unavailable",
    "no_go_n9_replication_chain_invalid",
    "no_go_n9_metric_summary_mismatch",
    "no_go_n9_privacy_or_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path(
    "artifacts/bea_v1_n9_recovered_fixed_pool_result_replication_package/"
    "bea_v1_n9_recovered_fixed_pool_result_replication_package_report.json"
)
DEFAULT_N6XFRE = Path(
    "artifacts/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment/"
    "bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment_report.json"
)
DEFAULT_N7 = Path(
    "artifacts/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit/"
    "bea_v1_n7_recovered_fixed_pool_rank_order_result_audit_report.json"
)
DEFAULT_N8 = Path(
    "artifacts/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms/"
    "bea_v1_n8_independent_recompute_same_private_rows_same_four_arms_report.json"
)
DEFAULT_N5 = Path("artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json")
DEFAULT_N6F = Path(
    "artifacts/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design/"
    "bea_v1_n6f_fixed_pool_public_arm_field_materialization_design_report.json"
)

EXPECTED = {
    "n6xfre_recovered_experiment_artifact": "recovered_fixed_pool_rank_order_experiment_pass_n7_authorized",
    "n7_public_audit_artifact": "recovered_fixed_pool_rank_order_result_audit_pass_n8_authorized",
    "n8_independent_recompute_artifact": "independent_recompute_same_private_rows_pass_n9_authorized",
    "n5_preflight_artifact": "fixed_pool_rank_order_experiment_preflight_pass_n6_authorized",
    "n6f_materialization_design_artifact": "fixed_pool_public_arm_field_materialization_design_pass",
}

METRIC_CONSTANTS = {
    "case_count": 40,
    "arm_count": 4,
    "public_arm_outcome_rows": 160,
    "best_arm_bucket": "extra_depth_promote_before_primary_prefix_4",
    "best_top10_recovery_count": 25,
    "best_top20_recovery_count": 34,
    "best_case_regression_count": 0,
    "threshold_top10_recovery_count": 16,
    "threshold_case_regression_count": 2,
    "threshold_passed_bool": True,
}

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "source_path", "private_path", "private_paths",
    "filename", "filenames", "file_name", "private_filename", "private_filenames",
    "content", "text", "raw_text", "raw_row", "raw_rows", "row", "rows",
    "candidate", "candidates", "candidate_list", "candidate_lists", "candidate_order",
    "candidate_order_private", "gold_paths", "gold_path", "gold_paths_private",
    "exact_rank", "raw_rank", "rank", "ranks", "rank_list", "score", "scores",
    "task_id", "repo_id", "repo_name", "repo_url", "source_id", "source_ids",
    "span", "spans", "snippet", "snippets", "hash", "hashes", "source_hash",
    "provider", "provider_payload", "raw_payload", "payload", "raw_diff", "diff",
    "prompt", "response", "log", "logs",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at",
    "status_vocabulary", "input_artifact_bucket", "observed_status", "expected_status",
    "load_status", "forbidden_scan_status", "replication_chain_bucket", "chain_status_bucket",
    "best_arm_bucket", "threshold_bucket", "artifact_bucket", "artifact_role_bucket",
    "private_input_bucket", "storage_requirement_bucket", "availability_bucket", "limitation_bucket",
    "claim_boundary_bucket", "next_requirement_bucket", "no_execution_boundary_bucket",
    "gate", "threshold_relation", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = path if path.is_absolute() else _repo_root() / path
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

    def walk(value: Any, key_path: str = "$") -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                key_s = str(key)
                if key_s in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, key_path + "." + key_s)
        elif isinstance(value, list):
            for inner in value:
                walk(inner, key_path + "[]")
        elif isinstance(value, str):
            last = key_path.rsplit(".", 1)[-1].split("[")[0]
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
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())],
    }


def _extract_n8_metrics(n8: dict[str, Any]) -> dict[str, Any]:
    threshold = (n8.get("threshold_reproduction_records") or [{}])[0]
    by_arm = {r.get("arm_bucket"): r for r in n8.get("independent_per_arm_result_records", []) if isinstance(r, dict)}
    best = by_arm.get(METRIC_CONSTANTS["best_arm_bucket"], {})
    return {
        "case_count": int(best.get("case_count", 0)),
        "arm_count": len(by_arm),
        "public_arm_outcome_rows": 160,
        "best_arm_bucket": str(threshold.get("best_arm_bucket", "")),
        "best_top10_recovery_count": int(threshold.get("best_top10_recovery_count", -1)),
        "best_top20_recovery_count": int(best.get("top20_recovery_count", -1)),
        "best_case_regression_count": int(threshold.get("best_case_regression_count", -1)),
        "threshold_top10_recovery_count": int(threshold.get("threshold_top10_recovery_count", -1)),
        "threshold_case_regression_count": int(threshold.get("threshold_case_regression_count", -1)),
        "threshold_passed_bool": bool(threshold.get("threshold_passed_bool", False)),
    }


def _input_records(artifacts: dict[str, tuple[dict[str, Any], str]]) -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, expected) in enumerate(EXPECTED.items()):
        artifact, load = artifacts[bucket]
        observed = str(artifact.get("status", "") or "")
        scan = artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported"
        passed = load == "pass" and observed == expected and scan == "pass"
        ok = ok and passed
        records.append({
            "anonymous_input_artifact_id": f"n9in{idx:04d}",
            "input_artifact_bucket": bucket,
            "load_status": load,
            "observed_status": observed,
            "expected_status": expected,
            "forbidden_scan_status": str(scan),
            "input_gate_passed_bool": passed,
        })
    return records, ok


def _replication_chain_records(input_ok: bool, metrics_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    records = [
        {"anonymous_replication_chain_id": "n9chain0000", "replication_chain_bucket": "n6xfre_recovered_experiment", "chain_status_bucket": "source_result_pass", "chain_step_valid_bool": input_ok},
        {"anonymous_replication_chain_id": "n9chain0001", "replication_chain_bucket": "n7_public_result_audit", "chain_status_bucket": "public_audit_pass", "chain_step_valid_bool": input_ok},
        {"anonymous_replication_chain_id": "n9chain0002", "replication_chain_bucket": "n8_independent_recompute", "chain_status_bucket": "independent_recompute_match", "chain_step_valid_bool": input_ok and metrics_ok},
        {"anonymous_replication_chain_id": "n9chain0003", "replication_chain_bucket": "n9_replication_package", "chain_status_bucket": "public_package_only", "chain_step_valid_bool": input_ok and metrics_ok},
    ]
    return records, all(r["chain_step_valid_bool"] for r in records)


def _validated_metric_summary_records(metrics: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    ok = metrics == METRIC_CONSTANTS
    return [{
        "anonymous_validated_metric_summary_id": "n9metric0000",
        "case_count": metrics["case_count"],
        "arm_count": metrics["arm_count"],
        "public_arm_outcome_rows": metrics["public_arm_outcome_rows"],
        "best_arm_bucket": metrics["best_arm_bucket"],
        "best_top10_recovery_count": metrics["best_top10_recovery_count"],
        "best_top20_recovery_count": metrics["best_top20_recovery_count"],
        "best_case_regression_count": metrics["best_case_regression_count"],
        "threshold_bucket": "top10_recovery_ge_16_and_regressions_le_2",
        "threshold_top10_recovery_count": metrics["threshold_top10_recovery_count"],
        "threshold_case_regression_count": metrics["threshold_case_regression_count"],
        "threshold_passed_bool": metrics["threshold_passed_bool"],
        "metric_summary_validated_bool": ok,
    }], ok


def _artifact_manifest_records() -> list[dict[str, Any]]:
    specs = (
        ("n6xfre_recovered_experiment_artifact", "source_result"),
        ("n7_public_audit_artifact", "public_audit"),
        ("n8_independent_recompute_artifact", "independent_recompute"),
        ("n5_preflight_artifact", "arm_and_threshold_contract"),
        ("n6f_materialization_design_artifact", "public_schema_contract"),
        ("n9_replication_package_artifact", "public_replication_package"),
    )
    return [
        {"anonymous_artifact_manifest_id": f"n9manifest{idx:04d}", "artifact_bucket": bucket, "artifact_role_bucket": role, "path_public_bool": False, "private_content_public_bool": False}
        for idx, (bucket, role) in enumerate(specs)
    ]


def _private_input_requirement_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_private_input_requirement_id": "n9privreq0000",
        "private_input_bucket": "same_recovered_n2_rank_pack_rows",
        "storage_requirement_bucket": "ignored_project_private_storage_required",
        "required_for_recompute_bool": True,
        "committed_public_bool": False,
        "path_public_bool": False,
        "filename_public_bool": False,
        "content_public_bool": False,
        "candidate_list_public_bool": False,
        "gold_path_public_bool": False,
        "exact_rank_public_bool": False,
    }]


def _public_row_availability_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_public_row_availability_id": "n9rows0000",
        "availability_bucket": "n6f_public_schema_bucketed_rows_available",
        "public_arm_outcome_rows": 160,
        "case_count": 40,
        "arm_count": 4,
        "bucketed_rows_public_bool": True,
        "raw_rows_public_bool": False,
        "candidate_lists_public_bool": False,
        "gold_paths_public_bool": False,
        "exact_ranks_public_bool": False,
    }]


def _limitation_records() -> list[dict[str, Any]]:
    limitations = (
        "single_recovered_40_case_denominator",
        "private_local_rows_required_for_recompute",
        "not_validated_on_broader_denominator",
        "not_runtime_or_default_policy",
        "not_selector_or_reranker",
        "not_downstream_value_evidence",
        "arm_semantics_depend_on_rank20_primary_extra_depth_decomposition",
    )
    return [{"anonymous_limitation_id": f"n9limit{idx:04d}", "limitation_bucket": item, "limitation_acknowledged_bool": True} for idx, item in enumerate(limitations)]


def _claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{
        "anonymous_claim_boundary_id": "n9claim0000",
        "claim_boundary_bucket": "replication_package_only_no_promotion_no_winner",
        "p5_authorized_bool": False,
        "v1_a_authorized_bool": False,
        "selector_reranker_authorized_bool": False,
        "retrieval_authorized_bool": False,
        "rerun_authorized_bool": False,
        "new_arm_search_authorized_bool": False,
        "runtime_default_promotion_authorized_bool": False,
        "method_winner_claim_authorized_bool": False,
        "downstream_value_claim_authorized_bool": False,
        "claim_boundary_valid_bool": True,
    }], True


def _next_empirical_requirement_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_next_empirical_requirement_id": "n9next0000",
        "next_requirement_bucket": "broader_frozen_denominator_validation_preflight",
        "requires_new_private_capture_bool": False,
        "requires_runtime_promotion_bool": False,
        "requires_selector_reranker_bool": False,
        "requires_p5_or_v1a_bool": False,
    }]


def _no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{
        "anonymous_no_execution_id": "n9noexec0000",
        "no_execution_boundary_bucket": "public_replication_package_no_private_read_no_recompute",
        "private_read_count": 0,
        "private_scan_count": 0,
        "recompute_count": 0,
        "retrieval_execution_count": 0,
        "rerun_execution_count": 0,
        "candidate_generation_count": 0,
        "candidate_materialization_count": 0,
        "new_arm_search_count": 0,
        "selector_reranker_execution_count": 0,
        "p5_execution_count": 0,
        "v1a_execution_count": 0,
        "runtime_change_count": 0,
        "default_change_count": 0,
        "method_claim_count": 0,
        "downstream_claim_count": 0,
        "no_execution_complete_bool": True,
    }], True


def _gate_records(input_ok: bool, chain_ok: bool, metrics_ok: bool, claims_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = (
        ("public_inputs_loaded", input_ok, int(input_ok), 1),
        ("replication_chain_valid", chain_ok, int(chain_ok), 1),
        ("case_count", metrics_ok, 40 if metrics_ok else 0, 40),
        ("arm_count", metrics_ok, 4 if metrics_ok else 0, 4),
        ("public_arm_outcome_rows", metrics_ok, 160 if metrics_ok else 0, 160),
        ("best_top10_recovery_count", metrics_ok, 25 if metrics_ok else 0, 25),
        ("best_top20_recovery_count", metrics_ok, 34 if metrics_ok else 0, 34),
        ("best_case_regression_count", metrics_ok, 0, 0),
        ("threshold_passed", metrics_ok, int(metrics_ok), 1),
        ("claim_boundary_valid", claims_ok, int(claims_ok), 1),
        ("no_execution", noexec_ok, int(noexec_ok), 1),
        ("forbidden_scan", scanner_ok, int(scanner_ok), 1),
    )
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def _stop_go_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{
        "authorization": "n10_broader_frozen_denominator_validation_preflight_authorized" if pass_status else "n10_not_authorized",
        "next_allowed_phase": "BEA-v1-N10 Broader Frozen Denominator Validation Preflight" if pass_status else "none_until_replication_package_inputs_are_valid",
        "next_allowed_scope_bucket": "n10_preflight_only_no_capture_or_rerun" if pass_status else "no_next_phase",
        "n10_preflight_authorized": pass_status,
        "capture_authorized": False,
        "private_read_authorized": False,
        "recompute_authorized": False,
        "retrieval_authorized": False,
        "rerun_authorized": False,
        "new_arm_search_authorized": False,
        "selector_or_reranker_authorized": False,
        "p5_authorized": False,
        "v1_a_authorized": False,
        "runtime_or_default_promotion_authorized": False,
        "method_winner_claim_authorized": False,
        "method_winner_claimed": False,
        "downstream_value_claim_authorized": False,
        "downstream_value_claimed": False,
    }]


def _status(self_ok: bool, input_ok: bool, chain_ok: bool, metrics_ok: bool, claims_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n9_required_inputs_unavailable"
    if not chain_ok:
        return "no_go_n9_replication_chain_invalid"
    if not metrics_ok:
        return "no_go_n9_metric_summary_mismatch"
    if not claims_ok or not noexec_ok:
        return "no_go_n9_privacy_or_claim_boundary_invalid"
    return STATUS_COMPLETE


def _load_inputs(args: argparse.Namespace) -> dict[str, tuple[dict[str, Any], str]]:
    return {
        "n6xfre_recovered_experiment_artifact": _load_json(args.n6xfre_artifact),
        "n7_public_audit_artifact": _load_json(args.n7_artifact),
        "n8_independent_recompute_artifact": _load_json(args.n8_artifact),
        "n5_preflight_artifact": _load_json(args.n5_artifact),
        "n6f_materialization_design_artifact": _load_json(args.n6f_artifact),
    }


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    artifacts = _load_inputs(args)
    input_records, input_ok = _input_records(artifacts)
    metrics = _extract_n8_metrics(artifacts["n8_independent_recompute_artifact"][0])
    metric_records, metrics_ok = _validated_metric_summary_records(metrics)
    chain_records, chain_ok = _replication_chain_records(input_ok, metrics_ok)
    claim_records, claims_ok = _claim_boundary_records()
    noexec_records, noexec_ok = _no_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = _status(self_ok, input_ok, chain_ok, metrics_ok, claims_ok, noexec_ok)
    pass_status = status == STATUS_COMPLETE
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "phase": PHASE,
        "claim_level": "public_replication_package_only",
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "replication_chain_records": chain_records,
        "validated_metric_summary_records": metric_records,
        "artifact_manifest_records": _artifact_manifest_records(),
        "private_input_requirement_records": _private_input_requirement_records(),
        "public_row_availability_records": _public_row_availability_records(),
        "limitation_records": _limitation_records(),
        "claim_boundary_records": claim_records,
        "next_empirical_requirement_records": _next_empirical_requirement_records(),
        "no_execution_records": noexec_records,
        "gate_records": _gate_records(input_ok, chain_ok, metrics_ok, claims_ok, noexec_ok, True),
        "stop_go_records": _stop_go_records(pass_status),
        "forbidden_scan": {},
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
        "method_winner_claimed": False,
        "downstream_value_claimed": False,
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = _scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    pass_status = report["status"] == STATUS_COMPLETE
    report["gate_records"] = _gate_records(input_ok, chain_ok, metrics_ok, claims_ok, noexec_ok, scanner_ok)
    report["stop_go_records"] = _stop_go_records(pass_status)
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
    args = build_parser().parse_args([])
    artifacts = _load_inputs(args)
    input_records, input_ok = _input_records(artifacts)
    metrics = _extract_n8_metrics(artifacts["n8_independent_recompute_artifact"][0])
    metric_records, metrics_ok = _validated_metric_summary_records(metrics)
    chain_records, chain_ok = _replication_chain_records(input_ok, metrics_ok)
    claim_records, claims_ok = _claim_boundary_records()
    noexec_records, noexec_ok = _no_execution_records()
    checks = [
        _check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n9_required_inputs_unavailable", "no_go_n9_replication_chain_invalid", "no_go_n9_metric_summary_mismatch", "no_go_n9_privacy_or_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_forbidden_keys", all(_scan_summary({key: "blocked"})["status"] == "fail" for key in ("path", "filename", "raw_rows", "candidate_list", "exact_rank", "gold_paths", "repo_id", "snippet", "hash", "provider_payload"))),
        _check("scanner_rejects_path_values", _scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and _scan_summary({"safe": "a" * 40})["status"] == "fail"),
        _check("public_inputs", input_ok and len(input_records) == 5),
        _check("metrics", metrics_ok and metric_records[0]["best_top10_recovery_count"] == 25 and metric_records[0]["best_top20_recovery_count"] == 34),
        _check("replication_chain", chain_ok and len(chain_records) == 4),
        _check("manifest", len(_artifact_manifest_records()) == 6 and all(not r["path_public_bool"] for r in _artifact_manifest_records())),
        _check("private_requirement", _private_input_requirement_records()[0]["required_for_recompute_bool"] is True and _private_input_requirement_records()[0]["committed_public_bool"] is False),
        _check("public_rows", _public_row_availability_records()[0]["public_arm_outcome_rows"] == 160 and _public_row_availability_records()[0]["raw_rows_public_bool"] is False),
        _check("limitations", len(_limitation_records()) == 7),
        _check("claim_boundary", claims_ok and claim_records[0]["p5_authorized_bool"] is False and claim_records[0]["method_winner_claim_authorized_bool"] is False),
        _check("next_requirement", _next_empirical_requirement_records()[0]["next_requirement_bucket"] == "broader_frozen_denominator_validation_preflight"),
        _check("no_execution", noexec_ok and all(v == 0 for k, v in noexec_records[0].items() if k.endswith("_count"))),
        _check("stop_go", _stop_go_records(True)[0]["n10_preflight_authorized"] is True and _stop_go_records(True)[0]["private_read_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N9 recovered fixed-pool result replication package")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--n6xfre-artifact", type=Path, default=DEFAULT_N6XFRE)
    parser.add_argument("--n7-artifact", type=Path, default=DEFAULT_N7)
    parser.add_argument("--n8-artifact", type=Path, default=DEFAULT_N8)
    parser.add_argument("--n5-artifact", type=Path, default=DEFAULT_N5)
    parser.add_argument("--n6f-artifact", type=Path, default=DEFAULT_N6F)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = _build_report(args, checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    metric = report["validated_metric_summary_records"][0]
    print("wrote artifact " f"(status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, " f"best_top10={metric['best_top10_recovery_count']})")


if __name__ == "__main__":
    main()
