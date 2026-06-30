#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10da_top2_local_window_upper_bound_package.v1"
PHASE = "BEA-v1-N10DA Top2 Local-Window Upper-Bound Public Package"
STATUS_COMPLETE = "top2_local_window_upper_bound_package_complete_n10db_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10da_required_public_inputs_unavailable",
    "no_go_n10da_upper_bound_chain_mismatch",
    "no_go_n10da_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10da_top2_local_window_upper_bound_package/bea_v1_n10da_top2_local_window_upper_bound_package_report.json")
PUBLIC_INPUTS = {
    "n10cz_upper_bound_artifact": (Path("artifacts/bea_v1_n10cz_top2_local_window_saturation_upper_bound/bea_v1_n10cz_top2_local_window_saturation_upper_bound_report.json"), "top2_local_window_saturation_upper_bound_complete_n10da_authorized"),
    "n10cy_pm1000_decomposition_artifact": (Path("artifacts/bea_v1_n10cy_top2_pm1000_marginal_gain_decomposition/bea_v1_n10cy_top2_pm1000_marginal_gain_decomposition_report.json"), "top2_pm1000_marginal_gain_decomposition_complete_n10cz_authorized"),
    "n10cx_high_window_package_artifact": (Path("artifacts/bea_v1_n10cx_top2_override_high_window_package/bea_v1_n10cx_top2_override_high_window_package_report.json"), "top2_override_high_window_package_complete_n10cy_authorized"),
}
VARIANTS = ("top2_pm1000", "top2_pm1500", "top2_pm2000", "top2_pm5000", "top2_file_extent_proxy")
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
    "package_bucket", "variant_bucket", "remaining_miss_bucket", "decision_bucket", "boundary_bucket",
    "no_recompute_boundary_bucket", "n10db_handoff_bucket", "authorization", "next_allowed_phase",
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
                if str(key) in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, marker + "." + str(key))
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
        rows.append({"anonymous_input_artifact_id": f"n10dain{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def by_variant(n10cz: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in n10cz.get("upper_bound_variant_result_records", []):
        if isinstance(row, dict) and isinstance(row.get("variant_bucket"), str):
            out[row["variant_bucket"]] = row
    return out


def package_records(n10cz: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], bool]:
    variants = by_variant(n10cz)
    summary = n10cz.get("saturation_summary_records", [{}])[0] if isinstance(n10cz.get("saturation_summary_records"), list) and n10cz.get("saturation_summary_records") else {}
    residuals = {r.get("remaining_miss_bucket"): r for r in n10cz.get("residual_mechanism_records", []) if isinstance(r, dict)}
    expected = {
        "top2_pm1000": (30, 36, 0, "local_window_saturated"),
        "top2_pm1500": (30, 36, 0, "local_window_saturated"),
        "top2_pm2000": (30, 36, 0, "local_window_saturated"),
        "top2_pm5000": (30, 36, 0, "local_window_saturated"),
        "top2_file_extent_proxy": (22, 29, 8, "upper_bound_no_improvement"),
    }
    ok = n10cz.get("status") == "top2_local_window_saturation_upper_bound_complete_n10da_authorized"
    ok = ok and len(variants) == 5 and all(v in variants for v in VARIANTS)
    ok = ok and all((variants[v].get("top10_span_overlap_count"), variants[v].get("top20_span_overlap_count"), variants[v].get("lost_pm1000_top10_hits"), variants[v].get("decision_bucket")) == values for v, values in expected.items())
    ok = ok and summary.get("local_window_saturated_bool") is True and summary.get("local_window_upper_bound_improves_bool") is False and summary.get("file_reach_dominates_residual_bool") is True
    pm1000_resid = residuals.get("top2_pm1000", {})
    ok = ok and pm1000_resid.get("file_not_in_top10_remaining_count") == 167 and pm1000_resid.get("same_file_no_span_remaining_count") == 4 and pm1000_resid.get("span_overlap_beyond_top10_remaining_count") == 12
    package = [{"anonymous_upper_bound_package_id": "n10dapackage0000", "package_bucket": "top2_local_window_upper_bound_public_package", "variant_count": len(variants), "pm1000_top10_span_overlap_count": variants.get("top2_pm1000", {}).get("top10_span_overlap_count"), "pm1000_top20_span_overlap_count": variants.get("top2_pm1000", {}).get("top20_span_overlap_count"), "large_pm_variants_all_equal_pm1000_bool": all(variants.get(v, {}).get("top10_span_overlap_count") == 30 and variants.get(v, {}).get("top20_span_overlap_count") == 36 for v in ("top2_pm1500", "top2_pm2000", "top2_pm5000")), "file_extent_proxy_not_runtime_policy_top10_span_overlap_count": variants.get("top2_file_extent_proxy", {}).get("top10_span_overlap_count"), "file_extent_proxy_not_runtime_policy_top20_span_overlap_count": variants.get("top2_file_extent_proxy", {}).get("top20_span_overlap_count"), "file_extent_proxy_lost_pm1000_top10_hits": variants.get("top2_file_extent_proxy", {}).get("lost_pm1000_top10_hits"), "local_window_saturated_bool": summary.get("local_window_saturated_bool"), "local_window_upper_bound_improves_bool": summary.get("local_window_upper_bound_improves_bool"), "file_reach_dominates_residual_bool": summary.get("file_reach_dominates_residual_bool"), "package_consistent_bool": ok}]
    variant_rows = []
    for idx, variant in enumerate(VARIANTS):
        row = variants.get(variant, {})
        variant_rows.append({"anonymous_upper_bound_variant_package_id": f"n10davar{idx:04d}", "variant_bucket": variant, "top10_span_overlap_count": row.get("top10_span_overlap_count"), "top20_span_overlap_count": row.get("top20_span_overlap_count"), "delta_top10_vs_pm1000": row.get("delta_top10_vs_pm1000"), "delta_top20_vs_pm1000": row.get("delta_top20_vs_pm1000"), "lost_pm1000_top10_hits": row.get("lost_pm1000_top10_hits"), "cost_proxy_bucket": row.get("cost_proxy_bucket"), "decision_bucket": row.get("decision_bucket"), "candidate_pool_changed_bool": row.get("candidate_pool_changed_bool"), "candidate_order_changed_bool": row.get("candidate_order_changed_bool")})
    residual_rows = [{"anonymous_residual_package_id": "n10daresid0000", "remaining_miss_bucket": "pm1000_and_larger_pm_variants", "file_not_in_top10_remaining_count": pm1000_resid.get("file_not_in_top10_remaining_count"), "same_file_no_span_remaining_count": pm1000_resid.get("same_file_no_span_remaining_count"), "span_overlap_beyond_top10_remaining_count": pm1000_resid.get("span_overlap_beyond_top10_remaining_count")}]
    decision_rows = [{"anonymous_decision_package_id": "n10dadecision0000", "decision_bucket": "local_pm_growth_line_should_stop", "next_research_bucket": "rank_file_reach_branch_scoping_or_experiment_oracle_decides", "local_window_saturated_bool": True, "rank_file_reach_dominates_bool": True, "rank_file_experiment_authorized_here_bool": False, "runtime_default_authorized_bool": False}]
    boundary_rows = [{"anonymous_claim_boundary_id": "n10daboundary0000", "boundary_bucket": "public_upper_bound_package_only", "same_source_n1_proxy_only_bool": True, "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "runtime_default_claim_bool": False, "heldout_generalization_claim_bool": False, "method_downstream_claim_bool": False, "rank_file_experiment_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "candidate_add_remove_reorder_authorized_bool": False, "top3_override_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "privacy_boundary_complete_bool": True}]
    return package, variant_rows, residual_rows, decision_rows, boundary_rows, ok


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10danorecompute0000", "no_recompute_boundary_bucket": "public_package_only", "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "runtime_default_promotion_count": 0, "rank_file_experiment_count": 0, "candidate_generation_count": 0, "candidate_add_remove_reorder_count": 0, "top3_override_count": 0, "adaptive_tuning_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10db_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10db_handoff_id": "n10dahandoff0000", "n10db_handoff_bucket": "n10db_rank_file_reach_branch_scoping_or_experiment_oracle_decides" if complete else "n10db_not_authorized", "n10db_authorized_bool": complete, "next_allowed_scope_bucket": "rank_file_reach_branch_scoping_or_experiment_oracle_decides" if complete else "none", "private_read_authorized_next_bool": False, "recompute_authorized_next_bool": False, "new_variant_authorized_next_bool": False, "runtime_default_authorized_bool": False, "heldout_generalization_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "candidate_add_remove_reorder_authorized_bool": False, "top3_override_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_downstream_authorized_bool": False}]


def gate_records(input_ok: bool, package_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("upper_bound_package_facts", package_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10db_authorized" if complete else "n10db_not_authorized", "next_allowed_phase": "BEA-v1-N10DB Rank/File Reach Branch Scoping or Experiment" if complete else "none_until_upper_bound_package_valid", "next_allowed_scope_bucket": "rank_file_reach_branch_scoping_or_experiment_oracle_decides" if complete else "no_next_phase", "n10db_authorized": complete, "private_read_authorized": False, "recompute_authorized": False, "new_variant_authorized": False, "local_refinement_authorized": False, "runtime_or_default_authorized": False, "existing_evaluator_hook_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_add_remove_reorder_authorized": False, "top3_override_authorized": False, "rank_file_experiment_authorized_here": False, "adaptive_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, package_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10da_required_public_inputs_unavailable"
    if not package_ok:
        return "no_go_n10da_upper_bound_chain_mismatch"
    if not norecompute_ok:
        return "no_go_n10da_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    package_rows, variant_rows, residual_rows, decision_rows, boundary_rows, package_ok = package_records(artifacts.get("n10cz_upper_bound_artifact", {}))
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, package_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_top2_local_window_upper_bound_package_only", "generated_by": "bea_v1_n10da_top2_local_window_upper_bound_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "upper_bound_package_records": package_rows, "upper_bound_variant_package_records": variant_rows, "residual_package_records": residual_rows, "decision_package_records": decision_rows, "claim_boundary_records": boundary_rows, "no_private_recompute_records": norecompute_rows, "n10db_handoff_records": n10db_handoff_records(complete), "gate_records": gate_records(input_ok, package_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10db_handoff_records"] = n10db_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, package_ok, norecompute_ok, scanner_ok)
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
    package_rows, variant_rows, residual_rows, decision_rows, boundary_rows, package_ok = package_records(artifacts.get("n10cz_upper_bound_artifact", {}))
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10da_required_public_inputs_unavailable", "no_go_n10da_upper_bound_chain_mismatch", "no_go_n10da_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects", scan_summary({"path": "x"})["status"] == "fail" and scan_summary({"safe": "private/file.jsonl"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 3),
        check("package", package_ok and package_rows[0]["local_window_saturated_bool"] is True and package_rows[0]["file_reach_dominates_residual_bool"] is True),
        check("variant_count", len(variant_rows) == 5 and all(r["variant_bucket"] in VARIANTS for r in variant_rows)),
        check("pm_growth_saturated", all(r["top10_span_overlap_count"] == 30 and r["top20_span_overlap_count"] == 36 for r in variant_rows if r["variant_bucket"] in ("top2_pm1000", "top2_pm1500", "top2_pm2000", "top2_pm5000"))),
        check("file_extent_proxy", any(r["variant_bucket"] == "top2_file_extent_proxy" and r["top10_span_overlap_count"] == 22 and r["top20_span_overlap_count"] == 29 and r["lost_pm1000_top10_hits"] == 8 for r in variant_rows)),
        check("residual", residual_rows[0]["file_not_in_top10_remaining_count"] == 167 and residual_rows[0]["same_file_no_span_remaining_count"] == 4),
        check("decision", decision_rows[0]["decision_bucket"] == "local_pm_growth_line_should_stop" and decision_rows[0]["rank_file_experiment_authorized_here_bool"] is False),
        check("boundary", boundary_rows[0]["private_read_count"] == 0 and boundary_rows[0]["rank_file_experiment_authorized_bool"] is False),
        check("no_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["recompute_count"] == 0),
        check("synthetic_mismatch", status_for(True, True, False, True) == "no_go_n10da_upper_bound_chain_mismatch"),
        check("false_flags", stop_go_records(True)[0]["n10db_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["rank_file_experiment_authorized_here"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description=PHASE)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for c in checks:
            print(f"[{'PASS' if c['passed'] else 'FAIL'}] {c['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        if not ok:
            raise SystemExit(1)
        return
    report = build_report(checks)
    write_json(Path(args.out), report)
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")
    if report["status"].startswith("fail_"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
