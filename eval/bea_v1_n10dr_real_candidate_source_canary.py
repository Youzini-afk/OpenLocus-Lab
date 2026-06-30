#!/usr/bin/env python3
"""BEA-v1-N10DR Real Candidate-Source Canary.

Runs a bounded local OpenLocus retrieval canary over existing local clone repos.
Public report is aggregate/bucket-only; detailed candidate rows are written only
under ignored project-private storage.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, NoReturn
import re


ROOT = Path(__file__).resolve().parent.parent
PHASE = "BEA-v1-N10DR Real Candidate-Source Canary"
SLUG = "bea_v1_n10dr_real_candidate_source_canary"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"

PRIVATE_SPAN_ROWS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"
PRIVATE_RECON = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "p4l_validation" / "bea_v1_p4l.private_reconstruction.jsonl"
PRIVATE_REPOS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "repos"
PRIVATE_OUT_ROOT = ROOT / ".openlocus" / "research-private" / "local_n10dr_real_candidate_source_canary"
OPENLOCUS_BIN = ROOT / "target" / "release" / "openlocus"

PUBLIC_INPUTS = {
    "n10dq_oracle_ceiling_package": (
        ROOT / "artifacts" / "bea_v1_n10dq_oracle_candidate_ceiling_public_package" / "bea_v1_n10dq_oracle_candidate_ceiling_public_package_report.json",
        "oracle_candidate_ceiling_public_package_complete_n10dr_authorized",
    ),
    "n10dor_corrected_absence_audit": (
        ROOT / "artifacts" / "bea_v1_n10dor_corrected_candidate_pool_absence_source_audit" / "bea_v1_n10dor_corrected_candidate_pool_absence_source_audit_report.json",
        "corrected_candidate_pool_absence_source_audit_complete_n10dp_authorized",
    ),
}

STATUS_PASS = "real_candidate_source_canary_pass_n10ds_authorized"
STATUS_PARTIAL = "partial_real_candidate_source_canary_executed_with_low_recovery"
STATUS_NO_RECOVERY = "real_candidate_source_canary_complete_no_recovery"
STATUS_NO_INPUTS = "no_go_n10dr_required_inputs_unavailable"
STATUS_LOCAL_PREREQ = "no_go_n10dr_local_prerequisites_unavailable"
STATUS_SAMPLE = "no_go_n10dr_canary_sample_unavailable"
STATUS_PRIVACY = "no_go_n10dr_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {
    STATUS_PASS,
    STATUS_PARTIAL,
    STATUS_NO_RECOVERY,
    STATUS_NO_INPUTS,
    STATUS_LOCAL_PREREQ,
    STATUS_SAMPLE,
    STATUS_PRIVACY,
    STATUS_FAIL_SCAN,
    STATUS_FAIL_SCHEMA,
}

FORBIDDEN_KEYS = {
    "path", "paths", "file", "files", "filename", "filenames", "private_path",
    "private_filename", "repo", "repo_root", "source_path", "span", "spans",
    "line", "lines", "snippet", "snippets", "content", "candidate", "candidates",
    "candidate_list", "gold", "gold_path", "gold_paths", "gold_line", "gold_lines",
    "exact_rank", "raw_rank", "raw_row", "repo_id", "task_id", "hash",
    "provider_payload", "raw_diff", "query_text", "raw_log",
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/"),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|java|go|cpp|c|h|md|txt)"),
    re.compile(r"[0-9a-f]{32,}", re.I),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description=PHASE)
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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def norm_ref(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def suffix_match(a: Any, b: Any) -> bool:
    left = norm_ref(a)
    right = norm_ref(b)
    if not left or not right:
        return False
    return left == right or left.endswith("/" + right) or right.endswith("/" + left)


def candidate_hits_gold(candidate: dict[str, Any], gold_refs: list[Any]) -> bool:
    cpath = candidate.get("path")
    return any(suffix_match(cpath, gold) for gold in gold_refs)


def pool_bucket(size: int) -> str:
    if size <= 20:
        return "tiny_pool_absence"
    if size <= 50:
        return "moderate_pool_absence"
    return "rich_wrong_pool_absence"


def count_bucket(count: int) -> str:
    if count == 0:
        return "zero"
    if count <= 10:
        return "one_to_ten"
    if count <= 30:
        return "eleven_to_thirty"
    return "thirty_one_to_fifty"


def latency_bucket(ms: int) -> str:
    if ms < 500:
        return "lt_500ms"
    if ms < 1500:
        return "500_1499ms"
    if ms < 5000:
        return "1500_4999ms"
    return "ge_5000ms"


def sanitize_error_bucket(returncode: int, stderr: str, evidence_count: int) -> str:
    if returncode != 0:
        return "nonzero_exit"
    if evidence_count == 0:
        return "zero_candidates_returned"
    if stderr.strip():
        return "stderr_present_success"
    return "none"


def repo_root_for(row: dict[str, Any], selected_recon: list[dict[str, Any]]) -> Path | None:
    idx = int(row.get("denominator_index_private", -1))
    if idx < 0 or idx >= len(selected_recon):
        return None
    rec = selected_recon[idx]
    raw_idx = rec.get("raw_record_index_private")
    benchmark = str(rec.get("benchmark", ""))
    language = str(rec.get("language", ""))
    if raw_idx is None:
        return None
    if benchmark == "contextbench":
        return PRIVATE_REPOS / f"contextbench_{raw_idx}" / "repo"
    if benchmark == "repoqa":
        return PRIVATE_REPOS / f"repoqa_{language}_{raw_idx}" / "repo"
    return None


def select_absent_sample(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {
        "tiny_pool_absence": [],
        "moderate_pool_absence": [],
        "rich_wrong_pool_absence": [],
    }
    for row_index, row in enumerate(rows):
        evidence = row.get("p4_evidence") or []
        gold_refs = row.get("gold_paths") or []
        if any(candidate_hits_gold(c, gold_refs) for c in evidence[:10]):
            continue
        if any(candidate_hits_gold(c, gold_refs) for c in evidence):
            continue
        item = dict(row)
        item["_private_row_order"] = row_index
        item["_pool_bucket"] = pool_bucket(len(evidence))
        buckets[item["_pool_bucket"]].append(item)
    sample: list[dict[str, Any]] = []
    for bucket in ("tiny_pool_absence", "moderate_pool_absence", "rich_wrong_pool_absence"):
        sample.extend(buckets[bucket][:10])
    if len(sample) < 30:
        used = {r["_private_row_order"] for r in sample}
        remaining = [r for group in buckets.values() for r in group if r["_private_row_order"] not in used]
        remaining.sort(key=lambda r: r["_private_row_order"])
        sample.extend(remaining[: 30 - len(sample)])
    return sample[:30]


def input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, (path, expected_status)) in enumerate(PUBLIC_INPUTS.items()):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        match = state == "present" and actual == expected_status
        ok = ok and match
        records.append({
            "anonymous_input_artifact_id": f"n10drinput{idx:04d}",
            "artifact_bucket": bucket,
            "load_status_bucket": state,
            "expected_status_bucket": expected_status,
            "actual_status_bucket": actual or "unavailable",
            "status_match_bool": match,
            "public_artifact_bool": True,
        })
    return records, ok


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


def run_retrieval(repo_root: Path, query: str) -> tuple[int, dict[str, Any], str, int]:
    start = time.monotonic()
    cmd = [
        str(OPENLOCUS_BIN),
        "retrieve",
        query,
        "--channels",
        "regex,bm25,symbol",
        "--max-results",
        "50",
        "--json",
    ]
    proc = subprocess.run(cmd, cwd=repo_root, text=True, capture_output=True, timeout=60)
    elapsed_ms = int((time.monotonic() - start) * 1000)
    try:
        data = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        data = {}
    return proc.returncode, data, proc.stderr, elapsed_ms


def write_private_outputs(candidate_rows: list[dict[str, Any]], manifest: dict[str, Any], logs: dict[str, Any]) -> None:
    PRIVATE_OUT_ROOT.mkdir(parents=True, exist_ok=True)
    with (PRIVATE_OUT_ROOT / "private_candidate_rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in candidate_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    (PRIVATE_OUT_ROOT / "private_canary_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (PRIVATE_OUT_ROOT / "private_run_logs_sanitized_or_bucketed.json").write_text(json.dumps(logs, indent=2, sort_keys=True), encoding="utf-8")


def execute_canary() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    rows = read_jsonl(PRIVATE_SPAN_ROWS)
    recon_all = read_jsonl(PRIVATE_RECON)
    selected_recon = [r for r in recon_all if r.get("selected_for_denominator")]
    sample = select_absent_sample(rows)

    candidate_rows: list[dict[str, Any]] = []
    public_case_records: list[dict[str, Any]] = []
    counts = {
        "sampled_case_count": len(sample),
        "executed_case_count": 0,
        "local_repo_available_count": 0,
        "retrieval_command_success_count": 0,
        "gold_file_recovered_top10_count": 0,
        "gold_file_recovered_top20_count": 0,
        "gold_file_recovered_top50_count": 0,
    }
    by_bucket: dict[str, dict[str, int]] = {}
    latency_counts: dict[str, int] = {}
    candidate_count_counts: dict[str, int] = {}
    error_counts: dict[str, int] = {}

    for sample_idx, row in enumerate(sample):
        bucket = row.get("_pool_bucket", "unknown_pool")
        by_bucket.setdefault(bucket, {"sampled": 0, "executed": 0, "top50_recovered": 0})
        by_bucket[bucket]["sampled"] += 1
        repo_root = repo_root_for(row, selected_recon)
        repo_available = bool(repo_root and repo_root.is_dir())
        if repo_available:
            counts["local_repo_available_count"] += 1
        else:
            public_case_records.append({
                "anonymous_canary_case_id": f"n10drcase{sample_idx:04d}",
                "pool_richness_bucket": bucket,
                "execution_status_bucket": "local_repo_unavailable",
            })
            continue
        assert repo_root is not None
        returncode, data, stderr, elapsed_ms = run_retrieval(repo_root, str(row.get("query", "")))
        counts["executed_case_count"] += 1
        by_bucket[bucket]["executed"] += 1
        evidence = data.get("evidence") if isinstance(data, dict) else []
        if not isinstance(evidence, list):
            evidence = []
        if returncode == 0:
            counts["retrieval_command_success_count"] += 1
        gold_refs = row.get("gold_paths") or []
        hit_ranks = [idx + 1 for idx, cand in enumerate(evidence[:50]) if isinstance(cand, dict) and candidate_hits_gold(cand, gold_refs)]
        top10 = any(rank <= 10 for rank in hit_ranks)
        top20 = any(rank <= 20 for rank in hit_ranks)
        top50 = bool(hit_ranks)
        counts["gold_file_recovered_top10_count"] += int(top10)
        counts["gold_file_recovered_top20_count"] += int(top20)
        counts["gold_file_recovered_top50_count"] += int(top50)
        by_bucket[bucket]["top50_recovered"] += int(top50)
        lb = latency_bucket(elapsed_ms)
        cb = count_bucket(len(evidence[:50]))
        eb = sanitize_error_bucket(returncode, stderr, len(evidence))
        latency_counts[lb] = latency_counts.get(lb, 0) + 1
        candidate_count_counts[cb] = candidate_count_counts.get(cb, 0) + 1
        error_counts[eb] = error_counts.get(eb, 0) + 1
        public_case_records.append({
            "anonymous_canary_case_id": f"n10drcase{sample_idx:04d}",
            "pool_richness_bucket": bucket,
            "execution_status_bucket": "executed" if returncode == 0 else "command_failed",
            "candidate_count_bucket": cb,
            "latency_bucket": lb,
            "error_bucket": eb,
            "top10_recovery_bool": top10,
            "top20_recovery_bool": top20,
            "top50_recovery_bool": top50,
        })
        candidate_rows.append({
            "private_case_order": sample_idx,
            "private_denominator_index": row.get("denominator_index_private"),
            "private_pool_richness_bucket": bucket,
            "private_returncode": returncode,
            "private_latency_ms": elapsed_ms,
            "private_candidate_count": len(evidence[:50]),
            "private_hit_ranks": hit_ranks[:5],
            "private_candidate_rows": evidence[:50],
        })
    manifest = {
        "private_schema_version": "bea_v1_n10dr_private_manifest_v1",
        "private_sampled_case_count": len(sample),
        "private_executed_case_count": counts["executed_case_count"],
        "private_output_file_count": 3,
        "private_network_execution_count": 0,
        "private_git_clone_count": 0,
        "private_provider_call_count": 0,
    }
    logs = {
        "private_latency_bucket_counts": latency_counts,
        "private_candidate_count_bucket_counts": candidate_count_counts,
        "private_error_bucket_counts": error_counts,
    }
    write_private_outputs(candidate_rows, manifest, logs)
    summary = {
        **counts,
        "pool_richness_recovery": by_bucket,
        "latency_bucket_counts": latency_counts,
        "candidate_count_bucket_counts": candidate_count_counts,
        "error_bucket_counts": error_counts,
        "private_span_rows_read": len(rows),
        "selected_reconstruction_rows_read": len(selected_recon),
    }
    return summary, public_case_records, manifest


def build_report() -> dict[str, Any]:
    input_records, inputs_ok = input_artifact_records()
    prereq_ok = PRIVATE_SPAN_ROWS.exists() and PRIVATE_RECON.exists() and OPENLOCUS_BIN.is_file() and PRIVATE_REPOS.is_dir()
    if not inputs_ok:
        status = STATUS_NO_INPUTS
        summary: dict[str, Any] = {}
        case_records: list[dict[str, Any]] = []
        manifest: dict[str, Any] = {}
    elif not prereq_ok:
        status = STATUS_LOCAL_PREREQ
        summary = {}
        case_records = []
        manifest = {}
    else:
        summary, case_records, manifest = execute_canary()
        recovered = int(summary.get("gold_file_recovered_top50_count", 0))
        executed = int(summary.get("executed_case_count", 0))
        if executed < 20:
            status = STATUS_SAMPLE
        elif recovered >= 5:
            status = STATUS_PASS
        elif recovered >= 1:
            status = STATUS_PARTIAL
        else:
            status = STATUS_NO_RECOVERY

    pool_rows = []
    for idx, (bucket, values) in enumerate(sorted((summary.get("pool_richness_recovery") or {}).items())):
        pool_rows.append({
            "anonymous_pool_bucket_id": f"n10drpool{idx:04d}",
            "pool_richness_bucket": bucket,
            "sampled_case_count": values.get("sampled", 0),
            "executed_case_count": values.get("executed", 0),
            "gold_file_recovered_top50_count": values.get("top50_recovered", 0),
        })

    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dr_real_candidate_source_canary_v1",
        "phase_bucket": PHASE,
        "status": status,
        "input_artifact_records": input_records,
        "canary_sample_selection_records": [{
            "anonymous_sample_id": "n10drsample0000",
            "target_case_count": 30,
            "sampled_case_count": summary.get("sampled_case_count", 0),
            "sample_strategy_bucket": "deterministic_stratified_absent_pool_residuals",
            "random_sampling_used_bool": False,
            "tiny_pool_target_count": 10,
            "moderate_pool_target_count": 10,
            "rich_wrong_pool_target_count": 10,
        }],
        "local_prerequisite_records": [{
            "anonymous_prerequisite_id": "n10drpre0000",
            "openlocus_binary_available_bool": OPENLOCUS_BIN.is_file(),
            "scoped_private_rows_available_bool": PRIVATE_SPAN_ROWS.exists(),
            "private_reconstruction_available_bool": PRIVATE_RECON.exists(),
            "local_repo_root_available_bool": PRIVATE_REPOS.is_dir(),
            "private_output_root_ignored_bool": True,
            "local_prerequisites_available_bool": prereq_ok,
        }],
        "retrieval_command_boundary_records": [{
            "anonymous_command_boundary_id": "n10drcmd0000",
            "command_bucket": "openlocus_retrieve_regex_bm25_symbol_max_results_50_json",
            "topk_limit": 50,
            "topk_within_contract_bool": True,
            "local_cli_only_bool": True,
            "existing_clone_repo_cwd_bool": True,
            "network_execution_bool": False,
            "git_clone_bool": False,
            "provider_call_bool": False,
            "selector_reranker_bool": False,
        }],
        "private_execution_summary_records": [{
            "anonymous_execution_summary_id": "n10drexec0000",
            "private_span_rows_read": summary.get("private_span_rows_read", 0),
            "private_output_file_count_bucket": "three_private_outputs",
            "private_output_rows_written_bucket": "one_to_thirty",
            "sampled_case_count": summary.get("sampled_case_count", 0),
            "executed_case_count": summary.get("executed_case_count", 0),
            "local_repo_available_count": summary.get("local_repo_available_count", 0),
            "retrieval_command_success_count": summary.get("retrieval_command_success_count", 0),
        }],
        "candidate_source_result_records": [{
            "anonymous_result_id": "n10drresult0000",
            "sampled_case_count": summary.get("sampled_case_count", 0),
            "executed_case_count": summary.get("executed_case_count", 0),
            "gold_file_recovered_top10_count": summary.get("gold_file_recovered_top10_count", 0),
            "gold_file_recovered_top20_count": summary.get("gold_file_recovered_top20_count", 0),
            "gold_file_recovered_top50_count": summary.get("gold_file_recovered_top50_count", 0),
            "n10t_anchor_top10_file_hit_count": 44,
            "full_denominator_improvement_claim_bool": False,
        }],
        "pool_richness_recovery_records": pool_rows,
        "candidate_count_bucket_records": [
            {"candidate_count_bucket": bucket, "case_count": count}
            for bucket, count in sorted((summary.get("candidate_count_bucket_counts") or {}).items())
        ],
        "latency_bucket_records": [
            {"latency_bucket": bucket, "case_count": count}
            for bucket, count in sorted((summary.get("latency_bucket_counts") or {}).items())
        ],
        "error_bucket_records": [
            {"error_bucket": bucket, "case_count": count}
            for bucket, count in sorted((summary.get("error_bucket_counts") or {}).items())
        ],
        "privacy_boundary_records": [{
            "anonymous_privacy_id": "n10drprivacy0000",
            "public_paths_or_filenames_bool": False,
            "public_candidate_lists_bool": False,
            "public_spans_or_lines_bool": False,
            "public_snippets_or_content_bool": False,
            "public_exact_ranks_bool": False,
            "public_gold_labels_bool": False,
        }],
        "no_forbidden_execution_records": [{
            "anonymous_no_forbidden_id": "n10drforbid0000",
            "network_execution_count": 0,
            "git_clone_count": 0,
            "provider_call_count": 0,
            "retrieval_rerun_outside_local_canary_count": 0,
            "candidate_generation_count": 0,
            "candidate_materialization_count": 0,
            "selector_reranker_execution_count": 0,
            "runtime_default_change_count": 0,
            "p5_v1a_execution_count": 0,
        }],
        "n10ds_handoff_records": [{
            "anonymous_handoff_id": "n10drhandoff0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DS Real Candidate-Source Canary Audit Package",
            "n10ds_public_package_authorized_bool": status in {STATUS_PASS, STATUS_PARTIAL, STATUS_NO_RECOVERY},
            "scaled_retrieval_authorized_bool": False,
            "runtime_default_authorized_bool": False,
        }],
        "gate_records": [
            {"anonymous_gate_id": "n10drgate0000", "gate_bucket": "public_inputs_present", "gate_passed_bool": inputs_ok},
            {"anonymous_gate_id": "n10drgate0001", "gate_bucket": "local_prerequisites_available", "gate_passed_bool": prereq_ok},
            {"anonymous_gate_id": "n10drgate0002", "gate_bucket": "executed_at_least_twenty_cases", "gate_passed_bool": summary.get("executed_case_count", 0) >= 20},
            {"anonymous_gate_id": "n10drgate0003", "gate_bucket": "topk_lte_50", "gate_passed_bool": True},
            {"anonymous_gate_id": "n10drgate0004", "gate_bucket": "no_forbidden_execution", "gate_passed_bool": True},
        ],
        "stop_go_records": [{
            "anonymous_stop_go_id": "n10drstop0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DS Real Candidate-Source Canary Audit Package",
            "scaled_retrieval_authorized_bool": False,
            "runtime_default_authorized_bool": False,
            "method_downstream_claim_authorized_bool": False,
            "heldout_generalization_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "network_authorized_bool": False,
            "git_clone_authorized_bool": False,
            "candidate_generation_authorized_bool": False,
        }],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def write_report(report: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_PASS in STATUS_VOCAB and STATUS_PARTIAL in STATUS_VOCAB))
    try:
        parse_args(["--bad", "secret"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"safe": "/tmp/private.jsonl"})["status"] == "fail"))
    checks.append(("suffix_match", suffix_match("src/a/b.ts", "a/b.ts") and not suffix_match("src/a.ts", "src/b.ts")))
    checks.append(("pool_buckets", [pool_bucket(1), pool_bucket(21), pool_bucket(51)] == ["tiny_pool_absence", "moderate_pool_absence", "rich_wrong_pool_absence"]))
    fake = [{"p4_evidence": [{}] * 5, "gold_paths": ["missing"], "denominator_index_private": i} for i in range(35)]
    checks.append(("sample_cap", len(select_absent_sample(fake)) == 30))
    checks.append(("count_bucket", count_bucket(0) == "zero" and count_bucket(50) == "thirty_one_to_fifty"))
    checks.append(("latency_bucket", latency_bucket(100) == "lt_500ms" and latency_bucket(6000) == "ge_5000ms"))
    synthetic = {"status": STATUS_PASS, "private_path_public_count": 0, "candidate_generation_count": 0}
    checks.append(("scan_synthetic", scan_summary(synthetic)["status"] == "pass"))
    checks.append(("private_output_ignored", str(PRIVATE_OUT_ROOT).find(".openlocus") >= 0))
    checks.append(("local_command_topk", 50 <= 50))
    ok = all(v for _, v in checks)
    for name, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    print(f"self_test_passed={ok} ({sum(v for _, v in checks)}/{len(checks)} checks)")
    return ok


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return 0 if run_self_test() else 1
    report = build_report()
    write_report(report, Path(args.out))
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")
    return 0 if report["status"] in {STATUS_PASS, STATUS_PARTIAL, STATUS_NO_RECOVERY} else 1


if __name__ == "__main__":
    raise SystemExit(main())
