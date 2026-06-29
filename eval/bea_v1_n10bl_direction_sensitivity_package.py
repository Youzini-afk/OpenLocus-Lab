#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10bl_direction_sensitivity_package.v1"
PHASE = "BEA-v1-N10BL Neighboring Asymmetry Direction-Sensitivity Package"
STATUS_COMPLETE = "direction_sensitivity_package_complete_n10bm_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10bl_required_public_inputs_unavailable",
    "no_go_n10bl_direction_sensitivity_chain_mismatch",
    "no_go_n10bl_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10bl_direction_sensitivity_package/bea_v1_n10bl_direction_sensitivity_package_report.json")
PUBLIC_INPUTS = {
    "n10bk_neighboring_asymmetry_micro_sweep_artifact": (Path("artifacts/bea_v1_n10bk_neighboring_asymmetry_micro_sweep/bea_v1_n10bk_neighboring_asymmetry_micro_sweep_report.json"), "neighboring_asymmetry_micro_sweep_complete_n10bl_authorized"),
    "n10bj_asymmetry_mechanism_package_artifact": (Path("artifacts/bea_v1_n10bj_asymmetric_window_mechanism_package/bea_v1_n10bj_asymmetric_window_mechanism_package_report.json"), "asymmetric_window_mechanism_package_complete_n10bk_authorized"),
    "n10bi_asymmetric_direction_decomposition_artifact": (Path("artifacts/bea_v1_n10bi_asymmetric_window_direction_decomposition/bea_v1_n10bi_asymmetric_window_direction_decomposition_report.json"), "asymmetric_window_direction_decomposition_complete_n10bj_authorized"),
}
EXPECTED_VARIANTS = (
    {"variant_bucket": "before0_after100", "direction_bucket": "after_heavy", "top10": 19, "top20": 22, "delta10": 0, "delta20": -1, "lost": 1, "winner": False},
    {"variant_bucket": "before25_after75", "direction_bucket": "after_heavy", "top10": 20, "top20": 24, "delta10": 1, "delta20": 1, "lost": 0, "winner": True},
    {"variant_bucket": "before50_after50", "direction_bucket": "balanced", "top10": 19, "top20": 23, "delta10": 0, "delta20": 0, "lost": 0, "winner": False},
    {"variant_bucket": "before75_after25", "direction_bucket": "before_heavy", "top10": 18, "top20": 22, "delta10": -1, "delta20": -1, "lost": 2, "winner": False},
    {"variant_bucket": "before100_after0", "direction_bucket": "before_heavy", "top10": 11, "top20": 13, "delta10": -8, "delta20": -10, "lost": 9, "winner": False},
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
    "variant_bucket", "direction_bucket", "winner_bucket", "trend_bucket", "package_bucket", "claim_boundary_bucket",
    "no_recompute_boundary_bucket", "n10bm_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
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
        rows.append({"anonymous_input_artifact_id": f"n10blin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def by_variant(rows: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("variant_bucket"), str):
                out[row["variant_bucket"]] = row
    return out


def direction_sensitivity_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10bk_neighboring_asymmetry_micro_sweep_artifact", {})
    by_name = by_variant(source.get("micro_sweep_result_records", []))
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, expected in enumerate(EXPECTED_VARIANTS):
        observed = by_name.get(expected["variant_bucket"], {})
        matched = (
            observed.get("direction_bucket") == expected["direction_bucket"]
            and observed.get("top10_span_overlap_count") == expected["top10"]
            and observed.get("top20_span_overlap_count") == expected["top20"]
            and observed.get("delta_vs_pm50_top10_count") == expected["delta10"]
            and observed.get("delta_vs_pm50_top20_count") == expected["delta20"]
            and observed.get("lost_pm50_top10_hits_count") == expected["lost"]
            and observed.get("winner_bool") == expected["winner"]
            and observed.get("total_window_cost_proxy") == 100
            and observed.get("candidate_pool_changed_bool") is False
            and observed.get("candidate_order_changed_bool") is False
        )
        ok = ok and matched
        rows.append({"anonymous_direction_sensitivity_package_id": f"n10blvar{idx:04d}", "package_bucket": "fixed_cost_direction_sensitivity", "variant_bucket": expected["variant_bucket"], "direction_bucket": expected["direction_bucket"], "top10_span_overlap_count": expected["top10"], "top20_span_overlap_count": expected["top20"], "delta_vs_pm50_top10_count": expected["delta10"], "delta_vs_pm50_top20_count": expected["delta20"], "lost_pm50_top10_hits_count": expected["lost"], "total_window_cost_proxy": 100, "winner_bool": expected["winner"], "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "n10bk_match_bool": matched})
    return rows, ok


def direction_summary_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10bk_neighboring_asymmetry_micro_sweep_artifact", {})
    summary_rows = source.get("direction_sensitivity_records", [])
    observed = summary_rows[0] if isinstance(summary_rows, list) and summary_rows and isinstance(summary_rows[0], dict) else {}
    ok = observed.get("winner_bucket") == "before25_after75" and observed.get("winner_direction_bucket") == "after_heavy" and observed.get("trend_bucket") == "nonmonotonic_direction_sensitivity" and observed.get("same_cost_proxy_bool") is True and observed.get("variant_count") == 5
    return [{"anonymous_direction_summary_id": "n10blsummary0000", "package_bucket": "fixed_cost_direction_sensitivity_summary", "winner_bucket": "before25_after75", "winner_direction_bucket": "after_heavy", "trend_bucket": "nonmonotonic_direction_sensitivity", "variant_count": 5, "fixed_cost_proxy_value": 100, "same_cost_proxy_bool": True, "n10bk_match_bool": ok}], ok


def boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10blclaim0000", "claim_boundary_bucket": "public_direction_sensitivity_package_only", "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "adaptive_per_row_choice_count": 0, "new_cost_budget_count": 0, "runtime_default_recommendation_bool": False, "runtime_default_promotion_bool": False, "heldout_claim_bool": False, "generalization_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "claim_boundary_valid_bool": True}], True


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10blnorecompute0000", "no_recompute_boundary_bucket": "public_direction_sensitivity_package_only", "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "adaptive_per_row_choice_count": 0, "new_cost_budget_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "runtime_default_change_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10bm_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10bm_handoff_id": "n10blhandoff0000", "n10bm_handoff_bucket": "n10bm_after_heavy_local_asymmetry_refinement_sweep_authorized" if complete else "n10bm_not_authorized", "n10bm_authorized_bool": complete, "same_scoped_n1_rows_authorized_bool": complete, "fixed_total_cost_100_only_bool": complete, "predeclared_variants_count": 7 if complete else 0, "new_cost_budget_authorized_bool": False, "adaptive_per_row_choice_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_claim_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, package_ok: bool, summary_ok: bool, boundary_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("direction_sensitivity_package", package_ok), ("winner_and_trend_summary", summary_ok), ("claim_boundary", boundary_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10bm_after_heavy_local_asymmetry_refinement_sweep_authorized" if complete else "n10bm_not_authorized", "next_allowed_phase": "BEA-v1-N10BM After-Heavy Local Asymmetry Refinement Sweep" if complete else "none_until_direction_sensitivity_package_is_consistent", "next_allowed_scope_bucket": "same_scoped_rows_fixed_cost_after_heavy_local_refinement" if complete else "no_next_phase", "n10bm_authorized": complete, "private_read_beyond_same_scoped_rows_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "new_variant_outside_predeclared_refinement_authorized": False, "adaptive_per_row_choice_authorized": False, "new_cost_budget_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, package_ok: bool, summary_ok: bool, boundary_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10bl_required_public_inputs_unavailable"
    if not package_ok or not summary_ok:
        return "no_go_n10bl_direction_sensitivity_chain_mismatch"
    if not boundary_ok or not norecompute_ok:
        return "no_go_n10bl_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    package_rows, package_ok = direction_sensitivity_package_records(artifacts)
    summary_rows, summary_ok = direction_summary_records(artifacts)
    boundary_rows, boundary_ok = boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, package_ok, summary_ok, boundary_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_direction_sensitivity_package_only", "generated_by": "bea_v1_n10bl_direction_sensitivity_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "direction_sensitivity_package_records": package_rows, "direction_summary_records": summary_rows, "claim_boundary_records": boundary_rows, "no_recompute_records": norecompute_rows, "n10bm_handoff_records": n10bm_handoff_records(complete), "gate_records": gate_records(input_ok, package_ok, summary_ok, boundary_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10bm_handoff_records"] = n10bm_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, package_ok, summary_ok, boundary_ok, norecompute_ok, scanner_ok)
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
    fake_rows = [{"variant_bucket": e["variant_bucket"], "direction_bucket": e["direction_bucket"], "top10_span_overlap_count": e["top10"], "top20_span_overlap_count": e["top20"], "delta_vs_pm50_top10_count": e["delta10"], "delta_vs_pm50_top20_count": e["delta20"], "lost_pm50_top10_hits_count": e["lost"], "winner_bool": e["winner"], "total_window_cost_proxy": 100, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False} for e in EXPECTED_VARIANTS]
    fake = {"n10bk_neighboring_asymmetry_micro_sweep_artifact": {"micro_sweep_result_records": fake_rows, "direction_sensitivity_records": [{"winner_bucket": "before25_after75", "winner_direction_bucket": "after_heavy", "trend_bucket": "nonmonotonic_direction_sensitivity", "same_cost_proxy_bool": True, "variant_count": 5}]}}
    return direction_sensitivity_package_records(fake)[1] and direction_summary_records(fake)[1]


def synthetic_mismatch() -> bool:
    fake = {"n10bk_neighboring_asymmetry_micro_sweep_artifact": {"micro_sweep_result_records": []}}
    return not direction_sensitivity_package_records(fake)[1] and status_for(True, True, False, True, True, True) == "no_go_n10bl_direction_sensitivity_chain_mismatch"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    package_rows, package_ok = direction_sensitivity_package_records(artifacts)
    summary_rows, summary_ok = direction_summary_records(artifacts)
    boundary_rows, boundary_ok = boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10bl_required_public_inputs_unavailable", "no_go_n10bl_direction_sensitivity_chain_mismatch", "no_go_n10bl_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 3),
        check("direction_package", package_ok and len(package_rows) == 5 and package_rows[1]["winner_bool"] is True),
        check("direction_summary", summary_ok and summary_rows[0]["winner_bucket"] == "before25_after75" and summary_rows[0]["trend_bucket"] == "nonmonotonic_direction_sensitivity"),
        check("claim_boundary", boundary_ok and boundary_rows[0]["runtime_default_recommendation_bool"] is False and boundary_rows[0]["new_cost_budget_count"] == 0),
        check("no_private_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["recompute_count"] == 0),
        check("synthetic_package_pass", synthetic_package_pass()),
        check("synthetic_mismatch", synthetic_mismatch()),
        check("false_flags", stop_go_records(True)[0]["n10bm_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["new_cost_budget_authorized"] is False),
        check("status_complete", status_for(True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BL direction sensitivity package")
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
