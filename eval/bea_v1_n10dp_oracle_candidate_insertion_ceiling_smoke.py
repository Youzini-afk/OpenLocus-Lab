#!/usr/bin/env python3
"""BEA-v1-N10DP Oracle Candidate-Insertion Ceiling Smoke."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn

STATUS_COMPLETE = "oracle_candidate_insertion_ceiling_smoke_complete_n10dq_authorized"
STATUS_NO_INPUTS = "no_go_n10dp_required_inputs_unavailable"
STATUS_PRIVATE_MISSING = "no_go_n10dp_private_span_rows_missing"
STATUS_ACCOUNTING = "no_go_n10dp_accounting_invalid"
STATUS_PRIVACY = "no_go_n10dp_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_INPUTS, STATUS_PRIVATE_MISSING, STATUS_ACCOUNTING, STATUS_PRIVACY, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRIVATE = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"
DEFAULT_N10DOR = ROOT / "artifacts" / "bea_v1_n10dor_corrected_candidate_pool_absence_source_audit" / "bea_v1_n10dor_corrected_candidate_pool_absence_source_audit_report.json"
DEFAULT_N10DNR = ROOT / "artifacts" / "bea_v1_n10dnr_corrected_deep_rank_promotion_public_package" / "bea_v1_n10dnr_corrected_deep_rank_promotion_public_package_report.json"
DEFAULT_N10DMR = ROOT / "artifacts" / "bea_v1_n10dmr_corrected_suffix_safe_deep_rank_promotion_smoke" / "bea_v1_n10dmr_corrected_suffix_safe_deep_rank_promotion_smoke_report.json"
DEFAULT_N10DO = ROOT / "artifacts" / "bea_v1_n10do_candidate_pool_absence_source_acquisition_audit" / "bea_v1_n10do_candidate_pool_absence_source_acquisition_audit_report.json"
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10dp_oracle_candidate_insertion_ceiling_smoke" / "bea_v1_n10dp_oracle_candidate_insertion_ceiling_smoke_report.json"

FORBIDDEN_KEYS = {"path", "paths", "filename", "filenames", "private_path", "private_filename", "source_path", "span", "spans", "line", "lines", "snippet", "snippets", "content", "candidate_list", "candidates", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "repo_id", "task_id", "hash", "provider_payload", "raw_diff"}
FORBIDDEN_VALUE_PATTERNS = [re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"), re.compile(r"/workspace/|/tmp/|/home/"), re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt)"), re.compile(r"[0-9a-f]{32,}", re.I)]

VARIANTS = [
    ("oracle_insert_gold_file_at_rank1", 1),
    ("oracle_insert_gold_file_at_rank5", 5),
    ("oracle_insert_gold_file_at_rank10", 10),
    ("oracle_append_gold_file_after_top10", 11),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10DP oracle ceiling smoke")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--private-span-rows", default=str(DEFAULT_PRIVATE))
    parser.add_argument("--n10dor-artifact", default=str(DEFAULT_N10DOR))
    parser.add_argument("--n10dnr-artifact", default=str(DEFAULT_N10DNR))
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


def input_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool]:
    specs = [
        ("n10dor_corrected_absence_audit", Path(args.n10dor_artifact), "corrected_candidate_pool_absence_source_audit_complete_n10dp_authorized"),
        ("n10dnr_corrected_deep_rank_package", Path(args.n10dnr_artifact), "corrected_deep_rank_promotion_public_package_complete_n10dor_authorized"),
        ("n10dmr_corrected_deep_rank_smoke", Path(args.n10dmr_artifact), "suffix_safe_deep_rank_promotion_smoke_complete_n10dnr_authorized"),
        ("n10do_historical_absence_audit", Path(args.n10do_artifact), "candidate_pool_absence_path_normalization_correction_complete_n10dmr_authorized"),
    ]
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(specs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        matched = state == "present" and actual == expected
        ok = ok and matched
        records.append({"anonymous_input_artifact_id": f"n10dpin{idx:04d}", "artifact_bucket": bucket, "load_status_bucket": state, "expected_status_bucket": expected, "actual_status_bucket": actual or "unavailable", "status_match_bool": matched, "public_artifact_bool": True})
    return records, ok


def load_rows(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return [], "missing"
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return rows, "present" if all(isinstance(r, dict) for r in rows) else "invalid"
    except Exception:
        return [], "invalid"


def norm(value: object) -> str:
    return str(value or "").replace("\\", "/").strip("/")


def n10t_order(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = [item for idx, item in enumerate(evidence, 1) if idx <= 20]
    extra = [item for idx, item in enumerate(evidence, 1) if idx > 20]
    return list(extra) + primary[:4] + primary[4:]


def suffix_match(candidate: str, gold: str) -> bool:
    candidate = norm(candidate)
    gold = norm(gold)
    return bool(candidate and gold and (candidate == gold or candidate.endswith("/" + gold) or gold.endswith("/" + candidate)))


def event_file_hit(ev: dict[str, Any], golds: list[str]) -> bool:
    candidate = norm(ev.get("path"))
    return any(suffix_match(candidate, gold) for gold in golds)


def file_hit(order: list[dict[str, Any]], golds: list[str], limit: int) -> bool:
    return any(event_file_hit(ev, golds) for ev in order[:limit])


def absent_from_pool(order: list[dict[str, Any]], golds: list[str]) -> bool:
    return not any(event_file_hit(ev, golds) for ev in order)


def analyze(rows: list[dict[str, Any]]) -> dict[str, int]:
    usable = [r for r in rows if isinstance(r.get("p4_evidence"), list) and isinstance(r.get("gold_paths"), list)]
    top10_hit = 0
    top20_hit = 0
    absent = 0
    for row in usable:
        order = n10t_order(row["p4_evidence"])
        golds = [norm(g) for g in row.get("gold_paths", []) if norm(g)]
        if file_hit(order, golds, 10):
            top10_hit += 1
        if file_hit(order, golds, 20):
            top20_hit += 1
        if absent_from_pool(order, golds):
            absent += 1
    return {"usable_rows": len(usable), "top10_hit": top10_hit, "top10_miss": len(usable) - top10_hit, "top20_hit": top20_hit, "absent": absent}


def variant_results(anchor: dict[str, int]) -> list[dict[str, Any]]:
    records = []
    for idx, (variant, insertion_rank) in enumerate(VARIANTS):
        in_top10 = insertion_rank <= 10
        in_top20 = insertion_rank <= 20
        top10 = anchor["top10_hit"] + (anchor["absent"] if in_top10 else 0)
        top20 = anchor["top20_hit"] + (anchor["absent"] if in_top20 else 0)
        records.append({"anonymous_oracle_result_id": f"n10dporacle{idx:04d}", "oracle_variant_bucket": variant, "oracle_candidate_position_bucket": "within_top10" if in_top10 else "after_top10_within_top20", "upper_bound_top10_file_reach": top10, "upper_bound_top20_file_reach": top20, "increment_over_current_anchor_top10": top10 - anchor["top10_hit"], "increment_over_current_anchor_top20": top20 - anchor["top20_hit"], "affected_absent_pool_cases": anchor["absent"], "oracle_span_overlap_status_bucket": "not_evaluated_no_oracle_span", "oracle_ceiling_non_policy_bool": True})
    return records


def accounting_ok(a: dict[str, int]) -> bool:
    return a == {"usable_rows": 213, "top10_hit": 44, "top10_miss": 169, "top20_hit": 58, "absent": 141}


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    inputs, inputs_ok = input_records(args)
    rows, row_state = load_rows(Path(args.private_span_rows))
    anchor = analyze(rows) if row_state == "present" else {"usable_rows": 0, "top10_hit": 0, "top10_miss": 0, "top20_hit": 0, "absent": 0}
    ok = row_state == "present" and accounting_ok(anchor)
    status = STATUS_COMPLETE if inputs_ok and ok else (STATUS_NO_INPUTS if not inputs_ok else (STATUS_PRIVATE_MISSING if row_state != "present" else STATUS_ACCOUNTING))
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dp_oracle_ceiling_smoke_v1",
        "phase_bucket": "BEA-v1-N10DP Oracle Candidate-Insertion Ceiling Smoke",
        "status": status,
        "input_artifact_records": inputs,
        "private_input_intake_records": [{"anonymous_private_input_id": "n10dppriv0000", "private_input_bucket": "scoped_n1_span_rows", "load_status_bucket": row_state, "private_span_rows_read": len(rows), "private_content_used_for_oracle_ceiling_bool": row_state == "present"}],
        "oracle_variant_contract_records": [{"anonymous_oracle_contract_id": f"n10dpcontract{idx:04d}", "oracle_variant_bucket": variant, "synthetic_oracle_file_candidate_bool": True, "non_policy_upper_bound_bool": True, "retrieval_or_generation_used_bool": False, "oracle_candidate_identity_public_bool": False} for idx, (variant, _) in enumerate(VARIANTS)],
        "oracle_ceiling_result_records": variant_results(anchor),
        "span_metric_boundary_records": [{"anonymous_span_boundary_id": "n10dpspan0000", "span_metric_evaluated_bool": False, "oracle_span_overlap_status_bucket": "not_evaluated_no_oracle_span", "span_overlap_not_faked_bool": True}],
        "non_policy_boundary_records": [{"anonymous_non_policy_id": "n10dpnonpolicy0000", "oracle_ceiling_only_bool": True, "feasible_policy_claim_bool": False, "runtime_default_claim_bool": False, "method_winner_claim_bool": False, "downstream_claim_bool": False, "heldout_generalization_claim_bool": False}],
        "privacy_boundary_records": [{"anonymous_privacy_id": "n10dpprivacy0000", "public_aggregate_only_bool": True, "private_path_public_count": 0, "candidate_list_public_count": 0, "oracle_candidate_identity_public_count": 0, "raw_span_or_line_public_count": 0}],
        "no_forbidden_execution_records": [{"anonymous_no_execution_id": "n10dpnoexec0000", "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "real_candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_add_remove_from_real_pool_count": 0, "selector_reranker_execution_count": 0, "runtime_default_change_count": 0}],
        "n10dq_handoff_records": [{"anonymous_handoff_id": "n10dphandoff0000", "next_allowed_phase_bucket": "BEA-v1-N10DQ Oracle Candidate-Insertion Ceiling Public Package", "n10dq_public_package_authorized_bool": True, "retrieval_authorized_bool": False, "real_candidate_generation_authorized_bool": False}],
        "gate_records": [{"anonymous_gate_id": "n10dpgate0000", "gate_bucket": "inputs_present", "gate_passed_bool": inputs_ok}, {"anonymous_gate_id": "n10dpgate0001", "gate_bucket": "anchor_accounting_corrected_suffix_safe", "gate_passed_bool": ok}, {"anonymous_gate_id": "n10dpgate0002", "gate_bucket": "oracle_variants_4", "gate_passed_bool": len(VARIANTS) == 4}, {"anonymous_gate_id": "n10dpgate0003", "gate_bucket": "no_forbidden_execution", "gate_passed_bool": True}],
        "stop_go_records": [{"anonymous_stop_go_id": "n10dpstop0000", "next_allowed_phase_bucket": "BEA-v1-N10DQ Oracle Candidate-Insertion Ceiling Public Package", "n10dq_public_package_authorized_bool": status == STATUS_COMPLETE, "retrieval_authorized_bool": False, "rerun_authorized_bool": False, "source_acquisition_authorized_bool": False, "real_candidate_generation_authorized_bool": False, "selector_reranker_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_generalization_authorized_bool": False, "method_downstream_claim_authorized_bool": False, "p5_v1a_authorized_bool": False}],
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
    tests.append(("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_FAIL_SCAN in STATUS_VOCAB))
    try:
        parse_args(["--bad", "secret"])
        tests.append(("safe_parser", False))
    except SystemExit as exc:
        tests.append(("safe_parser", exc.code == 2))
    tests.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    tests.append(("scanner_safe", scan_summary({"bucket": "aggregate"})["status"] == "pass"))
    tests.append(("suffix", suffix_match("a/b/c", "b/c") is True))
    rows = [{"p4_evidence": [{"path": f"f{i}"} for i in range(1, 22)], "gold_paths": ["missing"]}]
    tests.append(("analyze_absent", analyze(rows)["absent"] == 1))
    anchor = {"usable_rows": 213, "top10_hit": 44, "top10_miss": 169, "top20_hit": 58, "absent": 141}
    vr = variant_results(anchor)
    tests.append(("rank1_ceiling", vr[0]["upper_bound_top10_file_reach"] == 185 and vr[0]["upper_bound_top20_file_reach"] == 199))
    tests.append(("after_top10", vr[3]["upper_bound_top10_file_reach"] == 44 and vr[3]["upper_bound_top20_file_reach"] == 199))
    tests.append(("accounting", accounting_ok(anchor)))
    tests.append(("span_not_faked", vr[0]["oracle_span_overlap_status_bucket"] == "not_evaluated_no_oracle_span"))
    tests.append(("variant_count", len(VARIANTS) == 4))
    tests.append(("stop_false", build_report(parse_args([]))["stop_go_records"][0]["retrieval_authorized_bool"] is False if DEFAULT_PRIVATE.exists() else True))
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
    return 0 if report["status"] == STATUS_COMPLETE else 1


if __name__ == "__main__":
    raise SystemExit(main())
