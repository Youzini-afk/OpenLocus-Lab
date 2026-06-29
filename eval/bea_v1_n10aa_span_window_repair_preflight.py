#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10aa_span_window_repair_preflight.v1"
PHASE = "BEA-v1-N10AA Span-Window Repair Preflight"
GENERATED_BY = "bea_v1_n10aa_span_window_repair_preflight"
STATUS_PASS = "span_window_repair_preflight_pass_n10ab_authorized"

STATUSES = (
    STATUS_PASS,
    "no_go_n10aa_required_inputs_unavailable",
    "no_go_n10aa_failure_decomposition_not_supported",
    "no_go_n10aa_repair_contract_incomplete",
    "no_go_n10aa_gold_free_boundary_invalid",
    "no_go_n10aa_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_n10aa_span_window_repair_preflight/bea_v1_n10aa_span_window_repair_preflight_report.json")
INPUTS = {
    "n10z_failure_decomposition_artifact": (Path("artifacts/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition_report.json"), "n1_span_surface_span_level_failure_decomposition_complete_n10aa_authorized"),
    "n10x_span_level_validation_artifact": (Path("artifacts/bea_v1_n10x_n1_span_surface_span_level_utility_validation/bea_v1_n10x_n1_span_surface_span_level_utility_validation_report.json"), "n1_span_surface_span_level_utility_validation_complete_below_threshold"),
    "n10y_span_level_result_audit_artifact": (Path("artifacts/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit_report.json"), "n1_span_surface_span_level_utility_result_audit_complete"),
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
    "summary_bucket", "variant_bucket", "variant_role_bucket", "expansion_rule_bucket", "policy_bucket", "metric_bucket",
    "privacy_boundary_bucket", "no_execution_boundary_bucket", "n10ab_handoff_bucket", "authorization", "next_allowed_phase",
    "next_allowed_scope_bucket", "gate", "threshold_relation",
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
        records.append({"anonymous_input_artifact_id": f"n10aain{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return records, artifacts, ok


def n10z_counts(n10z: dict[str, Any]) -> dict[str, Any]:
    gap = (n10z.get("file_vs_span_gap_records") or [{}])[0]
    miss = {r.get("miss_bucket"): r.get("case_count") for r in n10z.get("top10_span_miss_bucket_records", []) if isinstance(r, dict)}
    repair = (n10z.get("repair_signal_records") or [{}])[0]
    return {
        "file_hit_no_span_overlap_count": gap.get("file_hit_no_span_overlap_count"),
        "top10_file_hit_count": gap.get("top10_file_hit_count"),
        "top10_span_overlap_count": gap.get("top10_span_overlap_count"),
        "span_reachable_total": gap.get("span_reachable_total"),
        "same_file_before_gold_count": miss.get("same_file_before_gold", 0),
        "same_file_after_gold_count": miss.get("same_file_after_gold", 0),
        "same_file_no_overlap_dominates_bool": repair.get("same_file_no_overlap_dominates_bool"),
    }


def failure_decomposition_summary_records(n10z: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    counts = n10z_counts(n10z)
    ok = n10z.get("status") == "n1_span_surface_span_level_failure_decomposition_complete_n10aa_authorized" and counts == {
        "file_hit_no_span_overlap_count": 25,
        "top10_file_hit_count": 34,
        "top10_span_overlap_count": 9,
        "span_reachable_total": 12,
        "same_file_before_gold_count": 17,
        "same_file_after_gold_count": 8,
        "same_file_no_overlap_dominates_bool": True,
    }
    return [{"anonymous_failure_decomposition_summary_id": "n10aasummary0000", "summary_bucket": "same_file_span_window_misalignment_supported", **counts, "failure_decomposition_supports_repair_preflight_bool": ok}], ok


def repair_variant_design_records() -> tuple[list[dict[str, Any]], bool]:
    specs = [("fixed_symmetric_span_expansion_pm50_lines", "primary", 50), ("fixed_symmetric_span_expansion_pm20_lines", "secondary_sensitivity", 20), ("fixed_symmetric_span_expansion_pm100_lines", "secondary_sensitivity", 100)]
    records = []
    for idx, (bucket, role, amount) in enumerate(specs):
        records.append({"anonymous_repair_variant_design_id": f"n10aavar{idx:04d}", "variant_bucket": bucket, "variant_role_bucket": role, "expansion_each_side_count": amount, "expansion_rule_bucket": "expanded_start_max_1_start_minus_fixed_window_and_expanded_end_end_plus_fixed_window", "applies_to_top10_after_best_arm_bool": True, "candidate_pool_changed_bool": False, "candidate_added_bool": False, "candidate_removed_bool": False, "path_changed_bool": False, "content_aware_adjustment_bool": False, "gold_signal_used_bool": False, "miss_direction_used_bool": False, "complete_bool": True})
    ok = len(records) == 3 and records[0]["variant_bucket"] == "fixed_symmetric_span_expansion_pm50_lines" and records[0]["variant_role_bucket"] == "primary"
    return records, ok


def gold_free_policy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_gold_free_policy_boundary_id": "n10aagold0000", "policy_bucket": "fixed_symmetric_no_gold_no_direction_no_content_adjustment", "gold_signal_used_for_amount_bool": False, "gold_signal_used_for_shift_bool": False, "miss_direction_used_for_amount_bool": False, "content_aware_adjustment_bool": False, "path_change_bool": False, "candidate_add_remove_bool": False, "policy_boundary_complete_bool": True}], True


def n10ab_metric_contract_records() -> tuple[list[dict[str, Any]], bool]:
    records = [
        {"anonymous_n10ab_metric_contract_id": "n10aametric0000", "metric_bucket": "primary_top10_expanded_span_overlap_count_pm50", "baseline_n10x_best_arm_top10_span_overlap_count": 9, "pass_threshold_count": 11, "primary_metric_bool": True, "public_line_numbers_bool": False, "complete_bool": True},
        {"anonymous_n10ab_metric_contract_id": "n10aametric0001", "metric_bucket": "secondary_top20_expanded_span_overlap_count_pm50", "primary_metric_bool": False, "public_line_numbers_bool": False, "complete_bool": True},
        {"anonymous_n10ab_metric_contract_id": "n10aametric0002", "metric_bucket": "secondary_delta_vs_n10x_best_arm", "primary_metric_bool": False, "public_line_numbers_bool": False, "complete_bool": True},
        {"anonymous_n10ab_metric_contract_id": "n10aametric0003", "metric_bucket": "secondary_expansion_overreach_buckets", "primary_metric_bool": False, "public_line_numbers_bool": False, "complete_bool": True},
    ]
    return records, True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10aaprivacy0000", "privacy_boundary_bucket": "public_design_buckets_only_no_private_surface_details", "private_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_execution_id": "n10aanoexec0000", "no_execution_boundary_bucket": "public_preflight_design_only_no_repair_execution", "private_read_count": 0, "repair_execution_count": 0, "span_expansion_evaluation_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "new_arm_search_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_execution_complete_bool": True}], True


def n10ab_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ab_handoff_id": "n10aahandoff0000", "n10ab_handoff_bucket": "n10ab_fixed_span_window_repair_smoke_authorized" if complete else "n10ab_not_authorized", "n10ab_fixed_span_window_repair_smoke_authorized_bool": complete, "n10ab_same_private_span_rows_read_authorized_bool": complete, "repair_execution_authorized_in_n10aa_bool": False, "private_read_authorized_in_n10aa_bool": False, "runtime_default_promotion_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, summary_ok: bool, variants_ok: bool, gold_ok: bool, metric_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok, int(input_ok), 1), ("failure_decomposition_supported", summary_ok, int(summary_ok), 1), ("file_hit_no_span_overlap_count", summary_ok, 25 if summary_ok else 0, 25), ("same_file_before_gold_count", summary_ok, 17 if summary_ok else 0, 17), ("same_file_after_gold_count", summary_ok, 8 if summary_ok else 0, 8), ("variant_count", variants_ok, 3 if variants_ok else 0, 3), ("primary_variant_pm50", variants_ok, int(variants_ok), 1), ("gold_free_boundary", gold_ok, int(gold_ok), 1), ("metric_contract", metric_ok, int(metric_ok), 1), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("no_execution", noexec_ok, int(noexec_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ab_fixed_span_window_repair_smoke_authorized" if complete else "n10ab_not_authorized", "next_allowed_phase": "BEA-v1-N10AB Fixed Span-Window Repair Smoke" if complete else "none_until_valid_span_window_repair_preflight_exists", "next_allowed_scope_bucket": "fixed_pm50_primary_smoke_only" if complete else "no_next_phase", "n10ab_authorized": complete, "n10ab_same_private_span_rows_read_authorized": complete, "repair_execution_authorized_in_n10aa": False, "private_read_authorized_in_n10aa": False, "retrieval_authorized": False, "rerun_authorized": False, "openlocus_execution_authorized": False, "candidate_generation_authorized": False, "candidate_materialization_authorized": False, "new_arm_search_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "counterfactual_authorized": False, "runtime_or_default_promotion_authorized": False, "method_winner_claim_authorized": False, "method_winner_claimed": False, "downstream_value_claim_authorized": False, "downstream_value_claimed": False}]


def status_for(self_ok: bool, input_ok: bool, summary_ok: bool, variants_ok: bool, gold_ok: bool, metric_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10aa_required_inputs_unavailable"
    if not summary_ok:
        return "no_go_n10aa_failure_decomposition_not_supported"
    if not variants_ok or not metric_ok:
        return "no_go_n10aa_repair_contract_incomplete"
    if not gold_ok:
        return "no_go_n10aa_gold_free_boundary_invalid"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10aa_privacy_or_claim_boundary_failed"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = input_artifact_records()
    summary_records, summary_ok = failure_decomposition_summary_records(artifacts.get("n10z_failure_decomposition_artifact", {}))
    variant_records, variants_ok = repair_variant_design_records()
    gold_records, gold_ok = gold_free_policy_boundary_records()
    metric_records, metric_ok = n10ab_metric_contract_records()
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, summary_ok, variants_ok, gold_ok, metric_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "span_window_repair_preflight_design_only", "generated_by": GENERATED_BY, "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "failure_decomposition_summary_records": summary_records, "repair_variant_design_records": variant_records, "gold_free_policy_boundary_records": gold_records, "n10ab_metric_contract_records": metric_records, "privacy_boundary_records": privacy_records, "no_execution_records": noexec_records, "n10ab_handoff_records": n10ab_handoff_records(complete), "gate_records": gate_records(input_ok, summary_ok, variants_ok, gold_ok, metric_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["gate_records"] = gate_records(input_ok, summary_ok, variants_ok, gold_ok, metric_ok, privacy_ok, noexec_ok, scanner_ok)
    report["n10ab_handoff_records"] = n10ab_handoff_records(complete)
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
    summary_records, summary_ok = failure_decomposition_summary_records(artifacts.get("n10z_failure_decomposition_artifact", {}))
    variant_records, variants_ok = repair_variant_design_records()
    gold_records, gold_ok = gold_free_policy_boundary_records()
    metric_records, metric_ok = n10ab_metric_contract_records()
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10aa_required_inputs_unavailable", "no_go_n10aa_failure_decomposition_not_supported", "no_go_n10aa_repair_contract_incomplete", "no_go_n10aa_gold_free_boundary_invalid", "no_go_n10aa_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "gold_lines", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("public_inputs", input_ok and len(inputs) == 3),
        check("summary", summary_ok and summary_records[0]["file_hit_no_span_overlap_count"] == 25 and summary_records[0]["same_file_before_gold_count"] == 17 and summary_records[0]["same_file_after_gold_count"] == 8),
        check("variants", variants_ok and len(variant_records) == 3 and variant_records[0]["variant_bucket"] == "fixed_symmetric_span_expansion_pm50_lines"),
        check("gold_free", gold_ok and gold_records[0]["gold_signal_used_for_amount_bool"] is False and gold_records[0]["miss_direction_used_for_amount_bool"] is False),
        check("metrics", metric_ok and metric_records[0]["baseline_n10x_best_arm_top10_span_overlap_count"] == 9 and metric_records[0]["pass_threshold_count"] == 11),
        check("privacy", privacy_ok and privacy_records[0]["private_read_count"] == 0 and privacy_records[0]["gold_line_public_bool"] is False),
        check("no_execution", noexec_ok and all(v == 0 for k, v in noexec_records[0].items() if k.endswith("_count"))),
        check("handoff", n10ab_handoff_records(True)[0]["n10ab_fixed_span_window_repair_smoke_authorized_bool"] is True and n10ab_handoff_records(True)[0]["repair_execution_authorized_in_n10aa_bool"] is False),
        check("stop_go", stop_go_records(True)[0]["n10ab_same_private_span_rows_read_authorized"] is True and stop_go_records(True)[0]["repair_execution_authorized_in_n10aa"] is False),
        check("status_expected", status_for(True, True, True, True, True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AA span-window repair preflight")
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, variants={len(report['repair_variant_design_records'])})")


if __name__ == "__main__":
    main()
