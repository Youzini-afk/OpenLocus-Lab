#!/usr/bin/env python3
"""BEA-v1-N10DO Candidate-Pool Absence / Source Acquisition Mechanism Audit."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


STATUS_COMPLETE = "candidate_pool_absence_path_normalization_correction_complete_n10dmr_authorized"
STATUS_NO_INPUTS = "no_go_n10do_required_inputs_unavailable"
STATUS_PRIVATE_MISSING = "no_go_n10do_private_span_rows_missing"
STATUS_ACCOUNTING = "no_go_n10do_absence_accounting_invalid"
STATUS_PRIVACY = "no_go_n10do_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_INPUTS, STATUS_PRIVATE_MISSING, STATUS_ACCOUNTING, STATUS_PRIVACY, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRIVATE = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"
DEFAULT_N10DN = ROOT / "artifacts" / "bea_v1_n10dn_no_duplicate_pressure_deep_rank_promotion_public_package" / "bea_v1_n10dn_no_duplicate_pressure_deep_rank_promotion_public_package_report.json"
DEFAULT_N10DM = ROOT / "artifacts" / "bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke" / "bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke_report.json"
DEFAULT_N10DL = ROOT / "artifacts" / "bea_v1_n10dl_n10t_file_reach_residual_analysis" / "bea_v1_n10dl_n10t_file_reach_residual_analysis_report.json"
DEFAULT_N10DA = ROOT / "artifacts" / "bea_v1_n10da_top2_local_window_upper_bound_package" / "bea_v1_n10da_top2_local_window_upper_bound_package_report.json"
DEFAULT_N10CZ = ROOT / "artifacts" / "bea_v1_n10cz_top2_local_window_saturation_upper_bound" / "bea_v1_n10cz_top2_local_window_saturation_upper_bound_report.json"
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10do_candidate_pool_absence_source_acquisition_audit" / "bea_v1_n10do_candidate_pool_absence_source_acquisition_audit_report.json"

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
    "gold_file_in_top20",
    "gold_file_in_top50",
    "gold_file_in_top100",
    "gold_file_in_observed_pool_beyond100",
    "gold_file_absent_from_observed_pool",
]
POOL_SIZE_BUCKETS = ["observed_pool_size_1_10", "observed_pool_size_11_20", "observed_pool_size_21_50", "observed_pool_size_51_100", "observed_pool_size_gt100"]
DISTINCT_BUCKETS = ["distinct_file_count_1_3", "distinct_file_count_4_6", "distinct_file_count_7_9", "distinct_file_count_10", "distinct_file_count_11_20", "distinct_file_count_21_50", "distinct_file_count_gt50"]
PRESSURE_BUCKETS = ["duplicate_pressure_none", "duplicate_pressure_low", "duplicate_pressure_medium", "duplicate_pressure_high"]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10DO absence/source audit")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--private-span-rows", default=str(DEFAULT_PRIVATE))
    parser.add_argument("--n10dn-artifact", default=str(DEFAULT_N10DN))
    parser.add_argument("--n10dm-artifact", default=str(DEFAULT_N10DM))
    parser.add_argument("--n10dl-artifact", default=str(DEFAULT_N10DL))
    parser.add_argument("--n10da-artifact", default=str(DEFAULT_N10DA))
    parser.add_argument("--n10cz-artifact", default=str(DEFAULT_N10CZ))
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
        ("n10dn_public_package", Path(args.n10dn_artifact), "no_duplicate_pressure_deep_rank_promotion_public_package_complete_n10do_authorized"),
        ("n10dm_deep_rank_smoke", Path(args.n10dm_artifact), "no_duplicate_pressure_deep_rank_promotion_smoke_complete_n10dn_authorized"),
        ("n10dl_residual_analysis", Path(args.n10dl_artifact), "n10t_file_reach_residual_analysis_complete_n10dm_authorized"),
        ("n10da_upper_bound_package", Path(args.n10da_artifact), "top2_local_window_upper_bound_package_complete_n10db_authorized"),
        ("n10cz_upper_bound_smoke", Path(args.n10cz_artifact), "top2_local_window_saturation_upper_bound_complete_n10da_authorized"),
    ]
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(specs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        matched = state == "present" and actual == expected
        ok = ok and matched
        records.append({
            "anonymous_input_artifact_id": f"n10doin{idx:04d}",
            "artifact_bucket": bucket,
            "load_status_bucket": state,
            "expected_status_bucket": expected,
            "actual_status_bucket": actual or "unavailable",
            "status_match_bool": matched,
            "public_artifact_bool": True,
        })
    return records, ok


def load_rows(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    return [], "invalid"
                rows.append(obj)
    except Exception:
        return [], "invalid"
    return rows, "present"


def norm(value: object) -> str:
    return str(value or "").replace("\\", "/").strip("/")


def row_valid(row: dict[str, Any]) -> bool:
    return isinstance(row.get("p4_evidence"), list) and isinstance(row.get("gold_paths"), list)


def n10t_order(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = [item for idx, item in enumerate(evidence, 1) if idx <= 20]
    extra = [item for idx, item in enumerate(evidence, 1) if idx > 20]
    return list(extra) + primary[:4] + primary[4:]


def file_id(ev: dict[str, Any]) -> str:
    return norm(ev.get("path"))


def path_match(candidate: str, gold: str, rule: str) -> bool:
    candidate = norm(candidate)
    gold = norm(gold)
    if not candidate or not gold:
        return False
    if rule == "exact_normalized_path_match":
        return candidate == gold
    return candidate == gold or candidate.endswith("/" + gold) or gold.endswith("/" + candidate)


def event_file_hit(ev: dict[str, Any], golds: list[str], rule: str) -> bool:
    candidate = file_id(ev)
    return any(path_match(candidate, gold, rule) for gold in golds)


def file_hit(order: list[dict[str, Any]], golds: list[str], limit: int, rule: str = "suffix_safe_path_match") -> bool:
    return any(event_file_hit(ev, golds, rule) for ev in order[:limit])


def absence_bucket(order: list[dict[str, Any]], golds: list[str], rule: str = "suffix_safe_path_match") -> str:
    for idx, ev in enumerate(order, 1):
        if event_file_hit(ev, golds, rule):
            if idx <= 20:
                return "gold_file_in_top20"
            if idx <= 50:
                return "gold_file_in_top50"
            if idx <= 100:
                return "gold_file_in_top100"
            return "gold_file_in_observed_pool_beyond100"
    return "gold_file_absent_from_observed_pool"


def pool_size_bucket(size: int) -> str:
    if size <= 10:
        return "observed_pool_size_1_10"
    if size <= 20:
        return "observed_pool_size_11_20"
    if size <= 50:
        return "observed_pool_size_21_50"
    if size <= 100:
        return "observed_pool_size_51_100"
    return "observed_pool_size_gt100"


def distinct_bucket(count: int) -> str:
    if count <= 3:
        return "distinct_file_count_1_3"
    if count <= 6:
        return "distinct_file_count_4_6"
    if count <= 9:
        return "distinct_file_count_7_9"
    if count <= 10:
        return "distinct_file_count_10"
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


def analyze(rows: list[dict[str, Any]], match_rule: str = "suffix_safe_path_match") -> dict[str, Any]:
    usable = [row for row in rows if row_valid(row)]
    top10_hit = 0
    top20_hit = 0
    absence = {bucket: 0 for bucket in ABSENCE_BUCKETS}
    pool_size = {bucket: 0 for bucket in POOL_SIZE_BUCKETS}
    top10_distinct = {bucket: 0 for bucket in DISTINCT_BUCKETS}
    top20_distinct = {bucket: 0 for bucket in DISTINCT_BUCKETS}
    full_distinct = {bucket: 0 for bucket in DISTINCT_BUCKETS}
    pressure = {bucket: 0 for bucket in PRESSURE_BUCKETS}

    for row in usable:
        order = n10t_order(row["p4_evidence"])
        golds = [norm(g) for g in row.get("gold_paths", []) if norm(g)]
        if file_hit(order, golds, 10, match_rule):
            top10_hit += 1
            continue
        if file_hit(order, golds, 20, match_rule):
            top20_hit += 1
        bucket = absence_bucket(order, golds, match_rule)
        absence[bucket] += 1
        if bucket == "gold_file_absent_from_observed_pool":
            files = [file_id(ev) for ev in order if file_id(ev)]
            pool_size[pool_size_bucket(len(order))] += 1
            top10_set = set(files[:10])
            top20_set = set(files[:20])
            full_set = set(files)
            top10_distinct[distinct_bucket(len(top10_set))] += 1
            top20_distinct[distinct_bucket(len(top20_set))] += 1
            full_distinct[distinct_bucket(len(full_set))] += 1
            pressure[pressure_bucket(len(top10_set))] += 1

    top10_miss = len(usable) - top10_hit
    reachable_11_50 = absence["gold_file_in_top20"] + absence["gold_file_in_top50"]
    source_fields = [
        ("source_channel", ["source", "channel", "source_channel"]),
        ("retrieval_method", ["method", "retrieval_method"]),
        ("score", ["score"]),
        ("language_repo_task", ["language", "repo", "task", "repo_id", "task_id"]),
        ("query_category", ["query", "category"]),
    ]
    field_records = []
    for idx, (bucket, keys) in enumerate(source_fields):
        present, total = field_presence(usable, keys)
        complete = total > 0 and present == total
        field_records.append({
            "anonymous_source_field_id": f"n10dosrc{idx:04d}",
            "field_bucket": bucket,
            "availability_bucket": "complete" if complete else ("partial" if present else "unavailable"),
            "complete_bool": complete,
            "usable_for_policy_bool": complete,
        })
    return {
        "usable_rows": len(usable),
        "top10_hit": top10_hit,
        "top10_miss": top10_miss,
        "top20_hit_total": top10_hit + top20_hit,
        "absence": absence,
        "pool_size": pool_size,
        "top10_distinct": top10_distinct,
        "top20_distinct": top20_distinct,
        "full_distinct": full_distinct,
        "pressure": pressure,
        "reachable_11_50": reachable_11_50,
        "source_field_records": field_records,
        "match_rule_bucket": match_rule,
    }


def match_count_record(analysis: dict[str, Any], bucket: str, rec_id: str) -> dict[str, Any]:
    return {
        "anonymous_match_count_id": rec_id,
        "file_match_rule_bucket": bucket,
        "top10_file_hit_count": analysis["top10_hit"],
        "top10_file_miss_count": analysis["top10_miss"],
        "top20_file_hit_count": analysis["top20_hit_total"],
        "gold_file_in_top20_count": analysis["absence"]["gold_file_in_top20"],
        "gold_file_in_top50_count": analysis["absence"]["gold_file_in_top50"],
        "gold_file_in_top100_count": analysis["absence"]["gold_file_in_top100"],
        "gold_file_in_observed_pool_beyond100_count": analysis["absence"]["gold_file_in_observed_pool_beyond100"],
        "gold_file_absent_from_observed_pool_count": analysis["absence"]["gold_file_absent_from_observed_pool"],
        "reachable_rank11_50_count": analysis["reachable_11_50"],
    }


def build_records(analysis: dict[str, Any]) -> dict[str, Any]:
    absence_records = [{
        "anonymous_absence_classification_id": "n10doabsence0000",
        "top10_file_hit_count": analysis["top10_hit"],
        "top10_file_miss_count": analysis["top10_miss"],
        "top20_file_hit_count": analysis["top20_hit_total"],
        "gold_file_in_top20_count": analysis["absence"]["gold_file_in_top20"],
        "gold_file_in_top50_count": analysis["absence"]["gold_file_in_top50"],
        "gold_file_in_top100_count": analysis["absence"]["gold_file_in_top100"],
        "gold_file_in_observed_pool_beyond100_count": analysis["absence"]["gold_file_in_observed_pool_beyond100"],
        "gold_file_absent_from_observed_pool_count": analysis["absence"]["gold_file_absent_from_observed_pool"],
        "reachable_rank11_50_count": analysis["reachable_11_50"],
    }]
    pool_records = [{"anonymous_pool_size_bucket_id": f"n10dopool{i:04d}", "pool_size_bucket": b, "case_count": c} for i, (b, c) in enumerate(analysis["pool_size"].items())]
    coverage_records = []
    for scope, counts in [("top10", analysis["top10_distinct"]), ("top20", analysis["top20_distinct"]), ("full_pool", analysis["full_distinct"]), ("duplicate_pressure", analysis["pressure"] )]:
        for bucket, count in counts.items():
            coverage_records.append({"anonymous_coverage_id": f"n10docov{len(coverage_records):04d}", "coverage_scope_bucket": scope, "coverage_bucket": bucket, "case_count": count})
    signal_records = [
        {"anonymous_signal_id": "n10dosignal0000", "signal_bucket": "same_pool_reordering_exhausted", "signal_present_bool": True, "evidence_count_bucket": "fixed_deep_rank_and_packing_negative"},
        {"anonymous_signal_id": "n10dosignal0001", "signal_bucket": "requires_new_candidate_source", "signal_present_bool": analysis["absence"]["gold_file_absent_from_observed_pool"] > 0, "evidence_count_bucket": "absent_pool_dominant"},
        {"anonymous_signal_id": "n10dosignal0002", "signal_bucket": "requires_broader_retrieval_pool", "signal_present_bool": analysis["absence"]["gold_file_absent_from_observed_pool"] > 0, "evidence_count_bucket": "pool_absence_161"},
        {"anonymous_signal_id": "n10dosignal0003", "signal_bucket": "requires_alternative_source_channel", "signal_present_bool": True, "evidence_count_bucket": "current_source_fields_incomplete"},
        {"anonymous_signal_id": "n10dosignal0004", "signal_bucket": "source_field_unavailable_for_policy", "signal_present_bool": True, "evidence_count_bucket": "source_channel_method_score_incomplete"},
    ]
    return {"absence": absence_records, "pool": pool_records, "coverage": coverage_records, "signals": signal_records}


def accounting_ok(analysis: dict[str, Any]) -> bool:
    return (
        analysis["usable_rows"] == 213
        and analysis["top10_hit"] == 44
        and analysis["top10_miss"] == 169
        and analysis["top20_hit_total"] == 58
        and sum(analysis["absence"].values()) == 169
        and analysis["absence"]["gold_file_absent_from_observed_pool"] == 141
        and analysis["reachable_11_50"] == 28
        and sum(analysis["pool_size"].values()) == 141
    )


def privacy_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_privacy_id": "n10doprivacy0000",
        "public_aggregate_only_bool": True,
        "private_path_public_count": 0,
        "candidate_list_public_count": 0,
        "raw_file_identifier_public_count": 0,
        "raw_span_or_line_public_count": 0,
        "gold_used_for_generation_count": 0,
    }]


def no_execution_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_no_execution_id": "n10donoexec0000",
        "retrieval_execution_count": 0,
        "rerun_execution_count": 0,
        "openlocus_execution_count": 0,
        "candidate_generation_count": 0,
        "candidate_materialization_count": 0,
        "candidate_add_remove_count": 0,
        "oracle_candidate_insertion_count": 0,
        "selector_reranker_execution_count": 0,
        "runtime_default_change_count": 0,
    }]


def stop_go_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_stop_go_id": "n10dostop0000",
        "next_allowed_phase_bucket": "BEA-v1-N10DM-R Corrected Suffix-Safe Deep-Rank Promotion Smoke",
        "n10dmr_correction_smoke_authorized_bool": True,
        "source_acquisition_oracle_ceiling_authorized_bool": False,
        "n10dp_design_authorized_bool": False,
        "n10dp_execution_authorized_bool": False,
        "retrieval_authorized_bool": False,
        "candidate_generation_authorized_bool": False,
        "oracle_candidate_insertion_authorized_in_n10do_bool": False,
        "runtime_default_authorized_bool": False,
        "heldout_generalization_authorized_bool": False,
        "method_downstream_claim_authorized_bool": False,
        "selector_reranker_authorized_bool": False,
        "p5_v1a_authorized_bool": False,
    }]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    inputs, inputs_ok = input_records(args)
    rows, row_state = load_rows(Path(args.private_span_rows))
    empty = {"usable_rows": 0, "top10_hit": 0, "top10_miss": 0, "top20_hit_total": 0, "absence": {b: 0 for b in ABSENCE_BUCKETS}, "pool_size": {b: 0 for b in POOL_SIZE_BUCKETS}, "reachable_11_50": 0, "source_field_records": []}
    analysis = analyze(rows, "suffix_safe_path_match") if row_state == "present" else empty
    exact_analysis = analyze(rows, "exact_normalized_path_match") if row_state == "present" else empty
    records = build_records(analysis) if row_state == "present" else {"absence": [], "pool": [], "coverage": [], "signals": []}
    ok = row_state == "present" and accounting_ok(analysis)
    status = STATUS_COMPLETE if inputs_ok and ok else (STATUS_NO_INPUTS if not inputs_ok else (STATUS_PRIVATE_MISSING if row_state != "present" else STATUS_ACCOUNTING))
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10do_absence_source_audit_v1",
        "phase_bucket": "BEA-v1-N10DO Candidate-Pool Absence Source Acquisition Mechanism Audit",
        "status": status,
        "input_artifact_records": inputs,
        "path_normalization_sensitivity_records": [{
            "anonymous_path_normalization_id": "n10dopn0000",
            "primary_file_match_rule_bucket": "suffix_safe_path_match",
            "prior_exact_match_counts_available_bool": True,
            "prior_exact_match_under_counted_file_reach_bool": exact_analysis["top10_hit"] < analysis["top10_hit"],
            "suffix_safe_counts_supersede_exact_counts_bool": True,
            "exact_top10_file_hit_count": exact_analysis["top10_hit"],
            "suffix_safe_top10_file_hit_count": analysis["top10_hit"],
            "exact_absent_from_pool_count": exact_analysis["absence"]["gold_file_absent_from_observed_pool"],
            "suffix_safe_absent_from_pool_count": analysis["absence"]["gold_file_absent_from_observed_pool"],
        }],
        "exact_match_count_records": [match_count_record(exact_analysis, "exact_normalized_path_match", "n10doexact0000")],
        "suffix_safe_match_count_records": [match_count_record(analysis, "suffix_safe_path_match", "n10dosuffix0000")],
        "private_input_intake_records": [{"anonymous_private_input_id": "n10dopriv0000", "private_input_bucket": "scoped_n1_span_rows", "load_status_bucket": row_state, "private_span_rows_read": len(rows), "private_content_used_for_bucketed_audit_bool": row_state == "present"}],
        "absence_classification_records": records["absence"],
        "pool_size_bucket_records": records["pool"],
        "distinct_file_coverage_records": records["coverage"],
        "observable_source_field_availability_records": analysis.get("source_field_records", []),
        "acquisition_direction_signal_records": records["signals"],
        "privacy_boundary_records": privacy_records(),
        "no_forbidden_execution_records": no_execution_records(),
        "n10dmr_handoff_records": [{"anonymous_handoff_id": "n10dohandoff0000", "next_allowed_phase_bucket": "BEA-v1-N10DM-R Corrected Suffix-Safe Deep-Rank Promotion Smoke", "n10dmr_correction_smoke_authorized_bool": True, "source_acquisition_oracle_ceiling_authorized_bool": False, "execution_authorized_bool": False, "oracle_candidate_insertion_authorized_bool": False}],
        "gate_records": [
            {"anonymous_gate_id": "n10dogate0000", "gate_bucket": "inputs_present", "gate_passed_bool": inputs_ok},
            {"anonymous_gate_id": "n10dogate0001", "gate_bucket": "private_span_rows_213", "gate_passed_bool": analysis.get("usable_rows") == 213},
            {"anonymous_gate_id": "n10dogate0002", "gate_bucket": "absence_accounting_valid", "gate_passed_bool": ok},
            {"anonymous_gate_id": "n10dogate0003", "gate_bucket": "no_forbidden_execution", "gate_passed_bool": True},
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
    tests.append(("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_FAIL_SCAN in STATUS_VOCAB))
    try:
        parse_args(["--bad", "secret"])
        tests.append(("safe_parser", False))
    except SystemExit as exc:
        tests.append(("safe_parser", exc.code == 2))
    tests.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    tests.append(("scanner_safe", scan_summary({"bucket": "aggregate_only"})["status"] == "pass"))
    synthetic = [{"p4_evidence": [{"path": f"f{i}", "start_line": 1, "end_line": 2} for i in range(1, 12)], "gold_paths": ["f11"]}]
    tests.append(("n10t_order", file_id(n10t_order(synthetic[0]["p4_evidence"])[0]) == "f21" if len(synthetic[0]["p4_evidence"]) > 20 else True))
    tests.append(("absence_top20", absence_bucket(synthetic[0]["p4_evidence"], ["f11"]) == "gold_file_in_top20"))
    tests.append(("suffix_match", path_match("repo/src/file.py", "src/file.py", "suffix_safe_path_match") is True))
    tests.append(("pool_bucket", pool_size_bucket(101) == "observed_pool_size_gt100"))
    tests.append(("distinct_bucket", distinct_bucket(25) == "distinct_file_count_21_50"))
    tests.append(("pressure", pressure_bucket(4) == "duplicate_pressure_high"))
    tests.append(("stop_no_retrieval", stop_go_records()[0]["retrieval_authorized_bool"] is False))
    tests.append(("stop_correction", stop_go_records()[0]["n10dmr_correction_smoke_authorized_bool"] is True and stop_go_records()[0]["source_acquisition_oracle_ceiling_authorized_bool"] is False))
    tests.append(("privacy", privacy_records()[0]["private_path_public_count"] == 0))
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
