#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package.v1"
PHASE = "BEA-v1-N10BB Cost-Aware Span-Window Selection Rule Smoke Audit Package"
STATUS_COMPLETE = "cost_aware_selection_rule_smoke_audit_package_complete_n10bc_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10bb_required_public_inputs_unavailable",
    "no_go_n10bb_selection_rule_chain_mismatch",
    "no_go_n10bb_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package_report.json")
PUBLIC_INPUTS = {
    "n10ba_selection_rule_smoke_artifact": (Path("artifacts/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke_report.json"), "cost_aware_span_window_selection_rule_smoke_complete_n10bb_authorized"),
    "n10az_adapter_frontier_audit_package_artifact": (Path("artifacts/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package_report.json"), "cost_aware_adapter_frontier_smoke_audit_package_complete_n10ba_authorized"),
    "n10ay_adapter_frontier_smoke_artifact": (Path("artifacts/bea_v1_n10ay_cost_aware_adapter_frontier_smoke/bea_v1_n10ay_cost_aware_adapter_frontier_smoke_report.json"), "cost_aware_adapter_frontier_smoke_pass_n10az_authorized"),
    "n10ax_claim_package_artifact": (Path("artifacts/bea_v1_n10ax_cost_sensitive_frontier_claim_package/bea_v1_n10ax_cost_sensitive_frontier_claim_package_report.json"), "cost_sensitive_frontier_claim_package_complete_n10ay_authorized"),
    "n10aw_mechanism_decomposition_artifact": (Path("artifacts/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition_report.json"), "cost_sensitive_span_window_frontier_mechanism_decomposition_complete_n10ax_authorized"),
}
OPERATING_POINTS = {
    "low_cost": {"variant_bucket": "pm30", "top10": 18, "top20": 22, "delta10": 9, "delta20": 12, "cost": 600, "cost_bucket": "low"},
    "balanced": {"variant_bucket": "before25_after75", "top10": 20, "top20": 24, "delta10": 11, "delta20": 14, "cost": 1000, "cost_bucket": "medium"},
    "max_recall": {"variant_bucket": "pm200", "top10": 25, "top20": 30, "delta10": 16, "delta20": 20, "cost": 4000, "cost_bucket": "very_high"},
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
    "selection_rule_chain_bucket", "operating_point_bucket", "variant_bucket", "cost_bucket", "rule_boundary_bucket",
    "adapter_path_bucket", "claim_boundary_bucket", "forbidden_claim_bucket", "no_recompute_boundary_bucket",
    "n10bc_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
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
        rows.append({"anonymous_input_artifact_id": f"n10bbin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def by_operating_point(rows: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("operating_point_bucket"), str):
                out[row["operating_point_bucket"]] = row
    return out


def selection_rule_chain_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10ba = artifacts.get("n10ba_selection_rule_smoke_artifact", {})
    n10az = artifacts.get("n10az_adapter_frontier_audit_package_artifact", {})
    n10ay = artifacts.get("n10ay_adapter_frontier_smoke_artifact", {})
    ok = n10ba.get("status") == PUBLIC_INPUTS["n10ba_selection_rule_smoke_artifact"][1] and n10az.get("status") == PUBLIC_INPUTS["n10az_adapter_frontier_audit_package_artifact"][1] and n10ay.get("status") == PUBLIC_INPUTS["n10ay_adapter_frontier_smoke_artifact"][1]
    return [{"anonymous_selection_rule_chain_id": "n10bbchain0000", "selection_rule_chain_bucket": "n10ba_public_audit_package", "n10ba_status_complete_bool": n10ba.get("status") == PUBLIC_INPUTS["n10ba_selection_rule_smoke_artifact"][1], "n10az_audit_complete_bool": n10az.get("status") == PUBLIC_INPUTS["n10az_adapter_frontier_audit_package_artifact"][1], "n10ay_smoke_pass_bool": n10ay.get("status") == PUBLIC_INPUTS["n10ay_adapter_frontier_smoke_artifact"][1], "selection_rule_chain_complete_bool": ok}], ok


def operating_point_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10ba = artifacts.get("n10ba_selection_rule_smoke_artifact", {})
    result_rows = by_operating_point(n10ba.get("operating_point_result_records", []))
    rule_rows = by_operating_point(n10ba.get("operating_point_rule_records", []))
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (point, expected) in enumerate(OPERATING_POINTS.items()):
        result = result_rows.get(point, {})
        rule = rule_rows.get(point, {})
        matched = result.get("variant_bucket") == expected["variant_bucket"] and rule.get("variant_bucket") == expected["variant_bucket"] and result.get("top10_span_overlap_count") == expected["top10"] and result.get("top20_span_overlap_count") == expected["top20"] and result.get("delta_top10_vs_baseline_count") == expected["delta10"] and result.get("delta_top20_vs_baseline_count") == expected["delta20"] and result.get("cost_proxy_value") == expected["cost"] and result.get("cost_bucket") == expected["cost_bucket"] and result.get("lost_previous_hits") == 0 and result.get("candidate_pool_changed_bool") is False and result.get("candidate_order_changed_bool") is False and rule.get("adaptive_per_case_selection_bool") is False and rule.get("new_window_size_bool") is False and rule.get("runtime_default_bool") is False
        ok = ok and matched
        rows.append({"anonymous_operating_point_package_id": f"n10bbop{idx:04d}", "operating_point_bucket": point, "variant_bucket": expected["variant_bucket"], "top10_span_overlap_count": expected["top10"], "top20_span_overlap_count": expected["top20"], "delta_top10_vs_baseline_count": expected["delta10"], "delta_top20_vs_baseline_count": expected["delta20"], "cost_proxy_value": expected["cost"], "cost_bucket": expected["cost_bucket"], "lost_previous_hits": 0, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "new_window_size_bool": False, "adaptive_per_case_selection_bool": False, "runtime_default_bool": False, "n10ba_match_bool": matched})
    return rows, ok


def rule_boundary_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    boundary = artifacts.get("n10ba_selection_rule_smoke_artifact", {}).get("rule_boundary_records", [])
    record = boundary[0] if isinstance(boundary, list) and boundary and isinstance(boundary[0], dict) else {}
    ok = record.get("operating_point_count") == 3 and record.get("new_window_size_count") == 0 and record.get("adaptive_per_case_selection_count") == 0 and record.get("runtime_default_count") == 0 and record.get("method_winner_claim_count") == 0 and record.get("downstream_value_claim_count") == 0 and record.get("heldout_claim_count") == 0
    return [{"anonymous_rule_boundary_id": "n10bbboundary0000", "rule_boundary_bucket": "named_operating_points_not_defaults_public_package", "operating_point_count": 3, "new_window_size_count": 0, "adaptive_per_case_selection_count": 0, "runtime_default_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "heldout_claim_count": 0, "rule_boundary_match_bool": ok}], ok


def adapter_path_audit_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    adapter_rows = artifacts.get("n10ba_selection_rule_smoke_artifact", {}).get("adapter_path_records", [])
    record = adapter_rows[0] if isinstance(adapter_rows, list) and adapter_rows and isinstance(adapter_rows[0], dict) else {}
    ok = record.get("adapter_imported_bool") is True and record.get("helper_imported_via_adapter_bool") is True and record.get("existing_evaluator_imported_bool") is False and record.get("existing_evaluator_called_bool") is False and record.get("existing_evaluator_hook_in_bool") is False and record.get("runtime_default_hook_bool") is False
    return [{"anonymous_adapter_path_audit_id": "n10bbadapter0000", "adapter_path_bucket": "adapter_helper_only_no_existing_evaluator_or_runtime_hook", "adapter_imported_bool": True, "helper_imported_via_adapter_bool": True, "existing_evaluator_imported_bool": False, "existing_evaluator_called_bool": False, "existing_evaluator_hook_in_bool": False, "runtime_default_hook_bool": False, "adapter_path_boundary_match_bool": ok}], ok


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10bbclaim0000", "claim_boundary_bucket": "same_source_n1_proxy_selection_rule_public_package_only", "allowed_claim_named_operating_points_packaged_bool": True, "runtime_default_claim_bool": False, "heldout_claim_bool": False, "generalization_claim_bool": False, "n2_equivalent_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "selector_reranker_claim_bool": False, "p5_or_v1a_claim_bool": False, "claim_boundary_valid_bool": True}], True


def forbidden_claim_records() -> tuple[list[dict[str, Any]], bool]:
    buckets = ("runtime_default", "heldout_generalization", "method_winner", "downstream_value", "retrieval_rerun", "candidate_generation", "selector_reranker", "p5_v1a", "new_variants", "adaptive_selection")
    return ([{"anonymous_forbidden_claim_id": f"n10bbforbid{idx:04d}", "forbidden_claim_bucket": bucket, "claim_made_bool": False, "claim_authorized_bool": False} for idx, bucket in enumerate(buckets)], True)


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10bbnorecompute0000", "no_recompute_boundary_bucket": "public_selection_rule_audit_package_only", "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "adaptive_selection_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "existing_evaluator_hook_in_count": 0, "runtime_default_change_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10bc_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10bc_handoff_id": "n10bbhandoff0000", "n10bc_handoff_bucket": "n10bc_operating_point_tradeoff_decomposition_authorized" if complete else "n10bc_not_authorized", "n10bc_authorized_bool": complete, "same_scoped_n1_span_rows_read_authorized_bool": complete, "broad_private_read_authorized_bool": False, "new_variant_authorized_bool": False, "analyze_low_balanced_max_recall_only_bool": True, "public_bucket_count_output_only_bool": True, "runtime_default_authorized_bool": False, "heldout_generalization_claim_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, chain_ok: bool, op_ok: bool, boundary_ok: bool, adapter_ok: bool, claim_ok: bool, forbid_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("selection_rule_chain", chain_ok), ("operating_point_package", op_ok), ("rule_boundary", boundary_ok), ("adapter_path", adapter_ok), ("claim_boundary", claim_ok), ("forbidden_claims_false", forbid_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10bc_operating_point_tradeoff_decomposition_authorized" if complete else "n10bc_not_authorized", "next_allowed_phase": "BEA-v1-N10BC Operating-Point Tradeoff Decomposition" if complete else "none_until_selection_rule_package_is_consistent", "next_allowed_scope_bucket": "same_scoped_rows_low_balanced_max_recall_tradeoff_decomposition" if complete else "no_next_phase", "n10bc_authorized": complete, "same_scoped_n1_span_rows_read_authorized": complete, "broad_private_read_authorized": False, "private_read_authorized": False, "new_variant_authorized": False, "adaptive_selection_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, chain_ok: bool, op_ok: bool, boundary_ok: bool, adapter_ok: bool, claim_ok: bool, forbid_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10bb_required_public_inputs_unavailable"
    if not chain_ok or not op_ok or not boundary_ok or not adapter_ok:
        return "no_go_n10bb_selection_rule_chain_mismatch"
    if not claim_ok or not forbid_ok or not norecompute_ok:
        return "no_go_n10bb_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    chain_rows, chain_ok = selection_rule_chain_records(artifacts)
    op_rows, op_ok = operating_point_package_records(artifacts)
    boundary_rows, boundary_ok = rule_boundary_records(artifacts)
    adapter_rows, adapter_ok = adapter_path_audit_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    forbidden_rows, forbid_ok = forbidden_claim_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, chain_ok, op_ok, boundary_ok, adapter_ok, claim_ok, forbid_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_selection_rule_smoke_audit_package_only", "generated_by": "bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "selection_rule_chain_records": chain_rows, "operating_point_package_records": op_rows, "rule_boundary_records": boundary_rows, "adapter_path_audit_records": adapter_rows, "claim_boundary_records": claim_rows, "forbidden_claim_records": forbidden_rows, "no_recompute_records": norecompute_rows, "n10bc_handoff_records": n10bc_handoff_records(complete), "gate_records": gate_records(input_ok, chain_ok, op_ok, boundary_ok, adapter_ok, claim_ok, forbid_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10bc_handoff_records"] = n10bc_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, chain_ok, op_ok, boundary_ok, adapter_ok, claim_ok, forbid_ok, norecompute_ok, scanner_ok)
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
    fake = {"n10ba_selection_rule_smoke_artifact": {"operating_point_result_records": [{"operating_point_bucket": k, "variant_bucket": v["variant_bucket"], "top10_span_overlap_count": v["top10"], "top20_span_overlap_count": v["top20"], "delta_top10_vs_baseline_count": v["delta10"], "delta_top20_vs_baseline_count": v["delta20"], "cost_proxy_value": v["cost"], "cost_bucket": v["cost_bucket"], "lost_previous_hits": 0, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False} for k, v in OPERATING_POINTS.items()], "operating_point_rule_records": [{"operating_point_bucket": k, "variant_bucket": v["variant_bucket"], "adaptive_per_case_selection_bool": False, "new_window_size_bool": False, "runtime_default_bool": False} for k, v in OPERATING_POINTS.items()], "rule_boundary_records": [{"operating_point_count": 3, "new_window_size_count": 0, "adaptive_per_case_selection_count": 0, "runtime_default_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "heldout_claim_count": 0}], "adapter_path_records": [{"adapter_imported_bool": True, "helper_imported_via_adapter_bool": True, "existing_evaluator_imported_bool": False, "existing_evaluator_called_bool": False, "existing_evaluator_hook_in_bool": False, "runtime_default_hook_bool": False}]}}
    return operating_point_package_records(fake)[1] and rule_boundary_records(fake)[1] and adapter_path_audit_records(fake)[1]


def synthetic_mismatch() -> bool:
    fake = {"n10ba_selection_rule_smoke_artifact": {"operating_point_result_records": []}}
    _rows, ok = operating_point_package_records(fake)
    return not ok and status_for(True, True, True, ok, True, True, True, True, True) == "no_go_n10bb_selection_rule_chain_mismatch"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    chain_rows, chain_ok = selection_rule_chain_records(artifacts)
    op_rows, op_ok = operating_point_package_records(artifacts)
    boundary_rows, boundary_ok = rule_boundary_records(artifacts)
    adapter_rows, adapter_ok = adapter_path_audit_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    forbidden_rows, forbid_ok = forbidden_claim_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10bb_required_public_inputs_unavailable", "no_go_n10bb_selection_rule_chain_mismatch", "no_go_n10bb_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 5),
        check("chain", chain_ok and chain_rows[0]["n10ba_status_complete_bool"] is True),
        check("operating_points", op_ok and len(op_rows) == 3 and op_rows[-1]["operating_point_bucket"] == "max_recall" and op_rows[-1]["top10_span_overlap_count"] == 25),
        check("rule_boundary", boundary_ok and boundary_rows[0]["adaptive_per_case_selection_count"] == 0),
        check("adapter_path", adapter_ok and adapter_rows[0]["existing_evaluator_hook_in_bool"] is False),
        check("claim_boundary", claim_ok and claim_rows[0]["runtime_default_claim_bool"] is False and claim_rows[0]["method_winner_claim_bool"] is False),
        check("forbidden_claims", forbid_ok and all(r["claim_made_bool"] is False for r in forbidden_rows)),
        check("no_private_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["recompute_count"] == 0),
        check("synthetic_package_pass", synthetic_package_pass()),
        check("synthetic_mismatch", synthetic_mismatch()),
        check("stop_go_false_flags", stop_go_records(True)[0]["n10bc_authorized"] is True and stop_go_records(True)[0]["same_scoped_n1_span_rows_read_authorized"] is True and stop_go_records(True)[0]["broad_private_read_authorized"] is False and stop_go_records(True)[0]["new_variant_authorized"] is False and stop_go_records(True)[0]["runtime_or_default_authorized"] is False),
        check("status_complete", status_for(True, True, True, True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BB selection rule smoke audit package")
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
