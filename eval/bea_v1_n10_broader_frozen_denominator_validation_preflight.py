#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10_broader_frozen_denominator_validation_preflight.v1"
PHASE = "BEA-v1-N10 Broader Frozen Denominator Validation Preflight"
GENERATED_BY = "bea_v1_n10_broader_frozen_denominator_validation_preflight"
STATUS_NO_GO = "no_go_n10_broader_rank_pack_denominator_unavailable"

STATUSES = (
    "broader_frozen_denominator_preflight_pass_n11_authorized",
    "no_go_n10_required_inputs_unavailable",
    STATUS_NO_GO,
    "no_go_n10_broader_denominator_incomplete_or_ambiguous",
    "no_go_n10_privacy_or_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_n10_broader_frozen_denominator_validation_preflight/bea_v1_n10_broader_frozen_denominator_validation_preflight_report.json")
DEFAULT_INPUTS = {
    "n9_replication_package_artifact": (Path("artifacts/bea_v1_n9_recovered_fixed_pool_result_replication_package/bea_v1_n9_recovered_fixed_pool_result_replication_package_report.json"), "recovered_fixed_pool_result_replication_package_complete"),
    "n8_independent_recompute_artifact": (Path("artifacts/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms_report.json"), "independent_recompute_same_private_rows_pass_n9_authorized"),
    "n6xfre_recovered_experiment_artifact": (Path("artifacts/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment_report.json"), "recovered_fixed_pool_rank_order_experiment_pass_n7_authorized"),
    "n6f_materialization_design_artifact": (Path("artifacts/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design_report.json"), "fixed_pool_public_arm_field_materialization_design_pass"),
    "p4l_locked_scheduler_artifact": (Path("artifacts/bea_v1_p4l_locked_non_python_scheduler_validation/bea_v1_p4l_locked_non_python_scheduler_validation_report.json"), "bea_v1_p4l_locked_non_python_scheduler_validation_pass"),
    "n1_span_refiner_artifact": (Path("artifacts/bea_v1_n1_frozen_p4_span_refiner_smoke/bea_v1_n1_frozen_p4_span_refiner_smoke_report.json"), "no_go_n1_inadequate_top10_actionable_denominator"),
    "n2_rank_pack_decomposition_artifact": (Path("artifacts/bea_v1_n2_rank_pack_actionability_decomposition/bea_v1_n2_rank_pack_actionability_decomposition_report.json"), "n2_rank_pack_actionability_decomposition_pass"),
}

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "gold_path", "gold_paths", "exact_rank", "raw_rank", "rank", "ranks", "score", "scores",
    "repo_id", "repo_name", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "result_bucket", "best_arm_bucket", "threshold_bucket", "candidate_denominator_bucket", "denominator_role_bucket",
    "availability_bucket", "field_contract_bucket", "feasibility_bucket", "blocker_bucket", "privacy_boundary_bucket",
    "no_execution_boundary_bucket", "n11_handoff_bucket", "gate", "threshold_relation", "authorization",
    "next_allowed_phase", "next_allowed_scope_bucket", "size_bucket", "schema_version_bucket", "extension_bucket",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = path if path.is_absolute() else repo_root() / path
    if not full.exists():
        return {}, "missing"
    try:
        data = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (data, "pass") if isinstance(data, dict) else ({}, "parse_failed")


def write_json(path: Path, data: dict[str, Any]) -> None:
    full = path if path.is_absolute() else repo_root() / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
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
            if digest_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})
    walk(obj)
    return violations


def scan_summary(obj: Any) -> dict[str, Any]:
    violations = scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def size_bucket(size: int | None) -> str:
    if size is None:
        return "none"
    if size < 1024 * 1024:
        return "small"
    if size < 100 * 1024 * 1024:
        return "medium"
    return "large"


def metadata_bucket(private_bucket: str) -> dict[str, Any]:
    # Exact local names are used only internally and are never serialized.
    rels = {
        "p4l_private_arm_outcomes": [".openlocus/research-private/local_n6xfr_recovery/p4l_validation/bea_v1_p4l.private_arm_outcomes.jsonl"],
        "n1_candidate_gold_trace": [".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_candidate_gold_trace.jsonl"],
        "n1_span_rows": [".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl"],
        "n2_private_rank_pack_rows": [".openlocus/research-private/local_n6xfr_recovery/n2_private/bea_v1_n2.private_rank_pack_rows.jsonl"],
    }
    files = [repo_root() / rel for rel in rels.get(private_bucket, [])]
    sizes = [p.stat().st_size for p in files if p.exists() and p.is_file()]
    return {
        "metadata_checked_bool": True,
        "private_content_read_bool": False,
        "private_path_public_bool": False,
        "private_filename_public_bool": False,
        "candidate_file_count_bucket": "one" if len(sizes) == 1 else ("zero" if not sizes else "few"),
        "candidate_size_bucket": "none" if not sizes else (size_bucket(sizes[0]) if len(sizes) == 1 else "mixed"),
        "extension_bucket": "jsonl" if sizes else "none",
        "schema_version_bucket": "not_read_metadata_only",
    }


def input_artifact_records() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(DEFAULT_INPUTS.items()):
        data, load = load_json(path)
        artifacts[bucket] = data
        observed = str(data.get("status", "") or "")
        scan = data.get("forbidden_scan", {}).get("status", "pass") if isinstance(data.get("forbidden_scan"), dict) else "pass"
        passed = load == "pass" and observed == expected and scan == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n10in{idx:04d}", "input_artifact_bucket": bucket, "load_status": load, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan), "input_gate_passed_bool": passed})
    return records, artifacts, ok


def recovered_result_summary_records(n9: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    metric = (n9.get("validated_metric_summary_records") or [{}])[0]
    ok = metric.get("case_count") == 40 and metric.get("arm_count") == 4 and metric.get("public_arm_outcome_rows") == 160 and metric.get("best_arm_bucket") == "extra_depth_promote_before_primary_prefix_4" and metric.get("best_top10_recovery_count") == 25 and metric.get("best_top20_recovery_count") == 34 and metric.get("best_case_regression_count") == 0 and metric.get("threshold_passed_bool") is True
    return [{"anonymous_recovered_result_summary_id": "n10summary0000", "result_bucket": "n6xfre_n8_replicated_recovered_40_case_result", "case_count": 40, "arm_count": 4, "public_arm_outcome_rows": 160, "best_arm_bucket": "extra_depth_promote_before_primary_prefix_4", "best_top10_recovery_count": 25, "best_top20_recovery_count": 34, "best_case_regression_count": 0, "threshold_bucket": "top10_recovery_ge_16_and_regressions_le_2", "threshold_passed_bool": True, "summary_matches_n9_bool": ok}], ok


def candidate_broader_denominator_records() -> list[dict[str, Any]]:
    specs = [
        ("n2_recovered_40_rank_blocked", "recovered_exact_rank_pack_not_broader", 40, True, False),
        ("p4l_locked_272", "broader_context_no_n2_equivalent_rank_pack", 272, False, True),
        ("n1_candidate_gold_trace_272", "broader_trace_context_no_n2_equivalent_rank_pack", 272, False, True),
        ("n1_span_rows_213", "span_context_no_n2_equivalent_rank_pack", 213, False, True),
    ]
    return [{"anonymous_candidate_denominator_id": f"n10den{idx:04d}", "candidate_denominator_bucket": bucket, "denominator_role_bucket": role, "candidate_case_count": count, "has_exact_n2_equivalent_rank_pack_fields_bool": exact, "broader_than_recovered_40_bool": broader, "usable_for_broader_validation_bool": exact and broader} for idx, (bucket, role, count, exact, broader) in enumerate(specs)]


def rank_pack_field_availability_records() -> list[dict[str, Any]]:
    buckets = ["p4l_private_arm_outcomes", "n1_candidate_gold_trace", "n1_span_rows", "n2_private_rank_pack_rows"]
    records = []
    for idx, bucket in enumerate(buckets):
        meta = metadata_bucket(bucket)
        exact = bucket == "n2_private_rank_pack_rows"
        broader = bucket != "n2_private_rank_pack_rows"
        records.append({"anonymous_rank_pack_field_availability_id": f"n10field{idx:04d}", "availability_bucket": bucket, "field_contract_bucket": "n2_equivalent_rank_pack_fields" if exact else "not_n2_equivalent_rank_pack_fields", "has_candidate_order_private_bool": exact, "has_gold_paths_private_bool": exact, "has_first_gold_rank_private_bool": exact, "has_denominator_index_private_bool": exact, "broader_than_recovered_40_bool": broader, "usable_for_broader_validation_bool": False, **meta})
    return records


def broader_validation_feasibility_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_broader_validation_feasibility_id": "n10feas0000", "feasibility_bucket": "not_feasible_current_inputs", "blocker_bucket": "no_broader_n2_equivalent_rank_pack_rows", "required_broader_case_count_minimum": 41, "covered_broader_n2_equivalent_rank_pack_case_count": 0, "n2_recovered_40_exact_but_not_broader_bool": True, "broader_context_without_required_fields_bool": True, "compute_new_arm_outcomes_authorized_bool": False, "broader_validation_feasible_bool": False}], False


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10privacy0000", "privacy_boundary_bucket": "metadata_only_no_private_content_no_paths", "private_content_read_bool": False, "private_path_public_bool": False, "private_filename_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "exact_rank_public_bool": False, "task_repo_id_public_bool": False, "source_span_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_execution_id": "n10noexec0000", "no_execution_boundary_bucket": "preflight_only_metadata_no_outcome_compute", "private_content_read_count": 0, "new_arm_outcome_compute_count": 0, "n6xfre_n8_recompute_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_n3_rerun_count": 0, "openlocus_binary_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_execution_complete_bool": True}], True


def n11_handoff_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n11_handoff_id": "n10handoff0000", "n11_handoff_bucket": "n11_not_authorized_no_broader_rank_pack" if not pass_status else "broader_rank_pack_validation_authorized", "n11_authorized_bool": pass_status, "required_input_bucket": "broader_n2_equivalent_rank_pack_rows", "private_content_read_authorized_bool": False, "new_arm_outcome_compute_authorized_bool": False}]


def gate_records(input_ok: bool, summary_ok: bool, feasibility: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok, int(input_ok), 1), ("recovered_result_summary_valid", summary_ok, int(summary_ok), 1), ("broader_n2_equivalent_rank_pack_available", feasibility, int(feasibility), 1), ("private_content_read_count", True, 0, 0), ("new_arm_outcome_compute_count", True, 0, 0), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("no_execution", noexec_ok, int(noexec_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n11_not_authorized" if not pass_status else "n11_broader_validation_authorized", "next_allowed_phase": "none_until_broader_n2_equivalent_rank_pack_rows_exist" if not pass_status else "BEA-v1-N11 Broader Frozen Denominator Validation", "next_allowed_scope_bucket": "blocked_on_broader_rank_pack_rows" if not pass_status else "n11_validation_only", "n11_authorized": pass_status, "private_content_read_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_or_default_promotion_authorized": False, "method_winner_claim_authorized": False, "method_winner_claimed": False, "downstream_value_claim_authorized": False, "downstream_value_claimed": False}]


def status_for(self_ok: bool, input_ok: bool, summary_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10_required_inputs_unavailable"
    if not summary_ok:
        return "no_go_n10_broader_denominator_incomplete_or_ambiguous"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10_privacy_or_claim_boundary_invalid"
    return STATUS_NO_GO


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = input_artifact_records()
    summary, summary_ok = recovered_result_summary_records(artifacts.get("n9_replication_package_artifact", {}))
    denom = candidate_broader_denominator_records()
    fields = rank_pack_field_availability_records()
    feasibility, feasible = broader_validation_feasibility_records()
    privacy, privacy_ok = privacy_boundary_records()
    noexec, noexec_ok = no_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, summary_ok, privacy_ok, noexec_ok)
    pass_status = status == "broader_frozen_denominator_preflight_pass_n11_authorized"
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "broader_denominator_preflight_only", "generated_by": GENERATED_BY, "generated_at": now_iso(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "recovered_result_summary_records": summary, "candidate_broader_denominator_records": denom, "rank_pack_field_availability_records": fields, "broader_validation_feasibility_records": feasibility, "privacy_boundary_records": privacy, "no_execution_records": noexec, "n11_handoff_records": n11_handoff_records(pass_status), "gate_records": gate_records(input_ok, summary_ok, feasible, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(pass_status), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    pass_status = report["status"] == "broader_frozen_denominator_preflight_pass_n11_authorized"
    report["gate_records"] = gate_records(input_ok, summary_ok, feasible, privacy_ok, noexec_ok, scanner_ok)
    report["n11_handoff_records"] = n11_handoff_records(pass_status)
    report["stop_go_records"] = stop_go_records(pass_status)
    return report


def check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--bad", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    inputs, artifacts, input_ok = input_artifact_records()
    summary, summary_ok = recovered_result_summary_records(artifacts.get("n9_replication_package_artifact", {}))
    denom = candidate_broader_denominator_records()
    fields = rank_pack_field_availability_records()
    feasibility, feasible = broader_validation_feasibility_records()
    privacy, privacy_ok = privacy_boundary_records()
    noexec, noexec_ok = no_execution_records()
    checks = [
        check("status_vocabulary", STATUSES[2] == STATUS_NO_GO and len(STATUSES) == 7),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "blocked"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_path", "exact_rank", "repo_id", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("inputs", input_ok and len(inputs) == 7),
        check("summary", summary_ok and summary[0]["best_top10_recovery_count"] == 25 and summary[0]["best_top20_recovery_count"] == 34),
        check("denominators", len(denom) == 4 and denom[0]["candidate_denominator_bucket"] == "n2_recovered_40_rank_blocked" and not any(r["usable_for_broader_validation_bool"] for r in denom)),
        check("field_metadata_only", len(fields) == 4 and all(r["private_content_read_bool"] is False and r["private_path_public_bool"] is False for r in fields)),
        check("feasibility_no_go", feasible is False and feasibility[0]["blocker_bucket"] == "no_broader_n2_equivalent_rank_pack_rows"),
        check("privacy", privacy_ok and privacy[0]["private_content_read_bool"] is False and privacy[0]["exact_rank_public_bool"] is False),
        check("no_execution", noexec_ok and all(v == 0 for k, v in noexec[0].items() if k.endswith("_count"))),
        check("n11_handoff", n11_handoff_records(False)[0]["n11_authorized_bool"] is False),
        check("stop_go", stop_go_records(False)[0]["next_allowed_phase"] == "none_until_broader_n2_equivalent_rank_pack_rows_exist" and stop_go_records(False)[0]["private_content_read_authorized"] is False),
        check("expected_status", status_for(True, True, True, True, True) == STATUS_NO_GO),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10 broader frozen denominator validation preflight")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for item in checks:
            print(f"[{'PASS' if item['passed'] else 'FAIL'}] {item['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = build_report(checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    write_json(args.out, report)
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")


if __name__ == "__main__":
    main()
