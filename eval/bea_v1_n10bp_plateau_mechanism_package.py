#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10bp_plateau_mechanism_package.v1"
PHASE = "BEA-v1-N10BP Plateau Mechanism Package"
STATUS_COMPLETE = "plateau_mechanism_package_complete_n10bq_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10bp_required_public_inputs_unavailable",
    "no_go_n10bp_plateau_chain_mismatch",
    "no_go_n10bp_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10bp_plateau_mechanism_package/bea_v1_n10bp_plateau_mechanism_package_report.json")
PUBLIC_INPUTS = {
    "n10bo_plateau_decomposition_artifact": (Path("artifacts/bea_v1_n10bo_plateau_mechanism_decomposition/bea_v1_n10bo_plateau_mechanism_decomposition_report.json"), "plateau_mechanism_decomposition_complete_n10bp_authorized"),
    "n10bn_local_refinement_package_artifact": (Path("artifacts/bea_v1_n10bn_local_refinement_package/bea_v1_n10bn_local_refinement_package_report.json"), "local_refinement_package_complete_n10bo_authorized"),
    "n10bm_local_refinement_artifact": (Path("artifacts/bea_v1_n10bm_after_heavy_local_asymmetry_refinement/bea_v1_n10bm_after_heavy_local_asymmetry_refinement_report.json"), "after_heavy_local_asymmetry_refinement_complete_n10bn_authorized"),
}
PLATEAU_VARIANTS = ("before20_after80", "before25_after75", "before30_after70", "before35_after65", "before40_after60")
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
    "variant_bucket", "package_bucket", "stability_bucket", "case_set_bucket", "direction_bucket", "claim_boundary_bucket",
    "no_recompute_boundary_bucket", "n10bq_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
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
        rows.append({"anonymous_input_artifact_id": f"n10bpin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def by_variant(rows: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("variant_bucket"), str):
                out[row["variant_bucket"]] = row
    return out


def plateau_fact_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10bo_plateau_decomposition_artifact", {})
    observed = by_variant(source.get("plateau_variant_aggregate_records", []))
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, name in enumerate(PLATEAU_VARIANTS):
        row = observed.get(name, {})
        matched = (
            row.get("top10_span_overlap_count") == 20
            and row.get("top20_span_overlap_count") == 24
            and row.get("common_top10_with_all_plateau_count") == 20
            and row.get("common_top20_with_all_plateau_count") == 24
            and row.get("unique_top10_count") == 0
            and row.get("unique_top20_count") == 0
            and row.get("lost_pm50_top10_count") == 0
            and row.get("candidate_pool_changed_bool") is False
            and row.get("candidate_order_changed_bool") is False
        )
        ok = ok and matched
        rows.append({"anonymous_plateau_fact_id": f"n10bpvar{idx:04d}", "package_bucket": "stable_plateau_variant", "variant_bucket": name, "top10_span_overlap_count": 20, "top20_span_overlap_count": 24, "common_top10_with_all_plateau_count": 20, "common_top20_with_all_plateau_count": 24, "unique_top10_count": 0, "unique_top20_count": 0, "lost_pm50_top10_count": 0, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "n10bo_match_bool": matched})
    return rows, ok


def common_core_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10bo_plateau_decomposition_artifact", {})
    core_rows = source.get("common_core_records", [])
    observed = core_rows[0] if isinstance(core_rows, list) and core_rows and isinstance(core_rows[0], dict) else {}
    stability_rows = source.get("stability_conclusion_records", [])
    stability = stability_rows[0] if isinstance(stability_rows, list) and stability_rows and isinstance(stability_rows[0], dict) else {}
    ok = (
        observed.get("top10_common_across_all_plateau_count") == 20
        and observed.get("top10_union_across_plateau_count") == 20
        and observed.get("top20_common_across_all_plateau_count") == 24
        and observed.get("top20_union_across_plateau_count") == 24
        and observed.get("top10_case_swap_count") == 0
        and observed.get("top20_case_swap_count") == 0
        and stability.get("stability_bucket") == "genuinely_stable_plateau"
        and stability.get("lost_pm50_max_count") == 0
    )
    return [{"anonymous_common_core_package_id": "n10bpcore0000", "case_set_bucket": "plateau_common_equals_union", "top10_common_across_all_plateau_count": 20, "top10_union_across_plateau_count": 20, "top20_common_across_all_plateau_count": 24, "top20_union_across_plateau_count": 24, "top10_case_swap_count": 0, "top20_case_swap_count": 0, "unique_case_count": 0, "lost_pm50_max_count": 0, "stability_bucket": "genuinely_stable_plateau", "n10bo_match_bool": ok}], ok


def direction_bucket_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    source = artifacts.get("n10bo_plateau_decomposition_artifact", {})
    rows = source.get("direction_contribution_records", [])
    observed = None
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("variant_bucket") == "plateau_common" and row.get("case_set_bucket") == "common_top10_all_plateau":
                observed = row
                break
    observed = observed or {}
    ok = observed.get("before_gold_gap_count") == 10 and observed.get("after_gold_gap_count") == 1 and observed.get("already_overlap_count") == 9 and observed.get("other_count") == 0 and observed.get("case_count") == 20
    return [{"anonymous_direction_bucket_package_id": "n10bpdir0000", "case_set_bucket": "common_top10_all_plateau", "direction_bucket": "before_after_overlap_mix", "before_gold_gap_count": 10, "after_gold_gap_count": 1, "already_overlap_count": 9, "other_count": 0, "case_count": 20, "n10bo_match_bool": ok}], ok


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10bpclaim0000", "claim_boundary_bucket": "public_plateau_mechanism_package_only", "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "adaptive_per_row_choice_count": 0, "new_cost_budget_count": 0, "runtime_default_recommendation_bool": False, "runtime_default_promotion_bool": False, "heldout_claim_bool": False, "generalization_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "claim_boundary_valid_bool": True}], True


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10bpnorecompute0000", "no_recompute_boundary_bucket": "public_plateau_mechanism_package_only", "private_read_count": 0, "recompute_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10bq_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10bq_handoff_id": "n10bphandoff0000", "n10bq_handoff_bucket": "n10bq_plateau_cost_minimization_sweep_authorized" if complete else "n10bq_not_authorized", "n10bq_authorized_bool": complete, "same_scoped_n1_rows_authorized_bool": complete, "fixed_ratio_family_only_bool": complete, "total_cost_values_count": 4 if complete else 0, "predeclared_variant_count": 20 if complete else 0, "public_aggregate_only_bool": True, "private_read_beyond_same_scoped_rows_authorized_bool": False, "new_ratio_outside_family_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_claim_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, plateau_ok: bool, core_ok: bool, dir_ok: bool, claim_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("plateau_variant_facts", plateau_ok), ("common_core_stability", core_ok), ("direction_bucket_facts", dir_ok), ("claim_boundary", claim_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10bq_plateau_cost_minimization_sweep_authorized" if complete else "n10bq_not_authorized", "next_allowed_phase": "BEA-v1-N10BQ Plateau Cost-Minimization Sweep" if complete else "none_until_plateau_package_is_consistent", "next_allowed_scope_bucket": "same_scoped_rows_fixed_ratio_family_cost_minimization" if complete else "no_next_phase", "n10bq_authorized": complete, "private_read_beyond_same_scoped_rows_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "new_ratio_outside_family_authorized": False, "adaptive_tuning_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, plateau_ok: bool, core_ok: bool, dir_ok: bool, claim_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10bp_required_public_inputs_unavailable"
    if not plateau_ok or not core_ok or not dir_ok:
        return "no_go_n10bp_plateau_chain_mismatch"
    if not claim_ok or not norecompute_ok:
        return "no_go_n10bp_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    plateau_rows, plateau_ok = plateau_fact_records(artifacts)
    core_rows, core_ok = common_core_records(artifacts)
    direction_rows, dir_ok = direction_bucket_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, plateau_ok, core_ok, dir_ok, claim_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_plateau_mechanism_package_only", "generated_by": "bea_v1_n10bp_plateau_mechanism_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "plateau_fact_package_records": plateau_rows, "common_core_package_records": core_rows, "direction_bucket_package_records": direction_rows, "claim_boundary_records": claim_rows, "no_recompute_records": norecompute_rows, "n10bq_handoff_records": n10bq_handoff_records(complete), "gate_records": gate_records(input_ok, plateau_ok, core_ok, dir_ok, claim_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10bq_handoff_records"] = n10bq_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, plateau_ok, core_ok, dir_ok, claim_ok, norecompute_ok, scanner_ok)
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
    fake_variants = [{"variant_bucket": name, "top10_span_overlap_count": 20, "top20_span_overlap_count": 24, "common_top10_with_all_plateau_count": 20, "common_top20_with_all_plateau_count": 24, "unique_top10_count": 0, "unique_top20_count": 0, "lost_pm50_top10_count": 0, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False} for name in PLATEAU_VARIANTS]
    fake = {"n10bo_plateau_decomposition_artifact": {"plateau_variant_aggregate_records": fake_variants, "common_core_records": [{"top10_common_across_all_plateau_count": 20, "top10_union_across_plateau_count": 20, "top20_common_across_all_plateau_count": 24, "top20_union_across_plateau_count": 24, "top10_case_swap_count": 0, "top20_case_swap_count": 0}], "stability_conclusion_records": [{"stability_bucket": "genuinely_stable_plateau", "lost_pm50_max_count": 0}], "direction_contribution_records": [{"variant_bucket": "plateau_common", "case_set_bucket": "common_top10_all_plateau", "before_gold_gap_count": 10, "after_gold_gap_count": 1, "already_overlap_count": 9, "other_count": 0, "case_count": 20}]}}
    return plateau_fact_records(fake)[1] and common_core_records(fake)[1] and direction_bucket_records(fake)[1]


def synthetic_mismatch() -> bool:
    fake = {"n10bo_plateau_decomposition_artifact": {"plateau_variant_aggregate_records": []}}
    return not plateau_fact_records(fake)[1] and status_for(True, True, False, True, True, True, True) == "no_go_n10bp_plateau_chain_mismatch"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    plateau_rows, plateau_ok = plateau_fact_records(artifacts)
    core_rows, core_ok = common_core_records(artifacts)
    direction_rows, dir_ok = direction_bucket_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10bp_required_public_inputs_unavailable", "no_go_n10bp_plateau_chain_mismatch", "no_go_n10bp_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 3),
        check("plateau_facts", plateau_ok and len(plateau_rows) == 5 and all(row["top10_span_overlap_count"] == 20 for row in plateau_rows)),
        check("common_core", core_ok and core_rows[0]["stability_bucket"] == "genuinely_stable_plateau" and core_rows[0]["unique_case_count"] == 0),
        check("direction_buckets", dir_ok and direction_rows[0]["before_gold_gap_count"] == 10 and direction_rows[0]["already_overlap_count"] == 9),
        check("claim_boundary", claim_ok and claim_rows[0]["runtime_default_recommendation_bool"] is False and claim_rows[0]["new_cost_budget_count"] == 0),
        check("no_private_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["recompute_count"] == 0),
        check("synthetic_package_pass", synthetic_package_pass()),
        check("synthetic_mismatch", synthetic_mismatch()),
        check("false_flags", stop_go_records(True)[0]["n10bq_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["new_ratio_outside_family_authorized"] is False),
        check("status_complete", status_for(True, True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BP plateau mechanism package")
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
