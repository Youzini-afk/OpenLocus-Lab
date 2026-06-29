#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10bh_pm50_comparator_package.v1"
PHASE = "BEA-v1-N10BH Cost-Aware Decisions vs Fixed-pm50 Comparator Audit Package"
STATUS_COMPLETE = "pm50_comparator_package_complete_n10bi_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10bh_required_public_inputs_unavailable",
    "no_go_n10bh_comparator_chain_mismatch",
    "no_go_n10bh_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10bh_pm50_comparator_package/bea_v1_n10bh_pm50_comparator_package_report.json")
PUBLIC_INPUTS = {
    "n10bg_pm50_comparator_artifact": (Path("artifacts/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator_report.json"), "cost_aware_decisions_vs_fixed_pm50_comparator_complete_n10bh_authorized"),
    "n10bf_budget_decision_package_artifact": (Path("artifacts/bea_v1_n10bf_cost_aware_budget_decision_package/bea_v1_n10bf_cost_aware_budget_decision_package_report.json"), "cost_aware_budget_decision_package_complete_n10bg_authorized"),
    "n10be_budget_decision_smoke_artifact": (Path("artifacts/bea_v1_n10be_cost_aware_operating_point_decision_smoke/bea_v1_n10be_cost_aware_operating_point_decision_smoke_report.json"), "cost_aware_operating_point_decision_smoke_complete_n10bf_authorized"),
    "n10as_exploratory_sweep_artifact": (Path("artifacts/bea_v1_n10as_exploratory_span_window_variant_sweep/bea_v1_n10as_exploratory_span_window_variant_sweep_report.json"), "exploratory_span_window_variant_sweep_complete_n10at_authorized"),
}
EXPECTED_COMPARATOR = {"variant_bucket": "pm50", "top10": 19, "top20": 23, "cost": 1000, "cost_bucket": "medium"}
EXPECTED_DECISIONS = {
    "strict_budget": {"op": "low_cost", "variant": "pm30", "top10": 18, "top20": 22, "delta10": -1, "delta20": -1, "cost_delta": -400, "cost": 600, "cost_bucket": "low", "lost": 1, "dominance": "cost_saving_tradeoff_vs_pm50"},
    "moderate_budget": {"op": "balanced", "variant": "before25_after75", "top10": 20, "top20": 24, "delta10": 1, "delta20": 1, "cost_delta": 0, "cost": 1000, "cost_bucket": "medium", "lost": 0, "dominance": "dominates_pm50"},
    "recall_budget": {"op": "max_recall", "variant": "pm200", "top10": 25, "top20": 30, "delta10": 6, "delta20": 7, "cost_delta": 3000, "cost": 4000, "cost_bucket": "very_high", "lost": 0, "dominance": "higher_recall_higher_cost_vs_pm50"},
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
    "comparator_bucket", "budget_bucket", "operating_point_bucket", "variant_bucket", "cost_bucket", "dominance_bucket",
    "claim_boundary_bucket", "no_recompute_boundary_bucket", "n10bi_handoff_bucket", "authorization", "next_allowed_phase",
    "next_allowed_scope_bucket", "gate", "threshold_relation",
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
        rows.append({"anonymous_input_artifact_id": f"n10bhin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def by_key(rows: Any, key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get(key), str):
                out[row[key]] = row
    return out


def comparator_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    src_rows = artifacts.get("n10bg_pm50_comparator_artifact", {}).get("fixed_pm50_comparator_records", [])
    src = src_rows[0] if isinstance(src_rows, list) and src_rows and isinstance(src_rows[0], dict) else {}
    ok = src.get("variant_bucket") == EXPECTED_COMPARATOR["variant_bucket"] and src.get("top10_span_overlap_count") == EXPECTED_COMPARATOR["top10"] and src.get("top20_span_overlap_count") == EXPECTED_COMPARATOR["top20"] and src.get("cost_proxy_value") == EXPECTED_COMPARATOR["cost"] and src.get("cost_bucket") == EXPECTED_COMPARATOR["cost_bucket"]
    return [{"anonymous_comparator_package_id": "n10bhcomp0000", "comparator_bucket": "fixed_pm50", "variant_bucket": "pm50", "top10_span_overlap_count": 19, "top20_span_overlap_count": 23, "cost_proxy_value": 1000, "cost_bucket": "medium", "n10bg_match_bool": ok}], ok


def decision_vs_pm50_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = by_key(artifacts.get("n10bg_pm50_comparator_artifact", {}).get("decision_vs_pm50_records", []), "budget_bucket")
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (budget, expected) in enumerate(EXPECTED_DECISIONS.items()):
        src = source.get(budget, {})
        matched = src.get("operating_point_bucket") == expected["op"] and src.get("variant_bucket") == expected["variant"] and src.get("top10_span_overlap_count") == expected["top10"] and src.get("top20_span_overlap_count") == expected["top20"] and src.get("delta_vs_pm50_top10_count") == expected["delta10"] and src.get("delta_vs_pm50_top20_count") == expected["delta20"] and src.get("cost_proxy_delta_vs_pm50") == expected["cost_delta"] and src.get("cost_proxy_value") == expected["cost"] and src.get("cost_bucket") == expected["cost_bucket"] and src.get("lost_original_span_hits") == expected["lost"] and src.get("dominance_bucket") == expected["dominance"] and src.get("candidate_pool_changed_bool") is False and src.get("candidate_order_changed_bool") is False
        ok = ok and matched
        rows.append({"anonymous_decision_vs_pm50_package_id": f"n10bhdecision{idx:04d}", "budget_bucket": budget, "operating_point_bucket": expected["op"], "variant_bucket": expected["variant"], "top10_span_overlap_count": expected["top10"], "top20_span_overlap_count": expected["top20"], "delta_vs_pm50_top10_count": expected["delta10"], "delta_vs_pm50_top20_count": expected["delta20"], "cost_proxy_delta_vs_pm50": expected["cost_delta"], "cost_proxy_value": expected["cost"], "cost_bucket": expected["cost_bucket"], "lost_original_span_hits": expected["lost"], "dominance_bucket": expected["dominance"], "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "n10bg_match_bool": matched})
    return rows, ok


def claim_boundary_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10bg_pm50_comparator_artifact", {}).get("claim_boundary_records", [])
    row = source[0] if isinstance(source, list) and source and isinstance(source[0], dict) else {}
    ok = row.get("runtime_default_recommendation_bool") is False and row.get("runtime_default_promotion_bool") is False and row.get("new_variant_count") == 0 and row.get("adaptive_selection_count") == 0 and row.get("heldout_claim_bool") is False and row.get("generalization_claim_bool") is False and row.get("method_winner_claim_bool") is False and row.get("downstream_value_claim_bool") is False
    return [{"anonymous_claim_boundary_id": "n10bhclaim0000", "claim_boundary_bucket": "public_pm50_comparator_package_only", "public_bucket_count_only_bool": True, "private_row_read_count": 0, "recompute_count": 0, "runtime_default_recommendation_bool": False, "runtime_default_promotion_bool": False, "new_variant_count": 0, "adaptive_selection_count": 0, "heldout_claim_bool": False, "generalization_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "claim_boundary_valid_bool": ok}], ok


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10bhnorecompute0000", "no_recompute_boundary_bucket": "public_pm50_comparator_package_only", "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "adaptive_selection_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "runtime_default_change_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10bi_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10bi_handoff_id": "n10bhhandoff0000", "n10bi_handoff_bucket": "n10bi_asymmetric_window_direction_mechanism_decomposition_authorized" if complete else "n10bi_not_authorized", "n10bi_authorized_bool": complete, "same_scoped_n1_rows_authorized_bool": complete, "compare_pm50_vs_before25_after75_bool": complete, "private_read_authorized_bool": complete, "new_variant_authorized_bool": False, "adaptive_selection_authorized_bool": False, "gold_direction_for_per_record_choice_authorized_bool": False, "runtime_default_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_claim_authorized_bool": False}]


def gate_records(input_ok: bool, comp_ok: bool, decisions_ok: bool, claim_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("fixed_pm50_comparator_package", comp_ok), ("decision_vs_pm50_package", decisions_ok), ("claim_boundary", claim_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10bi_asymmetric_window_direction_mechanism_decomposition_authorized" if complete else "n10bi_not_authorized", "next_allowed_phase": "BEA-v1-N10BI Asymmetric Window Direction Mechanism Decomposition" if complete else "none_until_pm50_comparator_package_is_consistent", "next_allowed_scope_bucket": "same_scoped_rows_pm50_vs_before25_after75_direction_decomposition" if complete else "no_next_phase", "n10bi_authorized": complete, "private_read_beyond_same_scoped_rows_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "new_variant_authorized": False, "adaptive_selection_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, comp_ok: bool, decisions_ok: bool, claim_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10bh_required_public_inputs_unavailable"
    if not comp_ok or not decisions_ok:
        return "no_go_n10bh_comparator_chain_mismatch"
    if not claim_ok or not norecompute_ok:
        return "no_go_n10bh_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    comp_rows, comp_ok = comparator_package_records(artifacts)
    decision_rows, decisions_ok = decision_vs_pm50_package_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records(artifacts)
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, comp_ok, decisions_ok, claim_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_pm50_comparator_package_only", "generated_by": "bea_v1_n10bh_pm50_comparator_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "fixed_pm50_comparator_package_records": comp_rows, "decision_vs_pm50_package_records": decision_rows, "claim_boundary_records": claim_rows, "no_recompute_records": norecompute_rows, "n10bi_handoff_records": n10bi_handoff_records(complete), "gate_records": gate_records(input_ok, comp_ok, decisions_ok, claim_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10bi_handoff_records"] = n10bi_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, comp_ok, decisions_ok, claim_ok, norecompute_ok, scanner_ok)
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
    fake = {"n10bg_pm50_comparator_artifact": {"fixed_pm50_comparator_records": [{"variant_bucket": "pm50", "top10_span_overlap_count": 19, "top20_span_overlap_count": 23, "cost_proxy_value": 1000, "cost_bucket": "medium"}], "decision_vs_pm50_records": [{"budget_bucket": k, "operating_point_bucket": v["op"], "variant_bucket": v["variant"], "top10_span_overlap_count": v["top10"], "top20_span_overlap_count": v["top20"], "delta_vs_pm50_top10_count": v["delta10"], "delta_vs_pm50_top20_count": v["delta20"], "cost_proxy_delta_vs_pm50": v["cost_delta"], "cost_proxy_value": v["cost"], "cost_bucket": v["cost_bucket"], "lost_original_span_hits": v["lost"], "dominance_bucket": v["dominance"], "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False} for k, v in EXPECTED_DECISIONS.items()], "claim_boundary_records": [{"runtime_default_recommendation_bool": False, "runtime_default_promotion_bool": False, "new_variant_count": 0, "adaptive_selection_count": 0, "heldout_claim_bool": False, "generalization_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False}]}}
    return comparator_package_records(fake)[1] and decision_vs_pm50_package_records(fake)[1] and claim_boundary_records(fake)[1]


def synthetic_mismatch() -> bool:
    fake = {"n10bg_pm50_comparator_artifact": {"fixed_pm50_comparator_records": []}}
    _rows, ok = comparator_package_records(fake)
    return not ok and status_for(True, True, ok, True, True, True) == "no_go_n10bh_comparator_chain_mismatch"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    comp_rows, comp_ok = comparator_package_records(artifacts)
    decision_rows, decisions_ok = decision_vs_pm50_package_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records(artifacts)
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10bh_required_public_inputs_unavailable", "no_go_n10bh_comparator_chain_mismatch", "no_go_n10bh_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 4),
        check("pm50_comparator", comp_ok and comp_rows[0]["top10_span_overlap_count"] == 19 and comp_rows[0]["top20_span_overlap_count"] == 23),
        check("decision_package", decisions_ok and len(decision_rows) == 3 and [r["dominance_bucket"] for r in decision_rows] == ["cost_saving_tradeoff_vs_pm50", "dominates_pm50", "higher_recall_higher_cost_vs_pm50"]),
        check("claim_boundary", claim_ok and claim_rows[0]["runtime_default_recommendation_bool"] is False and claim_rows[0]["method_winner_claim_bool"] is False),
        check("no_private_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["recompute_count"] == 0),
        check("synthetic_package_pass", synthetic_package_pass()),
        check("synthetic_mismatch", synthetic_mismatch()),
        check("false_flags", stop_go_records(True)[0]["n10bi_authorized"] is True and stop_go_records(True)[0]["new_variant_authorized"] is False and stop_go_records(True)[0]["runtime_or_default_authorized"] is False),
        check("status_complete", status_for(True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BH pm50 comparator package")
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
