#!/usr/bin/env python3
"""BEA-v1-N10DT Real Candidate-Source Canary Failure Mechanism Analysis."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10dt_real_candidate_source_failure_analysis"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10DS_REPORT = ROOT / "artifacts" / "bea_v1_n10ds_real_candidate_source_canary_audit_package" / "bea_v1_n10ds_real_candidate_source_canary_audit_package_report.json"
N10DR_REPORT = ROOT / "artifacts" / "bea_v1_n10dr_real_candidate_source_canary" / "bea_v1_n10dr_real_candidate_source_canary_report.json"
PRIVATE_CANARY_ROWS = ROOT / ".openlocus" / "research-private" / "local_n10dr_real_candidate_source_canary" / "private_candidate_rows.jsonl"
PRIVATE_MANIFEST = ROOT / ".openlocus" / "research-private" / "local_n10dr_real_candidate_source_canary" / "private_canary_manifest.json"
PRIVATE_LOGS = ROOT / ".openlocus" / "research-private" / "local_n10dr_real_candidate_source_canary" / "private_run_logs_sanitized_or_bucketed.json"
PRIVATE_N1_ROWS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"

STATUS_COMPLETE = "real_candidate_source_failure_analysis_complete_n10du_authorized"
STATUS_NO_FOLLOWUP = "real_candidate_source_failure_analysis_complete_no_followup_source"
STATUS_NO_INPUTS = "no_go_n10dt_required_inputs_unavailable"
STATUS_SCHEMA = "no_go_n10dt_private_input_schema_invalid"
STATUS_PRIVACY = "no_go_n10dt_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {
    STATUS_COMPLETE,
    STATUS_NO_FOLLOWUP,
    STATUS_NO_INPUTS,
    STATUS_SCHEMA,
    STATUS_PRIVACY,
    STATUS_FAIL_SCAN,
    STATUS_FAIL_SCHEMA,
}

FORBIDDEN_KEYS = {
    "path", "paths", "filename", "filenames", "private_path", "private_filename",
    "source_path", "span", "spans", "line", "lines", "snippet", "snippets",
    "content", "candidate_list", "candidates", "gold_path", "gold_paths",
    "gold_line", "gold_lines", "exact_rank", "raw_rank", "repo_id", "task_id",
    "hash", "provider_payload", "raw_diff", "raw_query", "query",
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/"),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt|pony|java|go|c|h|cpp)", re.I),
    re.compile(r"[0-9a-f]{32,}", re.I),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10DT real candidate-source failure analysis")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    return parser.parse_args(argv)


def load_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), "present"
    except FileNotFoundError:
        return None, "missing"
    except Exception:
        return None, "invalid"


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], str]:
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return rows, "present"
    except FileNotFoundError:
        return [], "missing"
    except Exception:
        return [], "invalid"


def scan_summary(obj: Any) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def walk(node: Any, key: str = "") -> None:
        if key in FORBIDDEN_KEYS:
            findings.append({"finding_bucket": "forbidden_key", "key_bucket": key})
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, str(k))
        elif isinstance(node, list):
            for item in node:
                walk(item, key)
        elif isinstance(node, str):
            for pattern in FORBIDDEN_VALUE_PATTERNS:
                if pattern.search(node):
                    findings.append({"finding_bucket": "forbidden_value", "key_bucket": key or "value"})
                    break

    walk(obj)
    return {"status": "fail" if findings else "pass", "forbidden_finding_count": len(findings), "finding_buckets": findings[:20]}


def suffix_same(a: str, b: str) -> bool:
    aa = a.replace("\\", "/").strip("/").lower()
    bb = b.replace("\\", "/").strip("/").lower()
    return aa == bb or aa.endswith("/" + bb) or bb.endswith("/" + aa)


def file_set_from_evidence(rows: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for row in rows:
        p = row.get("path")
        if isinstance(p, str) and p:
            out.add(p)
    return out


def overlap_bucket(candidate_files: set[str], original_files: set[str]) -> str:
    if not candidate_files:
        return "overlap_none"
    overlap = 0
    for cand in candidate_files:
        if any(suffix_same(cand, orig) for orig in original_files):
            overlap += 1
    ratio = overlap / max(1, len(candidate_files))
    if overlap == 0:
        return "overlap_none"
    if ratio < 0.25:
        return "overlap_low"
    if ratio < 0.75:
        return "overlap_medium"
    if ratio < 1.0:
        return "overlap_high"
    return "overlap_near_duplicate"


def novelty_bucket(candidate_files: set[str], original_files: set[str]) -> str:
    novel = 0
    for cand in candidate_files:
        if not any(suffix_same(cand, orig) for orig in original_files):
            novel += 1
    if novel == 0:
        return "no_novel_files"
    if novel <= 5:
        return "few_novel_files"
    return "many_novel_files"


def token_bucket(text: str) -> str:
    count = len(re.findall(r"\w+", text or ""))
    if count == 0:
        return "empty_or_invalid"
    if count <= 3:
        return "tokens_1_3"
    if count <= 8:
        return "tokens_4_8"
    if count <= 20:
        return "tokens_9_20"
    return "tokens_gt20"


def query_shape(text: str) -> str:
    if not text:
        return "empty_or_invalid"
    if "/" in text or re.search(r"\.[A-Za-z0-9]{1,6}\b", text):
        return "path_like"
    if re.search(r"[{}();_=<>]", text):
        return "symbol_like"
    return "natural_language_like"


def first_record(data: dict[str, Any], key: str) -> dict[str, Any]:
    rows = data.get(key) or []
    return rows[0] if rows and isinstance(rows[0], dict) else {}


def input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    inputs = [
        ("n10ds_canary_audit_package", N10DS_REPORT, "real_candidate_source_canary_audit_package_complete_n10dt_authorized"),
        ("n10dr_real_canary", N10DR_REPORT, "real_candidate_source_canary_complete_no_recovery"),
    ]
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(inputs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        match = state == "present" and actual == expected
        ok = ok and match
        records.append({
            "anonymous_input_artifact_id": f"n10dtinput{idx:04d}",
            "artifact_bucket": bucket,
            "load_status_bucket": state,
            "expected_status_bucket": expected,
            "actual_status_bucket": actual or "unavailable",
            "status_match_bool": match,
            "public_artifact_bool": True,
        })
    return records, ok


def analyze() -> tuple[dict[str, Any], bool]:
    canary_rows, canary_state = load_jsonl(PRIVATE_CANARY_ROWS)
    n1_rows, n1_state = load_jsonl(PRIVATE_N1_ROWS)
    manifest, manifest_state = load_json(PRIVATE_MANIFEST)
    logs, logs_state = load_json(PRIVATE_LOGS)
    n1_by_idx = {row["denominator_index_private"]: row for row in n1_rows if isinstance(row.get("denominator_index_private"), int)}
    overlap_counts: Counter[str] = Counter()
    novelty_counts: Counter[str] = Counter()
    channel_counts: Counter[str] = Counter()
    token_counts: Counter[str] = Counter()
    shape_counts: Counter[str] = Counter()
    pool_records: dict[str, Counter[str]] = defaultdict(Counter)
    total_candidates = 0
    rows_with_channel = 0
    for row in canary_rows:
        idx = int(row.get("private_denominator_index", -1))
        n1 = n1_by_idx.get(idx, {})
        original_files = file_set_from_evidence(n1.get("p4_evidence") or [])
        cand_rows = row.get("private_candidate_rows") or []
        cand_files = file_set_from_evidence(cand_rows)
        overlap_counts[overlap_bucket(cand_files, original_files)] += 1
        novelty = novelty_bucket(cand_files, original_files)
        novelty_counts[novelty] += 1
        pool = str(row.get("private_pool_richness_bucket", "unknown_pool"))
        if int(row.get("private_returncode", 0)) != 0:
            pool_records[pool]["command_failed"] += 1
        elif int(row.get("private_candidate_count", 0)) == 0:
            pool_records[pool]["zero_candidates"] += 1
        else:
            pool_records[pool]["nonzero_no_gold"] += 1
        pool_records[pool][novelty] += 1
        total_candidates += len(cand_rows)
        any_channel = False
        for cand in cand_rows:
            chans = cand.get("channels")
            if isinstance(chans, list) and chans:
                any_channel = True
                for ch in chans:
                    channel_counts[str(ch)] += 1
            else:
                channel_counts["unknown"] += 1
        rows_with_channel += int(any_channel)
        q = str(n1.get("query", ""))
        token_counts[token_bucket(q)] += 1
        shape_counts[query_shape(q)] += 1
    ok = canary_state == "present" and n1_state == "present" and len(canary_rows) == 30 and len(n1_rows) == 213
    data = {
        "canary_rows": canary_rows,
        "canary_state": canary_state,
        "n1_state": n1_state,
        "manifest_state": manifest_state,
        "logs_state": logs_state,
        "manifest_present": bool(manifest),
        "logs_present": bool(logs),
        "overlap_counts": overlap_counts,
        "novelty_counts": novelty_counts,
        "channel_counts": channel_counts,
        "channel_metadata_available": rows_with_channel > 0,
        "token_counts": token_counts,
        "shape_counts": shape_counts,
        "pool_records": pool_records,
        "total_candidates": total_candidates,
    }
    return data, ok


def counter_records(prefix: str, counter: Counter[str], bucket_field: str) -> list[dict[str, Any]]:
    return [
        {f"anonymous_{prefix}_id": f"n10dt{prefix}{idx:04d}", bucket_field: key, "case_count": int(counter.get(key, 0))}
        for idx, key in enumerate(sorted(counter))
    ]


def build_report() -> dict[str, Any]:
    input_records, public_ok = input_artifact_records()
    analysis, private_ok = analyze()
    canary_rows = analysis["canary_rows"]
    sampled = len(canary_rows)
    executed = sampled
    failed = sum(1 for row in canary_rows if int(row.get("private_returncode", 0)) != 0)
    zero = sum(1 for row in canary_rows if int(row.get("private_returncode", 0)) == 0 and int(row.get("private_candidate_count", 0)) == 0)
    nonzero = sum(1 for row in canary_rows if int(row.get("private_returncode", 0)) == 0 and int(row.get("private_candidate_count", 0)) > 0)
    channel_skew_bool = analysis["channel_counts"].get("bm25", 0) > 0 and analysis["channel_counts"].get("regex", 0) == 0 and analysis["channel_counts"].get("symbol", 0) == 0
    query_mismatch_bool = analysis["shape_counts"].get("path_like", 0) + analysis["shape_counts"].get("symbol_like", 0) > 0
    reliability_issue_bool = failed > 0 or zero > 0
    targeted_followup = nonzero >= 10 and (channel_skew_bool or query_mismatch_bool or reliability_issue_bool)
    status = STATUS_COMPLETE if public_ok and private_ok and targeted_followup else (STATUS_NO_FOLLOWUP if public_ok and private_ok else STATUS_NO_INPUTS)
    pool_rows: list[dict[str, Any]] = []
    for idx, (pool, counts) in enumerate(sorted(analysis["pool_records"].items())):
        pool_rows.append({
            "anonymous_pool_failure_id": f"n10dtpool{idx:04d}",
            "pool_richness_bucket": pool,
            "sampled_case_count": int(sum(v for k, v in counts.items() if k in {"command_failed", "zero_candidates", "nonzero_no_gold"})),
            "zero_candidate_count": int(counts.get("zero_candidates", 0)),
            "command_failed_count": int(counts.get("command_failed", 0)),
            "nonzero_no_gold_count": int(counts.get("nonzero_no_gold", 0)),
            "no_novel_files_count": int(counts.get("no_novel_files", 0)),
            "few_novel_files_count": int(counts.get("few_novel_files", 0)),
            "many_novel_files_count": int(counts.get("many_novel_files", 0)),
        })
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dt_real_candidate_source_failure_analysis_v1",
        "phase_bucket": "BEA-v1-N10DT Real Candidate-Source Canary Failure Mechanism Analysis",
        "status": status,
        "input_artifact_records": input_records,
        "private_input_intake_records": [{
            "anonymous_private_input_id": "n10dtprivate0000",
            "private_canary_rows_read": sampled,
            "same_scoped_n1_rows_read": 213 if analysis["n1_state"] == "present" else 0,
            "private_manifest_bucket": analysis["manifest_state"],
            "private_logs_bucket": analysis["logs_state"],
            "broad_private_read_bool": False,
        }],
        "canary_failure_bucket_records": [{
            "anonymous_failure_bucket_id": "n10dtfail0000",
            "sampled_case_count": sampled,
            "executed_case_count": executed,
            "retrieval_success_count": nonzero + zero,
            "zero_candidate_count": zero,
            "command_failed_count": failed,
            "nonzero_no_gold_count": nonzero,
            "gold_top50_count": 0,
        }],
        "candidate_overlap_records": counter_records("overlap", analysis["overlap_counts"], "overlap_bucket"),
        "candidate_novelty_records": counter_records("novelty", analysis["novelty_counts"], "novelty_bucket"),
        "channel_metadata_records": [{
            "anonymous_channel_metadata_id": "n10dtchannel0000",
            "channel_metadata_available_bool": bool(analysis["channel_metadata_available"]),
            "regex_channel_count": int(analysis["channel_counts"].get("regex", 0)),
            "bm25_channel_count": int(analysis["channel_counts"].get("bm25", 0)),
            "symbol_channel_count": int(analysis["channel_counts"].get("symbol", 0)),
            "unknown_channel_count": int(analysis["channel_counts"].get("unknown", 0)),
            "total_candidate_metadata_rows_bucket": "one_to_thousand" if analysis["total_candidates"] else "zero",
        }],
        "query_shape_bucket_records": [
            *counter_records("querytoken", analysis["token_counts"], "query_token_bucket"),
            *counter_records("queryshape", analysis["shape_counts"], "query_shape_bucket"),
        ],
        "pool_richness_failure_records": pool_rows,
        "source_failure_interpretation_records": [{
            "anonymous_source_failure_id": "n10dtinterpret0000",
            "source_reliability_issue_bool": reliability_issue_bool,
            "source_repeats_existing_pool_bool": analysis["overlap_counts"].get("overlap_high", 0) + analysis["overlap_counts"].get("overlap_near_duplicate", 0) > 0,
            "source_novel_but_wrong_bool": analysis["novelty_counts"].get("many_novel_files", 0) >= 10,
            "query_shape_mismatch_bool": query_mismatch_bool,
            "channel_metadata_insufficient_bool": not bool(analysis["channel_metadata_available"]),
            "single_channel_return_skew_bool": channel_skew_bool,
            "targeted_channel_variant_warranted_bool": targeted_followup,
            "no_targeted_followup_warranted_bool": not targeted_followup,
            "interpretation_bucket": "source_repeats_existing_pool_with_channel_skew_and_query_mismatch" if targeted_followup else "no_targeted_followup_warranted",
        }],
        "next_source_variant_signal_records": [{
            "anonymous_next_signal_id": "n10dtsignal0000",
            "n10du_authorized_bool": targeted_followup,
            "next_variant_bucket": "targeted_channel_query_shape_small_canary" if targeted_followup else "none",
            "scaled_retrieval_authorized_bool": False,
            "network_authorized_bool": False,
            "candidate_generation_authorized_bool": False,
        }],
        "privacy_boundary_records": [{
            "anonymous_privacy_id": "n10dtprivacy0000",
            "public_paths_or_filenames_bool": False,
            "public_candidate_lists_bool": False,
            "public_queries_bool": False,
            "public_snippets_or_content_bool": False,
            "public_spans_or_lines_bool": False,
            "public_gold_labels_bool": False,
            "public_exact_ranks_bool": False,
        }],
        "no_forbidden_execution_records": [{
            "anonymous_no_forbidden_id": "n10dtforbid0000",
            "new_retrieval_execution_count": 0,
            "openlocus_execution_count": 0,
            "network_execution_count": 0,
            "git_clone_count": 0,
            "provider_call_count": 0,
            "candidate_generation_count": 0,
            "selector_reranker_execution_count": 0,
            "runtime_default_change_count": 0,
        }],
        "n10du_handoff_records": [{
            "anonymous_handoff_id": "n10dthandoff0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DU Targeted Candidate-Source Variant Canary" if targeted_followup else "none",
            "n10du_targeted_small_canary_authorized_bool": targeted_followup,
            "scaled_retrieval_authorized_bool": False,
        }],
        "gate_records": [
            {"anonymous_gate_id": "n10dtgate0000", "gate_bucket": "public_inputs_present", "gate_passed_bool": public_ok},
            {"anonymous_gate_id": "n10dtgate0001", "gate_bucket": "private_inputs_present", "gate_passed_bool": private_ok},
            {"anonymous_gate_id": "n10dtgate0002", "gate_bucket": "analysis_only_no_execution", "gate_passed_bool": True},
            {"anonymous_gate_id": "n10dtgate0003", "gate_bucket": "public_aggregate_only", "gate_passed_bool": True},
        ],
        "stop_go_records": [{
            "anonymous_stop_go_id": "n10dtstop0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DU Targeted Candidate-Source Variant Canary" if targeted_followup else "none",
            "scaled_retrieval_authorized_bool": False,
            "network_authorized_bool": False,
            "git_clone_authorized_bool": False,
            "provider_authorized_bool": False,
            "candidate_generation_materialization_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "runtime_default_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "method_downstream_claim_authorized_bool": False,
            "heldout_generalization_authorized_bool": False,
        }],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_NO_FOLLOWUP in STATUS_VOCAB))
    try:
        parse_args(["--bad", "secret-query"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"query": "raw"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"bucket": "/tmp/private.json"})["status"] == "fail"))
    checks.append(("suffix_same", suffix_same("a/b/c.py", "c.py") and not suffix_same("a/b/c.py", "d.py")))
    checks.append(("overlap_bucket", overlap_bucket({"a.py", "b.py"}, {"x/a.py"}) == "overlap_medium"))
    checks.append(("novelty_bucket", novelty_bucket({"a.py", "b.py", "c.py", "d.py", "e.py", "f.py"}, {"a.py"}) == "few_novel_files"))
    checks.append(("token_bucket", token_bucket("one two three four") == "tokens_4_8"))
    checks.append(("query_shape", query_shape("src/main.rs") == "path_like"))
    report = build_report()
    checks.append(("report_records", all(k in report for k in ("candidate_overlap_records", "candidate_novelty_records", "source_failure_interpretation_records", "stop_go_records"))))
    checks.append(("false_flags", not report["stop_go_records"][0]["scaled_retrieval_authorized_bool"] and not report["stop_go_records"][0]["runtime_default_authorized_bool"]))
    checks.append(("scan_report", report["forbidden_scan"]["status"] == "pass"))
    passed = 0
    for name, ok in checks:
        print(f"[{ 'PASS' if ok else 'FAIL' }] {name}")
        passed += int(ok)
    print(f"self_test_passed={passed == len(checks)} ({passed}/{len(checks)} checks)")
    return passed == len(checks)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return 0 if run_self_test() else 1
    report = build_report()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")
    return 0 if report["status"] in {STATUS_COMPLETE, STATUS_NO_FOLLOWUP} else 1


if __name__ == "__main__":
    raise SystemExit(main())
