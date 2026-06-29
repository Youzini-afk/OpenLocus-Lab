#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10bn_local_refinement_package.v1"
PHASE = "BEA-v1-N10BN After-Heavy Local Asymmetry Refinement Package"
STATUS_COMPLETE = "local_refinement_package_complete_n10bo_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10bn_required_public_inputs_unavailable",
    "no_go_n10bn_local_refinement_chain_mismatch",
    "no_go_n10bn_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10bn_local_refinement_package/bea_v1_n10bn_local_refinement_package_report.json")
PUBLIC_INPUTS = {
    "n10bm_local_refinement_artifact": (Path("artifacts/bea_v1_n10bm_after_heavy_local_asymmetry_refinement/bea_v1_n10bm_after_heavy_local_asymmetry_refinement_report.json"), "after_heavy_local_asymmetry_refinement_complete_n10bn_authorized"),
    "n10bl_direction_sensitivity_package_artifact": (Path("artifacts/bea_v1_n10bl_direction_sensitivity_package/bea_v1_n10bl_direction_sensitivity_package_report.json"), "direction_sensitivity_package_complete_n10bm_authorized"),
    "n10bk_neighboring_asymmetry_micro_sweep_artifact": (Path("artifacts/bea_v1_n10bk_neighboring_asymmetry_micro_sweep/bea_v1_n10bk_neighboring_asymmetry_micro_sweep_report.json"), "neighboring_asymmetry_micro_sweep_complete_n10bl_authorized"),
    "n10bj_asymmetry_mechanism_package_artifact": (Path("artifacts/bea_v1_n10bj_asymmetric_window_mechanism_package/bea_v1_n10bj_asymmetric_window_mechanism_package_report.json"), "asymmetric_window_mechanism_package_complete_n10bk_authorized"),
}
EXPECTED_VARIANTS = (
    ("before10_after90", 20, 23, False),
    ("before15_after85", 20, 23, False),
    ("before20_after80", 20, 24, True),
    ("before25_after75", 20, 24, True),
    ("before30_after70", 20, 24, True),
    ("before35_after65", 20, 24, True),
    ("before40_after60", 20, 24, True),
)
PLATEAU_VARIANTS = (
    "before20_after80",
    "before25_after75",
    "before30_after70",
    "before35_after65",
    "before40_after60",
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
    "variant_bucket", "package_bucket", "winner_rule_bucket", "plateau_bucket", "conclusion_bucket", "claim_boundary_bucket",
    "no_recompute_boundary_bucket", "n10bo_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
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
        rows.append({"anonymous_input_artifact_id": f"n10bnin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def by_variant(rows: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("variant_bucket"), str):
                out[row["variant_bucket"]] = row
    return out


def package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10bm_local_refinement_artifact", {})
    observed = by_variant(source.get("local_refinement_result_records", []))
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (name, top10, top20, winner) in enumerate(EXPECTED_VARIANTS):
        row = observed.get(name, {})
        matched = (
            row.get("top10_span_overlap_count") == top10
            and row.get("top20_span_overlap_count") == top20
            and row.get("winner_bool") is winner
            and row.get("total_window_cost_proxy") == 100
            and row.get("candidate_pool_changed_bool") is False
            and row.get("candidate_order_changed_bool") is False
            and row.get("lost_before25_after75_top10_hits_count") == 0
            and row.get("lost_pm50_top10_hits_count") == 0
        )
        ok = ok and matched
        rows.append({"anonymous_local_refinement_package_id": f"n10bnvar{idx:04d}", "package_bucket": "after_heavy_local_refinement_fixed_cost_100", "variant_bucket": name, "top10_span_overlap_count": top10, "top20_span_overlap_count": top20, "total_window_cost_proxy": 100, "winner_bool": winner, "plateau_member_bool": name in PLATEAU_VARIANTS, "lost_before25_after75_top10_hits_count": 0, "lost_pm50_top10_hits_count": 0, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "n10bm_match_bool": matched})
    return rows, ok


def winner_rule_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10bm_local_refinement_artifact", {})
    local_rows = source.get("local_optimum_records", [])
    observed = local_rows[0] if isinstance(local_rows, list) and local_rows and isinstance(local_rows[0], dict) else {}
    ok = (
        observed.get("before25_after75_top10_span_overlap_count") == 20
        and observed.get("before25_after75_top20_span_overlap_count") == 24
        and observed.get("max_top10_span_overlap_count") == 20
        and observed.get("max_top20_span_overlap_count") == 24
        and observed.get("candidate_pool_changed_count") == 0
        and observed.get("candidate_order_changed_count") == 0
    )
    return [{"anonymous_winner_rule_id": "n10bnrule0000", "winner_rule_bucket": "top10_primary_top20_tiebreak", "top10_primary_metric_bool": True, "top20_tiebreak_metric_bool": True, "fixed_total_cost_proxy": 100, "winner_count": 5, "winner_rule_applied_bool": True, "n10bm_match_bool": ok}], ok


def plateau_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10bm_local_refinement_artifact", {})
    observed_rows = source.get("local_optimum_records", [])
    observed = observed_rows[0] if isinstance(observed_rows, list) and observed_rows and isinstance(observed_rows[0], dict) else {}
    ok = observed.get("local_optimum_bucket") == "before25_after75_local_optimum_plateau_member" and observed.get("plateau_tie_bucket") == "multiple_equal_winners" and observed.get("winner_count") == 5 and observed.get("fixed_total_cost_bool") is True
    return [{"anonymous_plateau_conclusion_id": "n10bnplateau0000", "plateau_bucket": "before20_after80_through_before40_after60", "conclusion_bucket": "before25_after75_is_plateau_member_not_unique_magic_value", "before25_after75_local_optimum_member_bool": True, "unique_magic_value_bool": False, "plateau_start_variant_bucket": "before20_after80", "plateau_end_variant_bucket": "before40_after60", "plateau_variant_count": 5, "multiple_equal_winners_bool": True, "candidate_pool_changed_count": 0, "candidate_order_changed_count": 0, "n10bm_match_bool": ok}], ok


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10bnclaim0000", "claim_boundary_bucket": "public_local_refinement_package_only", "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "adaptive_per_row_choice_count": 0, "new_cost_budget_count": 0, "runtime_default_recommendation_bool": False, "runtime_default_promotion_bool": False, "heldout_claim_bool": False, "generalization_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "claim_boundary_valid_bool": True}], True


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10bnnorecompute0000", "no_recompute_boundary_bucket": "public_local_refinement_package_only", "private_read_count": 0, "recompute_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10bo_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10bo_handoff_id": "n10bnhandoff0000", "n10bo_handoff_bucket": "n10bo_plateau_mechanism_decomposition_authorized" if complete else "n10bo_not_authorized", "n10bo_authorized_bool": complete, "same_scoped_n1_rows_authorized_bool": complete, "plateau_variants_only_bool": complete, "plateau_variant_count": 5 if complete else 0, "public_aggregate_only_bool": True, "private_read_beyond_same_scoped_rows_authorized_bool": False, "new_variant_authorized_bool": False, "adaptive_choice_authorized_bool": False, "new_cost_budget_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_claim_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, package_ok: bool, rule_ok: bool, plateau_ok: bool, claim_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("local_refinement_package", package_ok), ("winner_rule", rule_ok), ("plateau_conclusion", plateau_ok), ("claim_boundary", claim_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10bo_plateau_mechanism_decomposition_authorized" if complete else "n10bo_not_authorized", "next_allowed_phase": "BEA-v1-N10BO Plateau Mechanism Decomposition" if complete else "none_until_local_refinement_package_is_consistent", "next_allowed_scope_bucket": "same_scoped_rows_plateau_variants_only_public_aggregate" if complete else "no_next_phase", "n10bo_authorized": complete, "private_read_beyond_same_scoped_rows_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "new_variant_authorized": False, "adaptive_per_row_choice_authorized": False, "new_cost_budget_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, package_ok: bool, rule_ok: bool, plateau_ok: bool, claim_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10bn_required_public_inputs_unavailable"
    if not package_ok or not rule_ok or not plateau_ok:
        return "no_go_n10bn_local_refinement_chain_mismatch"
    if not claim_ok or not norecompute_ok:
        return "no_go_n10bn_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    package_rows, package_ok = package_records(artifacts)
    rule_rows, rule_ok = winner_rule_records(artifacts)
    plateau_rows, plateau_ok = plateau_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, package_ok, rule_ok, plateau_ok, claim_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_local_refinement_package_only", "generated_by": "bea_v1_n10bn_local_refinement_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "local_refinement_package_records": package_rows, "winner_rule_records": rule_rows, "plateau_conclusion_records": plateau_rows, "claim_boundary_records": claim_rows, "no_recompute_records": norecompute_rows, "n10bo_handoff_records": n10bo_handoff_records(complete), "gate_records": gate_records(input_ok, package_ok, rule_ok, plateau_ok, claim_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10bo_handoff_records"] = n10bo_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, package_ok, rule_ok, plateau_ok, claim_ok, norecompute_ok, scanner_ok)
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
    fake_rows = [{"variant_bucket": name, "top10_span_overlap_count": top10, "top20_span_overlap_count": top20, "winner_bool": winner, "total_window_cost_proxy": 100, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "lost_before25_after75_top10_hits_count": 0, "lost_pm50_top10_hits_count": 0} for name, top10, top20, winner in EXPECTED_VARIANTS]
    fake = {"n10bm_local_refinement_artifact": {"local_refinement_result_records": fake_rows, "local_optimum_records": [{"before25_after75_top10_span_overlap_count": 20, "before25_after75_top20_span_overlap_count": 24, "max_top10_span_overlap_count": 20, "max_top20_span_overlap_count": 24, "candidate_pool_changed_count": 0, "candidate_order_changed_count": 0, "local_optimum_bucket": "before25_after75_local_optimum_plateau_member", "plateau_tie_bucket": "multiple_equal_winners", "winner_count": 5, "fixed_total_cost_bool": True}]}}
    return package_records(fake)[1] and winner_rule_records(fake)[1] and plateau_records(fake)[1]


def synthetic_mismatch() -> bool:
    fake = {"n10bm_local_refinement_artifact": {"local_refinement_result_records": []}}
    return not package_records(fake)[1] and status_for(True, True, False, True, True, True, True) == "no_go_n10bn_local_refinement_chain_mismatch"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    package_rows, package_ok = package_records(artifacts)
    rule_rows, rule_ok = winner_rule_records(artifacts)
    plateau_rows, plateau_ok = plateau_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10bn_required_public_inputs_unavailable", "no_go_n10bn_local_refinement_chain_mismatch", "no_go_n10bn_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 4),
        check("package_records", package_ok and len(package_rows) == 7 and sum(1 for r in package_rows if r["winner_bool"]) == 5),
        check("winner_rule", rule_ok and rule_rows[0]["winner_rule_bucket"] == "top10_primary_top20_tiebreak"),
        check("plateau_conclusion", plateau_ok and plateau_rows[0]["plateau_variant_count"] == 5 and plateau_rows[0]["unique_magic_value_bool"] is False),
        check("claim_boundary", claim_ok and claim_rows[0]["runtime_default_recommendation_bool"] is False and claim_rows[0]["new_cost_budget_count"] == 0),
        check("no_private_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["recompute_count"] == 0),
        check("synthetic_package_pass", synthetic_package_pass()),
        check("synthetic_mismatch", synthetic_mismatch()),
        check("false_flags", stop_go_records(True)[0]["n10bo_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["new_variant_authorized"] is False),
        check("status_complete", status_for(True, True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BN local refinement package")
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
