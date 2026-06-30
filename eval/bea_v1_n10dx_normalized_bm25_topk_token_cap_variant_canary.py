#!/usr/bin/env python3
"""BEA-v1-N10DX Normalized-BM25 TopK/Token-Cap Variant Canary."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10dx_normalized_bm25_topk_token_cap_variant_canary"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10DW_REPORT = ROOT / "artifacts" / "bea_v1_n10dw_normalized_bm25_recovery_mechanism_analysis" / "bea_v1_n10dw_normalized_bm25_recovery_mechanism_analysis_report.json"
N10DU_REPORT = ROOT / "artifacts" / "bea_v1_n10du_targeted_candidate_source_variant_canary" / "bea_v1_n10du_targeted_candidate_source_variant_canary_report.json"
PRIVATE_N10DU_ROWS = ROOT / ".openlocus" / "research-private" / "local_n10du_targeted_source_variant_canary" / "private_variant_candidate_rows.jsonl"
PRIVATE_N1_ROWS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"
PRIVATE_RECON = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "p4l_validation" / "bea_v1_p4l.private_reconstruction.jsonl"
PRIVATE_REPOS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "repos"
OPENLOCUS_BIN = ROOT / "target" / "release" / "openlocus"
PRIVATE_OUT = ROOT / ".openlocus" / "research-private" / "local_n10dx_normalized_bm25_topk_token_cap_canary"

VARIANTS = [
    ("normalized_bm25_top50_cap12", 50, 12),
    ("normalized_bm25_top100_cap12", 100, 12),
    ("normalized_bm25_top50_cap24", 50, 24),
    ("normalized_bm25_top100_cap24", 100, 24),
]
BASELINE = "normalized_bm25_top50_cap12"

STATUS_PASS = "normalized_bm25_topk_token_cap_variant_canary_pass_n10dy_authorized"
STATUS_NO_GAIN = "normalized_bm25_topk_token_cap_variant_canary_complete_no_gain_n10dy_authorized"
STATUS_PARTIAL = "partial_normalized_bm25_topk_token_cap_variant_canary_executed_n10dy_authorized"
STATUS_NO_INPUTS = "no_go_n10dx_required_inputs_unavailable"
STATUS_PRIVACY = "no_go_n10dx_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_PASS, STATUS_NO_GAIN, STATUS_PARTIAL, STATUS_NO_INPUTS, STATUS_PRIVACY, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

FORBIDDEN_KEYS = {
    "path", "paths", "filename", "filenames", "private_path", "private_filename",
    "span", "spans", "line", "lines", "snippet", "snippets", "content", "query",
    "raw_query", "candidate_list", "candidates", "gold", "gold_path", "gold_paths",
    "exact_rank", "raw_rank", "repo", "repo_root", "hash", "provider_payload", "raw_diff",
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
    parser = SafeArgumentParser(description="BEA-v1-N10DX normalized BM25 topK/token cap canary")
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


def normalize_query(query: str, cap: int) -> str:
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


def run_retrieval(repo_root: Path, query: str, max_results: int) -> tuple[int, list[dict[str, Any]], int]:
    start = time.monotonic()
    proc = subprocess.run(
        [str(OPENLOCUS_BIN), "retrieve", query, "--channels", "bm25", "--max-results", str(max_results), "--json"],
        cwd=repo_root, text=True, capture_output=True, timeout=60,
    )
    elapsed = int((time.monotonic() - start) * 1000)
    try:
        data = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        data = {}
    evidence = data.get("evidence") if isinstance(data, dict) else []
    return proc.returncode, evidence[:max_results] if isinstance(evidence, list) else [], elapsed


def input_records() -> tuple[list[dict[str, Any]], bool]:
    inputs = [
        ("n10dw_mechanism_analysis", N10DW_REPORT, "normalized_bm25_recovery_mechanism_analysis_complete_n10dx_authorized"),
        ("n10du_targeted_canary", N10DU_REPORT, "targeted_candidate_source_variant_canary_pass_n10dv_authorized"),
    ]
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(inputs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        match = state == "present" and actual == expected
        ok = ok and match
        records.append({"anonymous_input_artifact_id": f"n10dxinput{idx:04d}", "artifact_bucket": bucket, "load_status_bucket": state, "expected_status_bucket": expected, "actual_status_bucket": actual or "unavailable", "status_match_bool": match, "public_artifact_bool": True})
    return records, ok


def n10du_sample_rows() -> list[dict[str, Any]]:
    rows = read_jsonl(PRIVATE_N10DU_ROWS)
    by_case: dict[int, dict[str, Any]] = {}
    for row in rows:
        case_order = int(row.get("private_case_order", 0))
        if row.get("private_variant_bucket") == "identifier_normalized_bm25_only":
            by_case[case_order] = row
    return [by_case[k] for k in sorted(by_case)]


def execute() -> tuple[dict[str, Any], dict[str, Any]]:
    sample_rows = n10du_sample_rows()
    n1_rows = {int(r["denominator_index_private"]): r for r in read_jsonl(PRIVATE_N1_ROWS) if isinstance(r.get("denominator_index_private"), int)}
    recon = [r for r in read_jsonl(PRIVATE_RECON) if r.get("selected_for_denominator")]
    variant_stats: dict[str, dict[str, Any]] = {name: {"executed": 0, "success": 0, "zero": 0, "nonzero": 0, "failed": 0, "top10": 0, "top20": 0, "top50": 0, "top100": 0, "candidate_buckets": Counter(), "latency_buckets": Counter(), "overlap": Counter(), "novelty": Counter()} for name, _, _ in VARIANTS}
    recovered_by_variant: dict[str, set[int]] = {name: set() for name, _, _ in VARIANTS}
    private_rows: list[dict[str, Any]] = []
    command_count = 0
    for sample in sample_rows:
        denom = int(sample.get("private_denominator_index", -1))
        n1 = n1_rows.get(denom, {})
        repo = repo_root_for(n1, recon)
        if repo is None or not repo.is_dir():
            continue
        gold_refs = n1.get("gold_paths") or []
        original_files = file_set(n1.get("p4_evidence") or [])
        for name, topk, cap in VARIANTS:
            query = normalize_query(str(n1.get("query", "")), cap)
            rc, evidence, elapsed = run_retrieval(repo, query, topk)
            command_count += 1
            stats = variant_stats[name]
            stats["executed"] += 1
            stats["success"] += int(rc == 0)
            stats["failed"] += int(rc != 0)
            stats["nonzero"] += int(rc == 0 and bool(evidence))
            stats["zero"] += int(rc == 0 and not evidence)
            stats["candidate_buckets"][count_bucket(len(evidence))] += 1
            stats["latency_buckets"][latency_bucket(elapsed)] += 1
            cand_files = file_set(evidence)
            stats["overlap"][overlap_bucket(cand_files, original_files)] += 1
            stats["novelty"][novelty_bucket(cand_files, original_files)] += 1
            hit_ranks = [idx + 1 for idx, cand in enumerate(evidence) if isinstance(cand, dict) and candidate_hits_gold(cand, gold_refs)]
            if hit_ranks:
                recovered_by_variant[name].add(denom)
            stats["top10"] += int(any(r <= 10 for r in hit_ranks))
            stats["top20"] += int(any(r <= 20 for r in hit_ranks))
            stats["top50"] += int(any(r <= 50 for r in hit_ranks))
            stats["top100"] += int(bool(hit_ranks))
            private_rows.append({"private_case_order": sample.get("private_case_order"), "private_denominator_index": denom, "private_variant_bucket": name, "private_topk": topk, "private_token_cap": cap, "private_returncode": rc, "private_candidate_count": len(evidence), "private_hit_ranks": hit_ranks[:5], "private_candidate_rows": evidence, "private_error_bucket": "none" if rc == 0 else "nonzero_exit"})
    PRIVATE_OUT.mkdir(parents=True, exist_ok=True)
    with (PRIVATE_OUT / "private_topk_token_cap_candidate_rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in private_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    manifest = {"private_schema_version": "n10dx_private_manifest_v1", "private_sampled_case_count": len(sample_rows), "private_variant_count": len(VARIANTS), "private_command_count": command_count}
    (PRIVATE_OUT / "private_topk_token_cap_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (PRIVATE_OUT / "private_topk_token_cap_command_summary.json").write_text(json.dumps({"private_command_count": command_count}, indent=2), encoding="utf-8")
    return {"sampled": len(sample_rows), "command_count": command_count, "variant_stats": variant_stats, "recovered_by_variant": recovered_by_variant}, manifest


def counter_records(prefix: str, counter: Counter[str], field: str) -> list[dict[str, Any]]:
    return [{f"anonymous_{prefix}_id": f"n10dx{prefix}{idx:04d}", field: bucket, "case_count": int(count)} for idx, (bucket, count) in enumerate(sorted(counter.items()))]


def build_report() -> dict[str, Any]:
    inputs, inputs_ok = input_records()
    prereq_ok = all(p.exists() for p in (PRIVATE_N10DU_ROWS, PRIVATE_N1_ROWS, PRIVATE_RECON)) and OPENLOCUS_BIN.is_file() and PRIVATE_REPOS.is_dir()
    if not inputs_ok or not prereq_ok:
        summary: dict[str, Any] = {"sampled": 0, "command_count": 0, "variant_stats": {}, "recovered_by_variant": {}}
        status = STATUS_NO_INPUTS
    else:
        summary, _manifest = execute()
        baseline = summary["variant_stats"][BASELINE]
        baseline_recovered = len(summary["recovered_by_variant"][BASELINE])
        improved = False
        for name, _topk, _cap in VARIANTS:
            stats = summary["variant_stats"][name]
            if len(summary["recovered_by_variant"][name]) > baseline_recovered or stats["top10"] > baseline["top10"] or stats["top20"] > baseline["top20"] or stats["top50"] > baseline["top50"]:
                improved = True
        status = STATUS_PASS if improved else STATUS_NO_GAIN
    variant_result_records = []
    baseline_stats = summary.get("variant_stats", {}).get(BASELINE, {})
    baseline_cases = set(summary.get("recovered_by_variant", {}).get(BASELINE, set()))
    best_variant = "none"
    best_score = (-1, -1, -1, -1)
    for idx, (name, topk, cap) in enumerate(VARIANTS):
        stats = summary.get("variant_stats", {}).get(name, {})
        recovered_cases = set(summary.get("recovered_by_variant", {}).get(name, set()))
        score = (len(recovered_cases), int(stats.get("top10", 0)), int(stats.get("top20", 0)), int(stats.get("top50", 0)))
        if score > best_score:
            best_score = score
            best_variant = name
        variant_result_records.append({
            "anonymous_variant_result_id": f"n10dxvarres{idx:04d}",
            "variant_bucket": name,
            "channel_bucket": "bm25",
            "query_mode_bucket": "identifier_normalized",
            "topk_limit": topk,
            "token_cap": cap,
            "executed_case_count": int(stats.get("executed", 0)),
            "retrieval_success_count": int(stats.get("success", 0)),
            "zero_candidate_case_count": int(stats.get("zero", 0)),
            "nonzero_candidate_case_count": int(stats.get("nonzero", 0)),
            "command_failed_count": int(stats.get("failed", 0)),
            "gold_file_recovered_top10_count": int(stats.get("top10", 0)),
            "gold_file_recovered_top20_count": int(stats.get("top20", 0)),
            "gold_file_recovered_top50_count": int(stats.get("top50", 0)),
            "gold_file_recovered_top100_count": int(stats.get("top100", 0)),
            "cases_recovered_count": len(recovered_cases),
            "additional_cases_vs_baseline_count": len(recovered_cases - baseline_cases),
            "candidate_count_bucket_records": counter_records("candbucket", stats.get("candidate_buckets", Counter()), "candidate_count_bucket"),
            "latency_bucket_records": counter_records("latbucket", stats.get("latency_buckets", Counter()), "latency_bucket"),
            "overlap_bucket_records": counter_records("ovbucket", stats.get("overlap", Counter()), "overlap_bucket"),
            "novelty_bucket_records": counter_records("novbucket", stats.get("novelty", Counter()), "novelty_bucket"),
        })
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dx_normalized_bm25_topk_token_cap_variant_canary_v1",
        "phase_bucket": "BEA-v1-N10DX Normalized-BM25 TopK/Token-Cap Variant Canary",
        "status": status,
        "input_artifact_records": inputs,
        "topk_token_cap_contract_records": [{"anonymous_contract_id": f"n10dxcontract{idx:04d}", "variant_bucket": name, "channel_bucket": "bm25", "query_mode_bucket": "identifier_normalized", "topk_limit": topk, "token_cap": cap, "fixed_predeclared_bool": True} for idx, (name, topk, cap) in enumerate(VARIANTS)],
        "query_normalization_records": [{"anonymous_query_norm_id": "n10dxnorm0000", "deterministic_bool": True, "gold_free_bool": True, "token_caps_tested": [12, 24], "fallback_to_original_if_empty_bool": True}],
        "command_boundary_records": [{"anonymous_command_boundary_id": "n10dxcmd0000", "actual_command_count": int(summary.get("command_count", 0)), "max_command_count": 120, "topk_limit_max": 100, "network_bool": False, "git_clone_bool": False, "provider_bool": False, "selector_reranker_bool": False, "local_cli_only_bool": True}],
        "private_execution_summary_records": [{"anonymous_private_execution_id": "n10dxexec0000", "sampled_case_count": int(summary.get("sampled", 0)), "variant_count": len(VARIANTS), "private_output_file_count_bucket": "three_private_outputs", "private_rows_written_bucket": "many", "same_scoped_private_rows_read_bool": True}],
        "variant_result_records": variant_result_records,
        "cross_variant_delta_records": [{
            "anonymous_cross_variant_id": "n10dxcross0000",
            "baseline_variant_bucket": BASELINE,
            "baseline_cases_recovered_count": len(baseline_cases),
            "best_variant_bucket": best_variant,
            "best_cases_recovered_count": best_score[0],
            "topk100_adds_recovered_cases_bool": any(r["topk_limit"] == 100 and r["additional_cases_vs_baseline_count"] > 0 for r in variant_result_records),
            "cap24_adds_recovered_cases_bool": any(r["token_cap"] == 24 and r["additional_cases_vs_baseline_count"] > 0 for r in variant_result_records),
            "material_improvement_bool": status == STATUS_PASS,
        }],
        "privacy_boundary_records": [{"anonymous_privacy_id": "n10dxprivacy0000", "public_raw_queries_bool": False, "public_paths_or_filenames_bool": False, "public_candidate_lists_bool": False, "public_exact_ranks_bool": False, "public_snippets_spans_gold_bool": False}],
        "no_forbidden_execution_records": [{"anonymous_no_forbidden_id": "n10dxforbid0000", "network_execution_count": 0, "git_clone_count": 0, "provider_call_count": 0, "selector_reranker_execution_count": 0, "runtime_default_change_count": 0, "p5_v1a_execution_count": 0, "candidate_generation_materialization_count": 0}],
        "n10dy_handoff_records": [{"anonymous_handoff_id": "n10dxhandoff0000", "next_allowed_phase_bucket": "BEA-v1-N10DY Normalized-BM25 TopK/Token-Cap Canary Public Package", "n10dy_public_package_authorized_bool": True, "future_focused_followup_possible_bool": status == STATUS_PASS}],
        "gate_records": [{"anonymous_gate_id": "n10dxgate0000", "gate_bucket": "public_inputs_present", "gate_passed_bool": inputs_ok}, {"anonymous_gate_id": "n10dxgate0001", "gate_bucket": "local_prerequisites_present", "gate_passed_bool": prereq_ok}, {"anonymous_gate_id": "n10dxgate0002", "gate_bucket": "variant_count_four", "gate_passed_bool": len(VARIANTS) == 4}, {"anonymous_gate_id": "n10dxgate0003", "gate_bucket": "commands_lte_120", "gate_passed_bool": int(summary.get("command_count", 0)) <= 120}],
        "stop_go_records": [{"anonymous_stop_go_id": "n10dxstop0000", "next_allowed_phase_bucket": "BEA-v1-N10DY Normalized-BM25 TopK/Token-Cap Canary Public Package", "scaled_retrieval_authorized_bool": False, "network_authorized_bool": False, "git_clone_authorized_bool": False, "provider_authorized_bool": False, "candidate_generation_materialization_authorized_bool": False, "selector_reranker_authorized_bool": False, "runtime_default_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_downstream_claim_authorized_bool": False, "heldout_generalization_authorized_bool": False}],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_PASS in STATUS_VOCAB and STATUS_NO_GAIN in STATUS_VOCAB))
    try:
        parse_args(["--bad", "secret"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("variant_grid", len(VARIANTS) == 4 and {v[1] for v in VARIANTS} == {50, 100} and {v[2] for v in VARIANTS} == {12, 24}))
    checks.append(("normalize_cap12", normalize_query("fooBar baz_qux alpha beta gamma delta epsilon zeta eta theta iota kappa lambda", 12).split()[-1] == "theta"))
    checks.append(("normalize_cap24", len(normalize_query("one two three four five six seven eight nine ten eleven twelve thirteen", 24).split()) == 13))
    checks.append(("scanner_key", scan_summary({"query": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"bucket": "/tmp/a.jsonl"})["status"] == "fail"))
    checks.append(("suffix", suffix_match("a/b/c.py", "b/c.py") and not suffix_match("a/b/c.py", "z.py")))
    checks.append(("bucket", count_bucket(75) == "fifty_one_to_one_hundred"))
    checks.append(("latency", latency_bucket(6000) == "ge_5000ms"))
    checks.append(("overlap", overlap_bucket({"a/b/c.py"}, {"b/c.py"}) == "overlap_near_duplicate"))
    checks.append(("scan_pass", scan_summary({"bucket": "safe", "count": 1})["status"] == "pass"))
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
    return 0 if report["status"] in {STATUS_PASS, STATUS_NO_GAIN, STATUS_PARTIAL} else 1


if __name__ == "__main__":
    raise SystemExit(main())
