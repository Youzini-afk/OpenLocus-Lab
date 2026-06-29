#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10ax_cost_sensitive_frontier_claim_package.v1"
PHASE = "BEA-v1-N10AX Cost-Sensitive Frontier Claim Package"
STATUS_COMPLETE = "cost_sensitive_frontier_claim_package_complete_n10ay_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10ax_required_public_inputs_unavailable",
    "no_go_n10ax_frontier_or_mechanism_mismatch",
    "no_go_n10ax_privacy_or_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10ax_cost_sensitive_frontier_claim_package/bea_v1_n10ax_cost_sensitive_frontier_claim_package_report.json")
PUBLIC_INPUTS = {
    "n10aw_mechanism_decomposition_artifact": (Path("artifacts/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition_report.json"), "cost_sensitive_span_window_frontier_mechanism_decomposition_complete_n10ax_authorized"),
    "n10av_replication_package_artifact": (Path("artifacts/bea_v1_n10av_exploratory_span_window_sweep_replication_package/bea_v1_n10av_exploratory_span_window_sweep_replication_package_report.json"), "exploratory_span_window_sweep_replication_package_complete_n10aw_authorized"),
    "n10au_independent_recompute_artifact": (Path("artifacts/bea_v1_n10au_independent_recompute_span_window_variant_sweep/bea_v1_n10au_independent_recompute_span_window_variant_sweep_report.json"), "independent_recompute_span_window_variant_sweep_pass_n10av_authorized"),
    "n10as_exploratory_sweep_artifact": (Path("artifacts/bea_v1_n10as_exploratory_span_window_variant_sweep/bea_v1_n10as_exploratory_span_window_variant_sweep_report.json"), "exploratory_span_window_variant_sweep_complete_n10at_authorized"),
    "n10z_failure_decomposition_artifact": (Path("artifacts/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition_report.json"), "n1_span_surface_span_level_failure_decomposition_complete_n10aa_authorized"),
}
TIER_EXPECTED = {
    "baseline": {"top10": 9, "top20": 10, "tier_label_bucket": "baseline_unexpanded", "cost_bucket": "zero"},
    "pm30": {"top10": 18, "top20": 22, "tier_label_bucket": "low_cost_frontier", "cost_bucket": "low"},
    "before25_after75": {"top10": 20, "top20": 24, "tier_label_bucket": "balanced_frontier", "cost_bucket": "medium"},
    "pm75": {"top10": 21, "top20": 25, "tier_label_bucket": "balanced_frontier", "cost_bucket": "medium"},
    "pm200": {"top10": 25, "top20": 30, "tier_label_bucket": "max_recall_frontier", "cost_bucket": "very_high"},
}
MECHANISM_EXPECTED = {
    ("pm30", "baseline"): {"new": 9, "before_gold_gap": 8, "after_gold_gap": 1, "already_reachable_late_rank": 0, "other_bucketed": 0},
    ("before25_after75", "pm30"): {"new": 2, "before_gold_gap": 2, "after_gold_gap": 0, "already_reachable_late_rank": 0, "other_bucketed": 0},
    ("pm75", "before25_after75"): {"new": 1, "before_gold_gap": 0, "after_gold_gap": 1, "already_reachable_late_rank": 0, "other_bucketed": 0},
    ("pm200", "pm75"): {"new": 4, "before_gold_gap": 3, "after_gold_gap": 1, "already_reachable_late_rank": 0, "other_bucketed": 0},
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
    "tier_bucket", "tier_label_bucket", "cost_bucket", "previous_tier_bucket", "mechanism_bucket", "claim_boundary_bucket",
    "allowed_claim_bucket", "forbidden_claim_bucket", "no_recompute_boundary_bucket", "n10ay_handoff_bucket",
    "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def root() -> Path:
    return Path(__file__).resolve().parent.parent



def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(rel: Path) -> tuple[dict[str, Any], str]:
    full = root() / rel
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(rel: Path, obj: dict[str, Any]) -> None:
    full = root() / rel
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
        rows.append({"anonymous_input_artifact_id": f"n10axin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def records_by_tier(rows: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("tier_bucket"), str):
                out[row["tier_bucket"]] = row
    return out


def frontier_claim_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10aw = artifacts.get("n10aw_mechanism_decomposition_artifact", {})
    aw_tiers = records_by_tier(n10aw.get("frontier_tier_delta_records", []))
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (tier, expected) in enumerate(TIER_EXPECTED.items()):
        source = aw_tiers.get(tier, {})
        matched = bool(source) and source.get("cumulative_span_hits") == expected["top10"] and source.get("cumulative_top20_span_hits") == expected["top20"] and source.get("lost_previous_hits") == 0 and source.get("cost_bucket") == expected["cost_bucket"]
        ok = ok and matched
        rows.append({"anonymous_frontier_claim_id": f"n10axfront{idx:04d}", "tier_bucket": tier, "tier_label_bucket": expected["tier_label_bucket"], "top10_span_overlap_count": expected["top10"], "top20_span_overlap_count": expected["top20"], "cost_bucket": expected["cost_bucket"], "lost_previous_hits": 0, "n10aw_match_bool": matched})
    return rows, ok


def mechanism_claim_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10aw = artifacts.get("n10aw_mechanism_decomposition_artifact", {})
    tier_rows = records_by_tier(n10aw.get("frontier_tier_delta_records", []))
    bucket_rows = n10aw.get("mechanism_bucket_records", [])
    bucket_map: dict[tuple[str, str, str], int] = {}
    if isinstance(bucket_rows, list):
        for row in bucket_rows:
            if isinstance(row, dict):
                bucket_map[(str(row.get("tier_bucket", "")), str(row.get("previous_tier_bucket", "")), str(row.get("mechanism_bucket", "")))] = int(row.get("new_span_hit_case_count", 0))
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, ((tier, previous), expected) in enumerate(MECHANISM_EXPECTED.items()):
        tier_row = tier_rows.get(tier, {})
        before = bucket_map.get((tier, previous, "before_gold_gap"), -1)
        after = bucket_map.get((tier, previous, "after_gold_gap"), -1)
        late = bucket_map.get((tier, previous, "already_reachable_late_rank"), -1)
        other = bucket_map.get((tier, previous, "other_bucketed"), -1)
        matched = tier_row.get("new_span_hits_vs_previous_tier") == expected["new"] and before == expected["before_gold_gap"] and after == expected["after_gold_gap"] and late == 0 and other == 0 and tier_row.get("lost_previous_hits") == 0
        ok = ok and matched
        rows.append({"anonymous_mechanism_claim_id": f"n10axmech{idx:04d}", "tier_bucket": tier, "previous_tier_bucket": previous, "new_span_hits_vs_previous_tier": expected["new"], "before_gold_gap_count": expected["before_gold_gap"], "after_gold_gap_count": expected["after_gold_gap"], "already_reachable_late_rank_count": 0, "other_bucketed_count": 0, "lost_previous_hits": 0, "wider_recovery_same_before_after_pattern_bool": True, "n10aw_match_bool": matched})
    return rows, ok


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10axclaim0000", "claim_boundary_bucket": "same_source_n1_proxy_cost_sensitive_frontier_package_only", "allowed_claim_bucket": "scoped_same_source_cost_sensitive_frontier_mechanism_summary", "exploratory_same_source_n1_proxy_only_bool": True, "heldout_claim_bool": False, "generalization_claim_bool": False, "n2_equivalent_claim_bool": False, "runtime_default_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "selector_reranker_claim_bool": False, "p5_or_v1a_claim_bool": False, "claim_boundary_valid_bool": True}], True


def forbidden_claim_records() -> tuple[list[dict[str, Any]], bool]:
    rows = []
    forbidden = ("runtime_default_promotion", "heldout_generalization", "n2_equivalent_validation", "method_winner", "downstream_value", "selector_reranker", "p5_v1a", "retrieval_rerun", "candidate_generation", "adaptive_tuning")
    for idx, bucket in enumerate(forbidden):
        rows.append({"anonymous_forbidden_claim_id": f"n10axforbid{idx:04d}", "forbidden_claim_bucket": bucket, "claim_made_bool": False, "claim_authorized_bool": False})
    return rows, True


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10axnorecompute0000", "no_recompute_boundary_bucket": "public_claim_package_only", "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "adaptive_tuning_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "existing_evaluator_hook_in_count": 0, "runtime_default_change_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10ay_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ay_handoff_id": "n10axhandoff0000", "n10ay_handoff_bucket": "n10ay_cost_aware_adapter_frontier_smoke_authorized" if complete else "n10ay_not_authorized", "n10ay_cost_aware_adapter_frontier_smoke_authorized_bool": complete, "same_scoped_n1_span_rows_read_authorized_bool": complete, "broad_private_read_authorized_bool": False, "adapter_helper_import_only_bool": True, "runtime_default_promotion_authorized_bool": False, "heldout_generalization_claim_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, frontier_ok: bool, mechanism_ok: bool, claim_ok: bool, forbidden_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("frontier_claims_match", frontier_ok), ("mechanism_claims_match", mechanism_ok), ("claim_boundary", claim_ok), ("forbidden_claims_false", forbidden_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ay_cost_aware_adapter_frontier_smoke_authorized" if complete else "n10ay_not_authorized", "next_allowed_phase": "BEA-v1-N10AY Cost-Aware Adapter Frontier Smoke" if complete else "none_until_cost_sensitive_claim_package_is_consistent", "next_allowed_scope_bucket": "direct_empirical_same_scoped_n1_rows_adapter_helper_only" if complete else "no_next_phase", "n10ay_authorized": complete, "same_scoped_n1_span_rows_read_authorized": complete, "broad_private_read_authorized": False, "private_read_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_materialization_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "new_variant_authorized": False, "adaptive_tuning_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, frontier_ok: bool, mechanism_ok: bool, claim_ok: bool, forbidden_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ax_required_public_inputs_unavailable"
    if not frontier_ok or not mechanism_ok:
        return "no_go_n10ax_frontier_or_mechanism_mismatch"
    if not claim_ok or not forbidden_ok or not norecompute_ok:
        return "no_go_n10ax_privacy_or_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    frontier_rows, frontier_ok = frontier_claim_records(artifacts)
    mechanism_rows, mechanism_ok = mechanism_claim_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    forbidden_rows, forbidden_ok = forbidden_claim_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, frontier_ok, mechanism_ok, claim_ok, forbidden_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_cost_sensitive_frontier_claim_package_only", "generated_by": "bea_v1_n10ax_cost_sensitive_frontier_claim_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "frontier_claim_records": frontier_rows, "mechanism_claim_records": mechanism_rows, "claim_boundary_records": claim_rows, "forbidden_claim_records": forbidden_rows, "no_recompute_records": norecompute_rows, "n10ay_handoff_records": n10ay_handoff_records(complete), "gate_records": gate_records(input_ok, frontier_ok, mechanism_ok, claim_ok, forbidden_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10ay_handoff_records"] = n10ay_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, frontier_ok, mechanism_ok, claim_ok, forbidden_ok, norecompute_ok, scanner_ok)
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
    artifacts = {"n10aw_mechanism_decomposition_artifact": {"frontier_tier_delta_records": [{"tier_bucket": k, "cumulative_span_hits": v["top10"], "cumulative_top20_span_hits": v["top20"], "lost_previous_hits": 0, "cost_bucket": v["cost_bucket"]} for k, v in TIER_EXPECTED.items()], "mechanism_bucket_records": []}}
    rows = []
    for (tier, previous), expected in MECHANISM_EXPECTED.items():
        artifacts["n10aw_mechanism_decomposition_artifact"]["frontier_tier_delta_records"].append({"tier_bucket": tier, "new_span_hits_vs_previous_tier": expected["new"], "lost_previous_hits": 0})
        for bucket in ("before_gold_gap", "after_gold_gap", "already_reachable_late_rank", "other_bucketed"):
            rows.append({"tier_bucket": tier, "previous_tier_bucket": previous, "mechanism_bucket": bucket, "new_span_hit_case_count": expected[bucket]})
    # Deduplicate tier rows by keeping the later rows would break frontier extraction; use real simpler object.
    artifacts["n10aw_mechanism_decomposition_artifact"]["frontier_tier_delta_records"] = [
        {"tier_bucket": "baseline", "cumulative_span_hits": 9, "cumulative_top20_span_hits": 10, "lost_previous_hits": 0, "cost_bucket": "zero"},
        {"tier_bucket": "pm30", "cumulative_span_hits": 18, "cumulative_top20_span_hits": 22, "lost_previous_hits": 0, "cost_bucket": "low", "new_span_hits_vs_previous_tier": 9},
        {"tier_bucket": "before25_after75", "cumulative_span_hits": 20, "cumulative_top20_span_hits": 24, "lost_previous_hits": 0, "cost_bucket": "medium", "new_span_hits_vs_previous_tier": 2},
        {"tier_bucket": "pm75", "cumulative_span_hits": 21, "cumulative_top20_span_hits": 25, "lost_previous_hits": 0, "cost_bucket": "medium", "new_span_hits_vs_previous_tier": 1},
        {"tier_bucket": "pm200", "cumulative_span_hits": 25, "cumulative_top20_span_hits": 30, "lost_previous_hits": 0, "cost_bucket": "very_high", "new_span_hits_vs_previous_tier": 4},
    ]
    artifacts["n10aw_mechanism_decomposition_artifact"]["mechanism_bucket_records"] = rows
    _, f_ok = frontier_claim_records(artifacts)
    _, m_ok = mechanism_claim_records(artifacts)
    return f_ok and m_ok


def synthetic_mismatch() -> bool:
    artifacts = {"n10aw_mechanism_decomposition_artifact": {"frontier_tier_delta_records": [{"tier_bucket": "baseline", "cumulative_span_hits": 8, "cumulative_top20_span_hits": 10, "lost_previous_hits": 0, "cost_bucket": "zero"}], "mechanism_bucket_records": []}}
    _, f_ok = frontier_claim_records(artifacts)
    return not f_ok and status_for(True, True, f_ok, True, True, True, True) == "no_go_n10ax_frontier_or_mechanism_mismatch"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    frontier_rows, frontier_ok = frontier_claim_records(artifacts)
    mechanism_rows, mechanism_ok = mechanism_claim_records(artifacts)
    claim_rows, claim_ok = claim_boundary_records()
    forbidden_rows, forbidden_ok = forbidden_claim_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10ax_required_public_inputs_unavailable", "no_go_n10ax_frontier_or_mechanism_mismatch", "no_go_n10ax_privacy_or_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 5),
        check("frontier_claims", frontier_ok and len(frontier_rows) == 5 and frontier_rows[-1]["tier_bucket"] == "pm200" and frontier_rows[-1]["top10_span_overlap_count"] == 25),
        check("mechanism_claims", mechanism_ok and len(mechanism_rows) == 4 and mechanism_rows[-1]["before_gold_gap_count"] == 3 and mechanism_rows[-1]["after_gold_gap_count"] == 1),
        check("claim_boundary", claim_ok and claim_rows[0]["heldout_claim_bool"] is False and claim_rows[0]["runtime_default_claim_bool"] is False and claim_rows[0]["method_winner_claim_bool"] is False),
        check("forbidden_claims_false", forbidden_ok and all(r["claim_made_bool"] is False and r["claim_authorized_bool"] is False for r in forbidden_rows)),
        check("no_private_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["recompute_count"] == 0 and norecompute_rows[0]["new_variant_count"] == 0),
        check("synthetic_package_pass", synthetic_package_pass()),
        check("synthetic_mismatch", synthetic_mismatch()),
        check("stop_go", stop_go_records(True)[0]["n10ay_authorized"] is True and stop_go_records(True)[0]["same_scoped_n1_span_rows_read_authorized"] is True and stop_go_records(True)[0]["broad_private_read_authorized"] is False and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["new_variant_authorized"] is False),
        check("status_complete", status_for(True, True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AX cost-sensitive frontier claim package")
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
