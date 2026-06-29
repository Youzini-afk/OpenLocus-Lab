#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10br_cost_minimization_package.v1"
PHASE = "BEA-v1-N10BR Plateau Cost-Minimization Package"
STATUS_COMPLETE = "cost_minimization_package_complete_n10bs_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10br_required_public_inputs_unavailable",
    "no_go_n10br_cost_minimization_chain_mismatch",
    "no_go_n10br_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10br_cost_minimization_package/bea_v1_n10br_cost_minimization_package_report.json")
PUBLIC_INPUTS = {
    "n10bq_cost_minimization_sweep_artifact": (Path("artifacts/bea_v1_n10bq_plateau_cost_minimization_sweep/bea_v1_n10bq_plateau_cost_minimization_sweep_report.json"), "plateau_cost_minimization_sweep_complete_n10br_authorized"),
    "n10bp_plateau_mechanism_package_artifact": (Path("artifacts/bea_v1_n10bp_plateau_mechanism_package/bea_v1_n10bp_plateau_mechanism_package_report.json"), "plateau_mechanism_package_complete_n10bq_authorized"),
    "n10bo_plateau_decomposition_artifact": (Path("artifacts/bea_v1_n10bo_plateau_mechanism_decomposition/bea_v1_n10bo_plateau_mechanism_decomposition_report.json"), "plateau_mechanism_decomposition_complete_n10bp_authorized"),
}
EXPECTED_COSTS = (
    {"total_cost_proxy": 60, "best_top10": 19, "best_top20": 23, "preserved": 0, "cost_bucket": "low", "preserves": False},
    {"total_cost_proxy": 80, "best_top10": 20, "best_top20": 24, "preserved": 1, "cost_bucket": "medium_low", "preserves": True},
    {"total_cost_proxy": 100, "best_top10": 20, "best_top20": 24, "preserved": 5, "cost_bucket": "medium", "preserves": True},
    {"total_cost_proxy": 120, "best_top10": 20, "best_top20": 24, "preserved": 5, "cost_bucket": "medium_high", "preserves": True},
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
    "package_bucket", "cost_bucket", "variant_bucket", "chosen_research_operating_point_bucket", "claim_boundary_bucket",
    "no_recompute_boundary_bucket", "n10bs_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
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
        rows.append({"anonymous_input_artifact_id": f"n10brin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def cost_summary_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10bq_cost_minimization_sweep_artifact", {})
    observed = {row.get("total_cost_proxy"): row for row in source.get("cost_summary_records", []) if isinstance(row, dict)} if isinstance(source.get("cost_summary_records"), list) else {}
    variants = source.get("cost_minimization_variant_records", [])
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, expected in enumerate(EXPECTED_COSTS):
        cost = expected["total_cost_proxy"]
        row = observed.get(cost, {})
        cost_variants = [v for v in variants if isinstance(v, dict) and v.get("total_cost_proxy") == cost]
        lost_core_min = min((int(v.get("lost_plateau_core_top10_count", 999)) for v in cost_variants), default=999)
        matched = (
            row.get("best_top10_span_overlap_count") == expected["best_top10"]
            and row.get("best_top20_span_overlap_count") == expected["best_top20"]
            and row.get("preserved_variant_count") == expected["preserved"]
            and row.get("cost_level_preserves_plateau_bool") is expected["preserves"]
            and row.get("cost_bucket") == expected["cost_bucket"]
        )
        ok = ok and matched
        rows.append({"anonymous_cost_summary_package_id": f"n10brcost{idx:04d}", "package_bucket": "plateau_cost_minimization_by_cost", "total_cost_proxy": cost, "cost_bucket": expected["cost_bucket"], "best_top10_span_overlap_count": expected["best_top10"], "best_top20_span_overlap_count": expected["best_top20"], "preserved_variant_count": expected["preserved"], "cost_level_preserves_plateau_bool": expected["preserves"], "minimum_lost_plateau_core_top10_count": lost_core_min if lost_core_min != 999 else 0, "n10bq_match_bool": matched})
    return rows, ok


def selected_point_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10bq_cost_minimization_sweep_artifact", {})
    choices = source.get("chosen_research_operating_point_records", [])
    choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
    variants = source.get("cost_minimization_variant_records", [])
    selected = None
    if isinstance(variants, list):
        for row in variants:
            if isinstance(row, dict) and row.get("variant_bucket") == "cost80_before25_after75":
                selected = row
                break
    selected = selected or {}
    ok = (
        choice.get("minimum_cost_preserving_plateau") == 80
        and choice.get("chosen_research_operating_point_bucket") == "cost80_before25_after75"
        and choice.get("runtime_default_recommendation_bool") is False
        and choice.get("method_winner_claim_bool") is False
        and selected.get("top10_span_overlap_count") == 20
        and selected.get("top20_span_overlap_count") == 24
        and selected.get("lost_plateau_core_top10_count") == 0
        and selected.get("lost_pm50_top10_count") == 0
        and selected.get("plateau_preserved_bool") is True
    )
    return [{"anonymous_selected_point_package_id": "n10brchoice0000", "chosen_research_operating_point_bucket": "cost80_before25_after75", "minimum_cost_preserving_plateau": 80, "top10_span_overlap_count": 20, "top20_span_overlap_count": 24, "lost_plateau_core_top10_count": 0, "lost_pm50_top10_count": 0, "plateau_preserved_bool": True, "runtime_default_recommendation_bool": False, "method_winner_claim_bool": False, "n10bq_match_bool": ok}], ok


def grid_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10bq_cost_minimization_sweep_artifact", {})
    variants = source.get("cost_minimization_variant_records", [])
    if not isinstance(variants, list):
        variants = []
    ratio_set = sorted({str(row.get("ratio_bucket")) for row in variants if isinstance(row, dict)})
    cost_values: set[int] = set()
    for row in variants:
        if isinstance(row, dict):
            value = row.get("total_cost_proxy")
            if isinstance(value, int):
                cost_values.add(value)
    cost_set = sorted(cost_values)
    ok = len(variants) == 20 and ratio_set == ["before20_after80", "before25_after75", "before30_after70", "before35_after65", "before40_after60"] and cost_set == [60, 80, 100, 120]
    return [{"anonymous_grid_package_id": "n10brgrid0000", "package_bucket": "twenty_predeclared_ratio_cost_variants", "variant_count": 20, "ratio_count": 5, "cost_count": 4, "cost60_present_bool": 60 in cost_set, "cost80_present_bool": 80 in cost_set, "cost100_present_bool": 100 in cost_set, "cost120_present_bool": 120 in cost_set, "all_variants_predeclared_bool": ok, "n10bq_match_bool": ok}], ok


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10brclaim0000", "claim_boundary_bucket": "public_cost_minimization_package_only", "private_read_count": 0, "recompute_count": 0, "runtime_default_recommendation_bool": False, "runtime_default_promotion_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "heldout_claim_bool": False, "generalization_claim_bool": False, "new_variant_count": 0, "adaptive_tuning_count": 0, "claim_boundary_valid_bool": True}], True


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10brnorecompute0000", "no_recompute_boundary_bucket": "public_cost_minimization_package_only", "private_read_count": 0, "recompute_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "candidate_generation_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10bs_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10bs_handoff_id": "n10brhandoff0000", "n10bs_handoff_bucket": "n10bs_boundary_cost_refinement_sweep_authorized" if complete else "n10bs_not_authorized", "n10bs_authorized_bool": complete, "same_scoped_n1_rows_authorized_bool": complete, "fixed_ratio_25_75_only_bool": complete, "predeclared_total_cost_count": 7 if complete else 0, "public_aggregate_only_bool": True, "private_read_beyond_same_scoped_rows_authorized_bool": False, "new_ratio_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "runtime_default_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_claim_authorized_bool": False}]


def gate_records(input_ok: bool, grid_ok: bool, cost_ok: bool, selected_ok: bool, claim_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("predeclared_grid_packaged", grid_ok), ("cost_summary_packaged", cost_ok), ("selected_research_point_packaged", selected_ok), ("claim_boundary", claim_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10bs_boundary_cost_refinement_sweep_authorized" if complete else "n10bs_not_authorized", "next_allowed_phase": "BEA-v1-N10BS Boundary-Cost Refinement Sweep" if complete else "none_until_cost_minimization_package_is_consistent", "next_allowed_scope_bucket": "same_scoped_rows_fixed_ratio_25_75_cost_boundary_sweep" if complete else "no_next_phase", "n10bs_authorized": complete, "private_read_beyond_same_scoped_rows_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "new_ratio_authorized": False, "adaptive_tuning_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, grid_ok: bool, cost_ok: bool, selected_ok: bool, claim_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10br_required_public_inputs_unavailable"
    if not grid_ok or not cost_ok or not selected_ok:
        return "no_go_n10br_cost_minimization_chain_mismatch"
    if not claim_ok or not norecompute_ok:
        return "no_go_n10br_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    grid_rows, grid_ok = grid_package_records(artifacts)
    cost_rows, cost_ok = cost_summary_package_records(artifacts)
    selected_rows, selected_ok = selected_point_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, grid_ok, cost_ok, selected_ok, claim_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_cost_minimization_package_only", "generated_by": "bea_v1_n10br_cost_minimization_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "grid_package_records": grid_rows, "cost_summary_package_records": cost_rows, "selected_research_operating_point_records": selected_rows, "claim_boundary_records": claim_rows, "no_recompute_records": norecompute_rows, "n10bs_handoff_records": n10bs_handoff_records(complete), "gate_records": gate_records(input_ok, grid_ok, cost_ok, selected_ok, claim_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10bs_handoff_records"] = n10bs_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, grid_ok, cost_ok, selected_ok, claim_ok, norecompute_ok, scanner_ok)
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
    fake_variants = []
    for cost in (60, 80, 100, 120):
        for ratio in ("before20_after80", "before25_after75", "before30_after70", "before35_after65", "before40_after60"):
            fake_variants.append({"total_cost_proxy": cost, "ratio_bucket": ratio, "variant_bucket": f"cost{cost}_{ratio}", "top10_span_overlap_count": 20 if cost >= 80 else 19, "top20_span_overlap_count": 24 if cost >= 80 else 23, "lost_plateau_core_top10_count": 0 if cost >= 80 and (cost != 80 or ratio == "before25_after75") else 1, "lost_pm50_top10_count": 0, "plateau_preserved_bool": cost >= 100 or (cost == 80 and ratio == "before25_after75")})
    fake_costs = [{"total_cost_proxy": e["total_cost_proxy"], "best_top10_span_overlap_count": e["best_top10"], "best_top20_span_overlap_count": e["best_top20"], "preserved_variant_count": e["preserved"], "cost_level_preserves_plateau_bool": e["preserves"], "cost_bucket": e["cost_bucket"]} for e in EXPECTED_COSTS]
    fake = {"n10bq_cost_minimization_sweep_artifact": {"cost_minimization_variant_records": fake_variants, "cost_summary_records": fake_costs, "chosen_research_operating_point_records": [{"minimum_cost_preserving_plateau": 80, "chosen_research_operating_point_bucket": "cost80_before25_after75", "runtime_default_recommendation_bool": False, "method_winner_claim_bool": False}]}}
    return grid_package_records(fake)[1] and cost_summary_package_records(fake)[1] and selected_point_records(fake)[1]


def synthetic_mismatch() -> bool:
    fake = {"n10bq_cost_minimization_sweep_artifact": {"cost_summary_records": []}}
    return not cost_summary_package_records(fake)[1] and status_for(True, True, True, False, True, True, True) == "no_go_n10br_cost_minimization_chain_mismatch"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    grid_rows, grid_ok = grid_package_records(artifacts)
    cost_rows, cost_ok = cost_summary_package_records(artifacts)
    selected_rows, selected_ok = selected_point_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10br_required_public_inputs_unavailable", "no_go_n10br_cost_minimization_chain_mismatch", "no_go_n10br_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 3),
        check("grid", grid_ok and grid_rows[0]["variant_count"] == 20),
        check("cost_summary", cost_ok and len(cost_rows) == 4 and cost_rows[0]["preserved_variant_count"] == 0 and cost_rows[1]["preserved_variant_count"] == 1),
        check("selected_point", selected_ok and selected_rows[0]["chosen_research_operating_point_bucket"] == "cost80_before25_after75" and selected_rows[0]["runtime_default_recommendation_bool"] is False),
        check("claim_boundary", claim_ok and claim_rows[0]["runtime_default_recommendation_bool"] is False and claim_rows[0]["method_winner_claim_bool"] is False),
        check("no_private_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["recompute_count"] == 0),
        check("synthetic_package_pass", synthetic_package_pass()),
        check("synthetic_mismatch", synthetic_mismatch()),
        check("false_flags", stop_go_records(True)[0]["n10bs_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["new_ratio_authorized"] is False),
        check("status_complete", status_for(True, True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BR cost minimization package")
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
