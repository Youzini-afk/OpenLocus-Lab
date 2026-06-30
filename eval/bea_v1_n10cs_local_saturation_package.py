#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10cs_local_saturation_package.v1"
PHASE = "BEA-v1-N10CS Local Saturation Sweep Public Package"
STATUS_COMPLETE = "local_saturation_package_complete_n10ct_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10cs_required_public_inputs_unavailable",
    "no_go_n10cs_n10cr_chain_mismatch",
    "no_go_n10cs_privacy_or_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10cs_local_saturation_package/bea_v1_n10cs_local_saturation_package_report.json")
PUBLIC_INPUTS = {
    "n10cr_local_saturation_sweep_artifact": (Path("artifacts/bea_v1_n10cr_mechanism_guided_local_saturation_sweep/bea_v1_n10cr_mechanism_guided_local_saturation_sweep_report.json"), "mechanism_guided_local_saturation_sweep_complete_n10cs_authorized"),
    "n10cq_mechanism_decomposition_artifact": (Path("artifacts/bea_v1_n10cq_refined_hybrid_mechanism_decomposition/bea_v1_n10cq_refined_hybrid_mechanism_decomposition_report.json"), "refined_hybrid_mechanism_decomposition_complete_n10cr_authorized"),
    "n10cp_refined_adapter_package_artifact": (Path("artifacts/bea_v1_n10cp_refined_hybrid_adapter_smoke_package/bea_v1_n10cp_refined_hybrid_adapter_smoke_package_report.json"), "refined_hybrid_adapter_package_complete_n10cq_authorized"),
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
    "variant_bucket", "package_bucket", "positive_result_bucket", "residual_bucket", "saturation_bucket",
    "boundary_bucket", "no_recompute_boundary_bucket", "n10ct_handoff_bucket", "authorization", "next_allowed_phase",
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
        rows.append({"anonymous_input_artifact_id": f"n10csin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def find_variant(artifact: dict[str, Any], variant: str) -> dict[str, Any]:
    for row in artifact.get("variant_result_records", []):
        if isinstance(row, dict) and row.get("variant_bucket") == variant:
            return row
    return {}


def first_record(artifact: dict[str, Any], key: str) -> dict[str, Any]:
    rows = artifact.get(key, [])
    return rows[0] if isinstance(rows, list) and rows and isinstance(rows[0], dict) else {}


def package_records(n10cr: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], bool]:
    refined = find_variant(n10cr, "anchor_refined_top2_pm200_short75_225")
    pm200 = find_variant(n10cr, "anchor_pm200_all_spans")
    positive = find_variant(n10cr, "top2_pm300_short75_225")
    saturation = first_record(n10cr, "saturation_decision_records")
    ok = (
        len(n10cr.get("variant_result_records", [])) == 8
        and refined.get("top10_span_overlap_count") == 25 and refined.get("top20_span_overlap_count") == 31
        and refined.get("cost_proxy_top10") == 3200 and refined.get("cost_proxy_top20") == 6200
        and pm200.get("top10_span_overlap_count") == 25 and pm200.get("top20_span_overlap_count") == 30
        and pm200.get("cost_proxy_top10") == 4000 and pm200.get("cost_proxy_top20") == 8000
        and positive.get("top10_span_overlap_count") == 26 and positive.get("top20_span_overlap_count") == 32
        and positive.get("cost_proxy_top10") == 3600 and positive.get("cost_proxy_top20") == 6600
        and positive.get("lost_refined_top10_hits") == 0
        and positive.get("candidate_pool_changed_bool") is False and positive.get("candidate_order_changed_bool") is False
        and saturation.get("saturation_bucket") == "local_window_not_saturated"
        and saturation.get("overall_saturation_bool") is False
        and saturation.get("rank_file_reach_pivot_allowed_next_bool") is False
    )
    local_package = [{"anonymous_local_saturation_package_id": "n10cspackage0000", "package_bucket": "n10cr_local_saturation_sweep_public_package", "n10cr_status_complete_bool": n10cr.get("status") == "mechanism_guided_local_saturation_sweep_complete_n10cs_authorized", "fixed_variant_count": len(n10cr.get("variant_result_records", [])), "refined_anchor_top10_span_overlap_count": refined.get("top10_span_overlap_count"), "refined_anchor_top20_span_overlap_count": refined.get("top20_span_overlap_count"), "refined_anchor_cost_proxy_top10": refined.get("cost_proxy_top10"), "refined_anchor_cost_proxy_top20": refined.get("cost_proxy_top20"), "pm200_all_spans_top10_span_overlap_count": pm200.get("top10_span_overlap_count"), "pm200_all_spans_top20_span_overlap_count": pm200.get("top20_span_overlap_count"), "pm200_all_spans_cost_proxy_top10": pm200.get("cost_proxy_top10"), "pm200_all_spans_cost_proxy_top20": pm200.get("cost_proxy_top20"), "package_consistent_bool": ok}]
    positive_rows = [{"anonymous_positive_result_id": "n10cspositive0000", "positive_result_bucket": "top2_pm300_short75_225_local_window_positive", "variant_bucket": "top2_pm300_short75_225", "top10_span_overlap_count": positive.get("top10_span_overlap_count"), "top20_span_overlap_count": positive.get("top20_span_overlap_count"), "cost_proxy_top10": positive.get("cost_proxy_top10"), "cost_proxy_top20": positive.get("cost_proxy_top20"), "delta_top10_vs_refined": positive.get("delta_top10_vs_refined"), "delta_top20_vs_refined": positive.get("delta_top20_vs_refined"), "lost_refined_top10_hits": positive.get("lost_refined_top10_hits"), "candidate_pool_changed_bool": positive.get("candidate_pool_changed_bool"), "candidate_order_changed_bool": positive.get("candidate_order_changed_bool"), "positive_result_verified_bool": positive.get("top10_span_overlap_count") == 26 and positive.get("top20_span_overlap_count") == 32}]
    residual_rows = [{"anonymous_residual_package_id": "n10csresidual0000", "residual_bucket": "positive_variant_residuals", "variant_bucket": "top2_pm300_short75_225", "file_not_in_top10_remaining_count": positive.get("file_not_in_top10_remaining_count"), "same_file_no_span_overlap_remaining_count": positive.get("same_file_no_span_overlap_remaining_count"), "span_overlap_beyond_top10_remaining_count": positive.get("span_overlap_beyond_top10_remaining_count"), "same_file_no_span_overlap_reduced_from_refined_count": 1 if positive.get("same_file_no_span_overlap_remaining_count") == 8 and refined.get("same_file_no_span_overlap_remaining_count") == 9 else 0, "file_not_in_top10_remains_primary_bool": positive.get("file_not_in_top10_remaining_count") == 167}]
    return local_package, positive_rows + [{"anonymous_positive_result_id": "n10cssaturation0000", "positive_result_bucket": "saturation_decision", "saturation_bucket": saturation.get("saturation_bucket"), "overall_saturation_bool": saturation.get("overall_saturation_bool"), "max_top10_span_overlap_count": saturation.get("max_top10_span_overlap_count"), "max_top20_span_overlap_count": saturation.get("max_top20_span_overlap_count"), "rank_file_reach_pivot_allowed_next_bool": saturation.get("rank_file_reach_pivot_allowed_next_bool")}], residual_rows, ok


def boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_boundary_id": "n10csboundary0000", "boundary_bucket": "public_package_no_broad_claims", "private_read_count": 0, "recompute_count": 0, "runtime_default_authorized_bool": False, "existing_evaluator_hook_authorized_bool": False, "heldout_generalization_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "candidate_add_remove_reorder_authorized_bool": False, "rank_file_promotion_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "selector_reranker_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_downstream_authorized_bool": False, "privacy_boundary_complete_bool": True}], True


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10csnorecompute0000", "no_recompute_boundary_bucket": "public_package_only", "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "runtime_default_promotion_count": 0, "candidate_generation_count": 0, "candidate_add_remove_reorder_count": 0, "adaptive_tuning_count": 0, "rank_file_promotion_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10ct_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ct_handoff_id": "n10cshandoff0000", "n10ct_handoff_bucket": "n10ct_next_exploration_authorized" if complete else "n10ct_not_authorized", "n10ct_authorized_bool": complete, "next_exploration_bucket": "around_top2_pm300_short75_225" if complete else "none", "adapter_smoke_or_bounded_pm300_neighborhood_allowed_bool": complete, "runtime_default_authorized_bool": False, "existing_evaluator_hook_authorized_bool": False, "heldout_generalization_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "candidate_add_remove_reorder_authorized_bool": False, "rank_file_promotion_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_downstream_authorized_bool": False}]


def gate_records(input_ok: bool, package_ok: bool, boundary_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("n10cr_package_facts", package_ok), ("privacy_claim_boundary", boundary_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ct_authorized" if complete else "n10ct_not_authorized", "next_allowed_phase": "BEA-v1-N10CT Exploration Around top2_pm300_short75_225" if complete else "none_until_local_saturation_package_valid", "next_allowed_scope_bucket": "adapter_smoke_or_bounded_pm300_neighborhood_oracle_scoped" if complete else "no_next_phase", "n10ct_authorized": complete, "runtime_or_default_authorized": False, "existing_evaluator_hook_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_add_remove_reorder_authorized": False, "rank_file_promotion_authorized": False, "adaptive_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, package_ok: bool, boundary_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10cs_required_public_inputs_unavailable"
    if not package_ok:
        return "no_go_n10cs_n10cr_chain_mismatch"
    if not boundary_ok or not norecompute_ok:
        return "no_go_n10cs_privacy_or_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    n10cr = artifacts.get("n10cr_local_saturation_sweep_artifact", {})
    package_rows, positive_rows, residual_rows, package_ok = package_records(n10cr)
    boundary_rows, boundary_ok = boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, package_ok, boundary_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_local_saturation_package_only", "generated_by": "bea_v1_n10cs_local_saturation_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "local_saturation_package_records": package_rows, "positive_result_package_records": positive_rows, "residual_package_records": residual_rows, "boundary_records": boundary_rows, "no_private_recompute_records": norecompute_rows, "n10ct_handoff_records": n10ct_handoff_records(complete), "gate_records": gate_records(input_ok, package_ok, boundary_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10ct_handoff_records"] = n10ct_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, package_ok, boundary_ok, norecompute_ok, scanner_ok)
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
    package_rows, positive_rows, residual_rows, package_ok = package_records(artifacts.get("n10cr_local_saturation_sweep_artifact", {}))
    boundary_rows, boundary_ok = boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10cs_required_public_inputs_unavailable", "no_go_n10cs_n10cr_chain_mismatch", "no_go_n10cs_privacy_or_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects", scan_summary({"path": "x"})["status"] == "fail" and scan_summary({"safe": "private/file.jsonl"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 3),
        check("package_facts", package_ok and package_rows[0]["fixed_variant_count"] == 8),
        check("positive_result", positive_rows[0]["top10_span_overlap_count"] == 26 and positive_rows[0]["top20_span_overlap_count"] == 32 and positive_rows[0]["lost_refined_top10_hits"] == 0),
        check("saturation", positive_rows[1]["saturation_bucket"] == "local_window_not_saturated" and positive_rows[1]["overall_saturation_bool"] is False),
        check("residual", residual_rows[0]["file_not_in_top10_remaining_count"] == 167 and residual_rows[0]["same_file_no_span_overlap_remaining_count"] == 8 and residual_rows[0]["span_overlap_beyond_top10_remaining_count"] == 12),
        check("boundary", boundary_ok and boundary_rows[0]["runtime_default_authorized_bool"] is False and boundary_rows[0]["rank_file_promotion_authorized_bool"] is False),
        check("no_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["recompute_count"] == 0),
        check("synthetic_mismatch", status_for(True, True, False, True, True) == "no_go_n10cs_n10cr_chain_mismatch"),
        check("false_flags", stop_go_records(True)[0]["n10ct_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["candidate_generation_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10CS local saturation public package")
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
