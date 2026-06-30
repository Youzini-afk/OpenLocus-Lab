#!/usr/bin/env python3
"""BEA-v1-N10DN-R Corrected Deep-Rank Promotion Public Package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn


STATUS_PASS = "corrected_deep_rank_promotion_public_package_complete_n10dor_authorized"
STATUS_NO_INPUTS = "no_go_n10dnr_required_public_inputs_unavailable"
STATUS_CHAIN = "no_go_n10dnr_chain_or_metric_mismatch"
STATUS_CLAIM = "no_go_n10dnr_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_PASS, STATUS_NO_INPUTS, STATUS_CHAIN, STATUS_CLAIM, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_N10DMR = ROOT / "artifacts" / "bea_v1_n10dmr_corrected_suffix_safe_deep_rank_promotion_smoke" / "bea_v1_n10dmr_corrected_suffix_safe_deep_rank_promotion_smoke_report.json"
DEFAULT_N10DO = ROOT / "artifacts" / "bea_v1_n10do_candidate_pool_absence_source_acquisition_audit" / "bea_v1_n10do_candidate_pool_absence_source_acquisition_audit_report.json"
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10dnr_corrected_deep_rank_promotion_public_package" / "bea_v1_n10dnr_corrected_deep_rank_promotion_public_package_report.json"

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
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10DN-R public package")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--n10dmr-artifact", default=str(DEFAULT_N10DMR))
    parser.add_argument("--n10do-artifact", default=str(DEFAULT_N10DO))
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
        ("n10dmr_corrected_smoke", Path(args.n10dmr_artifact), "suffix_safe_deep_rank_promotion_smoke_complete_n10dnr_authorized"),
        ("n10do_path_correction_context", Path(args.n10do_artifact), "candidate_pool_absence_path_normalization_correction_complete_n10dmr_authorized"),
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
            "anonymous_input_artifact_id": f"n10dnrin{idx:04d}",
            "artifact_bucket": bucket,
            "load_status_bucket": state,
            "expected_status_bucket": expected,
            "actual_status_bucket": actual or "unavailable",
            "status_match_bool": matched,
            "public_artifact_bool": True,
        })
    return records, loaded, ok


def result_map(n10dmr: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(r.get("variant_bucket")): r for r in n10dmr.get("corrected_variant_result_records", [])}


def package_summary_records(n10dmr: dict[str, Any]) -> list[dict[str, Any]]:
    vm = result_map(n10dmr)
    anchor = vm.get("anchor_n10t_order", {})
    decision = (n10dmr.get("decision_summary_records") or [{}])[0]
    return [{
        "anonymous_package_summary_id": "n10dnrsummary0000",
        "source_status_bucket": str(n10dmr.get("status", "unavailable")),
        "source_forbidden_scan_bucket": str(n10dmr.get("forbidden_scan", {}).get("status", "unavailable")),
        "matching_rule_bucket": "suffix_safe_primary",
        "variant_count": len(n10dmr.get("corrected_variant_result_records", [])),
        "anchor_file_top10_count": anchor.get("top10_file_reach_count"),
        "anchor_file_top20_count": anchor.get("top20_file_reach_count"),
        "anchor_projected_span_top10_count": anchor.get("top10_projected_span_overlap_count"),
        "anchor_projected_span_top20_count": anchor.get("top20_projected_span_overlap_count"),
        "positive_variant_count": decision.get("positive_variant_count"),
        "harmful_variant_count": decision.get("harmful_variant_count"),
        "old_negative_conclusion_still_holds_bool": decision.get("old_negative_conclusion_still_holds_bool"),
        "package_consistent_bool": anchor.get("top10_file_reach_count") == 44
        and anchor.get("top20_file_reach_count") == 58
        and anchor.get("top10_projected_span_overlap_count") == 39
        and anchor.get("top20_projected_span_overlap_count") == 49
        and decision.get("positive_variant_count") == 0
        and decision.get("harmful_variant_count") == 5
        and decision.get("old_negative_conclusion_still_holds_bool") is True,
    }]


def suffix_correction_summary_records(n10dmr: dict[str, Any]) -> list[dict[str, Any]]:
    sensitivity = {str(r.get("variant_bucket")): r for r in n10dmr.get("exact_vs_suffix_sensitivity_records", [])}
    anchor = sensitivity.get("anchor_n10t_order", {})
    return [{
        "anonymous_suffix_summary_id": "n10dnrsuffix0000",
        "prior_exact_file_top10_count": anchor.get("exact_top10_file_reach_count"),
        "prior_exact_file_top20_count": anchor.get("exact_top20_file_reach_count"),
        "suffix_safe_file_top10_count": anchor.get("suffix_top10_file_reach_count"),
        "suffix_safe_file_top20_count": anchor.get("suffix_top20_file_reach_count"),
        "suffix_minus_exact_top10_count": anchor.get("suffix_minus_exact_top10_file_reach_count"),
        "suffix_minus_exact_top20_count": anchor.get("suffix_minus_exact_top20_file_reach_count"),
        "suffix_safe_supersedes_exact_for_file_reach_bool": True,
    }]


def negative_result_records(n10dmr: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for idx, row in enumerate(n10dmr.get("corrected_variant_result_records", [])):
        if row.get("variant_bucket") == "anchor_n10t_order":
            continue
        records.append({
            "anonymous_negative_result_id": f"n10dnrneg{idx:04d}",
            "variant_bucket": row.get("variant_bucket"),
            "top10_file_reach_count": row.get("top10_file_reach_count"),
            "top20_file_reach_count": row.get("top20_file_reach_count"),
            "top10_projected_span_overlap_count": row.get("top10_projected_span_overlap_count"),
            "top20_projected_span_overlap_count": row.get("top20_projected_span_overlap_count"),
            "delta_top10_file_vs_anchor": row.get("delta_top10_file_vs_anchor"),
            "delta_top10_span_vs_anchor": row.get("delta_top10_span_vs_anchor"),
            "lost_anchor_file_top10_hits": row.get("lost_anchor_file_top10_hits"),
            "lost_anchor_span_top10_hits": row.get("lost_anchor_span_top10_hits"),
            "decision_bucket": row.get("decision_bucket"),
        })
    return records


def claim_boundary_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_claim_boundary_id": "n10dnrclaim0000",
        "allowed_claim_bucket": "corrected_suffix_safe_deep_rank_negative_package",
        "runtime_default_claim_bool": False,
        "heldout_generalization_claim_bool": False,
        "method_winner_claim_bool": False,
        "downstream_value_claim_bool": False,
        "retrieval_rerun_claim_bool": False,
        "candidate_generation_claim_bool": False,
    }]


def no_recompute_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_no_recompute_id": "n10dnrnorecomp0000",
        "private_read_count": 0,
        "recompute_count": 0,
        "retrieval_execution_count": 0,
        "candidate_generation_count": 0,
        "candidate_added_removed_count": 0,
        "selector_reranker_execution_count": 0,
    }]


def handoff_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_handoff_id": "n10dnrhandoff0000",
        "next_allowed_phase_bucket": "BEA-v1-N10DO-R Corrected Candidate-Pool Absence Source Mechanism Audit",
        "n10dor_corrected_absence_audit_authorized_bool": True,
        "design_or_audit_only_bool": True,
        "retrieval_authorized_bool": False,
        "candidate_generation_authorized_bool": False,
        "oracle_candidate_insertion_authorized_bool": False,
    }]


def stop_go_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_stop_go_id": "n10dnrstop0000",
        "next_allowed_phase_bucket": "BEA-v1-N10DO-R Corrected Candidate-Pool Absence Source Mechanism Audit",
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
    n10dmr = loaded.get("n10dmr_corrected_smoke", {})
    summary = package_summary_records(n10dmr)
    summary_ok = bool(summary[0].get("package_consistent_bool"))
    status = STATUS_PASS if inputs_ok and summary_ok else (STATUS_NO_INPUTS if not inputs_ok else STATUS_CHAIN)
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dnr_corrected_deep_rank_public_package_v1",
        "phase_bucket": "BEA-v1-N10DN-R Corrected Deep-Rank Promotion Public Package",
        "status": status,
        "input_artifact_records": inputs,
        "package_summary_records": summary,
        "suffix_correction_summary_records": suffix_correction_summary_records(n10dmr),
        "negative_result_records": negative_result_records(n10dmr),
        "claim_boundary_records": claim_boundary_records(),
        "privacy_boundary_records": [{
            "anonymous_privacy_id": "n10dnrprivacy0000",
            "public_aggregate_bucket_only_bool": True,
            "private_path_public_count": 0,
            "candidate_list_public_count": 0,
            "span_line_public_count": 0,
        }],
        "no_recompute_records": no_recompute_records(),
        "next_handoff_records": handoff_records(),
        "gate_records": [
            {"anonymous_gate_id": "n10dnrgate0000", "gate_bucket": "inputs_present", "gate_passed_bool": inputs_ok},
            {"anonymous_gate_id": "n10dnrgate0001", "gate_bucket": "package_summary_consistent", "gate_passed_bool": summary_ok},
            {"anonymous_gate_id": "n10dnrgate0002", "gate_bucket": "public_only_no_recompute", "gate_passed_bool": True},
        ],
        "stop_go_records": stop_go_records(),
    }
    scan = scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    return report


def run_self_tests() -> int:
    tests = 0
    assert STATUS_PASS in STATUS_VOCAB; tests += 1
    try:
        parse_args(["--unknown", "SECRET"])
    except SystemExit as exc:
        assert exc.code == 2
        tests += 1
    assert scan_summary({"path": "x"})["status"] == "fail"; tests += 1
    assert scan_summary({"safe_bucket": "aggregate_only"})["status"] == "pass"; tests += 1
    fake = {
        "status": "suffix_safe_deep_rank_promotion_smoke_complete_n10dnr_authorized",
        "forbidden_scan": {"status": "pass"},
        "corrected_variant_result_records": [
            {"variant_bucket": "anchor_n10t_order", "top10_file_reach_count": 44, "top20_file_reach_count": 58, "top10_projected_span_overlap_count": 39, "top20_projected_span_overlap_count": 49},
            {"variant_bucket": "v", "decision_bucket": "deep_rank_probe_harmful"},
        ],
        "decision_summary_records": [{"positive_variant_count": 0, "harmful_variant_count": 5, "old_negative_conclusion_still_holds_bool": True}],
        "exact_vs_suffix_sensitivity_records": [{"variant_bucket": "anchor_n10t_order", "exact_top10_file_reach_count": 34, "suffix_top10_file_reach_count": 44}],
    }
    assert package_summary_records(fake)[0]["package_consistent_bool"] is True; tests += 1
    bad = json.loads(json.dumps(fake)); bad["decision_summary_records"][0]["positive_variant_count"] = 1
    assert package_summary_records(bad)[0]["package_consistent_bool"] is False; tests += 1
    assert suffix_correction_summary_records(fake)[0]["suffix_safe_supersedes_exact_for_file_reach_bool"] is True; tests += 1
    assert len(negative_result_records(fake)) == 1; tests += 1
    assert no_recompute_records()[0]["private_read_count"] == 0; tests += 1
    assert stop_go_records()[0]["runtime_default_authorized_bool"] is False; tests += 1
    assert handoff_records()[0]["candidate_generation_authorized_bool"] is False; tests += 1
    assert claim_boundary_records()[0]["method_winner_claim_bool"] is False; tests += 1
    print(f"self-test passed: {tests}/12")
    return tests


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        run_self_tests()
        return 0
    report = build_report(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
