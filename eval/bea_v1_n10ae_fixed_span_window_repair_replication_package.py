#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10ae_fixed_span_window_repair_replication_package.v1"
PHASE = "BEA-v1-N10AE Fixed Span-Window Repair Replication Package"
STATUS_COMPLETE = "fixed_span_window_repair_replication_package_complete_n10af_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10ae_required_inputs_unavailable",
    "no_go_n10ae_chain_inconsistent",
    "no_go_n10ae_privacy_or_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_n10ae_fixed_span_window_repair_replication_package/bea_v1_n10ae_fixed_span_window_repair_replication_package_report.json")
INPUTS = {
    "n10ab_repair_smoke_artifact": (Path("artifacts/bea_v1_n10ab_fixed_span_window_repair_smoke/bea_v1_n10ab_fixed_span_window_repair_smoke_report.json"), "fixed_span_window_repair_smoke_pass_n10ac_authorized"),
    "n10ac_public_audit_artifact": (Path("artifacts/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit_report.json"), "fixed_span_window_repair_smoke_result_audit_complete_n10ad_authorized"),
    "n10ad_independent_recompute_artifact": (Path("artifacts/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke_report.json"), "independent_recompute_fixed_span_window_repair_smoke_pass_n10ae_authorized"),
    "n10aa_repair_preflight_artifact": (Path("artifacts/bea_v1_n10aa_span_window_repair_preflight/bea_v1_n10aa_span_window_repair_preflight_report.json"), "span_window_repair_preflight_pass_n10ab_authorized"),
    "n10z_failure_decomposition_artifact": (Path("artifacts/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition_report.json"), "n1_span_surface_span_level_failure_decomposition_complete_n10aa_authorized"),
}
EXPECTED_METRICS = {
    "baseline_top10_span_overlap_count": 9,
    "baseline_top20_span_overlap_count": 10,
    "pm20_top10_expanded_span_overlap_count": 15,
    "pm20_top20_expanded_span_overlap_count": 19,
    "pm50_top10_expanded_span_overlap_count": 19,
    "pm50_top20_expanded_span_overlap_count": 23,
    "pm50_delta_top10_vs_unexpanded_best_arm": 10,
    "pm50_pass_threshold_count": 11,
    "pm100_top10_expanded_span_overlap_count": 21,
    "pm100_top20_expanded_span_overlap_count": 25,
    "original_span_hit_lost_count": 0,
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
    "chain_bucket", "metric_bucket", "claim_boundary_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket",
    "n10af_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
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
    records: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(INPUTS.items()):
        artifact, load_status = load_json(path)
        artifacts[bucket] = artifact
        observed = str(artifact.get("status", "") or "")
        forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
        passed = load_status == "pass" and observed == expected and forbidden == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n10aein{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return records, artifacts, ok


def _variant_map(records: list[Any], key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in records:
        if isinstance(row, dict) and isinstance(row.get("variant_bucket"), str):
            out[str(row["variant_bucket"])] = row
    return out


def replication_chain_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10ab = artifacts.get("n10ab_repair_smoke_artifact", {})
    n10ac = artifacts.get("n10ac_public_audit_artifact", {})
    n10ad = artifacts.get("n10ad_independent_recompute_artifact", {})
    indep = (n10ad.get("independence_boundary_records") or [{}])[0]
    matches = n10ad.get("aggregate_match_records", [])
    ok = (
        n10ab.get("status") == "fixed_span_window_repair_smoke_pass_n10ac_authorized"
        and n10ac.get("status") == "fixed_span_window_repair_smoke_result_audit_complete_n10ad_authorized"
        and n10ad.get("status") == "independent_recompute_fixed_span_window_repair_smoke_pass_n10ae_authorized"
        and indep.get("n10ab_code_call_count") == 0
        and all(isinstance(r, dict) and r.get("aggregate_match_bool") is True for r in matches)
        and len(matches) == 4
    )
    return [{"anonymous_replication_chain_id": "n10aechain0000", "chain_bucket": "n10ab_pass_n10ac_audit_n10ad_independent_match", "n10ab_pass_bool": n10ab.get("status") == "fixed_span_window_repair_smoke_pass_n10ac_authorized", "n10ac_audit_complete_bool": n10ac.get("status") == "fixed_span_window_repair_smoke_result_audit_complete_n10ad_authorized", "n10ad_independent_recompute_pass_bool": n10ad.get("status") == "independent_recompute_fixed_span_window_repair_smoke_pass_n10ae_authorized", "n10ad_aggregate_match_bool": len(matches) == 4 and all(isinstance(r, dict) and r.get("aggregate_match_bool") is True for r in matches), "n10ab_code_call_count": int(indep.get("n10ab_code_call_count", -1)), "chain_consistent_bool": ok}], ok


def metric_consistency_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10ab = artifacts.get("n10ab_repair_smoke_artifact", {})
    n10ac = artifacts.get("n10ac_public_audit_artifact", {})
    n10ad = artifacts.get("n10ad_independent_recompute_artifact", {})
    ab = _variant_map(n10ab.get("repair_variant_execution_records", []), "variant_bucket")
    ad = _variant_map(n10ad.get("independent_recompute_records", []), "variant_bucket")
    ac = (n10ac.get("repair_smoke_result_audit_records") or [{}])[0]
    pm20_ab, pm50_ab, pm100_ab = ab.get("fixed_symmetric_span_expansion_pm20_lines", {}), ab.get("fixed_symmetric_span_expansion_pm50_lines", {}), ab.get("fixed_symmetric_span_expansion_pm100_lines", {})
    pm20_ad, pm50_ad, pm100_ad = ad.get("fixed_symmetric_span_expansion_pm20_lines", {}), ad.get("fixed_symmetric_span_expansion_pm50_lines", {}), ad.get("fixed_symmetric_span_expansion_pm100_lines", {})
    base_ad = ad.get("unexpanded_best_arm", {})
    values = {
        "baseline_top10_span_overlap_count": base_ad.get("top10_span_overlap_count"),
        "baseline_top20_span_overlap_count": base_ad.get("top20_span_overlap_count"),
        "pm20_top10_expanded_span_overlap_count": pm20_ad.get("top10_span_overlap_count"),
        "pm20_top20_expanded_span_overlap_count": pm20_ad.get("top20_span_overlap_count"),
        "pm50_top10_expanded_span_overlap_count": pm50_ad.get("top10_span_overlap_count"),
        "pm50_top20_expanded_span_overlap_count": pm50_ad.get("top20_span_overlap_count"),
        "pm50_delta_top10_vs_unexpanded_best_arm": pm50_ad.get("delta_top10_vs_unexpanded_best_arm"),
        "pm50_pass_threshold_count": ac.get("pm50_pass_threshold_count"),
        "pm100_top10_expanded_span_overlap_count": pm100_ad.get("top10_span_overlap_count"),
        "pm100_top20_expanded_span_overlap_count": pm100_ad.get("top20_span_overlap_count"),
        "original_span_hit_lost_count": pm50_ad.get("original_span_hit_lost_count"),
    }
    ok = all(values[k] == v for k, v in EXPECTED_METRICS.items())
    ok = ok and pm20_ab.get("top10_expanded_span_overlap_count") == 15 and pm50_ab.get("top10_expanded_span_overlap_count") == 19 and pm100_ab.get("top10_expanded_span_overlap_count") == 21
    ok = ok and all(row.get("candidate_pool_changed_bool") is False and row.get("candidate_added_count") == 0 and row.get("candidate_removed_count") == 0 for row in (pm20_ab, pm50_ab, pm100_ab))
    record = {"anonymous_metric_consistency_id": "n10aemetric0000", "metric_bucket": "fixed_window_repair_aggregate_metrics_stable", **{k: int(v if isinstance(v, int) else -1) for k, v in values.items()}, "candidate_pool_changed_bool": False, "candidate_added_count": 0, "candidate_removed_count": 0, "metric_consistency_bool": ok}
    return [record], ok


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10aeclaim0000", "claim_boundary_bucket": "fixed_local_span_window_expansion_on_n1_proxy_surface_only", "n1_proxy_surface_only_bool": True, "n2_equivalent_validation_bool": False, "retrieval_claim_bool": False, "selector_reranker_claim_bool": False, "runtime_default_policy_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "claim_boundary_valid_bool": True}], True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10aeprivacy0000", "privacy_boundary_bucket": "public_replication_package_aggregates_only", "private_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_valid_bool": True}], True


def no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_execution_id": "n10aenoexec0000", "no_execution_boundary_bucket": "public_package_only_no_private_read_no_recompute", "private_read_count": 0, "recompute_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "new_arm_search_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_execution_complete_bool": True}], True


def n10af_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10af_handoff_id": "n10aehandoff0000", "n10af_handoff_bucket": "n10af_next_step_selection_stronger_validation_preflight_authorized" if complete else "n10af_not_authorized", "n10af_preflight_authorized_bool": complete, "preflight_only_bool": True, "private_read_authorized_bool": False, "runtime_default_promotion_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, chain_ok: bool, metrics_ok: bool, claims_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok, int(input_ok), 1), ("replication_chain_consistent", chain_ok, int(chain_ok), 1), ("metrics_stable", metrics_ok, int(metrics_ok), 1), ("claim_boundary", claims_ok, int(claims_ok), 1), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("no_execution", noexec_ok, int(noexec_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10af_preflight_authorized" if complete else "n10af_not_authorized", "next_allowed_phase": "BEA-v1-N10AF Next-Step Selection Stronger Validation Preflight" if complete else "none_until_replication_chain_consistent", "next_allowed_scope_bucket": "preflight_only_no_execution" if complete else "no_next_phase", "n10af_preflight_authorized": complete, "private_read_authorized": False, "runtime_or_default_promotion_authorized": False, "method_winner_claim_authorized": False, "method_winner_claimed": False, "downstream_value_claim_authorized": False, "downstream_value_claimed": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_materialization_authorized": False, "new_arm_search_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, chain_ok: bool, metrics_ok: bool, claims_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ae_required_inputs_unavailable"
    if not chain_ok or not metrics_ok:
        return "no_go_n10ae_chain_inconsistent"
    if not claims_ok or not privacy_ok or not noexec_ok:
        return "no_go_n10ae_privacy_or_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = input_artifact_records()
    chain_records, chain_ok = replication_chain_records(artifacts)
    metric_records, metrics_ok = metric_consistency_records(artifacts)
    claim_records, claims_ok = claim_boundary_records()
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, chain_ok, metrics_ok, claims_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_replication_package_only", "generated_by": "bea_v1_n10ae_fixed_span_window_repair_replication_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "replication_chain_records": chain_records, "metric_consistency_records": metric_records, "claim_boundary_records": claim_records, "privacy_boundary_records": privacy_records, "no_execution_records": noexec_records, "n10af_handoff_records": n10af_handoff_records(complete), "gate_records": gate_records(input_ok, chain_ok, metrics_ok, claims_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["gate_records"] = gate_records(input_ok, chain_ok, metrics_ok, claims_ok, privacy_ok, noexec_ok, scanner_ok)
    report["n10af_handoff_records"] = n10af_handoff_records(complete)
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
    chain_records, chain_ok = replication_chain_records(artifacts)
    metric_records, metrics_ok = metric_consistency_records(artifacts)
    claim_records, claims_ok = claim_boundary_records()
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_execution_records()
    metric = metric_records[0]
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10ae_required_inputs_unavailable", "no_go_n10ae_chain_inconsistent", "no_go_n10ae_privacy_or_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "gold_lines", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("public_inputs", input_ok and len(inputs) == 5),
        check("chain", chain_ok and chain_records[0]["n10ad_aggregate_match_bool"] is True and chain_records[0]["n10ab_code_call_count"] == 0),
        check("baseline_metrics", metric["baseline_top10_span_overlap_count"] == 9 and metric["baseline_top20_span_overlap_count"] == 10),
        check("variant_metrics", metric["pm20_top10_expanded_span_overlap_count"] == 15 and metric["pm50_top10_expanded_span_overlap_count"] == 19 and metric["pm100_top20_expanded_span_overlap_count"] == 25),
        check("threshold_metrics", metrics_ok and metric["pm50_delta_top10_vs_unexpanded_best_arm"] == 10 and metric["pm50_pass_threshold_count"] == 11 and metric["original_span_hit_lost_count"] == 0),
        check("candidate_pool", metric["candidate_pool_changed_bool"] is False and metric["candidate_added_count"] == 0 and metric["candidate_removed_count"] == 0),
        check("claim_boundary", claims_ok and claim_records[0]["runtime_default_policy_bool"] is False and claim_records[0]["method_winner_claim_bool"] is False),
        check("privacy", privacy_ok and privacy_records[0]["private_read_count"] == 0 and privacy_records[0]["gold_line_public_bool"] is False),
        check("no_execution", noexec_ok and all(v == 0 for k, v in noexec_records[0].items() if k.endswith("_count"))),
        check("handoff", n10af_handoff_records(True)[0]["n10af_preflight_authorized_bool"] is True and stop_go_records(True)[0]["private_read_authorized"] is False),
        check("status_expected", status_for(True, True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AE fixed span-window repair replication package")
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
    metric = report["metric_consistency_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, pm50_top10={metric['pm50_top10_expanded_span_overlap_count']})")


if __name__ == "__main__":
    main()
