#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10ch_observable_hybrid_rule_audit_package.v1"
PHASE = "BEA-v1-N10CH Observable Hybrid Span-Shape Rule Sweep Audit Package"
STATUS_COMPLETE = "observable_hybrid_rule_package_complete_n10ci_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10ch_required_public_inputs_unavailable",
    "no_go_n10ch_hybrid_chain_mismatch",
    "no_go_n10ch_privacy_or_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10ch_observable_hybrid_rule_audit_package/bea_v1_n10ch_observable_hybrid_rule_audit_package_report.json")
PUBLIC_INPUTS = {
    "n10cg_observable_hybrid_rule_sweep_artifact": (Path("artifacts/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep_report.json"), "observable_hybrid_span_shape_rule_sweep_complete_n10ch_authorized"),
    "n10cf_span_shape_refinement_package_artifact": (Path("artifacts/bea_v1_n10cf_span_shape_refinement_audit_package/bea_v1_n10cf_span_shape_refinement_audit_package_report.json"), "span_shape_refinement_package_complete_n10cg_authorized"),
    "n10ce_span_shape_refinement_sweep_artifact": (Path("artifacts/bea_v1_n10ce_span_shape_gated_refinement_sweep/bea_v1_n10ce_span_shape_gated_refinement_sweep_report.json"), "span_shape_gated_refinement_sweep_complete_n10cf_authorized"),
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
    "package_bucket", "variant_bucket", "variant_family_bucket", "decision_bucket", "cost_bucket", "savings_bucket",
    "policy_input_boundary_bucket", "privacy_boundary_bucket", "claim_boundary_bucket", "no_recompute_boundary_bucket",
    "n10ci_handoff_bucket", "candidate_strategy_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
    "gate", "threshold_relation",
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
        rows.append({"anonymous_input_artifact_id": f"n10chin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def by_variant(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = artifact.get("variant_result_records", [])
    return {str(row.get("variant_bucket")): row for row in rows if isinstance(row, dict)} if isinstance(rows, list) else {}


def expected_positive_facts() -> list[dict[str, Any]]:
    return [
        {"variant_bucket": "anchor_short75_225", "top10_span_overlap_count": 24, "top20_span_overlap_count": 30, "cost_proxy_top10": 3000, "cost_proxy_top20": 6000, "decision_bucket": "no_hybrid_improvement", "lost_short75_225_hits": 0},
        {"variant_bucket": "anchor_pm200_all_spans", "top10_span_overlap_count": 25, "top20_span_overlap_count": 30, "cost_proxy_top10": 4000, "cost_proxy_top20": 8000, "decision_bucket": "no_hybrid_improvement", "lost_short75_225_hits": 0},
        {"variant_bucket": "short75_225_top3_all_pm200", "top10_span_overlap_count": 25, "top20_span_overlap_count": 31, "cost_proxy_top10": 3300, "cost_proxy_top20": 6300, "cost_savings_vs_pm200_top10": 700, "cost_savings_vs_pm200_top20": 1700, "decision_bucket": "recovers_pm200_at_lower_cost", "lost_short75_225_hits": 0},
        {"variant_bucket": "short75_225_top5_all_pm200", "top10_span_overlap_count": 25, "top20_span_overlap_count": 31, "cost_proxy_top10": 3500, "cost_proxy_top20": 6500, "cost_savings_vs_pm200_top10": 500, "cost_savings_vs_pm200_top20": 1500, "decision_bucket": "recovers_pm200_at_lower_cost", "lost_short75_225_hits": 0},
        {"variant_bucket": "short75_225_top10_all_pm200", "top10_span_overlap_count": 25, "top20_span_overlap_count": 31, "cost_proxy_top10": 4000, "cost_proxy_top20": 7000, "decision_bucket": "no_hybrid_improvement", "lost_short75_225_hits": 0},
    ]


def hybrid_rule_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    got = by_variant(artifacts.get("n10cg_observable_hybrid_rule_sweep_artifact", {}))
    ok = len(got) == 12
    rows: list[dict[str, Any]] = []
    for idx, fact in enumerate(expected_positive_facts()):
        variant = fact["variant_bucket"]
        observed = got.get(variant, {})
        match = all(observed.get(key) == value for key, value in fact.items() if key != "variant_bucket")
        ok = ok and match
        row = {"anonymous_hybrid_rule_package_id": f"n10chhybrid{idx:04d}", "package_bucket": "n10cg_observable_hybrid_rule_package", **fact, "n10cg_match_bool": match}
        if variant == "short75_225_top10_all_pm200":
            row["top10_cost_saving_success_bool"] = False
            row["not_success_reason_bucket"] = "top10_cost_not_below_pm200"
        rows.append(row)
    return rows, ok


def decision_summary_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10cg_observable_hybrid_rule_sweep_artifact", {})
    records = source.get("hybrid_decision_summary_records", [])
    row = records[0] if isinstance(records, list) and records and isinstance(records[0], dict) else {}
    ok = row.get("variant_count") == 12 and row.get("recovers_pm200_at_lower_cost_count") == 2 and row.get("improves_short_frontier_below_pm200_count") == 0 and row.get("best_observed_variant_bucket") == "short75_225_top3_all_pm200"
    return [{"anonymous_decision_summary_id": "n10chdecision0000", "package_bucket": "n10cg_hybrid_decision_package", "variant_count": 12, "recovers_pm200_at_lower_cost_count": 2, "improves_short_frontier_below_pm200_count": 0, "no_hybrid_improvement_count": 10, "best_observed_variant_bucket": "short75_225_top3_all_pm200", "best_observed_top10_span_overlap_count": 25, "best_observed_top20_span_overlap_count": 31, "n10cg_match_bool": ok}], ok


def medium_long_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    got = by_variant(artifacts.get("n10cg_observable_hybrid_rule_sweep_artifact", {}))
    variants = ["short75_225_medium20_60", "short75_225_medium40_120", "short75_225_medium75_225", "short75_225_top5_medium75_225", "short75_225_top10_medium75_225", "short75_225_top5_long75_225", "short75_225_top10_long75_225"]
    ok = True
    rows: list[dict[str, Any]] = []
    for idx, variant in enumerate(variants):
        observed = got.get(variant, {})
        retained = observed.get("top10_span_overlap_count") == 24 and observed.get("top20_span_overlap_count") == 30 and observed.get("decision_bucket") == "no_hybrid_improvement"
        ok = ok and retained
        rows.append({"anonymous_medium_long_package_id": f"n10chmidlong{idx:04d}", "package_bucket": "medium_long_hybrid_retained_short75_anchor", "variant_bucket": variant, "top10_span_overlap_count": 24, "top20_span_overlap_count": 30, "improved_anchor_bool": False, "retained_short75_anchor_bool": retained})
    return rows, ok


def policy_input_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_policy_boundary_id": "n10chpolicy0000", "policy_input_boundary_bucket": "observable_span_length_and_candidate_position_only", "span_length_bucket_policy_allowed_bool": True, "candidate_position_bucket_policy_allowed_bool": True, "gold_used_for_policy_bool": False, "outcome_used_for_policy_bool": False, "miss_direction_used_for_policy_bool": False, "file_identity_used_for_policy_bool": False, "content_used_for_policy_bool": False, "finer_bucket_used_bool": False, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "policy_boundary_valid_bool": True}], True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10chprivacy0000", "privacy_boundary_bucket": "public_observable_hybrid_rule_package_only", "private_read_count": 0, "recompute_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "privacy_boundary_complete_bool": True}], True


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10chclaim0000", "claim_boundary_bucket": "same_source_observable_hybrid_rule_package_only", "runtime_default_promotion_bool": False, "heldout_claim_bool": False, "generalization_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "candidate_add_remove_reorder_authorized_bool": False, "cluster_bridge_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "selector_reranker_authorized_bool": False, "p5_v1a_authorized_bool": False, "claim_boundary_valid_bool": True}], True


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10chnorecompute0000", "no_recompute_boundary_bucket": "public_observable_hybrid_package_only", "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "adaptive_tuning_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "candidate_generation_count": 0, "candidate_add_remove_reorder_count": 0, "cluster_bridge_execution_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10ci_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ci_handoff_id": "n10chhandoff0000", "n10ci_handoff_bucket": "n10ci_candidate_strategy_recompute_or_adapter_smoke_authorized" if complete else "n10ci_not_authorized", "n10ci_authorized_bool": complete, "candidate_strategy_bucket": "short75_225_top3_all_pm200", "candidate_strategy_scope_bucket": "independent_recompute_or_adapter_smoke_public_boundary", "private_read_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_generalization_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "candidate_add_remove_reorder_authorized_bool": False, "cluster_bridge_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_downstream_authorized_bool": False}]


def gate_records(input_ok: bool, hybrid_ok: bool, decision_ok: bool, mid_ok: bool, policy_ok: bool, privacy_ok: bool, claim_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("hybrid_rule_package", hybrid_ok), ("decision_summary", decision_ok), ("medium_long_retention", mid_ok), ("policy_input_boundary", policy_ok), ("privacy_boundary", privacy_ok), ("claim_boundary", claim_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ci_authorized" if complete else "n10ci_not_authorized", "next_allowed_phase": "BEA-v1-N10CI Candidate Strategy Independent Recompute or Adapter Smoke" if complete else "none_until_observable_hybrid_package_is_consistent", "next_allowed_scope_bucket": "short75_225_top3_all_pm200_only" if complete else "no_next_phase", "n10ci_authorized": complete, "private_read_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_add_remove_reorder_authorized": False, "cluster_bridge_authorized": False, "adaptive_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, hybrid_ok: bool, decision_ok: bool, mid_ok: bool, policy_ok: bool, privacy_ok: bool, claim_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ch_required_public_inputs_unavailable"
    if not hybrid_ok or not decision_ok or not mid_ok or not policy_ok:
        return "no_go_n10ch_hybrid_chain_mismatch"
    if not privacy_ok or not claim_ok or not norecompute_ok:
        return "no_go_n10ch_privacy_or_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    hybrid_rows, hybrid_ok = hybrid_rule_package_records(artifacts)
    decision_rows, decision_ok = decision_summary_records(artifacts)
    mid_rows, mid_ok = medium_long_package_records(artifacts)
    policy_rows, policy_ok = policy_input_boundary_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, hybrid_ok, decision_ok, mid_ok, policy_ok, privacy_ok, claim_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_observable_hybrid_rule_package_only", "generated_by": "bea_v1_n10ch_observable_hybrid_rule_audit_package", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "hybrid_rule_package_records": hybrid_rows, "hybrid_decision_package_records": decision_rows, "medium_long_retention_package_records": mid_rows, "policy_input_boundary_records": policy_rows, "privacy_boundary_records": privacy_rows, "claim_boundary_records": claim_rows, "no_recompute_records": norecompute_rows, "n10ci_handoff_records": n10ci_handoff_records(complete), "gate_records": gate_records(input_ok, hybrid_ok, decision_ok, mid_ok, policy_ok, privacy_ok, claim_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10ci_handoff_records"] = n10ci_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, hybrid_ok, decision_ok, mid_ok, policy_ok, privacy_ok, claim_ok, norecompute_ok, scanner_ok)
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


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    hybrid_rows, hybrid_ok = hybrid_rule_package_records(artifacts)
    decision_rows, decision_ok = decision_summary_records(artifacts)
    mid_rows, mid_ok = medium_long_package_records(artifacts)
    policy_rows, policy_ok = policy_input_boundary_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10ch_required_public_inputs_unavailable", "no_go_n10ch_hybrid_chain_mismatch", "no_go_n10ch_privacy_or_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 3),
        check("hybrid_package", hybrid_ok and len(hybrid_rows) == 5 and hybrid_rows[2]["decision_bucket"] == "recovers_pm200_at_lower_cost"),
        check("decision_summary", decision_ok and decision_rows[0]["recovers_pm200_at_lower_cost_count"] == 2),
        check("medium_long", mid_ok and len(mid_rows) == 7),
        check("policy_boundary", policy_ok and policy_rows[0]["gold_used_for_policy_bool"] is False and policy_rows[0]["file_identity_used_for_policy_bool"] is False),
        check("privacy", privacy_ok and privacy_rows[0]["private_read_count"] == 0),
        check("claim_boundary", claim_ok and claim_rows[0]["runtime_default_promotion_bool"] is False and claim_rows[0]["heldout_claim_bool"] is False),
        check("no_recompute", norecompute_ok and norecompute_rows[0]["recompute_count"] == 0 and norecompute_rows[0]["new_variant_count"] == 0),
        check("synthetic_mismatch", status_for(True, True, False, True, True, True, True, True, True) == "no_go_n10ch_hybrid_chain_mismatch"),
        check("false_flags", stop_go_records(True)[0]["n10ci_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["candidate_generation_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10CH observable hybrid rule audit package")
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
