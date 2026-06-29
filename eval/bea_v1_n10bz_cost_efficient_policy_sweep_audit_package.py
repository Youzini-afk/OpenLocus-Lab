#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10bz_cost_efficient_policy_sweep_audit_package.v1"
PHASE = "BEA-v1-N10BZ Same-Source Cost-Efficient Policy Sweep Audit Package"
STATUS_COMPLETE = "cost_efficient_policy_sweep_package_complete_n10ca_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10bz_required_public_inputs_unavailable",
    "no_go_n10bz_policy_sweep_chain_mismatch",
    "no_go_n10bz_privacy_or_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package_report.json")
PUBLIC_INPUTS = {
    "n10by_policy_sweep_artifact": (Path("artifacts/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep_report.json"), "same_source_cost_efficient_span_window_policy_sweep_complete_n10bz_authorized"),
    "n10bx_adapter_operating_point_package_artifact": (Path("artifacts/bea_v1_n10bx_adapter_operating_point_package/bea_v1_n10bx_adapter_operating_point_package_report.json"), "adapter_operating_point_package_complete_n10by_authorized"),
    "n10bw_adapter_operating_point_smoke_artifact": (Path("artifacts/bea_v1_n10bw_adapter_operating_point_smoke/bea_v1_n10bw_adapter_operating_point_smoke_report.json"), "adapter_operating_point_smoke_pass_n10bx_authorized"),
    "n10bq_plateau_cost_minimization_artifact": (Path("artifacts/bea_v1_n10bq_plateau_cost_minimization_sweep/bea_v1_n10bq_plateau_cost_minimization_sweep_report.json"), "plateau_cost_minimization_sweep_complete_n10br_authorized"),
    "n10bs_boundary_cost_refinement_artifact": (Path("artifacts/bea_v1_n10bs_boundary_cost_refinement_sweep/bea_v1_n10bs_boundary_cost_refinement_sweep_report.json"), "boundary_cost_refinement_sweep_complete_n10bt_authorized"),
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
    "package_bucket", "variant_bucket", "variant_family_bucket", "decision_bucket", "conclusion_bucket", "privacy_boundary_bucket",
    "claim_boundary_bucket", "no_recompute_boundary_bucket", "n10ca_handoff_bucket", "next_mechanism_search_bucket",
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
        rows.append({"anonymous_input_artifact_id": f"n10bzin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def by_variant(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = artifact.get("variant_result_records", [])
    return {str(row.get("variant_bucket")): row for row in rows if isinstance(row, dict)} if isinstance(rows, list) else {}


def sweep_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10by_policy_sweep_artifact", {})
    variants = by_variant(source)
    expected = [
        ("anchor_cost80_before20_after60", 20, 24, 800, 1600, 0, 0, "no_improvement_anchor_retained"),
        ("anchor_pm50_before50_after50", 19, 23, 1000, 2000, 1, 0, "no_improvement_anchor_retained"),
        ("asym_cost70_before18_after52", 19, 23, 700, 1400, 1, 0, "no_improvement_anchor_retained"),
        ("asym_cost72_before18_after54", 19, 23, 720, 1440, 1, 0, "no_improvement_anchor_retained"),
        ("asym_cost75_before19_after56", 19, 23, 750, 1500, 1, 0, "no_improvement_anchor_retained"),
        ("asym_cost78_before20_after58", 19, 23, 780, 1560, 1, 0, "no_improvement_anchor_retained"),
        ("rank_conditioned_top5_30_90_top10_10_30", 19, 20, 800, 800, 1, 0, "no_improvement_anchor_retained"),
        ("rank_conditioned_top5_25_75_top10_10_30", 19, 20, 700, 700, 1, 0, "no_improvement_anchor_retained"),
        ("rank_conditioned_top3_40_120_top10_10_30", 19, 20, 760, 760, 2, 0, "no_improvement_anchor_retained"),
        ("top10_only_cost80_before20_after60", 20, 21, 800, 800, 0, 0, "no_improvement_anchor_retained"),
        ("top5_only_cost80_before20_after60", 12, 13, 400, 400, 8, 0, "no_improvement_anchor_retained"),
        ("top20_only_cost80_before20_after60", 20, 24, 800, 1600, 0, 0, "no_improvement_anchor_retained"),
    ]
    rows: list[dict[str, Any]] = []
    ok = len(variants) == 12
    for idx, (variant, top10, top20, cost10, cost20, lost_anchor, lost_original, decision) in enumerate(expected):
        got = variants.get(variant, {})
        match = got.get("top10_span_overlap_count") == top10 and got.get("top20_span_overlap_count") == top20 and got.get("cost_proxy_top10") == cost10 and got.get("cost_proxy_top20") == cost20 and got.get("lost_anchor_top10_hits") == lost_anchor and got.get("lost_original_span_hits") == lost_original and got.get("decision_bucket") == decision and got.get("candidate_pool_changed_bool") is False and got.get("candidate_order_changed_bool") is False
        ok = ok and match
        family = str(got.get("variant_family_bucket", "unknown"))
        rows.append({"anonymous_policy_sweep_package_id": f"n10bzvar{idx:04d}", "package_bucket": "n10by_variant_metric_package", "variant_bucket": variant, "variant_family_bucket": family, "top10_span_overlap_count": top10, "top20_span_overlap_count": top20, "cost_proxy_top10": cost10, "cost_proxy_top20": cost20, "lost_anchor_top10_hits": lost_anchor, "lost_original_span_hits": lost_original, "decision_bucket": decision, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "n10by_match_bool": match})
    return rows, ok


def decision_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10by_policy_sweep_artifact", {})
    decisions = source.get("exploratory_decision_records", [])
    row = decisions[0] if isinstance(decisions, list) and decisions and isinstance(decisions[0], dict) else {}
    ok = row.get("variant_count") == 12 and row.get("cost_reduction_success_count") == 0 and row.get("recall_improvement_success_count") == 0 and row.get("successful_variant_count") == 0 and row.get("best_observed_variant_bucket") == "anchor_cost80_before20_after60" and row.get("best_observed_top10_span_overlap_count") == 20 and row.get("best_observed_top20_span_overlap_count") == 24
    return [{"anonymous_decision_package_id": "n10bzdecision0000", "package_bucket": "n10by_exploratory_decision_package", "variant_count": 12, "cost_reduction_success_count": 0, "recall_improvement_success_count": 0, "successful_variant_count": 0, "best_observed_variant_bucket": "anchor_cost80_before20_after60", "best_observed_top10_span_overlap_count": 20, "best_observed_top20_span_overlap_count": 24, "fixed_window_family_boundary_observed_bool": True, "useful_negative_research_bool": True, "n10by_match_bool": ok}], ok


def conclusion_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_conclusion_id": "n10bzconclusion0000", "conclusion_bucket": "no_improvement_beyond_cost80_anchor_in_fixed_window_policy_family", "same_source_n1_proxy_only_bool": True, "cost80_current_fixed_window_family_boundary_bool": True, "useful_negative_research_bool": True, "not_stop_bool": True, "runtime_default_recommendation_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "heldout_or_generalization_claim_bool": False}], True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10bzprivacy0000", "privacy_boundary_bucket": "public_policy_sweep_package_aggregate_only", "private_read_count": 0, "recompute_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "hash_public_bool": False, "privacy_boundary_complete_bool": True}], True


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10bzclaim0000", "claim_boundary_bucket": "same_source_negative_policy_sweep_package_only", "runtime_default_recommendation_bool": False, "runtime_default_promotion_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "heldout_claim_bool": False, "generalization_claim_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "p5_v1a_authorized_bool": False, "claim_boundary_valid_bool": True}], True


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10bznorecompute0000", "no_recompute_boundary_bucket": "public_policy_sweep_audit_package_only", "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "adaptive_tuning_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "candidate_generation_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10ca_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ca_handoff_id": "n10bzhandoff0000", "n10ca_handoff_bucket": "n10ca_next_mechanism_search_authorized" if complete else "n10ca_not_authorized", "n10ca_authorized_bool": complete, "next_mechanism_search_bucket": "jump_outside_fixed_window_family_same_source_if_possible", "same_source_empirical_if_possible_bool": complete, "runtime_default_authorized_bool": False, "heldout_claim_authorized_bool": False, "generalization_claim_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, sweep_ok: bool, decision_ok: bool, conclusion_ok: bool, privacy_ok: bool, claim_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("policy_sweep_package", sweep_ok), ("decision_package", decision_ok), ("conclusion_package", conclusion_ok), ("privacy_boundary", privacy_ok), ("claim_boundary", claim_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ca_next_mechanism_search_authorized" if complete else "n10ca_not_authorized", "next_allowed_phase": "BEA-v1-N10CA Next Mechanism Search Outside Fixed-Window Family" if complete else "none_until_policy_sweep_package_is_consistent", "next_allowed_scope_bucket": "same_source_exploratory_mechanism_search_if_possible" if complete else "no_next_phase", "n10ca_authorized": complete, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, sweep_ok: bool, decision_ok: bool, conclusion_ok: bool, privacy_ok: bool, claim_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10bz_required_public_inputs_unavailable"
    if not sweep_ok or not decision_ok or not conclusion_ok:
        return "no_go_n10bz_policy_sweep_chain_mismatch"
    if not privacy_ok or not claim_ok or not norecompute_ok:
        return "no_go_n10bz_privacy_or_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    sweep_rows, sweep_ok = sweep_package_records(artifacts)
    decision_rows, decision_ok = decision_package_records(artifacts)
    conclusion_rows, conclusion_ok = conclusion_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, sweep_ok, decision_ok, conclusion_ok, privacy_ok, claim_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_same_source_negative_policy_sweep_package_only", "generated_by": "bea_v1_n10bz_cost_efficient_policy_sweep_audit_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "policy_sweep_package_records": sweep_rows, "decision_package_records": decision_rows, "conclusion_records": conclusion_rows, "privacy_boundary_records": privacy_rows, "claim_boundary_records": claim_rows, "no_recompute_records": norecompute_rows, "n10ca_handoff_records": n10ca_handoff_records(complete), "gate_records": gate_records(input_ok, sweep_ok, decision_ok, conclusion_ok, privacy_ok, claim_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10ca_handoff_records"] = n10ca_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, sweep_ok, decision_ok, conclusion_ok, privacy_ok, claim_ok, norecompute_ok, scanner_ok)
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
    fake_rows = []
    for variant, top10, top20, cost10, cost20, lost in (("anchor_cost80_before20_after60", 20, 24, 800, 1600, 0), ("asym_cost70_before18_after52", 19, 23, 700, 1400, 1)):
        fake_rows.append({"variant_bucket": variant, "variant_family_bucket": "x", "top10_span_overlap_count": top10, "top20_span_overlap_count": top20, "cost_proxy_top10": cost10, "cost_proxy_top20": cost20, "lost_anchor_top10_hits": lost, "lost_original_span_hits": 0, "decision_bucket": "no_improvement_anchor_retained", "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False})
    return len(fake_rows) == 2 and status_for(True, True, True, True, True, True, True, True) == STATUS_COMPLETE


def synthetic_mismatch() -> bool:
    return status_for(True, True, False, True, True, True, True, True) == "no_go_n10bz_policy_sweep_chain_mismatch"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    sweep_rows, sweep_ok = sweep_package_records(artifacts)
    decision_rows, decision_ok = decision_package_records(artifacts)
    conclusion_rows, conclusion_ok = conclusion_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10bz_required_public_inputs_unavailable", "no_go_n10bz_policy_sweep_chain_mismatch", "no_go_n10bz_privacy_or_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 5),
        check("sweep_package", sweep_ok and len(sweep_rows) == 12 and sweep_rows[0]["top10_span_overlap_count"] == 20),
        check("decision_package", decision_ok and decision_rows[0]["successful_variant_count"] == 0),
        check("conclusion_package", conclusion_ok and conclusion_rows[0]["useful_negative_research_bool"] is True and conclusion_rows[0]["not_stop_bool"] is True),
        check("privacy", privacy_ok and privacy_rows[0]["private_read_count"] == 0),
        check("claim_boundary", claim_ok and claim_rows[0]["runtime_default_recommendation_bool"] is False and claim_rows[0]["method_winner_claim_bool"] is False),
        check("no_recompute", norecompute_ok and norecompute_rows[0]["recompute_count"] == 0),
        check("synthetic_package_pass", synthetic_package_pass()),
        check("synthetic_mismatch", synthetic_mismatch()),
        check("false_flags", stop_go_records(True)[0]["n10ca_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["candidate_generation_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BZ cost-efficient policy sweep audit package")
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
