#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package.v1"
PHASE = "BEA-v1-N10AZ Cost-Aware Adapter Frontier Smoke Result Audit Package"
STATUS_COMPLETE = "cost_aware_adapter_frontier_smoke_audit_package_complete_n10ba_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10az_required_public_inputs_unavailable",
    "no_go_n10az_adapter_frontier_chain_mismatch",
    "no_go_n10az_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package_report.json")
PUBLIC_INPUTS = {
    "n10ay_adapter_frontier_smoke_artifact": (Path("artifacts/bea_v1_n10ay_cost_aware_adapter_frontier_smoke/bea_v1_n10ay_cost_aware_adapter_frontier_smoke_report.json"), "cost_aware_adapter_frontier_smoke_pass_n10az_authorized"),
    "n10ax_claim_package_artifact": (Path("artifacts/bea_v1_n10ax_cost_sensitive_frontier_claim_package/bea_v1_n10ax_cost_sensitive_frontier_claim_package_report.json"), "cost_sensitive_frontier_claim_package_complete_n10ay_authorized"),
    "n10aw_mechanism_decomposition_artifact": (Path("artifacts/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition_report.json"), "cost_sensitive_span_window_frontier_mechanism_decomposition_complete_n10ax_authorized"),
    "n10av_replication_package_artifact": (Path("artifacts/bea_v1_n10av_exploratory_span_window_sweep_replication_package/bea_v1_n10av_exploratory_span_window_sweep_replication_package_report.json"), "exploratory_span_window_sweep_replication_package_complete_n10aw_authorized"),
}
FRONTIER = {
    "pm30": {"top10": 18, "top20": 22, "cost_value": 600, "cost_bucket": "low"},
    "before25_after75": {"top10": 20, "top20": 24, "cost_value": 1000, "cost_bucket": "medium"},
    "pm75": {"top10": 21, "top20": 25, "cost_value": 1500, "cost_bucket": "medium"},
    "pm200": {"top10": 25, "top20": 30, "cost_value": 4000, "cost_bucket": "very_high"},
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
    "audit_chain_bucket", "adapter_boundary_bucket", "variant_bucket", "cost_bucket", "claim_boundary_bucket",
    "forbidden_claim_bucket", "no_recompute_boundary_bucket", "n10ba_handoff_bucket", "authorization",
    "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation", "operating_point_bucket",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def root() -> Path:
    return Path(__file__).resolve().parent.parent



def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(rel: Path) -> tuple[dict[str, Any], str]:
    full = root() / rel
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(rel: Path, obj: dict[str, Any]) -> None:
    full = root() / rel
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
        rows.append({"anonymous_input_artifact_id": f"n10azin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def by_variant(rows: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("variant_bucket"), str):
                out[row["variant_bucket"]] = row
    return out


def audit_chain_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10ay = artifacts.get("n10ay_adapter_frontier_smoke_artifact", {})
    n10ax = artifacts.get("n10ax_claim_package_artifact", {})
    n10aw = artifacts.get("n10aw_mechanism_decomposition_artifact", {})
    n10av = artifacts.get("n10av_replication_package_artifact", {})
    ok = all(
        artifacts.get(bucket, {}).get("status") == expected
        for bucket, (_path, expected) in PUBLIC_INPUTS.items()
    )
    return [{"anonymous_audit_chain_id": "n10azchain0000", "audit_chain_bucket": "n10ay_to_n10az_public_package", "n10ay_status_pass_bool": n10ay.get("status") == PUBLIC_INPUTS["n10ay_adapter_frontier_smoke_artifact"][1], "n10ax_package_complete_bool": n10ax.get("status") == PUBLIC_INPUTS["n10ax_claim_package_artifact"][1], "n10aw_decomposition_complete_bool": n10aw.get("status") == PUBLIC_INPUTS["n10aw_mechanism_decomposition_artifact"][1], "n10av_replication_complete_bool": n10av.get("status") == PUBLIC_INPUTS["n10av_replication_package_artifact"][1], "audit_chain_complete_bool": ok}], ok


def adapter_boundary_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10ay = artifacts.get("n10ay_adapter_frontier_smoke_artifact", {})
    rows = n10ay.get("adapter_import_records", [])
    record = rows[0] if isinstance(rows, list) and rows and isinstance(rows[0], dict) else {}
    intake = n10ay.get("private_input_intake_records", [])
    intake_row = intake[0] if isinstance(intake, list) and intake and isinstance(intake[0], dict) else {}
    ok = record.get("adapter_imported_bool") is True and record.get("helper_imported_via_adapter_bool") is True and record.get("existing_evaluator_imported_bool") is False and record.get("existing_evaluator_called_bool") is False and record.get("existing_evaluator_hook_in_bool") is False and record.get("runtime_default_hook_bool") is False and intake_row.get("private_span_rows_read") == 213
    return [{"anonymous_adapter_boundary_id": "n10azadapter0000", "adapter_boundary_bucket": "default_off_adapter_helper_no_existing_evaluator_hook", "adapter_imported_bool": record.get("adapter_imported_bool") is True, "helper_imported_via_adapter_bool": record.get("helper_imported_via_adapter_bool") is True, "existing_evaluator_imported_bool": False, "existing_evaluator_called_bool": False, "existing_evaluator_hook_in_bool": False, "runtime_default_hook_bool": False, "same_scoped_input_row_count_from_n10ay": int(intake_row.get("private_span_rows_read", 0) or 0), "n10az_private_read_count": 0, "adapter_boundary_valid_bool": ok}], ok


def frontier_audit_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10ay = by_variant(artifacts.get("n10ay_adapter_frontier_smoke_artifact", {}).get("frontier_adapter_result_records", []))
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (variant, expected) in enumerate(FRONTIER.items()):
        observed = n10ay.get(variant, {})
        matched = observed.get("top10_span_overlap_count") == expected["top10"] and observed.get("top20_span_overlap_count") == expected["top20"] and observed.get("cost_proxy_value") == expected["cost_value"] and observed.get("cost_bucket") == expected["cost_bucket"] and observed.get("candidate_pool_changed_bool") is False and observed.get("candidate_order_changed_bool") is False and observed.get("original_span_hit_lost_count") == 0 and observed.get("expected_match_bool") is True
        ok = ok and matched
        rows.append({"anonymous_frontier_audit_id": f"n10azfront{idx:04d}", "variant_bucket": variant, "top10_span_overlap_count": expected["top10"], "top20_span_overlap_count": expected["top20"], "cost_proxy_value": expected["cost_value"], "cost_bucket": expected["cost_bucket"], "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "original_span_hit_lost_count": 0, "locked_aggregate_match_bool": matched})
    return rows, ok


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10azclaim0000", "claim_boundary_bucket": "same_source_n1_proxy_adapter_smoke_public_package_only", "allowed_claim_adapter_reproduces_locked_frontier_bool": True, "exploratory_same_source_n1_proxy_only_bool": True, "heldout_claim_bool": False, "generalization_claim_bool": False, "n2_equivalent_claim_bool": False, "runtime_default_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "selector_reranker_claim_bool": False, "p5_or_v1a_claim_bool": False, "claim_boundary_valid_bool": True}], True


def forbidden_claim_records() -> tuple[list[dict[str, Any]], bool]:
    buckets = ("runtime_default", "heldout_generalization", "method_winner", "downstream_value", "retrieval_rerun", "candidate_generation", "selector_reranker", "p5_v1a", "new_variants", "adaptive_tuning")
    return ([{"anonymous_forbidden_claim_id": f"n10azforbid{idx:04d}", "forbidden_claim_bucket": bucket, "claim_made_bool": False, "claim_authorized_bool": False} for idx, bucket in enumerate(buckets)], True)


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10aznorecompute0000", "no_recompute_boundary_bucket": "public_audit_package_only", "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "adaptive_tuning_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "existing_evaluator_hook_in_count": 0, "runtime_default_change_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10ba_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ba_handoff_id": "n10azhandoff0000", "n10ba_handoff_bucket": "n10ba_cost_aware_span_window_selection_rule_smoke_authorized" if complete else "n10ba_not_authorized", "n10ba_authorized_bool": complete, "same_scoped_n1_span_rows_read_authorized_bool": complete, "broad_private_read_authorized_bool": False, "predeclared_operating_points_only_bool": True, "low_cost_operating_point_bucket": "pm30", "balanced_operating_point_bucket": "before25_after75", "max_recall_operating_point_bucket": "pm200", "no_adaptive_per_case_selection_bool": True, "runtime_default_authorized_bool": False, "heldout_generalization_claim_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, chain_ok: bool, adapter_ok: bool, frontier_ok: bool, claim_ok: bool, forbidden_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("audit_chain", chain_ok), ("adapter_boundary", adapter_ok), ("frontier_metrics", frontier_ok), ("claim_boundary", claim_ok), ("forbidden_claims_false", forbidden_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ba_cost_aware_selection_rule_smoke_authorized" if complete else "n10ba_not_authorized", "next_allowed_phase": "BEA-v1-N10BA Cost-Aware Span-Window Selection Rule Smoke" if complete else "none_until_cost_aware_adapter_smoke_public_chain_is_consistent", "next_allowed_scope_bucket": "same_scoped_rows_named_operating_points_no_defaults" if complete else "no_next_phase", "n10ba_authorized": complete, "same_scoped_n1_span_rows_read_authorized": complete, "broad_private_read_authorized": False, "private_read_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "new_variant_authorized": False, "adaptive_tuning_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, chain_ok: bool, adapter_ok: bool, frontier_ok: bool, claim_ok: bool, forbidden_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10az_required_public_inputs_unavailable"
    if not chain_ok or not adapter_ok or not frontier_ok:
        return "no_go_n10az_adapter_frontier_chain_mismatch"
    if not claim_ok or not forbidden_ok or not norecompute_ok:
        return "no_go_n10az_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    chain_rows, chain_ok = audit_chain_records(artifacts)
    adapter_rows, adapter_ok = adapter_boundary_records(artifacts)
    frontier_rows, frontier_ok = frontier_audit_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    forbidden_rows, forbidden_ok = forbidden_claim_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, chain_ok, adapter_ok, frontier_ok, claim_ok, forbidden_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_adapter_frontier_smoke_audit_package_only", "generated_by": "bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "audit_chain_records": chain_rows, "adapter_boundary_records": adapter_rows, "frontier_audit_records": frontier_rows, "claim_boundary_records": claim_rows, "forbidden_claim_records": forbidden_rows, "no_recompute_records": norecompute_rows, "n10ba_handoff_records": n10ba_handoff_records(complete), "gate_records": gate_records(input_ok, chain_ok, adapter_ok, frontier_ok, claim_ok, forbidden_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10ba_handoff_records"] = n10ba_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, chain_ok, adapter_ok, frontier_ok, claim_ok, forbidden_ok, norecompute_ok, scanner_ok)
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
    artifacts = {"n10ay_adapter_frontier_smoke_artifact": {"status": PUBLIC_INPUTS["n10ay_adapter_frontier_smoke_artifact"][1], "adapter_import_records": [{"adapter_imported_bool": True, "helper_imported_via_adapter_bool": True, "existing_evaluator_imported_bool": False, "existing_evaluator_called_bool": False, "existing_evaluator_hook_in_bool": False, "runtime_default_hook_bool": False}], "private_input_intake_records": [{"private_span_rows_read": 213}], "frontier_adapter_result_records": [{"variant_bucket": k, "top10_span_overlap_count": v["top10"], "top20_span_overlap_count": v["top20"], "cost_proxy_value": v["cost_value"], "cost_bucket": v["cost_bucket"], "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "original_span_hit_lost_count": 0, "expected_match_bool": True} for k, v in FRONTIER.items()]}}
    _, adapter_ok = adapter_boundary_records(artifacts)
    _, frontier_ok = frontier_audit_records(artifacts)
    return adapter_ok and frontier_ok


def synthetic_mismatch() -> bool:
    artifacts = {"n10ay_adapter_frontier_smoke_artifact": {"frontier_adapter_result_records": []}}
    _, frontier_ok = frontier_audit_records(artifacts)
    return not frontier_ok and status_for(True, True, True, True, frontier_ok, True, True, True) == "no_go_n10az_adapter_frontier_chain_mismatch"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    chain_rows, chain_ok = audit_chain_records(artifacts)
    adapter_rows, adapter_ok = adapter_boundary_records(artifacts)
    frontier_rows, frontier_ok = frontier_audit_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    forbidden_rows, forbidden_ok = forbidden_claim_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10az_required_public_inputs_unavailable", "no_go_n10az_adapter_frontier_chain_mismatch", "no_go_n10az_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 4),
        check("audit_chain", chain_ok and chain_rows[0]["n10ay_status_pass_bool"] is True),
        check("adapter_boundary", adapter_ok and adapter_rows[0]["same_scoped_input_row_count_from_n10ay"] == 213 and adapter_rows[0]["runtime_default_hook_bool"] is False),
        check("frontier_audit", frontier_ok and len(frontier_rows) == 4 and frontier_rows[-1]["variant_bucket"] == "pm200" and frontier_rows[-1]["top10_span_overlap_count"] == 25),
        check("claim_boundary", claim_ok and claim_rows[0]["runtime_default_claim_bool"] is False and claim_rows[0]["method_winner_claim_bool"] is False),
        check("forbidden_claims_false", forbidden_ok and all(r["claim_made_bool"] is False for r in forbidden_rows)),
        check("no_private_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["recompute_count"] == 0),
        check("synthetic_package_pass", synthetic_package_pass()),
        check("synthetic_mismatch", synthetic_mismatch()),
        check("stop_go_false_flags", stop_go_records(True)[0]["n10ba_authorized"] is True and stop_go_records(True)[0]["same_scoped_n1_span_rows_read_authorized"] is True and stop_go_records(True)[0]["broad_private_read_authorized"] is False and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["new_variant_authorized"] is False),
        check("status_complete", status_for(True, True, True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AZ cost-aware adapter frontier smoke audit package")
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
