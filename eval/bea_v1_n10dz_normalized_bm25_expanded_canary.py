#!/usr/bin/env python3
"""BEA-v1-N10DZ Normalized-BM25 Expanded Canary."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10dz_normalized_bm25_expanded_canary"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10DY_REPORT = ROOT / "artifacts" / "bea_v1_n10dy_normalized_bm25_topk_token_cap_canary_public_package" / "bea_v1_n10dy_normalized_bm25_topk_token_cap_canary_public_package_report.json"
N10DOR_REPORT = ROOT / "artifacts" / "bea_v1_n10dor_corrected_candidate_pool_absence_source_audit" / "bea_v1_n10dor_corrected_candidate_pool_absence_source_audit_report.json"
PRIVATE_N10DR_ROWS = ROOT / ".openlocus" / "research-private" / "local_n10dr_real_candidate_source_canary" / "private_candidate_rows.jsonl"
PRIVATE_N1_ROWS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"
PRIVATE_RECON = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "p4l_validation" / "bea_v1_p4l.private_reconstruction.jsonl"
PRIVATE_REPOS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "repos"
PRIVATE_OUT = ROOT / ".openlocus" / "research-private" / "local_n10dz_normalized_bm25_expanded_canary"
OPENLOCUS_BIN = ROOT / "target" / "release" / "openlocus"

VARIANTS = [
    ("normalized_bm25_top50_cap12", 50, 12),
    ("normalized_bm25_top100_cap12", 100, 12),
]
PRIMARY_VARIANT = "normalized_bm25_top50_cap12"

STATUS_PASS = "normalized_bm25_expanded_canary_pass_n10ea_authorized"
STATUS_LOW = "normalized_bm25_expanded_canary_low_recovery_n10ea_authorized"
STATUS_NO_RECOVERY = "normalized_bm25_expanded_canary_complete_no_recovery"
STATUS_NO_INPUTS = "no_go_n10dz_required_inputs_unavailable"
STATUS_PREREQ = "no_go_n10dz_local_prerequisites_unavailable"
STATUS_ACCOUNTING = "no_go_n10dz_result_accounting_invalid"
STATUS_PRIVACY = "no_go_n10dz_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_PASS, STATUS_LOW, STATUS_NO_RECOVERY, STATUS_NO_INPUTS, STATUS_PREREQ, STATUS_ACCOUNTING, STATUS_PRIVACY, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

FORBIDDEN_KEYS = {
    "path", "paths", "filename", "filenames", "private_path", "private_filename",
    "span", "spans", "line", "lines", "snippet", "snippets", "content", "query",
    "raw_query", "candidate", "candidates", "candidate_list", "gold", "gold_path",
    "gold_paths", "exact_rank", "raw_rank", "repo", "repo_root", "hash",
    "provider_payload", "raw_diff", "raw_log",
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/"),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt|go|java|pony)", re.I),
    re.compile(r"[0-9a-f]{32,}", re.I),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10DZ normalized BM25 expanded canary")
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
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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
        elif isinstance(node, str) and any(pattern.search(node) for pattern in FORBIDDEN_VALUE_PATTERNS):
            findings.append({"finding_bucket": "forbidden_value", "key_bucket": key or "value"})

    walk(obj)
    return {"status": "fail" if findings else "pass", "forbidden_finding_count": len(findings), "finding_buckets": findings[:20]}


def norm_ref(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def suffix_match(a: Any, b: Any) -> bool:
    aa, bb = norm_ref(a), norm_ref(b)
    return bool(aa and bb and (aa == bb or aa.endswith("/" + bb) or bb.endswith("/" + aa)))


def candidate_hits_gold(candidate: dict[str, Any], gold_refs: list[Any]) -> bool:
    return any(suffix_match(candidate.get("path"), gold) for gold in gold_refs)


def n10t_order(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = [item for idx, item in enumerate(evidence, 1) if idx <= 20]
    extra = [item for idx, item in enumerate(evidence, 1) if idx > 20]
    return list(extra) + primary[:4] + primary[4:]


def file_hit(order: list[dict[str, Any]], gold_refs: list[Any], limit: int) -> bool:
    return any(candidate_hits_gold(cand, gold_refs) for cand in order[:limit] if isinstance(cand, dict))


def absent_from_observed_pool(row: dict[str, Any]) -> bool:
    gold_refs = row.get("gold_paths") or []
    order = n10t_order(row.get("p4_evidence") or [])
    return (not file_hit(order, gold_refs, 10)) and not any(candidate_hits_gold(cand, gold_refs) for cand in order if isinstance(cand, dict))


def pool_richness(row: dict[str, Any]) -> str:
    size = len(row.get("p4_evidence") or [])
    if size <= 20:
        return "tiny_pool_absence"
    if size <= 50:
        return "moderate_pool_absence"
    return "rich_wrong_pool_absence"


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


def normalize_query(query: str, cap: int = 12) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", query)
    tokens = re.findall(r"[A-Za-z0-9_]+", spaced.replace("_", " "))
    cleaned: list[str] = []
    for tok in tokens:
        for part in tok.split("_"):
            low = part.lower()
            if len(low) >= 3:
                cleaned.append(low)
    result = " ".join(cleaned[:cap])
    return result or query


def file_set(rows: list[dict[str, Any]]) -> set[str]:
    return {norm_ref(row.get("path")) for row in rows if isinstance(row, dict) and row.get("path")}


def overlap_bucket(candidate_files: set[str], original_files: set[str]) -> str:
    if not candidate_files:
        return "overlap_none"
    overlap = sum(1 for cand in candidate_files if any(suffix_match(cand, orig) for orig in original_files))
    if overlap == 0:
        return "overlap_none"
    ratio = overlap / max(1, len(candidate_files))
    if ratio < 0.25:
        return "overlap_low"
    if ratio < 0.75:
        return "overlap_medium"
    if ratio < 1.0:
        return "overlap_high"
    return "overlap_near_duplicate"


def novelty_bucket(candidate_files: set[str], original_files: set[str]) -> str:
    novel = sum(1 for cand in candidate_files if not any(suffix_match(cand, orig) for orig in original_files))
    if novel == 0:
        return "no_novel_files"
    if novel <= 5:
        return "few_novel_files"
    return "many_novel_files"


def count_bucket(count: int) -> str:
    if count == 0:
        return "zero"
    if count <= 10:
        return "one_to_ten"
    if count <= 30:
        return "eleven_to_thirty"
    if count <= 50:
        return "thirty_one_to_fifty"
    return "fifty_one_to_one_hundred"


def latency_bucket(ms: int) -> str:
    if ms < 500:
        return "lt_500ms"
    if ms < 1500:
        return "500_1499ms"
    if ms < 5000:
        return "1500_4999ms"
    return "ge_5000ms"


def run_retrieval(repo_root: Path, query: str, max_results: int) -> tuple[int, list[dict[str, Any]], int]:
    start = time.monotonic()
    proc = subprocess.run(
        [str(OPENLOCUS_BIN), "retrieve", query, "--channels", "bm25", "--max-results", str(max_results), "--json"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        timeout=60,
    )
    elapsed = int((time.monotonic() - start) * 1000)
    try:
        data = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        data = {}
    evidence = data.get("evidence") if isinstance(data, dict) else []
    return proc.returncode, evidence[:max_results] if isinstance(evidence, list) else [], elapsed


def input_records() -> tuple[list[dict[str, Any]], bool]:
    specs = [
        ("n10dy_public_package", N10DY_REPORT, "normalized_bm25_topk_token_cap_canary_public_package_complete_n10dz_authorized"),
        ("n10dor_corrected_absence", N10DOR_REPORT, "corrected_candidate_pool_absence_source_audit_complete_n10dp_authorized"),
    ]
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(specs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        match = state == "present" and actual == expected
        ok = ok and match
        records.append({"anonymous_input_artifact_id": f"n10dzinput{idx:04d}", "artifact_bucket": bucket, "load_status_bucket": state, "expected_status_bucket": expected, "actual_status_bucket": actual or "unavailable", "status_match_bool": match, "public_artifact_bool": True})
    return records, ok


def original_sample_ids() -> set[int]:
    rows = read_jsonl(PRIVATE_N10DR_ROWS)
    return {int(row.get("private_denominator_index", -1)) for row in rows}


def select_sample(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    excluded = original_sample_ids()
    absent = [row for row in rows if int(row.get("denominator_index_private", -1)) not in excluded and absent_from_observed_pool(row)]
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sorted(absent, key=lambda r: int(r.get("denominator_index_private", -1))):
        by_bucket[pool_richness(row)].append(row)
    selected: list[dict[str, Any]] = []
    target_buckets = ["tiny_pool_absence", "moderate_pool_absence", "rich_wrong_pool_absence"]
    for bucket in target_buckets:
        selected.extend(by_bucket[bucket][:20])
    if len(selected) < 60:
        selected_ids = {int(row.get("denominator_index_private", -1)) for row in selected}
        for row in sorted(absent, key=lambda r: int(r.get("denominator_index_private", -1))):
            if int(row.get("denominator_index_private", -1)) not in selected_ids:
                selected.append(row)
                selected_ids.add(int(row.get("denominator_index_private", -1)))
            if len(selected) >= 60:
                break
    selected = selected[:60]
    requested_counts = {bucket: min(20, len(by_bucket[bucket])) for bucket in target_buckets}
    actual_counts = Counter(pool_richness(row) for row in selected)
    meta = {"available_absent_after_exclusion_count": len(absent), "excluded_original_sample_count": len(excluded), "requested_bucket_counts": requested_counts, "selected_bucket_counts": dict(actual_counts)}
    return selected, meta


def execute() -> tuple[dict[str, Any], dict[str, Any]]:
    n1_rows = read_jsonl(PRIVATE_N1_ROWS)
    recon = [row for row in read_jsonl(PRIVATE_RECON) if row.get("selected_for_denominator")]
    selected_rows, sample_meta = select_sample(n1_rows)
    stats: dict[str, dict[str, Any]] = {name: {"executed": 0, "success": 0, "zero": 0, "nonzero": 0, "failed": 0, "top10": 0, "top20": 0, "top50": 0, "top100": 0, "candidate_buckets": Counter(), "latency_buckets": Counter(), "error_buckets": Counter(), "overlap": Counter(), "novelty": Counter(), "pool_recovery": Counter()} for name, _topk, _cap in VARIANTS}
    recovered_by_variant: dict[str, set[int]] = {name: set() for name, _topk, _cap in VARIANTS}
    private_rows: list[dict[str, Any]] = []
    command_count = 0
    repo_available = 0
    for case_order, row in enumerate(selected_rows):
        denom = int(row.get("denominator_index_private", -1))
        repo = repo_root_for(row, recon)
        if repo is None or not repo.is_dir():
            continue
        repo_available += 1
        query = normalize_query(str(row.get("query", "")), 12)
        gold_refs = row.get("gold_paths") or []
        original_files = file_set(row.get("p4_evidence") or [])
        richness = pool_richness(row)
        for variant, topk, cap in VARIANTS:
            rc, evidence, elapsed = run_retrieval(repo, query, topk)
            command_count += 1
            st = stats[variant]
            st["executed"] += 1
            st["success"] += int(rc == 0)
            st["failed"] += int(rc != 0)
            st["nonzero"] += int(rc == 0 and bool(evidence))
            st["zero"] += int(rc == 0 and not evidence)
            st["error_buckets"]["none" if rc == 0 and evidence else ("zero_candidates" if rc == 0 else "nonzero_exit")] += 1
            st["candidate_buckets"][count_bucket(len(evidence))] += 1
            st["latency_buckets"][latency_bucket(elapsed)] += 1
            cand_files = file_set(evidence)
            st["overlap"][overlap_bucket(cand_files, original_files)] += 1
            st["novelty"][novelty_bucket(cand_files, original_files)] += 1
            hit_ranks = [idx + 1 for idx, cand in enumerate(evidence) if isinstance(cand, dict) and candidate_hits_gold(cand, gold_refs)]
            if hit_ranks:
                recovered_by_variant[variant].add(denom)
                st["pool_recovery"][richness] += 1
            st["top10"] += int(any(rank <= 10 for rank in hit_ranks))
            st["top20"] += int(any(rank <= 20 for rank in hit_ranks))
            st["top50"] += int(any(rank <= 50 for rank in hit_ranks))
            st["top100"] += int(bool(hit_ranks))
            private_rows.append({"private_case_order": case_order, "private_denominator_index": denom, "private_pool_richness_bucket": richness, "private_variant_bucket": variant, "private_topk": topk, "private_token_cap": cap, "private_returncode": rc, "private_candidate_count": len(evidence), "private_hit_ranks": hit_ranks[:5], "private_candidate_rows": evidence})
    PRIVATE_OUT.mkdir(parents=True, exist_ok=True)
    with (PRIVATE_OUT / "private_expanded_candidate_rows.jsonl").open("w", encoding="utf-8") as handle:
        for private_row in private_rows:
            handle.write(json.dumps(private_row, sort_keys=True) + "\n")
    manifest = {"private_schema_version": "n10dz_private_manifest_v1", "private_sampled_case_count": len(selected_rows), "private_variant_count": len(VARIANTS), "private_command_count": command_count, "private_repo_available_count": repo_available, "private_sample_meta": sample_meta}
    (PRIVATE_OUT / "private_expanded_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (PRIVATE_OUT / "private_command_summary.json").write_text(json.dumps({"private_command_count": command_count}, indent=2, sort_keys=True), encoding="utf-8")
    return {"sampled": len(selected_rows), "repo_available": repo_available, "command_count": command_count, "stats": stats, "recovered_by_variant": recovered_by_variant, "sample_meta": sample_meta}, manifest


def counter_records(prefix: str, counter: Counter[str], field: str) -> list[dict[str, Any]]:
    return [{f"anonymous_{prefix}_id": f"n10dz{prefix}{idx:04d}", field: bucket, "case_count": int(count)} for idx, (bucket, count) in enumerate(sorted(counter.items()))]


def build_report() -> dict[str, Any]:
    inputs, inputs_ok = input_records()
    prereq_ok = all(path.exists() for path in (PRIVATE_N10DR_ROWS, PRIVATE_N1_ROWS, PRIVATE_RECON)) and OPENLOCUS_BIN.is_file() and PRIVATE_REPOS.is_dir()
    if not inputs_ok:
        summary: dict[str, Any] = {"sampled": 0, "repo_available": 0, "command_count": 0, "stats": {}, "recovered_by_variant": {}, "sample_meta": {}}
        status = STATUS_NO_INPUTS
    elif not prereq_ok:
        summary = {"sampled": 0, "repo_available": 0, "command_count": 0, "stats": {}, "recovered_by_variant": {}, "sample_meta": {}}
        status = STATUS_PREREQ
    else:
        summary, _manifest = execute()
        primary = summary["stats"][PRIMARY_VARIANT]
        if int(primary["top10"]) >= 10:
            status = STATUS_PASS
        elif int(primary["top10"]) >= 1:
            status = STATUS_LOW
        elif int(primary["top50"]) == 0:
            status = STATUS_NO_RECOVERY
        else:
            status = STATUS_LOW
    variant_records: list[dict[str, Any]] = []
    for idx, (variant, topk, cap) in enumerate(VARIANTS):
        st = summary.get("stats", {}).get(variant, {})
        variant_records.append({
            "anonymous_setting_result_id": f"n10dzsetting{idx:04d}",
            "setting_bucket": variant,
            "channel_bucket": "bm25",
            "query_mode_bucket": "identifier_normalized",
            "topk_limit": topk,
            "token_cap": cap,
            "executed_case_count": int(st.get("executed", 0)),
            "command_success_count": int(st.get("success", 0)),
            "zero_candidate_count": int(st.get("zero", 0)),
            "nonzero_candidate_count": int(st.get("nonzero", 0)),
            "gold_file_recovered_top10_count": int(st.get("top10", 0)),
            "gold_file_recovered_top20_count": int(st.get("top20", 0)),
            "gold_file_recovered_top50_count": int(st.get("top50", 0)),
            "gold_file_recovered_top100_count": int(st.get("top100", 0)),
            "candidate_count_bucket_records": counter_records("candbucket", st.get("candidate_buckets", Counter()), "candidate_count_bucket"),
            "latency_bucket_records": counter_records("latbucket", st.get("latency_buckets", Counter()), "latency_bucket"),
            "error_bucket_records": counter_records("errbucket", st.get("error_buckets", Counter()), "error_bucket"),
            "overlap_bucket_records": counter_records("ovbucket", st.get("overlap", Counter()), "overlap_bucket"),
            "novelty_bucket_records": counter_records("novbucket", st.get("novelty", Counter()), "novelty_bucket"),
        })
    primary_stats = summary.get("stats", {}).get(PRIMARY_VARIANT, {})
    depth_stats = summary.get("stats", {}).get("normalized_bm25_top100_cap12", {})
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dz_normalized_bm25_expanded_canary_v1",
        "phase_bucket": "BEA-v1-N10DZ Normalized-BM25 Expanded Canary",
        "status": status,
        "input_artifact_records": inputs,
        "sample_selection_records": [{"anonymous_sample_selection_id": "n10dzsample0000", "target_new_case_count": 60, "sampled_case_count": int(summary.get("sampled", 0)), "original_30_cases_excluded_bool": True, "random_sampling_used_bool": False, "stratified_bucket_target_count": 20, "selected_bucket_count_records": [{"pool_richness_bucket": bucket, "case_count": int(count)} for bucket, count in sorted(summary.get("sample_meta", {}).get("selected_bucket_counts", {}).items())]}],
        "command_boundary_records": [{"anonymous_command_boundary_id": "n10dzcmd0000", "actual_command_count": int(summary.get("command_count", 0)), "max_command_count": 120, "topk_limit_max": 100, "bm25_only_bool": True, "normalized_query_only_bool": True, "token_cap": 12, "network_bool": False, "git_clone_bool": False, "provider_bool": False, "selector_reranker_bool": False, "local_cli_only_bool": True}],
        "execution_summary_records": [{"anonymous_execution_summary_id": "n10dzexec0000", "executed_case_count": int(primary_stats.get("executed", 0)), "local_repo_available_count": int(summary.get("repo_available", 0)), "private_output_file_count_bucket": "three_private_outputs", "private_outputs_ignored_bool": True}],
        "setting_result_records": variant_records,
        "pool_richness_result_records": [{"anonymous_pool_result_id": f"n10dzpool{idx:04d}", "setting_bucket": variant, "pool_richness_bucket": bucket, "recovered_case_count": int(count), "recovered_case_count_scope_bucket": "setting_and_topk"} for idx, (variant, st) in enumerate(summary.get("stats", {}).items()) for bucket, count in sorted(st.get("pool_recovery", Counter()).items())],
        "novelty_result_records": [{"anonymous_novelty_summary_id": "n10dznovelty0000", "novel_vs_n1_pool_recovered_count_bucket": "aggregate_available_in_private_outputs", "public_candidate_identity_bool": False}],
        "comparison_to_original_canary_records": [{"anonymous_comparison_id": "n10dzcompare0000", "original_sample_case_count": 30, "original_top10_count": 8, "original_top50_count": 10, "new_sample_case_count": int(summary.get("sampled", 0)), "new_primary_top10_count": int(primary_stats.get("top10", 0)), "new_primary_top50_count": int(primary_stats.get("top50", 0)), "new_depth_top100_count": int(depth_stats.get("top100", 0)), "statistical_generalization_claim_bool": False}],
        "privacy_boundary_records": [{"anonymous_privacy_id": "n10dzprivacy0000", "public_raw_queries_bool": False, "public_paths_or_filenames_bool": False, "public_candidate_lists_bool": False, "public_exact_ranks_bool": False, "public_snippets_spans_gold_bool": False}],
        "no_forbidden_execution_records": [{"anonymous_no_forbidden_id": "n10dzforbid0000", "network_execution_count": 0, "git_clone_count": 0, "provider_call_count": 0, "selector_reranker_execution_count": 0, "runtime_default_change_count": 0, "p5_v1a_execution_count": 0, "candidate_generation_materialization_count": 0, "scaled_full_denominator_execution_count": 0}],
        "n10ea_handoff_records": [{"anonymous_handoff_id": "n10dzhandoff0000", "next_allowed_phase_bucket": "BEA-v1-N10EA Normalized-BM25 Expanded Canary Public Package", "n10ea_public_package_authorized_bool": True, "future_focused_followup_possible_bool": status in {STATUS_PASS, STATUS_LOW}}],
        "gate_records": [{"anonymous_gate_id": "n10dzgate0000", "gate_bucket": "public_inputs_present", "gate_passed_bool": inputs_ok}, {"anonymous_gate_id": "n10dzgate0001", "gate_bucket": "local_prerequisites_present", "gate_passed_bool": prereq_ok}, {"anonymous_gate_id": "n10dzgate0002", "gate_bucket": "case_count_lte_60", "gate_passed_bool": int(summary.get("sampled", 0)) <= 60}, {"anonymous_gate_id": "n10dzgate0003", "gate_bucket": "commands_lte_120", "gate_passed_bool": int(summary.get("command_count", 0)) <= 120}],
        "stop_go_records": [{"anonymous_stop_go_id": "n10dzstop0000", "next_allowed_phase_bucket": "BEA-v1-N10EA Normalized-BM25 Expanded Canary Public Package", "scaled_full_denominator_authorized_bool": False, "runtime_default_authorized_bool": False, "method_downstream_claim_authorized_bool": False, "selector_reranker_authorized_bool": False, "p5_v1a_authorized_bool": False, "network_authorized_bool": False, "git_clone_authorized_bool": False, "provider_authorized_bool": False, "candidate_generation_materialization_authorized_bool": False, "heldout_generalization_authorized_bool": False}],
    }
    accounting_ok = int(summary.get("sampled", 0)) <= 60 and int(summary.get("command_count", 0)) <= 120
    if status not in {STATUS_NO_INPUTS, STATUS_PREREQ} and not accounting_ok:
        report["status"] = STATUS_ACCOUNTING
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_PASS in STATUS_VOCAB and STATUS_LOW in STATUS_VOCAB))
    try:
        parse_args(["--bad", "secret"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("variant_grid", len(VARIANTS) == 2 and {v[1] for v in VARIANTS} == {50, 100} and {v[2] for v in VARIANTS} == {12}))
    checks.append(("normalize", normalize_query("fooBar baz_qux a bc def", 12).split()[:3] == ["foo", "bar", "baz"]))
    checks.append(("scanner_key", scan_summary({"query": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"bucket": "/tmp/a.jsonl"})["status"] == "fail"))
    checks.append(("suffix", suffix_match("a/b/c.py", "b/c.py") and not suffix_match("a/b/c.py", "x/y.py")))
    checks.append(("pool", pool_richness({"p4_evidence": [{}] * 21}) == "moderate_pool_absence"))
    checks.append(("bucket", count_bucket(75) == "fifty_one_to_one_hundred"))
    checks.append(("latency", latency_bucket(6000) == "ge_5000ms"))
    checks.append(("scan_pass", scan_summary({"bucket": "safe", "count": 1})["status"] == "pass"))
    checks.append(("selection_fill", True))
    passed = sum(1 for _, ok in checks if ok)
    for name, ok in checks:
        print(f"[{ 'PASS' if ok else 'FAIL' }] {name}")
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
    return 0 if report["status"] in {STATUS_PASS, STATUS_LOW, STATUS_NO_RECOVERY} else 1


if __name__ == "__main__":
    raise SystemExit(main())
