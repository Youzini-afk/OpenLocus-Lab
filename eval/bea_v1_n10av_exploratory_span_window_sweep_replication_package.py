#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10av_exploratory_span_window_sweep_replication_package.v1"
PHASE = "BEA-v1-N10AV Exploratory Span-Window Variant Sweep Replication Package"
STATUS_COMPLETE = "exploratory_span_window_sweep_replication_package_complete_n10aw_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10av_required_public_inputs_unavailable",
    "no_go_n10av_replication_chain_mismatch",
    "no_go_n10av_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10av_exploratory_span_window_sweep_replication_package/bea_v1_n10av_exploratory_span_window_sweep_replication_package_report.json")
PUBLIC_INPUTS = {
    "n10as_exploratory_sweep_artifact": (Path("artifacts/bea_v1_n10as_exploratory_span_window_variant_sweep/bea_v1_n10as_exploratory_span_window_variant_sweep_report.json"), "exploratory_span_window_variant_sweep_complete_n10at_authorized"),
    "n10at_audit_package_artifact": (Path("artifacts/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package_report.json"), "exploratory_span_window_variant_sweep_audit_package_complete_n10au_authorized"),
    "n10au_independent_recompute_artifact": (Path("artifacts/bea_v1_n10au_independent_recompute_span_window_variant_sweep/bea_v1_n10au_independent_recompute_span_window_variant_sweep_report.json"), "independent_recompute_span_window_variant_sweep_pass_n10av_authorized"),
}
FRONTIER = {
    "pm30": {"tier_bucket": "low_cost_frontier_point", "top10_span_overlap_count": 18, "top20_span_overlap_count": 22, "top10_cost_proxy_value": 600, "top10_cost_proxy_bucket": "low"},
    "before25_after75": {"tier_bucket": "balanced_frontier_point", "top10_span_overlap_count": 20, "top20_span_overlap_count": 24, "top10_cost_proxy_value": 1000, "top10_cost_proxy_bucket": "medium"},
    "pm75": {"tier_bucket": "balanced_frontier_point", "top10_span_overlap_count": 21, "top20_span_overlap_count": 25, "top10_cost_proxy_value": 1500, "top10_cost_proxy_bucket": "medium"},
    "pm200": {"tier_bucket": "max_recall_frontier_point", "top10_span_overlap_count": 25, "top20_span_overlap_count": 30, "top10_cost_proxy_value": 4000, "top10_cost_proxy_bucket": "very_high"},
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
    "replication_chain_bucket", "variant_bucket", "tier_bucket", "top10_cost_proxy_bucket", "match_status_bucket",
    "claim_boundary_bucket", "no_recompute_boundary_bucket", "next_option_bucket", "n10aw_handoff_bucket",
    "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
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
        rows.append({"anonymous_input_artifact_id": f"n10avin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def records_by_variant(artifact: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = artifact.get(key, [])
    out: dict[str, dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("variant_bucket"), str):
                out[row["variant_bucket"]] = row
    return out


def replication_chain_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10as = artifacts.get("n10as_exploratory_sweep_artifact", {})
    n10at = artifacts.get("n10at_audit_package_artifact", {})
    n10au = artifacts.get("n10au_independent_recompute_artifact", {})
    n10as_complete = n10as.get("status") == PUBLIC_INPUTS["n10as_exploratory_sweep_artifact"][1]
    n10at_complete = n10at.get("status") == PUBLIC_INPUTS["n10at_audit_package_artifact"][1]
    n10au_complete = n10au.get("status") == PUBLIC_INPUTS["n10au_independent_recompute_artifact"][1]
    aggregate_matches = n10au.get("aggregate_match_records", [])
    all_aggregate_match = isinstance(aggregate_matches, list) and len(aggregate_matches) == 15 and all(isinstance(r, dict) and r.get("aggregate_match_bool") is True for r in aggregate_matches)
    ok = n10as_complete and n10at_complete and n10au_complete and all_aggregate_match
    return [{"anonymous_replication_chain_id": "n10avchain0000", "replication_chain_bucket": "n10as_to_n10at_to_n10au", "n10as_sweep_complete_bool": n10as_complete, "n10at_public_audit_complete_bool": n10at_complete, "n10au_independent_recompute_complete_bool": n10au_complete, "n10au_all_15_aggregate_match_bool": all_aggregate_match, "replication_chain_complete_bool": ok}], ok


def frontier_summary_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10as = records_by_variant(artifacts.get("n10as_exploratory_sweep_artifact", {}), "variant_result_records")
    n10au = records_by_variant(artifacts.get("n10au_independent_recompute_artifact", {}), "recomputed_variant_result_records")
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (variant, expected) in enumerate(FRONTIER.items()):
        as_row = n10as.get(variant, {})
        au_row = n10au.get(variant, {})
        matched = bool(as_row) and bool(au_row) and all(as_row.get(k) == expected[k] and au_row.get(k) == expected[k] for k in ("top10_span_overlap_count", "top20_span_overlap_count", "top10_cost_proxy_value", "top10_cost_proxy_bucket")) and as_row.get("pareto_frontier_bool") is True and au_row.get("pareto_frontier_bool") is True
        ok = ok and matched
        rows.append({"anonymous_frontier_summary_id": f"n10avfront{idx:04d}", "variant_bucket": variant, "tier_bucket": expected["tier_bucket"], "top10_span_overlap_count": expected["top10_span_overlap_count"], "top20_span_overlap_count": expected["top20_span_overlap_count"], "top10_cost_proxy_value": expected["top10_cost_proxy_value"], "top10_cost_proxy_bucket": expected["top10_cost_proxy_bucket"], "n10as_n10au_metric_match_bool": matched, "same_source_exploratory_only_bool": True})
    return rows, ok


def independent_recompute_match_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10au = artifacts.get("n10au_independent_recompute_artifact", {})
    aggregate = n10au.get("aggregate_match_records", [])
    frontier = n10au.get("frontier_match_records", [])
    impl = n10au.get("independent_implementation_records", [])
    all_aggregate = isinstance(aggregate, list) and len(aggregate) == 15 and all(isinstance(r, dict) and r.get("aggregate_match_bool") is True for r in aggregate)
    all_frontier = isinstance(frontier, list) and len(frontier) == 4 and all(isinstance(r, dict) and r.get("frontier_match_bool") is True for r in frontier)
    independent = isinstance(impl, list) and bool(impl) and isinstance(impl[0], dict) and impl[0].get("n10as_evaluator_imported_bool") is False and impl[0].get("n10as_evaluator_called_bool") is False
    ok = all_aggregate and all_frontier and independent
    return [{"anonymous_independent_recompute_match_id": "n10avmatch0000", "match_status_bucket": "match" if ok else "mismatch", "all_15_variant_aggregate_match_bool": all_aggregate, "frontier_tier_match_bool": all_frontier, "n10as_evaluator_imported_bool": False if independent else True, "n10as_evaluator_called_bool": False if independent else True, "independent_recompute_match_bool": ok}], ok


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10avclaim0000", "claim_boundary_bucket": "same_source_exploratory_n1_proxy_replication_package_only", "allowed_claim_same_source_exploratory_frontier_replicated_bool": True, "n1_span_surface_proxy_only_bool": True, "heldout_claim_bool": False, "generalization_claim_bool": False, "n2_equivalent_claim_bool": False, "runtime_default_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "retrieval_or_rerun_claim_bool": False, "selector_reranker_claim_bool": False, "p5_or_v1a_claim_bool": False, "claim_boundary_valid_bool": True}], True


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10avnorecompute0000", "no_recompute_boundary_bucket": "public_replication_package_only", "private_read_count": 0, "variant_recompute_count": 0, "new_sweep_count": 0, "new_variant_count": 0, "adaptive_tuning_count": 0, "runtime_default_promotion_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_recompute_boundary_valid_bool": True}], True


def next_research_options_records() -> list[dict[str, Any]]:
    specs = [
        ("cost_sensitive_window_mechanism_decomposition", "public_or_scoped_preflight_required", False),
        ("default_off_adapter_variant_over_selected_frontier_points", "explicit_scope_required", False),
        ("broader_replay_or_heldout_validation", "requires_new_source_authorization_or_data", False),
    ]
    return [{"anonymous_next_research_option_id": f"n10avopt{idx:04d}", "next_option_bucket": name, "option_condition_bucket": condition, "authorized_for_immediate_execution_bool": immediate} for idx, (name, condition, immediate) in enumerate(specs)]


def gate_records(input_ok: bool, chain_ok: bool, frontier_ok: bool, match_ok: bool, claim_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("replication_chain_complete", chain_ok), ("frontier_summary_match", frontier_ok), ("independent_recompute_match", match_ok), ("claim_boundary", claim_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10aw_followup_selection_audit_authorized" if complete else "n10aw_not_authorized", "next_allowed_phase": "BEA-v1-N10AW Exploratory Span-Window Follow-Up Selection Audit" if complete else "none_until_public_replication_chain_is_consistent", "next_allowed_scope_bucket": "mechanism_or_cost_focused_followup_selection_audit_only" if complete else "no_next_phase", "n10aw_authorized": complete, "private_read_authorized": False, "variant_recompute_authorized": False, "new_sweep_authorized": False, "new_variant_authorized": False, "adaptive_tuning_authorized": False, "heldout_validation_authorized": False, "runtime_or_default_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, chain_ok: bool, frontier_ok: bool, match_ok: bool, claim_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10av_required_public_inputs_unavailable"
    if not chain_ok or not frontier_ok or not match_ok:
        return "no_go_n10av_replication_chain_mismatch"
    if not claim_ok or not norecompute_ok:
        return "no_go_n10av_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    chain_rows, chain_ok = replication_chain_records(artifacts)
    frontier_rows, frontier_ok = frontier_summary_records(artifacts)
    match_rows, match_ok = independent_recompute_match_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, chain_ok, frontier_ok, match_ok, claim_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_replication_package_same_source_exploratory_only", "generated_by": "bea_v1_n10av_exploratory_span_window_sweep_replication_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "replication_chain_records": chain_rows, "frontier_summary_records": frontier_rows, "independent_recompute_match_records": match_rows, "claim_boundary_records": claim_rows, "no_recompute_records": norecompute_rows, "next_research_options_records": next_research_options_records(), "gate_records": gate_records(input_ok, chain_ok, frontier_ok, match_ok, claim_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["gate_records"] = gate_records(input_ok, chain_ok, frontier_ok, match_ok, claim_ok, norecompute_ok, scanner_ok)
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


def synthetic_package_ok() -> bool:
    artifacts = {
        "n10as_exploratory_sweep_artifact": {"variant_result_records": [{"variant_bucket": k, "pareto_frontier_bool": True, **v} for k, v in FRONTIER.items()]},
        "n10au_independent_recompute_artifact": {"recomputed_variant_result_records": [{"variant_bucket": k, "pareto_frontier_bool": True, **v} for k, v in FRONTIER.items()], "aggregate_match_records": [{"aggregate_match_bool": True} for _ in range(15)], "frontier_match_records": [{"frontier_match_bool": True} for _ in range(4)], "independent_implementation_records": [{"n10as_evaluator_imported_bool": False, "n10as_evaluator_called_bool": False}]},
        "n10at_audit_package_artifact": {},
    }
    _, frontier_ok = frontier_summary_records(artifacts)
    _, match_ok = independent_recompute_match_records(artifacts)
    return frontier_ok and match_ok


def synthetic_mismatch_ok() -> bool:
    artifacts = {"n10as_exploratory_sweep_artifact": {"variant_result_records": []}, "n10au_independent_recompute_artifact": {"recomputed_variant_result_records": []}}
    _, frontier_ok = frontier_summary_records(artifacts)
    return not frontier_ok and status_for(True, True, True, frontier_ok, True, True, True) == "no_go_n10av_replication_chain_mismatch"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    chain_rows, chain_ok = replication_chain_records(artifacts)
    frontier_rows, frontier_ok = frontier_summary_records(artifacts)
    match_rows, match_ok = independent_recompute_match_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10av_required_public_inputs_unavailable", "no_go_n10av_replication_chain_mismatch", "no_go_n10av_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("input_artifacts", input_ok and len(input_rows) == 3),
        check("replication_chain", chain_ok and chain_rows[0]["n10au_all_15_aggregate_match_bool"] is True),
        check("frontier_summary", frontier_ok and len(frontier_rows) == 4 and frontier_rows[-1]["variant_bucket"] == "pm200" and frontier_rows[-1]["top10_span_overlap_count"] == 25),
        check("independent_match", match_ok and match_rows[0]["all_15_variant_aggregate_match_bool"] is True),
        check("claim_boundary_false_claims", claim_ok and claim_rows[0]["heldout_claim_bool"] is False and claim_rows[0]["runtime_default_claim_bool"] is False and claim_rows[0]["method_winner_claim_bool"] is False),
        check("no_private_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["variant_recompute_count"] == 0),
        check("synthetic_package_pass", synthetic_package_ok()),
        check("synthetic_mismatch", synthetic_mismatch_ok()),
        check("stop_go_false_flags", stop_go_records(True)[0]["n10aw_authorized"] is True and stop_go_records(True)[0]["private_read_authorized"] is False and stop_go_records(True)[0]["runtime_or_default_authorized"] is False),
        check("status_complete", status_for(True, True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AV exploratory span-window replication package")
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
