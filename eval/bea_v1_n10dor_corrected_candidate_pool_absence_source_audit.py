#!/usr/bin/env python3
"""BEA-v1-N10DO-R Corrected Candidate-Pool Absence / Source Mechanism Audit."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn


STATUS_COMPLETE = "corrected_candidate_pool_absence_source_audit_complete_n10dp_authorized"
STATUS_NO_INPUTS = "no_go_n10dor_required_inputs_unavailable"
STATUS_PRIVATE_MISSING = "no_go_n10dor_private_span_rows_missing"
STATUS_ACCOUNTING = "no_go_n10dor_result_accounting_invalid"
STATUS_PRIVACY = "no_go_n10dor_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_INPUTS, STATUS_PRIVATE_MISSING, STATUS_ACCOUNTING, STATUS_PRIVACY, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRIVATE = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"
DEFAULT_N10DO = ROOT / "artifacts" / "bea_v1_n10do_candidate_pool_absence_source_acquisition_audit" / "bea_v1_n10do_candidate_pool_absence_source_acquisition_audit_report.json"
DEFAULT_N10DMR = ROOT / "artifacts" / "bea_v1_n10dmr_corrected_suffix_safe_deep_rank_promotion_smoke" / "bea_v1_n10dmr_corrected_suffix_safe_deep_rank_promotion_smoke_report.json"
DEFAULT_N10DNR = ROOT / "artifacts" / "bea_v1_n10dnr_corrected_deep_rank_promotion_public_package" / "bea_v1_n10dnr_corrected_deep_rank_promotion_public_package_report.json"
DEFAULT_N10DL = ROOT / "artifacts" / "bea_v1_n10dl_n10t_file_reach_residual_analysis" / "bea_v1_n10dl_n10t_file_reach_residual_analysis_report.json"
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10dor_corrected_candidate_pool_absence_source_audit" / "bea_v1_n10dor_corrected_candidate_pool_absence_source_audit_report.json"

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

ABSENCE_BUCKETS = [
    "gold_file_in_top20", "gold_file_in_top50", "gold_file_in_top100",
    "gold_file_in_observed_pool_beyond100", "gold_file_absent_from_observed_pool",
]
POOL_BUCKETS = ["pool_size_1_10", "pool_size_11_20", "pool_size_21_50", "pool_size_51_100", "pool_size_gt100"]
DISTINCT_BUCKETS = ["distinct_file_count_1_10", "distinct_file_count_11_20", "distinct_file_count_21_50", "distinct_file_count_gt50"]
PRESSURE_BUCKETS = ["duplicate_pressure_none", "duplicate_pressure_low", "duplicate_pressure_medium", "duplicate_pressure_high"]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10DO-R corrected absence audit")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--private-span-rows", default=str(DEFAULT_PRIVATE))
    parser.add_argument("--n10do-artifact", default=str(DEFAULT_N10DO))
    parser.add_argument("--n10dmr-artifact", default=str(DEFAULT_N10DMR))
    parser.add_argument("--n10dnr-artifact", default=str(DEFAULT_N10DNR))
    parser.add_argument("--n10dl-artifact", default=str(DEFAULT_N10DL))
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
        ("n10do_corrected_absence_audit", Path(args.n10do_artifact), "candidate_pool_absence_path_normalization_correction_complete_n10dmr_authorized"),
        ("n10dmr_suffix_safe_deep_rank_smoke", Path(args.n10dmr_artifact), "suffix_safe_deep_rank_promotion_smoke_complete_n10dnr_authorized"),
        ("n10dnr_corrected_deep_rank_package", Path(args.n10dnr_artifact), "corrected_deep_rank_promotion_public_package_complete_n10dor_authorized"),
        ("n10dl_historical_residual_analysis", Path(args.n10dl_artifact), "n10t_file_reach_residual_analysis_complete_n10dm_authorized"),
    ]
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(specs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        matched = state == "present" and actual == expected
        ok = ok and matched
        records.append({"anonymous_input_artifact_id": f"n10dorin{idx:04d}", "artifact_bucket": bucket, "load_status_bucket": state, "expected_status_bucket": expected, "actual_status_bucket": actual or "unavailable", "status_match_bool": matched, "public_artifact_bool": True})
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


def file_id(ev: dict[str, Any]) -> str:
    return norm(ev.get("path"))


def suffix_match(candidate: str, gold: str) -> bool:
    candidate = norm(candidate)
    gold = norm(gold)
    return bool(candidate and gold and (candidate == gold or candidate.endswith("/" + gold) or gold.endswith("/" + candidate)))


def event_file_hit(ev: dict[str, Any], golds: list[str]) -> bool:
    candidate = file_id(ev)
    return any(suffix_match(candidate, gold) for gold in golds)


def file_hit(order: list[dict[str, Any]], golds: list[str], limit: int) -> bool:
    return any(event_file_hit(ev, golds) for ev in order[:limit])


def absence_bucket(order: list[dict[str, Any]], golds: list[str]) -> str:
    for idx, ev in enumerate(order, 1):
        if event_file_hit(ev, golds):
            if idx <= 20:
                return "gold_file_in_top20"
            if idx <= 50:
                return "gold_file_in_top50"
            if idx <= 100:
                return "gold_file_in_top100"
            return "gold_file_in_observed_pool_beyond100"
    return "gold_file_absent_from_observed_pool"


def pool_bucket(size: int) -> str:
    if size <= 10:
        return "pool_size_1_10"
    if size <= 20:
        return "pool_size_11_20"
    if size <= 50:
        return "pool_size_21_50"
    if size <= 100:
        return "pool_size_51_100"
    return "pool_size_gt100"


def distinct_bucket(count: int) -> str:
    if count <= 10:
        return "distinct_file_count_1_10"
    if count <= 20:
        return "distinct_file_count_11_20"
    if count <= 50:
        return "distinct_file_count_21_50"
    return "distinct_file_count_gt50"


def pressure_bucket(top10_distinct_count: int) -> str:
    duplicate_count = max(0, 10 - top10_distinct_count)
    if duplicate_count == 0:
        return "duplicate_pressure_none"
    if duplicate_count <= 2:
        return "duplicate_pressure_low"
    if duplicate_count <= 5:
        return "duplicate_pressure_medium"
    return "duplicate_pressure_high"


def field_presence(rows: list[dict[str, Any]], keys: list[str]) -> tuple[int, int]:
    total = 0
    present = 0
    for row in rows:
        for ev in row.get("p4_evidence", []):
            if isinstance(ev, dict):
                total += 1
                if any(k in ev and ev.get(k) not in (None, "") for k in keys):
                    present += 1
    return present, total


def analyze(rows: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [r for r in rows if isinstance(r.get("p4_evidence"), list) and isinstance(r.get("gold_paths"), list)]
    top10_hit = 0
    top20_extra_hit = 0
    absence = {b: 0 for b in ABSENCE_BUCKETS}
    pool = {b: 0 for b in POOL_BUCKETS}
    full_distinct = {b: 0 for b in DISTINCT_BUCKETS}
    wrong = {"tiny_pool_absence": 0, "moderate_pool_absence": 0, "rich_wrong_pool_absence": 0}
    top10_distinct = {b: 0 for b in DISTINCT_BUCKETS}
    top20_distinct = {b: 0 for b in DISTINCT_BUCKETS}
    pressure = {b: 0 for b in PRESSURE_BUCKETS}
    for row in usable:
        order = n10t_order(row["p4_evidence"])
        golds = [norm(g) for g in row.get("gold_paths", []) if norm(g)]
        if file_hit(order, golds, 10):
            top10_hit += 1
            continue
        if file_hit(order, golds, 20):
            top20_extra_hit += 1
        bucket = absence_bucket(order, golds)
        absence[bucket] += 1
        if bucket == "gold_file_absent_from_observed_pool":
            files = [file_id(ev) for ev in order if file_id(ev)]
            pool[pool_bucket(len(order))] += 1
            distinct_full_count = len(set(files))
            full_distinct[distinct_bucket(distinct_full_count)] += 1
            if len(order) <= 20:
                wrong["tiny_pool_absence"] += 1
            elif len(order) <= 50:
                wrong["moderate_pool_absence"] += 1
            else:
                wrong["rich_wrong_pool_absence"] += 1
            top10_files = set(files[:10])
            top20_files = set(files[:20])
            top10_distinct[distinct_bucket(len(top10_files))] += 1
            top20_distinct[distinct_bucket(len(top20_files))] += 1
            pressure[pressure_bucket(len(top10_files))] += 1
    source_fields = [("source_channel", ["source", "channel", "source_channel"]), ("retrieval_method", ["method", "retrieval_method"]), ("score", ["score"]), ("language_repo_task_bucket", ["language", "repo", "task", "repo_id", "task_id"]), ("query_category", ["query", "category"])]
    field_records = []
    for idx, (bucket, keys) in enumerate(source_fields):
        present, total = field_presence(usable, keys)
        complete = total > 0 and present == total
        field_records.append({"anonymous_source_field_id": f"n10dorsrc{idx:04d}", "field_bucket": bucket, "availability_bucket": "complete" if complete else ("partial" if present else "unavailable"), "complete_bool": complete, "usable_for_targeted_policy_bool": complete})
    return {"usable_rows": len(usable), "top10_hit": top10_hit, "top10_miss": len(usable) - top10_hit, "top20_hit": top10_hit + top20_extra_hit, "absence": absence, "pool": pool, "full_distinct": full_distinct, "wrong": wrong, "top10_distinct": top10_distinct, "top20_distinct": top20_distinct, "pressure": pressure, "source_fields": field_records}


def build_bucket_records(prefix: str, field: str, counts: dict[str, int]) -> list[dict[str, Any]]:
    return [{"anonymous_bucket_id": f"{prefix}{idx:04d}", field: bucket, "case_count": count} for idx, (bucket, count) in enumerate(counts.items())]


def accounting_ok(a: dict[str, Any]) -> bool:
    return a["usable_rows"] == 213 and a["top10_hit"] == 44 and a["top10_miss"] == 169 and a["top20_hit"] == 58 and sum(a["absence"].values()) == 169 and a["absence"]["gold_file_absent_from_observed_pool"] == 141 and a["absence"]["gold_file_in_top20"] == 14 and a["absence"]["gold_file_in_top50"] == 14 and sum(a["pool"].values()) == 141


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    inputs, inputs_ok = input_records(args)
    rows, row_state = load_rows(Path(args.private_span_rows))
    a = analyze(rows) if row_state == "present" else {"usable_rows": 0, "top10_hit": 0, "top10_miss": 0, "top20_hit": 0, "absence": {b: 0 for b in ABSENCE_BUCKETS}, "pool": {b: 0 for b in POOL_BUCKETS}, "full_distinct": {b: 0 for b in DISTINCT_BUCKETS}, "wrong": {"tiny_pool_absence": 0, "moderate_pool_absence": 0, "rich_wrong_pool_absence": 0}, "top10_distinct": {b: 0 for b in DISTINCT_BUCKETS}, "top20_distinct": {b: 0 for b in DISTINCT_BUCKETS}, "pressure": {b: 0 for b in PRESSURE_BUCKETS}, "source_fields": []}
    ok = row_state == "present" and accounting_ok(a)
    status = STATUS_COMPLETE if inputs_ok and ok else (STATUS_NO_INPUTS if not inputs_ok else (STATUS_PRIVATE_MISSING if row_state != "present" else STATUS_ACCOUNTING))
    signal_records = [
        {"anonymous_signal_id": "n10dorsig0000", "signal_bucket": "same_pool_optimization_exhausted", "signal_present_bool": True, "evidence_bucket": "corrected_deep_rank_negative"},
        {"anonymous_signal_id": "n10dorsig0001", "signal_bucket": "candidate_source_absent_from_pool", "signal_present_bool": a["absence"]["gold_file_absent_from_observed_pool"] > 0, "evidence_bucket": "absent_pool_dominant"},
        {"anonymous_signal_id": "n10dorsig0002", "signal_bucket": "rich_wrong_pool_suggests_source_quality_gap", "signal_present_bool": a["wrong"]["rich_wrong_pool_absence"] > 0, "evidence_bucket": "rich_wrong_pool_absence_present"},
        {"anonymous_signal_id": "n10dorsig0003", "signal_bucket": "tiny_pool_suggests_pool_size_gap", "signal_present_bool": a["wrong"]["tiny_pool_absence"] > 0, "evidence_bucket": "tiny_pool_absence_present"},
        {"anonymous_signal_id": "n10dorsig0004", "signal_bucket": "source_metadata_unavailable_for_targeted_policy", "signal_present_bool": True, "evidence_bucket": "source_fields_incomplete"},
    ]
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dor_corrected_absence_source_audit_v1",
        "phase_bucket": "BEA-v1-N10DO-R Corrected Candidate-Pool Absence Source Mechanism Audit",
        "status": status,
        "input_artifact_records": inputs,
        "private_input_intake_records": [{"anonymous_private_input_id": "n10dorpriv0000", "private_input_bucket": "scoped_n1_span_rows", "load_status_bucket": row_state, "private_span_rows_read": len(rows), "private_content_used_for_bucketed_audit_bool": row_state == "present"}],
        "corrected_absence_summary_records": [{"anonymous_absence_summary_id": "n10dorabs0000", "primary_file_match_rule_bucket": "suffix_safe_path_match", "top10_file_hit_count": a["top10_hit"], "top10_file_miss_count": a["top10_miss"], "top20_file_hit_count": a["top20_hit"], "first_gold_file_rank_11_20_count": a["absence"]["gold_file_in_top20"], "first_gold_file_rank_21_50_count": a["absence"]["gold_file_in_top50"], "first_gold_file_rank_51_100_count": a["absence"]["gold_file_in_top100"], "first_gold_file_rank_gt100_count": a["absence"]["gold_file_in_observed_pool_beyond100"], "gold_file_absent_from_observed_pool_count": a["absence"]["gold_file_absent_from_observed_pool"], "reachable_rank11_50_count": a["absence"]["gold_file_in_top20"] + a["absence"]["gold_file_in_top50"]}],
        "pool_size_bucket_records": build_bucket_records("n10dorpool", "pool_size_bucket", a["pool"]),
        "full_pool_distinct_file_records": build_bucket_records("n10dordist", "distinct_file_count_bucket", a["full_distinct"]),
        "wrong_pool_richness_records": build_bucket_records("n10dorwrong", "wrong_pool_richness_bucket", a["wrong"]),
        "topk_saturation_records": build_bucket_records("n10dortop10", "top10_distinct_file_bucket", a["top10_distinct"]) + build_bucket_records("n10dortop20", "top20_distinct_file_bucket", a["top20_distinct"]) + build_bucket_records("n10dorpress", "duplicate_pressure_bucket", a["pressure"]),
        "observable_source_field_availability_records": a["source_fields"],
        "source_mechanism_direction_records": signal_records,
        "oracle_ceiling_handoff_records": [{"anonymous_handoff_id": "n10dorhandoff0000", "next_allowed_phase_bucket": "BEA-v1-N10DP Oracle Candidate-Insertion Ceiling Smoke", "n10dp_oracle_ceiling_smoke_authorized_bool": True, "n10dp_design_only_preview_bool": True, "oracle_candidate_insertion_authorized_in_n10dor_bool": False, "retrieval_authorized_bool": False, "candidate_generation_authorized_bool": False}],
        "privacy_boundary_records": [{"anonymous_privacy_id": "n10dorprivacy0000", "public_aggregate_only_bool": True, "private_path_public_count": 0, "candidate_list_public_count": 0, "raw_file_identifier_public_count": 0, "raw_span_or_line_public_count": 0, "gold_used_for_policy_count": 0}],
        "no_forbidden_execution_records": [{"anonymous_no_execution_id": "n10dornoexec0000", "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_add_remove_count": 0, "oracle_candidate_insertion_count": 0, "selector_reranker_execution_count": 0, "runtime_default_change_count": 0}],
        "gate_records": [
            {"anonymous_gate_id": "n10dorgate0000", "gate_bucket": "inputs_present", "gate_passed_bool": inputs_ok},
            {"anonymous_gate_id": "n10dorgate0001", "gate_bucket": "private_span_rows_213", "gate_passed_bool": a["usable_rows"] == 213},
            {"anonymous_gate_id": "n10dorgate0002", "gate_bucket": "corrected_absence_accounting", "gate_passed_bool": ok},
            {"anonymous_gate_id": "n10dorgate0003", "gate_bucket": "no_forbidden_execution", "gate_passed_bool": True},
        ],
        "stop_go_records": [{"anonymous_stop_go_id": "n10dorstop0000", "next_allowed_phase_bucket": "BEA-v1-N10DP Oracle Candidate-Insertion Ceiling Smoke", "n10dp_oracle_ceiling_smoke_authorized_bool": status == STATUS_COMPLETE, "oracle_candidate_insertion_authorized_in_n10dor_bool": False, "retrieval_authorized_bool": False, "candidate_generation_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_generalization_authorized_bool": False, "method_downstream_claim_authorized_bool": False, "selector_reranker_authorized_bool": False, "p5_v1a_authorized_bool": False}],
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
    tests.append(("scanner_safe", scan_summary({"bucket": "aggregate_only"})["status"] == "pass"))
    tests.append(("suffix_match", suffix_match("repo/src/a", "src/a") is True))
    tests.append(("pool_bucket", pool_bucket(101) == "pool_size_gt100"))
    tests.append(("distinct_bucket", distinct_bucket(55) == "distinct_file_count_gt50"))
    tests.append(("pressure", pressure_bucket(4) == "duplicate_pressure_high"))
    synthetic = [{"p4_evidence": [{"path": f"repo/f{i}"} for i in range(1, 22)], "gold_paths": ["f15"]}]
    tests.append(("analyze_counts", analyze(synthetic)["top10_miss"] == 1 and analyze(synthetic)["absence"]["gold_file_in_top20"] == 1))
    tests.append(("forbidden_values", scan_summary({"bucket": "/tmp/secret"})["status"] == "fail"))
    tests.append(("stop_false", build_report(parse_args([]))["stop_go_records"][0]["retrieval_authorized_bool"] is False if DEFAULT_PRIVATE.exists() else True))
    tests.append(("handoff_name", "Oracle" in build_report(parse_args([]))["stop_go_records"][0]["next_allowed_phase_bucket"] if DEFAULT_PRIVATE.exists() else True))
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
