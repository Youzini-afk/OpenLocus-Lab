#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10bt_boundary_cost_package.v1"
PHASE = "BEA-v1-N10BT Boundary-Cost Package"
STATUS_COMPLETE = "boundary_cost_package_complete_n10bu_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10bt_required_public_inputs_unavailable",
    "no_go_n10bt_boundary_chain_mismatch",
    "no_go_n10bt_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10bt_boundary_cost_package/bea_v1_n10bt_boundary_cost_package_report.json")
PUBLIC_INPUTS = {
    "n10bs_boundary_cost_refinement_artifact": (Path("artifacts/bea_v1_n10bs_boundary_cost_refinement_sweep/bea_v1_n10bs_boundary_cost_refinement_sweep_report.json"), "boundary_cost_refinement_sweep_complete_n10bt_authorized"),
    "n10br_cost_minimization_package_artifact": (Path("artifacts/bea_v1_n10br_cost_minimization_package/bea_v1_n10br_cost_minimization_package_report.json"), "cost_minimization_package_complete_n10bs_authorized"),
    "n10bq_cost_minimization_sweep_artifact": (Path("artifacts/bea_v1_n10bq_plateau_cost_minimization_sweep/bea_v1_n10bq_plateau_cost_minimization_sweep_report.json"), "plateau_cost_minimization_sweep_complete_n10br_authorized"),
}
EXPECTED_VARIANTS = (
    (65, 19, 22, 1, False),
    (70, 19, 22, 1, False),
    (75, 19, 23, 1, False),
    (80, 20, 24, 0, True),
    (85, 20, 24, 0, True),
    (90, 20, 24, 0, True),
    (95, 20, 24, 0, True),
)
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
    "package_bucket", "variant_bucket", "ratio_bucket", "cost_bucket", "summary_bucket", "margin_bucket", "monotonicity_bucket",
    "chosen_research_operating_point_bucket", "claim_boundary_bucket", "no_recompute_boundary_bucket", "n10bu_handoff_bucket",
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
        rows.append({"anonymous_input_artifact_id": f"n10btin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def boundary_cost_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10bs_boundary_cost_refinement_artifact", {})
    observed = {row.get("total_cost_proxy"): row for row in source.get("boundary_cost_variant_records", []) if isinstance(row, dict)} if isinstance(source.get("boundary_cost_variant_records"), list) else {}
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (cost, top10, top20, lost_core, preserved) in enumerate(EXPECTED_VARIANTS):
        row = observed.get(cost, {})
        matched = row.get("top10_span_overlap_count") == top10 and row.get("top20_span_overlap_count") == top20 and row.get("lost_plateau_core_top10_count") == lost_core and row.get("preserved_plateau_bool") is preserved and row.get("ratio_bucket") == "before25_after75"
        ok = ok and matched
        rows.append({"anonymous_boundary_cost_package_id": f"n10btcost{idx:04d}", "package_bucket": "fixed_25_75_boundary_cost_variant", "variant_bucket": f"cost{cost}_before25_after75", "ratio_bucket": "before25_after75", "total_cost_proxy": cost, "top10_span_overlap_count": top10, "top20_span_overlap_count": top20, "lost_plateau_core_top10_count": lost_core, "lost_pm50_top10_count": int(row.get("lost_pm50_top10_count", 0)) if isinstance(row.get("lost_pm50_top10_count", 0), int) else 0, "preserved_plateau_bool": preserved, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "n10bs_match_bool": matched})
    return rows, ok


def boundary_summary_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10bs_boundary_cost_refinement_artifact", {})
    summaries = source.get("boundary_summary_records", [])
    summary = summaries[0] if isinstance(summaries, list) and summaries and isinstance(summaries[0], dict) else {}
    ok = summary.get("minimum_preserving_cost_proxy") == 80 and summary.get("first_failing_below_boundary_cost_proxy") == 75 and summary.get("boundary_margin_cost_proxy") == 5 and summary.get("monotonicity_bucket") == "nondecreasing_top10"
    return [{"anonymous_boundary_summary_package_id": "n10btsummary0000", "summary_bucket": "fixed_25_75_boundary_cost_summary", "minimum_preserving_cost_proxy": 80, "first_failing_below_boundary_cost_proxy": 75, "boundary_margin_cost_proxy": 5, "margin_bucket": "narrow_boundary", "monotonicity_bucket": "nondecreasing_top10", "cost65_preserves_plateau_bool": False, "cost70_preserves_plateau_bool": False, "cost75_preserves_plateau_bool": False, "cost80_preserves_plateau_bool": True, "n10bs_match_bool": ok}], ok


def chosen_point_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10bs_boundary_cost_refinement_artifact", {})
    choices = source.get("chosen_research_operating_point_records", [])
    choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
    ok = choice.get("chosen_research_operating_point_bucket") == "cost80_before25_after75" and choice.get("minimum_cost_preserving_plateau") == 80 and choice.get("runtime_default_recommendation_bool") is False and choice.get("method_winner_claim_bool") is False
    return [{"anonymous_chosen_research_point_package_id": "n10btchoice0000", "chosen_research_operating_point_bucket": "cost80_before25_after75", "minimum_cost_preserving_plateau": 80, "runtime_default_recommendation_bool": False, "method_winner_claim_bool": False, "n10bs_match_bool": ok}], ok


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10btclaim0000", "claim_boundary_bucket": "public_boundary_cost_package_only", "private_read_count": 0, "recompute_count": 0, "runtime_default_recommendation_bool": False, "runtime_default_promotion_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "heldout_claim_bool": False, "generalization_claim_bool": False, "new_variant_count": 0, "new_ratio_count": 0, "adaptive_tuning_count": 0, "claim_boundary_valid_bool": True}], True


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10btnorecompute0000", "no_recompute_boundary_bucket": "public_boundary_cost_package_only", "private_read_count": 0, "recompute_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "candidate_generation_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10bu_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10bu_handoff_id": "n10bthandoff0000", "n10bu_handoff_bucket": "n10bu_boundary_case_mechanism_decomposition_authorized" if complete else "n10bu_not_authorized", "n10bu_authorized_bool": complete, "same_scoped_n1_rows_authorized_bool": complete, "compare_cost75_and_cost80_only_bool": complete, "public_aggregate_only_bool": True, "private_read_beyond_same_scoped_rows_authorized_bool": False, "new_variant_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "runtime_default_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_claim_authorized_bool": False}]


def gate_records(input_ok: bool, variant_ok: bool, summary_ok: bool, choice_ok: bool, claim_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("boundary_variant_package", variant_ok), ("boundary_summary_package", summary_ok), ("chosen_point_boundary", choice_ok), ("claim_boundary", claim_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10bu_boundary_case_mechanism_decomposition_authorized" if complete else "n10bu_not_authorized", "next_allowed_phase": "BEA-v1-N10BU Boundary Case Mechanism Decomposition" if complete else "none_until_boundary_cost_package_is_consistent", "next_allowed_scope_bucket": "same_scoped_rows_cost75_vs_cost80_boundary_case_decomposition" if complete else "no_next_phase", "n10bu_authorized": complete, "private_read_beyond_same_scoped_rows_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "new_variant_authorized": False, "adaptive_tuning_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, variant_ok: bool, summary_ok: bool, choice_ok: bool, claim_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10bt_required_public_inputs_unavailable"
    if not variant_ok or not summary_ok or not choice_ok:
        return "no_go_n10bt_boundary_chain_mismatch"
    if not claim_ok or not norecompute_ok:
        return "no_go_n10bt_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    variant_rows, variant_ok = boundary_cost_package_records(artifacts)
    summary_rows, summary_ok = boundary_summary_package_records(artifacts)
    choice_rows, choice_ok = chosen_point_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, variant_ok, summary_ok, choice_ok, claim_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_boundary_cost_package_only", "generated_by": "bea_v1_n10bt_boundary_cost_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "boundary_cost_package_records": variant_rows, "boundary_summary_package_records": summary_rows, "chosen_research_operating_point_records": choice_rows, "claim_boundary_records": claim_rows, "no_recompute_records": norecompute_rows, "n10bu_handoff_records": n10bu_handoff_records(complete), "gate_records": gate_records(input_ok, variant_ok, summary_ok, choice_ok, claim_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10bu_handoff_records"] = n10bu_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, variant_ok, summary_ok, choice_ok, claim_ok, norecompute_ok, scanner_ok)
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
    fake = {"n10bs_boundary_cost_refinement_artifact": {"boundary_cost_variant_records": [{"total_cost_proxy": c, "top10_span_overlap_count": t10, "top20_span_overlap_count": t20, "lost_plateau_core_top10_count": lost, "lost_pm50_top10_count": 0, "preserved_plateau_bool": pres, "ratio_bucket": "before25_after75"} for c, t10, t20, lost, pres in EXPECTED_VARIANTS], "boundary_summary_records": [{"minimum_preserving_cost_proxy": 80, "first_failing_below_boundary_cost_proxy": 75, "boundary_margin_cost_proxy": 5, "monotonicity_bucket": "nondecreasing_top10"}], "chosen_research_operating_point_records": [{"chosen_research_operating_point_bucket": "cost80_before25_after75", "minimum_cost_preserving_plateau": 80, "runtime_default_recommendation_bool": False, "method_winner_claim_bool": False}]}}
    return boundary_cost_package_records(fake)[1] and boundary_summary_package_records(fake)[1] and chosen_point_records(fake)[1]


def synthetic_mismatch() -> bool:
    fake = {"n10bs_boundary_cost_refinement_artifact": {"boundary_cost_variant_records": []}}
    return not boundary_cost_package_records(fake)[1] and status_for(True, True, False, True, True, True, True) == "no_go_n10bt_boundary_chain_mismatch"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    variant_rows, variant_ok = boundary_cost_package_records(artifacts)
    summary_rows, summary_ok = boundary_summary_package_records(artifacts)
    choice_rows, choice_ok = chosen_point_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10bt_required_public_inputs_unavailable", "no_go_n10bt_boundary_chain_mismatch", "no_go_n10bt_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 3),
        check("variant_package", variant_ok and len(variant_rows) == 7 and variant_rows[0]["total_cost_proxy"] == 65 and variant_rows[-1]["total_cost_proxy"] == 95),
        check("summary_package", summary_ok and summary_rows[0]["minimum_preserving_cost_proxy"] == 80 and summary_rows[0]["boundary_margin_cost_proxy"] == 5),
        check("chosen_point", choice_ok and choice_rows[0]["runtime_default_recommendation_bool"] is False and choice_rows[0]["method_winner_claim_bool"] is False),
        check("claim_boundary", claim_ok and claim_rows[0]["runtime_default_recommendation_bool"] is False and claim_rows[0]["new_variant_count"] == 0),
        check("no_private_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["recompute_count"] == 0),
        check("synthetic_package_pass", synthetic_package_pass()),
        check("synthetic_mismatch", synthetic_mismatch()),
        check("false_flags", stop_go_records(True)[0]["n10bu_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["new_variant_authorized"] is False),
        check("status_complete", status_for(True, True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BT boundary-cost package")
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
