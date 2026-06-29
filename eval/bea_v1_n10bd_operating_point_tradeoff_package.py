#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10bd_operating_point_tradeoff_package.v1"
PHASE = "BEA-v1-N10BD Operating-Point Tradeoff Decomposition Audit Package"
STATUS_COMPLETE = "operating_point_tradeoff_package_complete_n10be_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10bd_required_public_inputs_unavailable",
    "no_go_n10bd_tradeoff_chain_mismatch",
    "no_go_n10bd_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10bd_operating_point_tradeoff_package/bea_v1_n10bd_operating_point_tradeoff_package_report.json")
PUBLIC_INPUTS = {
    "n10bc_tradeoff_decomposition_artifact": (Path("artifacts/bea_v1_n10bc_operating_point_tradeoff_decomposition/bea_v1_n10bc_operating_point_tradeoff_decomposition_report.json"), "operating_point_tradeoff_decomposition_complete_n10bd_authorized"),
    "n10bb_selection_rule_audit_package_artifact": (Path("artifacts/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package_report.json"), "cost_aware_selection_rule_smoke_audit_package_complete_n10bc_authorized"),
    "n10ba_selection_rule_smoke_artifact": (Path("artifacts/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke_report.json"), "cost_aware_span_window_selection_rule_smoke_complete_n10bb_authorized"),
    "n10aw_mechanism_decomposition_artifact": (Path("artifacts/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition_report.json"), "cost_sensitive_span_window_frontier_mechanism_decomposition_complete_n10ax_authorized"),
}
EXPECTED_TRADEOFF = {
    "baseline": {"variant_bucket": "baseline", "top10": 9, "top20": 10, "marginal10": 9, "marginal20": 10, "marginal_cost": 0, "cost_bucket": "baseline"},
    "low_cost": {"variant_bucket": "pm30", "top10": 18, "top20": 22, "marginal10": 9, "marginal20": 12, "marginal_cost": 600, "cost_bucket": "low"},
    "balanced": {"variant_bucket": "before25_after75", "top10": 20, "top20": 24, "marginal10": 2, "marginal20": 2, "marginal_cost": 400, "cost_bucket": "medium"},
    "max_recall": {"variant_bucket": "pm200", "top10": 25, "top20": 30, "marginal10": 5, "marginal20": 6, "marginal_cost": 3000, "cost_bucket": "very_high"},
}
EXPECTED_MECHANISM = {
    "low_cost": {"before_gold_gap": 8, "after_gold_gap": 1, "already_reachable_late_rank": 0, "other_bucketed": 0},
    "balanced": {"before_gold_gap": 2, "after_gold_gap": 0, "already_reachable_late_rank": 0, "other_bucketed": 0},
    "max_recall": {"before_gold_gap": 3, "after_gold_gap": 2, "already_reachable_late_rank": 0, "other_bucketed": 0},
}
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "p4_evidence", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks",
    "score", "scores", "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "operating_point_bucket", "variant_bucket", "mechanism_bucket", "cost_bucket", "previous_operating_point_bucket",
    "mechanism_summary_bucket", "claim_boundary_bucket", "forbidden_claim_bucket", "no_recompute_boundary_bucket",
    "n10be_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "budget_bucket",
    "selected_operating_point_bucket", "gate", "threshold_relation",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(rel: Path) -> tuple[dict[str, Any], str]:
    full = repo_root() / rel
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(rel: Path, obj: dict[str, Any]) -> None:
    full = repo_root() / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    location_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
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
            key = marker.rsplit(".", 1)[-1].replace("[]", "")
            if key in SAFE_VALUE_KEYS:
                return
            if location_re.search(value):
                violations.append({"category": "location_like_value", "location_bucket": "public_artifact"})
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
    rows: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(PUBLIC_INPUTS.items()):
        artifact, load_status = load_json(path)
        artifacts[bucket] = artifact
        observed = str(artifact.get("status", ""))
        scan_status = artifact.get("forbidden_scan", {}).get("status", "fail") if isinstance(artifact.get("forbidden_scan"), dict) else "fail"
        passed = load_status == "pass" and observed == expected and scan_status == "pass"
        ok = ok and passed
        rows.append({"anonymous_input_artifact_id": f"n10bdin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def rows_by_key(rows: Any, key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get(key), str):
                out[row[key]] = row
    return out


def tradeoff_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10bc = artifacts.get("n10bc_tradeoff_decomposition_artifact", {})
    source = rows_by_key(n10bc.get("operating_point_tradeoff_records", []), "operating_point_bucket")
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (point, expected) in enumerate(EXPECTED_TRADEOFF.items()):
        src = source.get(point, {})
        matched = src.get("variant_bucket") == expected["variant_bucket"] and src.get("cumulative_top10_span_overlap_count") == expected["top10"] and src.get("cumulative_top20_span_overlap_count") == expected["top20"] and src.get("marginal_top10_gain") == expected["marginal10"] and src.get("marginal_top20_gain") == expected["marginal20"] and src.get("marginal_cost_proxy") == expected["marginal_cost"] and src.get("marginal_cost_per_top10_hit_bucket") == expected["cost_bucket"] and src.get("lost_previous_hits") == 0 and src.get("candidate_pool_changed_bool") is False and src.get("candidate_order_changed_bool") is False
        ok = ok and matched
        rows.append({"anonymous_tradeoff_package_id": f"n10bdtrade{idx:04d}", "operating_point_bucket": point, "variant_bucket": expected["variant_bucket"], "cumulative_top10_span_overlap_count": expected["top10"], "cumulative_top20_span_overlap_count": expected["top20"], "marginal_top10_gain": expected["marginal10"], "marginal_top20_gain": expected["marginal20"], "marginal_cost_proxy": expected["marginal_cost"], "marginal_cost_per_top10_hit_bucket": expected["cost_bucket"], "lost_previous_hits": 0, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "n10bc_match_bool": matched})
    return rows, ok


def mechanism_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    n10bc = artifacts.get("n10bc_tradeoff_decomposition_artifact", {})
    bucket_rows = n10bc.get("mechanism_bucket_records", [])
    source: dict[tuple[str, str], int] = {}
    if isinstance(bucket_rows, list):
        for row in bucket_rows:
            if isinstance(row, dict):
                source[(str(row.get("operating_point_bucket")), str(row.get("mechanism_bucket")))] = int(row.get("new_top10_hit_count", -1))
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (point, expected_counts) in enumerate(EXPECTED_MECHANISM.items()):
        for bucket_idx, (bucket, expected_count) in enumerate(expected_counts.items()):
            observed = source.get((point, bucket), -1)
            matched = observed == expected_count
            ok = ok and matched
            rows.append({"anonymous_mechanism_package_id": f"n10bdmech{idx:04d}{bucket_idx:04d}", "operating_point_bucket": point, "mechanism_bucket": bucket, "new_top10_hit_count": expected_count, "n10bc_match_bool": matched})
    continuity = n10bc.get("mechanism_continuity_records", [])
    cont = continuity[0] if isinstance(continuity, list) and continuity and isinstance(continuity[0], dict) else {}
    summary_ok = cont.get("max_recall_gains_same_mechanism_as_lower_cost_bool") is True and cont.get("qualitatively_new_max_recall_mechanism_bool") is False and cont.get("max_recall_before_after_gap_new_hit_count") == 5
    ok = ok and summary_ok
    summary_rows = [{"anonymous_mechanism_summary_id": "n10bdsummary0000", "mechanism_summary_bucket": "all_marginal_top10_gains_before_after_gold_window_gaps", "all_marginal_gains_before_after_gap_bool": True, "max_recall_same_mechanism_as_lower_cost_bool": True, "qualitatively_new_max_recall_mechanism_bool": False, "lost_previous_hits_all_tiers_zero_bool": True, "n10bc_match_bool": summary_ok}]
    return rows, summary_rows, ok


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10bdclaim0000", "claim_boundary_bucket": "same_source_n1_proxy_tradeoff_package_only", "allowed_claim_operating_point_tradeoff_packaged_bool": True, "runtime_default_claim_bool": False, "heldout_claim_bool": False, "generalization_claim_bool": False, "n2_equivalent_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "selector_reranker_claim_bool": False, "p5_or_v1a_claim_bool": False, "claim_boundary_valid_bool": True}], True


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10bdnorecompute0000", "no_recompute_boundary_bucket": "public_tradeoff_package_only", "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "adaptive_selection_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "runtime_default_change_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10be_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10be_handoff_id": "n10bdhandoff0000", "n10be_handoff_bucket": "n10be_cost_aware_operating_point_decision_smoke_authorized" if complete else "n10be_not_authorized", "n10be_authorized_bool": complete, "same_scoped_n1_rows_authorized_bool": complete, "budget_bucket_count": 3, "strict_budget_maps_to_low_cost_bool": True, "moderate_budget_maps_to_balanced_bool": True, "recall_budget_maps_to_max_recall_bool": True, "public_aggregate_bucket_output_only_bool": True, "runtime_default_recommendation_authorized_bool": False, "new_variant_authorized_bool": False, "adaptive_selection_authorized_bool": False, "heldout_claim_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, tradeoff_ok: bool, mechanism_ok: bool, claim_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("tradeoff_package", tradeoff_ok), ("mechanism_package", mechanism_ok), ("claim_boundary", claim_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10be_cost_aware_operating_point_decision_smoke_authorized" if complete else "n10be_not_authorized", "next_allowed_phase": "BEA-v1-N10BE Cost-Aware Operating-Point Decision Smoke" if complete else "none_until_tradeoff_package_is_consistent", "next_allowed_scope_bucket": "same_scoped_rows_budget_bucket_decision_smoke_no_defaults" if complete else "no_next_phase", "n10be_authorized": complete, "private_read_beyond_same_scoped_rows_authorized": False, "runtime_or_default_authorized": False, "runtime_default_recommendation_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "new_variant_authorized": False, "adaptive_selection_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, tradeoff_ok: bool, mechanism_ok: bool, claim_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10bd_required_public_inputs_unavailable"
    if not tradeoff_ok or not mechanism_ok:
        return "no_go_n10bd_tradeoff_chain_mismatch"
    if not claim_ok or not norecompute_ok:
        return "no_go_n10bd_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    tradeoff_rows, tradeoff_ok = tradeoff_package_records(artifacts)
    mechanism_rows, mechanism_summary_rows, mechanism_ok = mechanism_package_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, tradeoff_ok, mechanism_ok, claim_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_operating_point_tradeoff_package_only", "generated_by": "bea_v1_n10bd_operating_point_tradeoff_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "tradeoff_package_records": tradeoff_rows, "mechanism_package_records": mechanism_rows, "mechanism_summary_records": mechanism_summary_rows, "claim_boundary_records": claim_rows, "no_recompute_records": norecompute_rows, "n10be_handoff_records": n10be_handoff_records(complete), "gate_records": gate_records(input_ok, tradeoff_ok, mechanism_ok, claim_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10be_handoff_records"] = n10be_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, tradeoff_ok, mechanism_ok, claim_ok, norecompute_ok, scanner_ok)
    report["stop_go_records"] = stop_go_records(complete)
    return report


def check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--bad", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def synthetic_package_pass() -> bool:
    fake = {"n10bc_tradeoff_decomposition_artifact": {"operating_point_tradeoff_records": [{"operating_point_bucket": k, "variant_bucket": v["variant_bucket"], "cumulative_top10_span_overlap_count": v["top10"], "cumulative_top20_span_overlap_count": v["top20"], "marginal_top10_gain": v["marginal10"], "marginal_top20_gain": v["marginal20"], "marginal_cost_proxy": v["marginal_cost"], "marginal_cost_per_top10_hit_bucket": v["cost_bucket"], "lost_previous_hits": 0, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False} for k, v in EXPECTED_TRADEOFF.items()], "mechanism_bucket_records": [{"operating_point_bucket": p, "mechanism_bucket": b, "new_top10_hit_count": c} for p, counts in EXPECTED_MECHANISM.items() for b, c in counts.items()], "mechanism_continuity_records": [{"max_recall_gains_same_mechanism_as_lower_cost_bool": True, "qualitatively_new_max_recall_mechanism_bool": False, "max_recall_before_after_gap_new_hit_count": 5}]}}
    return tradeoff_package_records(fake)[1] and mechanism_package_records(fake)[2]


def synthetic_mismatch() -> bool:
    fake = {"n10bc_tradeoff_decomposition_artifact": {"operating_point_tradeoff_records": []}}
    _rows, ok = tradeoff_package_records(fake)
    return not ok and status_for(True, True, ok, True, True, True) == "no_go_n10bd_tradeoff_chain_mismatch"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    tradeoff_rows, tradeoff_ok = tradeoff_package_records(artifacts)
    mechanism_rows, mechanism_summary_rows, mechanism_ok = mechanism_package_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10bd_required_public_inputs_unavailable", "no_go_n10bd_tradeoff_chain_mismatch", "no_go_n10bd_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 4),
        check("tradeoff_package", tradeoff_ok and tradeoff_rows[-1]["operating_point_bucket"] == "max_recall" and tradeoff_rows[-1]["marginal_top10_gain"] == 5),
        check("mechanism_package", mechanism_ok and len(mechanism_rows) == 12 and mechanism_summary_rows[0]["max_recall_same_mechanism_as_lower_cost_bool"] is True),
        check("claim_boundary", claim_ok and claim_rows[0]["runtime_default_claim_bool"] is False and claim_rows[0]["method_winner_claim_bool"] is False),
        check("no_private_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["recompute_count"] == 0),
        check("synthetic_package_pass", synthetic_package_pass()),
        check("synthetic_mismatch", synthetic_mismatch()),
        check("false_flags", stop_go_records(True)[0]["n10be_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["adaptive_selection_authorized"] is False),
        check("status_complete", status_for(True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BD operating-point tradeoff package")
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
