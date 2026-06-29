#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10bj_asymmetric_window_mechanism_package.v1"
PHASE = "BEA-v1-N10BJ Asymmetric Window Direction Mechanism Package"
STATUS_COMPLETE = "asymmetric_window_mechanism_package_complete_n10bk_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10bj_required_public_inputs_unavailable",
    "no_go_n10bj_mechanism_chain_mismatch",
    "no_go_n10bj_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10bj_asymmetric_window_mechanism_package/bea_v1_n10bj_asymmetric_window_mechanism_package_report.json")
PUBLIC_INPUTS = {
    "n10bi_asymmetric_direction_decomposition_artifact": (Path("artifacts/bea_v1_n10bi_asymmetric_window_direction_decomposition/bea_v1_n10bi_asymmetric_window_direction_decomposition_report.json"), "asymmetric_window_direction_decomposition_complete_n10bj_authorized"),
    "n10bh_pm50_comparator_package_artifact": (Path("artifacts/bea_v1_n10bh_pm50_comparator_package/bea_v1_n10bh_pm50_comparator_package_report.json"), "pm50_comparator_package_complete_n10bi_authorized"),
    "n10bg_pm50_comparator_artifact": (Path("artifacts/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator_report.json"), "cost_aware_decisions_vs_fixed_pm50_comparator_complete_n10bh_authorized"),
}
EXPECTED_BUCKETS = {
    ("gained_by_before25_after75_vs_pm50", "before_gold_gap"): 1,
    ("gained_by_before25_after75_vs_pm50", "after_gold_gap"): 0,
    ("gained_by_before25_after75_vs_pm50", "already_overlap"): 0,
    ("gained_by_before25_after75_vs_pm50", "other"): 0,
    ("lost_by_before25_after75_vs_pm50", "before_gold_gap"): 0,
    ("lost_by_before25_after75_vs_pm50", "after_gold_gap"): 0,
    ("lost_by_before25_after75_vs_pm50", "already_overlap"): 0,
    ("lost_by_before25_after75_vs_pm50", "other"): 0,
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
    "mechanism_bucket", "comparator_bucket", "variant_bucket", "cost_bucket", "gain_loss_bucket", "direction_bucket",
    "no_gold_policy_bucket", "claim_boundary_bucket", "no_recompute_boundary_bucket", "n10bk_handoff_bucket",
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
        rows.append({"anonymous_input_artifact_id": f"n10bjin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def direction_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    src = artifacts.get("n10bi_asymmetric_direction_decomposition_artifact", {})
    pair_rows = src.get("comparator_pair_records", [])
    mech_rows = src.get("mechanism_summary_records", [])
    pairs = {r.get("variant_bucket"): r for r in pair_rows if isinstance(r, dict)} if isinstance(pair_rows, list) else {}
    mech = mech_rows[0] if isinstance(mech_rows, list) and mech_rows and isinstance(mech_rows[0], dict) else {}
    ok = (
        pairs.get("pm50", {}).get("top10_span_overlap_count") == 19
        and pairs.get("pm50", {}).get("top20_span_overlap_count") == 23
        and pairs.get("before25_after75", {}).get("top10_span_overlap_count") == 20
        and pairs.get("before25_after75", {}).get("top20_span_overlap_count") == 24
        and pairs.get("pm50", {}).get("cost_proxy_value") == 1000
        and pairs.get("before25_after75", {}).get("cost_proxy_value") == 1000
        and mech.get("top10_net_gain_count") == 1
        and mech.get("top20_net_gain_count") == 1
        and mech.get("top10_gained_case_count") == 1
        and mech.get("top10_lost_case_count") == 0
    )
    rows = [
        {"anonymous_direction_package_id": "n10bjdir0000", "comparator_bucket": "fixed_symmetric_pm50", "variant_bucket": "pm50", "top10_span_overlap_count": 19, "top20_span_overlap_count": 23, "cost_proxy_value": 1000, "cost_bucket": "medium"},
        {"anonymous_direction_package_id": "n10bjdir0001", "comparator_bucket": "asymmetric_before25_after75", "variant_bucket": "before25_after75", "top10_span_overlap_count": 20, "top20_span_overlap_count": 24, "cost_proxy_value": 1000, "cost_bucket": "medium"},
        {"anonymous_direction_package_id": "n10bjdir0002", "mechanism_bucket": "same_cost_asymmetric_net_gain", "top10_net_gain_count": 1, "top20_net_gain_count": 1, "top10_gained_case_count": 1, "top10_lost_case_count": 0, "same_cost_bool": True},
    ]
    return rows, ok


def gain_loss_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    src_rows = artifacts.get("n10bi_asymmetric_direction_decomposition_artifact", {}).get("gain_loss_bucket_records", [])
    observed = {(r.get("gain_loss_bucket"), r.get("direction_bucket")): r.get("top10_case_count") for r in src_rows if isinstance(r, dict)} if isinstance(src_rows, list) else {}
    ok = all(observed.get(key) == value for key, value in EXPECTED_BUCKETS.items())
    rows = []
    for idx, ((gain_loss_bucket, direction_bucket), count) in enumerate(EXPECTED_BUCKETS.items()):
        rows.append({"anonymous_gain_loss_package_id": f"n10bjbucket{idx:04d}", "gain_loss_bucket": gain_loss_bucket, "direction_bucket": direction_bucket, "top10_case_count": count, "public_bucket_only_bool": True, "n10bi_match_bool": observed.get((gain_loss_bucket, direction_bucket)) == count})
    return rows, ok


def no_gold_policy_package_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    src_rows = artifacts.get("n10bi_asymmetric_direction_decomposition_artifact", {}).get("no_gold_policy_records", [])
    src = src_rows[0] if isinstance(src_rows, list) and src_rows and isinstance(src_rows[0], dict) else {}
    ok = src.get("predeclared_global_windows_bool") is True and src.get("per_row_adaptive_window_count") == 0 and src.get("gold_used_to_choose_window_count") == 0 and src.get("miss_direction_used_to_choose_window_count") == 0
    return [{"anonymous_no_gold_policy_package_id": "n10bjnogold0000", "no_gold_policy_bucket": "fixed_global_windows_no_per_row_direction_choice", "predeclared_global_windows_bool": True, "per_row_adaptive_window_count": 0, "gold_used_to_choose_window_count": 0, "miss_direction_used_to_choose_window_count": 0, "content_aware_adjustment_count": 0, "n10bi_match_bool": ok}], ok


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10bjclaim0000", "claim_boundary_bucket": "public_asymmetry_mechanism_package_only", "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "adaptive_tuning_count": 0, "runtime_default_recommendation_bool": False, "runtime_default_promotion_bool": False, "heldout_claim_bool": False, "generalization_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "claim_boundary_valid_bool": True}], True


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10bjnorecompute0000", "no_recompute_boundary_bucket": "public_asymmetry_mechanism_package_only", "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "adaptive_tuning_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "runtime_default_change_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10bk_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10bk_handoff_id": "n10bjhandoff0000", "n10bk_handoff_bucket": "n10bk_neighboring_asymmetry_micro_sweep_authorized" if complete else "n10bk_not_authorized", "n10bk_authorized_bool": complete, "same_scoped_n1_rows_authorized_bool": complete, "same_cost_proxy_only_bool": complete, "predeclared_variants_count": 5 if complete else 0, "new_cost_budget_authorized_bool": False, "adaptive_per_row_choice_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_claim_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, direction_ok: bool, buckets_ok: bool, nogold_ok: bool, claim_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("direction_mechanism_facts", direction_ok), ("gain_loss_buckets", buckets_ok), ("no_gold_policy", nogold_ok), ("claim_boundary", claim_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10bk_neighboring_asymmetry_micro_sweep_authorized" if complete else "n10bk_not_authorized", "next_allowed_phase": "BEA-v1-N10BK Neighboring Asymmetry Micro-Sweep" if complete else "none_until_asymmetry_package_is_consistent", "next_allowed_scope_bucket": "same_cost_direction_sensitivity_micro_sweep" if complete else "no_next_phase", "n10bk_authorized": complete, "private_read_beyond_same_scoped_rows_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "new_variant_outside_predeclared_set_authorized": False, "adaptive_per_row_choice_authorized": False, "new_cost_budget_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, direction_ok: bool, buckets_ok: bool, nogold_ok: bool, claim_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10bj_required_public_inputs_unavailable"
    if not direction_ok or not buckets_ok or not nogold_ok:
        return "no_go_n10bj_mechanism_chain_mismatch"
    if not claim_ok or not norecompute_ok:
        return "no_go_n10bj_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    direction_rows, direction_ok = direction_package_records(artifacts)
    bucket_rows, buckets_ok = gain_loss_package_records(artifacts)
    nogold_rows, nogold_ok = no_gold_policy_package_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, direction_ok, buckets_ok, nogold_ok, claim_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_asymmetry_mechanism_package_only", "generated_by": "bea_v1_n10bj_asymmetric_window_mechanism_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "direction_mechanism_package_records": direction_rows, "gain_loss_bucket_package_records": bucket_rows, "no_gold_policy_package_records": nogold_rows, "claim_boundary_records": claim_rows, "no_recompute_records": norecompute_rows, "n10bk_handoff_records": n10bk_handoff_records(complete), "gate_records": gate_records(input_ok, direction_ok, buckets_ok, nogold_ok, claim_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10bk_handoff_records"] = n10bk_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, direction_ok, buckets_ok, nogold_ok, claim_ok, norecompute_ok, scanner_ok)
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
    fake = {"n10bi_asymmetric_direction_decomposition_artifact": {"comparator_pair_records": [{"variant_bucket": "pm50", "top10_span_overlap_count": 19, "top20_span_overlap_count": 23, "cost_proxy_value": 1000}, {"variant_bucket": "before25_after75", "top10_span_overlap_count": 20, "top20_span_overlap_count": 24, "cost_proxy_value": 1000}], "mechanism_summary_records": [{"top10_net_gain_count": 1, "top20_net_gain_count": 1, "top10_gained_case_count": 1, "top10_lost_case_count": 0}], "gain_loss_bucket_records": [{"gain_loss_bucket": k[0], "direction_bucket": k[1], "top10_case_count": v} for k, v in EXPECTED_BUCKETS.items()], "no_gold_policy_records": [{"predeclared_global_windows_bool": True, "per_row_adaptive_window_count": 0, "gold_used_to_choose_window_count": 0, "miss_direction_used_to_choose_window_count": 0}]}}
    return direction_package_records(fake)[1] and gain_loss_package_records(fake)[1] and no_gold_policy_package_records(fake)[1]


def synthetic_mismatch() -> bool:
    fake = {"n10bi_asymmetric_direction_decomposition_artifact": {"comparator_pair_records": []}}
    return not direction_package_records(fake)[1] and status_for(True, True, False, True, True, True, True) == "no_go_n10bj_mechanism_chain_mismatch"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    direction_rows, direction_ok = direction_package_records(artifacts)
    bucket_rows, buckets_ok = gain_loss_package_records(artifacts)
    nogold_rows, nogold_ok = no_gold_policy_package_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10bj_required_public_inputs_unavailable", "no_go_n10bj_mechanism_chain_mismatch", "no_go_n10bj_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 3),
        check("direction_package", direction_ok and direction_rows[0]["top10_span_overlap_count"] == 19 and direction_rows[1]["top10_span_overlap_count"] == 20),
        check("gain_loss_buckets", buckets_ok and sum(r["top10_case_count"] for r in bucket_rows if r["gain_loss_bucket"].startswith("gained")) == 1 and sum(r["top10_case_count"] for r in bucket_rows if r["gain_loss_bucket"].startswith("lost")) == 0),
        check("no_gold_policy", nogold_ok and nogold_rows[0]["gold_used_to_choose_window_count"] == 0),
        check("claim_boundary", claim_ok and claim_rows[0]["runtime_default_recommendation_bool"] is False and claim_rows[0]["heldout_claim_bool"] is False),
        check("no_private_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["recompute_count"] == 0),
        check("synthetic_package_pass", synthetic_package_pass()),
        check("synthetic_mismatch", synthetic_mismatch()),
        check("false_flags", stop_go_records(True)[0]["n10bk_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["new_cost_budget_authorized"] is False),
        check("status_complete", status_for(True, True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BJ asymmetry mechanism package")
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
