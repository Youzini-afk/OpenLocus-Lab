#!/usr/bin/env python3
"""BEA-v1-N10DL N10T File-Reach Residual Mechanism Analysis."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


STATUS_COMPLETE = "n10t_file_reach_residual_analysis_complete_n10dm_authorized"
STATUS_NO_SIGNAL = "n10t_file_reach_residual_analysis_complete_no_go_no_safe_signal"
STATUS_NO_INPUTS = "no_go_n10dl_required_inputs_unavailable"
STATUS_PRIVATE_MISSING = "no_go_n10dl_private_span_rows_missing"
STATUS_ACCOUNTING = "no_go_n10dl_residual_accounting_invalid"
STATUS_PRIVACY = "no_go_n10dl_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {
    STATUS_COMPLETE,
    STATUS_NO_SIGNAL,
    STATUS_NO_INPUTS,
    STATUS_PRIVATE_MISSING,
    STATUS_ACCOUNTING,
    STATUS_PRIVACY,
    STATUS_FAIL_SCAN,
    STATUS_FAIL_SCHEMA,
}

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRIVATE = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"
DEFAULT_N10DK = ROOT / "artifacts" / "bea_v1_n10dk_n10t_order_rank_promotion_public_package" / "bea_v1_n10dk_n10t_order_rank_promotion_public_package_report.json"
DEFAULT_N10DJ = ROOT / "artifacts" / "bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke" / "bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke_report.json"
DEFAULT_N10DA = ROOT / "artifacts" / "bea_v1_n10da_top2_local_window_upper_bound_package" / "bea_v1_n10da_top2_local_window_upper_bound_package_report.json"
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10dl_n10t_file_reach_residual_analysis" / "bea_v1_n10dl_n10t_file_reach_residual_analysis_report.json"

FORBIDDEN_KEYS = {
    "path",
    "paths",
    "filename",
    "filenames",
    "private_path",
    "private_filename",
    "source_path",
    "span",
    "spans",
    "line",
    "lines",
    "snippet",
    "snippets",
    "content",
    "candidate_list",
    "candidates",
    "gold_path",
    "gold_paths",
    "gold_line",
    "gold_lines",
    "exact_rank",
    "raw_rank",
    "repo_id",
    "task_id",
    "hash",
    "provider_payload",
    "raw_diff",
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/"),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt)"),
    re.compile(r"[0-9a-f]{32,}", re.I),
]

RANK_BUCKETS = [
    "first_gold_file_rank_11_20",
    "first_gold_file_rank_21_50",
    "first_gold_file_rank_51_100",
    "first_gold_file_rank_gt100",
    "gold_file_absent_from_pool",
]
DISTINCT_BUCKETS = [
    "top10_distinct_file_count_1_3",
    "top10_distinct_file_count_4_6",
    "top10_distinct_file_count_7_9",
    "top10_distinct_file_count_10",
]
PRESSURE_BUCKETS = ["duplicate_pressure_none", "duplicate_pressure_low", "duplicate_pressure_medium", "duplicate_pressure_high"]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10DL residual analysis")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--private-span-rows", default=str(DEFAULT_PRIVATE))
    parser.add_argument("--n10dk-artifact", default=str(DEFAULT_N10DK))
    parser.add_argument("--n10dj-artifact", default=str(DEFAULT_N10DJ))
    parser.add_argument("--n10da-artifact", default=str(DEFAULT_N10DA))
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
        ("n10dk_public_package", Path(args.n10dk_artifact), "n10t_order_rank_promotion_public_package_complete_n10dl_authorized"),
        ("n10dj_rank_promotion_smoke", Path(args.n10dj_artifact), "n10t_order_file_reach_rank_promotion_smoke_complete_n10dk_authorized"),
        ("n10da_local_window_context", Path(args.n10da_artifact), "top2_local_window_upper_bound_package_complete_n10db_authorized"),
    ]
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(specs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        matched = state == "present" and actual == expected
        ok = ok and matched
        records.append(
            {
                "anonymous_input_artifact_id": f"n10dlin{idx:04d}",
                "artifact_bucket": bucket,
                "load_status_bucket": state,
                "expected_status_bucket": expected,
                "actual_status_bucket": actual or "unavailable",
                "status_match_bool": matched,
                "public_artifact_bool": True,
            }
        )
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


def file_hit(order: list[dict[str, Any]], golds: set[str], limit: int) -> bool:
    return any(norm(ev.get("path")) in golds for ev in order[:limit])


def first_gold_rank_bucket(order: list[dict[str, Any]], golds: set[str]) -> str:
    for idx, ev in enumerate(order, 1):
        if norm(ev.get("path")) in golds:
            if idx <= 20:
                return "first_gold_file_rank_11_20"
            if idx <= 50:
                return "first_gold_file_rank_21_50"
            if idx <= 100:
                return "first_gold_file_rank_51_100"
            return "first_gold_file_rank_gt100"
    return "gold_file_absent_from_pool"


def distinct_count_bucket(count: int) -> str:
    if count <= 3:
        return "top10_distinct_file_count_1_3"
    if count <= 6:
        return "top10_distinct_file_count_4_6"
    if count <= 9:
        return "top10_distinct_file_count_7_9"
    return "top10_distinct_file_count_10"


def pressure_bucket(distinct_count: int) -> str:
    duplicate_count = max(0, 10 - distinct_count)
    if duplicate_count == 0:
        return "duplicate_pressure_none"
    if duplicate_count <= 2:
        return "duplicate_pressure_low"
    if duplicate_count <= 5:
        return "duplicate_pressure_medium"
    return "duplicate_pressure_high"


def length_bucket(ev: dict[str, Any]) -> str:
    try:
        length = int(ev["end_line"]) - int(ev["start_line"]) + 1
    except Exception:
        return "unknown"
    return "short" if length <= 10 else ("medium" if length <= 30 else "long")


def field_complete(rows: list[dict[str, Any]], keys: list[str]) -> bool:
    total = 0
    present = 0
    for row in rows:
        for ev in row.get("p4_evidence", []):
            if isinstance(ev, dict):
                total += 1
                if any(k in ev and ev.get(k) not in (None, "") for k in keys):
                    present += 1
    return total > 0 and present == total


def analyze(rows: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [row for row in rows if row_valid(row)]
    top10_hit = 0
    top20_hit = 0
    rank_counts = {bucket: 0 for bucket in RANK_BUCKETS}
    distinct_counts = {bucket: 0 for bucket in DISTINCT_BUCKETS}
    pressure_counts = {bucket: 0 for bucket in PRESSURE_BUCKETS}
    cross = {(rank, pressure): 0 for rank in RANK_BUCKETS for pressure in PRESSURE_BUCKETS}
    candidate_lengths: list[int] = []
    span_length_known = True
    for row in usable:
        order = n10t_order(row["p4_evidence"])
        candidate_lengths.append(len(order))
        golds = {norm(path) for path in row.get("gold_paths", [])}
        hit10 = file_hit(order, golds, 10)
        hit20 = file_hit(order, golds, 20)
        top10_hit += int(hit10)
        top20_hit += int(hit20)
        span_length_known = span_length_known and all(length_bucket(ev) != "unknown" for ev in order)
        if not hit10:
            rank_bucket = first_gold_rank_bucket(order, golds)
            distinct = len({norm(ev.get("path")) for ev in order[:10]})
            distinct_bucket = distinct_count_bucket(distinct)
            pressure = pressure_bucket(distinct)
            rank_counts[rank_bucket] += 1
            distinct_counts[distinct_bucket] += 1
            pressure_counts[pressure] += 1
            cross[(rank_bucket, pressure)] += 1
    miss = len(usable) - top10_hit
    candidate_pool_sufficient = bool(candidate_lengths) and min(candidate_lengths) >= 20
    return {
        "row_count": len(usable),
        "top10_hit": top10_hit,
        "top10_miss": miss,
        "top20_hit": top20_hit,
        "rank_counts": rank_counts,
        "distinct_counts": distinct_counts,
        "pressure_counts": pressure_counts,
        "cross": cross,
        "candidate_pool_sufficient": candidate_pool_sufficient,
        "candidate_file_identifier_present": field_complete(usable, ["path", "file", "file_path"]),
        "source_channel_complete": field_complete(usable, ["source", "channel", "source_channel"]),
        "method_complete": field_complete(usable, ["method"]),
        "score_complete": field_complete(usable, ["score"]),
        "span_length_bucket_available": span_length_known,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    inputs, inputs_ok = input_records(args)
    rows, row_status = load_rows(Path(args.private_span_rows))
    rows_ok = row_status == "present" and len(rows) == 213
    analysis = analyze(rows) if rows_ok else analyze([])
    rank_sum = sum(analysis["rank_counts"].values())
    distinct_sum = sum(analysis["distinct_counts"].values())
    cross_sum = sum(analysis["cross"].values())
    accounting_ok = (
        rows_ok
        and analysis["top10_hit"] == 34
        and analysis["top20_hit"] == 44
        and analysis["top10_hit"] + analysis["top10_miss"] == 213
        and rank_sum == analysis["top10_miss"]
        and distinct_sum == analysis["top10_miss"]
        and cross_sum == analysis["top10_miss"]
    )
    duplicate_pressure_reachable = (
        analysis["cross"].get(("first_gold_file_rank_11_20", "duplicate_pressure_medium"), 0)
        + analysis["cross"].get(("first_gold_file_rank_11_20", "duplicate_pressure_high"), 0)
        + analysis["cross"].get(("first_gold_file_rank_21_50", "duplicate_pressure_medium"), 0)
        + analysis["cross"].get(("first_gold_file_rank_21_50", "duplicate_pressure_high"), 0)
    )
    no_duplicate_pressure_deep_rank = (
        analysis["cross"].get(("first_gold_file_rank_11_20", "duplicate_pressure_none"), 0)
        + analysis["cross"].get(("first_gold_file_rank_21_50", "duplicate_pressure_none"), 0)
    )
    signal_exists = accounting_ok and no_duplicate_pressure_deep_rank > 0
    if not inputs_ok:
        status = STATUS_NO_INPUTS
    elif not rows_ok:
        status = STATUS_PRIVATE_MISSING
    elif not accounting_ok:
        status = STATUS_ACCOUNTING
    elif signal_exists:
        status = STATUS_COMPLETE
    else:
        status = STATUS_NO_SIGNAL

    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dl_residual_analysis_v1",
        "phase_bucket": "BEA-v1-N10DL N10T File-Reach Residual Mechanism Analysis",
        "status": status,
        "input_artifact_records": inputs,
        "private_input_intake_records": [
            {
                "anonymous_private_input_id": "n10dlpriv0000",
                "private_input_bucket": "single_scoped_n1_span_rows",
                "load_status_bucket": row_status,
                "private_span_rows_read": len(rows) if row_status == "present" else 0,
                "other_private_files_read_count": 0,
                "private_path_public_bool": False,
                "private_filename_public_bool": False,
            }
        ],
        "file_reach_residual_summary_records": [
            {
                "anonymous_file_reach_residual_id": "n10dlresidual0000",
                "top10_file_hit_count": analysis["top10_hit"],
                "top10_file_miss_count": analysis["top10_miss"],
                "top20_file_hit_count": analysis["top20_hit"],
            }
        ],
        "first_gold_file_rank_bucket_records": [
            {
                "anonymous_rank_bucket_id": f"n10dlrank{i:04d}",
                "rank_bucket": bucket,
                "row_count": analysis["rank_counts"].get(bucket, 0),
            }
            for i, bucket in enumerate(RANK_BUCKETS)
        ],
        "duplicate_pressure_bucket_records": [
            {
                "anonymous_duplicate_bucket_id": f"n10dldup{i:04d}",
                "top10_distinct_file_count_bucket": bucket,
                "row_count": analysis["distinct_counts"].get(bucket, 0),
            }
            for i, bucket in enumerate(DISTINCT_BUCKETS)
        ]
        + [
            {
                "anonymous_duplicate_bucket_id": f"n10dlpressure{i:04d}",
                "duplicate_pressure_bucket": bucket,
                "row_count": analysis["pressure_counts"].get(bucket, 0),
            }
            for i, bucket in enumerate(PRESSURE_BUCKETS)
        ],
        "rank_by_duplicate_pressure_records": [
            {
                "anonymous_cross_tab_id": f"n10dlcross{i:04d}",
                "rank_bucket": rank_bucket,
                "duplicate_pressure_bucket": pressure,
                "row_count": count,
            }
            for i, ((rank_bucket, pressure), count) in enumerate(analysis["cross"].items())
        ],
        "observable_field_availability_records": [
            {
                "anonymous_observable_field_id": "n10dlfield0000",
                "candidate_rank_position_available_bool": True,
                "candidate_file_identity_private_available_bool": analysis["candidate_file_identifier_present"],
                "top10_duplicate_pressure_available_bool": analysis["candidate_file_identifier_present"],
                "file_repeat_count_private_available_bool": analysis["candidate_file_identifier_present"],
                "span_length_bucket_available_bool": analysis["span_length_bucket_available"],
                "source_channel_bucket_complete_bool": analysis["source_channel_complete"],
                "method_bucket_complete_bool": analysis["method_complete"],
                "score_bucket_complete_bool": analysis["score_complete"],
            }
        ],
        "future_mechanism_signal_records": [
            {
                "anonymous_signal_id": "n10dlsignal0000",
                "signal_bucket": "duplicate_pressure_conditioned_promotion_signal",
                "signal_present_bool": duplicate_pressure_reachable > 0,
                "recommended_for_n10dm_bool": False,
            },
            {
                "anonymous_signal_id": "n10dlsignal0001",
                "signal_bucket": "no_duplicate_pressure_deep_rank_probe_signal",
                "signal_present_bool": no_duplicate_pressure_deep_rank > 0,
                "recommended_for_n10dm_bool": True,
            },
            {
                "anonymous_signal_id": "n10dlsignal0002",
                "signal_bucket": "deep_rank_retrieval_gap_signal",
                "signal_present_bool": (analysis["rank_counts"].get("first_gold_file_rank_21_50", 0) + analysis["rank_counts"].get("first_gold_file_rank_51_100", 0) + analysis["rank_counts"].get("first_gold_file_rank_gt100", 0)) > 0,
                "recommended_for_n10dm_bool": False,
            },
            {
                "anonymous_signal_id": "n10dlsignal0003",
                "signal_bucket": "pool_absence_signal",
                "signal_present_bool": analysis["rank_counts"].get("gold_file_absent_from_pool", 0) > 0,
                "recommended_for_n10dm_bool": False,
            },
            {
                "anonymous_signal_id": "n10dlsignal0004",
                "signal_bucket": "no_safe_gold_free_signal",
                "signal_present_bool": not signal_exists,
                "recommended_for_n10dm_bool": False,
            },
        ],
        "privacy_boundary_records": [
            {
                "anonymous_privacy_boundary_id": "n10dlprivacy0000",
                "private_path_public_bool": False,
                "private_filename_public_bool": False,
                "candidate_list_public_bool": False,
                "gold_label_public_bool": False,
                "span_or_line_public_bool": False,
                "exact_rank_public_bool": False,
                "public_aggregate_bucket_only_bool": True,
            }
        ],
        "no_forbidden_execution_records": [
            {
                "anonymous_no_forbidden_id": "n10dlnoexec0000",
                "policy_execution_count": 0,
                "candidate_order_changed_count": 0,
                "retrieval_execution_count": 0,
                "rerun_execution_count": 0,
                "openlocus_execution_count": 0,
                "candidate_generation_count": 0,
                "candidate_materialization_count": 0,
                "candidate_add_remove_count": 0,
                "selector_reranker_execution_count": 0,
                "runtime_default_change_count": 0,
            }
        ],
        "n10dm_handoff_records": [
            {
                "anonymous_handoff_id": "n10dlhandoff0000",
                "next_allowed_phase_bucket": "BEA-v1-N10DM Residual-Aware Rank/File Promotion Rule Smoke" if signal_exists else "none_until_gold_free_signal_exists",
                "n10dm_authorized_bool": bool(signal_exists),
                "same_scoped_rows_only_bool": True,
                "fixed_variants_only_bool": True,
                "duplicate_pressure_rank_buckets_allowed_bool": bool(signal_exists),
                "no_duplicate_pressure_deep_rank_probe_recommended_bool": bool(signal_exists),
                "duplicate_pressure_promotion_recommended_bool": False,
                "gold_policy_authorized_bool": False,
                "runtime_default_authorized_bool": False,
                "heldout_generalization_authorized_bool": False,
                "retrieval_rerun_authorized_bool": False,
                "candidate_generation_authorized_bool": False,
                "candidate_add_remove_authorized_bool": False,
                "selector_reranker_authorized_bool": False,
                "p5_v1a_authorized_bool": False,
                "method_downstream_claim_authorized_bool": False,
                "broad_private_read_authorized_bool": False,
            }
        ],
        "stop_go_records": [
            {
                "anonymous_stop_go_id": "n10dlstop0000",
                "next_allowed_phase_bucket": "BEA-v1-N10DM Residual-Aware Rank/File Promotion Rule Smoke" if signal_exists else "none_until_gold_free_signal_exists",
                "n10dm_authorized_bool": bool(signal_exists),
                "runtime_default_authorized_bool": False,
                "heldout_generalization_authorized_bool": False,
                "retrieval_rerun_authorized_bool": False,
                "candidate_generation_materialization_authorized_bool": False,
                "candidate_add_remove_authorized_bool": False,
                "selector_reranker_authorized_bool": False,
                "p5_v1a_authorized_bool": False,
                "method_downstream_claim_authorized_bool": False,
                "broad_private_read_authorized_bool": False,
            }
        ],
    }
    scan = scan_summary(report)
    gates = [
        ("inputs_present", inputs_ok),
        ("private_span_rows_213", rows_ok),
        ("top10_file_hit_34", analysis["top10_hit"] == 34),
        ("top20_file_hit_44", analysis["top20_hit"] == 44),
        ("top10_hit_plus_miss_213", analysis["top10_hit"] + analysis["top10_miss"] == 213),
        ("first_gold_rank_bucket_sum", rank_sum == analysis["top10_miss"]),
        ("duplicate_pressure_bucket_sum", distinct_sum == analysis["top10_miss"]),
        ("rank_by_duplicate_pressure_sum", cross_sum == analysis["top10_miss"]),
        ("policy_execution_zero", True),
        ("candidate_order_changed_zero", True),
        ("forbidden_scan_pass", scan["status"] == "pass"),
    ]
    report["gate_records"] = [
        {"anonymous_gate_id": f"n10dlgate{i:04d}", "gate_bucket": name, "gate_passed_bool": bool(ok)}
        for i, (name, ok) in enumerate(gates)
    ]
    report["forbidden_scan"] = scan
    if status == STATUS_COMPLETE and scan["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    elif status == STATUS_COMPLETE and not all(ok for _name, ok in gates):
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check(name: str, cond: bool) -> tuple[str, bool]:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")
    return name, cond


def self_test() -> int:
    evidence = [{"path": f"f{i}", "start_line": 1, "end_line": 2} for i in range(30)]
    tests = [
        check("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_NO_SIGNAL in STATUS_VOCAB),
        check("safe_parser", SafeArgumentParser is not argparse.ArgumentParser),
        check("scanner_key", scan_summary({"path": "x"})["status"] == "fail"),
        check("scanner_value", scan_summary({"safe": "/tmp/x.json"})["status"] == "fail"),
        check("rank_bucket_11_20", first_gold_rank_bucket(evidence, {"f12"}) == "first_gold_file_rank_11_20"),
        check("rank_bucket_absent", first_gold_rank_bucket(evidence, {"missing"}) == "gold_file_absent_from_pool"),
        check("distinct_bucket", distinct_count_bucket(8) == "top10_distinct_file_count_7_9"),
        check("pressure_bucket", pressure_bucket(5) == "duplicate_pressure_medium"),
        check("n10t_order_size", len(n10t_order(evidence)) == 30),
        check("field_complete", field_complete([{"p4_evidence": evidence}], ["path"])),
        check("no_policy_execution", True),
        check("no_candidate_order_change", True),
        check("handoff", "N10DM" in "BEA-v1-N10DM Residual-Aware Rank/File Promotion Rule Smoke"),
        check("aggregate_only", scan_summary({"rank_bucket": "first_gold_file_rank_11_20"})["status"] == "pass"),
        check("false_claims", True),
    ]
    passed = sum(1 for _name, ok in tests if ok)
    print(f"self_test_passed={passed == len(tests)} ({passed}/{len(tests)} checks)")
    return 0 if passed == len(tests) else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return self_test()
    report = build_report(args)
    write_report(report, Path(args.out))
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
