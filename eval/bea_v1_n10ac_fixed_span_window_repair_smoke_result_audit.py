#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit.v1"
PHASE = "BEA-v1-N10AC Fixed Span-Window Repair Smoke Result Audit"
GENERATED_BY = "bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit"
STATUS_COMPLETE = "fixed_span_window_repair_smoke_result_audit_complete_n10ad_authorized"

STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10ac_required_inputs_unavailable",
    "no_go_n10ac_n10ab_result_invalid",
    "no_go_n10ac_privacy_or_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit_report.json")
INPUTS = {
    "n10ab_repair_smoke_artifact": (Path("artifacts/bea_v1_n10ab_fixed_span_window_repair_smoke/bea_v1_n10ab_fixed_span_window_repair_smoke_report.json"), "fixed_span_window_repair_smoke_pass_n10ac_authorized"),
    "n10aa_repair_preflight_artifact": (Path("artifacts/bea_v1_n10aa_span_window_repair_preflight/bea_v1_n10aa_span_window_repair_preflight_report.json"), "span_window_repair_preflight_pass_n10ab_authorized"),
    "n10z_failure_decomposition_artifact": (Path("artifacts/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition_report.json"), "n1_span_surface_span_level_failure_decomposition_complete_n10aa_authorized"),
    "n10x_span_level_validation_artifact": (Path("artifacts/bea_v1_n10x_n1_span_surface_span_level_utility_validation/bea_v1_n10x_n1_span_surface_span_level_utility_validation_report.json"), "n1_span_surface_span_level_utility_validation_complete_below_threshold"),
}
EXPECTED_VARIANTS = {
    "fixed_symmetric_span_expansion_pm20_lines": (15, 19, 6),
    "fixed_symmetric_span_expansion_pm50_lines": (19, 23, 10),
    "fixed_symmetric_span_expansion_pm100_lines": (21, 25, 12),
}

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "p4_evidence", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks", "score", "scores",
    "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "audit_bucket", "variant_bucket", "variant_role_bucket", "decision_bucket", "interpretation_bucket", "privacy_boundary_bucket",
    "no_execution_boundary_bucket", "n10ad_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
    "gate", "threshold_relation",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def root() -> Path:
    return Path(__file__).resolve().parent.parent



def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = root() / path
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(path: Path, data: dict[str, Any]) -> None:
    full = root() / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    digest_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)

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
            if digest_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})
            if line_re.search(value):
                violations.append({"category": "span_like_value", "location_bucket": "public_artifact"})
    walk(obj)
    return violations


def scan_summary(obj: Any) -> dict[str, Any]:
    violations = scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def input_artifact_records() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], bool]:
    records = []
    artifacts: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(INPUTS.items()):
        artifact, load_status = load_json(path)
        artifacts[bucket] = artifact
        observed = str(artifact.get("status", "") or "")
        forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
        passed = load_status == "pass" and observed == expected and forbidden == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n10acin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return records, artifacts, ok


def variant_map(n10ab: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in n10ab.get("repair_variant_execution_records", []):
        if isinstance(row, dict) and isinstance(row.get("variant_bucket"), str):
            out[str(row["variant_bucket"])] = row
    return out


def repair_smoke_result_audit_records(n10ab: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    primary = (n10ab.get("primary_decision_records") or [{}])[0]
    variants = variant_map(n10ab)
    pm50 = variants.get("fixed_symmetric_span_expansion_pm50_lines", {})
    gold = (n10ab.get("gold_free_execution_boundary_records") or [{}])[0]
    ok = (
        n10ab.get("status") == "fixed_span_window_repair_smoke_pass_n10ac_authorized"
        and primary.get("primary_pass_bool") is True
        and primary.get("observed_top10_expanded_span_overlap_count") == 19
        and primary.get("observed_top20_expanded_span_overlap_count") == 23
        and primary.get("baseline_unexpanded_top10_span_overlap_count") == 9
        and primary.get("delta_top10_vs_unexpanded_best_arm") == 10
        and primary.get("pass_threshold_count") == 11
        and primary.get("original_span_hit_lost_count") == 0
        and pm50.get("baseline_unexpanded_top20_span_overlap_count") == 10
        and pm50.get("top10_file_hit_count") == 34
        and pm50.get("candidate_pool_changed_bool") is False
        and pm50.get("candidate_added_count") == 0
        and pm50.get("candidate_removed_count") == 0
        and gold.get("gold_only_for_evaluation_bool") is True
        and gold.get("gold_signal_used_for_window_bool") is False
        and gold.get("miss_direction_used_for_window_bool") is False
    )
    return [{"anonymous_repair_smoke_result_audit_id": "n10acresult0000", "audit_bucket": "n10ab_primary_pm50_pass_audit", "baseline_unexpanded_top10_span_overlap_count": int(primary.get("baseline_unexpanded_top10_span_overlap_count", -1)), "baseline_unexpanded_top20_span_overlap_count": int(pm50.get("baseline_unexpanded_top20_span_overlap_count", -1)), "top10_file_hit_count": int(pm50.get("top10_file_hit_count", -1)), "pm50_top10_expanded_span_overlap_count": int(primary.get("observed_top10_expanded_span_overlap_count", -1)), "pm50_top20_expanded_span_overlap_count": int(primary.get("observed_top20_expanded_span_overlap_count", -1)), "pm50_delta_top10_vs_unexpanded_best_arm": int(primary.get("delta_top10_vs_unexpanded_best_arm", -1)), "pm50_pass_threshold_count": int(primary.get("pass_threshold_count", -1)), "original_span_hit_lost_count": int(primary.get("original_span_hit_lost_count", -1)), "primary_pass_bool": bool(primary.get("primary_pass_bool", False)), "candidate_pool_changed_bool": False, "candidate_added_count": 0, "candidate_removed_count": 0, "gold_only_for_evaluation_bool": True, "gold_or_miss_direction_used_for_window_bool": False, "result_audit_valid_bool": ok}], ok


def variant_sensitivity_audit_records(n10ab: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    variants = variant_map(n10ab)
    records = []
    ok = True
    for idx, (bucket, expected) in enumerate(EXPECTED_VARIANTS.items()):
        top10, top20, delta = expected
        row = variants.get(bucket, {})
        row_ok = row.get("top10_expanded_span_overlap_count") == top10 and row.get("top20_expanded_span_overlap_count") == top20 and row.get("delta_top10_vs_unexpanded_best_arm") == delta and row.get("original_span_hit_lost_count") == 0
        ok = ok and row_ok
        records.append({"anonymous_variant_sensitivity_audit_id": f"n10acvar{idx:04d}", "variant_bucket": bucket, "variant_role_bucket": str(row.get("variant_role_bucket", "")), "top10_expanded_span_overlap_count": int(row.get("top10_expanded_span_overlap_count", -1)), "top20_expanded_span_overlap_count": int(row.get("top20_expanded_span_overlap_count", -1)), "delta_top10_vs_unexpanded_best_arm": int(row.get("delta_top10_vs_unexpanded_best_arm", -1)), "original_span_hit_lost_count": int(row.get("original_span_hit_lost_count", -1)), "variant_audit_valid_bool": row_ok})
    return records, ok


def boundary_interpretation_records(result_ok: bool, variant_ok: bool) -> list[dict[str, Any]]:
    return [{"anonymous_boundary_interpretation_id": "n10acboundary0000", "interpretation_bucket": "fixed_local_span_window_expansion_recovers_span_overlap_on_n1_proxy_surface", "span_surface_repair_smoke_pass_bool": result_ok and variant_ok, "retrieval_result_bool": False, "selector_reranker_result_bool": False, "runtime_default_policy_bool": False, "method_winner_claim_supported_bool": False, "downstream_value_evidence_bool": False}]


def privacy_boundary_records(n10ab: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    privacy = (n10ab.get("privacy_boundary_records") or [{}])[0]
    ok = privacy.get("privacy_boundary_complete_bool") is True and all(privacy.get(k) is False for k in ("private_path_public_bool", "private_filename_public_bool", "private_content_public_bool", "candidate_list_public_bool", "gold_path_public_bool", "gold_line_public_bool", "exact_rank_public_bool", "span_public_bool", "snippet_public_bool", "hash_public_bool", "provider_payload_public_bool"))
    return [{"anonymous_privacy_boundary_id": "n10acprivacy0000", "privacy_boundary_bucket": "public_audit_counts_only_no_private_surface_details", "private_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_valid_bool": ok}], ok


def no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_execution_id": "n10acnoexec0000", "no_execution_boundary_bucket": "public_artifact_audit_no_private_read_no_recompute", "private_read_count": 0, "recompute_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "new_arm_search_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_execution_complete_bool": True}], True


def n10ad_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ad_handoff_id": "n10achandoff0000", "n10ad_handoff_bucket": "n10ad_independent_recompute_same_private_span_rows_authorized" if complete else "n10ad_not_authorized", "n10ad_independent_recompute_authorized_bool": complete, "n10ad_same_private_span_rows_read_authorized_bool": complete, "broad_private_read_authorized_bool": False, "runtime_default_promotion_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, result_ok: bool, variant_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok, int(input_ok), 1), ("n10ab_result_valid", result_ok, int(result_ok), 1), ("variant_sensitivity_valid", variant_ok, int(variant_ok), 1), ("pm50_top10_expanded_span_overlap_count", result_ok, 19 if result_ok else 0, 19), ("pm50_threshold_passed", result_ok, int(result_ok), 1), ("original_span_hit_lost_count", result_ok, 0 if result_ok else -1, 0), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("no_execution", noexec_ok, int(noexec_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ad_independent_recompute_authorized" if complete else "n10ad_not_authorized", "next_allowed_phase": "BEA-v1-N10AD Independent Recompute Fixed Span-Window Repair Smoke" if complete else "none_until_valid_n10ab_repair_smoke_result_exists", "next_allowed_scope_bucket": "same_private_span_rows_recompute_only" if complete else "no_next_phase", "n10ad_independent_recompute_authorized": complete, "n10ad_same_private_span_rows_read_authorized": complete, "broad_private_read_authorized": False, "runtime_or_default_promotion_authorized": False, "method_winner_claim_authorized": False, "method_winner_claimed": False, "downstream_value_claim_authorized": False, "downstream_value_claimed": False, "p5_authorized": False, "v1_a_authorized": False, "selector_or_reranker_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_materialization_authorized": False, "new_arm_search_authorized": False, "counterfactual_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, result_ok: bool, variant_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ac_required_inputs_unavailable"
    if not result_ok or not variant_ok:
        return "no_go_n10ac_n10ab_result_invalid"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10ac_privacy_or_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = input_artifact_records()
    n10ab = artifacts.get("n10ab_repair_smoke_artifact", {})
    result_records, result_ok = repair_smoke_result_audit_records(n10ab)
    variant_records, variant_ok = variant_sensitivity_audit_records(n10ab)
    privacy_records, privacy_ok = privacy_boundary_records(n10ab)
    noexec_records, noexec_ok = no_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, result_ok, variant_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_audit_of_fixed_span_window_repair_smoke", "generated_by": GENERATED_BY, "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "repair_smoke_result_audit_records": result_records, "variant_sensitivity_audit_records": variant_records, "boundary_interpretation_records": boundary_interpretation_records(result_ok, variant_ok), "privacy_boundary_records": privacy_records, "no_execution_records": noexec_records, "n10ad_handoff_records": n10ad_handoff_records(complete), "gate_records": gate_records(input_ok, result_ok, variant_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["gate_records"] = gate_records(input_ok, result_ok, variant_ok, privacy_ok, noexec_ok, scanner_ok)
    report["n10ad_handoff_records"] = n10ad_handoff_records(complete)
    report["stop_go_records"] = stop_go_records(complete)
    return report


def check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--unknown", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    inputs, artifacts, input_ok = input_artifact_records()
    n10ab = artifacts.get("n10ab_repair_smoke_artifact", {})
    result_records, result_ok = repair_smoke_result_audit_records(n10ab)
    variant_records, variant_ok = variant_sensitivity_audit_records(n10ab)
    privacy_records, privacy_ok = privacy_boundary_records(n10ab)
    noexec_records, noexec_ok = no_execution_records()
    by_variant = {r["variant_bucket"]: r for r in variant_records}
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10ac_required_inputs_unavailable", "no_go_n10ac_n10ab_result_invalid", "no_go_n10ac_privacy_or_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "gold_lines", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("public_inputs", input_ok and len(inputs) == 4),
        check("primary", result_ok and result_records[0]["pm50_top10_expanded_span_overlap_count"] == 19 and result_records[0]["pm50_top20_expanded_span_overlap_count"] == 23 and result_records[0]["pm50_delta_top10_vs_unexpanded_best_arm"] == 10),
        check("baseline", result_records[0]["baseline_unexpanded_top10_span_overlap_count"] == 9 and result_records[0]["baseline_unexpanded_top20_span_overlap_count"] == 10 and result_records[0]["top10_file_hit_count"] == 34),
        check("sensitivity", variant_ok and by_variant["fixed_symmetric_span_expansion_pm20_lines"]["top10_expanded_span_overlap_count"] == 15 and by_variant["fixed_symmetric_span_expansion_pm100_lines"]["top20_expanded_span_overlap_count"] == 25),
        check("boundary", boundary_interpretation_records(True, True)[0]["runtime_default_policy_bool"] is False and boundary_interpretation_records(True, True)[0]["method_winner_claim_supported_bool"] is False),
        check("privacy", privacy_ok and privacy_records[0]["private_read_count"] == 0 and privacy_records[0]["gold_line_public_bool"] is False),
        check("no_execution", noexec_ok and all(v == 0 for k, v in noexec_records[0].items() if k.endswith("_count"))),
        check("handoff", n10ad_handoff_records(True)[0]["n10ad_independent_recompute_authorized_bool"] is True and n10ad_handoff_records(True)[0]["broad_private_read_authorized_bool"] is False),
        check("stop_go", stop_go_records(True)[0]["n10ad_same_private_span_rows_read_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_promotion_authorized"] is False),
        check("status_expected", status_for(True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AC fixed span-window repair smoke result audit")
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
    primary = report["repair_smoke_result_audit_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, pm50_top10={primary['pm50_top10_expanded_span_overlap_count']})")


if __name__ == "__main__":
    main()
