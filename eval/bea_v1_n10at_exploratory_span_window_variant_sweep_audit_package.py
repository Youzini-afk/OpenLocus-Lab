#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package.v1"
PHASE = "BEA-v1-N10AT Exploratory Span-Window Variant Sweep Audit Package"
STATUS_COMPLETE = "exploratory_span_window_variant_sweep_audit_package_complete_n10au_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10at_required_public_inputs_unavailable",
    "no_go_n10at_n10as_result_invalid",
    "no_go_n10at_frontier_tier_mismatch",
    "no_go_n10at_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
N10AS_STATUS = "exploratory_span_window_variant_sweep_complete_n10at_authorized"
DEFAULT_OUT = Path("artifacts/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package_report.json")
N10AS_REPORT = Path("artifacts/bea_v1_n10as_exploratory_span_window_variant_sweep/bea_v1_n10as_exploratory_span_window_variant_sweep_report.json")
EXPECTED_TIERS: dict[str, dict[str, Any]] = {
    "pm30": {"tier_bucket": "low_cost_frontier_point", "top10_span_overlap_count": 18, "top20_span_overlap_count": 22, "top10_cost_proxy_value": 600, "top10_cost_proxy_bucket": "low", "pareto_frontier_bool": True},
    "before25_after75": {"tier_bucket": "balanced_frontier_point", "top10_span_overlap_count": 20, "top20_span_overlap_count": 24, "top10_cost_proxy_value": 1000, "top10_cost_proxy_bucket": "medium", "pareto_frontier_bool": True},
    "pm75": {"tier_bucket": "balanced_frontier_point", "top10_span_overlap_count": 21, "top20_span_overlap_count": 25, "top10_cost_proxy_value": 1500, "top10_cost_proxy_bucket": "medium", "pareto_frontier_bool": True},
    "pm200": {"tier_bucket": "max_recall_frontier_point", "top10_span_overlap_count": 25, "top20_span_overlap_count": 30, "top10_cost_proxy_value": 4000, "top10_cost_proxy_bucket": "very_high", "pareto_frontier_bool": True},
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
    "variant_bucket", "tier_bucket", "top10_cost_proxy_bucket", "variant_family_bucket", "claim_boundary_bucket",
    "no_recompute_boundary_bucket", "n10au_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
    "gate", "threshold_relation", "audit_status_bucket",
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
        data = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (data, "pass") if isinstance(data, dict) else ({}, "parse_failed")


def write_json(rel: Path, data: dict[str, Any]) -> None:
    full = repo_root() / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    location_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    digest_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)
    span_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)
    def walk(value: Any, marker: str = "$.") -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                key_s = str(key)
                if key_s in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, marker + key_s + ".")
        elif isinstance(value, list):
            for inner in value:
                walk(inner, marker + "[]")
        elif isinstance(value, str):
            key = marker.rstrip(".").rsplit(".", 1)[-1].replace("[]", "")
            if key in SAFE_VALUE_KEYS:
                return
            if location_re.search(value):
                violations.append({"category": "location_like_value", "location_bucket": "public_artifact"})
            if digest_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})
            if span_re.search(value):
                violations.append({"category": "span_like_value", "location_bucket": "public_artifact"})
    walk(obj)
    return violations


def scan_summary(obj: Any) -> dict[str, Any]:
    violations = scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": key, "count": count} for key, count in sorted(counts.items())]}


def input_artifact_records(n10as: dict[str, Any], load_status: str) -> tuple[list[dict[str, Any]], bool]:
    observed = str(n10as.get("status", ""))
    forbidden = n10as.get("forbidden_scan", {}).get("status", "fail") if isinstance(n10as.get("forbidden_scan"), dict) else "fail"
    ok = load_status == "pass" and observed == N10AS_STATUS and forbidden == "pass"
    return [{"anonymous_input_artifact_id": "n10atin0000", "input_artifact_bucket": "n10as_exploratory_variant_sweep_artifact", "load_status": load_status, "observed_status": observed, "expected_status": N10AS_STATUS, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": ok}], ok


def results_by_variant(n10as: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = n10as.get("variant_result_records", [])
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("variant_bucket"), str):
            result[str(row["variant_bucket"])] = row
    return result


def frontier_tier_audit_records(n10as: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    by_variant = results_by_variant(n10as)
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (variant, expected) in enumerate(EXPECTED_TIERS.items()):
        observed = by_variant.get(variant, {})
        matched = bool(observed) and all(observed.get(key) == value for key, value in expected.items() if key != "tier_bucket")
        ok = ok and matched
        rows.append({
            "anonymous_frontier_tier_audit_id": f"n10attier{idx:04d}",
            "variant_bucket": variant,
            "tier_bucket": expected["tier_bucket"],
            "top10_span_overlap_count": observed.get("top10_span_overlap_count", -1),
            "top20_span_overlap_count": observed.get("top20_span_overlap_count", -1),
            "top10_cost_proxy_value": observed.get("top10_cost_proxy_value", -1),
            "top10_cost_proxy_bucket": observed.get("top10_cost_proxy_bucket", "missing"),
            "pareto_frontier_bool": bool(observed.get("pareto_frontier_bool", False)),
            "audit_matched_bool": matched,
        })
    return rows, ok


def n10as_boundary_ok(n10as: dict[str, Any]) -> bool:
    stop = n10as.get("stop_go_records", [])
    rec = n10as.get("exploratory_recommendation_records", [])
    noexec = n10as.get("no_forbidden_execution_records", [])
    if not (isinstance(stop, list) and stop and isinstance(stop[0], dict)):
        return False
    if not (isinstance(rec, list) and rec and isinstance(rec[0], dict)):
        return False
    if not (isinstance(noexec, list) and noexec and isinstance(noexec[0], dict)):
        return False
    return (
        stop[0].get("n10at_authorized") is True
        and stop[0].get("private_read_authorized") is False
        and stop[0].get("extra_sweep_authorized") is False
        and stop[0].get("heldout_validation_claim_authorized") is False
        and stop[0].get("runtime_or_default_authorized") is False
        and rec[0].get("recommended_variant_bucket") == "pm200"
        and rec[0].get("recommended_top10_span_overlap_count") == 25
        and rec[0].get("recommended_top20_span_overlap_count") == 30
        and rec[0].get("heldout_claim_bool") is False
        and rec[0].get("runtime_default_claim_bool") is False
        and rec[0].get("method_winner_claim_bool") is False
        and noexec[0].get("per_record_adaptive_window_count") == 0
        and noexec[0].get("gold_used_for_variant_selection_count") == 0
        and noexec[0].get("candidate_pool_changed_count") == 0
        and noexec[0].get("candidate_order_changed_count") == 0
    )


def claim_boundary_records(n10as: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    ok = n10as_boundary_ok(n10as)
    return [{"anonymous_claim_boundary_id": "n10atclaim0000", "claim_boundary_bucket": "same_source_exploratory_n1_span_surface_proxy_only", "n1_span_surface_proxy_only_bool": True, "same_source_only_bool": True, "heldout_claim_bool": False, "n2_equivalent_claim_bool": False, "runtime_default_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "generalization_claim_bool": False, "selector_reranker_claim_bool": False, "retrieval_or_rerun_claim_bool": False, "claim_boundary_valid_bool": ok}], ok


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10atnorecompute0000", "no_recompute_boundary_bucket": "public_audit_package_only", "private_read_count": 0, "variant_recompute_count": 0, "extra_sweep_count": 0, "new_variant_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "adaptive_tuning_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_promotion_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10au_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10au_handoff_id": "n10athandoff0000", "n10au_handoff_bucket": "n10au_independent_recompute_authorized" if complete else "n10au_not_authorized", "n10au_independent_recompute_authorized_bool": complete, "n10au_same_scoped_private_rows_authorized_bool": complete, "private_read_in_n10at_bool": False, "extra_sweep_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_validation_claim_authorized_bool": False}]


def gate_records(input_ok: bool, frontier_ok: bool, claim_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("n10as_public_artifact_loaded", input_ok), ("frontier_tiers_match", frontier_ok), ("claim_boundary_valid", claim_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": int(passed), "threshold_value": 1} for name, passed in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10au_independent_recompute_authorized" if complete else "n10au_not_authorized", "next_allowed_phase": "BEA-v1-N10AU Independent Recompute Exploratory Span-Window Variant Sweep" if complete else "none_until_valid_n10as_public_sweep_artifact_exists", "next_allowed_scope_bucket": "same_scoped_private_rows_full_15_variant_independent_recompute" if complete else "no_next_phase", "n10au_authorized": complete, "private_read_authorized_for_n10au_only": complete, "private_read_in_n10at_authorized": False, "extra_sweep_authorized": False, "new_variant_authorized": False, "heldout_validation_claim_authorized": False, "runtime_or_default_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "adaptive_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, frontier_ok: bool, claim_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10at_required_public_inputs_unavailable"
    if not frontier_ok:
        return "no_go_n10at_frontier_tier_mismatch"
    if not claim_ok or not norecompute_ok:
        return "no_go_n10at_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    n10as, load_status = load_json(N10AS_REPORT)
    input_rows, input_ok = input_artifact_records(n10as, load_status)
    tier_rows, frontier_ok = frontier_tier_audit_records(n10as)
    claim_rows, claim_ok = claim_boundary_records(n10as)
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(item["passed"] for item in checks)
    status = status_for(self_ok, input_ok, frontier_ok, claim_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "phase": PHASE,
        "claim_level": "public_audit_package_same_source_exploratory_only",
        "generated_by": "bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package",
        "generated_at": now(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_rows,
        "frontier_tier_audit_records": tier_rows,
        "claim_boundary_records": claim_rows,
        "no_recompute_records": norecompute_rows,
        "n10au_handoff_records": n10au_handoff_records(complete),
        "gate_records": gate_records(input_ok, frontier_ok, claim_ok, norecompute_ok, True),
        "stop_go_records": stop_go_records(complete),
        "forbidden_scan": {},
        "method_winner_claimed": False,
        "downstream_value_claimed": False,
    }
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10au_handoff_records"] = n10au_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, frontier_ok, claim_ok, norecompute_ok, scanner_ok)
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


def synthetic_frontier_ok() -> bool:
    fake = {"variant_result_records": [{"variant_bucket": k, **{kk: vv for kk, vv in v.items() if kk != "tier_bucket"}} for k, v in EXPECTED_TIERS.items()]}
    _, ok = frontier_tier_audit_records(fake)
    return ok


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    n10as, load_status = load_json(N10AS_REPORT)
    input_rows, input_ok = input_artifact_records(n10as, load_status)
    tier_rows, frontier_ok = frontier_tier_audit_records(n10as)
    claim_rows, claim_ok = claim_boundary_records(n10as)
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10at_required_public_inputs_unavailable", "no_go_n10at_n10as_result_invalid", "no_go_n10at_frontier_tier_mismatch", "no_go_n10at_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({key: "x"})["status"] == "fail" for key in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("input_artifact", input_ok and len(input_rows) == 1),
        check("synthetic_frontier", synthetic_frontier_ok()),
        check("frontier_tiers", frontier_ok and len(tier_rows) == 4 and tier_rows[-1]["variant_bucket"] == "pm200" and tier_rows[-1]["top10_span_overlap_count"] == 25),
        check("claim_boundary", claim_ok and claim_rows[0]["heldout_claim_bool"] is False and claim_rows[0]["runtime_default_claim_bool"] is False),
        check("no_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["variant_recompute_count"] == 0),
        check("stop_go", stop_go_records(True)[0]["n10au_authorized"] is True and stop_go_records(True)[0]["extra_sweep_authorized"] is False),
        check("status_complete", status_for(True, True, True, True, True) == STATUS_COMPLETE),
        check("status_no_input", status_for(True, False, True, True, True) == "no_go_n10at_required_public_inputs_unavailable"),
        check("status_frontier", status_for(True, True, False, True, True) == "no_go_n10at_frontier_tier_mismatch"),
    ]
    return checks, all(item["passed"] for item in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AT exploratory span-window sweep audit package")
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
