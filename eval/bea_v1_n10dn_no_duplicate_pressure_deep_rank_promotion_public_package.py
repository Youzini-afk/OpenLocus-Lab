#!/usr/bin/env python3
"""BEA-v1-N10DN No-Duplicate-Pressure Deep-Rank Promotion Public Package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


STATUS_PASS = "no_duplicate_pressure_deep_rank_promotion_public_package_complete_n10do_authorized"
STATUS_NO_INPUTS = "no_go_n10dn_required_public_inputs_unavailable"
STATUS_CHAIN = "no_go_n10dn_chain_or_metric_mismatch"
STATUS_CLAIM = "no_go_n10dn_claim_boundary_invalid"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"

STATUS_VOCAB = {STATUS_PASS, STATUS_NO_INPUTS, STATUS_CHAIN, STATUS_CLAIM, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_N10DM = ROOT / "artifacts" / "bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke" / "bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke_report.json"
DEFAULT_N10DL = ROOT / "artifacts" / "bea_v1_n10dl_n10t_file_reach_residual_analysis" / "bea_v1_n10dl_n10t_file_reach_residual_analysis_report.json"
DEFAULT_N10DK = ROOT / "artifacts" / "bea_v1_n10dk_n10t_order_rank_promotion_public_package" / "bea_v1_n10dk_n10t_order_rank_promotion_public_package_report.json"
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10dn_no_duplicate_pressure_deep_rank_promotion_public_package" / "bea_v1_n10dn_no_duplicate_pressure_deep_rank_promotion_public_package_report.json"

FORBIDDEN_KEYS = {
    "path", "paths", "filename", "filenames", "private_path", "private_filename", "source_path",
    "span", "spans", "line", "lines", "snippet", "snippets", "content", "candidate_list",
    "candidates", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank",
    "repo_id", "task_id", "hash", "provider_payload", "raw_diff",
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/"),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt)"),
    re.compile(r"[0-9a-f]{32,}", re.I),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10DN public package")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--n10dm-artifact", default=str(DEFAULT_N10DM))
    parser.add_argument("--n10dl-artifact", default=str(DEFAULT_N10DL))
    parser.add_argument("--n10dk-artifact", default=str(DEFAULT_N10DK))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    return parser.parse_args(argv)


def scan_summary(obj: Any) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def walk(node: Any, key: str = "") -> None:
        if key in FORBIDDEN_KEYS:
            findings.append({"bucket": "forbidden_key", "key_bucket": key})
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, str(k))
        elif isinstance(node, list):
            for item in node:
                walk(item, key)
        elif isinstance(node, str):
            for pat in FORBIDDEN_VALUE_PATTERNS:
                if pat.search(node):
                    findings.append({"bucket": "forbidden_value", "key_bucket": key or "value"})
                    break

    walk(obj)
    return {"status": "fail" if findings else "pass", "forbidden_finding_count": len(findings), "finding_buckets": findings[:20]}


def load_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), "present"
    except FileNotFoundError:
        return None, "missing"
    except Exception:
        return None, "invalid"


def input_artifact_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    specs = [
        ("n10dm_deep_rank_smoke", Path(args.n10dm_artifact), "no_duplicate_pressure_deep_rank_promotion_smoke_complete_n10dn_authorized"),
        ("n10dl_residual_analysis", Path(args.n10dl_artifact), "n10t_file_reach_residual_analysis_complete_n10dm_authorized"),
        ("n10dk_rank_promotion_package", Path(args.n10dk_artifact), "n10t_order_rank_promotion_public_package_complete_n10dl_authorized"),
    ]
    records: list[dict[str, Any]] = []
    loaded: dict[str, Any] = {}
    ok = True
    for idx, (bucket, path, expected) in enumerate(specs):
        data, state = load_json(path)
        loaded[bucket] = data or {}
        actual = str(data.get("status", "")) if data else ""
        matched = state == "present" and actual == expected
        ok = ok and matched
        records.append({
            "anonymous_input_artifact_id": f"n10dnin{idx:04d}",
            "artifact_bucket": bucket,
            "load_status_bucket": state,
            "expected_status_bucket": expected,
            "actual_status_bucket": actual or "unavailable",
            "status_match_bool": matched,
            "public_artifact_bool": True,
        })
    return records, loaded, ok


def result_map(n10dm: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(r.get("variant_bucket")): r for r in n10dm.get("variant_result_records", [])}


def package_summary_records(n10dm: dict[str, Any]) -> list[dict[str, Any]]:
    vm = result_map(n10dm)
    anchor = vm.get("anchor_n10t_order", {})
    decision = (n10dm.get("decision_summary_records") or [{}])[0]
    harm = (n10dm.get("harm_summary_records") or [{}])[0]
    return [{
        "anonymous_package_summary_id": "n10dnsummary0000",
        "source_status_bucket": str(n10dm.get("status", "unavailable")),
        "source_forbidden_scan_bucket": str(n10dm.get("forbidden_scan", {}).get("status", "unavailable")),
        "variant_count": len(n10dm.get("variant_result_records", [])),
        "anchor_file_top10_count": anchor.get("top10_file_reach_count"),
        "anchor_file_top20_count": anchor.get("top20_file_reach_count"),
        "anchor_projected_span_top10_count": anchor.get("top10_projected_span_overlap_count"),
        "anchor_projected_span_top20_count": anchor.get("top20_projected_span_overlap_count"),
        "positive_variant_count": decision.get("deep_rank_probe_positive_count"),
        "span_projection_positive_count": decision.get("span_projection_positive_count"),
        "harmful_variant_count": decision.get("deep_rank_probe_harmful_count"),
        "max_lost_anchor_file_top10_hits": harm.get("max_lost_anchor_file_top10_hits"),
        "max_lost_anchor_span_top10_hits": harm.get("max_lost_anchor_span_top10_hits"),
        "package_consistent_bool": anchor.get("top10_file_reach_count") == 34 and anchor.get("top20_file_reach_count") == 44 and anchor.get("top10_projected_span_overlap_count") == 30 and anchor.get("top20_projected_span_overlap_count") == 36 and decision.get("deep_rank_probe_positive_count") == 0 and decision.get("deep_rank_probe_harmful_count") == 5,
    }]


def negative_variant_records(n10dm: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for idx, row in enumerate(n10dm.get("variant_result_records", [])):
        records.append({
            "anonymous_variant_package_id": f"n10dnvar{idx:04d}",
            "variant_bucket": row.get("variant_bucket"),
            "top10_file_reach_count": row.get("top10_file_reach_count"),
            "top20_file_reach_count": row.get("top20_file_reach_count"),
            "top10_projected_span_overlap_count": row.get("top10_projected_span_overlap_count"),
            "top20_projected_span_overlap_count": row.get("top20_projected_span_overlap_count"),
            "lost_anchor_file_top10_hits": row.get("lost_anchor_file_top10_hits"),
            "lost_anchor_span_top10_hits": row.get("lost_anchor_span_top10_hits"),
            "recovered_rank11_20_residual_count": row.get("recovered_rank11_20_residual_count"),
            "decision_bucket": row.get("decision_bucket"),
        })
    return records


def closure_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_closure_id": "n10dnclosure0000",
        "closure_bucket": "fixed_deep_rank_promotion_line_closed_without_new_observable_signal",
        "negative_result_bool": True,
        "further_fixed_deep_rank_promotion_authorized_bool": False,
        "next_mechanism_bucket": "candidate_pool_absence_source_acquisition_audit",
        "candidate_pool_absence_residual_count": 161,
        "useful_negative_research_bool": True,
    }]


def boundary_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_boundary_id": "n10dnboundary0000",
        "package_boundary_bucket": "public_only_no_recompute_no_private_read",
        "private_read_count": 0,
        "recompute_count": 0,
        "runtime_default_claim_bool": False,
        "selector_reranker_claim_bool": False,
        "candidate_generation_claim_bool": False,
        "method_winner_claim_bool": False,
        "downstream_value_claim_bool": False,
        "heldout_generalization_claim_bool": False,
        "broad_private_read_claim_bool": False,
    }]


def stop_go_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_stop_go_id": "n10dnstop0000",
        "next_allowed_phase_bucket": "BEA-v1-N10DO Candidate-Pool Absence Source Acquisition Mechanism Audit",
        "n10do_candidate_pool_absence_audit_authorized_bool": True,
        "further_fixed_deep_rank_promotion_authorized_bool": False,
        "runtime_default_authorized_bool": False,
        "heldout_generalization_authorized_bool": False,
        "retrieval_rerun_authorized_bool": False,
        "candidate_generation_materialization_authorized_bool": False,
        "candidate_add_remove_authorized_bool": False,
        "selector_reranker_authorized_bool": False,
        "p5_v1a_authorized_bool": False,
        "adaptive_tuning_authorized_bool": False,
        "method_downstream_claim_authorized_bool": False,
        "broad_private_read_authorized_bool": False,
    }]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    inputs, loaded, inputs_ok = input_artifact_records(args)
    n10dm = loaded.get("n10dm_deep_rank_smoke", {})
    summary = package_summary_records(n10dm)
    summary_ok = bool(summary[0].get("package_consistent_bool"))
    status = STATUS_PASS if inputs_ok and summary_ok else (STATUS_NO_INPUTS if not inputs_ok else STATUS_CHAIN)
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dn_deep_rank_public_package_v1",
        "phase_bucket": "BEA-v1-N10DN No-Duplicate-Pressure Deep-Rank Promotion Public Package",
        "status": status,
        "input_artifact_records": inputs,
        "package_summary_records": summary,
        "variant_package_records": negative_variant_records(n10dm),
        "fixed_deep_rank_promotion_closure_records": closure_records(),
        "privacy_boundary_records": boundary_records(),
        "no_private_recompute_records": [{
            "anonymous_no_private_recompute_id": "n10dnno0000",
            "private_read_count": 0,
            "recompute_count": 0,
            "new_variant_count": 0,
            "public_artifact_only_bool": True,
        }],
        "n10do_handoff_records": [{
            "anonymous_handoff_id": "n10dnhandoff0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DO Candidate-Pool Absence Source Acquisition Mechanism Audit",
            "n10do_candidate_pool_absence_audit_authorized_bool": True,
            "same_source_public_package_bool": True,
            "broad_private_read_authorized_bool": False,
            "runtime_default_authorized_bool": False,
            "retrieval_rerun_authorized_bool": False,
            "candidate_generation_materialization_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "method_downstream_claim_authorized_bool": False,
        }],
        "gate_records": [
            {"anonymous_gate_id": "n10dngate0000", "gate_bucket": "inputs_present", "gate_passed_bool": inputs_ok},
            {"anonymous_gate_id": "n10dngate0001", "gate_bucket": "source_status_complete", "gate_passed_bool": n10dm.get("status") == "no_duplicate_pressure_deep_rank_promotion_smoke_complete_n10dn_authorized"},
            {"anonymous_gate_id": "n10dngate0002", "gate_bucket": "negative_metrics_match", "gate_passed_bool": summary_ok},
            {"anonymous_gate_id": "n10dngate0003", "gate_bucket": "public_only_no_recompute", "gate_passed_bool": True},
        ],
        "stop_go_records": stop_go_records(),
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def write_report(report: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_self_test() -> int:
    tests: list[tuple[str, bool]] = []
    tests.append(("status_vocab", STATUS_PASS in STATUS_VOCAB and STATUS_FAIL_SCAN in STATUS_VOCAB))
    try:
        parse_args(["--bad", "secret"])
        tests.append(("safe_parser", False))
    except SystemExit as exc:
        tests.append(("safe_parser", exc.code == 2))
    tests.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    tests.append(("scanner_safe", scan_summary({"bucket": "aggregate_only"})["status"] == "pass"))
    fake = {
        "status": "no_duplicate_pressure_deep_rank_promotion_smoke_complete_n10dn_authorized",
        "forbidden_scan": {"status": "pass"},
        "variant_result_records": [
            {"variant_bucket": "anchor_n10t_order", "top10_file_reach_count": 34, "top20_file_reach_count": 44, "top10_projected_span_overlap_count": 30, "top20_projected_span_overlap_count": 36},
        ],
        "decision_summary_records": [{"deep_rank_probe_positive_count": 0, "span_projection_positive_count": 0, "deep_rank_probe_harmful_count": 5}],
        "harm_summary_records": [{"max_lost_anchor_file_top10_hits": 14, "max_lost_anchor_span_top10_hits": 10}],
    }
    tests.append(("summary_pass", package_summary_records(fake)[0]["package_consistent_bool"] is True))
    bad = json.loads(json.dumps(fake))
    bad["decision_summary_records"][0]["deep_rank_probe_harmful_count"] = 4
    tests.append(("summary_mismatch", package_summary_records(bad)[0]["package_consistent_bool"] is False))
    tests.append(("closure_false", closure_records()[0]["further_fixed_deep_rank_promotion_authorized_bool"] is False))
    stop = stop_go_records()[0]
    tests.append(("handoff", stop["n10do_candidate_pool_absence_audit_authorized_bool"] is True))
    tests.append(("false_runtime", stop["runtime_default_authorized_bool"] is False))
    tests.append(("false_retrieval", stop["retrieval_rerun_authorized_bool"] is False))
    tests.append(("false_generation", stop["candidate_generation_materialization_authorized_bool"] is False))
    tests.append(("false_fixed_deep", stop["further_fixed_deep_rank_promotion_authorized_bool"] is False))
    passed = sum(1 for _, ok in tests if ok)
    for name, ok in tests:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"self_test_passed={passed == len(tests)} ({passed}/{len(tests)} checks)")
    return 0 if passed == len(tests) else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return run_self_test()
    report = build_report(args)
    write_report(report, Path(args.out))
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
